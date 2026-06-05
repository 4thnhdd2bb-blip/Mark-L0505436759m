"""METACOD GLP-1 module — v2 clinical validation driver.

Companion to test_clinical_validation.py. Adds:
  - Parametrized runner over ALL_CASES_V2 (25 cases)
  - Coverage matrix meta-test: every rule in rule_pack_v2 has at least one positive case
    across the union of v1 + v2 case packs

Run together:
    pytest tests/clinical/ -v

Run only v2:
    pytest tests/clinical/test_clinical_validation_v2.py -v
"""

from __future__ import annotations

import pytest

from tests.clinical.cases import ALL_CASES as ALL_CASES_V1
from tests.clinical.cases_v2 import ALL_CASES_V2, ClinicalCase


# ============================================================================
# Parametrized v2 runner — same shape as v1 driver
# ============================================================================

@pytest.mark.clinical
@pytest.mark.parametrize("case", ALL_CASES_V2, ids=lambda c: c.case_id)
def test_clinical_case_v2(case: ClinicalCase, resources):
    from pharmacist_agent import PatientContext, PharmacistAgent

    patient = PatientContext(**case.patient_input)
    agent = PharmacistAgent(
        patient=patient,
        rule_pack=resources.rule_pack,
        drug_db=resources.drug_db,
    )
    assessment = agent.assess()
    expected = case.expected
    fired_rule_ids = {f.rule_id for f in assessment.interactions}

    # 1. Triage colour
    assert assessment.triage_color.value == expected.triage_color, (
        f"[{case.case_id}] triage: expected {expected.triage_color!r}, "
        f"got {assessment.triage_color.value!r}. Rationale: {case.clinical_rationale}"
    )

    # 2. GLP-1 decision
    assert assessment.forecast.glp1_dosing.decision.value == expected.glp1_decision, (
        f"[{case.case_id}] glp1_decision: expected {expected.glp1_decision!r}, "
        f"got {assessment.forecast.glp1_dosing.decision.value!r}"
    )

    # 3. Rules that must fire
    missing = set(expected.rules_that_must_fire) - fired_rule_ids
    assert not missing, (
        f"[{case.case_id}] expected to fire but didn't: {sorted(missing)}. "
        f"Actually fired: {sorted(fired_rule_ids)}"
    )

    # 4. Rules that must NOT fire
    unexpected = set(expected.rules_that_must_not_fire) & fired_rule_ids
    assert not unexpected, (
        f"[{case.case_id}] fired unexpectedly: {sorted(unexpected)}. "
        f"All fired: {sorted(fired_rule_ids)}"
    )

    # 5. Future risk keys
    risk_keys = {r.i18n_key for r in assessment.forecast.future_risks}
    missing_risks = set(expected.future_risk_keys_must_include) - risk_keys
    assert not missing_risks, (
        f"[{case.case_id}] missing future risk keys: {sorted(missing_risks)}"
    )

    # 6. Chronic adjustment keys
    adj_keys = {c.adjustment_i18n_key for c in assessment.forecast.chronic_med_adjustments}
    missing_adj = set(expected.chronic_adjustment_keys_must_include) - adj_keys
    assert not missing_adj, (
        f"[{case.case_id}] missing chronic adjustment keys: {sorted(missing_adj)}"
    )

    # 7. Grade-A rule minimum
    grade_a_count = sum(1 for f in assessment.interactions if f.evidence_grade.value == "A")
    assert grade_a_count >= expected.min_grade_a_rules, (
        f"[{case.case_id}] expected at least {expected.min_grade_a_rules} Grade A rule(s), "
        f"saw {grade_a_count}"
    )


# ============================================================================
# Coverage matrix meta-test
# ============================================================================

@pytest.mark.clinical
def test_every_rule_has_a_positive_case(resources):
    """Every rule_id in the loaded rule_pack must appear in `rules_that_must_fire`
    of at least one v1 or v2 case. This blocks silent introductions of new rules
    without accompanying validation coverage.
    """
    all_rules = {r["rule_id"] for r in resources.rule_pack.get("rules", [])}

    covered: set[str] = set()
    for case in ALL_CASES_V1 + ALL_CASES_V2:
        covered.update(case.expected.rules_that_must_fire)

    uncovered = all_rules - covered
    assert not uncovered, (
        f"The following rules have NO positive clinical case "
        f"(neither in v1 nor v2 case pack): {sorted(uncovered)}. "
        f"Each rule must have at least one ClinicalCase whose "
        f"rules_that_must_fire includes it."
    )


@pytest.mark.clinical
def test_every_case_references_existing_rules(resources):
    """Every rule_id referenced by a case (in must_fire or must_not_fire) must
    exist in the loaded rule_pack. Catches typos in case definitions before they
    drift unnoticed.
    """
    all_rules = {r["rule_id"] for r in resources.rule_pack.get("rules", [])}

    referenced: set[str] = set()
    for case in ALL_CASES_V1 + ALL_CASES_V2:
        referenced.update(case.expected.rules_that_must_fire)
        referenced.update(case.expected.rules_that_must_not_fire)

    phantom = referenced - all_rules
    assert not phantom, (
        f"The following rule_ids are referenced by cases but absent from "
        f"the rule_pack: {sorted(phantom)}. Fix the case definitions or "
        f"add the rules to the rule_pack."
    )
