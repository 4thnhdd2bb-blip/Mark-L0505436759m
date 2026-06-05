"""
METACOD-RF KCTS Integration — loader for the KCTS modifier document.

ENGINE-INTERNAL research document (NOT clinical guidance, NOT patient-facing).

KCTS (Kidney Collecting Tubule Syndrome) is a Hamer-derived research HYPOTHESIS
documented here as a "systemic modifier" over the three axes. This loader only
indexes structure and exposes the governance + cross-guard surfaces so tests can
enforce that the artifact stays research-only, is never operationalized into the
engine, never reorders evidence-based care, and never silently equates its
phase/membrane vocabulary with the canon.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class KCTSIntegration:
    """Read-only view over the KCTS integration JSON document."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        with open(self.path, encoding="utf-8") as f:
            self._data = json.load(f)
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
    def is_modifier_not_axis(self) -> bool:
        return bool(self.meta.get("critical_constants", {}).get("kcts_is_modifier_not_axis", False))

    @property
    def referenced_membrane_codes(self) -> list[str]:
        return list(self.meta.get("critical_constants", {}).get("referenced_membrane_codes", []))

    @property
    def phase_crosswalk(self) -> list[dict]:
        return list(self.meta.get("phase_crosswalk", []))

    @property
    def governance_annotation(self) -> dict:
        return self.meta.get("metacod_rf_governance_safety_annotation", {})

    @property
    def provenance_risk(self) -> dict:
        return self.meta.get("provenance_and_risk_note", {})
