/* ==========================================================================
   board.js -- client for the live tutoring board.

   Holds one Server-Sent Events connection open. It opens on the whole board,
   and every time the tutor writes a card file the server pushes what changed;
   this applies it (`absorb`) and re-renders the whole: markdown
   to HTML, KaTeX for the mathematics, compiled SVG for anything TikZ. Sending
   text or dropping a file posts back the other way.
   ========================================================================== */

(function () {
"use strict";

/* WHICH SESSION THIS BOARD IS. The server serves a board at `/s/<id>/board`,
   and everything the board asks about its session goes back under that prefix:
   `api` for a fetch, `atSession` for a URL the server handed over. Outside a
   session (a test's one-session server) `BASE` is empty. Static assets stay
   absolute, and so do the cross-subject routes (`/subjects.json`). */
function sessionBase() {
  var m = /^\/s\/[^\/]+/.exec((window.location && window.location.pathname) || "");
  return m ? m[0] : "";
}
var BASE = sessionBase();
var SESSION = BASE ? decodeURIComponent(BASE.slice(3)) : "";

function api(path, init) { return fetch(BASE + path, init); }

/* A leading-slash URL the server wrote (`/answers/...`, `/doc/<id>/<n>.png`,
   `/slate/page-...`), under this session. Idempotent, so a sink can apply it to
   a URL somebody already prefixed. */
function atSession(url) {
  if (!BASE || typeof url !== "string" || url.charAt(0) !== "/"
      || url.charAt(1) === "/") return url;
  if (url.indexOf("/static/") === 0 || url.indexOf(BASE + "/") === 0) return url;
  return BASE + url;
}

/* What markdown may link to inside the session: the rest is the web, or a
   static asset, and stays as written. */
var SESSION_URL = /^\/(result|doc|figure|answers|slate|source)\//;
function mdUrl(url) { return BASE && SESSION_URL.test(url) ? BASE + url : url; }

/* The page's own links to the session's other surfaces. */
if (BASE) {
  Array.prototype.forEach.call(
    document.querySelectorAll('a[href^="/slate"], a[href^="/board"], a[href^="/library"]'),
    function (a) { a.setAttribute("href", BASE + a.getAttribute("href")); });
}

var els = {
  older: document.getElementById("older"),
  bar: document.getElementById("bar"),
  dot: document.getElementById("dot"),
  course: document.getElementById("course"),
  chapter: document.getElementById("chapter"),
  board: document.getElementById("board"),
  cards: document.getElementById("cards"),
  empty: document.getElementById("empty"),
  emptyLead: document.getElementById("empty-lead"),
  begin: document.getElementById("begin"),
  noTutor: document.getElementById("no-tutor"),
  tutorBad: document.getElementById("tutorbad"),
  skip: document.getElementById("skip"),
  notesend: document.getElementById("notesend"),
  annotate: document.getElementById("btn-annotate"),
  calc: document.getElementById("btn-calc"),
  notepick: document.getElementById("notepick"),
  notepickList: document.getElementById("notepick-list"),
  notepickEmpty: document.getElementById("notepick-empty"),
  notepickAll: document.getElementById("notepick-all"),
  notepickSend: document.getElementById("notepick-send"),
  notepickClose: document.getElementById("notepick-close"),
  offline: document.getElementById("offline"),
  linkbad: document.getElementById("linkbad"),
  newver: document.getElementById("newver"),
  newverNow: document.getElementById("newver-now"),
  newverLater: document.getElementById("newver-later"),
  hwbar: document.getElementById("hwbar"),
  healthbar: document.getElementById("healthbar"),
  healthText: document.getElementById("health-text"),
  hwSet: document.getElementById("hw-set"),
  hwCount: document.getElementById("hw-count"),
  hwBuild: document.getElementById("hw-build"),
  jump: document.getElementById("jump"),
  panic: document.getElementById("panic"),
  findink: document.getElementById("findink"),
  reopen: document.getElementById("reopen"),
  addFile: document.getElementById("btn-add-file"),
  scratch: document.getElementById("scratch"),
  scratchList: document.getElementById("scratch-list"),
  writer: document.getElementById("writer"),
  sent: document.getElementById("sent"),
  sentText: document.getElementById("sent-text"),
  trace: document.getElementById("trace"),
  agent: document.getElementById("agent"),
  finish: document.getElementById("finish"),
  finishLead: document.getElementById("finish-lead"),
  finishSub: document.getElementById("finish-sub"),
  save: document.getElementById("btn-save"),
  barmenu: document.getElementById("barmenu"),
  subjectBtn: document.getElementById("btn-subject"),
  modeBtn: document.getElementById("btn-mode"),
  makeBtn: document.getElementById("btn-make"),
  endBtn: document.getElementById("btn-end"),
  makemenu: document.getElementById("makemenu"),
  makeAbout: document.getElementById("make-about"),
  makeWriteup: document.getElementById("make-writeup"),
  makeDeck: document.getElementById("make-deck"),
  makePaper: document.getElementById("make-paper"),
  makeSaid: document.getElementById("make-said"),
  subjpick: document.getElementById("subjpick"),
  subjpickList: document.getElementById("subjpick-list"),
  subjpickForm: document.getElementById("subjpick-form"),
  subjpickName: document.getElementById("subjpick-name"),
  subjpickPhi: document.getElementById("subjpick-phi"),
  subjpickSaid: document.getElementById("subjpick-said"),
  endedbar: document.getElementById("endedbar"),
  codebar: document.getElementById("codebar"),
  codeCmd: document.getElementById("code-cmd"),
  codeCopy: document.getElementById("code-copy"),
  codeStep: document.getElementById("code-step"),
  codeClose: document.getElementById("code-close"),
  codeBtn: document.getElementById("btn-code"),
  chrome: document.getElementById("chrome"),
  drawbar: document.getElementById("drawbar"),
  home: document.getElementById("btn-home"),
  finishLeave: document.getElementById("finish-leave"),
  finishYes: document.getElementById("finish-yes"),
  finishNo: document.getElementById("finish-no"),
  saveDot: null,
  pushed: document.getElementById("pushed"),
  pushedIcon: document.getElementById("pushed-icon"),
  pushedText: document.getElementById("pushed-text"),
  pushedGet: document.getElementById("pushed-get"),
  pushedView: document.getElementById("pushed-view"),
  carry: document.getElementById("carry"),
  busy: document.getElementById("busy"),
  busyText: document.getElementById("busy-text"),
  busySince: document.getElementById("busy-since"),
  newsBar: document.getElementById("newsbar"),
  newsLead: document.getElementById("news-lead"),
  writeupList: document.getElementById("writeup-list"),
  newsHide: document.getElementById("news-hide"),
  typebox: document.getElementById("typebox"),
  saybox: document.getElementById("saybox"),
  said: document.getElementById("said"),
  saidLabel: document.getElementById("said-label"),
  saidText: document.getElementById("said-text"),
  saidHint: document.getElementById("said-hint"),
  sayMath: document.getElementById("say-math"),
  sendType: document.getElementById("send-type"),
  tabWrite: document.getElementById("tab-write"),
  tabType: document.getElementById("tab-type"),
  file: document.getElementById("file"),
  drop: document.getElementById("drop")
};

var seenIds = Object.create(null);
var firstPaint = true;
/* Which sitting the last frame was of. `null` until the first one, so the marks
   restored from the very first payload are not thrown away before they are
   drawn. See the note in `render`. */
var sittingKey = null;
/* When a hand last touched the page. A scroll repeated after typesetting
   settles asks this first, because repeating it under somebody already reading
   is worse than landing wrong. A real gesture, not our own `scrollTo`. */
var handledAt = 0;
/* How many payloads have brought a card. Anything that wants to put the page
   somewhere and then put it there again a moment later has to give that up the
   moment the tutor writes: the second landing was computed for a lesson that no
   longer exists. */
var cardsArrived = 0;
["wheel", "touchstart", "pointerdown", "keydown"].forEach(function (ev) {
  window.addEventListener(ev, function () { handledAt = Date.now(); },
                          { passive: true });
});

/* ---------------------------------------------------------------- markdown */
/* Math and code are pulled out first so markdown never mangles a subscript or
   an asterisk that belongs to a formula. They go back in as escaped text, which
   is exactly what KaTeX's auto-render wants to walk. */

/* Private-use sentinels. They cannot occur in a lesson, so a parked math or
   code placeholder never collides with a digit written in the prose. */
var SENT_OPEN = "\uE000", SENT_CLOSE = "\uE001", SENT_NEST = "\uE002";
var SENT_RE = /\uE000(\d+)\uE001/g;

var MATH_PATTERNS = [
  { open: "$$", close: "$$", display: true },
  { open: "\\[", close: "\\]", display: true },
  { open: "\\(", close: "\\)", display: false },
  { open: "$", close: "$", display: false }
];

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function protect(src, store) {
  var out = "";
  var i = 0;
  while (i < src.length) {
    var ch = src[i];

    /* fenced code block */
    if (src.startsWith("```", i) && (i === 0 || src[i - 1] === "\n")) {
      var fenceEnd = src.indexOf("\n```", i + 3);
      var stop = fenceEnd === -1 ? src.length : fenceEnd + 4;
      store.push({ kind: "fence", text: src.slice(i, stop) });
      out += SENT_OPEN + (store.length - 1) + SENT_CLOSE;
      i = stop;
      continue;
    }

    /* inline code */
    if (ch === "`") {
      var tickEnd = src.indexOf("`", i + 1);
      if (tickEnd !== -1) {
        store.push({ kind: "code", text: src.slice(i + 1, tickEnd) });
        out += SENT_OPEN + (store.length - 1) + SENT_CLOSE;
        i = tickEnd + 1;
        continue;
      }
    }

    /* escaped dollar */
    if (ch === "\\" && src[i + 1] === "$") { out += "\\$"; i += 2; continue; }

    /* math */
    var matched = false;
    for (var p = 0; p < MATH_PATTERNS.length; p++) {
      var pat = MATH_PATTERNS[p];
      if (!src.startsWith(pat.open, i)) continue;
      var from = i + pat.open.length;
      var end = -1;
      var j = from;
      while (j < src.length) {
        if (src[j] === "\\") { j += 2; continue; }
        if (src.startsWith(pat.close, j)) { end = j; break; }
        j++;
      }
      if (end === -1) continue;
      store.push({
        kind: "math",
        text: pat.open + src.slice(from, end) + pat.close,
        display: pat.display
      });
      out += SENT_OPEN + (store.length - 1) + SENT_CLOSE;
      i = end + pat.close.length;
      matched = true;
      break;
    }
    if (matched) continue;

    out += ch;
    i++;
  }
  return out;
}

function restore(html, store) {
  return html.replace(SENT_RE, function (_, n) {
    var item = store[+n];
    if (!item) return "";
    if (item.kind === "code") return "<code>" + escapeHtml(item.text) + "</code>";
    if (item.kind === "fence") return renderFence(item.text);
    /* math: escaped text, KaTeX walks the text node and replaces it */
    var span = item.display ? "div" : "span";
    return "<" + span + ' class="math-raw">' + escapeHtml(item.text) + "</" + span + ">";
  });
}

/* A CODE FENCE KEEPS ITS INFO STRING. "```py board/x.py#L40-58" is Python,
   highlighted (`codeview.js`, highlight.js in web/vendor/highlight/), numbered
   from 40, under a caption linking the read-only source viewer at that range.
   A path with no language takes one from its extension. Math and TikZ fences
   are left as they were: TikZ never gets here (the server compiles it), and a
   math fence is plain preformatted text. */
var PLAIN_FENCE = /^(math|tikz|tikzcd|latex)$/i;

function renderFence(text) {
  var info = (/^```([^\n]*)/.exec(text) || ["", ""])[1].trim();
  var body = text.replace(/^```[^\n]*\n?/, "").replace(/\n?```\s*$/, "");
  var words = info ? info.split(/\s+/) : [];
  var CV = window.CodeView;
  if (!words.length || PLAIN_FENCE.test(words[0]) || !CV) {
    return "<pre><code>" + escapeHtml(body) + "</code></pre>";
  }
  var lang = "", at = null;
  words.forEach(function (w, n) {
    var r = CV.ref(w);
    if (r && !at) at = r;
    else if (!r && n === 0) lang = w;
  });
  lang = CV.language(lang) || CV.language(at ? CV.fromPath(at.path) : "");
  var cls = lang ? ' class="hljs language-' + CV.esc(lang) + '"' : "";
  if (!at) {
    return '<pre class="code"><code' + cls + ">" + CV.body(body, lang) + "</code></pre>";
  }
  var label = at.path + (at.from ? "#L" + at.from + (at.to > at.from ? "-" + at.to : "") : "");
  var href = BASE + "/source/" + at.path.split("/").map(encodeURIComponent).join("/")
    + (at.from ? "?from=" + at.from + "&to=" + at.to : "");
  return '<figure class="code-fence"><figcaption><a class="code-ref" href="'
    + CV.esc(href) + '" target="_blank" rel="noopener"><code>' + CV.esc(label)
    + "</code></a></figcaption>"
    + '<pre class="code numbered"><code' + cls + ">"
    + CV.body(body, lang, at.from || 1) + "</code></pre></figure>";
}

function inline(s) {
  return s
    /* `card-img` is what fits it to the card. A result figure is a 300-dpi PNG
       two thousand pixels wide, and an <img> with no rule on it is drawn at that
       size, so a graph put on the board ran off the glass. */
    .replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, function (all, alt, src) {
      return '<img class="card-img" alt="' + alt + '" src="' + mdUrl(src) + '">';
    })
    /* AN ADDRESS STAYS IN THIS PAGE. Every other link is the web, and the web
       opens in its own tab so that a tap on a citation is not the lesson
       leaving the glass. An address is the opposite thing: it is this board
       being asked to go somewhere, and a second tab is a second board. */
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, function (all, text, href) {
      href = mdUrl(href);
      return href.indexOf("#/") === 0
        ? '<a href="' + href + '">' + text + "</a>"
        : '<a href="' + href + '" target="_blank" rel="noopener">' + text + "</a>";
    })
    .replace(/\*\*\*([^*]+)\*\*\*/g, "<strong><em>$1</em></strong>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[\s(])\*([^*\n]+)\*(?=$|[\s.,;:)!?])/g, "$1<em>$2</em>")
    .replace(/(^|[\s(])_([^_\n]+)_(?=$|[\s.,;:)!?])/g, "$1<em>$2</em>")
    .replace(/~~([^~]+)~~/g, "<del>$1</del>");
}

function splitRow(line) {
  return line.replace(/^\s*\|?/, "").replace(/\|?\s*$/, "").split("|").map(function (c) {
    return c.trim();
  });
}

function renderMarkdown(src) {
  var store = [];
  var text = protect(src.replace(/\r\n/g, "\n"), store);
  /* Prose is escaped now that math and code are safely parked in the store.
     `>` is deliberately left alone so blockquote lines still match. */
  text = text.replace(/&/g, "&amp;").replace(/</g, "&lt;");
  var lines = text.split("\n");
  var out = [];
  var i = 0;

  function isBlank(s) { return !s || !s.trim(); }

  while (i < lines.length) {
    var line = lines[i];

    if (isBlank(line)) { i++; continue; }

    /* compiled figure placeholder */
    var fig = line.match(/^\s*@@FIGURE:([0-9a-f]+):(\w+)@@\s*$/);
    if (fig) {
      var id = fig[1], status = fig[2];
      if (status === "ready") {
        out.push('<div class="figure"><img alt="figure" src="' + BASE + '/figure/' + id + '.svg"></div>');
      } else if (status === "error") {
        out.push('<div class="figure error">figure ' + id + " failed to compile</div>");
      } else {
        out.push('<div class="figure pending" data-fig="' + id + '">compiling figure…</div>');
      }
      i++;
      continue;
    }

    /* heading */
    var h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) {
      var lvl = Math.min(h[1].length, 3);
      out.push("<h" + lvl + ">" + inline(h[2].trim()) + "</h" + lvl + ">");
      i++;
      continue;
    }

    /* horizontal rule */
    if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) { out.push("<hr>"); i++; continue; }

    /* table */
    if (line.indexOf("|") !== -1 && i + 1 < lines.length &&
        /^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$/.test(lines[i + 1]) && lines[i + 1].indexOf("-") !== -1) {
      var header = splitRow(line);
      var aligns = splitRow(lines[i + 1]).map(function (c) {
        if (/^:.*:$/.test(c)) return "center";
        if (/:$/.test(c)) return "right";
        return "left";
      });
      i += 2;
      var body = [];
      while (i < lines.length && lines[i].indexOf("|") !== -1 && !isBlank(lines[i])) {
        body.push(splitRow(lines[i]));
        i++;
      }
      var t = "<table><thead><tr>";
      header.forEach(function (c, n) {
        t += '<th style="text-align:' + (aligns[n] || "left") + '">' + inline(c) + "</th>";
      });
      t += "</tr></thead><tbody>";
      body.forEach(function (row) {
        t += "<tr>";
        row.forEach(function (c, n) {
          t += '<td style="text-align:' + (aligns[n] || "left") + '">' + inline(c) + "</td>";
        });
        t += "</tr>";
      });
      out.push(t + "</tbody></table>");
      continue;
    }

    /* blockquote */
    if (/^\s*>/.test(line)) {
      var quoted = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) {
        quoted.push(lines[i].replace(/^\s*>\s?/, ""));
        i++;
      }
      out.push("<blockquote><p>" +
               inline(quoted.join("\n").trim()).replace(/\n{2,}/g, "</p><p>").replace(/\n/g, " ") +
               "</p></blockquote>");
      continue;
    }

    /* list */
    var bullet = line.match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
    if (bullet) {
      var result = renderList(lines, i, store);
      out.push(result.html);
      i = result.next;
      continue;
    }

    /* paragraph */
    var para = [];
    while (i < lines.length && !isBlank(lines[i]) &&
           !/^(#{1,6})\s/.test(lines[i]) &&
           !/^\s*>/.test(lines[i]) &&
           !/^\s*([-*+]|\d+[.)])\s/.test(lines[i]) &&
           !/^\s*@@FIGURE:/.test(lines[i]) &&
           !/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(lines[i])) {
      para.push(lines[i]);
      i++;
    }
    /* A line no rule above took (a malformed placeholder) is text, never a
       line the loop stands on for ever. */
    if (!para.length) para.push(lines[i++]);
    out.push("<p>" + inline(para.join("\n").trim()).replace(/\n/g, " ") + "</p>");
  }

  return restore(out.join("\n"), store);
}

/* nested lists, by leading indent */
function renderList(lines, start, store) {
  var first = lines[start].match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
  var indent = first[1].length;
  var ordered = /\d/.test(first[2]);
  var items = [];
  var i = start;

  while (i < lines.length) {
    var m = lines[i].match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
    if (!m) {
      if (!lines[i].trim()) {
        /* a blank line only continues the list if an item follows */
        var look = i + 1;
        if (look < lines.length && /^\s*([-*+]|\d+[.)])\s/.test(lines[look]) &&
            lines[look].match(/^(\s*)/)[1].length >= indent) { i++; continue; }
      }
      if (lines[i].trim() && lines[i].match(/^(\s*)/)[1].length > indent) {
        items[items.length - 1].push(lines[i].trim());
        i++;
        continue;
      }
      break;
    }
    if (m[1].length < indent) break;
    if (m[1].length > indent) {
      var sub = renderList(lines, i, store);
      items[items.length - 1].push(SENT_NEST + sub.html);
      i = sub.next;
      continue;
    }
    items.push([m[3]]);
    i++;
  }

  var tag = ordered ? "ol" : "ul";
  var html = "<" + tag + ">";
  items.forEach(function (chunks) {
    var nested = "";
    var body = [];
    chunks.forEach(function (c) {
      if (c[0] === SENT_NEST) nested += c.slice(1);
      else body.push(c);
    });
    html += "<li>" + inline(body.join(" ")) + nested + "</li>";
  });
  return { html: html + "</" + tag + ">", next: i };
}

/* ------------------------------------------------------------------ KaTeX */

/* What the payload last said this course writes in, merged over the board's own
   table and rebuilt only when it changes -- `typeset` runs on every card and
   this must not be a fresh object each time. */
var boardMacros = null;
var courseMacrosRaw = null;

function setCourseMacros(got) {
  var next = JSON.stringify(got || {});
  if (next === courseMacrosRaw) return;
  courseMacrosRaw = next;
  boardMacros = null;
}

function courseMacros() {
  if (boardMacros) return boardMacros;
  boardMacros = {};
  var base = window.BOARD_MACROS || {};
  for (var k in base) if (base.hasOwnProperty(k)) boardMacros[k] = base[k];
  var mine = courseMacrosRaw ? JSON.parse(courseMacrosRaw) : {};
  for (var j in mine) if (mine.hasOwnProperty(j)) boardMacros[j] = mine[j];
  return boardMacros;
}

function typeset(root) {
  if (!window.renderMathInElement) return;
  try {
    window.renderMathInElement(root, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "\\[", right: "\\]", display: true },
        { left: "\\(", right: "\\)", display: false },
        { left: "$", right: "$", display: false }
      ],
      /* The board's vocabulary, with THIS COURSE'S OWN over the top. A course
         defines what it writes in and the board fills the gaps -- the same rule
         the TeX side has always had through `\providecommand`, which is the
         point: the two engines render the same source the same way. A course
         that redefines a board macro at a different arity is not a clash to
         resolve here, it is the course being right about its own notation. */
      macros: courseMacros(),
      throwOnError: false,
      errorColor: "#9a2020",
      strict: false,
      trust: katexTrust
    });
  } catch (e) { /* a bad formula must never blank the board */ }
}

/* WHAT A CARD'S MATH MAY REACH OUTSIDE ITSELF, and it is an allowlist. A card is
   text a model wrote, so KaTeX's trusted commands are judged one by one:
   `\href` and `\url` go to http, https or a relative URL and nowhere else (no
   `javascript:`, no `data:`); `\includegraphics` loads only from this origin;
   `\htmlId`, `\htmlClass`, `\htmlStyle`, `\htmlData` and any command KaTeX adds
   later are refused. KaTeX has already worked out `protocol` from the URL, as
   `_relative` where there is none, and refuses a URL it cannot read. */
function katexTrust(ctx) {
  var cmd = ctx && ctx.command;
  var protocol = ctx && ctx.protocol;
  if (cmd === "\\href" || cmd === "\\url") {
    return protocol === "http" || protocol === "https" || protocol === "_relative";
  }
  if (cmd === "\\includegraphics") return sameOrigin(ctx.url);
  return false;
}

/* Resolved against the page, so `//elsewhere/x.png` -- relative to KaTeX, and
   another host to a browser -- is caught. No page, no image. */
function sameOrigin(url) {
  var here = window.location;
  if (!here || !here.href || typeof URL !== "function") return false;
  try {
    return new URL(String(url || ""), here.href).origin === here.origin;
  } catch (e) { return false; }
}

/* A SLUG IS NOT A TITLE. `board write` names the file from the title, so a
   title that is a file stem is not drawn: it stays in the front matter and
   names the file, and a `lesson` card's head goes with it. A stem is no
   whitespace, all lower case, and three or more parts joined by hyphens or
   underscores; `Well-ordering` and `mean-square` are titles. */
function cardTitle(c) {
  var said = ((c && c.title) || "").trim();
  if (!said || /\s/.test(said)) return said;
  if (said !== said.toLowerCase()) return said;
  return said.split(/[-_]+/).length >= 3 ? "" : said;
}

/* ------------------------------------------------- what the board just did */
/* A RENDERING FAULT IS OVER BEFORE ANYBODY CAN DESCRIBE IT, so the board keeps
   its own last few hundred moves and `⋯ → what just happened` reads them back
   on the device, with a copy button. It costs one small object pushed onto a
   bounded array; nothing is formatted or measured until the panel opens, and
   the uninteresting renders (a heartbeat, a count) are not recorded. */
var TRACE_MAX = 300;
var traceLog = [];
var traceFrom = 0;

function trace(what, of) {
  var now = Date.now();
  if (!traceFrom) traceFrom = now;
  traceLog.push({ at: now - traceFrom, what: what, of: of || null });
  if (traceLog.length > TRACE_MAX) traceLog.shift();
}

/* AND THE INK LAYER WRITES INTO THE SAME LOG: its worst fault, a stroke whose
   lift never arrived, refuses every scroll (`STROKE_QUIET` in `annotate.js`).
   Exposed rather than passed in, because that file loads first. */
window.BoardTrace = trace;

/* AND WHICH SHELL IS RUNNING. `board.js` is in `sw.js`'s `SHELL`, so an
   installed app serves its cached copy until `VERSION` moves. It is read from
   the running page, never the server: a server on new code serving an old
   shell is the case being diagnosed. The cache's name IS `VERSION`, and every
   shell cache present is named. */
var shellVersion = "shell unknown";

function askShell() {
  try {
    if (!window.caches || !window.caches.keys) return;
    window.caches.keys().then(function (keys) {
      var mine = (keys || []).filter(function (k) {
        return /^board-shell-/.test(String(k));
      });
      if (mine.length) shellVersion = mine.join(" + ");
    }, function () { /* no answer: unknown, and saying so is the honest line */ });
  } catch (e) { /* no cache storage at all: a browser tab, not the app */ }
}
askShell();

/* Reduce Motion is not consulted by `typeOut` any more, and the next fault
   reported from a device that has it on will still want to know that it does. */
function shellHead() {
  var still = "?";
  try {
    still = (window.matchMedia
             && window.matchMedia("(prefers-reduced-motion: reduce)").matches)
      ? "yes" : "no";
  } catch (e) { /* no matchMedia */ }
  return shellVersion + "  ·  reduce motion: " + still;
}

/* What a copied trace opens with: the shell, then the code behind it. */
function traceHead() {
  return shellHead() + (codeLine ? "  ·  " + codeLine : "");
}

/* WHICH CODE THE BOARD IS RUNNING, and whether the tree has moved past it.
   The other half of the shell line: a board and a tutor read their code once,
   when they start, so a ship reaches the glass only when its node's watch
   restarts them. Asked when the panel opens, and never on the plain `/health`
   poll, because the tree's stamp is a git call. */
var codeLine = "";
var codeStale = false;

function askCode() {
  return api("/health?code=1", { cache: "no-store" }).then(function (r) {
    if (r && r.ok === false) throw new Error("HTTP " + r.status);
    return r.json();
  }).then(function (h) {
    var c = (h && h.code) || {};
    if (!c.running) {
      codeLine = "board code: from before stamps";
      codeStale = true;
    } else {
      codeLine = "board code " + c.running + " · tutor code "
        + (c.tutor || "?") + " · tree " + (c.tree || "?");
      codeStale = !!(c.tree && c.running !== c.tree);
      if (codeStale) {
        codeLine += " -- older than the tree; its node's watch restarts it "
          + "within a beat";
      }
    }
    paintCode();
  }, function () {
    /* NO ANSWER IS AN ANSWER. The shell comes off disk, so a new one often
       runs against an old server, and a server that cannot answer this at
       all is the most stale board there is -- it must not look unknown. */
    codeLine = "board code: unknown -- /health?code=1 did not answer; the "
      + "board is older than this shell or unreachable";
    codeStale = true;
    paintCode();
  });
}

function paintCode() {
  var el = document.getElementById("trace-code");
  if (!el) return;
  el.textContent = codeLine;
  el.classList.toggle("stale", codeStale);
}

/* ------------------------------------------------------------------ render */
var KIND_LABEL = {
  lesson: "lesson",
  question: "your move",
  correct: "correct",
  wrong: "not quite",
  review: "review",
  note: "aside",
  recap: "recap",
  /* A doing turn's placeholder, and what replaces it when the turn ended
     without writing its report over it. */
  pending: "working",
  stopped: "stopped without a report"
};

/* Which kinds are a reply to a piece of working, as opposed to new teaching.
   `note` is one: it answers what the student just wrote. A `lesson` or a
   `recap` stands on its own and is never folded. */
var REPLY_KIND = { wrong: 1, correct: 1, review: 1, note: 1 };

/* What a reply says about the answer it replied to. Two kinds are a verdict;
   everything else that answers working is "open", which is the amber default
   -- see where `verdictOf` is built. */
var VERDICT_OF = { correct: "correct", wrong: "wrong" };

/* AND THE KIND IS NOT WHAT DECIDES WHETHER A CARD IS REPLYING. `REPLY_KIND`
   is the folding rule; a band turns on whether the card replies to work that
   was handed in, which the transcript answers (`cardVerdict`). `recap` is the
   one kind that is never a reply. */
var NEVER_REPLY = { recap: 1 };

/* The verdict on each question, by card id, as of the last render. Read by
   `paintBoards`, which runs after the transcript is built and paints the same
   answer's board with the same colour. */
var lastVerdicts = Object.create(null);

function timeLabel(t) {
  var d = new Date(t * 1000);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}


/* Nodes inserted by the last reconcile, so only they get typeset. */
var freshNodes = [];

/* Keyed, and **in place**. A node that is already where it belongs is not
   touched -- not moved, not re-appended. Re-inserting a node restarts its CSS
   animations and forces style, layout and paint for the whole lesson, and
   payloads arrive while nothing on screen has changed. */

/* WHERE A CARD AT THE END OF THE LESSON GOES: ABOVE THE WRITING SURFACE, NEVER
   BELOW IT. The surface has no key and is the lesson's last child; a card
   appended past it types out under a full-height board, off the glass. A
   reply belongs above the board you would answer it on, where it is read. */
function tailAnchor(host) {
  var n = host.lastChild, anchor = null;
  while (n && !(n.dataset && n.dataset.key)) { anchor = n; n = n.previousSibling; }
  return anchor;
}

function reconcile(host, wanted) {
  var have = Object.create(null);
  var i, node, key;

  for (i = 0; i < host.childNodes.length; i++) {
    node = host.childNodes[i];
    key = node.dataset && node.dataset.key;
    if (key) have[key] = node;
  }

  var cursor = host.firstChild;
  for (i = 0; i < wanted.length; i++) {
    /* Either a node just built, or a key saying "the one already on screen is
       still right". */
    key = wanted[i].key;
    node = wanted[i].node;
    var kept = have[key];
    /* The writing surface lives among these nodes and has no key of its own;
       `placeWriter` owns where it sits, so step over it rather than matching
       against it. */
    while (cursor && !(cursor.dataset && cursor.dataset.key)) {
      cursor = cursor.nextSibling;
    }
    /* Past the last keyed node there may be nothing but the surface, and a card
       goes in front of it rather than after it -- see `tailAnchor`. */
    var at = cursor || tailAnchor(host);
    if (kept) {
      delete have[key];
      if (kept === cursor) {
        cursor = cursor.nextSibling;      /* already in place: leave it alone */
        continue;
      }
      host.insertBefore(kept, at);
    } else if (node) {
      host.insertBefore(node, at);
      freshNodes.push(node);
    }
  }

  /* Anything left in `have` is a node the payload no longer contains. */
  for (key in have) {
    if (have[key].parentNode === host) host.removeChild(have[key]);
  }
}

function render(data) {
  /* Any settle still running belongs to a card this payload supersedes. */
  settleEnd(false);
  /* A live frame that arrives while a past lesson is open is kept, not shown.
     Being yanked out of what you are reading because the tutor wrote something
     is worse than finding it when you come back. */
  if (!data.archived) {
    lastLive = data;
    if (!pagesLoaded) { pagesLoaded = true; loadPages(); }
    document.getElementById("btn-history").hidden = !(data.history > 0);
    if (reading) { els.jump.hidden = false; return; }
  }
  var state = data.state || {};

  /* WHICH TRANSCRIPT IS ON SCREEN, AND THE MARKS THAT BELONG TO IT. The
     annotation store is keyed by card number, and `0001` names a different card
     in a past lesson -- so the store is dropped at the boundary. The live one is
     named by its stamp and label; a past one by the archive's own id. */
  var sitting = data.archived
    ? "past:" + (reading || "")
    : "live:" + (state.opened || "") + "|" + (state.chapter || "");
  if (sittingKey !== null && sitting !== sittingKey && window.Annotate) {
    window.Annotate.forget();
  }
  sittingKey = sitting;

  paintHeader(state);
  /* A review's label is "Test review — Ch 1, Ch 7", which the strip underneath
     already says in full and in the course's own words. Repeating it here costs
     the bar the width that the chapter line exists to have, and the bar is the
     one row on this page that cannot grow. The label still goes into the state,
     because a filed lesson needs a name in the history. */
  var reviewing = (state.session || "") === "review";
  els.chapter.textContent = (state.chapter && !reviewing) ? "· " + state.chapter : "";
  document.title = (state.course || "Board") + (state.chapter ? " · " + state.chapter : "");

  /* The lesson is one transcript: the tutor's cards and the student's answers
     in the order they happened, the answer directly under the question it
     answers. A revised answer keeps its original place -- it supersedes what
     was there rather than being appended to the end -- which is why the sort
     runs on when the turn STARTED, not when it was last edited. */
  /* Order by position in the lesson, not by clock. Cards are numbered in the
     order they were written, and that number is what fixes their place: sorting
     them by mtime meant that correcting a typo in card three moved it to the end
     of the transcript, after everything the student had since answered. A turn
     sits immediately after the card it answers; a turn that answers nothing --
     the opening "begin" -- falls back to where its time puts it. */
  var ordered = (data.cards || []).slice().sort(function (a, b) {
    return (a.id || "").localeCompare(b.id || "");
  });
  var at = Object.create(null);
  /* A CARD THE STUDENT HAS ANSWERED IS A QUESTION, WHATEVER IT CALLED ITSELF.
     Everything the answer block is made of hangs off a question's id: its
     board, its page, where the surface sits, whether a sent answer is a live
     board. A tutor that asks at the foot of a `lesson` card has asked, so the
     student's own answers (the turns, on disk) are the second and stronger
     authority, and a card with one answer keeps its boards for good. */
  var isQuestion = Object.create(null);
  ordered.forEach(function (c, n) {
    at[c.id] = n;
    if (c.kind === "question") isQuestion[c.id] = true;
  });
  /* AND A TURN THAT NAMES NOTHING IS ADOPTED BY THE CARD IT WAS WRITTEN UNDER:
     the last card written before the page was sent, both halves of which are on
     disk. A turn about nothing could be given no board. Ink only: "begin" and a
     direction change are about the session and fall where their time puts them. */
  var written = ordered.filter(function (c) { return typeof c.mtime === "number"; });
  (data.turns || []).forEach(function (t) {
    if (t.answers || t.kind !== "ink") return;
    var anchor = null;
    written.forEach(function (c) { if (c.mtime <= t.t) anchor = c.id; });
    if (anchor) t.answers = anchor;
  });
  (data.turns || []).forEach(function (t) {
    if (t.answers && at[t.answers] !== undefined) isQuestion[t.answers] = true;
  });
  /* And the one a board was asked for on, which has no answer against it yet --
     that first send is exactly the moment there is nothing to go on. */
  if (reopenedFor && at[reopenedFor] !== undefined) isQuestion[reopenedFor] = true;
  /* A filed lesson and a past one are read-only: no surface is built for either,
     so the frozen picture is the only record there is and it stays. */
  var live = !data.archived && !reading;

  /* ------------------------------------------- one step, handed over */
  /* THE WAY OUT OF ONE STEP OF COACHING, WITHOUT LEAVING IT: "you do this step".
     On the newest card only, because that is the step. `/handover` names the
     card and leaves the session as it is (`_handover` in `routes/lesson.py`). */
  var coaching = live && (state.aim_now || state.aim || "") === "coach";
  var thisStep = ordered.length ? ordered[ordered.length - 1].id : "";

  /* Whether a written answer already has a board carrying the same ink. Every
     question owns a page and nothing is wiped, so the frozen picture and the
     board are two copies of the same ink, and the board is the answer. The
     picture comes back when there is no board to replace it: a filed or past
     lesson, a browser that never held the page, a surface not built yet. */
  function onABoard(m) {
    if (!(live && !!writer && m.kind === "ink" && !!m.png
          && !!m.answers && !!isQuestion[m.answers])) return false;
    var found = false;
    slotsOf(m.answers).forEach(function (k) {
      if (boardPage[k].p !== undefined) found = true;
    });
    return found;
  }

  /* Feedback supersedes feedback. Only the newest revision of an answer is
     rendered, so only the newest reply to the open question stays open; the
     replies it replaced fold to their heading and open again on a tap. */
  var superseded = Object.create(null);
  /* Per question, not merely after the newest one. A question stays open for as
     long as it takes -- one exercise ran to eleven cards and two hours -- and
     the rule was "replies after the NEWEST question card", so for all of that
     time there was no newest question after them and nothing folded at all. A
     reply belongs to the question it follows, and it is superseded by the next
     reply to that same question. */
  var runs = [];
  ordered.forEach(function (c, n) {
    if (c.kind === "question" || !runs.length) runs.push([]);
    if (REPLY_KIND[c.kind]) runs[runs.length - 1].push(c.id);
  });
  runs.forEach(function (run) {
    run.slice(0, -1).forEach(function (id) { superseded[id] = true; });
  });

  /* AND THE NEWEST REPLY IN A QUESTION'S RUN IS THE VERDICT ON WHAT THEY SENT:
     green if right, red if wrong, amber (`--ask`) when it is neither -- amber is
     the default, not a third case. An unanswered turn carries no verdict; the
     pulsing strip says the tutor is reading it. The walk is `runEndOf`'s and
     uses `isQuestion`, not `kind === "question"`. */
  /* AND THE SAME WALK PAINTS THE CARD. The response carries the band; the
     answer and its board keep a thinner rule in the same colour
     (`.mine[data-verdict]`, `.board[data-verdict]`). Which card is a reply is
     about the transcript, not the kind: the first card written after the answer.
     A `correct` or `wrong` carries its verdict wherever it falls. */
  var answeredAt = Object.create(null);
  (data.turns || []).forEach(function (t) {
    if (t.signal || !t.answers) return;
    (answeredAt[t.answers] = answeredAt[t.answers] || []).push(t.t0 || t.t);
  });

  var verdictOf = Object.create(null);
  /* Per CARD, and read where the card is built. */
  var cardVerdict = Object.create(null);
  /* And how many right in a row this one is, which is the reward -- see
     `streakAt` where the head is assembled. */
  var streakAt = Object.create(null);
  var verdictFor = null;
  var sinceCard = -Infinity;      /* the last card in this question's run */
  var streak = 0;
  ordered.forEach(function (c) {
    if (isQuestion[c.id]) { verdictFor = c.id; sinceCard = c.mtime; return; }
    var replying = !NEVER_REPLY[c.kind] && verdictFor !== null
      && typeof c.mtime === "number"
      && (answeredAt[verdictFor] || []).some(function (t) {
        return t > sinceCard && t <= c.mtime;
      });
    sinceCard = c.mtime;
    var says = VERDICT_OF[c.kind] || (replying ? "open" : "");
    if (!says) return;
    cardVerdict[c.id] = says;
    /* THE RUN IS THE REWARD: consecutive correct answers are counted. Reset by a
       wrong answer and nothing else -- not an aside, a question or teaching in
       between -- so thinking out loud is never punished. */
    if (says === "correct") streakAt[c.id] = ++streak;
    else if (says === "wrong") streak = 0;
    if (verdictFor && (replying || REPLY_KIND[c.kind])) verdictOf[verdictFor] = says;
  });
  lastVerdicts = verdictOf;

  /* Every typed answer a question has, in order, so the second one can say
     which it is. The boards say "attempt 2 of 3" for a second page of ink and
     the words are owed the same, for the same reason: a question that stays
     open for an evening collects several answers, and three bubbles in a row
     under one card are otherwise three unlabelled things. */
  var typedOn = Object.create(null);
  (data.turns || []).forEach(function (t) {
    if (t.kind !== "text" || t.signal || !t.answers) return;
    (typedOn[t.answers] = typedOn[t.answers] || []).push(t.id);
  });

  var items = [];
  ordered.forEach(function (c, n) {
    items.push({ pos: n, sub: 0, t: c.mtime, key: "card:" + c.id, card: c });
  });
  (data.turns || []).forEach(function (t) {
    var when = t.t0 || t.t;
    var pos = -1;
    ordered.forEach(function (c, n) { if (c.mtime <= when) pos = n; });
    if (t.answers && at[t.answers] !== undefined) {
      /* Under the card it answers -- BUT NEVER ABOVE A CARD WRITTEN BEFORE IT. A
         question collects answers over an evening; where the two rules disagree the
         clock is right. Ink's board is placed by `paintBoards`, so this moves only
         a one-line receipt. */
      pos = t.kind === "text" ? Math.max(pos, at[t.answers]) : at[t.answers];
    }
    items.push({ pos: pos, sub: 1, t: when, key: "turn:" + t.id, turn: t });
  });
  items.sort(function (a, b) {
    return (a.pos - b.pos) || (a.sub - b.sub) || (a.t - b.t);
  });

  /* TWO QUESTIONS, AND ONLY THE SECOND IS ABOUT THE KIND OF ANSWER. Is an answer
     outstanding: yes, typed or written (a signal is not one). Is it rendered into
     the transcript: not a sent, unanswered page of ink, which is still on the
     surface directly below; it takes its place when the tutor replies. A typed
     answer is duplicated nowhere, so it stays. */
  awaitingReply = null;
  var lastItem = items[items.length - 1];
  if (lastItem && lastItem.turn && !lastItem.turn.signal) {
    awaitingReply = lastItem.turn;
    if (lastItem.turn.kind !== "text") items.pop();
  }
  /* AND IT IS STILL OUTSTANDING WHILE THE REPLY IS ARRIVING (`replyArriving`):
     `awaitingReply` goes when the card's RECORD lands, before a word is on the
     glass. Held only against a card; a signal tap of theirs on top ends it. */
  /* A REPLY IS LANDING ON THIS FRAME -- something of theirs was outstanding when
     the last one was drawn, and it is not any more. That has to be remembered
     ACROSS payloads, because the card that answers a send arrives in the very
     payload that clears the send: asking `replyArriving()` here would ask
     whether anything is typing, and nothing is -- `typeOut` does not run until a
     hundred lines below this. */
  /* A reply is a CARD. Anything of theirs arriving on top -- a signal tap, which
     is a turn and is never a receipt -- means the answer the receipt was about
     is no longer the newest thing they did, and nothing is landing. */
  replyLanding = !awaitingReply && !!wasAwaiting && !(lastItem && lastItem.turn);
  if (awaitingReply) heldReply = awaitingReply;
  else if (replyLanding) heldReply = wasAwaiting;
  else if (!replyArriving() || (lastItem && lastItem.turn)) heldReply = null;
  wasAwaiting = awaitingReply;

  /* Where the reader is, before the lesson is rebuilt around them. Put back at
     the foot of this function unless something down there has a better idea
     about where the page should be. */
  /* Recorded per payload, because whether the reply had landed on THIS one is
     the fact every hold decision downstream turns on. */
  if (replyLanding) {
    trace("reply", { cards: (data.cards || []).length,
                     owed: awaitingReply ? 1 : 0,
                     agent: (data.agent && data.agent.state) || "-" });
  }
  var place = firstPaint ? null : anchorNow();
  /* What is on screen already, by key. Most payloads change nothing in the
     lesson, so only what is genuinely new is parsed and built. */
  var onScreen = Object.create(null);
  for (var ex = 0; ex < els.cards.childNodes.length; ex++) {
    var exNode = els.cards.childNodes[ex];
    var exKey = exNode.dataset && exNode.dataset.key;
    if (exKey) onScreen[exKey] = true;
  }
  var wanted = [];
  var anythingNew = false;
  var freshCards = [];

  items.forEach(function (item) {
    /* A CARD WRITTEN OVER IS A CARD ARRIVING. A doing turn lands one sentence and
       later replaces it with the report (`board write --over`). The mtime is a
       card's version, as `rev` is a turn's, so the overwrite is fresh: it types
       out, `anythingNew` is true, and `typingCards` holds the surface until the
       last character lands. */
    var stamp = item.key + (item.turn ? ":r" + (item.turn.rev || 1)
                                      : ":m" + Math.round(item.card.mtime));
    var fresh = !firstPaint && !seenIds[stamp];
    /* NEWS IS A CARD. YOUR OWN ANSWER IS NOT NEWS. `anythingNew` leads only to
       `revealNewest`, the top of the tutor's newest card, which sits above the
       writing surface; counting a fresh turn would throw the page up the moment
       your own answer appears. A turn's own landing is `revealSent`. */
    if (fresh && item.card) anythingNew = true;
    seenIds[stamp] = true;

    /* The key is identity plus version: a card edited in place, or a turn
       revised, changes its key and is rebuilt; everything else is reused.
       Whether the answer is showing as a picture or standing aside for its board
       is part of that identity -- the surface is built a frame after the first
       payment, and without this the turn keeps the picture it was born with. */
    var onBoard = !!item.turn && onABoard(item.turn);
    /* The verdict is part of the turn's identity too: it is written by a card
       that arrives minutes after the turn did, and a node kept because its key
       had not changed would keep the colour it was born with -- which is no
       colour at all, for ever. */
    var says = (item.turn && item.turn.answers)
      ? (verdictOf[item.turn.answers] || "") : "";
    /* Which typed answer of how many, and it is in the key because the "of" end
       of it changes when the NEXT one is sent -- on a node that would otherwise
       be kept exactly as it is. */
    var oneOf = (item.turn && item.turn.kind === "text" && item.turn.answers)
      ? (typedOn[item.turn.answers] || []) : [];
    var nth = oneOf.length > 1 ? oneOf.indexOf(item.turn.id) + 1 : 0;
    /* Whether this card is the step on offer is part of its identity too, for
       the same reason the verdict is part of a turn's: the aim can change under
       a card nothing else touched, and a node kept because its key had not
       moved would keep a button the sitting no longer offers -- or go on
       lacking one it now does. */
    var offer = !!item.card && coaching && item.card.id === thisStep;
    /* The card's own verdict and its place in a run, in its key for the reason
       the turn's verdict is in its: both are written by something that arrives
       after the card did -- the answer that makes it a reply, the next right
       answer that makes it one of four -- and a node kept because its key had
       not moved would keep the band and the count it was born with. */
    var band = item.card ? (cardVerdict[item.card.id] || "") : "";
    var run = item.card ? (streakAt[item.card.id] || 0) : 0;
    var wantKey = stamp + (item.card
      ? (offer ? ":h" : "") + (band ? ":v" + band : "")
        + (run > 1 ? ":s" + run : "")
      : (onBoard ? ":b" : "") + (says ? ":v" + says : "")
        + (nth ? ":n" + nth + "/" + oneOf.length : ""));
    if (onScreen[wantKey]) {
      wanted.push({ key: wantKey, node: null });     /* keep what is there */
      return;
    }
    var node = document.createElement(item.card ? "article" : "div");
    node.dataset.key = wantKey;
    if (item.card) {
      var c = item.card;
      if (fresh) freshCards.push(node);
      node.className = "card" + (fresh ? " fresh" : "");
      node.dataset.kind = c.kind;
      node.dataset.card = c.id;      /* what an annotation is anchored to */
      if (band) node.dataset.verdict = band;
      if (run > 1) node.dataset.streak = run;
      var head = "";
      var shown = cardTitle(c);
      /* AND A CARD CARRYING A VERDICT ALWAYS HAS A HEAD, because the head is
         where the mark is. A titleless `lesson` card had no head at all, so a
         lesson card that is a reply would have had the colour and nothing else
         -- and colour is never the only signal here: the tick, the cross and
         the question mark are TEXT, they scale with the type, they survive the
         card being folded to its heading, and they are the whole of what this
         says to somebody who cannot tell the green from the red. */
      /* AND THE FALLBACK THAT WROTE IT, when the provider could not: `by` is
         stamped by `board write` on a turn `recipes.resolve` handed over. */
      if (c.kind !== "lesson" || shown || band || c.by) {
        head = '<div class="card-head">' +
               '<span class="kind">' + (KIND_LABEL[c.kind] || c.kind) + "</span>" +
               (run > 1 ? '<span class="streak">' + run + ' in a row</span>' : "") +
               (shown ? '<span class="card-title"></span>' : "") +
               (c.by ? '<span class="card-by"></span>' : "") +
               '<span class="card-num">' + c.id + "</span></div>";
      }
      node.innerHTML = head + '<div class="body"></div>';
      if (shown) node.querySelector(".card-title").textContent = shown;
      if (c.by) node.querySelector(".card-by").textContent = "by " + c.by;
      node.querySelector(".body").innerHTML = renderMarkdown(c.body || "");
      if (offer) {
        var over = document.createElement("button");
        over.type = "button";
        over.className = "hand-over";
        over.textContent = "you do this step";
        over.addEventListener("click", function () { handOver(c.id, over); });
        node.appendChild(over);
      }
    } else {
      var m = item.turn;
      node.className = "mine" + (fresh ? " fresh" : "");
      node.dataset.turn = m.id;
      if (m.answers) node.dataset.answers = m.answers;
      if (says) node.dataset.verdict = says;
      node.innerHTML = '<span class="when"></span><span class="text"></span>';
      var when = "you · " + timeLabel(m.t);
      if (m.kind === "annotation") {
        when += " · wrote on card " + (m.answers || "?");
        if (m.where) when += " " + m.where;
      }
      if (nth) when += " · answer " + nth + " of " + oneOf.length;
      if ((m.rev || 1) > 1) when += " · revised";
      node.querySelector(".when").textContent = when;
      if (m.signal) {
        var chip = document.createElement("span");
        chip.className = "signal";
        chip.dataset.signal = m.signal;
        chip.textContent = SIGNAL_LABEL[m.signal] || m.signal;
        node.querySelector(".when").after(chip);
      }
      node.querySelector(".text").innerHTML = renderMarkdown(m.text || "");
      if (m.png && onBoard) {
        /* The working is on the board under this question's run -- below the
           feedback, which is where a correction wants it. One line here, so the
           transcript still says an answer was sent and when, and a tap goes to
           it rather than making anyone hunt. */
        var toBoard = document.createElement("button");
        toBoard.type = "button";
        toBoard.className = "to-board";
        toBoard.textContent = "on the board below ↓";
        toBoard.addEventListener("click", function () { showBoardFor(m.answers); });
        node.appendChild(toBoard);
      } else if (m.png) {
        /* Frozen at the moment it was sent, so it is what was handed in and
           not whatever the slate says now. The revision is in the URL, so
           there is nothing stale for the browser to hold on to. */
        var shotWrap = document.createElement("a");
        shotWrap.href = atSession(m.png);
        shotWrap.className = "slate-shot";
        shotWrap.addEventListener("click", function (e) {
          e.preventDefault();
          openViewer(m.png, "your answer · " + (m.iso || ""));
        });
        var shot = document.createElement("img");
        shot.src = atSession(m.png);
        shot.loading = "lazy";
        shot.alt = "what you wrote";
        /* It has a width and no height, so until it decodes it occupies nothing
           and then suddenly occupies a screenful. If that happens above the
           reader it takes the page down with it, which is the other half of
           "after I submit a response it scrolls me up above the last board". */
        var shotWas = 0;
        shot.addEventListener("load", function () {
          shotWas = holdBelow(shotWrap, shotWas);
        });
        shotWrap.appendChild(shot);
        node.appendChild(shotWrap);
      }
      if (m.files && m.files.length) {
        var box = document.createElement("div");
        box.className = "files";
        node.appendChild(box);
        m.files.forEach(function (f) {
          var a = document.createElement("a");
          a.href = BASE + "/uploads/" + encodeURIComponent(f);
          a.target = "_blank";
          a.rel = "noopener";
          if (/\.(png|jpe?g|gif|webp|heic)$/i.test(f)) {
            var img = document.createElement("img");
            img.src = a.href;
            a.appendChild(img);
          } else {
            a.textContent = f;
          }
          box.appendChild(a);
        });
      }
    }
    wanted.push({ key: wantKey, node: node });
  });

  /* Reconcile rather than rebuild: nodes are keyed by card id and revision, so
     an unchanged card is left exactly where it is, with its typesetting, scroll
     position and selection. */
  reconcile(els.cards, wanted);
  paintSuperseded(superseded);

  /* KaTeX walks the DOM it is handed. Handing it the whole lesson every frame
     re-renders mathematics that was already rendered; hand it only what was
     just inserted. */
  freshNodes.forEach(typeset);
  freshNodes.length = 0;
  /* After the typesetting, never before: KaTeX measures what it renders, and it
     cannot measure what is display:none. And before `placeWriter`, which asks
     `typingCards()` to decide whether to hold the surface: on the frame the
     response lands, the card must already be typing. */
  if (freshCards.length) {
    trace("fresh", { cards: freshCards.map(function (c) {
      return (c.dataset && c.dataset.card) || "?"; }).join(","),
      first: firstPaint ? 1 : 0 });
  }
  if (!firstPaint) freshCards.forEach(typeOut);
  freshCards.length = 0;

  /* The way out stays open until the tutor has actually said something. Keyed on
     CARDS, not on the transcript: asking makes the transcript non-empty, so
     keying on that retired the only control on the page the moment it was used
     -- and if nothing was listening, there was no way to ask again and no text
     box in maths to ask with. A board the tutor has never written on is still a
     board waiting to start. */
  var started = (data.cards || []).length > 0;
  els.empty.hidden = started || linkDead;

  /* THE CLUSTER'S HEALTH, the same for every session: relay looks down, not
     synced, a skipped pass (`relay.health`). */
  if (data.relay !== undefined) paintHealth(data.relay);

  /* WHAT THIS COURSE WRITES IN. Before anything is typeset below, because a
     card rendered against the wrong vocabulary is the defect this carries:
     `\E[...]` drawn as its own source, and `\EE{X}` drawn at the board's arity
     as a bare E with the brackets gone. Both engines take the course's own
     definition first now. See `tutorboard/coursemacros.py`. */
  if (data.macros !== undefined) setCourseMacros(data.macros);

  /* WHICH OF THE SESSION'S OWN DOCUMENTS EXIST: what the banner's buttons
     are enabled from, and what `warmPaper`, `inHand` and `saveCopy` read. */
  papers = data.papers || {};
  paintSession(state, data.push, data.agent, data.export,
               (data.hw && data.hw.build) || null);
  paintHomework(data.hw);
  if (!started) paintWaiting(data);
  seedTextDrafts(data);
  paintNotesSend();
  paintSent();
  /* The save count, results and jobs are the subject's, and arrive from
     `/subject.json` rather than on this frame; a frame that still carries
     one (a past lesson, a test) is honoured. */
  if (data.unsaved !== undefined) paintSave(data.unsaved);
  paintOlder();
  /* THE LESSON WAS FILED WHILE THIS PAGE WAS OPEN: `history` rose. Only when the
     field is there (a frame built by hand has none, and a missing field is not
     zero), and never off an archived frame. What goes, goes in both halves: the
     pages the archive renamed away, and the board-to-page mapping. */
  if (typeof data.history === "number" && !data.archived) {
    if (pastCount !== null && data.history > pastCount) lessonWasFiled();
    pastCount = data.history;
  }
  land();

  var lastQuestion = 0, lastSent = 0, newestQ = null;
  (data.cards || []).forEach(function (c) {
    if (isQuestion[c.id] && c.mtime > lastQuestion) {
      lastQuestion = c.mtime;
      newestQ = c.id;
    }
  });
  (data.turns || []).forEach(function (m) { if (m.t > lastSent) lastSent = m.t; });
  var settled = false;
  (data.cards || []).forEach(function (c) {
    if (c.kind === "correct" && c.mtime >= lastQuestion) settled = true;
  });
  var owed = !!newestQ && !settled;

  lastNewestQ = newestQ || "";
  /* And the newest card of any kind, which is what "write on the board" anchors
     to when the tutor has asked nothing: the student is answering the thing they
     have just read, and a turn that names it can be revised, kept and come back
     to. A turn that names nothing is a picture. */
  lastNewestCard = "";
  var newestAt = 0;
  (data.cards || []).forEach(function (c) {
    if (c.mtime > newestAt) { newestAt = c.mtime; lastNewestCard = c.id; }
  });
  /* The pin is let go further down, where `qids`, the mapping and the turns are
     all current -- which is what it takes to tell a board with working on it
     nobody has handed in from a board with nothing on it. */
  if (reopenedFor !== null && reopenedFor !== (newestQ || "")) reopenedFor = null;
  if (reopenedFor !== null && !data.archived) owed = true;

  pinnedTo = owed ? newestQ : null;

  /* A sent answer keeps the block open, because the tutor's next move is usually
     to point at a mistake in it. A declined one does the opposite: the whole
     point of skipping is that the prompt goes away. */
  var skipped = !!newestQ && (data.turns || []).some(function (t) {
    return t.signal === "skip" && t.answers === newestQ;
  });
  if (skipped) {
    pinnedTo = null;
    owed = false;
  }

  /* Which answer the panel is editing. An ink turn already sent against the
     current question is the one to correct; anything else starts a new one. */
  /* Which question is being answered. Usually the newest one; whichever the
     student picked, if they went back to an earlier one. A question that has
     scrolled off the top of the transcript is still a question, and going back
     to add a line to the proof under it is ordinary work, not an edge case. */
  var qids = ordered.filter(function (c) { return !!isQuestion[c.id]; })
                    .map(function (c) { return c.id; });
  /* And the running census of what this lesson has asked, which is what tells a
     board from a leftover record. It only ever grows, and only a live frame with
     a question in it adds to it -- see `seenQs`. */
  if (!data.archived && qids.length) {
    seenAny = true;
    qids.forEach(function (q) { seenQs[q] = true; });
  }

  /* Where each question's run ends: the last card written before the next
     question was asked. The newest board of a question sits there, because an
     answer belongs under the feedback it is answering. */
  var runEndOf = Object.create(null);
  var openQ = null;
  ordered.forEach(function (c) {
    if (isQuestion[c.id]) { openQ = c.id; runEndOf[c.id] = c.id; return; }
    if (openQ) runEndOf[openQ] = c.id;
  });

  /* Before anything reads the mapping: bring the chain of boards up to date with
     the transcript, and let the surface -- which may know more about where this
     lesson's working actually is than this browser does -- correct it. */
  /* THE BOARD-TO-PAGE MAPPING BELONGS TO THE LIVE LESSON, AND ONLY IT MAY
     WRITE. A past lesson's card ids start at 0001 too; left to run, `syncSlots`,
     `repairPages` and `savePages` would write its records under the live key.
     Nothing is drawn from the mapping on an archived frame anyway. */
  if (!data.archived) {
    lastTurns = data.turns || [];
    syncSlots(qids, runEndOf, lastTurns);
    repairPages();
    /* And the order boards stand in, which is read off the same mapping and so
       means nothing on a frame that is not this sitting's. */
    slotOrder = [];
    qids.forEach(function (q) {
      slotsOf(q).forEach(function (k) { slotOrder.push(k); });
    });
  }

  /* Which BOARD is being written on. Usually the attempt in hand on the newest
     question; whichever they picked, if they went back to an earlier one. A
     board that has scrolled off the top of the transcript is still a board, and
     going back to add a line to the proof on it is ordinary work. */
  /* A NEW QUESTION LETS GO OF THE PIN, UNLESS THERE IS WORKING UNDER IT. Only a
     pin a CARRY set, and only while what was carried is unsent: one question's
     grace, counted by `pinHeld`. Questions that arrive while a past lesson is
     open are not counted (the live frame is not drawn then). */
  if (!data.archived && workingOn && workingOnAt !== (newestQ || "")) {
    if (pinCarried && !pinHeld && unsentInk(workingOn)) {
      pinHeld = true;
      workingOnAt = newestQ || "";
    } else {
      workingOn = null;
      workingOnAt = null;
      pinHeld = false;
      pinCarried = false;
    }
  }
  /* An archived frame's `qids` are the ARCHIVE's question ids, so a pinned
     board's question is missing from them for reasons that have nothing to do
     with this sitting. Only a live frame may say a board has gone. */
  if (!data.archived && workingOn
      && (!boardPage[workingOn]
          || qids.indexOf(slotQ(workingOn)) === -1)) {
    workingOn = null;
    pinCarried = false;
    pinHeld = false;
  }
  var liveKey = workingOn || (newestQ ? newestSlot(newestQ) : null);
  var onQ = liveKey ? slotQ(liveKey) : newestQ;

  var mine = (data.turns || []).filter(function (t) {
    return t.kind === "ink" && t.answers === onQ;
  });
  var latestMine = (data.turns || []).filter(function (t) {
    return t.answers === onQ;
  });
  answering = {
    question: onQ,
    turn: mine.length ? mine[mine.length - 1] : null,
    /* The newest turn of any kind, so an old question can reopen on the surface
       it was answered with and carry the answer back for correction. */
    latest: latestMine.length ? latestMine[latestMine.length - 1] : null,
  };
  if (workingOn) owed = !data.archived;

  /* The writing surface goes at the END of the transcript, under the tutor's
     feedback. While an answer is waiting to be read it stays where it is
     (`paintSent`), and never under a frozen copy of the ink still on it. */
  /* The surface goes where the BOARD it is standing in for goes -- the attempt
     in hand at the end of the question's own run, or, if they went back, exactly
     where that earlier attempt was written. For the newest question the end of
     the run is the end of the transcript, which is where the surface has always
     gone; for an earlier one it is directly under the feedback that question
     got, which is the same rule and the same reason. */
  var runEnd = (liveKey && boardPage[liveKey] && boardPage[liveKey].a)
             || runEndOf[onQ] || null;
  var qNode = runEnd
    ? els.cards.querySelector('[data-card="' + runEnd + '"]')
    : null;
  if (!qNode) {
    var kids = els.cards.children;
    for (var q = kids.length - 1; q >= 0; q--) {
      if (kids[q] !== els.writer && kids[q].dataset && kids[q].dataset.key) {
        qNode = kids[q];
        break;
      }
    }
  }
  /* A past lesson is read only: no pen, no box, nothing to send into a session
     that has already been filed. So `liveKey` on an archived frame names a board
     of the ARCHIVE, and writing it down would point the pen -- and `restoreAnswer`
     with it -- at somebody else's lesson the moment the reader comes back. The
     live sitting's answer to this stands until a live frame changes it. */
  if (!data.archived) liveSlot = liveKey;
  /* THE HOLD IS ON THE BOARD FOLLOWING A CARD, NEVER ON A TAP.
     Somebody who touches an earlier board is asking for the surface to go there
     now, and a request made by hand outranks an animation. `workingOn` and
     `reopenedFor` are what a tap sets; with either of them the surface moves. */
  placeWriter(owed && !data.archived, qNode, live,
              replyArriving() && !workingOn && reopenedFor === null);
  /* The boards do not come and go with the answer panel: a `correct` card shuts
     the panel and the boards stay, as places to carry on working. The one board
     not drawn is the one the live surface stands in for. */
  /* A SURFACE HELD SHUT IS STILL THE SURFACE FOR THAT QUESTION.
     Every question's board is drawn as a picture except the one the live surface
     is standing in for -- so a surface held shut for the two seconds a card is
     typing had its dormant photograph drawn in its place, which is the next
     board showing up early wearing a different hat. See `writerHeldShut`. */
  paintBoards(qids, (els.writer.hidden && !writerHeldShut) ? null : liveKey, !live);
  /* Offered exactly when there is no surface to write on: the tutor has written
     something, and nothing is owed. */
  if (els.reopen) {
    els.reopen.hidden = !!data.archived || !!reading
                        || !(data.cards || []).length
                        || !els.writer.hidden;
  }
  paintBusy(data);
  /* And the documents asked for from this session. See `paintNews`. */
  paintNews(data);

  /* The ink layer is per card and idempotent: reconciled nodes keep the layer
     they already had, new ones get one. Then the saved marks are laid back
     over, without disturbing anything being drawn at this moment. */
  if (window.Annotate) {
    Array.prototype.forEach.call(els.cards.querySelectorAll("[data-card]"),
                                 window.Annotate.attach);
    window.Annotate.load(data.notes);
    /* Which of those the tutor has already been given. Without this, marks
       restored after a reload all read as undelivered, and the follow-up offer
       came back for ink that had gone days ago. */
    window.Annotate.loadSent(data.notes_sent);
  }
  renderScratch(data.uploads || []);
  /* And every address written into the lesson, checked against the payload
     that just arrived. A card naming a document that moved this morning reads
     as dead this afternoon, in its own sentence. */
  markAddresses();

  /* Put the reader back where they were. Everything below this either leaves the
     page alone or says explicitly where it should go, and both of those are
     decisions; content appearing above somebody is not. */
  holdAnchor(place);

  if (firstPaint) {
    firstPaint = false;
    /* Somebody is looking at this workspace. Said once here and again on every
       card that lands, which is what keeps it from notifying about the lesson
       being read right now. */
    markSeen(true);
    revealNewest(false);
    /* Mathematics is typeset and answer images decode after this frame, and
       both change the height of everything above the newest card -- so the
       place we just scrolled to is not where that card ends up. Land on it
       again once the page has settled, unless a hand has since intervened. */
    window.requestAnimationFrame(function () { if (!handledAt) revealNewest(false); });
    setTimeout(function () { if (!handledAt) revealNewest(false); }, 400);
  } else if (!anythingNew) {
    /* NOTHING ARRIVED. Do not move the page: a heartbeat, a count changing or a
       figure finishing is not a card. */
  } else {
    cardsArrived++;
    /* Read, because it landed in front of somebody. Without this the workspace
       being worked in would notify about its own cards the moment the reader
       switched away from it. */
    markSeen(false);
    /* Something is on the board. Whatever the send was waiting for has landed,
       whether or not the tutor's own state ever said so. */
    sendingAt = 0;
    sendingWord = "";
    /* A CARD ARRIVING NEVER MOVES THE READER. IT GROWS INTO VIEW, the way a chat
       page does. The student's working keeps its place in the run (a live surface
       and a dormant board are one box), so nothing above the reader changes height
       and the reply grows down from where "the tutor is writing" was.
       `revealNewest` is for the first paint and the jump button only. */
    var fresh = newestCardNode();
    var box = fresh && fresh.getBoundingClientRect();
    els.jump.hidden = !!box && box.top < window.innerHeight;
  }
}

/* Where to be after pressing Send: looking at the foot of the writing surface,
   a little above the middle of the window, so the receipt and "the tutor is
   writing" under it are on screen with the last thing written above. */
function revealSent() {
  if (!els.writer || els.writer.hidden) return;
  var r = els.writer.getBoundingClientRect();
  var top = r.bottom + window.scrollY - window.innerHeight * 0.62;
  if (top < 0) top = 0;
  window.scrollTo({ top: top, behavior: "smooth" });
}

/* And again once the payload the send provoked has landed: the receipt appears,
   the tutor's chip changes, and both of them move the thing we were aiming at.
   Not if a hand has intervened -- at that point the person has said where they
   want to be, which outranks anything here. */
function revealSentSettling() {
  var at = Date.now();
  var news = cardsArrived;
  revealSent();
  /* And not once a card has arrived. These repeats re-land on the surface's foot
     after the receipt settles; once the tutor replies, `els.writer` is the fresh
     sheet below the reply, and landing on it drags the reader past the card. */
  [300, 900].forEach(function (ms) {
    setTimeout(function () {
      if (handledAt <= at && cardsArrived === news) revealSent();
    }, ms);
  });
}

/* A hand mid-answer is not to be moved. The tutor writing a second card while
   the student is still writing on the first is ordinary, and scrolling the page
   out from under a pen is not a thing to do to somebody drawing a diagram --
   they get the button instead, and take it when they are ready. */
function penBusy() {
  return !!(writer && writer.busy && writer.busy());
}

/* The end-of-session offer, and the outcome of the last push. Both belong on
   the board rather than in a terminal: the person who has to answer, and the
   person who needs to know a push failed, is holding an iPad. */
var pushDismissed = 0;

/* Five minutes of "nothing is happening" is how a person concludes the thing is
   broken and taps the button again -- which wakes the tutor a second time and
   gets two opening cards written. A turn in progress is knowable, so say it. */
function paintWaiting(data) {
  /* Leave the just-tapped label alone for a moment, or the payload the tap
     itself provokes overwrites it before it has been read. */
  if (Date.now() - sentAt < 4000) return;
  var asked = (data.turns || []).some(function (t) { return t.signal === "begin"; });

  if (working) {
    els.emptyLead.textContent = "The tutor is writing…";
    els.begin.textContent = "the tutor is working";
    els.begin.disabled = true;          /* asking again now writes a second card */
    return;
  }
  /* A START IS IN FLIGHT, AND "ask again" IS THE WRONG THING TO OFFER.

     Tapping begin on an unattended board now STARTS a tutor -- the request
     used to go into an inbox nobody was reading and sit there. So the empty
     board's own words have to follow the start, or the one button on the
     screen goes on inviting the tap that produces a second opening card. */
  if (asked && lastLive && lastLive.agent
      && lastLive.agent.state === "waking") {
    els.emptyLead.textContent = "The tutor is starting up…";
    els.begin.textContent = "starting the tutor";
    els.begin.disabled = true;
    return;
  }
  els.emptyLead.textContent = asked ? "The tutor has not written anything yet."
                                    : "Nothing on the board yet.";
  els.begin.textContent = asked ? "ask again" : "ask the tutor to begin";
  els.begin.disabled = false;
}

/* A homework sitting produces a document, and the state of that document lives
   in a .tex file nobody on an iPad can see. Which set, how much of it is written
   up, and whether the last compile passed -- with the LaTeX error itself when it
   did not, because "the build failed" without the reason is a message that
   sends someone to a laptop. */
function paintHomework(hw) {
  if (!hw) { els.hwbar.hidden = true; return; }
  els.hwbar.hidden = false;

  if (!hw.name) {
    els.hwSet.textContent = "homework";
    els.hwCount.textContent = hw.ambiguous && hw.ambiguous.length
      ? "which set? the tutor has not said" : "no problem set found";
    els.hwBuild.textContent = "";
    els.hwBuild.removeAttribute("data-ok");
    els.hwBuild.removeAttribute("title");
    return;
  }

  els.hwSet.textContent = hw.name;
  if (!hw.total) {
    els.hwCount.textContent = "no problems transcribed yet";
  } else {
    var left = hw.total - hw.written;
    els.hwCount.textContent = hw.written + " of " + hw.total + " written up" +
      (left ? " · " + left + " to go" : " · complete");
  }

  var b = hw.build;
  if (!b) {
    els.hwBuild.textContent = "not compiled yet";
    els.hwBuild.removeAttribute("data-ok");
    els.hwBuild.removeAttribute("title");
    return;
  }
  els.hwBuild.dataset.ok = b.ok ? "yes" : "no";
  els.hwBuild.textContent = b.ok
    ? "compiled " + (b.iso || "").slice(11, 16)
    : lastLine(b.detail || "") || "compile failed";
  /* The error ellipsizes in a narrow strip; the whole line is its tooltip. */
  if (b.ok) els.hwBuild.removeAttribute("title");
  else els.hwBuild.title = els.hwBuild.textContent;
}

/* A LaTeX log ends with the thing that went wrong; the hundred lines above it
   are font declarations. */
function lastLine(text) {
  var lines = text.split("\n").filter(function (l) { return l.trim(); });
  for (var i = lines.length - 1; i >= 0; i--) {
    if (/^!|error|Error|ERROR/.test(lines[i])) return lines[i].trim().slice(0, 160);
  }
  return lines.length ? lines[lines.length - 1].trim().slice(0, 160) : "";
}

function paintSession(state, push, agent, exported, hwBuilt) {
  /* Whether an assistant is attached, and whether it is thinking. Without this
     the page looks identical when nothing is listening at all. */
  /* Never hidden. A blank space where this belongs reads as "fine", and it is
     the opposite of fine: it means anything sent goes into an inbox nobody is
     reading. Somebody tapped "ask the tutor to begin", got a green connection
     dot, and waited on a session that did not exist. */
  els.agent.hidden = false;
  /* Only a record the server has judged stale means nobody is there. "Working"
     is emphatically attached: a turn in progress is the tutor doing its job, and
     a five-minute turn used to read on the iPad as a death. */
  /* "reattaching" counts as attached: a daemon being bounced onto new code is
     coming back in seconds, and telling somebody mid-lesson that nothing is
     reading the board is both wrong and alarming. */
  /* "waking" counts as attached for exactly the reason "reattaching" does, and
     it is the more common of the two: a tutor coming up is a tutor, and telling
     somebody mid-lesson that nothing is reading the board is both wrong and the
     specific thing that makes them send again. */
  attached = !!agent && agent.state !== "stale";
  working = !!agent && agent.state === "working";
  /* And say it where somebody about to tap is actually looking, not only in the
     chrome. An empty board with nothing attached is a dead end, and the person
     holding the iPad cannot be expected to infer that from a missing chip. */
  els.noTutor.hidden = attached;
  /* And in the chrome, where it is legible from anywhere in the lesson. The
     panel above only exists on a board with no cards on it; a tutor dies in the
     middle of one that has plenty. */
  els.tutorBad.hidden = attached;
  if (!agent) {
    els.agent.dataset.state = "none";
    els.agent.textContent = "no tutor";
  } else {
    els.agent.dataset.state = agent.state || "stale";
    els.agent.textContent =
      agent.state === "working" ? (agent.agent || "assistant") + " is working"
      /* STARTING ONE IS NOT INSTANT, AND SILENCE READS AS DEATH: a tutor coming
         up says so, with an ellipsis, and is asked about first because it is the
         state most likely to be misread as the worst one. */
    : agent.state === "waking" ? (agent.agent || "assistant") + " is waking up…"
    : agent.state === "listening" ? (agent.agent || "assistant") + " listening"
      /* An interactive assistant is not listening to the board -- it is sitting
         in a terminal waiting for its person. "Attached" is the true word, and
         the useful one: somebody is on the other end. */
    : agent.state === "attached" ? (agent.agent || "assistant") + " attached"
      /* Bounced onto new code, not dead. It comes back on its own. */
    : agent.state === "reattaching" ? (agent.agent || "assistant") + " reattaching…"
    : agent.state === "wrapping up" ? (agent.agent || "assistant") + " wrapping up…"
      /* Only reached when the record exists but nothing recognises its state --
         a daemon whose process is gone. TWO WORDS, because this is a bar that
         cannot grow: "tutor stopped — nothing is reading the board" came out as
         "tutor stopped - nothing is rea...", which loses the half that matters.
         `#tutorbad` carries the sentence. */
    : "tutor stopped";
    /* AND IF SOMEBODY ELSE IS WRITING, SAY WHY, NOT JUST WHO. The strip already
       names the assistant, so a swap changes the name on its own -- but a name
       that changed silently is a question rather than an answer. `agent_why` is
       written by the daemon at the moment it climbs down to another provider,
       and it is the sentence a student is owed: this is the one thing the board
       does on their behalf without being asked. */
    els.agent.title = agent.agent_why || "";
  }
  /* The chip is the first thing the bar gives up width on, so its words are also
     its title -- unless `agent_why`, the sentence a student is owed when somebody
     else is teaching, is already there. The busy strip says it too
     (`stalledWord`), because a title is a tooltip and glass does not hover. */
  if (!els.agent.title) els.agent.title = els.agent.textContent;
  if (leavingTo) return;              /* a decision is in front of the student */
  if (state.finished) {
    els.finishLead.textContent = "Session finished.";
    els.finishSub.textContent = "Save this work and push it to GitHub?";
    els.finishYes.textContent = "Push";
    els.finishNo.textContent = "Not now";
    els.finishLeave.hidden = true;
    els.finish.hidden = false;
  } else if (els.finish.hidden !== false || !savePrompted()) {
    /* Leave a prompt the student raised themselves standing. */
    if (!savePrompted()) els.finish.hidden = true;
  }

  paintBanner(push, exported, hwBuilt);
}

/* THE BANNER, WHICH IS ABOUT A DOCUMENT AND NOT ABOUT THE SESSION: three
   callers know nothing about the session, so it is its own function. */
function paintBanner(push, exported, hwBuilt) {
  /* One banner, THREE things that can land in it: a push, an export and a
     compile of the write-up, and the newest is the one being waited on. The
     write-up's record comes off disk (`hw.build` on the payload), so the next
     payload does not repaint it away. */
  var last = push;
  if (exported && (!push || (exported.at || 0) > (push.at || 0))) last = exported;
  if (hwBuilt && (!last || (hwBuilt.at || 0) > (last.at || 0))) last = hwBuilt;
  if (!last || last.at <= pushDismissed) {
    els.pushed.hidden = true;
    offerDocument(null);
    return;
  }
  els.pushed.hidden = false;
  els.pushed.className = "pushed " + (last.ok ? "ok" : "bad");
  els.pushedIcon.textContent = last.ok ? "✓" : "✕";
  /* AND A WAY TO READ IT, AND A WAY TO TAKE IT WITH YOU, off the iPad. Which
     document the banner is ABOUT is decided here; whether it EXISTS is the
     payload's (`papers`), off the files. */
  offerDocument(last === exported ? "lesson"
                : (last === hwBuilt || last.kind === "hw") ? "homework" : null);
  if (last === exported) {
    /* A photograph says how many pages it came to, because that is the one
       thing about it a person cannot see from here and the one thing that says
       whether the whole evening is in there. */
    var howMany = last.pages
      ? " — " + last.pages + (last.pages === 1 ? " page" : " pages")
        + ", saved in the repository and staged for the next save"
      : " — saved in the repository, and staged for the next save";
    els.pushedText.textContent = last.ok
      ? (last.pdf || "the lesson") + howMany
      : "Export failed — "
        + ((last.detail || "no detail").split("\n")[0] || "no detail");
  } else if (last === hwBuilt || last.kind === "hw") {
    els.pushedText.textContent = last.ok
      ? (last.pdf || last.set || "the write-up")
        + " — compiled, kept in the repository, and staged for the next save"
      : "The write-up did not compile — "
        + (lastLine(last.detail || "") || "no detail");
  } else if (last.ok) {
    var first = (last.detail || "").split("\n").filter(function (l) { return l.trim(); });
    els.pushedText.textContent = (first[first.length - 1] || "pushed") + " · " + last.iso;
  } else {
    els.pushedText.textContent = "Push failed — " + (last.detail || "no detail");
  }
}

/* ======================================================================
   THE DOCUMENTS: reading one on the board, and taking one off it.

   A document is never navigated to: in an installed web app iOS treats a
   download link as a navigation, which leaves the board with no way back. It
   is FETCHED and handed to the system as a file -- `navigator.share` with a
   `File` (the share sheet, over the board), else a blob URL with `download`,
   else a NEW context, never this one. `AbortError` is a Cancel, not a failure.

   Reading is `readKind`: the pages, drawn to PNG by the machine that holds the
   PDF, in the one reader (`reader.js`). Not an `<iframe>`: iOS renders a PDF
   in a frame as one unscrollable page.

   `papers` says which documents exist and when each was written; it enables
   the buttons and invalidates a warm copy. The banner's record says which
   document the banner is ABOUT.
   ====================================================================== */

/* Which documents exist right now, keyed by kind, off the payload: they
   survive every repaint and every reload. */
var papers = {};

/* One fetched document per kind, kept against the moment the PDF was written,
   so a rebuild is never served from here. WARMED THE MOMENT IT IS OFFERED:
   Safari refuses a `navigator.share` called after an `await`, so the document
   has to be in hand before the tap. */
var warm = Object.create(null);

/* WHERE A DOCUMENT IS, SAID ONCE.

   A kind names a document to the server and is never a path -- and the kind is
   also the tail of the route, which is why there is one rule here rather than
   three places that each glue a string together. Three families answer to the
   same two routes: `lesson` and `homework`, the two the board itself builds,
   and `doc/<id>`, a document this subject has. */
function paperUrl(kind) { return BASE + "/download/" + kind; }
function paperViewUrl(kind) { return BASE + "/view/" + kind; }

/* THE NAME THE INK IS ANCHORED UNDER: the family is stripped, and the anchor
   is `doc/<ident>/p<n>`. */
function paperIdent(kind) {
  if (kind.indexOf("doc/") === 0) return kind.slice(4);
  return kind;
}

function paperTitle(kind) {
  if (kind === "homework") return "the written-up homework";
  if (kind === "lesson") return "this lesson";
  /* A document the board did not build has no name of its own until `/view`
     answers with one, and "this lesson" would be a lie in the meantime. */
  return "this document";
}

function warmPaper(kind) {
  var have = papers[kind];
  if (!have) return null;
  var slot = warm[kind];
  if (slot && slot.at === have.at) return slot.job;
  var job = fetch(paperUrl(kind), { credentials: "same-origin" })
    .then(function (res) {
      if (!res.ok) throw new Error("the board would not give it up (" + res.status + ")");
      return res.blob().then(function (blob) {
        var name = nameFrom(res, have.name || "lesson.pdf");
        var file = null;
        try {
          file = new File([blob], name, { type: "application/pdf" });
        } catch (e) { file = null; }
        return { blob: blob, name: name, file: file };
      });
    });
  slot = warm[kind] = { at: have.at, job: job, got: null };
  job.then(function (got) {
    if (warm[kind] === slot) slot.got = got;
  }, function () { /* the tap will try again and say so */ });
  return job;
}

function inHand(kind) {
  var slot = warm[kind], have = papers[kind];
  return slot && have && slot.at === have.at ? slot.got : null;
}

function nameFrom(res, fallback) {
  /* The server names the file -- it is the only side that knows the course and
     the set, and `ch07-homework.pdf` in a Files app says neither whose it is
     nor what it is from. */
  var cd = res.headers ? (res.headers.get("Content-Disposition") || "") : "";
  var m = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(cd);
  return (m && decodeURIComponent(m[1])) || fallback;
}

/* ------------------------------------------------- the banner's two buttons */
var bannerKind = null;

function offerDocument(kind) {
  if (!els.pushedGet) return;
  /* A document the payload does not list is a document that is not on disk --
     a `.tex` that failed to compile, or a lesson nobody has exported. No
     button at all beats a button that hands over nothing. */
  var have = kind && papers[kind];
  bannerKind = have ? kind : null;
  if (els.pushedView) {
    els.pushedView.hidden = !have;
    els.pushedView.disabled = false;
    els.pushedView.textContent = "read it";
  }
  els.pushedGet.hidden = !have;
  els.pushedGet.disabled = false;
  els.pushedGet.textContent = "save a copy";
  if (have) warmPaper(kind);
}

/* Is this the installed app, with no browser chrome around it?
   It decides the LAST RESORT and nothing else: in a tab, a PDF opened in place
   has a back button and a share button; in a standalone app it has neither, and
   that is the whole of the defect being fixed. */
function standalone() {
  if (navigator.standalone === true) return true;
  try { return global_matches("(display-mode: standalone)"); } catch (e) { return false; }
}

function global_matches(query) {
  return !!(window.matchMedia && window.matchMedia(query).matches);
}

/* ------------------------------------------------------- taking a copy away */
/* `btn` is whichever control was tapped -- the banner's, or the one in the
   reader's own bar. Both do the same thing to the same document, and neither
   may navigate this window. */
function saveCopy(kind, btn) {
  if (!kind || !papers[kind]) return;
  var got = inHand(kind);
  /* In hand already: share on the frame of the tap, inside the gesture, which
     is the only moment Safari will allow it. */
  if (got) return shareIt(got, kind, btn);

  var was = btn ? btn.textContent : "";
  if (btn) { btn.disabled = true; btn.textContent = "getting it…"; }
  var back = function () {
    if (btn) { btn.disabled = false; btn.textContent = was || "save a copy"; }
  };
  return (warmPaper(kind) || Promise.reject(new Error("nothing to save")))
    .then(function (ready) {
      back();
      /* The gesture is gone by now, so sharing may be refused -- `shareIt`
         falls through to saving, and saving does not need one. */
      shareIt(ready, kind, btn);
    }, function (err) {
      back();
      sayBadly("Could not hand it over — "
               + ((err && err.message) || "the board did not answer"));
    });
}

/* Said where the person who tapped is looking. The banner is the board's own
   place for "something slow happened, here is how it went", and it is where an
   export already reports -- but a tap in the viewer happens with the banner
   behind a full-screen panel, so that one says it in the panel instead. */
function sayBadly(text) {
  if (paperOpen && reader) {
    reader.say("<strong>That did not work</strong>" + escapeHtml(text));
    return;
  }
  els.pushed.hidden = false;
  els.pushed.className = "pushed bad";
  els.pushedIcon.textContent = "✕";
  els.pushedText.textContent = text;
}

/* THE SHARE SHEET FIRST, AND NOTHING THAT NAVIGATES EVER. `navigator.share`
   with a `File` raises the native sheet OVER the board, and Cancel returns to
   the lesson, which never went anywhere. */
function shareIt(got, kind, btn) {
  var done = function (label) {
    if (btn) btn.textContent = label || "save a copy";
  };
  if (got.file && navigator.share && navigator.canShare
      && navigator.canShare({ files: [got.file] })) {
    try {
      var p = navigator.share({ files: [got.file], title: got.name });
      if (p && p.then) {
        p.then(function () { done("saved"); }, function (err) {
          /* Cancel is a decision, not a fault. */
          if (err && err.name === "AbortError") { done(); return; }
          saveBlob(got, kind, done);
        });
        return p;
      }
    } catch (e) { /* refused outright; save instead */ }
  }
  return saveBlob(got, kind, done);
}

/* No share sheet here, and still nothing that navigates THIS window: a blob
   URL with `download` saves in place, but an installed iOS app treats it as a
   navigation, so there the last resort is a NEW context (Safari, which has a
   way back). */
function saveBlob(got, kind, done) {
  var a = document.createElement("a");
  if (standalone() || !("download" in a)) {
    window.open(paperUrl(kind), "_blank", "noopener");
    done();
    return;
  }
  var href = URL.createObjectURL(got.blob);
  a.href = href;
  a.download = got.name;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  /* Long enough for the save to have started, and then reclaimed: a blob of a
     lesson-sized PDF held for the rest of the sitting is memory an iPad wants
     for the board. */
  setTimeout(function () { URL.revokeObjectURL(href); }, 60000);
  done("saved");
}

function act(label, cls, fn) {
  var b = document.createElement("button");
  b.type = "button";
  b.className = cls;
  b.textContent = label;
  b.addEventListener("click", fn);
  return b;
}


/* ------------------------------------------------------ reading it, in place */
/* THE ONE READER, `reader.js`, built over everything by this page. The pages
   are pictures from `/view/<kind>` (`tutorboard/course/paper.py` says why).
   The board's own tools on its bar: save a copy, and the last round. The pen,
   the pinch, the marked copy and every ink save are the reader's: each save
   goes through `inkkeep.js`, owed and retried. A send (`sendNotes`) is not a
   save. */
var paperOpen = null;          /* the kind on the glass, or null */

var keeper = window.InkKeep && window.Annotate ? window.InkKeep.make({
  url: BASE + "/annotate/save",
  paint: function () { if (reader) reader.paintKeep(); }
}) : null;

function readerTool(id, label, title, cls) {
  var b = document.createElement("button");
  b.type = "button";
  b.id = id;
  b.textContent = label;
  b.title = title;
  if (cls) b.className = cls;
  return b;
}

var paperTools = {
  /* ITS LAST ROUND OF FEEDBACK, read as pairs in the library reader. */
  round: readerTool("reader-round", "",
                    "the last round's notes beside what was done, in the library"),
  get: readerTool("reader-get", "save a copy", "this PDF, to keep", "pushed-get")
};
paperTools.round.hidden = true;

var reader = window.Reader ? window.Reader.mount({
  keeper: keeper,
  url: function (path) { return BASE + path; },
  tools: [paperTools.round, paperTools.get]
}) : null;

/* A DOCUMENT THIS COURSE POINTS AT, rather than one it built: `readKind` with
   `doc/<id>`. Whether `save a copy` is offered is one question only: is this
   kind in `papers`. */
function openDoc(id, name, then) { readKind("doc/" + id, name, then); }

/* `then` is handed what `/view` answered, once the pages are on screen. An
   address naming one page of a document cannot scroll to it until the pictures
   exist, and there is nothing else on this page that knows when that is. */
function readKind(kind, label, then) {
  if (!kind || !reader) return;
  paperOpen = kind;
  var have = papers[kind];
  paperTools.get.hidden = !have;
  paperTools.get.textContent = "save a copy";
  paperTools.get.disabled = false;
  paperTools.round.hidden = true;
  /* In hand before the tap: Safari will not raise the share sheet for a
     `navigator.share` called after a fetch has resolved, so the wait is spent
     while the pages are being drawn rather than after `save a copy`. */
  if (have) warmPaper(kind);
  reader.open({
    pagesUrl: paperViewUrl(kind),
    id: paperIdent(kind),
    /* The caller's label first: `have.name` is the filename the PDF will be
       SAVED under, which is the right thing in a Files app and the wrong
       thing in a title bar. */
    title: label || (have && have.name) || paperTitle(kind),
    /* THE INK IS THE DOCUMENT'S, however it was reached: `doc/<ident>/p<n>`. */
    inkKey: "doc/" + paperIdent(kind),
    /* KEEP A MARKED COPY: the ink burned into a new PDF beside the original. */
    burn: kind,
    src: atSession,
    count: function (got) {
      return got.n + (got.n === 1 ? " page" : " pages")
        + (got.truncated ? " (the first " + got.n + " only)" : "");
    },
    drawing: function () {
      reader.say("<strong>Drawing the pages…</strong>"
                 + "A long document takes a few seconds the first time. "
                 + "After that it opens straight away.");
    },
    /* Marks made on this document before, put back: the cards' off the
       payload, and the document's own, which come with its pages. A stroke
       stored with a retired kind field is ordinary ink here. */
    ink: function (got) {
      if (!window.Annotate) return;
      if (lastLive) {
        window.Annotate.load(lastLive.notes);
        window.Annotate.loadSent(lastLive.notes_sent);
      }
      if (got.ink) {
        window.Annotate.load(got.ink);
        window.Annotate.loadSent(got.ink_sent || {});
      }
    },
    drawn: function (got) {
      paintPaperRound(kind);
      /* The address bar now names this document, so a link to it can be
         copied off the glass. */
      remember();
      if (then) then(got);
    },
    failed: function (got) {
      paperFailed(kind, got || {});
      if (then) then(null);
    },
    onClose: function () {
      /* The pen goes with the reader. Leaving annotate mode on when the
         document closes drops somebody back into the lesson with the pen out
         and the toolbar up, which is a mode they did not ask for. */
      if (window.Annotate && window.Annotate.isOn()) setAnnotating(false);
      paperOpen = null;
      paperTools.round.hidden = true;
      remember();                  /* and the address stops naming the document */
    }
  });
}

/* A document that cannot be drawn here is still a document. Say why in a
   sentence, and offer the two things that do work: keep it, or hand it to
   Safari, which has its own PDF reader and a way back. */
function paperFailed(kind, got) {
  var lead = got.why === "none"
    ? (kind === "homework" ? "The write-up has not been compiled yet."
       : kind === "lesson" ? "This lesson has not been exported yet."
                           : "That document is no longer where it was.")
    : got.why === "no-renderer"
      ? "This machine cannot draw the pages."
      : "The pages could not be drawn.";
  var why = got.detail || "";
  var box = reader.say("<strong>" + escapeHtml(lead) + "</strong>"
           + (got.why === "none" || got.why === "no-renderer"
              ? escapeHtml(why)
              /* A renderer's own output is a log, and a log reads as one. */
              : '<span class="detail">' + escapeHtml(why) + "</span>"));
  /* The offer to MAKE it only exists for the two the board builds. A document
     that has gone is a file somebody moved, and there is no button on this
     page that can put it back. */
  if (got.why === "none" && (kind === "homework" || kind === "lesson")) {
    box.appendChild(act(kind === "homework" ? "compile it now" : "export it now",
                        "pushed-get", function () {
      closeReader();
      if (kind === "homework") doExportHomework();
      else doExport();
    }));
    return;
  }
  if (got.why === "none") return;
  if (papers[kind]) {
    box.appendChild(act("save a copy", "pushed-get", function (e) {
      saveCopy(kind, e.currentTarget);
    }));
    box.appendChild(act("open it in the browser", "pushed-get quiet", function () {
      /* A NEW context, never this one. In the installed app that is Safari,
         which has chrome, a share button and a way back to the board. */
      window.open(paperUrl(kind), "_blank", "noopener");
    }));
  }
}

/* ITS ROUND, ONE TAP AWAY IN THE LIBRARY. The pairs -- what was written beside
   what was done -- live in the library reader (`ledger.js`); a second panel of
   them here would be a second ledger on the glass. So a document with rounds
   says where its last one stands, and the chip opens it there. */
function paintPaperRound(kind) {
  var b = paperTools.round;
  b.hidden = true;
  if (kind.indexOf("doc/") !== 0) return;
  api("/library/ledger/" + encodeURIComponent(paperIdent(kind)),
        { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (got) {
      var r = got && got.ok && got.rounds && got.rounds[0];
      if (!r || paperOpen !== kind) return;
      b.textContent = "Round " + r.round + (!r.landed ? " · revising"
        : r.done ? " done" : " · " + r.open + " open") + " → read in the library";
      b.onclick = function () {
        window.location.href = BASE + "/library?doc=" + encodeURIComponent(got.document);
      };
      b.hidden = false;
    })
    .catch(function () { /* no rounds to point at */ });
}

/* Shut. The reader saves what is owed first and lets the pictures go. */
function closeReader() { if (reader) reader.close(); }

if (reader) {
  paperTools.get.onclick = function (e) { saveCopy(paperOpen, e.currentTarget); };
  /* THE PEN, ON THE READER'S BAR, because the title bar is underneath it: the
     same mode as the lesson's own pen, reported on whichever is reachable. */
  if (reader.els.pen) {
    reader.els.pen.onclick = function () {
      setAnnotating(!(window.Annotate && window.Annotate.isOn()));
    };
  }
}

/* The whole conversation as one document, kept in the repository under a
   numbered name. */
/* The written-up work, compiled and kept, then handed over. `board writeup
   build` is the one compile; this presses the button and offers the result as
   the lesson export does. `kind: "hw"` tells the banner which document it is. */
function doExportHomework() {
  els.pushed.hidden = false;
  els.pushed.className = "pushed";
  els.pushedIcon.textContent = "…";
  els.pushedText.textContent = "compiling the write-up — LaTeX takes a moment…";
  offerDocument(null);
  return api("/hw/build", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}"
  }).then(function (r) { return r.json(); })
    .then(function (rec) {
      rec = rec || {};
      rec.kind = "hw";
      rec.at = Date.now() / 1000;
      /* In the write-up's own slot, which is where its record belongs. It
         used to arrive as `push`, and the next payload -- which carries a real
         `push.json` and knows nothing about this -- painted straight over it.
         The payload carries the same record from `live/hw.json` a moment later,
         so this only fills the second before it arrives. */
      paintBanner(null, null, rec);
    })
    .catch(function () {
      els.pushed.className = "pushed bad";
      els.pushedIcon.textContent = "✕";
      els.pushedText.textContent = "Could not reach the board to compile it";
    });
}

/* THIS LESSON, AS IT WAS READ: the board's own pixels, photographed here
   (`shot.js` says why it cannot be anywhere else). The server owns the name,
   the version and the repository copy. It says which card it is on: this can
   take twenty seconds. */
function doExport() {
  els.pushed.hidden = false;
  els.pushed.className = "pushed";
  els.pushedIcon.textContent = "…";
  offerDocument(null);           /* not the last document's buttons, while this builds */

  var shot = global_TutorShot();
  if (!shot) {
    /* `shot.js` is a separate, deferred script; a board that got here from a
       cache without it says so rather than throw. */
    els.pushed.className = "pushed bad";
    els.pushedIcon.textContent = "✕";
    els.pushedText.textContent = "Could not photograph the lesson — "
      + "reload the board and try again";
    return Promise.resolve(null);
  }
  els.pushedText.textContent = "photographing the lesson…";
  return shot.send(function (done, total) {
    els.pushedText.textContent = "photographing the lesson — card "
      + done + " of " + total + "…";
  }).then(function (rec) {
    paintBanner(null, rec || { ok: false, detail: "no answer" }, null);
  }).catch(function (err) {
    els.pushed.className = "pushed bad";
    els.pushedIcon.textContent = "✕";
    els.pushedText.textContent = "Could not photograph the lesson — "
      + ((err && err.message) || "the browser refused");
  });
}

/* Asked for rather than captured at load: `shot.js` is a deferred script. */
function global_TutorShot() {
  return (typeof window !== "undefined" && window.TutorShot) || null;
}

/* Is the standing prompt one the student raised, rather than the end of a
   session? Then a payload arriving must not sweep it away mid-decision. */
function savePrompted() {
  return !els.finish.hidden && /^Save this work/.test(els.finishLead.textContent || "");
}

function doPush() {
  els.finish.hidden = true;
  els.finishLeave.hidden = true;
  els.pushed.hidden = false;
  els.pushed.className = "pushed";
  els.pushedIcon.textContent = "…";
  els.pushedText.textContent = "saving and pushing…";
  return api("/push", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({})
  }).then(function (r) { return r.json(); })
    .then(function (rec) { paintBanner(rec, null, null); })
    .catch(function () {
      els.pushed.className = "pushed bad";
      els.pushedIcon.textContent = "✕";
      els.pushedText.textContent = "Push failed — could not reach the board";
    });
}

/* Pushing from the leaving flow goes on to leave; from anywhere else it just
   pushes and the lesson carries on. */
els.finishYes.onclick = function () {
  var go = !!leavingTo;
  var done = doPush();
  if (go && done && done.then) done.then(goLeave, goLeave);
};

/* Saving must not depend on the tutor. Sessions end by being abandoned -- a lid
   closes, an allocation expires, somebody puts the iPad down -- and until now
   the only way to the push was a prompt that only `board finish` could raise.
   Work that is not committed is one bad night's sleep from gone. */
els.save.onclick = function () {
  els.finishLead.textContent = "Save this work?";
  els.finishSub.textContent = "Commit everything so far and push it to GitHub. "
                            + "The lesson stays open.";
  els.finish.hidden = false;
};
els.finishNo.onclick = function () {
  els.finish.hidden = true;
  els.finishLeave.hidden = true;
  leavingTo = null;
  api("/dismiss-finish", { method: "POST" }).catch(function () {});
};
document.getElementById("pushed-close").onclick = function () {
  els.pushed.hidden = true;
  pushDismissed = Date.now() / 1000;
};

function nearBottom() {
  return window.innerHeight + window.scrollY >= document.body.scrollHeight - 160;
}

/* The newest thing the tutor has written. Not the newest thing on the page: the
   writing surface is the last element in the transcript, by design, because a
   correction is written under the feedback it answers. */
function newestCardNode() {
  var all = els.cards.querySelectorAll("[data-card]");
  return all.length ? all[all.length - 1] : null;
}

/* Where the eye should land when a card arrives: the TOP of that card, tucked
   under the bar. It used to be the bottom of the document, which is the bottom
   of the writing surface -- so the reply that had just been waited for was
   pushed off the top of the screen and what arrived instead was a blank slate.
   The first line of the new feedback is the thing to read first. */
function revealNewest(smooth) {
  revealCard(newestCardNode(), smooth);
}

/* Any card's top, tucked under the bar; with no card, the foot of the page. */
function revealCard(node, smooth) {
  var top;
  if (node) {
    var bar = document.getElementById("bar");
    var under = bar ? bar.getBoundingClientRect().height : 0;
    top = node.getBoundingClientRect().top + window.scrollY - under - 10;
    if (top < 0) top = 0;
  } else {
    top = document.body.scrollHeight;
  }
  if (smooth) window.scrollTo({ top: top, behavior: "smooth" });
  else ownScroll(function () { window.scrollTo(0, top); });
}

/* A scroll the board makes on its own, told to the pen latch so it is not read
   as a page in flight (`Annotate.ownScroll`). */
function ownScroll(fn) {
  if (window.Annotate && window.Annotate.ownScroll) window.Annotate.ownScroll(fn);
  else fn();
}

/* A CARD IS TYPED OUT, AND NOTHING MOVES WHILE IT IS. A card arrives whole, so
   this reveals what is already in hand.

   THE CARD IS ITS FINAL SIZE FROM THE FIRST FRAME. Every character is laid out
   at once; the part not said yet carries `visibility: hidden`, which occupies
   its space exactly, so moving a character across cannot reflow anything.

   MATHEMATICS, CODE AND FIGURES ARE ATOMS, hidden whole and shown whole when
   the cursor reaches them, costing TYPE_ATOM characters of time. This runs
   after typesetting: KaTeX cannot measure what is not laid out.

   NOTHING CANCELS IT; a long card is typed faster, never skipped. It runs
   whether or not the card is on the glass. */
var TYPE_CPS = 110;        /* characters a second: past reading speed, still a hand */
var TYPE_MIN = 420;        /* even one line is typed, not placed */
var TYPE_ALL = 4200;       /* and the longest card there can be is over in four seconds */
var TYPE_ATOM = 10;        /* what a formula or a figure costs, in characters */

/* What is never cut into characters. A KaTeX subtree is one object; so is a
   table, a compiled diagram, a picture and a block of code, where the alignment
   is the meaning. */
var TYPE_ATOMIC = ".katex, .katex-display, pre, table, svg, img, figure";

/* Whether anything is being typed at this moment; the writing surface and the
   receipt above it read it (`replyArriving`). A count and a deadline, because
   `requestAnimationFrame` stops in a background tab. THE DEADLINE IS A WATCHDOG,
   NOT A BUDGET: every frame that lands pushes it out, so a card making progress
   holds for as long as it takes, and a stalled tab lets go `TYPE_STALL` after
   its last frame. */
var typingNow = 0;
var typingUntil = 0;
var TYPE_STALL = 2500;     /* silence, not elapsed time, is what releases a hold */
/* And how long a card whose PACING was lost holds the surface anyway. Short
   enough that nobody waits, long enough that the answer and the next board are
   two events rather than one. A stall is what takes it: see `finish` in
   `typeOut`. */
var TYPE_SETTLE = 250;
var settleTimer = null;
var settleNode = null;

/* WHICH CARDS ARE STILL ARRIVING -- A FACT ABOUT THE PAGE, NOT A CLASS ON A
   BODY. `placeWriter` comes down as far as the first card still arriving; the
   hold and this marker are taken and given back together, so a path that holds
   without animating (a stall) is still findable. */
var typingHeld = [];

function cardArriving(node) { return !!node && typingHeld.indexOf(node) !== -1; }

/* AND A HOLD NEVER SURVIVES INTO THE NEXT PAYLOAD: a newer picture of the
   lesson supersedes the card it was held for, so `render` drops it on the way
   in. `again` is false there, since that render places the surface itself. */
function settleEnd(again) {
  if (!settleTimer) return;
  clearTimeout(settleTimer);
  settleTimer = null;
  if (settleNode) {
    var s = typingHeld.indexOf(settleNode);
    if (s !== -1) typingHeld.splice(s, 1);
    settleNode = null;
  }
  if (typingNow > 0) typingNow--;
  if (again && !typingNow && lastLive) render(lastLive);
}

function typingCards() { return typingNow > 0 && Date.now() < typingUntil; }

/* One hold on the page, taken and given back in pairs, and the card it is for.
   The node is what `placeWriter` looks for; see `typingHeld`. */
/* AND TAKING A HOLD ARMS THE WATCHDOG RATHER THAN ASKING IT ANYTHING. Asking
   `keepTyping()` here compared against the LAST card's deadline, so a card
   arriving minutes after the previous one traced a `stall` before painting a
   character. The gap between two cards is not a stall in either. */
function holdTyping(node) {
  typingNow++;
  if (node && typingHeld.indexOf(node) === -1) typingHeld.push(node);
  typingUntil = Date.now() + TYPE_STALL;
}

/* Still going. Called on every frame the animation gets; it answers whether
   the watchdog had already let go (a frame after the deadline: the main thread
   was away longer than `TYPE_STALL`). Letting go is right, silently is not:
   the caller is told, so `finish` in `typeOut` ends the card as one event
   followed by the board. */
function keepTyping() {
  var now = Date.now();
  var late = !!(typingNow > 0 && typingUntil && now > typingUntil);
  if (late) trace("stall", { late: now - typingUntil, held: typingNow });
  typingUntil = now + TYPE_STALL;
  return late;
}

function releaseTyping(node) {
  var h = node ? typingHeld.indexOf(node) : -1;
  if (h !== -1) typingHeld.splice(h, 1);
  if (typingNow > 0) typingNow--;
  /* And now the writing surface may come down under it, and the receipt above
     it may stop talking. `placeWriter` and `paintSent` held for exactly this
     long; one more render is what moves them. */
  if (!typingNow && lastLive) render(lastLive);
}

/* THE ONE QUESTION BOTH SURFACES ASK: HAS THE REPLY ACTUALLY LANDED -- its node
   in the document, typeset, typed out -- not has its record arrived. The
   writing surface and the busy receipt both ask this, so no next board comes
   down and the pulse stays until the whole response is rendered. A figure is
   an atom (`TYPE_ATOMIC`), so it decodes within the animation. */
function replyArriving() { return typingCards(); }

/* The card's content in the order it is read: runs of text, and atoms. */
function typeUnits(root) {
  var units = [];
  (function walk(node) {
    var kids = node.childNodes;
    for (var i = 0; i < kids.length; i++) {
      var n = kids[i];
      if (n.nodeType === 3) {
        /* Whitespace between two inline elements is not a character anybody
           watches arrive, and hiding it would open a gap that closes again. */
        if (n.data && /\S/.test(n.data)) units.push({ text: n, full: n.data });
        continue;
      }
      if (n.nodeType !== 1) continue;
      if (n.matches && n.matches(TYPE_ATOMIC)) { units.push({ atom: n }); continue; }
      walk(n);
    }
  })(root);
  return units;
}

/* Lay a unit out in full and paint none of it. */
function typeDress(u) {
  if (u.atom) {
    u.was = u.atom.style.visibility;
    u.atom.style.visibility = "hidden";
    u.n = TYPE_ATOM;
    return;
  }
  var span = document.createElement("span");
  span.className = "tw";
  var said = document.createElement("span");
  said.className = "tw-said";
  var soon = document.createElement("span");
  soon.className = "tw-soon";
  soon.appendChild(document.createTextNode(u.full));
  span.appendChild(said);
  span.appendChild(soon);
  u.text.parentNode.replaceChild(span, u.text);
  u.span = span;
  u.said = said;
  u.soon = soon;
  u.n = u.full.length;
}

/* Paint the first `k` characters of it, and no more. */
function typeShow(u, k) {
  if (u.atom) {
    if (k > 0) u.atom.style.visibility = u.was || "";
    return;
  }
  if (u.at === k) return;
  u.at = k;
  u.said.textContent = u.full.slice(0, k);
  u.soon.textContent = u.full.slice(k);
}

/* And put the DOM back the way markdown left it, so nothing downstream -- the
   address marker, the annotation layer, an export -- ever sees the scaffolding. */
function typeUndress(u) {
  if (u.atom) { u.atom.style.visibility = u.was || ""; return; }
  if (!u.span || !u.span.parentNode) return;
  u.span.parentNode.replaceChild(document.createTextNode(u.full), u.span);
}

function typeOut(card) {
  var which = (card && card.dataset && card.dataset.card) || "?";
  if (!card || card._typed) { trace("skip", { card: which, why: "already typed" }); return; }
  card._typed = true;
  var body = card.querySelector(".body");
  if (!body) { trace("skip", { card: which, why: "no body" }); return; }
  var units = typeUnits(body);
  /* NOTHING TO TYPE IS NOTHING HELD, and that is a real way for a card to
     arrive whole with the surface free to move under it -- a body that is one
     atomic block, or an empty one. Recorded rather than silent, because from the
     outside it looks exactly like the animation being off. */
  if (!units.length) { trace("skip", { card: which, why: "no units" }); return; }

  var total = 0;
  units.forEach(function (u) {
    typeDress(u);
    u.start = total;
    u.at = 0;
    total += u.n;
  });
  if (!total) {
    units.forEach(typeUndress);
    trace("skip", { card: which, why: "nothing to paint" });
    return;
  }

  /* EVERY CARD TYPES, AND REDUCE MOTION DOES NOT GOVERN THIS ONE ANIMATION. The
     owner asked for it explicitly, and an explicit request about one animation
     outranks a system-wide default; Reduce Motion still governs the entry slide,
     the reveal and the settle. A card with nothing to type is `skip` above. */
  var ms = Math.max(TYPE_MIN, Math.min(TYPE_ALL, Math.round(total / TYPE_CPS * 1000)));
  var rate = total / Math.max(1, ms);          /* characters per millisecond */
  var t0 = null, at = 0;

  var done = function () {
    units.forEach(typeUndress);
    try { body.normalize(); } catch (e) { /* not fatal */ }
    body.classList.remove("typing");
  };

  holdTyping(card);
  body.classList.add("typing");
  var began = Date.now();
  trace("type", { card: which, ms: ms, units: units.length, chars: total });

  var finish = function (stalled) {
    done();
    /* How long it ACTUALLY took beside what it asked for. The two being far
       apart is a stalled main thread, which is the difference between a card
       that typed and a card that appeared. */
    trace("typed", { card: which, asked: ms, took: Date.now() - began,
                     stalled: stalled ? 1 : 0 });
    /* A STALL LOSES THE PACING. IT MUST NOT ALSO LOSE THE ORDER. The card is
       finished whole and the hold is handed to the settle: nothing moves for
       `TYPE_SETTLE`, then the surface comes down. The hold taken above is the one
       the settle gives back, so `typingNow` is not touched here. */
    if (stalled && !settleTimer) {
      settleNode = card;
      settleTimer = setTimeout(function () { settleEnd(true); }, TYPE_SETTLE);
      return;
    }
    releaseTyping(card);
  };

  /* THE CLOCK IS READ HERE, NOT TAKEN FROM THE CALLBACK.

     `requestAnimationFrame` hands its callback a timestamp, and a page that has
     replaced it with a timer -- a test harness, an older browser, a polyfill --
     hands it nothing. Subtracting that gives NaN, no character is ever due, and
     the card sits half-typed for ever with the writing surface held behind it.
     A card that cannot finish is worse than one that does not animate. */
  var step = function () {
    var now = Date.now();
    if (t0 === null) t0 = now;
    /* A FRAME IS PROOF OF LIFE. Nothing else here can tell a card that is
       taking its time from a tab that stopped animating -- and a frame that
       arrives too late to be proof of anything says so, which is this card's
       cue to stop pacing and land. */
    var stalled = keepTyping();
    var want = stalled ? total
      : Math.min(total, Math.ceil((now - t0) * rate));
    while (at < units.length && units[at].start < want) {
      var u = units[at];
      var take = Math.min(u.n, want - u.start);
      typeShow(u, take);
      if (take >= u.n) at++;
      else break;
    }
    if (at < units.length) { window.requestAnimationFrame(step); return; }
    finish(stalled);
  };
  window.requestAnimationFrame(step);
}

/* ------------------------------------------------------- keeping the place --

   NOTHING THAT ARRIVES ABOVE THE READER MAY MOVE THE READER. A sent answer is
   rendered above the surface, and its frozen picture is an `img` with no height
   until it decodes, so the page grows above the reader. Safari has no scroll
   anchoring, so this is it: note which node the reader is looking at and where
   it sits, and put it back after the rebuild. Anchored by card or turn id, not
   render key, because a key carries a version. */
function anchorId(node) {
  if (!node || !node.dataset) return null;
  if (node.dataset.card) return '[data-card="' + node.dataset.card + '"]';
  if (node.dataset.turn) return '[data-turn="' + node.dataset.turn + '"]';
  /* A dormant board keeps its identity across renders too. NOT the live surface:
     its place in the run is deliberately moved -- the next board opens under the
     tutor's newest word -- so holding it still would follow it down the page. */
  if (node.dataset.slot) return '[data-slot="' + node.dataset.slot + '"]';
  return null;
}

function anchorNow() {
  var kids = els.cards.children;
  var last = null;
  for (var i = 0; i < kids.length; i++) {
    var sel = anchorId(kids[i]);
    if (!sel) continue;
    var r = kids[i].getBoundingClientRect();
    /* The first thing whose foot is still on the glass: that is what is being
       read, or what is immediately above it. */
    if (r.bottom > 0) return { sel: sel, top: r.top };
    last = { sel: sel, top: r.top };
  }
  /* PAST EVERYTHING KEYED IS WHERE A SEND LEAVES YOU. Hold the last thing above
     the reader rather than giving up: `revealSent` parks them at the foot of the
     surface, which has no id. Not the surface itself, which moves when the tutor
     replies; its place is taken by the question's own frozen board with the same
     ink, so holding what is above it keeps the working where it was. */
  return last;
}

function holdAnchor(a) {
  if (!a) return;
  var node = null;
  try { node = els.cards.querySelector(a.sel); } catch (e) { return; }
  if (!node) return;
  var moved = node.getBoundingClientRect().top - a.top;
  /* A pixel of rounding is not a jump, and correcting it would cancel a smooth
     scroll that is legitimately in flight. */
  if (Math.abs(moved) < 2) return;
  ownScroll(function () { window.scrollBy(0, moved); });
}

/* And the same again for one late-decoding picture, which arrives long after any
   render has finished. */
function holdBelow(node, before) {
  var r = node.getBoundingClientRect();
  var grew = r.height - before;
  if (grew > 1 && r.top < 0) ownScroll(function () { window.scrollBy(0, grew); });
  return r.height;
}

/* "Was the lesson still being read when this arrived." Near the bottom counts,
   and so does having the newest card anywhere on screen -- because the board
   now parks that card at the TOP of the window, which on a long lesson is
   nowhere near the bottom of the document. Judging by the bottom alone would
   call that scrolled-away and offer a jump button for the card being read. */
function following() {
  if (nearBottom()) return true;
  var node = newestCardNode();
  if (!node) return false;
  var r = node.getBoundingClientRect();
  return r.bottom > 0 && r.top < window.innerHeight;
}

/* Applied after the reconcile rather than folded into a card's key. A card
   becomes superseded when the NEXT one is written, and rebuilding a card --
   re-parsing its markdown, re-typesetting its mathematics, dropping the ink
   layer drawn on it -- because something after it arrived is exactly the work
   the keyed reconcile exists to avoid. */
function paintSuperseded(set) {
  Array.prototype.forEach.call(els.cards.querySelectorAll("[data-card]"),
                               function (node) {
    var old = !!set[node.dataset.card];
    node.classList.toggle("superseded", old);
    if (!old) node.classList.remove("open");
    var head = node.querySelector(".card-head");
    if (!head) return;
    var tag = head.querySelector(".card-older");
    if (old && !tag) {
      tag = document.createElement("span");
      tag.className = "card-older";
      head.appendChild(tag);
    } else if (!old && tag) {
      tag.remove();
    }
    if (tag) tag.textContent = node.classList.contains("open") ? "fold" : "replaced";
    if (old && !head._foldable) {
      head._foldable = true;
      head.addEventListener("click", function () {
        if (!node.classList.contains("superseded")) return;
        node.classList.toggle("open");
        var t = head.querySelector(".card-older");
        if (t) t.textContent = node.classList.contains("open") ? "fold" : "replaced";
      });
    }
  });
}

/* Photos and PDFs only. Sent pages used to land here too, which is why answers
   appeared as a pile of thumbnails at the bottom of the screen with nothing to
   say which question they belonged to. They are part of the lesson now. */
function renderScratch(uploads) {
  els.scratchList.innerHTML = "";
  if (!uploads.length) {
    els.scratchList.innerHTML = '<p class="name">nothing uploaded yet. '
      + 'What you write goes into the lesson itself.</p>';
    return;
  }

  function tile(url, label, bust, doc) {
    url = atSession(url);
    var a = document.createElement("a");
    a.href = url;
    /* A PDF OPENS IN THE READER, to be written on: its id is the library's
       (`library.uploads`), and the ink is keyed on it until `board file`
       re-keys it to where the tutor files it. */
    if (doc) {
      a.addEventListener("click", function (e) {
        e.preventDefault();
        els.scratch.hidden = true;
        openDoc(doc, label);
      });
      a.className = "is-doc";
    }
    /* Never a new context. Installed to the home screen there is no browser
       chrome, so a raw image opened this way has no back button and no way out
       of it short of killing the app. Images open in a viewer this page owns
       and can close; anything else is left to the system. */
    var isImage = /\.(png|jpe?g|gif|webp|heic)(\?|$)/i.test(url);
    if (doc) {
      /* opened above */
    } else if (isImage) {
      a.addEventListener("click", function (e) {
        e.preventDefault();
        openViewer(bust ? url + "?t=" + Math.round(bust) : url, label);
      });
    } else {
      a.target = "_blank";
      a.rel = "noopener";
    }
    if (isImage) {
      var img = document.createElement("img");
      img.src = bust ? url + "?t=" + Math.round(bust) : url;
      img.loading = "lazy";
      a.appendChild(img);
    }
    var name = document.createElement("span");
    name.className = "name";
    name.textContent = label;
    a.appendChild(name);
    els.scratchList.appendChild(a);
  }

  uploads.slice().reverse().forEach(function (u) {
    tile(u.url, u.size ? u.name + "  ·  " + sizeWords(u.size) : u.name,
         0, u.doc || "");
  });
}

/* ------------------------------------------------------------ past lessons */
/* Reading an old lesson is reading the same transcript, so it goes through the
   same renderer. The live stream is what is suspended, not the page: whatever
   arrives while you are reading is still there when you come back. */
var reading = null;
var lastLive = null;
/* How many sittings this subject has filed, as of the last frame that said.
   `null` until one does: "it went up" has no answer before there is a number
   to compare with. */
var pastCount = null;

function openHistory() {
  var panel = document.getElementById("history");
  var list = document.getElementById("history-list");
  panel.hidden = false;
  list.innerHTML = '<p class="name">looking…</p>';
  api("/archive").then(function (r) { return r.json(); }).then(function (d) {
    var sessions = d.sessions || [];
    if (!sessions.length) {
      list.innerHTML = '<p class="name">no finished lessons yet.</p>';
      return;
    }
    list.innerHTML = "";
    sessions.forEach(function (s) {
      var row = document.createElement("div");
      row.className = "session-line";

      var b = document.createElement("button");
      b.type = "button";
      b.className = "session-row";
      b.innerHTML = '<span class="session-name"></span>'
                  + '<span class="session-sub"></span>';
      b.querySelector(".session-name").textContent =
        s.chapter || s.course || s.id;
      b.querySelector(".session-sub").textContent =
        [s.session, s.opened, s.cards + " cards",
         s.turns + " of yours"].filter(Boolean).join(" · ");
      b.addEventListener("click", function () { showSession(s.id); });
      row.appendChild(b);

      list.appendChild(row);
    });
  }).catch(function () {
    list.innerHTML = '<p class="name">could not read the archive.</p>';
  });
}

/* `then` is handed the sitting once it is on screen, or `null` if there was
   none to show. An address naming a card inside a past sitting has to wait for
   the sitting itself before it can ask whether that card is in it, and asking
   the server twice for the same lesson to find out is a second request for an
   answer already in hand. */
function showSession(id, then) {
  api("/archive/" + encodeURIComponent(id))
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (!d || d.ok === false) { if (then) then(null); return; }
      document.getElementById("history").hidden = true;
      reading = id;
      seenIds = {};
      firstPaint = true;
      var bar = document.getElementById("reading");
      bar.hidden = false;
      document.getElementById("reading-what").textContent =
        (d.state && (d.state.chapter || d.state.course)) || id;
      /* Its own marks, not the lesson's. `render` drops whatever the previous
         sitting left in the store before this lands. */
      render({ state: d.state || {}, cards: d.cards || [], turns: d.turns || [],
               notes: d.notes || {}, uploads: [], messages: [],
               archived: true });
      if (then) then(d);
    })
    .catch(function () { if (then) then(null); /* else stay where we are */ });
}

function backToLesson() {
  reading = null;
  seenIds = {};
  firstPaint = true;
  document.getElementById("reading").hidden = true;
  if (lastLive) render(lastLive);
}

/* ------------------------------------------------------------- the viewer */
/* Built once, on first use, and closed by three separate gestures, because the
   thing being fixed here is being stuck. */
var viewer = null;

function buildViewer() {
  viewer = document.createElement("div");
  viewer.id = "viewer";
  viewer.hidden = true;
  viewer.innerHTML = '<button id="viewer-close" type="button" title="close">✕</button>'
                   + '<figure><img alt=""><figcaption></figcaption></figure>';
  document.body.appendChild(viewer);
  viewer.addEventListener("click", function (e) {
    if (e.target === viewer || e.target.id === "viewer-close") closeViewer();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeViewer();
  });
}

function openViewer(url, label) {
  if (!viewer) buildViewer();
  viewer.querySelector("img").src = atSession(url);
  viewer.querySelector("figcaption").textContent = label || "";
  viewer.hidden = false;
  document.body.classList.add("viewing");
  viewer.querySelector("#viewer-close").focus();
}

function closeViewer() {
  if (!viewer || viewer.hidden) return;
  viewer.hidden = true;
  viewer.querySelector("img").src = "";
  document.body.classList.remove("viewing");
}


/* ------------------------------------------------------- annotating a card */
/* Marks over the tutor's own words. They save themselves shortly after the pen
   lifts, so a reload never costs them, and they are sent as their own kind of
   turn -- anchored to the card they sit on, because that is the question they
   are asking about. */
var noteSaveTimer = null;

/* THE TICKED CARDS GO TO THE TUTOR, and nothing else does. There is no "send
   everything unsent": a default like that re-delivered a card marked up
   yesterday as a fresh turn every time anything else was sent. What goes is
   what was ticked. A send is not a save: every save is the keeper's
   (`saveInk`). */
function sendNotes(ids) {
  if (!window.Annotate || !ids.length) return Promise.resolve([]);
  return Promise.all(ids.map(function (id) {
    var body = window.Annotate.payload(id, true);
    return api("/annotate/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function () {
      window.Annotate.clean(id);
      window.Annotate.sent(id);
    });
  }));
}

/* THE AUTOSAVE, and the only way ink reaches disk unasked: `inkkeep.js`. */
function saveInk() { return keeper ? keeper.save() : Promise.resolve([]); }

/* Not while a hand is on the glass: serialising a well-annotated card is real
   main-thread time, as with the slate's own autosave. The strokes are written
   the moment the hand stops; `pagehide` is the backstop. */
var noteSaveOwed = 0;
var NOTE_SAVE_WAIT = 8000;

function queueNoteSave() {
  if (!noteSaveOwed) noteSaveOwed = Date.now();
  if (noteSaveTimer) clearTimeout(noteSaveTimer);
  noteSaveTimer = setTimeout(function () {
    /* Deferred, but not indefinitely: a hand that reads and scrolls for a
       minute is a hand that is never idle, and ink that has not reached disk in
       eight seconds has waited long enough. */
    if (Date.now() - noteSaveOwed < NOTE_SAVE_WAIT
        && (penBusy() || (window.Annotate && window.Annotate.busy()))) {
      queueNoteSave();
      return;
    }
    noteSaveOwed = 0;
    saveInk();
  }, 900);
}

/* The annotation tools: `annbar.js`, the one bar every page that writes on
   something mounts. Its "done" turns the mode off. The clipboard is shared with
   both writing surfaces, so it fills up without anything on the lesson being
   touched; the bar listens to it itself, so copying on the slate is what makes
   Paste worth offering on a card. */
var annBar = window.AnnBar && window.Annotate
  ? window.AnnBar.mount({ kind: "annbar-board", where: "card",
                          onDone: function () { setAnnotating(false); } })
  : { show: function () {}, paint: function () {} };

if (window.Annotate) {
  window.Annotate.onChange(function () {
    queueNoteSave();
    annBar.paint();
    paintNotesSend();
    /* The offer of a marked copy appears the moment there IS writing on the
       document, and goes away when the last stroke is erased. */
    if (reader) reader.paintKeep();
  });
  /* A closing tab must not take the last sentence still being typed. The
     last stroke is the keeper's: it flushes on `pagehide` itself. */
  window.addEventListener("pagehide", function () { flushTextDraft(); });
}

function setAnnotating(next) {
  if (!window.Annotate) return;
  window.Annotate.setOn(next);
  annBar.show(next);
  els.annotate.setAttribute("aria-pressed", next ? "true" : "false");
  els.annotate.title = next ? "stop writing on the lesson"
                            : "write on the lesson itself";
  /* The same mode, reported on whichever control is actually reachable. A
     document is read full-screen over the chrome, so while one is open the pen
     on the reader's bar is the only one of the two anybody can see. */
  var pen = reader && reader.els.pen;
  if (pen) {
    pen.setAttribute("aria-pressed", next ? "true" : "false");
    pen.title = next ? "stop writing on this page" : "write on this page";
  }
  annBar.paint();
}

els.annotate.onclick = function () {
  setAnnotating(!window.Annotate.isOn());
};

/* The calculator floats over the lesson; calc.js owns the panel and this owns
   the menu entry, which says whether it is showing. Reopened after a reload if
   it was open, like the rest of its state. */
if (els.calc && window.Calc) {
  var paintCalc = function (on) {
    els.calc.setAttribute("aria-pressed", on ? "true" : "false");
    els.calc.textContent = on ? "±  hide the calculator" : "±  calculator";
  };
  window.Calc.onChange(paintCalc);
  els.calc.onclick = function () { window.Calc.toggle(); };
  if (window.Calc.wasOpen()) window.Calc.open();
}

/* ----------------------------------------------- sending the annotations */

function haveNotes() {
  return !!(window.Annotate && window.Annotate.unsent().length);
}

/* What Send does: the working goes first, unconditionally, and alone. Marks on
   the lesson go only through the picker. A Send that asks a question first is
   a Send that does nothing. The one exception: an empty surface with unsent
   marks opens the picker, because the marks are what is being handed in. */
function askWhatToSend(sendWork) {
  var written = !writer || writer.strokes() > 0;
  if (!written && haveNotes()) {
    openNotePick();
    return;
  }
  sendWork();
}

window.askWhatToSend = askWhatToSend;

/* WHICH MARKED RESPONSES GO, chosen by ticking them.

   Every card with marks on it is a row, and only those, so with nothing marked
   there is nothing to tick and nothing can be sent. A card whose marks were
   delivered is listed as sent and starts unticked; ticking it sends it again.
   Ticks are kept while the picker is open and forgotten when it closes. */
var pickTicked = null;

function cardById(id) {
  var found = null;
  ((lastLive && lastLive.cards) || []).forEach(function (c) {
    if (c.id === id) found = c;
  });
  return found;
}

/* The first line a person would read, markdown stripped to its words. */
function cardFirstLine(c) {
  var lines = ((c && c.body) || "").split("\n");
  for (var i = 0; i < lines.length; i++) {
    var t = lines[i].replace(/<[^>]*>/g, "").replace(/[#*_`>$\\]/g, "")
                    .replace(/\s+/g, " ").trim();
    if (t) return t.length > 80 ? t.slice(0, 79) + "…" : t;
  }
  return "";
}

function ageLabel(t) {
  if (!t) return "";
  var s = Math.max(0, Date.now() / 1000 - t);
  if (s < 60) return "just now";
  if (s < 3600) return Math.floor(s / 60) + " min ago";
  if (s < 86400) return Math.floor(s / 3600) + " h ago";
  return Math.floor(s / 86400) + " d ago";
}

function pickIds() {
  if (!window.Annotate) return [];
  /* Newest first: the card just marked is the one most likely wanted. */
  return window.Annotate.marked().slice().sort().reverse();
}

function paintNotePick() {
  if (!els.notepick || els.notepick.hidden) return;
  var ids = pickIds();
  var unsent = window.Annotate ? window.Annotate.unsent() : [];
  var ticked = {};
  ids.forEach(function (id) {
    ticked[id] = (id in pickTicked) ? pickTicked[id] : unsent.indexOf(id) !== -1;
  });
  pickTicked = ticked;
  els.notepickList.textContent = "";
  ids.forEach(function (id) {
    var c = cardById(id);
    var row = document.createElement("div");
    row.className = "notepick-row";
    row.dataset.card = id;
    var tick = document.createElement("label");
    tick.className = "notepick-tick";
    var box = document.createElement("input");
    box.type = "checkbox";
    box.checked = !!ticked[id];
    box.setAttribute("aria-label", "send card " + id);
    box.addEventListener("change", function () {
      pickTicked[id] = box.checked;
      paintPickCount();
    });
    tick.appendChild(box);
    var go = document.createElement("button");
    go.type = "button";
    go.className = "notepick-go";
    go.innerHTML = '<span class="notepick-name"></span><span class="notepick-sub"></span>';
    go.querySelector(".notepick-name").textContent =
      (c && (cardTitle(c) || cardFirstLine(c))) || "card " + id;
    var sub = [(c && (KIND_LABEL[c.kind] || c.kind)) || "card", id];
    if (c && c.mtime) sub.push(ageLabel(c.mtime));
    if (unsent.indexOf(id) === -1) sub.push("sent");
    go.querySelector(".notepick-sub").textContent = sub.join(" · ");
    go.addEventListener("click", function () { pickJump(id); });
    row.appendChild(tick);
    row.appendChild(go);
    els.notepickList.appendChild(row);
  });
  els.notepickEmpty.hidden = ids.length > 0;
  els.notepickList.hidden = !ids.length;
  paintPickCount();
}

function pickChosen() {
  return pickIds().filter(function (id) { return pickTicked && pickTicked[id]; });
}

function paintPickCount() {
  var ids = pickIds();
  var n = pickChosen().length;
  els.notepickSend.textContent = "send " + n;
  els.notepickSend.disabled = !n || pickSending;
  els.notepickAll.disabled = !ids.length;
  /* All until everything is ticked, then none. */
  els.notepickAll.textContent = ids.length && n === ids.length ? "none" : "all";
}

function openNotePick() {
  if (!els.notepick) return;
  pickTicked = {};
  els.notepick.hidden = false;
  paintNotePick();
}

function closeNotePick() {
  if (!els.notepick) return;
  els.notepick.hidden = true;
  pickTicked = null;
}

/* The card under the glass, where `revealNewest` puts the newest one. */
function pickJump(id) {
  closeNotePick();
  var node = null;
  try { node = els.cards.querySelector('[data-card="' + id + '"]'); } catch (e) {}
  if (!node) return;
  revealCard(node, true);
  node.classList.add("landed");
  window.setTimeout(function () { node.classList.remove("landed"); }, 2400);
}

var pickSending = false;

function pickSend() {
  var ids = pickChosen();
  if (!ids.length || pickSending) return;
  pickSending = true;
  els.notesend.disabled = true;
  paintPickCount();
  /* Same rule as the board's Send: say something on the frame the button was
     pressed. What follows encodes a picture per card and waits on a request
     for each. */
  saySending();
  sendNotes(ids).then(function () {
    pickSending = false;
    els.notesend.disabled = false;
    closeNotePick();
    paintNotesSend();
    toastSent();
  }, function () {
    pickSending = false;
    els.notesend.disabled = false;
    paintPickCount();
  });
}

if (els.notepick) {
  els.notepickSend.onclick = pickSend;
  els.notepickClose.onclick = closeNotePick;
  els.notepickAll.onclick = function () {
    var ids = pickIds();
    var all = ids.length && pickChosen().length === ids.length;
    ids.forEach(function (id) { pickTicked[id] = !all; });
    paintNotePick();
  };
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !els.notepick.hidden) closeNotePick();
  });
  /* A tap outside closes it. The button that opened it is not outside: its own
     tap toggles, through the stack. */
  document.addEventListener("pointerdown", function (e) {
    if (els.notepick.hidden) return;
    if (els.notepick.contains(e.target) || els.notesend.contains(e.target)) return;
    closeNotePick();
  }, true);
}

/* Its tap is registered with the moveable stack: `Recentre` tells a tap from a
   press-and-hold to move it, and a `click` listener of its own would fire
   alongside. */
function notesTap() {
  if (els.notepick.hidden) openNotePick(); else closeNotePick();
}

/* Always on the glass. Marks can be made at any time -- on a card from ten
   minutes ago, with no question owed and no Send button anywhere on the page --
   and a button that comes and goes with them is a button nobody learns the
   place of. With nothing marked it opens a picker that says so. */
function paintNotesSend() {
  var wasHidden = els.notesend.hidden;
  els.notesend.hidden = false;
  /* A widget in the stack is placed from JavaScript, so one that has just
     appeared has no place yet until it is measured and put there. */
  if (wasHidden) panicRemeasure();
  paintNotePick();
}


/* --------------------------------------------------- something to save yet? */
/* Leaving is silent. An app is swiped away, a lid closes, a lesson is put down
   mid-thought -- and none of those raise anything. So the state of the working
   tree is on the board: if there is uncommitted work, the save says so before
   you go, and if you come back to a session you left with work outstanding, the
   offer is put in front of you once rather than waiting to be found. */
var unsaved = 0;
var offeredOnReturn = false;
var lastUnsavedKnown = false;

function paintSave(n) {
  lastUnsavedKnown = (typeof n === "number");
  unsaved = lastUnsavedKnown ? n : 0;
  var has = unsaved > 0;
  els.save.classList.toggle("dirty", has);
  /* The word in its own span, so a phone can drop it and keep the count. */
  els.save.textContent = "⤓";
  var word = document.createElement("span");
  word.className = "bar-word";
  word.textContent = " save";
  els.save.appendChild(word);
  if (has) els.save.appendChild(document.createTextNode(" " + unsaved));
  els.save.title = has
    ? unsaved + " file(s) not yet committed — tap to save and push"
    : "everything here is committed";
}

function offerSaveOnReturn() {
  /* Only when there is genuinely something to lose, only once per return, and
     never on top of a decision already in front of the student. */
  if (!unsaved || offeredOnReturn || !els.finish.hidden) return;
  offeredOnReturn = true;
  els.finishLead.textContent = "Save this work?";
  els.finishSub.textContent = "You left with " + unsaved
    + " file(s) uncommitted. Commit and push them now — the lesson stays open.";
  els.finish.hidden = false;
}

document.addEventListener("visibilitychange", function () {
  if (document.hidden) offeredOnReturn = false;    /* arm it for the next return */
  else setTimeout(offerSaveOnReturn, 600);         /* after the first payload lands */
});


/* ------------------------------------------------------------ leaving here */
/* The back arrow is the ordinary way out of a lesson, and walking out of a
   lesson is exactly when uncommitted work gets left behind. The session itself
   is safe -- cards, turns and answers are files, and they are still here when
   you come back -- but what is on disk is not what is pushed. So the way out
   asks, every time, rather than only when the board happens to know something is
   outstanding. */
var leavingTo = null;

function askBeforeLeaving(href) {
  /* Nothing outstanding, nothing to ask about. A prompt that appears every time
     regardless is a prompt that gets dismissed without being read, which is how
     the one time it mattered gets dismissed too. `unsaved` is unknown (null) in
     a directory that is not a repository at all -- ask then, rather than assume.
   */
  if (unsaved === 0 && lastUnsavedKnown) { window.location.href = href; return; }
  leavingTo = href;
  els.finishLead.textContent = "Leaving this lesson.";
  els.finishSub.textContent = (unsaved > 0
      ? unsaved + " file(s) are not committed. "
      : "Everything here is already committed. ")
    + "The lesson is kept either way — it is still here when you come back.";
  els.finishYes.textContent = unsaved > 0 ? "Save and push" : "Push anyway";
  els.finishNo.textContent = "Stay";
  els.finishLeave.hidden = false;
  els.finish.hidden = false;
}

function goLeave() {
  var to = leavingTo || "/";
  leavingTo = null;
  els.finish.hidden = true;
  els.finishLeave.hidden = true;
  /* Announced before the page tears down: anything that needs a last word --
     an autosave of ink in progress, and whatever comes later -- gets it here
     rather than racing the navigation. */
  try {
    window.dispatchEvent(new CustomEvent("board:leave", { detail: { to: to } }));
  } catch (e) { /* an old engine without CustomEvent still leaves */ }
  if (keeper) keeper.flush();
  window.location.href = to;
}

els.home.addEventListener("click", function (e) {
  e.preventDefault();
  askBeforeLeaving(els.home.getAttribute("href") || "/");
});

els.finishLeave.onclick = goLeave;


/* ------------------------------------------------- one step, written for them */
/* The health strip under the bar: the worst line first, all of them in its
   tooltip. Hidden while the cluster is well. */
function paintHealth(h) {
  if (!els.healthbar) return;
  var lines = (h && h.lines) || [];
  els.healthbar.hidden = lines.length === 0;
  els.healthText.textContent = lines.length
    ? lines[0] + (lines.length > 1 ? "  (+" + (lines.length - 1) + " more)" : "")
    : "";
  els.healthbar.title = lines.join("\n");
  els.healthbar.classList.toggle("down", !!(h && h.down));
}

/* One step, written for them, and the session stays in teach. Painted before
   the answer comes back: the payload that carries it is a poll away, and a
   control that does nothing for a second is a control somebody taps again. */
function handOver(card, button) {
  if (button) {
    button.disabled = true;
    button.textContent = "handed over";
  }
  api("/handover", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ card: card })
  }).catch(function () { /* the payload will say what actually happened */ });
}

/* ------------------------------------------------- where the board is now */
/* The surface on the glass, spelled as an address in the bar, so a link to it
   can be copied off the glass: a document while one is open, else the lesson.
   Always `replaceState`, so the back button still leaves the board. */
var landed = false;

function remember() {
  addrShow(paperOpen ? { surface: "document:" + paperOpen }
                     : { surface: "lesson" });
}

/* Once per load, once a payload is here: an address in the bar is followed,
   against what the payload holds. */
function land() {
  if (landed || !addrWanted || !lastLive) return;
  landed = true;
  var asked = addrWanted;
  addrWanted = null;
  addrGo(asked);
}

/* ------------------------------------------------------------- addresses */
/* ONE RESOLVER. `address.js` is the grammar and has no opinion about browsers;
   this is the only thing anywhere that takes a session address, `#/s/<id>/…`,
   and puts the board on the surface it names.

     1. A NAME FROM A BROWSER NEVER REACHES A FILESYSTEM. Every component is
        looked up in what this page was handed -- `lastLive.cards`,
        `lastLive.uploads`, `lastLive.slate` -- or by id on the server. A miss
        is a miss, said plainly.
     2. A LINK THAT NO LONGER RESOLVES SAYS SO WHERE IT IS WRITTEN:
        `markAddresses` checks every address in the lesson against the same
        payload this resolver uses.
     3. TWO SPELLINGS OF AN ADDRESS IS TWO BUGS. `spell` is the only builder. */
var addrWanted = null;         /* an address waiting for the first payload */
var addrGoneSaid = Object.create(null);   /* address text -> why it is dead */

function ADDR() { return window.Address || null; }

function addrParse(text) {
  var g = ADDR();
  if (!g) return null;
  try { return g.parse(text); } catch (e) { return null; }
}

/* The one link speller on this page. Everything it is given is placed in THIS
   session, because a board can only make an address for where it is. */
function spell(spec) {
  var g = ADDR();
  if (!g || !SESSION) return "";
  var out = { session: SESSION }, k;
  for (k in spec) {
    if (Object.prototype.hasOwnProperty.call(spec, k)) out[k] = spec[k];
  }
  return g.format(out);
}

/* Where the board is now, in the bar, from `remember`. Always `replaceState`:
   the back button must still leave the board. */
function addrShow(here) {
  if (!here || !window.history || !window.history.replaceState) return;
  var want;
  if (typeof here.surface === "string"
             && here.surface.indexOf("document:doc/") === 0) {
    want = spell({ surface: "doc",
                   doc: here.surface.slice("document:doc/".length) });
  } else {
    /* THE LESSON, WITH NOTHING OVER IT -- and the bar may already name a card
       or a page of handwriting. Each IS the lesson with something pointed out
       on it, neither can be spelled from `here`, and overwriting one with the
       bare session takes a link off the glass a second after it was followed.
       Never downgrade. */
    var now = addrParse(window.location.hash || "");
    if (now && now.session === SESSION && now.surface !== "session") return;
    want = spell({ surface: "session" });
  }
  if (!want || want === window.location.hash) return;
  try {
    window.history.replaceState({}, "", window.location.pathname
                                        + (window.location.search || "") + want);
  } catch (e) { /* a browser that refuses keeps the bar it had */ }
}

/* What the board says about where a link put it, or failed to. `els.pushed` is
   the page's one place for news, and news is what this is: it stays up until
   something newer happens rather than until a timer says so. */
function addrSaid(icon, text, bad) {
  els.pushed.hidden = false;
  els.pushed.className = bad ? "pushed bad" : "pushed";
  els.pushedIcon.textContent = icon;
  els.pushedText.textContent = text;
  offerDocument(null);      /* the banner's buttons belong to a document */
}

function addrDead(a, why) {
  addrGoneSaid[a.text] = why;
  markAddresses();
  addrSaid("✕", why, true);
  return "gone";
}

function addrArrived(a) {
  delete addrGoneSaid[a.text];
  markAddresses();
  return "ok";
}

/* Everything over the lesson goes, because an address is somebody saying where
   they want to be and a drawer left open is a drawer sitting on top of it. */
function addrShut() {
  [els.scratch, document.getElementById("history")].forEach(function (p) {
    if (p) p.hidden = true;
  });
  if (paperOpen) closeReader();
  closeViewer();
}

/* A card, anywhere in whatever transcript is on screen. Lit for a moment: a
   lesson is a wall of text, and "it scrolled somewhere" is not "here". */
function addrToCard(id) {
  var node = null;
  try { node = els.cards.querySelector('[data-card="' + id + '"]'); }
  catch (e) { return false; }
  if (!node) return false;
  if (node.scrollIntoView) node.scrollIntoView({ block: "start" });
  node.classList.add("landed");
  window.setTimeout(function () { node.classList.remove("landed"); }, 2400);
  return true;
}

function addrHolds(card) {
  return ((lastLive && lastLive.cards) || []).some(function (c) {
    return c.id === card;
  });
}

/* A card of this session. One older than the cards held is fetched, a
   window at a time, before it is called gone. */
function addrSessionCard(a) {
  if (addrHolds(a.card)) {
    addrShut();
    if (reading) backToLesson();
    window.setTimeout(function () {
      if (addrToCard(a.card)) addrArrived(a);
      else addrDead(a, "card " + a.card + " is not in this session");
    }, 0);
    return;
  }
  var first = ((model && model.cards) || [])[0];
  if (olderLeft && first && parseInt(a.card, 10) < parseInt(first.id, 10)) {
    fetchOlder(function (more) {
      if (more) addrSessionCard(a);
      else addrDead(a, "card " + a.card + " is not in this session");
    });
    return;
  }
  addrDead(a, "card " + a.card + " is not in this session");
}

/* Another session's address is that session's board, with the address
   carried whole; this one's names the session, a card, a document or a page
   of the slate here. */
function addrGo(a) {
  if (!a || !a.session) return "bad";
  if (a.session !== SESSION) {
    window.location.href = "/s/" + encodeURIComponent(a.session) + "/board" + a.text;
    return "elsewhere";
  }
  if (a.surface === "session") return addrArrived(a);
  if (a.surface === "card") {
    addrSessionCard(a);
    return "ok";
  }

  addrShut();
  if (reading) backToLesson();

  if (a.surface === "doc") {
    /* A PDF handed to the session, else any document of its subject, found
       by the server by its id (`library.readable`); a miss is said by
       `readKind` in its own sentence. */
    var known = null;
    ((lastLive && lastLive.uploads) || []).forEach(function (u) {
      if (!known && u.doc === a.doc) known = { id: u.doc, name: u.name };
    });
    if (!known) known = { id: a.doc, name: "" };
    openDoc(known.id, known.name, function (got) {
      if (!got) return;              /* `readKind` has already said why */
      if (!a.page) { addrArrived(a); return; }
      var pages = reader.els.pages.querySelectorAll(".lib-page img");
      if (a.page > pages.length) {
        addrDead(a, (known.name || "that document") + " has "
                 + (pages.length === 1 ? "one page" : pages.length + " pages")
                 + ", so there is no page " + a.page);
        return;
      }
      if (pages[a.page - 1].scrollIntoView) {
        pages[a.page - 1].scrollIntoView({ block: "start" });
      }
      addrArrived(a);
    });
    return "ok";
  }

  if (a.surface === "slate") {
    var page = null;
    ((lastLive && lastLive.slate) || []).forEach(function (p) {
      if (p.page === a.page) page = p;
    });
    if (!page) return addrDead(a, "there is no page " + a.page + " on the slate");
    openViewer(page.url, "slate — page " + a.page);
    return addrArrived(a);
  }

  return "bad";
}

/* Whether an address can be resolved RIGHT NOW, without opening anything, and
   why not. Only a card of this session is pre-checked: another session's is
   that board's to answer, a card older than the window held is fetched on the
   tap rather than called gone here, and a document is only answerable by
   asking the server. */
function addrMisses(a) {
  var first = ((model && model.cards) || [])[0];
  if (a.session !== SESSION || a.surface !== "card"
      || (first && a.card < first.id)) return "";
  return addrHolds(a.card) ? "" : "card " + a.card + " is not in this session";
}

/* EVERY ADDRESS WRITTEN INTO THE LESSON, MARKED WHERE IT IS WRITTEN. A dead
   link reads as dead in its own sentence; it never quietly lands somewhere
   near. Gibberish -- an old `#/w/` link among it -- is a third thing again
   and says so. */
function markAddresses() {
  var links, i, el, a, why;
  try { links = els.cards.querySelectorAll('a[href^="#/"]'); }
  catch (e) { return; }
  for (i = 0; i < links.length; i++) {
    el = links[i];
    el.classList.add("addr");
    a = addrParse(el.getAttribute("href"));
    if (!a) {
      el.classList.add("bad");
      el.classList.remove("dead");
      el.title = "this is not an address";
      continue;
    }
    el.classList.remove("bad");
    why = addrGoneSaid[a.text] || addrMisses(a);
    if (why) el.classList.add("dead"); else el.classList.remove("dead");
    el.title = why || a.text;
  }
}

/* Read once, before anything is painted, so a cold start on a link lands where
   the link said rather than where this board was last left. */
addrWanted = addrParse((window.location && window.location.hash) || "");

window.addEventListener("hashchange", function () {
  var a = addrParse(window.location.hash || "");
  if (!a) return;               /* not an address; the bar is not ours to mind */
  addrGo(a);
});


/* The overflow menu. Closing on any choice matters more than it looks: on a
   tablet a menu that stays open after a tap is a menu that swallows the next
   one. */
document.getElementById("btn-more").onclick = function (e) {
  e.stopPropagation();
  closeHeaderMenus();
  els.barmenu.hidden = !els.barmenu.hidden;
  if (!els.barmenu.hidden) placeMenu();
};

/* WHERE THE MENU GOES AND HOW MUCH ROOM IT HAS, measured against the VISIBLE
   viewport (`window.visualViewport`), never `innerHeight`: the keyboard and a
   pinch change what can be seen and not the layout viewport, and a menu capped
   taller than the screen does not overflow, so iOS scrolls the page instead.
   It hangs from the real bottom of the chrome stack, whose banners come and
   go. (It lives outside `#chrome` in `board.html`: WebKit does not hand a
   touch drag to a scroller inside a sticky element.) */
function placeMenu() {
  if (!els.barmenu || els.barmenu.hidden) return;
  var vv = window.visualViewport;
  var h = vv ? vv.height : window.innerHeight;
  var oy = vv ? vv.offsetTop : 0;
  var ox = vv ? vv.offsetLeft : 0;
  var w = vv ? vv.width : window.innerWidth;
  var pad = 12;
  /* Under the whole stack, not under the title bar: the menu opens below
     whatever banners are up, because opening behind one hides its first
     entries. Never above the top of the glass, and never pushed so far down
     that there is no room left underneath it. */
  var stack = els.chrome ? els.chrome.getBoundingClientRect().bottom : 0;
  var top = Math.min(Math.max(stack + 4, oy + 4), oy + h - 140);
  /* `right` is measured from the LAYOUT viewport's right edge, because that is
     what `position: fixed` is fixed to -- so the visible right edge has to be
     put back in those terms. */
  var right = Math.max(6, window.innerWidth - (ox + w) + 10);
  els.barmenu.style.top = top + "px";
  els.barmenu.style.right = right + "px";
  /* And the floor is the top of the writing toolbar, not the bottom of the
     glass. `#drawbar` is fixed to the bottom and grows UPWARD -- it is
     `column-reverse`, so the slate's own menu and its selection bar open above
     the tool row -- and on a board with the pen out it reaches well into the
     lower half of this menu. Being painted on top of it is not the same as not
     overlapping it: an entry drawn over a black tool bar is still an entry
     nobody can read. */
  var floor = oy + h;
  if (els.drawbar && !els.drawbar.hidden) {
    var bar = els.drawbar.getBoundingClientRect();
    if (bar.height > 0 && bar.top < floor) floor = bar.top;
  }
  /* Never so small that it is a scroller with one entry in it: below this the
     menu is the wrong shape for the screen and the cap is the lesser problem. */
  els.barmenu.style.maxHeight = Math.max(140, floor - top - pad) + "px";
  menuCue();
}

/* Placed again while it is open, because everything this measures moves: the
   keyboard comes up under a typed answer, a banner lands in the stack, the iPad
   is turned. Coalesced to one placement a frame -- a forced layout per scroll
   event is how a page that is merely scrolling starts to stutter, which is the
   same reason `panicSoon` exists. */
var menuFrame = 0;

function placeMenuSoon() {
  if (menuFrame || !els.barmenu || els.barmenu.hidden) return;
  menuFrame = window.requestAnimationFrame(function () {
    menuFrame = 0;
    placeMenu();
  });
}

/* Is there more below, and is the person being told? On iOS a scroller shows
   no bar until a finger is already on it, so a capped menu and a truncated one
   look the same from a foot away -- which is the defect again in a new coat.
   The fade at the bottom edge is the difference, and it goes when the end of
   the list is reached, because a permanent one says "more" about nothing. */
function menuCue() {
  var m = els.barmenu;
  if (!m || m.hidden) return;
  var left = m.scrollHeight - m.clientHeight - m.scrollTop;
  m.classList.toggle("more", left > 4);
}

/* Turning the iPad, the keyboard coming up, a pinch, a banner arriving: all of
   them change where the menu can be and how much of it fits. The visual
   viewport is the one that reports the first three; the window is the fallback
   for anything without it. */
["resize", "orientationchange", "scroll"].forEach(function (ev) {
  window.addEventListener(ev, placeMenuSoon, { passive: true });
});
if (window.visualViewport) {
  ["resize", "scroll"].forEach(function (ev) {
    window.visualViewport.addEventListener(ev, placeMenuSoon);
  });
}
els.barmenu.addEventListener("scroll", menuCue, { passive: true });
Array.prototype.forEach.call(els.barmenu.querySelectorAll("button"), function (b) {
  b.addEventListener("click", function () { els.barmenu.hidden = true; });
});
document.addEventListener("click", function (e) {
  if (els.barmenu.hidden) return;
  if (!els.barmenu.contains(e.target)) els.barmenu.hidden = true;
});


/* ---------------------------------------------------- the session header
   Four controls and no more (`test/link.js` counts `.sess-ctl`): the subject
   chip, the teach/do toggle, Make and End. Each paints from the payload's
   state, which is the session's session.json, and after a tap from the
   server's answer, so a bind or a flip shows before the next payload does. */
var headerState = {};
/* What a bind just set, held over a payload built before it landed. */
var boundTo = null;
/* A flip on its way to the server: the payload does not paint over it. */
var modeAsked = null;
var endArmed = 0;
/* Which kind of subject the picker's form is making, and its patient-data
   answer: null until a project's is given. */
var making = null;
var makingPhi = null;

/* A stored session's state always carries `subject`, null while unbound. A
   workspace's state (the one-session test server) never does, and is named
   by its course as before. */
function isStoredState(state) {
  return Object.prototype.hasOwnProperty.call(state || {}, "subject");
}

function paintHeader(state) {
  var st = Object.assign({}, state || {});
  if (boundTo) {
    if (st.subject === boundTo.id || Date.now() - boundTo.at > 8000) boundTo = null;
    else { st.subject = boundTo.id; st.course = boundTo.name; }
  }
  headerState = st;
  var stored = isStoredState(st);
  var bound = !stored || !!st.subject;
  els.course.textContent = !stored ? (st.course || "board")
    : bound ? (st.course || st.subject) : "unbound";
  els.subjectBtn.dataset.bound = bound ? "1" : "0";
  els.subjectBtn.title = bound
    ? "this session is about " + els.course.textContent + " (tap to change)"
    : "this session is not bound to a course or project yet (tap to bind it)";
  paintMode(modeAsked || (st.mode === "do" ? "do" : "teach"));
  var ended = !!st.ended;
  if (ended) document.body.dataset.ended = "1";
  else delete document.body.dataset.ended;
  els.endedbar.hidden = !ended;
  paintClusterCode(st);
  els.subjectBtn.disabled = ended;
  els.modeBtn.disabled = ended;
  els.makeBtn.disabled = ended;
  if (!els.makemenu.hidden) paintMake();
  if (ended) {
    disarmEnd();
    els.endBtn.disabled = true;
    els.endBtn.textContent = "ended";
    els.endBtn.title = "this session ended " + st.ended;
  } else if (!endArmed && els.endBtn.textContent === "ended") {
    els.endBtn.disabled = false;
    els.endBtn.textContent = "end";
    els.endBtn.title = "end this session (tap twice)";
  }
}

/* CODING AT THE CLUSTER. session.json `code` is set while a coding session
   holds paths there (`cluster.Ear` hears its ref): the strip shows the exact
   command, `board code <id> <paths>`, and the last step. Before it starts the
   overflow menu's entry opens the strip with `board code <id> ` to copy and
   the paths left to type. */
var clusterCodeAsked = false;

function clusterCommand(st) {
  var code = st.code || null;
  var paths = (code && code.paths) || [];
  return "board code " + (st.id || "") + (paths.length ? " " + paths.join(" ") : " ");
}

function paintClusterCode(st) {
  if (!els.codebar) return;
  var stored = isStoredState(st) && !!st.id;
  var code = st.code && st.code.ref ? st.code : null;
  if (els.codeBtn) els.codeBtn.hidden = !stored || !!code;
  var show = stored && (!!code || clusterCodeAsked);
  els.codebar.hidden = !show;
  if (!show) return;
  var cmd = clusterCommand(st);
  if (els.codeCmd.value !== cmd) els.codeCmd.value = cmd;
  els.codeClose.hidden = !!code;
  if (code) {
    els.codeStep.textContent = code.step ? "step " + code.step : "no step yet";
    els.codeStep.title = code.sha ? "code/" + st.id + " at " + String(code.sha).slice(0, 12) : "";
  } else {
    els.codeStep.textContent = "then the paths you will write";
    els.codeStep.title = "";
  }
}

if (els.codeCopy) els.codeCopy.onclick = function () {
  var text = els.codeCmd.value;
  var said = function (word) {
    els.codeCopy.textContent = word;
    setTimeout(function () { els.codeCopy.textContent = "copy"; }, 1500);
  };
  try { els.codeCmd.select(); } catch (e) { /* not selectable here */ }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(function () { said("copied"); },
      function () { said(document.execCommand && document.execCommand("copy") ? "copied" : "select it"); });
  } else {
    said(document.execCommand && document.execCommand("copy") ? "copied" : "select it");
  }
};
if (els.codeBtn) els.codeBtn.onclick = function () {
  els.barmenu.hidden = true;
  clusterCodeAsked = true;
  paintClusterCode(headerState);
};
if (els.codeClose) els.codeClose.onclick = function () {
  clusterCodeAsked = false;
  paintClusterCode(headerState);
};

function paintMode(mode) {
  els.modeBtn.dataset.now = mode;
  els.modeBtn.ariaPressed = mode === "do" ? "true" : "false";
}

function postJson(url, body) {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {})
  }).then(function (r) {
    return r.json().catch(function () { return { ok: false, error: "HTTP " + r.status }; });
  });
}

/* Header menus: one open at a time, hung under the chrome stack. */
function closeHeaderMenus() {
  els.makemenu.hidden = true;
  els.subjpick.hidden = true;
}

function hangMenu(menu) {
  var stack = els.chrome ? els.chrome.getBoundingClientRect().bottom : 0;
  menu.style.top = Math.max(stack + 4, 4) + "px";
}

/* TEACH OR DO. The toggle flips session.json `mode` through `POST /mode`. */
els.modeBtn.onclick = function () {
  if (headerState.ended || modeAsked) return;
  var was = els.modeBtn.dataset.now === "do" ? "do" : "teach";
  var want = was === "do" ? "teach" : "do";
  modeAsked = want;
  paintMode(want);
  postJson(BASE + "/mode", { mode: want }).then(function (got) {
    modeAsked = null;
    paintMode(got && got.ok ? got.mode : was);
  }, function () {
    modeAsked = null;
    paintMode(was);
  });
};

/* MAKE: a write-up, a deck or a paper, from this session.

   write-up builds the session's own write-up now (`POST /hw/build`; the
   tutor adds to it as answers are agreed). deck and paper ask for a new
   document (`POST /artifact`): the server makes its doc.json and queues a
   `[writeup]` turn that writes and builds it, and the strip says when it is
   done. The line above them says what it is about; empty, it is this
   session. All three need a subject, so an unbound session says so. */
function openMakeMenu(e) {
  if (e && e.stopPropagation) e.stopPropagation();
  var open = els.makemenu.hidden;
  closeHeaderMenus();
  els.barmenu.hidden = true;
  if (open && !headerState.ended) {
    paintMake();
    els.makemenu.hidden = false;
    hangMenu(els.makemenu);
  }
}
els.makeBtn.onclick = openMakeMenu;

var makeAsking = false;

function makeSay(text) { els.makeSaid.textContent = text || ""; }

function paintMake() {
  var unbound = isStoredState(headerState) && !headerState.subject;
  [els.makeWriteup, els.makeDeck, els.makePaper].forEach(function (b) {
    b.disabled = makeAsking || unbound || !!headerState.ended;
  });
  if (unbound) makeSay("Bind this session to a course or project first: tap its chip.");
  else if (!makeAsking && /^Bind this session/.test(els.makeSaid.textContent)) makeSay("");
}

function askArtifact(make) {
  if (makeAsking) return;
  makeAsking = true;
  paintMake();
  var about = (els.makeAbout.value || "").trim();
  makeSay("asking for " + (make === "deck" ? "a deck" : "a paper") + "…");
  postJson(BASE + "/artifact", { make: make, about: about }).then(function (got) {
    makeAsking = false;
    if (!got || !got.ok) { paintMake(); makeSay("Not asked: " + ((got && got.error) || "refused")); return; }
    els.makeAbout.value = "";
    paintMake();
    makeSay((make === "deck" ? "A deck" : "A paper") + " is being written: "
            + (got.source || "its file") + ". The strip says when it is done.");
  }, function () {
    makeAsking = false;
    paintMake();
    makeSay("Not asked: the server did not answer.");
  });
}

els.makeDeck.onclick = function (e) { e.stopPropagation(); askArtifact("deck"); };
els.makePaper.onclick = function (e) { e.stopPropagation(); askArtifact("paper"); };
els.makeWriteup.onclick = function (e) {
  e.stopPropagation();
  if (makeAsking) return;
  makeAsking = true;
  paintMake();
  makeSay("building the write-up…");
  postJson(BASE + "/hw/build", {}).then(function (got) {
    makeAsking = false;
    paintMake();
    makeSay(got && got.ok ? "The write-up is built" + (got.pdf ? ": " + got.pdf : ".")
            : "Not built: " + ((got && (got.detail || got.error)) || "refused"));
  }, function () {
    makeAsking = false;
    paintMake();
    makeSay("Not built: the server did not answer.");
  });
};

/* END, after a second tap. The first arms it for four seconds. */
function disarmEnd() {
  if (endArmed) clearTimeout(endArmed);
  endArmed = 0;
  els.endBtn.classList.remove("armed");
  if (els.endBtn.textContent !== "ended") els.endBtn.textContent = "end";
}

els.endBtn.onclick = function (e) {
  e.stopPropagation();
  if (headerState.ended || els.endBtn.disabled) return;
  if (!endArmed) {
    els.endBtn.classList.add("armed");
    els.endBtn.textContent = "end? tap again";
    endArmed = setTimeout(disarmEnd, 4000);
    return;
  }
  disarmEnd();
  els.endBtn.disabled = true;
  els.endBtn.textContent = "ending…";
  postJson(BASE + "/end", {}).then(function (got) {
    if (got && got.ok) {
      var rec = got.session || {};
      paintHeader(Object.assign({}, headerState, { ended: rec.ended || "now" }));
    } else {
      els.endBtn.disabled = false;
      els.endBtn.textContent = "end";
      els.endBtn.title = "not ended: " + ((got && got.error) || "no answer");
    }
  }, function () {
    els.endBtn.disabled = false;
    els.endBtn.textContent = "end";
    els.endBtn.title = "not ended: the server did not answer";
  });
};

/* THE SUBJECT CHIP: pick a course or project, or make one, and bind. */
function pickSaid(text) { els.subjpickSaid.textContent = text || ""; }

els.subjectBtn.onclick = function (e) {
  e.stopPropagation();
  if (headerState.ended) return;
  var open = els.subjpick.hidden;
  closeHeaderMenus();
  els.barmenu.hidden = true;
  if (!open) return;
  making = null;
  makingPhi = null;
  els.subjpickForm.hidden = true;
  pickSaid("");
  els.subjpickList.textContent = "";
  els.subjpick.hidden = false;
  hangMenu(els.subjpick);
  fetch("/subjects.json").then(function (r) { return r.json(); }).then(function (got) {
    paintSubjects((got && got.subjects) || []);
  }, function () { pickSaid("The list of courses and projects did not come."); });
};

function paintSubjects(list) {
  var host = els.subjpickList;
  host.textContent = "";
  [["course", "Courses"], ["project", "Projects"]].forEach(function (g) {
    var some = list.filter(function (one) { return one.kind === g[0]; });
    if (!some.length) return;
    var head = document.createElement("div");
    head.className = "subjpick-group";
    head.textContent = g[1];
    host.appendChild(head);
    some.forEach(function (one) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = one.name || one.slug || one.id;
      b.dataset.subject = one.id;
      if (one.id === headerState.subject) b.className = "on";
      b.onclick = function (ev) { ev.stopPropagation(); bindTo(one.id); };
      host.appendChild(b);
    });
  });
  if (!host.firstChild) pickSaid("No courses or projects yet: make one below.");
}

function bindTo(id) {
  pickSaid("binding…");
  return postJson(BASE + "/bind", { subject: id }).then(function (got) {
    if (!got || !got.ok) { pickSaid((got && got.error) || "Not bound."); return; }
    boundTo = { id: got.subject.id, name: got.subject.name, at: Date.now() };
    paintHeader(Object.assign({}, headerState));
    closeHeaderMenus();
  }, function () { pickSaid("Not bound: the server did not answer."); });
}

function startMaking(kind) {
  making = kind;
  makingPhi = null;
  els.subjpickForm.hidden = false;
  els.subjpickPhi.hidden = kind !== "project";
  Array.prototype.forEach.call(els.subjpickPhi.querySelectorAll("button"),
                               function (b) { b.classList.remove("on"); });
  els.subjpickName.placeholder = kind === "project" ? "the project's name" : "the course's name";
  pickSaid("");
  try { els.subjpickName.focus(); } catch (e) { /* not focusable here */ }
}

document.getElementById("subjpick-course").onclick = function (e) {
  e.stopPropagation(); startMaking("course");
};
document.getElementById("subjpick-project").onclick = function (e) {
  e.stopPropagation(); startMaking("project");
};
["no", "yes"].forEach(function (word) {
  var b = document.getElementById("subjpick-phi-" + word);
  b.onclick = function (e) {
    e.stopPropagation();
    makingPhi = word === "yes";
    Array.prototype.forEach.call(els.subjpickPhi.querySelectorAll("button"),
                                 function (x) { x.classList.toggle("on", x === b); });
  };
});
document.getElementById("subjpick-go").onclick = function (e) {
  e.stopPropagation();
  var name = (els.subjpickName.value || "").trim();
  if (!making) return;
  if (!name) { pickSaid("Name it first."); return; }
  if (making === "project" && makingPhi === null) {
    pickSaid("Say whether it holds patient data."); return;
  }
  var body = { kind: making, name: name };
  if (making === "project") body.phi = makingPhi;
  pickSaid("making " + name + "…");
  postJson("/subjects/new", body).then(function (got) {
    if (!got || !got.ok) { pickSaid((got && got.error) || "Not made."); return; }
    els.subjpickName.value = "";
    bindTo(got.subject.id);
  }, function () { pickSaid("Not made: the server did not answer."); });
};

[els.subjpick, els.makemenu].forEach(function (menu) {
  menu.addEventListener("click", function (e) { e.stopPropagation(); });
});
document.addEventListener("click", function () {
  closeHeaderMenus();
  if (endArmed) disarmEnd();
});


/* What happened to the thing I just sent. Silence after sending is what makes a
   person tap Send again, or wonder whether the pen even worked. */
function paintSent() {
  /* ONE MORE STATE, CHOSEN RATHER THAN LEFT ALONE. "the tutor is reading it"
     stops being true the moment the card starts typing, and the strip is then on
     screen for the whole of the type-out -- which is the few seconds somebody is
     actually watching it. So the arrival gets its own words. */
  var owed = awaitingReply || (replyArriving() ? heldReply : null);
  if (!owed) { els.sent.hidden = true; return; }
  els.sent.hidden = false;
  var when = timeLabel(owed.t);
  var state = !awaitingReply ? "arriving"
            : attached ? (working ? "working" : "waiting") : "none";
  els.sent.dataset.state = state;
  els.sentText.textContent =
      state === "arriving" ? "sent at " + when + " — the answer is arriving"
    : state === "working" ? "sent at " + when + " — the tutor is reading it"
    : state === "waiting" ? "sent at " + when + " — waiting for the tutor"
    : "sent at " + when + " — no tutor is attached to read it yet";
}

/* ------------------------------------------------------------------ stream */
var source = null;
var linkDead = false;
var everGotData = false;
var attached = false;      /* is there a tutor on the other end at all */
var awaitingReply = null;  /* an answer sent and not yet replied to */
/* The same answer, kept while its reply is on its way onto the glass. The
   receipt cannot read it off the transcript any more: the card is in the
   payload, so `awaitingReply` is already null, and the thing the person is
   waiting for is still arriving. See `replyArriving`. */
var heldReply = null;
/* What was outstanding when the LAST payload was drawn, and whether a reply is
   landing on this one. It has to be remembered across payloads, because the card
   that answers a send arrives in the very payload that clears the send: by the
   time anything downstream asks, nothing is outstanding any more. The receipt
   reads it, and so does the trace, where it is the line that says whether a
   payload was recognised as a reply landing at all. */
var wasAwaiting = null;
var replyLanding = false;
var working = false;       /* and is it in the middle of a turn right now */
var sentAt = 0;            /* when begin was last tapped, so its label survives a frame */

/* An unreachable board used to be indistinguishable from an empty one: the shell
   comes out of the service worker's cache, the payload never arrives, and the
   page says "Nothing on the board yet" — which reads as "the tutor has not
   written", not as "you are looking at nothing live". The only signal that the
   link was down was a 0.55rem dot. So say it where the lesson would be. */
function paintLink(dead) {
  linkDead = dead;
  els.dot.className = dead ? "dot dead" : "dot live";
  els.dot.title = dead ? "not connected to the board" : "connected to the board";
  /* Never seen a payload: the page has nothing true on it, so this replaces the
     empty state. Seen one: keep the lesson readable and warn above it. */
  els.offline.hidden = !(dead && !everGotData);
  els.linkbad.hidden = !(dead && everGotData);
  if (dead && !everGotData) els.empty.hidden = true;
}

/* NOT WHILE THE NIB IS DOWN. A payload repaints the lesson, which costs the
   main thread the pen also needs, and payloads land constantly while writing.
   So a payload that arrives with a nib down is held, and only the NEWEST is
   drawn the moment the nib lifts. The window is the stroke itself, not
   `busy()`, whose tail runs for seconds. */
var heldPayload = null;
var heldTimer = null;
var heldSince = 0;
/* AND NEVER FOR LONG. A stroke is a second of somebody's life; a surface that
   believes one is still in progress is a lesson that has stopped updating, and
   that is a far worse failure than the stall this avoids. A nib lifted past the
   edge of the glass, a gesture the browser took for itself, an app sent to the
   background -- each of those can leave a stroke that never ends. So the hold
   has a ceiling, and past it the payload is drawn whatever the hand is doing. */
var HOLD_FOR = 700;

function inking() {
  try {
    if (writer && writer.inking && writer.inking()) return true;
    if (window.Annotate && window.Annotate.busy()) return true;
  } catch (e) { /* a surface that cannot answer is a surface that is not drawing */ }
  return false;
}

function drawHeld() {
  if (inking() && Date.now() - heldSince < HOLD_FOR) return;
  if (heldTimer) { clearInterval(heldTimer); heldTimer = null; }
  var data = heldPayload;
  heldPayload = null;
  if (!data) return;
  try { render(data); } catch (e) { /* a torn frame is not worth the lesson */ }
}

function renderOrHold(data) {
  if (!inking()) {
    heldPayload = null;
    if (heldTimer) { clearInterval(heldTimer); heldTimer = null; }
    render(data);
    return;
  }
  if (!heldPayload) { heldSince = Date.now(); trace("hold", { why: "nib down" }); }
  heldPayload = data;
  /* Polled rather than hung off pointerup, because a stroke does not always end
     with one: a nib lifted past the edge of the glass, a gesture the browser
     took for itself, an app sent to the background. A held payload that waits
     for an event that never comes is a lesson that stops updating. */
  if (!heldTimer) heldTimer = setInterval(drawHeld, 120);
}

/* ------------------------------------------------ the payload, kept whole */
/* THE SERVER SENDS THE WHOLE BOARD ONCE, THEN WHAT CHANGED: `cards_changed`,
   `cards_removed` and the top-level keys that moved, applied here to `model`.
   `render` is still handed a whole frame. A card that slides out of the
   server's window stays; only `cards_removed` removes. Older cards come on a
   tap (`fetchOlder`); what the subject holds comes from `/subject.json`. */
var model = null;
var olderLeft = 0;         /* cards older than the oldest one held */
var olderBusy = false;

function absorb(msg) {
  if (!msg || typeof msg !== "object") return null;
  if (!msg.delta) {
    model = msg;
    model.cards = sortCards(msg.cards || []);
    olderLeft = msg.cards_older || 0;
    return model;
  }
  /* A delta before any whole payload has nothing to apply to; the whole one
     is on its way. One the whole payload already holds changes nothing. */
  if (!model) return null;
  if (typeof msg.seq === "number" && typeof model.seq === "number"
      && msg.seq <= model.seq) return null;
  var byId = Object.create(null);
  (model.cards || []).forEach(function (c) { byId[c.id] = c; });
  (msg.cards_removed || []).forEach(function (id) { delete byId[id]; });
  (msg.cards_changed || []).forEach(function (c) { if (c && c.id) byId[c.id] = c; });
  model.cards = sortCards(Object.keys(byId).map(function (k) { return byId[k]; }));
  /* Fewer cards below the window means some were deleted; more means the
     window slid over cards this page still has. */
  if (typeof msg.cards_older === "number" && msg.cards_older < (model.cards_older || 0)) {
    olderLeft = Math.max(0, olderLeft - ((model.cards_older || 0) - msg.cards_older));
  }
  Object.keys(msg).forEach(function (k) {
    if (k === "delta" || k === "cards_changed" || k === "cards_removed") return;
    model[k] = msg[k];
  });
  return model;
}

function sortCards(list) {
  return list.slice().sort(function (a, b) {
    return (a.id || "").localeCompare(b.id || "");
  });
}

function shallow(o) {
  var out = {};
  for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) out[k] = o[k];
  return out;
}

/* A whole frame for `render`, which annotates the turns it is given: a copy,
   so the model stays what the server said. */
function frame() {
  var out = shallow(model);
  out.cards = (model.cards || []).map(shallow);
  out.turns = (model.turns || []).map(shallow);
  return out;
}

function paintOlder() {
  if (!els.older) return;
  var n = (model && !reading) ? olderLeft : 0;
  els.older.hidden = !n;
  els.older.disabled = olderBusy;
  els.older.textContent = olderBusy ? "fetching earlier cards…"
    : n + (n === 1 ? " earlier card" : " earlier cards");
}

/* `then(more)`, when given, is told whether any earlier card arrived. */
function fetchOlder(then) {
  var told = typeof then === "function" ? then : function () {};
  if (!model || olderBusy || !olderLeft) { told(false); return; }
  var first = (model.cards || [])[0];
  var before = first ? parseInt(first.id, 10) : 10000;
  if (!(before > 0)) { told(false); return; }
  olderBusy = true;
  paintOlder();
  api("/cards?before=" + before, { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (got) {
      olderBusy = false;
      if (!got || !got.ok || !model) { paintOlder(); told(false); return; }
      var byId = Object.create(null);
      (model.cards || []).forEach(function (c) { byId[c.id] = c; });
      (got.cards || []).forEach(function (c) { if (!byId[c.id]) byId[c.id] = c; });
      model.cards = sortCards(Object.keys(byId).map(function (k) { return byId[k]; }));
      olderLeft = got.older || 0;
      /* Their ink rides with them; the next delta's `notes` is the window's
         only, and `Annotate.load` keeps what it has already adopted. */
      model.notes = shallow(model.notes || {});
      model.notes_sent = shallow(model.notes_sent || {});
      Object.keys(got.notes || {}).forEach(function (k) { model.notes[k] = got.notes[k]; });
      Object.keys(got.notes_sent || {}).forEach(function (k) {
        model.notes_sent[k] = got.notes_sent[k];
      });
      renderOrHold(frame());
      told((got.cards || []).length > 0);
    }, function () { olderBusy = false; paintOlder(); told(false); });
}
if (els.older) els.older.onclick = function () { fetchOlder(); };

/* WHAT THE SUBJECT HOLDS, ASKED FOR RATHER THAN STREAMED. When the board
   opens, when the drawer does, when the page comes back into view, and on a
   push at least SUBJECT_EVERY ms after the last ask. No timer of its own: a
   board nothing is pushed to has nothing new to ask about, and the tick
   reads nothing outside the session. */
var subjectInfo = null;
var subjectAt = 0;
var subjectBusy = false;
var SUBJECT_EVERY = 30000;

function fetchSubject(then) {
  if (subjectBusy) return;
  subjectBusy = true;
  subjectAt = Date.now();
  api("/subject.json", { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (got) {
      subjectBusy = false;
      if (got && got.ok) takeSubject(got);
      if (then) then();
    }, function () { subjectBusy = false; if (then) then(); });
}

function subjectSoon() {
  if (!subjectBusy && Date.now() - subjectAt >= SUBJECT_EVERY) fetchSubject();
}

function takeSubject(got) {
  subjectInfo = got;
  if (got.unsaved !== undefined) paintSave(got.unsaved);
  if (lastLive && !lastLive.archived) {
    try { paintBusy(lastLive); } catch (e) { /* and so does the strip */ }
  }
}

document.addEventListener("visibilitychange", function () {
  if (!document.hidden && model) subjectSoon();
});

function connect() {
  if (source) source.close();
  source = new EventSource(BASE + "/events");
  source.onopen = function () { paintLink(false); };
  source.onerror = function () { paintLink(true); };
  source.onmessage = function (ev) {
    if (!ev.data) return;
    everGotData = true;
    paintLink(false);
    var data = null;
    try { data = absorb(JSON.parse(ev.data)); } catch (e) { /* a torn frame */ }
    if (!data) return;
    try { renderOrHold(frame()); } catch (e) { /* ignore a torn frame */ }
    subjectSoon();
  };
}

/* ------------------------------------------------------- the answer block */
/* The board is part of the lesson, not something laid over it: after each
   render it is moved into the card flow directly beneath the question it
   answers. Moving the node keeps the component alive; the strokes are redrawn
   from data afterwards, so nothing is lost even if the bitmap is not. */
var writer = null;
var pinnedTo = null;
/* Which question is open and which of my turns answers it, so Send knows
   whether it is starting an answer or correcting one. */
var answering = { question: null, turn: null, latest: null };
var loadedTurn = null;
/* Which question the student asked for the surface back on, or null for "not
   asked". Empty string means "asked, on a lesson with no open question". */
var reopenedFor = null;
/* The newest question as of the last render. The button below used to walk the
   card list itself and take the last question in payload order, while `render`
   takes the newest by mtime -- two answers to one question, and the request
   expiring the instant it was made if they ever disagreed. */
var lastNewestQ = "";
/* The newest card of any kind, for the same reason and read at the same moment. */
var lastNewestCard = "";
/* Which question they are answering, if they went back to an earlier one, and
   which question was newest when they went. A NEW question ends the excursion,
   as with `reopenedFor`: otherwise the surface stays pinned above it and the
   new question gets no board at all. */
var workingOn = null;
var workingOnAt = null;
/* Whether a CARRY set the pin, and whether it has already been carried across
   one new question. The grace belongs to a carry alone (its working is on no
   disk), and lasts one question: a pin that never lets go leaves a new
   question with no board. */
var pinCarried = false;
var pinHeld = false;
/* The board the surface is standing in for, as `render` last worked it out.
   `workingOn` is a request; this is the answer to it, and it is what
   `restoreAnswer` puts under the pen. */
var liveSlot = null;
/* Which slate page belongs to which board.

   A question is a CHAIN of boards: you write, hand it in, the tutor answers,
   and the next attempt carries on below the answer. Each attempt is a board
   that stays where it was written and can still be written on. A new attempt
   opens on a COPY of the one before, so the working carries forward and the
   board above keeps what it had. No page is ever destroyed.

   The record is one entry per BOARD, kept per course because the pages are:

       "<question>#<attempt>": { p: <page index>, a: <card it sits under> }

   `p` is missing on a board nobody has written on yet (it is cut on first
   touch). `a` is where the board sits: the newest board of a question floats
   to the end of its run, under the feedback it answers, until it is frozen. */
/* `p` IS A PAGE NUMBER, NOT AN INDEX INTO THE SURFACE'S ARRAY: the list comes
   back with only the pages ever saved, so an index slides. The key is
   versioned because records written as indices say nothing about it; a bumped
   key drops them and `repairPages` rebuilds from the turns on disk
   (`lesson/slate.py` carries the measurements). */
var PAGES_KEY = "board.pages.n";
var boardPage = {};
var pagesLoaded = false;

/* THE MAPPING BELONGS TO ONE LESSON, NOT TO A CHAPTER. Card numbers restart
   with each lesson, so under a chapter-wide key old records come back under
   new names: a phantom board above the live one, and a sheet shared and
   copied off. `opened` is rewritten when a lesson starts, so course, chapter
   and it name this one; `sittingKey` in `render` drops the annotation store at
   the same boundary. */
function pagesKey() {
  var st = (lastLive && lastLive.state) || {};
  return pagesScope(st) + ":" + (st.opened || "-");
}

/* A session names its own records; a board outside one keys by course and
   chapter, as a sitting did. */
function pagesScope(st) {
  return SESSION ? PAGES_KEY + ":s:" + SESSION
                 : PAGES_KEY + ":" + (st.course || "?") + ":" + (st.chapter || "-");
}

function loadPages() {
  var raw = {};
  try { raw = JSON.parse(localStorage.getItem(pagesKey()) || "{}") || {}; }
  catch (e) { raw = {}; }
  boardPage = {};
  for (var k in raw) {
    var v = raw[k];
    /* Before a question could have more than one board, the record was the page
       number alone under the question's own id. That is its first attempt, and
       where it sits is worked out on the next render. */
    if (typeof v === "number") boardPage[slotKey(k, 0)] = { p: v, a: null };
    else if (v && typeof v === "object") {
      boardPage[k.indexOf("#") === -1 ? slotKey(k, 0) : k] =
        { p: typeof v.p === "number" ? v.p : undefined, a: v.a || null };
    }
  }
  dropOtherSittings();
}

/* The records of every OTHER lesson on this chapter, thrown away: their card
   numbers mean something else now. The chapter's only -- another can be open
   in a second tab -- and nothing at all while this lesson cannot be named,
   because that key is the one it would be writing to. */
function dropOtherSittings() {
  var st = (lastLive && lastLive.state) || {};
  if (!st.opened) return;
  var mine = pagesKey();
  var here = pagesScope(st);
  var doomed = [];
  try {
    for (var i = 0; i < localStorage.length; i++) {
      var k = localStorage.key(i);
      if (!k || k === mine) continue;
      if (k === here || k.indexOf(here + ":") === 0) doomed.push(k);
    }
    doomed.forEach(function (k) { localStorage.removeItem(k); });
  } catch (e) { /* a full or locked store is not worth losing the lesson over */ }
}

/* The sitting was filed. Everything keyed to it goes with it.

   Called only on a rise in `history` -- see the guards where that is read. The
   slate's half is `Slate.reset`, which DROPS its pages rather than saving them:
   they are in the archive already, and writing them back into `live/slate/` is
   the whole of what this repairs. */
function lessonWasFiled() {
  boardPage = {};
  /* And the census of what was asked. The next sitting numbers its cards from
     0001 again, so every id in it means something else from now on. */
  seenQs = Object.create(null);
  seenAny = false;
  savePages();
  loadedTurn = null;
  reclaimSeen = null;
  reclaimOwed = null;
  if (writer && writer.reset) {
    try { writer.reset(); } catch (e) { /* a blank board beats a broken one */ }
  }
}

function savePages() {
  try { localStorage.setItem(pagesKey(), JSON.stringify(boardPage)); } catch (e) {}
}

/* A board's name is its question and which attempt it is. */
function slotKey(q, n) { return q + "#" + n; }
function slotQ(key) { return key.slice(0, key.lastIndexOf("#")); }
function slotN(key) {
  var n = parseInt(key.slice(key.lastIndexOf("#") + 1), 10);
  return isNaN(n) ? 0 : n;
}

/* Every board in the lesson, in reading order, as of the last render. What
   "the board before this one" means, which is the whole of the carry-over. */
var slotOrder = [];

/* Every question this LIVE lesson has asked, over every frame so far: what
   separates a board from a leftover record (`pageOwnedByOther`). It only grows,
   because a question missing from one frame (a card still being written) is
   not over. Empty until the first live frame with a question; while empty,
   every record counts. */
var seenQs = Object.create(null);
var seenAny = false;

/* The last board before this one that somebody has actually written on. A
   follow-up question gets a blank board; whether it belongs with the proof
   above is the person's call, so the working is brought forward by one tap,
   never by a guess. */
function prevInkSlot(key) {
  if (!writer || !writer.inkOn) return null;
  var i = slotOrder.indexOf(key);
  if (i < 0) i = slotOrder.length;
  for (var n = i - 1; n >= 0; n--) {
    var p = pageOf(slotOrder[n]);
    if (p !== undefined && writer.inkOn(p) > 0) return slotOrder[n];
  }
  return null;
}

/* Bring that working onto this board, as a COPY: from here the two go their
   own ways. Never over ink. The copy lands on the page this board already
   holds (cutting a second abandons the first, since `fresh` hands back only
   the trailing blank); the one case that cuts a sheet is a page this board
   SHARES with another board on the screen (`pagesKey`), the repair
   `restoreAnswer` makes too. Not under a pen that is down: `clone` counts only
   committed strokes, so this waits, as `syncSlots` does, and comes back. */
function carryOver(key) {
  if (!writer || !writer.clone) return;
  if (writer.writing && writer.writing()) { renderSoon(); return; }
  var rec = boardPage[key];
  if (!rec || (rec.p !== undefined && writer.inkOn(rec.p) > 0)) return;
  var from = prevInkSlot(key);
  var src = pageOf(from);
  if (src === undefined) return;
  var onto = pageOwnedByOther(rec.p, key) ? undefined : rec.p;
  rec.p = writer.clone(src, onto);
  savePages();
  loadedTurn = null;
}

/* Carrying the working onto a board is asking to WRITE on that board, so both
   controls that offer the carry pin the surface there too. The pin goes on
   BEFORE the copy, so the one render is already pinned, and with `workingOnAt`
   set, or the next frame lets it go. Not under a pen that is down
   (`carryOver`'s rule): the ask waits with the copy. */
function carryHere(key) {
  if (!key || !boardPage[key]) return;
  if (writer && writer.writing && writer.writing()) { renderSoon(); return; }
  workingOn = key;
  workingOnAt = lastNewestQ;
  reopenedFor = null;
  pinCarried = true;
  pinHeld = false;
  carryOver(key);
  if (lastLive) render(lastLive);
}

/* Come back to this in a moment, when the hand is off the glass. A payload is
   not due for thirty seconds and the board must not wait that long to catch up
   with itself. */
var soonTimer = null;
function renderSoon(ms) {
  clearTimeout(soonTimer);
  soonTimer = setTimeout(function () {
    if (lastLive) render(lastLive);
  }, ms || 1200);
}

/* Every board a question has, oldest attempt first. */
function slotsOf(q) {
  var out = [];
  for (var k in boardPage) { if (slotQ(k) === q) out.push(k); }
  out.sort(function (a, b) { return slotN(a) - slotN(b); });
  return out;
}

/* The one an answer goes on now: the last attempt of the question. */
function newestSlot(q) {
  var all = slotsOf(q);
  return all.length ? all[all.length - 1] : null;
}

function pageOf(key) {
  var rec = key && boardPage[key];
  return rec ? rec.p : undefined;
}

/* Does any OTHER board already own this page? One board per page: the slate
   hands back a trailing blank page, and two boards that reach it before either
   is written on would share it. The slate deals in ink, not questions. */
function pageOwnedByOther(n, key) {
  if (n === undefined || !n) return false;
  for (var k in boardPage) {
    if (k === key || boardPage[k].p !== n) continue;
    /* AND ANOTHER BOARD MEANS A BOARD THIS LESSON HAS. A record for a question the
       lesson never carried is not an owner, and counting it makes a live board copy
       itself off a good sheet. Ignored rather than deleted: deleting can throw away
       a record for a board somebody is writing on. */
    if (!seenAny || seenQs[slotQ(k)]) return true;
  }
  return false;
}

/* The chain of boards, brought up to date with the transcript. A board is
   frozen once what it holds was handed in AND the tutor has written since; the
   next attempt opens on a copy. Both halves are needed: it is the reply to an
   answer that ends an attempt. */
function syncSlots(qids, runEndOf, turns) {
  var changed = false;
  var handedIn = {};                  /* question -> the page its answer came off */
  (turns || []).forEach(function (t) {
    if (!t || t.kind !== "ink" || !t.answers) return;
    if (typeof t.page === "number") handedIn[t.answers] = t.page;
  });
  var ready = !!(writer && writer.ready && writer.ready());
  qids.forEach(function (q) {
    var end = runEndOf[q] || q;
    var key = newestSlot(q);
    if (!key) {
      /* A question nobody has reached yet still has a board: it says the
         question can be answered here, and touching it cuts the page. */
      boardPage[slotKey(q, 0)] = { p: undefined, a: end };
      changed = true;
      return;
    }
    var rec = boardPage[key];
    var sent = rec.p !== undefined && handedIn[q] === rec.p;
    if (sent && rec.a && rec.a !== end) {
      /* Handed in, and answered underneath. This attempt is finished with:
         freeze it here and open the next one on a copy of it. */
      if (!ready) return;             /* the pages are not knowable yet; next render */
      /* But never under a pen that is down. Cutting the next attempt moves the
         page, and a page that moves mid-word takes the rest of the word with
         it. There is nothing about this that has to happen in this particular
         second. */
      if (writer.writing && writer.writing()) { renderSoon(); return; }
      var next = slotKey(q, slotN(key) + 1);
      boardPage[next] = { p: writer.clone(rec.p), a: end };
      /* And the surface follows it. Somebody pinned to the attempt just frozen
         asked to write on this question, and the place to write is the attempt
         now in hand; leaving the pin on a finished board holds the surface there
         and paints the live one underneath it as a picture, which is the extra
         board by another route. */
      if (workingOn === key) {
        workingOn = next;
        workingOnAt = lastNewestQ;
        /* What was carried has been handed in and answered; the new board's
           grace is its own, and it has not earned one. */
        pinCarried = false;
        pinHeld = false;
      }
      changed = true;
    } else if (!sent || !rec.a) {
      /* Still the attempt in progress, so it follows the end of the run: the
         place to answer is under the last thing the tutor said. */
      if (rec.a !== end) { rec.a = end; changed = true; }
    }
  });
  if (changed) savePages();
}

/* The turns this lesson has, kept so the page mapping can be repaired against
   them from wherever it is read. */
var lastTurns = [];

/* The answer each question actually handed in, newest revision of it. */
function sentAnswers() {
  var out = {};
  (lastTurns || []).forEach(function (t) {
    if (!t || t.kind !== "ink" || !t.answers || !t.png) return;
    var have = out[t.answers];
    if (!have || (t.t || 0) >= (have.t || 0)) out[t.answers] = t;
  });
  return out;
}

/* Working nobody has handed in. There is ink on the page this board holds and
   no answer came off that page, so nothing on disk carries it: take the surface
   away and the only copy of it left is a photograph. */
function unsentInk(key) {
  var rec = key && boardPage[key];
  if (!rec || rec.p === undefined) return false;
  if (!writer || !writer.inkOn || writer.inkOn(rec.p) <= 0) return false;
  var sent = sentAnswers()[slotQ(key)];
  return !(sent && sent.page === rec.p);
}

/* Has the page this board points at stopped being the answer that came off it?
   Fewer strokes than were handed in is the test: a page loses strokes only by
   being cleared, reused or cloned over. More strokes is carrying on writing.
   Returns the answer that came off it. */
function lostAnswer(key, share) {
  if (!writer || !writer.pages || !writer.hasPage) return null;
  var q = slotQ(key);
  var answer = sentAnswers()[q];
  if (!answer) return null;
  var page = pageOf(key);
  /* AND ONLY THE BOARD IT WAS HANDED IN OFF. An answer is keyed by question, and
     the next attempt opens on a copy holding every stroke of it; erasing that copy
     is ordinary and must not bring the old answer back under the pen. The record
     says which sheet the answer came off: if some board of this question is on
     it, the answer is accounted for (`repairPages`'s guard). Only where no board
     holds it has the record rotted. */
  if (typeof answer.page === "number") {
    var from = answer.page;
    if (page !== from) {
      var held = false;
      slotsOf(q).forEach(function (k) { if (pageOf(k) === from) held = true; });
      if (held) return null;
    }
  }
  if (page === undefined || !writer.hasPage(page)) return answer;
  if (typeof answer.strokes === "number" && writer.inkOn
      && writer.inkOn(page) < answer.strokes * (share === undefined ? 1 : share)) {
    return answer;
  }
  return null;
}

/* The frozen strokes of an answer, by the URL the turn carries:
   `live/answers/<turn>.json`, written once and never moved. A past board is
   drawn from it. Fetched once per URL; a failure is remembered, and the board
   falls back to the picture. */
var frozenInk = {};
function frozenFor(url) {
  if (!url) return null;
  if (Object.prototype.hasOwnProperty.call(frozenInk, url)) {
    var have = frozenInk[url];
    return have === "asking" ? null : have;
  }
  frozenInk[url] = "asking";
  fetch(atSession(url)).then(function (r) { return r.json(); }).then(function (d) {
    frozenInk[url] = (d && d.strokes && d.strokes.length) ? d : null;
    if (lastLive) render(lastLive);
  }).catch(function () { frozenInk[url] = null; });
  return null;
}

/* A board whose sheet no longer holds what was handed in off it, given that
   answer back on a page of its own, so the working does not vanish under the
   pen. Once per board per lesson, and never over ink: `adoptInk` cuts a new
   page. */
var reclaimed = {};
/* What the sheet held when its answer was first ruled gone. See below. */
var reclaimFrom = {};
/* ASKED WHEN A BOARD IS OPENED, NOT WHILE SOMEBODY IS SITTING ON IT: clearing
   your own answer's sheet to write it again is ordinary. `reclaimSeen` is the
   slot live last time round; a new one is OWED a judgement until one is
   reached (the frozen strokes fetched, the hand off the glass). Once judged,
   nothing done to that sheet reopens it. */
var reclaimSeen = null;
var reclaimOwed = null;
function reclaimAnswer(key) {
  if (!writer || !writer.adoptInk || reclaimed[key]) { reclaimOwed = null; return; }
  /* A HALF of what was handed in, where showing the frozen picture asks only for
     one stroke fewer: moving the page under the pen is not reversible, and an
     edited sheet holds nearly all its strokes while a cleared or reused one holds
     a handful. */
  var answer = lostAnswer(key, 0.5);
  /* Judged: the answer is where it was handed in, or there is nothing frozen to
     put back. Either way the question is closed until this board is opened
     again. */
  if (!answer || !answer.ink) { delete reclaimFrom[key]; reclaimOwed = null; return; }
  /* A SHEET THAT IS GAINING INK IS A SHEET SOMEBODY IS USING. The judgement is
     made against what the sheet held when first ruled gone, and abandoned if it
     has grown since; the frozen answer stays on disk and on the dormant board. */
  var at = pageOf(key);
  var now = (at !== undefined && writer.inkOn) ? writer.inkOn(at) : 0;
  if (reclaimFrom[key] === undefined) reclaimFrom[key] = now;
  if (now > reclaimFrom[key]) { reclaimOwed = null; return; }
  var ink = frozenFor(answer.ink);
  if (!ink) return;                 /* the fetch renders again when it lands */
  if (writer.writing && writer.writing()) { renderSoon(); return; }
  reclaimed[key] = true;
  reclaimOwed = null;
  boardPage[key].p = writer.adoptInk(ink);
  savePages();
  loadedTurn = null;
}

/* Which page a question sits on, taken back from the record when the record in
   this browser has rotted. `boardPage` lives in localStorage with no way to
   expire; every answer handed in carries the page it was sent from, on disk.
   Applied only where the entry in hand is untrustworthy -- absent, past the end
   of the pages, sharing a sheet, or blank where the record names a written-on
   page. If any board of the question already holds it, nothing moves. */
function repairPages() {
  if (!writer || !writer.ready || !writer.ready()) return;
  var sentOn = {};
  lastTurns.forEach(function (t) {
    if (!t || t.kind !== "ink" || !t.answers) return;
    if (typeof t.page !== "number") return;
    var page = t.page;                     /* the sheet's own number */
    if (!writer.hasPage(page)) return;
    var have = sentOn[t.answers];
    if (!have || (t.t || 0) >= have.t) sentOn[t.answers] = { t: t.t || 0, page: page };
  });
  /* Which question the RECORD says each page was sent for: a board on a page
     that belongs to another question's answer is wrong on evidence, and looks
     healthy to every other test above. */
  var pageOwner = {};
  for (var qq in sentOn) {
    var owned = sentOn[qq].page;
    if (pageOwner[owned] === undefined) pageOwner[owned] = qq;
    else if (pageOwner[owned] !== qq) pageOwner[owned] = null;   /* shared: no claim */
  }

  var changed = false;
  for (var q in sentOn) {
    var want = sentOn[q].page;
    var keys = slotsOf(q);
    if (!keys.length) continue;            /* nothing to repair onto yet */
    var held = false;
    keys.forEach(function (k) { if (boardPage[k].p === want) held = true; });
    if (held) continue;
    var key = keys[keys.length - 1];
    var now = boardPage[key].p;
    var rotten = now === undefined
              || !writer.hasPage(now)
              || pageOwnedByOther(now, key)
              || (writer.inkOn && writer.inkOn(now) === 0 && writer.inkOn(want) > 0)
              || (pageOwner[now] && pageOwner[now] !== q);
    if (!rotten) continue;
    boardPage[key].p = want;
    changed = true;
  }
  if (changed) savePages();
}

/* Every question has a board under it, and one of them is real. A live surface
   is two device-resolution canvases (about 17 MB on an iPad), so there is one,
   and the rest are photographs of themselves drawn by the same paint code at
   CSS resolution. Touching one makes it the live one, handing a pen already
   coming down straight through. */
function boardSlot(key, qid) {
  var slot = els.cards.querySelector('[data-slot="' + key + '"]');
  if (slot) return slot;
  slot = document.createElement("section");
  slot.className = "board";
  /* The board's own name, and the question it belongs to. Both, because a
     question has several boards and everything outside this function -- the
     transcript's way back to the working, the tests -- asks about a question. */
  slot.dataset.slot = key;
  slot.dataset.board = qid;
  slot.innerHTML =
    '<div class="board-head">'
    + '<span class="board-label">Your answer</span>'
    + '<span class="board-hint"></span>'
    + '<button type="button" class="board-carry" hidden></button>'
    + '<button type="button" class="board-send">Send</button>'
    + "</div>"
    + '<img class="board-shot" alt="what you have written here"'
    + ' decoding="async" loading="lazy">';

  var goLive = function (ev, andSend) {
    if (workingOn === key && !els.writer.hidden) return;
    /* Touching a board is asking to write on THAT board -- this attempt, not
       merely this question -- and `workingOn` is already the whole of that ask:
       an answer is owed wherever it points, so this opens the panel on a lesson
       the tutor has marked right without needing a second flag to say so. */
    workingOn = key;
    workingOnAt = lastNewestQ;
    reopenedFor = null;
    pinCarried = false;
    pinHeld = false;
    if (lastLive) render(lastLive);
    if (!writer) return;
    /* Lay the real canvas out now rather than on the next frame: a pen is
       already on the glass and its first sample is converted against the
       canvas's rectangle. */
    writer.relayout();
    if (ev && writer.sheet) handOnStroke(ev, writer.sheet());
    if (andSend) writer.save(true);
  };

  slot.addEventListener("pointerdown", function (ev) {
    if (ev.target.closest
        && ev.target.closest(".board-send, .board-carry")) return;
    goLive(ev, false);
  });
  slot.querySelector(".board-send").onclick = function () { goLive(null, true); };
  slot.querySelector(".board-carry").onclick = function (ev) {
    ev.stopPropagation();
    carryHere(key);
  };
  return slot;
}

/* Go to the board that carries a question's working, wherever it is on the page:
   the picture of it, or the live surface if that question is the one open. A
   question has a chain of boards; the one meant here is the attempt in hand,
   which is the last of them. */
function showBoardFor(qid) {
  var all = els.cards.querySelectorAll('[data-board="' + qid + '"]');
  var n = all.length ? all[all.length - 1] : null;
  if (!n && !els.writer.hidden && answering.question === qid) n = els.writer;
  if (n && n.scrollIntoView) n.scrollIntoView({ block: "center", behavior: "smooth" });
}

/* A stroke that landed on a picture, given to the canvas that replaced it.
   Without this the first mark on a dormant board is always lost -- and a first
   mark that does nothing is indistinguishable from a broken pen. */
function handOnStroke(ev, sheet) {
  if (!sheet || !sheet.dispatchEvent) return;
  var Ctor = window.PointerEvent || window.MouseEvent;
  var copy;
  try {
    copy = new Ctor("pointerdown", {
      bubbles: true, cancelable: true,
      clientX: ev.clientX, clientY: ev.clientY,
      pointerId: ev.pointerId, pointerType: ev.pointerType || "pen",
      pressure: ev.pressure || 0.5, isPrimary: true,
    });
  } catch (e) { return; }
  sheet.dispatchEvent(copy);
}

/* Every board this lesson has, each under the card it was written beneath, and
   the live surface swapped in for whichever one is being written on. */
/* Offered on a board with nothing on it, when there is working behind it, and
   never anywhere else. Named with the question it would come from, because
   "carry it over" means nothing without saying over from where. */
function paintCarry(btn, key) {
  if (!btn) return;
  var rec = key && boardPage[key];
  var blank = !!rec && (rec.p === undefined
                        || !writer || !writer.inkOn || writer.inkOn(rec.p) === 0);
  var from = blank ? prevInkSlot(key) : null;
  btn.hidden = !from;
  if (from) {
    btn.textContent = "↴ carry over from question " + slotQ(from);
    btn.title = "copy that board's working onto this one, to carry on with it";
  }
}

function paintBoards(qids, liveKey, off) {
  /* The answer each question actually handed in, newest revision. A slate page
     is live (written again, cleared, cloned, reused); what was handed in is
     written once into live/answers/ and cannot move. So a board whose page no
     longer holds the answer that came off it shows the answer instead. */
  var sentInk = sentAnswers();
  /* Every photograph is keyed by the paper it was taken on as well as by what is
     on it. The paper is a device setting -- one tap turns the whole sitting from
     slate to white -- and without it in the key the pictures kept the old scheme
     until something else happened to change them. */
  var skin = writer && writer.paper ? writer.paper() : "";
  /* And the box each picture sits in is painted the same colour as the paper.
     It was #101114 in the stylesheet -- the slate's own black -- which is right
     until somebody chooses white paper, and then every board that has nothing on
     it yet is a black rectangle in a run of white ones. */
  if (skin && window.Slate && window.Slate.paperBg) {
    document.documentElement.style.setProperty(
      "--shot-bg", window.Slate.paperBg(skin.split("/")[0]));
  }

  /* Every board in the lesson, in reading order, with which attempt of its
     question it is. */
  var all = [];
  qids.forEach(function (qid) {
    var attempts = slotsOf(qid);
    attempts.forEach(function (key, i) {
      all.push({ key: key, qid: qid, n: i + 1, of: attempts.length });
    });
  });
  var live = {};
  all.forEach(function (it) { live[it.key] = true; });

  Array.prototype.forEach.call(els.cards.querySelectorAll("[data-slot]"),
                               function (node) {
    /* The board being written on has the real surface, so its picture goes --
       leaving it would show the board twice, once alive and once as a
       photograph of a moment ago. */
    if (off || !live[node.dataset.slot] || node.dataset.slot === liveKey) {
      node.remove();
    }
  });
  if (off || !writer) return;

  all.forEach(function (it) {
    if (it.key === liveKey) return;                /* the real one goes here */
    var rec = boardPage[it.key];
    var anchor = els.cards.querySelector('[data-card="' + rec.a + '"]');
    if (!anchor || !anchor.parentNode) return;
    var slot = boardSlot(it.key, it.qid);
    if (anchor.nextSibling !== slot) {
      anchor.parentNode.insertBefore(slot, anchor.nextSibling);
    }
    slot.hidden = false;
    /* The same verdict as the turn above it, on the same answer. A question
       answered in ink keeps its board for the rest of the sitting, and that
       board -- not the one-line receipt in the transcript -- is what the person
       actually looks back at. */
    var said = lastVerdicts[it.qid];
    if (said) slot.dataset.verdict = said;
    else delete slot.dataset.verdict;
    /* Which attempt this is, but only once there is more than one -- on a
       question answered in one go the number is noise. */
    var which = it.of > 1
      ? "question " + it.qid + " · attempt " + it.n + " of " + it.of
      : "question " + it.qid;
    slot.querySelector(".board-hint").textContent = which + " · tap to write";
    var page = rec.p;

    var answer = lostAnswer(it.key);
    if (answer) {
      slot.querySelector(".board-hint").textContent = which + " · as it was handed in";
      var frozen = slot.querySelector(".board-shot");
      /* Drawn from the frozen STROKES, by the slate, on the paper in hand, so a past
         board is indistinguishable from a live one. The answer's PNG (dark on white,
         cropped, for an agent) is the fallback for an answer with no frozen strokes. */
      var ink = frozenFor(answer.ink);
      var mark = "frozen:" + (answer.ink || answer.png) + ":" + skin
               + ":" + (ink ? "ink" : "png");
      if (slot.dataset.shot !== mark) {
        var drawn = "";
        if (ink && writer.previewInk) {
          var fb = slot.getBoundingClientRect();
          drawn = writer.previewInk(ink,
                                    Math.round(fb.width) || 900,
                                    Math.round(frozen.getBoundingClientRect().height) || 420);
        }
        /* Nothing to show yet: the strokes are on their way. Leave the board as
           it is rather than flashing the inverted picture up and swapping it a
           moment later. */
        if (drawn || !ink) {
          frozen.src = drawn || atSession(answer.png);
          frozen.alt = "the answer handed in for question " + it.qid;
          slot.dataset.shot = mark;
        }
      }
      paintCarry(slot.querySelector(".board-carry"), it.key);
      return;
    }

    if (page === undefined) {
      /* Never written on, so there is no picture to take -- but a blank board is
         still a board. It says the question can be answered here, and touching it
         cuts the page. It used to show nothing at all, which is fine exactly as
         long as the live surface happens to be under that question, and is a
         question posed with nowhere to answer it the moment anything parks the
         surface somewhere else. Something did. */
      /* And it has to SAY it is blank. An empty board with the same caption as
         a full one reads as a board whose working has gone missing, which is
         how it was read the first evening it existed -- by someone whose ink
         was on disk the whole time. A board is allowed to be empty; it is not
         allowed to be ambiguous about it. */
      slot.querySelector(".board-hint").textContent =
        which + " · nothing written here yet · tap to write";
      var blank = slot.querySelector(".board-shot");
      if (slot.dataset.shot !== "blank") {
        blank.removeAttribute("src");
        blank.alt = "";                   /* no broken-image text on a blank sheet */
        slot.dataset.shot = "blank";
      }
      paintCarry(slot.querySelector(".board-carry"), it.key);
      return;
    }
    paintCarry(slot.querySelector(".board-carry"), it.key);
    /* Redrawn only when the page it is a picture of has actually changed. */
    var mark = page + ":" + (writer.inkOn ? writer.inkOn(page) : 0) + ":" + skin;
    if (slot.dataset.shot === mark) return;
    var shot = slot.querySelector(".board-shot");
    var box = slot.getBoundingClientRect();
    var w = Math.round(box.width) || 900;
    var h = Math.round(shot.getBoundingClientRect().height) || 420;
    var url = writer.preview ? writer.preview(page, w, h) : "";
    if (!url) return;
    shot.src = url;
    slot.dataset.shot = mark;
  });
}

/* Two of these can still be SENT -- begin and skip -- and the other three only
   ever appear in a transcript written before the signals went. A lesson filed in
   May is still read on this board, and a turn whose whole content was a tap has
   nothing else to render, so the labels stay. */
var SIGNAL_LABEL = { done: "ready to check", help: "needs help", confused: "confused",
                     begin: "asked the tutor to begin", skip: "skipped this one",
                     handover: "handed this step over" };

/* The answer block, in every course.

   Two ways, because the question decides which is easier: write on the card
   itself, which is how you answer *about a place* in it, or type, which is how
   you answer in sentences. Both come back as an ordinary turn, and a sentence
   saying what was just implemented is one of them -- there is no separate
   channel for that and there is no longer a tap that stands in for it. */
/* A card is a file, and the lesson shows nothing until that file exists. So the
   minute a tutor spends writing one is a minute of a blank screen with no way to
   tell it apart from a tutor that has died -- and the difference used to be a dot
   in the title bar the size of a full stop. Say it where the card is going to
   appear, and count, because a wait you can see the length of is a different
   experience from one you cannot. */
var busySince = 0;
var busyTurn = -1;
/* The words a stall is being reported with, so the ticker does not overwrite
   them with "the tutor is writing" one second later. */
var busyStalled = null;
var busyFrom = 0;
/* Whether the turn running now is one that does the work. Held rather than
   recomputed in `tickBusy`, which fires on a timer and has no payload. */
var busyDoing = false;
var busyAim = "";                /* what the work IS, when the turn does it */
/* WHAT THE TURN WAS WOKEN FOR, off the daemon's own record. One value matters:
   `direction`, whose opening card is a receipt rather than the answer, so the
   strip keeps talking over it. */
var busySignal = "";
var busyTimer = null;
/* WHEN SEND WAS TAPPED, AND WHETHER ANYTHING HAS ANSWERED YET. The strip says
   "sending to tutor" from the tap until the tutor picks it up, so there is
   immediate feedback and no temptation to send twice. It expires: an inbox
   nobody is reading must not leave "sending" up all evening. */
var sendingAt = 0;
var sendingWord = "";
var SENDING_FOR = 100000;

function saySending(word) {
  sendingAt = Date.now();
  /* WHAT was sent, when it is not a page of working. A direction change archives
     the lesson and replaces the tutor, which takes long enough to read as
     nothing happening at all -- and "sending to the tutor" would be a lie about
     which tutor. Empty means the ordinary send, and the ordinary words. */
  sendingWord = word || "";
  if (lastLive) paintBusy(lastLive);
  /* AND GO AND LOOK AT IT, NOW: the strip is under the surface, so the reader is
     brought there on the tap rather than on the reply. `revealSentSettling` still
     re-lands once the receipt settles, and stands down when a card arrives. */
  revealSent();
}

/* The newest card's mtime -- a correction to an existing card counts as much as
   a new one, since either way something appeared for them to read. */
/* IS THIS A TURN THAT DOES THE WORK, rather than one that teaches it: the
   session's mode (`stance_now`), or an older frame's aim, stance or product.
   In a doing turn, a card landing does NOT mean the work is finished. */
function doingTurn(state) {
  state = state || {};
  var aim = state.aim || "";
  if (state.session === "make") return true;
  if (aim === "build" || aim === "paper" || aim === "slides") return true;
  if (aim === "teach" || aim === "coach" || aim === "trace" || aim === "drill") {
    return false;
  }
  var kind = state.session || "lecture";
  if (kind !== "lecture" && kind !== "homework") return false;
  /* The sitting's answer, or failing that the one the server resolved for it --
     `stance_now`, which is the sitting's own stance, its aim, the repository's
     word, or its family's default, in that order and decided in one place. The
     client cannot read `tutorboard.json` and must not re-derive a precedence. */
  return (state.stance || state.stance_now
          || state.declared_stance || "teach") === "do";
}

function newestCard(data) {
  /* A `pending` card is the placeholder a turn opens with, not its answer, so
     it never counts as something new having landed. */
  var newest = 0;
  (data.cards || []).forEach(function (c) {
    if (c.kind !== "pending" && c.mtime > newest) newest = c.mtime;
  });
  return newest;
}

/* NOTHING THE READER CAN BE WAITING ON IS ALLOWED TO BE SILENT. A tutor still
   coming up, a turn that failed, and a session with no tutor attached are one
   question -- IS THERE SOMETHING IN THE INBOX THAT NOTHING HAS PICKED UP -- and
   the server answers it off disk (`notes.waiting`), so it survives a reload, a
   second device and a restart. `sendingAt` covers only the sub-second before
   the first payload. The order below is urgency: a turn in progress, then a
   failure being retried, then work unclaimed, then the wire. */
function longAgo(ms) {
  var secs = Math.max(0, Math.round(ms / 1000));
  if (secs < 60) return secs + "s";
  var mins = Math.floor(secs / 60);
  if (mins < 60) return mins + "m " + (secs % 60) + "s";
  return Math.floor(mins / 60) + "h " + (mins % 60) + "m";
}

/* What to say about a tutor that is not currently writing, given that something
   is sitting in the inbox for it. Returns null when there is nothing to say. */
function stalledWord(st, waiting, unsaved) {
  var who = (st && st.agent) || "the tutor";

  /* A FAILED TURN IS NEWS ON ITS OWN, AND CANNOT WAIT ON THE INBOX TO SAY SO: the
     message it failed on was marked read when it was handed over, so it leaves
     no trace there. Asked first and independently, timed from the failure. */
  /* AND WHETHER THE WORK IS STILL THERE, which after a doing turn is the fact
     that decides what to do next. "Send again to retry it" reads as starting
     over, and a turn that was stopped after twenty minutes of writing code has
     left every one of those files on disk, uncommitted. Saying so is the
     difference between sending again to CONTINUE and sending again expecting
     the same twenty minutes back. */
  var kept = (st && st.failure && !st.retrying && unsaved)
    ? " Its work so far is still here — " + unsaved
      + (unsaved === 1 ? " file changed" : " files changed")
      + ", not yet saved."
    : "";
  var failed = st && st.failure
    ? { text: (st.retrying
               ? who + " hit a problem and is trying again"
               : who + "'s last turn failed")
            + " — " + failWord(st.failure.error)
            + (st.retrying ? "." : ". Send again to carry on.") + kept,
        bad: !st.retrying,
        since: Date.now() - (st.failure.at || 0) * 1000 }
    : null;

  /* A PROVIDER STANDING ASIDE IS A STANDING FACT, NOT AN EVENT, and until now
     it was written only into a log file and a hover tooltip. It is the sentence
     that answers "why is nothing happening": which provider went quiet, what it
     could not reach, when it will be asked again, and who is teaching instead.
     `agent_why` is the daemon's own words for the swap and already carries the
     host and the hour; `stood_down` is there for the case where nothing could
     take the turn, so there was no swap to describe. */
  var aside = null;
  if (st && st.agent_why) {
    aside = { text: st.agent_why, since: 0 };
  } else if (st && st.stood_down) {
    aside = { text: who + " is standing aside — "
                  + (st.stood_down.host
                     ? st.stood_down.host + " does not answer from this machine"
                     : st.stood_down.why)
                  + ", and nothing else here can take the lesson. Asking again at "
                  + clockWord(st.stood_down.until) + ".",
              bad: true, since: 0 };
  }

  /* NEWEST FACT WINS. Somebody who sends again after a failure has made the
     send the newer thing that happened, and going on about the old failure over
     the top of it is the board talking about the past. The other way round -- a
     failure since the last unclaimed send -- and the failure is the news. */
  if (!waiting) return failed || aside;
  if (failed && (st.failure.at || 0) >= (waiting.since || 0)) return failed;
  var held = Date.now() - (waiting.since || 0) * 1000;
  /* The first couple of seconds belong to the wire and to the daemon's quarter
     second poll. Announcing a stall there would make every ordinary send flash
     a warning -- but not at the cost of dropping a failure that is still the
     standing fact about this tutor. */
  if (held < 4000) return failed || aside;
  var many = waiting.count > 1 ? " (" + waiting.count + " things waiting)" : "";
  /* A DIRECTION CHANGE REPLACES THE TUTOR IT WAS SENT TO, so every state below
     is the expected one rather than a stall, and none of the sentences below
     describe it. The old tutor is writing its handoff and a new one is coming up
     behind it; that takes as long as it takes and the only wrong answer is
     silence -- or worse, "no tutor is reading the board", which is true, alarming
     and entirely beside the point. */
  if (waiting.signal === "direction") {
    return { text: "the new direction is in the inbox. The tutor is being "
                 + "replaced, and the one that comes up re-plans from it. "
                 + "No need to send again.",
             since: held };
  }
  if (!st || st.state === "stale") {
    return { text: "handed in — but no tutor is reading the board" + many
                 + ". It will be answered as soon as one is attached.",
             bad: true, since: held };
  }
  if (st.state === "waking") {
    return { text: who + " is still waking up — your work is in its inbox"
                 + many + " and will be answered. No need to send again.",
             since: held };
  }
  if (st.state === "reattaching") {
    return { text: who + " is restarting — your work is in its inbox" + many
                 + " and will be answered when it comes back.", since: held };
  }
  /* Attached, no failure, and still nothing taken. Rare, and worth saying
     plainly rather than pretending: the daemon polls every quarter second, so
     this means it is busy with something that is not this. */
  return { text: who + " has not picked this up yet" + many + ".", since: held };
}

/* An epoch second as a wall clock, in the reader's own timezone. The board
   draws every other time this way; a string formatted in Python would be a
   second place the format is decided. */
function clockWord(secs) {
  if (!secs) return "soon";
  return new Date(secs * 1000)
    .toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/* A daemon's error string is for a log. This is for somebody holding an iPad. */
function failWord(err) {
  var e = String(err || "");
  if (/allowance/i.test(e)) return "its usage allowance has run out here";
  /* A hostname is a fact about somebody else's server and the person holding
     the iPad did not choose it and cannot act on it. What they can act on is
     that this is the provider rather than the lesson, the machine or them. */
  if (/^cannot reach /i.test(e)) return "its provider does not answer from this machine";
  if (/egress|network/i.test(e)) return "this machine cannot reach the internet";
  if (/timed out/i.test(e)) return "the turn ran too long and was stopped";
  if (/^exit /.test(e)) return "the assistant exited (" + e + ")";
  return e || "no detail";
}

function paintBusy(data) {
  if (!els.busy) return;
  var st = data.agent || null;
  var working = !!st && st.state === "working" && !data.archived;
  /* The tutor has picked it up, or given up waiting for it to be picked up. */
  if (working || Date.now() - sendingAt > SENDING_FOR) { sendingAt = 0; sendingWord = ""; }
  if (!working) {
    /* No turn, no turn's words. The ticker fires without a payload. */
    busySignal = "";
    var stalled = data.archived ? null
      : stalledWord(st, data.waiting, unsaved || 0);
    if (stalled) {
      els.busy.hidden = false;
      els.busy.classList.toggle("busy-bad", !!stalled.bad);
      els.busyText.textContent = stalled.text;
      els.busySince.textContent = longAgo(stalled.since);
      /* Counted from the message's own timestamp, so the number does not restart
         at zero every time the payload changes. `busySince` is the clock the
         ticker reads. */
      busySince = Date.now() - stalled.since;
      busyTurn = -1;
      busyStalled = stalled.text;
      if (!busyTimer) busyTimer = setInterval(tickBusy, 1000);
      return;
    }
    busyStalled = null;
    els.busy.classList.remove("busy-bad");
    if (sendingAt && !data.archived) {
      /* Not "the tutor is writing" -- it has not been handed anything yet, and
         saying so would be the board guessing. This is the half-second of the
         send that belongs to the wire. */
      els.busy.hidden = false;
      /* THE LINK IS THE FIRST THING THAT COULD BE WRONG: with the stream down
         nothing is carrying a send, so "sending" would be a claim nobody corrects. */
      els.busyText.textContent = linkDead
        ? "not connected to the board — this has not been sent yet"
        : (sendingWord || "sending to the tutor");
      els.busy.classList.toggle("busy-bad", !!linkDead);
      els.busySince.textContent = "";
      busySince = 0;
      busyTurn = -1;
      /* AND THE CLOCK KEEPS RUNNING. This used to stop the ticker, so the only
         thing that could ever clear a stuck "sending" was the next payload --
         which is precisely what does not arrive when the send is the thing that
         went wrong. `tickBusy` re-asks on its own now. */
      if (!busyTimer) busyTimer = setInterval(tickBusy, 1000);
      return;
    }
    /* A SLURM JOB REGISTERED HERE IS STILL OUT. No turn is running, and the
       work is: the strip says so, on the job's own clock, until the daemon's
       poll sees it end and a turn reports it. */
    var running = data.jobs || (subjectInfo && subjectInfo.jobs) || [];
    var job = !data.archived && running[0];
    if (job) {
      var more = running.length > 1 ? " (+" + (running.length - 1) + " more)" : "";
      var asked = String(job.state).toUpperCase() === "REQUESTED";
      var word = asked
        ? "waiting for the cluster — " + (job.title || job.thread || "a request")
          + more
        : "running — " + (job.title || job.thread || "a job") + ": job "
          + job.jobid + (String(job.state).toUpperCase() === "PENDING" ? ", pending" : "")
          + more;
      els.busy.hidden = false;
      els.busy.classList.remove("busy-bad");
      els.busyText.textContent = word;
      busySince = job.submitted ? job.submitted * 1000 : Date.now();
      els.busySince.textContent = longAgo(Date.now() - busySince);
      busyTurn = -1;
      busyStalled = word;
      if (!busyTimer) busyTimer = setInterval(tickBusy, 1000);
      return;
    }
    els.busy.hidden = true;
    busySince = 0;
    busyTurn = -1;
    if (busyTimer) { clearInterval(busyTimer); busyTimer = null; }
    return;
  }
  busyStalled = null;
  els.busy.classList.remove("busy-bad");
  /* A new turn restarts the clock; the same turn continuing does not. */
  var turn = st.turns || 0;
  busyDoing = doingTurn(data.state);
  busyAim = (data.state || {}).aim || "";
  busySignal = st.turn_signal || "";
  if (busyTurn !== turn || !busySince) {
    busyTurn = turn;
    /* THE DAEMON'S CLOCK, NOT THIS PAGE'S.

       This used to start counting when the browser first SAW the working state,
       which on a reload, on a second device, or on a board opened halfway
       through a turn is nowhere near when the turn began -- so a four-minute
       turn read as "8s" to whoever had just picked the iPad up. */
    busySince = st.turn_started ? st.turn_started * 1000 : Date.now();
    busyFrom = newestCard(data);
  }

  /* The card is what they are waiting for, and a turn does not end when the card
     lands -- the tutor goes on to verify, file, and write the handoff, and the
     daemon says "working" for all of it. So this counted on for minutes after
     the answer was already on screen, which is how a 34-second card came to look
     like a four-minute wait. Once something new is on the board, stop talking. */
  /* ...AND THAT IS A TEACHING TURN'S RULE TOO. A turn that DOES the work opens
     with one sentence and then writes code, runs it, and replaces the sentence
     with the report; so in a doing turn the strip stays for as long as the tutor
     says it is working, and says what kind of work it is. A `direction` turn's
     opening card is a receipt too. */
  if (!busyDoing && busySignal !== "direction" && newestCard(data) > busyFrom) {
    els.busy.hidden = true;
    if (busyTimer) { clearInterval(busyTimer); busyTimer = null; }
    return;
  }
  /* Deliberately NOT inside #cards. That container is reconciled -- keyed nodes
     are matched and moved in place -- and an unkeyed element sitting among them
     is stepped over by the cursor walk, so cards get inserted on the wrong side
     of it and the answer block stops sitting under its own question. It lives
     immediately after the lesson instead, which puts it in the same place on
     screen and out of the way of everything. */
  els.busy.hidden = false;
  tickBusy();
  if (!busyTimer) busyTimer = setInterval(tickBusy, 1000);
}

function tickBusy() {
  if (!els.busy || els.busy.hidden) return;
  /* A send with no clock of its own: nothing here counts up, but the expiry has
     to be able to fire without a payload, and the words change the moment the
     link does. */
  if (!busySince && sendingAt) {
    if (lastLive) paintBusy(lastLive);
    return;
  }
  if (!busySince) return;
  els.busySince.textContent = longAgo(Date.now() - busySince);
  /* A stall keeps its own words -- they say what is wrong, which the writing
     message does not, and the number beside them is doing the counting. */
  if (busyStalled) {
    els.busyText.textContent = busyStalled;
    return;
  }
  var secs = Math.max(0, Math.round((Date.now() - busySince) / 1000));
  /* RE-PLANNING SAYS RE-PLANNING, and it says it before anything else here.
     A direction change is the one send where the person knows they have asked
     for something big, so "the tutor is writing" is both true and useless: what
     they are waiting to hear is that the PLAN is being redone, and where it will
     appear when it is. It outranks the doing words below because the sitting's
     aim is about the evening's work and this turn is about none of it. */
  if (busySignal === "direction") {
    els.busyText.textContent = secs > 120
      ? "still re-planning — the new plan lands here"
      : "re-planning — reading the plan and rewriting it for the new direction";
    return;
  }
  /* A DOING TURN SAYS WHAT IT IS DOING. "The tutor is writing" is true of a
     card and reads as false when the card is already on screen and nothing has
     changed for four minutes -- which is what a turn spends writing code, running
     it and reading what came back. Say that instead, and say where the answer
     will appear, because the one-line card already up is not it. */
  if (busyDoing) {
    /* WHAT the work is, and only where an aim has said: `doingTurn` is also true
       for a paper, a deck, or a plain `do`, so the aim chooses the words and the
       fallback claims nothing. */
    var doingWord = busyAim === "build" ? " — writing the code and running it"
                  : busyAim === "paper" ? " — writing it up"
                  : busyAim === "slides" ? " — putting the deck together"
                  : "";
    els.busyText.textContent = secs > 150
      ? "still working" + doingWord + ". The report lands here"
      : "working on it" + doingWord;
    return;
  }
  /* Past a couple of minutes, silence stops being reassuring. Say that this one
     is long rather than letting the number say it alone. */
  els.busyText.textContent = secs > 150
    ? "the tutor is still writing — this one is taking a while"
    : "the tutor is writing";
}

/* ------------------------------------------------- the strip in the chrome

   Documents asked for from this session, in the chrome under the bar rather
   than over the lesson: the turn writing one writes no card, so this strip is
   the only place "it is being written" and "it is there" can be said. */

function newsAgo(when) {
  var ms = Date.now() - (when || 0) * 1000;
  if (ms < 60000) return "just now";
  return longAgo(ms) + " ago";
}

/* A DOCUMENT ASKED FOR FROM THIS SESSION.

   In the chrome rather than on the glass: the lesson underneath belongs to
   somebody's evening, and a deck being written must not push a proof off the
   screen. That is the whole design of `POST /artifact`.

   IT EXISTS BECAUSE THE TURN IS TOLD TO WRITE NO CARD. A write-up turn is
   invisible on the board by construction, so "I asked for a deck and nothing
   happened" had nowhere at all to be answered. The server holds the record and
   derives its state from the library — see `tutorboard/writeups.py`.

   A FINISHED ONE IS A LINK TO THE LIBRARY, because that is where it went and
   because reading it is what takes the row away. A finished write-up waved
   off is told to the SERVER it has been seen, since the fact is about the
   document rather than about this page. */
var WRITEUP_WORD = { writing: "being written", done: "in the library",
                     failed: "did not land" };
var writeupShown = "";
/* Finished ones `✕` has waved off, held here until the server's record says
   `seen` and the row stops arriving. Keyed by state, so the same ask failing
   later shows again. */
var writeupMuted = Object.create(null);

function writeupKey(w) {
  return (w.id || "") + "@" + (w.state || "");
}

function writeupsShowing(data) {
  return ((data && data.writeups) || []).filter(function (w) {
    return !writeupMuted[writeupKey(w)];
  }).slice(0, 3);
}

function writeupSeen(id) {
  api("/writeup/seen", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: id })
  }).catch(function () { /* the next payload is the truth either way */ });
}

function paintWriteups(show) {
  if (!els.writeupList) return;
  var sig = show.map(writeupKey).join("~");
  if (sig === writeupShown) return;
  writeupShown = sig;
  els.writeupList.textContent = "";
  show.forEach(function (w) {
    var done = w.state === "done";
    var row = document.createElement(done ? "a" : "div");
    row.className = "news-row writeup-row";
    row.dataset.state = w.state || "";
    if (done) {
      row.href = BASE + "/library" + (w.doc ? "?doc=" + encodeURIComponent(w.doc) : "");
      /* Going there IS reading it, so the row is retired on the way out rather
         than left for a second tap. */
      row.onclick = function () { writeupSeen(w.id); };
    }
    var pill = document.createElement("span");
    pill.className = "writeup-state";
    pill.textContent = WRITEUP_WORD[w.state] || w.state || "";
    var where = document.createElement("span");
    where.className = "news-where";
    where.textContent = w.makes === "slides" ? "a deck" : "a paper";
    var what = document.createElement("span");
    what.className = "news-what";
    /* What they asked it to be about, and where they said nothing the truthful
       answer is the evening — which is what the server defaulted it to. */
    what.textContent = w.about || "what this sitting has covered";
    var when = document.createElement("span");
    when.className = "news-when";
    when.textContent = newsAgo(w.at);
    row.appendChild(pill);
    row.appendChild(where);
    row.appendChild(what);
    row.appendChild(when);
    if (done) {
      var go = document.createElement("span");
      go.className = "news-go";
      go.textContent = "→";
      row.appendChild(go);
    }
    if (w.state === "failed") {
      var why = document.createElement("span");
      why.className = "writeup-why";
      why.textContent = "nothing has appeared in the library. Ask again.";
      row.appendChild(why);
    }
    els.writeupList.appendChild(row);
  });
}

/* The one line at the top of the strip, built out of what is in it. */
function newsLeadFor(papers) {
  var parts = [];
  var writing = 0;
  papers.forEach(function (w) {
    if (w.state === "writing") writing++;
  });
  var landed = papers.length - writing;
  if (writing) {
    parts.push(writing === 1 ? "a document is being written here"
                             : writing + " documents are being written here");
  }
  if (landed) {
    parts.push(landed === 1 ? "a document is in the library"
                            : landed + " documents are in the library");
  }
  var said = parts.join(" \u00b7 ");
  return said.charAt(0).toUpperCase() + said.slice(1);
}

function paintNews(data) {
  if (!els.newsBar) return;
  var papers = els.writeupList ? writeupsShowing(data) : [];
  if (!papers.length) {
    els.newsBar.hidden = true;
    if (els.writeupList) els.writeupList.textContent = "";
    writeupShown = "";
    return;
  }
  els.newsBar.hidden = false;
  els.newsLead.textContent = newsLeadFor(papers);
  paintWriteups(papers);
}

if (els.newsHide) {
  els.newsHide.onclick = function () {
    /* A FINISHED DOCUMENT IS RETIRED, on the server, because the fact is about
       the document rather than this page: a second device stops offering it
       too. Muted here as well, or the next payload paints it back before the
       server's record changes.
       A DOCUMENT BEING WRITTEN HERE IS NOT MUTED: it comes back on the next
       payload, because it is work happening on this board. */
    ((lastLive && lastLive.writeups) || []).forEach(function (w) {
      if (w.state === "writing") return;
      writeupMuted[writeupKey(w)] = true;
      writeupSeen(w.id);
    });
    els.newsBar.hidden = true;
    writeupShown = "";
  };
}

/* SOMEBODY IS LOOKING AT THIS BOARD, AND ONLY THE PAGE CAN SAY SO.

   The server cannot: a board is a long-lived process that goes on running in an
   empty room, and a request arriving proves a browser is open rather than that
   anybody is in front of it. So the page says it, at the three moments it is
   true -- when the lesson first paints, when a card lands in front of the
   reader, and when the tab comes back to the front after being away.

   Throttled, because the third of those fires on every app switch on a tablet
   and this is a write to a shared filesystem. `keepalive` so the last one, sent
   as the app goes into the background, is not cancelled with the page. */
var seenAt = 0;
var SEEN_EVERY = 20000;

function markSeen(force) {
  /* A BOARD IN A BACKGROUND TAB IS NOT BEING READ, and this is the whole point
     of the feature: the person is working in another workspace, on another
     device or behind another tab, while a turn runs here. A page that went on
     marking itself seen from behind everything else would quietly cancel its own
     notification -- the one case the notification exists for. */
  if (document.hidden) return;
  var now = Date.now();
  if (!force && now - seenAt < SEEN_EVERY) return;
  seenAt = now;
  try {
    api("/seen", { method: "POST", keepalive: true }).catch(function () {});
  } catch (e) { /* offline; the marker is a convenience, not the lesson */ }
}

document.addEventListener("visibilitychange", function () {
  if (!document.hidden) markSeen(true);
});

/* The writing surface is not capped against the visual viewport: a cap shrinks
   as fast as the page is magnified, so zooming into the writing would do
   nothing. The re-centre button is the way back instead; `--gap` on `#writer`
   leaves page down each side for a thumb. */

/* Whether the surface is shut only because something is still being typed into
   the lesson -- rather than because nothing is owed. `paintBoards` needs the
   difference; see its call. */
var writerHeldShut = false;
/* What the hold was last time the surface was placed, so the trace records the
   change rather than the state four times a second. */
var traceHeld = false;

function placeWriter(owed, questionNode, live, hold) {
  /* A BOARD THAT IS NOT OPEN YET DOES NOT OPEN WHILE A CARD IS STILL TYPING. A
     surface that was never open has no tool bar to take away, so it simply
     arrives a beat later, under a finished response. `typeOut` renders once more
     when the last character lands, which is what opens it. */
  writerHeldShut = !!(hold && owed && els.writer.hidden);
  if (writerHeldShut) owed = false;
  /* Only when something about it CHANGED. This runs on every payload and most
     of them place the surface exactly where it already was. */
  var was = els.writer.hidden;
  if (was !== !owed || hold !== traceHeld) {
    trace("writer", { owed: owed ? 1 : 0, hold: hold ? 1 : 0,
                      shut: writerHeldShut ? 1 : 0,
                      at: (questionNode && questionNode.dataset
                           && questionNode.dataset.card) || "-",
                      typing: typingNow });
  }
  traceHeld = !!hold;
  els.writer.hidden = !owed;
  /* The surface's re-centre exists while the surface does, and not otherwise:
     a button offering to find writing on a board that is not on screen is a
     button that does nothing, which is worse than no button. */
  if (els.findink) {
    var wasHidden = els.findink.hidden;
    els.findink.hidden = !owed;
    if (wasHidden !== els.findink.hidden) {
      /* The change of pens moves the button under it, so that one is measured
         again too — a stale height leaves a gap or an overlap in the stack. */
      panicRemeasure();
    }
  }
  /* The tool bar is fixed to the bottom of the window, so the page has to give
     up the height it occupies or the last card sits underneath it. */
  document.body.classList.toggle("tools-out", !!owed);
  paintPanel();
  if (!owed) {
    /* The panel is shut and the pages behind it are still the lesson's: every
       dormant board is a picture drawn from them, so with no surface built there
       is nothing to draw and the transcript comes back as photographs of sent
       answers alone. Build it anyway on a live lesson -- hidden, unlaid-out and
       costing what one surface has always cost -- and re-render once, now that
       there is something to take pictures with. A filed lesson and a past one
       build nothing: there is no writing to be done in either. */
    if (live) makeWriter(function () { if (lastLive) render(lastLive); });
    return;
  }

  /* The anchor is looked up by card id now, so it can be any node in the lesson
     rather than only the last child -- which means checking it is actually IN
     the lesson before inserting beside it. */
  /* AND IT DOES NOT MOVE UNDER A CARD THAT IS STILL BEING WRITTEN. Held where it
     is, not hidden (hiding would take the tool bar off the screen and back). The
     card types out below it, and the surface comes down under the card in one
     move when the last character lands; `typeOut` renders once more to do it. */
  var host = questionNode && questionNode.parentNode;
  if (hold) {
    /* HELD -- BUT ONLY AGAINST THE CARD THAT IS TYPING. The surface comes down as
       far as the first card still being typed and no further, so the receipt and
       anything finished reconcile into place at once. Which card that is comes
       from the hold itself (`typingHeld`, see `holdTyping`), not from a class the
       animation sets. */
    var kids = els.cards.children;
    var below = null, passed = false;
    for (var k = 0; k < kids.length; k++) {
      if (kids[k] === els.writer) { passed = true; continue; }
      if (passed && cardArriving(kids[k])) { below = kids[k]; break; }
    }
    if (below && below.previousElementSibling !== els.writer) {
      els.cards.insertBefore(els.writer, below);
    }
  } else if (host && questionNode.nextSibling !== els.writer) {
    host.insertBefore(els.writer, questionNode.nextSibling);
  } else if (!host && els.writer.parentNode !== els.cards) {
    els.cards.appendChild(els.writer);
  }

  if (!makeWriter(restoreAnswer) && writer) {
    requestAnimationFrame(writer.relayout);
    restoreAnswer();
  }
}

/* The one place the surface is built. Returns whether it started building one --
   `false` means there is already one, or this browser has no Slate at all. */
function makeWriter(then) {
  if (writer || !window.Slate) return false;
  {
    requestAnimationFrame(function () {
      writer = window.Slate.create({
        root: document.getElementById("slate"),
        bar: document.getElementById("drawbar"),
        compact: true,
        stateUrl: BASE + "/slate/state",
        saveUrl: BASE + "/slate/save",
        fullUrl: BASE + "/slate",
        context: function () {
          return { turn: answering.turn ? answering.turn.id : null,
                   answers: answering.question };
        },
        onSend: function (res) {
          /* The ink that was just sent is already on the surface -- it is what
             was sent. Without this, the payload that follows carries a turn one
             revision newer than the one `restoreAnswer` has loaded, so it fetches
             the answer back off the server and hands it to `load`, which re-fits
             the page: the working visibly jumps and the zoom you were writing at
             is thrown away, every single time Send is pressed. */
          if (res && res.turn && res.rev) loadedTurn = res.turn + ":r" + res.rev;
          /* Ink was the half they answered on, so ink is the half the next
             question opens on. The twin of the line in `say`. */
          setAnswerKind("write");
          toastSent();
          revealSentSettling();
        },
        /* The tap itself, before the picture is encoded and before the wire is
           touched. The only job here is to put something on the glass on the
           frame the button was pressed. */
        onSending: saySending,
        /* The working goes alone; a blank surface with marks opens the
           picker instead. */
        beforeSend: askWhatToSend,
        /* The saved pages have arrived and the count can be believed. Everything
           about which question sits on which page was deferred until now. */
        onPages: function () {
          restoreAnswer();
          if (lastLive) render(lastLive);
        },
        /* The paper is a device setting and every board on the page is drawn
           with it, so one tap has to repaint the photographs too -- otherwise
           the live surface turns white and a dozen dormant boards stay on
           slate. */
        onPaper: function () { if (lastLive) render(lastLive); },
      });
      window.__writerDebug = writer.debug;
      if (then) then();
    });
  }
  return true;
}

/* Put the right page under the pen for whichever question is being answered, and
   put a previously sent answer back on it when the tutor has commented.
 
   Nothing is ever wiped. Each question gets a page of its own, and a page that
   has been written on stays written on for the life of the sitting -- the ⋯ menu
   walks them, and going back to an earlier question comes back here and returns
   to its page with the working still on it. */
function restoreAnswer() {
  if (!writer) return;
  /* Not until the surface knows what its pages actually are. For its first
     half-second it is one blank sheet, and acting on that count refiles
     questions onto the wrong page and blocks the real pages' adoption. `onPages`
     calls this the moment the count is real. */
  if (!writer.ready || !writer.ready()) return;
  /* The pages have only just become knowable, and this is the first thing to
     read the mapping when they do. */
  repairPages();

  /* Before anything decides which page goes under the pen: if this board's sheet
     no longer holds the answer that came off it, the answer comes back first. */
  /* And it is asked when a board is OPENED, not on every render of the board
     somebody is sitting on. See `reclaimOwed`. */
  if (liveSlot !== reclaimSeen) { reclaimSeen = liveSlot; reclaimOwed = liveSlot; }
  if (liveSlot && boardPage[liveSlot] && reclaimOwed === liveSlot) {
    reclaimAnswer(liveSlot);
  }

  if (liveSlot && boardPage[liveSlot] && writer.fresh) {
    var rec = boardPage[liveSlot];
    var want = rec.p;
    if (want === undefined || !writer.hasPage(want)) {
      /* Nobody has written on this board yet. A blank page at the end, unless
         the page in hand is still blank -- in which case it is already the right
         one, and adding another would leave an empty page behind on every board.
         That reuse is right only while the blank page belongs to nobody: hand it
         to a second board and the two share a sheet, which is one board changing
         when you write on another. */
      want = writer.fresh(pageOwnedByOther(writer.lastPage(), liveSlot));
      rec.p = want;
      savePages();
    } else if (pageOwnedByOther(want, liveSlot)) {
      /* Already sharing. Give this one its own copy: the working stays where it
         is on screen -- nothing disappears out from under anybody -- and from
         here the two boards go their own ways. Repaired when the board is opened
         rather than in a sweep, because that is when the copy becomes the page in
         hand and the ordinary save carries it to disk. */
      want = writer.clone(want);
      rec.p = want;
      savePages();
      loadedTurn = null;
    } else if (want !== writer.at()) {
      writer.go(want);
      /* A different page is a different answer: whatever was loaded is not on
         this one. */
      loadedTurn = null;
    }
  }

  var id = answering.turn ? answering.turn.id + ":r" + answering.turn.rev : null;
  if (id === loadedTurn) return;
  if (!answering.turn) {
    /* Nothing sent against this question yet. The page is either blank or holds
       working in progress, and both are right -- there is nothing to restore and
       nothing to destroy. */
    loadedTurn = null;
    return;
  }
  /* And only when the page is empty. Once there is ink on this question's page
     it IS the answer, newer than anything the server can hand back, and
     replacing it would throw away everything written since the last send. */
  if (writer.inkOn && writer.inkOn() > 0) {
    loadedTurn = id;
    return;
  }
  var mark = id;
  fetch(atSession(answering.turn.ink)).then(function (r) { return r.json(); })
    .then(function (data) {
      if (mark !== (answering.turn && answering.turn.id + ":r" + answering.turn.rev)) return;
      writer.load(data);
      loadedTurn = mark;
    })
    .catch(function () { /* offline: leave whatever is on the surface */ });
}

/* Confirm, and get out of the way. Closing the panel here is what made a
   correction impossible: the ink was gone from under you the moment it went. */
var hintWas = null, hintTimer = null;

function toastSent() {
  var hint = document.getElementById("writer-hint");
  if (!hint) return;
  if (hintWas === null) hintWas = hint.textContent;
  hint.textContent = "sent — keep writing, Send again to update it";
  hint.classList.add("just-sent");
  clearTimeout(hintTimer);
  hintTimer = setTimeout(function () {
    hint.textContent = hintWas;
    hint.classList.remove("just-sent");
  }, 2600);
}

/* ------------------------------------------------------------------ input */
/* --------------------------------------- one answer panel, two surfaces */
/* The student writes on the slate or types, whichever they ANSWERED with last.
   A typed draft is kept per question, as the slate keeps a page per question.
   The ink carries over between questions (`carryOver`) and typing does not: a
   typed box opens only with what was typed against THAT question. */

var ANSWER_KIND = "answer-kind";
var textDrafts = {};            /* question id -> typed draft */
var textDraftsSeeded = false;
var lastTextQuestion = null;
var textSaveTimer = null;

/* WHICH SITTING A REMEMBERED HALF BELONGS TO.

   The remembered half is a fact about an evening, not about a browser. `opened`
   is rewritten every time a sitting starts and `course` names the workspace, so
   the two together name this sitting and no other. A half remembered anywhere
   else reads as belonging to no sitting at all, which is what lets the aim
   answer the first question of this one -- see `answerKind`. */
function sittingTag() {
  var st = (lastLive && lastLive.state) || {};
  return (SESSION ? "s:" + SESSION : (st.course || "")) + " @ " + (st.opened || "");
}

/* THE HALF A QUESTION WITH NO HISTORY OF ITS OWN OPENS ON: whichever half the
   last answer was SENT on (`say`, the writer's `onSend`, or a tab press). The
   first question of a session has no last, so `doingTurn` answers: teach is
   the board, do is the keyboard. */
function answerKind() {
  try {
    var saved = JSON.parse(localStorage.getItem(ANSWER_KIND) || "null");
    if (saved && saved.sitting === sittingTag()
        && (saved.kind === "type" || saved.kind === "write")) {
      return saved.kind;
    }
  } catch (e) {}
  return doingTurn((lastLive && lastLive.state) || {}) ? "type" : "write";
}

/* Stamped with the sitting it was answered in. An untagged value parses as
   nothing and is ignored, which is the honest reading of one: nothing can say
   which evening it came from. */
function setAnswerKind(kind) {
  try {
    localStorage.setItem(ANSWER_KIND,
                         JSON.stringify({ kind: kind, sitting: sittingTag() }));
  } catch (e) {}
}

function seedTextDrafts(data) {
  if (textDraftsSeeded) return;
  textDraftsSeeded = true;
  var d = data.text_drafts || {};
  Object.keys(d).forEach(function (q) { textDrafts[q] = d[q]; });
}

function flushTextDraft() {
  clearTimeout(textSaveTimer);
  textSaveTimer = null;
  if (!lastTextQuestion) return;
  api("/text/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: lastTextQuestion,
                           text: textDrafts[lastTextQuestion] || "" })
  }).catch(function () {});
}

function saveTextDraft() {
  if (!answering.question) return;
  var q = answering.question;
  textDrafts[q] = els.saybox.value;
  clearTimeout(textSaveTimer);
  textSaveTimer = setTimeout(function () {
    api("/text/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, text: textDrafts[q] || "" })
    }).catch(function () {});
  }, 800);
}

function restoreTextDraft() {
  if (!answering.question) { els.saybox.value = ""; return; }
  if (lastTextQuestion === answering.question) return;
  if (lastTextQuestion !== null) flushTextDraft();
  lastTextQuestion = answering.question;
  /* A different question is a different answer, so nothing typed into this box
     is a correction to anything until the block above it is tapped. */
  correctingTurn = null;
  els.saybox.value = textDrafts[answering.question] || "";
  autosize();
}

/* Which surface a question opens on: what the person asked for on THIS
   question, else the one it was answered with, else the remembered choice. A
   decision outranks an inference from what is on disk. */
var pickedKind = {};

function panelKind() {
  var q = answering.question;
  if (q && pickedKind[q]) return pickedKind[q];
  var t = answering.latest;
  if (t) {
    if (t.kind === "ink" || t.kind === "annotation") return "write";
    if (t.kind === "text" && !t.signal) return "type";
  }
  return answerKind();
}

/* A tab press, recorded against the question it was pressed on. */
function pickKind(kind) {
  if (answering.question) pickedKind[answering.question] = kind;
  setAnswerKind(kind);
  paintPanel();
}

/* The write half or the type half, decided by the question's own history and the
   remembered kind. */
function paintPanel() {
  var open = !els.writer.hidden;
  /* The live board gets the same offer the dormant ones get, in the same words:
     this is where the person actually is when a follow-up question lands them on
     a blank sheet. */
  paintCarry(els.carry, open ? liveSlot : null);
  var typing = open && panelKind() === "type";
  els.typebox.hidden = !typing;
  var slate = document.getElementById("slate");
  if (slate) slate.hidden = typing;
  document.getElementById("drawbar").hidden = !(open && !typing);
  els.tabWrite.classList.toggle("on", !typing);
  els.tabType.classList.toggle("on", typing);
  /* THE BOX BELONGS TO THE QUESTION, NOT TO WHICHEVER TAB IS SHOWING: the draft
     is restored whenever the panel is open. What was sent comes back ABOVE the
     box (`paintSay`), never into it. Typesetting and sizing happen only on the
     half that is showing: neither KaTeX nor `scrollHeight` measures what is
     hidden. */
  if (open) restoreTextDraft();
  syncSaid();
  if (typing) { paintSay(); autosize(); }
  else if (writer) requestAnimationFrame(writer.relayout);
}

/* Which typed answer the box is CORRECTING, as opposed to answering afresh.
   Every typed answer used to overwrite the one before it because the send asked
   `answering.latest` -- the newest turn on the question, of any kind -- and a
   question stays open for an evening. Set in exactly two places: the tap on the
   block above the box, and nowhere else that puts words into the box. Anything
   typed into an empty box is a new answer, and new answers are kept. */
var correctingTurn = null;

/* ------------------------------------------ the rendered block above the box */
/* THE TYPED HALF KEEPS WHAT IT SENT, IN PLACE, RENDERED, as sent ink stays on
   its board. One block above the box is the preview while typing and the record
   once sent, through the same renderer a card uses. `#saybox` stays a textarea:
   `contenteditable` would cost autocorrect, undo, selection, `autosize`, the
   draft save and the ⌘-Enter send. */

/* Text that is trying to be mathematics: a dollar, a TeX delimiter, or a
   backslash command. Any of those and the block opens; prose with none of them
   leaves this panel exactly the height it was. */
var TEX_LIKE = /\$|\\\(|\\\[|\\[A-Za-z]/;

/* A backslash command with no delimiter around it, which renders as NOTHING.
   Asked of `protect`, so math, code and fences are already parked. A HINT, not
   a fix: `\d+` and `C:\temp` are backslash commands too, and this board is used
   for code. */
function bareCommand(src) {
  var store = [];
  var left = protect(String(src || "").replace(/\r\n/g, "\n"), store);
  var m = /\\([A-Za-z]+)/.exec(left);
  return m ? m[0] : null;
}

/* The newest typed answer to the question now open, kept here as well as read
   off the payload: the block has to hold the words on the frame AFTER the send,
   and the payload that carries the turn back is a round trip away. */
var saidNow = null;

function syncSaid() {
  var t = answering.latest;
  if (t && t.kind === "text" && !t.signal && t.text) {
    saidNow = { question: answering.question, text: t.text, turn: t.id };
    return;
  }
  if (!saidNow || saidNow.question !== answering.question) saidNow = null;
}

/* Not the draft save's 800ms, which is the one thing here that is deliberately
   NOT shared with it. A save nobody sees can wait; a preview that arrives most
   of a second after the keystroke reads as broken rather than as considered. */
var SAY_SHOW_MS = 160;
var sayShowTimer = null;

function laterPaintSay() {
  clearTimeout(sayShowTimer);
  sayShowTimer = setTimeout(paintSay, SAY_SHOW_MS);
}

function paintSay() {
  clearTimeout(sayShowTimer);
  sayShowTimer = null;
  var typed = els.saybox.value;
  if (TEX_LIKE.test(typed)) {
    var bare = bareCommand(typed);
    els.said.dataset.state = "preview";
    els.said.removeAttribute("tabindex");
    els.saidLabel.textContent = "as it will read";
    els.saidText.innerHTML = renderMarkdown(typed);
    typeset(els.saidText);
    els.saidHint.hidden = !bare;
    if (bare) els.saidHint.textContent = bare + " will not render — wrap it in $…$";
    els.said.hidden = false;
    return;
  }
  if (saidNow && saidNow.question === answering.question && saidNow.text) {
    els.said.dataset.state = "sent";
    els.said.setAttribute("tabindex", "0");
    els.saidLabel.textContent = "sent · tap to correct";
    els.saidText.innerHTML = renderMarkdown(saidNow.text);
    typeset(els.saidText);
    els.saidHint.hidden = true;
    els.said.hidden = false;
    return;
  }
  els.said.hidden = true;
  els.said.dataset.state = "";
  els.saidText.innerHTML = "";
  els.saidHint.hidden = true;
}

/* THE TAP ON THE BLOCK, the typed counterpart of going back to a board: it
   hands the sent answer back to the box, to be corrected in its place. A tap is
   somebody asking, so it has no guards. */
function correctSaid() {
  if (els.said.dataset.state !== "sent" || !saidNow || !saidNow.text) return;
  correctingTurn = saidNow.turn || null;
  els.saybox.value = saidNow.text;
  autosize();
  saveTextDraft();
  paintSay();
  els.saybox.focus();
}

els.said.addEventListener("click", correctSaid);
els.said.addEventListener("keydown", function (e) {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); correctSaid(); }
});

/* A `$` COSTS A THUMB RATHER THAN A KEYBOARD HUNT.
   The other two ways of getting mathematics out of an iPad keyboard were both
   refused: wrapping anything that looks like TeX misreads a regex and a Windows
   path as formulae, and this board is used in code workspaces. One tap wraps
   what is selected, or drops a pair with the caret between them, and it cannot
   be wrong about what anybody meant. */
function wrapMath() {
  var box = els.saybox;
  var a = box.selectionStart, b = box.selectionEnd;
  if (typeof a !== "number") { a = box.value.length; b = a; }
  var chosen = box.value.slice(a, b);
  box.value = box.value.slice(0, a) + "$" + chosen + "$" + box.value.slice(b);
  box.focus();
  /* Between the pair when there was nothing to wrap; past the closing dollar
     when there was, because the wrapping is the whole edit in that case. */
  var caret = chosen ? b + 2 : a + 1;
  try { box.setSelectionRange(caret, caret); } catch (e) {}
  autosize();
  saveTextDraft();
  paintSay();
}

function autosize() {
  els.saybox.style.height = "auto";
  els.saybox.style.height = Math.min(els.saybox.scrollHeight, 9 * 16) + "px";
}

function say(signal) {
  var text = els.saybox.value.trim();
  if (!text && !signal) return;
  /* THE HALF AN ANSWER WAS SENT ON IS THE HALF THE NEXT QUESTION OPENS ON.
     A signal is a tap on a button rather than an answer given on a surface, so
     it says nothing about which half to offer next. */
  if (!signal) setAnswerKind("type");
  saySending();
  els.saybox.value = "";
  if (answering.question) { textDrafts[answering.question] = ""; }
  autosize();
  /* THE WORDS STAY WHERE THEY WERE TYPED, ON THIS FRAME. Not when the payload
     comes back with the turn on it -- that is a round trip, and what the box
     does in the meantime is the whole of the report. A signal is a tap on a
     button rather than an answer, so it leaves nothing behind. The turn id
     arrives below and is what makes a later tap a revision. */
  if (!signal) {
    saidNow = { question: answering.question, text: text, turn: null };
    paintSay();
  }
  /* A CORRECTION REVISES; A SECOND ANSWER IS A SECOND ANSWER. Only a box holding
     an answer it was HANDED to fix (`correctingTurn`) sends a new revision of it;
     anything typed into an empty box is new and kept, as ink keeps every
     attempt. Signals always start fresh. */
  var revise = (!signal && correctingTurn) ? correctingTurn : null;
  return api("/say", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: text, signal: signal || null,
                           answers: answering.question, turn: revise })
  }).then(function (r) { return r.json(); }).then(function (data) {
    /* Which turn the block is now showing, so that a tap on it corrects the
       answer that is actually on the glass rather than starting a second one. */
    if (data && data.turn && saidNow && !saidNow.turn) saidNow.turn = data.turn;
    /* The box is empty again, so it is correcting nothing. Without this the
       NEXT thing typed into it would be sent as a revision of what was just
       sent, which is the defect wearing a different coat. */
    correctingTurn = null;
    els.sendType.classList.add("sent");
    setTimeout(function () { els.sendType.classList.remove("sent"); }, 900);
  });
}

els.tabWrite.onclick = function () { pickKind("write"); };
els.tabType.onclick = function () { pickKind("type"); };

function sendTyped() {
  if (!els.saybox.value.trim()) return;
  say(null);
}

els.sendType.onclick = sendTyped;

els.sayMath.onclick = wrapMath;

els.saybox.addEventListener("input", function () {
  /* Cleared by hand is starting over, not correcting what was in it. */
  if (!els.saybox.value.trim()) correctingTurn = null;
  autosize();
  saveTextDraft();
  laterPaintSay();
});
els.saybox.addEventListener("keydown", function (e) {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
    e.preventDefault();
    sendTyped();
  }
});

/* There were three signal buttons here -- ready to check, I need help, I'm
   confused -- shown only in a `code` course, docked over the lesson, one tap
   each. They are gone with the mode that produced them. Anything they said is
   said better in a written or typed turn, which every course has and which
   arrives with the sentence that makes it useful; a tap that means "look at what
   I changed" is a tap that leaves the tutor to guess at what and why. */

/* UPLOADS (D21): every file lands in this session's uploads/, with a line
   that wakes no turn. One XHR per batch, because fetch says nothing about
   progress and a 150 MB PDF over Tailscale takes long enough to need it. The
   drawer opens to show it; a refusal or a dropped link is an error line that
   stays until it is dismissed. The server takes at most 1 GB a body. */
var UPLOAD_MAX = 1024 * 1024 * 1024;

function sizeWords(n) {
  if (n < 1024) return n + " B";
  var units = ["KB", "MB", "GB"];
  var i = -1;
  do { n /= 1024; i++; } while (n >= 1024 && i < units.length - 1);
  return (n >= 10 ? Math.round(n) : Math.round(n * 10) / 10) + " " + units[i];
}

function uploadLine(cls) {
  var line = document.createElement("div");
  line.className = "upload-line " + cls;
  var words = document.createElement("span");
  words.className = "upload-words";
  line.appendChild(words);
  document.getElementById("upload-state").appendChild(line);
  return line;
}

function uploadFailed(line, why) {
  line.className = "upload-line bad";
  line.querySelector(".upload-words").textContent = why;
  var bar = line.querySelector("progress");
  if (bar) bar.remove();
  var x = document.createElement("button");
  x.type = "button";
  x.className = "upload-dismiss";
  x.textContent = "✕";
  x.title = "dismiss";
  x.onclick = function () { line.remove(); };
  line.appendChild(x);
}

/* `then(got)` is handed the server's answer once every file is in: Annotate
   a PDF opens the one it sent (`got.files[0].doc`) in the reader. */
function upload(files, then) {
  if (!files || !files.length) return;
  var list = Array.prototype.slice.call(files);
  var total = list.reduce(function (n, f) { return n + (f.size || 0); }, 0);
  var label = list.length === 1 ? list[0].name : list.length + " files";
  if (els.scratch.hidden) {
    els.scratch.hidden = false;
    loadMaterials();
  }
  var line = uploadLine("going");
  var words = line.querySelector(".upload-words");
  if (total > UPLOAD_MAX) {
    uploadFailed(line, label + " is " + sizeWords(total)
      + ": an upload may be at most 1 GB. Nothing was sent.");
    return;
  }
  var bar = document.createElement("progress");
  bar.max = 100;
  bar.value = 0;
  line.insertBefore(bar, words);
  words.textContent = "uploading " + label + " (" + sizeWords(total) + ")";
  var form = new FormData();
  list.forEach(function (f, i) { form.append("f" + i, f, f.name); });
  var xhr = new XMLHttpRequest();
  xhr.open("POST", BASE + "/upload");
  xhr.upload.onprogress = function (e) {
    if (!e.lengthComputable || !e.total) return;
    var pct = Math.floor(100 * e.loaded / e.total);
    bar.value = pct;
    words.textContent = "uploading " + label + ": " + pct + "% of "
      + sizeWords(e.total);
  };
  xhr.onload = function () {
    var got = {};
    try { got = JSON.parse(xhr.responseText || "{}"); } catch (e) { got = {}; }
    if (xhr.status === 200 && got.ok) {
      bar.value = 100;
      line.className = "upload-line done";
      words.textContent = "uploaded " + (got.saved || []).join(", ")
        + ". The tutor reads it with what you say next.";
      setTimeout(function () { line.remove(); }, 6000);
      if (then) then(got);
      return;
    }
    uploadFailed(line, "upload failed (" + xhr.status + "): "
      + (got.error || xhr.statusText || "the board refused it"));
  };
  xhr.onerror = function () {
    uploadFailed(line, "upload failed: the board did not answer. Nothing of "
      + label + " was kept; send it again.");
  };
  xhr.onabort = xhr.onerror;
  xhr.send(form);
}

/* THE SUBJECT'S MATERIALS, asked for each time the drawer opens. A delete
   takes a second tap within 4 s; the file and its ink go to the trash. */
function loadMaterials() {
  var box = document.getElementById("materials");
  var list = document.getElementById("materials-list");
  api("/materials.json").then(function (r) {
    return r.json().catch(function () { return {}; });
  }).then(function (got) {
    if (!got || !got.ok) { box.hidden = true; return; }
    box.hidden = false;
    document.getElementById("materials-head").textContent =
      (got.subject || "the subject") + ": materials";
    list.innerHTML = "";
    if (!(got.materials || []).length) {
      list.innerHTML = '<p class="name">none yet. The tutor files uploads here.</p>';
      return;
    }
    got.materials.forEach(function (m) { list.appendChild(materialRow(m)); });
  }).catch(function () { box.hidden = true; });
}

function materialRow(m) {
  var row = document.createElement("div");
  row.className = "mat-row";
  row.dataset.name = m.name;
  var name = document.createElement("span");
  name.className = "mat-name";
  name.textContent = m.name + "  ·  " + sizeWords(m.size || 0);
  /* A PDF the library offers opens in the reader, its ink keyed on its id. */
  if (m.doc) {
    name.classList.add("is-doc");
    name.setAttribute("role", "button");
    name.title = "open it to read and write on";
    name.onclick = function () {
      els.scratch.hidden = true;
      openDoc(m.doc, m.name);
    };
  }
  row.appendChild(name);
  var del = document.createElement("button");
  del.type = "button";
  del.className = "mat-delete";
  del.textContent = "delete";
  var armed = null;
  del.onclick = function () {
    if (!armed) {
      del.textContent = "tap again to delete";
      del.classList.add("armed");
      armed = setTimeout(function () {
        armed = null;
        del.textContent = "delete";
        del.classList.remove("armed");
      }, 4000);
      return;
    }
    clearTimeout(armed);
    armed = null;
    del.disabled = true;
    del.textContent = "deleting";
    api("/material/delete", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: m.name })
    }).then(function (r) {
      return r.json().catch(function () { return {}; });
    }).then(function (got) {
      if (got && got.ok) { row.remove(); loadMaterials(); return; }
      del.disabled = false;
      del.classList.remove("armed");
      del.textContent = (got && got.error) || "could not delete";
    }).catch(function () {
      del.disabled = false;
      del.classList.remove("armed");
      del.textContent = "the board is not answering";
    });
  };
  row.appendChild(del);
  return row;
}

els.file.addEventListener("change", function () { upload(els.file.files); els.file.value = ""; });

/* ANNOTATE A PDF: one PDF into this session's uploads/, like any upload, and
   then the reader on it. */
var pdfInput = document.getElementById("file-pdf");
if (pdfInput) {
  pdfInput.addEventListener("change", function () {
    var files = pdfInput.files;
    upload(files, function (got) {
      var one = (got.files || []).filter(function (f) { return f.doc; })[0];
      if (!one) return;
      els.scratch.hidden = true;
      openDoc(one.doc, one.name);
    });
    pdfInput.value = "";
  });
}
var annotBtn = document.getElementById("btn-annot-pdf");
if (annotBtn && pdfInput) {
  annotBtn.onclick = function () {
    els.barmenu.hidden = true;
    pdfInput.click();
  };
}

/* paste an image straight from the iPad clipboard */
document.addEventListener("paste", function (e) {
  if (!e.clipboardData || !e.clipboardData.files || !e.clipboardData.files.length) return;
  upload(e.clipboardData.files);
});

/* Drag and drop anywhere. iPadOS raises dragenter for gestures that are not
   file drags and may never raise the dragleave, so the overlay opens only for
   a drag carrying files, closes on every event that ends one, has a watchdog,
   and is pointer-events: none. */
var dragDepth = 0;
var dragWatchdog = null;

function carriesFiles(e) {
  var dt = e.dataTransfer;
  if (!dt) return false;
  if (dt.types) {
    for (var i = 0; i < dt.types.length; i++) {
      if (dt.types[i] === "Files") return true;
    }
  }
  return false;
}

function showDrop() {
  els.drop.hidden = false;
  clearTimeout(dragWatchdog);
  dragWatchdog = setTimeout(hideDrop, 1500);
}

function hideDrop() {
  dragDepth = 0;
  clearTimeout(dragWatchdog);
  els.drop.hidden = true;
}

window.addEventListener("dragenter", function (e) {
  if (!carriesFiles(e)) return;
  e.preventDefault();
  dragDepth++;
  showDrop();
});
window.addEventListener("dragover", function (e) {
  if (!carriesFiles(e)) return;
  e.preventDefault();
  showDrop();
});
window.addEventListener("dragleave", function (e) {
  dragDepth = Math.max(0, dragDepth - 1);
  if (!dragDepth) hideDrop();
});
window.addEventListener("drop", function (e) {
  /* Always prevent the default: a dropped link would otherwise navigate the
     board away to whatever was dragged. */
  e.preventDefault();
  hideDrop();
  upload(e.dataTransfer && e.dataTransfer.files);
});
window.addEventListener("dragend", hideDrop);

/* Coming back to the app, or touching anything, means no drag is in progress. */
["blur", "focus", "pageshow", "touchstart", "pointerdown", "scroll"].forEach(function (t) {
  window.addEventListener(t, function () {
    if (!els.drop.hidden) hideDrop();
  }, { passive: true });
});
document.addEventListener("visibilitychange", function () { hideDrop(); });

/* ------------------------------------------------------------------ chrome */
var FS_KEY = "board.fontsize";

function setFontSize(px) {
  px = Math.max(14, Math.min(30, px));
  document.documentElement.style.setProperty("--fs", px + "px");
  try { localStorage.setItem(FS_KEY, String(px)); } catch (e) {}
}
function currentFontSize() {
  var v = parseInt(getComputedStyle(document.documentElement).getPropertyValue("--fs"), 10);
  return isNaN(v) ? 18 : v;
}

document.getElementById("btn-bigger").onclick = function () { setFontSize(currentFontSize() + 1); };
document.getElementById("btn-smaller").onclick = function () { setFontSize(currentFontSize() - 1); };
/* The theme is `typeface.js`'s, one function for every page. */
document.getElementById("btn-theme").onclick = function () {
  if (window.Typeface) window.Typeface.theme("next");
};
document.getElementById("btn-print").onclick = function () { window.print(); };
/* HOW MUCH IS ON THE LIVE SURFACE, for the photograph: `shot.js` skips a blank
   live board and keeps unsent working. Set here at the top level, because the
   slate is mounted lazily. No writer is nothing written; a writer that cannot
   answer is kept. */
if (window.TutorShot) {
  window.TutorShot.url = BASE + "/export/shot";
  window.TutorShot.liveInk = function () {
    if (!writer || !writer.strokes) return 0;
    try { return writer.strokes(); } catch (e) { return 1; }
  };
}

/* Three controls, one document, and none of them navigates this window. */
els.pushedGet.onclick = function (e) { saveCopy(bannerKind, e.currentTarget); };
els.pushedView.onclick = function () { readKind(bannerKind); };

/* A PAGE, so it is a navigation rather than a panel -- and a plain one, the way
   the slate is: the lesson is files and is still here when you come back, and
   nothing on the library page can change it. */
document.getElementById("btn-library").onclick = function () {
  window.location.href = BASE + "/library";
};


/* Escape leaves the document, the way it leaves the picture viewer. A panel
   that covers the whole glass needs more than one way out of it. */
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape" && paperOpen) closeReader();
});
document.getElementById("btn-export").onclick = function () { doExport(); };
document.getElementById("btn-export-hw").onclick = doExportHomework;
/* WHAT JUST HAPPENED, read on the device that saw it. Built only when it is
   opened: the whole design of the buffer is that it costs nothing until then. */
function paintTrace() {
  var host = document.getElementById("trace-list");
  askShell();                 /* it may have installed since the page opened */
  var head = document.getElementById("trace-shell");
  if (head) head.textContent = shellHead();
  askCode();
  host.textContent = "";
  if (!traceLog.length) {
    var none = document.createElement("div");
    none.className = "tr-of";
    none.textContent = "nothing recorded yet.";
    host.appendChild(none);
  }
  traceLog.forEach(function (e) {
    var row = document.createElement("div");
    row.className = "tr";
    row.dataset.what = e.what;
    var at = document.createElement("span");
    at.className = "tr-at";
    at.textContent = e.at;
    var what = document.createElement("span");
    what.className = "tr-what";
    what.textContent = e.what;
    var of = document.createElement("span");
    of.className = "tr-of";
    of.textContent = e.of ? traceSay(e.of) : "";
    row.appendChild(at);
    row.appendChild(what);
    row.appendChild(of);
    host.appendChild(row);
  });
  host.scrollTop = host.scrollHeight;
  /* THE ONE LINE THAT SAYS WHETHER ANYTHING IS WRONG, so the panel answers the
     question before it is read line by line. A stall is the main thread having
     been away longer than the watchdog waits: the card lands whole and the
     board still waits for it, so what was lost is the pacing and not the order.
     A skip is a card that never held at all. */
  var stalls = traceLog.filter(function (e) { return e.what === "stall"; }).length;
  var skips = traceLog.filter(function (e) { return e.what === "skip"; }).length;
  document.getElementById("trace-said").textContent =
      stalls ? stalls + " stall(s): the main thread was away, so a card landed "
                      + "whole instead of typing. The next board still waited "
                      + "for it."
    : skips ? skips + " card(s) took no hold at all — they arrived whole."
    : traceLog.length + " moves, and nothing in them looks wrong.";
}

function traceSay(of) {
  var out = [];
  Object.keys(of).forEach(function (k) { out.push(k + "=" + of[k]); });
  return out.join(" ");
}

document.getElementById("btn-trace").onclick = function () {
  paintTrace();
  els.trace.hidden = false;
};
document.getElementById("trace-close").onclick = function () {
  els.trace.hidden = true;
};
/* Copied as text, because the person who can see the fault is not the person
   who can read the source, and reading three hundred lines aloud is not a bug
   report. */
document.getElementById("trace-copy").onclick = function (e) {
  /* THE SHELL FIRST, BEFORE A SINGLE MOVE. Three hundred lines pasted into a
     report say what the board did; the first line says which board did it. */
  var text = [traceHead()].concat(traceLog.map(function (x) {
    return x.at + "\t" + x.what + "\t" + (x.of ? traceSay(x.of) : "");
  })).join("\n");
  var said = e.currentTarget;
  var back = function (word) {
    said.textContent = word;
    setTimeout(function () { said.textContent = "copy"; }, 1200);
  };
  try {
    navigator.clipboard.writeText(text).then(function () { back("copied"); },
                                            function () { back("select it"); });
  } catch (err) { back("select it"); }
};

document.getElementById("btn-reload").onclick = function () { location.reload(); };
/* Nothing live has ever arrived, so the shell itself may be a cached one --
   reload rather than merely re-open the stream. */
document.getElementById("offline-retry").onclick = function () { location.reload(); };
document.getElementById("linkbad-retry").onclick = function () { connect(); };

/* The first turn of a session, from the device. Sending it makes the board
   non-empty, so the empty state (and this button with it) goes away on the next
   frame -- but disable it immediately, because a tutor woken four times writes
   four opening cards. */
/* Declining the prompt is still a turn: it is in the transcript, and it wakes the
   tutor the same way an answer does, because the tutor has to carry on. */
if (els.carry) {
  els.carry.onclick = function () { carryHere(liveSlot); };
}
els.skip.onclick = function () {
  els.skip.disabled = true;
  say("skip").then(function () {
    els.skip.disabled = false;
  }, function () {
    els.skip.disabled = false;
  });
};

els.begin.onclick = function () {
  els.begin.disabled = true;
  /* Say which of the two this is. With a tutor attached the request is being
     waited on; with none, the send STARTS one (see `spawn.wake_tutor`) and the
     honest word for that is "starting", not "nobody is reading this" -- which
     was true when the request went into an inbox and stayed there, and is a
     needless fright now that it does not. */
  els.begin.textContent = attached ? "asked — waiting for the tutor"
                                   : "asked — starting the tutor…";
  sentAt = Date.now();
  say("begin").catch(function () {
    els.begin.disabled = false;
    els.begin.textContent = "ask the tutor to begin";
  });
};
if (els.reopen) {
  els.reopen.onclick = function () {
    /* On a lesson with an open question this is that question. With none -- a
       tutor that posed the exercise in a `lesson` card and asked at the foot of
       it -- it is the newest card, so what they write is ABOUT something and
       keeps a board of its own. Empty only when there is no card at all. */
    reopenedFor = lastNewestQ || lastNewestCard;
    workingOn = null;
    workingOnAt = null;
    /* The pin belongs to the board it was set on, and this asks for a different
       surface. Left standing it would spend a carry's grace on a question the
       carry has nothing to do with. */
    pinCarried = false;
    pinHeld = false;
    els.reopen.hidden = true;
    if (lastLive) render(lastLive);
    /* Straight to it: the button was pressed because there was something to
       write, and hunting for the surface that just appeared is not part of it. */
    setTimeout(function () {
      if (!els.writer.hidden && els.writer.scrollIntoView) {
        els.writer.scrollIntoView({ block: "center", behavior: "smooth" });
      }
    }, 60);
  };
}

if (els.addFile) {
  els.addFile.onclick = function () { els.file.click(); };
}

document.getElementById("btn-scratch").onclick = function () {
  els.scratch.hidden = !els.scratch.hidden;
  if (!els.scratch.hidden) loadMaterials();
};
document.getElementById("btn-scratch-close").onclick = function () { els.scratch.hidden = true; };
document.getElementById("btn-history").onclick = openHistory;
document.getElementById("btn-history-close").onclick = function () {
  document.getElementById("history").hidden = true;
};
document.getElementById("reading-back").onclick = backToLesson;
els.jump.onclick = function () {
  revealNewest(true);
  els.jump.hidden = true;
};

/* --------------------------------------------------------- the way back ----

   A pinch-zoomed page has no reliable reverse gear, so one tap puts the
   magnification back. Placement, dragging and the first tap are `recentre.js`,
   shared with the front door. In order down the glass:

     #panic     the page's own magnification, put back. The one that is dragged.
     #findink   the view, put back over the writing.
     #notesend  the marks on the lesson, handed over through a picker. */
/* Safari pinches the page from `gesturestart` whatever `touch-action` says on
   some builds, so the page pinch is refused here as well as in `board.css`. The
   writing surface reads its pinch from pointer events, which this does not
   touch. Under `page-magnified` (`readerzoom.js`: a document open on
   a page Safari has magnified) the pinch is Safari's, the way back out. */
["gesturestart", "gesturechange"].forEach(function (t) {
  document.addEventListener(t, function (e) {
    if (!document.documentElement.classList.contains("page-magnified")) e.preventDefault();
  }, { passive: false });
});

function panicSoon() { if (window.Recentre) window.Recentre.soon(); }
function panicPlace() { if (window.Recentre) window.Recentre.place(); }
function panicRemeasure() { if (window.Recentre) window.Recentre.remeasure(); }

if (els.panic && window.Recentre) {
  window.Recentre.mount({
    key: "board.panic",
    /* Safari kept its zoom: the newest card, brought under the glass. */
    onStuck: function () { revealNewest(true); },
    buttons: [
      { el: els.panic },
      { el: els.findink, onTap: function (el) {
          if (!writer || !writer.fitInk) return;
          writer.fitInk();
          window.Recentre.flash(el);
        } },
      /* Its tap is registered here rather than as a `click` listener of its
         own, because `Recentre` has to tell a tap from a press-and-hold to move
         the button -- two listeners would fire one after the other. */
      { el: els.notesend, w: 150, onTap: notesTap },
    ],
  });
}


window.addEventListener("scroll", function () {
  /* `following` reads a rectangle, which forces layout, and this fires for
     every frame of a flick. It is only ever asked while there is a button to
     put away. */
  if (els.jump.hidden) return;
  if (following()) els.jump.hidden = true;
});
try {
  var savedFs = localStorage.getItem(FS_KEY);
  if (savedFs) setFontSize(parseInt(savedFs, 10));
} catch (e) { /* the sheet's own size stands */ }

connect();

/* the browser drops SSE when a phone sleeps; reconnect on wake */
document.addEventListener("visibilitychange", function () {
  if (!document.hidden && (!source || source.readyState === 2)) connect();
});

/* ------------------------------------------------------------------ PWA */
/* Registering needs a secure context. Over Tailscale HTTPS or on localhost
   this installs the app shell; over plain HTTP it is skipped and everything
   still works, just without offline start-up. */
if ("serviceWorker" in navigator && window.isSecureContext) {
  /* Swiping out of an installed iOS app and back in RESUMES it, so an update is
     asked for every time the app comes back to the foreground.

     BUT NEVER OUT FROM UNDER SOMEBODY WHO IS READING IT. A reload loses the
     scroll position, folds every card and flashes white mid-proof, and a new
     worker arrives at a moment nobody chose. So a new worker is NEWS: taken at
     once when the page is hidden, offered in a strip otherwise, and never while
     there is ink the disk has not been told about. */
  var hadController = !!navigator.serviceWorker.controller;
  var reloading = false;
  var updateWaiting = false;

  function inkOwed() {
    try {
      if (writer && writer.owed && writer.owed()) return true;
    } catch (e) { /* no surface mounted; nothing owed */ }
    return false;
  }

  /* Whether now is a moment a reload costs nothing. Hidden is the whole of it:
     nothing is being read, nothing is being written, and the page comes back
     rebuilt rather than torn down. */
  function reloadIsFree() {
    return document.hidden && !inkOwed();
  }

  function takeUpdate() {
    if (reloading) return;
    if (inkOwed()) return;             /* the ink first, always */
    reloading = true;
    location.reload();
  }

  function offerUpdate() {
    if (!els.newver || reloading) return;
    if (reloadIsFree()) { takeUpdate(); return; }
    els.newver.hidden = false;
  }

  navigator.serviceWorker.addEventListener("controllerchange", function () {
    if (!hadController || reloading) return;   /* not the first install */
    updateWaiting = true;
    offerUpdate();
  });

  /* The moment the app is put down is the moment to take it. */
  document.addEventListener("visibilitychange", function () {
    if (updateWaiting && document.hidden) takeUpdate();
  });

  if (els.newver) {
    els.newverNow.onclick = takeUpdate;
    els.newverLater.onclick = function () {
      els.newver.hidden = true;        /* still waiting; taken when put down */
    };
  }

  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).then(function (reg) {
      function check() {
        if (!document.hidden) { try { reg.update(); } catch (e) {} }
      }
      document.addEventListener("visibilitychange", check);
      window.addEventListener("pageshow", check);
      window.addEventListener("focus", check);
    }).catch(function () {});
  });
}

})();
