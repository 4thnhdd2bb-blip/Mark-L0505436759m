"""
METACOD GLP-1 Complication Prevention — database models

SQLAlchemy 2.0 ORM models supporting:
  - Patient + Visit lifecycle
  - Snapshot of medications at the time of each assessment (immutable audit trail)
  - Rule trigger audit log (which rules fired, with rule_pack version pin)
  - White Coat Rule sign-off (pending → signed → released to EHR)
  - General audit logging (every assessment, every sign-off, every export)

Compatible with FastAPI / SQLAlchemy async or sync sessions.
Default backend: SQLite for development; PostgreSQL for production (set DATABASE_URL).

Author: METACOD team
License: proprietary
"""

from __future__ import annotations

import enum
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)


# ============================================================================
# Engine / session factory
# ============================================================================

DATABASE_URL = os.environ.get(
    "METACOD_GLP1_DATABASE_URL",
    "sqlite:///./metacod_glp1.db",
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


class Base(DeclarativeBase):
    pass


# ============================================================================
# Enums
# ============================================================================

class TriageColorEnum(str, enum.Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class GLP1DecisionEnum(str, enum.Enum):
    CONTINUE = "CONTINUE"
    HOLD = "HOLD"
    REVIEW = "REVIEW"


class SignOffStatusEnum(str, enum.Enum):
    PENDING = "pending_sign_off"
    SIGNED = "signed"
    REJECTED = "rejected"
    AMENDED = "amended"


class AuditEventTypeEnum(str, enum.Enum):
    ASSESSMENT_CREATED = "assessment_created"
    SIGN_OFF_REQUESTED = "sign_off_requested"
    SIGN_OFF_COMPLETED = "sign_off_completed"
    SIGN_OFF_REJECTED = "sign_off_rejected"
    REPORT_EXPORTED = "report_exported"
    RULE_PACK_UPDATED = "rule_pack_updated"
    DRUG_DB_UPDATED = "drug_db_updated"


# ============================================================================
# Helpers
# ============================================================================

def _gen_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================================
# Models
# ============================================================================

class Patient(Base):
    """Minimal patient record. PHI handling is deferred to outer system; this model
    holds a stable identifier and basic demographics needed by the rule engine."""

    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _gen_id("PAT"))
    external_mrn: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    age_years: Mapped[int] = mapped_column(Integer, nullable=False)
    sex: Mapped[str] = mapped_column(String(16), nullable=False)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    locale: Mapped[str] = mapped_column(String(8), default="ru", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    visits: Mapped[list["Visit"]] = relationship(back_populates="patient", cascade="all, delete-orphan")


class Visit(Base):
    """One assessment session = one Visit. Stores the full input snapshot (patient
    context as submitted) and the full output (assessment as produced by the agent).
    Immutable once signed off."""

    __tablename__ = "visits"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _gen_id("VIS"))
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False)

    # Input snapshot — exact PatientContext used for the assessment
    input_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Output snapshot — exact PharmacistAssessment produced
    output_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Quick-query summary fields (denormalized for indexing)
    triage_color: Mapped[TriageColorEnum] = mapped_column(SAEnum(TriageColorEnum), nullable=False)
    glp1_decision: Mapped[GLP1DecisionEnum] = mapped_column(SAEnum(GLP1DecisionEnum), nullable=False)
    sign_off_status: Mapped[SignOffStatusEnum] = mapped_column(
        SAEnum(SignOffStatusEnum), default=SignOffStatusEnum.PENDING, nullable=False
    )

    # Versioning — required for SaMD traceability
    rule_pack_version: Mapped[str] = mapped_column(String(32), nullable=False)
    drug_db_version: Mapped[str] = mapped_column(String(32), nullable=False)
    agent_version: Mapped[str] = mapped_column(String(32), default="2.0.0", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    patient: Mapped[Patient] = relationship(back_populates="visits")
    medication_snapshots: Mapped[list["MedicationSnapshot"]] = relationship(
        back_populates="visit", cascade="all, delete-orphan"
    )
    rule_triggers: Mapped[list["RuleTrigger"]] = relationship(
        back_populates="visit", cascade="all, delete-orphan"
    )
    sign_offs: Mapped[list["SignOff"]] = relationship(back_populates="visit", cascade="all, delete-orphan")


class MedicationSnapshot(Base):
    """Each medication as submitted at the time of a visit. Captured separately for
    fast querying ('which patients were on apixaban during 2026-Q2?')."""

    __tablename__ = "medication_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[str] = mapped_column(ForeignKey("visits.id", ondelete="CASCADE"), index=True, nullable=False)

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    profile_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    route: Mapped[str] = mapped_column(String(32), default="oral", nullable=False)
    dose: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_essential: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    visit: Mapped[Visit] = relationship(back_populates="medication_snapshots")


class RuleTrigger(Base):
    """Audit: every rule that fired during a visit. Captures rule_id, the rule_pack
    version that produced it, the medication it applied to, and the severity/grade —
    enough to reconstruct decisions later for regulatory review."""

    __tablename__ = "rule_triggers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[str] = mapped_column(ForeignKey("visits.id", ondelete="CASCADE"), index=True, nullable=False)

    rule_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    rule_pack_version: Mapped[str] = mapped_column(String(32), nullable=False)
    medication_name: Mapped[str] = mapped_column(String(256), nullable=False)
    medication_profile_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_grade: Mapped[str] = mapped_column(String(4), nullable=False)

    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    visit: Mapped[Visit] = relationship(back_populates="rule_triggers")


class SignOff(Base):
    """White Coat Rule: every assessment requires explicit physician sign-off before
    becoming part of the patient's record / being exportable to EHR. Stores the
    physician identifier, timestamp, and any amendment notes."""

    __tablename__ = "sign_offs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[str] = mapped_column(ForeignKey("visits.id", ondelete="CASCADE"), index=True, nullable=False)

    physician_id: Mapped[str] = mapped_column(String(128), nullable=False)
    physician_name: Mapped[str] = mapped_column(String(256), nullable=False)

    status: Mapped[SignOffStatusEnum] = mapped_column(SAEnum(SignOffStatusEnum), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    amended_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    visit: Mapped[Visit] = relationship(back_populates="sign_offs")


class AuditLog(Base):
    """Generic append-only audit log for SaMD compliance. Every state change in the
    system is recorded here, regardless of which table it touched."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[AuditEventTypeEnum] = mapped_column(SAEnum(AuditEventTypeEnum), index=True, nullable=False)

    actor_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    target_table: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)

    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True, nullable=False)


class LearningAmendment(Base):
    """A single typed difference between the agent's original assessment and the
    physician-amended version, captured at sign-off (active learning substrate).

    One sign-off amendment may produce many rows — one per change-type per rule_id.
    Decomposed structure makes pattern queries cheap, e.g.:

        SELECT rule_id, COUNT(*) FROM learning_amendments
        WHERE amendment_type = 'rule_removed' GROUP BY rule_id ORDER BY 2 DESC;
    """

    __tablename__ = "learning_amendments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    visit_id = Column(String(64), nullable=False, index=True)
    sign_off_id = Column(Integer, ForeignKey("sign_offs.id"), nullable=False, index=True)

    rule_id = Column(String(128), nullable=True, index=True)
    amendment_type = Column(String(32), nullable=False, index=True)

    original_value_json = Column(Text, nullable=True)
    amended_value_json = Column(Text, nullable=True)

    physician_id = Column(String(64), nullable=False, index=True)
    physician_notes = Column(Text, nullable=True)

    # Pinned versions at sign-off — critical for SaMD trace
    rule_pack_version = Column(String(16), nullable=True)
    drug_db_version = Column(String(16), nullable=True)
    agent_version = Column(String(16), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        UniqueConstraint(
            "visit_id", "sign_off_id", "rule_id", "amendment_type",
            name="uq_learning_amendments_dedupe",
        ),
        Index(
            "ix_learning_amendments_rule_type_created",
            "rule_id", "amendment_type", "created_at",
        ),
    )


# ============================================================================
# Public helpers
# ============================================================================

def init_db() -> None:
    """Create all tables. For dev only — production uses Alembic migrations."""
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """FastAPI dependency: yield a session."""
    return SessionLocal()


def persist_assessment(
    session: Session,
    patient_input: dict,
    assessment: dict,
    rule_findings: list[dict],
) -> str:
    """Persist a complete assessment.

    Args:
        session: SQLAlchemy session
        patient_input: full PatientContext as dict (will be stored verbatim as input_payload)
        assessment: full PharmacistAssessment as dict (stored as output_payload)
        rule_findings: list of InteractionFinding dicts (one per fired rule)

    Returns:
        visit_id (string)
    """
    # Ensure patient row exists (or create a stub)
    patient_id = patient_input.get("patient_id")
    patient = session.get(Patient, patient_id) if patient_id else None
    if patient is None:
        patient = Patient(
            id=patient_id or _gen_id("PAT"),
            age_years=patient_input.get("age_years", 0),
            sex=patient_input.get("sex", "unknown"),
            weight_kg=patient_input.get("weight_kg"),
        )
        session.add(patient)
        session.flush()

    # Create the Visit
    visit = Visit(
        patient_id=patient.id,
        input_payload=patient_input,
        output_payload=assessment,
        triage_color=TriageColorEnum(assessment["triage_color"]),
        glp1_decision=GLP1DecisionEnum(assessment["forecast"]["glp1_dosing"]["decision"]),
        rule_pack_version=assessment["rule_pack_version"],
        drug_db_version=assessment["drug_db_version"],
        agent_version=assessment.get("agent_version", "2.0.0"),
    )
    session.add(visit)
    session.flush()

    # Snapshot medications
    for med in patient_input.get("medications", []):
        session.add(MedicationSnapshot(
            visit_id=visit.id,
            name=med["name"],
            profile_id=med["profile_id"],
            route=med.get("route", "oral"),
            dose=med.get("dose"),
            is_essential=med.get("is_essential", False),
        ))

    # Snapshot rule triggers
    for finding in rule_findings:
        session.add(RuleTrigger(
            visit_id=visit.id,
            rule_id=finding["rule_id"],
            rule_pack_version=assessment["rule_pack_version"],
            medication_name=finding["medication_name"],
            medication_profile_id=finding.get("medication_profile_id", ""),
            severity=finding.get("severity", "moderate"),
            evidence_grade=finding.get("evidence_grade", "C"),
        ))

    # Audit log entry
    session.add(AuditLog(
        event_type=AuditEventTypeEnum.ASSESSMENT_CREATED,
        target_table="visits",
        target_id=visit.id,
        payload={
            "patient_id": patient.id,
            "triage": assessment["triage_color"],
            "rule_count": len(rule_findings),
            "rule_pack_version": assessment["rule_pack_version"],
        },
    ))

    session.commit()
    return visit.id


def sign_off_visit(
    session: Session,
    visit_id: str,
    physician_id: str,
    physician_name: str,
    status: SignOffStatusEnum = SignOffStatusEnum.SIGNED,
    notes: Optional[str] = None,
    amended_payload: Optional[dict] = None,
) -> int:
    """Apply White Coat Rule sign-off to a visit."""
    visit = session.get(Visit, visit_id)
    if visit is None:
        raise ValueError(f"Visit not found: {visit_id}")

    sign_off = SignOff(
        visit_id=visit_id,
        physician_id=physician_id,
        physician_name=physician_name,
        status=status,
        notes=notes,
        amended_payload=amended_payload,
    )
    session.add(sign_off)

    visit.sign_off_status = status

    event_type = {
        SignOffStatusEnum.SIGNED: AuditEventTypeEnum.SIGN_OFF_COMPLETED,
        SignOffStatusEnum.REJECTED: AuditEventTypeEnum.SIGN_OFF_REJECTED,
        SignOffStatusEnum.AMENDED: AuditEventTypeEnum.SIGN_OFF_COMPLETED,
    }.get(status, AuditEventTypeEnum.SIGN_OFF_REQUESTED)

    session.add(AuditLog(
        event_type=event_type,
        actor_id=physician_id,
        actor_role="physician",
        target_table="visits",
        target_id=visit_id,
        payload={"status": status.value, "notes": notes},
    ))

    session.commit()
    session.refresh(sign_off)
    return sign_off.id


# ============================================================================
# CLI bootstrap
# ============================================================================

if __name__ == "__main__":
    print(f"Initializing database at {DATABASE_URL}")
    init_db()
    print("Done. Tables:")
    for tbl in Base.metadata.sorted_tables:
        print(f"  - {tbl.name}")
