"""
METACOD-RF Nosology Registries — structure + canon/governance tests.

Auto-discovers every metacod_rf/nosology_registry_*.json so new blocks are
covered without editing this file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.metacod_bridge import ENERGY_AXES
from services.nosology_registry import (
    CANONICAL_MEMBRANE_CODES,
    PATTERN_REQUIRED_KEYS,
    NosologyRegistry,
)

pytestmark = pytest.mark.unit


def _registry_files() -> list[Path]:
    src = Path(__file__).resolve().parents[2]
    return sorted((src / "metacod_rf").glob("nosology_registry_*.json"))


REGISTRY_FILES = _registry_files()


@pytest.fixture(params=REGISTRY_FILES, ids=lambda p: p.stem)
def registry(request):
    return NosologyRegistry(request.param)


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_at_least_three_registries_present():
    assert len(REGISTRY_FILES) >= 3


def test_schema_and_contours(registry):
    assert registry.meta["schema"] == "metacod_rf_nosology_registry"
    assert registry.contour_names()
    assert len(registry) >= 6


def test_every_pattern_has_required_keys(registry):
    for p in registry.patterns():
        missing = set(PATTERN_REQUIRED_KEYS) - set(p.keys())
        assert not missing, f"{p.get('nosology')!r} missing {sorted(missing)}"
        assert p["icd10"]
        assert isinstance(p["sym_readout"], list) and p["sym_readout"]


# ---------------------------------------------------------------------------
# Canon consistency
# ---------------------------------------------------------------------------

def test_membrane_base_codes_are_canonical(registry):
    extra = registry.all_base_membrane_codes() - CANONICAL_MEMBRANE_CODES
    assert not extra, f"non-canonical membrane codes: {sorted(extra)}"


def test_six_ki_not_equated_with_five_canon(registry):
    note = registry.meta.get("canon_discrepancy_note", "")
    assert "6 Ki" in note and "ENERGY_AXES" in note
    assert len(ENERGY_AXES) == 5


# ---------------------------------------------------------------------------
# Governance / honesty
# ---------------------------------------------------------------------------

def test_flagged_research_only(registry):
    assert registry.ready_for_clinical_use is False
    assert registry.meta.get("mark_validated") == "pending review"
    assert "not clinical guidance" in registry.meta["status"].lower()


def test_hard_stops_are_physician_owned_data(registry):
    # Every registry that carries hard-stops must flag them physician-owned and
    # not-operationalized (they reference therapy/balneo/compounding protocols).
    if "hard_stops_physician_owned" in registry.meta:
        note = registry.meta.get("hard_stops_note", "").lower()
        assert "physician-owned" in note
        assert "not operationaliz" in note or "не операционализ" in note


def test_source_readiness_claim_does_not_change_governance(registry):
    claim = registry.meta.get("source_readiness_claim", "")
    if claim:
        assert "research-only" in claim.lower() or "research" in claim.lower()
    assert registry.ready_for_clinical_use is False
