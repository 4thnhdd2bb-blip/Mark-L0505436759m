/**
 * Dual-layer projection.
 *
 * The agent produces ONE full PharmacistAssessment (admin layer). What each
 * audience sees is a narrowing:
 *   - admin / research : everything, including admin_trace (internal pattern terms).
 *   - physician        : full clinical content + rule_ids + mechanism, but the
 *                        METACOD-internal pattern terminology is blanked.
 *   - patient          : only triage, patient-facing actions and the GLP-1 dosing
 *                        decision — NEVER rule_ids, mechanisms, internal patterns,
 *                        risk axes, physician actions, lab orders or forecasts.
 */
import type {
  PharmacistAssessment,
  InteractionFinding,
  ViewLayer,
  I18nAction,
} from "@metacod/shared";

const EMPTY_TRACE = { rule_id: "", pattern: "", i18n_key_internal: "", mechanism: "" };

function stripActionRuleId(a: I18nAction): I18nAction {
  const { rule_id: _omit, ...rest } = a;
  return rest;
}

function physicianFinding(f: InteractionFinding): InteractionFinding {
  // Keep mechanism (for clinician trust) but hide the internal pattern terminology.
  return {
    ...f,
    admin_trace: { rule_id: f.rule_id, pattern: "", i18n_key_internal: "", mechanism: f.admin_trace.mechanism },
  };
}

function patientFinding(f: InteractionFinding): InteractionFinding {
  return {
    rule_id: "",
    rule_name: "",
    medication_name: f.medication_name,
    medication_profile_id: "",
    severity: f.severity,
    underexposure_risk: "low",
    overexposure_risk: "low",
    delayed_onset_risk: "low",
    net_pk_variability: "low",
    evidence_grade: f.evidence_grade,
    sources: [],
    physician_actions: [],
    patient_actions: f.patient_actions.map(stripActionRuleId),
    lab_plan: [],
    admin_trace: EMPTY_TRACE,
  };
}

export function project(full: PharmacistAssessment, layer: ViewLayer): PharmacistAssessment {
  switch (layer) {
    case "admin":
    case "research":
      return full;

    case "physician":
      return { ...full, interactions: full.interactions.map(physicianFinding) };

    case "patient":
      return {
        ...full,
        interactions: full.interactions
          .filter((f) => f.patient_actions.length > 0)
          .map(patientFinding),
        forecast: {
          glp1_dosing: full.forecast.glp1_dosing,
          future_risks: [], // forward-looking clinical reasoning is not patient-facing
          chronic_med_adjustments: [],
        },
      };
  }
}
