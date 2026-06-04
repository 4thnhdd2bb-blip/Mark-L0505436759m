"""
METACOD-RF Constitutional Model — loader for the biomarker quality-panel model.

ENGINE-INTERNAL research model (NOT clinical guidance, NOT patient-facing).
Loads constitutional_model_v0_X.json: per-energy biomarker panels that map each
of the 5 energies (cold/damp/dry/heat/wind) to routine lab markers with a
three-zone quality structure (deficient / optimal / excess).

Per the document's own validation_status, the biomarker SELECTIONS are
HYPOTHESES (not validated correlations); optimal ranges are standard clinical
references + Mark's canonical adjustments. This loader preserves the content
verbatim and only indexes structure — no clinical re-interpretation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

# The 5 energy axes this model must cover (mirrors services.metacod_bridge.ENERGY_AXES).
ENERGY_KEYS = ("cold", "damp", "dry", "heat", "wind")

# Each per-energy marker row carries this three-zone quality structure.
MARKER_ZONE_KEYS = ("marker", "deficient_quality", "optimal_range", "excess_quality")


class ConstitutionalModel:
    """Read-only view over one constitutional-model JSON document."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self.meta: dict = data.get("_meta", {})
        self.panels: dict = data.get("energy_biomarker_panels", {})
        self.multi_energy_markers: list = data.get("multi_energy_markers", [])
        self.cross_reference: dict = data.get("cross_reference", {})

    def energies(self) -> set[str]:
        return set(self.panels.keys())

    def panel(self, energy: str) -> Optional[dict]:
        return self.panels.get(energy)

    def markers(self, energy: str) -> list[dict]:
        return list(self.panels.get(energy, {}).get("markers", []))

    def all_markers(self) -> list[dict]:
        out: list[dict] = []
        for energy in self.panels:
            out.extend(self.markers(energy))
        return out

    @property
    def version(self) -> str:
        return str(self.meta.get("version", ""))

    @property
    def ready_for_clinical_use(self) -> bool:
        return bool(self.meta.get("ready_for_clinical_use", False))

    @property
    def validation_status(self) -> dict[str, Any]:
        return self.meta.get("validation_status", {})
