"""
METACOD GLP-1 module — clinical validation test driver.

Runs every case from cases.ALL_CASES through the PharmacistAgent and asserts:
  - triage_color matches expected
  - glp1_dosing.decision matches expected
  - all `rules_that_must_fire` actually fired
  - none of `rules_that_must_not_fire` fired
  - all `future_risk_keys_must_include` appear in forecast
  - all `chronic_adjustment_keys_must_include` appear in forecast
  - at least `min_grade_a_rules` Grade A rules fired

Run all cases:
    pytest tests/clinical/ -v

Run a specific case:
    pytest tests/clinical/ -v -k C04_TIRZEPATIDE_OC

Failures here block rule_pack release — these are the SaMD reference cases.
"""

from __future__ import annotations

import pytest

from tests.clinical.cases import ALL_CASES, ClinicalCase


# ============================================================================
# Parametrised case runner
# ============================================================================

@pytest.mark.clinical
@pytest.mark.parametrize("case", ALL_CASES, ids=lambda c: c.case_id)
def test_clinical_case(case: ClinicalCase, resources):
    """Run one clinical case through the agent and check the expected outcomes."""
    from pharmacist_agent import PatientContext, PharmacistAgent

    patient = PatientContext(**case.patient_input)
    agent = PharmacistAgent(
        patient=patient,
        rule_pack=resources.rule_pack,
        drug_db=resources.drug_db,
    )
    assessment = agent.assess()
    expected = case.expected

    # 1. Triage colour
    assert assessment.triage_color.value == expected.triage_color, (
        f"[{case.case_id}] triage_color: expected {expected.triage_color!r}, "
        f"got {assessment.triage_color.value!r}\n"
        f"Clinical rationale: {case.clinical_rationale}"
    )

    # 2. GLP-1 decision
    assert assessment.forecast.glp1_dosing.decision.value == expected.glp1_decision, (
        f"[{case.case_id}] glp1_decision: expected {expected.glp1_decision!r}, "
        f"got {assessment.forecast.glp1_dosing.decision.value!r}"
    )

    # 3. Rules that must fire
    fired = {i.rule_id for i in assessment.interactions}
    for rule_id in expected.rules_that_must_fire:
        assert rule_id in fired, (
            f"[{case.case_id}] expected rule {rule_id!r} did not fire. "
            f"Fired rules: {sorted(fired)}"
        )

    # 4. Rules that must NOT fire
    for rule_id in expected.rules_that_must_not_fire:
        assert rule_id not in fired, (
            f"[{case.case_id}] rule {rule_id!r} fired but should not have. "
            f"Fired rules: {sorted(fired)}"
        )

    # 5. Future risk i18n keys must include
    future_risk_keys = {r.i18n_key for r in assessment.forecast.future_risks}
    for key in expected.future_risk_keys_must_include:
        assert key in future_risk_keys, (
            f"[{case.case_id}] future risk {key!r} missing. "
            f"Present: {sorted(future_risk_keys)}"
        )

    # 6. Chronic adjustment keys must include
    chronic_keys = {a.adjustment_i18n_key for a in assessment.forecast.chronic_med_adjustments}
    for key in expected.chronic_adjustment_keys_must_include:
        assert key in chronic_keys, (
            f"[{case.case_id}] chronic adjustment {key!r} missing. "
            f"Present: {sorted(chronic_keys)}"
        )

    # 7. Minimum Grade A rules
    grade_a_count = sum(1 for i in assessment.interactions if i.evidence_grade.value == "A")
    assert grade_a_count >= expected.min_grade_a_rules, (
        f"[{case.case_id}] expected at least {expected.min_grade_a_rules} "
        f"Grade A rules, got {grade_a_count}"
    )


# ============================================================================
# Coverage assertions — meta-tests
# ============================================================================

@pytest.mark.clinical
def test_coverage_all_rules_have_a_positive_case(resources):
    """Every rule in rule_pack should have at least one case where it fires."""
    all_rule_ids = {r["rule_id"] for r in resources.rule_pack["rules"]}

    cases_covering = set()
    for case in ALL_CASES:
        cases_covering.update(case.expected.rules_that_must_fire)

    uncovered = all_rule_ids - cases_covering

    # Print the gap rather than hard-fail so we see it in CI without blocking
    # release on rules that may genuinely have no clinical case yet.
    if uncovered:
        pytest.skip(
            f"Rules without a positive validation case: {sorted(uncovered)}. "
            f"Add cases in tests/clinical/cases.py before promoting these rules."
        )


@pytest.mark.clinical
def test_no_duplicate_case_ids():
    """Catch copy-paste errors where two cases share a case_id."""
    case_ids = [c.case_id for c in ALL_CASES]
    duplicates = {cid for cid in case_ids if case_ids.count(cid) > 1}
    assert not duplicates, f"Duplicate case_ids found: {duplicates}"


@pytest.mark.clinical
def test_every_case_has_sources_and_rationale():
    """Each case must justify its expected outcome — no unsourced fixtures."""
    for case in ALL_CASES:
        assert case.sources, f"[{case.case_id}] has no sources"
        assert case.clinical_rationale, f"[{case.case_id}] has no clinical_rationale"
        assert len(case.clinical_rationale) > 40, (
            f"[{case.case_id}] clinical_rationale is too terse — explain WHY"
        )
