"""
METACOD-RF Diagnostic DB loader (lab / imaging / functional / procedures).

Parallel to services.metacod_rf (drug DB). Read-only views over dx_batch*.json.
Reuses the drug DB's provenance-tag helpers so the same governance gates apply:
tests carry [LBL]/[GL]/[RCT] external-evidence anchors with METACOD interpretive
overlays flagged [RF]; entries are research-only and never auto-validated.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator, Optional

from services.metacod_rf import iter_tagged_strings  # reuse tag walker


class DxTest:
    __slots__ = ("_d",)

    def __init__(self, record: dict):
        self._d = record

    @property
    def test_id(self) -> str:
        return self._d["test_id"]

    @property
    def name_full(self) -> str:
        return self._d["name_full"]

    @property
    def name_ru(self) -> str:
        return self._d.get("name_ru", "")

    @property
    def test_type(self) -> str:
        return self._d.get("test_type", "")

    @property
    def mark_validated(self):
        return self._d.get("status_flags", {}).get("mark_validated", False)

    @property
    def validation_state(self) -> str:
        v = self.mark_validated
        if v is True:
            return "full"
        if isinstance(v, str) and v.strip().upper().startswith("PARTIAL"):
            return "partial"
        return "none"

    @property
    def is_fully_validated(self) -> bool:
        return self.validation_state == "full"

    def get(self, key: str, default: Any = None) -> Any:
        return self._d.get(key, default)

    def tagged_statements(self) -> list[str]:
        return list(iter_tagged_strings(self._d))


class DxCatalog:
    """Loads and indexes one diagnostics batch JSON (dx_batch*.json)."""

    def __init__(self, batch_path: Path | str):
        self.path = Path(batch_path)
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self.meta: dict = data.get("_meta", {})
        self._by_id: dict[str, DxTest] = {}
        self._by_name: dict[str, DxTest] = {}
        for rec in data.get("tests", []):
            t = DxTest(rec)
            self._by_id[t.test_id] = t
            self._by_name[t.name_full.lower()] = t

    def get(self, test_id: str) -> Optional[DxTest]:
        return self._by_id.get(test_id)

    def by_name(self, name_full: str) -> Optional[DxTest]:
        return self._by_name.get(name_full.lower())

    def all_ids(self) -> set[str]:
        return set(self._by_id.keys())

    def __iter__(self) -> Iterator[DxTest]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    @property
    def ready_for_clinical_use(self) -> bool:
        return bool(self.meta.get("ready_for_clinical_use", False))
