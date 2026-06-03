"""
METACOD GLP-1 — FHIR R4 mapper.

Pure transformation: (PharmacistAssessment + visit metadata) → FHIR Bundle.

  - No DB access
  - No network calls
  - Deterministic: identical inputs always produce byte-identical Bundle JSON
    (uses uuid5(NAMESPACE_URL, visit_id + resource_type + index))

This separation lets us:
  1. Unit-test the mapping in isolation
  2. Cache Bundle output keyed on visit_id
  3. Replay any historical visit's FHIR Bundle for audit / SaMD review
  4. Plug the mapper into any deployment (FastAPI, batch job, message bus)

The mapping is opinionated — METACOD-specific decisions encoded:
  - System URI namespace: "http://metacod.health/codes/{slug}"
  - Patient reference: "Patient/{patient_id}" (logical reference; EHR resolves)
  - Visit identifier: "Encounter/{visit_id}" (referenced by Observations)
  - Triage emits one Observation with category=survey, code from triage colour
  - Each rule-based finding emits one Observation with code=rule_id
  - Each unique lab-plan test emits one ServiceRequest (deduplicated across rules)
  - Forecast emits one ClinicalImpression with finding[] pointing at the Observations

Caller is expected to supply already-resolved (locale-aware) text on the input
PharmacistAssessment. The mapper itself does not consult i18n catalogs — it
copies the supplied texts verbatim onto FHIR fields. The locale of the Bundle
is set via `language` and a `Meta.tag` for the resolved locale.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from schemas.fhir_r4 import (
    Annotation,
    Bundle,
    BundleEntry,
    ClinicalImpression,
    ClinicalImpressionFinding,
    CodeableConcept,
    Coding,
    Duration,
    Meta,
    MedicationStatement,
    Observation,
    Reference,
    ServiceRequest,
    Timing,
    TimingRepeat,
)

# ----------------------------------------------------------------------------
# Namespaces
# ----------------------------------------------------------------------------

NAMESPACE_METACOD = uuid.UUID("6f6f8a9c-2c4f-5a4e-9e7c-2c4f5a4e9e7c")  # arbitrary fixed UUID v4 used as v5 seed

SYS_METACOD_DRUG = "http://metacod.health/codes/drug-db"
SYS_METACOD_RULE = "http://metacod.health/codes/rule"
SYS_METACOD_TRIAGE = "http://metacod.health/codes/triage"
SYS_METACOD_LAB = "http://metacod.health/codes/lab-plan"
SYS_METACOD_FORECAST = "http://metacod.health/codes/forecast"
SYS_LOINC = "http://loinc.org"
SYS_UCUM = "http://unitsofmeasure.org"
SYS_FHIR_OBS_CATEGORY = "http://terminology.hl7.org/CodeSystem/observation-category"
SYS_FHIR_INTERPRETATION = "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation"
SYS_FHIR_SERVICE_CATEGORY = "http://terminology.hl7.org/CodeSystem/service-category"
SYS_FHIR_EVIDENCE_GRADE = "http://metacod.health/codes/evidence-grade"

# Loose LOINC mapping for the most common test_name strings we use internally.
# When a test_name is not in this map, we fall back to METACOD lab-plan system.
LOINC_MAP = {
    "TSH": "11580-8",
    "free_T4": "3026-2",
    "INR": "6301-6",
    "eGFR": "33914-3",
    "creatinine": "2160-0",
    "K": "2823-3",
    "Na": "2951-2",
    "Mg": "2601-3",
    "Ca": "2008-9",
    "ALT": "1742-6",
    "AST": "1920-8",
    "albumin": "1751-7",
    "CRP": "1988-5",
    "hemoglobin": "718-7",
    "ferritin": "2276-4",
    "transferrin_saturation": "2502-3",
    "ECG_QTc": "8633-8",
    "HbA1c": "4548-4",
    "digoxin_level": "10535-3",
    "lithium_level": "14334-7",
    "phenytoin_free_and_total_level": "3968-5",
    "valproate_free_and_total_level": "4086-5",
    "clozapine_level": "9610-2",
    "tacrolimus_or_cyclosporine_trough": "29240-1",
    "itraconazole_trough_level": "29239-3",
    "posaconazole_trough_level": "57878-0",
    "voriconazole_trough_level": "33874-9",
}


# ----------------------------------------------------------------------------
# ID generation — deterministic uuid5(NAMESPACE, visit_id + resource_type + key)
# ----------------------------------------------------------------------------

def _det_uuid(visit_id: str, resource_type: str, key: str) -> str:
    return str(uuid.uuid5(NAMESPACE_METACOD, f"{visit_id}|{resource_type}|{key}"))


def _urn(uuid_str: str) -> str:
    return f"urn:uuid:{uuid_str}"


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

_INTERPRETATION_BY_SEVERITY = {
    "high": Coding(system=SYS_FHIR_INTERPRETATION, code="HU", display="Significantly high"),
    "moderate": Coding(system=SYS_FHIR_INTERPRETATION, code="H", display="High"),
    "low": Coding(system=SYS_FHIR_INTERPRETATION, code="N", display="Normal"),
}

_OBS_CATEGORY_SURVEY = Coding(system=SYS_FHIR_OBS_CATEGORY, code="survey", display="Survey")
_OBS_CATEGORY_THERAPY = Coding(system=SYS_FHIR_OBS_CATEGORY, code="therapy", display="Therapy")


def _patient_reference(patient_id: str) -> Reference:
    return Reference(reference=f"Patient/{patient_id}", type="Patient", display=f"Patient {patient_id}")


def _encounter_reference(visit_id: str) -> Reference:
    return Reference(reference=f"Encounter/{visit_id}", type="Encounter", display=f"Visit {visit_id}")


def _evidence_grade_coding(grade) -> CodeableConcept:
    # accept enum or str
    code = grade.value if hasattr(grade, "value") else str(grade)
    label_map = {"A": "Regulatory or RCT", "B": "Observational + mechanistic", "C": "Mechanistic / expert"}
    return CodeableConcept(coding=[Coding(system=SYS_FHIR_EVIDENCE_GRADE, code=code, display=label_map.get(code, code))])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _drug_codeable(profile_id: str, display_name: str) -> CodeableConcept:
    return CodeableConcept(
        coding=[Coding(system=SYS_METACOD_DRUG, code=profile_id, display=display_name)],
        text=display_name,
    )


def _lab_codeable(test_name: str, label: Optional[str] = None) -> CodeableConcept:
    coding = []
    loinc = LOINC_MAP.get(test_name)
    if loinc:
        coding.append(Coding(system=SYS_LOINC, code=loinc, display=test_name))
    coding.append(Coding(system=SYS_METACOD_LAB, code=test_name, display=label or test_name))
    return CodeableConcept(coding=coding, text=label or test_name)


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------

def assessment_to_fhir_bundle(
    assessment: dict,
    visit_id: str,
    locale: str = "en",
    authored_on: Optional[str] = None,
) -> Bundle:
    """
    Map an assessment object (PharmacistAssessment.model_dump()) to a FHIR Bundle.

    Args:
      assessment: serialized PharmacistAssessment (already locale-resolved by the
                  i18n layer — every i18n_key has a sibling i18n_text)
      visit_id: external visit identifier
      locale: BCP-47 language tag; used for Bundle.language and Meta.tag
      authored_on: ISO 8601 timestamp for when the assessment was authored; defaults to now

    Returns:
      Bundle resource ready to serialize to JSON.
    """
    patient_id: str = assessment["patient_id"]
    authored = authored_on or _now_iso()
    subject_ref = _patient_reference(patient_id)
    encounter_ref = _encounter_reference(visit_id)

    # Locale tag on Bundle meta
    meta = Meta(
        lastUpdated=authored,
        source=f"http://metacod.health/glp1/visit/{visit_id}",
        tag=[
            Coding(system="urn:ietf:bcp:47", code=locale, display=f"Locale {locale}"),
            Coding(system="http://metacod.health/codes/rule-pack", code=assessment.get("rule_pack_version", "unknown")),
            Coding(system="http://metacod.health/codes/drug-db", code=assessment.get("drug_db_version", "unknown")),
            Coding(system="http://metacod.health/codes/agent", code=assessment.get("agent_version", "unknown")),
        ],
    )

    entries: list[BundleEntry] = []

    # ---------- MedicationStatement: one per interaction's medication (deduplicated by name) ----------
    # We use the interactions list because patient.medications isn't on the assessment;
    # the mapper operates on the assessment alone. Adopters wanting MedicationStatements
    # for non-interaction meds should extend this loop with the visit's medication snapshot.
    seen_meds: set[str] = set()
    for idx, finding in enumerate(assessment.get("interactions", [])):
        med_name = finding.get("medication_name", "")
        if not med_name or med_name in seen_meds:
            continue
        seen_meds.add(med_name)
        # We don't have profile_id directly on the finding, so we synthesize a stable key from the name
        med_key = med_name.lower().replace(" ", "_")[:64]
        ms_id = _det_uuid(visit_id, "MedicationStatement", med_key)
        ms = MedicationStatement(
            id=ms_id,
            subject=subject_ref,
            medicationCodeableConcept=_drug_codeable(med_key, med_name),
            effectiveDateTime=authored,
            dateAsserted=authored,
            note=[Annotation(text=f"Mentioned in METACOD GLP-1 assessment for visit {visit_id}", time=authored)],
        )
        entries.append(BundleEntry(fullUrl=_urn(ms_id), resource=ms.model_dump(exclude_none=True)))

    # ---------- ServiceRequest: one per unique lab plan item across all interactions ----------
    seen_labs: dict[str, dict] = {}  # canonical test_name → {text, interval_weeks, rule_ids}
    for finding in assessment.get("interactions", []):
        for lab in finding.get("lab_plan", []):
            t = lab.get("test")
            if not t:
                continue
            entry = seen_labs.setdefault(t, {
                "text": lab.get("i18n_text") or lab.get("i18n_key", ""),
                "interval_weeks": lab.get("interval_weeks"),
                "rule_ids": [],
            })
            rid = lab.get("rule_id") or finding.get("rule_id")
            if rid and rid not in entry["rule_ids"]:
                entry["rule_ids"].append(rid)

    for test_name, info in seen_labs.items():
        sr_id = _det_uuid(visit_id, "ServiceRequest", test_name)
        timing = None
        if info.get("interval_weeks") is not None:
            timing = Timing(repeat=TimingRepeat(
                boundsDuration=Duration(value=float(info["interval_weeks"]), unit="weeks", system=SYS_UCUM, code="wk"),
            ))
        notes = [Annotation(text=info["text"] or test_name, time=authored)]
        if info["rule_ids"]:
            notes.append(Annotation(text=f"Triggered by rule(s): {', '.join(info['rule_ids'])}", time=authored))
        sr = ServiceRequest(
            id=sr_id,
            subject=subject_ref,
            code=_lab_codeable(test_name, label=info.get("text")),
            authoredOn=authored,
            category=[CodeableConcept(coding=[Coding(system=SYS_FHIR_SERVICE_CATEGORY, code="108252007", display="Laboratory procedure")])],
            occurrenceTiming=timing,
            note=notes,
        )
        entries.append(BundleEntry(fullUrl=_urn(sr_id), resource=sr.model_dump(exclude_none=True)))

    # ---------- Observation: triage banner ----------
    triage_color = assessment.get("triage_color", "green")
    triage_text = assessment.get("triage_summary_i18n_text") or assessment.get("triage_summary_i18n_key", "")
    triage_obs_id = _det_uuid(visit_id, "Observation", "triage")
    triage_obs = Observation(
        id=triage_obs_id,
        subject=subject_ref,
        category=[CodeableConcept(coding=[_OBS_CATEGORY_SURVEY])],
        code=CodeableConcept(
            coding=[Coding(system=SYS_METACOD_TRIAGE, code=triage_color, display=f"METACOD triage: {triage_color}")],
            text=triage_text,
        ),
        effectiveDateTime=authored,
        valueString=triage_text,
        interpretation=[CodeableConcept(coding=[_INTERPRETATION_BY_SEVERITY.get(_severity_from_triage(triage_color))])],
        derivedFrom=[encounter_ref],
        note=[Annotation(text=triage_text, time=authored)] if triage_text else [],
    )
    triage_entry_id = triage_obs_id  # keep for ClinicalImpression linking
    entries.append(BundleEntry(fullUrl=_urn(triage_obs_id), resource=triage_obs.model_dump(exclude_none=True)))

    # ---------- Observation: one per InteractionFinding ----------
    interaction_obs_ids: list[tuple[str, str]] = []  # (rule_id, observation_id)
    for idx, finding in enumerate(assessment.get("interactions", [])):
        rule_id = finding.get("rule_id", f"unknown_{idx}")
        med_name = finding.get("medication_name", "")
        obs_id = _det_uuid(visit_id, "Observation", f"finding-{idx}-{rule_id}")
        interaction_obs_ids.append((rule_id, obs_id))

        # Build a concatenated note from physician_actions, patient_actions, mechanism
        note_lines: list[str] = []
        for a in finding.get("physician_actions", []):
            txt = a.get("i18n_text") or a.get("i18n_key", "")
            if txt:
                note_lines.append(f"[physician] {txt}")
        for a in finding.get("patient_actions", []):
            txt = a.get("i18n_text") or a.get("i18n_key", "")
            if txt:
                note_lines.append(f"[patient] {txt}")
        # Mechanism is in admin_trace — include in note for audit; downstream EHR can filter
        admin = finding.get("admin_trace") or {}
        if admin.get("mechanism"):
            note_lines.append(f"[mechanism] {admin['mechanism']}")
        sources = finding.get("sources") or []
        if sources:
            note_lines.append(f"[sources] {' · '.join(sources)}")

        severity = finding.get("severity", "moderate")
        interp = _INTERPRETATION_BY_SEVERITY.get(severity)

        obs = Observation(
            id=obs_id,
            subject=subject_ref,
            category=[CodeableConcept(coding=[_OBS_CATEGORY_THERAPY])],
            code=CodeableConcept(
                coding=[Coding(system=SYS_METACOD_RULE, code=rule_id, display=finding.get("rule_name", rule_id))],
                text=finding.get("rule_name", rule_id),
            ),
            effectiveDateTime=authored,
            valueString=f"{finding.get('rule_name', rule_id)} — {med_name}".strip(" —"),
            interpretation=[CodeableConcept(coding=[interp])] if interp else [],
            derivedFrom=[encounter_ref],
            note=[Annotation(text=line, time=authored) for line in note_lines],
        )
        # Attach evidence grade as a category alongside therapy
        obs.category.append(_evidence_grade_coding(finding.get("evidence_grade", "C")))
        entries.append(BundleEntry(fullUrl=_urn(obs_id), resource=obs.model_dump(exclude_none=True)))

    # ---------- ClinicalImpression: forecast + GLP-1 decision ----------
    forecast = assessment.get("forecast", {})
    glp1 = forecast.get("glp1_dosing", {})
    decision = glp1.get("decision", "")
    decision_text = glp1.get("i18n_text") or glp1.get("i18n_key", "")
    rationale_texts = glp1.get("rationale_i18n_texts") or []

    impression_id = _det_uuid(visit_id, "ClinicalImpression", "forecast")
    impression_notes: list[Annotation] = []
    if decision_text:
        impression_notes.append(Annotation(text=f"GLP-1 decision ({decision}): {decision_text}", time=authored))
    for r in rationale_texts:
        impression_notes.append(Annotation(text=f"Rationale: {r}", time=authored))
    for risk in forecast.get("future_risks", []):
        txt = risk.get("i18n_text") or risk.get("i18n_key", "")
        tf = risk.get("timeframe_weeks")
        if txt:
            impression_notes.append(Annotation(text=f"Future risk (+{tf}w): {txt}", time=authored))
    for adj in forecast.get("chronic_med_adjustments", []):
        adj_text = adj.get("adjustment_i18n_text") or adj.get("adjustment_i18n_key", "")
        med_name = adj.get("medication_name", "")
        if adj_text:
            impression_notes.append(Annotation(text=f"Chronic adjustment ({med_name}): {adj_text}", time=authored))
    # v3 dose adjustments
    for da in assessment.get("dose_adjustments", []):
        impression_notes.append(Annotation(
            text=f"Dose individualization ({da.get('source','')}): {da.get('medication_name','')} "
                 f"→ {da.get('adjustment_type','')} {da.get('adjustment_magnitude_percent','')}% "
                 f"[{da.get('rationale_i18n_key','')}]",
            time=authored,
        ))

    impression = ClinicalImpression(
        id=impression_id,
        subject=subject_ref,
        date=authored,
        summary=(f"GLP-1: {decision}. " + (decision_text or "")).strip(),
        finding=[
            ClinicalImpressionFinding(
                itemReference=Reference(reference=f"Observation/{obs_id}", type="Observation"),
                basis=rule_id,
            )
            for rule_id, obs_id in interaction_obs_ids
        ] + [
            ClinicalImpressionFinding(
                itemReference=Reference(reference=f"Observation/{triage_entry_id}", type="Observation"),
                basis="triage",
            )
        ],
        note=impression_notes,
    )
    entries.append(BundleEntry(fullUrl=_urn(impression_id), resource=impression.model_dump(exclude_none=True)))

    bundle = Bundle(
        id=_det_uuid(visit_id, "Bundle", "root"),
        meta=meta,
        type="collection",
        timestamp=authored,
        total=len(entries),
        entry=entries,
    )
    bundle.language = locale  # set via extra=allow
    return bundle


# ----------------------------------------------------------------------------
# Helpers exported for tests
# ----------------------------------------------------------------------------

def _severity_from_triage(triage_color: str) -> str:
    """Map a triage colour to FHIR-grade severity."""
    return {"red": "high", "yellow": "moderate", "green": "low"}.get(triage_color, "moderate")
