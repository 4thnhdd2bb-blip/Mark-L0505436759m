/**
 * Persistence + audit schemas.
 *
 * Firestore equivalents of the v4 SQLAlchemy data model (Patient / Visit /
 * MedicationSnapshot / RuleTrigger / SignOff / AuditLog). Each assessment is one
 * Visit storing the FULL input + output snapshot, version-pinned, immutable once
 * signed. The White Coat Rule lives in SignOffRecord; everything is auditable.
 */
import { z } from "zod";
import {
  IsoTimestamp,
  TriageColor,
  GLP1Decision,
  SignOffStatus,
  AuditEventType,
  UserRole,
} from "./enums.js";
import { PatientContext } from "./patient.js";
import { PharmacistAssessment } from "./assessment.js";

/** Denormalized medication snapshot for fast querying. */
export const MedicationSnapshot = z.object({
  name: z.string(),
  profile_id: z.string(),
  route: z.string().default("oral"),
  dose: z.string().nullable().optional(),
  is_essential: z.boolean().default(false),
});
export type MedicationSnapshot = z.infer<typeof MedicationSnapshot>;

/** Audit: one record per rule that fired during a visit. */
export const RuleTrigger = z.object({
  rule_id: z.string(),
  rule_pack_version: z.string(),
  medication_name: z.string(),
  medication_profile_id: z.string(),
  severity: z.string(),
  evidence_grade: z.string(),
  triggered_at: IsoTimestamp,
});
export type RuleTrigger = z.infer<typeof RuleTrigger>;

/** White Coat Rule sign-off record. */
export const SignOffRecord = z.object({
  status: SignOffStatus,
  physician_id: z.string().optional(),
  physician_name: z.string().optional(),
  notes: z.string().nullable().optional(),
  signed_at: IsoTimestamp.optional(),
  /** Physician edits applied at sign-off (status === "amended"). */
  amended_payload: z.unknown().optional(),
});
export type SignOffRecord = z.infer<typeof SignOffRecord>;

/** One assessment session. Stores exact input + output, version-pinned. */
export const Visit = z.object({
  visit_id: z.string(),
  patient_id: z.string(),
  input_payload: PatientContext,
  output_payload: PharmacistAssessment,
  triage_color: TriageColor,
  glp1_decision: GLP1Decision,
  sign_off: SignOffRecord,
  rule_pack_version: z.string(),
  drug_db_version: z.string(),
  agent_version: z.string().default("2.0.0"),
  medication_snapshots: z.array(MedicationSnapshot).default([]),
  rule_triggers: z.array(RuleTrigger).default([]),
  created_at: IsoTimestamp,
});
export type Visit = z.infer<typeof Visit>;

/** Append-only audit log entry (SaMD traceability). */
export const AuditLogEntry = z.object({
  id: z.string(),
  event_type: AuditEventType,
  actor_id: z.string().nullable().optional(),
  actor_role: UserRole.nullable().optional(),
  target_table: z.string().nullable().optional(),
  target_id: z.string().nullable().optional(),
  payload: z.record(z.string(), z.unknown()).nullable().optional(),
  occurred_at: IsoTimestamp,
});
export type AuditLogEntry = z.infer<typeof AuditLogEntry>;
