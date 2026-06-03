/**
 * The four PK risk axes the engine reasons about. We deliberately model the
 * MECHANISM, never "disease X -> dose -25%". GLP-1 therapy slows gastric
 * emptying -> delayed Tmax / variable Cmax -> oral therapy becomes unreliable,
 * and that unreliability resolves into exactly four independent failure modes.
 */
import { z } from "zod";
import { Severity, LocalizedText } from "./common.js";

export const RiskType = z.enum([
  /** Reduced bioavailability (F down): drug under-absorbed -> sub-therapeutic. */
  "underexposure",
  /** Right-shifted Tmax: correct dose, but effect arrives late / erratically. */
  "delayed_onset",
  /** Reduced clearance (hepatic/renal) -> accumulation -> toxicity. */
  "overexposure",
  /** Low albumin raises free fraction: total level looks fine but free drug is high. */
  "free_fraction_misleading",
]);
export type RiskType = z.infer<typeof RiskType>;

/**
 * A single risk surfaced by the engine. Always carries the rule_id that produced
 * it (traceability / audit) and a mechanism_trace key (why, in plain language).
 */
export const RiskFlag = z.object({
  risk_type: RiskType,
  severity: Severity,
  /** Rule that raised this flag — links output back to rule_pack for audit. */
  rule_id: z.string().min(1),
  /** Drug(s) implicated, by drug_id. */
  drug_ids: z.array(z.string()).default([]),
  /** Mechanistic explanation as an i18n key (admin/clinical layer). */
  mechanism_trace: LocalizedText,
});
export type RiskFlag = z.infer<typeof RiskFlag>;
