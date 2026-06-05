"""
METACOD-RF CONCORD-500 v3.0 enrichment SPEC — loader.

ENGINE-INTERNAL research artifact. Records the v3.0 ENRICHED architecture
(3-layer enrichment: clinical / METACOD / graph) + distributions + honest
boundaries. NOT the data itself (the ~3 MB bundle and ~1.8 MB SQL are not in the
repo). Carries the CRITICAL governance flag: the v3.0 'conflict theme' Hamer
layer is in tension with the KCTS v1.1 disavowal and must be reconciled by Mark
before the data is materialized.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Concord500V3Spec:
    def __init__(self, path: Path | str):
        self._data = json.loads(Path(path).read_text(encoding="utf-8"))
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
    def governance(self) -> dict:
        return self.meta.get("governance_safety_annotation", {})

    @property
    def critical_flag(self) -> dict:
        return self.meta.get("CRITICAL_GOVERNANCE_FLAG", {})

    @property
    def enrichment_layers(self) -> dict:
        return self._data.get("enrichment_layers", {})

    @property
    def distributions(self) -> dict:
        return self._data.get("distributions_qc", {})
