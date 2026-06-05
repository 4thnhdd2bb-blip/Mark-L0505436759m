"""
METACOD-RF Diagnostic Algorithms — loader.

ENGINE-INTERNAL research artifact (NOT clinical guidance, NOT patient-facing,
NOT operationalized). Loads diagnostic_algorithms_v1_X.json: the consolidated
patient-analysis decision flows (ALG-0 .. ALG-10) that tie together the Park
six-energy routing, constitution, membrane (corrected canon), phase, KCTS,
biomarker-quality, nosology, three-axis synthesis, drug-selection scoring, and
monitoring.

These are DOCUMENTED reasoning flows, not validated diagnostic criteria. The
loader indexes structure only; no clinical re-interpretation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


class DiagnosticAlgorithms:
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
    def unresolved_discrepancies(self) -> dict:
        return self.meta.get("unresolved_discrepancies", {})

    @property
    def algorithms(self) -> list[dict]:
        return list(self._data.get("algorithms", []))

    @property
    def ids(self) -> list[str]:
        return [a.get("id", "") for a in self.algorithms]

    def algorithm(self, alg_id: str) -> Optional[dict]:
        key = alg_id.strip().upper()
        for a in self.algorithms:
            if str(a.get("id", "")).upper() == key:
                return a
        return None

    @property
    def pipeline_order(self) -> list[str]:
        return list(self._data.get("pipeline_overview", {}).get("order", []))
