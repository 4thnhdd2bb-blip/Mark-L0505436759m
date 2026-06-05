"""
METACOD-RF Symptom DB (CONCORD-500) — structure + governance + safety gates.

Verifies the materialized SYM-056..155 batch: 100 unique ids, research-only /
not-operationalized governance wall, emergency red-flag content preserved,
GLP-1 safety alert present, [RF] energy overlay marked, SYM-namespace parallel
flag recorded, no Hamer/AIRE causality.
"""

from __future__ import annotations

import json
import re

import pytest

from services.symptom_db import SymptomDB

pytestmark = pytest.mark.unit

BATCH = "sym_batch_concord500_056_155.json"


@pytest.fixture(scope="module")
def db(data_dir):
    return SymptomDB(data_dir / "metacod_rf" / BATCH)


def test_loads_100_unique_ids(db):
    assert len(db) == 100
    ids = db.all_ids()
    assert len(ids) == 100
    assert "SYM-056" in ids and "SYM-155" in ids


def test_research_only_governance_wall(db):
    assert db.ready_for_clinical_use is False
    assert "not clinical guidance" in db.meta["status"].lower()
    assert db.meta.get("mark_validated") == "pending review"
    g = db.meta["governance_safety_annotation"]
    for key in ("research_only", "red_flags_preserved", "energy_overlay_is_RF",
                "not_patient_facing", "drug_safety_flags", "no_hamer_aire_causality"):
        assert g.get(key), f"governance missing {key}"


def test_namespace_parallel_flag_recorded(db):
    note = db.meta.get("namespace_note", "").lower()
    assert "symptom_registry" in note and "parallel" in note
    assert "flag-for-mark" in note


def test_emergency_red_flags_preserved(db):
    # Safety-critical content must survive verbatim.
    seizure = db.get("SYM-114")
    assert any("status_epilepticus" in r for r in seizure.red_flags)
    stroke = db.get("SYM-101")
    assert any("tpa" in r.lower() or "thrombectomy" in r.lower() for r in stroke.red_flags)
    assert seizure.is_emergency


def test_glp1_safety_alert_present(db):
    suicide = db.get("SYM-136")
    blob = json.dumps(suicide.get("red_flags", []), ensure_ascii=False).lower()
    assert "glp1" in blob and "fda" in blob
    # GLP-1 functional fields preserved on appetite/satiety symptoms.
    assert db.get("SYM-063").get("glp1_alert")
    assert db.get("SYM-064").get("glp1_relation")


def test_energy_overlay_is_subset_and_marked(db):
    # Some symptoms carry the [RF] energy overlay, others (pure clinical) don't.
    with_e = db.with_energy_overlay()
    assert 0 < len(with_e) < len(db)
    assert db.get("SYM-145").energy_primary == "liver_qi_stagnation_heat"


def test_systems_indexing(db):
    assert len(db.by_system("neurological")) >= 20
    assert len(db.by_system("gi")) >= 15


def test_no_hamer_aire_causality(db):
    body = json.dumps([s._d for s in db], ensure_ascii=False).lower()
    assert not re.search(r"\baire\b", body)
    assert "hamer" not in body
