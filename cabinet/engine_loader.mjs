/**
 * METACOD Cabinet — engine loader (Node, ESM).
 *
 * The cabinet (python/ui/cabinet.html, "METACOD — Кабинет") is a portable
 * single-file web app. Its differential engine and 350-entry treatment base
 * (DX_META / DX_NAMES / DB350 / SYMKW) plus the pure scoring/report functions
 * live inline so the page works offline.
 *
 * For the retroactive Clalit batch we must NOT duplicate those clinical
 * dosing tables (a transcription error in a dose is unacceptable). Instead we
 * read the cabinet file at runtime as the single source of truth and lift out
 * exactly the two delimited blocks the cabinet already marks:
 *
 *     // ===================== ДВИЖОК ДИФФЕРЕНЦИАЛА ... =====================
 *     ...                                       (DX_META, DX_NAMES, DB350,
 *     // ===================== /движок =====================   SYMKW, scoring,
 *                                                              report builders)
 *     // ===================== ОПРОСНИК СИМПТОМОВ ... =========
 *     ...                                       (SYMPTOMS, FULLQ, fq* helpers)
 *     // ===================== /опросник =====================
 *
 * These blocks are pure logic + data. The browser-only helpers they reference
 * (t, esc, LANG, document, …) are only used inside function bodies we never
 * call from the batch, so a tiny stub prelude is enough to evaluate the module.
 *
 * Result: the batch always scores with whatever is in the committed cabinet —
 * update the cabinet, the batch follows, zero divergence.
 */

import { readFile, writeFile, mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const ENGINE_START = "===================== ДВИЖОК ДИФФЕРЕНЦИАЛА";
const ENGINE_END = "===================== /движок";
const QUIZ_START = "===================== ОПРОСНИК СИМПТОМОВ";
const QUIZ_END = "===================== /опросник";

// Stub prelude: identity/no-op versions of the cabinet's browser globals so the
// extracted blocks evaluate. We only ever CALL the pure functions below.
const PRELUDE = `
var LANG = 'ru';
var t = (k) => String(k == null ? '' : k);
var esc = (s) => String(s == null ? '' : s);
function alert(){}
function readCompressedImage(){}
var navigator = { clipboard: { writeText(){} } };
var location = {};
var window = { open(){}, location: {} };
var document = {
  createElement: () => ({ style:{}, click(){}, appendChild(){}, getContext: () => ({ drawImage(){} }), toDataURL: () => '' }),
  getElementById: () => null,
  querySelectorAll: () => [],
  addEventListener(){},
};
`;

const EXPORTS = `
export {
  DX_META, DX_NAMES, DB350, SYMKW,
  scoreDifferential, evMatched, tokenMatch,
  buildSignalsFromPatient, patientCautions,
  parseAnketaCode, buildReportText,
  matchDB350, SYMPTOMS, FULLQ
};
`;

function sliceBlock(src, startNeedle, endNeedle) {
  const s = src.indexOf(startNeedle);
  const e = src.indexOf(endNeedle, s + startNeedle.length);
  if (s === -1 || e === -1) {
    throw new Error(
      `Could not locate cabinet block between "${startNeedle}" and "${endNeedle}". ` +
      `Is this a METACOD cabinet.html with the expected section markers?`
    );
  }
  // Include the whole start-comment line through the end-comment closing.
  const lineStart = src.lastIndexOf("/*", s);
  const close = src.indexOf("*/", e);
  return src.slice(lineStart === -1 ? s : lineStart, close === -1 ? e : close + 2);
}

/**
 * Load the cabinet engine from an HTML file path.
 * @param {string} cabinetPath absolute or relative path to cabinet.html
 * @returns {Promise<object>} the engine namespace (DX_META, scoreDifferential, …)
 */
export async function loadEngine(cabinetPath) {
  const html = await readFile(cabinetPath, "utf8");
  const engineBlock = sliceBlock(html, ENGINE_START, ENGINE_END);
  const quizBlock = sliceBlock(html, QUIZ_START, QUIZ_END);

  const moduleSource = [PRELUDE, engineBlock, "\n", quizBlock, "\n", EXPORTS].join("\n");

  const dir = await mkdtemp(join(tmpdir(), "metacod-engine-"));
  const file = join(dir, "engine.generated.mjs");
  await writeFile(file, moduleSource, "utf8");

  const mod = await import(pathToFileURL(file).href);
  return mod;
}

export default loadEngine;
