"""
METACOD-RF Symptom Registry — loader for the topographic symptom registry.

ENGINE-INTERNAL research registry (NOT clinical guidance, NOT patient-facing).
Each symptom (SYM-XXX) is decomposed by histogenetic layer, 6-Ki energy/redox
status, Hamer phase and membrane drift code. A verbatim backend preset
(symptoms_map) is preserved alongside the human-readable registry.

Canon note: uses 6 Ki (Тепло/Жар separate) — NOT the 5-energy canon; energies
are not equated with services.metacod_bridge.ENERGY_AXES. Membrane drift codes
may carry qualifiers («ложный»/false, «→»/«_to_» transitions); base_membrane_codes()
extracts the canonical-8 base code(s).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

CANONICAL_MEMBRANE_CODES = {"M-0", "M-A1", "M-A2", "M-A3", "M-S", "M-D1", "M-D2", "M-D3"}
SYMPTOM_KEYS = ("sym_id", "name", "histogenetic_layer", "energy_6ki", "phase",
                "membrane_drift", "pathophysiology")

_CODE_RE = re.compile(r"M-(?:0|A[123]|S|D[123])")


def base_membrane_codes(value: str) -> list[str]:
    """Extract canonical-8 base membrane code(s) from a drift string.

    "M-D1"            -> ["M-D1"]
    "M-D2 → M-S"      -> ["M-D2", "M-S"]
    "M-D2_to_M-S"     -> ["M-D2", "M-S"]
    "M-A3 ложный"     -> ["M-A3"]
    "M-A3_false"      -> ["M-A3"]
    """
    return _CODE_RE.findall(value or "")


class SymptomRegistry:
    """Read-only view over the symptom registry document."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self.meta: dict = data.get("_meta", {})
        self._symptoms: list[dict] = data.get("symptoms", [])
        self._by_id = {s["sym_id"]: s for s in self._symptoms}
        preset = data.get("backend_preset_symptoms_map", {})
        self.preset: dict = preset.get("symptoms_registry", {})

    @property
    def version(self) -> str:
        return str(self.meta.get("version", ""))

    @property
    def ready_for_clinical_use(self) -> bool:
        return bool(self.meta.get("ready_for_clinical_use", False))

    def symptoms(self) -> list[dict]:
        return list(self._symptoms)

    def get(self, sym_id: str) -> Optional[dict]:
        return self._by_id.get(sym_id)

    def ids(self) -> set[str]:
        return set(self._by_id.keys())

    def all_base_membrane_codes(self) -> set[str]:
        out: set[str] = set()
        for s in self._symptoms:
            out.update(base_membrane_codes(s.get("membrane_drift", "")))
        for entry in self.preset.values():
            out.update(base_membrane_codes(entry.get("membrane_code", "")))
        return out

    def __len__(self) -> int:
        return len(self._symptoms)
