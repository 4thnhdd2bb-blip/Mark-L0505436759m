"""
METACOD GLP-1 module — v3 subsystem unit tests.

Tests for the three v3 additions:
  - DoseIndividualization: BMI / weight-loss trajectory + pharmacogenomics
  - InteractionMatrixEngine: static perpetrator → victim DDI matrix
  - BayesianLabProjector: OLS linear regression on lab history

These import the agent directly (conftest puts python/ on sys.path); they don't
require rule_pack or drug_db. They run alongside the existing v2 test suite.
"""

from __future__ import annotations

import pytest

from pharmacist_agent import (
    BayesianLabProjector,
    DoseIndividualization,
    InteractionMatrixEngine,
    LabHistoryPoint,
    MedicationInput,
    PatientContext,
    Pharmacogenomics,
    WeightTrajectoryPoint,
    EvidenceGrade,
)

pytestmark = pytest.mark.unit


def _patient(meds, **kw):
    """Helper: build a PatientContext with a list of (name, profile_id) tuples."""
    return PatientContext(
        patient_id=kw.pop("patient_id", "P-TEST"),
        age_years=kw.pop("age_years", 50),
        sex=kw.pop("sex", "female"),
        weight_kg=kw.pop("weight_kg", 70.0),
        medications=[MedicationInput(name=n, profile_id=p, route="oral") for n, p in meds],
        **kw,
    )


def _drug_db():
    """Minimal drug_db_index for the tests — only the profile_ids we reference."""
    return {
        "amiodarone": {"display_name": {"en": "Amiodarone"}},
        "lithium_carbonate": {"display_name": {"en": "Lithium"}},
        "digoxin": {"display_name": {"en": "Digoxin"}},
        "metoprolol_succinate": {"display_name": {"en": "Metoprolol succinate"}},
        "voriconazole": {"display_name": {"en": "Voriconazole"}},
        "escitalopram": {"display_name": {"en": "Escitalopram"}},
        "fluoxetine": {"display_name": {"en": "Fluoxetine"}},
        "tacrolimus": {"display_name": {"en": "Tacrolimus"}},
        "carbamazepine": {"display_name": {"en": "Carbamazepine"}},
        "apixaban": {"display_name": {"en": "Apixaban"}},
        "omeprazole": {"display_name": {"en": "Omeprazole"}},
        "levothyroxine_tablet": {"display_name": {"en": "Levothyroxine"}},
        "ciprofloxacin": {"display_name": {"en": "Ciprofloxacin"}},
        "furosemide_oral": {"display_name": {"en": "Furosemide"}},
        "sevelamer": {"display_name": {"en": "Sevelamer"}},
        "mycophenolate_mofetil": {"display_name": {"en": "MMF"}},
    }


# ============================================================================
# DoseIndividualization
# ============================================================================

class TestDoseIndividualization:

    def test_no_weight_trajectory_returns_empty(self):
        """Without weight history and without pgx, nothing fires."""
        di = DoseIndividualization()
        patient = _patient([("Amiodarone 200mg", "amiodarone")])
        result = di.evaluate(patient, _drug_db())
        assert result == []

    def test_slow_weight_loss_does_not_trigger(self):
        """1%/month is below the 2%/month threshold."""
        di = DoseIndividualization()
        patient = _patient(
            [("Amiodarone 200mg", "amiodarone")],
            weight_trajectory=[
                WeightTrajectoryPoint(weight_kg=80.0, date="2026-03-01"),
                WeightTrajectoryPoint(weight_kg=79.2, date="2026-04-01"),
                WeightTrajectoryPoint(weight_kg=78.4, date="2026-06-01"),
            ],
        )
        result = di.evaluate(patient, _drug_db())
        assert all(d.source != "weight_loss_rate" for d in result)

    def test_fast_weight_loss_triggers_amiodarone(self):
        """~3%/month sustained → amiodarone monitor flag with -15% magnitude."""
        di = DoseIndividualization()
        patient = _patient(
            [("Amiodarone 200mg", "amiodarone")],
            weight_trajectory=[
                WeightTrajectoryPoint(weight_kg=85.0, date="2026-02-01"),
                WeightTrajectoryPoint(weight_kg=75.0, date="2026-06-01"),
            ],
        )
        result = di.evaluate(patient, _drug_db())
        amio = [d for d in result if d.drug_profile_id == "amiodarone"]
        assert len(amio) == 1
        assert amio[0].source == "weight_loss_rate"
        assert amio[0].adjustment_type == "monitor"
        assert amio[0].adjustment_magnitude_percent == -15.0
        assert amio[0].evidence_grade == EvidenceGrade.B

    def test_pgx_cyp2c19_poor_voriconazole(self):
        di = DoseIndividualization()
        patient = _patient(
            [("Voriconazole 200mg", "voriconazole")],
            pharmacogenomics=Pharmacogenomics(cyp2c19_phenotype="poor"),
        )
        result = di.evaluate(patient, _drug_db())
        vori = [d for d in result if d.drug_profile_id == "voriconazole"]
        assert len(vori) == 1
        assert vori[0].source == "pharmacogenomics"
        assert vori[0].adjustment_type == "decrease"
        assert vori[0].adjustment_magnitude_percent == -25.0
        assert "cyp2c19_poor_voriconazole" in vori[0].rationale_i18n_key

    def test_pgx_cyp3a5_expresser_tacrolimus_dose_up(self):
        di = DoseIndividualization()
        patient = _patient(
            [("Tacrolimus 1mg", "tacrolimus")],
            pharmacogenomics=Pharmacogenomics(cyp3a5_phenotype="expresser"),
        )
        result = di.evaluate(patient, _drug_db())
        tac = [d for d in result if d.drug_profile_id == "tacrolimus"]
        assert len(tac) == 1
        assert tac[0].adjustment_type == "increase"
        assert tac[0].adjustment_magnitude_percent == 50.0

    def test_pgx_hla_b1502_positive_carbamazepine_contraindication(self):
        di = DoseIndividualization()
        patient = _patient(
            [("Carbamazepine 200mg", "carbamazepine")],
            pharmacogenomics=Pharmacogenomics(hla_b1502=True),
        )
        result = di.evaluate(patient, _drug_db())
        cbz = [d for d in result if d.drug_profile_id == "carbamazepine"]
        assert len(cbz) == 1
        assert cbz[0].adjustment_type == "alternative"
        assert "hla_b1502" in cbz[0].rationale_i18n_key

    def test_hla_b1502_negative_does_not_trigger(self):
        """Negative HLA-B*1502 is the safe case — no recommendation issued."""
        di = DoseIndividualization()
        patient = _patient(
            [("Carbamazepine 200mg", "carbamazepine")],
            pharmacogenomics=Pharmacogenomics(hla_b1502=False),
        )
        result = di.evaluate(patient, _drug_db())
        assert result == []

    def test_no_pharmacogenomics_means_no_pgx_flags(self):
        di = DoseIndividualization()
        patient = _patient([("Voriconazole 200mg", "voriconazole")])
        result = di.evaluate(patient, _drug_db())
        assert all(d.source != "pharmacogenomics" for d in result)


# ============================================================================
# InteractionMatrixEngine
# ============================================================================

class TestInteractionMatrixEngine:

    def test_no_pairs_when_only_one_drug(self):
        engine = InteractionMatrixEngine()
        patient = _patient([("Amiodarone", "amiodarone")])
        assert engine.find_pairs(patient, _drug_db()) == []

    def test_ppi_lt4_pair_found(self):
        engine = InteractionMatrixEngine()
        patient = _patient([
            ("Omeprazole", "omeprazole"),
            ("Levothyroxine 100", "levothyroxine_tablet"),
        ])
        pairs = engine.find_pairs(patient, _drug_db())
        assert len(pairs) == 1
        assert pairs[0].perpetrator_profile_id == "omeprazole"
        assert pairs[0].victim_profile_id == "levothyroxine_tablet"
        assert pairs[0].mechanism_i18n_key == "ddi.ppi_lt4_dissolution"
        assert pairs[0].severity == "high"
        assert pairs[0].evidence_grade == EvidenceGrade.A

    def test_carbamazepine_apixaban_inducer_pair(self):
        engine = InteractionMatrixEngine()
        patient = _patient([
            ("Carbamazepine 200mg", "carbamazepine"),
            ("Apixaban 5mg", "apixaban"),
        ])
        pairs = engine.find_pairs(patient, _drug_db())
        assert any(p.mechanism_i18n_key == "ddi.cyp3a_inducer_doac" for p in pairs)

    def test_loop_lithium_pair(self):
        engine = InteractionMatrixEngine()
        patient = _patient([
            ("Furosemide", "furosemide_oral"),
            ("Lithium", "lithium_carbonate"),
        ])
        pairs = engine.find_pairs(patient, _drug_db())
        assert any(p.mechanism_i18n_key == "ddi.loop_lithium_toxicity" for p in pairs)

    def test_no_false_positive_unrelated_drugs(self):
        engine = InteractionMatrixEngine()
        # Two drugs that have no encoded matrix entry between them
        patient = _patient([
            ("Metoprolol succinate", "metoprolol_succinate"),
            ("Sevelamer", "sevelamer"),
        ])
        pairs = engine.find_pairs(patient, _drug_db())
        assert pairs == []

    def test_multi_drug_finds_all_applicable_pairs(self):
        """Three perpetrator-victim pairs encoded among five drugs."""
        engine = InteractionMatrixEngine()
        patient = _patient([
            ("Omeprazole", "omeprazole"),
            ("Levothyroxine", "levothyroxine_tablet"),
            ("Ciprofloxacin", "ciprofloxacin"),
            ("Amiodarone", "amiodarone"),
        ])
        pairs = engine.find_pairs(patient, _drug_db())
        # Expected: omeprazole→LT4, ciprofloxacin↔amiodarone (QT additive)
        mechs = {p.mechanism_i18n_key for p in pairs}
        assert "ddi.ppi_lt4_dissolution" in mechs
        assert "ddi.qt_additive" in mechs


# ============================================================================
# BayesianLabProjector
# ============================================================================

class TestBayesianLabProjector:

    def test_insufficient_points_returns_empty(self):
        """<3 points → no projection."""
        p = BayesianLabProjector()
        history = [
            LabHistoryPoint(test_name="TSH", value=2.5, date="2026-04-01"),
            LabHistoryPoint(test_name="TSH", value=3.0, date="2026-05-01"),
        ]
        assert p.project(history) == []

    def test_rising_trend_detected(self):
        """Clear monotonic rise → 'rising' direction with positive slope."""
        p = BayesianLabProjector()
        history = [
            LabHistoryPoint(test_name="TSH", value=2.0, date="2026-01-01"),
            LabHistoryPoint(test_name="TSH", value=3.5, date="2026-02-15"),
            LabHistoryPoint(test_name="TSH", value=5.0, date="2026-04-01"),
            LabHistoryPoint(test_name="TSH", value=6.5, date="2026-05-15"),
        ]
        result = p.project(history, weeks_ahead=4)
        assert len(result) == 1
        proj = result[0]
        assert proj.test_name == "TSH"
        assert proj.trend_direction == "rising"
        assert proj.slope_per_week > 0
        assert proj.projected_value > 6.5  # extrapolation past last point
        assert proj.ci_low < proj.projected_value < proj.ci_high
        assert proj.historical_points_used == 4

    def test_falling_trend_detected(self):
        p = BayesianLabProjector()
        history = [
            LabHistoryPoint(test_name="eGFR", value=68.0, date="2026-01-01"),
            LabHistoryPoint(test_name="eGFR", value=62.0, date="2026-02-15"),
            LabHistoryPoint(test_name="eGFR", value=55.0, date="2026-04-01"),
            LabHistoryPoint(test_name="eGFR", value=48.0, date="2026-05-15"),
        ]
        result = p.project(history, weeks_ahead=8)
        assert len(result) == 1
        assert result[0].trend_direction == "falling"
        assert result[0].slope_per_week < 0

    def test_stable_trend_under_threshold(self):
        """Tiny noise around a constant → 'stable'."""
        p = BayesianLabProjector()
        history = [
            LabHistoryPoint(test_name="INR", value=2.5, date="2026-01-01"),
            LabHistoryPoint(test_name="INR", value=2.6, date="2026-02-01"),
            LabHistoryPoint(test_name="INR", value=2.4, date="2026-03-01"),
            LabHistoryPoint(test_name="INR", value=2.55, date="2026-04-01"),
        ]
        result = p.project(history, weeks_ahead=4)
        assert len(result) == 1
        assert result[0].trend_direction == "stable"
        assert abs(result[0].slope_per_week) < 0.05

    def test_multiple_tests_grouped_independently(self):
        p = BayesianLabProjector()
        history = [
            LabHistoryPoint(test_name="TSH", value=2.0, date="2026-01-01"),
            LabHistoryPoint(test_name="TSH", value=4.0, date="2026-03-01"),
            LabHistoryPoint(test_name="TSH", value=6.0, date="2026-05-01"),
            LabHistoryPoint(test_name="INR", value=2.5, date="2026-01-01"),
            LabHistoryPoint(test_name="INR", value=2.4, date="2026-03-01"),
            LabHistoryPoint(test_name="INR", value=2.5, date="2026-05-01"),
        ]
        result = p.project(history)
        names = {r.test_name for r in result}
        assert names == {"TSH", "INR"}

    def test_confidence_interval_widens_with_extrapolation(self):
        """CI for a projection further into the future is wider than nearer."""
        p = BayesianLabProjector()
        history = [
            LabHistoryPoint(test_name="TSH", value=2.0, date="2026-01-01"),
            LabHistoryPoint(test_name="TSH", value=2.5, date="2026-02-01"),
            LabHistoryPoint(test_name="TSH", value=3.2, date="2026-03-01"),
            LabHistoryPoint(test_name="TSH", value=3.5, date="2026-04-01"),
        ]
        near = p.project(history, weeks_ahead=2)[0]
        far = p.project(history, weeks_ahead=20)[0]
        near_width = near.ci_high - near.ci_low
        far_width = far.ci_high - far.ci_low
        assert far_width > near_width

    def test_malformed_dates_skipped(self):
        """Bad ISO date strings cause that test group to be skipped, not crash."""
        p = BayesianLabProjector()
        history = [
            LabHistoryPoint(test_name="TSH", value=2.0, date="not-a-date"),
            LabHistoryPoint(test_name="TSH", value=3.0, date="also-bad"),
            LabHistoryPoint(test_name="TSH", value=4.0, date="still-bad"),
            LabHistoryPoint(test_name="INR", value=2.5, date="2026-01-01"),
            LabHistoryPoint(test_name="INR", value=2.5, date="2026-02-01"),
            LabHistoryPoint(test_name="INR", value=2.5, date="2026-03-01"),
        ]
        result = p.project(history)
        # TSH skipped due to bad dates; INR projected normally
        assert all(r.test_name != "TSH" for r in result)
        assert any(r.test_name == "INR" for r in result)

    def test_disclaimer_emitted_for_small_n(self):
        """Projection from n=3 or n=4 has the disclaimer key set."""
        p = BayesianLabProjector()
        history = [
            LabHistoryPoint(test_name="TSH", value=2.0, date="2026-01-01"),
            LabHistoryPoint(test_name="TSH", value=3.0, date="2026-02-01"),
            LabHistoryPoint(test_name="TSH", value=4.0, date="2026-03-01"),
        ]
        result = p.project(history)
        assert result[0].confidence_note_i18n_key == "projection.linear_regression_disclaimer"

    def test_no_disclaimer_for_ample_n(self):
        """n >= 5 → no disclaimer (sufficient statistical confidence)."""
        p = BayesianLabProjector()
        history = [
            LabHistoryPoint(test_name="TSH", value=2.0 + 0.5 * i, date=f"2026-0{(i % 9) + 1}-01")
            for i in range(5)
        ]
        result = p.project(history)
        assert result[0].confidence_note_i18n_key is None
