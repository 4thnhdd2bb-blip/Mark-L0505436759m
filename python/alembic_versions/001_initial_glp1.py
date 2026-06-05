"""METACOD GLP-1 — initial schema

Revision ID: 001_initial_glp1
Revises:
Create Date: 2026-06-03

Creates the full initial schema for the GLP-1 module:
  - patients
  - visits (full input + output JSON snapshot, version-pinned)
  - medication_snapshots (denormalized for fast querying)
  - rule_triggers (audit: every rule that fired)
  - sign_offs (White Coat Rule)
  - audit_log (append-only event log)

Run with: `alembic upgrade head` after configuring alembic.ini.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# ----- Alembic identifiers -----
revision = "001_initial_glp1"
down_revision = None
branch_labels = None
depends_on = None


# ----- Enum values (mirror SAEnum in database.py) -----
TRIAGE_COLORS = ("green", "yellow", "red")
GLP1_DECISIONS = ("CONTINUE", "HOLD", "REVIEW")
SIGN_OFF_STATUSES = ("pending_sign_off", "signed", "rejected", "amended")
AUDIT_EVENT_TYPES = (
    "assessment_created",
    "sign_off_requested",
    "sign_off_completed",
    "sign_off_rejected",
    "report_exported",
    "rule_pack_updated",
    "drug_db_updated",
)


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("external_mrn", sa.String(128), nullable=True),
        sa.Column("age_years", sa.Integer, nullable=False),
        sa.Column("sex", sa.String(16), nullable=False),
        sa.Column("weight_kg", sa.Float, nullable=True),
        sa.Column("locale", sa.String(8), nullable=False, server_default="ru"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_patients_external_mrn", "patients", ["external_mrn"])

    op.create_table(
        "visits",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("patient_id", sa.String(64), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("input_payload", sa.JSON, nullable=False),
        sa.Column("output_payload", sa.JSON, nullable=False),
        sa.Column("triage_color", sa.Enum(*TRIAGE_COLORS, name="triagecolorenum"), nullable=False),
        sa.Column("glp1_decision", sa.Enum(*GLP1_DECISIONS, name="glp1decisionenum"), nullable=False),
        sa.Column("sign_off_status", sa.Enum(*SIGN_OFF_STATUSES, name="signoffstatusenum"),
                  nullable=False, server_default="pending_sign_off"),
        sa.Column("rule_pack_version", sa.String(32), nullable=False),
        sa.Column("drug_db_version", sa.String(32), nullable=False),
        sa.Column("agent_version", sa.String(32), nullable=False, server_default="2.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_visits_patient_id", "visits", ["patient_id"])
    op.create_index("ix_visits_triage_color", "visits", ["triage_color"])
    op.create_index("ix_visits_sign_off_status", "visits", ["sign_off_status"])

    op.create_table(
        "medication_snapshots",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("visit_id", sa.String(64), sa.ForeignKey("visits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("profile_id", sa.String(128), nullable=False),
        sa.Column("route", sa.String(32), nullable=False, server_default="oral"),
        sa.Column("dose", sa.String(128), nullable=True),
        sa.Column("is_essential", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_med_snap_visit_id", "medication_snapshots", ["visit_id"])
    op.create_index("ix_med_snap_profile_id", "medication_snapshots", ["profile_id"])

    op.create_table(
        "rule_triggers",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("visit_id", sa.String(64), sa.ForeignKey("visits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", sa.String(128), nullable=False),
        sa.Column("rule_pack_version", sa.String(32), nullable=False),
        sa.Column("medication_name", sa.String(256), nullable=False),
        sa.Column("medication_profile_id", sa.String(128), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("evidence_grade", sa.String(4), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_rule_triggers_visit_id", "rule_triggers", ["visit_id"])
    op.create_index("ix_rule_triggers_rule_id", "rule_triggers", ["rule_id"])
    op.create_index("ix_rule_triggers_profile_id", "rule_triggers", ["medication_profile_id"])

    op.create_table(
        "sign_offs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("visit_id", sa.String(64), sa.ForeignKey("visits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("physician_id", sa.String(128), nullable=False),
        sa.Column("physician_name", sa.String(256), nullable=False),
        sa.Column("status", sa.Enum(*SIGN_OFF_STATUSES, name="signoffstatusenum"), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("amended_payload", sa.JSON, nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sign_offs_visit_id", "sign_offs", ["visit_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.Enum(*AUDIT_EVENT_TYPES, name="auditeventtypeenum"), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=True),
        sa.Column("actor_role", sa.String(64), nullable=True),
        sa.Column("target_table", sa.String(64), nullable=True),
        sa.Column("target_id", sa.String(64), nullable=True),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_event_type", "audit_log", ["event_type"])
    op.create_index("ix_audit_target_id", "audit_log", ["target_id"])
    op.create_index("ix_audit_occurred_at", "audit_log", ["occurred_at"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("sign_offs")
    op.drop_table("rule_triggers")
    op.drop_table("medication_snapshots")
    op.drop_table("visits")
    op.drop_table("patients")

    # Drop enums (PostgreSQL needs explicit drop)
    sa.Enum(name="auditeventtypeenum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="signoffstatusenum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="glp1decisionenum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="triagecolorenum").drop(op.get_bind(), checkfirst=True)
