"""
METACOD Patient-Facing Filter — defense-in-depth content guard.

Mandated identically across every METACOD transfer document:
  - v6.0 CONCORD-50  Memory Rule #10 (Patient-Facing Filter, HARD REGULATION)
  - v1.8 Transition   §6.5 (Patient-facing language rule)
  - Patient Chat Starter v4.0 (forbidden-terms list)

Purpose: a *detector* (not an auto-rewriter) that scans any text or nested
structure destined for a patient and flags proprietary / internal / unvalidated
METACOD terminology that must NEVER reach a patient-facing document:
  M-codes, anabolic/catabolic shift language, Revici compounded names,
  Hamer/GNM terms, Park/Wu-Xing/energy-axis terms, CLOSED tables
  (Phase-Energy Matrix, Color Therapy, Su Jok), and internal engine IDs.

This complements the structural three-layer guard in metacod_bridge.py: the
bridge guarantees structurally that proprietary *fields* never enter
patient_view; this filter additionally scans resolved *text* for leaked terms.

The denylist contains only term NAMES to block — never any CLOSED values,
doses, formulas, or matrices. It is engine-internal and safe to version.

It is deliberately conservative (over-flags rather than under-flags): a false
positive costs a physician one glance; a false negative leaks proprietary or
unvalidated terminology to a patient. Detection only — never silently rewrites
clinical text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


# ============================================================================
# Denylist — derived verbatim from Memory Rule #10 / §6.5 forbidden lists
# ============================================================================
# Each entry: (category, compiled regex). Patterns are case-insensitive and
# Unicode-aware (cover both Latin and Cyrillic spellings where the docs list
# both). Grouped by the categories the source documents use.

_RAW_PATTERNS: list[tuple[str, str]] = [
    # --- Membrane codes (M-0 / M-A1-3 / M-S / M-D1-3) and "membrane state" ---
    ("m_code", r"\bM-(?:0|A[1-3]?|D[1-3]?|S)\b"),
    ("m_code", r"\bM-state\b"),
    ("m_code", r"\bмембранн\w*\s+(?:код|статус|состояни)\w*"),
    ("m_code", r"\bmembrane\s+(?:code|state)\b"),

    # --- Anabolic / catabolic "shift" membrane language ---
    ("anabolic_catabolic", r"\b(?:ана|ката)болическ\w*\s+сдвиг\w*"),
    ("anabolic_catabolic", r"\b(?:ana|cata)bolic\s+shift\b"),

    # --- Revici / compounded proprietary names ---
    ("revici", r"\brevici\b"),
    ("revici", r"\bревичи\b"),
    ("revici", r"\bcompounded\b"),
    ("revici", r"\bTSel\b"),
    ("revici", r"\bSecol\b"),
    ("revici", r"\bheptano\w*"),      # heptanoic / heptanol
    ("revici", r"\bгептано\w*"),
    ("revici", r"\bdiselenide\b"),
    ("revici", r"\bmodified\s+salt\b"),
    ("revici", r"\bмодифицированн\w*\s+сол\w*"),

    # --- Hamer / GNM phase terms ---
    ("hamer", r"\bhamer\b"),
    ("hamer", r"\bхамер\w*"),
    ("hamer", r"\bDHS\b"),
    ("hamer", r"\bGNM\b"),
    ("hamer", r"\bSBS\b"),
    ("hamer", r"\bepicris\w*"),
    ("hamer", r"\bэпикриз\w*"),
    ("hamer", r"\bSandlauf\b"),
    ("hamer", r"\bCA-PCL\b"),
    ("hamer", r"\bPCL-[AB]\b"),
    ("hamer", r"\b(?:biological|биологическ\w*)\s+(?:conflict|конфликт\w*)"),

    # --- Park / Wu Xing / energy-axis / JCZ terms ---
    ("park_energy", r"\bpark\b"),
    ("park_energy", r"\bwu\s*xing\b"),
    ("park_energy", r"\bу-?син\b"),
    ("park_energy", r"\bjun[-\s]?chen[-\s]?zuo[-\s]?shi\b"),
    ("park_energy", r"\bJCZ\b"),
    ("park_energy", r"\benergy\s+(?:ax[ie]s|vector)\b"),
    ("park_energy", r"\bэнергетическ\w*\s+(?:ос[ьи]|вектор\w*)"),
    ("park_energy", r"\bKO[-\s]?(?:cycle|цикл\w*)"),
    # Yang/Yin only as the framework polarity markers (whole-token / hyphenated
    # constitution labels) to limit false positives on unrelated words/names.
    ("park_energy", r"\byang\b"),
    ("park_energy", r"\byin\b"),
    ("park_energy", r"\bЯн-\w+"),
    ("park_energy", r"\bИнь-\w+"),

    # --- CLOSED tables / tools ---
    ("closed_table", r"\bphase[-\s]?energy\s+matrix\b"),
    ("closed_table", r"\bcolor\s+therapy\b"),
    ("closed_table", r"\bцветотерап\w*"),
    ("closed_table", r"\bsu\s*jok\b"),
    ("closed_table", r"\bсу[-\s]?джок\b"),
    ("closed_table", r"\bAIRE\b"),
    ("closed_table", r"\bKCTS\b"),
    ("closed_table", r"\bDCM\b"),
    ("closed_table", r"\bDPM\b"),

    # --- Internal engine identifiers (rule/drug/disease traceability codes) ---
    ("internal_id", r"\bDRG-COMP-\d+\b"),
    ("internal_id", r"\b(?:DRG|DIS|LAB|SYM|HS|AUD)-[0-9A-Za-z]+\b"),
]

_COMPILED: list[tuple[str, re.Pattern[str]]] = [
    (cat, re.compile(pat, re.IGNORECASE | re.UNICODE)) for cat, pat in _RAW_PATTERNS
]

# Categories the source documents enumerate — used by coverage meta-tests.
FORBIDDEN_CATEGORIES: frozenset[str] = frozenset(
    cat for cat, _ in _RAW_PATTERNS
)


# ============================================================================
# Result types
# ============================================================================

@dataclass(frozen=True)
class Violation:
    """A single forbidden-term hit."""
    category: str
    term: str          # the matched substring
    start: int         # char offset within the scanned string
    end: int
    path: str = ""     # JSON-ish path when scanning a structure

    def __str__(self) -> str:
        loc = f" at {self.path}" if self.path else ""
        return f"[{self.category}] {self.term!r}{loc}"


class PatientFacingLeakError(AssertionError):
    """Raised when patient-destined content contains forbidden terminology."""

    def __init__(self, violations: list[Violation]):
        self.violations = violations
        sample = "; ".join(str(v) for v in violations[:8])
        more = "" if len(violations) <= 8 else f" (+{len(violations) - 8} more)"
        super().__init__(
            f"Patient-facing content leaked {len(violations)} forbidden "
            f"term(s): {sample}{more}"
        )


# ============================================================================
# Core API
# ============================================================================

def scan_text(text: str, path: str = "") -> list[Violation]:
    """Return all forbidden-term hits in a single string (may be empty)."""
    if not text:
        return []
    out: list[Violation] = []
    for category, rx in _COMPILED:
        for m in rx.finditer(text):
            out.append(
                Violation(
                    category=category,
                    term=m.group(0),
                    start=m.start(),
                    end=m.end(),
                    path=path,
                )
            )
    return out


def scan_structure(obj: Any, path: str = "") -> list[Violation]:
    """Recursively scan a nested dict/list/str structure (e.g. a patient_view).

    Dict KEYS are intentionally NOT scanned — i18n keys like
    ``patient.lt4_take_30min_before`` are identifiers, not patient-visible text.
    Only string VALUES are scanned.
    """
    out: list[Violation] = []
    if isinstance(obj, str):
        out.extend(scan_text(obj, path or "<root>"))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(scan_structure(v, f"{path}.{k}" if path else str(k)))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            out.extend(scan_structure(v, f"{path}[{i}]"))
    # numbers / bools / None carry no text
    return out


def is_patient_safe(obj: Any) -> bool:
    """True iff no forbidden terminology is present anywhere in `obj`."""
    return not scan_structure(obj)


def assert_patient_safe(obj: Any) -> None:
    """Raise PatientFacingLeakError if any forbidden terminology is present.

    Intended as a hard gate immediately before emitting a patient-facing
    document / API response.
    """
    violations = scan_structure(obj)
    if violations:
        raise PatientFacingLeakError(violations)


def redact(text: str, placeholder: str = "[—]") -> str:
    """Best-effort masking of forbidden terms in a string.

    NOTE: redaction is a last-resort safety net, not a substitute for authoring
    clean patient text. It never alters clinical meaning beyond removing the
    flagged token, and is deliberately not applied automatically to engine
    output — call it explicitly only where masking is acceptable.
    """
    spans = sorted(
        ((v.start, v.end) for v in scan_text(text)),
        key=lambda s: s[0],
        reverse=True,
    )
    out = text
    for start, end in spans:
        out = out[:start] + placeholder + out[end:]
    return out


def categories_present(obj: Any) -> set[str]:
    """Set of forbidden categories that appear in `obj` (for diagnostics)."""
    return {v.category for v in scan_structure(obj)}


def iter_terms(violations: Iterable[Violation]) -> list[str]:
    """Convenience: distinct matched terms, preserving first-seen order."""
    seen: dict[str, None] = {}
    for v in violations:
        seen.setdefault(v.term, None)
    return list(seen.keys())
