"""
METACOD-RF (Research Framework) drug database — loader + read-only catalog.

This is an ENGINE-INTERNAL research dataset, NOT clinical guidance and NOT a
patient-facing surface. Each batch JSON (e.g. metacod_rf/drugs_batch01_glp1.json)
holds drug records whose statements are provenance-tagged:

    [LBL]      FDA / EMA label
    [GL]       clinical guideline (ESC/ADA/AACE/...)
    [RCT]      a specific RCT
    [CLASS]    class pattern extrapolation
    [OBS-Mark] Mark's clinical observation (often a pending placeholder)
    [RF]       METACOD research-framework hypothesis (theoretical, unvalidated)

The catalog is deliberately schema-light: it preserves the authored content
verbatim (no clinical re-interpretation) and only indexes/validates structure
and provenance so downstream code and tests can reason about it.

Mark owns all clinical content; [OBS-Mark] placeholders stay empty until he
fills them, and `status_flags.mark_validated` gates research-readiness.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterator, Optional

# The recognised provenance tags (the batch _meta.source_tag_legend keys, plus
# the compound "[RF energy interpretation]" / "[RF note: ...]" free forms which
# still resolve to the RF tag). Anything else is flagged by validation.
KNOWN_SOURCE_TAGS = ("LBL", "GL", "RCT", "CLASS", "OBS-Mark", "RF")

# Non-source bracketed prefixes that legitimately appear but are NOT provenance
# claims: "[TBD]" in unfilled fields, and "[GOVERNANCE]" on METACOD-RF safety
# annotations (e.g. standard-care-primacy notes on KCTS-derived content). Not a
# provenance violation.
PLACEHOLDER_TAGS = ("TBD", "GOVERNANCE")

# Matches a leading provenance tag such as "[LBL]" / "[OBS-Mark]" /
# "[RF energy interpretation]" / "[RF note: ...]".
_TAG_RE = re.compile(r"\[(?P<tag>[A-Za-z][A-Za-z0-9\- ]*?)(?::[^\]]*)?\]")


def first_tag(text: str) -> Optional[str]:
    """Return the first bracketed tag's leading token, or None.

    "[RF] Damp-reducing"            -> "RF"
    "[RF energy interpretation] .." -> "RF"
    "[OBS-Mark] [TBD]"              -> "OBS-Mark"
    "no tag here"                   -> None
    """
    m = _TAG_RE.match(text.strip())
    if not m:
        return None
    return m.group("tag").split()[0]


def iter_tagged_strings(value: Any) -> Iterator[str]:
    """Yield every string that carries a leading provenance tag, walking
    nested dicts/lists. Strings without a leading tag are skipped."""
    if isinstance(value, str):
        if _TAG_RE.match(value.strip()):
            yield value
    elif isinstance(value, list):
        for item in value:
            yield from iter_tagged_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_tagged_strings(item)


class RFDrug:
    """Read-only view over a single drug record."""

    __slots__ = ("_d",)

    def __init__(self, record: dict):
        self._d = record

    @property
    def drug_id(self) -> str:
        return self._d["drug_id"]

    @property
    def name_inn(self) -> str:
        return self._d["name_inn"]

    @property
    def name_ru(self) -> str:
        return self._d.get("name_ru", "")

    @property
    def mark_validated(self):
        """Raw status_flags.mark_validated value.

        Tri-state, set by Mark only:
          False     — not yet reviewed
          "PARTIAL" — clinical pattern observations recorded, NOT full validation
          True       — fully validated (requires formal sign-off; not auto-set)
        """
        return self._d.get("status_flags", {}).get("mark_validated", False)

    @property
    def validation_state(self) -> str:
        """Normalized: 'none' | 'partial' | 'full'."""
        v = self.mark_validated
        if v is True:
            return "full"
        if isinstance(v, str) and v.strip().upper().startswith("PARTIAL"):
            return "partial"
        return "none"

    @property
    def is_fully_validated(self) -> bool:
        return self.validation_state == "full"

    def get(self, key: str, default: Any = None) -> Any:
        return self._d.get(key, default)

    def as_dict(self) -> dict:
        return self._d

    def tagged_statements(self) -> list[str]:
        return list(iter_tagged_strings(self._d))


class RFDrugCatalog:
    """Loads and indexes one METACOD-RF batch JSON. Read-only after init."""

    def __init__(self, batch_path: Path | str):
        self.path = Path(batch_path)
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self.meta: dict = data.get("_meta", {})
        self._by_id: dict[str, RFDrug] = {}
        self._by_inn: dict[str, RFDrug] = {}
        for rec in data.get("drugs", []):
            drug = RFDrug(rec)
            self._by_id[drug.drug_id] = drug
            self._by_inn[drug.name_inn.lower()] = drug

    def get(self, drug_id: str) -> Optional[RFDrug]:
        return self._by_id.get(drug_id)

    def by_inn(self, name_inn: str) -> Optional[RFDrug]:
        return self._by_inn.get(name_inn.lower())

    def all_ids(self) -> set[str]:
        return set(self._by_id.keys())

    def __iter__(self) -> Iterator[RFDrug]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, drug_id: str) -> bool:
        return drug_id in self._by_id

    @property
    def ready_for_clinical_use(self) -> bool:
        return bool(self.meta.get("ready_for_clinical_use", False))
