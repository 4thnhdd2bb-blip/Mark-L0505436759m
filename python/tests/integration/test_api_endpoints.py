"""
METACOD GLP-1 module — integration tests for the FastAPI router.

Uses the `client` fixture from conftest.py which provides a TestClient bound
to an isolated SQLite database with rule_pack + drug_db pre-loaded.

Each test is a real HTTP round-trip — no mocks of the router or the agent.
"""

from __future__ import annotations

import pytest


# ============================================================================
# Helpers
# ============================================================================

def _basic_payload(**overrides) -> dict:
    """Build a minimal valid assess payload."""
    base = {
        "locale": "ru",
        "patient": {
            "patient_id": "P-TEST",
            "age_years": 55,
            "sex": "female",
            "weight_kg": 75.0,
            "glp1_agent": "semaglutide_sc",
            "glp1_weeks_since_start": 12,
            "glp1_weeks_since_last_dose_increase": 8,
            "ppi_or_h2_blocker": True,
            "symptoms": {"nausea_score": 2},
            "labs": {"egfr_ml_min": 85, "tsh_miu_l": 6.0},
            "medications": [
                {"name": "Levothyroxine 75 mcg", "profile_id": "levothyroxine_tablet", "route": "oral"},
            ],
        },
    }
    base.update(overrides)
    return base


# ============================================================================
# /_info
# ============================================================================

@pytest.mark.integration
def test_info_endpoint_reports_loaded_state(client):
    resp = client.get("/glp1/_info")
    assert resp.status_code == 200
    data = resp.json()

    assert data["rule_pack_version"]
    assert data["drug_db_version"]
    assert data["rule_count"] > 0
    assert data["drug_count"] > 0
    assert set(data["available_locales"]) >= {"ru", "en"}


# ============================================================================
# POST /glp1/assess
# ============================================================================

@pytest.mark.integration
def test_assess_returns_201_and_visit_id(client):
    resp = client.post("/glp1/assess", json=_basic_payload())
    assert resp.status_code == 201
    data = resp.json()

    assert data["visit_id"].startswith("VIS-")
    assert data["locale"] == "ru"
    assert data["direction"] == "ltr"
    assert data["sign_off_status"] == "pending_sign_off"
    assert data["rule_pack_version"]


@pytest.mark.integration
def test_assess_resolves_i18n_to_russian_by_default(client):
    resp = client.post("/glp1/assess", json=_basic_payload(locale="ru"))
    data = resp.json()

    triage_text = data["assessment"]["triage_summary_i18n_text"]
    # Cyrillic check — translation actually applied
    assert any("А" <= ch <= "я" or ch in "Ё-ё" for ch in triage_text), (
        f"Expected Cyrillic in Russian translation, got: {triage_text!r}"
    )


@pytest.mark.integration
def test_assess_resolves_to_hebrew_with_rtl(client):
    payload = _basic_payload(locale="he")
    resp = client.post("/glp1/assess", json=payload)
    data = resp.json()

    assert data["direction"] == "rtl"
    triage_text = data["assessment"]["triage_summary_i18n_text"]
    # Hebrew Unicode block
    assert any("֐" <= ch <= "׿" for ch in triage_text), (
        f"Expected Hebrew chars in HE translation, got: {triage_text!r}"
    )


@pytest.mark.integration
def test_assess_fires_lt4_ppi_rule(client):
    """End-to-end check that the prototypical LT4 + PPI scenario fires the rule."""
    resp = client.post("/glp1/assess", json=_basic_payload())
    data = resp.json()

    rule_ids = [i["rule_id"] for i in data["assessment"]["interactions"]]
    assert "LT4_TABLET_PPI" in rule_ids


@pytest.mark.integration
def test_assess_persists_audit_entry(client):
    """After an assessment, /audit-log should contain an assessment_created entry."""
    resp = client.post("/glp1/assess", json=_basic_payload())
    visit_id = resp.json()["visit_id"]

    resp2 = client.get("/glp1/audit-log")
    entries = resp2.json()["entries"]

    matching = [e for e in entries if e["target_id"] == visit_id and e["event_type"] == "assessment_created"]
    assert matching, f"No assessment_created audit entry for {visit_id}"


# ============================================================================
# POST /glp1/sign-off — White Coat Rule
# ============================================================================

@pytest.mark.integration
def test_sign_off_workflow_end_to_end(client):
    # 1. Assess
    visit_id = client.post("/glp1/assess", json=_basic_payload()).json()["visit_id"]

    # 2. Visit is pending
    visit = client.get(f"/glp1/visit/{visit_id}").json()
    assert visit["summary"]["sign_off_status"] == "pending_sign_off"
    assert visit["sign_offs"] == []

    # 3. Sign off
    resp = client.post("/glp1/sign-off", json={
        "visit_id": visit_id,
        "physician_id": "DR-TEST",
        "physician_name": "Dr. Test",
        "status": "signed",
        "notes": "Approved",
    })
    assert resp.status_code == 200

    # 4. Status is now signed and sign_off appears
    visit2 = client.get(f"/glp1/visit/{visit_id}").json()
    assert visit2["summary"]["sign_off_status"] == "signed"
    assert len(visit2["sign_offs"]) == 1
    assert visit2["sign_offs"][0]["physician_id"] == "DR-TEST"

    # 5. Audit log has the sign_off_completed event
    audit = client.get("/glp1/audit-log").json()["entries"]
    assert any(
        e["event_type"] == "sign_off_completed" and e["target_id"] == visit_id
        for e in audit
    )


@pytest.mark.integration
def test_sign_off_unknown_visit_returns_404(client):
    resp = client.post("/glp1/sign-off", json={
        "visit_id": "VIS-does-not-exist",
        "physician_id": "DR-X",
        "physician_name": "Dr. X",
        "status": "signed",
    })
    assert resp.status_code == 404


@pytest.mark.integration
def test_sign_off_invalid_status_returns_400(client):
    visit_id = client.post("/glp1/assess", json=_basic_payload()).json()["visit_id"]

    resp = client.post("/glp1/sign-off", json={
        "visit_id": visit_id,
        "physician_id": "DR-X",
        "physician_name": "Dr. X",
        "status": "totally-bogus",
    })
    assert resp.status_code == 400


# ============================================================================
# GET /glp1/visit/{id}/report.html
# ============================================================================

@pytest.mark.integration
def test_report_html_clinical_layer_excludes_admin_markers(client):
    visit_id = client.post("/glp1/assess", json=_basic_payload()).json()["visit_id"]

    resp = client.get(f"/glp1/visit/{visit_id}/report.html?layer=clinical&locale=ru")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")

    html = resp.text
    assert "[admin]" not in html, "Clinical layer must not leak admin internal text"
    assert "LT4_TABLET_PPI" not in html, "Clinical layer must not leak rule_id"


@pytest.mark.integration
def test_report_html_admin_layer_includes_rule_id(client):
    visit_id = client.post("/glp1/assess", json=_basic_payload()).json()["visit_id"]

    resp = client.get(f"/glp1/visit/{visit_id}/report.html?layer=admin&locale=ru")
    assert resp.status_code == 200
    html = resp.text

    assert "[admin]" in html, "Admin layer must include the resolved [admin] prefix text"
    assert "LT4_TABLET_PPI" in html, "Admin layer must expose rule_id"


@pytest.mark.integration
def test_report_html_invalid_layer_returns_400(client):
    visit_id = client.post("/glp1/assess", json=_basic_payload()).json()["visit_id"]

    resp = client.get(f"/glp1/visit/{visit_id}/report.html?layer=bogus")
    assert resp.status_code == 400


# ============================================================================
# Introspection endpoints
# ============================================================================

@pytest.mark.integration
def test_list_rules_filter_by_evidence_grade(client):
    resp = client.get("/glp1/rules?evidence_grade=A")
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) > 0
    assert all(r["evidence_grade"] == "A" for r in rules)


@pytest.mark.integration
def test_list_drugs_filter_by_class(client):
    resp = client.get("/glp1/drugs?class=DOAC")
    assert resp.status_code == 200
    drugs = resp.json()
    assert len(drugs) > 0
    assert all(d["class"] == "DOAC" for d in drugs)
