/**
 * PatientInput — everything the engine needs to assess a case.
 *
 * Fields are chosen to satisfy the Part 2 priority rules. Anything the rules read
 * lives here; nothing here is free text the engine has to NLP-parse.
 */
import { z } from "zod";
import { Route, DrugForm } from "./drug.js";

/** GLP-1 / GIP agents the module reasons about. */
export const Glp1Agent = z.enum([
  "none",
  "semaglutide",   // Ozempic / Wegovy
  "tirzepatide",   // Mounjaro / Zepbound (GIP/GLP-1)
  "dulaglutide",   // Trulicity
  "liraglutide",   // Victoza / Saxenda
  "other",
]);
export type Glp1Agent = z.infer<typeof Glp1Agent>;

/** Therapy phase — start and each dose escalation re-open the underexposure window. */
export const Glp1Phase = z.enum(["start", "escalation", "maintenance"]);
export type Glp1Phase = z.infer<typeof Glp1Phase>;

export const Glp1Therapy = z.object({
  agent: Glp1Agent.default("none"),
  phase: Glp1Phase.default("maintenance"),
  /** Weeks since start or since the most recent escalation. <4 = high-risk window. */
  weeks_since_change: z.number().min(0).nullable().default(null),
});
export type Glp1Therapy = z.infer<typeof Glp1Therapy>;

/** One medication the patient is currently taking. */
export const MedicationEntry = z.object({
  /** Links to DrugProfile.drug_id so the engine can read molecular properties. */
  drug_id: z.string().min(1),
  /** Display name as entered (free text, for the UI only — engine uses drug_id). */
  label: z.string().optional(),
  route: Route.default("oral"),
  form: DrugForm.default("tablet"),
  dose_mg: z.number().positive().nullable().default(null),
  /** Free-form schedule string for display; structured timing below for rules. */
  frequency: z.string().optional(),
  /** Hour-of-day administration times (0..23), used by the cation-separation rule. */
  administration_hours: z.array(z.number().min(0).max(23)).default([]),
});
export type MedicationEntry = z.infer<typeof MedicationEntry>;

/** Child-Pugh class for hepatic reserve. */
export const ChildPugh = z.enum(["A", "B", "C"]);

/** Lab values. All optional/nullable — engine degrades gracefully and asks for them. */
export const Labs = z.object({
  egfr: z.number().min(0).nullable().default(null),            // mL/min/1.73m2
  crp_mg_l: z.number().min(0).nullable().default(null),        // C-reactive protein
  albumin_g_l: z.number().min(0).nullable().default(null),
  tsh: z.number().min(0).nullable().default(null),
  ferritin: z.number().min(0).nullable().default(null),
  tsat_pct: z.number().min(0).max(100).nullable().default(null), // transferrin saturation
  alt: z.number().min(0).nullable().default(null),
  ast: z.number().min(0).nullable().default(null),
  inr: z.number().min(0).nullable().default(null),
});
export type Labs = z.infer<typeof Labs>;

/** Relevant comorbidities / states that change PK. */
export const Conditions = z.object({
  heart_failure: z.boolean().default(false),
  /** Decompensated HF with gut wall edema -> impaired oral loop diuretic absorption. */
  gut_edema: z.boolean().default(false),
  cirrhosis: z.boolean().default(false),
  child_pugh: ChildPugh.nullable().default(null),
  /** Severe systemic inflammation/sepsis -> cytokine-driven CYP suppression. */
  severe_inflammation: z.boolean().default(false),
  /** Months since bariatric surgery (<6 = unpredictable absorption window). */
  bariatric_surgery_months_ago: z.number().min(0).nullable().default(null),
});
export type Conditions = z.infer<typeof Conditions>;

/** Acute GI / systemic symptoms driving triage (RED / YELLOW / GREEN). */
export const Symptoms = z.object({
  nausea_0_10: z.number().min(0).max(10).default(0),
  vomiting_episodes_24h: z.number().min(0).default(0),
  persistent_vomiting: z.boolean().default(false),
  constipation_days: z.number().min(0).default(0),
  diarrhea_episodes_24h: z.number().min(0).default(0),
  severe_abdominal_pain: z.boolean().default(false),
  gi_bleeding: z.boolean().default(false),
  /** Cannot keep down medications or fluids — a RED-flag input. */
  unable_to_keep_meds_or_fluids: z.boolean().default(false),
  dehydration: z.boolean().default(false),
  reduced_urine_output: z.boolean().default(false),
  aki_signs: z.boolean().default(false),
  /** Patient-reported weaker/delayed effect of an oral medication. */
  weaker_or_delayed_oral_effect: z.boolean().default(false),
});
export type Symptoms = z.infer<typeof Symptoms>;

export const PatientInput = z.object({
  /** Pseudonymous case id — NO direct identifiers stored in the engine layer. */
  case_id: z.string().min(1),
  age_years: z.number().min(0).max(120).nullable().default(null),
  sex: z.enum(["female", "male", "other", "unknown"]).default("unknown"),
  weight_kg: z.number().positive().nullable().default(null),

  glp1: Glp1Therapy.default({}),
  medications: z.array(MedicationEntry).default([]),
  labs: Labs.default({}),
  conditions: Conditions.default({}),
  symptoms: Symptoms.default({}),
});
export type PatientInput = z.infer<typeof PatientInput>;
