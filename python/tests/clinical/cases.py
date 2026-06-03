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


CASE_16_TETRACYCLINE_CATION = ClinicalCase(
    case_id="C16_DOXYCYCLINE_CATION_CHELATION",
    description="48F, semaglutide week 18, doxycycline for infection + concurrent calcium/iron product.",
    clinical_rationale=(
        "Tetracyclines form non-absorbable chelates with multivalent cations → "
        "reduced absorption and therapy failure. Fire CATION_CHELATION_TETRACYCLINE "
        "(Grade A); enforce separation from minerals/dairy."
    ),
    sources=[
        "FDA Doxycycline prescribing information",
        "Neuvonen PJ — tetracycline-cation PK literature",
    ],
    patient_input=_patient(
        patient_id="P-CASE-16",
        age_years=48,
        sex="female",
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=18,
        glp1_weeks_since_last_dose_increase=12,
        calcium_iron_magnesium_aluminum_products=True,
        labs={"egfr_ml_min": 82},
        medications=[
            {"name": "Doxycycline 100 mg bid", "profile_id": "doxycycline", "route": "oral"},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["CATION_CHELATION_TETRACYCLINE"],
        min_grade_a_rules=1,
    ),
)

CASE_17_DIGOXIN_LOW_EGFR = ClinicalCase(
    case_id="C17_DIGOXIN_LOW_EGFR",
    description="74M, semaglutide week 26, digoxin for rate control + eGFR 40 (CKD-3b).",
    clinical_rationale=(
        "Digoxin is renally cleared with a narrow therapeutic index; falling eGFR "
        "predictably raises levels → toxicity. Fire EGFR_LOW_DIGOXIN (Grade A); "
        "check level and consider dose reduction."
    ),
    sources=["FDA Digoxin prescribing information"],
    patient_input=_patient(
        patient_id="P-CASE-17",
        age_years=74,
        sex="male",
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=26,
        glp1_weeks_since_last_dose_increase=20,
        labs={"egfr_ml_min": 40, "creatinine_mg_dl": 1.7},
        medications=[
            {"name": "Digoxin 0.125 mg daily", "profile_id": "digoxin", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["EGFR_LOW_DIGOXIN"],
        rules_that_must_not_fire=["EGFR_LOW_DOAC"],
        min_grade_a_rules=1,
    ),
)

CASE_18_GLP1_TMAX_SENSITIVE = ClinicalCase(
    case_id="C18_GLP1_TMAX_SENSITIVE_DRUG",
    description="52F, semaglutide week 22, ciprofloxacin (Tmax-sensitive) without concurrent cations.",
    clinical_rationale=(
        "GLP-1-induced delayed gastric emptying right-shifts Tmax for drugs that "
        "depend on a rapid peak. Fire GLP1_GASTROPARESIS_TMAX_SENSITIVE (Grade C, "
        "mechanistic). With no cations present, the chelation rule must NOT fire."
    ),
    sources=[
        "Ozempic / Mounjaro prescribing information — delayed gastric emptying",
        "Camilleri M — GI motility pharmacology",
    ],
    patient_input=_patient(
        patient_id="P-CASE-18",
        age_years=52,
        sex="female",
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=22,
        glp1_weeks_since_last_dose_increase=16,
        calcium_iron_magnesium_aluminum_products=False,
        labs={"egfr_ml_min": 88},
        medications=[
            {"name": "Ciprofloxacin 500 mg bid", "profile_id": "ciprofloxacin", "route": "oral"},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["GLP1_GASTROPARESIS_TMAX_SENSITIVE"],
        rules_that_must_not_fire=["CATION_CHELATION_FLUOROQUINOLONE"],
    ),
)

CASE_19_POSACONAZOLE_PPI = ClinicalCase(
    case_id="C19_POSACONAZOLE_PPI_V2",
    description="61M, semaglutide week 30, posaconazole oral suspension (drug_master v2) + omeprazole.",
    clinical_rationale=(
        "Validates v2 drug_master: posaconazole oral suspension requires acidic pH "
        "for absorption, so PPI co-administration causes under-exposure. The existing "
        "mechanism-first PPI_AZOLE_PH_SENSITIVE rule fires on the new drug profile "
        "without any rule change — proves additive drug_master expansion works."
    ),
    sources=[
        "FDA Noxafil prescribing information",
        "Krishna G et al. posaconazole absorption pH/fat dependence",
    ],
    patient_input=_patient(
        patient_id="P-CASE-19",
        age_years=61,
        sex="male",
        glp1_agent="semaglutide_sc",
        glp1_weeks_since_start=30,
        glp1_weeks_since_last_dose_increase=24,
        ppi_or_h2_blocker=True,
        labs={"egfr_ml_min": 76, "alt_u_l": 24},
        medications=[
            {"name": "Posaconazole suspension 200 mg", "profile_id": "posaconazole_oral_suspension", "route": "oral"},
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


# ============================================================================
# v2 rule_pack — drug-drug rules (med_summary derived context)
# ============================================================================

CASE_20_PPI_TKI = ClinicalCase(
    case_id="C20_PPI_TKI_PH",
    description="64M, semaglutide week 20, erlotinib (EGFR TKI) for NSCLC + omeprazole.",
    clinical_rationale=(
        "EGFR TKIs need acidic pH for dissolution; PPI reduces AUC 30–60% → "
        "subtherapeutic exposure and resistance. Fire PPI_TKI_PH_SENSITIVE (Grade A)."
    ),
    sources=["FDA Tarceva label — PPI warning", "Hilberg O et al."],
    patient_input=_patient(
        patient_id="P-CASE-20", age_years=64, sex="male",
        glp1_agent="semaglutide_sc", glp1_weeks_since_start=20, glp1_weeks_since_last_dose_increase=14,
        ppi_or_h2_blocker=True, labs={"egfr_ml_min": 78},
        medications=[
            {"name": "Erlotinib 150 mg", "profile_id": "erlotinib", "route": "oral", "is_essential": True},
            {"name": "Omeprazole 20 mg", "profile_id": "omeprazole", "route": "oral"},
        ],
    ),
    expected=ExpectedOutcomes(triage_color="green", glp1_decision="CONTINUE",
        rules_that_must_fire=["PPI_TKI_PH_SENSITIVE"], min_grade_a_rules=1),
)

CASE_21_LITHIUM_LOOP = ClinicalCase(
    case_id="C21_LITHIUM_LOOP_DIURETIC",
    description="58F, bipolar on lithium, started oral furosemide for edema (no GLP-1).",
    clinical_rationale=(
        "Loop diuretic volume contraction raises proximal tubular Li reabsorption → "
        "lithium toxicity. Fire LITHIUM_LOOP_DIURETIC_TOXICITY (Grade A); check level in 1w."
    ),
    sources=["FDA Lithium prescribing information", "Finley PR et al."],
    patient_input=_patient(
        patient_id="P-CASE-21", age_years=58, sex="female", glp1_agent="none",
        labs={"egfr_ml_min": 72},
        medications=[
            {"name": "Lithium carbonate 600 mg", "profile_id": "lithium_carbonate", "route": "oral", "is_essential": True},
            {"name": "Furosemide 40 mg", "profile_id": "furosemide_oral", "route": "oral"},
        ],
    ),
    expected=ExpectedOutcomes(triage_color="green", glp1_decision="CONTINUE",
        rules_that_must_fire=["LITHIUM_LOOP_DIURETIC_TOXICITY"], min_grade_a_rules=1),
)

CASE_22_INSULIN_SU_GLP1 = ClinicalCase(
    case_id="C22_SULFONYLUREA_GLP1_HYPO",
    description="60M, semaglutide week 14, glipizide for T2DM — additive hypoglycemia risk.",
    clinical_rationale=(
        "GLP-1 plus an insulin secretagogue amplifies hypoglycemia risk. Fire "
        "INSULIN_SU_GLP1_HYPOGLYCEMIA (Grade A); proactively reduce SU and intensify monitoring."
    ),
    sources=["FDA GLP-1 labels — hypoglycemia warnings with SU/insulin"],
    patient_input=_patient(
        patient_id="P-CASE-22", age_years=60, sex="male",
        glp1_agent="semaglutide_sc", glp1_weeks_since_start=14, glp1_weeks_since_last_dose_increase=10,
        labs={"egfr_ml_min": 80},
        medications=[
            {"name": "Glipizide 5 mg", "profile_id": "glipizide", "route": "oral"},
        ],
    ),
    expected=ExpectedOutcomes(triage_color="green", glp1_decision="CONTINUE",
        rules_that_must_fire=["INSULIN_SU_GLP1_HYPOGLYCEMIA"], min_grade_a_rules=1),
)

CASE_23_QT_COMBO = ClinicalCase(
    case_id="C23_QT_PROLONGATION_COMBO",
    description="70M, amiodarone + sotalol (two QT-prolonging antiarrhythmics).",
    clinical_rationale=(
        "Two concurrent QT-prolonging drugs give additive QT prolongation → torsades "
        "risk. Fire QT_PROLONGATION_COMBO (Grade A); baseline ECG, correct K/Mg."
    ),
    sources=["CredibleMeds QT lists", "AHA/ACC drug-induced QT statement"],
    patient_input=_patient(
        patient_id="P-CASE-23", age_years=70, sex="male", glp1_agent="none",
        labs={"egfr_ml_min": 68},
        medications=[
            {"name": "Amiodarone 200 mg", "profile_id": "amiodarone", "route": "oral", "is_essential": True},
            {"name": "Sotalol 80 mg bid", "profile_id": "sotalol", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(triage_color="green", glp1_decision="CONTINUE",
        rules_that_must_fire=["QT_PROLONGATION_COMBO"], min_grade_a_rules=1),
)

CASE_24_TACROLIMUS_CYP3A = ClinicalCase(
    case_id="C24_TACROLIMUS_INFECTION_CYP3A",
    description="48F kidney transplant on tacrolimus, presents with acute infection.",
    clinical_rationale=(
        "Cytokine-driven CYP3A suppression during infection (or a strong CYP3A inhibitor) "
        "raises tacrolimus exposure → nephro/neurotoxicity. Fire TACROLIMUS_CYP3A_PERTURBATION (A)."
    ),
    sources=["FDA Prograf label", "Brunet M et al. tacrolimus TDM consensus"],
    patient_input=_patient(
        patient_id="P-CASE-24", age_years=48, sex="female", glp1_agent="none",
        acute_infection=True, labs={"egfr_ml_min": 62, "crp_mg_l": 70},
        medications=[
            {"name": "Tacrolimus 2 mg bid", "profile_id": "tacrolimus", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(triage_color="green", glp1_decision="CONTINUE",
        rules_that_must_fire=["TACROLIMUS_CYP3A_PERTURBATION"], min_grade_a_rules=1),
)

CASE_25_PHENYTOIN_HYPOALB = ClinicalCase(
    case_id="C25_PHENYTOIN_HYPOALBUMINEMIA",
    description="55M on phenytoin with albumin 3.2 g/dL — free fraction rises.",
    clinical_rationale=(
        "Phenytoin is ~90% albumin-bound with saturable kinetics; low albumin raises free "
        "phenytoin while total looks reassuring. Fire PHENYTOIN_HYPOALBUMINEMIA (A); measure free level."
    ),
    sources=["FDA Dilantin prescribing information", "Patsalos PN et al."],
    patient_input=_patient(
        patient_id="P-CASE-25", age_years=55, sex="male", glp1_agent="none",
        labs={"egfr_ml_min": 75, "albumin_g_dl": 3.2},
        medications=[
            {"name": "Phenytoin 100 mg tid", "profile_id": "phenytoin", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(triage_color="green", glp1_decision="CONTINUE",
        rules_that_must_fire=["PHENYTOIN_HYPOALBUMINEMIA"], min_grade_a_rules=1),
)

CASE_26_VALPROATE_HYPOALB = ClinicalCase(
    case_id="C26_VALPROATE_HYPOALBUMINEMIA",
    description="62F on valproate with albumin 3.2 g/dL.",
    clinical_rationale=(
        "Valproate is highly albumin-bound; low albumin raises free fraction, total may "
        "underestimate exposure. Fire VALPROATE_HYPOALBUMINEMIA (Grade B)."
    ),
    sources=["FDA Depakote prescribing information"],
    patient_input=_patient(
        patient_id="P-CASE-26", age_years=62, sex="female", glp1_agent="none",
        labs={"egfr_ml_min": 70, "albumin_g_dl": 3.2},
        medications=[
            {"name": "Valproate 500 mg bid", "profile_id": "valproate_sodium", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(triage_color="green", glp1_decision="CONTINUE",
        rules_that_must_fire=["VALPROATE_HYPOALBUMINEMIA"]),
)

CASE_27_MMF_SEQUESTRANT = ClinicalCase(
    case_id="C27_MMF_BILE_SEQUESTRANT",
    description="40M transplant on mycophenolate mofetil + bile acid sequestrant.",
    clinical_rationale=(
        "MPA relies on enterohepatic recirculation; a bile acid sequestrant interrupts the "
        "loop → reduced AUC → under-immunosuppression. Fire MMF_BILE_SEQUESTRANT (Grade B)."
    ),
    sources=["FDA CellCept prescribing information"],
    patient_input=_patient(
        patient_id="P-CASE-27", age_years=40, sex="male", glp1_agent="none",
        bile_acid_sequestrants=True, labs={"egfr_ml_min": 66},
        medications=[
            {"name": "Mycophenolate mofetil 1 g bid", "profile_id": "mycophenolate_mofetil", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(triage_color="green", glp1_decision="CONTINUE",
        rules_that_must_fire=["MMF_BILE_SEQUESTRANT"]),
)

CASE_28_CARBAMAZEPINE_INDUCER = ClinicalCase(
    case_id="C28_CARBAMAZEPINE_CYP3A_INDUCER",
    description="66M on apixaban who is also taking carbamazepine (strong CYP3A inducer).",
    clinical_rationale=(
        "Carbamazepine strongly induces CYP3A → accelerated DOAC clearance → subtherapeutic "
        "anticoagulation and thrombosis risk. Fire CARBAMAZEPINE_CYP3A_INDUCER (Grade A) on the DOAC."
    ),
    sources=["FDA Tegretol prescribing information — DDI section"],
    patient_input=_patient(
        patient_id="P-CASE-28", age_years=66, sex="male", glp1_agent="none",
        labs={"egfr_ml_min": 80},
        medications=[
            {"name": "Apixaban 5 mg bid", "profile_id": "apixaban", "route": "oral", "is_essential": True},
            {"name": "Carbamazepine 200 mg bid", "profile_id": "carbamazepine", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(triage_color="green", glp1_decision="CONTINUE",
        rules_that_must_fire=["CARBAMAZEPINE_CYP3A_INDUCER"], min_grade_a_rules=1),
)

CASE_29_CLOZAPINE_INFLAMMATION = ClinicalCase(
    case_id="C29_CLOZAPINE_INFLAMMATION",
    description="45M on clozapine, presents with acute infection (CRP 80).",
    clinical_rationale=(
        "Inflammation suppresses CYP1A2 → clozapine levels can double within days → "
        "sedation, seizures, ileus. Fire CLOZAPINE_INFLAMMATION_TOXICITY (Grade B); check level now."
    ),
    sources=["Ruan CJ et al.", "de Leon J et al."],
    patient_input=_patient(
        patient_id="P-CASE-29", age_years=45, sex="male", glp1_agent="none",
        acute_infection=True, labs={"egfr_ml_min": 85, "crp_mg_l": 80},
        medications=[
            {"name": "Clozapine 300 mg", "profile_id": "clozapine", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(triage_color="green", glp1_decision="CONTINUE",
        rules_that_must_fire=["CLOZAPINE_INFLAMMATION_TOXICITY"]),
)

CASE_30_LAMOTRIGINE_OC = ClinicalCase(
    case_id="C30_LAMOTRIGINE_OC_CLEARANCE",
    description="29F on lamotrigine who starts a combined oral contraceptive.",
    clinical_rationale=(
        "Estrogen induces UGT1A4 → lamotrigine clearance rises ~50%, with rebound in the "
        "pill-free week → breakthrough seizures. Fire LAMOTRIGINE_OC_CLEARANCE (Grade A)."
    ),
    sources=["FDA Lamictal prescribing information", "Sabers A et al."],
    patient_input=_patient(
        patient_id="P-CASE-30", age_years=29, sex="female", glp1_agent="none",
        labs={"egfr_ml_min": 95},
        medications=[
            {"name": "Lamotrigine 200 mg", "profile_id": "lamotrigine", "route": "oral", "is_essential": True},
            {"name": "Combined OC", "profile_id": "combined_oral_contraceptive", "route": "oral"},
        ],
    ),
    expected=ExpectedOutcomes(triage_color="green", glp1_decision="CONTINUE",
        rules_that_must_fire=["LAMOTRIGINE_OC_CLEARANCE"], min_grade_a_rules=1),
)

CASE_31_BARIATRIC_MR = ClinicalCase(
    case_id="C31_BARIATRIC_MODIFIED_RELEASE",
    description="44F, 3 months post-RYGB, on metoprolol succinate ER (no GLP-1).",
    clinical_rationale=(
        "Altered transit after bariatric surgery degrades the tuned ER release profile → "
        "erratic levels. Fire BARIATRIC_MODIFIED_RELEASE (Grade B); switch to IR/alternative."
    ),
    sources=["Yska JP et al. PK post-bariatric review"],
    patient_input=_patient(
        patient_id="P-CASE-31", age_years=44, sex="female", glp1_agent="none",
        bariatric_type="RYGB", months_since_bariatric=3, labs={"egfr_ml_min": 88},
        medications=[
            {"name": "Metoprolol succinate 50 mg", "profile_id": "metoprolol_succinate", "route": "oral"},
        ],
    ),
    expected=ExpectedOutcomes(triage_color="green", glp1_decision="CONTINUE",
        rules_that_must_fire=["BARIATRIC_MODIFIED_RELEASE"]),
)

CASE_32_GLP1_ANTIHYPERTENSIVE = ClinicalCase(
    case_id="C32_GLP1_ANTIHYPERTENSIVE_TAPER",
    description="59M, semaglutide week 12, metoprolol succinate — anticipate BP fall.",
    clinical_rationale=(
        "Sustained GLP-1 weight loss lowers BP by week 8–12; without proactive antihypertensive "
        "taper, orthostatic hypotension and falls follow. Fire GLP1_WEIGHT_LOSS_ANTIHYPERTENSIVE_TAPER (B)."
    ),
    sources=["FDA Wegovy / Mounjaro / Zepbound labels — BP reduction"],
    patient_input=_patient(
        patient_id="P-CASE-32", age_years=59, sex="male",
        glp1_agent="semaglutide_sc", glp1_weeks_since_start=12, glp1_weeks_since_last_dose_increase=8,
        labs={"egfr_ml_min": 82},
        medications=[
            {"name": "Metoprolol succinate 100 mg", "profile_id": "metoprolol_succinate", "route": "oral"},
        ],
    ),
    expected=ExpectedOutcomes(triage_color="green", glp1_decision="CONTINUE",
        rules_that_must_fire=["GLP1_WEIGHT_LOSS_ANTIHYPERTENSIVE_TAPER"]),
)

CASE_33_PSYCHOTROPIC_TMAX = ClinicalCase(
    case_id="C33_PSYCHOTROPIC_TMAX",
    description="53F, semaglutide week 16, repaglinide (rapid meglitinide) — Tmax shift.",
    clinical_rationale=(
        "GLP-1 gastric-emptying delay right-shifts Tmax of rapid-action agents → uneven "
        "plasma profile and postprandial hypoglycemia. Fire PSYCHOTROPIC_GASTROPARESIS_TMAX (Grade C)."
    ),
    sources=["FDA GLP-1 labels — gastric emptying", "Camilleri M"],
    patient_input=_patient(
        patient_id="P-CASE-33", age_years=53, sex="female",
        glp1_agent="semaglutide_sc", glp1_weeks_since_start=16, glp1_weeks_since_last_dose_increase=12,
        labs={"egfr_ml_min": 84},
        medications=[
            {"name": "Repaglinide 1 mg", "profile_id": "repaglinide", "route": "oral"},
        ],
    ),
    expected=ExpectedOutcomes(triage_color="green", glp1_decision="CONTINUE",
        rules_that_must_fire=["PSYCHOTROPIC_GASTROPARESIS_TMAX"]),
)

CASE_34_SHORT_BOWEL_BILE = ClinicalCase(
    case_id="C34_SHORT_BOWEL_BILE_DEPENDENT",
    description="50M with short bowel syndrome on cyclosporine (bile-dependent).",
    clinical_rationale=(
        "Short bowel reduces the bile acid pool and ileal reabsorption; bile-dependent "
        "lipophilic drugs absorb erratically. Fire SHORT_BOWEL_BILE_DEPENDENT (Grade B)."
    ),
    sources=["Mendes-Braz M et al.", "Brunet M et al."],
    patient_input=_patient(
        patient_id="P-CASE-34", age_years=50, sex="male", glp1_agent="none",
        short_bowel=True, labs={"egfr_ml_min": 70},
        medications=[
            {"name": "Cyclosporine 100 mg bid", "profile_id": "cyclosporine", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(triage_color="green", glp1_decision="CONTINUE",
        rules_that_must_fire=["SHORT_BOWEL_BILE_DEPENDENT"]),
)

CASE_35_BARIATRIC_NTI = ClinicalCase(
    case_id="C35_BARIATRIC_PROTEIN_BINDING_NTI",
    description="46F, 8 months post-RYGB, on warfarin (high protein binding + NTI).",
    clinical_rationale=(
        "Post-bariatric malabsorption + altered transit destabilize narrow-TI highly "
        "protein-bound drugs — variance is high even before symptoms. Fire BARIATRIC_PROTEIN_BINDING_NTI (C)."
    ),
    sources=["Yska JP et al.", "ISTH 2021 anticoagulation post-bariatric"],
    patient_input=_patient(
        patient_id="P-CASE-35", age_years=46, sex="female", glp1_agent="none",
        bariatric_type="RYGB", months_since_bariatric=8, labs={"egfr_ml_min": 86, "albumin_g_dl": 3.8, "inr": 2.4},
        medications=[
            {"name": "Warfarin 5 mg", "profile_id": "warfarin", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(triage_color="green", glp1_decision="CONTINUE",
        rules_that_must_fire=["BARIATRIC_PROTEIN_BINDING_NTI"]),
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
    CASE_16_TETRACYCLINE_CATION,
    CASE_17_DIGOXIN_LOW_EGFR,
    CASE_18_GLP1_TMAX_SENSITIVE,
    CASE_19_POSACONAZOLE_PPI,
    CASE_20_PPI_TKI,
    CASE_21_LITHIUM_LOOP,
    CASE_22_INSULIN_SU_GLP1,
    CASE_23_QT_COMBO,
    CASE_24_TACROLIMUS_CYP3A,
    CASE_25_PHENYTOIN_HYPOALB,
    CASE_26_VALPROATE_HYPOALB,
    CASE_27_MMF_SEQUESTRANT,
    CASE_28_CARBAMAZEPINE_INDUCER,
    CASE_29_CLOZAPINE_INFLAMMATION,
    CASE_30_LAMOTRIGINE_OC,
    CASE_31_BARIATRIC_MR,
    CASE_32_GLP1_ANTIHYPERTENSIVE,
    CASE_33_PSYCHOTROPIC_TMAX,
    CASE_34_SHORT_BOWEL_BILE,
    CASE_35_BARIATRIC_NTI,
]
