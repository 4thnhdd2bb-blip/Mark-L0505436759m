/**
 * METACOD Cabinet — Word (.doc) report renderer for the batch pipeline.
 *
 * Produces a print-quality, Word-openable document (HTML-based .doc — opens
 * natively in Microsoft Word / LibreOffice, no dependency, RTL-aware) from the
 * cabinet engine's differential result. Mirrors the cabinet's on-screen
 * conclusion (visitReportHTML / diffResultHTML) so a batch-generated Word and
 * the interactive cabinet read as one product.
 *
 * Palette borrowed from the cabinet UI (teal editorial-clinical).
 */

const LABELS = {
  ru: {
    title: "Медицинское заключение (история болезни)",
    brand: "METACOD — Кабинет · ретроспективный анализ",
    reportFor: "Заключение для", age: "возраст", sex: "пол",
    complaints: "Жалобы и отмеченные симптомы",
    meds: "Текущие лекарства", allergies: "Аллергии",
    cautions: "Предостережения",
    suspected: "Предполагаемые диагнозы (METACOD)",
    why: "Почему", workup: "Рекомендованное обследование",
    today: "Лечение сегодня", after: "После подтверждения",
    followUp: "Контроль", match: "совпадение",
    none: "—",
    disc: "Это поддержка клинического решения, а не окончательный диагноз. Препарат, доза и диагноз — решение лечащего врача.",
  },
  en: {
    title: "Medical report (case summary)",
    brand: "METACOD — Cabinet · retrospective analysis",
    reportFor: "Report for", age: "age", sex: "sex",
    complaints: "Complaints and marked symptoms",
    meds: "Current medications", allergies: "Allergies",
    cautions: "Cautions",
    suspected: "Suspected diagnoses (METACOD)",
    why: "Why", workup: "Recommended work-up",
    today: "Treatment today", after: "After confirmation",
    followUp: "Follow-up", match: "match",
    none: "—",
    disc: "This is clinical decision support, not a final diagnosis. Drug, dose and diagnosis are the treating physician's decision.",
  },
  he: {
    title: "סיכום רפואי (היסטוריית מחלה)",
    brand: "METACOD — מרפאה · ניתוח רטרוספקטיבי",
    reportFor: "סיכום עבור", age: "גיל", sex: "מין",
    complaints: "תלונות ותסמינים מסומנים",
    meds: "תרופות נוכחיות", allergies: "אלרגיות",
    cautions: "אזהרות",
    suspected: "אבחנות משוערות (METACOD)",
    why: "מדוע", workup: "בירור מומלץ",
    today: "טיפול היום", after: "לאחר אישור",
    followUp: "מעקב", match: "התאמה",
    none: "—",
    disc: "זוהי תמיכה בהחלטה קלינית, לא אבחנה סופית. תרופה, מינון ואבחנה — באחריות הרופא המטפל.",
  },
};

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function L(locale, key) {
  return (LABELS[locale] || LABELS.ru)[key] ?? LABELS.ru[key] ?? key;
}

const STYLE = `
  @page { margin: 2cm; }
  body { font-family: Georgia, "Times New Roman", serif; color: #15302f; line-height: 1.5; font-size: 11pt; }
  .brand { color: #5d716f; font-size: 9pt; letter-spacing: .5px; }
  h1 { color: #0a5b63; font-size: 18pt; margin: 2pt 0; }
  .meta { color: #5d716f; font-size: 9.5pt; margin-bottom: 10pt; }
  h2 { color: #0a5b63; font-size: 12pt; border-bottom: 1px solid #dde7e6; padding-bottom: 2pt; margin: 14pt 0 4pt; }
  .dx { border-left: 3px solid #0e7c86; padding: 4pt 0 4pt 10pt; margin: 8pt 0; }
  .dx-name { font-weight: bold; font-size: 11.5pt; color: #15302f; }
  .pct { display: inline-block; background: #e2f1f0; color: #0a5b63; border-radius: 8pt; padding: 0 6pt; font-size: 9pt; font-weight: bold; }
  .lbl { font-weight: bold; color: #0a5b63; }
  .caution { color: #7a1610; }
  .flag { background: #fbe9e7; border: 1px solid #f3c9c4; border-radius: 6pt; padding: 6pt 8pt; color: #7a1610; }
  ul { margin: 2pt 0 2pt 0; padding-left: 16pt; }
  .disc { margin-top: 16pt; border-top: 1px solid #dde7e6; padding-top: 6pt; font-size: 9pt; color: #5d716f; }
`;

function row(label, value) {
  if (value == null || value === "") return "";
  return `<div style="margin:3pt 0"><span class="lbl">${esc(label)}:</span> ${esc(value)}</div>`;
}

function renderDx(d, locale) {
  const checks = [];
  if (d.workup) checks.push(...(d.workup.labs || []), ...(d.workup.imaging || []), ...(d.workup.procedures || []));
  const why = (d.matched || []).map((m) => m.text).slice(0, 6).join("; ");
  const cautions = (d.cautions || []).map((c) => `<li class="caution">${esc(c)}</li>`).join("");
  return `<div class="dx">
    <div class="dx-name">${esc(d.name)} <span class="pct">${d.matchPct}% ${esc(L(locale, "match"))}</span></div>
    ${why ? `<div><span class="lbl">${esc(L(locale, "why"))}:</span> ${esc(why)}</div>` : ""}
    ${checks.length ? `<div><span class="lbl">${esc(L(locale, "workup"))}:</span> ${esc(checks.join("; "))}</div>` : ""}
    ${d.treatmentToday ? `<div><span class="lbl">${esc(L(locale, "today"))}:</span> ${esc(d.treatmentToday)}</div>` : ""}
    ${d.treatmentFinal ? `<div><span class="lbl">${esc(L(locale, "after"))}:</span> ${esc(d.treatmentFinal)}</div>` : ""}
    ${d.followUp ? `<div><span class="lbl">${esc(L(locale, "followUp"))}:</span> ${esc(d.followUp)}</div>` : ""}
    ${cautions ? `<ul>${cautions}</ul>` : ""}
  </div>`;
}

/**
 * Build a single-patient Word (.doc) document.
 *
 * @param {object} args
 * @param {object} args.patient  { name, age, sex, allergies, meds:[{name,dose}] }
 * @param {object} args.extra    { complaint, fqParts:[], symLabels:[] }
 * @param {Array}  args.dx       scoreDifferential() output
 * @param {Array}  args.cautions patientCautions() output (strings)
 * @param {string} [args.locale] ru | en | he
 * @param {string} [args.generatedAt] ISO date string
 * @returns {string} a complete Word-openable HTML document
 */
export function buildWordDoc({ patient, extra = {}, dx = [], cautions = [], locale = "ru", generatedAt }) {
  const dir = locale === "he" ? "rtl" : "ltr";
  const date = generatedAt || new Date().toISOString().slice(0, 10);
  const complaintBits = [extra.complaint, ...(extra.symLabels || []), ...(extra.fqParts || [])]
    .filter((x) => x && String(x).trim());
  const meds = (patient.meds || []).map((m) => m.name + (m.dose ? ` ${m.dose}` : "")).join("; ");
  const head =
    `${esc(patient.name || L(locale, "none"))}` +
    (patient.age != null && patient.age !== "" ? ` · ${esc(L(locale, "age"))} ${esc(patient.age)}` : "") +
    (patient.sex ? ` · ${esc(L(locale, "sex"))} ${esc(patient.sex)}` : "");

  const dxHtml = dx.length
    ? dx.slice(0, 5).map((d) => renderDx(d, locale)).join("")
    : `<div class="meta">${esc(L(locale, "none"))}</div>`;

  return `<!DOCTYPE html>
<html xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word"
      xmlns="http://www.w3.org/TR/REC-html40" lang="${locale}" dir="${dir}">
<head><meta charset="utf-8"><title>${esc(L(locale, "title"))}</title>
<!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->
<style>${STYLE}</style></head>
<body dir="${dir}">
  <div class="brand">${esc(L(locale, "brand"))} · ${esc(date)}</div>
  <h1>${esc(L(locale, "title"))}</h1>
  <div class="meta"><span class="lbl">${esc(L(locale, "reportFor"))}:</span> ${head}</div>

  <h2>${esc(L(locale, "complaints"))}</h2>
  <div>${complaintBits.length ? esc(complaintBits.join(" · ")) : esc(L(locale, "none"))}</div>

  <h2>${esc(L(locale, "meds"))}</h2>
  <div>${meds ? esc(meds) : esc(L(locale, "none"))}</div>

  <h2>${esc(L(locale, "allergies"))}</h2>
  <div>${patient.allergies ? esc(patient.allergies) : esc(L(locale, "none"))}</div>

  ${cautions.length ? `<h2>${esc(L(locale, "cautions"))}</h2><div class="flag">${cautions.map((c) => esc(c)).join("<br>")}</div>` : ""}

  <h2>${esc(L(locale, "suspected"))}</h2>
  ${dxHtml}

  <div class="disc">${esc(L(locale, "disc"))}</div>
</body>
</html>`;
}

/** Wrap several per-patient report bodies into one combined Word workbook. */
export function combineWordDocs(htmlDocs) {
  const bodies = htmlDocs.map((doc, i) => {
    const m = doc.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
    const inner = m ? m[1] : doc;
    const brk = i === 0 ? "" : `<br clear="all" style="mso-special-character:line-break;page-break-before:always">`;
    return brk + inner;
  });
  const dir = htmlDocs[0] && /dir="rtl"/.test(htmlDocs[0]) ? "rtl" : "ltr";
  return `<!DOCTYPE html>
<html xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word"
      xmlns="http://www.w3.org/TR/REC-html40" dir="${dir}">
<head><meta charset="utf-8"><title>METACOD batch</title>
<!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->
<style>${STYLE}</style></head>
<body dir="${dir}">${bodies.join("\n")}</body></html>`;
}

export default buildWordDoc;
