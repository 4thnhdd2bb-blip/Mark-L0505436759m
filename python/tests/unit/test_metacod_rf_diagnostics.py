"""
METACOD-RF Diagnostics DB — structure + governance + provenance.

Parallel to test_metacod_rf_drugs. Enforces the same governance wall on the
diagnostics database (lab/imaging/functional/procedures): research-only, never
auto-validated, provenance-tagged, EBM-anchored majority, KCTS interpretation
EBM-reframed (no Hamer/AIRE causality in entries).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.diagnostic_db import DxCatalog
from services.metacod_rf import KNOWN_SOURCE_TAGS, PLACEHOLDER_TAGS, first_tag

pytestmark = pytest.mark.unit

# python/tests/unit/ -> python/
DX_DIR = Path(__file__).resolve().parents[2] / "metacod_rf"
DX_FILES = sorted(DX_DIR.glob("dx_batch*.json"))

# test_id -> name_full (exact round-trip guard)
EXPECTED: dict[str, dict[str, str]] = {
    "DX-01-FoundationLabs": {
        "TST-001": "Complete blood count (CBC) with differential",
        "TST-002": "Reticulocyte count",
        "TST-003": "Basic metabolic panel (BMP)",
        "TST-004": "Comprehensive metabolic panel (CMP)",
        "TST-005": "Sodium (Na⁺)",
        "TST-006": "Potassium (K⁺)",
        "TST-007": "Serum creatinine + eGFR",
        "TST-008": "Blood urea nitrogen (BUN)",
        "TST-009": "Fasting plasma glucose",
        "TST-010": "Calcium (total + ionized)",
        "TST-011": "Magnesium",
        "TST-012": "Phosphate (inorganic phosphorus)",
        "TST-013": "Serum albumin",
        "TST-014": "Total protein",
    },
    "DX-18-BodyComposition": {
        "FUN-001": "Bioelectrical impedance analysis (BIA)",
        "FUN-002": "Dual-energy X-ray absorptiometry (DEXA)",
        "FUN-003": "Heart rate variability (HRV)",
        "FUN-004": "Urinary pH (4-point: morning + post-meal)",
        "FUN-005": "Urine specific gravity",
        "FUN-006": "Bristol Stool Scale (+ METACOD energy mapping)",
        "FUN-007": "Bioimpedance spectroscopy / Cole-Cole α",
        "FUN-008": "Handgrip strength (dynamometry)",
        "FUN-009": "Indirect calorimetry (resting metabolic rate)",
    },
}


def _catalogs():
    return [DxCatalog(p) for p in DX_FILES]


@pytest.fixture(params=DX_FILES, ids=lambda p: p.stem)
def catalog(request):
    return DxCatalog(request.param)


def test_dx_files_present():
    assert DX_FILES, "expected dx_batch*.json diagnostics files"


def test_count_matches_meta(catalog):
    assert len(catalog) == catalog.meta["preparations_count"]


def test_required_keys(catalog):
    for t in catalog:
        for k in ("test_id", "name_full", "name_ru", "status", "batch", "test_type", "status_flags"):
            assert t.get(k) is not None, f"{t.test_id} missing {k}"
        assert t.get("status") == "METACOD-RF"
        assert t.test_id.split("-")[0] in {"TST", "IMG", "FUN", "PRO"}


def test_flagged_research_only(catalog):
    assert catalog.ready_for_clinical_use is False
    assert "not clinical guidance" in catalog.meta["status"].lower()


def test_no_test_fully_validated(catalog):
    for t in catalog:
        assert not t.is_fully_validated, f"{t.test_id} must not be auto-promoted to full validation"
        assert t.validation_state in {"none", "partial"}


def test_known_provenance_tags(catalog):
    bad = []
    for t in catalog:
        for stmt in t.tagged_statements():
            tag = first_tag(stmt)
            if tag not in KNOWN_SOURCE_TAGS and tag not in PLACEHOLDER_TAGS:
                bad.append((t.test_id, stmt))
    assert not bad, f"unknown provenance tags: {bad[:5]}"


def test_majority_external_anchor(catalog):
    # Tests must mostly carry an [LBL]/[GL]/[RCT] external-evidence anchor
    # (standard ranges/indications), with METACOD [RF] overlay separable.
    drugs = list(catalog)
    anchor = {"LBL", "GL", "RCT"}
    with_anchor = [t for t in drugs if anchor & {first_tag(s) for s in t.tagged_statements()}]
    assert len(with_anchor) >= (len(drugs) + 1) // 2


def test_three_axis_present(catalog):
    for t in catalog:
        tap = t.get("three_axis_profile") or {}
        assert {"constitutional", "membrane", "phase"} <= set(tap), f"{t.test_id} three-axis incomplete"


def test_no_hamer_aire_causality_in_entries(catalog):
    # KCTS interpretation in diagnostics must be EBM-reframed (v1.1): no entry
    # may assert Hamer/AIRE psychic-conflict causality.
    import json as _json
    import re as _re
    blob = _json.dumps([t.get(k) for t in catalog for k in ("mark_canonical", "three_axis_profile")],
                       ensure_ascii=False).lower()
    assert not _re.search(r"\baire\b", blob), "AIRE causal terminology must not appear in diagnostic entries (v1.1 EBM)"
    assert not _re.search(r"\bhamer\b", blob), "Hamer causality must not appear in diagnostic entries (v1.1 EBM)"


def test_expected_ids_and_names():
    for batch_id, expected in EXPECTED.items():
        cat = next((c for c in _catalogs() if c.meta["batch_id"] == batch_id), None)
        assert cat is not None, f"missing batch {batch_id}"
        assert cat.all_ids() == set(expected), f"{batch_id} id set mismatch"
        for tid, name in expected.items():
            assert cat.get(tid).name_full == name
            assert cat.by_name(name).test_id == tid
