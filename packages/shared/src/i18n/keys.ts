/**
 * i18n contract for the whole module.
 *
 * Every user-facing string is a KEY resolved per-locale at the edge (Expo client
 * or PDF generator). The engine never emits localized prose. Hebrew is RTL.
 */
import { Locale } from "../schemas/common.js";

export const LOCALES = ["ru", "en", "he"] as const;

/** Right-to-left locales. The UI flips layout direction when this is true. */
const RTL_LOCALES = new Set<Locale>(["he"]);
export function isRtl(locale: Locale): boolean {
  return RTL_LOCALES.has(locale);
}

/** Text direction helper for React Native style (`writingDirection` / `direction`). */
export function direction(locale: Locale): "ltr" | "rtl" {
  return isRtl(locale) ? "rtl" : "ltr";
}

/**
 * A locale dictionary maps i18n keys to template strings. Templates may contain
 * {param} placeholders interpolated from LocalizedText.params.
 */
export type Dictionary = Record<string, string>;

/** Resolve a key+params against a dictionary, with a visible fallback on miss. */
export function resolve(
  dict: Dictionary,
  key: string,
  params?: Record<string, string | number>,
): string {
  const template = dict[key];
  if (template === undefined) return `⟦${key}⟧`; // visible so missing keys are caught in QA
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (_, name: string) =>
    name in params ? String(params[name]) : `{${name}}`,
  );
}
