"""
METACOD bridge — adapter from GLP-1 PharmacistAssessment to METACOD core synthesis.

Maps each fired interaction's rule_id through rule_energy_mapping.json to
contributions on the five TCM energy axes (cold, damp, dry, heat, wind) and
six quantity axes (excess, deficiency, stagnation, collapse, fluid_retention,
overloss). Aggregates across all fired rules per visit. Determines dominant
energy and quantity, then maps to phase_route via the fixed mapping.

Produces the METACOD three-layer output:
  - patient_view   : safe generic guidance, NO proprietary terminology
  - physician_view : GLP-1 clinical findings as-is (already EBM-language)
  - hidden_admin   : full energy/quantity/phase synthesis + GNM correlation,
                     never surfaced to patient or physician

Architecture note (adapter-first):
  This module does NOT touch the existing GLP-1 v3 codebase or the METACOD v3
  backend. It's a pure transformation layer that the METACOD synthesis engine
  can call after running the GLP-1 PharmacistAgent. Olek can later adapt this
  into a tighter integration with the existing METACOD Visit / Plan / Synthesis
  Pydantic models — the contract here is plain dicts.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ============================================================================
# Constants (mirror Mark's METACOD framework)
# ============================================================================

ENERGY_AXES = ("cold", "damp", "dry", "heat", "wind")
QUANTITY_AXES = ("excess", "deficiency", "stagnation", "collapse", "fluid_retention", "overloss")

# Fixed energy → phase route mapping (per Mark's framework)
ENERGY_TO_PHASE: dict[str, str] = {
    "cold": "CA",
    "damp": "PCL-A",
    "wind": "epicrisis",
    "dry": "PCL-B",
    "heat": "Normotonia",  # canon ch.4.2: Heat = Normotonia (confirmed by Mark 2026-06-03)
}

# Treatment sequence — wind first, then damp, cold, dry, heat
TREATMENT_SEQUENCE: tuple[str, ...] = ("wind", "damp", "cold", "dry", "heat")
TREATMENT_PRIORITY: dict[str, int] = {axis: i + 1 for i, axis in enumerate(TREATMENT_SEQUENCE)}

# Magnitude bounds
MAGNITUDE_MIN = 1
MAGNITUDE_MAX = 3


# ============================================================================
# Loaded mapping
# ============================================================================

@dataclass
class RuleMapping:
    rule_id: str
    energy_contributions: list[dict]      # [{axis: str, magnitude: int}, ...]
    quantity_contributions: list[dict]    # [{axis: str, magnitude: int}, ...]
    phase_route_hint: str
    collecting_tubules_priority: bool
    treatment_priority_order: int
    rationale_ru: str


class RuleEnergyMappingCatalog:
    """Loads and indexes rule_energy_mapping.json. Read-only after init."""
    
    def __init__(self, mapping_path: Path | str):
        self.path = Path(mapping_path)
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self.meta = data.get("_meta", {})
        self._index: dict[str, RuleMapping] = {}
        for entry in data.get("mappings", []):
            rm = RuleMapping(
                rule_id=entry["rule_id"],
                energy_contributions=entry.get("energy_contributions", []),
                quantity_contributions=entry.get("quantity_contributions", []),
                phase_route_hint=entry.get("phase_route_hint", ""),
                collecting_tubules_priority=entry.get("collecting_tubules_priority", False),
                treatment_priority_order=entry.get("treatment_priority_order", 99),
                rationale_ru=entry.get("rationale_ru", ""),
            )
            self._index[rm.rule_id] = rm
    
    def get(self, rule_id: str) -> Optional[RuleMapping]:
        return self._index.get(rule_id)
    
    def __contains__(self, rule_id: str) -> bool:
        return rule_id in self._index
    
    def __len__(self) -> int:
        return len(self._index)
    
    def all_rule_ids(self) -> set[str]:
        return set(self._index.keys())


# ============================================================================
# Synthesis result
# ============================================================================

@dataclass
class METACODSynthesis:
    """Output of the bridge — feeds into METACOD core synthesis engine."""
    
    # Aggregated TCM scores
    energy_scores: dict[str, int] = field(default_factory=lambda: {axis: 0 for axis in ENERGY_AXES})
    quantity_scores: dict[str, int] = field(default_factory=lambda: {axis: 0 for axis in QUANTITY_AXES})
    
    # Dominant patterns
    dominant_energy: Optional[str] = None
    dominant_quantity: Optional[str] = None
    phase_route: Optional[str] = None
    
    # Treatment ordering — energies in order they should be treated
    treatment_order: list[str] = field(default_factory=list)
    
    # Collecting Tubules priority flag
    collecting_tubules_active: bool = False
    
    # Per-rule contribution trace (for admin layer / debugging)
    contributions_trace: list[dict] = field(default_factory=list)
    
    # Source counts
    rules_with_mapping: int = 0
    rules_without_mapping: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "energy_scores": dict(self.energy_scores),
            "quantity_scores": dict(self.quantity_scores),
            "dominant_energy": self.dominant_energy,
            "dominant_quantity": self.dominant_quantity,
            "phase_route": self.phase_route,
            "treatment_order": list(self.treatment_order),
            "collecting_tubules_active": self.collecting_tubules_active,
            "rules_with_mapping": self.rules_with_mapping,
            "rules_without_mapping": list(self.rules_without_mapping),
            "contributions_trace": list(self.contributions_trace),
        }


# ============================================================================
# Bridge — main entry
# ============================================================================

class METACODBridge:
    """Adapter from PharmacistAssessment → METACODSynthesis + three-layer output."""
    
    def __init__(self, catalog: RuleEnergyMappingCatalog):
        self.catalog = catalog
    
    def synthesize(self, assessment: dict) -> METACODSynthesis:
        """Compute METACODSynthesis from a PharmacistAssessment dict.
        
        Args:
          assessment: PharmacistAssessment.model_dump() output
        
        Returns:
          METACODSynthesis with aggregated scores, dominant patterns, phase route,
          treatment order, and per-rule trace.
        """
        synth = METACODSynthesis()
        
        interactions = assessment.get("interactions", []) or []
        # Deduplicate by rule_id — same rule can fire on multiple meds
        seen_rules: set[str] = set()
        
        for finding in interactions:
            rule_id = finding.get("rule_id")
            if not rule_id or rule_id in seen_rules:
                continue
            seen_rules.add(rule_id)
            
            mapping = self.catalog.get(rule_id)
            if mapping is None:
                synth.rules_without_mapping.append(rule_id)
                continue
            
            synth.rules_with_mapping += 1
            
            # Apply energy contributions
            for c in mapping.energy_contributions:
                axis = c.get("axis")
                mag = self._clamp_magnitude(c.get("magnitude", 1))
                if axis in synth.energy_scores:
                    synth.energy_scores[axis] += mag
            
            # Apply quantity contributions
            for c in mapping.quantity_contributions:
                axis = c.get("axis")
                mag = self._clamp_magnitude(c.get("magnitude", 1))
                if axis in synth.quantity_scores:
                    synth.quantity_scores[axis] += mag
            
            # Collecting Tubules priority
            if mapping.collecting_tubules_priority:
                synth.collecting_tubules_active = True
            
            # Trace entry
            synth.contributions_trace.append({
                "rule_id": rule_id,
                "rule_name": finding.get("rule_name", rule_id),
                "severity": finding.get("severity"),
                "energy_contributions": [dict(c) for c in mapping.energy_contributions],
                "quantity_contributions": [dict(c) for c in mapping.quantity_contributions],
                "phase_route_hint": mapping.phase_route_hint,
                "treatment_priority_order": mapping.treatment_priority_order,
                "rationale_ru": mapping.rationale_ru,
            })
        
        # Determine dominants and phase route
        synth.dominant_energy = self._argmax_or_none(synth.energy_scores)
        synth.dominant_quantity = self._argmax_or_none(synth.quantity_scores)
        if synth.dominant_energy:
            synth.phase_route = ENERGY_TO_PHASE.get(synth.dominant_energy)
        
        # Treatment order: only include axes with non-zero score, sorted by global treatment sequence
        synth.treatment_order = [
            axis for axis in TREATMENT_SEQUENCE
            if synth.energy_scores.get(axis, 0) > 0
        ]
        
        return synth
    
    def build_three_layer_output(
        self,
        assessment: dict,
        synthesis: METACODSynthesis,
        locale: str = "ru",
    ) -> dict[str, Any]:
        """Produce the METACOD three-layer output structure.
        
        Layer 1 — patient_view  : safe, no proprietary terms; pull only the
                                  generic GI/safety advice and triage from assessment
        Layer 2 — physician_view: GLP-1 EBM findings as-is — already physician-safe
        Layer 3 — hidden_admin  : full TCM synthesis + per-rule trace; NEVER shown
                                  to patient or physician under any condition
        
        The `_layer_guarantees` field carries machine-readable assertions for
        downstream pipelines / UI guardrails.
        """
        # ----- Patient view: aggressively sanitized -----
        triage = assessment.get("triage_color", "green")
        # Translate triage to plain language per locale (METACOD-style — no "yellow/red"
        # technical terms either; just guidance). We use the same key the agent emitted.
        patient_view: dict[str, Any] = {
            "triage_color": triage,
            "triage_summary_i18n_key": assessment.get("triage_summary_i18n_key"),
            "glp1_decision": (assessment.get("forecast") or {}).get("glp1_dosing", {}).get("decision"),
            "glp1_decision_i18n_key": (assessment.get("forecast") or {}).get("glp1_dosing", {}).get("i18n_key"),
            # Patient-facing action keys ONLY — physician_actions are excluded
            "patient_actions_i18n_keys": [
                a.get("i18n_key")
                for f in (assessment.get("interactions") or [])
                for a in (f.get("patient_actions") or [])
                if a.get("i18n_key")
            ],
            "locale": locale,
        }
        
        # ----- Physician view: GLP-1 clinical layer as-is -----
        physician_view: dict[str, Any] = {
            "triage_color": triage,
            "triage_summary_i18n_key": assessment.get("triage_summary_i18n_key"),
            "interactions": [
                {
                    "rule_id": f.get("rule_id"),
                    "rule_name": f.get("rule_name"),
                    "medication_name": f.get("medication_name"),
                    "severity": f.get("severity"),
                    "evidence_grade": f.get("evidence_grade"),
                    "physician_actions": f.get("physician_actions", []),
                    "patient_actions": f.get("patient_actions", []),
                    "lab_plan": f.get("lab_plan", []),
                    "sources": f.get("sources", []),
                    # admin_trace is DELIBERATELY excluded — that's hidden_admin only
                }
                for f in (assessment.get("interactions") or [])
            ],
            "forecast": assessment.get("forecast"),
            "dose_adjustments": assessment.get("dose_adjustments", []),
            "rule_pack_version": assessment.get("rule_pack_version"),
            "drug_db_version": assessment.get("drug_db_version"),
            "agent_version": assessment.get("agent_version"),
        }
        
        # ----- Hidden admin: full synthesis + per-rule trace + admin_trace -----
        hidden_admin: dict[str, Any] = {
            "tcm_synthesis": synthesis.to_dict(),
            "per_rule_admin_traces": [
                f.get("admin_trace") for f in (assessment.get("interactions") or [])
                if f.get("admin_trace")
            ],
            "projected_labs": assessment.get("projected_labs", []),
            "interaction_matrix": assessment.get("interaction_matrix", []),
            "treatment_sequence_recommended": synthesis.treatment_order,
            "collecting_tubules_priority_active": synthesis.collecting_tubules_active,
        }
        
        return {
            "patient_view": patient_view,
            "physician_view": physician_view,
            "hidden_admin": hidden_admin,
            "_layer_guarantees": {
                "patient_view_excludes": ["admin_trace", "mechanism", "tcm_synthesis",
                                          "energy_scores", "phase_route", "rationale_ru",
                                          "physician_actions"],
                "physician_view_excludes": ["admin_trace", "mechanism", "tcm_synthesis",
                                            "energy_scores", "phase_route", "rationale_ru"],
                "hidden_admin_only": ["tcm_synthesis", "per_rule_admin_traces",
                                       "interaction_matrix", "projected_labs"],
            },
        }
    
    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------
    
    @staticmethod
    def _clamp_magnitude(m) -> int:
        try:
            v = int(m)
        except (TypeError, ValueError):
            return MAGNITUDE_MIN
        return max(MAGNITUDE_MIN, min(MAGNITUDE_MAX, v))
    
    @staticmethod
    def _argmax_or_none(scores: dict[str, int]) -> Optional[str]:
        """Return axis with highest score; None if all zero. Ties broken by treatment sequence priority (wind first)."""
        non_zero = {k: v for k, v in scores.items() if v > 0}
        if not non_zero:
            return None
        max_score = max(non_zero.values())
        candidates = [k for k, v in non_zero.items() if v == max_score]
        if len(candidates) == 1:
            return candidates[0]
        # Tie-break by treatment sequence priority — earlier in sequence wins (wind > damp > cold > dry > heat)
        return min(candidates, key=lambda axis: TREATMENT_PRIORITY.get(axis, 99))
