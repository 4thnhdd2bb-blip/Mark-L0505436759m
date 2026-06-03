/**
 * Audit + White Coat Rule.
 *
 * SaMD Class IIa requires that every assessment is reproducible and that no
 * machine output reaches an EHR without an explicit physician signature. The
 * sign-off state machine and the immutable audit record live here.
 */
import { z } from "zod";
import { IsoTimestamp } from "./common.js";

/**
 * White Coat Rule state machine:
 *   pending_sign_off --sign--> signed --export--> EHR
 *   pending_sign_off --reject--> rejected (with reason)
 * `signed` is the ONLY state from which a report may be exported to an EHR.
 */
export const SignOffState = z.enum(["pending_sign_off", "signed", "rejected"]);
export type SignOffState = z.infer<typeof SignOffState>;

export const SignOffRecord = z.object({
  state: SignOffState,
  /** Physician who acted. Required once state leaves pending_sign_off. */
  physician_id: z.string().optional(),
  signed_at: IsoTimestamp.optional(),
  /** How the signature was captured (for medico-legal traceability). */
  method: z.enum(["password", "biometric", "sso", "manual"]).optional(),
  /** Mandatory free-text reason when state === "rejected". */
  rejection_reason: z.string().optional(),
});
export type SignOffRecord = z.infer<typeof SignOffRecord>;

/** Roles that interact with the system — gates the dual-layer projection too. */
export const UserRole = z.enum(["physician", "pharmacist", "admin", "researcher"]);
export type UserRole = z.infer<typeof UserRole>;

/**
 * Immutable audit log entry. We store hashes of the input/output snapshots plus
 * the rule_pack version so a past decision can be reproduced and defended.
 */
export const AuditLogEntry = z.object({
  id: z.string().min(1),
  assessment_id: z.string().min(1),
  case_id: z.string().min(1),
  timestamp: IsoTimestamp,
  user_id: z.string().min(1),
  role: UserRole,
  action: z.enum(["assess", "sign_off", "reject", "export", "view"]),
  rule_pack_version: z.string().min(1),
  drug_master_version: z.string().min(1),
  /** SHA-256 of the canonicalised input/output JSON (full snapshots kept separately). */
  input_hash: z.string().min(1),
  output_hash: z.string().min(1),
});
export type AuditLogEntry = z.infer<typeof AuditLogEntry>;
