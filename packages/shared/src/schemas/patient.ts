/**
 * Patient input — ported 1:1 from the v4 PatientContext / GISymptoms / Labs /
 * MedicationInput Pydantic models. Field names and nesting are preserved exactly,
 * because the rule DSL addresses them by dotted path (e.g. "patient.labs.egfr_ml_min",
 * "patient.ppi_or_h2_blocker"). Do not rename without updating rule_pack_v1.json.
 */
import { z } from "zod";

export const MedicationInput = z.object({
  name: z.string(),
  profile_id: z.string(),
  route: z.string().default("oral"),
  dose: z.string().nullable().optional(),
  is_essential: z.boolean().default(false),
});
export type MedicationInput = z.infer<typeof MedicationInput>;

export const GISymptoms = z.object({
  nausea_score: z.number().int().min(0).max(10).default(0),
  vomiting_episodes_24h: z.number().int().min(0).default(0),
  abdominal_pain_score: z.number().int().min(0).max(10).default(0),
  bloating_score: z.number().int().min(0).max(10).default(0),
  early_satiety: z.boolean().default(false),
  constipation_days_without_stool: z.number().int().min(0).default(0),
  diarrhea_episodes_24h: z.number().int().min(0).default(0),
  unable_to_keep_fluids: z.boolean().default(false),
  unable_to_keep_meds: z.boolean().default(false),
  dizziness_or_orthostasis: z.boolean().default(false),
  reduced_urine_output: z.boolean().default(false),
  black_stool_or_visible_blood: z.boolean().default(false),
  fever: z.boolean().default(false),
  weaker_effect_of_regular_meds: z.boolean().default(false),
  delayed_effect_of_regular_meds: z.boolean().default(false),
});
export type GISymptoms = z.infer<typeof GISymptoms>;

export const Labs = z.object({
  egfr_ml_min: z.number().nullable().default(null),
  creatinine_mg_dl: z.number().nullable().default(null),
  crp_mg_l: z.number().nullable().default(null),
  tsh_miu_l: z.number().nullable().default(null),
  free_t4_ng_dl: z.number().nullable().default(null),
  hemoglobin_g_dl: z.number().nullable().default(null),
  ferritin_ng_ml: z.number().nullable().default(null),
  albumin_g_dl: z.number().nullable().default(null),
  alt_u_l: z.number().nullable().default(null),
  ast_u_l: z.number().nullable().default(null),
  inr: z.number().nullable().default(null),
});
export type Labs = z.infer<typeof Labs>;

export const PatientContext = z.object({
  patient_id: z.string(),
  age_years: z.number().int(),
  sex: z.string(),
  weight_kg: z.number().nullable().optional(),

  // GLP-1 context
  glp1_agent: z.string().default("none"),
  glp1_current_dose: z.string().nullable().optional(),
  glp1_weeks_since_start: z.number().int().nullable().optional(),
  glp1_weeks_since_last_dose_increase: z.number().int().nullable().optional(),

  // Acid / cation perpetrators
  ppi_or_h2_blocker: z.boolean().default(false),
  calcium_iron_magnesium_aluminum_products: z.boolean().default(false),
  bile_acid_sequestrants: z.boolean().default(false),
  sucralfate: z.boolean().default(false),

  // Organ function
  child_pugh: z.string().default("none"), // none | A | B | C
  aki_present: z.boolean().default(false),
  dialysis: z.string().default("none"),

  // Cardiopulmonary
  heart_failure_congestion: z.boolean().default(false),
  gut_edema_suspected: z.boolean().default(false),

  // Inflammation
  systemic_inflammation: z.string().default("none"), // none | mild | moderate | severe
  acute_infection: z.boolean().default(false),

  // GI anatomy
  bariatric_type: z.string().default("none"),
  months_since_bariatric: z.number().int().nullable().optional(),
  short_bowel: z.boolean().default(false),

  // Current state
  symptoms: GISymptoms.default({}),
  labs: Labs.default({}),
  medications: z.array(MedicationInput).default([]),
});
export type PatientContext = z.infer<typeof PatientContext>;
