"""
METACOD-RF Topographic Atlas of Tissue Reactivity — loader.

ENGINE-INTERNAL research registry (NOT clinical guidance, NOT patient-facing).
Maps, per organ system / organ, a set of patterns: energy(6 Ki)/redox-status →
pole (Ян/Инь) → biophysical vector → clinical readout → ICD-10 + membrane code.

Canon note (preserved in _meta.canon_discrepancy_note): this atlas uses the
SIX Ki articulation (Тепло AND Жар separate), which is NOT the 5-energy canon
(post 01-Jun-2026 merge). So its energies do not map 1:1 to
services.metacod_bridge.ENERGY_AXES. Membrane codes DO align with the canonical
8 levels.

Structure-only; no clinical re-interpretation. The embedded triorigin_core.py
snippet is kept as a non-runnable documentation string (see _meta).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, Optional

CANONICAL_MEMBRANE_CODES = {"M-0", "M-A1", "M-A2", "M-A3", "M-S", "M-D1", "M-D2", "M-D3"}
PATTERN_KEYS = ("energy_redox", "pole", "biophysical_vector", "clinical_readout", "icd10", "membrane_code")


class TopographicAtlas:
    """Read-only view over the topographic atlas document."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self.meta: dict = data.get("_meta", {})
        self.redox_equivalents: dict = data.get("redox_equivalents", {})
        self._systems: list[dict] = data.get("systems", [])

    @property
    def version(self) -> str:
        return str(self.meta.get("version", ""))

    @property
    def ready_for_clinical_use(self) -> bool:
        return bool(self.meta.get("ready_for_clinical_use", False))

    @property
    def atlas_energies(self) -> list[str]:
        return list(self.meta.get("atlas_energies", []))

    def systems(self) -> list[str]:
        return [s["system"] for s in self._systems]

    def organs(self) -> list[dict]:
        out: list[dict] = []
        for s in self._systems:
            out.extend(s.get("organs", []))
        return out

    def patterns(self) -> Iterator[dict]:
        for s in self._systems:
            for organ in s.get("organs", []):
                yield from organ.get("patterns", [])

    def membrane_codes(self) -> set[str]:
        return {p.get("membrane_code") for p in self.patterns()}

    def icd10_codes(self) -> list[str]:
        return [p.get("icd10") for p in self.patterns()]

    def __len__(self) -> int:
        return sum(1 for _ in self.patterns())
