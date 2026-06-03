/**
 * Ports (dependency-inversion interfaces). Pure API handlers depend on these,
 * not on Firestore/clock/crypto directly, so they are unit-testable and the
 * Firebase wiring (index.ts) is the only place that touches infrastructure.
 */
import type { Visit, SignOffRecord, AuditLogEntry, UserRole } from "@metacod/shared";

/** Persistence for visits (one per assessment; immutable snapshot, version-pinned). */
export interface VisitStore {
  save(visit: Visit): Promise<void>;
  get(visit_id: string): Promise<Visit | null>;
  updateSignOff(visit_id: string, signOff: SignOffRecord): Promise<void>;
}

/** Append-only audit sink (immutable). */
export interface AuditSink {
  append(entry: AuditLogEntry): Promise<void>;
}

export interface Clock {
  nowIso(): string;
}

export interface IdGen {
  newId(prefix: string): string;
}

export interface Hasher {
  /** Canonicalises + SHA-256-hashes a value for audit snapshots. */
  sha256(value: unknown): string;
}

/** The authenticated caller. Drives the dual-layer projection and authz. */
export interface Actor {
  user_id: string;
  user_name?: string;
  role: UserRole;
}

export interface Deps {
  store: VisitStore;
  audit: AuditSink;
  clock: Clock;
  ids: IdGen;
  hasher: Hasher;
}
