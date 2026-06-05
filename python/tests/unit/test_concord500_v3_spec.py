"""
METACOD-RF CONCORD-500 v3.0 spec — governance + Hamer/KCTS-v1.1 conflict flag.

The spec must stay research-only, record that the data files are NOT in the repo,
and — critically — flag the v3.0 'conflict theme' Hamer layer as in tension with
the KCTS v1.1 disavowal, blocking materialization until Mark reconciles it.
"""

from __future__ import annotations

import json

import pytest

from services.concord500_v3_spec import Concord500V3Spec

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def spec(data_dir):
    return Concord500V3Spec(data_dir / "metacod_rf" / "concord500_v3_enrichment_spec.json")


def test_loads_v3(spec):
    assert spec.version == "3.0_enriched"
    assert spec.meta["schema"] == "metacod_rf_concord500_v3_spec"


def test_research_only(spec):
    assert spec.ready_for_clinical_use is False
    g = spec.governance
    for key in ("research_only", "rule_derived_not_curated",
                "graph_statistical_not_causal", "not_operationalized",
                "not_patient_facing"):
        assert g.get(key), f"governance missing {key}"


def test_data_files_recorded_as_absent(spec):
    nf = spec.meta.get("data_files_not_in_repo", {})
    assert "master_bundle_v3.0_enriched.json" in nf
    assert "concord500_v3_enrichment.sql" in nf


def test_hamer_conflict_theme_resolved_phase_taxonomy_only(spec):
    flag = spec.critical_flag
    blob = json.dumps(flag, ensure_ascii=False).lower()
    assert "hamer" in blob and "conflict" in blob
    assert "kcts v1.1" in blob or "kcts_v1_1" in blob or "kcts v1_1" in blob
    assert "disavow" in blob
    # Mark resolved → option A: phase-taxonomy only, conflict-theme dropped.
    res = flag.get("resolution", {})
    assert res.get("chosen") == "A_phase_taxonomy_only"
    assert "drop" in json.dumps(res, ensure_ascii=False).lower()


def test_materialization_plan_split_into_batches(spec):
    plan = spec.meta.get("materialization_plan", {})
    assert plan
    assert "split" in json.dumps(plan, ensure_ascii=False).lower()


def test_three_enrichment_layers(spec):
    layers = spec.enrichment_layers
    assert set(layers.keys()) == {"layer_1_clinical", "layer_2_metacod", "layer_3_graph"}
