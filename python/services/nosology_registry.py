"""
METACOD-RF Nosology Registry — loader for nosology-pattern registries.

ENGINE-INTERNAL research registries (NOT clinical guidance, NOT patient-facing).
Each pattern maps a nosology (+ ICD-10) through a 6-Ki energy/redox status to a
SYM readout, optional lab markers, and a membrane drift code. Used by the
extended metabolic/cardiovascular/renal, respiratory and nephro-urinal blocks.

Canon note: 6 Ki (Тепло/Жар separate) — NOT the 5-energy canon; energies are not
equated with services.metacod_bridge.ENERGY_AXES. Membrane drift codes may carry
qualifiers/transitions; base codes are extracted via
services.symptom_registry.base_membrane_codes and cross-guarded to the canonical 8.
Therapy hard-stops are physician-owned data, not operationalized.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterator

from services.symptom_registry import CANONICAL_MEMBRANE_CODES, base_membrane_codes

PATTERN_REQUIRED_KEYS = ("nosology", "icd10", "energy_6ki", "redox_equivalent",
                         "sym_readout", "membrane_drift")

_SYM_REF_RE = re.compile(r"SYM-\d+")


class NosologyRegistry:
    """Read-only view over one nosology-pattern registry document."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self.meta: dict = data.get("_meta", {})
        self._contours: list[dict] = data.get("contours", [])

    @property
    def version(self) -> str:
        return str(self.meta.get("version", ""))

    @property
    def ready_for_clinical_use(self) -> bool:
        return bool(self.meta.get("ready_for_clinical_use", False))

    def contour_names(self) -> list[str]:
        return [c["contour"] for c in self._contours]

    def patterns(self) -> Iterator[dict]:
        for c in self._contours:
            yield from c.get("patterns", [])

    def all_base_membrane_codes(self) -> set[str]:
        out: set[str] = set()
        for p in self.patterns():
            out.update(base_membrane_codes(p.get("membrane_drift", "")))
        return out

    def numeric_sym_refs(self) -> set[str]:
        out: set[str] = set()
        for p in self.patterns():
            for item in p.get("sym_readout", []):
                out.update(_SYM_REF_RE.findall(item))
        return out

    def __len__(self) -> int:
        return sum(1 for _ in self.patterns())
