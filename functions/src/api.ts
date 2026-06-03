/**
 * API handlers — pure, transport-agnostic. index.ts binds these to Firebase
 * callable functions. Each handler validates input with zod, enforces the White
 * Coat Rule / authz, writes audit records, and returns a role-projected result.
 * Clinical content is bundled + version-pinned with the engine (loadContent).
 */
import { z } from "zod";
import { PatientContext, Locale, ViewLayer } from "@metacod/shared";
import type {
  Visit,
  SignOffRecord,
  ViewLayer as ViewLayerT,
  UserRole,
  PharmacistAssessment,
  MedicationSnapshot,
  RuleTrigger,
} from "@metacod/shared";
import { assess, project, loadContent, AGENT_VERSION } from "@metacod/engine";
import type { Actor, Deps } from "./ports.js";

/** Map an actor role to the default projection layer. */
function roleToLayer(role: UserRole): ViewLayerT {
  switch (role) {
    case "admin":
      return "admin";
    case "researcher":
      return "research";
    case "physician":
    case "pharmacist":
      return "physician";
  }
}

// ---------- assessPatient ----------

export const AssessRequest = z.object({ input: PatientContext });
export type AssessRequest = z.infer<typeof AssessRequest>;

export interface AssessResponse {
  visit_id: string;
  view: ViewLayerT;
  assessment: PharmacistAssessment; // projected for the caller's role
}

export async function handleAssess(raw: unknown, deps: Deps, actor: Actor): Promise<AssessResponse> {
  const { input } = AssessRequest.parse(raw);
  const { rulePack, drugMaster } = loadContent();

  const full = assess(input, rulePack, drugMaster);
  const visit_id = deps.ids.newId("VIS");
  const now = deps.clock.nowIso();

  const medication_snapshots: MedicationSnapshot[] = input.medications.map((m) => ({
    name: m.name,
    profile_id: m.profile_id,
    route: m.route,
    ...(m.dose != null ? { dose: m.dose } : {}),
    is_essential: m.is_essential,
  }));

  const rule_triggers: RuleTrigger[] = full.interactions.map((f) => ({
    rule_id: f.rule_id,
    rule_pack_version: full.rule_pack_version,
    medication_name: f.medication_name,
    medication_profile_id: f.medication_profile_id,
    severity: f.severity,
    evidence_grade: f.evidence_grade,
    triggered_at: now,
  }));

  const visit: Visit = {
    visit_id,
    patient_id: input.patient_id,
    input_payload: input,
    output_payload: full, // store FULL admin-layer output; project on read
    triage_color: full.triage_color,
    glp1_decision: full.forecast.glp1_dosing.decision,
    sign_off: { status: "pending_sign_off" },
    rule_pack_version: full.rule_pack_version,
    drug_db_version: full.drug_db_version,
    agent_version: AGENT_VERSION,
    medication_snapshots,
    rule_triggers,
    created_at: now,
  };

  await deps.store.save(visit);
  await deps.audit.append({
    id: deps.ids.newId("AUD"),
    event_type: "assessment_created",
    actor_id: actor.user_id,
    actor_role: actor.role,
    target_table: "visits",
    target_id: visit_id,
    payload: {
      triage: full.triage_color,
      rule_count: full.interactions.length,
      rule_pack_version: full.rule_pack_version,
      drug_db_version: full.drug_db_version,
      input_hash: deps.hasher.sha256(input),
      output_hash: deps.hasher.sha256(full),
    },
    occurred_at: now,
  });

  const view = roleToLayer(actor.role);
  return { visit_id, view, assessment: project(full, view) };
}

// ---------- signOffAssessment (White Coat Rule) ----------

export const SignOffRequest = z.object({
  visit_id: z.string().min(1),
  decision: z.enum(["sign", "reject", "amend"]),
  notes: z.string().optional(),
  amended_payload: z.unknown().optional(),
});
export type SignOffRequest = z.infer<typeof SignOffRequest>;

export interface SignOffResponse {
  visit_id: string;
  sign_off: SignOffRecord;
}

export async function handleSignOff(raw: unknown, deps: Deps, actor: Actor): Promise<SignOffResponse> {
  const req = SignOffRequest.parse(raw);

  // White Coat Rule: only a physician may sign off / amend / reject.
  if (actor.role !== "physician") {
    throw new Error("FORBIDDEN: only a physician may sign off an assessment.");
  }
  if (req.decision === "reject" && !req.notes) {
    throw new Error("INVALID_ARGUMENT: notes (reason) required when rejecting.");
  }

  const visit = await deps.store.get(req.visit_id);
  if (!visit) throw new Error("NOT_FOUND: visit does not exist.");
  if (visit.sign_off.status !== "pending_sign_off") {
    throw new Error(`FAILED_PRECONDITION: visit is already ${visit.sign_off.status}.`);
  }

  const now = deps.clock.nowIso();
  const status = req.decision === "sign" ? "signed" : req.decision === "amend" ? "amended" : "rejected";
  const sign_off: SignOffRecord = {
    status,
    physician_id: actor.user_id,
    ...(actor.user_name ? { physician_name: actor.user_name } : {}),
    signed_at: now,
    ...(req.notes != null ? { notes: req.notes } : {}),
    ...(req.decision === "amend" && req.amended_payload !== undefined
      ? { amended_payload: req.amended_payload }
      : {}),
  };

  await deps.store.updateSignOff(req.visit_id, sign_off);
  await deps.audit.append({
    id: deps.ids.newId("AUD"),
    event_type: req.decision === "reject" ? "sign_off_rejected" : "sign_off_completed",
    actor_id: actor.user_id,
    actor_role: actor.role,
    target_table: "visits",
    target_id: req.visit_id,
    payload: { status, notes: req.notes ?? null },
    occurred_at: now,
  });

  return { visit_id: req.visit_id, sign_off };
}

// ---------- getReport ----------

export const GetReportRequest = z.object({
  visit_id: z.string().min(1),
  locale: Locale,
  view: ViewLayer,
});
export type GetReportRequest = z.infer<typeof GetReportRequest>;

export interface GetReportResponse {
  visit_id: string;
  locale: z.infer<typeof Locale>;
  view: ViewLayerT;
  assessment: PharmacistAssessment; // projected; client/PDF layer resolves i18n keys
}

export async function handleGetReport(raw: unknown, deps: Deps, actor: Actor): Promise<GetReportResponse> {
  const req = GetReportRequest.parse(raw);
  const visit = await deps.store.get(req.visit_id);
  if (!visit) throw new Error("NOT_FOUND: visit does not exist.");

  // A patient-facing report may only be produced from a SIGNED assessment.
  if (req.view === "patient" && visit.sign_off.status !== "signed") {
    throw new Error("FAILED_PRECONDITION: patient report requires a signed assessment.");
  }
  if ((req.view === "admin" || req.view === "research") && !(actor.role === "admin" || actor.role === "researcher")) {
    throw new Error("FORBIDDEN: insufficient role for this view.");
  }

  await deps.audit.append({
    id: deps.ids.newId("AUD"),
    event_type: "report_exported",
    actor_id: actor.user_id,
    actor_role: actor.role,
    target_table: "visits",
    target_id: req.visit_id,
    payload: { view: req.view, locale: req.locale },
    occurred_at: deps.clock.nowIso(),
  });

  return {
    visit_id: req.visit_id,
    locale: req.locale,
    view: req.view,
    assessment: project(visit.output_payload, req.view),
  };
}
