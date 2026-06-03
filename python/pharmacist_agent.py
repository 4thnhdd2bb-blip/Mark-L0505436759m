"""
METACOD GLP-1 Complication Prevention — Pharmacist Agent v2.1

Refactored from Gemini prototype, extended in v2.1 to support drug-drug rule
conditions through a derived `med_summary` context plus DSL `contains` and
`any_in` operators. Backward compatible with v1 rule_pack.

Responsibilities:
  - Evaluates drug-patient interactions against the rule_pack
  - Triages patient state (green / yellow / red)
  - Generates clinical forecasts (DOSE HOLD logic, future risks, chronic med adjustments)
  - Returns i18n-keyed outputs with evidence grading and mechanism traces (dual-layer)

Design principles:
  - No hardcoded clinical strings — every user-facing string is an i18n key
  - No autonomous prescribing — every output is a recommendation requiring physician
    sign-off (METACOD White Coat Rule)
  - Safe DSL evaluation (no eval/exec) — structured conditions only
  - Pydantic models throughout for type safety and FastAPI compatibility
  - Deterministic for the same input — supports audit logging and SaMD compliance

Author: METACOD team
License: proprietary
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================

class EvidenceGrade(str, Enum):
    A = "A"  # Regulatory label or RCT
    B = "B"  # Multiple observational + mechanistic
    C = "C"  # Mechanistic / expert consensus only


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class TriageColor(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class GLP1Decision(str, Enum):
    CONTINUE = "CONTINUE"
    HOLD = "HOLD"
    REVIEW = "REVIEW"


# ============================================================================
# Input models
# ============================================================================

class MedicationInput(BaseModel):
    name: str
    profile_id: str
    route: str = "oral"
    dose: Optional[str] = None
    is_essential: bool = False


class GISymptoms(BaseModel):
    nausea_score: int = Field(0, ge=0, le=10)
    vomiting_episodes_24h: int = Field(0, ge=0)
    abdominal_pain_score: int = Field(0, ge=0, le=10)
    bloating_score: int = Field(0, ge=0, le=10)
    early_satiety: bool = False
    constipation_days_without_stool: int = Field(0, ge=0)
    diarrhea_episodes_24h: int = Field(0, ge=0)
    unable_to_keep_fluids: bool = False
    unable_to_keep_meds: bool = False
    dizziness_or_orthostasis: bool = False
    reduced_urine_output: bool = False
    black_stool_or_visible_blood: bool = False
    fever: bool = False
    weaker_effect_of_regular_meds: bool = False
    delayed_effect_of_regular_meds: bool = False


class Labs(BaseModel):
    egfr_ml_min: Optional[float] = None
    creatinine_mg_dl: Optional[float] = None
    crp_mg_l: Optional[float] = None
    tsh_miu_l: Optional[float] = None
    free_t4_ng_dl: Optional[float] = None
    hemoglobin_g_dl: Optional[float] = None
    ferritin_ng_ml: Optional[float] = None
    albumin_g_dl: Optional[float] = None
    alt_u_l: Optional[float] = None
    ast_u_l: Optional[float] = None
    inr: Optional[float] = None


class PatientContext(BaseModel):
    patient_id: str
    age_years: int
    sex: str
    weight_kg: Optional[float] = None

    # GLP-1 context
    glp1_agent: str = "none"
    glp1_current_dose: Optional[str] = None
    glp1_weeks_since_start: Optional[int] = None
    glp1_weeks_since_last_dose_increase: Optional[int] = None

    # Acid / cation perpetrators
    ppi_or_h2_blocker: bool = False
    calcium_iron_magnesium_aluminum_products: bool = False
    bile_acid_sequestrants: bool = False
    sucralfate: bool = False

    # Organ function
    child_pugh: str = "none"
    aki_present: bool = False
    dialysis: str = "none"

    # Cardiopulmonary
    heart_failure_congestion: bool = False
    gut_edema_suspected: bool = False

    # Inflammation
    systemic_inflammation: str = "none"
    acute_infection: bool = False

    # GI anatomy
    bariatric_type: str = "none"
    months_since_bariatric: Optional[int] = None
    short_bowel: bool = False

    # Current state
    symptoms: GISymptoms = Field(default_factory=GISymptoms)
    labs: Labs = Field(default_factory=Labs)
    medications: list[MedicationInput] = Field(default_factory=list)


# ============================================================================
# Output models
# ============================================================================

class I18nAction(BaseModel):
    i18n_key: str
    evidence_grade: EvidenceGrade
    rule_id: Optional[str] = None


class LabRecommendation(BaseModel):
    test: str
    interval_weeks: int
    i18n_key: str
    rule_id: Optional[str] = None


class AdminTrace(BaseModel):
    """Hidden admin/research layer — internal pattern terminology, never shown to patient."""
    rule_id: str
    pattern: str
    i18n_key_internal: str
    mechanism: str


class InteractionFinding(BaseModel):
    rule_id: str
    rule_name: str
    medication_name: str
    severity: str
    underexposure_risk: RiskLevel = RiskLevel.LOW
    overexposure_risk: RiskLevel = RiskLevel.LOW
    delayed_onset_risk: RiskLevel = RiskLevel.LOW
    net_pk_variability: RiskLevel = RiskLevel.LOW
    evidence_grade: EvidenceGrade
    sources: list[str] = Field(default_factory=list)
    physician_actions: list[I18nAction] = Field(default_factory=list)
    patient_actions: list[I18nAction] = Field(default_factory=list)
    lab_plan: list[LabRecommendation] = Field(default_factory=list)
    admin_trace: AdminTrace


class GLP1DosingRecommendation(BaseModel):
    decision: GLP1Decision
    i18n_key: str
    rationale_i18n_keys: list[str] = Field(default_factory=list)
    evidence_grade: EvidenceGrade


class FutureRisk(BaseModel):
    i18n_key: str
    timeframe_weeks: int
    evidence_grade: EvidenceGrade
    rule_id: Optional[str] = None


class ChronicMedAdjustment(BaseModel):
    medication_name: str
    adjustment_i18n_key: str
    trigger_i18n_key: str
    timeframe_weeks: int
    evidence_grade: EvidenceGrade


class ClinicalForecast(BaseModel):
    glp1_dosing: GLP1DosingRecommendation
    future_risks: list[FutureRisk] = Field(default_factory=list)
    chronic_med_adjustments: list[ChronicMedAdjustment] = Field(default_factory=list)


class PharmacistAssessment(BaseModel):
    patient_id: str
    triage_color: TriageColor
    triage_summary_i18n_key: str
    interactions: list[InteractionFinding] = Field(default_factory=list)
    forecast: ClinicalForecast
    rule_pack_version: str
    drug_db_version: str
    sign_off_status: str = "pending_sign_off"

    def to_audit_record(self) -> dict[str, Any]:
        """Compact record for audit logging."""
        return {
            "patient_id": self.patient_id,
            "triage": self.triage_color.value,
            "rule_ids_triggered": [f.rule_id for f in self.interactions],
            "glp1_decision": self.forecast.glp1_dosing.decision.value,
            "rule_pack_version": self.rule_pack_version,
            "drug_db_version": self.drug_db_version,
        }


# ============================================================================
# Rule DSL evaluator — safe, no eval/exec
# ============================================================================

class RuleEvaluator:
    """Walk structured conditions against {patient, drug} context."""

    @staticmethod
    def _get_field(context: dict, dotted_path: str) -> Any:
        parts = dotted_path.split(".")
        value: Any = context
        for part in parts:
            if value is None:
                return None
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = getattr(value, part, None)
        return value

    @classmethod
    def evaluate(cls, condition: dict, context: dict) -> bool:
        # Logical operators
        if "and" in condition:
            return all(cls.evaluate(c, context) for c in condition["and"])
        if "or" in condition:
            return any(cls.evaluate(c, context) for c in condition["or"])
        if "not" in condition:
            return not cls.evaluate(condition["not"], context)

        # Leaf
        field = condition.get("field")
        if field is None:
            return False
        value = cls._get_field(context, field)

        if "eq" in condition:
            return value == condition["eq"]
        if "neq" in condition:
            return value != condition["neq"]
        if "in" in condition:
            return value in condition["in"]
        if "contains" in condition:
            # field is a list; check whether the expected value is in it
            return isinstance(value, list) and condition["contains"] in value
        if "any_in" in condition:
            # field is a list; check whether any of the expected values are in it
            return isinstance(value, list) and any(v in value for v in condition["any_in"])

        # Numeric comparisons (None safe)
        if value is None:
            return False
        try:
            if "lt" in condition:
                return value < condition["lt"]
            if "lte" in condition:
                return value <= condition["lte"]
            if "gt" in condition:
                return value > condition["gt"]
            if "gte" in condition:
                return value >= condition["gte"]
        except TypeError:
            return False

        return False


# ============================================================================
# Pharmacist Agent
# ============================================================================

class PharmacistAgent:
    """Main decision-support agent — assembles triage + interactions + forecast."""

    # Configurable thresholds (can be lifted into a config file if needed)
    NAUSEA_YELLOW = 5
    NAUSEA_HOLD = 5
    VOMITING_HOLD = 1
    CONSTIPATION_YELLOW_DAYS = 3
    DIARRHEA_YELLOW_EPISODES = 4
    VOMITING_RED_24H = 5
    PAIN_RED_SCORE = 8
    GLP1_RECENT_WEEKS = 4
    EGFR_DOAC_REVIEW = 50
    EGFR_DOAC_CRITICAL = 30
    ALBUMIN_LOW = 3.0

    def __init__(
        self,
        patient: PatientContext,
        rule_pack: dict,
        drug_db: dict,
    ):
        self.patient = patient
        self.rule_pack = rule_pack
        self.drug_db_index = {p["profile_id"]: p for p in drug_db.get("profiles", [])}
        self._drug_db_version = drug_db.get("schema_version", "unknown")

    # ---------- Public entry ----------

    def assess(self) -> PharmacistAssessment:
        triage_color, triage_key = self._triage()
        interactions = self._analyze_interactions()
        forecast = self._generate_forecast()

        return PharmacistAssessment(
            patient_id=self.patient.patient_id,
            triage_color=triage_color,
            triage_summary_i18n_key=triage_key,
            interactions=interactions,
            forecast=forecast,
            rule_pack_version=self.rule_pack.get("rule_pack_version", "unknown"),
            drug_db_version=self._drug_db_version,
        )

    # ---------- Triage ----------

    def _triage(self) -> tuple[TriageColor, str]:
        s = self.patient.symptoms

        # RED — ER / immediate evaluation
        if (
            s.unable_to_keep_fluids
            or s.unable_to_keep_meds
            or s.black_stool_or_visible_blood
            or s.reduced_urine_output
            or s.vomiting_episodes_24h >= self.VOMITING_RED_24H
            or s.abdominal_pain_score >= self.PAIN_RED_SCORE
        ):
            return TriageColor.RED, "triage.red.emergency"

        # YELLOW — hold GLP-1 escalation, reassess oral therapy
        glp1_recent = (
            (self.patient.glp1_weeks_since_start or 99) < self.GLP1_RECENT_WEEKS
            or (self.patient.glp1_weeks_since_last_dose_increase or 99) < self.GLP1_RECENT_WEEKS
        )
        if (
            s.nausea_score >= self.NAUSEA_YELLOW
            or s.vomiting_episodes_24h > 0
            or s.constipation_days_without_stool >= self.CONSTIPATION_YELLOW_DAYS
            or s.diarrhea_episodes_24h >= self.DIARRHEA_YELLOW_EPISODES
            or s.weaker_effect_of_regular_meds
            or s.delayed_effect_of_regular_meds
            or (glp1_recent and (s.nausea_score >= 3 or s.early_satiety))
        ):
            return TriageColor.YELLOW, "triage.yellow.hold_and_reassess"

        return TriageColor.GREEN, "triage.green.stable"

    # ---------- Interactions ----------

    def _analyze_interactions(self) -> list[InteractionFinding]:
        findings: list[InteractionFinding] = []
        patient_dict = self.patient.model_dump()
        patient_dict["med_summary"] = self._compute_medication_summary()

        for med in self.patient.medications:
            profile = self.drug_db_index.get(med.profile_id)
            if profile is None:
                continue

            context = {"patient": patient_dict, "drug": profile}

            for rule in self.rule_pack.get("rules", []):
                if not RuleEvaluator.evaluate(rule.get("when", {}), context):
                    continue

                findings.append(self._build_finding(rule, med, profile))

        return findings

    # ---------- Medication summary (for drug-drug rule context) ----------

    # Static class membership lists (extend as drug_db grows)
    _CYP3A_STRONG_INDUCERS = {"carbamazepine", "phenytoin", "rifampin", "rifampicin"}
    _CYP3A_STRONG_INHIBITORS = {
        "itraconazole_capsule", "voriconazole",
        "posaconazole_oral_suspension", "fluconazole",
        "clarithromycin", "ritonavir",
    }
    _BILE_SEQUESTRANT_IDS = {"cholestyramine", "colesevelam", "colestipol", "sevelamer"}
    _LITHIUM_IDS = {"lithium_carbonate", "lithium_citrate"}
    _NTI_HEPATIC = {"warfarin", "phenytoin", "valproate_sodium", "tacrolimus",
                    "cyclosporine", "amiodarone", "carbamazepine"}
    _HYPOGLYCEMIC_NON_INSULIN = {"sulfonylurea", "meglitinide"}
    _HYPOGLYCEMIC_INSULIN = {"insulin_basal", "insulin_rapid"}

    def _compute_medication_summary(self) -> dict:
        """Pre-compute drug-drug context flags from the patient's medication list.

        Exposed to the rule DSL as patient.med_summary.* — lets rules check
        combinations (e.g. lithium + loop diuretic, ≥2 QT-prolonging drugs)
        without each rule walking the medication list itself.
        """
        classes: list[str] = []
        profile_ids: list[str] = []
        qt_count = 0
        bile_dependent_count = 0

        has_acid_suppression = False
        has_cation_perpetrator = False
        has_loop_diuretic = False
        has_oral_contraceptive = False
        has_lithium = False
        has_dependent_lt4 = False
        has_glp1 = self.patient.glp1_agent != "none"
        has_bile_sequestrant = self.patient.bile_acid_sequestrants
        has_cyp3a_strong_inducer = False
        has_cyp3a_strong_inhibitor = False
        has_hypoglycemic_secretagogue = False
        has_insulin = False

        for med in self.patient.medications:
            profile = self.drug_db_index.get(med.profile_id, {})
            cls = profile.get("class", "")
            classes.append(cls)
            profile_ids.append(med.profile_id)

            if profile.get("qt_prolongation_risk"):
                qt_count += 1
            if profile.get("bile_dependent"):
                bile_dependent_count += 1
            if profile.get("is_perpetrator_acid_suppression"):
                has_acid_suppression = True
            if profile.get("is_perpetrator_cation"):
                has_cation_perpetrator = True
            if profile.get("oral_contraceptive"):
                has_oral_contraceptive = True

            if cls == "loop_diuretic":
                has_loop_diuretic = True
            if cls in self._HYPOGLYCEMIC_NON_INSULIN:
                has_hypoglycemic_secretagogue = True
            if cls in self._HYPOGLYCEMIC_INSULIN:
                has_insulin = True

            if med.profile_id in self._LITHIUM_IDS:
                has_lithium = True
            if med.profile_id.startswith("levothyroxine"):
                has_dependent_lt4 = True
            if med.profile_id in self._CYP3A_STRONG_INDUCERS:
                has_cyp3a_strong_inducer = True
            if med.profile_id in self._CYP3A_STRONG_INHIBITORS:
                has_cyp3a_strong_inhibitor = True
            if med.profile_id in self._BILE_SEQUESTRANT_IDS:
                has_bile_sequestrant = True

        return {
            "classes": classes,
            "profile_ids": profile_ids,
            "qt_prolonging_med_count": qt_count,
            "bile_dependent_med_count": bile_dependent_count,
            "has_acid_suppression": has_acid_suppression,
            "has_cation_perpetrator": has_cation_perpetrator,
            "has_loop_diuretic": has_loop_diuretic,
            "has_oral_contraceptive": has_oral_contraceptive,
            "has_lithium": has_lithium,
            "has_levothyroxine": has_dependent_lt4,
            "has_glp1": has_glp1,
            "has_bile_sequestrant": has_bile_sequestrant,
            "has_cyp3a_strong_inducer": has_cyp3a_strong_inducer,
            "has_cyp3a_strong_inhibitor": has_cyp3a_strong_inhibitor,
            "has_hypoglycemic_secretagogue": has_hypoglycemic_secretagogue,
            "has_insulin": has_insulin,
        }

    def _build_finding(
        self,
        rule: dict,
        med: MedicationInput,
        profile: dict,
    ) -> InteractionFinding:
        risk = rule.get("risk", {})
        admin = rule.get("admin_layer", {})
        rule_grade = EvidenceGrade(rule.get("evidence_grade", "C"))

        return InteractionFinding(
            rule_id=rule["rule_id"],
            rule_name=rule.get("name", ""),
            medication_name=med.name,
            severity=rule.get("severity", "moderate"),
            underexposure_risk=RiskLevel(risk.get("underexposure_risk", "low")),
            overexposure_risk=RiskLevel(risk.get("overexposure_risk", "low")),
            delayed_onset_risk=RiskLevel(risk.get("delayed_onset_risk", "low")),
            net_pk_variability=RiskLevel(risk.get("net_pk_variability", "low")),
            evidence_grade=rule_grade,
            sources=rule.get("sources", []),
            physician_actions=[
                I18nAction(
                    i18n_key=a["i18n_key"],
                    evidence_grade=EvidenceGrade(a.get("evidence_grade", rule_grade.value)),
                    rule_id=rule["rule_id"],
                )
                for a in rule.get("physician_actions", [])
            ],
            patient_actions=[
                I18nAction(
                    i18n_key=a["i18n_key"],
                    evidence_grade=EvidenceGrade(a.get("evidence_grade", rule_grade.value)),
                    rule_id=rule["rule_id"],
                )
                for a in rule.get("patient_actions", [])
            ],
            lab_plan=[
                LabRecommendation(
                    test=lab["test"],
                    interval_weeks=lab["interval_weeks"],
                    i18n_key=lab["i18n_key"],
                    rule_id=rule["rule_id"],
                )
                for lab in rule.get("lab_plan", [])
            ],
            admin_trace=AdminTrace(
                rule_id=rule["rule_id"],
                pattern=admin.get("pattern", "unknown"),
                i18n_key_internal=admin.get("i18n_key_internal", ""),
                mechanism=rule.get("mechanism", ""),
            ),
        )

    # ---------- Forecast ----------

    def _generate_forecast(self) -> ClinicalForecast:
        return ClinicalForecast(
            glp1_dosing=self._compute_glp1_dosing(),
            future_risks=self._compute_future_risks(),
            chronic_med_adjustments=self._compute_chronic_adjustments(),
        )

    def _compute_glp1_dosing(self) -> GLP1DosingRecommendation:
        s = self.patient.symptoms

        if (
            s.nausea_score >= self.NAUSEA_HOLD
            or s.vomiting_episodes_24h >= self.VOMITING_HOLD
            or s.unable_to_keep_meds
            or s.unable_to_keep_fluids
        ):
            return GLP1DosingRecommendation(
                decision=GLP1Decision.HOLD,
                i18n_key="forecast.glp1.hold_no_escalation",
                rationale_i18n_keys=["forecast.glp1.rationale.gi_intolerance"],
                evidence_grade=EvidenceGrade.A,
            )

        glp1_recent = (
            (self.patient.glp1_weeks_since_last_dose_increase or 99) < self.GLP1_RECENT_WEEKS
        )
        if glp1_recent:
            return GLP1DosingRecommendation(
                decision=GLP1Decision.REVIEW,
                i18n_key="forecast.glp1.review_recent_escalation",
                rationale_i18n_keys=["forecast.glp1.rationale.first_4_weeks_attenuates"],
                evidence_grade=EvidenceGrade.A,
            )

        return GLP1DosingRecommendation(
            decision=GLP1Decision.CONTINUE,
            i18n_key="forecast.glp1.continue_standard_titration",
            rationale_i18n_keys=["forecast.glp1.rationale.stable_tolerance"],
            evidence_grade=EvidenceGrade.B,
        )

    def _compute_future_risks(self) -> list[FutureRisk]:
        risks: list[FutureRisk] = []
        labs = self.patient.labs
        s = self.patient.symptoms

        # AKI from dehydration / persistent GI losses
        if (
            s.vomiting_episodes_24h > 0
            or s.diarrhea_episodes_24h >= self.DIARRHEA_YELLOW_EPISODES
            or s.reduced_urine_output
        ):
            risks.append(FutureRisk(
                i18n_key="forecast.risk.aki_dehydration",
                timeframe_weeks=2,
                evidence_grade=EvidenceGrade.A,
            ))

        # DOAC accumulation as eGFR drops
        has_doac = any(
            self._is_class(m.profile_id, "DOAC")
            for m in self.patient.medications
        )
        if (
            has_doac
            and labs.egfr_ml_min is not None
            and labs.egfr_ml_min < self.EGFR_DOAC_REVIEW
        ):
            risks.append(FutureRisk(
                i18n_key="forecast.risk.doac_accumulation_low_egfr",
                timeframe_weeks=8,
                evidence_grade=EvidenceGrade.A,
            ))

        # Orthostatic hypotension from weight loss + antihypertensives
        glp1_active = self.patient.glp1_agent != "none"
        has_antihypertensive = any(
            self._is_class_in(m.profile_id, {"ace_inhibitor", "arb", "beta_blocker", "ccb"})
            for m in self.patient.medications
        )
        if (
            glp1_active
            and has_antihypertensive
            and (self.patient.glp1_weeks_since_start or 0) > self.GLP1_RECENT_WEEKS
        ):
            risks.append(FutureRisk(
                i18n_key="forecast.risk.orthostatic_weight_loss",
                timeframe_weeks=8,
                evidence_grade=EvidenceGrade.B,
            ))

        # LT4 drift on PPI
        has_lt4 = any(m.profile_id.startswith("levothyroxine") for m in self.patient.medications)
        if has_lt4 and self.patient.ppi_or_h2_blocker:
            risks.append(FutureRisk(
                i18n_key="forecast.risk.lt4_drift_ppi",
                timeframe_weeks=6,
                evidence_grade=EvidenceGrade.A,
            ))

        # Inflammation-driven CYP suppression
        if (
            self.patient.systemic_inflammation in {"moderate", "severe"}
            or (labs.crp_mg_l is not None and labs.crp_mg_l >= 50)
        ):
            has_cyp_substrate = any(
                self._has_flag(m.profile_id, "inflammation_sensitive_clearance")
                for m in self.patient.medications
            )
            if has_cyp_substrate:
                risks.append(FutureRisk(
                    i18n_key="forecast.risk.cyp_substrate_toxicity_in_inflammation",
                    timeframe_weeks=2,
                    evidence_grade=EvidenceGrade.B,
                ))

        if not risks:
            risks.append(FutureRisk(
                i18n_key="forecast.risk.stable_profile",
                timeframe_weeks=4,
                evidence_grade=EvidenceGrade.C,
            ))

        return risks

    def _compute_chronic_adjustments(self) -> list[ChronicMedAdjustment]:
        adj: list[ChronicMedAdjustment] = []
        labs = self.patient.labs
        glp1_weeks = self.patient.glp1_weeks_since_start or 0
        glp1_active = self.patient.glp1_agent != "none"

        for med in self.patient.medications:
            profile = self.drug_db_index.get(med.profile_id)
            if profile is None:
                continue
            cls = profile.get("class", "")

            # DOAC reduction trigger as eGFR falls
            if (
                cls == "DOAC"
                and labs.egfr_ml_min is not None
                and labs.egfr_ml_min < self.EGFR_DOAC_REVIEW
            ):
                adj.append(ChronicMedAdjustment(
                    medication_name=med.name,
                    adjustment_i18n_key="adjust.doac_reduce_at_egfr_30",
                    trigger_i18n_key="trigger.egfr_falling",
                    timeframe_weeks=8,
                    evidence_grade=EvidenceGrade.A,
                ))

            # Antihypertensive taper after sustained GLP-1 use
            if (
                cls in {"ace_inhibitor", "arb", "beta_blocker", "ccb"}
                and glp1_active
                and glp1_weeks > 8
            ):
                adj.append(ChronicMedAdjustment(
                    medication_name=med.name,
                    adjustment_i18n_key="adjust.antihypertensive_taper_25_50",
                    trigger_i18n_key="trigger.expected_weight_loss",
                    timeframe_weeks=8,
                    evidence_grade=EvidenceGrade.B,
                ))

            # LT4 dose review after sustained weight loss
            if (
                cls == "thyroid_hormone"
                and glp1_active
                and glp1_weeks > 12
            ):
                adj.append(ChronicMedAdjustment(
                    medication_name=med.name,
                    adjustment_i18n_key="adjust.lt4_review_dose_weight_loss",
                    trigger_i18n_key="trigger.expected_weight_loss",
                    timeframe_weeks=12,
                    evidence_grade=EvidenceGrade.B,
                ))

            # Antidiabetic taper — metformin/SU/insulin with GLP-1 + falling A1c (proxy: weight loss timeline)
            if (
                cls in {"biguanide", "sulfonylurea", "insulin"}
                and glp1_active
                and glp1_weeks > 8
            ):
                adj.append(ChronicMedAdjustment(
                    medication_name=med.name,
                    adjustment_i18n_key="adjust.antidiabetic_review_for_hypoglycemia",
                    trigger_i18n_key="trigger.glp1_glycemic_effect",
                    timeframe_weeks=8,
                    evidence_grade=EvidenceGrade.A,
                ))

        return adj

    # ---------- Helpers ----------

    def _is_class(self, profile_id: str, target_class: str) -> bool:
        profile = self.drug_db_index.get(profile_id, {})
        return profile.get("class") == target_class

    def _is_class_in(self, profile_id: str, classes: set[str]) -> bool:
        profile = self.drug_db_index.get(profile_id, {})
        return profile.get("class") in classes

    def _has_flag(self, profile_id: str, flag: str) -> bool:
        profile = self.drug_db_index.get(profile_id, {})
        return bool(profile.get(flag))


# ============================================================================
# Convenience loaders
# ============================================================================

def load_resources(
    rule_pack_path: str,
    drug_db_path: str,
) -> tuple[dict, dict]:
    """Load rule pack and drug master DB from disk."""
    with open(rule_pack_path, "r", encoding="utf-8") as f:
        rule_pack = json.load(f)
    with open(drug_db_path, "r", encoding="utf-8") as f:
        drug_db = json.load(f)
    return rule_pack, drug_db


# ============================================================================
# Smoke test — run directly: python pharmacist_agent.py
# ============================================================================

if __name__ == "__main__":
    import sys

    rule_pack_path = sys.argv[1] if len(sys.argv) > 1 else "rule_pack_v2.json"
    drug_db_path = sys.argv[2] if len(sys.argv) > 2 else "drug_master_v2.json"

    rule_pack, drug_db = load_resources(rule_pack_path, drug_db_path)

    patient = PatientContext(
        patient_id="P-DEMO-001",
        age_years=58,
        sex="female",
        weight_kg=82,
        glp1_agent="tirzepatide_sc",
        glp1_current_dose="5 mg weekly",
        glp1_weeks_since_start=2,
        glp1_weeks_since_last_dose_increase=2,
        ppi_or_h2_blocker=True,
        calcium_iron_magnesium_aluminum_products=False,
        symptoms=GISymptoms(
            nausea_score=7,
            vomiting_episodes_24h=1,
            constipation_days_without_stool=3,
            early_satiety=True,
            weaker_effect_of_regular_meds=True,
        ),
        labs=Labs(egfr_ml_min=52, crp_mg_l=8, tsh_miu_l=6.4, albumin_g_dl=3.5),
        medications=[
            MedicationInput(name="Levothyroxine 100 mcg", profile_id="levothyroxine_tablet", route="oral", is_essential=True),
            MedicationInput(name="Apixaban 5 mg bid", profile_id="apixaban", route="oral", is_essential=True),
            MedicationInput(name="Omeprazole 20 mg", profile_id="omeprazole", route="oral"),
        ],
    )

    agent = PharmacistAgent(patient, rule_pack, drug_db)
    assessment = agent.assess()

    print(json.dumps(assessment.model_dump(), indent=2, ensure_ascii=False))
    print("\n--- AUDIT RECORD ---")
    print(json.dumps(assessment.to_audit_record(), indent=2, ensure_ascii=False))
