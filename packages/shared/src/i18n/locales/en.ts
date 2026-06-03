/**
 * English dictionary — STRUCTURAL keys only for Part 1 (triage, dispositions,
 * risk axes, lab names). Per-rule clinical strings are added alongside the
 * rule_pack in Part 2; full UI copy in Part 3.
 */
import type { Dictionary } from "../keys.js";

export const en: Dictionary = {
  // Triage levels
  "triage.RED": "Emergency",
  "triage.YELLOW": "Caution",
  "triage.GREEN": "Stable",
  // Dispositions
  "disposition.er_now": "Go to the emergency department now.",
  "disposition.hold_glp1_reassess": "Hold the GLP-1 dose and reassess oral medications.",
  "disposition.continue": "Stable — continue current plan with monitoring.",
  // Risk axes
  "risk.underexposure": "Under-exposure (reduced absorption)",
  "risk.delayed_onset": "Delayed onset (right-shifted Tmax)",
  "risk.overexposure": "Over-exposure (reduced clearance)",
  "risk.free_fraction_misleading": "Misleading total level (raised free fraction)",
  // Lab names
  "lab.egfr": "eGFR",
  "lab.crp": "C-reactive protein (CRP)",
  "lab.tsh": "TSH",
  "lab.ferritin": "Ferritin",
  "lab.tsat": "Transferrin saturation",
  "lab.alt_ast": "ALT / AST",
  "lab.inr": "INR",
  "lab.albumin": "Albumin",
};
