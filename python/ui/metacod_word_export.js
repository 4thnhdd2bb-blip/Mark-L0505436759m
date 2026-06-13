/*!
 * METACOD Cabinet — Word (.docx) export add-on.
 *
 * Drop-in, dependency-free. Add ONE line just before </body> of cabinet.html:
 *
 *     <script src="metacod_word_export.js"></script>
 *
 * It watches for any conclusion the cabinet renders (the `.rep` report block,
 * the `.rx-sheet` prescription) and adds a "📝 Скачать Word (.docx)" button
 * next to the existing Print button. The download is a Word-openable document
 * (HTML-based .doc — opens natively in Microsoft Word / LibreOffice, keeps the
 * cabinet's styling, and respects right-to-left for Hebrew).
 *
 * Why .doc(HTML) and not a real OOXML .docx? The cabinet is a portable, offline
 * single file with no build step or libraries; HTML-based Word documents give a
 * beautiful, editable result with zero dependencies. For server-side true .docx
 * (python-docx) see python/reports/docx_renderer.py; for bulk 60k conclusions
 * see cabinet/batch.mjs.
 */
(function () {
  "use strict";

  var LABELS = {
    ru: { btn: "📝 Скачать Word (.docx)", file: "Заключение" },
    en: { btn: "📝 Download Word (.docx)", file: "Report" },
    he: { btn: "📝 הורד Word (.docx)", file: "סיכום" },
  };
  function lang() {
    var l = (document.documentElement.lang || "ru").slice(0, 2);
    return LABELS[l] ? l : "ru";
  }
  function L(k) { return LABELS[lang()][k]; }

  function dir() { return document.documentElement.dir === "rtl" ? "rtl" : "ltr"; }

  // Pull the cabinet's own report/prescription CSS so the Word file looks the same.
  function collectStyles() {
    var css = "";
    var sheets = document.querySelectorAll("style");
    for (var i = 0; i < sheets.length; i++) css += sheets[i].textContent + "\n";
    // Keep it lean: Word only needs the report-related rules, but shipping all
    // inline styles is harmless and guarantees fidelity.
    return css;
  }

  function wrapWord(innerHTML) {
    var d = dir();
    return (
      '<!DOCTYPE html><html xmlns:o="urn:schemas-microsoft-com:office:office" ' +
      'xmlns:w="urn:schemas-microsoft-com:office:word" ' +
      'xmlns="http://www.w3.org/TR/REC-html40" dir="' + d + '">' +
      '<head><meta charset="utf-8">' +
      "<!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View>" +
      "</w:WordDocument></xml><![endif]-->" +
      "<style>@page{margin:2cm}body{font-family:Georgia,'Times New Roman',serif;" +
      "color:#15302f;line-height:1.5}" + collectStyles() + "</style></head>" +
      '<body dir="' + d + '">' + innerHTML + "</body></html>"
    );
  }

  function download(filename, html) {
    var blob = new Blob(["﻿" + html], { type: "application/msword" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { document.body.removeChild(a); URL.revokeObjectURL(url); }, 0);
  }

  function todayStr() {
    var d = new Date();
    return d.getFullYear() + "-" +
      String(d.getMonth() + 1).padStart(2, "0") + "-" +
      String(d.getDate()).padStart(2, "0");
  }

  function downloadNode(node, baseName) {
    download((baseName || L("file")) + "_" + todayStr() + ".doc", wrapWord(node.innerHTML));
  }

  // Public API (also usable from the cabinet directly).
  window.METACODWord = {
    download: download,
    wrap: wrapWord,
    fromNode: downloadNode,
  };

  function makeButton(onClick) {
    var b = document.createElement("button");
    b.className = "btn-ghost btn-sm metacod-word-btn";
    b.type = "button";
    b.textContent = L("btn");
    b.addEventListener("click", onClick);
    return b;
  }

  // Inject a Word button beside report / prescription blocks as they appear.
  function augment(root) {
    var reports = (root || document).querySelectorAll(".rep, .rx-sheet");
    for (var i = 0; i < reports.length; i++) {
      var rep = reports[i];
      if (rep.getAttribute("data-metacod-word") === "1") continue;
      rep.setAttribute("data-metacod-word", "1");
      var btn = makeButton((function (node) {
        return function () { downloadNode(node, L("file")); };
      })(rep));
      // Place after the report block, inside the same card if possible.
      var anchor = rep.parentNode;
      (anchor || rep).insertBefore
        ? (anchor || rep).appendChild(btn)
        : rep.appendChild(btn);
    }
  }

  function start() {
    augment(document);
    var obs = new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        if (muts[i].addedNodes && muts[i].addedNodes.length) { augment(document); break; }
      }
    });
    obs.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
