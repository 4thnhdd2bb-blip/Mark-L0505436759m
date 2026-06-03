/**
 * Rule schema — one entry of rule_pack_v1.json.
 *
 * Ported from the v4 DSL. A rule's `when` is a structured condition evaluated
 * safely (no eval/exec) against a context of { patient, drug } — see the engine's
 * RuleEvaluator. Leaf predicates address a dotted `field` path and apply one
 * comparison operator. Logical nodes are `and` / `or` (arrays) and `not` (single).
 */
import { z } from "zod";
import { EvidenceGrade, RiskLevel } from "./enums.js";

/**
 * Recursive condition DSL. Declared as a TS type first so zod's z.lazy can be
 * given an explicit annotation (zod cannot infer recursive types on its own).
 * A leaf is `{ field, <op>: value }`; the value is intentionally `unknown`
 * (the operator decides how to compare).
 */
export type Condition =
  | { and: Condition[] }
  | { or: Condition[] }
  | { not: Condition }
  | {
      field: string;
      eq?: unknown;
      neq?: unknown;
      in?: unknown[] | undefined;
      lt?: number | undefined;
      lte?: number | undefined;
      gt?: number | undefined;
      gte?: number | undefined;
    };

const LeafCondition = z.object({
  field: z.string(),
  eq: z.unknown().optional(),
  neq: z.unknown().optional(),
  in: z.array(z.unknown()).optional(),
  lt: z.number().optional(),
  lte: z.number().optional(),
  gt: z.number().optional(),
  gte: z.number().optional(),
});

export const Condition: z.ZodType<Condition> = z.lazy(() =>
  z.union([
    z.object({ and: z.array(Condition) }),
    z.object({ or: z.array(Condition) }),
    z.object({ not: Condition }),
    LeafCondition,
  ]),
);

/** An i18n-keyed action with its own evidence grade (defaults to the rule's). */
export const RuleI18nAction = z.object({
  i18n_key: z.string(),
  evidence_grade: EvidenceGrade.optional(),
});
export type RuleI18nAction = z.infer<typeof RuleI18nAction>;

/** A lab order the rule recommends. */
export const RuleLabPlan = z.object({
  test: z.string(),
  interval_weeks: z.number().int(),
  i18n_key: z.string(),
});
export type RuleLabPlan = z.infer<typeof RuleLabPlan>;

/** Risk-axis profile a rule contributes (any axis may be omitted -> low). */
export const RuleRisk = z.object({
  underexposure_risk: RiskLevel.optional(),
  overexposure_risk: RiskLevel.optional(),
  delayed_onset_risk: RiskLevel.optional(),
  net_pk_variability: RiskLevel.optional(),
});
export type RuleRisk = z.infer<typeof RuleRisk>;

/** Admin/research-only layer: METACOD-internal pattern terminology. */
export const RuleAdminLayer = z.object({
  pattern: z.string(),
  i18n_key_internal: z.string(),
});
export type RuleAdminLayer = z.infer<typeof RuleAdminLayer>;

export const Rule = z.object({
  rule_id: z.string(),
  name: z.string().default(""),
  severity: z.enum(["high", "moderate", "low"]).default("moderate"),
  evidence_grade: EvidenceGrade.default("C"),
  mechanism: z.string().default(""),
  when: Condition,
  risk: RuleRisk.default({}),
  physician_actions: z.array(RuleI18nAction).default([]),
  patient_actions: z.array(RuleI18nAction).default([]),
  lab_plan: z.array(RuleLabPlan).default([]),
  admin_layer: RuleAdminLayer,
  sources: z.array(z.string()).default([]),
});
export type Rule = z.infer<typeof Rule>;

export const RulePack = z
  .object({
    rule_pack_version: z.string(),
    last_updated: z.string().optional(),
    description: z.string().optional(),
    dsl_documentation: z.record(z.string(), z.string()).optional(),
    rules: z.array(Rule),
  })
  .passthrough();
export type RulePack = z.infer<typeof RulePack>;
