"""
METACOD-RF Diagnostic Foundation — structure + governance.

The diagnostics DB is an ARCHITECTURE PROPOSAL awaiting Mark validation. These
tests ENFORCE that it stays inside the governance wall (research-only, content
not yet filled, KCTS detection EBM-reframed per v1.1, Revici/energy overlays
flagged as RF hypotheses — not validated diagnostic rules).
"""

from __future__ import annotations

import pytest

from services.diagnostic_foundation import DiagnosticFoundation

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def doc(data_dir):
    return DiagnosticFoundation(data_dir / "metacod_rf" / "diagnostic_foundation_v1_0.json")


# --- structure ---

def test_loads_v1_0(doc):
    assert doc.version == "1.0"
    assert doc.meta["schema"] == "metacod_rf_diagnostic_foundation"


def test_four_categories_with_distinct_prefixes(doc):
    cats = doc.categories
    assert len(cats) == 4
    prefixes = {c["id_prefix"] for c in cats}
    assert prefixes == {"TST", "IMG", "FUN", "PRO"}
    assert set(doc.id_prefixes) == {"TST", "IMG", "FUN", "PRO"}


def test_twenty_batch_plan(doc):
    assert len(doc.batch_plan) == 20
    assert doc.batch_plan[0]["batch"] == "DX-01"
    assert doc.batch_plan[-1]["batch"] == "DX-20"


def test_six_open_questions(doc):
    assert len(doc.open_questions) == 6


def test_entry_template_present(doc):
    keys = doc.entry_template_keys
    assert any("test_id" in k for k in keys)
    assert any("mark_validated" in k for k in keys)


# --- governance (safety) ---

def test_research_only_and_content_not_filled(doc):
    assert doc.ready_for_clinical_use is False
    assert doc.content_filling_started is False
    assert "not clinical guidance" in doc.meta["status"].lower()


def test_governance_annotation_present(doc):
    g = doc.governance
    for key in ("tests_are_inputs_not_interventions", "reference_ranges_vs_interpretation",
                "revici_hypotheses_flagged", "not_operationalized", "standard_care_primacy"):
        assert g.get(key), f"governance missing {key}"


def test_kcts_detection_is_ebm_reframed(doc):
    # The new artifact must use the v1.1 EBM model (psychosocial / chronic-stress /
    # fluid-retention), with Hamer/AIRE causality disavowed — not re-introduced.
    assert doc.meta.get("kcts_v1_1_alignment"), "must carry KCTS v1.1 alignment note"
    align = doc.meta["kcts_v1_1_alignment"].lower()
    assert "hamer" in align and ("отвергнут" in align or "disavow" in align.lower())
    kd = doc.kcts_detection_ebm
    assert kd.get("psychosocial_clinical_markers"), "EBM psychosocial markers expected"


def test_revici_overlays_flagged_rf(doc):
    # urinary-pH / Bristol / membrane-panel must be flagged as RF hypotheses,
    # not presented as validated diagnostic rules.
    tiers = doc.mark_canonical_tiers
    revici = tiers["tier_2_urinary_ph_revici"]["evidence"].upper()
    assert "RF" in revici or "REVICI" in revici
    bristol = tiers["tier_6_bristol_stool"]["evidence"].upper()
    assert "RF" in bristol
