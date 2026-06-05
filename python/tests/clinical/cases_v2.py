"""
METACOD GLP-1 module — clinical validation case library v2.

Extends cases.py (v1) with cases covering rule_pack_v2 new rules + v1 coverage gaps.

Structure (additive to v1):
  CASE_V2_01 .. CASE_V2_16  — one positive case per new rule
  CASE_V2_17 .. CASE_V2_19  — closes v1 coverage gaps (DIGOXIN, TETRACYCLINE, GLP1_TMAX)
  CASE_V2_20 .. CASE_V2_22  — multi-rule stress (oncology, transplant, bipolar)
  CASE_V2_23 .. CASE_V2_25  — boundary edge cases (must NOT fire just-below-threshold)

Each case carries clinical_rationale and sources, runs through the same SaMD
driver as v1. Failures here block rule_pack v2.x releases.
"""

from __future__ import annotations

from tests.clinical.cases import ClinicalCase, ExpectedOutcomes, _patient


# ============================================================================
# 16 new-rule positive cases
# ============================================================================

CASE_V2_01_PPI_TKI = ClinicalCase(
    case_id="C_V2_01_PPI_TKI_ERLOTINIB",
    description="65M lung cancer on erlotinib + omeprazole for reflux — PPI tanks TKI absorption.",
    clinical_rationale=(
        "Erlotinib requires gastric pH < 4 for adequate dissolution. PPI raises pH > 5, "
        "AUC drops 30–60%, threatening therapy efficacy. PPI_TKI_PH_SENSITIVE must fire."
    ),
    sources=["FDA Tarceva label", "Hilberg O et al."],
    patient_input=_patient(
        patient_id="P-V2-01", age_years=65, sex="male", weight_kg=68,
        ppi_or_h2_blocker=True,
        labs={"egfr_ml_min": 78, "albumin_g_dl": 3.8},
        medications=[
            {"name": "Erlotinib 150 mg", "profile_id": "erlotinib", "route": "oral", "is_essential": True},
            {"name": "Omeprazole 20 mg", "profile_id": "omeprazole", "route": "oral", "is_essential": False},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["PPI_TKI_PH_SENSITIVE"],
        min_grade_a_rules=1,
    ),
)


CASE_V2_02_LITHIUM_LOOP = ClinicalCase(
    case_id="C_V2_02_LITHIUM_LOOP_DIURETIC",
    description="58F bipolar on lithium with new furosemide for ankle edema — toxicity risk.",
    clinical_rationale=(
        "Loop diuretic contracts volume → proximal tubule reabsorbs more Li → toxicity. "
        "LITHIUM_LOOP_DIURETIC_TOXICITY fires; dose reduction 25–50% and weekly level."
    ),
    sources=["FDA Lithium prescribing information", "Finley PR et al."],
    patient_input=_patient(
        patient_id="P-V2-02", age_years=58, sex="female", weight_kg=72,
        labs={"egfr_ml_min": 68, "albumin_g_dl": 4.0},
        medications=[
            {"name": "Lithium carbonate 600 mg", "profile_id": "lithium_carbonate", "route": "oral", "is_essential": True},
            {"name": "Furosemide 40 mg", "profile_id": "furosemide_oral", "route": "oral", "is_essential": False},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["LITHIUM_LOOP_DIURETIC_TOXICITY"],
        min_grade_a_rules=1,
    ),
)


CASE_V2_03_INSULIN_GLP1 = ClinicalCase(
    case_id="C_V2_03_INSULIN_GLP1_HYPOGLYCEMIA",
    description="62M T2DM on basal insulin starting semaglutide — proactive insulin dose reduction needed.",
    clinical_rationale=(
        "GLP-1 + insulin = additive glucose lowering. FDA label requires proactive "
        "insulin reduction (~20%). INSULIN_SU_GLP1_HYPOGLYCEMIA fires Grade A."
    ),
    sources=["FDA Ozempic / Wegovy labels — hypoglycemia warnings"],
    patient_input=_patient(
        patient_id="P-V2-03", age_years=62, sex="male", weight_kg=92,
        glp1_agent="semaglutide_sc", glp1_weeks_since_start=8, glp1_weeks_since_last_dose_increase=8,
        labs={"egfr_ml_min": 72},
        medications=[
            {"name": "Insulin glargine 30 U", "profile_id": "insulin_glargine", "route": "sc", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["INSULIN_SU_GLP1_HYPOGLYCEMIA"],
        min_grade_a_rules=1,
    ),
)


CASE_V2_04_QT_COMBO = ClinicalCase(
    case_id="C_V2_04_QT_PROLONGATION_COMBO",
    description="70F on amiodarone with new ciprofloxacin for UTI — additive QT.",
    clinical_rationale=(
        "Two QT-prolonging agents → additive QT prolongation, torsades risk especially "
        "with hypokalemia. QT_PROLONGATION_COMBO fires (≥2 QT meds in regimen)."
    ),
    sources=["CredibleMeds QT lists", "AHA/ACC scientific statement"],
    patient_input=_patient(
        patient_id="P-V2-04", age_years=70, sex="female", weight_kg=64,
        labs={"egfr_ml_min": 58, "albumin_g_dl": 3.9},
        medications=[
            {"name": "Amiodarone 200 mg", "profile_id": "amiodarone", "route": "oral", "is_essential": True},
            {"name": "Ciprofloxacin 500 mg", "profile_id": "ciprofloxacin", "route": "oral", "is_essential": False},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["QT_PROLONGATION_COMBO"],
        min_grade_a_rules=1,
    ),
)


CASE_V2_05_TACROLIMUS_AZOLE = ClinicalCase(
    case_id="C_V2_05_TACROLIMUS_CYP3A_PERTURBATION",
    description="45F kidney transplant on tacrolimus, started voriconazole for invasive aspergillosis.",
    clinical_rationale=(
        "Voriconazole is a strong CYP3A4 inhibitor; tacrolimus is a CYP3A substrate. "
        "Levels can quadruple in days → nephro/neurotoxicity. TACROLIMUS_CYP3A_PERTURBATION fires."
    ),
    sources=["FDA Prograf / Vfend labels", "Brunet M et al."],
    patient_input=_patient(
        patient_id="P-V2-05", age_years=45, sex="female", weight_kg=63,
        labs={"egfr_ml_min": 52, "albumin_g_dl": 3.7},
        medications=[
            {"name": "Tacrolimus 2 mg bid", "profile_id": "tacrolimus", "route": "oral", "is_essential": True},
            {"name": "Voriconazole 200 mg bid", "profile_id": "voriconazole", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["TACROLIMUS_CYP3A_PERTURBATION"],
        min_grade_a_rules=1,
    ),
)


CASE_V2_06_PHENYTOIN_LOW_ALB = ClinicalCase(
    case_id="C_V2_06_PHENYTOIN_HYPOALBUMINEMIA",
    description="48M cirrhosis on phenytoin for old seizures, albumin 2.9 — free fraction matters.",
    clinical_rationale=(
        "Phenytoin is 90% albumin-bound with saturable kinetics. At albumin 2.9, free "
        "fraction can be 2x normal → 'normal' total is actually toxic. Sheiner-Tozer correction needed."
    ),
    sources=["FDA Dilantin", "Patsalos PN et al."],
    patient_input=_patient(
        patient_id="P-V2-06", age_years=48, sex="male", weight_kg=70,
        child_pugh="B",
        labs={"egfr_ml_min": 68, "albumin_g_dl": 2.9, "alt_u_l": 80},
        medications=[
            {"name": "Phenytoin 300 mg", "profile_id": "phenytoin", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["PHENYTOIN_HYPOALBUMINEMIA", "HYPOALBUMINEMIA_HIGH_PROTEIN_BINDING"],
        min_grade_a_rules=1,
    ),
)


CASE_V2_07_VALPROATE_LOW_ALB = ClinicalCase(
    case_id="C_V2_07_VALPROATE_HYPOALBUMINEMIA",
    description="55F migraine prophylaxis on valproate, albumin 3.2 — modest free-fraction rise.",
    clinical_rationale="Valproate is 90% albumin-bound; low albumin → elevated free valproate.",
    sources=["FDA Depakote"],
    patient_input=_patient(
        patient_id="P-V2-07", age_years=55, sex="female", weight_kg=66,
        labs={"egfr_ml_min": 75, "albumin_g_dl": 3.2},
        medications=[
            {"name": "Valproate sodium 500 mg", "profile_id": "valproate_sodium", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["VALPROATE_HYPOALBUMINEMIA"],
    ),
)


CASE_V2_08_MMF_SEVELAMER = ClinicalCase(
    case_id="C_V2_08_MMF_BILE_SEQUESTRANT",
    description="42M renal transplant on MMF, started sevelamer for hyperphosphatemia.",
    clinical_rationale=(
        "Sevelamer is a bile-acid sequestrant; MMF undergoes enterohepatic recirculation. "
        "Sequestrant disrupts the loop → MPA AUC drops 30–40% → rejection risk."
    ),
    sources=["FDA CellCept label"],
    patient_input=_patient(
        patient_id="P-V2-08", age_years=42, sex="male", weight_kg=78,
        labs={"egfr_ml_min": 28, "albumin_g_dl": 3.6},
        medications=[
            {"name": "MMF 1g bid", "profile_id": "mycophenolate_mofetil", "route": "oral", "is_essential": True},
            {"name": "Sevelamer 800 mg tid", "profile_id": "sevelamer", "route": "oral", "is_essential": False},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["MMF_BILE_SEQUESTRANT"],
    ),
)


CASE_V2_09_CARBAMAZEPINE_APIXABAN = ClinicalCase(
    case_id="C_V2_09_CARBAMAZEPINE_CYP3A_INDUCER",
    description="60F AFib on apixaban started carbamazepine for trigeminal neuralgia.",
    clinical_rationale=(
        "Carbamazepine is a strong CYP3A4 inducer. Apixaban is a CYP3A substrate. "
        "Induction → subtherapeutic apixaban → stroke risk."
    ),
    sources=["FDA Tegretol label — DDI section"],
    patient_input=_patient(
        patient_id="P-V2-09", age_years=60, sex="female", weight_kg=74,
        labs={"egfr_ml_min": 62, "albumin_g_dl": 4.0},
        medications=[
            {"name": "Apixaban 5 mg bid", "profile_id": "apixaban", "route": "oral", "is_essential": True},
            {"name": "Carbamazepine 200 mg", "profile_id": "carbamazepine", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["CARBAMAZEPINE_CYP3A_INDUCER"],
        min_grade_a_rules=1,
    ),
)


CASE_V2_10_CLOZAPINE_INFECTION = ClinicalCase(
    case_id="C_V2_10_CLOZAPINE_INFLAMMATION_TOXICITY",
    description="38M schizophrenia on clozapine, acute pneumonia + CRP 95 — level may double in days.",
    clinical_rationale=(
        "Cytokines suppress CYP1A2; clozapine level can double in 3–5 days during acute "
        "inflammation → sedation, hypotension, seizures, ileus."
    ),
    sources=["Ruan CJ et al. clozapine inflammation"],
    patient_input=_patient(
        patient_id="P-V2-10", age_years=38, sex="male", weight_kg=85,
        acute_infection=True, systemic_inflammation="moderate",
        labs={"egfr_ml_min": 88, "crp_mg_l": 95, "albumin_g_dl": 3.4},
        medications=[
            {"name": "Clozapine 300 mg", "profile_id": "clozapine", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["CLOZAPINE_INFLAMMATION_TOXICITY", "INFLAMMATION_CYP_SUBSTRATE"],
    ),
)


CASE_V2_11_LAMOTRIGINE_OC = ClinicalCase(
    case_id="C_V2_11_LAMOTRIGINE_OC_CLEARANCE",
    description="28F epilepsy on lamotrigine starting combined oral contraceptive.",
    clinical_rationale=(
        "Estrogen induces UGT1A4 → lamotrigine clearance up ~50%. Risk of breakthrough "
        "seizures on active OC days, rebound in pill-free week."
    ),
    sources=["FDA Lamictal label", "Sabers A et al."],
    patient_input=_patient(
        patient_id="P-V2-11", age_years=28, sex="female", weight_kg=58,
        labs={"egfr_ml_min": 92, "albumin_g_dl": 4.2},
        medications=[
            {"name": "Lamotrigine 200 mg", "profile_id": "lamotrigine", "route": "oral", "is_essential": True},
            {"name": "COC ethinyl/levonorgestrel", "profile_id": "combined_oral_contraceptive", "route": "oral", "is_essential": False},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["LAMOTRIGINE_OC_CLEARANCE"],
        min_grade_a_rules=1,
    ),
)


CASE_V2_12_BARIATRIC_MR = ClinicalCase(
    case_id="C_V2_12_BARIATRIC_MODIFIED_RELEASE",
    description="44F 3 months post-gastric-bypass on metoprolol succinate ER for hypertension.",
    clinical_rationale=(
        "ER formulations rely on precisely tuned transit time and absorptive surface — "
        "both altered post-bariatric. Release profile becomes erratic in first 6 months."
    ),
    sources=["Yska JP et al."],
    patient_input=_patient(
        patient_id="P-V2-12", age_years=44, sex="female", weight_kg=85,
        bariatric_type="RYGB", months_since_bariatric=3,
        labs={"egfr_ml_min": 80},
        medications=[
            {"name": "Metoprolol succinate ER 50 mg", "profile_id": "metoprolol_succinate", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["BARIATRIC_MODIFIED_RELEASE"],
    ),
)


CASE_V2_13_ANTIHYPERTENSIVE_TAPER = ClinicalCase(
    case_id="C_V2_13_GLP1_ANTIHYPERTENSIVE_TAPER",
    description="56M tirzepatide week 14, on metoprolol — sustained weight loss, BP likely dropping.",
    clinical_rationale=(
        "GLP-1 weight loss drops BP 5–10 mmHg systolic by week 8–12. Without proactive "
        "antihypertensive taper, orthostasis becomes common."
    ),
    sources=["FDA Mounjaro / Wegovy labels"],
    patient_input=_patient(
        patient_id="P-V2-13", age_years=56, sex="male", weight_kg=92,
        glp1_agent="tirzepatide_sc", glp1_weeks_since_start=14, glp1_weeks_since_last_dose_increase=4,
        labs={"egfr_ml_min": 70, "albumin_g_dl": 4.0},
        medications=[
            {"name": "Metoprolol tartrate 50 mg bid", "profile_id": "metoprolol_succinate", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["GLP1_WEIGHT_LOSS_ANTIHYPERTENSIVE_TAPER"],
    ),
)


CASE_V2_14_PSYCHOTROPIC_TMAX = ClinicalCase(
    case_id="C_V2_14_PSYCHOTROPIC_GASTROPARESIS_TMAX",
    description="55F T2DM on prandial repaglinide started tirzepatide for obesity — Tmax shifts.",
    clinical_rationale=(
        "Repaglinide is meglitinide class with strict Tmax timing (must align with meal). "
        "Tirzepatide-induced gastroparesis shifts Tmax unpredictably → erratic glycemic response."
    ),
    sources=["FDA Prandin label", "Camilleri M"],
    patient_input=_patient(
        patient_id="P-V2-14", age_years=55, sex="female", weight_kg=88,
        glp1_agent="tirzepatide_sc", glp1_weeks_since_start=6, glp1_weeks_since_last_dose_increase=6,
        labs={"egfr_ml_min": 82, "albumin_g_dl": 4.0},
        medications=[
            {"name": "Repaglinide 1 mg with meals", "profile_id": "repaglinide", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["PSYCHOTROPIC_GASTROPARESIS_TMAX", "INSULIN_SU_GLP1_HYPOGLYCEMIA"],
        min_grade_a_rules=1,
    ),
)


CASE_V2_15_SHORT_BOWEL_TACROLIMUS = ClinicalCase(
    case_id="C_V2_15_SHORT_BOWEL_BILE_DEPENDENT",
    description="36F intestinal transplant + tacrolimus + short bowel syndrome.",
    clinical_rationale=(
        "Short bowel reduces bile-acid pool; tacrolimus needs bile for solubilization. "
        "Absorption becomes erratic and reduced."
    ),
    sources=["Mendes-Braz M et al."],
    patient_input=_patient(
        patient_id="P-V2-15", age_years=36, sex="female", weight_kg=54,
        short_bowel=True,
        labs={"egfr_ml_min": 58, "albumin_g_dl": 3.5},
        medications=[
            {"name": "Tacrolimus 1 mg bid", "profile_id": "tacrolimus", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["SHORT_BOWEL_BILE_DEPENDENT"],
    ),
)


CASE_V2_16_BARIATRIC_NTI = ClinicalCase(
    case_id="C_V2_16_BARIATRIC_PROTEIN_BINDING_NTI",
    description="48F 9 months post-sleeve gastrectomy on warfarin (NTI, high protein binding).",
    clinical_rationale=(
        "Warfarin: NTI + 99% protein-bound + heavy CYP metabolism. Post-bariatric malabsorption "
        "and altered transit destabilize PK; intensify monitoring in first 12 months."
    ),
    sources=["Yska JP et al.", "ISTH 2021 anticoagulation post-bariatric"],
    patient_input=_patient(
        patient_id="P-V2-16", age_years=48, sex="female", weight_kg=72,
        bariatric_type="sleeve", months_since_bariatric=9,
        labs={"egfr_ml_min": 75, "albumin_g_dl": 3.8, "inr": 2.6},
        medications=[
            {"name": "Warfarin 5 mg", "profile_id": "warfarin", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["BARIATRIC_PROTEIN_BINDING_NTI"],
    ),
)


# ============================================================================
# 3 v1-gap closure cases
# ============================================================================

CASE_V2_17_DIGOXIN_LOW_EGFR = ClinicalCase(
    case_id="C_V2_17_EGFR_LOW_DIGOXIN",
    description="75F CHF on digoxin with newly worsened eGFR 35 — accumulation risk.",
    clinical_rationale="Digoxin is renally cleared NTI; eGFR <50 → predictable accumulation.",
    sources=["FDA Digoxin label"],
    patient_input=_patient(
        patient_id="P-V2-17", age_years=75, sex="female", weight_kg=60,
        labs={"egfr_ml_min": 35, "creatinine_mg_dl": 1.7, "albumin_g_dl": 3.6},
        medications=[
            {"name": "Digoxin 0.125 mg", "profile_id": "digoxin", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["EGFR_LOW_DIGOXIN"],
        min_grade_a_rules=1,
    ),
)


CASE_V2_18_DOXYCYCLINE_CATION = ClinicalCase(
    case_id="C_V2_18_CATION_CHELATION_TETRACYCLINE",
    description="50M on doxycycline for chlamydia, also taking calcium carbonate supplements.",
    clinical_rationale="Tetracycline chelation with multivalent cations → absorption failure.",
    sources=["FDA Doxycycline label"],
    patient_input=_patient(
        patient_id="P-V2-18", age_years=50, sex="male", weight_kg=80,
        calcium_iron_magnesium_aluminum_products=True,
        labs={"egfr_ml_min": 85},
        medications=[
            {"name": "Doxycycline 100 mg bid", "profile_id": "doxycycline", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["CATION_CHELATION_TETRACYCLINE"],
        min_grade_a_rules=1,
    ),
)


CASE_V2_19_GLP1_TMAX_FUROSEMIDE = ClinicalCase(
    case_id="C_V2_19_GLP1_GASTROPARESIS_TMAX_SENSITIVE",
    description="68F CHF on oral furosemide + new semaglutide for obesity — Tmax shifts.",
    clinical_rationale=(
        "Furosemide is tmax_sensitive (rapid peak diuresis). GLP-1 gastroparesis delays "
        "Tmax → unpredictable diuretic peak."
    ),
    sources=["FDA Ozempic label"],
    patient_input=_patient(
        patient_id="P-V2-19", age_years=68, sex="female", weight_kg=85,
        glp1_agent="semaglutide_sc", glp1_weeks_since_start=10, glp1_weeks_since_last_dose_increase=6,
        labs={"egfr_ml_min": 55, "albumin_g_dl": 3.8},
        medications=[
            {"name": "Furosemide 40 mg", "profile_id": "furosemide_oral", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["GLP1_GASTROPARESIS_TMAX_SENSITIVE"],
    ),
)


# ============================================================================
# 3 multi-rule stress cases
# ============================================================================

CASE_V2_20_ONCOLOGY_STACK = ClinicalCase(
    case_id="C_V2_20_ONCOLOGY_TKI_PPI_QT",
    description="65F renal cell carcinoma on pazopanib + omeprazole for reflux + ondansetron-driven QT — multi-rule.",
    clinical_rationale=(
        "Pazopanib (TKI requires acidic pH, QT-prolonging) + PPI + amiodarone for AFib. "
        "Expect PPI_TKI_PH_SENSITIVE + QT_PROLONGATION_COMBO."
    ),
    sources=["FDA Votrient label", "FDA Cordarone label"],
    patient_input=_patient(
        patient_id="P-V2-20", age_years=65, sex="female", weight_kg=68,
        ppi_or_h2_blocker=True,
        labs={"egfr_ml_min": 60, "albumin_g_dl": 3.7},
        medications=[
            {"name": "Pazopanib 800 mg", "profile_id": "pazopanib", "route": "oral", "is_essential": True},
            {"name": "Omeprazole 40 mg", "profile_id": "omeprazole", "route": "oral", "is_essential": False},
            {"name": "Amiodarone 200 mg", "profile_id": "amiodarone", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["PPI_TKI_PH_SENSITIVE", "QT_PROLONGATION_COMBO"],
        min_grade_a_rules=2,
    ),
)


CASE_V2_21_TRANSPLANT_STACK = ClinicalCase(
    case_id="C_V2_21_TRANSPLANT_CNI_AZOLE_INFLAMMATION",
    description="50M kidney transplant on tacrolimus + posaconazole + acute sepsis CRP 120.",
    clinical_rationale=(
        "Three independent CYP3A perturbations stack: strong inhibitor (posaconazole) + "
        "cytokine suppression (sepsis). Tacrolimus needs urgent TDM."
    ),
    sources=["Brunet M et al.", "FDA Prograf / Noxafil"],
    patient_input=_patient(
        patient_id="P-V2-21", age_years=50, sex="male", weight_kg=75,
        acute_infection=True, systemic_inflammation="severe",
        ppi_or_h2_blocker=False,
        labs={"egfr_ml_min": 45, "crp_mg_l": 120, "albumin_g_dl": 3.0, "alt_u_l": 75},
        medications=[
            {"name": "Tacrolimus 2 mg bid", "profile_id": "tacrolimus", "route": "oral", "is_essential": True},
            {"name": "Posaconazole suspension 200 mg tid", "profile_id": "posaconazole_oral_suspension", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_fire=["TACROLIMUS_CYP3A_PERTURBATION", "INFLAMMATION_CYP_SUBSTRATE"],
        min_grade_a_rules=1,
    ),
)


CASE_V2_22_BIPOLAR_GLP1 = ClinicalCase(
    case_id="C_V2_22_BIPOLAR_GLP1_POLYPHARMACY",
    description="38F bipolar on lithium + lamotrigine + COC, new furosemide + tirzepatide, early intolerance.",
    clinical_rationale=(
        "Lithium + loop diuretic toxicity. Lamotrigine + OC clearance. Tirzepatide week 1 escalation "
        "with mild nausea + early satiety → glp1_recent + symptoms triggers yellow."
    ),
    sources=["FDA Lithium", "FDA Lamictal", "FDA Mounjaro"],
    patient_input=_patient(
        patient_id="P-V2-22", age_years=38, sex="female", weight_kg=92,
        glp1_agent="tirzepatide_sc", glp1_weeks_since_start=1, glp1_weeks_since_last_dose_increase=1,
        symptoms={
            "nausea_score": 3,
            "vomiting_episodes_24h": 0,
            "abdominal_pain_score": 0,
            "bloating_score": 1,
            "early_satiety": True,
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
        labs={"egfr_ml_min": 70, "albumin_g_dl": 3.9},
        medications=[
            {"name": "Lithium carbonate 600 mg", "profile_id": "lithium_carbonate", "route": "oral", "is_essential": True},
            {"name": "Lamotrigine 200 mg", "profile_id": "lamotrigine", "route": "oral", "is_essential": True},
            {"name": "COC", "profile_id": "combined_oral_contraceptive", "route": "oral", "is_essential": False},
            {"name": "Furosemide 20 mg", "profile_id": "furosemide_oral", "route": "oral", "is_essential": False},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="yellow",
        glp1_decision="REVIEW",
        rules_that_must_fire=[
            "LITHIUM_LOOP_DIURETIC_TOXICITY",
            "LAMOTRIGINE_OC_CLEARANCE",
            "GLP1_TIRZEPATIDE_OC_EARLY",
        ],
        min_grade_a_rules=2,
    ),
)


# ============================================================================
# 3 edge / boundary negative cases
# ============================================================================

CASE_V2_23_BARIATRIC_EDGE_6MO = ClinicalCase(
    case_id="C_V2_23_BARIATRIC_MR_BOUNDARY_6MO",
    description="Boundary: months_since_bariatric == 6 (rule wants strict <6) — MR rule must NOT fire.",
    clinical_rationale=(
        "Rule condition is months_since_bariatric < 6. At exactly 6 months, "
        "BARIATRIC_MODIFIED_RELEASE must NOT fire — the post-op window has just closed."
    ),
    sources=["BARIATRIC_MODIFIED_RELEASE rule definition"],
    patient_input=_patient(
        patient_id="P-V2-23", age_years=44, sex="female", weight_kg=78,
        bariatric_type="RYGB", months_since_bariatric=6,
        labs={"egfr_ml_min": 80},
        medications=[
            {"name": "Metoprolol succinate ER 50 mg", "profile_id": "metoprolol_succinate", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_not_fire=["BARIATRIC_MODIFIED_RELEASE"],
    ),
)


CASE_V2_24_ALBUMIN_EDGE = ClinicalCase(
    case_id="C_V2_24_PHENYTOIN_ALBUMIN_BOUNDARY_3.5",
    description="Boundary: albumin == 3.5 — phenytoin hypoalbuminemia rule wants strict <3.5, must NOT fire.",
    clinical_rationale=(
        "Rule condition albumin_g_dl < 3.5. At exactly 3.5, no rule fires. "
        "Test boundary semantics — at 3.4 we expect fire (separate case)."
    ),
    sources=["PHENYTOIN_HYPOALBUMINEMIA rule definition"],
    patient_input=_patient(
        patient_id="P-V2-24", age_years=50, sex="male", weight_kg=75,
        labs={"egfr_ml_min": 75, "albumin_g_dl": 3.5},
        medications=[
            {"name": "Phenytoin 300 mg", "profile_id": "phenytoin", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_not_fire=["PHENYTOIN_HYPOALBUMINEMIA", "HYPOALBUMINEMIA_HIGH_PROTEIN_BINDING"],
    ),
)


CASE_V2_25_QT_SINGLE = ClinicalCase(
    case_id="C_V2_25_QT_SINGLE_DRUG_NEGATIVE",
    description="Single QT-prolonging drug (just amiodarone) — combo rule needs ≥2 to fire.",
    clinical_rationale=(
        "QT_PROLONGATION_COMBO requires qt_prolonging_med_count >= 2. With only amiodarone, "
        "it must NOT fire."
    ),
    sources=["QT_PROLONGATION_COMBO rule definition"],
    patient_input=_patient(
        patient_id="P-V2-25", age_years=70, sex="male", weight_kg=80,
        labs={"egfr_ml_min": 65, "albumin_g_dl": 3.8},
        medications=[
            {"name": "Amiodarone 200 mg", "profile_id": "amiodarone", "route": "oral", "is_essential": True},
        ],
    ),
    expected=ExpectedOutcomes(
        triage_color="green",
        glp1_decision="CONTINUE",
        rules_that_must_not_fire=["QT_PROLONGATION_COMBO"],
    ),
)


# ============================================================================
# Export
# ============================================================================

ALL_CASES_V2: list[ClinicalCase] = [
    CASE_V2_01_PPI_TKI,
    CASE_V2_02_LITHIUM_LOOP,
    CASE_V2_03_INSULIN_GLP1,
    CASE_V2_04_QT_COMBO,
    CASE_V2_05_TACROLIMUS_AZOLE,
    CASE_V2_06_PHENYTOIN_LOW_ALB,
    CASE_V2_07_VALPROATE_LOW_ALB,
    CASE_V2_08_MMF_SEVELAMER,
    CASE_V2_09_CARBAMAZEPINE_APIXABAN,
    CASE_V2_10_CLOZAPINE_INFECTION,
    CASE_V2_11_LAMOTRIGINE_OC,
    CASE_V2_12_BARIATRIC_MR,
    CASE_V2_13_ANTIHYPERTENSIVE_TAPER,
    CASE_V2_14_PSYCHOTROPIC_TMAX,
    CASE_V2_15_SHORT_BOWEL_TACROLIMUS,
    CASE_V2_16_BARIATRIC_NTI,
    CASE_V2_17_DIGOXIN_LOW_EGFR,
    CASE_V2_18_DOXYCYCLINE_CATION,
    CASE_V2_19_GLP1_TMAX_FUROSEMIDE,
    CASE_V2_20_ONCOLOGY_STACK,
    CASE_V2_21_TRANSPLANT_STACK,
    CASE_V2_22_BIPOLAR_GLP1,
    CASE_V2_23_BARIATRIC_EDGE_6MO,
    CASE_V2_24_ALBUMIN_EDGE,
    CASE_V2_25_QT_SINGLE,
]
