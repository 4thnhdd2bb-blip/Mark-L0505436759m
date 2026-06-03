# METACOD GLP-1 — UI (single-file React)

Trilingual (RU / EN / HE + RTL) clinical interface for the GLP-1 module. One
`index.html`, no build step (React + Babel from CDN). Runs from `file://`, GitHub
Pages, or served by the FastAPI backend.

## Run

**Demo mode (`file://`)** — open `index.html` directly. Uses the embedded
`mock-assessment`; the header badge shows `DEMO`. No backend needed.

**Live mode** — point it at the backend:
```
file:///path/to/index.html?api=http://localhost:8001
```
Badge switches to `LIVE`; buttons call `POST /glp1/assess` and `POST /glp1/sign-off`.

**Served by FastAPI (recommended, no CORS)** — `python/main.py` already mounts this
folder:
```bash
cd python && METACOD_GLP1_INIT_DB=1 python main.py
# open http://localhost:8001/   → the UI, same-origin → /glp1/* works directly
```
`/` serves `index.html`; `/ui/*` serves assets; `/healthz` is the JSON probe.

## Layers

- **Clinical** (default) — triage, interaction cards (rule name, medication,
  physician actions, patient education, lab plan, evidence grade), forecast. No
  `rule_id`, no mechanism, no internal pattern terms.
- **Admin** (header toggle) — adds a violet `[admin]` block per interaction:
  `rule_id`, `pattern`, resolved internal text, `mechanism`, sources. For SaMD
  audit / physician training — never shown to patients.

## RTL

Switching locale to `he` sets `document.documentElement.dir = "rtl"`. Layout uses
CSS logical properties so it mirrors cleanly; Latin technical tokens (rule_id,
version) keep LTR within the RTL flow.

## API contract

```
POST /glp1/assess   { locale, patient }      → 201 { visit_id, locale, direction, assessment, ... }
POST /glp1/sign-off { visit_id, physician_id, physician_name, status, notes } → 200 { sign_off_id, ... }
```
In demo mode both return the embedded mock after a short delay.

## Extend

Everything is in one file. New form field → add a `<Field>`/`<Checkbox>` in the
relevant fieldset. New chrome strings → edit the `ui-i18n` JSON block. Restyle →
edit the CSS variables in `:root`. For a real history/dashboard view, graduate this
to a Vite + React project (this single-file build is the pilot artifact); the
target component architecture is the Expo-RN client in `packages/` / `apps/`.

## Not yet

History view (`GET /glp1/visit/{id}`, `/glp1/audit-log`), medication autocomplete
(`GET /glp1/drugs?search=`), PDF button (use browser print on `report.html`),
auth (v4 layer), power-user features.
