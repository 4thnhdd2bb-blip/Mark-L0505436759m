/**
 * Drug Profile Schema — the molecular profile that feeds the rule engine.
 *
 * Rules do NOT hard-code drug names. A rule asks questions like "is this drug
 * gastric-emptying sensitive AND chelation-sensitive?" and the answers come from
 * this profile. That keeps the rule_pack small and lets new drugs inherit
 * existing rules just by filling in their properties.
 *
 * drug_master_v1.json (Part 2) is an array of objects validated by `DrugProfile`.
 */
import { z } from "zod";
import { Source } from "./common.js";

/** Route of administration for a given product/order. */
export const Route = z.enum([
  "oral",
  "sublingual",
  "buccal",
  "iv",
  "im",
  "subcutaneous",
  "transdermal",
  "inhaled",
  "rectal",
  "other",
]);
export type Route = z.infer<typeof Route>;

/** Galenic form — matters for gastric-emptying sensitivity and NTI risk. */
export const DrugForm = z.enum([
  "tablet",
  "capsule",
  "modified_release", // MR / ER / XR / SR — high risk under altered GI transit
  "liquid",           // solution/suspension — often the mitigation for absorption issues
  "orodispersible",
  "injectable",
  "patch",
  "other",
]);
export type DrugForm = z.infer<typeof DrugForm>;

/** Absorption characteristics — the upstream half of the underexposure/delay axes. */
export const Absorption = z.object({
  /** Oral bioavailability fraction 0..1 (null if not orally absorbed). */
  oral_bioavailability: z.number().min(0).max(1).nullable().default(null),
  /** True if absorption depends materially on gastric emptying / GI transit. */
  gastric_emptying_sensitive: z.boolean().default(false),
  /** Typical Tmax in hours under normal physiology (for delayed-onset reasoning). */
  tmax_hours: z.number().positive().nullable().default(null),
  /** Absorption requires acidic stomach (e.g. weak-base salts) — PPI-sensitive. */
  acid_dependent_absorption: z.boolean().default(false),
  food_effect: z.enum(["none", "increases", "decreases", "variable"]).default("none"),
});

/** First-pass / distribution — drivers of overexposure and free-fraction axes. */
export const Distribution = z.object({
  /** High hepatic first-pass: clearance drops sharply in cirrhosis -> overexposure. */
  high_first_pass: z.boolean().default(false),
  /** Hepatic extraction ratio 0..1 (informs first-pass magnitude). */
  hepatic_extraction_ratio: z.number().min(0).max(1).nullable().default(null),
  /** Plasma protein binding fraction 0..1. */
  protein_binding: z.number().min(0).max(1).nullable().default(null),
  /** Predominantly albumin-bound -> low albumin raises free fraction (misleading totals). */
  albumin_bound: z.boolean().default(false),
});

/** Metabolism — CYP fingerprint for cytokine-driven suppression reasoning (CRP rule). */
export const Metabolism = z.object({
  cyp_substrate: z.array(z.string()).default([]), // e.g. ["CYP3A4", "CYP2C9"]
  cyp_inhibitor: z.array(z.string()).default([]),
  cyp_inducer: z.array(z.string()).default([]),
});

/** Elimination — renal vs hepatic split + half-life for accumulation reasoning. */
export const Elimination = z.object({
  renal_clearance_fraction: z.number().min(0).max(1).nullable().default(null),
  hepatic_clearance_fraction: z.number().min(0).max(1).nullable().default(null),
  half_life_hours: z.number().positive().nullable().default(null),
});

/** Boolean property bag the rule conditions match against. */
export const DrugProperties = z.object({
  narrow_therapeutic_index: z.boolean().default(false),
  modified_release: z.boolean().default(false),
  /** Binds di/trivalent cations (Ca/Fe/Mg/Al) -> needs >=4h separation. */
  chelation_sensitive: z.boolean().default(false),
  /** Is itself a polyvalent cation source (Ca/Fe/Mg/Al antacids, supplements). */
  polyvalent_cation_source: z.boolean().default(false),
  /** Anticoagulant subclass flags used by eGFR/bariatric rules. */
  doac: z.boolean().default(false),
  vka: z.boolean().default(false),
});

export const DrugProfile = z.object({
  drug_id: z.string().min(1), // stable slug, e.g. "levothyroxine"
  inn: z.string().min(1),     // international non-proprietary name
  brand_names: z.array(z.string()).default([]),
  drug_class: z.string().min(1),
  atc_code: z.string().optional(),

  absorption: Absorption,
  distribution: Distribution,
  metabolism: Metabolism,
  elimination: Elimination,
  properties: DrugProperties,

  /** Forms available on market — used to suggest mitigations (e.g. liquid LT4, IV iron). */
  forms_available: z.array(DrugForm).default([]),
  /** Non-oral / alternative routes available, for "switch route" actions. */
  routes_available: z.array(Route).default([]),

  sources: z.array(Source).default([]),
});
export type DrugProfile = z.infer<typeof DrugProfile>;
