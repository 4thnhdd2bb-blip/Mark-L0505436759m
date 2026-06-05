"""
METACOD-RF Predictive Matrix #1 (semaglutide × triads) — structure + governance.

Validates SHAPE and HONEST FLAGGING, never the clinical correctness of the
(hypothesis-level) predictions.
"""

from __future__ import annotations

import pytest

from services.metacod_rf import RFDrugCatalog
from services.predictive_matrix import PREDICTED_PARAM_KEYS, PredictiveMatrix

pytestmark = pytest.mark.unit

EXPECTED_TRIADS = {"T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"}


@pytest.fixture(scope="module")
def matrix(data_dir):
    return PredictiveMatrix(data_dir / "metacod_rf" / "predictive_matrix_01_semaglutide.json")


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_matrix_loads(matrix):
    assert matrix.matrix_id == "PM-01"
    assert matrix.meta["schema"] == "metacod_rf_predictive_matrix"
    assert len(matrix) == 8


def test_eight_triads_present(matrix):
    assert set(matrix.triad_ids()) == EXPECTED_TRIADS
    for tid in EXPECTED_TRIADS:
        t = matrix.triad(tid)
        assert t and t.get("name") and t.get("clinical_phenotype")
        assert t.get("yin_yang_dominance")


def test_every_triad_has_a_prediction_over_all_five_parameters(matrix):
    pred_triads = {p["triad_id"] for p in matrix.predictions()}
    assert pred_triads == EXPECTED_TRIADS
    for tid in EXPECTED_TRIADS:
        pred = matrix.prediction(tid)
        for param in PREDICTED_PARAM_KEYS:
            assert param in pred, f"{tid} prediction missing {param}"
            assert pred[param].get("rating"), f"{tid}.{param} has no rating"
        assert pred.get("confidence")
        assert pred.get("recommend")


def test_predictions_reference_existing_triads(matrix):
    for p in matrix.predictions():
        assert matrix.triad(p["triad_id"]) is not None, f"prediction for unknown {p['triad_id']}"


def test_clinical_navigation_buckets(matrix):
    nav = matrix.clinical_navigation
    assert nav.get("best_candidates")
    assert nav.get("avoid")
    assert nav.get("individual_assessment_required")
    # Anna (T4) and frail-elderly (T5) must be in the avoid bucket (Mark canonical).
    avoid_text = " ".join(nav["avoid"])
    assert "T4" in avoid_text and "T5" in avoid_text


# ---------------------------------------------------------------------------
# Governance / honesty
# ---------------------------------------------------------------------------

def test_flagged_research_and_hypotheses(matrix):
    assert matrix.ready_for_clinical_use is False
    assert matrix.all_predictions_are_hypotheses is True
    assert "not clinical guidance" in matrix.meta["status"].lower()


def test_drug_resolves_to_real_rf_batch_entry(matrix, data_dir):
    # Cross-link guard: the matrix's drug must exist in the RF drug DB (batch 01).
    assert matrix.drug_id == "DRG-001"
    cat = RFDrugCatalog(data_dir / "metacod_rf" / "drugs_batch01_glp1.json")
    drug = cat.get(matrix.drug_id)
    assert drug is not None and drug.name_inn == "Semaglutide"
