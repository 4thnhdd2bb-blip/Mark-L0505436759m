"""
i18n coverage guard.

Ensures every i18n key referenced by rule_pack_v2.json resolves in all three
locales, and that RU/EN/HE have identical key sets. Catches missing translations
(which would render as [[key]] in the UI/report) before they ship.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

LOCALES = ("ru", "en", "he")


def _load_locale(data_dir: Path, loc: str) -> dict:
    data = json.loads((data_dir / f"i18n_glp1_{loc}.json").read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if k != "_meta"}


def _rule_pack_keys(data_dir: Path) -> set[str]:
    rp = json.loads((data_dir / "rule_pack_v2.json").read_text(encoding="utf-8"))
    keys: set[str] = set()
    for r in rp["rules"]:
        for a in r.get("physician_actions", []):
            keys.add(a["i18n_key"])
        for a in r.get("patient_actions", []):
            keys.add(a["i18n_key"])
        for lab in r.get("lab_plan", []):
            keys.add(lab["i18n_key"])
        internal = r.get("admin_layer", {}).get("i18n_key_internal")
        if internal:
            keys.add(internal)
    return keys


@pytest.mark.unit
def test_locales_have_identical_key_sets(data_dir):
    sets = {loc: set(_load_locale(data_dir, loc)) for loc in LOCALES}
    assert sets["ru"] == sets["en"] == sets["he"], (
        "Locale key-set mismatch: "
        f"ru-only={sorted(sets['ru'] - sets['en'] - sets['he'])} "
        f"en-only={sorted(sets['en'] - sets['ru'] - sets['he'])} "
        f"he-only={sorted(sets['he'] - sets['ru'] - sets['en'])}"
    )


@pytest.mark.unit
def test_every_rule_pack_key_resolves_in_all_locales(data_dir):
    needed = _rule_pack_keys(data_dir)
    assert needed, "rule_pack produced no i18n keys — check rule_pack_v2.json"
    for loc in LOCALES:
        present = set(_load_locale(data_dir, loc))
        missing = needed - present
        assert not missing, f"[{loc}] missing rule_pack i18n keys: {sorted(missing)}"


def _v3_keys() -> set[str]:
    """Every i18n key the v3 subsystems can emit (dose / pgx / ddi / projection)."""
    from pharmacist_agent import DoseIndividualization, InteractionMatrixEngine

    keys: set[str] = set()
    di = DoseIndividualization
    # BMI / Vd rationale keys
    for spec in di._BMI_VD_SENSITIVE.values():
        keys.add(spec["rationale_key"])
    # Pharmacogenomics keys (constructed exactly as the agent does)
    for phenotype, drugs in di._PGX_CYP2D6.items():
        for pid in drugs:
            keys.add(f"dose.pgx_cyp2d6_{phenotype}_{pid}")
    for phenotype, drugs in di._PGX_CYP2C19.items():
        for pid in drugs:
            keys.add(f"dose.pgx_cyp2c19_{phenotype}_{pid}")
    for phenotype, drugs in di._PGX_CYP3A5.items():
        for pid in drugs:
            keys.add(f"dose.pgx_cyp3a5_{phenotype}_{pid}")
    keys.add("dose.pgx_hla_b1502_carbamazepine")
    # Interaction matrix mechanism keys
    for _perp, _vic, _sev, _grade, mech_key in InteractionMatrixEngine._MATRIX:
        keys.add(mech_key)
    # Projection disclaimer
    keys.add("projection.linear_regression_disclaimer")
    return keys


@pytest.mark.unit
def test_every_v3_subsystem_key_resolves_in_all_locales(data_dir):
    needed = _v3_keys()
    assert needed, "no v3 keys collected — check pharmacist_agent v3 subsystems"
    for loc in LOCALES:
        present = set(_load_locale(data_dir, loc))
        missing = needed - present
        assert not missing, f"[{loc}] missing v3 subsystem i18n keys: {sorted(missing)}"
