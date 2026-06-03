/**
 * Declarative condition evaluator.
 *
 * This is the heart that lets the rule_pack be DATA, not code: every Rule.when
 * is a Condition AST evaluated here against (patient, drug profiles). Part 2 only
 * adds JSON; the matching logic does not change.
 */
import type {
  Condition,
  LeafPredicate,
  DrugMatch,
  ComparisonOp,
  PatientInput,
  MedicationEntry,
  DrugProfile,
} from "@metacod/shared";

export interface EvalContext {
  patient: PatientInput;
  /** drug_id -> molecular profile (from drug_master). */
  drugIndex: ReadonlyMap<string, DrugProfile>;
}

/** Safe dot-path read into a plain object tree. Returns undefined on any miss. */
export function getPath(root: unknown, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc != null && typeof acc === "object" && key in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, root);
}

function applyOp(left: unknown, op: ComparisonOp, value: unknown): boolean {
  switch (op) {
    case "exists":
      return left !== undefined && left !== null;
    case "eq":
      return left === value;
    case "ne":
      return left !== value;
    case "in":
      return Array.isArray(value) && value.includes(left as never);
    case "lt":
    case "lte":
    case "gt":
    case "gte": {
      if (typeof left !== "number" || typeof value !== "number") return false;
      if (op === "lt") return left < value;
      if (op === "lte") return left <= value;
      if (op === "gt") return left > value;
      return left >= value;
    }
    default:
      return false;
  }
}

/** Does a single medication (joined with its profile) satisfy a DrugMatch? */
function medMatches(med: MedicationEntry, ctx: EvalContext, m: DrugMatch): boolean {
  if (m.drug_id !== undefined && med.drug_id !== m.drug_id) return false;
  if (m.route !== undefined && med.route !== m.route) return false;
  if (m.form !== undefined && med.form !== m.form) return false;

  const profile = ctx.drugIndex.get(med.drug_id);
  if (m.drug_class !== undefined) {
    if (!profile || profile.drug_class !== m.drug_class) return false;
  }
  for (const propPath of m.has_properties ?? []) {
    if (!profile || getPath(profile, propPath) !== true) return false;
  }
  return true;
}

/** Smallest gap in hours between any administration time of two meds. */
function minHourGap(a: MedicationEntry, b: MedicationEntry): number | null {
  if (a.administration_hours.length === 0 || b.administration_hours.length === 0) return null;
  let best = Infinity;
  for (const ha of a.administration_hours) {
    for (const hb of b.administration_hours) {
      const raw = Math.abs(ha - hb);
      best = Math.min(best, Math.min(raw, 24 - raw)); // wrap-around clock distance
    }
  }
  return best;
}

function evalLeaf(leaf: LeafPredicate, ctx: EvalContext): boolean {
  switch (leaf.kind) {
    case "patient":
      return applyOp(getPath(ctx.patient, leaf.path), leaf.op, leaf.value);

    case "glp1_agent": {
      const g = ctx.patient.glp1;
      if (!leaf.in.includes(g.agent)) return false;
      if (leaf.within_weeks_of_change !== undefined) {
        return g.weeks_since_change !== null && g.weeks_since_change <= leaf.within_weeks_of_change;
      }
      return true;
    }

    case "has_medication":
      return ctx.patient.medications.some((med) => medMatches(med, ctx, leaf.match));

    case "concurrent": {
      const meds = ctx.patient.medications;
      for (let i = 0; i < meds.length; i++) {
        for (let j = 0; j < meds.length; j++) {
          if (i === j) continue;
          const a = meds[i]!;
          const b = meds[j]!;
          if (!medMatches(a, ctx, leaf.a) || !medMatches(b, ctx, leaf.b)) continue;
          if (leaf.within_hours !== undefined) {
            const gap = minHourGap(a, b);
            if (gap === null || gap > leaf.within_hours) continue;
          }
          return true;
        }
      }
      return false;
    }
  }
}

/** Evaluate a full condition tree. */
export function evaluateCondition(cond: Condition, ctx: EvalContext): boolean {
  if ("all" in cond) return cond.all.every((c) => evaluateCondition(c, ctx));
  if ("any" in cond) return cond.any.some((c) => evaluateCondition(c, ctx));
  if ("not" in cond) return !evaluateCondition(cond.not, ctx);
  return evalLeaf(cond, ctx);
}
