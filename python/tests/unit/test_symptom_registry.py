"""
METACOD-RF Symptom Registry v3.0 — structure + canon-consistency tests.
"""

from __future__ import annotations

import pytest

from services.metacod_bridge import ENERGY_AXES
from services.symptom_registry import (
    CANONICAL_MEMBRANE_CODES,
    SYMPTOM_KEYS,
    SymptomRegistry,
    base_membrane_codes,
)

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def registry(data_dir):
    return SymptomRegistry(data_dir / "metacod_rf" / "symptom_registry_v3_0.json")


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_loads_v3_0(registry):
    assert registry.version == "3.0"
    assert registry.meta["schema"] == "metacod_rf_symptom_registry"
    assert registry.meta["registry_total_symptoms"] == 172


def test_thirty_five_detailed_symptoms(registry):
    assert len(registry) == 35
    assert registry.meta["detailed_symptoms_count"] == 35


def test_every_symptom_has_full_structure(registry):
    for s in registry.symptoms():
        missing = set(SYMPTOM_KEYS) - set(s.keys())
        assert not missing, f"{s.get('sym_id')} missing {sorted(missing)}"
        assert s["sym_id"].startswith("SYM-")


def test_symptom_ids_unique(registry):
    ids = [s["sym_id"] for s in registry.symptoms()]
    assert len(ids) == len(set(ids))


def test_backend_preset_is_subset_of_registry(registry):
    preset_ids = set(registry.preset.keys())
    assert preset_ids, "preset empty"
    assert preset_ids <= registry.ids(), (
        f"preset references symptoms absent from detailed registry: "
        f"{sorted(preset_ids - registry.ids())}"
    )


# ---------------------------------------------------------------------------
# Canon consistency
# ---------------------------------------------------------------------------

def test_base_membrane_codes_helper():
    assert base_membrane_codes("M-D1") == ["M-D1"]
    assert base_membrane_codes("M-D2 → M-S") == ["M-D2", "M-S"]
    assert base_membrane_codes("M-D2_to_M-S") == ["M-D2", "M-S"]
    assert base_membrane_codes("M-A3 ложный") == ["M-A3"]
    assert base_membrane_codes("M-A3_false") == ["M-A3"]


def test_all_base_membrane_codes_are_canonical(registry):
    # Cross-guard across both the detailed drift strings and the backend preset:
    # after stripping qualifiers («ложный»/transitions), every base code is one
    # of the canonical 8.
    extra = registry.all_base_membrane_codes() - CANONICAL_MEMBRANE_CODES
    assert not extra, f"non-canonical membrane codes: {sorted(extra)}"


def test_six_ki_energy_model_not_equated_with_five_canon(registry):
    note = registry.meta.get("canon_discrepancy_note", "")
    assert "6 Ki" in note
    assert "5" in note  # explicitly states it is NOT the 5-energy canon
    # The registry must not declare its energy model equal to the bridge axes.
    assert "ENERGY_AXES" in note
    assert len(ENERGY_AXES) == 5


# ---------------------------------------------------------------------------
# Governance / honesty
# ---------------------------------------------------------------------------

def test_flagged_research_only(registry):
    assert registry.ready_for_clinical_use is False
    assert registry.meta.get("mark_validated") == "pending review"
    assert "not clinical guidance" in registry.meta["status"].lower()


def test_source_readiness_claim_does_not_change_governance(registry):
    # The source claims "absolute readiness for clinical use"; the repo must
    # record that this does NOT change governance (stays research-only).
    claim = registry.meta.get("source_readiness_claim", "")
    assert "research-only" in claim.lower() or "research" in claim.lower()
    assert registry.ready_for_clinical_use is False
