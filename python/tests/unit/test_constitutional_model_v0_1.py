"""
METACOD-RF Constitutional Model v0.1 — structure + governance + cross-guards.

v0.1 is the conceptual two-axis framework (Parts A-E). This validates that the
prose sections are present, that it is honestly flagged research-only, and that
its declared critical_constants (5 energies, 5 phases) match the rest of the
canon — so the conceptual layer can't silently drift from the engine vocabulary.
"""

from __future__ import annotations

import pytest

from services.constitutional_model import (
    PHASE_KEYS,
    ConstitutionalModelV01,
)
from services.metacod_bridge import ENERGY_AXES

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def model(data_dir):
    return ConstitutionalModelV01(
        data_dir / "metacod_rf" / "constitutional_model_v0_1.json"
    )


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_model_loads_v0_1(model):
    assert model.version == "0.1"
    assert model.meta["schema"] == "metacod_rf_constitutional_model_v0_1"


def test_all_five_parts_present(model):
    for key in (
        "part_A_constitutional_axis",
        "part_B_process_phase_axis",
        "part_C_clinical_scenarios",
        "part_D_acknowledged_limitations",
        "part_E_open_research_questions",
    ):
        assert model.section(key), f"missing {key}"


def test_part_A_core_subsections(model):
    a = model.section("part_A_constitutional_axis")
    for key in ("triad_principle", "yin_yang_dominance", "quantity", "quality",
                "temporal_dimensions", "open_problem_constitution_algorithm"):
        assert key in a, f"Part A missing {key}"
    # The central open problem must be flagged unsolved, not glossed over.
    op = a["open_problem_constitution_algorithm"]
    assert "не решённое" in op["status"].lower() or "open" in op["status"].lower()


def test_part_B_five_phases_in_order(model):
    seq = model.section("part_B_process_phase_axis")["five_phases"]["sequence"]
    names = [p["phase"].split(" ")[0] for p in seq]
    assert names == list(PHASE_KEYS)


def test_phase_not_constitution_separation_recorded(model):
    b = model.section("part_B_process_phase_axis")
    assert "proxy" in b["phase_not_constitution"]["rule"].lower()


# ---------------------------------------------------------------------------
# Cross-guards against the canon (no silent drift)
# ---------------------------------------------------------------------------

def test_energies_match_tcm_bridge_axes(model):
    assert set(model.energies) == set(ENERGY_AXES)


def test_phases_match_canonical_phase_keys(model):
    assert model.phases == PHASE_KEYS


# ---------------------------------------------------------------------------
# Honest research-only flagging (governance)
# ---------------------------------------------------------------------------

def test_flagged_research_only(model):
    assert model.ready_for_clinical_use is False
    assert "not clinical guidance" in model.meta["status"].lower()


def test_not_based_on_pseudoscientific_claims(model):
    nb = model.meta.get("not_based_on", [])
    joined = " ".join(nb).lower()
    assert "hamer" in joined and "revici" in joined, (
        "v0.1 must keep explicit that it is NOT based on Hamer psychogenic / "
        "Revici universal-mechanism claims."
    )
