/**
 * Firebase Cloud Functions binding — the ONLY place that touches infrastructure.
 * It builds the Deps from Firestore + node crypto and exposes the three callable
 * endpoints. Pure logic lives in api.ts; engine logic in @metacod/engine.
 *
 * PART 1 STATUS: wiring + Firestore-backed ports. Firestore security rules,
 * content seeding (rule_pack/drug_master docs) and indexes are finalised in Part 2.
 */
import { createHash, randomUUID } from "node:crypto";
import { initializeApp } from "firebase-admin/app";
import { getFirestore } from "firebase-admin/firestore";
import { onCall, HttpsError, type CallableRequest } from "firebase-functions/v2/https";
import { RulePack, DrugProfile, type SignOffRecord } from "@metacod/shared";
import {
  handleAssess,
  handleSignOff,
  handleGetReport,
} from "./api.js";
import type { Actor, Deps, AssessmentRecord, AuditSink } from "./ports.js";

initializeApp();
const db = getFirestore();

/** Deterministic JSON canonicalisation (sorted keys) for stable audit hashes. */
function canonical(value: unknown): string {
  return JSON.stringify(value, (_k, v) =>
    v && typeof v === "object" && !Array.isArray(v)
      ? Object.fromEntries(Object.entries(v as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b)))
      : v,
  );
}

const deps: Deps = {
  content: {
    async getActiveRulePack() {
      const snap = await db.collection("content").doc("active_rule_pack").get();
      const data = snap.data();
      if (!data) throw new HttpsError("failed-precondition", "No active rule pack configured.");
      return { pack: RulePack.parse(data.pack), version: String(data.version) };
    },
    async getDrugMaster() {
      const snap = await db.collection("content").doc("active_drug_master").get();
      const data = snap.data();
      if (!data) throw new HttpsError("failed-precondition", "No active drug master configured.");
      return { profiles: z_parseProfiles(data.profiles), version: String(data.version) };
    },
  },
  store: {
    async save(record: AssessmentRecord) {
      await db.collection("assessments").doc(record.assessment_id).set(record);
    },
    async get(id: string) {
      const snap = await db.collection("assessments").doc(id).get();
      return (snap.data() as AssessmentRecord | undefined) ?? null;
    },
    async updateSignOff(id: string, signOff: SignOffRecord) {
      await db.collection("assessments").doc(id).update({ "output.meta.sign_off": signOff });
    },
  },
  audit: {
    async append(entry) {
      await db.collection("audit_log").doc(entry.id).set(entry);
    },
  } satisfies AuditSink,
  clock: { nowIso: () => new Date().toISOString() },
  ids: { newId: () => randomUUID() },
  hasher: { sha256: (v: unknown) => createHash("sha256").update(canonical(v)).digest("hex") },
};

function z_parseProfiles(raw: unknown): DrugProfile[] {
  if (!Array.isArray(raw)) throw new HttpsError("failed-precondition", "drug_master must be an array.");
  return raw.map((p) => DrugProfile.parse(p));
}

/** Extract the authenticated actor (role from custom claims). */
function actorOf(request: CallableRequest): Actor {
  const auth = request.auth;
  if (!auth) throw new HttpsError("unauthenticated", "Authentication required.");
  const role = (auth.token.role as Actor["role"] | undefined) ?? undefined;
  if (!role) throw new HttpsError("permission-denied", "No role claim on user.");
  return { user_id: auth.uid, role };
}

/** Translate handler errors (string-coded) into typed HttpsError responses. */
function wrap<T>(fn: () => Promise<T>): Promise<T> {
  return fn().catch((e: unknown) => {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.startsWith("FORBIDDEN")) throw new HttpsError("permission-denied", msg);
    if (msg.startsWith("NOT_FOUND")) throw new HttpsError("not-found", msg);
    if (msg.startsWith("FAILED_PRECONDITION")) throw new HttpsError("failed-precondition", msg);
    if (msg.startsWith("INVALID_ARGUMENT")) throw new HttpsError("invalid-argument", msg);
    throw new HttpsError("internal", msg);
  });
}

export const assessPatient = onCall((request) =>
  wrap(() => handleAssess(request.data, deps, actorOf(request))),
);

export const signOffAssessment = onCall((request) =>
  wrap(() => handleSignOff(request.data, deps, actorOf(request))),
);

export const getReport = onCall((request) =>
  wrap(() => handleGetReport(request.data, deps, actorOf(request))),
);
