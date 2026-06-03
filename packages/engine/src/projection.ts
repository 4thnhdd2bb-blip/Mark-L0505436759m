/**
 * Dual-layer projection.
 *
 * The engine builds ONE full EngineOutput (admin layer). What each audience sees
 * is a narrowing of it. The hard invariants:
 *   - patient NEVER sees rule_ids, mechanism traces, internal pattern names,
 *     risk axes, clinician actions or lab orders.
 *   - internal pattern names are admin/research ONLY.
 *   - physician sees clinical content + rule_ids + mechanism traces for trust.
 */
import type { EngineOutput, ViewLayer, ActionItem } from "@metacod/shared";

function stripRuleId(a: ActionItem): ActionItem {
  const { rule_id: _omit, ...rest } = a;
  return rest;
}

/** Project the full output for a given audience. Returns a redacted EngineOutput. */
export function project(full: EngineOutput, layer: ViewLayer): EngineOutput {
  switch (layer) {
    case "admin":
    case "research":
      return full; // full visibility

    case "physician":
      // Clinical content + traceability, but internal pattern names stay hidden.
      return { ...full, internal_patterns: [] };

    case "patient":
      return {
        ...full,
        risk_flags: [],
        clinician_actions: [],
        lab_plan: [],
        internal_patterns: [],
        patient_actions: full.patient_actions.map(stripRuleId),
        pharmacist_forecast: {
          glp1_dosing: full.pharmacist_forecast.glp1_dosing,
          glp1_rationale: full.pharmacist_forecast.glp1_rationale,
          future_risks: [], // forward-looking clinical reasoning is not patient-facing
          chronic_med_adjustments: full.pharmacist_forecast.chronic_med_adjustments.map(stripRuleId),
        },
      };
  }
}
