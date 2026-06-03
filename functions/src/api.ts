/**
 * API handlers — pure, transport-agnostic. index.ts binds these to Firebase
 * callable functions. Each handler validates input with zod, enforces the
 * White Coat Rule / authz, writes an audit record, and returns a role-projected
 * result. Persistence/clock/crypto come via Deps (ports.ts).
 */
import { z } from "zod";
import { PatientInput, Locale, ViewLayer } from "@metacod/shared";
import type { EngineOutput, SignOffRecord, ViewLayer as ViewLayerT } from "@metacod/shared";
import { assess, project } from "@metacod/engine";
import type { Actor, Deps } from "./ports.js";

/** Map an actor role to the default projection layer. */
function roleToLayer(role: Actor["role"]): ViewLayerT {
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

export const AssessRequest = z.object({
  input: PatientInput,
});
export type AssessRequest = z.infer<typeof AssessRequest>;

export interface AssessResponse {
  assessment_id: string;
  view: ViewLayerT;
  output: EngineOutput; // already projected for the caller's role
}

export async function handleAssess(raw: unknown, deps: Deps, actor: Actor): Promise<AssessResponse> {
  const { input } = AssessRequest.parse(raw);

  const [{ pack, version: ruleVersion }, { profiles, version: drugVersion }] = await Promise.all([
    deps.content.getActiveRulePack(),
    deps.content.getDrugMaster(),
  ]);

  const assessment_id = deps.ids.newId();
  const generated_at = deps.clock.nowIso();

  const full = assess(input, pack, profiles, {
    assessment_id,
    generated_at,
    rule_pack_version: ruleVersion,
    drug_master_version: drugVersion,
  });

  await deps.store.save({
    assessment_id,
    case_id: input.case_id,
    input,
    output: full, // store the FULL admin-layer output; project on read
    created_at: generated_at,
  });

  await deps.audit.append({
    id: deps.ids.newId(),
    assessment_id,
    case_id: input.case_id,
    timestamp: generated_at,
    user_id: actor.user_id,
    role: actor.role,
    action: "assess",
    rule_pack_version: ruleVersion,
    drug_master_version: drugVersion,
    input_hash: deps.hasher.sha256(input),
    output_hash: deps.hasher.sha256(full),
  });

  const view = roleToLayer(actor.role);
  return { assessment_id, view, output: project(full, view) };
}

// ---------- signOffAssessment (White Coat Rule) ----------

export const SignOffRequest = z.object({
  assessment_id: z.string().min(1),
  decision: z.enum(["sign", "reject"]),
  method: z.enum(["password", "biometric", "sso", "manual"]),
  rejection_reason: z.string().min(1).optional(),
});
export type SignOffRequest = z.infer<typeof SignOffRequest>;

export interface SignOffResponse {
  assessment_id: string;
  sign_off: SignOffRecord;
}

export async function handleSignOff(raw: unknown, deps: Deps, actor: Actor): Promise<SignOffResponse> {
  const req = SignOffRequest.parse(raw);

  // Authz: only a physician may sign off (White Coat Rule).
  if (actor.role !== "physician") {
    throw new Error("FORBIDDEN: only a physician may sign off an assessment.");
  }
  if (req.decision === "reject" && !req.rejection_reason) {
    throw new Error("INVALID_ARGUMENT: rejection_reason is required when rejecting.");
  }

  const record = await deps.store.get(req.assessment_id);
  if (!record) throw new Error("NOT_FOUND: assessment does not exist.");

  // Transition is only legal from pending_sign_off.
  if (record.output.meta.sign_off.state !== "pending_sign_off") {
    throw new Error(`FAILED_PRECONDITION: assessment is already ${record.output.meta.sign_off.state}.`);
  }

  const now = deps.clock.nowIso();
  const sign_off: SignOffRecord =
    req.decision === "sign"
      ? { state: "signed", physician_id: actor.user_id, signed_at: now, method: req.method }
      : {
          state: "rejected",
          physician_id: actor.user_id,
          signed_at: now,
          method: req.method,
          rejection_reason: req.rejection_reason!,
        };

  await deps.store.updateSignOff(req.assessment_id, sign_off);

  await deps.audit.append({
    id: deps.ids.newId(),
    assessment_id: req.assessment_id,
    case_id: record.case_id,
    timestamp: now,
    user_id: actor.user_id,
    role: actor.role,
    action: req.decision === "sign" ? "sign_off" : "reject",
    rule_pack_version: record.output.meta.rule_pack_version,
    drug_master_version: record.output.meta.drug_master_version,
    input_hash: deps.hasher.sha256(record.input),
    output_hash: deps.hasher.sha256(record.output),
  });

  return { assessment_id: req.assessment_id, sign_off };
}

// ---------- getReport ----------

export const GetReportRequest = z.object({
  assessment_id: z.string().min(1),
  locale: Locale,
  /** Requested audience. Patient handouts require a signed assessment. */
  view: ViewLayer,
});
export type GetReportRequest = z.infer<typeof GetReportRequest>;

export interface GetReportResponse {
  assessment_id: string;
  locale: z.infer<typeof Locale>;
  view: ViewLayerT;
  output: EngineOutput; // projected; client/PDF layer resolves i18n keys
}

export async function handleGetReport(raw: unknown, deps: Deps, actor: Actor): Promise<GetReportResponse> {
  const req = GetReportRequest.parse(raw);
  const record = await deps.store.get(req.assessment_id);
  if (!record) throw new Error("NOT_FOUND: assessment does not exist.");

  // A patient-facing report may only be produced from a SIGNED assessment.
  if (req.view === "patient" && record.output.meta.sign_off.state !== "signed") {
    throw new Error("FAILED_PRECONDITION: patient report requires a signed assessment.");
  }
  // Research/admin layers require the matching role.
  if ((req.view === "admin" || req.view === "research") && !(actor.role === "admin" || actor.role === "researcher")) {
    throw new Error("FORBIDDEN: insufficient role for this view.");
  }

  await deps.audit.append({
    id: deps.ids.newId(),
    assessment_id: req.assessment_id,
    case_id: record.case_id,
    timestamp: deps.clock.nowIso(),
    user_id: actor.user_id,
    role: actor.role,
    action: "view",
    rule_pack_version: record.output.meta.rule_pack_version,
    drug_master_version: record.output.meta.drug_master_version,
    input_hash: deps.hasher.sha256(record.input),
    output_hash: deps.hasher.sha256(record.output),
  });

  return {
    assessment_id: req.assessment_id,
    locale: req.locale,
    view: req.view,
    output: project(record.output, req.view),
  };
}
