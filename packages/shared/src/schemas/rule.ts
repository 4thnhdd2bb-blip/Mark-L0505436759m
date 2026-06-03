/**
 * Rule schema — one entry of rule_pack_v1.json (Part 2 fills ~15-20 of these).
 *
 * Design goals:
 *  - Mechanism-first: a rule fires on PK properties, not on disease names.
 *  - Fully declarative condition AST so the rule_pack is data, not code, and can
 *    be versioned, audited and (later) reviewed by clinicians without a deploy.
 *  - Every rule carries evidence_grade + sources + a mechanism_trace for the
 *    admin/research layer, and i18n action keys for both clinician and patient.
 */
import { z } from "zod";
import { EvidenceGrade, Severity, Source, LocalizedText } from "./common.js";
import { RiskType } from "./risk.js";
import { Route, DrugForm } from "./drug.js";

/** Comparison operators usable in a patient-fact predicate. */
export const ComparisonOp = z.enum(["eq", "ne", "lt", "lte", "gt", "gte", "in", "exists"]);
export type ComparisonOp = z.infer<typeof ComparisonOp>;

/**
 * Matches a single current medication joined with its DrugProfile.
 * All present sub-fields must hold for the medication to match.
 * `has_properties` are dot-paths into DrugProfile that must be boolean-true,
 * e.g. "properties.chelation_sensitive", "absorption.gastric_emptying_sensitive".
 */
export const DrugMatch = z.object({
  drug_id: z.string().optional(),
  drug_class: z.string().optional(),
  route: Route.optional(),
  form: DrugForm.optional(),
  has_properties: z.array(z.string()).optional(),
});
export type DrugMatch = z.infer<typeof DrugMatch>;

/** Leaf predicate over a patient fact (dot-path into PatientInput). */
export const PatientPredicate = z.object({
  kind: z.literal("patient"),
  path: z.string().min(1),           // e.g. "labs.egfr", "conditions.gut_edema"
  op: ComparisonOp,
  value: z.union([z.string(), z.number(), z.boolean(), z.array(z.union([z.string(), z.number()]))]).optional(),
});

/** Leaf predicate: current GLP-1 agent is in a set. */
export const Glp1Predicate = z.object({
  kind: z.literal("glp1_agent"),
  in: z.array(z.string()).min(1),
  /** Optional: only when within the high-risk start/escalation window (<weeks). */
  within_weeks_of_change: z.number().positive().optional(),
});

/** Leaf predicate: at least one current medication matches. */
export const HasMedicationPredicate = z.object({
  kind: z.literal("has_medication"),
  match: DrugMatch,
});

/** Leaf predicate: two medications co-administered (both present concurrently). */
export const ConcurrentPredicate = z.object({
  kind: z.literal("concurrent"),
  a: DrugMatch,
  b: DrugMatch,
  /** For the cation-separation rule: flag if doses are within N hours of each other. */
  within_hours: z.number().positive().optional(),
});

export const LeafPredicate = z.discriminatedUnion("kind", [
  PatientPredicate,
  Glp1Predicate,
  HasMedicationPredicate,
  ConcurrentPredicate,
]);
export type LeafPredicate = z.infer<typeof LeafPredicate>;

/**
 * Recursive boolean condition tree. zod needs an explicit type annotation for
 * recursion, so we declare the TS type first, then the lazy schema.
 */
export type Condition =
  | LeafPredicate
  | { all: Condition[] }
  | { any: Condition[] }
  | { not: Condition };

export const Condition: z.ZodType<Condition> = z.lazy(() =>
  z.union([
    LeafPredicate,
    z.object({ all: z.array(Condition) }),
    z.object({ any: z.array(Condition) }),
    z.object({ not: Condition }),
  ]),
);

/** An action emitted when a rule fires, addressed to one audience. */
export const RuleAction = z.object({
  /** i18n key for the action text. */
  text: LocalizedText,
  /** Optional structured hint the UI/PDF can use (e.g. "switch_to_liquid"). */
  code: z.string().optional(),
});
export type RuleAction = z.infer<typeof RuleAction>;

/** A lab the rule recommends ordering, as a stable code resolved to i18n later. */
export const LabRecommendation = z.enum([
  "egfr",
  "crp",
  "tsh",
  "ferritin",
  "tsat",
  "alt_ast",
  "inr",
  "albumin",
]);
export type LabRecommendation = z.infer<typeof LabRecommendation>;

export const Rule = z.object({
  /** Stable, human-readable id, e.g. "PPI-LT4-UNDEREXPOSURE-001". */
  rule_id: z.string().min(1),
  /** rule_pack version this entry shipped in — copied into every audit record. */
  pack_version: z.string().min(1),
  enabled: z.boolean().default(true),

  /** What PK failure mode this rule represents and how hard it bites. */
  risk_type: RiskType,
  severity: Severity,

  /** Declarative trigger. Fires when this evaluates true against (patient, drugs). */
  when: Condition,

  /** Evidence + provenance (admin/research layer + audit). */
  evidence_grade: EvidenceGrade,
  sources: z.array(Source).min(1),
  /** Plain-language "why", admin/clinical only — never shown to the patient. */
  mechanism_trace: LocalizedText,
  /** Internal pattern name, admin-only, never patient-facing. */
  internal_pattern_name: z.string().optional(),

  /** Outputs, split by audience (dual-layer). */
  clinician_actions: z.array(RuleAction).default([]),
  patient_actions: z.array(RuleAction).default([]),
  lab_plan: z.array(LabRecommendation).default([]),
});
export type Rule = z.infer<typeof Rule>;

/** The whole pack: validated as a unit so version + ids stay consistent. */
export const RulePack = z.object({
  version: z.string().min(1),
  generated_at: z.string().optional(),
  rules: z.array(Rule),
});
export type RulePack = z.infer<typeof RulePack>;
