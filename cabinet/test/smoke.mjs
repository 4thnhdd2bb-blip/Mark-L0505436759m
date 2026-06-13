/**
 * METACOD Cabinet batch — smoke tests (node --test).
 *
 *   node --test cabinet/test/smoke.mjs
 *
 * Exercises the full path against the synthetic fixture cabinet:
 * engine extraction → ingest (CSV + JSONL) → scoring → Word output.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { readFile, rm, mkdtemp, readdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const execFileP = promisify(execFile);
const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..");
const FIXTURE = join(HERE, "fixture_cabinet.html");

const { loadEngine } = await import(join(ROOT, "engine_loader.mjs"));
const { csvToRecords, jsonlToRecords, recordToAnketaText, recordId } = await import(join(ROOT, "ingest.mjs"));
const { buildWordDoc, combineWordDocs } = await import(join(ROOT, "word.mjs"));

test("engine_loader lifts the cabinet engine from HTML", async () => {
  const E = await loadEngine(FIXTURE);
  assert.ok(E.DX_META.cold, "DX_META.cold present");
  assert.ok(E.DX_META.htn, "DX_META.htn present");
  assert.equal(typeof E.scoreDifferential, "function");
  assert.equal(typeof E.parseAnketaCode, "function");
  assert.ok(Array.isArray(E.DB350) && E.DB350.length >= 2);
  assert.ok(Array.isArray(E.SYMPTOMS) && E.SYMPTOMS.length >= 1);
});

test("scoring a hypothyroid patient ranks 'cold' first with cautions", async () => {
  const E = await loadEngine(FIXTURE);
  const o = E.parseAnketaCode(
    "[METACOD-КОД]name=Тест;sym=g3;age=64;sex=жен;hr=55;meds=левотироксин;alg=ибупрофен;c=зябкость, прибавка веса, нет сил"
  );
  const tmp = { name: o.name, dob: "", allergies: o.allergies, meds: o.meds ? [{ name: o.meds }] : [], symptoms: [], checklist: {} };
  (o.symIds || []).forEach((s) => (tmp.checklist[s] = true));
  const extra = { complaint: o.complaint, symIds: o.symIds, hr: o.hr, sbp: o.sbp, dbp: o.dbp, age: o.age };
  const sig = E.buildSignalsFromPatient(tmp, extra);
  const dx = E.scoreDifferential(sig);
  assert.ok(dx.length >= 1, "at least one differential");
  assert.equal(dx[0].id, "cold", "top diagnosis is hypothyroidism");
  assert.ok(dx[0].matchPct >= 50, `match% should be meaningful, got ${dx[0].matchPct}`);
  const pc = E.patientCautions(sig);
  assert.ok(pc.some((c) => c.includes("НПВС")), "NSAID allergy caution surfaced");
});

test("ingest: CSV and JSONL produce equivalent anketa codes", () => {
  const csv = "id,name,age,sym,complaint\nP1,Анна,40,\"g3,n1\",устал\n";
  const recs = csvToRecords(csv);
  assert.equal(recs.length, 1);
  const code = recordToAnketaText(recs[0]);
  assert.ok(code.startsWith("[METACOD-КОД]"));
  assert.ok(code.includes("sym=g3,n1"));
  assert.ok(code.includes("age=40"));

  const j = jsonlToRecords('{"id":"P9","code":"[METACOD-КОД]sym=g3;age=50"}\n');
  assert.equal(recordToAnketaText(j[0]), "[METACOD-КОД]sym=g3;age=50");
  assert.equal(recordId(j[0], 0), "P9");
});

test("buildWordDoc produces a Word-openable, RTL-aware document", async () => {
  const E = await loadEngine(FIXTURE);
  const o = E.parseAnketaCode("[METACOD-КОД]name=Тест;sym=g3;hr=55;c=зябкость, нет сил");
  const tmp = { name: o.name, dob: "", allergies: "", meds: [], symptoms: [], checklist: {} };
  (o.symIds || []).forEach((s) => (tmp.checklist[s] = true));
  const extra = { complaint: o.complaint, symIds: o.symIds, hr: o.hr };
  const sig = E.buildSignalsFromPatient(tmp, extra);
  const dx = E.scoreDifferential(sig);

  const ru = buildWordDoc({ patient: { name: "Тест", age: 64 }, dx, cautions: [], locale: "ru" });
  assert.ok(ru.includes("application/msword") === false); // sanity: it's HTML, not the mime
  assert.ok(ru.includes("urn:schemas-microsoft-com:office:word"), "carries Word namespace");
  assert.ok(ru.includes("Медицинское заключение"));
  assert.ok(ru.includes("Гипотиреоз"));

  const he = buildWordDoc({ patient: { name: "Test" }, dx, cautions: [], locale: "he" });
  assert.ok(he.includes('dir="rtl"'), "Hebrew is right-to-left");

  const combined = combineWordDocs([ru, ru]);
  assert.ok(combined.includes("page-break-before"), "combined workbook paginates patients");
});

test("batch CLI runs end-to-end over the JSONL sample", async () => {
  const out = await mkdtemp(join(tmpdir(), "metacod-batch-"));
  try {
    const { stdout } = await execFileP("node", [
      join(ROOT, "batch.mjs"),
      "--cabinet", FIXTURE,
      "--in", join(ROOT, "sample_patients.jsonl"),
      "--out", out,
      "--combined",
    ]);
    assert.ok(/done: 3 ok, 0 failed/.test(stdout), `expected 3 ok, got:\n${stdout}`);

    const files = await readdir(out);
    assert.ok(files.includes("summary.csv"));
    assert.ok(files.includes("P1.doc"));
    assert.ok(files.some((f) => /^combined_\d+\.doc$/.test(f)), "combined workbook written");

    const summary = await readFile(join(out, "summary.csv"), "utf8");
    assert.ok(summary.includes("Гипотиреоз"), "summary names the diagnosis");
    assert.ok(summary.split("\n").length >= 4, "header + 3 patients");

    const p1 = await readFile(join(out, "P1.doc"), "utf8");
    assert.ok(p1.includes("Гипотиреоз") && p1.includes("Иванова"));
  } finally {
    await rm(out, { recursive: true, force: true });
  }
});

test("batch CLI runs end-to-end over the CSV sample (summary-only)", async () => {
  const out = await mkdtemp(join(tmpdir(), "metacod-batch-csv-"));
  try {
    const { stdout } = await execFileP("node", [
      join(ROOT, "batch.mjs"),
      "--cabinet", FIXTURE,
      "--in", join(ROOT, "sample_patients.csv"),
      "--out", out,
      "--summary-only",
    ]);
    assert.ok(/done: 3 ok, 0 failed/.test(stdout), `expected 3 ok, got:\n${stdout}`);
    const files = await readdir(out);
    assert.deepEqual(files.sort(), ["summary.csv"], "summary-only writes just the spreadsheet");
  } finally {
    await rm(out, { recursive: true, force: true });
  }
});
