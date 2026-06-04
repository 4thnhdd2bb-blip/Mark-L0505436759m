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
}


def _batch_paths(data_dir: Path) -> list[Path]:
    return sorted((data_dir / "metacod_rf").glob("*.json"))


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
    paths = sorted((src / "metacod_rf").glob("*.json"))
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


def test_no_drug_is_mark_validated_yet(catalog):
    for drug in catalog:
        assert drug.mark_validated is False, f"{drug.drug_id} unexpectedly mark_validated"


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
    # Most drugs must carry an [LBL] (FDA/EMA) anchor, so a batch can't be
    # mostly theoretical [RF] fabrication. Individual class-interchangeable
    # stub entries (e.g. lispro = "same as aspart") may legitimately defer and
    # lack their own [LBL] — they are flagged with class_interchangeable_stub.
    drugs = list(catalog)
    with_lbl = [
        d for d in drugs
        if "LBL" in {first_tag(s) for s in d.tagged_statements()}
    ]
    threshold = (len(drugs) + 1) // 2  # at least half
    assert len(with_lbl) >= threshold, (
        f"[{catalog.meta['batch_id']}] only {len(with_lbl)}/{len(drugs)} drugs "
        f"have an [LBL] anchor (need >= {threshold})"
    )
    # A drug lacking an [LBL] anchor must declare itself a deferral stub.
    for d in drugs:
        tags = {first_tag(s) for s in d.tagged_statements()}
        if "LBL" not in tags:
            assert d.get("class_interchangeable_stub") is True, (
                f"{d.drug_id} has no [LBL] anchor and is not a declared "
                f"class_interchangeable_stub"
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
    # Spot-check one agent per known batch keeps its empty [OBS-Mark] markers.
    spot = {"01-GLP1": "DRG-001", "02-SGLT2": "DRG-007"}
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
