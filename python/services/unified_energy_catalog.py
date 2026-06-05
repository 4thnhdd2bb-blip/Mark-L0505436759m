"""
METACOD-RF Unified Energy Catalog — loader.

ENGINE-INTERNAL research framework (NOT clinical guidance, NOT patient-facing,
NOT operationalized). Loads unified_energy_catalog_v1_X.json: the consolidated
Park Jae Woo Six-Energies reference structured for patient analysis — Yin/Yang
primary routing → per-energy cards (chakra/meridians/organs/symptoms/diseases/
emotions/temperament/timing/windows) → clinical-system disease checklists → the
17 diagnostic channels, plus the six→five energy crosswalk and cross-references
to the rest of the RF layer.

The loader indexes structure only; no clinical re-interpretation. Energy is an
[RF] symptom-pattern descriptor — never a diagnosis or a prescribing trigger.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


class UnifiedEnergyCatalog:
    """Read-only view over the unified energy catalog document."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        with open(self.path, encoding="utf-8") as f:
            self._data = json.load(f)
        self.meta: dict = self._data.get("_meta", {})

    def section(self, key: str) -> Any:
        return self._data.get(key)

    @property
    def version(self) -> str:
        return str(self.meta.get("version", ""))

    @property
    def ready_for_clinical_use(self) -> bool:
        return bool(self.meta.get("ready_for_clinical_use", False))

    @property
    def ready_for_research_use(self) -> bool:
        return bool(self.meta.get("ready_for_research_use", False))

    @property
    def mark_validated(self):
        return self.meta.get("mark_validated", False)

    @property
    def governance(self) -> dict:
        return self.meta.get("governance_safety_annotation", {})

    @property
    def reconciliation(self) -> dict:
        return self.meta.get("energy_count_reconciliation", {})

    @property
    def energies(self) -> list[dict]:
        return list(self._data.get("energies", []))

    def energy(self, name: str) -> Optional[dict]:
        """Look up an energy card by id, name_ru or name_en (case-insensitive)."""
        key = name.strip().lower()
        for e in self.energies:
            if key in (str(e.get("id", "")).lower(),
                       str(e.get("name_ru", "")).lower(),
                       str(e.get("name_en", "")).lower()):
                return e
        return None

    @property
    def yin_yang_routing(self) -> dict:
        return self._data.get("yin_yang_routing", {})

    @property
    def clinical_systems(self) -> list[dict]:
        return list(self._data.get("clinical_systems", []))

    @property
    def diagnostic_channels(self) -> list[str]:
        return list(self._data.get("diagnostic_channels_17", {}).get("channels", []))

    @property
    def liver_mapping(self) -> dict:
        return self._data.get("liver_mapping_decision", {})

    @property
    def cross_references(self) -> dict:
        return self._data.get("cross_references", {})
