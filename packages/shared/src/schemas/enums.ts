/**
 * Enumerations shared across the GLP-1 module. These mirror the v4 Pydantic enums
 * 1:1 so the ported clinical content (rule_pack_v1 / drug_master_v1) and the i18n
 * keys line up exactly. As zod enums they give runtime validation on the Firebase
 * server and static types on the Expo client via z.infer.
 */
import { z } from "zod";

/** Evidence grading on every rule and recommendation. */
export const EvidenceGrade = z.enum(["A", "B", "C"]);
//  A = regulatory label or RCT
//  B = multiple observational + mechanistic
//  C = mechanistic / expert consensus only
export type EvidenceGrade = z.infer<typeof EvidenceGrade>;

/** Per-axis PK risk magnitude. */
export const RiskLevel = z.enum(["low", "moderate", "high"]);
export type RiskLevel = z.infer<typeof RiskLevel>;

/** Triage gate output. */
export const TriageColor = z.enum(["green", "yellow", "red"]);
export type TriageColor = z.infer<typeof TriageColor>;

/** GLP-1 dosing decision from the Pharmacist Agent. */
export const GLP1Decision = z.enum(["CONTINUE", "HOLD", "REVIEW"]);
export type GLP1Decision = z.infer<typeof GLP1Decision>;

/** White Coat Rule sign-off state machine. */
export const SignOffStatus = z.enum(["pending_sign_off", "signed", "rejected", "amended"]);
export type SignOffStatus = z.infer<typeof SignOffStatus>;

/** Append-only audit event taxonomy. */
export const AuditEventType = z.enum([
  "assessment_created",
  "sign_off_requested",
  "sign_off_completed",
  "sign_off_rejected",
  "report_exported",
  "rule_pack_updated",
  "drug_db_updated",
]);
export type AuditEventType = z.infer<typeof AuditEventType>;

/** Roles that interact with the system — drive dual-layer projection + authz. */
export const UserRole = z.enum(["physician", "pharmacist", "admin", "researcher"]);
export type UserRole = z.infer<typeof UserRole>;

/** Supported locales. Hebrew renders RTL — see i18n/keys.ts. */
export const Locale = z.enum(["ru", "en", "he"]);
export type Locale = z.infer<typeof Locale>;

/** Audience for a projected assessment (dual-layer). */
export const ViewLayer = z.enum(["admin", "research", "physician", "patient"]);
export type ViewLayer = z.infer<typeof ViewLayer>;

/** ISO-8601 timestamp string (UTC). */
export const IsoTimestamp = z.string().datetime({ offset: true });
export type IsoTimestamp = z.infer<typeof IsoTimestamp>;
