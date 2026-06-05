/**
 * Firebase Cloud Functions binding — the ONLY place that touches infrastructure.
 * Builds Deps from Firestore + node crypto and exposes the three callable
 * endpoints. Pure logic lives in api.ts; clinical logic in @metacod/engine.
 *
 * Firestore collections:
 *   visits/{visit_id}      — full input+output snapshot, version-pinned, sign-off state
 *   audit_log/{id}         — append-only event log
 * Security rules + content management UI are finalised alongside the admin app.
 */
import { createHash, randomUUID } from "node:crypto";
import { initializeApp } from "firebase-admin/app";
import { getFirestore } from "firebase-admin/firestore";
import { onCall, HttpsError, type CallableRequest } from "firebase-functions/v2/https";
import type { Visit, SignOffRecord } from "@metacod/shared";
import { handleAssess, handleSignOff, handleGetReport } from "./api.js";
import type { Actor, Deps } from "./ports.js";

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
  store: {
    async save(visit: Visit) {
      await db.collection("visits").doc(visit.visit_id).set(visit);
    },
    async get(visit_id: string) {
      const snap = await db.collection("visits").doc(visit_id).get();
      return (snap.data() as Visit | undefined) ?? null;
    },
    async updateSignOff(visit_id: string, signOff: SignOffRecord) {
      await db.collection("visits").doc(visit_id).update({
        sign_off: signOff,
        "output_payload.sign_off_status": signOff.status,
      });
    },
  },
  audit: {
    async append(entry) {
      await db.collection("audit_log").doc(entry.id).set(entry);
    },
  },
  clock: { nowIso: () => new Date().toISOString() },
  ids: { newId: (prefix: string) => `${prefix}-${randomUUID()}` },
  hasher: { sha256: (v: unknown) => createHash("sha256").update(canonical(v)).digest("hex") },
};

/** Extract the authenticated actor (role from custom claims). */
function actorOf(request: CallableRequest): Actor {
  const auth = request.auth;
  if (!auth) throw new HttpsError("unauthenticated", "Authentication required.");
  const role = auth.token.role as Actor["role"] | undefined;
  if (!role) throw new HttpsError("permission-denied", "No role claim on user.");
  const name = auth.token.name as string | undefined;
  return { user_id: auth.uid, role, ...(name ? { user_name: name } : {}) };
}

/** Translate string-coded handler errors into typed HttpsError responses. */
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

export const assessPatient = onCall((request) => wrap(() => handleAssess(request.data, deps, actorOf(request))));
export const signOffAssessment = onCall((request) => wrap(() => handleSignOff(request.data, deps, actorOf(request))));
export const getReport = onCall((request) => wrap(() => handleGetReport(request.data, deps, actorOf(request))));
