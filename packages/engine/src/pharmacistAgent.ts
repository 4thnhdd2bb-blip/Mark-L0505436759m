/**
 * Pharmacist Agent — produces the forecast layer: GLP-1 dosing decision
 * (HOLD / CONTINUE / CAUTION), future risks and chronic-med adjustments.
 *
 * PART 1 STATUS: deterministic baseline only. The full refactor (DOSE HOLD logic,
 * future-risk projection at next escalation, chronic-med adjustment synthesis,
 * i18n + evidence grading) lands in PART 2 once the v4 agent code is provided.
 * The baseline below is intentionally conservative and safe.
 */
import type {
  PatientInput,
  TriageResult,
  PharmacistForecast,
} from "@metacod/shared";
import type { RuleEngineResult } from "./ruleEngine.js";

export function runPharmacistAgent(
  _patient: PatientInput,
  triage: TriageResult,
  rules: RuleEngineResult,
): PharmacistForecast {
  // Baseline DOSE HOLD logic: triage HOLD, or any high-severity risk, holds GLP-1.
  const hasHighRisk = rules.risk_flags.some((r) => r.severity === "high");
  const hold = triage.hold_glp1 || hasHighRisk;

  const glp1_dosing = hold ? "HOLD" : rules.risk_flags.length > 0 ? "CAUTION" : "CONTINUE";
  const glp1_rationale = hold
    ? { key: "pharmacist.glp1.hold_baseline" }
    : rules.risk_flags.length > 0
      ? { key: "pharmacist.glp1.caution_baseline" }
      : { key: "pharmacist.glp1.continue_baseline" };

  return {
    glp1_dosing,
    glp1_rationale,
    future_risks: [], // populated in Part 2 (escalation-window projection)
    chronic_med_adjustments: [], // populated in Part 2 (route/form/timing synthesis)
  };
}
