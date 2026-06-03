/**
 * Pharmacist Agent — decision-support core, ported 1:1 from the v4 Python agent.
 *
 * Pure logic: triage + per-medication interaction analysis against the rule_pack
 * + clinical forecast (GLP-1 dosing, future risks, chronic med adjustments).
 * Deterministic for the same input → supports audit logging and SaMD compliance.
 * Every user-facing string is an i18n key; no autonomous prescribing (output is a
 * recommendation requiring physician sign-off — the White Coat Rule).
 */
import type {
  PatientContext,
  RulePack,
  DrugMaster,
  DrugProfile,
  Rule,
  MedicationInput,
  PharmacistAssessment,
  InteractionFinding,
  ClinicalForecast,
  GLP1DosingRecommendation,
  FutureRisk,
  ChronicMedAdjustment,
  I18nAction,
  TriageColor,
  EvidenceGrade,
} from "@metacod/shared";
import { evaluate, type EvalContext } from "./evaluator.js";

/** Configurable thresholds — mirror the v4 PharmacistAgent class constants. */
export const THRESHOLDS = {
  NAUSEA_YELLOW: 5,
  NAUSEA_HOLD: 5,
  VOMITING_HOLD: 1,
  CONSTIPATION_YELLOW_DAYS: 3,
  DIARRHEA_YELLOW_EPISODES: 4,
  VOMITING_RED_24H: 5,
  PAIN_RED_SCORE: 8,
  GLP1_RECENT_WEEKS: 4,
  EGFR_DOAC_REVIEW: 50,
  EGFR_DOAC_CRITICAL: 30,
  ALBUMIN_LOW: 3.0,
} as const;

export const AGENT_VERSION = "2.0.0";

export class PharmacistAgent {
  private readonly drugIndex: Map<string, DrugProfile>;
  private readonly drugDbVersion: string;

  constructor(
    private readonly patient: PatientContext,
    private readonly rulePack: RulePack,
    drugMaster: DrugMaster,
  ) {
    this.drugIndex = new Map(drugMaster.profiles.map((p) => [p.profile_id, p]));
    this.drugDbVersion = drugMaster.schema_version ?? "unknown";
  }

  // ---------- Public entry ----------

  assess(): PharmacistAssessment {
    const [triageColor, triageKey] = this.triage();
    const interactions = this.analyzeInteractions();
    const forecast = this.generateForecast(interactions);

    return {
      patient_id: this.patient.patient_id,
      triage_color: triageColor,
      triage_summary_i18n_key: triageKey,
      interactions,
      forecast,
      rule_pack_version: this.rulePack.rule_pack_version ?? "unknown",
      drug_db_version: this.drugDbVersion,
      sign_off_status: "pending_sign_off",
    };
  }

  // ---------- Triage ----------

  private triage(): [TriageColor, string] {
    const s = this.patient.symptoms;

    // RED — ER / immediate evaluation
    if (
      s.unable_to_keep_fluids ||
      s.unable_to_keep_meds ||
      s.black_stool_or_visible_blood ||
      s.reduced_urine_output ||
      s.vomiting_episodes_24h >= THRESHOLDS.VOMITING_RED_24H ||
      s.abdominal_pain_score >= THRESHOLDS.PAIN_RED_SCORE
    ) {
      return ["red", "triage.red.emergency"];
    }

    // YELLOW — hold GLP-1 escalation, reassess oral therapy
    const glp1Recent =
      (this.patient.glp1_weeks_since_start ?? 99) < THRESHOLDS.GLP1_RECENT_WEEKS ||
      (this.patient.glp1_weeks_since_last_dose_increase ?? 99) < THRESHOLDS.GLP1_RECENT_WEEKS;

    if (
      s.nausea_score >= THRESHOLDS.NAUSEA_YELLOW ||
      s.vomiting_episodes_24h > 0 ||
      s.constipation_days_without_stool >= THRESHOLDS.CONSTIPATION_YELLOW_DAYS ||
      s.diarrhea_episodes_24h >= THRESHOLDS.DIARRHEA_YELLOW_EPISODES ||
      s.weaker_effect_of_regular_meds ||
      s.delayed_effect_of_regular_meds ||
      (glp1Recent && (s.nausea_score >= 3 || s.early_satiety))
    ) {
      return ["yellow", "triage.yellow.hold_and_reassess"];
    }

    return ["green", "triage.green.stable"];
  }

  // ---------- Interactions ----------

  private analyzeInteractions(): InteractionFinding[] {
    const findings: InteractionFinding[] = [];

    for (const med of this.patient.medications) {
      const profile = this.drugIndex.get(med.profile_id);
      if (!profile) continue;

      const context: EvalContext = { patient: this.patient, drug: profile };

      for (const rule of this.rulePack.rules) {
        if (!evaluate(rule.when, context)) continue;
        findings.push(this.buildFinding(rule, med));
      }
    }

    return findings;
  }

  private buildFinding(rule: Rule, med: MedicationInput): InteractionFinding {
    const ruleGrade = rule.evidence_grade;
    const mapAction = (a: { i18n_key: string; evidence_grade?: EvidenceGrade | undefined }): I18nAction => ({
      i18n_key: a.i18n_key,
      evidence_grade: a.evidence_grade ?? ruleGrade,
      rule_id: rule.rule_id,
    });

    return {
      rule_id: rule.rule_id,
      rule_name: rule.name,
      medication_name: med.name,
      medication_profile_id: med.profile_id,
      severity: rule.severity,
      underexposure_risk: rule.risk.underexposure_risk ?? "low",
      overexposure_risk: rule.risk.overexposure_risk ?? "low",
      delayed_onset_risk: rule.risk.delayed_onset_risk ?? "low",
      net_pk_variability: rule.risk.net_pk_variability ?? "low",
      evidence_grade: ruleGrade,
      sources: rule.sources,
      physician_actions: rule.physician_actions.map(mapAction),
      patient_actions: rule.patient_actions.map(mapAction),
      lab_plan: rule.lab_plan.map((lab) => ({
        test: lab.test,
        interval_weeks: lab.interval_weeks,
        i18n_key: lab.i18n_key,
        rule_id: rule.rule_id,
      })),
      admin_trace: {
        rule_id: rule.rule_id,
        pattern: rule.admin_layer.pattern,
        i18n_key_internal: rule.admin_layer.i18n_key_internal,
        mechanism: rule.mechanism,
      },
    };
  }

  // ---------- Forecast ----------

  private generateForecast(_interactions: InteractionFinding[]): ClinicalForecast {
    return {
      glp1_dosing: this.computeGlp1Dosing(),
      future_risks: this.computeFutureRisks(),
      chronic_med_adjustments: this.computeChronicAdjustments(),
    };
  }

  private computeGlp1Dosing(): GLP1DosingRecommendation {
    const s = this.patient.symptoms;

    if (
      s.nausea_score >= THRESHOLDS.NAUSEA_HOLD ||
      s.vomiting_episodes_24h >= THRESHOLDS.VOMITING_HOLD ||
      s.unable_to_keep_meds ||
      s.unable_to_keep_fluids
    ) {
      return {
        decision: "HOLD",
        i18n_key: "forecast.glp1.hold_no_escalation",
        rationale_i18n_keys: ["forecast.glp1.rationale.gi_intolerance"],
        evidence_grade: "A",
      };
    }

    const glp1Recent =
      (this.patient.glp1_weeks_since_last_dose_increase ?? 99) < THRESHOLDS.GLP1_RECENT_WEEKS;
    if (glp1Recent) {
      return {
        decision: "REVIEW",
        i18n_key: "forecast.glp1.review_recent_escalation",
        rationale_i18n_keys: ["forecast.glp1.rationale.first_4_weeks_attenuates"],
        evidence_grade: "A",
      };
    }

    return {
      decision: "CONTINUE",
      i18n_key: "forecast.glp1.continue_standard_titration",
      rationale_i18n_keys: ["forecast.glp1.rationale.stable_tolerance"],
      evidence_grade: "B",
    };
  }

  private computeFutureRisks(): FutureRisk[] {
    const risks: FutureRisk[] = [];
    const labs = this.patient.labs;
    const s = this.patient.symptoms;

    // AKI from dehydration / persistent GI losses
    if (
      s.vomiting_episodes_24h > 0 ||
      s.diarrhea_episodes_24h >= THRESHOLDS.DIARRHEA_YELLOW_EPISODES ||
      s.reduced_urine_output
    ) {
      risks.push({ i18n_key: "forecast.risk.aki_dehydration", timeframe_weeks: 2, evidence_grade: "A" });
    }

    // DOAC accumulation as eGFR drops
    const hasDoac = this.patient.medications.some((m) => this.isClass(m.profile_id, "DOAC"));
    if (hasDoac && labs.egfr_ml_min !== null && labs.egfr_ml_min < THRESHOLDS.EGFR_DOAC_REVIEW) {
      risks.push({ i18n_key: "forecast.risk.doac_accumulation_low_egfr", timeframe_weeks: 8, evidence_grade: "A" });
    }

    // Orthostatic hypotension from weight loss + antihypertensives
    const glp1Active = this.patient.glp1_agent !== "none";
    const hasAntihypertensive = this.patient.medications.some((m) =>
      this.isClassIn(m.profile_id, new Set(["ace_inhibitor", "arb", "beta_blocker", "ccb"])),
    );
    if (
      glp1Active &&
      hasAntihypertensive &&
      (this.patient.glp1_weeks_since_start ?? 0) > THRESHOLDS.GLP1_RECENT_WEEKS
    ) {
      risks.push({ i18n_key: "forecast.risk.orthostatic_weight_loss", timeframe_weeks: 8, evidence_grade: "B" });
    }

    // LT4 drift on PPI
    const hasLt4 = this.patient.medications.some((m) => m.profile_id.startsWith("levothyroxine"));
    if (hasLt4 && this.patient.ppi_or_h2_blocker) {
      risks.push({ i18n_key: "forecast.risk.lt4_drift_ppi", timeframe_weeks: 6, evidence_grade: "A" });
    }

    // Inflammation-driven CYP suppression
    if (
      ["moderate", "severe"].includes(this.patient.systemic_inflammation) ||
      (labs.crp_mg_l !== null && labs.crp_mg_l >= 50)
    ) {
      const hasCypSubstrate = this.patient.medications.some((m) =>
        this.hasFlag(m.profile_id, "inflammation_sensitive_clearance"),
      );
      if (hasCypSubstrate) {
        risks.push({
          i18n_key: "forecast.risk.cyp_substrate_toxicity_in_inflammation",
          timeframe_weeks: 2,
          evidence_grade: "B",
        });
      }
    }

    if (risks.length === 0) {
      risks.push({ i18n_key: "forecast.risk.stable_profile", timeframe_weeks: 4, evidence_grade: "C" });
    }

    return risks;
  }

  private computeChronicAdjustments(): ChronicMedAdjustment[] {
    const adj: ChronicMedAdjustment[] = [];
    const labs = this.patient.labs;
    const glp1Weeks = this.patient.glp1_weeks_since_start ?? 0;
    const glp1Active = this.patient.glp1_agent !== "none";

    for (const med of this.patient.medications) {
      const profile = this.drugIndex.get(med.profile_id);
      if (!profile) continue;
      const cls = profile.class ?? "";

      // DOAC reduction trigger as eGFR falls
      if (cls === "DOAC" && labs.egfr_ml_min !== null && labs.egfr_ml_min < THRESHOLDS.EGFR_DOAC_REVIEW) {
        adj.push({
          medication_name: med.name,
          adjustment_i18n_key: "adjust.doac_reduce_at_egfr_30",
          trigger_i18n_key: "trigger.egfr_falling",
          timeframe_weeks: 8,
          evidence_grade: "A",
        });
      }

      // Antihypertensive taper after sustained GLP-1 use
      if (["ace_inhibitor", "arb", "beta_blocker", "ccb"].includes(cls) && glp1Active && glp1Weeks > 8) {
        adj.push({
          medication_name: med.name,
          adjustment_i18n_key: "adjust.antihypertensive_taper_25_50",
          trigger_i18n_key: "trigger.expected_weight_loss",
          timeframe_weeks: 8,
          evidence_grade: "B",
        });
      }

      // LT4 dose review after sustained weight loss
      if (cls === "thyroid_hormone" && glp1Active && glp1Weeks > 12) {
        adj.push({
          medication_name: med.name,
          adjustment_i18n_key: "adjust.lt4_review_dose_weight_loss",
          trigger_i18n_key: "trigger.expected_weight_loss",
          timeframe_weeks: 12,
          evidence_grade: "B",
        });
      }

      // Antidiabetic taper — metformin / SU / insulin with GLP-1
      if (["biguanide", "sulfonylurea", "insulin"].includes(cls) && glp1Active && glp1Weeks > 8) {
        adj.push({
          medication_name: med.name,
          adjustment_i18n_key: "adjust.antidiabetic_review_for_hypoglycemia",
          trigger_i18n_key: "trigger.glp1_glycemic_effect",
          timeframe_weeks: 8,
          evidence_grade: "A",
        });
      }
    }

    return adj;
  }

  // ---------- Helpers ----------

  private isClass(profileId: string, targetClass: string): boolean {
    return this.drugIndex.get(profileId)?.class === targetClass;
  }

  private isClassIn(profileId: string, classes: Set<string>): boolean {
    const cls = this.drugIndex.get(profileId)?.class;
    return cls !== undefined && classes.has(cls);
  }

  private hasFlag(profileId: string, flag: string): boolean {
    return Boolean((this.drugIndex.get(profileId) as Record<string, unknown> | undefined)?.[flag]);
  }
}

/** Convenience wrapper. */
export function assess(
  patient: PatientContext,
  rulePack: RulePack,
  drugMaster: DrugMaster,
): PharmacistAssessment {
  return new PharmacistAgent(patient, rulePack, drugMaster).assess();
}
