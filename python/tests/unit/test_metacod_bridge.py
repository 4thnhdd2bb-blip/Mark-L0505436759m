"""
METACOD GLP-1 module — unit tests for the METACOD TCM bridge.

Covers:
  - RuleEnergyMappingCatalog load + indexing
  - Coverage meta-test: every rule_pack_v2 rule_id has a mapping entry, and
    every mapping references an existing rule (no drift either way)
  - Schema validity of the baseline mappings (axes + magnitude bounds)
  - METACODBridge.synthesize  : aggregation, dedup, dominant + phase route,
    treatment order, rules_without_mapping, tie-break, magnitude clamping
  - build_three_layer_output  : LAYER LEAKAGE GUARDS — proprietary TCM synthesis
    and admin_trace must never appear in patient_view / physician_view; patient
    view must not carry physician_actions
  - treatment_sequence ordering: priority order, unmapped-to-bottom, stability,
    no-mutation, Collecting-Tubules-first (via a synthetic catalog), explain_ordering
  - End-to-end against the real PharmacistAgent output

The bridge is a Python-track-only subsystem (METACOD core synthesis adapter).
The energy/quantity mappings in rule_energy_mapping.json are BASELINE content
authored for Mark's clinical review (review_status in _meta), not final.
"""

from __future__ import annotations

import json

import pytest

from services.metacod_bridge import (
    ENERGY_AXES,
    ENERGY_TO_PHASE,
    QUANTITY_AXES,
    TREATMENT_PRIORITY,
    TREATMENT_SEQUENCE,
    METACODBridge,
    METACODSynthesis,
    RuleEnergyMappingCatalog,
)
from services.treatment_sequence import (
    explain_ordering,
    reorder_by_treatment_sequence,
)

pytestmark = pytest.mark.unit


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def catalog(data_dir):
    """The real baseline catalog loaded from python/rule_energy_mapping.json."""
    return RuleEnergyMappingCatalog(data_dir / "rule_energy_mapping.json")


@pytest.fixture(scope="module")
def bridge(catalog):
    return METACODBridge(catalog)


def _finding(rule_id, **over):
    """Minimal interaction/finding dict shaped like a PharmacistAgent finding."""
    f = {
        "rule_id": rule_id,
        "rule_name": rule_id,
        "medication_name": "Test med",
        "severity": "moderate",
        "evidence_grade": "B",
        "physician_actions": [{"i18n_key": f"action.{rule_id}_phys"}],
        "patient_actions": [{"i18n_key": f"patient.{rule_id}_pt"}],
        "lab_plan": [],
        "sources": [],
        "admin_trace": {"rule_id": rule_id, "mechanism": "SECRET internal mechanism note"},
    }
    f.update(over)
    return f


def _assessment(interactions, **over):
    a = {
        "triage_color": "amber",
        "triage_summary_i18n_key": "triage.amber",
        "interactions": interactions,
        "forecast": {"glp1_dosing": {"decision": "continue", "i18n_key": "glp1.continue"}},
        "dose_adjustments": [],
        "rule_pack_version": "2.0.0",
        "drug_db_version": "2.0.0",
        "agent_version": "3.0.0",
        "projected_labs": [{"lab": "tsh", "value": 9.9}],
        "interaction_matrix": [{"pair": "x-y"}],
    }
    a.update(over)
    return a


# ============================================================================
# Catalog load + coverage
# ============================================================================

def test_catalog_loads_all_31(catalog):
    assert len(catalog) == 31
    # Heat→Normotonia confirmed by Mark; treatment_sequence ordering still pending review.
    review = catalog.meta.get("review_status", "")
    assert "heat_phase_confirmed" in review
    assert "pending" in review


def test_every_rule_pack_rule_has_a_mapping(catalog, resources):
    """Hard coverage gate: every rule in rule_pack_v2 must have an energy mapping,
    so synthesize() never silently drops a fired rule into rules_without_mapping."""
    rule_ids = {r["rule_id"] for r in resources.rule_pack.get("rules", [])}
    missing = rule_ids - catalog.all_rule_ids()
    assert not missing, f"rule_pack rules without an energy mapping: {sorted(missing)}"


def test_no_phantom_mappings(catalog, resources):
    """Every mapping must reference a rule that actually exists in the rule_pack."""
    rule_ids = {r["rule_id"] for r in resources.rule_pack.get("rules", [])}
    phantom = catalog.all_rule_ids() - rule_ids
    assert not phantom, f"mappings referencing non-existent rules: {sorted(phantom)}"


def test_all_mappings_have_valid_axes_and_magnitudes(catalog):
    for rule_id in catalog.all_rule_ids():
        m = catalog.get(rule_id)
        for c in m.energy_contributions:
            assert c["axis"] in ENERGY_AXES, f"{rule_id}: bad energy axis {c['axis']}"
            assert 1 <= c["magnitude"] <= 3, f"{rule_id}: energy magnitude out of range"
        for c in m.quantity_contributions:
            assert c["axis"] in QUANTITY_AXES, f"{rule_id}: bad quantity axis {c['axis']}"
            assert 1 <= c["magnitude"] <= 3, f"{rule_id}: quantity magnitude out of range"
        assert 1 <= m.treatment_priority_order <= 5


def test_catalog_get_and_contains(catalog):
    assert "LT4_TABLET_PPI" in catalog
    assert catalog.get("LT4_TABLET_PPI") is not None
    assert catalog.get("___does_not_exist___") is None
    assert "___does_not_exist___" not in catalog


# ============================================================================
# synthesize
# ============================================================================

def test_synthesize_aggregates_two_cold_rules(bridge):
    # LT4_TABLET_PPI: cold/3 + deficiency/3 ; ORAL_IRON_PPI: cold/2 + deficiency/3
    assessment = _assessment([_finding("LT4_TABLET_PPI"), _finding("ORAL_IRON_PPI")])
    s = bridge.synthesize(assessment)

    assert s.energy_scores["cold"] == 5
    assert s.quantity_scores["deficiency"] == 6
    assert s.dominant_energy == "cold"
    assert s.dominant_quantity == "deficiency"
    assert s.phase_route == ENERGY_TO_PHASE["cold"] == "CA"
    assert s.treatment_order == ["cold"]
    assert s.rules_with_mapping == 2
    assert s.rules_without_mapping == []
    assert len(s.contributions_trace) == 2


def test_synthesize_dedups_same_rule_id(bridge):
    # Same rule firing twice (e.g. two meds) counts once.
    assessment = _assessment([_finding("LT4_TABLET_PPI"), _finding("LT4_TABLET_PPI")])
    s = bridge.synthesize(assessment)
    assert s.rules_with_mapping == 1
    assert s.energy_scores["cold"] == 3  # not 6


def test_synthesize_records_rules_without_mapping(bridge):
    assessment = _assessment([_finding("NOT_A_REAL_RULE")])
    s = bridge.synthesize(assessment)
    assert s.rules_with_mapping == 0
    assert s.rules_without_mapping == ["NOT_A_REAL_RULE"]
    assert s.dominant_energy is None
    assert s.phase_route is None
    assert s.treatment_order == []


def test_synthesize_empty_assessment(bridge):
    s = bridge.synthesize(_assessment([]))
    assert all(v == 0 for v in s.energy_scores.values())
    assert s.dominant_energy is None
    assert s.dominant_quantity is None
    assert s.phase_route is None
    assert s.treatment_order == []


def test_treatment_order_follows_global_sequence(bridge):
    # A wind rule (BARIATRIC_EARLY_DOAC) + a cold rule (LT4_TABLET_PPI):
    # treatment_order must be in global sequence order (wind before cold).
    assessment = _assessment([_finding("LT4_TABLET_PPI"), _finding("BARIATRIC_EARLY_DOAC")])
    s = bridge.synthesize(assessment)
    assert s.treatment_order == ["wind", "cold"]


def test_argmax_tiebreak_prefers_wind(bridge):
    # Equal scores → earlier-in-sequence axis wins (wind first).
    assert METACODBridge._argmax_or_none({"heat": 2, "wind": 2}) == "wind"
    assert METACODBridge._argmax_or_none({"dry": 3, "damp": 3}) == "damp"
    assert METACODBridge._argmax_or_none({"cold": 0, "heat": 0}) is None


def test_clamp_magnitude_bounds(bridge):
    assert METACODBridge._clamp_magnitude(0) == 1
    assert METACODBridge._clamp_magnitude(99) == 3
    assert METACODBridge._clamp_magnitude(2) == 2
    assert METACODBridge._clamp_magnitude("nonsense") == 1


# ============================================================================
# Three-layer output — LEAKAGE GUARDS
# ============================================================================

# Proprietary tokens that must never appear in patient or physician serialized views.
_PROPRIETARY_TOKENS = (
    "tcm_synthesis", "energy_scores", "quantity_scores", "phase_route",
    "rationale_ru", "collecting_tubules", "treatment_priority",
    "treatment_order", "dominant_energy", "interaction_matrix", "projected_labs",
)


def test_hidden_admin_carries_full_synthesis(bridge):
    assessment = _assessment([_finding("LT4_TABLET_PPI")])
    s = bridge.synthesize(assessment)
    out = bridge.build_three_layer_output(assessment, s, locale="ru")

    admin = out["hidden_admin"]
    assert admin["tcm_synthesis"]["energy_scores"]["cold"] == 3
    assert admin["tcm_synthesis"]["phase_route"] == "CA"
    # admin_trace from the finding is surfaced ONLY here
    assert any("SECRET internal mechanism" in json.dumps(t) for t in admin["per_rule_admin_traces"])
    assert admin["projected_labs"]
    assert admin["interaction_matrix"]


def test_patient_view_excludes_proprietary_and_physician_actions(bridge):
    assessment = _assessment([_finding("LT4_TABLET_PPI")])
    s = bridge.synthesize(assessment)
    out = bridge.build_three_layer_output(assessment, s, locale="ru")

    blob = json.dumps(out["patient_view"], ensure_ascii=False)
    for tok in _PROPRIETARY_TOKENS:
        assert tok not in blob, f"patient_view leaked proprietary token: {tok}"
    # No physician-facing action keys, no admin mechanism note
    assert "physician_actions" not in out["patient_view"]
    assert "SECRET internal mechanism" not in blob
    assert "_phys" not in blob, "patient_view leaked a physician action key"
    # But it DOES carry the safe patient action key
    assert "patient.LT4_TABLET_PPI_pt" in out["patient_view"]["patient_actions_i18n_keys"]


def test_physician_view_excludes_admin_trace_and_tcm(bridge):
    assessment = _assessment([_finding("LT4_TABLET_PPI")])
    s = bridge.synthesize(assessment)
    out = bridge.build_three_layer_output(assessment, s, locale="ru")

    blob = json.dumps(out["physician_view"], ensure_ascii=False)
    assert "tcm_synthesis" not in blob
    assert "energy_scores" not in blob
    assert "rationale_ru" not in blob
    assert "SECRET internal mechanism" not in blob, "physician_view leaked admin_trace"
    assert "admin_trace" not in blob
    # Physician view keeps the EBM clinical content
    phys_interaction = out["physician_view"]["interactions"][0]
    assert phys_interaction["rule_id"] == "LT4_TABLET_PPI"
    assert phys_interaction["physician_actions"]


def test_layer_guarantees_block_present(bridge):
    out = bridge.build_three_layer_output(_assessment([]), bridge.synthesize(_assessment([])))
    g = out["_layer_guarantees"]
    assert "physician_actions" in g["patient_view_excludes"]
    assert "tcm_synthesis" in g["physician_view_excludes"]
    assert "tcm_synthesis" in g["hidden_admin_only"]


# ============================================================================
# treatment_sequence ordering
# ============================================================================

def test_reorder_by_treatment_priority(catalog):
    # Original: cold (tpo3) then wind (tpo1) → reordered wind first.
    assessment = _assessment([_finding("LT4_TABLET_PPI"), _finding("BARIATRIC_EARLY_DOAC")])
    out = reorder_by_treatment_sequence(assessment, catalog)

    order = [f["rule_id"] for f in out["interactions"]]
    assert order == ["BARIATRIC_EARLY_DOAC", "LT4_TABLET_PPI"]
    meta = out["treatment_sequence_metadata"]
    assert meta["ordering_applied"] is True
    assert meta["trace"][0]["rule_id"] == "BARIATRIC_EARLY_DOAC"
    assert meta["trace"][0]["final_index"] == 0


def test_reorder_unmapped_rule_falls_to_bottom(catalog):
    assessment = _assessment([_finding("NOT_A_REAL_RULE"), _finding("LT4_TABLET_PPI")])
    out = reorder_by_treatment_sequence(assessment, catalog)
    order = [f["rule_id"] for f in out["interactions"]]
    assert order == ["LT4_TABLET_PPI", "NOT_A_REAL_RULE"]


def test_reorder_is_stable_within_bucket(catalog):
    # Two cold (tpo3) rules keep original relative order.
    assessment = _assessment([_finding("LT4_TABLET_PPI"), _finding("ORAL_IRON_PPI")])
    out = reorder_by_treatment_sequence(assessment, catalog)
    order = [f["rule_id"] for f in out["interactions"]]
    assert order == ["LT4_TABLET_PPI", "ORAL_IRON_PPI"]


def test_reorder_does_not_mutate_original(catalog):
    interactions = [_finding("LT4_TABLET_PPI"), _finding("BARIATRIC_EARLY_DOAC")]
    assessment = _assessment(interactions)
    original_order = [f["rule_id"] for f in assessment["interactions"]]
    _ = reorder_by_treatment_sequence(assessment, catalog)
    assert [f["rule_id"] for f in assessment["interactions"]] == original_order
    assert "treatment_sequence_metadata" not in assessment


def test_reorder_empty_interactions(catalog):
    out = reorder_by_treatment_sequence(_assessment([]), catalog)
    assert out["treatment_sequence_metadata"]["ordering_applied"] is False
    assert out["treatment_sequence_metadata"]["reason"] == "no_interactions"


def test_collecting_tubules_findings_go_first(tmp_path):
    """Synthetic catalog with a Collecting-Tubules-priority rule: it must jump to
    position 0 regardless of its treatment_priority_order."""
    synthetic = {
        "_meta": {"version": "test"},
        "mappings": [
            {
                "rule_id": "CT_RULE",
                "energy_contributions": [{"axis": "heat", "magnitude": 1}],
                "quantity_contributions": [],
                "phase_route_hint": "Normotonia",
                "collecting_tubules_priority": True,
                "treatment_priority_order": 5,  # last by energy, but CT overrides
                "rationale_ru": "тест",
            },
            {
                "rule_id": "WIND_RULE",
                "energy_contributions": [{"axis": "wind", "magnitude": 2}],
                "quantity_contributions": [],
                "phase_route_hint": "epicrisis",
                "collecting_tubules_priority": False,
                "treatment_priority_order": 1,
                "rationale_ru": "тест",
            },
        ],
    }
    p = tmp_path / "synthetic_mapping.json"
    p.write_text(json.dumps(synthetic), encoding="utf-8")
    cat = RuleEnergyMappingCatalog(p)

    assessment = _assessment([_finding("WIND_RULE"), _finding("CT_RULE")])
    out = reorder_by_treatment_sequence(assessment, cat)
    order = [f["rule_id"] for f in out["interactions"]]
    assert order == ["CT_RULE", "WIND_RULE"]
    assert out["treatment_sequence_metadata"]["collecting_tubules_active"] is True


def test_explain_ordering_returns_lines(catalog):
    assessment = _assessment([_finding("LT4_TABLET_PPI"), _finding("BARIATRIC_EARLY_DOAC")])
    out = reorder_by_treatment_sequence(assessment, catalog)
    lines_ru = explain_ordering(out["treatment_sequence_metadata"], locale="ru")
    lines_en = explain_ordering(out["treatment_sequence_metadata"], locale="en")
    assert len(lines_ru) == 2
    assert len(lines_en) == 2
    assert "BARIATRIC_EARLY_DOAC" in lines_ru[0]
    assert explain_ordering({}, locale="ru") == []


# ============================================================================
# End-to-end against the real PharmacistAgent
# ============================================================================

def test_end_to_end_real_agent(catalog, bridge, resources):
    """Run the real agent on an LT4 + PPI patient, then synthesize + reorder +
    three-layer over its actual model_dump output. Proves the bridge consumes
    the live assessment shape, not just hand-crafted dicts."""
    from pharmacist_agent import PatientContext, PharmacistAgent

    patient = PatientContext(
        patient_id="P-METACOD",
        age_years=60,
        sex="female",
        weight_kg=70.0,
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=10,
        glp1_weeks_since_last_dose_increase=6,
        ppi_or_h2_blocker=True,
        symptoms={"nausea_score": 2},
        labs={"egfr_ml_min": 80, "tsh_miu_l": 6.5},
        medications=[
            {"name": "Levothyroxine 75 mcg", "profile_id": "levothyroxine_tablet", "route": "oral"},
        ],
    )
    agent = PharmacistAgent(patient=patient, rule_pack=resources.rule_pack, drug_db=resources.drug_db)
    assessment = agent.assess().model_dump()

    fired = {f["rule_id"] for f in assessment["interactions"]}
    assert "LT4_TABLET_PPI" in fired

    s = bridge.synthesize(assessment)
    # LT4_TABLET_PPI contributes cold; so cold must be represented and have a phase route.
    assert s.energy_scores["cold"] >= 3
    assert s.phase_route is not None
    assert isinstance(s.to_dict(), dict)

    reordered = reorder_by_treatment_sequence(assessment, catalog)
    assert reordered["treatment_sequence_metadata"]["ordering_applied"] is True

    out = bridge.build_three_layer_output(assessment, s, locale="ru")
    # Cross-check leakage on REAL data, not just synthetic.
    patient_blob = json.dumps(out["patient_view"], ensure_ascii=False)
    for tok in _PROPRIETARY_TOKENS:
        assert tok not in patient_blob
