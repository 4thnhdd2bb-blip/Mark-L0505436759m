"""METACOD GLP-1 — Active learning unit tests.

Two layers:
  1. `compute_amendments()` — pure diff logic, no DB. Most tests here.
  2. `capture_amendment()` + `aggregate_patterns()` — uses an in-memory SQLite
     to verify idempotency and end-to-end flow without a real Postgres.

The diff logic tests cover every amendment_type at least once.
"""

from __future__ import annotations

import sys
import json
from datetime import datetime
from copy import deepcopy

import pytest

from services.learning import (
    Amendment,
    compute_amendments,
    AMENDMENT_TYPES,
)

pytestmark = pytest.mark.unit


# ============================================================================
# Pure diff tests — compute_amendments()
# ============================================================================

@pytest.fixture
def base_assessment() -> dict:
    """A small but realistic assessment with two interactions."""
    return {
        "patient_id": "P-001",
        "triage_color": "yellow",
        "triage_summary_i18n_key": "triage.yellow.hold",
        "triage_summary_i18n_text": "Hold and reassess",
        "rule_pack_version": "2.0.0",
        "drug_db_version": "2.0.0",
        "agent_version": "3.0.0",
        "interactions": [
            {
                "rule_id": "LT4_TABLET_PPI",
                "rule_name": "LT4 + PPI",
                "medication_name": "Levothyroxine 100 mcg",
                "severity": "high",
                "evidence_grade": "A",
                "physician_actions": [
                    {"i18n_key": "action.lt4_check_tsh_4w", "i18n_text": "Check TSH at 4 weeks", "evidence_grade": "A"},
                    {"i18n_key": "action.lt4_consider_liquid", "i18n_text": "Consider liquid LT4", "evidence_grade": "A"},
                ],
                "patient_actions": [
                    {"i18n_key": "patient.lt4_separate", "i18n_text": "Take LT4 30–60 min before PPI", "evidence_grade": "A"},
                ],
                "lab_plan": [
                    {"test": "TSH", "interval_weeks": 4, "i18n_key": "lab.tsh_4w"},
                    {"test": "free_T4", "interval_weeks": 4, "i18n_key": "lab.ft4_4w"},
                ],
            },
            {
                "rule_id": "EGFR_LOW_DOAC",
                "rule_name": "DOAC at low eGFR",
                "medication_name": "Apixaban 5 mg",
                "severity": "high",
                "evidence_grade": "A",
                "physician_actions": [
                    {"i18n_key": "action.doac_check_label", "i18n_text": "Check DOAC label renal dose", "evidence_grade": "A"},
                ],
                "patient_actions": [],
                "lab_plan": [
                    {"test": "eGFR", "interval_weeks": 4, "i18n_key": "lab.egfr_4w"},
                ],
            },
        ],
        "forecast": {
            "glp1_dosing": {"decision": "HOLD", "i18n_key": "forecast.glp1.hold", "i18n_text": "Hold escalation"},
            "future_risks": [],
            "chronic_med_adjustments": [],
        },
    }


class TestComputeAmendmentsNoChange:

    def test_identical_returns_empty(self, base_assessment):
        out = compute_amendments(base_assessment, deepcopy(base_assessment))
        assert out == []

    def test_empty_both_returns_empty(self):
        out = compute_amendments({}, {})
        assert out == []

    def test_resilient_to_missing_keys(self, base_assessment):
        amended = deepcopy(base_assessment)
        del amended["forecast"]
        out = compute_amendments(base_assessment, amended)
        # We expect a glp1_decision_changed (None vs HOLD)
        types = {a.amendment_type for a in out}
        assert "glp1_decision_changed" in types


class TestComputeAmendmentsTopLevel:

    def test_triage_changed(self, base_assessment):
        amended = deepcopy(base_assessment)
        amended["triage_color"] = "green"
        amended["triage_summary_i18n_text"] = "Stable"
        out = compute_amendments(base_assessment, amended)
        triage = [a for a in out if a.amendment_type == "triage_changed"]
        assert len(triage) == 1
        assert triage[0].rule_id is None
        assert triage[0].original_value["triage_color"] == "yellow"
        assert triage[0].amended_value["triage_color"] == "green"

    def test_glp1_decision_changed(self, base_assessment):
        amended = deepcopy(base_assessment)
        amended["forecast"]["glp1_dosing"]["decision"] = "CONTINUE"
        out = compute_amendments(base_assessment, amended)
        glp1 = [a for a in out if a.amendment_type == "glp1_decision_changed"]
        assert len(glp1) == 1
        assert glp1[0].original_value["decision"] == "HOLD"
        assert glp1[0].amended_value["decision"] == "CONTINUE"


class TestComputeAmendmentsRuleLevel:

    def test_rule_removed(self, base_assessment):
        amended = deepcopy(base_assessment)
        amended["interactions"] = [f for f in amended["interactions"] if f["rule_id"] != "EGFR_LOW_DOAC"]
        out = compute_amendments(base_assessment, amended)
        removed = [a for a in out if a.amendment_type == "rule_removed"]
        assert len(removed) == 1
        assert removed[0].rule_id == "EGFR_LOW_DOAC"
        assert removed[0].original_value["rule_id"] == "EGFR_LOW_DOAC"
        assert removed[0].amended_value is None

    def test_rule_added(self, base_assessment):
        amended = deepcopy(base_assessment)
        amended["interactions"].append({
            "rule_id": "MANUAL_PHYSICIAN_NOTE",
            "rule_name": "Physician-added warning",
            "medication_name": "Apixaban",
            "severity": "moderate",
            "evidence_grade": "C",
            "physician_actions": [],
            "patient_actions": [],
            "lab_plan": [],
        })
        out = compute_amendments(base_assessment, amended)
        added = [a for a in out if a.amendment_type == "rule_added"]
        assert len(added) == 1
        assert added[0].rule_id == "MANUAL_PHYSICIAN_NOTE"

    def test_severity_changed(self, base_assessment):
        amended = deepcopy(base_assessment)
        amended["interactions"][0]["severity"] = "moderate"  # high → moderate
        out = compute_amendments(base_assessment, amended)
        sev = [a for a in out if a.amendment_type == "severity_changed"]
        assert len(sev) == 1
        assert sev[0].rule_id == "LT4_TABLET_PPI"
        assert sev[0].original_value["severity"] == "high"
        assert sev[0].amended_value["severity"] == "moderate"


class TestComputeAmendmentsActions:

    def test_action_removed(self, base_assessment):
        amended = deepcopy(base_assessment)
        amended["interactions"][0]["physician_actions"] = [
            a for a in amended["interactions"][0]["physician_actions"]
            if a["i18n_key"] != "action.lt4_consider_liquid"
        ]
        out = compute_amendments(base_assessment, amended)
        removed = [a for a in out if a.amendment_type == "action_removed"]
        assert len(removed) == 1
        assert removed[0].rule_id == "LT4_TABLET_PPI"
        assert removed[0].original_value["i18n_key"] == "action.lt4_consider_liquid"

    def test_action_added(self, base_assessment):
        amended = deepcopy(base_assessment)
        amended["interactions"][0]["physician_actions"].append(
            {"i18n_key": "action.lt4_recheck_after_3mo", "i18n_text": "Recheck in 3 months", "evidence_grade": "C"}
        )
        out = compute_amendments(base_assessment, amended)
        added = [a for a in out if a.amendment_type == "action_added"]
        assert len(added) == 1
        assert added[0].amended_value["i18n_key"] == "action.lt4_recheck_after_3mo"

    def test_patient_action_removed(self, base_assessment):
        amended = deepcopy(base_assessment)
        amended["interactions"][0]["patient_actions"] = []
        out = compute_amendments(base_assessment, amended)
        removed = [a for a in out if a.amendment_type == "patient_action_removed"]
        assert len(removed) == 1
        assert removed[0].original_value["i18n_key"] == "patient.lt4_separate"


class TestComputeAmendmentsLabPlan:

    def test_lab_removed(self, base_assessment):
        amended = deepcopy(base_assessment)
        amended["interactions"][0]["lab_plan"] = [
            l for l in amended["interactions"][0]["lab_plan"] if l["test"] != "free_T4"
        ]
        out = compute_amendments(base_assessment, amended)
        removed = [a for a in out if a.amendment_type == "lab_removed"]
        assert len(removed) == 1
        assert removed[0].original_value["test"] == "free_T4"

    def test_lab_added(self, base_assessment):
        amended = deepcopy(base_assessment)
        amended["interactions"][0]["lab_plan"].append(
            {"test": "anti_TPO", "interval_weeks": 12, "i18n_key": "lab.anti_tpo_12w"}
        )
        out = compute_amendments(base_assessment, amended)
        added = [a for a in out if a.amendment_type == "lab_added"]
        assert len(added) == 1
        assert added[0].amended_value["test"] == "anti_TPO"

    def test_lab_interval_changed(self, base_assessment):
        amended = deepcopy(base_assessment)
        amended["interactions"][0]["lab_plan"][0]["interval_weeks"] = 6  # TSH 4w → 6w
        out = compute_amendments(base_assessment, amended)
        ch = [a for a in out if a.amendment_type == "lab_interval_changed"]
        assert len(ch) == 1
        assert ch[0].original_value == {"test": "TSH", "interval_weeks": 4}
        assert ch[0].amended_value == {"test": "TSH", "interval_weeks": 6}


class TestComputeAmendmentsCombined:

    def test_multiple_amendment_types_in_one_diff(self, base_assessment):
        """A realistic 'physician disagrees with multiple things' scenario."""
        amended = deepcopy(base_assessment)
        # 1. Downgrade triage
        amended["triage_color"] = "green"
        # 2. Change GLP-1 decision
        amended["forecast"]["glp1_dosing"]["decision"] = "REVIEW"
        # 3. Remove one rule
        amended["interactions"] = [f for f in amended["interactions"] if f["rule_id"] != "EGFR_LOW_DOAC"]
        # 4. Downgrade severity on the remaining rule
        amended["interactions"][0]["severity"] = "moderate"
        # 5. Remove a lab
        amended["interactions"][0]["lab_plan"] = [
            l for l in amended["interactions"][0]["lab_plan"] if l["test"] != "free_T4"
        ]

        out = compute_amendments(base_assessment, amended)
        types = {a.amendment_type for a in out}
        assert types == {"triage_changed", "glp1_decision_changed", "rule_removed", "severity_changed", "lab_removed"}

    def test_amendment_types_all_in_constant(self):
        """Every type compute_amendments can emit is also listed in AMENDMENT_TYPES."""
        emitted_types = {
            "triage_changed", "glp1_decision_changed",
            "rule_removed", "rule_added", "severity_changed",
            "action_removed", "action_added",
            "patient_action_removed", "patient_action_added",
            "lab_removed", "lab_added", "lab_interval_changed",
        }
        assert emitted_types <= AMENDMENT_TYPES


# ============================================================================
# Amendment.to_db_kwargs
# ============================================================================

class TestAmendmentSerialization:

    def test_to_db_kwargs_serializes_json(self):
        amd = Amendment(
            amendment_type="rule_removed",
            rule_id="R1",
            original_value={"severity": "high"},
            amended_value=None,
        )
        kwargs = amd.to_db_kwargs(
            visit_id="V1", sign_off_id=1, physician_id="DR1", physician_notes="reason",
            rule_pack_version="2.0.0",
        )
        assert kwargs["rule_id"] == "R1"
        assert kwargs["amendment_type"] == "rule_removed"
        assert json.loads(kwargs["original_value_json"]) == {"severity": "high"}
        assert kwargs["amended_value_json"] is None
        assert kwargs["rule_pack_version"] == "2.0.0"

    def test_to_db_kwargs_handles_none_values(self):
        amd = Amendment(amendment_type="rule_added", rule_id="R2", original_value=None, amended_value={"x": 1})
        kwargs = amd.to_db_kwargs(visit_id="V1", sign_off_id=1, physician_id="DR1", physician_notes=None)
        assert kwargs["original_value_json"] is None
        assert json.loads(kwargs["amended_value_json"]) == {"x": 1}


# ============================================================================
# Capture + analytics integration (in-memory SQLite)
# ============================================================================

@pytest.fixture
def db_session(monkeypatch):
    """In-memory SQLite session with the LearningAmendment table + SignOff stub.

    Module-local fixture: shadows the conftest db_session for this file only.
    """
    from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, ForeignKey, UniqueConstraint
    from sqlalchemy.orm import DeclarativeBase, sessionmaker

    class TestBase(DeclarativeBase):
        pass

    class SignOff(TestBase):
        __tablename__ = "sign_offs"
        id = Column(Integer, primary_key=True, autoincrement=True)
        visit_id = Column(String(64))
        physician_id = Column(String(64))

    class LearningAmendment(TestBase):
        __tablename__ = "learning_amendments"
        id = Column(Integer, primary_key=True, autoincrement=True)
        visit_id = Column(String(64), nullable=False, index=True)
        sign_off_id = Column(Integer, ForeignKey("sign_offs.id"), nullable=False)
        rule_id = Column(String(128), nullable=True, index=True)
        amendment_type = Column(String(32), nullable=False, index=True)
        original_value_json = Column(Text, nullable=True)
        amended_value_json = Column(Text, nullable=True)
        physician_id = Column(String(64), nullable=False)
        physician_notes = Column(Text, nullable=True)
        rule_pack_version = Column(String(16), nullable=True)
        drug_db_version = Column(String(16), nullable=True)
        agent_version = Column(String(16), nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        __table_args__ = (UniqueConstraint("visit_id", "sign_off_id", "rule_id", "amendment_type",
                                           name="uq_learning_amendments_dedupe"),)

    engine = create_engine("sqlite:///:memory:")
    TestBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()

    # Insert a stub sign_off for FK
    sess.add(SignOff(id=1, visit_id="V1", physician_id="DR1"))
    sess.commit()

    # Patch the `database` module so services/learning.py can import LearningAmendment
    import types
    fake_database = types.ModuleType("database")
    fake_database.LearningAmendment = LearningAmendment
    monkeypatch.setitem(sys.modules, "database", fake_database)

    yield sess

    sess.close()
    engine.dispose()


class TestCaptureAndAnalytics:

    def test_capture_persists_amendments(self, db_session, base_assessment):
        from services.learning import capture_amendment
        amended = deepcopy(base_assessment)
        amended["interactions"][0]["severity"] = "moderate"
        amended["interactions"] = [f for f in amended["interactions"] if f["rule_id"] != "EGFR_LOW_DOAC"]

        summary = capture_amendment(
            db_session=db_session,
            visit_id="V1", sign_off_id=1,
            original_assessment=base_assessment, amended_assessment=amended,
            physician_id="DR1", physician_notes="Lower eGFR was a lab error",
        )
        assert summary["amendments_persisted"] == 2  # severity_changed + rule_removed
        assert summary["amendments_skipped_duplicate"] == 0
        assert set(summary["amendment_types"]) == {"severity_changed", "rule_removed"}

    def test_capture_is_idempotent(self, db_session, base_assessment):
        from services.learning import capture_amendment
        amended = deepcopy(base_assessment)
        amended["interactions"][0]["severity"] = "moderate"
        kwargs = dict(visit_id="V1", sign_off_id=1, original_assessment=base_assessment,
                      amended_assessment=amended, physician_id="DR1", physician_notes=None)
        first = capture_amendment(db_session=db_session, **kwargs)
        second = capture_amendment(db_session=db_session, **kwargs)
        assert first["amendments_persisted"] == 1
        assert second["amendments_persisted"] == 0
        assert second["amendments_skipped_duplicate"] == 1

    def test_aggregate_patterns_returns_top_n(self, db_session, base_assessment):
        from services.learning import capture_amendment, aggregate_patterns
        # Create amendments across two sign_offs
        amended1 = deepcopy(base_assessment)
        amended1["interactions"] = [f for f in amended1["interactions"] if f["rule_id"] != "EGFR_LOW_DOAC"]
        capture_amendment(db_session=db_session, visit_id="V1", sign_off_id=1,
                          original_assessment=base_assessment, amended_assessment=amended1,
                          physician_id="DR1", physician_notes=None)

        # Add a second sign-off row
        from sqlalchemy import text
        db_session.execute(text("INSERT INTO sign_offs (id, visit_id, physician_id) VALUES (2, 'V2', 'DR2')"))
        db_session.commit()

        amended2 = deepcopy(base_assessment)
        amended2["interactions"] = [f for f in amended2["interactions"] if f["rule_id"] != "EGFR_LOW_DOAC"]
        capture_amendment(db_session=db_session, visit_id="V2", sign_off_id=2,
                          original_assessment=base_assessment, amended_assessment=amended2,
                          physician_id="DR2", physician_notes=None)

        result = aggregate_patterns(db_session=db_session, amendment_type="rule_removed")
        assert result["total_amendments"] == 2
        assert result["top_by_rule_type"][0]["rule_id"] == "EGFR_LOW_DOAC"
        assert result["top_by_rule_type"][0]["count"] == 2
        assert len(result["top_physicians"]) == 2

    def test_aggregate_patterns_filter_by_rule_id(self, db_session, base_assessment):
        from services.learning import capture_amendment, aggregate_patterns
        amended = deepcopy(base_assessment)
        amended["interactions"][0]["severity"] = "moderate"
        amended["interactions"] = [f for f in amended["interactions"] if f["rule_id"] != "EGFR_LOW_DOAC"]
        capture_amendment(db_session=db_session, visit_id="V1", sign_off_id=1,
                          original_assessment=base_assessment, amended_assessment=amended,
                          physician_id="DR1", physician_notes=None)

        # Filter to only LT4_TABLET_PPI
        result = aggregate_patterns(db_session=db_session, rule_id="LT4_TABLET_PPI")
        assert result["total_amendments"] == 1
        types = {r["amendment_type"] for r in result["top_by_rule_type"]}
        assert types == {"severity_changed"}

    def test_aggregate_patterns_invalid_amendment_type_rejected(self, db_session):
        from services.learning import aggregate_patterns
        with pytest.raises(ValueError):
            aggregate_patterns(db_session=db_session, amendment_type="not_a_real_type")
