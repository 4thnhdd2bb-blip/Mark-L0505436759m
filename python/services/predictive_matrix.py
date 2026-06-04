"""
METACOD-RF Predictive Matrix — loader for drug × constitutional-triad
response-prediction matrices.

ENGINE-INTERNAL research model (NOT clinical guidance, NOT patient-facing).
Every prediction is a HYPOTHESIS (drug energy profile × constitutional triad →
predicted response pattern), pending retrospective/prospective validation.

The loader preserves content verbatim and only indexes structure (triads,
per-triad predictions over the declared predicted_parameters) — no clinical
re-interpretation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

# The five predicted parameters every prediction must cover.
PREDICTED_PARAM_KEYS = (
    "titration_tolerance",
    "peak_adaptation_speed",
    "late_phase_dominant_AE",
    "predicted_efficacy_magnitude",
    "predicted_efficacy_duration",
)


class PredictiveMatrix:
    """Read-only view over one predictive-matrix JSON document."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self.meta: dict = data.get("_meta", {})
        self._triads: list[dict] = data.get("triads", [])
        self._predictions: list[dict] = data.get("predictions", [])
        self.clinical_navigation: dict = data.get("clinical_navigation", {})
        self._triad_by_id = {t["id"]: t for t in self._triads}
        self._pred_by_triad = {p["triad_id"]: p for p in self._predictions}

    @property
    def matrix_id(self) -> str:
        return str(self.meta.get("matrix_id", ""))

    @property
    def drug_id(self) -> str:
        return str(self.meta.get("drug_id", ""))

    @property
    def ready_for_clinical_use(self) -> bool:
        return bool(self.meta.get("ready_for_clinical_use", False))

    @property
    def all_predictions_are_hypotheses(self) -> bool:
        return bool(self.meta.get("all_predictions_are_hypotheses", False))

    def triad_ids(self) -> list[str]:
        return [t["id"] for t in self._triads]

    def triad(self, triad_id: str) -> Optional[dict]:
        return self._triad_by_id.get(triad_id)

    def prediction(self, triad_id: str) -> Optional[dict]:
        return self._pred_by_triad.get(triad_id)

    def predictions(self) -> list[dict]:
        return list(self._predictions)

    def __len__(self) -> int:
        return len(self._triads)
