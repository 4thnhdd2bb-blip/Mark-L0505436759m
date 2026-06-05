"""
METACOD-RF Unified Energy Catalog — structure + governance + Park-fidelity gates.

Verifies that the consolidated Park Six-Energies catalog is faithful to its
source (six energies, Yang/Yin split, Liver=Wind canonical, energy↔meridian
internal consistency) and stays behind the governance wall (research-only, not
operationalized, not patient-facing, no Hamer/AIRE causality, six→five crosswalk
recorded).
"""

from __future__ import annotations

import json
import re

import pytest

from services.unified_energy_catalog import UnifiedEnergyCatalog

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def cat(data_dir):
    return UnifiedEnergyCatalog(data_dir / "metacod_rf" / "unified_energy_catalog_v1_0.json")


def test_loads_v1_0(cat):
    assert cat.version == "1.0"
    assert cat.meta["schema"] == "metacod_rf_unified_energy_catalog"


def test_research_only_and_governance_wall(cat):
    assert cat.ready_for_clinical_use is False
    assert cat.ready_for_research_use is True
    assert cat.mark_validated == "pending review"
    g = cat.governance
    for key in ("energy_overlay_is_RF_construct", "not_operationalized",
                "not_patient_facing", "evidence_separation",
                "no_hamer_aire_causality"):
        assert g.get(key), f"governance missing {key}"


def test_six_energies_with_yang_yin_split(cat):
    energies = cat.energies
    assert len(energies) == 6
    names = {e["name_en"].split()[0] for e in energies}
    assert names == {"Wind", "Heat", "Fire", "Damp", "Dry", "Cold"}
    yang = [e for e in energies if e["polarity"] == "Yang"]
    yin = [e for e in energies if e["polarity"] == "Yin"]
    assert {e["name_en"].split()[0] for e in yang} == {"Wind", "Heat", "Fire"}
    assert {e["name_en"].split()[0] for e in yin} == {"Damp", "Dry", "Cold"}


def test_heat_and_fire_kept_separate(cat):
    # Park's distinction Тепло(Heat) vs Жар(Fire) must survive in the catalog...
    assert cat.energy("Тепло") is not None
    assert cat.energy("Жар") is not None
    # ...and the six→five engine crosswalk must record the merge.
    r = cat.reconciliation
    blob = json.dumps(r, ensure_ascii=False).lower()
    assert "merge" in blob or "слива" in blob or "сворач" in blob
    assert "heat" in r.get("crosswalk", "").lower()


def test_liver_is_wind_canonical(cat):
    lm = cat.liver_mapping
    assert "ветер" in lm.get("canonical", "").lower() or "wind" in lm.get("canonical", "").lower()
    # Wind energy card must carry Liver on the UM (Yin) meridian.
    wind = cat.energy("Ветер")
    assert "печень" in json.dumps(wind["meridians"], ensure_ascii=False).lower() \
        or "liver" in json.dumps(wind["meridians"], ensure_ascii=False).lower()


def test_each_energy_card_is_complete(cat):
    required = ("id", "name_ru", "name_en", "polarity", "chakra", "meridians",
                "organs", "functional_systems", "core_symptoms",
                "typical_diseases", "temperament", "windows", "timing")
    for e in cat.energies:
        for k in required:
            assert e.get(k), f"{e.get('id')} missing {k}"
        assert {"A_yang", "UM_yin"} <= set(e["meridians"].keys())


def test_yin_yang_routing_is_primary_layer(cat):
    yy = cat.yin_yang_routing
    assert len(yy.get("discriminators", [])) >= 18
    assert set(yy.get("yang_energies", [])) and set(yy.get("yin_energies", []))


def test_seventeen_diagnostic_channels(cat):
    assert len(cat.diagnostic_channels) == 17


def test_clinical_systems_present(cat):
    systems = cat.clinical_systems
    assert len(systems) >= 8
    joined = json.dumps(systems, ensure_ascii=False).lower()
    for token in ("невролог", "эндокрин", "лимфат"):
        assert token in joined


def test_cross_references_link_rf_layer(cat):
    xr = cat.cross_references
    for key in ("symptom_registry", "topographic_atlas", "master_integration",
                "engine_bridge", "drug_db", "diagnostic_db"):
        assert key in xr, f"cross_reference missing {key}"


def test_no_hamer_aire_causality(cat):
    # No psychic-conflict causal layer anywhere in the catalog body.
    blob = json.dumps(cat.section("energies"), ensure_ascii=False).lower()
    blob += json.dumps(cat.section("clinical_systems"), ensure_ascii=False).lower()
    assert not re.search(r"\baire\b", blob)
    assert "hamer" not in blob
    assert "not used" in cat.meta.get("kcts_v1_1_alignment", "").lower() \
        or "no hamer" in json.dumps(cat.governance, ensure_ascii=False).lower()
