/**
 * Part 2 parity test — proves the TS port reproduces the v4 Python agent on the
 * reference demo patient (P-DEMO-001), plus content validation and dual-layer
 * projection invariants. Built dist + node's built-in test runner (no extra deps).
 *
 *   npm run build && node --test packages/engine/test/parity.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { assess, project, evaluate, loadContent } from "../dist/index.js";

const { rulePack, drugMaster } = loadContent();

test("clinical content loads and validates", () => {
  assert.equal(rulePack.rule_pack_version, "1.0.0");
  assert.equal(rulePack.rules.length, 15);
  assert.equal(drugMaster.schema_version, "2.0.0");
  assert.equal(drugMaster.profiles.length, 60);
});

// Reference demo patient from the v4 agent's __main__ block.
const demo = {
  patient_id: "P-DEMO-001",
  age_years: 58,
  sex: "female",
  weight_kg: 82,
  glp1_agent: "tirzepatide_sc",
  glp1_current_dose: "5 mg weekly",
  glp1_weeks_since_start: 2,
  glp1_weeks_since_last_dose_increase: 2,
  ppi_or_h2_blocker: true,
  symptoms: {
    nausea_score: 7,
    vomiting_episodes_24h: 1,
    constipation_days_without_stool: 3,
    early_satiety: true,
    weaker_effect_of_regular_meds: true,
  },
  labs: { egfr_ml_min: 52, crp_mg_l: 8, tsh_miu_l: 6.4, albumin_g_dl: 3.5 },
  medications: [
    { name: "Levothyroxine 100 mcg", profile_id: "levothyroxine_tablet", route: "oral", is_essential: true },
    { name: "Apixaban 5 mg bid", profile_id: "apixaban", route: "oral", is_essential: true },
    { name: "Omeprazole 20 mg", profile_id: "omeprazole", route: "oral" },
  ],
};

// PatientContext is parsed/defaulted inside callers in production; for the pure
// engine we pass a structurally-complete object (zod defaults are applied upstream).
import { PatientContext } from "../../shared/dist/index.js";
const demoParsed = PatientContext.parse(demo);

test("demo patient → YELLOW triage, HOLD GLP-1, single PPI/LT4 interaction", () => {
  const out = assess(demoParsed, rulePack, drugMaster);

  assert.equal(out.triage_color, "yellow");
  assert.equal(out.forecast.glp1_dosing.decision, "HOLD");

  assert.equal(out.interactions.length, 1);
  assert.equal(out.interactions[0].rule_id, "LT4_TABLET_PPI");
  assert.equal(out.interactions[0].underexposure_risk, "high");
  assert.equal(out.interactions[0].medication_name, "Levothyroxine 100 mcg");

  assert.equal(out.sign_off_status, "pending_sign_off"); // White Coat Rule

  const futureKeys = out.forecast.future_risks.map((r) => r.i18n_key).sort();
  assert.deepEqual(futureKeys, ["forecast.risk.aki_dehydration", "forecast.risk.lt4_drift_ppi"]);
  assert.equal(out.forecast.chronic_med_adjustments.length, 0);
});

test("RED triage when GI bleeding present", () => {
  const red = PatientContext.parse({ ...demo, symptoms: { ...demo.symptoms, black_stool_or_visible_blood: true } });
  const out = assess(red, rulePack, drugMaster);
  assert.equal(out.triage_color, "red");
});

test("dual-layer projection hides admin/clinical detail from the patient", () => {
  const full = assess(demoParsed, rulePack, drugMaster);

  const admin = project(full, "admin");
  assert.equal(admin.interactions[0].admin_trace.pattern, "pH_dependent_dissolution_failure");

  const physician = project(full, "physician");
  assert.equal(physician.interactions[0].admin_trace.pattern, ""); // internal terms blanked
  assert.ok(physician.interactions[0].admin_trace.mechanism.length > 0); // mechanism kept
  assert.equal(physician.interactions[0].physician_actions.length, 3);

  const patient = project(full, "patient");
  assert.equal(patient.interactions[0].physician_actions.length, 0);
  assert.equal(patient.interactions[0].admin_trace.pattern, "");
  assert.equal(patient.interactions[0].rule_id, "");
  assert.equal(patient.forecast.future_risks.length, 0);
  for (const a of patient.interactions[0].patient_actions) assert.equal(a.rule_id, undefined);
});

test("evaluate() resolves dotted paths against {patient, drug}", () => {
  const ctx = { patient: demoParsed, drug: drugMaster.profiles.find((p) => p.profile_id === "levothyroxine_tablet") };
  assert.equal(evaluate({ field: "patient.ppi_or_h2_blocker", eq: true }, ctx), true);
  assert.equal(evaluate({ field: "drug.profile_id", eq: "levothyroxine_tablet" }, ctx), true);
  assert.equal(evaluate({ field: "patient.labs.egfr_ml_min", lt: 50 }, ctx), false); // 52
});
