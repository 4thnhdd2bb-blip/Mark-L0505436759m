"""METACOD GLP-1 — Alembic migration 002: learning_amendments table.

Captures decomposed differences between an original assessment and the
physician-amended version at sign-off time. One row per amendment-type per
rule, queryable for patterns (e.g. "which rules are most often removed?").

Revises: 001_initial_glp1
Revision ID: 002_learning_amendments
"""

from alembic import op
import sqlalchemy as sa


revision = "002_learning_amendments"
down_revision = "001_initial_glp1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_amendments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("visit_id", sa.String(64), nullable=False, index=True),
        sa.Column("sign_off_id", sa.Integer, nullable=False, index=True),
        sa.Column("rule_id", sa.String(128), nullable=True, index=True),
        sa.Column(
            "amendment_type",
            sa.String(32),
            nullable=False,
            index=True,
            # enum-like: triage_changed | glp1_decision_changed | rule_removed |
            #           rule_added | severity_changed | action_removed | action_added |
            #           lab_removed | lab_added | lab_interval_changed |
            #           patient_action_removed | patient_action_added
        ),
        sa.Column("original_value_json", sa.Text, nullable=True),
        sa.Column("amended_value_json", sa.Text, nullable=True),
        sa.Column("physician_id", sa.String(64), nullable=False, index=True),
        sa.Column("physician_notes", sa.Text, nullable=True),
        sa.Column("rule_pack_version", sa.String(16), nullable=True),
        sa.Column("drug_db_version", sa.String(16), nullable=True),
        sa.Column("agent_version", sa.String(16), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "visit_id", "sign_off_id", "rule_id", "amendment_type",
            name="uq_learning_amendments_dedupe",
        ),
        sa.ForeignKeyConstraint(["sign_off_id"], ["sign_offs.id"], name="fk_learning_amendments_sign_off"),
    )
    op.create_index(
        "ix_learning_amendments_rule_type_created",
        "learning_amendments",
        ["rule_id", "amendment_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_learning_amendments_rule_type_created", table_name="learning_amendments")
    op.drop_table("learning_amendments")
