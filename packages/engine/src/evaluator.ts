/**
 * Safe rule DSL evaluator — ported 1:1 from the v4 RuleEvaluator.
 *
 * No eval/exec: a condition is a structured object walked against a context of
 * { patient, drug }. Logical nodes are `and` / `or` (arrays) and `not` (single).
 * A leaf is `{ field: "<dotted.path>", <op>: value }` with one of:
 *   eq, neq, in, lt, lte, gt, gte. Numeric comparisons are null-safe (a missing
 *   value never throws and simply fails the comparison) — matching v4 semantics.
 */
import type { Condition } from "@metacod/shared";

export type EvalContext = Record<string, unknown>;

/** Walk a dotted path into a plain-object context. Returns undefined on any miss. */
export function getField(context: unknown, dottedPath: string): unknown {
  let value: unknown = context;
  for (const part of dottedPath.split(".")) {
    if (value == null || typeof value !== "object") return undefined;
    value = (value as Record<string, unknown>)[part];
  }
  return value;
}

export function evaluate(condition: Condition, context: EvalContext): boolean {
  // Logical operators
  if ("and" in condition) return condition.and.every((c) => evaluate(c, context));
  if ("or" in condition) return condition.or.some((c) => evaluate(c, context));
  if ("not" in condition) return !evaluate(condition.not, context);

  // Leaf
  const leaf = condition;
  const value = getField(context, leaf.field);

  if ("eq" in leaf && leaf.eq !== undefined) return value === leaf.eq;
  if ("neq" in leaf && leaf.neq !== undefined) return value !== leaf.neq;
  if ("in" in leaf && leaf.in !== undefined) return leaf.in.includes(value);
  // field is a list; expected value present in it
  if ("contains" in leaf && leaf.contains !== undefined)
    return Array.isArray(value) && value.includes(leaf.contains);
  // field is a list; any of the expected values present in it
  if ("any_in" in leaf && leaf.any_in !== undefined)
    return Array.isArray(value) && leaf.any_in.some((v) => value.includes(v));

  // Numeric comparisons (null/non-number safe)
  if (typeof value !== "number") return false;
  if (leaf.lt !== undefined) return value < leaf.lt;
  if (leaf.lte !== undefined) return value <= leaf.lte;
  if (leaf.gt !== undefined) return value > leaf.gt;
  if (leaf.gte !== undefined) return value >= leaf.gte;

  return false;
}
