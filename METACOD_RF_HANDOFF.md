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
     M-S = pathological *stagnant* (NOT "balanced"). **CORRECTED CANON v1.1 (Mark,
     Том I + Module 02 — `master_integration_v1_1.json`):** **M-A = ANABOLIC**
     (sterol excess, rigidity, HMGCR active, metabolic-syndrome; feels better
     evening; urine pH AM <5.5) — **NOT inflammation**. **M-D = CATABOLIC**
     (peroxidation, MDA↑/GPX4↓; feels better morning) — this is where chronic
     inflammation lives (M-D1 hidden / M-D2 autoimmune). **Inflammation location:**
     acute=**Phase 2**, hidden-chronic=**M-D1**, autoimmune=**M-D2**,
     fibrotic-nonhealing=**M-S** — **never M-A**. **Treatment DIRECTION is OPPOSITE:**
     M-A→catabolic-shift (Se/S/Mg/omega-3/statin/metformin/SGLT2); M-D→anabolic
     support + anti-inflammatory + GPX4; M-S→three-parallel (fibrolysis + Yin +
     stop-peroxidation). **Misclassification → opposite treatment → harm** — hence
     this stays RF/research-only, never auto-driving prescribing. (v1.0's
     "M-A=inflammation" error was corrected across repo: three_axis_framework,
     diagnostic_foundation, dx imaging batches 12/13/14/16/20, batch-02, batch-26.)
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
- **KCTS** = a **modifier** (not an axis): `kcts_integration_v1_0.json`, now **v1.1
  EBM-REFORMULATED** (Mark decision 2026-06). Operative model is now **pure EBM**:
  persistent fluid-retention + chronic-stress physiology (HPA/cortisol/HRV) +
  low-grade inflammation (hsCRP) + psychosocial burden (isolation/carer-burden/
  treatment-refractory disease). **Hamer/GNM lineage, "AIRE" psychic-conflict
  causality, literal "collecting-tubule/endoderm/SBS" anatomy, and "Layer 0 =
  AIRE-resolution-FIRST" are DISAVOWED as mechanism** — retained only as disclosed
  origin in `provenance_and_risk_note`. Psychosocial/fluid-retention support runs
  **alongside, never before/instead of**, evidence-based disease treatment. The
  v1.1 doc **governs/supersedes** all per-batch KCTS mentions. Still research-only,
  not operationalized, not patient-facing.

### Open canonical questions awaiting Mark (do NOT decide these unilaterally)
- **Q1** — 6 Ki → 5 energy mapping (atlases/registries use 6 Ki; bridge uses 5).
  Not equated anywhere; cross-guards keep them separate.
- **Q2** — `treatment_sequence` order in the TCM bridge (still baseline).
- **Logic-review flags** carried in drug batches 15/17/18 `_meta.class_notes`.
- **KCTS/AIRE direction — RESOLVED + CLEANUP DONE (2026-06):** Mark chose **reframe
  to pure EBM**. (1) Central `kcts_integration_v1_0.json` v1.1 (governs/supersedes
  all batches). (2) Batch 27 authored in EBM style. (3) **Legacy-text cleanup
  COMPLETE:** a `_meta.kcts_v1_1_alignment` note now sits at the top of every file
  that carried legacy wording — batch files 15/18/19/22/23/24/25 (KCTS/AIRE
  subordinated to v1.1: psychosocial/chronic-stress/fluid-retention; Hamer/AIRE
  causality + collecting-tubule disavowed) and the 3 conceptual files
  (constitutional_model, symptom_registry, three_axis_framework — note clarifies
  their Hamer refs are histogenetic-layer/phase taxonomy with psychogenic claims
  already STRIPPED, no AIRE/KCTS causal layer). Reframe is now 100% closed at the
  governance level — no file presents legacy AIRE/Hamer causality as current canon.

---

## 3. Repository state (FACTUAL — verified, not the transition-doc's view)

> The June transition document describes the **Claude.ai project** state
> (~201 drugs, batches 01–11, 26 output files). **This repo differs.** Below is
> the actual git content.

### Drug batches present (27 files, **507 drugs**)
| batch_id | n | notes |
|---|---|---|
| 01-GLP1 | 6 | DRG-001..006; DRG-001 semaglutide PARTIAL (OBS-Mark-001 wax-wane) + RF literature scan |
| 02-SGLT2 | 4 | DRG-007..010 |
| 03-Biguanides+DPP4 | 6 | DRG-011..016 |
| 04-Old_School_Antidiabetics | 7 | DRG-017..023 |
| 05-Insulins+Pramlintide | 10 | DRG-024..033; DRG-025 lispro expanded from stub |
| 06-Cardiovascular | 78 | DRG-034..096 + 380-394 (acute/IV expansion); **Claude-authored gap-fill** (largest); BB/ACEi/ARB/ARNI/CCB/diuretics/MRA/statins/lipid/antiplatelets/anticoagulants/antiarrhythmics/digoxin/nitrates/ivabradine/PAH/pressors/ranolazine; apixaban=082 (cross-ref batch 19) |
| 07-Psychiatric | 34 | DRG-097..118 |
| 08-Endocrine | 37 | DRG-119..143 + 395-406 (expansion); **Claude-authored gap-fill**; thyroid/glucocorticoids/bone/pituitary/sex-hormones; prednisolone=125 (cross-ref batch 21) |
| 09-Pulmonology | 28 | DRG-144..161 + 407-416 (expansion); **Claude-authored gap-fill**; SABA/LABA/LAMA/SAMA/montelukast=148/ICS/combo/theophylline/roflumilast/biologics/IPF-antifibrotics/antitussive |
| 10-Rheumatology | 18 | DRG-162..179; **Claude-authored gap-fill**; csDMARDs/immunosuppressants/TNF-i/IL6/CTLA4/JAK/IL1/gout; MTX↔Zuo, allopurinol-colchicine↔Yin-Fire/gout context |
| 11-Gastroenterology | 33 | DRG-180..199 (source claimed 22; 20 enumerable) |
| 12-Neurology | 32 | DRG-202..216 |
| 13-Urology_Gyn | 23 | DRG-217..231 (source claimed 16; 15 enumerable; 2 cross-refs) |
| 14-Antimicrobials | 18 | DRG-232..249; **Claude-authored standard-evidence gap-fill** (not Mark source); beta-lactams/macrolides/FQ/tetra/aminoglyc/glycopeptide/oxazolidinone/sulfa/nitrofurantoin/nitroimidazole/azole; honors cross-refs cipro=239/moxi=241/metronidazole=248 |
| 15-Antivirals | 13 | DRG-251..255; KCTS-text governance-flagged |
| 16-Oncology | 12 | DRG-256..267; **Claude-authored standard-evidence gap-fill**; TKI/mAb/checkpoint/hormonal(SERM/AI/GnRH-ADT)/PARP/BTK; leuprolide→Mark ADT support stack; checkpoint→post-cure framework Q |
| 17-Anesthesia | 18 | DRG-268..277; acute-use short profiles |
| 18-Addiction | 10 | DRG-278..285; HIGH KCTS framing separated from evidence base |
| 19-Geriatric | 10 | DRG-286..295; framework-heavy (Beers/STOPP-START/CGA/deprescribing/ACB, [GL]-anchored) + Vit D/melatonin + apixaban/donepezil cross-refs |
| 20-Dermatology | 24 | DRG-296..310; topical steroids/retinoids/calcineurin/psoriasis-biologics/acne/specific; lesion-systemic paradox RF hypothesis |
| 21-Ophthalmology | 15 | DRG-311..320; glaucoma/dry-eye/anti-VEGF + cross-refs; topical→systemic absorption warning |
| 22-ENT | 8 | DRG-321..328; nasal steroid/antihistamine/vestibular/decongestant/tinnitus framework; rhinitis medicamentosa flag |
| 23-Pediatric | 7 | DRG-329..335; framework-heavy; source claimed 8, 7 enumerable (no DRG-336 block); ACEs↔AIRE overlap flagged speculative |
| 24-Renal | 10 | DRG-336..342; phosphate binders/ESA/active-VitD+calcimimetic/finerenone/tolvaptan; source claimed 8, 7 enumerable; STRONGEST KCTS push ("CKD=textbook KCTS / AIRE-screening should be standard") — hard-walled, standard-care primacy |
| 25-Rare-Diseases | 9 | DRG-343..351; CFTR-modulators/HAE/lysosomal-ERT-SRT/PAH/SMA/gene-therapy/DMD; source claimed 10, 9 enumerable; framework Qs (post-cure state, gene-therapy=constitutional, KCTS-rare-disease model) flagged [RF] for Mark |
| 26-Nutraceuticals | 24 | DRG-352..369; alkalinization 3:2:1 / ADT-stack / Zuo formula / Mariana n=1 / adaptogens / microbiome; source claimed 17, 18 enumerable (reverse under-count); HEAVIEST Mark-canonical — 11 source-"CONFIRMED/PARTIAL" deliberately mapped to validation_state=partial (NOT full; sign-off pending); [RCT] added as valid majority-anchor; alkalinization+ADT governance-noted |
| 27-Hematology | 13 | DRG-372..379 (source skipped 370-371); iron oral/IV, hydroxyurea, TPO-agonists, givosiran siRNA, eculizumab/complement; authored AFTER KCTS v1.1 reframe — sickle-cell = EBM psychosocial burden, NOT "AIRE accumulation" |

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
- `diagnostic_foundation_v1_0.json` — diagnostics DB architecture/foundation
- Loaders in `python/services/`, tests in `python/tests/unit/`. **809 tests, 0 skipped.**

### Diagnostics DB (parallel test/imaging database — COMPLETE 2026-06)
- Separate research DB: `dx_batch*.json` + loader `services/diagnostic_db.py` +
  `diagnostic_foundation_v1_0.json` + tests (`test_metacod_rf_diagnostics.py`,
  `test_diagnostic_foundation.py`). IDs: TST/IMG/FUN/PRO.
- Mark authorized **full scope** (~300-390 across lab/imaging/functional/procedures,
  20 batches DX-01..DX-20) **+ full Mark-canonical core**. **COMPLETE — all 20
  batches / 230 entries:** Lab category A (DX-01..DX-11, TST-001..132), Imaging
  (DX-12..DX-15, IMG-001..049), Functional (DX-16/DX-17 + DX-18, FUN-001..029),
  Procedures (DX-19/DX-20, PRO-001..020) + **DX-21 niche labs** (CSF/toxicology-TDM/genetics/salivary-hormones, TST-133..150) = **21 batches / 248 entries**. Claude-authored standard-evidence.
- Governance: tests REVEAL axis states (vs drugs target); ref-ranges/indications
  `[LBL/GL]`, energy/membrane/phase interpretation `[RF]`; BIA phase-angle =
  evidence-based prognostic (zone-mapping `[RF]`); Revici urine-pH / Bristol
  energy-mapping / Cole-Cole = `[RF]` hypotheses; KCTS EBM-reframed (no Hamer/AIRE
  in entries — enforced by test); Claude-authored (reconcile with Mark originals);
  `mark_validated` false; research-only.
- **Open: Mark Q1-Q6** (scope confirmed YES-full; start confirmed DX-18+DX-01;
  Q2-Q5 accepted as-proposed unless Mark revises).

### Gap-fill in progress (Mark authorized Claude to author missing directions, EBM style, 2026-06)
- **DONE — gap-fill COMPLETE (Claude-authored standard-evidence, flagged
  `claude_authored_standard_evidence`):** 06 Cardiovascular (DRG-034..096),
  08 Endocrine (DRG-119..143), 09 Pulmonology (DRG-144..161), 10 Rheumatology
  (DRG-162..179), 14 Antimicrobials (DRG-232..249), 16 Oncology (DRG-256..267).
  Standard [LBL]/[GL]/[RCT] pharmacology; `[OBS-Mark]` empty, `mark_validated`
  false. **Reconcile with Mark's own versions if they surface (his canonical
  observations take priority).**
- **DRG space now essentially contiguous DRG-001..379.** Documented minor
  source gaps only: 200-201 (batch-11 non-enumerable 2), 250 (batch-14/15
  boundary), 370-371 (batch-26/27 boundary). No reserved-class gaps remain.
- **EXPANSION block DRG-380..512 (133 entries, Claude-authored standard-evidence,
  `_meta.expansion_note`):** class-completion per Mark "дополняй все препараты".
  380-416 = acute/IV + missing subclasses in cardio/endo/pulmo. 417-512 = missing
  agents across psych (clozapine/haloperidol/lurasidone/MAOI/TCA/esketamine…),
  GI (rifaximin/UDCA/budesonide/prucalopride/secretagogues…), neuro (topiramate/
  gepants/anti-CGRP/botox/COMT/lecanemab/MS-DMTs/ALS…), uro-gyn (OAB/GnRH-antag/
  gonadotropins/OB), antivirals (Paxlovid/remdesivir/INSTI/HBV/CMV), anesthesia
  (midazolam/dexmedetomidine/volatiles/NMB/locals/dantrolene), addiction, derm,
  ophtho, renal (K-binders/HIF-PHI), nutra (CoQ10/zinc/berberine…), heme
  (G-CSF/chelators/reversal-agents/antifibrinolytics). All `[OBS-Mark]` empty,
  `mark_validated` false. Reconcile with Mark's originals if they surface.
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
- **[OBS-Mark] fields** — empty across most batches; most valuable in
  gastroenterology (batch 11, Mark's specialty). `validation_state` is now
  `partial` on: semaglutide (DRG-001) + 11 batch-26 nutraceutical entries
  (alkalinization 3:2:1, ADT stack, Zuo formula, Mariana n=1). NO entry is
  `full` — full sign-off requires an explicit Mark statement, not a pasted-doc
  "CONFIRMED" (deliberate governance mapping, see batch-26 `_meta`).
- **Retrospective validation** — 5–10 cases for the semaglutide predictive matrix.
- **Mariana case** — flagship n=1 (bronchiectasis: NAC/serratiopeptidase/ectoin
  + AIRE/KCTS hypothesis). Referenced in kcts_integration + batch 26; potential
  teaching-case writeup pending Mark.

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
