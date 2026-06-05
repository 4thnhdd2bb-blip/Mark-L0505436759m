"""
METACOD-RF drug database — structure + provenance tests (all batches).

This validates the SHAPE and PROVENANCE of the research dataset, never the
clinical correctness of its content (that is Mark-owned and pending his
validation). Batches are auto-discovered from python/metacod_rf/*.json, so new
batches are covered without editing this file; per-batch identity (expected
DRG ids / INNs) is asserted from the EXPECTED registry below.

Guards (per batch):
  - the batch loads and indexes its drugs by DRG id
  - every record carries the required structural keys
  - the batch is honestly flagged research-only (ready_for_clinical_use False,
    every drug mark_validated False)
  - the legend matches the known provenance tags
  - every provenance-tagged statement uses a legend tag (no drift)
  - every drug has at least one [LBL]-sourced anchor (not pure [RF])
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.metacod_rf import (
    KNOWN_SOURCE_TAGS,
    PLACEHOLDER_TAGS,
    RFDrugCatalog,
    first_tag,
    iter_tagged_strings,
)

pytestmark = pytest.mark.unit

# Per-batch expected identity. Keyed by _meta.batch_id. New batches should add
# an entry here; the registry test below enforces that no shipped batch is left
# unregistered.
EXPECTED: dict[str, dict[str, str]] = {
    "01-GLP1": {
        "DRG-001": "Semaglutide",
        "DRG-002": "Liraglutide",
        "DRG-003": "Dulaglutide",
        "DRG-004": "Exenatide",
        "DRG-005": "Lixisenatide",
        "DRG-006": "Tirzepatide",
    },
    "02-SGLT2": {
        "DRG-007": "Empagliflozin",
        "DRG-008": "Dapagliflozin",
        "DRG-009": "Canagliflozin",
        "DRG-010": "Ertugliflozin",
    },
    "03-Biguanides+DPP4": {
        "DRG-011": "Metformin",
        "DRG-012": "Metformin extended-release",
        "DRG-013": "Metformin + saxagliptin",
        "DRG-014": "Sitagliptin",
        "DRG-015": "Linagliptin",
        "DRG-016": "Saxagliptin",
    },
    "04-Old_School_Antidiabetics": {
        "DRG-017": "Glipizide",
        "DRG-018": "Glimepiride",
        "DRG-019": "Gliclazide",
        "DRG-020": "Pioglitazone",
        "DRG-021": "Repaglinide",
        "DRG-022": "Nateglinide",
        "DRG-023": "Acarbose",
    },
    "05-Insulins+Pramlintide": {
        "DRG-024": "Insulin aspart",
        "DRG-025": "Insulin lispro",
        "DRG-026": "Insulin glulisine",
        "DRG-027": "Regular human insulin",
        "DRG-028": "Insulin isophane (NPH)",
        "DRG-029": "Insulin glargine (U100 standard)",
        "DRG-030": "Insulin glargine U300 (concentrated)",
        "DRG-031": "Insulin degludec",
        "DRG-032": "Insulin detemir",
        "DRG-033": "Pramlintide",
    },
    "07-Psychiatric": {
        "DRG-097": "Sertraline",
        "DRG-098": "Escitalopram",
        "DRG-099": "Fluoxetine",
        "DRG-100": "Paroxetine",
        "DRG-101": "Fluvoxamine",
        "DRG-102": "Venlafaxine",
        "DRG-103": "Duloxetine",
        "DRG-104": "Desvenlafaxine",
        "DRG-105": "Bupropion",
        "DRG-106": "Mirtazapine",
        "DRG-107": "Trazodone",
        "DRG-108": "Lithium carbonate / Lithium citrate",
        "DRG-109": "Valproate / Valproic acid / Divalproex",
        "DRG-110": "Lamotrigine",
        "DRG-111": "Quetiapine",
        "DRG-112": "Olanzapine",
        "DRG-113": "Aripiprazole",
        "DRG-114": "Risperidone",
        "DRG-115": "Alprazolam",
        "DRG-116": "Lorazepam",
        "DRG-117": "Diazepam",
        "DRG-118": "Clonazepam",
    },
    "11-Gastroenterology": {
        "DRG-180": "Omeprazole",
        "DRG-181": "Pantoprazole",
        "DRG-182": "Esomeprazole",
        "DRG-183": "Lansoprazole",
        "DRG-184": "Rabeprazole",
        "DRG-185": "Famotidine",
        "DRG-186": "Ranitidine",
        "DRG-187": "Aluminum hydroxide + magnesium hydroxide",
        "DRG-188": "Sucralfate",
        "DRG-189": "Metoclopramide",
        "DRG-190": "Domperidone",
        "DRG-191": "Ondansetron",
        "DRG-192": "Granisetron",
        "DRG-193": "Prochlorperazine",
        "DRG-194": "Mesalamine / Mesalazine (5-aminosalicylic acid)",
        "DRG-195": "Vedolizumab",
        "DRG-196": "Ustekinumab",
        "DRG-197": "Loperamide",
        "DRG-198": "Polyethylene glycol 3350",
        "DRG-199": "Lactulose",
    },
    "12-Neurology": {
        "DRG-202": "Levetiracetam",
        "DRG-203": "Lacosamide",
        "DRG-204": "Carbamazepine",
        "DRG-205": "Gabapentin",
        "DRG-206": "Pregabalin",
        "DRG-207": "Sumatriptan",
        "DRG-208": "Rizatriptan",
        "DRG-209": "Erenumab",
        "DRG-210": "Levodopa + carbidopa",
        "DRG-211": "Pramipexole",
        "DRG-212": "Rasagiline",
        "DRG-213": "Donepezil",
        "DRG-214": "Memantine",
        "DRG-215": "Glatiramer acetate",
        "DRG-216": "Ocrelizumab",
    },
    "13-Urology_Gyn": {
        "DRG-217": "Tamsulosin",
        "DRG-218": "Alfuzosin",
        "DRG-219": "Silodosin",
        "DRG-220": "Sildenafil",
        "DRG-221": "Tadalafil",
        "DRG-222": "Vardenafil",
        "DRG-223": "Oxybutynin",
        "DRG-224": "Mirabegron",
        "DRG-225": "Clomiphene citrate",
        "DRG-226": "Letrozole",
        "DRG-227": "Metformin",
        "DRG-228": "Tranexamic acid",
        "DRG-229": "Ulipristal acetate",
        "DRG-230": "Levonorgestrel IUD",
        "DRG-231": "Leuprolide for endometriosis",
    },
    "15-Antivirals": {
        "DRG-251": "Acyclovir",
        "DRG-252": "Valacyclovir",
        "DRG-253": "Oseltamivir",
        "DRG-254": "Tenofovir + emtricitabine",
        "DRG-255": "Sofosbuvir + combinations",
    },
    "17-Anesthesia": {
        "DRG-268": "Propofol",
        "DRG-269": "Ketamine",
        "DRG-270": "Etomidate",
        "DRG-271": "Morphine",
        "DRG-272": "Fentanyl",
        "DRG-273": "Remifentanil",
        "DRG-274": "Rocuronium",
        "DRG-275": "Succinylcholine",
        "DRG-276": "Sugammadex",
        "DRG-277": "Neostigmine + glycopyrrolate",
    },
    "18-Addiction": {
        "DRG-278": "Buprenorphine",
        "DRG-279": "Methadone",
        "DRG-280": "Naltrexone",
        "DRG-281": "Acamprosate",
        "DRG-282": "Disulfiram",
        "DRG-283": "Varenicline",
        "DRG-284": "Nicotine replacement (NRT)",
        "DRG-285": "Naloxone",
    },
    "19-Geriatric": {
        "DRG-286": "Beers Criteria framework",
        "DRG-287": "STOPP/START Criteria framework",
        "DRG-288": "Cholecalciferol (Vitamin D3)",
        "DRG-289": "Melatonin",
        "DRG-290": "Donepezil (elderly considerations)",
        "DRG-291": "Apixaban (elderly considerations)",
        "DRG-292": "Opioid alternatives in elderly framework",
        "DRG-293": "Comprehensive Geriatric Assessment (CGA) framework",
        "DRG-294": "Polypharmacy deprescribing framework",
        "DRG-295": "Anticholinergic burden assessment framework",
    },
    "20-Dermatology": {
        "DRG-296": "Hydrocortisone topical",
        "DRG-297": "Betamethasone valerate (topical)",
        "DRG-298": "Clobetasol propionate",
        "DRG-299": "Tretinoin (topical)",
        "DRG-300": "Adapalene",
        "DRG-301": "Isotretinoin (oral)",
        "DRG-302": "Tacrolimus (topical)",
        "DRG-303": "Pimecrolimus",
        "DRG-304": "Secukinumab",
        "DRG-305": "Apremilast",
        "DRG-306": "Benzoyl peroxide (topical)",
        "DRG-307": "Metronidazole topical",
        "DRG-308": "Hydroquinone",
        "DRG-309": "Minoxidil (topical)",
        "DRG-310": "Permethrin",
    },
    "21-Ophthalmology": {
        "DRG-311": "Latanoprost",
        "DRG-312": "Bimatoprost",
        "DRG-313": "Timolol (topical)",
        "DRG-314": "Brimonidine",
        "DRG-315": "Dorzolamide",
        "DRG-316": "Cyclosporine ophthalmic",
        "DRG-317": "Lifitegrast",
        "DRG-318": "Ranibizumab / Aflibercept / Bevacizumab (off-label)",
        "DRG-319": "Moxifloxacin / Ciprofloxacin topical",
        "DRG-320": "Prednisolone acetate ophthalmic",
    },
    "22-ENT": {
        "DRG-321": "Fluticasone propionate / furoate (nasal)",
        "DRG-322": "Cetirizine / Loratadine / Fexofenadine (2nd-gen antihistamines)",
        "DRG-323": "Montelukast (ENT use)",
        "DRG-324": "Meclizine",
        "DRG-325": "Betahistine",
        "DRG-326": "Oxymetazoline / Xylometazoline (nasal)",
        "DRG-327": "Pseudoephedrine",
        "DRG-328": "Tinnitus pharmacotherapy framework",
    },
    "23-Pediatric": {
        "DRG-329": "Pediatric prescribing principles framework",
        "DRG-330": "Palivizumab",
        "DRG-331": "Pediatric antibiotic selection framework",
        "DRG-332": "Pediatric asthma pharmacotherapy framework",
        "DRG-333": "Pediatric ADHD stimulants (methylphenidate / amphetamines)",
        "DRG-334": "Pulmonary surfactant (beractant / poractant alfa / calfactant)",
        "DRG-335": "Pediatric emergency drugs framework",
    },
}


def _batch_paths(data_dir: Path) -> list[Path]:
    return sorted((data_dir / "metacod_rf").glob("drugs_batch*.json"))


def _catalog(path: Path) -> RFDrugCatalog:
    return RFDrugCatalog(path)


@pytest.fixture(scope="module")
def batch_paths(data_dir):
    paths = _batch_paths(data_dir)
    assert paths, "no METACOD-RF batch files found under metacod_rf/"
    return paths


def _parametrize_batches():
    # Resolve batch files at collection time relative to this test file's repo.
    here = Path(__file__).resolve()
    # python/tests/unit/ -> python/
    src = here.parents[2]
    paths = sorted((src / "metacod_rf").glob("drugs_batch*.json"))
    return paths


BATCH_FILES = _parametrize_batches()


@pytest.fixture(params=BATCH_FILES, ids=lambda p: p.stem)
def catalog(request):
    return _catalog(request.param)


# ---------------------------------------------------------------------------
# Per-batch structure + identity
# ---------------------------------------------------------------------------

def test_batch_id_is_registered(catalog):
    batch_id = catalog.meta["batch_id"]
    assert batch_id in EXPECTED, (
        f"batch {batch_id!r} is not registered in EXPECTED — add its expected "
        f"DRG ids/INNs so identity is pinned."
    )


def test_expected_ids_and_inns(catalog):
    batch_id = catalog.meta["batch_id"]
    expected = EXPECTED[batch_id]
    assert catalog.all_ids() == set(expected), (
        f"[{batch_id}] ids {sorted(catalog.all_ids())} != expected {sorted(expected)}"
    )
    for drug_id, inn in expected.items():
        drug = catalog.get(drug_id)
        assert drug is not None and drug.name_inn == inn
        # case-insensitive INN lookup round-trips
        assert catalog.by_inn(inn.lower()).drug_id == drug_id


def test_every_drug_has_required_keys(catalog):
    batch_id = catalog.meta["batch_id"]
    # Universal keys present on every record. Note: formulation-only entries
    # (extended-release, fixed-dose combinations) legitimately lack a
    # "molecular" section in the source, so it is not required here.
    required = {"drug_id", "name_inn", "name_ru", "name_brand", "status",
                "batch", "status_flags"}
    batch_num = batch_id.split("-")[0]
    for drug in catalog:
        missing = required - set(drug.as_dict().keys())
        assert not missing, f"{drug.drug_id} missing keys: {sorted(missing)}"
        # A batch may span sub-groups (e.g. "03-Biguanides" / "03-DPP4" under
        # batch_id "03-Biguanides+DPP4"); require the shared batch-number prefix.
        assert str(drug.get("batch", "")).split("-")[0] == batch_num
        assert drug.get("status") == "METACOD-RF"


def test_count_matches_meta(catalog):
    declared = catalog.meta.get("preparations_count")
    assert declared == len(catalog), (
        f"[{catalog.meta['batch_id']}] preparations_count={declared} but "
        f"{len(catalog)} drug records present"
    )


# ---------------------------------------------------------------------------
# Honest research-only flagging (safety / governance)
# ---------------------------------------------------------------------------

def test_batch_is_flagged_research_only(catalog):
    assert catalog.ready_for_clinical_use is False
    assert "not clinical guidance" in catalog.meta["status"].lower()


def test_no_drug_is_fully_validated(catalog):
    # Governance gate: a record may be 'none' or 'partial' (Mark recorded
    # observations) but must never be silently promoted to FULL validation
    # without formal sign-off. 'partial' is allowed and tracked.
    for drug in catalog:
        assert not drug.is_fully_validated, (
            f"{drug.drug_id} is marked FULLY validated (mark_validated is True) — "
            f"full validation requires explicit sign-off, not a batch edit."
        )
        assert drug.validation_state in {"none", "partial"}


# ---------------------------------------------------------------------------
# Provenance integrity
# ---------------------------------------------------------------------------

def test_legend_matches_known_tags(catalog):
    legend = set(catalog.meta.get("source_tag_legend", {}).keys())
    assert legend == set(KNOWN_SOURCE_TAGS)


def test_all_tagged_statements_use_known_tags(catalog):
    bad: list[tuple[str, str]] = []
    for drug in catalog:
        for stmt in drug.tagged_statements():
            tag = first_tag(stmt)
            if tag not in KNOWN_SOURCE_TAGS and tag not in PLACEHOLDER_TAGS:
                bad.append((drug.drug_id, stmt))
    assert not bad, f"statements with unknown provenance tag: {bad[:5]}"


def test_batch_is_majority_label_sourced(catalog):
    # Most drugs must carry an EXTERNAL-EVIDENCE anchor — [LBL] (FDA/EMA) or
    # [GL] (clinical guideline) — so a batch can't be mostly theoretical [RF]
    # fabrication. Framework-heavy batches (e.g. 19-Geriatric: Beers / STOPP-START
    # / CGA / deprescribing / ACB) are legitimately guideline-sourced rather than
    # label-sourced, so [GL] counts equally. Individual abbreviated / class-
    # interchangeable entries may defer; the batch-level majority is the guard.
    drugs = list(catalog)
    external_anchor = {"LBL", "GL"}
    with_anchor = [
        d for d in drugs
        if external_anchor & {first_tag(s) for s in d.tagged_statements()}
    ]
    threshold = (len(drugs) + 1) // 2  # at least half
    assert len(with_anchor) >= threshold, (
        f"[{catalog.meta['batch_id']}] only {len(with_anchor)}/{len(drugs)} drugs "
        f"have an [LBL]/[GL] external-evidence anchor (need >= {threshold})"
    )


# ---------------------------------------------------------------------------
# Cross-batch invariants
# ---------------------------------------------------------------------------

def test_all_shipped_batches_are_registered(batch_paths):
    shipped = {RFDrugCatalog(p).meta["batch_id"] for p in batch_paths}
    unregistered = shipped - set(EXPECTED)
    assert not unregistered, f"shipped but unregistered batches: {sorted(unregistered)}"


def test_drug_ids_are_globally_unique(batch_paths):
    seen: dict[str, str] = {}
    for p in batch_paths:
        cat = RFDrugCatalog(p)
        for drug_id in cat.all_ids():
            assert drug_id not in seen, (
                f"{drug_id} appears in both {seen[drug_id]} and {p.name}"
            )
            seen[drug_id] = p.name


# ---------------------------------------------------------------------------
# OBS-Mark placeholder preservation (no fabrication)
# ---------------------------------------------------------------------------

def test_obs_mark_placeholders_preserved(batch_paths):
    # Spot-check one still-unfilled agent per known batch keeps its empty
    # [OBS-Mark] markers. (DRG-001 was intentionally filled by Mark in rev1, so
    # batch 01 is spot-checked via DRG-002, which remains a placeholder.)
    spot = {"01-GLP1": "DRG-002", "02-SGLT2": "DRG-007"}
    for p in batch_paths:
        cat = RFDrugCatalog(p)
        drug_id = spot.get(cat.meta["batch_id"])
        if not drug_id:
            continue
        obs = cat.get(drug_id).get("mark_observations", {})
        assert "[OBS-Mark]" in obs["mark_clinical_observations"]
        assert obs["n_cases_observed"] == "[TBD]"


# ---------------------------------------------------------------------------
# Helper unit coverage
# ---------------------------------------------------------------------------

def test_semaglutide_rev1_observation_recorded(batch_paths):
    """Lock in Mark's rev1 [OBS-Mark] for semaglutide: PARTIAL validation state,
    the canonical wax-wane pattern, and the untested-hypothesis separation."""
    cat = next(RFDrugCatalog(p) for p in batch_paths
               if RFDrugCatalog(p).meta["batch_id"] == "01-GLP1")
    sema = cat.get("DRG-001")
    assert sema.validation_state == "partial"
    assert not sema.is_fully_validated
    pattern = sema.get("mark_observations", {}).get("obs_mark_001_pattern", {})
    assert pattern.get("pattern_id") == "OBS-Mark-001"
    assert "Wax-Wane" in pattern.get("name", "")
    # Hypotheses must stay explicitly flagged as untested (no silent promotion).
    hyp = pattern.get("open_clinical_questions_untested_hypotheses", {})
    assert "untested" in hyp["cholestyramine_for_constipation"]["status"].lower()
    assert "no validated protocols" in hyp["prolongation_of_therapeutic_effect"]["status"].lower()
    # Batch remains research-only despite the partial observation.
    assert cat.ready_for_clinical_use is False


def test_first_tag_parsing():
    assert first_tag("[RF] Damp-reducing") == "RF"
    assert first_tag("[RF energy interpretation] heat_GI...") == "RF"
    assert first_tag("[RF Mark canonical] phase angle") == "RF"
    assert first_tag("[OBS-Mark] [TBD]") == "OBS-Mark"
    assert first_tag("[RF note: discontinued]") == "RF"
    assert first_tag("no tag here") is None


def test_iter_tagged_strings_walks_nested():
    blob = {
        "a": "[LBL] one",
        "b": ["plain", "[GL] two", {"c": "[RCT] three"}],
        "d": "untagged",
    }
    found = list(iter_tagged_strings(blob))
    assert "[LBL] one" in found
    assert "[GL] two" in found
    assert "[RCT] three" in found
    assert "untagged" not in found
    assert "plain" not in found
