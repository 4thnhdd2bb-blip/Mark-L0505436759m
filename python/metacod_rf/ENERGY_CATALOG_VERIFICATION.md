# Energy Catalog — Verification Report

**Source:** Park Jae Woo, «Теория Шести Энергий в рисунках и таблицах» — consolidated
extraction v0.2–v0.9 FINAL (`METACOD_Park_Symptoms_Consolidated` v1.0), supplied by Mark 2026-06.
**Scope of check:** correctness of the energy + disease catalogs already in the repo
("каталоги вчера") against this canonical source, and consolidation into one
`unified_energy_catalog_v1_0.json` for patient analysis.
**Status:** METACOD-RF research-only. `ready_for_clinical_use: false`. `mark_validated: pending review`.

---

## 1. What was verified

| Item | Source (Park) | Repo artifact(s) | Result |
|---|---|---|---|
| Energy count | **6** (Ветер/Тепло/Жар/Влажность/Сухость/Холод) | `topographic_atlas_v6_0` (6 Ki), `symptom_registry_v3_0` (6 Ki) | ✅ match — both RF artifacts use Park's six-energy articulation |
| Engine canon | — | `metacod_bridge.py`, `rule_energy_mapping.json` | ⚠️ engine uses **5** energies (Тепло+Жар→`heat`). Known + self-documented. Crosswalk now recorded. |
| Yang/Yin split | Yang = Heat/Fire/Wind; Yin = Damp/Dry/Cold (Tab 2) | new catalog | ✅ encoded as primary routing layer (22 discriminators) |
| Energy↔meridian | A/UM pairs K-L, F-E, J-I, C-D, B-A, G-H (Tab 5 ⟷ Tab 6) | new catalog | ✅ Tab 5 (quick-ref) and Tab 6 (psychoemotional) are mutually consistent |
| Energy↔chakra | Wind=Anahata, Heat=Vishuddha, Fire=Ajna, Damp=Manipura, Dry=Svadhisthana, Cold=Muladhara | new catalog | ✅ recorded verbatim |
| **Liver mapping** | **Liver = Wind** (Mark canonical, 23-05-2026; book alts Fire/Dry secondary) | new catalog `liver_mapping_decision` | ✅ canonical Liver=Wind; alts flagged secondary |
| Disease checklists | 9 clinical systems (neuro, endo, lymph, bone, spine, breast, GI, extremities, skin) | new catalog `clinical_systems` | ✅ transcribed by energy; standard disease names = independently valid |
| Redox equivalents | — | `topographic_atlas.redox_equivalents` groups **Тепло_Жар** together | ✅ consistent with the six→five merge |

**Conclusion:** the catalogs sent earlier are **correct and faithful** to the Park source.
The only reconciliation point is structural, not an error — see §2.

---

## 2. The one reconciliation: six energies vs five

- **Park canon = 6 energies.** Тепло (Heat — acute inflammation/hyperemia) and
  Жар (Fire — hypertension/obesity/sweating/metabolic) are **distinct**.
- **Engine canon = 5 energies.** `metacod_bridge` / `rule_energy_mapping` merge
  Тепло+Жар into a single `heat` axis (post 01-Jun-2026).
- **Rule (recorded in the catalog `_meta.energy_count_reconciliation`):** keep
  Park's full six-energy articulation in the RF layer (so the Heat/Fire
  distinction is never lost); collapse **Тепло+Жар → `heat`** only when mapping
  down to the engine. Crosswalk: `Wind=wind · Heat→heat · Fire→heat · Damp=damp · Dry=dry · Cold=cold`.

Both `symptom_registry_v3_0` and `topographic_atlas_v6_0` already carry the same
`canon_discrepancy_note`, so the layer is internally consistent.

---

## 3. The unified catalog (`unified_energy_catalog_v1_0.json`)

A single reference structured for patient analysis:

- **`yin_yang_routing`** — PRIMARY ROUTING LAYER (A vs УМ), 22 discriminators (Tab 2).
- **`energies[6]`** — one card per energy: polarity, chakra, A/UM meridians, organs,
  functional systems, core symptoms, universal symptom map, typical diseases,
  pain character, emotions, mental pattern, temperament, psychoemotional energies,
  windows, meteorological trigger, full timing (season/lunar/diurnal/life-cycle), redox equivalent.
- **`clinical_systems[9]`** — disease checklists by energy (incl. endocrine gland
  anatomical mapping + sexual-dysfunction table; lymphatic anatomical mapping).
- **`pain_differential`**, **`diagnostic_channels_17`**, **`liver_mapping_decision`**,
  **`usage_for_patient_analysis`** (6-step pipeline), **`cross_references`** to the rest of the RF layer.

Loader: `services/unified_energy_catalog.py`. Tests: `tests/unit/test_unified_energy_catalog.py` (11).

---

## 4. Governance (unchanged wall)

- Energy classification is an **[RF] symptom-pattern descriptor — not a diagnosis,
  not a prescribing trigger**. Standard ICD diagnosis + EBM care are primary and parallel.
- **Not operationalized** (documentation only), **not patient-facing** (Variant B),
  **no Hamer/AIRE psychic-conflict causality** (KCTS v1.1 EBM).
- Where an entry names a standard disease, that disease and its standard care are
  `[GL/RCT]`-valid **independently** of the energy label placed on it.

---

## 5. Open questions for Mark

1. **Q1 (energy mapping):** confirm the six→five collapse rule (Тепло+Жар→heat)
   is the intended engine behavior, or whether the engine should be lifted to six.
2. **Constitutional triad ↔ energy:** how the Park triads T1–T8 / Yin-Yang
   constitution axis binds to these six energies (constitution is a separate, slower axis).
3. **Channel weighting:** the 17 diagnostic channels currently carry no relative
   weights — pending Mark's voting/confidence scheme (Master Integration Layer-2 mentions an 8–12 concordant rule).
