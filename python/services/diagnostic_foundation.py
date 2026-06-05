"""
METACOD-RF Diagnostic Tests & Imaging — Foundation loader.

Parallel research-data layer to the drug DB: architecture/schema for a future
diagnostics database (lab / imaging / functional / procedures). This is an
ARCHITECTURE PROPOSAL — content is NOT filled (content_filling_started == False)
and the artifact stays inside the governance wall: research-only, not
operationalized, not patient-facing, KCTS detection EBM-reframed per v1.1.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DiagnosticFoundation:
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
    def content_filling_started(self) -> bool:
        return bool(self.meta.get("content_filling_started", False))

    @property
    def id_prefixes(self) -> dict:
        return self._data.get("id_prefixes", {})

    @property
    def categories(self) -> list[dict]:
        return list(self._data.get("categories", []))

    @property
    def entry_template_keys(self) -> list[str]:
        return list(self._data.get("entry_template_keys", []))

    @property
    def batch_plan(self) -> list[dict]:
        return list(self._data.get("proposed_batch_plan", []))

    @property
    def open_questions(self) -> list[str]:
        return list(self._data.get("open_questions_for_mark", []))

    @property
    def mark_canonical_tiers(self) -> dict:
        return self._data.get("mark_canonical_priority_tiers", {})

    @property
    def kcts_detection_ebm(self) -> dict:
        return self._data.get("kcts_detection_ebm", {})

    @property
    def governance(self) -> dict:
        return self.meta.get("governance_safety_annotation", {})
