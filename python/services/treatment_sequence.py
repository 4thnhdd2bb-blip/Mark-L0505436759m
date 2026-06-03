"""
METACOD treatment-sequence ordering — orders physician findings and lab plan
by the TCM treatment sequence (wind → damp → cold → dry → heat).

Inputs:
  - The PharmacistAssessment dict
  - The METACODSynthesis from metacod_bridge

Output:
  - The same assessment dict with `interactions` reordered, plus a new
    `treatment_sequence_metadata` block describing the ordering choices.

This is purely a presentational reordering — the underlying clinical content
is not changed. The aim is that when a physician reads the assessment, the
most-priority-by-TCM findings appear first, helping align with Mark's
framework's ordering principles.

Special cases:
  - Collecting Tubules Syndrome: if any fired rule has
    collecting_tubules_priority=true, those findings move to position 0,
    regardless of energy axis.
  - Rules without an energy mapping fall to the END of the sorted list
    (deterministic, no silent drop).
  - Stable sort within the same priority bucket — preserves original order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from services.metacod_bridge import (
    METACODSynthesis,
    RuleEnergyMappingCatalog,
    TREATMENT_PRIORITY,
    TREATMENT_SEQUENCE,
)


@dataclass
class OrderingTrace:
    """Per-finding ordering metadata for audit / debugging."""
    rule_id: str
    original_index: int
    final_index: int
    dominant_energy: Optional[str]
    treatment_priority_order: int
    collecting_tubules_priority: bool


def reorder_by_treatment_sequence(
    assessment: dict,
    catalog: RuleEnergyMappingCatalog,
) -> dict:
    """Return a *new* assessment dict with `interactions` reordered.
    
    Original assessment is not mutated. The reordered dict has an added field
    `treatment_sequence_metadata` describing the ordering decisions.
    
    Ordering rule:
      1. Collecting-Tubules-priority findings first (rare for drug-interaction rules)
      2. Then, by treatment_priority_order from the catalog (1=wind ... 5=heat)
      3. Stable within bucket — preserves original relative order
      4. Findings whose rule_id has no catalog entry → bottom, original relative order
    """
    interactions = list(assessment.get("interactions") or [])
    if not interactions:
        # Nothing to reorder
        out = dict(assessment)
        out["treatment_sequence_metadata"] = {
            "ordering_applied": False,
            "reason": "no_interactions",
            "trace": [],
        }
        return out
    
    indexed = list(enumerate(interactions))  # [(orig_idx, finding), ...]
    
    def sort_key(item: tuple[int, dict]) -> tuple[int, int, int]:
        orig_idx, finding = item
        rule_id = finding.get("rule_id") or ""
        mapping = catalog.get(rule_id)
        
        if mapping is None:
            # No mapping → bottom bucket, preserve original order
            return (2, 99, orig_idx)
        
        if mapping.collecting_tubules_priority:
            # Top bucket — always position 0
            return (0, mapping.treatment_priority_order, orig_idx)
        
        # Normal bucket — by treatment priority, then original order for stability
        return (1, mapping.treatment_priority_order, orig_idx)
    
    sorted_indexed = sorted(indexed, key=sort_key)
    new_interactions = [f for _, f in sorted_indexed]
    
    # Build trace
    trace: list[OrderingTrace] = []
    for new_idx, (orig_idx, finding) in enumerate(sorted_indexed):
        rule_id = finding.get("rule_id") or "unknown"
        mapping = catalog.get(rule_id)
        dominant_energy = None
        if mapping and mapping.energy_contributions:
            # Pick the highest-magnitude energy axis as the "dominant" for this finding
            top = max(mapping.energy_contributions, key=lambda c: c.get("magnitude", 0))
            dominant_energy = top.get("axis")
        trace.append(OrderingTrace(
            rule_id=rule_id,
            original_index=orig_idx,
            final_index=new_idx,
            dominant_energy=dominant_energy,
            treatment_priority_order=mapping.treatment_priority_order if mapping else 99,
            collecting_tubules_priority=mapping.collecting_tubules_priority if mapping else False,
        ))
    
    out = dict(assessment)
    out["interactions"] = new_interactions
    out["treatment_sequence_metadata"] = {
        "ordering_applied": True,
        "treatment_sequence": list(TREATMENT_SEQUENCE),
        "collecting_tubules_active": any(t.collecting_tubules_priority for t in trace),
        "trace": [
            {
                "rule_id": t.rule_id,
                "original_index": t.original_index,
                "final_index": t.final_index,
                "dominant_energy": t.dominant_energy,
                "treatment_priority_order": t.treatment_priority_order,
                "collecting_tubules_priority": t.collecting_tubules_priority,
            }
            for t in trace
        ],
    }
    return out


def reorder_lab_plan_by_energy(
    finding: dict,
    energy_axis: Optional[str],
) -> dict:
    """Within a single finding, reorder lab_plan items by the finding's dominant
    energy axis (no-op for now — labs don't have inherent TCM axis, but the hook
    is here for future expansion when individual labs are mapped).
    """
    # Hook for future per-lab energy mapping. For now, just return unchanged.
    return finding


def explain_ordering(metadata: dict, locale: str = "ru") -> list[str]:
    """Return human-readable explanation lines for the ordering decisions,
    one per finding. Useful for hidden_admin display.
    
    locale='ru' returns Russian, 'en' returns English. Other locales fall back to English.
    """
    if not metadata or not metadata.get("ordering_applied"):
        return []
    
    lines: list[str] = []
    
    if locale == "ru":
        for t in metadata.get("trace", []):
            ct = " (Collecting Tubules — приоритет 0)" if t["collecting_tubules_priority"] else ""
            energy = t.get("dominant_energy") or "—"
            lines.append(
                f"#{t['final_index'] + 1} {t['rule_id']}: "
                f"energy={energy}, treatment_priority={t['treatment_priority_order']}{ct}"
            )
    else:
        for t in metadata.get("trace", []):
            ct = " (Collecting Tubules — priority 0)" if t["collecting_tubules_priority"] else ""
            energy = t.get("dominant_energy") or "—"
            lines.append(
                f"#{t['final_index'] + 1} {t['rule_id']}: "
                f"energy={energy}, treatment_priority={t['treatment_priority_order']}{ct}"
            )
    return lines
