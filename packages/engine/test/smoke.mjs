/**
 * Part 1 smoke test — proves the engine runs end-to-end against the schemas:
 * triage gating, declarative rule firing, dual-layer projection, White Coat state.
 * Uses the built dist + node's built-in test runner (no extra deps).
 *
 *   npm run build && node --test packages/engine/test/smoke.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { assess, project, evaluateCondition, buildDrugIndex } from "../dist/index.js";

// --- Minimal fixtures -------------------------------------------------------

const levothyroxine = {
  drug_id: "levothyroxine",
  inn: "levothyroxine",
  brand_names: ["Euthyrox"],
  drug_class: "thyroid_hormone",
  absorption: { oral_bioavailability: 0.7, gastric_emptying_sensitive: true, tmax_hours: 2, acid_dependent_absorption: true, food_effect: "decreases" },
  distribution: { high_first_pass: false, hepatic_extraction_ratio: null, protein_binding: 0.99, albumin_bound: false },
  metabolism: { cyp_substrate: [], cyp_inhibitor: [], cyp_inducer: [] },
  elimination: { renal_clearance_fraction: 0.0, hepatic_clearance_fraction: 1.0, half_life_hours: 168 },
  properties: { narrow_therapeutic_index: true, modified_release: false, chelation_sensitive: true, polyvalent_cation_source: false, doac: false, vka: false },
  forms_available: ["tablet", "liquid"],
  routes_available: ["oral"],
  sources: [],
};

const omeprazole = {
  drug_id: "omeprazole", inn: "omeprazole", brand_names: ["Losec"], drug_class: "ppi",
  absorption: { oral_bioavailability: 0.4, gastric_emptying_sensitive: false, tmax_hours: 1, acid_dependent_absorption: false, food_effect: "none" },
  distribution: { high_first_pass: true, hepatic_extraction_ratio: 0.6, protein_binding: 0.95, albumin_bound: true },
  metabolism: { cyp_substrate: ["CYP2C19"], cyp_inhibitor: ["CYP2C19"], cyp_inducer: [] },
  elimination: { renal_clearance_fraction: 0.8, hepatic_clearance_fraction: 0.2, half_life_hours: 1 },
  properties: { narrow_therapeutic_index: false, modified_release: false, chelation_sensitive: false, polyvalent_cation_source: false, doac: false, vka: false },
  forms_available: ["capsule"], routes_available: ["oral"], sources: [],
};

// One illustrative rule (the real rule_pack_v1 lands in Part 2).
const rulePack = {
  version: "rule_pack_v1-sample",
  rules: [
    {
      rule_id: "PPI-LT4-UNDEREXPOSURE-001",
      pack_version: "rule_pack_v1-sample",
      enabled: true,
      risk_type: "underexposure",
      severity: "high",
      when: {
        all: [
          { kind: "has_medication", match: { drug_class: "ppi" } },
          { kind: "has_medication", match: { drug_id: "levothyroxine", form: "tablet" } },
        ],
      },
      evidence_grade: "B",
      sources: [{ citation: "Sample source for Part 1 smoke test" }],
      mechanism_trace: { key: "rule.PPI-LT4.mechanism" },
      internal_pattern_name: "acid-dependent-absorption-loss",
      clinician_actions: [{ text: { key: "rule.PPI-LT4.clinician.tsh_check" } }],
      patient_actions: [{ text: { key: "rule.PPI-LT4.patient.inform" } }],
      lab_plan: ["tsh"],
    },
  ],
};

const drugIndex = buildDrugIndex([levothyroxine, omeprazole]);

const basePatient = {
  case_id: "case-001",
  age_years: 54, sex: "female", weight_kg: null,
  glp1: { agent: "semaglutide", phase: "maintenance", weeks_since_change: 12 },
  medications: [
    { drug_id: "omeprazole", route: "oral", form: "capsule", dose_mg: 20, administration_hours: [8] },
    { drug_id: "levothyroxine", route: "oral", form: "tablet", dose_mg: 0.1, administration_hours: [7] },
  ],
  labs: { egfr: null, crp_mg_l: null, albumin_g_l: null, tsh: null, ferritin: null, tsat_pct: null, alt: null, ast: null, inr: null },
  conditions: { heart_failure: false, gut_edema: false, cirrhosis: false, child_pugh: null, severe_inflammation: false, bariatric_surgery_months_ago: null },
  symptoms: { nausea_0_10: 0, vomiting_episodes_24h: 0, persistent_vomiting: false, constipation_days: 0, diarrhea_episodes_24h: 0, severe_abdominal_pain: false, gi_bleeding: false, unable_to_keep_meds_or_fluids: false, dehydration: false, reduced_urine_output: false, aki_signs: false },
};

const ctx = { assessment_id: "a-1", generated_at: "2026-06-03T10:00:00.000Z", rule_pack_version: "rule_pack_v1-sample", drug_master_version: "drug_master_v1-sample" };

test("GREEN patient: PPI+LT4 rule fires with traceable rule_id", () => {
  const out = assess(basePatient, rulePack, [levothyroxine, omeprazole], ctx);
  assert.equal(out.triage.level, "GREEN");
  assert.equal(out.risk_flags.length, 1);
  assert.equal(out.risk_flags[0].rule_id, "PPI-LT4-UNDEREXPOSURE-001");
  assert.equal(out.risk_flags[0].risk_type, "underexposure");
  assert.equal(out.meta.sign_off.state, "pending_sign_off"); // White Coat Rule
  assert.equal(out.pharmacist_forecast.glp1_dosing, "HOLD"); // high-severity risk holds GLP-1
});

test("RED triage short-circuits and suppresses PK rules", () => {
  const red = { ...basePatient, symptoms: { ...basePatient.symptoms, gi_bleeding: true } };
  const out = assess(red, rulePack, [levothyroxine, omeprazole], ctx);
  assert.equal(out.triage.level, "RED");
  assert.equal(out.risk_flags.length, 0);
  assert.equal(out.triage.disposition.key, "disposition.er_now");
});

test("YELLOW on GLP-1 escalation <4 weeks holds GLP-1", () => {
  const y = { ...basePatient, glp1: { agent: "tirzepatide", phase: "escalation", weeks_since_change: 1 } };
  const out = assess(y, rulePack, [levothyroxine, omeprazole], ctx);
  assert.equal(out.triage.level, "YELLOW");
  assert.equal(out.triage.hold_glp1, true);
});

test("patient projection strips rule_ids, mechanism traces and internal patterns", () => {
  const full = assess(basePatient, rulePack, [levothyroxine, omeprazole], ctx);
  const patient = project(full, "patient");
  assert.equal(patient.risk_flags.length, 0);
  assert.equal(patient.clinician_actions.length, 0);
  assert.equal(patient.lab_plan.length, 0);
  assert.equal(patient.internal_patterns.length, 0);
  for (const a of patient.patient_actions) assert.equal(a.rule_id, undefined);

  const physician = project(full, "physician");
  assert.equal(physician.internal_patterns.length, 0); // admin-only
  assert.equal(physician.risk_flags[0].rule_id, "PPI-LT4-UNDEREXPOSURE-001"); // traceable

  const admin = project(full, "admin");
  assert.deepEqual(admin.internal_patterns, ["acid-dependent-absorption-loss"]);
});

test("evaluateCondition matches drug properties directly", () => {
  const fired = evaluateCondition(
    { kind: "has_medication", match: { has_properties: ["properties.chelation_sensitive"] } },
    { patient: basePatient, drugIndex },
  );
  assert.equal(fired, true); // levothyroxine is chelation_sensitive
});
