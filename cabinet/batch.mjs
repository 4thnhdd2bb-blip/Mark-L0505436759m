#!/usr/bin/env node
/**
 * METACOD Cabinet — retroactive batch runner.
 *
 * Scores many (e.g. 60 000) historical patients through the *cabinet's own*
 * differential engine and writes a beautiful Word (.doc) conclusion per
 * patient plus a summary spreadsheet — the deliverable for the retroactive
 * Clalit analysis.
 *
 * Usage:
 *   node cabinet/batch.mjs --cabinet python/ui/cabinet.html \
 *        --in patients.jsonl --out ./out [--locale ru|en|he]
 *
 * Options:
 *   --cabinet <path>   cabinet.html to lift the engine from (source of truth)
 *   --in <path>        input file (.jsonl / .ndjson / .csv)
 *   --out <dir>        output directory (default ./metacod_out)
 *   --locale <l>       report language: ru (default) | en | he
 *   --summary-only     write only summary.csv (recommended for very large runs)
 *   --combined         also emit combined Word workbooks (chunked)
 *   --chunk <n>        patients per combined workbook (default 500)
 *   --limit <n>        process only the first n records (smoke testing)
 *
 * The summary.csv has one row per patient: id, name, age, sex, the top-3
 * suspected diagnoses with match %, and a caution count — ideal for triaging
 * 60k charts before opening the individual Word conclusions.
 */

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { join } from "node:path";

import { loadEngine } from "./engine_loader.mjs";
import { recordsFromText, detectFormat, recordToAnketaText, recordId } from "./ingest.mjs";
import { buildWordDoc, combineWordDocs } from "./word.mjs";

function parseArgs(argv) {
  const a = { out: "./metacod_out", locale: "ru", chunk: 500, summaryOnly: false, combined: false, limit: 0 };
  for (let i = 2; i < argv.length; i++) {
    const k = argv[i];
    const next = () => argv[++i];
    if (k === "--cabinet") a.cabinet = next();
    else if (k === "--in") a.in = next();
    else if (k === "--out") a.out = next();
    else if (k === "--locale") a.locale = next();
    else if (k === "--chunk") a.chunk = parseInt(next(), 10) || 500;
    else if (k === "--limit") a.limit = parseInt(next(), 10) || 0;
    else if (k === "--summary-only") a.summaryOnly = true;
    else if (k === "--combined") a.combined = true;
    else if (k === "--help" || k === "-h") a.help = true;
  }
  return a;
}

const HELP = `METACOD Cabinet — retroactive batch runner

  node cabinet/batch.mjs --cabinet python/ui/cabinet.html --in patients.jsonl --out ./out

Required: --cabinet <cabinet.html>  --in <patients.jsonl|.csv>
Optional: --out <dir> --locale ru|en|he --summary-only --combined --chunk <n> --limit <n>
`;

function csvCell(v) {
  const s = String(v == null ? "" : v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** Map cabinet symptom ids -> human label in the chosen locale. */
function buildSymLabelMap(SYMPTOMS, locale) {
  const map = {};
  for (const group of SYMPTOMS || []) {
    for (const it of group.items || []) map[it.id] = it[locale] || it.ru || it.id;
  }
  return map;
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help || !args.cabinet || !args.in) {
    console.log(HELP);
    process.exit(args.help ? 0 : 1);
  }

  const t0 = Date.now();
  console.log(`[metacod] loading engine from ${args.cabinet}`);
  const E = await loadEngine(args.cabinet);
  console.log(`[metacod] engine ready: ${Object.keys(E.DX_META).length} differential patterns, ` +
              `${E.DB350.length} treatment-base entries`);

  const symLabel = buildSymLabelMap(E.SYMPTOMS, args.locale);

  const text = await readFile(args.in, "utf8");
  const format = detectFormat(args.in);
  let records = recordsFromText(text, format);
  if (args.limit > 0) records = records.slice(0, args.limit);
  console.log(`[metacod] ${records.length} records (${format})`);

  await mkdir(args.out, { recursive: true });
  const summary = [[
    "id", "name", "age", "sex",
    "dx1", "dx1_pct", "dx2", "dx2_pct", "dx3", "dx3_pct",
    "n_dx", "cautions", "word_file",
  ]];

  const combinedBuffer = [];
  let chunkIndex = 0;
  const flushCombined = async (force) => {
    if (!args.combined) return;
    if (!combinedBuffer.length) return;
    if (!force && combinedBuffer.length < args.chunk) return;
    chunkIndex++;
    const name = `combined_${String(chunkIndex).padStart(4, "0")}.doc`;
    await writeFile(join(args.out, name), combineWordDocs(combinedBuffer));
    combinedBuffer.length = 0;
  };

  let ok = 0, failed = 0;
  for (let i = 0; i < records.length; i++) {
    const rec = records[i];
    const id = recordId(rec, i);
    try {
      const code = recordToAnketaText(rec);
      const o = E.parseAnketaCode(code);
      if (!o) throw new Error("no [METACOD-КОД] parsed");

      const tmp = {
        name: o.name || rec.name || id,
        dob: "",
        allergies: o.allergies || "",
        meds: o.meds ? [{ name: o.meds, dose: "" }] : [],
        symptoms: [],
        checklist: {},
      };
      (o.symIds || []).forEach((sid) => { tmp.checklist[sid] = true; });

      const extra = {
        complaint: o.complaint, symIds: o.symIds,
        sbp: o.sbp, dbp: o.dbp, hr: o.hr, pregnant: o.pregnant, age: o.age,
      };
      const sig = E.buildSignalsFromPatient(tmp, extra);
      const dx = E.scoreDifferential(sig);
      const cautions = E.patientCautions(sig);

      const patient = { name: tmp.name, age: o.age, sex: o.sex, allergies: tmp.allergies, meds: tmp.meds };
      const reportExtra = {
        complaint: o.complaint,
        symLabels: (o.symIds || []).map((sid) => symLabel[sid] || sid),
      };

      let wordFile = "";
      const doc = buildWordDoc({ patient, extra: reportExtra, dx, cautions, locale: args.locale });
      if (!args.summaryOnly) {
        wordFile = `${id}.doc`;
        await writeFile(join(args.out, wordFile), doc);
      }
      if (args.combined) { combinedBuffer.push(doc); await flushCombined(false); }

      const top = dx.slice(0, 3);
      summary.push([
        id, tmp.name, o.age ?? "", o.sex ?? "",
        top[0]?.name ?? "", top[0]?.matchPct ?? "",
        top[1]?.name ?? "", top[1]?.matchPct ?? "",
        top[2]?.name ?? "", top[2]?.matchPct ?? "",
        dx.length, cautions.length, wordFile,
      ]);
      ok++;
    } catch (e) {
      failed++;
      summary.push([id, rec.name ?? "", "", "", `ERROR: ${e.message}`, "", "", "", "", "", 0, 0, ""]);
    }
    if ((i + 1) % 1000 === 0) console.log(`[metacod] ${i + 1}/${records.length} …`);
  }
  await flushCombined(true);

  const summaryCsv = summary.map((r) => r.map(csvCell).join(",")).join("\n");
  await writeFile(join(args.out, "summary.csv"), summaryCsv, "utf8");

  const secs = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`[metacod] done: ${ok} ok, ${failed} failed → ${args.out} (summary.csv` +
              `${args.summaryOnly ? "" : " + per-patient .doc"}${args.combined ? " + combined" : ""}) in ${secs}s`);
}

main().catch((e) => { console.error("[metacod] fatal:", e); process.exit(1); });
