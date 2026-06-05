"""METACOD GLP-1 — Active learning capture and analytics.

Two responsibilities:

  1. **Capture**: at sign-off, decompose the diff between the agent's original
     assessment and the physician-amended payload into a list of typed
     amendment records. Persisted to learning_amendments.

  2. **Analytics**: aggregate captured amendments to surface patterns
     (which rules are most often removed, which severity downgrades are
     common, which physicians amend most aggressively).

This is purely capture + simple aggregation — no ML, no rule-tuning logic
yet. It's the substrate that rule tuning can later sit on top of.

Design notes:
  - Pure-function `compute_amendments()` separated from DB-touching
    `capture_amendment()` so the diff logic is unit-testable in isolation.
  - Idempotent: re-running capture on the same (visit_id, sign_off_id) pair
    is a no-op thanks to the UNIQUE constraint on the table.
  - Amendments are decomposed (one row per change type per rule), not stored
    as a single blob. This is what makes the analytics queries cheap.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


# ============================================================================
# Amendment data class — what compute_amendments() emits
# ============================================================================

@dataclass(frozen=True)
class Amendment:
    """A single typed change. `rule_id` is None for triage / GLP-1 decision changes."""
    amendment_type: str
    rule_id: Optional[str]
    original_value: Optional[Any]
    amended_value: Optional[Any]

    def to_db_kwargs(self, visit_id: str, sign_off_id: int, physician_id: str,
                     physician_notes: Optional[str],
                     rule_pack_version: Optional[str] = None,
                     drug_db_version: Optional[str] = None,
                     agent_version: Optional[str] = None) -> dict:
        return {
            "visit_id": visit_id,
            "sign_off_id": sign_off_id,
            "rule_id": self.rule_id,
            "amendment_type": self.amendment_type,
            "original_value_json": json.dumps(self.original_value, sort_keys=True) if self.original_value is not None else None,
            "amended_value_json": json.dumps(self.amended_value, sort_keys=True) if self.amended_value is not None else None,
            "physician_id": physician_id,
            "physician_notes": physician_notes,
            "rule_pack_version": rule_pack_version,
            "drug_db_version": drug_db_version,
            "agent_version": agent_version,
        }


# Valid amendment types — used by analytics filters and validation
AMENDMENT_TYPES = frozenset({
    "triage_changed",
    "glp1_decision_changed",
    "rule_removed",
    "rule_added",
    "severity_changed",
    "action_removed",
    "action_added",
    "patient_action_removed",
    "patient_action_added",
    "lab_removed",
    "lab_added",
    "lab_interval_changed",
})


# ============================================================================
# Pure diff computation
# ============================================================================

def compute_amendments(original: dict, amended: dict) -> list[Amendment]:
    """Decompose the difference between two assessment dicts into typed Amendment records.

    Pure function: no DB, no globals, no I/O. Returns an empty list when no
    differences are detected. Resilient to missing/malformed fields — best-effort
    extraction with defensive `.get(...)` access throughout.

    Algorithm:
      1. Top-level: triage_color, forecast.glp1_dosing.decision
      2. interactions[]: set diff on rule_id keys → removed / added
      3. For surviving rule_ids: severity, physician_actions[], patient_actions[],
         lab_plan[] diff on canonical keys (i18n_key for actions, test for labs)
    """
    out: list[Amendment] = []

    # ----- Top-level: triage colour -----
    o_triage = original.get("triage_color")
    a_triage = amended.get("triage_color")
    if o_triage != a_triage:
        out.append(Amendment(
            amendment_type="triage_changed",
            rule_id=None,
            original_value={"triage_color": o_triage, "summary": original.get("triage_summary_i18n_text") or original.get("triage_summary_i18n_key")},
            amended_value={"triage_color": a_triage, "summary": amended.get("triage_summary_i18n_text") or amended.get("triage_summary_i18n_key")},
        ))

    # ----- Top-level: GLP-1 decision -----
    o_glp1 = (original.get("forecast") or {}).get("glp1_dosing") or {}
    a_glp1 = (amended.get("forecast") or {}).get("glp1_dosing") or {}
    if o_glp1.get("decision") != a_glp1.get("decision"):
        out.append(Amendment(
            amendment_type="glp1_decision_changed",
            rule_id=None,
            original_value={"decision": o_glp1.get("decision"), "rationale": o_glp1.get("i18n_text") or o_glp1.get("i18n_key")},
            amended_value={"decision": a_glp1.get("decision"), "rationale": a_glp1.get("i18n_text") or a_glp1.get("i18n_key")},
        ))

    # ----- Interactions: rule-level diff -----
    o_rules = {f.get("rule_id"): f for f in (original.get("interactions") or []) if f.get("rule_id")}
    a_rules = {f.get("rule_id"): f for f in (amended.get("interactions") or []) if f.get("rule_id")}

    for rid in sorted(o_rules.keys() - a_rules.keys()):
        out.append(Amendment(
            amendment_type="rule_removed",
            rule_id=rid,
            original_value=_compact_finding(o_rules[rid]),
            amended_value=None,
        ))

    for rid in sorted(a_rules.keys() - o_rules.keys()):
        out.append(Amendment(
            amendment_type="rule_added",
            rule_id=rid,
            original_value=None,
            amended_value=_compact_finding(a_rules[rid]),
        ))

    # ----- For surviving rules: severity, action, lab diffs -----
    for rid in sorted(o_rules.keys() & a_rules.keys()):
        o = o_rules[rid]
        a = a_rules[rid]

        # Severity
        if o.get("severity") != a.get("severity"):
            out.append(Amendment(
                amendment_type="severity_changed",
                rule_id=rid,
                original_value={"severity": o.get("severity")},
                amended_value={"severity": a.get("severity")},
            ))

        # Physician actions
        out.extend(_diff_action_list(rid, o.get("physician_actions") or [], a.get("physician_actions") or [],
                                     removed_type="action_removed", added_type="action_added"))

        # Patient actions
        out.extend(_diff_action_list(rid, o.get("patient_actions") or [], a.get("patient_actions") or [],
                                     removed_type="patient_action_removed", added_type="patient_action_added"))

        # Lab plan — by `test` name; also detect interval change on survivors
        o_labs = {lab.get("test"): lab for lab in (o.get("lab_plan") or []) if lab.get("test")}
        a_labs = {lab.get("test"): lab for lab in (a.get("lab_plan") or []) if lab.get("test")}

        for t in sorted(o_labs.keys() - a_labs.keys()):
            out.append(Amendment(
                amendment_type="lab_removed",
                rule_id=rid,
                original_value=_compact_lab(o_labs[t]),
                amended_value=None,
            ))
        for t in sorted(a_labs.keys() - o_labs.keys()):
            out.append(Amendment(
                amendment_type="lab_added",
                rule_id=rid,
                original_value=None,
                amended_value=_compact_lab(a_labs[t]),
            ))
        for t in sorted(o_labs.keys() & a_labs.keys()):
            o_iw = o_labs[t].get("interval_weeks")
            a_iw = a_labs[t].get("interval_weeks")
            if o_iw != a_iw:
                out.append(Amendment(
                    amendment_type="lab_interval_changed",
                    rule_id=rid,
                    original_value={"test": t, "interval_weeks": o_iw},
                    amended_value={"test": t, "interval_weeks": a_iw},
                ))

    return out


def _diff_action_list(rid: str, original: list[dict], amended: list[dict],
                      removed_type: str, added_type: str) -> list[Amendment]:
    """Diff two lists of actions keyed on i18n_key (canonical action identity)."""
    out: list[Amendment] = []
    o_keys = {a.get("i18n_key"): a for a in original if a.get("i18n_key")}
    a_keys = {a.get("i18n_key"): a for a in amended if a.get("i18n_key")}
    for k in sorted(o_keys.keys() - a_keys.keys()):
        out.append(Amendment(
            amendment_type=removed_type,
            rule_id=rid,
            original_value={"i18n_key": k, "i18n_text": o_keys[k].get("i18n_text"), "evidence_grade": o_keys[k].get("evidence_grade")},
            amended_value=None,
        ))
    for k in sorted(a_keys.keys() - o_keys.keys()):
        out.append(Amendment(
            amendment_type=added_type,
            rule_id=rid,
            original_value=None,
            amended_value={"i18n_key": k, "i18n_text": a_keys[k].get("i18n_text"), "evidence_grade": a_keys[k].get("evidence_grade")},
        ))
    return out


def _compact_finding(finding: dict) -> dict:
    """Compact representation of a finding for storage (drop heavy admin trace and sources)."""
    return {
        "rule_id": finding.get("rule_id"),
        "rule_name": finding.get("rule_name"),
        "medication_name": finding.get("medication_name"),
        "severity": finding.get("severity"),
        "evidence_grade": finding.get("evidence_grade"),
        "physician_actions": [{"i18n_key": a.get("i18n_key")} for a in (finding.get("physician_actions") or [])],
        "patient_actions": [{"i18n_key": a.get("i18n_key")} for a in (finding.get("patient_actions") or [])],
        "lab_plan": [{"test": l.get("test"), "interval_weeks": l.get("interval_weeks")} for l in (finding.get("lab_plan") or [])],
    }


def _compact_lab(lab: dict) -> dict:
    return {"test": lab.get("test"), "interval_weeks": lab.get("interval_weeks"),
            "i18n_key": lab.get("i18n_key")}


# ============================================================================
# DB-touching capture
# ============================================================================

def capture_amendment(
    db_session,
    *,
    visit_id: str,
    sign_off_id: int,
    original_assessment: dict,
    amended_assessment: dict,
    physician_id: str,
    physician_notes: Optional[str] = None,
    rule_pack_version: Optional[str] = None,
    drug_db_version: Optional[str] = None,
    agent_version: Optional[str] = None,
) -> dict:
    """Persist decomposed amendments to learning_amendments table.

    Idempotent: if rows already exist for (visit_id, sign_off_id, rule_id, amendment_type),
    the INSERT is skipped (relies on the UNIQUE constraint defined by the migration).

    Returns a summary dict:
      {
        "amendments_detected": int,
        "amendments_persisted": int,
        "amendments_skipped_duplicate": int,
        "amendment_types": list[str],
      }
    """
    # Lazy import keeps this module importable without SQLAlchemy installed during unit tests
    from database import LearningAmendment  # type: ignore[import]
    from sqlalchemy.exc import IntegrityError

    amendments = compute_amendments(original_assessment, amended_assessment)

    versions = {
        "rule_pack_version": rule_pack_version or original_assessment.get("rule_pack_version"),
        "drug_db_version": drug_db_version or original_assessment.get("drug_db_version"),
        "agent_version": agent_version or original_assessment.get("agent_version"),
    }

    persisted = 0
    skipped = 0
    types_present: set[str] = set()

    for amd in amendments:
        types_present.add(amd.amendment_type)
        kwargs = amd.to_db_kwargs(
            visit_id=visit_id,
            sign_off_id=sign_off_id,
            physician_id=physician_id,
            physician_notes=physician_notes,
            **versions,
        )
        row = LearningAmendment(**kwargs)
        db_session.add(row)
        try:
            db_session.flush()
            persisted += 1
        except IntegrityError:
            db_session.rollback()
            skipped += 1
            continue

    if persisted:
        db_session.commit()

    return {
        "amendments_detected": len(amendments),
        "amendments_persisted": persisted,
        "amendments_skipped_duplicate": skipped,
        "amendment_types": sorted(types_present),
    }


# ============================================================================
# Analytics
# ============================================================================

def aggregate_patterns(
    db_session,
    *,
    rule_id: Optional[str] = None,
    amendment_type: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    top_n: int = 10,
) -> dict:
    """Aggregate amendment patterns. Returns top-N counts grouped by (rule_id, amendment_type)
    plus top physicians by amendment volume on the filter.

    Use cases:
      - "Which Grade A rules are most often removed?" → amendment_type='rule_removed'
      - "Did physicians frequently amend the new INSULIN_SU_GLP1_HYPOGLYCEMIA rule?" → rule_id=...
      - "Time trend since rule_pack v2 release" → since=v2_release_date
    """
    from sqlalchemy import func
    from database import LearningAmendment  # type: ignore[import]

    def _apply_filters(query):
        if rule_id:
            query = query.filter(LearningAmendment.rule_id == rule_id)
        if amendment_type:
            if amendment_type not in AMENDMENT_TYPES:
                raise ValueError(f"unknown amendment_type: {amendment_type}")
            query = query.filter(LearningAmendment.amendment_type == amendment_type)
        if since:
            query = query.filter(LearningAmendment.created_at >= since)
        if until:
            query = query.filter(LearningAmendment.created_at <= until)
        return query

    # Validate amendment_type early (before any query) so error path is consistent
    if amendment_type and amendment_type not in AMENDMENT_TYPES:
        raise ValueError(f"unknown amendment_type: {amendment_type}")

    # Top-N by (rule_id, amendment_type)
    by_rule_type_q = db_session.query(
        LearningAmendment.rule_id,
        LearningAmendment.amendment_type,
        func.count(LearningAmendment.id).label("count"),
    )
    by_rule_type_q = _apply_filters(by_rule_type_q)
    by_rule_type = by_rule_type_q.group_by(LearningAmendment.rule_id, LearningAmendment.amendment_type) \
                                 .order_by(func.count(LearningAmendment.id).desc()) \
                                 .limit(top_n).all()

    # Top physicians on the same filter
    by_phys_q = db_session.query(
        LearningAmendment.physician_id,
        func.count(LearningAmendment.id).label("count"),
    )
    by_phys_q = _apply_filters(by_phys_q)
    top_physicians = by_phys_q.group_by(LearningAmendment.physician_id) \
                              .order_by(func.count(LearningAmendment.id).desc()) \
                              .limit(top_n).all()

    # Total amendment count under the same filter (separate query so it's not skewed by group_by)
    total_q = db_session.query(func.count(LearningAmendment.id))
    total_q = _apply_filters(total_q)
    total = total_q.scalar()

    return {
        "filter": {
            "rule_id": rule_id,
            "amendment_type": amendment_type,
            "since": since.isoformat() if since else None,
            "until": until.isoformat() if until else None,
        },
        "total_amendments": int(total or 0),
        "top_by_rule_type": [
            {"rule_id": r, "amendment_type": t, "count": int(c)}
            for r, t, c in by_rule_type
        ],
        "top_physicians": [
            {"physician_id": p, "count": int(c)} for p, c in top_physicians
        ],
    }
