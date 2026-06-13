/**
 * METACOD Cabinet — batch input ingestion (CSV + JSONL).
 *
 * Each input record describes one (historical) patient. Two shapes are
 * accepted, mirroring how the cabinet itself takes data:
 *
 *   1. A ready cabinet code string:
 *        { "id": "P1", "code": "[METACOD-КОД]sym=g3,c1;age=64;bp=150/95;..." }
 *
 *   2. Flat fields (we assemble the code for you):
 *        { "id":"P1","name":"...","age":64,"sex":"жен","sbp":150,"dbp":95,
 *          "hr":78,"preg":false,"meds":"левотироксин","alg":"ибупрофен",
 *          "complaint":"зябкость, прибавка веса", "sym":"g3,c1" }
 *
 * `sym` is a comma-separated list of cabinet symptom ids (g3, c1, f4, …) or a
 * JSON array. CSV uses the same column names as the flat JSON fields.
 */

/** Minimal RFC-4180-ish CSV parser (quotes, escaped quotes, embedded newlines). */
export function parseCSV(text) {
  const rows = [];
  let row = [], field = "", i = 0, inQuotes = false;
  const n = text.length;
  while (i < n) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i += 2; continue; }
        inQuotes = false; i++; continue;
      }
      field += c; i++; continue;
    }
    if (c === '"') { inQuotes = true; i++; continue; }
    if (c === ",") { row.push(field); field = ""; i++; continue; }
    if (c === "\r") { i++; continue; }
    if (c === "\n") { row.push(field); rows.push(row); row = []; field = ""; i++; continue; }
    field += c; i++;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows.filter((r) => r.length && !(r.length === 1 && r[0] === ""));
}

export function csvToRecords(text) {
  const rows = parseCSV(text);
  if (!rows.length) return [];
  const header = rows[0].map((h) => h.trim());
  return rows.slice(1).map((cells) => {
    const rec = {};
    header.forEach((key, idx) => { rec[key] = (cells[idx] ?? "").trim(); });
    return rec;
  });
}

export function jsonlToRecords(text) {
  return text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)
    .map((line, idx) => {
      try { return JSON.parse(line); }
      catch (e) { throw new Error(`JSONL parse error on line ${idx + 1}: ${e.message}`); }
    });
}

export function recordsFromText(text, format) {
  if (format === "csv") return csvToRecords(text);
  if (format === "jsonl") return jsonlToRecords(text);
  throw new Error(`Unknown format "${format}" (expected csv | jsonl)`);
}

export function detectFormat(path) {
  if (/\.jsonl$/i.test(path) || /\.ndjson$/i.test(path)) return "jsonl";
  if (/\.csv$/i.test(path)) return "csv";
  return "jsonl";
}

function bool(v) {
  if (v === true) return true;
  const s = String(v ?? "").toLowerCase().trim();
  return s === "1" || s === "true" || s === "да" || s === "yes" || s === "y";
}

/** Build a cabinet `[METACOD-КОД]` string from flat fields. */
export function recordToAnketaText(rec) {
  if (rec.code && String(rec.code).includes("[METACOD-КОД]")) return String(rec.code);

  const sym = Array.isArray(rec.sym)
    ? rec.sym.join(",")
    : String(rec.sym ?? rec.symIds ?? "").replace(/\s+/g, "");
  const sbp = rec.sbp ?? rec.bp_sys ?? "";
  const dbp = rec.dbp ?? rec.bp_dia ?? "";
  const bp = (sbp !== "" || dbp !== "") ? `${sbp}/${dbp}` : "";

  const pairs = [
    ["name", rec.name ?? ""],
    ["sym", sym],
    ["age", rec.age ?? ""],
    ["sex", rec.sex ?? ""],
    ["bp", bp],
    ["hr", rec.hr ?? ""],
    ["preg", bool(rec.preg ?? rec.pregnant) ? "1" : ""],
    ["meds", rec.meds ?? ""],
    ["alg", rec.alg ?? rec.allergies ?? ""],
    ["c", rec.complaint ?? rec.c ?? ""],
  ].filter(([, v]) => String(v) !== "");

  return "[METACOD-КОД]" + pairs.map(([k, v]) => `${k}=${v}`).join(";");
}

/** Stable per-record id for output filenames. */
export function recordId(rec, index) {
  return String(rec.id ?? rec.patient_id ?? rec.passport ?? `row${index + 1}`)
    .replace(/[^A-Za-z0-9_\-]+/g, "_")
    .slice(0, 60) || `row${index + 1}`;
}
