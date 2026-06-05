/**
 * Assessment output models — ported from the v4 PharmacistAssessment family.
 *
 * Every user-facing string is an i18n key (resolved per-locale at the edge).
 * The full assessment is the admin layer; physician/patient views are narrowings
 * produced by the engine's `project()` (dual-layer). `admin_trace` is the
 * METACOD-internal terminology and appears ONLY in the admin/research layer.
 */
import { z } from "zod";
import { EvidenceGrade, RiskLevel, TriageColor, GLP1Decision, SignOffStatus } from "./enums.js";

export const I18nAction = z.object({
  i18n_key: z.string(),
  evidence_grade: EvidenceGrade,
  rule_id: z.string().nullable().optional(),
});
export type I18nAction = z.infer<typeof I18nAction>;

export const LabRecommendation = z.object({
  test: z.string(),
  interval_weeks: z.number().int(),
  i18n_key: z.string(),
  rule_id: z.string().nullable().optional(),
});
export type LabRecommendation = z.infer<typeof LabRecommendation>;

/** Hidden admin/research layer — internal pattern terminology, never shown to patient. */
export const AdminTrace = z.object({
  rule_id: z.string(),
  pattern: z.string(),
  i18n_key_internal: z.string(),
  mechanism: z.string(),
});
export type AdminTrace = z.infer<typeof AdminTrace>;

export const InteractionFinding = z.object({
  rule_id: z.string(),
  rule_name: z.string(),
  medication_name: z.string(),
  medication_profile_id: z.string().default(""),
  severity: z.string(),
  underexposure_risk: RiskLevel.default("low"),
  overexposure_risk: RiskLevel.default("low"),
  delayed_onset_risk: RiskLevel.default("low"),
  net_pk_variability: RiskLevel.default("low"),
  evidence_grade: EvidenceGrade,
  sources: z.array(z.string()).default([]),
  physician_actions: z.array(I18nAction).default([]),
  patient_actions: z.array(I18nAction).default([]),
  lab_plan: z.array(LabRecommendation).default([]),
  admin_trace: AdminTrace,
});
export type InteractionFinding = z.infer<typeof InteractionFinding>;

export const GLP1DosingRecommendation = z.object({
  decision: GLP1Decision,
  i18n_key: z.string(),
  rationale_i18n_keys: z.array(z.string()).default([]),
  evidence_grade: EvidenceGrade,
});
export type GLP1DosingRecommendation = z.infer<typeof GLP1DosingRecommendation>;

export const FutureRisk = z.object({
  i18n_key: z.string(),
  timeframe_weeks: z.number().int(),
  evidence_grade: EvidenceGrade,
  rule_id: z.string().nullable().optional(),
});
export type FutureRisk = z.infer<typeof FutureRisk>;

export const ChronicMedAdjustment = z.object({
  medication_name: z.string(),
  adjustment_i18n_key: z.string(),
  trigger_i18n_key: z.string(),
  timeframe_weeks: z.number().int(),
  evidence_grade: EvidenceGrade,
});
export type ChronicMedAdjustment = z.infer<typeof ChronicMedAdjustment>;

export const ClinicalForecast = z.object({
  glp1_dosing: GLP1DosingRecommendation,
  future_risks: z.array(FutureRisk).default([]),
  chronic_med_adjustments: z.array(ChronicMedAdjustment).default([]),
});
export type ClinicalForecast = z.infer<typeof ClinicalForecast>;

export const PharmacistAssessment = z.object({
  patient_id: z.string(),
  triage_color: TriageColor,
  triage_summary_i18n_key: z.string(),
  interactions: z.array(InteractionFinding).default([]),
  forecast: ClinicalForecast,
  rule_pack_version: z.string(),
  drug_db_version: z.string(),
  sign_off_status: SignOffStatus.default("pending_sign_off"),
});
export type PharmacistAssessment = z.infer<typeof PharmacistAssessment>;
