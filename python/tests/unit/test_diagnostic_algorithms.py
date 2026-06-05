"""
METACOD-RF Diagnostic Algorithms — structure + governance + safety-flag gates.

Verifies the consolidated decision flows are complete (ALG-0..ALG-10), stay
research-only / not-operationalized, carry the membrane-direction harm warning,
explicitly flag the unresolved urine-pH↔membrane discrepancy, and keep KCTS EBM
(no Hamer/AIRE causality).
"""

from __future__ import annotations

import json
import re

import pytest

from services.diagnostic_algorithms import DiagnosticAlgorithms

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def alg(data_dir):
    return DiagnosticAlgorithms(data_dir / "metacod_rf" / "diagnostic_algorithms_v1_0.json")


def test_loads_v1_0(alg):
    assert alg.version == "1.0"
    assert alg.meta["schema"] == "metacod_rf_diagnostic_algorithms"


def test_research_only_and_not_operationalized(alg):
    assert alg.ready_for_clinical_use is False
    g = alg.governance
    for key in ("not_operationalized", "rf_overlay",
                "membrane_direction_harm_warning", "not_patient_facing",
                "no_hamer_aire_causality"):
        assert g.get(key), f"governance missing {key}"


def test_eleven_algorithms_in_order(alg):
    ids = alg.ids
    assert ids == [f"ALG-{i}" for i in range(11)]
    assert len(alg.pipeline_order) == 11


def test_each_algorithm_complete(alg):
    for a in alg.algorithms:
        for k in ("id", "name", "purpose", "steps", "output", "governance"):
            assert a.get(k), f"{a.get('id')} missing {k}"
        assert isinstance(a["steps"], list) and a["steps"]


def test_membrane_algorithm_flags_ph_discrepancy(alg):
    # The urine-pH membrane-direction contradiction must be recorded and ALG-3
    # must defer to it (not silently pick a direction).
    disc = alg.unresolved_discrepancies.get("urine_pH_membrane_direction", {})
    assert disc, "missing urine_pH discrepancy record"
    blob = json.dumps(disc, ensure_ascii=False).lower()
    assert "three_axis" in blob and "master_integration" in blob
    assert "flag-for-mark" in blob or "flag" in blob
    a3 = alg.algorithm("ALG-3")
    steps_blob = json.dumps(a3["steps"], ensure_ascii=False).lower()
    assert "flag" in steps_blob or "indeterminate" in steps_blob


def test_membrane_directions_opposite_in_synthesis(alg):
    a8 = alg.algorithm("ALG-8")
    blob = json.dumps(a8, ensure_ascii=False).lower()
    assert "catabolic" in blob and "anabolic" in blob and "opposite" in blob.replace("противополож", "opposite")


def test_no_hamer_aire_causality(alg):
    a5 = alg.algorithm("ALG-5")
    blob = json.dumps(a5, ensure_ascii=False).lower()
    # KCTS algorithm must use EBM operative model and disavow Hamer/AIRE causality.
    assert "ebm" in blob
    assert "disavow" in blob or "не используется" in blob
    # No causal AIRE invocation in the algorithm bodies.
    body = json.dumps(alg.algorithms, ensure_ascii=False).lower()
    assert not re.search(r"\baire\b", body) or "disavow" in body or "не используется" in body
