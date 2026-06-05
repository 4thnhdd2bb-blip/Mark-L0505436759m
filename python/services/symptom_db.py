"""
METACOD-RF Symptom DB loader (CONCORD-500 clinical-triage symptom catalog).

Parallel to services.metacod_rf (drug DB) and services.diagnostic_db (test DB).
Read-only views over sym_batch*.json (SYM-### ids). Each symptom carries standard
clinical fields ([GL]: differentials / red_flags / workup / screen / drug_induced)
plus an [RF] energy overlay (energy_primary / yang_yin). Research-only, not
operationalized, not a triage engine.

NB: this CONCORD SYM-### namespace is PARALLEL to (not unified with) the Park
symptom_registry_v3_0 sym_id namespace — see _meta.namespace_note.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator, Optional


class Symptom:
    __slots__ = ("_d",)

    def __init__(self, record: dict):
        self._d = record

    @property
    def sym_id(self) -> str:
        return self._d["id"]

    @property
    def name_ru(self) -> str:
        return self._d.get("name_ru", "")

    @property
    def popular(self) -> str:
        return self._d.get("popular", "")

    @property
    def system(self) -> str:
        return self._d.get("system", "")

    @property
    def level(self) -> str:
        return self._d.get("level", "")

    @property
    def energy_primary(self) -> str:
        """[RF] energy overlay (may be absent)."""
        return self._d.get("energy_primary", "")

    @property
    def red_flags(self) -> list[str]:
        return list(self._d.get("red_flags", []))

    @property
    def differentials(self) -> list[str]:
        return list(self._d.get("differentials", []))

    @property
    def is_emergency(self) -> bool:
        return "emergency" in str(self._d.get("yang_yin", "")).lower() or bool(self.red_flags)

    def get(self, key: str, default: Any = None) -> Any:
        return self._d.get(key, default)


class SymptomDB:
    """Loads and indexes one symptom batch JSON (sym_batch*.json)."""

    def __init__(self, batch_path: Path | str):
        self.path = Path(batch_path)
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self.meta: dict = data.get("_meta", {})
        self._by_id: dict[str, Symptom] = {}
        for rec in data.get("symptoms", []):
            s = Symptom(rec)
            self._by_id[s.sym_id] = s

    def get(self, sym_id: str) -> Optional[Symptom]:
        return self._by_id.get(sym_id)

    def all_ids(self) -> set[str]:
        return set(self._by_id.keys())

    def by_system(self, system: str) -> list[Symptom]:
        return [s for s in self._by_id.values() if s.system == system]

    def with_energy_overlay(self) -> list[Symptom]:
        return [s for s in self._by_id.values() if s.energy_primary]

    def __iter__(self) -> Iterator[Symptom]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    @property
    def ready_for_clinical_use(self) -> bool:
        return bool(self.meta.get("ready_for_clinical_use", False))
