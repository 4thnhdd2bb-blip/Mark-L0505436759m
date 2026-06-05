"""
METACOD-RF Constitutional Model — structure + governance tests.

Validates the SHAPE and HONEST FLAGGING of the biomarker quality-panel model,
never the clinical correctness of the (hypothesis-level) biomarker selections.
"""

from __future__ import annotations

import pytest

from services.constitutional_model import (
    ENERGY_KEYS,
    MARKER_ZONE_KEYS,
    ConstitutionalModel,
)
from services.metacod_bridge import ENERGY_AXES

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def model(data_dir):
    return ConstitutionalModel(data_dir / "metacod_rf" / "constitutional_model_v0_2.json")


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_model_loads_v0_2(model):
    assert model.version == "0.2"
    assert model.meta["schema"] == "metacod_rf_constitutional_model"


def test_covers_all_five_energies(model):
    assert model.energies() == set(ENERGY_KEYS)


def test_energy_keys_match_tcm_bridge_axes(model):
    # The constitutional model and the TCM bridge must agree on the 5 axes,
    # so synthesis and quality assessment speak the same energy vocabulary.
    assert model.energies() == set(ENERGY_AXES)


def test_every_panel_has_markers_with_three_zone_structure(model):
    for energy in ENERGY_KEYS:
        panel = model.panel(energy)
        assert panel is not None, f"missing panel for {energy}"
        assert panel.get("wu_xing_associations"), f"{energy}: no wu_xing_associations"
        markers = model.markers(energy)
        assert markers, f"{energy}: no markers"
        for m in markers:
            missing = set(MARKER_ZONE_KEYS) - set(m.keys())
            assert not missing, f"{energy} marker {m.get('marker')!r} missing {sorted(missing)}"
        assert panel.get("clinical_interpretation_patterns"), f"{energy}: no interpretation patterns"


def test_multi_energy_and_cross_reference_present(model):
    assert len(model.multi_energy_markers) >= 5
    assert all({"marker", "interpretation"} <= set(m.keys()) for m in model.multi_energy_markers)
    assert model.cross_reference.get("limitations")
    assert model.cross_reference.get("open_questions")
    assert model.cross_reference.get("clinical_navigation")


def test_all_markers_have_a_label(model):
    for m in model.all_markers():
        assert m.get("marker"), f"marker row without a name: {m}"


# ---------------------------------------------------------------------------
# Honest research-only flagging (governance)
# ---------------------------------------------------------------------------

def test_flagged_research_only(model):
    assert model.ready_for_clinical_use is False
    assert "not clinical guidance" in model.meta["status"].lower()


def test_biomarker_selections_flagged_as_hypotheses(model):
    vs = model.validation_status
    assert "HYPOTHES" in vs.get("biomarker_selections", "").upper(), (
        "biomarker_selections must stay flagged as hypotheses, not validated"
    )


def test_unprovided_parts_not_fabricated(model):
    # Parts A-E live in v0.1 and were not supplied; the doc must say so rather
    # than the repo inventing them.
    note = model.meta.get("parts_not_included", "")
    assert "A-E" in note and "v0.1" in note
