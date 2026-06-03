"""
METACOD GLP-1 — FHIR mapper unit tests.

Tests cover:
  - Bundle structure (resourceType, type, language, total, meta tags)
  - Determinism: same input → byte-identical JSON across invocations
  - MedicationStatement: one per unique medication_name across interactions
  - ServiceRequest: lab plan items deduplicated by test_name across rules
  - Observation: triage + one per interaction; interpretation maps from severity
  - ClinicalImpression: forecast + GLP-1 decision + finding[] linking back to obs
  - LOINC mapping where present, METACOD-internal codes as fallback
  - Locale tagging on Meta.tag
  - exclude_none on serialized output (no FHIR null leaks)
"""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from services.fhir_mapper import (
    assessment_to_fhir_bundle,
    _det_uuid,
    _severity_from_triage,
    LOINC_MAP,
    SYS_LOINC,
    SYS_METACOD_RULE,
    SYS_METACOD_TRIAGE,
    SYS_METACOD_LAB,
)

pytestmark = pytest.mark.unit


# ============================================================================
# Test fixtures — a realistic assessment dict
# ============================================================================

@pytest.fixture
def baseline_assessment() -> dict:
    """A locale-resolved PharmacistAssessment dict (i18n_text fields filled)."""
    return {
        "patient_id": "P-DEMO-001",
        "triage_color": "yellow",
        "triage_summary_i18n_key": "triage.yellow.hold_and_reassess",
        "triage_summary_i18n_text": "Yellow — hold GLP-1 escalation and reassess oral therapy",
        "rule_pack_version": "2.0.0",
        "drug_db_version": "2.0.0",
        "agent_version": "3.0.0",
        "sign_off_status": "pending_sign_off",
        "interactions": [
            {
                "rule_id": "LT4_TABLET_PPI",
                "rule_name": "Levothyroxine tablet underexposure with PPI/H2RA",
                "medication_name": "Levothyroxine 100 mcg",
                "severity": "high",
                "evidence_grade": "A",
                "sources": ["Centanni M et al. NEJM 2017"],
                "physician_actions": [
                    {"i18n_key": "action.lt4_check_tsh_4w", "i18n_text": "Check TSH at 4 weeks while on PPI", "evidence_grade": "A", "rule_id": "LT4_TABLET_PPI"},
                ],
                "patient_actions": [
                    {"i18n_key": "patient.lt4_separate_from_ppi", "i18n_text": "Take levothyroxine fasting, 30–60 minutes before any PPI", "evidence_grade": "A", "rule_id": "LT4_TABLET_PPI"},
                ],
                "lab_plan": [
                    {"test": "TSH", "interval_weeks": 4, "i18n_key": "lab.tsh_4w", "i18n_text": "TSH at 4 weeks", "rule_id": "LT4_TABLET_PPI"},
                    {"test": "free_T4", "interval_weeks": 4, "i18n_key": "lab.ft4_4w", "i18n_text": "Free T4 at 4 weeks", "rule_id": "LT4_TABLET_PPI"},
                ],
                "admin_trace": {
                    "rule_id": "LT4_TABLET_PPI",
                    "pattern": "pH_dependent_dissolution_failure",
                    "i18n_key_internal": "admin.lt4_tablet_ph_dissolution_failure",
                    "i18n_text_internal": "[admin] LT4 tablet dissolution failure with elevated gastric pH",
                    "mechanism": "Elevated gastric pH impairs LT4 tablet dissolution",
                },
            },
        ],
        "forecast": {
            "glp1_dosing": {
                "decision": "HOLD",
                "i18n_key": "forecast.glp1.hold_no_escalation",
                "i18n_text": "GLP-1: HOLD escalation until GI symptoms resolve",
                "rationale_i18n_keys": ["forecast.glp1.rationale.gi_intolerance"],
                "rationale_i18n_texts": ["GI intolerance (nausea/vomiting)"],
                "evidence_grade": "A",
            },
            "future_risks": [
                {"i18n_key": "forecast.risk.aki_dehydration", "i18n_text": "Risk of AKI from dehydration", "timeframe_weeks": 2, "evidence_grade": "A"},
            ],
            "chronic_med_adjustments": [],
        },
        "dose_adjustments": [],
        "interaction_matrix": [],
        "projected_labs": [],
    }


# ============================================================================
# Bundle structure
# ============================================================================

class TestBundleStructure:

    def test_resource_type_and_type(self, baseline_assessment):
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001", locale="en")
        d = b.model_dump(exclude_none=True)
        assert d["resourceType"] == "Bundle"
        assert d["type"] == "collection"
        assert d["language"] == "en"
        assert d["id"]  # determined uuid5

    def test_total_matches_entry_count(self, baseline_assessment):
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001")
        d = b.model_dump(exclude_none=True)
        assert d["total"] == len(d["entry"])

    def test_meta_tags_include_versions_and_locale(self, baseline_assessment):
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001", locale="ru")
        d = b.model_dump(exclude_none=True)
        tags = d["meta"]["tag"]
        systems = {t["system"]: t["code"] for t in tags}
        assert systems["urn:ietf:bcp:47"] == "ru"
        assert systems["http://metacod.health/codes/rule-pack"] == "2.0.0"
        assert systems["http://metacod.health/codes/drug-db"] == "2.0.0"
        assert systems["http://metacod.health/codes/agent"] == "3.0.0"

    def test_deterministic_across_invocations(self, baseline_assessment):
        """Same input → byte-identical Bundle JSON. Critical for ETag and EHR-side dedup."""
        b1 = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001", locale="en", authored_on="2026-06-03T12:00:00+00:00")
        b2 = assessment_to_fhir_bundle(deepcopy(baseline_assessment), visit_id="VIS-001", locale="en", authored_on="2026-06-03T12:00:00+00:00")
        j1 = json.dumps(b1.model_dump(exclude_none=True), sort_keys=True)
        j2 = json.dumps(b2.model_dump(exclude_none=True), sort_keys=True)
        assert j1 == j2


# ============================================================================
# MedicationStatement
# ============================================================================

class TestMedicationStatement:

    def test_one_per_unique_medication(self, baseline_assessment):
        # Add a second interaction on the SAME medication — should not duplicate
        baseline_assessment["interactions"].append({
            **baseline_assessment["interactions"][0],
            "rule_id": "LT4_TABLET_CATION",
            "rule_name": "LT4 cation chelation",
        })
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001")
        meds = [e["resource"] for e in b.model_dump(exclude_none=True)["entry"]
                if e["resource"]["resourceType"] == "MedicationStatement"]
        assert len(meds) == 1

    def test_medication_codeable_text(self, baseline_assessment):
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001")
        meds = [e["resource"] for e in b.model_dump(exclude_none=True)["entry"]
                if e["resource"]["resourceType"] == "MedicationStatement"]
        assert meds[0]["medicationCodeableConcept"]["text"] == "Levothyroxine 100 mcg"

    def test_subject_reference(self, baseline_assessment):
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001")
        meds = [e["resource"] for e in b.model_dump(exclude_none=True)["entry"]
                if e["resource"]["resourceType"] == "MedicationStatement"]
        assert meds[0]["subject"]["reference"] == "Patient/P-DEMO-001"


# ============================================================================
# ServiceRequest
# ============================================================================

class TestServiceRequest:

    def test_one_per_unique_lab_test(self, baseline_assessment):
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001")
        srs = [e["resource"] for e in b.model_dump(exclude_none=True)["entry"]
               if e["resource"]["resourceType"] == "ServiceRequest"]
        # baseline has TSH + free_T4 = 2 unique tests
        assert len(srs) == 2
        test_codes = {s["code"]["text"] for s in srs}
        # text comes from i18n_text or i18n_key
        assert any("TSH" in t for t in test_codes)

    def test_loinc_attached_when_known(self, baseline_assessment):
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001")
        srs = [e["resource"] for e in b.model_dump(exclude_none=True)["entry"]
               if e["resource"]["resourceType"] == "ServiceRequest"]
        tsh_sr = next(s for s in srs if any(c.get("system") == SYS_LOINC and c.get("code") == LOINC_MAP["TSH"] for c in s["code"]["coding"]))
        # We expect both LOINC coding and METACOD fallback
        systems = {c["system"] for c in tsh_sr["code"]["coding"]}
        assert SYS_LOINC in systems
        assert SYS_METACOD_LAB in systems

    def test_metacod_fallback_for_unknown_test(self, baseline_assessment):
        """A test_name not in LOINC_MAP still produces a valid ServiceRequest with METACOD coding."""
        baseline_assessment["interactions"][0]["lab_plan"].append({
            "test": "some_obscure_test", "interval_weeks": 4,
            "i18n_key": "lab.obscure", "i18n_text": "Some obscure test",
        })
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001")
        srs = [e["resource"] for e in b.model_dump(exclude_none=True)["entry"]
               if e["resource"]["resourceType"] == "ServiceRequest"]
        obscure = next(s for s in srs if s["code"]["text"] == "Some obscure test")
        systems = {c["system"] for c in obscure["code"]["coding"]}
        assert SYS_LOINC not in systems
        assert SYS_METACOD_LAB in systems

    def test_timing_in_weeks(self, baseline_assessment):
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001")
        srs = [e["resource"] for e in b.model_dump(exclude_none=True)["entry"]
               if e["resource"]["resourceType"] == "ServiceRequest"]
        tsh = next(s for s in srs if "TSH" in s["code"]["text"])
        bd = tsh["occurrenceTiming"]["repeat"]["boundsDuration"]
        assert bd["value"] == 4.0
        assert bd["unit"] == "weeks"
        assert bd["code"] == "wk"


# ============================================================================
# Observation
# ============================================================================

class TestObservation:

    def test_triage_observation_present(self, baseline_assessment):
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001")
        obs = [e["resource"] for e in b.model_dump(exclude_none=True)["entry"]
               if e["resource"]["resourceType"] == "Observation"]
        triage_obs = [o for o in obs if any(c["system"] == SYS_METACOD_TRIAGE for c in o["code"]["coding"])]
        assert len(triage_obs) == 1
        assert triage_obs[0]["valueString"].startswith("Yellow")

    def test_one_observation_per_interaction(self, baseline_assessment):
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001")
        obs = [e["resource"] for e in b.model_dump(exclude_none=True)["entry"]
               if e["resource"]["resourceType"] == "Observation"]
        rule_obs = [o for o in obs if any(c["system"] == SYS_METACOD_RULE for c in o["code"]["coding"])]
        assert len(rule_obs) == 1
        assert rule_obs[0]["code"]["coding"][0]["code"] == "LT4_TABLET_PPI"

    def test_interpretation_maps_from_severity(self, baseline_assessment):
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001")
        obs = [e["resource"] for e in b.model_dump(exclude_none=True)["entry"]
               if e["resource"]["resourceType"] == "Observation"]
        rule_obs = next(o for o in obs if any(c["system"] == SYS_METACOD_RULE for c in o["code"]["coding"]))
        # severity=high → HU code in v3-ObservationInterpretation
        codes = {c["code"] for cc in rule_obs["interpretation"] for c in cc["coding"]}
        assert "HU" in codes

    def test_note_carries_physician_and_patient_actions_and_mechanism(self, baseline_assessment):
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001")
        obs = [e["resource"] for e in b.model_dump(exclude_none=True)["entry"]
               if e["resource"]["resourceType"] == "Observation"]
        rule_obs = next(o for o in obs if any(c["system"] == SYS_METACOD_RULE for c in o["code"]["coding"]))
        note_blob = " ".join(n["text"] for n in rule_obs["note"])
        assert "[physician]" in note_blob
        assert "[patient]" in note_blob
        assert "[mechanism]" in note_blob
        assert "[sources]" in note_blob


# ============================================================================
# ClinicalImpression
# ============================================================================

class TestClinicalImpression:

    def test_present_with_decision_in_summary(self, baseline_assessment):
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001")
        ci = next(e["resource"] for e in b.model_dump(exclude_none=True)["entry"]
                  if e["resource"]["resourceType"] == "ClinicalImpression")
        assert ci["status"] == "completed"
        assert "HOLD" in ci["summary"]

    def test_findings_link_back_to_observations(self, baseline_assessment):
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001")
        ci = next(e["resource"] for e in b.model_dump(exclude_none=True)["entry"]
                  if e["resource"]["resourceType"] == "ClinicalImpression")
        # Should have at least: 1 finding per rule (1) + 1 for triage = 2
        assert len(ci["finding"]) == 2
        triage_finding = [f for f in ci["finding"] if f["basis"] == "triage"]
        assert len(triage_finding) == 1

    def test_future_risks_appear_in_notes(self, baseline_assessment):
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-001")
        ci = next(e["resource"] for e in b.model_dump(exclude_none=True)["entry"]
                  if e["resource"]["resourceType"] == "ClinicalImpression")
        note_blob = " ".join(n["text"] for n in ci["note"])
        assert "AKI" in note_blob or "dehydration" in note_blob


# ============================================================================
# Determinism / helpers
# ============================================================================

class TestHelpers:

    def test_det_uuid_stable(self):
        a = _det_uuid("VIS-001", "Observation", "key1")
        b = _det_uuid("VIS-001", "Observation", "key1")
        assert a == b

    def test_det_uuid_differs_by_inputs(self):
        a = _det_uuid("VIS-001", "Observation", "key1")
        b = _det_uuid("VIS-002", "Observation", "key1")
        c = _det_uuid("VIS-001", "MedicationStatement", "key1")
        d = _det_uuid("VIS-001", "Observation", "key2")
        assert len({a, b, c, d}) == 4

    def test_severity_mapping(self):
        assert _severity_from_triage("red") == "high"
        assert _severity_from_triage("yellow") == "moderate"
        assert _severity_from_triage("green") == "low"
        assert _severity_from_triage("unknown") == "moderate"  # safe fallback

    def test_empty_interactions_still_produces_valid_bundle(self, baseline_assessment):
        """A green-triage patient with no rules should still produce a Bundle with triage + ClinicalImpression."""
        baseline_assessment["interactions"] = []
        baseline_assessment["triage_color"] = "green"
        baseline_assessment["triage_summary_i18n_text"] = "Green — stable"
        b = assessment_to_fhir_bundle(baseline_assessment, visit_id="VIS-NIL")
        d = b.model_dump(exclude_none=True)
        assert d["resourceType"] == "Bundle"
        types = [e["resource"]["resourceType"] for e in d["entry"]]
        assert "Observation" in types  # triage
        assert "ClinicalImpression" in types
        assert "MedicationStatement" not in types  # no interactions → no meds
        assert "ServiceRequest" not in types       # no labs
