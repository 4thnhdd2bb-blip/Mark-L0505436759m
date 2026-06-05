# METACOD-RF — Comprehensive Database Summary

**Status:** METACOD-RF — Research Framework, **NOT clinical guidance**.
**Scope:** the research-data layer under `python/metacod_rf/` (drug DB + conceptual/registry artifacts).
**Generated:** 2026-06, branch `claude/project-setup-la07j`. Figures below are machine-verified from the repo, not estimates.

> Companion docs: `METACOD_RF_HANDOFF.md` (continuity/decisions), `python/README_INTEGRATION.md` (file layout). This file is the at-a-glance state of the whole DB.

---

## 1. Scale (verified)

| Metric | Value |
|---|---|
| Drug-batch files | **27** |
| Total drug/concept entries | **507** (507 unique DRG IDs — no collisions) |
| — authored from Mark's pasted source docs | **220** |
| — Claude-authored (191 gap-fill batches + 133 expansion-block DRG-380..512) | **324** (flagged) |
| Conceptual / registry files | **17** (incl. diagnostics foundation) |
| Test suite | **639 passing, 0 skipped** |
| `ready_for_clinical_use` across **all** artifacts | **false** (verified) |

DRG ID space is essentially contiguous **DRG-001..379** core + a **380..512 expansion block** (133 class-completion entries across all systems). Documented minor gaps only: 200-201, 250, 370-371.

---

## 2. Batch inventory

✎ = Claude-authored standard-evidence gap-fill (reconcile with Mark's originals if they surface — his canonical observations take priority). All others materialized from Mark's pasted source docs.

| Batch | n | DRG | Auth | Group |
|---|---|---|---|---|
| 01-GLP1 | 6 | 001–006 | src | GLP-1 RA (DRG-001 semaglutide PARTIAL-validated) |
| 02-SGLT2 | 4 | 007–010 | src | SGLT2 inhibitors |
| 03-Biguanides+DPP4 | 6 | 011–016 | src | metformin + DPP-4 |
| 04-Old-school antidiabetics | 7 | 017–023 | src | SU/TZD/glinide/α-glucosidase |
| 05-Insulins | 10 | 024–033 | src | insulins + pramlintide |
| 06-Cardiovascular | 78 | 034–096 +380–394 | ✎ | BB/ACEi/ARB/ARNI/CCB/diuretics/MRA/statins/lipid/antiplatelet/anticoagulant/antiarrhythmic/digoxin/nitrate/ivabradine/PAH/pressor/ranolazine |
| 07-Psychiatric | 34 | 097–118 +417–428 | src✎ | antidepressants/antipsychotics/mood/anxiolytics |
| 08-Endocrine | 37 | 119–143 +395–406 | ✎ | thyroid/glucocorticoid/bone/pituitary/sex-hormone |
| 09-Pulmonology | 28 | 144–161 +407–416 | ✎ | bronchodilators/ICS/biologics/IPF-antifibrotics |
| 10-Rheumatology | 18 | 162–179 | ✎ | csDMARDs/biologics/JAK/gout |
| 11-Gastroenterology | 33 | 180–199 +429–441 | src✎ | PPI/H2/prokinetic/antiemetic/5-ASA/IBD-biologic/laxative (Mark's specialty) |
| 12-Neurology | 32 | 202–216 +442–458 | src✎ | antiepileptic/triptan/anti-CGRP/Parkinson/dementia/MS |
| 13-Urology/Gyn | 23 | 217–231 +459–466 | src✎ | α1-blocker/PDE5/OAB/fertility-PCOS |
| 14-Antimicrobials | 18 | 232–249 | ✎ | β-lactam/macrolide/FQ/tetra/aminoglycoside/glycopeptide/oxazolidinone/sulfa/nitrofurantoin/nitroimidazole/azole |
| 15-Antivirals | 13 | 251–255 +467–474 | src✎ | HSV/VZV/influenza/HIV-HBV/HCV-DAA |
| 16-Oncology | 12 | 256–267 | ✎ | TKI/mAb/checkpoint/hormonal(SERM/AI/GnRH-ADT)/PARP/BTK |
| 17-Anesthesia | 18 | 268–277 +475–482 | src✎ | IV induction/opioid/NMB/reversal |
| 18-Addiction | 10 | 278–285 +483–484 | src✎ | OUD/AUD/smoking/overdose-reversal |
| 19-Geriatric | 10 | 286–295 | src | Beers/STOPP-START/CGA/deprescribing/ACB + Vit D/melatonin + cross-refs |
| 20-Dermatology | 24 | 296–310 +485–493 | src✎ | topical steroid/retinoid/calcineurin/psoriasis-biologic/acne/specific |
| 21-Ophthalmology | 15 | 311–320 +494–498 | src✎ | glaucoma/dry-eye/anti-VEGF + cross-refs |
| 22-ENT | 8 | 321–328 | src | nasal steroid/antihistamine/vestibular/decongestant/tinnitus |
| 23-Pediatric | 7 | 329–335 | src | prescribing/antibiotic/asthma/emergency frameworks + palivizumab/surfactant/ADHD |
| 24-Renal | 10 | 336–342 +499–501 | src✎ | phosphate binders/ESA/active-VitD/calcimimetic/finerenone/tolvaptan |
| 25-Rare diseases | 9 | 343–351 | src | CFTR-modulators/HAE/lysosomal-ERT-SRT/PAH/SMA/gene-therapy/DMD |
| 26-Nutraceuticals | 24 | 352–369 +502–507 | src✎ | alkalinization 3:2:1 / ADT-stack / Zuo / Mariana / adaptogens / microbiome |
| 27-Hematology | 13 | 372–379 +508–512 | src✎ | iron/hydroxyurea/TPO-agonist/givosiran-siRNA/eculizumab-complement |

---

## 3. Provenance distribution (verified tag counts)

Every clinical statement carries a provenance tag. Counts across the DB:

| Tag | Meaning | Count |
|---|---|---|
| `[LBL]` | FDA/EMA label | 3150 |
| `[OBS-Mark]` | Mark clinical observation (mostly empty placeholders `[TBD]`) | 749 |
| `[GL]` | Clinical guideline | 511 |
| `[RF]` | Research-framework / theoretical (energy/membrane/phase overlay) | 426 |
| `[RCT]` | Named randomized trial / trial body | 169 |
| `[CLASS]` | Class extrapolation | 16 |
| `[TBD]`/`[GOVERNANCE]` | placeholders / governance annotations | 10 |

**Reading:** the DB is overwhelmingly anchored in external evidence (`LBL`+`GL`+`RCT` ≈ 3830 statements). `[RF]` (426) is the energy/three-axis overlay, always tagged as theoretical. `[OBS-Mark]` slots are reserved for Mark's input and remain largely unfilled (`[TBD]`).

---

## 4. Validation status (governance gate)

| State | Count | Notes |
|---|---|---|
| `none` | 495 | not yet Mark-reviewed |
| `partial` | 12 | Mark observations recorded, **not** full sign-off |
| `full` | **0** | full validation requires explicit formal sign-off — never auto-set |

The 12 `partial`: **DRG-001 semaglutide** (wax-wane observation OBS-Mark-001) + **11 batch-26 Mark-canonical nutraceuticals** (alkalinization NaHCO₃/KHCO₃/Mg, creatine, leucine, omega-3, Vit D ADT-dose, B-vitamin Zuo formula, NAC/serratiopeptidase/ectoin Mariana case). These reflect *Mark confirming his own protocols*, deliberately mapped to `partial` — **not** external EBM validation and **not** clinical readiness.

---

## 5. Governance posture (the safety line)

Enforced uniformly and checked by tests:

1. **Research-only.** Every artifact `ready_for_clinical_use: false`; status string contains "not clinical guidance".
2. **Not operationalized.** The RF layer (drug overlay, KCTS modifier, three-axis) is **not** wired into the engine: it does not change `rule_pack`, `metacod_bridge`, or any patient-facing output.
3. **Not patient-facing.** Internal energy/membrane/KCTS vocabulary never reaches patients (Patient-Facing Filter domain).
4. **Standard-care primacy.** Nothing in the RF layer may delay/replace/deprioritize evidence-based, time-critical care.
5. **Provenance honesty.** Pharmacology facts (`LBL/GL/RCT`) are separable from and valid independently of the `RF` overlay; class-interchangeable/abbreviated entries deferred honestly; source count discrepancies recorded (`source_count_claim` + `repo_gap_note`).

### KCTS — EBM-reformulated (v1.1, Mark decision 2026-06)
`kcts_integration_v1_0.json` is **v1.1 EBM-reframed**. Operative model = **EBM only**: persistent fluid-retention + chronic-stress physiology (HPA/cortisol/HRV) + low-grade inflammation (hsCRP) + psychosocial burden. **Hamer/GNM lineage, "AIRE" psychic-conflict causality, literal "collecting-tubule/endoderm/SBS" anatomy, and "Layer 0 = AIRE-first"** are **DISAVOWED as mechanism** (retained only as disclosed origin). The v1.1 doc **governs/supersedes** all per-batch mentions, and every legacy-bearing file now carries a `kcts_v1_1_alignment` note — the reframe is closed at the governance level.

---

## 5b. Diagnostics DB (parallel test/imaging database — STARTED)

Separate research database under the same governance wall (`dx_batch*.json`,
loader `services/diagnostic_db.py`, foundation `diagnostic_foundation_v1_0.json`).
Per Mark: full scope (~300-390 across lab/imaging/functional/procedures, 20 batches)
+ full Mark-canonical core; started **DX-18 (9 functional — BIA/DEXA/HRV/urine-pH/
SG/Bristol/Cole-Cole/grip/RMR)** and **DX-01 (14 foundation labs)** = 23 entries.
Tests **REVEAL** axis states (vs drugs target them); reference ranges/indications
= `[LBL/GL]`, energy/membrane/phase interpretation = `[RF]`; BIA phase-angle =
evidence-based prognostic, METACOD zone-mapping `[RF]`; Revici urine-pH / Bristol
energy-mapping / Cole-Cole membrane = `[RF]` hypotheses; KCTS EBM-reframed. 18 batches remain.

---

## 6. Conceptual / registry layer (17 files)

- `three_axis_framework_v1_0.json` — Constitution × Membrane × Phase
- `diagnostic_foundation_v1_0.json` — diagnostics DB architecture/foundation
- `kcts_integration_v1_0.json` — KCTS modifier (v1.1 EBM-reframed)
- `constitutional_model_v0_1.json` + `v0_2.json` — constitution model + 5-energy biomarker panels
- `predictive_matrix_01_semaglutide.json` — semaglutide × 8 constitutional triads (hypotheses)
- `symptom_registry_v3_0.json`, `topographic_atlas_v6_0.json`
- 9 nosology registries (metabolic-cv-renal, respiratory, nephro-urinal, hepatobiliary, cardiology, spleen-pancreas, gallbladder, small-intestine, gastroduodenal)

Loaders for each live in `python/services/`; cross-guards keep RF vocabulary (6-Ki, membrane codes, phases) from being silently equated with the engine canon.

---

## 7. Cross-reference integrity (honored throughout gap-fill)

apixaban=DRG-082 (↔19), prednisolone=125 (↔21), montelukast=148 (↔22), ciprofloxacin=239 / moxifloxacin=241 / metronidazole=248 (↔20/21), bevacizumab in 16 (↔21 anti-VEGF), leuprolide/ADT (↔26 ADT support stack), folate+MTX Zuo (10↔26), gout agents ↔ Mark Yin-Fire context.

---

## 8. Mark-canonical anchors preserved (documented, not fabricated)

- **Alkalinization 3:2:1** (NaHCO₃:KHCO₃:Mg) — universal Layer 1 *(research-only; physiologic universality not externally validated — governance-noted)*.
- **ADT support stack** (creatine 5 g / leucine 3 g·meal / Vit D 4000–5000 / EPA 2–4 g + resistance training + BIA/DEXA/PHQ-9) — most evidence-grounded canonical element (sarcopenia prevention).
- **Zuo (compensatory-protection) formula** (B12+metformin, folate+MTX, omega-3+statin).
- **Mariana case** — flagship n=1 (bronchiectasis), reframed EBM: standard antimicrobial first-line + concurrent psychosocial/supplement adjuncts.
- Long-term steroid → M-A2→M-A3; long-term GLP-1 → sarcopenia; ADT → M-A→M-D2/D3 (documented membrane observations).

---

## 9. Pending (physician-owned — do NOT fabricate)

- `[OBS-Mark]` fields across the DB (most valuable in gastroenterology, batch 11).
- Su Jok protocols; "Immature Wind" concept; retrospective validation cases.
- Open architecture Qs: **Q1** 6-Ki→5-energy mapping, **Q2** `treatment_sequence` order.
- Reconciliation of Claude-authored gap-fill batches (06/08/09/10/14/16) with Mark's own versions if they surface.
- **No drug entry is `full`-validated** — full sign-off is an explicit Mark act, never a batch edit.

---

*This summary is regenerated as the DB grows; figures verified against the repo at generation time.*
