/* ==========================================================================
   codeview.js -- code, highlighted and numbered, for a card and for /source/.

   `CodeView.ref("board/x.py#L40-58")` reads an excerpt's address; `body`
   highlights code with the vendored highlight.js (web/vendor/highlight/, six
   languages) and, given a first line number, cuts it into one span per line
   carrying that number. Without highlight.js, or for a language it does not
   have, the code is escaped and nothing else.

   On the read-only source page (`routes/pages.py`, GET /source/<path>) the
   server has already numbered and marked every line, so the page reads without
   this file; this only colours it and scrolls to the marked range.
   ========================================================================== */

(function () {
"use strict";

/* An extension's language, for a fence that names a path and no language. */
var EXT = { py: "python", go: "go", sh: "bash", bash: "bash", zsh: "bash",
            lean: "lean", r: "r", sql: "sql" };

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function hl() { return typeof window !== "undefined" && window.hljs ? window.hljs : null; }

/* The language highlight.js knows by this name or alias, lower-cased, or "". */
function language(name) {
  var h = hl();
  name = String(name || "").toLowerCase();
  return name && h && h.getLanguage(name) ? name : "";
}

function fromPath(path) {
  var m = /\.([A-Za-z0-9]+)$/.exec(String(path || ""));
  return m ? (EXT[m[1].toLowerCase()] || "") : "";
}

/* `path#L40-58`, `path#L40` or a bare path: {path, from, to}, or null. A word
   is a path when it has an `#L` range or a slash; a lone word is a language. */
function ref(word) {
  var m = /^([^\s#?"'<>`]+)#L(\d+)(?:-L?(\d+))?$/.exec(String(word || ""));
  if (m) {
    var from = +m[2], to = m[3] ? +m[3] : from;
    if (to < from) { var t = from; from = to; to = t; }
    return { path: m[1], from: from, to: to };
  }
  if (/^[^\s#?"'<>`]*\/[^\s#?"'<>`]+$/.test(String(word || ""))) {
    return { path: word, from: 0, to: 0 };
  }
  return null;
}

/* Highlighted HTML split into lines, every span closed at the end of its line
   and reopened on the next, so each line stands alone. */
function splitLines(html) {
  var out = [], open = [], cur = "";
  html.split(/(<span[^>]*>|<\/span>|\n)/).forEach(function (part) {
    if (!part) return;
    if (part === "\n") {
      out.push(cur + new Array(open.length + 1).join("</span>"));
      cur = open.join("");
    } else if (part.indexOf("<span") === 0) {
      open.push(part); cur += part;
    } else if (part === "</span>") {
      open.pop(); cur += part;
    } else {
      cur += part;
    }
  });
  out.push(cur + new Array(open.length + 1).join("</span>"));
  return out;
}

function highlighted(code, lang) {
  var h = hl();
  if (lang && h) {
    try { return h.highlight(code, { language: lang, ignoreIllegals: true }).value; }
    catch (e) { /* a grammar that throws leaves the code plain */ }
  }
  return esc(code);
}

/* The inside of a <code>: highlighted, and with `start` a number, one block
   span per line numbered from it; lines from `mark` to `markTo` get `mark`. */
function body(code, lang, start, mark, markTo) {
  var html = highlighted(code, language(lang));
  if (typeof start !== "number") return html;
  var lines = splitLines(html);
  return lines.map(function (line, i) {
    var n = start + i;
    var cls = mark && n >= mark && n <= (markTo || mark) ? "line mark" : "line";
    return '<span class="' + cls + '" data-n="' + n + '">' + line
      + (i < lines.length - 1 ? "\n" : "") + "</span>";
  }).join("");
}

/* The source page: colour the server's numbered lines, keep their marks. */
function upgrade(doc) {
  var el = doc.querySelector("code[data-source]");
  if (!el) return;
  var lang = language(el.getAttribute("data-lang"));
  var from = +el.getAttribute("data-from") || 0;
  var to = +el.getAttribute("data-to") || from;
  if (lang) {
    el.innerHTML = body(el.textContent, lang, 1, from, to);
    el.classList.add("hljs");
  }
  var first = el.querySelector(".line.mark");
  if (first && first.scrollIntoView) first.scrollIntoView({ block: "center" });
}

var api = { ref: ref, body: body, language: language, fromPath: fromPath,
            splitLines: splitLines, esc: esc, upgrade: upgrade };
if (typeof window !== "undefined") window.CodeView = api;
if (typeof module !== "undefined" && module.exports) module.exports = api;

if (typeof document !== "undefined" && document.querySelector
    && document.body && document.body.classList
    && document.body.classList.contains("source-page")) {
  /* The board's theme is `typeface.js`'s, loaded before this on the page. */
  upgrade(document);
}
})();
