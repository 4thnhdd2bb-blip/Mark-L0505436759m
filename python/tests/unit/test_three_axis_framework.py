"""
METACOD-RF Three-Axis Framework v1.0 — structure + canon-consistency tests.

Validates the SHAPE, canon constants and honest flagging of the integrating
framework, never the clinical correctness of its (research-level) content.
"""

from __future__ import annotations

import pytest

from services.metacod_bridge import ENERGY_AXES, ENERGY_TO_PHASE
from services.three_axis_framework import ThreeAxisFramework

pytestmark = pytest.mark.unit

MEMBRANE_LEVELS = {"M-0", "M-A1", "M-A2", "M-A3", "M-S", "M-D1", "M-D2", "M-D3"}
PHASES = {"CA", "PCL-A", "Epicrisis", "PCL-B", "Normotonia"}
TRIAD_IDS = {"T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"}
SCENARIO_KEYS = {
    "A_t2dm_new", "B_heart_failure", "C_active_oncology", "D_pregnancy",
    "E_frail_elderly_poly", "F_pre_oncology_screening", "G_adt_initiation",
    "H_major_surgery_recovery",
}


@pytest.fixture(scope="module")
def fw(data_dir):
    return ThreeAxisFramework(data_dir / "metacod_rf" / "three_axis_framework_v1_0.json")


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_loads_v1_0(fw):
    assert fw.version == "1.0"
    assert fw.meta["schema"] == "metacod_rf_three_axis_framework"


def test_three_axes_present(fw):
    assert set(fw.axes.keys()) == {"constitutional", "membrane", "phase"}


def test_eight_membrane_levels(fw):
    assert set(fw.membrane_levels().keys()) == MEMBRANE_LEVELS
    for lvl, body in fw.membrane_levels().items():
        assert body.get("name") and body.get("biomarkers"), f"{lvl} incomplete"
    # M-S must keep its «not balanced» canonical semantic.
    assert "balanced" in fw.axis("membrane")["semantic_M_S"].lower()


def test_five_phases_with_polarity(fw):
    phases = fw.phases()
    assert set(phases.keys()) == PHASES
    for p, body in phases.items():
        assert body.get("polarity") and body.get("signature")


def test_eight_triads(fw):
    assert {t["id"] for t in fw.triads()} == TRIAD_IDS


def test_eight_integration_scenarios(fw):
    assert set(fw.scenarios().keys()) == SCENARIO_KEYS


def test_special_patterns_present(fw):
    for key in ("lesion_systemic_paradox", "adt_catastrophe", "pregnancy_m_a_shift"):
        assert key in fw.special_patterns


# ---------------------------------------------------------------------------
# Canon consistency (cross-guards with the TCM bridge)
# ---------------------------------------------------------------------------

def test_energy_constants_match_bridge_axes(fw):
    assert set(fw.constants["energies"]) == set(ENERGY_AXES)


def test_membrane_constant_matches_levels(fw):
    assert set(fw.constants["membranes"]) == MEMBRANE_LEVELS


def test_phase_constants_match_bridge_phase_routes(fw):
    # The framework's 5 phases must match the phase-route vocabulary the TCM
    # bridge maps energies to (case-insensitive: bridge uses "epicrisis").
    fw_phases = {p.lower() for p in fw.constants["phases"]}
    bridge_phases = {v.lower() for v in ENERGY_TO_PHASE.values()}
    assert fw_phases == bridge_phases


# ---------------------------------------------------------------------------
# Honest research-only flagging (governance)
# ---------------------------------------------------------------------------

def test_flagged_research_only(fw):
    assert fw.ready_for_clinical_use is False
    assert fw.ready_for_research_use is True
    assert fw.mark_validated == "pending review"
    assert "not clinical guidance" in fw.meta["status"].lower()


def test_open_problems_and_validation_path_present(fw):
    op = fw.open_problems_validation
    assert op.get("core_open_problems")
    assert op.get("validation_path")
    assert op.get("known_limitations")
    assert "Clinical judgment" in op.get("not_a_replacement_for", [])
