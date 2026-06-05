# METACOD GLP-1 v5 — Python wiring (FastAPI) integration guide

This package adds the GLP-1 Complication Prevention surface to the existing v4
METACOD FastAPI app **without touching v4 endpoints**. It mounts as a router at
`/glp1/*` and shares nothing with v4 except optionally the SQLAlchemy engine.

> **Layout note.** In this repository everything is **flat under `python/`** —
> source modules, the clinical content JSON, the i18n JSON, and the `tests/` tree
> all live together. The original guide assumed three sibling directories; here a
> single `PYTHONPATH=python` is all that's needed.

---

## File layout (this repo)

```
python/
├── main.py                      # Standalone / reference app (mount pattern below)
├── pharmacist_agent.py          # Part 2 — agent + rule DSL + Pydantic models
├── database.py                  # Part 2 — SQLAlchemy models + persistence helpers
├── rule_pack_v2.json            # 31 rules (verbatim, version-pinned)
├── drug_master_v2.json          # 60 molecular drug profiles (v2)
├── rule_energy_mapping.json     # METACOD TCM bridge: rule_id → energy/quantity axes (baseline, pending Mark's review)
├── i18n_glp1_ru.json / en / he  # locale dictionaries (_meta carries direction)
├── alembic_versions/
│   └── 001_initial_glp1.py      # initial migration (production)
├── routers/glp1.py              # the router — main deliverable
├── services/
│   ├── i18n.py                  # locale loader + recursive resolver
│   ├── resources.py             # rule_pack + drug_db singleton cache
│   ├── metacod_bridge.py        # METACOD TCM bridge: assessment → energy/quantity synthesis + three-layer output
│   ├── treatment_sequence.py    # reorder findings by TCM treatment sequence (wind→damp→cold→dry→heat)
│   ├── patient_facing_filter.py # Patient-Facing Filter: detect proprietary/internal terms leaking to patients
│   ├── metacod_rf.py            # METACOD-RF drug DB loader/catalog (engine-internal, research-only, provenance-tagged)
│   ├── constitutional_model.py  # METACOD-RF constitutional model loader (energy → biomarker quality panels)
│   ├── predictive_matrix.py     # METACOD-RF predictive matrix loader (drug × constitutional triad → response prediction)
│   ├── three_axis_framework.py  # METACOD-RF three-axis framework loader (Constitution × Membrane × Phase)
│   ├── topographic_atlas.py     # METACOD-RF topographic atlas loader (tissue × 6-Ki × redox → ICD-10 + membrane code)
│   ├── symptom_registry.py      # METACOD-RF symptom registry loader (SYM × histogenetic layer × 6-Ki × phase × membrane drift)
│   ├── nosology_registry.py     # METACOD-RF nosology registry loader (nosology/ICD-10 × 6-Ki × redox × SYM × membrane drift)
│   └── diagnostic_foundation.py # METACOD-RF diagnostics DB foundation loader (lab/imaging/functional/procedures architecture; ARCHITECTURE PROPOSAL, content not filled)
├── metacod_rf/
│   ├── drugs_batch01_glp1.json  # METACOD-RF research drug DB — batch 01 (6 GLP-1 agents, pending Mark validation)
│   ├── drugs_batch02_sglt2.json # METACOD-RF research drug DB — batch 02 (4 SGLT2 inhibitors, pending Mark validation)
│   ├── drugs_batch03_biguanides_dpp4.json # METACOD-RF research drug DB — batch 03 (3 biguanides + 3 DPP-4, pending validation)
│   ├── drugs_batch04_old_school.json      # METACOD-RF research drug DB — batch 04 (SU/TZD/glinides/α-glucosidase, 7 agents)
│   ├── drugs_batch05_insulins.json        # METACOD-RF research drug DB — batch 05 (9 insulins + pramlintide — antidiabetic group complete)
│   ├── drugs_batch06_cardiovascular.json   # METACOD-RF research drug DB — batch 06 (78 cardio (63 core 034-096 + 15 acute/IV expansion 380-394): BB/ACEi/ARB/ARNI/CCB/diuretics/MRA/statins/lipid(PCSK9/inclisiran)/antiplatelets/anticoagulants(warfarin/heparin/LMWH/DOACs)/antiarrhythmics/digoxin/nitrates/ivabradine/PAH/vasopressor-inotrope/ranolazine; DRG-034..096; CLAUDE-AUTHORED standard-evidence gap-fill; apixaban=082 cross-ref batch 19)
│   ├── drugs_batch07_psychiatric.json     # METACOD-RF research drug DB — batch 07 (34 psychiatric (22 core + 12 expansion 417-428: clozapine/haloperidol/lurasidone/ziprasidone/paliperidone/buspirone/esketamine/TCA/MAOI/hydroxyzine), three-axis profiled)
│   ├── drugs_batch08_endocrine.json        # METACOD-RF research drug DB — batch 08 (37 endocrine non-DM (25 core 119-143 + 12 expansion 395-406: contraceptives/Cushing-agents/glucagon/diazoxide/pegvisomant/pasireotide/vaptan/finasteride): thyroid/glucocorticoids/bone/pituitary/sex-hormones; DRG-119..143; CLAUDE-AUTHORED standard-evidence gap-fill; prednisolone=125 cross-ref batch 21)
│   ├── drugs_batch09_pulmonology.json      # METACOD-RF research drug DB — batch 09 (28 pulmo (18 core 144-161 + 10 expansion 407-416: tezepelumab/reslizumab/zileuton/zafirlukast/triple-combo/LABA-LAMA/extra-LAMA-LABA/dornase/mucoactive): SABA/LABA/LAMA/SAMA/montelukast/ICS/combo/theophylline/roflumilast/biologics/IPF-antifibrotics/antitussive; DRG-144..161; CLAUDE-AUTHORED gap-fill; montelukast=148 cross-ref batch 22)
│   ├── drugs_batch10_rheumatology.json     # METACOD-RF research drug DB — batch 10 (18 rheum: csDMARDs/immunosuppressants/TNF-i/IL6/CTLA4/JAK/IL1/gout; DRG-162..179; CLAUDE-AUTHORED gap-fill; MTX↔Zuo, gout↔Yin-Fire context)
│   ├── drugs_batch11_gastroenterology.json # METACOD-RF research drug DB — batch 11 (33 GI (20 core + 13 expansion 429-441: rifaximin/UDCA/oral-budesonide/bile-acid-sequestrant/prucalopride/secretagogues/antispasmodic/pancrelipase/aprepitant…): PPI/H2/antacid/prokinetic/antiemetic/5-ASA/IBD-biologic/laxative; Mark primary specialty; batches 06/08/09/10 not in repo, IDs jump 118→180)
│   ├── drugs_batch12_neurology.json        # METACOD-RF research drug DB — batch 12 (32 neuro (15 core + 17 expansion 442-458: topiramate/oxcarbazepine/phenytoin/CBD/gepants/anti-CGRP/botox/COMT/amantadine/DA-agonists/AChEI/lecanemab/MS-DMTs/ALS…): antiepileptics/triptans/anti-CGRP/Parkinson/dementia/MS; DRG-202..216)
│   ├── drugs_batch13_urology_gyn.json      # METACOD-RF research drug DB — batch 13 (23 uro/gyn (15 core + 8 expansion 459-466: OAB-antimuscarinics/GnRH-antagonists/gonadotropins/oxytocin/misoprostol/dinoprostone/vaginal-estrogen/phenazopyridine): α1-blockers/PDE5/OAB/fertility-PCOS/gyn; DRG-217..231; source claimed 16, 15 enumerable)
│   ├── drugs_batch14_antimicrobials.json   # METACOD-RF research drug DB — batch 14 (18 antimicrobials: beta-lactams/macrolides/FQ/tetra/aminoglyc/glycopeptide/oxazolidinone/sulfa/nitrofurantoin/nitroimidazole/azole; DRG-232..249; CLAUDE-AUTHORED standard-evidence gap-fill, not Mark source; honors cross-ref cipro=239/moxi=241/metronidazole=248)
│   ├── drugs_batch15_antivirals.json       # METACOD-RF research drug DB — batch 15 (13 antivirals (5 core + 8 expansion 467-474: famciclovir/ganciclovir/baloxavir/Paxlovid/remdesivir/INSTI/HBV/letermovir): HSV/VZV/influenza/HIV-HBV/HCV-DAA; DRG-251..255; KCTS-text governance-flagged)
│   ├── drugs_batch16_oncology.json         # METACOD-RF research drug DB — batch 16 (12 targeted-oncology/hormonal: imatinib/trastuzumab/rituximab/bevacizumab/pembrolizumab/nivo-ipi/osimertinib/tamoxifen/letrozole/leuprolide-ADT/olaparib/ibrutinib; DRG-256..267; CLAUDE-AUTHORED standard-evidence gap-fill; leuprolide ties to Mark ADT support stack)
│   ├── drugs_batch17_anesthesia.json       # METACOD-RF research drug DB — batch 17 (18 anesthesia (10 core + 8 expansion 475-482: midazolam/dexmedetomidine/volatiles/NMB/local-anesthetics/dantrolene/N2O): IV induction/opioids/NMB/reversal; DRG-268..277; acute-use short profiles; KCTS pre-op hypothesis governance-flagged)
│   ├── drugs_batch18_addiction.json        # METACOD-RF research drug DB — batch 18 (10 addiction (8 core + 2 expansion 483-484: lofexidine/nalmefene): OUD/AUD/smoking/overdose-reversal; DRG-278..285; HIGH KCTS framing — evidence-based psychosocial-MAT separated from unvalidated Hamer/AIRE causal claim; naloxone standard-care primacy)
│   ├── drugs_batch19_geriatric.json        # METACOD-RF research drug DB — batch 19 (10 geriatric: framework-heavy — Beers/STOPP-START/CGA/deprescribing/ACB [GL]-anchored + Vit D/melatonin + apixaban/donepezil cross-refs; DRG-286..295)
│   ├── drugs_batch20_dermatology.json      # METACOD-RF research drug DB — batch 20 (24 derm (15 core + 9 expansion 485-493: mupirocin/calcipotriene/terbinafine/topical-antifungal/azelaic/imiquimod/5-FU/acitretin/dapsone): topical steroids/retinoids/calcineurin-inh/psoriasis-biologics/acne-rosacea/specific; DRG-296..310; lesion-systemic paradox RF hypothesis)
│   ├── drugs_batch21_ophthalmology.json    # METACOD-RF research drug DB — batch 21 (15 ophth (10 core + 5 expansion 494-498: netarsudil/pilocarpine/olopatadine/brinzolamide/acetazolamide): glaucoma PGA/BB/α2/CAI + dry-eye + anti-VEGF + topical abx/steroid cross-refs; DRG-311..320; topical→systemic absorption warning)
│   ├── drugs_batch22_ent.json              # METACOD-RF research drug DB — batch 22 (8 ENT: nasal steroid/2nd-gen antihistamine/montelukast x-ref/vestibular/decongestants/tinnitus framework; DRG-321..328; rhinitis medicamentosa flag)
│   ├── drugs_batch23_pediatric.json        # METACOD-RF research drug DB — batch 23 (7 peds, framework-heavy: prescribing/antibiotic/asthma/emergency frameworks + palivizumab/surfactant/ADHD-stimulants; DRG-329..335; source claimed 8, 7 enumerable; ACEs↔AIRE overlap flagged speculative)
│   ├── drugs_batch24_renal.json            # METACOD-RF research drug DB — batch 24 (10 renal (7 core + 3 expansion 499-501: K-binders/HIF-PHI/iron-based-binder): phosphate binders/ESA/active-VitD+calcimimetic/finerenone/tolvaptan; DRG-336..342; source claimed 8, 7 enumerable; STRONGEST KCTS operationalization push — 'CKD=textbook KCTS' hard-walled governance, standard-care primacy)
│   ├── drugs_batch25_rare_diseases.json    # METACOD-RF research drug DB — batch 25 (9 orphan: CFTR-modulators/HAE/lysosomal-ERT-SRT/PAH/SMA/gene-therapy/DMD; DRG-343..351; source claimed 10, 9 enumerable; 'post-cure'/gene-therapy=constitutional + KCTS-rare-disease framework Qs flagged for Mark)
│   ├── drugs_batch26_nutraceuticals.json   # METACOD-RF research drug DB — batch 26 (24 nutraceuticals (18 core + 6 expansion 502-507: CoQ10/zinc/vit-C/calcium/berberine/ALA): alkalinization 3:2:1/anabolic/omega-3/vitamins/adaptogens/microbiome/specific/melatonin; DRG-352..369; source claimed 17, 18 enumerable; HEAVIEST Mark-canonical content — 11 'CONFIRMED'/'PARTIAL' mapped to validation_state=partial (NOT full — sign-off pending); [RCT] now a valid majority-anchor; alkalinization+ADT-stack governance-noted)
│   ├── drugs_batch27_hematology.json       # METACOD-RF research drug DB — batch 27 (13 heme (8 core + 5 expansion 508-512: G-CSF/iron-chelators/anticoag-reversal/antifibrinolytics/protamine): oral/IV iron, hydroxyurea, eltrombopag/romiplostim, pentoxifylline, heme arginate, givosiran siRNA, eculizumab/ravulizumab; DRG-372..379, source skipped 370-371; authored post-KCTS-v1.1 reframe — sickle-cell = EBM psychosocial burden)
│   ├── constitutional_model_v0_1.json     # METACOD-RF constitutional model v0.1: conceptual two-axis framework (Parts A-E; constitution × process/phase)
│   ├── constitutional_model_v0_2.json     # METACOD-RF constitutional model: 5-energy biomarker quality panels (research, hypotheses)
│   ├── predictive_matrix_01_semaglutide.json # METACOD-RF predictive matrix #1: semaglutide × 8 constitutional triads (hypotheses)
│   ├── three_axis_framework_v1_0.json     # METACOD-RF three-axis diagnostic framework (Constitution × Membrane × Phase; research)
│   ├── diagnostic_foundation_v1_0.json    # METACOD-RF Diagnostics DB foundation (parallel to drug DB: lab/imaging/functional/procedures; 4 categories, 20-batch plan, Mark-canonical tiers BIA/urine-pH/Bristol/membrane-panel flagged RF; KCTS EBM-reframed; content_filling_started=false — awaiting Mark Q1-Q6)
│   ├── kcts_integration_v1_0.json         # METACOD-RF KCTS modifier — v1.1 EBM-REFORMULATED (Mark decision 2026-06): operative model = fluid-retention + chronic-stress physiology + psychosocial burden; Hamer/AIRE causality + collecting-tubule anatomy DISAVOWED (origin-only); governs all per-batch KCTS mentions; research-only, not operationalized, must not delay evidence-based care)
│   ├── topographic_atlas_v6_0.json        # METACOD-RF topographic atlas: 10 systems / 14 organs / 140 tissue-reactivity patterns (6-Ki, research)
│   ├── symptom_registry_v3_0.json         # METACOD-RF symptom registry: 35 detailed of 172 (histogenetic layer × 6-Ki × phase × membrane drift)
│   ├── nosology_registry_metabolic_cv_renal_v3_11.json # METACOD-RF nosology registry: diabetic + cardiovascular + nephro contours (21 patterns)
│   ├── nosology_registry_respiratory_v6_0.json         # METACOD-RF nosology registry: respiratory (tracheobronchial/alveolar/pleural, 30 patterns)
│   ├── nosology_registry_nephro_urinal_v3_12.json      # METACOD-RF nosology registry: nephro-urinal contour (11 patterns)
│   ├── nosology_registry_hepatobiliary_v6_0.json       # METACOD-RF nosology registry: hepatobiliary (13 patterns + lab panel)
│   ├── nosology_registry_cardiology_v6_0.json          # METACOD-RF nosology registry: cardiology (13 patterns)
│   ├── nosology_registry_spleen_pancreas_v6_0.json     # METACOD-RF nosology registry: spleen + pancreas (21 patterns + lab panel)
│   ├── nosology_registry_gallbladder_v6_0.json         # METACOD-RF nosology registry: gallbladder / biliary (12 patterns + lab panel)
│   ├── nosology_registry_small_intestine_v6_0.json     # METACOD-RF nosology registry: small intestine (10 patterns + lab panel)
│   └── nosology_registry_gastroduodenal_v6_0.json      # METACOD-RF nosology registry: stomach + duodenum (10 patterns + lab panel)
├── schemas/glp1_api.py          # Pydantic request/response models
├── reports/html_renderer.py     # HTML report (print-to-PDF)
├── requirements.txt
├── pytest.ini
├── tests/                       # clinical / unit / integration (621 tests, 0 skipped)
└── tests/unit/test_metacod_bridge.py  # METACOD TCM bridge: synthesis + layer-leakage guards + ordering
```

---

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/glp1/assess` | Run a new pharmacist assessment, persist as a Visit |
| `POST` | `/glp1/sign-off` | White Coat Rule — physician sign-off |
| `GET` | `/glp1/visit/{id}` | Fetch visit + sign-off history (i18n resolved) |
| `GET` | `/glp1/visit/{id}/report.html` | Printable report (locale, layer=clinical\|admin) |
| `GET` | `/glp1/visit/{id}/report.pdf` | Server-side PDF (WeasyPrint; 501 + fallback if absent) |
| `GET` | `/glp1/audit-log` | Filterable audit trail |
| `GET` | `/glp1/rules` | Introspect loaded rule_pack |
| `GET` | `/glp1/drugs` | Introspect drug DB |
| `GET` | `/glp1/visit/{id}/fhir-bundle` | HL7 FHIR R4 Bundle export (deterministic, `application/fhir+json`) |
| `GET` | `/glp1/learning/patterns` | Active-learning amendment analytics (counts, no PHI) |
| `GET` | `/glp1/_info` | Startup sanity probe (versions, counts) |

OpenAPI at `/docs` and `/redoc`.

---

## Run standalone (dev / Oleg)

```bash
cd python
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
METACOD_GLP1_INIT_DB=1 python main.py     # creates SQLite tables on first run
# open http://localhost:8001/docs
```

## Integrate into the v4 FastAPI app (non-invasive)

```python
# In your v4 app setup — add python/ to PYTHONPATH first.
from routers.glp1 import router as glp1_router
from services.resources import resources_cache
from services.i18n import i18n_cache
from pathlib import Path

DATA_DIR = Path("/path/to/python")  # holds rule_pack_v2.json, drug_master_v2.json, i18n_glp1_*.json

# v4 startup (lifespan or @app.on_event("startup")):
resources_cache.load(DATA_DIR / "rule_pack_v2.json", DATA_DIR / "drug_master_v2.json")
i18n_cache.load_all(base_dir=DATA_DIR)

app.include_router(glp1_router)   # existing v4 routes untouched; live at /glp1/*
```

### Env-var driven startup

```bash
export METACOD_GLP1_DATA_DIR=/opt/metacod/python
export METACOD_GLP1_DATABASE_URL=postgresql+psycopg://metacod:****@db/metacod
export METACOD_GLP1_CORS_ORIGINS=https://app.metacod.health
export METACOD_GLP1_INIT_DB=1   # dev only — production uses Alembic
```

---

## Database

- **Share v4's engine**: replace `SessionLocal` in `routers/glp1.py` with v4's session factory.
- **Dedicated GLP-1 DB**: set `METACOD_GLP1_DATABASE_URL`. Tables are namespaced and
  won't collide with v4 schema.
- First dev run: `METACOD_GLP1_INIT_DB=1 python main.py` (or `python database.py`).
- Production: `alembic upgrade head` (migration in `alembic_versions/`).

---

## i18n

Every clinical string leaves the agent as an i18n **key** (e.g. `action.lt4_check_tsh_4w`).
`resolve_i18n()` walks the assessment and adds sibling `*_i18n_text` fields for the
requested locale; the original keys are preserved (so audit stays locale-independent
and the same assessment can be re-rendered in another language). The `_meta.direction`
(`ltr`/`rtl`) is surfaced on the response so the frontend mirrors layout for Hebrew.

---

## Tests

```bash
cd python
. .venv/bin/activate
pip install -r requirements.txt
pytest                 # all 621 tests
pytest -m clinical     # SaMD reference cases only
pytest -m unit         # rule DSL safety + correctness
pytest -m integration  # full HTTP round-trip (TestClient + isolated SQLite)
pytest -k C04 -v       # a single clinical case by id
```

Three layers: **clinical** (60 SaMD reference cases — failures block rule_pack
release), **unit** (DSL eval safety/correctness), **integration** (TestClient against
an isolated SQLite DB per test).

> Coverage is complete: every rule in `rule_pack_v2.json` now has at least one
> positive clinical case, so the coverage meta-test passes (no skips).

---

## Versioning contract (SaMD traceability)

Every Visit pins `rule_pack_version`, `drug_db_version`, `agent_version` (`3.0.0`),
so past assessments remain reproducible when rules or drug profiles change.

---

## Deferred

- Server-side PDF (WeasyPrint) — endpoint returns 501 + browser-print fallback until installed.
- React UI on top of these endpoints.
- Extended rule_pack (30+) to exercise the new drug classes in drug_master v2
  (TKI/PPI, QT-combination, immunosuppressant, etc.). drug_db is already at 60 profiles.
- HL7 FHIR R4 export — DONE (/glp1/visit/{id}/fhir-bundle, Bundle: MedicationStatement / ServiceRequest / Observation / ClinicalImpression). EHR transaction-submit (POST) and FHIR profile validation remain future work.
