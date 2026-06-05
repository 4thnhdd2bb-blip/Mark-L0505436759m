"""
METACOD-RF Master Integration — loader for the symptoms→diagnostics→drugs
architecture document (v1.1 CORRECTED).

ENGINE-INTERNAL research artifact (NOT clinical guidance, NOT patient-facing,
NOT operationalized). Records the corrected membrane canon (M-A anabolic /
M-D catabolic+inflammation / M-S sclerotic), the OPPOSITE treatment directions
per membrane, the 6-layer pipeline, and the drug-selection scoring — all [RF].
The loader indexes structure only; no clinical re-interpretation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MasterIntegration:
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
    def errata(self) -> dict:
        return self.meta.get("errata_v1_0_to_v1_1", {})

    @property
    def governance(self) -> dict:
        return self.meta.get("governance_safety_annotation", {})

    @property
    def membrane_canon(self) -> dict:
        return self._data.get("membrane_canon_v1_1", {})

    @property
    def treatment_direction(self) -> dict:
        return self._data.get("treatment_direction_v1_1", {})

    @property
    def layers(self) -> list[dict]:
        return list(self._data.get("six_layer_architecture", []))
