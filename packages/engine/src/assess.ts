/**
 * Orchestrator: triage -> (PK rules) -> pharmacist forecast -> full EngineOutput.
 *
 * Pure function: all identifiers, timestamps and versions are injected so the
 * engine stays deterministic and testable. The result starts in the White Coat
 * Rule's `pending_sign_off` state — nothing reaches an EHR until a physician signs.
 */
import type {
  PatientInput,
  RulePack,
  DrugProfile,
  EngineOutput,
} from "@metacod/shared";
import { assessTriage } from "./triage.js";
import { runRules, buildDrugIndex } from "./ruleEngine.js";
import { runPharmacistAgent } from "./pharmacistAgent.js";

export interface AssessContext {
  assessment_id: string;
  generated_at: string; // ISO-8601 (injected, not read from clock)
  rule_pack_version: string;
  drug_master_version: string;
}

export function assess(
  patient: PatientInput,
  pack: RulePack,
  drugProfiles: readonly DrugProfile[],
  ctx: AssessContext,
): EngineOutput {
  const triage = assessTriage(patient);

  // RED short-circuits to an emergency disposition; PK rule output is suppressed
  // to keep the message unambiguous. Everything is still audited upstream.
  const drugIndex = buildDrugIndex(drugProfiles);
  const rules =
    triage.level === "RED"
      ? { risk_flags: [], clinician_actions: [], patient_actions: [], lab_plan: [], internal_patterns: [], fired_rule_ids: [] }
      : runRules(patient, pack, drugIndex);

  const pharmacist = runPharmacistAgent(patient, triage, rules);

  return {
    meta: {
      assessment_id: ctx.assessment_id,
      case_id: patient.case_id,
      generated_at: ctx.generated_at,
      rule_pack_version: ctx.rule_pack_version,
      drug_master_version: ctx.drug_master_version,
      sign_off: { state: "pending_sign_off" },
    },
    triage,
    risk_flags: rules.risk_flags,
    clinician_actions: rules.clinician_actions,
    patient_actions: rules.patient_actions,
    lab_plan: rules.lab_plan,
    pharmacist_forecast: pharmacist,
    internal_patterns: rules.internal_patterns,
  };
}
