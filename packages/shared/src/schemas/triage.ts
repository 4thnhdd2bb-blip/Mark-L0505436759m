/**
 * Triage — the fast safety gate that runs BEFORE the PK rule engine.
 * RED short-circuits everything to an ER disposition; YELLOW typically means
 * HOLD GLP-1 and reassess oral meds; GREEN proceeds to full assessment.
 */
import { z } from "zod";
import { LocalizedText } from "./common.js";

export const TriageLevel = z.enum(["RED", "GREEN", "YELLOW"]);
export type TriageLevel = z.infer<typeof TriageLevel>;

export const TriageReason = z.object({
  /** Symptom/finding code that contributed, for audit (e.g. "persistent_vomiting"). */
  code: z.string().min(1),
  text: LocalizedText,
});
export type TriageReason = z.infer<typeof TriageReason>;

export const TriageResult = z.object({
  level: TriageLevel,
  reasons: z.array(TriageReason).default([]),
  /** Disposition instruction as an i18n key (e.g. ER now / hold GLP-1 / continue). */
  disposition: LocalizedText,
  /** Convenience flag the Pharmacist layer reads. */
  hold_glp1: z.boolean().default(false),
});
export type TriageResult = z.infer<typeof TriageResult>;
