import type { Locale } from "../schemas/enums.js";
import type { Dictionary } from "./keys.js";
import { ru } from "./locales/ru.js";
import { en } from "./locales/en.js";
import { he } from "./locales/he.js";

export * from "./keys.js";

/** All dictionaries keyed by locale. */
export const dictionaries: Record<Locale, Dictionary> = { ru, en, he };

export function dictionaryFor(locale: Locale): Dictionary {
  return dictionaries[locale];
}
