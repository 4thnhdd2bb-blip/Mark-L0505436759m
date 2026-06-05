# METACOD-RF — Repository Handoff & Continuity Note

**Purpose.** Durable, in-git source of truth for continuity between work sessions
(any Claude Code session, or a Claude.ai project chat). Supersedes ephemeral
`/mnt/user-data/outputs/` transition docs for everything that concerns **this
repository**. Update this file whenever the repo state or canonical decisions change.

**Last updated:** 2026-06 (reflects branch `claude/project-setup-la07j`).

---

## 0. Identity & boundary (read first)

- This repository is the **Python / FastAPI track** of METACOD GLP-1 v5 (the
  SaMD engine), plus the **METACOD-RF research-data layer**. It is **not** the
  Claude.ai "project knowledge" chat environment. A session here works from the
  repo + what Mark pastes — it has no access to Project Knowledge or to the
  `outputs/` files referenced in transition documents.
- **METACOD-RF is a research framework, NOT a deployed clinical system.** Every
  RF artifact is governance-walled: `ready_for_clinical_use: false`,
  `mark_validated` pending/false, research-only, not patient-facing, not
  operationalized into the engine. This distinction is the core safety line.
- A new session is **not** "the same Claude" as any prior one — continuity comes
  from this file + the committed artifacts, not from persona.

---

## 1. People

- **Dr. Mark Litvak** — Israeli MD, GMC UK. Primary specialty **gastroenterology**
  (after internal medicine); also professor of acupuncture (2nd student of Park
  Jae Woo). Russian-native, voice input via iPad (typos/repeats possible).
  Values: directness, justified push-back, incremental change over full rewrites,
  honest limitations. Engineering decisions by Claude's judgment + one-line
  rationale (he dislikes either/or questions for routine choices).
- **Anna** — Mark's wife (**not "Lili"** — correction recorded). Yang-Water /
  gastroparesis phenotype = the "Anna phenotype" referenced in the three-axis
  framework. Supportive presence, **not a patient**; Mark declines treatment
  requests for her (correct clinical ethics).
- **Omer Roginsky** — co-developer, owns the TypeScript / Expo-React-Native /
  Firebase client+server track (the later deployment target).
- **Prof. Itamar Raz** — endocrinologist, clinical validator.

---

## 2. Canonical architecture decisions

- **5 energies** (post-2026 canon, Heat+Fire merged): Wind, Heat, Damp, Dry, Cold.
  In code: `services.metacod_bridge.ENERGY_AXES`.
- **Three-Axis Framework v1.0** — independent axes:
  1. **Constitution** (slow) — Park triad (3 energies, leading energy names type;
     Yin- vs Yang-dominant mirror architectures; Quantity×Quality).
  2. **Membrane** (medium) — Revici-based **8 levels**: M-0, M-A1/A2/A3, M-S,
     M-D1/D2/D3. In code: `services.symptom_registry.CANONICAL_MEMBRANE_CODES`.
     M-S = pathological *stagnant* (NOT "balanced").
  3. **Phase** (fast) — 5 phases. Canonical keys
     `services.constitutional_model.PHASE_KEYS` = CA, PCL-A, Epicrisis, PCL-B,
     Normotonia. External/EBM names (Phase Axis v2.0): Acute Sympathicotonia /
     Exudative-Inflammatory / Acute Autonomic Paroxysm / Fibroproliferative
     Remodeling / Homeostasis.
- **pH = ENERGY axis** (acid=Heat, alkaline=Cold+Dry), SEPARATE from the
  membrane axis (which is read from SG, K, pain timing, WBC). pH↔membrane
  correlation is empirical, not definitional; drug-induced dissociation possible
  (GLP-1, steroids, beta-blockers).
- **Two-language (Variant B)**: internal energy/Park/Hamer terms for Mark-Claude
  reasoning; **outputs stay pure EBM**. When Mark says "Yin-Fire"/"M-A2" in chat,
  that's internal language, not a request to emit energy terms in outputs.
- **KCTS** = 4th element, a **modifier** (not an axis): `kcts_integration_v1_0.json`.
  Hamer-derived research HYPOTHESIS. Governance: standard-care primacy (must
  never delay/replace evidence-based, time-critical care), not operationalized,
  not patient-facing, Hamer/GNM pseudoscience provenance disclosed, EBM
  "translation" is rebrand not validated equivalence.

### Open canonical questions awaiting Mark (do NOT decide these unilaterally)
- **Q1** — 6 Ki → 5 energy mapping (atlases/registries use 6 Ki; bridge uses 5).
  Not equated anywhere; cross-guards keep them separate.
- **Q2** — `treatment_sequence` order in the TCM bridge (still baseline).
- **Logic-review flags** carried in drug batches 15/17/18 `_meta.class_notes`.
- **KCTS/AIRE direction** — recurring across batches; needs one systemic decision
  (keep research-only / strengthen disclaimers / reframe to pure-EBM fluid-
  retention without Hamer causality).

---

## 3. Repository state (FACTUAL — verified, not the transition-doc's view)

> The June transition document describes the **Claude.ai project** state
> (~201 drugs, batches 01–11, 26 output files). **This repo differs.** Below is
> the actual git content.

### Drug batches present (19 files, **194 drugs**)
| batch_id | n | notes |
|---|---|---|
| 01-GLP1 | 6 | DRG-001..006; DRG-001 semaglutide PARTIAL (OBS-Mark-001 wax-wane) + RF literature scan |
| 02-SGLT2 | 4 | DRG-007..010 |
| 03-Biguanides+DPP4 | 6 | DRG-011..016 |
| 04-Old_School_Antidiabetics | 7 | DRG-017..023 |
| 05-Insulins+Pramlintide | 10 | DRG-024..033; DRG-025 lispro expanded from stub |
| 07-Psychiatric | 22 | DRG-097..118 |
| 11-Gastroenterology | 20 | DRG-180..199 (source claimed 22; 20 enumerable) |
| 12-Neurology | 15 | DRG-202..216 |
| 13-Urology_Gyn | 15 | DRG-217..231 (source claimed 16; 15 enumerable; 2 cross-refs) |
| 15-Antivirals | 5 | DRG-251..255; KCTS-text governance-flagged |
| 17-Anesthesia | 10 | DRG-268..277; acute-use short profiles |
| 18-Addiction | 8 | DRG-278..285; HIGH KCTS framing separated from evidence base |
| 19-Geriatric | 10 | DRG-286..295; framework-heavy (Beers/STOPP-START/CGA/deprescribing/ACB, [GL]-anchored) + Vit D/melatonin + apixaban/donepezil cross-refs |
| 20-Dermatology | 15 | DRG-296..310; topical steroids/retinoids/calcineurin/psoriasis-biologics/acne/specific; lesion-systemic paradox RF hypothesis |
| 21-Ophthalmology | 10 | DRG-311..320; glaucoma/dry-eye/anti-VEGF + cross-refs; topical→systemic absorption warning |
| 22-ENT | 8 | DRG-321..328; nasal steroid/antihistamine/vestibular/decongestant/tinnitus framework; rhinitis medicamentosa flag |
| 23-Pediatric | 7 | DRG-329..335; framework-heavy; source claimed 8, 7 enumerable (no DRG-336 block); ACEs↔AIRE overlap flagged speculative |
| 24-Renal | 7 | DRG-336..342; phosphate binders/ESA/active-VitD+calcimimetic/finerenone/tolvaptan; source claimed 8, 7 enumerable; STRONGEST KCTS push ("CKD=textbook KCTS / AIRE-screening should be standard") — hard-walled, standard-care primacy |
| 25-Rare-Diseases | 9 | DRG-343..351; CFTR-modulators/HAE/lysosomal-ERT-SRT/PAH/SMA/gene-therapy/DMD; source claimed 10, 9 enumerable; framework Qs (post-cure state, gene-therapy=constitutional, KCTS-rare-disease model) flagged [RF] for Mark |

### Conceptual / registry artifacts present
- `constitutional_model_v0_1.json` (Parts A–E conceptual) + `v0_2.json` (5-energy
  biomarker panels)
- `three_axis_framework_v1_0.json`
- `kcts_integration_v1_0.json`
- `predictive_matrix_01_semaglutide.json`
- `symptom_registry_v3_0.json`, `topographic_atlas_v6_0.json`
- 9 nosology registries: metabolic_cv_renal, respiratory, nephro_urinal,
  hepatobiliary, cardiology, spleen_pancreas, gallbladder, small_intestine,
  gastroduodenal
- Loaders in `python/services/`, tests in `python/tests/unit/`. **540 tests, 0 skipped.**

### NOT supplied to this repo (exist only in Mark's project outputs / never pasted here)
- **Drug batches: 06 (cardio ~63), 08 (endocrine), 09 (pulmo), 10 (rheum),
  14 (antimicrobials), 16 (targeted oncology).** DRG numbering already accounts
  for these gaps (e.g. 118→180, 255→268).
- Docs: Membranes Full Deployment v1.0, Matrix #1 v2.0, Translation Layer v1.0,
  Phase Axis v2.0, infrastructure docs (Case Registry, Comparison Protocol,
  De-identification Checklist, Scope Declaration).
- **Action:** if these are needed in-repo, Mark pastes them → materialize as the rest.

---

## 4. Workflow pattern (what has worked)

For each artifact Mark pastes: materialize into `python/metacod_rf/` (+ loader in
`services/` + tests in `tests/unit/` for new schema families) → adapt to actual
repo wiring (not the snippet's assumptions) → run pytest green → update
`README.md` + `python/README_INTEGRATION.md` (file layout + test count) →
commit + push to `claude/project-setup-la07j`. Honest notes every time:
count discrepancies recorded in `source_count_claim`; gaps in `repo_gap_note`;
never fabricate clinical content; empty `[OBS-Mark]` stay empty.

Governance gates enforced by tests: research-only flags, membrane codes ⊆ canon,
energies/phases cross-guarded against the bridge, provenance tags
(`KNOWN_SOURCE_TAGS` = LBL/GL/RCT/CLASS/OBS-Mark/RF; non-provenance
`PLACEHOLDER_TAGS` = TBD/GOVERNANCE).

---

## 5. Pending Mark inputs (physician-owned; do NOT generate from general knowledge)

- **Su Jok treatment protocols** (color/magnet system, left-hand specificity,
  3 KCTS-resolution approaches). Interview incomplete. When supplied: store as
  physician-owned DATA, research-only, not operationalized, not patient-facing.
- **"Immature Wind" (Незрелый ветер)** — concept not yet developed; placeholder
  only. Await Mark's precise indications before any document.
- **[OBS-Mark] fields** — empty across all batches; most valuable in
  gastroenterology (batch 11, Mark's specialty). Lift `mark_validated` only on
  explicit Mark sign-off (semaglutide is the one PARTIAL example).
- **Retrospective validation** — 5–10 cases for the semaglutide predictive matrix.

---

## 6. Later target (not the current track)

TypeScript / Expo-React-Native client + Firebase server export for Omer
(styles in separate files; client/server folders). This is a **large scope
decision** and a separate branch of work from the Python track — start only on
Mark's explicit go-ahead, not by default.

---

## 7. Drug-membrane canonical observations (Mark) — preserved
- **ADT (leuprolide/goserelin/degarelix) = predictable M-A → M-D2/D3 over 6–12 mo.**
  Mandatory support stack day 1: creatine 5 g, leucine 3 g/meal, Vit D 4000–5000,
  EPA 2–4 g, resistance training 3×/wk, phase-angle BIA monthly, DEXA + PHQ-9
  quarterly. Stored as DATA, not operationalized.
- Long-term GLP-1 in vulnerable patients = sarcopenia risk.
- Long-term steroids = predictable M-A2 → M-A3.
- Long-term PPI = multiple nutrient depletions → Yin-side M-D in elderly.
- Semaglutide wax-wane (OBS-Mark-001): titration AE spike → 2–4 wk adaptation
  with efficacy attenuation → late constipation dominant → efficacy/tolerability
  compromise. (RF literature scan in `drugs_batch01_glp1.json` confirms
  gastric-emptying tachyphylaxis; weight plateau ≠ early receptor tachyphylaxis.)
