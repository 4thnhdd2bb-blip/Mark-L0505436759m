"""
Unit tests for the METACOD Patient-Facing Filter (services/patient_facing_filter).

The filter is mandated identically in v6.0 Memory Rule #10, v1.8 §6.5, and the
Patient Chat Starter: proprietary / internal / unvalidated METACOD terminology
must NEVER appear in patient-facing content. These tests pin that contract.
"""

from __future__ import annotations

import pytest

from services.patient_facing_filter import (
    FORBIDDEN_CATEGORIES,
    PatientFacingLeakError,
    Violation,
    assert_patient_safe,
    categories_present,
    is_patient_safe,
    redact,
    scan_structure,
    scan_text,
)

pytestmark = pytest.mark.unit


# ============================================================================
# Forbidden terminology is detected — one representative per category
# ============================================================================

@pytest.mark.parametrize(
    "text,expected_category",
    [
        ("Пациент в состоянии M-A2 по мембране", "m_code"),
        ("membrane state shifted overnight", "m_code"),
        ("выраженный анаболический сдвиг", "anabolic_catabolic"),
        ("this reflects a catabolic shift", "anabolic_catabolic"),
        ("apply the principle of Revici here", "revici"),
        ("start TSel 1cc PO", "revici"),
        ("Heptanoic Acid 50% IM", "revici"),
        ("Modified Salt Agent A 5 g/d", "revici"),
        ("this is a Hamer CA-PCL transition", "hamer"),
        ("epicrisis spike expected", "hamer"),
        ("the biological conflict resolved", "hamer"),
        ("Park constitution is Yin-Fire", "park_energy"),
        ("balance via the KO-cycle", "park_energy"),
        ("Jun-Chen-Zuo-Shi structure", "park_energy"),
        ("see the Phase-Energy Matrix entry", "closed_table"),
        ("apply Color Therapy yellow", "closed_table"),
        ("Su Jok point confirmation", "closed_table"),
        ("traceable to DRG-COMP-101", "internal_id"),
        ("rule DIS-031 fired", "internal_id"),
    ],
)
def test_forbidden_terms_detected(text, expected_category):
    violations = scan_text(text)
    assert violations, f"expected a violation in {text!r}"
    assert expected_category in {v.category for v in violations}, (
        f"{text!r}: expected category {expected_category}, "
        f"got {[v.category for v in violations]}"
    )


def test_every_category_has_at_least_one_pattern():
    # Guards against a category name drifting out of the denylist silently.
    assert FORBIDDEN_CATEGORIES == {
        "m_code", "anabolic_catabolic", "revici", "hamer",
        "park_energy", "closed_table", "internal_id",
    }


# ============================================================================
# Clean / allowed conventional language passes untouched
# ============================================================================

@pytest.mark.parametrize(
    "text",
    [
        "Take levothyroxine 75 mcg on an empty stomach, 30 minutes before breakfast.",
        "Принимайте левотироксин натощак, за 30 минут до еды. Контроль ТТГ через 4 недели.",
        "Omega-3 1.5 g/day, vitamin D, magnesium, glycine at night.",
        "Средиземноморская диета, физическая активность, сон, контроль стресса.",
        "Phase angle on BIA and lipid panel at the next visit.",  # allowed physiologic terms
        "ICD-10 E03.9 hypothyroidism; recheck ferritin before iron.",
    ],
)
def test_allowed_conventional_language_passes(text):
    assert is_patient_safe(text), (
        f"clean text wrongly flagged: {scan_text(text)}"
    )


# ============================================================================
# Structure scanning + path reporting
# ============================================================================

def test_scan_structure_reports_paths():
    payload = {
        "summary": "All clear, continue as advised.",
        "notes": ["Hydrate well", "Pattern is M-D2 catabolic"],
        "nested": {"deep": "uses Color Therapy"},
    }
    violations = scan_structure(payload)
    paths = {v.path for v in violations}
    assert any("notes[1]" in p for p in paths)
    assert any("nested.deep" in p for p in paths)
    cats = {v.category for v in violations}
    assert {"m_code", "closed_table"} <= cats


def test_dict_keys_are_not_scanned():
    # i18n keys are identifiers, not patient-visible text.
    payload = {"patient.epicrisis_marker_key": "Drink fluids and rest."}
    assert is_patient_safe(payload), (
        f"key wrongly scanned: {scan_structure(payload)}"
    )


# ============================================================================
# Hard gate behaviour
# ============================================================================

def test_assert_patient_safe_passes_on_clean():
    assert_patient_safe({"advice": "Rest, hydrate, follow up in two weeks."})


def test_assert_patient_safe_raises_on_leak():
    with pytest.raises(PatientFacingLeakError) as ei:
        assert_patient_safe({"advice": "Your membrane is M-S, start compounded Secol."})
    msg = str(ei.value)
    assert "forbidden" in msg.lower()
    assert ei.value.violations  # carries structured detail


def test_categories_present_helper():
    cats = categories_present("M-A2 with Revici Heptanol per Hamer epicrisis")
    assert {"m_code", "revici", "hamer"} <= cats


# ============================================================================
# redact() best-effort masking
# ============================================================================

def test_redact_masks_terms_but_keeps_clean_text():
    out = redact("Continue levothyroxine; underlying pattern is M-A2 anabolic shift.")
    assert "M-A2" not in out
    assert "anabolic shift" not in out
    assert "levothyroxine" in out  # clinical content preserved
    assert is_patient_safe(out)


# ============================================================================
# Integration with the METACOD bridge patient_view
# ============================================================================

def test_bridge_patient_view_passes_filter(data_dir):
    """The bridge's structurally-sanitised patient_view must also pass the
    content filter (defense in depth: structure + text)."""
    from services.metacod_bridge import (
        METACODBridge,
        RuleEnergyMappingCatalog,
    )

    catalog = RuleEnergyMappingCatalog(data_dir / "rule_energy_mapping.json")
    bridge = METACODBridge(catalog)

    assessment = {
        "triage_color": "amber",
        "triage_summary_i18n_key": "triage.amber",
        "interactions": [
            {
                "rule_id": "LT4_TABLET_PPI",
                "rule_name": "LT4 + PPI",
                "severity": "moderate",
                "patient_actions": [{"i18n_key": "patient.lt4_take_30min_before"}],
                "physician_actions": [{"i18n_key": "action.lt4_check_tsh_4w"}],
                "admin_trace": {"mechanism": "Revici M-A2 Heptanol per Hamer"},
            }
        ],
        "forecast": {"glp1_dosing": {"decision": "continue", "i18n_key": "glp1.continue"}},
    }
    synth = bridge.synthesize(assessment)
    out = bridge.build_three_layer_output(assessment, synth, locale="ru")

    # patient_view carries only i18n KEYS + triage — no forbidden VALUES.
    assert is_patient_safe(out["patient_view"]), (
        f"patient_view leaked: {scan_structure(out['patient_view'])}"
    )
    # And the hidden_admin DID carry the proprietary mechanism (proves the
    # filter would have caught it had it leaked downward).
    assert not is_patient_safe(out["hidden_admin"])


def test_resolved_patient_text_with_leak_is_caught():
    """Simulate a resolved (i18n-substituted) patient payload that wrongly
    includes engine jargon — the gate must catch it before emission."""
    resolved_patient_payload = {
        "triage_text": "Поговорите с врачом о приёме лекарства.",
        "actions_text": [
            "Принимайте таблетку за 30 минут до еды.",
            # BUG injected: admin terminology leaked into patient text
            "Коррекция по мембранному коду M-A2 (Revici).",
        ],
    }
    with pytest.raises(PatientFacingLeakError):
        assert_patient_safe(resolved_patient_payload)
