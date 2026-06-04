"""
METACOD-RF drug database — batch 01 (GLP-1) structure + provenance tests.

This validates the SHAPE and PROVENANCE of the research dataset, never the
clinical correctness of its content (that is Mark-owned and pending his
validation). Guards:
  - the batch loads, indexes 6 drugs with the expected DRG ids
  - every record carries the required structural keys
  - the batch is honestly flagged research-only (ready_for_clinical_use False,
    every drug mark_validated False)
  - every provenance-tagged statement uses a tag from the legend (no drift)
  - [OBS-Mark] placeholders are preserved (not silently invented/filled)
"""

from __future__ import annotations

import pytest

from services.metacod_rf import (
    KNOWN_SOURCE_TAGS,
    PLACEHOLDER_TAGS,
    RFDrugCatalog,
    first_tag,
    iter_tagged_strings,
)

pytestmark = pytest.mark.unit

EXPECTED_IDS = {"DRG-001", "DRG-002", "DRG-003", "DRG-004", "DRG-005", "DRG-006"}
EXPECTED_INNS = {
    "DRG-001": "Semaglutide",
    "DRG-002": "Liraglutide",
    "DRG-003": "Dulaglutide",
    "DRG-004": "Exenatide",
    "DRG-005": "Lixisenatide",
    "DRG-006": "Tirzepatide",
}


@pytest.fixture(scope="module")
def rf_catalog(data_dir):
    return RFDrugCatalog(data_dir / "metacod_rf" / "drugs_batch01_glp1.json")


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_batch_loads_six_drugs(rf_catalog):
    assert len(rf_catalog) == 6
    assert rf_catalog.all_ids() == EXPECTED_IDS
    assert rf_catalog.meta["batch_id"] == "01-GLP1"


def test_expected_inns_and_lookup(rf_catalog):
    for drug_id, inn in EXPECTED_INNS.items():
        drug = rf_catalog.get(drug_id)
        assert drug is not None
        assert drug.name_inn == inn
        # case-insensitive INN lookup round-trips to the same record
        assert rf_catalog.by_inn(inn.lower()).drug_id == drug_id
    assert rf_catalog.get("DRG-999") is None


def test_every_drug_has_required_keys(rf_catalog):
    required = {"drug_id", "name_inn", "name_ru", "name_brand", "status", "batch",
                "molecular", "status_flags"}
    for drug in rf_catalog:
        missing = required - set(drug.as_dict().keys())
        assert not missing, f"{drug.drug_id} missing keys: {sorted(missing)}"
        assert drug.get("batch") == "01-GLP1"
        assert drug.get("status") == "METACOD-RF"


# ---------------------------------------------------------------------------
# Honest research-only flagging (safety / governance)
# ---------------------------------------------------------------------------

def test_batch_is_flagged_research_only(rf_catalog):
    assert rf_catalog.ready_for_clinical_use is False
    assert "not clinical guidance" in rf_catalog.meta["status"].lower()


def test_no_drug_is_mark_validated_yet(rf_catalog):
    # The batch ships with mark_validated False everywhere; this gate prevents
    # a record being silently promoted to "validated" without Mark's sign-off.
    for drug in rf_catalog:
        assert drug.mark_validated is False, f"{drug.drug_id} unexpectedly mark_validated"


def test_obs_mark_placeholders_preserved(rf_catalog):
    # Semaglutide carries several [OBS-Mark] placeholders that must stay as
    # authored (empty/TBD), never fabricated.
    sema = rf_catalog.get("DRG-001")
    obs = sema.get("mark_observations", {})
    assert "[OBS-Mark]" in obs["mark_clinical_observations"]
    assert obs["n_cases_observed"] == "[TBD]"


# ---------------------------------------------------------------------------
# Provenance integrity
# ---------------------------------------------------------------------------

def test_all_tagged_statements_use_known_tags(rf_catalog):
    bad: list[tuple[str, str]] = []
    for drug in rf_catalog:
        for stmt in drug.tagged_statements():
            tag = first_tag(stmt)
            if tag not in KNOWN_SOURCE_TAGS and tag not in PLACEHOLDER_TAGS:
                bad.append((drug.drug_id, stmt))
    assert not bad, f"statements with unknown provenance tag: {bad[:5]}"


def test_legend_matches_known_tags(rf_catalog):
    legend = set(rf_catalog.meta.get("source_tag_legend", {}).keys())
    assert legend == set(KNOWN_SOURCE_TAGS)


def test_every_drug_has_at_least_one_label_sourced_statement(rf_catalog):
    # Each agent should have at least one [LBL] (FDA/EMA) anchor — i.e. the
    # record isn't purely theoretical [RF] content.
    for drug in rf_catalog:
        tags = {first_tag(s) for s in drug.tagged_statements()}
        assert "LBL" in tags, f"{drug.drug_id} has no [LBL]-sourced statement"


# ---------------------------------------------------------------------------
# Helper unit coverage
# ---------------------------------------------------------------------------

def test_first_tag_parsing():
    assert first_tag("[RF] Damp-reducing") == "RF"
    assert first_tag("[RF energy interpretation] heat_GI...") == "RF"
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
