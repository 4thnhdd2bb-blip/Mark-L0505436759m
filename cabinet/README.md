# METACOD Cabinet — Word export & retroactive batch

Tooling built **on top of the METACOD Cabinet** (`python/ui/cabinet.html` —
the single-file patient/doctor/admin web app: 153-question intake, differential
engine `DX_META`, ~350-entry treatment base `DB350`, trilingual RU/EN/HE).

Two deliverables:

1. **Beautiful Word conclusions** — both interactively (cabinet add-on) and in bulk.
2. **Retroactive batch** — score tens of thousands of historical patients
   (the Clalit 60k use-case) through the cabinet's own engine and emit one Word
   conclusion per patient plus a triage spreadsheet.

> Clinical safety: the batch never re-types the cabinet's dosing tables. It
> reads `cabinet.html` at runtime as the **single source of truth** and lifts
> the engine out of it. Update the cabinet → the batch follows automatically.

---

## 1. Word export inside the cabinet (interactive)

Add **one line** before `</body>` in `cabinet.html`:

```html
<script src="metacod_word_export.js"></script>
```

(`metacod_word_export.js` lives in `python/ui/`, next to the cabinet.)

A **“📝 Скачать Word (.docx)”** button then appears next to every conclusion
and prescription the cabinet renders. The download opens natively in Microsoft
Word / LibreOffice, keeps the cabinet styling, and is right-to-left for Hebrew.
No build step, no libraries — the cabinet stays a portable single file.

---

## 2. Retroactive batch (60k patients)

```bash
node cabinet/batch.mjs \
  --cabinet python/ui/cabinet.html \
  --in patients.jsonl \
  --out ./out \
  --locale ru
```

Per run you get, in `--out`:

- `summary.csv` — one row per patient: id, name, age, sex, **top-3 suspected
  diagnoses with match %**, and a caution count. Ideal for triaging 60k charts.
- `<id>.doc` — a styled Word conclusion per patient (skip with `--summary-only`).
- `combined_NNNN.doc` — optional combined workbooks (`--combined`, chunked by
  `--chunk`, default 500) when you’d rather not have 60k separate files.

### Options

| flag | meaning |
|---|---|
| `--cabinet <path>` | cabinet.html to lift the engine from (**required**) |
| `--in <path>` | input `.jsonl` / `.ndjson` / `.csv` (**required**) |
| `--out <dir>` | output directory (default `./metacod_out`) |
| `--locale ru\|en\|he` | conclusion language (default `ru`) |
| `--summary-only` | write only `summary.csv` (recommended for very large runs) |
| `--combined` | also emit combined Word workbooks |
| `--chunk <n>` | patients per combined workbook (default 500) |
| `--limit <n>` | process only first `n` records (smoke testing) |

### Input formats

Each record is one patient. Either give a ready cabinet code…

```jsonl
{"id":"P3","code":"[METACOD-КОД]sym=g3,n1;age=70;bp=150/92;hr=58;meds=амлодипин;c=зябкость, головная боль"}
```

…or flat fields and the batch assembles the code for you:

```jsonl
{"id":"P1","name":"Иванова Мария","age":64,"sex":"жен","hr":55,"meds":"левотироксин","alg":"ибупрофен","complaint":"зябкость, прибавка веса, нет сил","sym":"g3"}
```

CSV uses the same column names (see `sample_patients.csv`). `sym` is a
comma-separated list of cabinet symptom ids (`g3`, `c1`, `f4`, …) — the same
ids the cabinet questionnaire emits in its `[METACOD-КОД]` string.

Try the samples:

```bash
node cabinet/batch.mjs --cabinet cabinet/test/fixture_cabinet.html \
  --in cabinet/sample_patients.jsonl --out /tmp/demo --combined
cat /tmp/demo/summary.csv
```

---

## Files

| file | role |
|---|---|
| `engine_loader.mjs` | extracts the cabinet engine (движок + опросник blocks) from `cabinet.html` |
| `word.mjs` | renders a beautiful Word (.doc) conclusion + combined workbooks |
| `ingest.mjs` | CSV / JSONL parsing → normalised `[METACOD-КОД]` records |
| `batch.mjs` | CLI: input → cabinet engine → Word per patient + `summary.csv` |
| `test/fixture_cabinet.html` | synthetic test cabinet (real functions, tiny fake dataset) |
| `test/smoke.mjs` | end-to-end tests |
| `sample_patients.{jsonl,csv}` | example inputs |
| `../python/ui/metacod_word_export.js` | the interactive cabinet add-on |

## Tests

```bash
node --test cabinet/test/smoke.mjs
```

## Related (FastAPI track)

For the GLP-1 FastAPI engine there is also a native OOXML `.docx` renderer
(`python/reports/docx_renderer.py`, needs `pip install python-docx`) and the
`/glp1/visit/{id}/report.html|pdf` endpoints — a separate track from the
cabinet, sharing the same trilingual, evidence-graded philosophy.
