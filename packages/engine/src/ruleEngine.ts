/**
 * Rule engine — evaluates a RulePack against a patient and emits risk flags,
 * clinician/patient actions and a lab plan, each tagged with the rule_id that
 * produced it (traceability). The logic is complete; Part 2 supplies the data
 * (rule_pack_v1.json) and the drug_master index it joins against.
 */
import type {
  PatientInput,
  RulePack,
  DrugProfile,
  RiskFlag,
  ActionItem,
  LabOrder,
} from "@metacod/shared";
import { evaluateCondition, type EvalContext } from "./evaluator.js";

export interface RuleEngineResult {
  risk_flags: RiskFlag[];
  clinician_actions: ActionItem[];
  patient_actions: ActionItem[];
  lab_plan: LabOrder[];
  internal_patterns: string[];
  fired_rule_ids: string[];
}

export function buildDrugIndex(profiles: readonly DrugProfile[]): Map<string, DrugProfile> {
  return new Map(profiles.map((p) => [p.drug_id, p]));
}

export function runRules(
  patient: PatientInput,
  pack: RulePack,
  drugIndex: ReadonlyMap<string, DrugProfile>,
): RuleEngineResult {
  const ctx: EvalContext = { patient, drugIndex };
  const result: RuleEngineResult = {
    risk_flags: [],
    clinician_actions: [],
    patient_actions: [],
    lab_plan: [],
    internal_patterns: [],
    fired_rule_ids: [],
  };

  for (const rule of pack.rules) {
    if (!rule.enabled) continue;
    if (!evaluateCondition(rule.when, ctx)) continue;

    result.fired_rule_ids.push(rule.rule_id);

    result.risk_flags.push({
      risk_type: rule.risk_type,
      severity: rule.severity,
      rule_id: rule.rule_id,
      drug_ids: [],
      mechanism_trace: rule.mechanism_trace,
    });

    for (const a of rule.clinician_actions) {
      result.clinician_actions.push({ text: a.text, rule_id: rule.rule_id, ...(a.code ? { code: a.code } : {}) });
    }
    for (const a of rule.patient_actions) {
      result.patient_actions.push({ text: a.text, rule_id: rule.rule_id, ...(a.code ? { code: a.code } : {}) });
    }
    for (const lab of rule.lab_plan) {
      result.lab_plan.push({ lab, reason: rule.mechanism_trace, rule_id: rule.rule_id });
    }
    if (rule.internal_pattern_name) result.internal_patterns.push(rule.internal_pattern_name);
  }

  return result;
}
