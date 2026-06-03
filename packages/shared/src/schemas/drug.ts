/**
 * Drug Profile Schema — molecular PK profile consumed by the rule DSL.
 *
 * Ported from the v4 drug_master_v1.json field set. The rule engine reads these
 * fields by dotted path (e.g. "drug.class", "drug.high_first_pass",
 * "drug.requires_acidic_pH", "drug.protein_binding"), so names are preserved.
 *
 * The schema is intentionally permissive (.passthrough(), most fields optional):
 * profiles vary field-by-field and the clinical team extends them drug-by-drug.
 * Only the identity fields are required.
 */
import { z } from "zod";
import { EvidenceGrade, Locale } from "./enums.js";

const Tristate = z.enum(["none", "low", "moderate", "high"]);

/** Trilingual display name. */
export const DisplayName = z.record(Locale, z.string());
export type DisplayName = z.infer<typeof DisplayName>;

export const DrugProfile = z
  .object({
    profile_id: z.string(),
    display_name: DisplayName,
    class: z.string(),
    route: z.string().default("oral"),

    // Absorption sensitivities
    requires_acidic_pH: Tristate.optional(),
    cation_binding_sensitive: z.boolean().optional(),
    proximal_absorption_critical: z.boolean().optional(),
    bile_dependent: z.boolean().optional(),
    food_effect: z.enum(["none", "with_food", "fasting", "specific"]).optional(),

    // First-pass / hepatic
    high_first_pass: z.boolean().optional(),
    hepatic_extraction: Tristate.optional(),
    inflammation_sensitive_clearance: z.boolean().optional(),

    // Elimination
    renal_clearance_fraction: z.enum(["low", "moderate", "high", "variable"]).optional(),
    active_metabolites_renally_cleared: z.boolean().optional(),

    // Binding / index
    protein_binding: Tristate.optional(),
    narrow_therapeutic_index: z.boolean().optional(),
    tdm_available: z.union([z.boolean(), z.string()]).optional(),

    // GI-motility / anatomy sensitivity
    tmax_sensitive: z.boolean().optional(),
    modified_release: z.boolean().optional(),
    post_bariatric_variability: Tristate.optional(),
    gut_edema_sensitive: z.boolean().optional(),

    // Special flags
    oral_contraceptive: z.boolean().optional(),
    is_perpetrator_cation: z.boolean().optional(),
    is_perpetrator_acid_suppression: z.boolean().optional(),

    // Metadata
    monitor: z.array(z.string()).optional(),
    alternative_formulations: z.array(z.string()).optional(),
    evidence_grade: EvidenceGrade.optional(),
    last_reviewed: z.string().optional(),
    sources: z.array(z.string()).optional(),
  })
  .passthrough();
export type DrugProfile = z.infer<typeof DrugProfile>;

/** The whole drug master file: version + profiles. */
export const DrugMaster = z
  .object({
    schema_version: z.string(),
    last_updated: z.string().optional(),
    description: z.string().optional(),
    field_definitions: z.record(z.string(), z.string()).optional(),
    profiles: z.array(DrugProfile),
  })
  .passthrough();
export type DrugMaster = z.infer<typeof DrugMaster>;
