/**
 * Common primitives shared across every schema in the GLP-1 module.
 *
 * These mirror the role Pydantic base types played in v4, but as zod schemas so
 * the SAME definition gives us (a) runtime validation on the Firebase server and
 * (b) static TypeScript types on the Expo client via `z.infer`.
 */
import { z } from "zod";

/**
 * Evidence grading used on every clinical rule and recommendation.
 *  A — RCT / guideline / strong PK evidence.
 *  B — cohort / mechanistic PK with clinical corroboration.
 *  C — case reports / expert consensus / first-principles mechanism only.
 * The full rubric is defined in Part 3.
 */
export const EvidenceGrade = z.enum(["A", "B", "C"]);
export type EvidenceGrade = z.infer<typeof EvidenceGrade>;

/** Supported locales. Hebrew is rendered RTL — see `isRtl` in i18n/keys.ts. */
export const Locale = z.enum(["ru", "en", "he"]);
export type Locale = z.infer<typeof Locale>;

/** ISO-8601 timestamp string (UTC). Stored verbatim in audit log. */
export const IsoTimestamp = z.string().datetime({ offset: true });
export type IsoTimestamp = z.infer<typeof IsoTimestamp>;

/** Opaque identifier helpers. Branding keeps ids from being mixed up at compile time. */
export const Id = z.string().min(1);
export type Id = z.infer<typeof Id>;

/**
 * A literature/guideline source attached to a rule or a drug property.
 * `url` is optional because some sources are print-only references.
 */
export const Source = z.object({
  citation: z.string().min(1),
  url: z.string().url().optional(),
  /** PubMed id / DOI / guideline code, when available, for traceability. */
  ref_id: z.string().optional(),
});
export type Source = z.infer<typeof Source>;

/**
 * A user-facing string is NEVER a raw literal anywhere in the engine output.
 * It is always an i18n key plus optional interpolation params, resolved by the
 * client/PDF layer per locale. This is what keeps the module trilingual and lets
 * the same EngineOutput render RU/EN/HE.
 */
export const LocalizedText = z.object({
  key: z.string().min(1),
  params: z.record(z.union([z.string(), z.number()])).optional(),
});
export type LocalizedText = z.infer<typeof LocalizedText>;

/** Severity scale reused by risks and rules. */
export const Severity = z.enum(["low", "moderate", "high"]);
export type Severity = z.infer<typeof Severity>;
