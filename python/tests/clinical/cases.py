"""
METACOD GLP-1 module — clinical validation case library.

Each case is a real-world clinical scenario with:
  - patient_input  : full PatientContext payload
  - expected       : assertions the engine must satisfy

These are SaMD reference cases — they are run on every change to rule_pack or
agent and must pass. Failures here block release of a new rule_pack version.

Sources cited for each case justify the expected outcome at evidence grade level.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExpectedOutcomes:
    triage_color: str                                       # "green" | "yellow" | "red"
    glp1_decision: str                                      # "CONTINUE" | "HOLD" | "REVIEW"
    rules_that_must_fire: list[str] = field(default_factory=list)
    rules_that_must_not_fire: list[str] = field(default_factory=list)
    future_risk_keys_must_include: list[str] = field(default_factory=list)
    chronic_adjustment_keys_must_include: list[str] = field(default_factory=list)
    min_grade_a_rules: int = 0                              # at least this many Grade A rules must fire


@dataclass
class ClinicalCase:
    case_id: str
    description: str
    clinical_rationale: str
    sources: list[str]
    patient_input: dict
    expected: ExpectedOutcomes


# ----- Shared patient defaults -----

def _patient(**overrides) -> dict:
    """Build a complete PatientContext dict with sensible defaults; override per case."""
    base = {
        "patient_id": "P-CASE",
        "age_years": 55,
        "sex": "female",
        "weight_kg": 80.0,
        "glp1_agent": "none",
        "glp1_weeks_since_start": None,
        "glp1_weeks_since_last_dose_increase": None,
        "ppi_or_h2_blocker": False,
        "calcium_iron_magnesium_aluminum_products": False,
        "bile_acid_sequestrants": False,
        "sucralfate": False,
        "child_pugh": "none",
        "aki_present": False,
        "dialysis": "none",
        "heart_failure_congestion": False,
        "gut_edema_suspected": False,
        "systemic_inflammation": "none",
        "acute_infection": False,
        "bariatric_type": "none",
        "months_since_bariatric": None,
        "short_bowel": False,
        "symptoms": {
            "nausea_score": 0,
            "vomiting_episodes_24h": 0,
            "abdominal_pain_score": 0,
            "bloating_score": 0,
            "early_satiety": False,
            "constipation_days_without_stool": 0,
            "diarrhea_episodes_24h": 0,
            "unable_to_keep_fluids": False,
            "unable_to_keep_meds": False,
            "dizziness_or_orthostasis": False,
            "reduced_urine_output": False,
            "black_stool_or_visible_blood": False,
            "fever": False,
            "weaker_effect_of_regular_meds": False,
            "delayed_effect_of_regular_meds": False,
        },
        "labs": {},
        "medications": [],
    }
    base.update(overrides)
    return base


# ============================================================================
# Cases
# ============================================================================

CASE_01_LT4_PPI_TIRZEPATIDE = ClinicalCase(
    case_id="C01_LT4_PPI_TIRZEPATIDE_NAUSEA",
    description="58F, tirzepatide week 2, LT4 tablet + omeprazole, rising TSH, nausea — the prototypical scenario.",
    clinical_rationale=(
        "PPI elevates gastric pH → LT4 tablet dissolution failure → TSH drift. "
        "Tirzepatide first 4 weeks compounds with delayed gastric emptying. "
        "Should fire LT4_TABLET_PPI (Grade A) and recommend GLP-1 HOLD due to nausea."
    ),
    sources=[
        "Centanni M et al. NEJM 2017",
        "FDA Mounjaro/Tirzepatide label",
    ],
    patient_input=_patient(
        patient_id="P-CASE-01",
        age_years=58,
        sex="female",
        glp1_agent="tirzepatide_sc",
        glp1_weeks_since_start=2,
        glp1_weeks_since_last_dose_increase=2,
        ppi_or_h2_blocker=True,
        symptoms={
            "nausea_score": 7,
            "vomiting_episodes_24h": 1,
            "abdominal_pain_score": 0,
            "bloating_score": 0,
            "early_satiety": True,
            "constipation_days_without_stool": 3,
            "diarrhea_episodes_24h": 0,
            "unable_to_keep_fluids": False,
            "unable_to_keep_meds": False,
            "dizziness_or_orthostasis": False,
            "reduced_urine_output": False,
            "black_stool_or_visible_blood": False,
            "fever": False,
            "weaker_effect_of_regular_meds": True,
            "delayed_effect_of_regular_meds": False,
        },
        labs={"egfr_ml_min": 65, "tsh_miu_l": 6.4, "crp_mg_l": 5},
        medications=[
            {"name": "Levothyroxine 100 mcg", "profile_id": "levothyroxine_tablet", "route": "oral", "is_essential": True},
            {"name": "Omeprazole 20 mg", "profile_id": "omeprazole", "route": "oral", "is_essential": False},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="yellow",
        glp1_decision="HOLD",
        rules_that_must_fire=["LT4_TABLET_PPI"],
        rules_that_must_not_fire=["EGFR_LOW_DOAC", "CIRRHOSIS_HIGH_FIRST_PASS"],
        future_risk_keys_must_include=["forecast.risk.lt4_drift_ppi"],
        min_grade_a_rules=1,
    ),
)

CASE_02_LT4_CATION_CHELATION = ClinicalCase(
    case_id="C02_LT4_CALCIUM_CHELATION",
    description="65F, semaglutide stable week 12, LT4 tablet + daily calcium carbonate supplement, no PPI.",
    clinical_rationale=(
        "Calcium binds LT4 in lumen → reduced bioavailability. Should fire "
        "LT4_TABLET_CATION (Grade A). Stable on GLP-1, no GI symptoms, "
        "so triage GREEN and GLP-1 CONTINUE."
    ),
    sources=[
        "Liwanpo L & Hershman JM — LT4 absorption interactions",
        "Virili C et al. 2023 systematic review",
    ],
    patient_input=_patient(
        patient_id="P-CASE-02",
        age_years=65,
        sex="female",
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=12,
        glp1_weeks_since_last_dose_increase=8,
        calcium_iron_magnesium_aluminum_products=True,
        labs={"egfr_ml_min": 72, "tsh_miu_l": 5.8},
        medications=[
            {"name": "Levothyroxine 75 mcg", "profile_id": "levothyroxine_tablet", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["LT4_TABLET_CATION"],
        rules_that_must_not_fire=["LT4_TABLET_PPI"],
        min_grade_a_rules=1,
    ),
)

CASE_03_ORAL_IRON_PPI = ClinicalCase(
    case_id="C03_ORAL_IRON_PPI_REFRACTORY_ANEMIA",
    description="45F, semaglutide week 16, ferrous sulfate + pantoprazole, persistent low ferritin.",
    clinical_rationale=(
        "PPI impairs Fe3+→Fe2+ conversion → oral iron under-absorption. "
        "Should fire ORAL_IRON_PPI (Grade A). Recommend IV iron after 8w if no response."
    ),
    sources=[
        "Stoffel NU et al. Haematologica 2024",
        "Lopes M et al. PPI-iron systematic review",
    ],
    patient_input=_patient(
        patient_id="P-CASE-03",
        age_years=45,
        sex="female",
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=16,
        glp1_weeks_since_last_dose_increase=10,
        ppi_or_h2_blocker=True,
        labs={"egfr_ml_min": 88, "hemoglobin_g_dl": 10.4, "ferritin_ng_ml": 15, "crp_mg_l": 4},
        medications=[
            {"name": "Ferrous sulfate 325 mg", "profile_id": "oral_iron_ferrous_sulfate", "route": "oral"},
            {"name": "Pantoprazole 40 mg", "profile_id": "pantoprazole", "route": "oral"},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["ORAL_IRON_PPI"],
        min_grade_a_rules=1,
    ),
)

CASE_04_TIRZEPATIDE_OC_EARLY = ClinicalCase(
    case_id="C04_TIRZEPATIDE_OC_WEEK_1",
    description="28F, tirzepatide week 1, combined oral contraceptive — FDA label trigger.",
    clinical_rationale=(
        "FDA Mounjaro/Zepbound label mandates non-oral or barrier contraception "
        "for first 4 weeks after start and each escalation. Must fire "
        "GLP1_TIRZEPATIDE_OC_EARLY (Grade A). REVIEW decision due to recent start."
    ),
    sources=[
        "FDA Mounjaro prescribing information",
        "FDA Zepbound prescribing information",
    ],
    patient_input=_patient(
        patient_id="P-CASE-04",
        age_years=28,
        sex="female",
        glp1_agent="tirzepatide_sc",
        glp1_weeks_since_start=1,
        glp1_weeks_since_last_dose_increase=1,
        labs={"egfr_ml_min": 95},
        medications=[
            {"name": "Combined OC", "profile_id": "combined_oral_contraceptive", "route": "oral"},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="REVIEW",
        rules_that_must_fire=["GLP1_TIRZEPATIDE_OC_EARLY"],
        min_grade_a_rules=1,
    ),
)

CASE_05_FUROSEMIDE_HF_CONGESTION = ClinicalCase(
    case_id="C05_FUROSEMIDE_HF_GUT_EDEMA",
    description="68M, semaglutide week 20, oral furosemide + HF congestion / suspected gut edema.",
    clinical_rationale=(
        "Gut wall edema in decompensated HF impairs furosemide oral bioavailability. "
        "Switch to IV or torsemide/bumetanide. Should fire FUROSEMIDE_GUT_EDEMA (Grade B)."
    ),
    sources=[
        "Mentz RJ et al. TRANSFORM-HF 2023",
        "Buggey J et al. Loop diuretic bioavailability in HF",
    ],
    patient_input=_patient(
        patient_id="P-CASE-05",
        age_years=68,
        sex="male",
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=20,
        glp1_weeks_since_last_dose_increase=12,
        heart_failure_congestion=True,
        gut_edema_suspected=True,
        labs={"egfr_ml_min": 55, "crp_mg_l": 12},
        medications=[
            {"name": "Furosemide 40 mg po", "profile_id": "furosemide_oral", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["FUROSEMIDE_GUT_EDEMA"],
    ),
)

CASE_06_DOAC_LOW_EGFR = ClinicalCase(
    case_id="C06_APIXABAN_LOW_EGFR",
    description="72M, semaglutide week 24, apixaban + eGFR 42 (CKD-3b).",
    clinical_rationale=(
        "DOAC accumulation risk at low eGFR. Apixaban dose adjustment per label. "
        "Should fire EGFR_LOW_DOAC (Grade A). Chronic adjustment trigger expected."
    ),
    sources=[
        "FDA Apixaban label",
        "ESC AF guidelines",
    ],
    patient_input=_patient(
        patient_id="P-CASE-06",
        age_years=72,
        sex="male",
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=24,
        glp1_weeks_since_last_dose_increase=20,
        labs={"egfr_ml_min": 42, "creatinine_mg_dl": 1.6},
        medications=[
            {"name": "Apixaban 5 mg bid", "profile_id": "apixaban", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["EGFR_LOW_DOAC"],
        future_risk_keys_must_include=["forecast.risk.doac_accumulation_low_egfr"],
        chronic_adjustment_keys_must_include=["adjust.doac_reduce_at_egfr_30"],
        min_grade_a_rules=1,
    ),
)

CASE_07_CIRRHOSIS_PPI = ClinicalCase(
    case_id="C07_CIRRHOSIS_B_OMEPRAZOLE",
    description="60M, semaglutide week 8, cirrhosis Child-Pugh B, on omeprazole (high first-pass).",
    clinical_rationale=(
        "Child-Pugh B + high-first-pass drug → reduced hepatic extraction → "
        "elevated bioavailability and prolonged t½. Fire CIRRHOSIS_HIGH_FIRST_PASS (A)."
    ),
    sources=[
        "FDA Guidance — Hepatic Impairment PK Studies",
        "EMA Hepatic impairment PK guideline",
    ],
    patient_input=_patient(
        patient_id="P-CASE-07",
        age_years=60,
        sex="male",
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=8,
        glp1_weeks_since_last_dose_increase=4,
        child_pugh="B",
        labs={"egfr_ml_min": 70, "albumin_g_dl": 3.2, "inr": 1.4},
        medications=[
            {"name": "Omeprazole 40 mg", "profile_id": "omeprazole", "route": "oral"},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["CIRRHOSIS_HIGH_FIRST_PASS"],
        min_grade_a_rules=1,
    ),
)

CASE_08_INFLAMMATION_CYP = ClinicalCase(
    case_id="C08_ACUTE_INFECTION_CYP_SUBSTRATE",
    description="55M, semaglutide week 14, omeprazole, acute infection with CRP 85 mg/L.",
    clinical_rationale=(
        "Cytokine-driven CYP3A4 suppression during inflammation → CYP substrate "
        "accumulation. Omeprazole is inflammation-sensitive. Fire INFLAMMATION_CYP_SUBSTRATE (B)."
    ),
    sources=[
        "Stanke-Labesque F et al. Inflammation–CYP interactions",
        "Lenoir C et al. IL-6 and CYP3A4",
    ],
    patient_input=_patient(
        patient_id="P-CASE-08",
        age_years=55,
        sex="male",
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=14,
        glp1_weeks_since_last_dose_increase=10,
        acute_infection=True,
        systemic_inflammation="severe",
        labs={"egfr_ml_min": 75, "crp_mg_l": 85},
        medications=[
            {"name": "Omeprazole 20 mg", "profile_id": "omeprazole", "route": "oral"},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["INFLAMMATION_CYP_SUBSTRATE"],
        future_risk_keys_must_include=["forecast.risk.cyp_substrate_toxicity_in_inflammation"],
    ),
)

CASE_09_FQ_CATION_CHELATION = ClinicalCase(
    case_id="C09_CIPRO_IRON_CHELATION",
    description="50F, semaglutide week 28, ciprofloxacin for UTI + concurrent oral iron.",
    clinical_rationale=(
        "Fluoroquinolone forms non-absorbable chelate with iron → therapy failure. "
        "Fire CATION_CHELATION_FLUOROQUINOLONE (Grade A). Enforce ≥4h separation."
    ),
    sources=[
        "Polk RE et al. fluoroquinolone-cation studies",
        "FDA Ciprofloxacin label",
    ],
    patient_input=_patient(
        patient_id="P-CASE-09",
        age_years=50,
        sex="female",
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=28,
        glp1_weeks_since_last_dose_increase=24,
        calcium_iron_magnesium_aluminum_products=True,
        labs={"egfr_ml_min": 80},
        medications=[
            {"name": "Ciprofloxacin 500 mg bid", "profile_id": "ciprofloxacin", "route": "oral"},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["CATION_CHELATION_FLUOROQUINOLONE"],
        min_grade_a_rules=1,
    ),
)

CASE_10_ITRACONAZOLE_PPI = ClinicalCase(
    case_id="C10_ITRA_CAPSULE_PPI",
    description="60M, semaglutide week 30, itraconazole capsule for onychomycosis + omeprazole.",
    clinical_rationale=(
        "Itraconazole capsule dissolution is highly pH-dependent — PPI causes "
        "therapy failure. Fire PPI_AZOLE_PH_SENSITIVE (Grade A). Switch to oral solution or IV."
    ),
    sources=[
        "FDA Itraconazole capsule label",
        "Lim SG et al.",
    ],
    patient_input=_patient(
        patient_id="P-CASE-10",
        age_years=60,
        sex="male",
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=30,
        glp1_weeks_since_last_dose_increase=26,
        ppi_or_h2_blocker=True,
        labs={"egfr_ml_min": 78, "alt_u_l": 22},
        medications=[
            {"name": "Itraconazole 100 mg capsule", "profile_id": "itraconazole_capsule", "route": "oral"},
            {"name": "Omeprazole 20 mg", "profile_id": "omeprazole", "route": "oral"},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["PPI_AZOLE_PH_SENSITIVE"],
        min_grade_a_rules=1,
    ),
)

CASE_11_BARIATRIC_DOAC = ClinicalCase(
    case_id="C11_RECENT_BARIATRIC_APIXABAN",
    description="35F, semaglutide week 6, apixaban 3 months post-RYGB.",
    clinical_rationale=(
        "Altered proximal GI anatomy <6 months post-bariatric → unpredictable DOAC "
        "exposure. Specialist review or LMWH/VKA bridge. Fire BARIATRIC_EARLY_DOAC (B)."
    ),
    sources=[
        "ISTH 2021 anticoagulation post-bariatric",
        "Anticoagulation Forum 2025",
    ],
    patient_input=_patient(
        patient_id="P-CASE-11",
        age_years=35,
        sex="female",
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=6,
        glp1_weeks_since_last_dose_increase=6,
        bariatric_type="RYGB",
        months_since_bariatric=3,
        labs={"egfr_ml_min": 85, "albumin_g_dl": 3.6},
        medications=[
            {"name": "Apixaban 5 mg bid", "profile_id": "apixaban", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["BARIATRIC_EARLY_DOAC"],
    ),
)

CASE_12_RED_TRIAGE_EMERGENCY = ClinicalCase(
    case_id="C12_RED_PERSISTENT_VOMITING",
    description="60F, tirzepatide week 6, persistent vomiting, unable to keep fluids, reduced urine.",
    clinical_rationale=(
        "RED triage criteria: cannot keep fluids/meds, reduced urine output. "
        "Immediate ER evaluation. GLP-1 HOLD. AKI risk in forecast."
    ),
    sources=[
        "FDA GLP-1 label GI warnings",
        "Clinical safety reporting — dehydration/AKI on GLP-1 escalation",
    ],
    patient_input=_patient(
        patient_id="P-CASE-12",
        age_years=60,
        sex="female",
        glp1_agent="tirzepatide_sc",
        glp1_weeks_since_start=6,
        glp1_weeks_since_last_dose_increase=2,
        symptoms={
            "nausea_score": 9,
            "vomiting_episodes_24h": 6,
            "abdominal_pain_score": 5,
            "bloating_score": 4,
            "early_satiety": True,
            "constipation_days_without_stool": 0,
            "diarrhea_episodes_24h": 0,
            "unable_to_keep_fluids": True,
            "unable_to_keep_meds": True,
            "dizziness_or_orthostasis": True,
            "reduced_urine_output": True,
            "black_stool_or_visible_blood": False,
            "fever": False,
            "weaker_effect_of_regular_meds": True,
            "delayed_effect_of_regular_meds": False,
        },
        labs={"egfr_ml_min": 55, "creatinine_mg_dl": 1.4, "tsh_miu_l": 5.0},
        medications=[
            {"name": "Apixaban 5 mg bid", "profile_id": "apixaban", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="red",
        glp1_decision="HOLD",
        future_risk_keys_must_include=["forecast.risk.aki_dehydration"],
    ),
)

CASE_13_GREEN_BASELINE_STABLE = ClinicalCase(
    case_id="C13_GREEN_BASELINE",
    description="50M, semaglutide week 20 stable, no concomitant meds, normal labs.",
    clinical_rationale=(
        "Negative control. Verifies that with no qualifying conditions and no "
        "GI symptoms, the engine produces GREEN / CONTINUE and fires zero rules."
    ),
    sources=["Baseline stability check"],
    patient_input=_patient(
        patient_id="P-CASE-13",
        age_years=50,
        sex="male",
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=20,
        glp1_weeks_since_last_dose_increase=12,
        labs={"egfr_ml_min": 95, "tsh_miu_l": 2.1, "albumin_g_dl": 4.4, "crp_mg_l": 2},
        medications=[],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=[],
        rules_that_must_not_fire=[
            "LT4_TABLET_PPI", "ORAL_IRON_PPI", "EGFR_LOW_DOAC",
            "CIRRHOSIS_HIGH_FIRST_PASS", "INFLAMMATION_CYP_SUBSTRATE",
        ],
    ),
)

CASE_14_MULTI_RULE_COMPLEX = ClinicalCase(
    case_id="C14_MULTI_RULE_COMPLEX",
    description="70F, semaglutide week 4 (recent escalation), LT4 tablet + PPI + calcium + apixaban + eGFR 38.",
    clinical_rationale=(
        "Compound scenario stress-test. Should fire LT4_TABLET_PPI + LT4_TABLET_CATION "
        "+ EGFR_LOW_DOAC simultaneously. GLP-1 REVIEW (recent escalation). "
        "Future risks should include DOAC accumulation and LT4 drift."
    ),
    sources=["Composite — exercises rule co-firing"],
    patient_input=_patient(
        patient_id="P-CASE-14",
        age_years=70,
        sex="female",
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=4,
        glp1_weeks_since_last_dose_increase=2,
        ppi_or_h2_blocker=True,
        calcium_iron_magnesium_aluminum_products=True,
        labs={"egfr_ml_min": 38, "creatinine_mg_dl": 1.8, "tsh_miu_l": 7.5, "albumin_g_dl": 3.8},
        medications=[
            {"name": "Levothyroxine 88 mcg", "profile_id": "levothyroxine_tablet", "route": "oral", "is_essential": True},
            {"name": "Pantoprazole 40 mg", "profile_id": "pantoprazole", "route": "oral"},
            {"name": "Apixaban 2.5 mg bid", "profile_id": "apixaban", "route": "oral", "is_essential": True},
            {"name": "Calcium carbonate 500 mg", "profile_id": "oral_iron_ferrous_bisglycinate", "route": "oral"},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="REVIEW",
        rules_that_must_fire=["LT4_TABLET_PPI", "LT4_TABLET_CATION", "EGFR_LOW_DOAC"],
        future_risk_keys_must_include=[
            "forecast.risk.doac_accumulation_low_egfr",
            "forecast.risk.lt4_drift_ppi",
        ],
        min_grade_a_rules=3,
    ),
)

CASE_15_HYPOALBUMINEMIA_WARFARIN = ClinicalCase(
    case_id="C15_HYPOALBUMINEMIA_WARFARIN",
    description="65M, semaglutide week 12, warfarin (highly protein-bound), albumin 2.4 g/dL.",
    clinical_rationale=(
        "Hypoalbuminemia raises free fraction of warfarin → total level misleading, "
        "clinical bleeding response may exceed INR target. Fire "
        "HYPOALBUMINEMIA_HIGH_PROTEIN_BINDING (Grade B)."
    ),
    sources=[
        "Roberts JA et al. PK in hypoalbuminemia",
        "Ulldemolins M et al. free vs total drug level",
    ],
    patient_input=_patient(
        patient_id="P-CASE-15",
        age_years=65,
        sex="male",
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=12,
        glp1_weeks_since_last_dose_increase=8,
        labs={"egfr_ml_min": 60, "albumin_g_dl": 2.4, "inr": 2.6},
        medications=[
            {"name": "Warfarin 5 mg daily", "profile_id": "warfarin", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["HYPOALBUMINEMIA_HIGH_PROTEIN_BINDING"],
    ),
)


# ============================================================================
# Export
# ============================================================================

ALL_CASES: list[ClinicalCase] = [
    CASE_01_LT4_PPI_TIRZEPATIDE,
    CASE_02_LT4_CATION_CHELATION,
    CASE_03_ORAL_IRON_PPI,
    CASE_04_TIRZEPATIDE_OC_EARLY,
    CASE_05_FUROSEMIDE_HF_CONGESTION,
    CASE_06_DOAC_LOW_EGFR,
    CASE_07_CIRRHOSIS_PPI,
    CASE_08_INFLAMMATION_CYP,
    CASE_09_FQ_CATION_CHELATION,
    CASE_10_ITRACONAZOLE_PPI,
    CASE_11_BARIATRIC_DOAC,
    CASE_12_RED_TRIAGE_EMERGENCY,
    CASE_13_GREEN_BASELINE_STABLE,
    CASE_14_MULTI_RULE_COMPLEX,
    CASE_15_HYPOALBUMINEMIA_WARFARIN,
]
