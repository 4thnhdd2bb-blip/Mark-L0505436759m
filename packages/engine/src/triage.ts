/**
 * Triage — fast safety gate, evaluated before the PK rule engine.
 * Thresholds come straight from the module spec. RED dominates YELLOW dominates
 * GREEN. RED short-circuits the assessment to an ER disposition.
 */
import type { PatientInput, TriageResult, TriageReason } from "@metacod/shared";

function reason(code: string, key: string): TriageReason {
  return { code, text: { key } };
}

/** RED: any single finding here means emergency. */
function redReasons(p: PatientInput): TriageReason[] {
  const s = p.symptoms;
  const out: TriageReason[] = [];
  if (s.persistent_vomiting) out.push(reason("persistent_vomiting", "triage.reason.persistent_vomiting"));
  if (s.unable_to_keep_meds_or_fluids) out.push(reason("unable_to_keep_meds_or_fluids", "triage.reason.unable_to_keep_meds_or_fluids"));
  if (s.severe_abdominal_pain) out.push(reason("severe_abdominal_pain", "triage.reason.severe_abdominal_pain"));
  if (s.gi_bleeding) out.push(reason("gi_bleeding", "triage.reason.gi_bleeding"));
  if (s.dehydration && s.reduced_urine_output) out.push(reason("dehydration_oliguria", "triage.reason.dehydration_oliguria"));
  if (s.aki_signs) out.push(reason("aki_signs", "triage.reason.aki_signs"));
  return out;
}

/** YELLOW: any finding here means caution + HOLD GLP-1, reassess oral meds. */
function yellowReasons(p: PatientInput): TriageReason[] {
  const s = p.symptoms;
  const out: TriageReason[] = [];
  if (s.nausea_0_10 >= 5) out.push(reason("nausea_ge_5", "triage.reason.nausea_ge_5"));
  if (s.vomiting_episodes_24h > 0 && s.vomiting_episodes_24h < 3) out.push(reason("vomiting_lt_3", "triage.reason.vomiting_lt_3"));
  if (s.constipation_days >= 3) out.push(reason("constipation_ge_3d", "triage.reason.constipation_ge_3d"));
  if (s.diarrhea_episodes_24h >= 4) out.push(reason("diarrhea_ge_4", "triage.reason.diarrhea_ge_4"));
  if (s.weaker_or_delayed_oral_effect) out.push(reason("weaker_delayed_oral", "triage.reason.weaker_delayed_oral"));
  const g = p.glp1;
  if (
    (g.phase === "start" || g.phase === "escalation") &&
    g.weeks_since_change !== null &&
    g.weeks_since_change < 4
  ) {
    out.push(reason("glp1_start_or_escalation_lt_4w", "triage.reason.glp1_start_or_escalation_lt_4w"));
  }
  return out;
}

export function assessTriage(patient: PatientInput): TriageResult {
  const red = redReasons(patient);
  if (red.length > 0) {
    return { level: "RED", reasons: red, disposition: { key: "disposition.er_now" }, hold_glp1: true };
  }
  const yellow = yellowReasons(patient);
  if (yellow.length > 0) {
    return { level: "YELLOW", reasons: yellow, disposition: { key: "disposition.hold_glp1_reassess" }, hold_glp1: true };
  }
  return { level: "GREEN", reasons: [], disposition: { key: "disposition.continue" }, hold_glp1: false };
}
