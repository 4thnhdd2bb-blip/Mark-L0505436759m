/**
 * Ports (dependency-inversion interfaces). The pure API handlers depend on these,
 * not on Firestore/clock/crypto directly, so they are unit-testable and the
 * Firebase wiring (index.ts) is the only place that touches infrastructure.
 */
import type {
  PatientInput,
  EngineOutput,
  RulePack,
  DrugProfile,
  SignOffRecord,
  AuditLogEntry,
} from "@metacod/shared";

/** A persisted assessment, including the FULL (admin-layer) engine output. */
export interface AssessmentRecord {
  assessment_id: string;
  case_id: string;
  input: PatientInput;
  output: EngineOutput;
  created_at: string;
}

/** Loads the active, versioned clinical content. */
export interface ContentProvider {
  getActiveRulePack(): Promise<{ pack: RulePack; version: string }>;
  getDrugMaster(): Promise<{ profiles: DrugProfile[]; version: string }>;
}

/** Persistence for assessments. */
export interface AssessmentStore {
  save(record: AssessmentRecord): Promise<void>;
  get(assessment_id: string): Promise<AssessmentRecord | null>;
  updateSignOff(assessment_id: string, signOff: SignOffRecord): Promise<void>;
}

/** Append-only audit sink (immutable). */
export interface AuditSink {
  append(entry: AuditLogEntry): Promise<void>;
}

export interface Clock {
  nowIso(): string;
}

export interface IdGen {
  newId(): string;
}

export interface Hasher {
  /** Canonicalises + SHA-256-hashes an object for the audit snapshot. */
  sha256(value: unknown): string;
}

/** The authenticated caller. Drives the dual-layer projection and authz. */
export interface Actor {
  user_id: string;
  role: "physician" | "pharmacist" | "admin" | "researcher";
}

export interface Deps {
  content: ContentProvider;
  store: AssessmentStore;
  audit: AuditSink;
  clock: Clock;
  ids: IdGen;
  hasher: Hasher;
}
