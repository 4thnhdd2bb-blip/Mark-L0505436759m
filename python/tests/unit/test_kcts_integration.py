"""
METACOD-RF KCTS Integration — structure + governance + cross-guards.

KCTS is a Hamer-derived research hypothesis. These tests do NOT judge its
clinical validity; they ENFORCE that the artifact stays inside the governance
wall: research-only, not operationalized, not patient-facing, never reordering
evidence-based care, and never silently equating its vocabulary with the canon.
"""

from __future__ import annotations

import pytest

from services.kcts_integration import KCTSIntegration
from services.symptom_registry import CANONICAL_MEMBRANE_CODES
from services.constitutional_model import PHASE_KEYS

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def doc(data_dir):
    return KCTSIntegration(data_dir / "metacod_rf" / "kcts_integration_v1_0.json")


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_loads_v1_1(doc):
    # v1.1 = EBM-reformulated (Mark decision 2026-06): Hamer/AIRE causality
    # disavowed as mechanism, retained only as disclosed origin.
    assert doc.version == "1.1"
    assert doc.meta["schema"] == "metacod_rf_kcts_integration"
    assert doc.meta.get("reformulation_note_v1_1"), "v1.1 must record the EBM reformulation"


def test_kcts_is_modifier_not_fourth_axis(doc):
    assert doc.is_modifier_not_axis is True


def test_all_eight_parts_present(doc):
    for key in (
        "part_1_concept",
        "part_1_3_dual_language",
        "part_2_detection",
        "part_3_kcts_x_phase",
        "part_4_kcts_x_membrane",
        "part_5_drug_implications",
        "part_6_mariana_case",
        "part_7_integration",
        "part_8_open_questions_validation",
    ):
        assert doc.section(key), f"missing {key}"


# ---------------------------------------------------------------------------
# Governance gates (safety)
# ---------------------------------------------------------------------------

def test_flagged_research_only(doc):
    assert doc.ready_for_clinical_use is False
    assert "not clinical guidance" in doc.meta["status"].lower()


def test_governance_safety_annotation_present(doc):
    g = doc.governance_annotation
    # The four load-bearing safety promises must be present and non-empty.
    for key in ("standard_care_primacy", "not_operationalized",
                "not_patient_facing", "causal_claim_status"):
        assert g.get(key), f"governance annotation missing {key}"
    # Standard-care primacy must explicitly refuse to delay evidence-based care.
    primacy = g["standard_care_primacy"].lower()
    assert "не может её откладыва" in primacy or "не должно использоваться" in primacy


def test_hamer_provenance_disclosed(doc):
    pr = doc.provenance_risk
    blob = " ".join(str(v) for v in pr.values()).lower()
    assert "hamer" in blob, "KCTS must disclose its Hamer / GNM derivation"
    assert "pseudoscience" in blob, "external pseudoscience status must be disclosed"


def test_not_a_replacement_for_standard_infectious_oncology_care(doc):
    nr = doc.section("part_8_open_questions_validation")["not_a_replacement_for"]
    joined = " ".join(nr).lower()
    assert "infectious" in joined and ("oncology" in joined or "cancer" in joined)


# ---------------------------------------------------------------------------
# Cross-guards against the canon (no silent drift / equation)
# ---------------------------------------------------------------------------

def test_referenced_membrane_codes_subset_of_canon(doc):
    refs = set(doc.referenced_membrane_codes)
    assert refs, "expected at least one referenced membrane code"
    assert refs <= CANONICAL_MEMBRANE_CODES, (
        f"KCTS references non-canonical membrane codes: {refs - CANONICAL_MEMBRANE_CODES}"
    )


def test_phase_crosswalk_maps_to_canonical_phases(doc):
    cw = doc.phase_crosswalk
    assert len(cw) == len(PHASE_KEYS)
    mapped = [row["canonical_phase"] for row in cw]
    # The crosswalk RECORDS a correspondence (not an identity) and must cover
    # exactly the 5 canonical phases.
    assert mapped == list(PHASE_KEYS), (
        f"phase crosswalk {mapped} must map onto canonical {list(PHASE_KEYS)}"
    )
