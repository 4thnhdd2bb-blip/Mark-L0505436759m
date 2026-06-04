"""
METACOD-RF Three-Axis Diagnostic Framework — loader.

ENGINE-INTERNAL research framework (NOT clinical guidance, NOT patient-facing).
Loads three_axis_framework_v1_X.json: the integrating model over three
independent axes — Constitution (slow), Membrane (medium), Phase (fast) — plus
special patterns, integrated biomarker panels, integration scenarios, and the
open-problems / validation path.

The loader preserves content verbatim and only indexes structure — no clinical
re-interpretation. mark_validated is "pending review"; ready_for_clinical_use
is false.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


class ThreeAxisFramework:
    """Read-only view over one three-axis framework document."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self.meta: dict = data.get("_meta", {})
        self.axes: dict = data.get("axes", {})
        self.two_axis_interactions: dict = data.get("two_axis_interactions", {})
        self.special_patterns: dict = data.get("special_patterns", {})
        self.integrated_biomarker_panels: dict = data.get("integrated_biomarker_panels", {})
        self.three_axis_integration: dict = data.get("three_axis_integration", {})
        self.open_problems_validation: dict = data.get("open_problems_validation", {})
        self.quick_reference: dict = data.get("quick_reference", {})

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
    def constants(self) -> dict[str, Any]:
        return self.meta.get("critical_constants", {})

    def axis(self, name: str) -> Optional[dict]:
        return self.axes.get(name)

    def membrane_levels(self) -> dict:
        return self.axes.get("membrane", {}).get("levels", {})

    def membrane_level(self, level: str) -> Optional[dict]:
        return self.membrane_levels().get(level)

    def phases(self) -> dict:
        return self.axes.get("phase", {}).get("phase_signatures", {})

    def triads(self) -> list[dict]:
        return self.axes.get("constitutional", {}).get("triads", [])

    def scenarios(self) -> dict:
        return self.three_axis_integration.get("scenarios", {})
