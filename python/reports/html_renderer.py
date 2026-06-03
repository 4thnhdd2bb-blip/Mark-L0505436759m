"""
METACOD GLP-1 module — HTML report renderer.

Produces a print-friendly HTML document from a resolved PharmacistAssessment
(i18n already resolved). Supports two layers:

  - "clinical"  : default — what the physician sees / hands to the patient
  - "admin"     : adds rule_ids, mechanism traces, and internal pattern terms
                  used for METACOD research / SaMD audit review only

RTL is applied automatically for HE locale via dir="rtl" on <html>.

For browser print-to-PDF: render and return as text/html.
For server-side PDF: pipe the same HTML through WeasyPrint in routers/glp1.py.

No Jinja2 dependency — uses pure f-strings to keep the integration footprint
minimal. A Jinja2 templates/ directory is a clean Part 3 polish step when more
report variations are needed.
"""

from __future__ import annotations

import html as html_module
from datetime import datetime
from typing import Any


# ----- Static styles (print-friendly, embedded so a single-file render works) -----

_CSS = """
* { box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1a1a1a;
    line-height: 1.45;
    margin: 0;
    padding: 32px;
    max-width: 800px;
    background: #fff;
}
h1 { font-size: 22px; margin: 0 0 4px 0; }
h2 { font-size: 16px; margin: 24px 0 8px 0; padding-bottom: 4px; border-bottom: 1px solid #e0e0e0; }
h3 { font-size: 14px; margin: 16px 0 4px 0; }
p, li { font-size: 13px; margin: 4px 0; }
.meta { color: #555; font-size: 12px; margin-bottom: 16px; }
.triage { display: inline-block; padding: 6px 12px; border-radius: 4px; font-weight: 600; font-size: 13px; }
.triage-green { background: #e6f4ea; color: #1e8449; }
.triage-yellow { background: #fff8e1; color: #b7791f; }
.triage-red { background: #fdecea; color: #c0392b; }
.grade { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 11px; font-weight: 600; margin-left: 6px; }
.grade-A { background: #d1f0d8; color: #1e6f3e; }
.grade-B { background: #fff4d1; color: #8a6a00; }
.grade-C { background: #ececec; color: #555; }
.rule { border-left: 3px solid #ccc; padding: 8px 12px; margin: 8px 0; background: #fafafa; }
.rule.high { border-left-color: #c0392b; }
.rule.moderate { border-left-color: #b7791f; }
.rule.low { border-left-color: #1e8449; }
.mech { font-style: italic; color: #555; font-size: 12px; }
.admin { background: #f5f0ff; border: 1px dashed #9b6dff; padding: 6px 10px; margin: 4px 0; font-size: 11px; color: #4a2e8a; }
.admin-label { font-weight: 700; text-transform: uppercase; font-size: 10px; letter-spacing: 0.05em; }
.footer { margin-top: 32px; padding-top: 12px; border-top: 1px solid #e0e0e0; font-size: 11px; color: #666; }
.footer .signoff-pending { color: #b7791f; font-weight: 600; }
.footer .signoff-signed { color: #1e8449; font-weight: 600; }
.footer .signoff-rejected { color: #c0392b; font-weight: 600; }
ul { padding-left: 20px; margin: 4px 0; }
.med { font-weight: 600; }
.sources { font-size: 11px; color: #777; margin-top: 4px; }
@media print {
    body { padding: 16px; }
    .admin { background: #f9f6ff; }
}
[dir="rtl"] .rule { border-left: none; border-right: 3px solid #ccc; }
[dir="rtl"] .rule.high { border-right-color: #c0392b; }
[dir="rtl"] .rule.moderate { border-right-color: #b7791f; }
[dir="rtl"] .rule.low { border-right-color: #1e8449; }
[dir="rtl"] ul { padding-left: 0; padding-right: 20px; }
"""


def _esc(s: Any) -> str:
    """HTML-escape any value, converting None to empty string."""
    if s is None:
        return ""
    return html_module.escape(str(s))


def _grade_badge(grade: str) -> str:
    g = _esc(grade)
    return f'<span class="grade grade-{g}">{g}</span>'


def _triage_class(color: str) -> str:
    return {"green": "triage-green", "yellow": "triage-yellow", "red": "triage-red"}.get(color, "triage-green")


# ----- Section renderers -----

def _render_meta(visit_id: str, patient: dict, created_at: str) -> str:
    return f"""
    <div class="meta">
        <strong>Visit:</strong> {_esc(visit_id)}
        &nbsp;|&nbsp;
        <strong>Patient:</strong> {_esc(patient.get("patient_id", ""))}
        ({_esc(patient.get("age_years", ""))}y, {_esc(patient.get("sex", ""))})
        &nbsp;|&nbsp;
        <strong>Generated:</strong> {_esc(created_at)}
    </div>
    """


def _render_triage(assessment: dict) -> str:
    color = assessment.get("triage_color", "green")
    text = assessment.get("triage_summary_i18n_text") or assessment.get("triage_summary_i18n_key", "")
    return f"""
    <h2>Triage</h2>
    <span class="triage {_triage_class(color)}">{_esc(text)}</span>
    """


def _render_interactions(assessment: dict, layer: str) -> str:
    interactions = assessment.get("interactions", [])
    if not interactions:
        return "<h2>Interactions</h2><p>No rule triggers for this visit.</p>"

    parts = ["<h2>Drug–patient interactions</h2>"]
    for finding in interactions:
        severity = finding.get("severity", "moderate")
        grade = finding.get("evidence_grade", "C")
        rule_name = finding.get("rule_name", finding.get("rule_id", ""))
        med = finding.get("medication_name", "")

        parts.append(f'<div class="rule {_esc(severity)}">')
        parts.append(f'<h3>{_esc(rule_name)} {_grade_badge(grade)}</h3>')
        parts.append(f'<p><span class="med">{_esc(med)}</span></p>')

        if layer == "admin":
            mech = finding.get("admin_trace", {}).get("mechanism", "")
            if mech:
                parts.append(f'<p class="mech">{_esc(mech)}</p>')

        # Physician actions
        phys_actions = finding.get("physician_actions", [])
        if phys_actions:
            parts.append("<h4>Physician actions</h4><ul>")
            for a in phys_actions:
                txt = a.get("i18n_text") or a.get("i18n_key", "")
                parts.append(f'<li>{_esc(txt)} {_grade_badge(a.get("evidence_grade", grade))}</li>')
            parts.append("</ul>")

        # Patient actions
        pat_actions = finding.get("patient_actions", [])
        if pat_actions:
            parts.append("<h4>Patient education</h4><ul>")
            for a in pat_actions:
                txt = a.get("i18n_text") or a.get("i18n_key", "")
                parts.append(f'<li>{_esc(txt)}</li>')
            parts.append("</ul>")

        # Labs
        lab_plan = finding.get("lab_plan", [])
        if lab_plan:
            parts.append("<h4>Lab plan</h4><ul>")
            for lab in lab_plan:
                txt = lab.get("i18n_text") or lab.get("i18n_key", lab.get("test", ""))
                parts.append(f'<li>{_esc(txt)}</li>')
            parts.append("</ul>")

        # Admin trace (visible only in admin layer)
        if layer == "admin":
            trace = finding.get("admin_trace", {})
            if trace:
                internal_text = trace.get("i18n_text_internal", "")
                parts.append(
                    '<div class="admin">'
                    '<span class="admin-label">admin</span> &nbsp;'
                    f'rule_id: <code>{_esc(trace.get("rule_id", ""))}</code> &nbsp;|&nbsp; '
                    f'pattern: <code>{_esc(trace.get("pattern", ""))}</code>'
                    + (f'<br>{_esc(internal_text)}' if internal_text else '')
                    + '</div>'
                )

        sources = finding.get("sources", [])
        if sources and layer == "admin":
            parts.append('<div class="sources">Sources: ' + "; ".join(_esc(s) for s in sources) + "</div>")

        parts.append("</div>")

    return "\n".join(parts)


def _render_forecast(assessment: dict, layer: str) -> str:
    forecast = assessment.get("forecast", {})
    parts = ["<h2>Clinical forecast</h2>"]

    glp1 = forecast.get("glp1_dosing", {})
    if glp1:
        decision = _esc(glp1.get("decision", ""))
        text = glp1.get("i18n_text") or glp1.get("i18n_key", "")
        grade = glp1.get("evidence_grade", "C")
        parts.append(f"<h3>GLP-1 dosing decision {_grade_badge(grade)}</h3>")
        parts.append(f"<p><strong>{decision}</strong> — {_esc(text)}</p>")
        rationale_texts = glp1.get("rationale_i18n_texts") or glp1.get("rationale_i18n_keys", [])
        if rationale_texts:
            parts.append("<ul>")
            for r in rationale_texts:
                parts.append(f"<li>{_esc(r)}</li>")
            parts.append("</ul>")

    future_risks = forecast.get("future_risks", [])
    if future_risks:
        parts.append("<h3>Future risks</h3><ul>")
        for r in future_risks:
            txt = r.get("i18n_text") or r.get("i18n_key", "")
            tf = r.get("timeframe_weeks", "")
            grade = r.get("evidence_grade", "C")
            parts.append(f"<li>[+{_esc(tf)}w] {_esc(txt)} {_grade_badge(grade)}</li>")
        parts.append("</ul>")

    adjustments = forecast.get("chronic_med_adjustments", [])
    if adjustments:
        parts.append("<h3>Chronic medication adjustments</h3><ul>")
        for a in adjustments:
            adj_txt = a.get("adjustment_i18n_text") or a.get("adjustment_i18n_key", "")
            trig_txt = a.get("trigger_i18n_text") or a.get("trigger_i18n_key", "")
            med = a.get("medication_name", "")
            tf = a.get("timeframe_weeks", "")
            grade = a.get("evidence_grade", "C")
            parts.append(
                f'<li><span class="med">{_esc(med)}</span> — {_esc(adj_txt)} '
                f'<em>({_esc(trig_txt)}, +{_esc(tf)}w)</em> {_grade_badge(grade)}</li>'
            )
        parts.append("</ul>")

    return "\n".join(parts)


def _render_footer(assessment: dict, sign_off_status: str) -> str:
    status_class = {
        "pending_sign_off": "signoff-pending",
        "signed": "signoff-signed",
        "rejected": "signoff-rejected",
        "amended": "signoff-signed",
    }.get(sign_off_status, "signoff-pending")

    return f"""
    <div class="footer">
        <p>
            Status:
            <span class="{status_class}">{_esc(sign_off_status)}</span>
            &nbsp;|&nbsp;
            rule_pack: {_esc(assessment.get("rule_pack_version", ""))}
            &nbsp;|&nbsp;
            drug_db: {_esc(assessment.get("drug_db_version", ""))}
        </p>
        <p>
            METACOD Health — GLP-1 Complication Prevention module.
            This document is decision support; clinical judgment of the treating physician prevails.
        </p>
    </div>
    """


# ----- Public entry point -----

def render_report_html(
    visit_id: str,
    patient: dict,
    assessment: dict,
    locale: str = "ru",
    direction: str = "ltr",
    layer: str = "clinical",
    sign_off_status: str = "pending_sign_off",
    created_at: str | None = None,
) -> str:
    """Return a complete HTML document for the visit.

    Args:
        visit_id: stable identifier
        patient: PatientContext as dict
        assessment: PharmacistAssessment as dict, with i18n_text already resolved
        locale: 'ru' | 'en' | 'he'
        direction: 'ltr' | 'rtl'
        layer: 'clinical' (default) or 'admin'
        sign_off_status: enum value
        created_at: ISO timestamp; defaults to now
    """
    created_at = created_at or datetime.utcnow().isoformat(timespec="seconds")

    body = "\n".join([
        _render_meta(visit_id, patient, created_at),
        _render_triage(assessment),
        _render_interactions(assessment, layer),
        _render_forecast(assessment, layer),
        _render_footer(assessment, sign_off_status),
    ])

    return f"""<!DOCTYPE html>
<html lang="{_esc(locale)}" dir="{_esc(direction)}">
<head>
    <meta charset="utf-8">
    <title>METACOD GLP-1 — {_esc(visit_id)}</title>
    <style>{_CSS}</style>
</head>
<body>
    <h1>METACOD GLP-1 Complication Prevention</h1>
    {body}
</body>
</html>
"""
