"""
METACOD GLP-1 module — API-layer request/response schemas.

Thin wrappers over the agent's input/output models. We do not redefine
PatientContext or PharmacistAssessment here — they live in pharmacist_agent.py
and are reused directly. This file adds only the HTTP-layer concerns:
locale selection, physician identity, audit-log filtering, etc.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# Re-export the agent's input model so callers can import everything from schemas.*
from pharmacist_agent import PatientContext  # noqa: F401


# ============================================================================
# /glp1/assess
# ============================================================================

class AssessRequest(BaseModel):
    """Wraps PatientContext with the optional locale and acting-physician hint."""
    patient: PatientContext
    locale: str = Field(default="ru", description="Output language: ru | en | he")
    physician_id: Optional[str] = None
    physician_name: Optional[str] = None


class AssessResponse(BaseModel):
    visit_id: str
    locale: str
    direction: str = Field(description="ltr | rtl — UI layout hint")
    assessment: dict = Field(description="Full PharmacistAssessment with resolved i18n_text fields")
    rule_pack_version: str
    drug_db_version: str
    sign_off_status: str = "pending_sign_off"


# ============================================================================
# /glp1/sign-off
# ============================================================================

class SignOffRequest(BaseModel):
    visit_id: str
    physician_id: str
    physician_name: str
    status: str = Field(default="signed", description="signed | rejected | amended")
    notes: Optional[str] = None
    amended_payload: Optional[dict] = None


class SignOffResponse(BaseModel):
    sign_off_id: int
    visit_id: str
    status: str
    signed_at: datetime


# ============================================================================
# /glp1/visit/{id}
# ============================================================================

class VisitSummary(BaseModel):
    visit_id: str
    patient_id: str
    triage_color: str
    glp1_decision: str
    sign_off_status: str
    rule_pack_version: str
    drug_db_version: str
    agent_version: str
    created_at: datetime
    rule_ids_triggered: list[str] = Field(default_factory=list)


class VisitDetail(BaseModel):
    summary: VisitSummary
    input_payload: dict
    output_payload: dict = Field(description="Output with resolved i18n if locale provided")
    direction: str = "ltr"
    sign_offs: list[dict] = Field(default_factory=list)


# ============================================================================
# /glp1/audit-log
# ============================================================================

class AuditLogEntry(BaseModel):
    id: int
    event_type: str
    actor_id: Optional[str] = None
    actor_role: Optional[str] = None
    target_table: Optional[str] = None
    target_id: Optional[str] = None
    payload: Optional[dict] = None
    occurred_at: datetime


class AuditLogResponse(BaseModel):
    total: int
    page: int
    page_size: int
    entries: list[AuditLogEntry]


# ============================================================================
# /glp1/rules and /glp1/drugs (read-only introspection)
# ============================================================================

class RuleSummary(BaseModel):
    rule_id: str
    name: str
    severity: str
    evidence_grade: str
    mechanism: str
    sources: list[str] = Field(default_factory=list)


class DrugSummary(BaseModel):
    profile_id: str
    display_name: dict[str, str]
    drug_class: str = Field(alias="class")
    route: str
    evidence_grade: str
    last_reviewed: Optional[str] = None

    model_config = {"populate_by_name": True}


# ============================================================================
# Error envelope
# ============================================================================

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    rule_pack_version: Optional[str] = None
