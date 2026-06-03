/**
 * EngineOutput — the canonical result of one assessment.
 *
 * It is produced once, in full (admin layer), then PROJECTED for the audience:
 *  - AdminView/ResearchView: everything (rule_ids, mechanism_trace, internal names).
 *  - PhysicianView: clinical content + rule_ids for traceability.
 *  - PatientView: simplified language only — NEVER rule_ids, mechanism traces or
 *    internal pattern names.
 * The projection contract is defined here; the implementation lives in engine.
 */
import { z } from "zod";
import { IsoTimestamp, LocalizedText } from "./common.js";
import { RiskFlag } from "./risk.js";
import { TriageResult } from "./triage.js";
import { LabRecommendation } from "./rule.js";
import { SignOffRecord } from "./audit.js";

/** A recommendation addressed to clinician or patient, traceable to a rule. */
export const ActionItem = z.object({
  text: LocalizedText,
  /** Originating rule — present in admin/physician layers, stripped for patients. */
  rule_id: z.string().optional(),
  code: z.string().optional(),
});
export type ActionItem = z.infer<typeof ActionItem>;

/** A lab the plan recommends, with the reason as an i18n key. */
export const LabOrder = z.object({
  lab: LabRecommendation,
  reason: LocalizedText,
  rule_id: z.string().optional(),
});
export type LabOrder = z.infer<typeof LabOrder>;

/** GLP-1 dosing decision from the Pharmacist Agent. */
export const Glp1DosingDecision = z.enum(["HOLD", "CONTINUE", "CAUTION"]);
export type Glp1DosingDecision = z.infer<typeof Glp1DosingDecision>;

/**
 * Pharmacist forecast — the reasoning layer on top of the rules:
 * what to do with the GLP-1 now, what risks are coming, and which chronic meds
 * need adjustment given the altered PK.
 */
export const PharmacistForecast = z.object({
  glp1_dosing: Glp1DosingDecision,
  glp1_rationale: LocalizedText,
  /** Risks not yet active but expected (e.g. at next escalation). */
  future_risks: z.array(
    z.object({
      text: LocalizedText,
      rule_id: z.string().optional(),
    }),
  ).default([]),
  /** Concrete chronic-medication adjustments (route/form/timing/monitoring). */
  chronic_med_adjustments: z.array(ActionItem).default([]),
});
export type PharmacistForecast = z.infer<typeof PharmacistForecast>;

/** Provenance stamped on every output, mirrored into the audit log. */
export const OutputMeta = z.object({
  assessment_id: z.string().min(1),
  case_id: z.string().min(1),
  generated_at: IsoTimestamp,
  rule_pack_version: z.string().min(1),
  drug_master_version: z.string().min(1),
  sign_off: SignOffRecord,
});
export type OutputMeta = z.infer<typeof OutputMeta>;

/**
 * Full output (admin layer). Physician/patient views are narrowings of this —
 * see ViewLayer and the projection contract in engine/src/projection.ts.
 */
export const EngineOutput = z.object({
  meta: OutputMeta,
  triage: TriageResult,
  risk_flags: z.array(RiskFlag).default([]),
  clinician_actions: z.array(ActionItem).default([]),
  patient_actions: z.array(ActionItem).default([]),
  lab_plan: z.array(LabOrder).default([]),
  pharmacist_forecast: PharmacistForecast,
  /** Admin/research-only: internal pattern names that fired. Never projected to others. */
  internal_patterns: z.array(z.string()).default([]),
});
export type EngineOutput = z.infer<typeof EngineOutput>;

/** Audience for a projected output. */
export const ViewLayer = z.enum(["admin", "research", "physician", "patient"]);
export type ViewLayer = z.infer<typeof ViewLayer>;
