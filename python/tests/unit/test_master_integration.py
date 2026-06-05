"""
METACOD-RF Master Integration (v1.1) — structure + governance + canon correction.

Enforces the governance wall on the symptoms→diagnostics→drugs architecture:
research-only, not operationalized, membrane axis (and its OPPOSITE treatment
directions) flagged as RF construct that must not auto-drive prescribing, the
v1.0→v1.1 M-A/inflammation correction recorded, KCTS EBM (no Hamer/AIRE causality).
"""

from __future__ import annotations

import json
import re

import pytest

from services.master_integration import MasterIntegration

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def doc(data_dir):
    return MasterIntegration(data_dir / "metacod_rf" / "master_integration_v1_1.json")


def test_loads_v1_1(doc):
    assert doc.version == "1.1-CORRECTED"
    assert doc.meta["schema"] == "metacod_rf_master_integration"


def test_research_only_and_not_operationalized(doc):
    assert doc.ready_for_clinical_use is False
    assert "not clinical guidance" in doc.meta["status"].lower()
    g = doc.governance
    for key in ("membrane_is_RF_construct", "not_operationalized",
                "standard_care_primacy", "not_patient_facing"):
        assert g.get(key), f"governance missing {key}"


def test_errata_records_M_A_correction(doc):
    e = doc.errata
    blob = (e.get("error", "") + e.get("correction", "")).lower()
    assert "m-a" in blob and "inflammation" in blob
    assert "anabolic" in e.get("correction", "").lower()


def test_membrane_canon_inflammation_not_in_M_A(doc):
    canon = doc.membrane_canon
    # Inflammation must be located in Phase-2 / M-D / M-S — explicitly NOT M-A.
    loc = canon["inflammation_location"]
    assert "M-A" in loc.get("NOT", "")
    assert "Phase 2" in loc.get("acute", "")
    # M-A definition must read anabolic / sterol — not inflammatory.
    assert "anabolic" in canon["M-A_anabolic"]["definition"].lower()


def test_treatment_directions_are_opposite(doc):
    td = doc.treatment_direction
    assert "catabolic" in td["M-A"].lower()
    assert "anabolic" in td["M-D"].lower()
    assert "_critical" in td and "opposite" in td["_critical"].lower()


def test_six_layers(doc):
    assert len(doc.layers) == 6


def test_no_hamer_aire_causality(doc):
    # The clinical membrane canon must not invoke AIRE/Hamer causality...
    canon_blob = json.dumps(doc.section("membrane_canon_v1_1"), ensure_ascii=False).lower()
    assert not re.search(r"\baire\b", canon_blob)
    assert "hamer" not in canon_blob
    # ...and the KCTS alignment note must explicitly mark Hamer/AIRE as NOT used.
    assert "not used" in doc.meta.get("kcts_v1_1_alignment", "").lower()
