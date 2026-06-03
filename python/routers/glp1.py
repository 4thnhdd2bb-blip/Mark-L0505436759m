"""
METACOD GLP-1 module — FastAPI router.

Exposes the complete GLP-1 complication-prevention surface as REST endpoints:

  POST   /glp1/assess                      — run a new assessment for a patient
  POST   /glp1/sign-off                    — physician sign-off (White Coat Rule)
  GET    /glp1/visit/{id}                  — fetch a visit + sign-off history
  GET    /glp1/visit/{id}/report.html      — printable clinical / admin report
  GET    /glp1/visit/{id}/report.pdf       — same report rendered as PDF
  GET    /glp1/audit-log                   — filterable audit trail
  GET    /glp1/rules                       — introspection: rule_pack contents
  GET    /glp1/drugs                       — introspection: drug DB profiles

Notes:
  - All clinical strings come back in the requested locale via resolve_i18n.
  - The router mounts at /glp1 by default; the v4 app keeps its own routes
    untouched.
  - PDF generation uses WeasyPrint if installed; otherwise the endpoint returns
    HTTP 501 and the client falls back to browser print-to-PDF of report.html.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

# Local imports (flat layout — adjust to your v4 package layout)
from database import (
    AuditLog,
    SessionLocal,
    SignOffStatusEnum,
    Visit,
    persist_assessment,
    sign_off_visit,
)
from pharmacist_agent import PharmacistAgent

from reports.html_renderer import render_report_html
from schemas.glp1_api import (
    AssessRequest,
    AssessResponse,
    AuditLogEntry,
    AuditLogResponse,
    DrugSummary,
    ErrorResponse,
    RuleSummary,
    SignOffRequest,
    SignOffResponse,
    VisitDetail,
    VisitSummary,
)
from services.i18n import i18n_cache, resolve_i18n
from services.fhir_mapper import assessment_to_fhir_bundle
from services.resources import ResourceBundle, get_resources

import json as _json


router = APIRouter(
    prefix="/glp1",
    tags=["GLP-1 Module"],
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)


# ============================================================================
# DB session dependency
# ============================================================================

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Helpers
# ============================================================================

def _build_rule_findings(assessment_dict: dict, patient_dict: dict) -> list[dict]:
    """Build the persistence-layer rule_findings list from assessment.interactions
    + patient.medications. Lookup table maps medication name → profile_id."""
    med_name_to_profile = {
        m["name"]: m["profile_id"]
        for m in patient_dict.get("medications", [])
    }
    findings: list[dict] = []
    for interaction in assessment_dict.get("interactions", []):
        findings.append({
            "rule_id": interaction["rule_id"],
            "medication_name": interaction["medication_name"],
            "medication_profile_id": med_name_to_profile.get(interaction["medication_name"], ""),
            "severity": interaction.get("severity", "moderate"),
            "evidence_grade": interaction.get("evidence_grade", "C"),
        })
    return findings


def _direction_for(locale: str) -> str:
    return i18n_cache.direction(locale)


# ============================================================================
# POST /glp1/assess
# ============================================================================

@router.post("/assess", response_model=AssessResponse, status_code=status.HTTP_201_CREATED)
def assess(
    payload: AssessRequest,
    db: Session = Depends(get_db),
    resources: ResourceBundle = Depends(get_resources),
) -> AssessResponse:
    """Run a pharmacist assessment and persist the visit (pending sign-off)."""

    agent = PharmacistAgent(
        patient=payload.patient,
        rule_pack=resources.rule_pack,
        drug_db=resources.drug_db,
    )
    assessment = agent.assess()

    assessment_dict = assessment.model_dump()
    patient_dict = payload.patient.model_dump()
    rule_findings = _build_rule_findings(assessment_dict, patient_dict)

    visit_id = persist_assessment(
        session=db,
        patient_input=patient_dict,
        assessment=assessment_dict,
        rule_findings=rule_findings,
    )

    resolved = resolve_i18n(assessment_dict, locale=payload.locale)

    return AssessResponse(
        visit_id=visit_id,
        locale=payload.locale,
        direction=_direction_for(payload.locale),
        assessment=resolved,
        rule_pack_version=resources.rule_pack_version,
        drug_db_version=resources.drug_db_version,
        sign_off_status="pending_sign_off",
    )


# ============================================================================
# POST /glp1/sign-off — White Coat Rule
# ============================================================================

@router.post("/sign-off", response_model=SignOffResponse)
def sign_off(
    payload: SignOffRequest,
    db: Session = Depends(get_db),
) -> SignOffResponse:
    try:
        status_enum = SignOffStatusEnum(payload.status)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{payload.status}'. "
                   f"Expected one of: {[s.value for s in SignOffStatusEnum]}",
        ) from exc

    try:
        sign_off_id = sign_off_visit(
            session=db,
            visit_id=payload.visit_id,
            physician_id=payload.physician_id,
            physician_name=payload.physician_name,
            status=status_enum,
            notes=payload.notes,
            amended_payload=payload.amended_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return SignOffResponse(
        sign_off_id=sign_off_id,
        visit_id=payload.visit_id,
        status=status_enum.value,
        signed_at=datetime.utcnow(),
    )


# ============================================================================
# GET /glp1/visit/{visit_id}
# ============================================================================

@router.get("/visit/{visit_id}", response_model=VisitDetail)
def get_visit(
    visit_id: str,
    locale: str = Query("ru", description="ru | en | he"),
    db: Session = Depends(get_db),
) -> VisitDetail:
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit not found: {visit_id}")

    rule_ids = [t.rule_id for t in visit.rule_triggers]
    summary = VisitSummary(
        visit_id=visit.id,
        patient_id=visit.patient_id,
        triage_color=visit.triage_color.value,
        glp1_decision=visit.glp1_decision.value,
        sign_off_status=visit.sign_off_status.value,
        rule_pack_version=visit.rule_pack_version,
        drug_db_version=visit.drug_db_version,
        agent_version=visit.agent_version,
        created_at=visit.created_at,
        rule_ids_triggered=rule_ids,
    )

    output_resolved = resolve_i18n(visit.output_payload, locale=locale)

    sign_offs = [{
        "id": so.id,
        "physician_id": so.physician_id,
        "physician_name": so.physician_name,
        "status": so.status.value,
        "notes": so.notes,
        "signed_at": so.signed_at.isoformat(),
    } for so in visit.sign_offs]

    return VisitDetail(
        summary=summary,
        input_payload=visit.input_payload,
        output_payload=output_resolved,
        direction=_direction_for(locale),
        sign_offs=sign_offs,
    )


# ============================================================================
# GET /glp1/visit/{visit_id}/report.html
# ============================================================================

@router.get("/visit/{visit_id}/report.html", response_class=Response)
def get_visit_report_html(
    visit_id: str,
    locale: str = Query("ru"),
    layer: str = Query("clinical", description="clinical | admin"),
    db: Session = Depends(get_db),
) -> Response:
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit not found: {visit_id}")

    if layer not in ("clinical", "admin"):
        raise HTTPException(status_code=400, detail="layer must be 'clinical' or 'admin'")

    output_resolved = resolve_i18n(visit.output_payload, locale=locale)

    html = render_report_html(
        visit_id=visit.id,
        patient=visit.input_payload,
        assessment=output_resolved,
        locale=locale,
        direction=_direction_for(locale),
        layer=layer,
        sign_off_status=visit.sign_off_status.value,
        created_at=visit.created_at.isoformat(),
    )

    return Response(content=html, media_type="text/html; charset=utf-8")


# ============================================================================
# GET /glp1/visit/{visit_id}/report.pdf
# ============================================================================

@router.get("/visit/{visit_id}/report.pdf", response_class=Response)
def get_visit_report_pdf(
    visit_id: str,
    locale: str = Query("ru"),
    layer: str = Query("clinical"),
    db: Session = Depends(get_db),
) -> Response:
    try:
        from weasyprint import HTML  # type: ignore
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Server-side PDF generation requires WeasyPrint. "
                   "Install with: pip install weasyprint. "
                   "Alternative: GET /report.html and use browser print-to-PDF.",
        )

    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit not found: {visit_id}")

    output_resolved = resolve_i18n(visit.output_payload, locale=locale)

    html_str = render_report_html(
        visit_id=visit.id,
        patient=visit.input_payload,
        assessment=output_resolved,
        locale=locale,
        direction=_direction_for(locale),
        layer=layer,
        sign_off_status=visit.sign_off_status.value,
        created_at=visit.created_at.isoformat(),
    )

    pdf_bytes = HTML(string=html_str).write_pdf()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="visit_{visit_id}.pdf"'},
    )


# ============================================================================
# GET /glp1/visit/{visit_id}/fhir-bundle — HL7 FHIR R4 export
# ============================================================================

@router.get("/visit/{visit_id}/fhir-bundle", response_class=Response)
def get_visit_fhir_bundle(
    visit_id: str,
    locale: str = Query("ru", description="Locale for the resolved FHIR text: ru | en | he"),
    db: Session = Depends(get_db),
) -> Response:
    """Return the FHIR R4 Bundle representation of the saved assessment.

    Read-only and deterministic for a given (visit_id, locale): every resource
    has a uuid5-derived id, so repeated calls produce byte-identical JSON (good
    for ETag and EHR-side deduplication). Maps the stored (admin-layer) assessment;
    push the physician-signed visit to the EHR.
    """
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit not found: {visit_id}")

    # The stored output_payload carries i18n keys; resolve to text for the locale
    # so the FHIR resources carry human-readable strings.
    resolved = resolve_i18n(visit.output_payload, locale=locale)
    authored_on = visit.created_at.isoformat() if visit.created_at else None

    bundle = assessment_to_fhir_bundle(
        assessment=resolved,
        visit_id=str(visit.id),
        locale=locale,
        authored_on=authored_on,
    )

    payload = bundle.model_dump(exclude_none=True)
    body = _json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    etag = f'W/"{hash((visit_id, locale, len(body))) & 0xFFFFFFFF:08x}"'
    return Response(
        content=body,
        media_type="application/fhir+json",
        headers={"ETag": etag, "Cache-Control": "private, max-age=300"},
    )


# ============================================================================
# GET /glp1/audit-log
# ============================================================================

@router.get("/audit-log", response_model=AuditLogResponse)
def get_audit_log(
    event_type: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> AuditLogResponse:
    stmt = select(AuditLog)
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if target_id:
        stmt = stmt.where(AuditLog.target_id == target_id)

    # Count
    count_rows = db.execute(stmt).scalars().all()
    total = len(count_rows)

    # Page
    offset = (page - 1) * page_size
    paged = sorted(count_rows, key=lambda r: r.occurred_at, reverse=True)[offset: offset + page_size]

    entries = [
        AuditLogEntry(
            id=row.id,
            event_type=row.event_type.value,
            actor_id=row.actor_id,
            actor_role=row.actor_role,
            target_table=row.target_table,
            target_id=row.target_id,
            payload=row.payload,
            occurred_at=row.occurred_at,
        )
        for row in paged
    ]

    return AuditLogResponse(total=total, page=page, page_size=page_size, entries=entries)


# ============================================================================
# GET /glp1/rules — read-only introspection
# ============================================================================

@router.get("/rules", response_model=list[RuleSummary])
def list_rules(
    evidence_grade: Optional[str] = Query(None, description="A | B | C"),
    resources: ResourceBundle = Depends(get_resources),
) -> list[RuleSummary]:
    rules = resources.rule_pack.get("rules", [])
    if evidence_grade:
        rules = [r for r in rules if r.get("evidence_grade") == evidence_grade]
    return [
        RuleSummary(
            rule_id=r["rule_id"],
            name=r.get("name", ""),
            severity=r.get("severity", "moderate"),
            evidence_grade=r.get("evidence_grade", "C"),
            mechanism=r.get("mechanism", ""),
            sources=r.get("sources", []),
        )
        for r in rules
    ]


# ============================================================================
# GET /glp1/drugs — read-only introspection
# ============================================================================

@router.get("/drugs", response_model=list[DrugSummary])
def list_drugs(
    drug_class: Optional[str] = Query(None, alias="class"),
    search: Optional[str] = Query(None, description="case-insensitive substring on profile_id"),
    resources: ResourceBundle = Depends(get_resources),
) -> list[DrugSummary]:
    profiles = resources.drug_db.get("profiles", [])

    if drug_class:
        profiles = [p for p in profiles if p.get("class") == drug_class]
    if search:
        s = search.lower()
        profiles = [p for p in profiles if s in p.get("profile_id", "").lower()]

    return [
        DrugSummary(
            profile_id=p["profile_id"],
            display_name=p.get("display_name", {}),
            **{"class": p.get("class", "")},
            route=p.get("route", "oral"),
            evidence_grade=p.get("evidence_grade", "C"),
            last_reviewed=p.get("last_reviewed"),
        )
        for p in profiles
    ]


# ============================================================================
# GET /glp1/_info — startup-state sanity probe (handy in dev / CI)
# ============================================================================

@router.get("/_info")
def info(resources: ResourceBundle = Depends(get_resources)) -> dict:
    return {
        "rule_pack_version": resources.rule_pack_version,
        "drug_db_version": resources.drug_db_version,
        "rule_count": resources.rule_count,
        "drug_count": resources.drug_count,
        "available_locales": i18n_cache.available_locales(),
        "agent_version": "2.0.0",
    }
