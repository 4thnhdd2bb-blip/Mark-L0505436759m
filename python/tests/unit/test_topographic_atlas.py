"""
METACOD-RF Topographic Atlas v6.0 — structure + canon-consistency tests.

Validates SHAPE, membrane-code canon alignment, the documented 6-Ki-vs-5-canon
discrepancy, and honest research-only flagging. Never validates the clinical
correctness of the (research-level) tissue-reactivity mappings.
"""

from __future__ import annotations

import pytest

from services.metacod_bridge import ENERGY_AXES
from services.topographic_atlas import (
    CANONICAL_MEMBRANE_CODES,
    PATTERN_KEYS,
    TopographicAtlas,
)

pytestmark = pytest.mark.unit

EXPECTED_SYSTEMS = {"endocrine", "nervous", "reproductive", "kinetic", "immune", "sensory"}


@pytest.fixture(scope="module")
def atlas(data_dir):
    return TopographicAtlas(data_dir / "metacod_rf" / "topographic_atlas_v6_0.json")


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_loads_v6_0(atlas):
    assert atlas.version == "6.0"
    assert atlas.meta["schema"] == "metacod_rf_topographic_atlas"


def test_six_systems_complete(atlas):
    assert set(atlas.systems()) == EXPECTED_SYSTEMS
    assert atlas.meta.get("systems_pending") == []


def test_ten_organs_present(atlas):
    # endocrine(2) + nervous(1) + reproductive(1) + kinetic(1) + immune(3) + sensory(2)
    organs = atlas.organs()
    assert len(organs) == 10
    for o in organs:
        assert o.get("label") and o.get("patterns")


def test_every_pattern_has_full_structure(atlas):
    patterns = list(atlas.patterns())
    assert len(patterns) == 100  # 10 organs × 10 energy/redox rows
    for p in patterns:
        missing = set(PATTERN_KEYS) - set(p.keys())
        assert not missing, f"pattern missing {sorted(missing)}: {p.get('energy_redox')}"
        assert p["pole"] in {"Ян (А)", "Инь (УМ)"}


# ---------------------------------------------------------------------------
# Canon consistency
# ---------------------------------------------------------------------------

def test_membrane_codes_are_canonical(atlas):
    # Cross-guard: every membrane code must be one of the canonical 8 levels.
    extra = atlas.membrane_codes() - CANONICAL_MEMBRANE_CODES
    assert not extra, f"non-canonical membrane codes in atlas: {sorted(extra)}"


def test_six_ki_vs_five_canon_discrepancy_is_flagged(atlas):
    # The atlas uses 6 Ki (Тепло AND Жар separate) — NOT the 5-energy canon.
    # This must be explicitly documented, and the atlas energies must NOT be
    # silently equated with the bridge's 5 ENERGY_AXES.
    assert len(atlas.atlas_energies) == 6
    assert "Тепло" in atlas.atlas_energies and "Жар" in atlas.atlas_energies
    note = atlas.meta.get("canon_discrepancy_note", "")
    assert "6 Ki" in note and "5" in note
    # 6 != 5: the energy models are deliberately different sizes.
    assert len(atlas.atlas_energies) != len(ENERGY_AXES)


# ---------------------------------------------------------------------------
# Governance / honesty
# ---------------------------------------------------------------------------

def test_flagged_research_only(atlas):
    assert atlas.ready_for_clinical_use is False
    assert "not clinical guidance" in atlas.meta["status"].lower()
    assert atlas.meta.get("mark_validated") == "pending review"


def test_embedded_code_snippet_is_non_runnable_documentation(atlas):
    snip = atlas.meta.get("safety_monitoring_snippet", {})
    assert snip.get("runnable") is False
    # Stored verbatim as a string, never materialized as an importable module.
    assert "6ki_profile" in snip.get("code_verbatim", "")
    assert "physician-owned" in snip.get("note", "").lower()
