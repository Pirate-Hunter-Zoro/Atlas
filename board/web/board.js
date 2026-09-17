/* ==========================================================================
   board.js -- client for the live tutoring board.

   Holds one Server-Sent Events connection open. Every time the tutor writes a
   card file, the server pushes the whole board and this re-renders it: markdown
   to HTML, KaTeX for the mathematics, compiled SVG for anything TikZ. Sending
   text or dropping a file posts back the other way.
   ========================================================================== */

(function () {
"use strict";

var els = {
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
  annbar: document.getElementById("annbar"),
  annPen: document.getElementById("ann-pen"),
  annErase: document.getElementById("ann-erase"),
  annSelect: document.getElementById("ann-select"),
  annClip: document.getElementById("ann-clip"),
  annCopy: document.getElementById("ann-copy"),
  annCut: document.getElementById("ann-cut"),
  annPaste: document.getElementById("ann-paste"),
  annDel: document.getElementById("ann-del"),
  annSay: document.getElementById("ann-say"),
  annUndo: document.getElementById("ann-undo"),
  annRedo: document.getElementById("ann-redo"),
  annClear: document.getElementById("ann-clear"),
  annDone: document.getElementById("ann-done"),
  annotate: document.getElementById("btn-annotate"),
  sendwhat: document.getElementById("sendwhat"),
  sendNotes: document.getElementById("send-notes"),
  sendCancel: document.getElementById("send-cancel"),
  offline: document.getElementById("offline"),
  linkbad: document.getElementById("linkbad"),
  newver: document.getElementById("newver"),
  newverNow: document.getElementById("newver-now"),
  newverLater: document.getElementById("newver-later"),
  hwbar: document.getElementById("hwbar"),
  hwSet: document.getElementById("hw-set"),
  hwCount: document.getElementById("hw-count"),
  hwBuild: document.getElementById("hw-build"),
  jump: document.getElementById("jump"),
  panic: document.getElementById("panic"),
  findink: document.getElementById("findink"),
  mapback: document.getElementById("mapback"),
  redirect: document.getElementById("redirect"),
  steer: document.getElementById("steer"),
  steerNow: document.getElementById("steer-now"),
  steerBox: document.getElementById("steerbox"),
  steerClose: document.getElementById("steer-close"),
  steerCancel: document.getElementById("steer-cancel"),
  steerGo: document.getElementById("steer-go"),
  reopen: document.getElementById("reopen"),
  addFile: document.getElementById("btn-add-file"),
  scratch: document.getElementById("scratch"),
  scratchList: document.getElementById("scratch-list"),
  writer: document.getElementById("writer"),
  sent: document.getElementById("sent"),
  sentText: document.getElementById("sent-text"),
  session: document.getElementById("session"),
  kind: document.getElementById("kind"),
  kindLecture: document.getElementById("kind-lecture"),
  kindSets: document.getElementById("kind-sets"),
  kindReview: document.getElementById("kind-review"),
  kindWalk: document.getElementById("kind-walk"),
  kindStance: document.getElementById("kind-stance"),
  kindWho: document.getElementById("kind-who"),
  kindWhoWays: document.getElementById("kind-who-ways"),
  kindWhoNote: document.getElementById("kind-who-note"),
  kindWhoUp: document.getElementById("kind-who-up"),
  kindAim: document.getElementById("kind-aim"),
  kindAimWays: document.getElementById("kind-aim-ways"),
  trace: document.getElementById("trace"),
  elsewhere: document.getElementById("elsewhere"),
  elsewhereList: document.getElementById("elsewhere-list"),
  elsewhereWho: document.getElementById("elsewhere-who"),
  elsewhereTask: document.getElementById("elsewhere-task"),
  elsewhereSaid: document.getElementById("elsewhere-said"),
  elsewhereGo: document.getElementById("elsewhere-go"),
  stanceTeach: document.getElementById("stance-teach"),
  stanceDo: document.getElementById("stance-do"),
  kindCancel: document.getElementById("kind-cancel"),
  rvbar: document.getElementById("rvbar"),
  rvLead: document.getElementById("rv-lead"),
  rvScope: document.getElementById("rv-scope"),
  rvChange: document.getElementById("rv-change"),
  review: document.getElementById("review"),
  reviewTitle: document.getElementById("review-title"),
  reviewList: document.getElementById("review-list"),
  reviewAll: document.getElementById("review-all"),
  reviewCount: document.getElementById("review-count"),
  reviewStart: document.getElementById("review-start"),
  reviewNote: document.getElementById("review-note"),
  contents: document.getElementById("contents"),
  contentsList: document.getElementById("contents-list"),
  agent: document.getElementById("agent"),
  finish: document.getElementById("finish"),
  finishLead: document.getElementById("finish-lead"),
  finishSub: document.getElementById("finish-sub"),
  save: document.getElementById("btn-save"),
  barmenu: document.getElementById("barmenu"),
  chrome: document.getElementById("chrome"),
  drawbar: document.getElementById("drawbar"),
  notesAgain: document.getElementById("btn-notes-again"),
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
  papersPanel: document.getElementById("papers"),
  papersList: document.getElementById("papers-list"),
  paper: document.getElementById("paper"),
  paperName: document.getElementById("paper-name"),
  paperSub: document.getElementById("paper-sub"),
  paperGet: document.getElementById("paper-get"),
  paperInk: document.getElementById("paper-ink"),
  paperKeep: document.getElementById("paper-keep"),
  keepwhat: document.getElementById("keepwhat"),
  paperPages: document.getElementById("paper-pages"),
  carry: document.getElementById("carry"),
  busy: document.getElementById("busy"),
  busyText: document.getElementById("busy-text"),
  busySince: document.getElementById("busy-since"),
  newsBar: document.getElementById("newsbar"),
  newsLead: document.getElementById("news-lead"),
  newsList: document.getElementById("news-list"),
  newsHide: document.getElementById("news-hide"),
  typebox: document.getElementById("typebox"),
  saybox: document.getElementById("saybox"),
  sendType: document.getElementById("send-type"),
  tabWrite: document.getElementById("tab-write"),
  tabType: document.getElementById("tab-type"),
  sendNoAsk: document.getElementById("send-no-ask"),
  file: document.getElementById("file"),
  drop: document.getElementById("drop"),
  map: document.getElementById("map"),
  mapTitle: document.getElementById("map-title"),
  mapCount: document.getElementById("map-count"),
  mapFit: document.getElementById("map-fit"),
  mapClose: document.getElementById("map-close"),
  mapPlane: document.getElementById("map-plane"),
  mapSheet: document.getElementById("map-sheet"),
  mapLoose: document.getElementById("map-loose"),
  mapWhy: document.getElementById("map-why"),
  work: document.getElementById("work"),
  workTitle: document.getElementById("work-title"),
  workSub: document.getElementById("work-sub"),
  workList: document.getElementById("work-list"),
  workText: document.getElementById("work-text"),
  workClose: document.getElementById("work-close")
};

var seenIds = Object.create(null);
var firstPaint = true;
/* Which sitting the last frame was of. `null` until the first one, so the marks
   restored from the very first payload are not thrown away before they are
   drawn. See the note in `render`. */
var sittingKey = null;
/* When a hand last touched the page. Several things here want to put the page
   somewhere and then put it there again a moment later, once the mathematics has
   typeset and the images have decoded and everything above has settled to its
   real height. Repeating a scroll under somebody who has already started reading
   is worse than landing in the wrong place, so every one of those repeats asks
   first. A real gesture, not our own `scrollTo` -- which fires a scroll event
   like any other and would otherwise cancel every repeat immediately. */
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
    if (item.kind === "fence") {
      var body = item.text.replace(/^```[^\n]*\n?/, "").replace(/\n?```\s*$/, "");
      return "<pre><code>" + escapeHtml(body) + "</code></pre>";
    }
    /* math: escaped text, KaTeX walks the text node and replaces it */
    var span = item.display ? "div" : "span";
    return "<" + span + ' class="math-raw">' + escapeHtml(item.text) + "</" + span + ">";
  });
}

function inline(s) {
  return s
    .replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, '<img alt="$1" src="$2">')
    /* AN ADDRESS STAYS IN THIS PAGE. Every other link is the web, and the web
       opens in its own tab so that a tap on a citation is not the lesson
       leaving the glass. An address is the opposite thing: it is this board
       being asked to go somewhere, and a second tab is a second board. */
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, function (all, text, href) {
      return href.indexOf("#/w/") === 0
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
        out.push('<div class="figure"><img alt="figure" src="/figure/' + id + '.svg"></div>');
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
      macros: window.BOARD_MACROS || {},
      throwOnError: false,
      errorColor: "#9a2020",
      strict: false,
      trust: true
    });
  } catch (e) { /* a bad formula must never blank the board */ }
}

/* A SLUG IS NOT A TITLE, AND ON THE GLASS IT IS THE FILENAME SHOWING THROUGH.

   `board write` derives a card's filename from its title, so a tutor that
   passes the slug where the title goes gets the slug drawn across the top of the
   card -- reported as `LESSON not-for-every-i-for-one-i-and-that-is-the-whole-fix`
   and, accurately, "What an eyesore."

   It is not deleted: it stays in the front matter and it still names the file,
   which is where it earns its keep. It is simply not a sentence written for a
   reader, so it is not drawn as one -- and for a `lesson` card, whose head
   exists only to carry a title, that takes the whole head away with it.

   The test is narrow on purpose. No whitespace, all lower case, and three or
   more parts joined by hyphens or underscores: that is a file stem. `Well-ordering`
   has a capital and two parts and is a title; so is `mean-square`. */
function cardTitle(c) {
  var said = ((c && c.title) || "").trim();
  if (!said || /\s/.test(said)) return said;
  if (said !== said.toLowerCase()) return said;
  return said.split(/[-_]+/).length >= 3 ? "" : said;
}

/* ------------------------------------------------- what the board just did */
/* A RENDERING FAULT IS OVER BEFORE ANYBODY CAN DESCRIBE IT.

   Two have now been diagnosed from a sentence -- "the next board showed up over
   the yellow pulsing indicator, and then the AI response just all showed up at
   once between the boards" -- and one of those diagnoses was WRONG, because
   nothing anywhere could say whether the card typed, whether the hold was taken,
   or whether it let go early. Each wrong guess costs somebody an evening and
   then another report in the same words.

   So the board keeps its own last few hundred moves and `☰ → what just
   happened` reads them back on the device, with a copy button, because the
   person who can see the fault is not the person who can read the source.

   WHAT IT COSTS, since this runs in every sitting for ever: one small object
   pushed onto a bounded array. Nothing is formatted, nothing touches the DOM and
   nothing is measured until the panel is opened. The uninteresting renders --
   a heartbeat, an uncommitted count changing -- are not recorded at all, or the
   four-a-second poll would bury the twenty lines that matter. */
var TRACE_MAX = 300;
var traceLog = [];
var traceFrom = 0;

function trace(what, of) {
  var now = Date.now();
  if (!traceFrom) traceFrom = now;
  traceLog.push({ at: now - traceFrom, what: what, of: of || null });
  if (traceLog.length > TRACE_MAX) traceLog.shift();
}

/* ------------------------------------------------------------------ render */
var KIND_LABEL = {
  lesson: "lesson",
  question: "your move",
  correct: "correct",
  wrong: "not quite",
  review: "review",
  note: "aside",
  recap: "recap"
};

/* Which kinds are a reply to a piece of working, as opposed to new teaching.

   `note` is in here, and leaving it out was most of why folding did nothing on a
   real lesson: an evening on one exercise produced five `note` cards -- "no, and
   it is a name collision", "the symbol is fixed, which element is h?" -- every
   one of them an answer to something the student had just written, and every one
   of them left open. A `lesson` or a `recap` is material that stands on its own
   and is never folded. */
var REPLY_KIND = { wrong: 1, correct: 1, review: 1, note: 1 };

/* What a reply says about the answer it replied to. Two kinds are a verdict;
   everything else that answers working is "open", which is the amber default
   -- see where `verdictOf` is built. */
var VERDICT_OF = { correct: "correct", wrong: "wrong" };

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
   touched at all -- not moved, not re-appended, not re-inserted.

   This used to collect every kept node into a fragment and append the fragment,
   which detaches and re-inserts the entire lesson on every payload. The DOM is
   happy with that; CSS is not. Taking a node out of the document and putting it
   back restarts its animations, and every `.card` carried an entry animation, so
   each frame slid the whole board up from half a rem and faded it back in --
   read from a chair as the board glitching, shifting, and snapping back to where
   it already was. Payloads arrive for reasons that have nothing to do with the
   lesson (a slate save, a figure finishing, the uncommitted count changing), so
   it happened while nothing on screen had changed at all.

   It also threw away work: re-inserting a subtree forces style, layout and paint
   for the whole lesson, and re-inserting a canvas costs a fresh compositor
   layer. Moving only what actually moved is both correct and most of the fix. */
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
    if (kept) {
      delete have[key];
      if (kept === cursor) {
        cursor = cursor.nextSibling;      /* already in place: leave it alone */
        continue;
      }
      host.insertBefore(kept, cursor);
    } else if (node) {
      host.insertBefore(node, cursor);
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
    /* Before the early return below, because the map belongs to the COURSE and
       not to the lesson in front of it: reading a past lesson must not freeze
       the picture of the repository underneath it. */
    paintMap(data.map, data.state || {});
    if (!pagesLoaded) { pagesLoaded = true; loadPages(); }
    document.getElementById("btn-history").hidden = !(data.history > 0);
    if (reading) { els.jump.hidden = false; return; }
  }
  var state = data.state || {};

  /* WHICH SITTING IS ON SCREEN, AND THE MARKS THAT BELONG TO IT.

     Cards are numbered from 0001 within a sitting, and the annotation store is
     keyed by that number -- so the key `0001` means a different card the moment
     a section is archived or a past lesson is opened. Nothing dropped the store
     at either boundary, and the ink went on being drawn under its old key over
     whatever card now carries it. Reported from the device: old annotations
     showing up on new tutoring text blocks.

     The sitting's own stamp is what identifies it, plus its label, because
     `opened` is to the minute and two sittings can share one. A past lesson is
     named by the archive's own id, which is unique by construction. */
  var sitting = data.archived
    ? "past:" + (reading || "")
    : "live:" + (state.opened || "") + "|" + (state.chapter || "");
  if (sittingKey !== null && sitting !== sittingKey && window.Annotate) {
    window.Annotate.forget();
  }
  sittingKey = sitting;

  els.course.textContent = state.course || "board";
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

     Everything the answer block is made of hangs off a card id: which board is
     open, which page it is on, where the surface sits in the transcript,
     whether a sent answer is a live board or a dead picture of one. All of it
     was hung off `kind: question` alone -- and a tutor that poses the exercise
     in a `lesson` card and asks at the foot of it, which is easy to do and
     breaks nothing visible on the board, left the student's ink with nothing to
     be about. It froze into a picture the moment it was sent, no board was kept
     for it, and there was nothing to revise in place. Reported as: "my written
     response was frozen in an image above ... ALL boards were independent of
     each other and I could edit them any time. Where did this feature go?"

     So the student's own work is the second authority, and the stronger one: a
     card somebody has written an answer against was a question in the only
     sense that matters here. It is read off the turns, which are on disk, so it
     survives a reload and a second device -- and once a card has one answer it
     keeps its boards for good. */
  var isQuestion = Object.create(null);
  ordered.forEach(function (c, n) {
    at[c.id] = n;
    if (c.kind === "question") isQuestion[c.id] = true;
  });
  /* AND A TURN THAT NAMES NOTHING IS ADOPTED BY THE CARD IT WAS WRITTEN UNDER.

     A page handed in while no card had declared itself a question was recorded
     answering nothing at all, and a turn that is about nothing cannot be given
     a board, kept, revised or found again: it froze into a picture the moment
     it was sent and the lesson lost every board between one response and the
     next. Reported as: "I see no prior board work in between responses
     anywhere, which really disorganizes the tutoring session."

     Which card it was about is not a guess. It is the last one written before
     the page was sent -- the thing they were looking at when they wrote it --
     and both halves of that are on disk, so a lesson recorded before any of
     this comes back with its boards rather than staying broken. Ink only: the
     opening "begin" and a direction change are about the sitting rather than
     about a card, and they keep falling where their time puts them. */
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
  /* THE WAY OUT OF ONE STEP OF COACHING, WITHOUT LEAVING IT.

     A coach card names the calls, the arguments and the order and lets you type
     it, and there was no way out of any one of them: the only escape was the
     aim chooser, which changes the WHOLE sitting to `build` and writes every
     card after it the new way. Asked for as "in coach coding mode, I still want
     to be able to have a 'fuck this, you do this step' option."

     ON THE NEWEST CARD ONLY, because that is the step. The ones above it are
     steps that have already been typed, and a button offering to write them is
     a button that means nothing. `/handover` names the card, the sitting is
     left exactly as it is, and the card that comes back is a report of that
     step with the next one posed under it. See `_handover` in
     `routes/lesson.py`. */
  var coaching = live && (state.aim_now || state.aim || "") === "coach";
  var thisStep = ordered.length ? ordered[ordered.length - 1].id : "";

  /* Whether a written answer already has a board carrying the same ink.

     The transcript froze every ink answer into a picture at the moment it was
     sent -- which was right when the slate was one surface that got written
     over, because then the picture was the only copy of what had been handed in.
     It is not one surface any more: every question owns a page, nothing is ever
     wiped, and that page is still under the board at the end of the question's
     run. So the picture and the board are two copies of the same ink, one of
     them dead, and going back up the lesson to an earlier answer found the dead
     one. The board is the answer.

     The rule already existed for the newest unanswered turn, a few lines below,
     for exactly this reason. This is that rule, now that every question can keep
     one. The picture comes back the moment there is no board to replace it:
     a filed lesson, a past one, a browser that has never held this question's
     page -- the mapping is local to the device that wrote it -- or a surface
     that has not been built yet. */
  function onABoard(m) {
    if (!(live && !!writer && m.kind === "ink" && !!m.png
          && !!m.answers && !!isQuestion[m.answers])) return false;
    var found = false;
    slotsOf(m.answers).forEach(function (k) {
      if (boardPage[k].p !== undefined) found = true;
    });
    return found;
  }

  /* Feedback supersedes feedback. An answer is versioned and only its newest
     revision is rendered -- three goes at Exercise 1.3 show as one attempt --
     but the cards that replied to the first two were never versioned, so they
     stayed open beside the third. Three "not quite" cards then sat in a row
     under a single piece of working, and the reading order said they were
     three live objections to what is on screen now, when two of them were
     about ink that had already been rewritten. It is the reply, not the
     lesson, that has been replaced: only the newest reply to the open question
     stays open. The ones it replaced fold to their heading, one line each, and
     open again on a tap -- a transcript keeps both halves and this removes
     nothing. */
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

  /* AND THE NEWEST REPLY IN A QUESTION'S RUN IS THE VERDICT ON WHAT THEY SENT.

     Asked for in these words: "if I'm right in my response, put a nice green
     sidebar down the response as it comes back. Red if I'm wrong. Yellow if
     it's not really a right/wrong situation -- like if we're vibe-coding or I
     ask a question." Every sitting, not only a lecture: a step that worked, a
     step that did not, and a question put back to the person are the three
     moods of a build as much as of a proof.

     AMBER IS THE DEFAULT, NOT A THIRD CASE. Most replies in a doing sitting and
     most in a walkthrough are neither right nor wrong -- `note` and `review`
     are the tutor answering rather than marking -- and a surface that knows
     only green and red has to guess at all of them.

     `--ask` is that amber, and not `--note`, which the kinds use for `review`:
     `--note` is the blue of an aside, and what was asked for is yellow.

     WAITING IS NOT AMBER. A question whose reply has not arrived is a different
     state from one answered with something that is neither right nor wrong, and
     painting both the same colour is the defect this exists to fix in a new
     coat. So an unanswered turn carries no verdict at all -- the pulsing strip
     is what says the tutor is reading it -- and the colour arrives with the
     reply, which is exactly when there is something to say.

     This walk is `runEndOf`'s, deliberately: `isQuestion` rather than
     `kind === "question"`, because a tutor who poses the exercise in a `lesson`
     card and asks at the foot of it has asked a question, and the student's own
     answer against that card is what settles it. The folding runs above split
     on the kind alone and are left exactly as they were. */
  var verdictOf = Object.create(null);
  var verdictFor = null;
  ordered.forEach(function (c) {
    if (isQuestion[c.id]) { verdictFor = c.id; return; }
    if (verdictFor && REPLY_KIND[c.kind]) {
      verdictOf[verdictFor] = VERDICT_OF[c.kind] || "open";
    }
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
      /* Under the card it answers -- BUT NEVER ABOVE A CARD WRITTEN BEFORE IT.
         A question stays open for an evening and collects several answers, so
         pinning every one of them to the question card stacked a whole sitting's
         typing hours above the feedback each piece of it was replying to. The
         two rules disagree only when the question is not the newest card, and
         where they disagree the clock is right.

         Ink is unaffected in practice and would be right if it were: its board
         is placed at the end of the question's run by `paintBoards`, and this
         line moves a one-line receipt, not the working. */
      pos = t.kind === "text" ? Math.max(pos, at[t.answers]) : at[t.answers];
    }
    items.push({ pos: pos, sub: 1, t: when, key: "turn:" + t.id, turn: t });
  });
  items.sort(function (a, b) {
    return (a.pos - b.pos) || (a.sub - b.sub) || (a.t - b.t);
  });

  /* TWO QUESTIONS, AND ONLY THE SECOND OF THEM IS ABOUT THE KIND OF ANSWER.
     They shared one condition, which is why a typed answer raised no receipt
     and no pulse at all: "I also don't see the yellow pulsing tutor working
     signal whenever I elect to type a response instead of writing one." What
     was seen instead was the brief `saySending` strip, which expires, and then
     silence for the whole turn.

     IS AN ANSWER OUTSTANDING -- and it is, whether it was typed or written. A
     signal is not one: a tap on "begin" or on an aim is in the transcript
     because they did it, and "sent at 20:14" is a sentence about work handed in.

     IS IT RENDERED INTO THE TRANSCRIPT -- and a page of ink that has been sent
     and not yet answered is not, because the same ink is still on the writing
     surface directly below and a frozen copy of it immediately above is the
     same thing twice. It takes its proper place the moment the tutor replies,
     which is when it stops being "what I am looking at" and becomes "what was
     handed in". That argument is about ink and holds for ink only: a typed
     answer is duplicated nowhere, so it stays. */
  awaitingReply = null;
  var lastItem = items[items.length - 1];
  if (lastItem && lastItem.turn && !lastItem.turn.signal) {
    awaitingReply = lastItem.turn;
    if (lastItem.turn.kind !== "text") items.pop();
  }
  /* AND IT IS STILL OUTSTANDING WHILE THE REPLY IS ARRIVING -- see
     `replyArriving`. `awaitingReply` goes the instant a card's RECORD lands,
     which is before a word of it is on the glass, so this is what the receipt
     keeps talking about for the rest of the type-out.

     Held only against a card. Anything of THEIRS arriving on top -- a signal
     tap, which is a turn and is never a receipt -- means the answer the receipt
     was about is no longer the newest thing they did. */
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
  /* What is on screen already, by key. A payload arrives for all sorts of
     reasons that have nothing to do with the lesson -- the tutor's heartbeat
     lands every thirty seconds while it writes, the uncommitted count changes, a
     figure finishes compiling -- and every one of them used to re-parse the
     markdown of every card, rebuild its DOM, and hand the lot to a reconcile
     that threw all of it away because the keys had not changed. On a tablet
     holding a long lesson that is the whole cost of a frame, spent on nothing.
     Build only what is genuinely new. */
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
    /* A CARD WRITTEN OVER IS A CARD ARRIVING, AND IT USED TO BE NOTHING AT ALL.

       The stamp was identity alone for a card, so a card rewritten in place had
       been seen already: not fresh, not news, not typed out. That is every
       response in a sitting that DOES the work. `board write` lands one sentence
       so the board is not blank, the turn then writes code for four minutes, and
       `board write --over` replaces that sentence with the report -- which
       therefore appeared instantly, whole, with no typing and with the next
       board already sitting under it. Reported from a direction change in
       PSYCH-ASR: "when the response from the agent came back, it just showed up
       suddenly and the next board, etc. was there before it."

       The mtime is the version of a card, exactly as `rev` is the version of a
       turn, and it belongs in the stamp for the same reason. With it here the
       overwrite is fresh, so it types out; `anythingNew` is true, so the send
       stops saying it is in flight; and `typingCards` holds the writing surface
       where it is until the last character lands. One line, and it is what makes
       the typing rule true of EVERY response rather than only of the ones that
       happen to be written once. */
    var stamp = item.key + (item.turn ? ":r" + (item.turn.rev || 1)
                                      : ":m" + Math.round(item.card.mtime));
    var fresh = !firstPaint && !seenIds[stamp];
    /* NEWS IS A CARD. YOUR OWN ANSWER IS NOT NEWS.

       `anythingNew` is the whole basis of the decision at the foot of this
       function, and the only reveal it can lead to is `revealNewest` -- the top
       of the newest thing the TUTOR has written, which on a board with a
       question open sits directly ABOVE the writing surface. So counting a
       fresh turn here means: the moment your own answer appears in the payload
       the send provoked, the page is thrown up to the card above the board you
       just wrote on.
       Reported twice, the second time after the transcript had been stopped from
       shifting underneath anybody: "after I submit my response, it still
       glitch-scrolls me up to above the board." Nothing was shifting by then.
       This was the board deciding, on its own, that something had arrived worth
       reading -- and the something was the student.

       Intermittent because it is gated on `!penBusy()`, whose tail is about a
       second after the last touch: whether the payload beat the tail decided
       whether the page jumped. And the jump is a GLITCH rather than a move
       because `revealSentSettling` re-lands on the surface's foot 300ms and
       900ms after a send, so a payload arriving inside that window is yanked up
       and dragged back.

       A turn appearing has its own answer to where the page should be, and it is
       `revealSent`: the foot of the surface, where the receipt is. Nothing about
       a turn belongs here. */
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
    var wantKey = stamp + (item.card ? (offer ? ":h" : "")
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
      var head = "";
      var shown = cardTitle(c);
      if (c.kind !== "lesson" || shown) {
        head = '<div class="card-head">' +
               '<span class="kind">' + (KIND_LABEL[c.kind] || c.kind) + "</span>" +
               (shown ? '<span class="card-title"></span>' : "") +
               '<span class="card-num">' + c.id + "</span></div>";
      }
      node.innerHTML = head + '<div class="body"></div>';
      if (shown) node.querySelector(".card-title").textContent = shown;
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
        shotWrap.href = m.png;
        shotWrap.className = "slate-shot";
        shotWrap.addEventListener("click", function (e) {
          e.preventDefault();
          openViewer(m.png, "your answer · " + (m.iso || ""));
        });
        var shot = document.createElement("img");
        shot.src = m.png;
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
          a.href = "/uploads/" + encodeURIComponent(f);
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

  /* Reconcile rather than rebuild. Every payload used to blow the lesson away
     and construct it again: every card's markdown re-parsed, every formula
     re-typeset by KaTeX, every compiled figure re-fetched and re-decoded. That
     cost grows with the length of the lesson and is paid on every keystroke of
     the tutor's, on an iPad, for cards that did not change. Nodes are keyed by
     card id and revision, so an unchanged card is left exactly where it is --
     which also keeps its scroll position and any selection inside it. */
  reconcile(els.cards, wanted);
  paintSuperseded(superseded);

  /* KaTeX walks the DOM it is handed. Handing it the whole lesson every frame
     re-renders mathematics that was already rendered; hand it only what was
     just inserted. */
  freshNodes.forEach(typeset);
  freshNodes.length = 0;
  /* After the typesetting, never before: KaTeX measures what it renders, and it
     cannot measure what is display:none.

     AND BEFORE `placeWriter`, WHICH IS THE HALF THAT WAS MISSING. The writing
     surface is held where it is while a card types -- that is what "no next
     board showing up until the agent's response is rendered" means -- and the
     thing it asks in order to decide is `typingCards()`. These two lines used to
     run at the FOOT of this function, a hundred lines after that question was
     asked, so on the one frame that matters -- the frame the response lands on
     -- nothing was typing yet, the surface came straight down under the new
     question, and the answer then filled in above it. Every frame after that
     held correctly, which is why this looked intermittent rather than wrong.

     Nothing else here depends on the order: the cards are in the document by
     now, which is all either pass needs. */
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

  /* WHO CAN BE ASKED, AND WHAT THE LOCAL MODEL'S SERVER IS DOING. Both off the
     payload: the registry is in `bin/tutor` because an agent entry is a command
     recipe, and the server's state is `squeue`, which the browser cannot ask.
     `assistants` stays null when nothing could say -- which is not the same as
     an empty list, and is why the chooser is not drawn rather than drawn empty. */
  if (data.assistants !== undefined) assistants = data.assistants;
  if (data.colibri !== undefined) colibriNow = data.colibri;

  papers = data.papers || {};
  renderPapers();                /* a build that lands while it is open shows */
  paintSession(state, data.push, data.agent, data.export,
               (data.hw && data.hw.build) || null);
  paintHomework(data.hw);
  paintReview(state, data.review, data.walk);
  if (!started) paintWaiting(data);
  seedTextDrafts(data);
  paintNotesSend();
  paintSent();
  paintSave(data.unsaved);
  if (data.sets) knownSets = data.sets;
  if (data.contents) contents = data.contents;
  planInfo = data.plan || null;
  readingInfo = data.reading || null;
  resultsInfo = data.results || null;
  pastCount = data.history || 0;
  /* Once per load, and only now: where a course opens depends on what its
     documents are, and this is the first payload that says. */
  mapLand();

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
  if (workingOn && workingOnAt !== (newestQ || "")) {
    workingOn = null;
    workingOnAt = null;
  }
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
  lastTurns = data.turns || [];
  syncSlots(qids, runEndOf, lastTurns);
  repairPages();
  slotOrder = [];
  qids.forEach(function (q) {
    slotsOf(q).forEach(function (k) { slotOrder.push(k); });
  });

  /* Which BOARD is being written on. Usually the attempt in hand on the newest
     question; whichever they picked, if they went back to an earlier one. A
     board that has scrolled off the top of the transcript is still a board, and
     going back to add a line to the proof on it is ordinary work. */
  if (workingOn && (!boardPage[workingOn]
                    || qids.indexOf(slotQ(workingOn)) === -1)) workingOn = null;
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

  /* The writing surface goes at the END of the transcript, under whatever the
     last thing in it is. That is what makes a correction work the way a person
     expects: the tutor's feedback arrives, and the surface to fix the answer on
     is beneath the feedback rather than scrolled off above it.

     While an answer is waiting to be read there is nothing to put under, so the
     surface stays where it is and says so underneath itself -- see paintSent.
     What it must never do is sit under a frozen copy of the very ink still
     showing on the surface: that is the same thing twice, one above the other. */
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
     that has already been filed. */
  liveSlot = liveKey;
  /* THE HOLD IS ON THE BOARD FOLLOWING A CARD, NEVER ON A TAP.
     Somebody who touches an earlier board is asking for the surface to go there
     now, and a request made by hand outranks an animation. `workingOn` and
     `reopenedFor` are what a tap sets; with either of them the surface moves. */
  placeWriter(owed && !data.archived, qNode, live,
              replyArriving() && !workingOn && reopenedFor === null);
  /* The boards do not come and go with the answer panel.

     They used to: the whole set was torn down the moment nothing was owed, which
     is the moment the tutor writes a `correct` card. So getting an exercise
     RIGHT deleted every board on the page, and scrolling back up through the
     lesson found nothing but the frozen pictures of what had been sent -- which
     is a record of the answer, not a place to carry on working. Reported from
     the device, in exactly those words: "I want the actual writing board
     containing my response".

     The one board that is not drawn is the one the LIVE surface is standing in
     for, because that one is really there. With the panel shut there is no such
     board, and every one of them gets its picture. */
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
  /* And what has landed in the workspaces this one is not. See `paintNews`. */
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
    /* NOTHING ARRIVED. Do not move the page.

       A payload lands for all sorts of reasons that are not a card: the tutor's
       heartbeat every thirty seconds, the uncommitted count changing, a figure
       finishing. The old rule was "if they were at the bottom, scroll to the
       bottom", which on a board already at the bottom is a no-op -- so this was
       invisible for as long as the destination was the bottom. The moment the
       destination became the newest card's first line, every heartbeat yanked
       the page a screenful while nobody was doing anything at all. */
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
    /* A CARD ARRIVING NEVER MOVES THE READER. IT GROWS INTO VIEW.

       Asked for twice, the second time as a specification: "when I submit the
       response, I'm scrolled to the bottom of the written/typed response I just
       submitted, where I can clearly see the 'the tutor is writing...' message,
       and once the tutor response is available, have it start getting portrayed
       for the user to see line by line, WITHOUT scrolling the user down -- they'll
       scroll their own way down to read the response." The first ask named the
       thing it should feel like, which is any chat page on the web: the reader is
       stationary and the text grows downward past them.

       The layout grants it for nothing, which is the good part. Measured: before
       the reply the run is [question][live board], and after it is
       [question][the same board, frozen][receipt][reply][the next board]. The
       student's working keeps its PLACE in the run -- a live surface and a dormant
       board are one box by construction, same head and same height, because a
       dormant board has to be indistinguishable from a live one -- and everything
       new lands below it. So nothing above the reader changes height, the reply
       appears in the space under their working where "the tutor is writing" was,
       and it grows down through it. All that was ever needed was to stop aiming
       the page at it.

       `revealNewest` still exists, and is still right, for the two places that
       are not this: the first paint of a lesson, where there is no reader yet to
       leave alone, and the jump button, which is somebody asking to be taken
       there. The button is the whole of what is left of the old behaviour -- a
       card that begins below the fold has nothing to watch grow, and a page that
       has silently changed under somebody needs to say so. */
    var fresh = newestCardNode();
    var box = fresh && fresh.getBoundingClientRect();
    els.jump.hidden = !!box && box.top < window.innerHeight;
  }
}

/* Where to be after pressing Send: looking at the foot of the writing surface.

   Send is the one moment in a sitting when the interesting thing is BELOW the
   working rather than above it. The receipt that says it arrived sits under the
   surface, and "the tutor is writing" sits under that -- and both of them are
   the answer to the question a person actually has after pressing the button,
   which is whether anything is happening. Landing anywhere above the working
   answers a question nobody asked and hides the two lines that matter.

   The foot of the surface goes a little above the middle of the window, so what
   is under it is on screen with room to spare and the last thing written is
   still visible above it. */
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
  /* And not once a card has arrived.

     These repeats exist to re-land on the surface's foot after the receipt and
     the tutor's chip have settled to their real heights. The moment the tutor
     REPLIES, the surface is not where it was: the reply lands above it and the
     next board opens underneath, so `els.writer` is now a fresh blank sheet
     below the card being read, and landing on its foot drags the reader down
     past the very thing they were waiting for. That is the other half of being
     "scrolled into the middle of that message" -- two smooth scrolls with
     different destinations, one aimed above the card and one below it. */
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
  currentSet = hw && hw.name ? hw.name : null;
  if (!hw) { els.hwbar.hidden = true; return; }
  els.hwbar.hidden = false;

  if (!hw.name) {
    els.hwSet.textContent = "homework";
    els.hwCount.textContent = hw.ambiguous && hw.ambiguous.length
      ? "which set? the tutor has not said" : "no problem set found";
    els.hwBuild.textContent = "";
    els.hwBuild.removeAttribute("data-ok");
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
    return;
  }
  els.hwBuild.dataset.ok = b.ok ? "yes" : "no";
  els.hwBuild.textContent = b.ok
    ? "compiled " + (b.iso || "").slice(11, 16)
    : lastLine(b.detail || "") || "compile failed";
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
      /* STARTING ONE IS NOT INSTANT, AND SILENCE READS AS DEATH.

         A start brings the tailnet link up, starts the board, opens the
         sitting, reads the addresses back and catches the repository up from
         the remote -- all of it with the board already serving this page. Until
         there was a word for it, the record on disk was the LAST run's, whose
         pid is gone, and the board said "tutor stopped, nothing is reading the
         board". Reported from a relaunch: "It seemed to tell me the tutor was
         dead which put me in 'send again' mode leading to massive confusion."

         The ellipsis is deliberate and so is the ordering: this is the first
         thing the strip is asked about, because it is the state most likely to
         be misread as the worst one. */
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
  }
  /* The chip is the first thing the bar gives up width on, and squeezed hard it
     is its status dot and nothing else. So the words live somewhere they can
     still be got at rather than only in a chip that may have been trimmed. */
  els.agent.title = els.agent.textContent;
  var kind = state.session || "lecture";
  sittingKind = kind;
  els.session.hidden = false;
  /* "review", not "test review": the badge sits in a bar that is already at
     capacity, and eleven uppercase letters at this letter-spacing pushed the
     chapter label to "Tes…" and the tutor chip to "no". The strip underneath
     carries the full name, so the bar does not have to. */
  els.session.textContent = kind;
  els.session.dataset.kind = kind;
  els.session.title = "tap to switch: lecture, homework, test review, walkthrough";
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

/* THE BANNER, WHICH IS ABOUT A DOCUMENT AND NOT ABOUT THE SITTING.

   Its own function because three things call it and none of them knows anything
   about the sitting. They used to call `paintSession` with an empty state to
   reach this code, which repainted the session badge as "lecture" for the
   second before the next payload put it back -- a homework sitting announcing
   itself as a lecture at the exact moment somebody exports their homework. */
function paintBanner(push, exported, hwBuilt) {
  /* One banner, THREE things that can land in it. A push, an export and a
     compile of the write-up are all "something slow happened, here is how it
     went", and the newest one is the one the person is waiting on -- an export
     triggers a payload the moment it finishes, and without this that payload
     would repaint the banner with a push from an hour ago.

     THE WRITE-UP'S RECORD COMES OFF DISK NOW, and that is the fix rather than a
     tidying. It used to reach this function once, invented by the client from
     the reply to `/hw/build` and belonging to no file anywhere -- so the very
     next payload, a second later, repainted the banner from `push.json` and
     took the controls for the document with it. Reported from the iPad: "it
     compiles the homework, but it's not letting me view the compiled .pdf or
     save it anywhere locally." The compile had worked. The button lived for
     about a second, and a tap after that did nothing at all, because the URL
     behind it had been cleared. `live/hw.json` is where that record has always
     been written; the payload carries it as `hw.build`. */
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
  /* AND A WAY TO READ IT, AND A WAY TO TAKE IT WITH YOU.

     The repository copy is the archival one and nothing about it changes. But a
     compute node is not a place an iPad can reach, and a tailnet path is not
     something anybody can hand to a professor -- so a document that exists only
     there is a document the person who asked for it cannot use. Asked for in
     exactly those terms: "so I can save it to files in my iCloud, get it on my
     phone, and email it to my prof, lickety split."

     Which document this banner is ABOUT is decided here; whether that document
     EXISTS is decided by the payload, off the files (`papers`), and not by the
     record that happens to be in the banner. Those are different questions, and
     conflating them is what made a `.tex` that failed to compile and a PDF
     sitting on disk look the same from here. */
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
      ? (last.pdf || last.tex) + howMany
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
   THE TWO DOCUMENTS: reading one on the board, and taking one off it.

   THIS WAS AN ANCHOR AND THE ANCHOR WAS A TRAP. Reported from the iPad: "when I
   try to do the local export on the iPad, it just opens the document up, and I
   can't put it anywhere. The only thing I can do is exit the app and go back in
   again."

   Both halves of that are the same mistake, and this page already knew better
   about it somewhere else -- `renderScratch` says it in as many words:
   installed to the home screen there is no browser chrome, so anything opened
   in place has no back button and no way out of it short of killing the app. A
   plain `<a download href="/download/lesson">` is exactly that. iOS honours
   `download` in a Safari tab and ignores it in a standalone web app, where the
   tap is a NAVIGATION: the web view leaves the board, renders the PDF with no
   chrome around it, and there is nothing on the screen that goes back. The
   share sheet the `Content-Disposition` was supposed to raise never appears,
   which is the "I can't put it anywhere" half.

   So the document is never navigated to. It is FETCHED, and handed to the
   system as a file:

     - `navigator.share` with a `File` raises the native share sheet OVER the
       board. Files, iCloud Drive, a phone by AirDrop, an email to a professor
       -- and Cancel returns to the lesson, because the lesson never went
       anywhere. That is both halves answered by one mechanism, which is why it
       is the first choice rather than a nicety.
     - Where sharing a file is not available, a blob URL with `download` on it,
       which is the desktop answer and saves without navigating either.
     - And only if neither will do, a NEW context -- never this one. In a
       standalone app that hands the PDF to Safari, which has chrome, a share
       button and a way back to the board. A dead end in another app is
       recoverable; a dead end in this one costs the lesson.

   `AbortError` is somebody tapping Cancel and is not a failure. Anything else
   says what went wrong, in the banner, where the export already reports.

   AND READING IT IS A DIFFERENT QUESTION, which is the second report and the
   reason this section is no longer only about downloads: "it compiles the
   homework, but it's not letting me view the compiled .pdf or save it anywhere
   locally on the iPad." A share sheet is somewhere to PUT a document. It is not
   somewhere to read one, and "did the proof make it in" was not answerable from
   the board at all. `openPaper` is that half -- the pages, drawn to PNG by the
   machine that holds the PDF, shown in a panel this page owns and can close.
   Not an `<iframe>`: iOS renders a PDF in a frame as one unscrollable page.

   THREE THINGS DECIDE THE CONTROLS, AND ONLY ONE OF THEM IS AN EVENT.

     - `papers`, off the payload, says which documents exist. A file, checked on
       disk on every payload. This is what the buttons are enabled from.
     - the banner's record says which document the banner is ABOUT.
     - the ⋯ menu's `documents` panel needs neither, and is why a document is
       reachable ten days after it was made rather than for the one second the
       banner that announced it stayed on screen.
   ====================================================================== */

/* Which documents exist right now, keyed by kind -- `lesson`, `homework`. Off
   the payload (`papers`), so it survives every repaint and every reload. */
var papers = {};

/* One fetched document per kind, kept against the moment the PDF was written so
   a rebuild is never served from here.

   WARMED THE MOMENT IT IS OFFERED, and this is the difference between the share
   sheet appearing and an error. Safari's transient activation does not survive
   an `await`: a `navigator.share` called after a fetch has resolved is a share
   called without a user gesture, and it is refused. The document has to be in
   hand BEFORE the tap, so it is fetched when the button appears -- which is also
   when the person can first see it, so the wait is spent where nobody is looking
   at it rather than after they have pressed. */
var warm = Object.create(null);

function paperUrl(kind) { return "/download/" + kind; }

function paperTitle(kind) {
  return kind === "homework" ? "the written-up homework" : "this lesson";
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
/* `btn` is whichever control was tapped -- the banner's, the documents panel's,
   or the one in the viewer's own bar. All three do the same thing to the same
   document, and none of them may navigate this window. */
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
  if (els.paper && !els.paper.hidden) {
    paperSay("<strong>That did not work</strong>" + escapeHtml(text));
    return;
  }
  els.pushed.hidden = false;
  els.pushed.className = "pushed bad";
  els.pushedIcon.textContent = "✕";
  els.pushedText.textContent = text;
}

/* THE SHARE SHEET FIRST, AND NOTHING THAT NAVIGATES EVER.

   `navigator.share` with a `File` raises the native sheet OVER the board:
   Files, iCloud Drive, a phone by AirDrop, an email to a professor -- and
   Cancel returns to the lesson, because the lesson never went anywhere. That
   is both halves of what was reported answered by one mechanism, which is why
   it is the first choice and not a nicety. */
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

/* No share sheet here, and still nothing that navigates THIS window.

   A blob URL with `download` on it saves without leaving the page, which is the
   whole point -- but iOS ignores `download` in a standalone app and treats the
   tap as a navigation, which is exactly the trap being fixed. So in the
   installed app the last resort is a NEW context: that hands the PDF to Safari,
   which has chrome, a share button and a way back. A dead end in another app is
   recoverable; a dead end in this one costs the lesson. */
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

/* ------------------------------------------------- the documents, at any time */
/* The three export buttons MAKE a document. This is how you get back to one,
   and it is the answer to the half of the report that no amount of fixing the
   banner would have covered: a document made ten days ago is still a document,
   and until this existed there was no control on the page that could reach it.
   It also offers to make the one that is not there, so the panel is never a
   dead end. */
function openPapers() {
  els.papersPanel.hidden = false;
  renderPapers();
  /* Fetched now, for the same reason the banner fetches when its button
     appears: Safari will not raise the share sheet for a `navigator.share`
     called after a fetch resolves, because by then the tap's activation is
     gone. Opening this panel is somebody about to save one of two documents,
     which is the right moment to spend the wait. */
  ["lesson", "homework"].forEach(function (kind) { warmPaper(kind); });
}

function renderPapers() {
  if (els.papersPanel.hidden) return;
  els.papersList.innerHTML = "";
  ["lesson", "homework"].forEach(function (kind) {
    var have = papers[kind];
    var row = document.createElement("div");
    row.className = "paper-row";
    var head = document.createElement("strong");
    /* Which lesson document this is, because there are two and they are not the
       same document: the photograph of the glass, and the whole course typeset.
       Both are written under one numbered series in `transcripts/`, so the
       filename alone does not say which was made last. */
    head.textContent = kind === "homework" ? "The written-up homework"
      : have && have.scope === "all" ? "The whole course, typeset"
      : "This lesson";
    row.appendChild(head);

    var sub = document.createElement("span");
    sub.className = "name";
    if (have) {
      sub.textContent = [have.name, have.iso, kb(have.size)]
        .filter(Boolean).join(" · ");
    } else {
      sub.textContent = kind === "homework"
        ? "not compiled yet — the write-up has no PDF on disk"
        : "not exported yet — nothing has been made of this lesson";
    }
    row.appendChild(sub);

    var acts = document.createElement("div");
    acts.className = "paper-acts";
    if (have) {
      acts.appendChild(act("read it here", "pushed-get quiet", function () {
        els.papersPanel.hidden = true;
        openPaper(kind);
      }));
      acts.appendChild(act("save a copy", "pushed-get", function (e) {
        saveCopy(kind, e.currentTarget);
      }));
    } else {
      acts.appendChild(act(kind === "homework" ? "compile it now"
                                              : "export it now",
                           "pushed-get", function () {
        els.papersPanel.hidden = true;
        if (kind === "homework") doExportHomework();
        else doExport("lesson");
      }));
    }
    row.appendChild(acts);
    els.papersList.appendChild(row);
  });
}

function act(label, cls, fn) {
  var b = document.createElement("button");
  b.type = "button";
  b.className = cls;
  b.textContent = label;
  b.addEventListener("click", fn);
  return b;
}

function kb(bytes) {
  if (!bytes) return "";
  return bytes >= 1048576 ? (bytes / 1048576).toFixed(1) + " MB"
                          : Math.max(1, Math.round(bytes / 1024)) + " KB";
}

/* ------------------------------------------------------ reading it, in place */
/* The pages come back as pictures from `/view/<kind>`, drawn by the machine
   that holds the PDF. Everything about why it is pictures rather than the PDF
   itself is in `tutorboard/course/paper.py`; the short of it is that iOS gives
   a PDF in a frame one unscrollable page, and a PDF navigated to in a
   standalone app is a lesson with no way back to it. */
var paperOpen = null;

/* A DOCUMENT THIS COURSE POINTS AT, rather than one it built. `openPaper` takes
   `doc/<id>` as its kind and everything below works unchanged, because the
   route, the rasteriser, the cache and the page URLs are the same ones -- what
   differs is only how the file was found. A deck has no build record, so there
   is no `save a copy` for it and the button hides itself. */
function openDoc(id, name, then) { openPaper("doc/" + id, name, then); }

/* `then` is handed what `/view` answered, once the pages are on screen. An
   address naming one page of a document cannot scroll to it until the pictures
   exist, and there is nothing else on this page that knows when that is. */
function openPaper(kind, label, then) {
  if (!kind) return;
  paperOpen = kind;
  els.paper.hidden = false;
  document.body.classList.add("papering");
  var have = papers[kind];
  els.paperName.textContent = (have && have.name) || label || paperTitle(kind);
  els.paperSub.textContent = "";
  els.paperGet.hidden = !have;
  els.paperGet.textContent = "save a copy";
  els.paperGet.disabled = false;
  if (have) warmPaper(kind);          /* in hand before the tap; see openPapers */
  paperSay("<strong>Drawing the pages…</strong>"
           + "A long document takes a few seconds the first time. "
           + "After that it opens straight away.");
  els.paperPages.scrollTop = 0;

  fetch("/view/" + kind, { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (got) {
      if (paperOpen !== kind) return;          /* closed, or another opened */
      if (!got || !got.ok) {
        paperFailed(kind, got || {});
        if (then) then(null);
        return;
      }
      els.paperName.textContent = got.name || label || paperTitle(kind);
      els.paperSub.textContent = got.n + (got.n === 1 ? " page" : " pages")
        + (got.truncated ? " (the first " + got.n + " only)" : "");
      els.paperPages.innerHTML = "";
      got.pages.forEach(function (url, i) {
        /* EACH PAGE IN ITS OWN BOX, because the box is what the ink is
           anchored to. A page is a picture whose size on the glass depends on
           the width of the panel and the zoom -- so ink stored in page pixels
           would be somewhere else the moment the iPad rotates. Stored in
           fractions of this box, it is in the same place on the page for ever,
           which is the trick `annotate.js` already plays one level in, on
           cards.

           The key is the tail of a §2.1 address, `doc/<ident>/p<n>`, so a mark
           sent to the tutor names a place the tutor can open. */
        var box = document.createElement("div");
        box.className = "paper-page";
        var ident = kind.indexOf("doc/") === 0 ? kind.slice(4) : kind;
        box.dataset.ann = "doc/" + ident + "/p" + (i + 1);

        var img = document.createElement("img");
        img.src = url;
        /* Lazily, because a hundred-page transcript is a hundred pictures and
           the person is reading page one. */
        img.loading = i < 2 ? "eager" : "lazy";
        img.decoding = "async";
        img.alt = "page " + (i + 1);
        box.appendChild(img);
        els.paperPages.appendChild(box);
        /* A picture arrives with no height until it has decoded, and a layer
           sized against a zero-height box covers nothing. `annotate.js` already
           re-sizes on its own when a card grows; this is the same event, said
           explicitly because an image is the one thing that grows all at once
           long after it was inserted. */
        if (window.Annotate) {
          window.Annotate.attach(box);
          img.addEventListener("load", function () {
            window.Annotate.redrawAll();
          });
        }
      });
      /* Marks made on this document before, put back. Same call the lesson
         makes; the store is keyed by a string and does not care which kind of
         thing the string names. */
      if (window.Annotate && lastLive) {
        window.Annotate.load(lastLive.notes);
        window.Annotate.loadSent(lastLive.notes_sent);
      }
      /* Marks restored means there may be something to keep, and the offer is
         drawn off the store rather than off this session's strokes -- ink put on
         this document a week ago is still ink on this document. */
      paintKeep();
      /* The address bar now names this document, so a link to it can be copied
         off the glass. */
      mapRemember();
      if (then) then(got);
    })
    .catch(function () {
      if (paperOpen !== kind) return;
      paperFailed(kind, { detail: "the board did not answer" });
      if (then) then(null);
    });
}

/* A document that cannot be drawn here is still a document. Say why in a
   sentence, and offer the two things that do work: keep it, or hand it to
   Safari, which has its own PDF reader and a way back. */
function paperFailed(kind, got) {
  var lead = got.why === "none"
    ? (kind.indexOf("doc/") === 0 ? "That document is no longer where it was."
       : kind === "homework" ? "The write-up has not been compiled yet."
                             : "This lesson has not been exported yet.")
    : got.why === "no-renderer"
      ? "This machine cannot draw the pages."
      : "The pages could not be drawn.";
  var why = got.detail || "";
  paperSay("<strong>" + escapeHtml(lead) + "</strong>"
           + (got.why === "none" || got.why === "no-renderer"
              ? escapeHtml(why)
              /* A renderer's own output is a log, and a log reads as one. */
              : '<span class="detail">' + escapeHtml(why) + "</span>"));
  var box = els.paperPages.querySelector(".paper-say");
  if (got.why === "none") {
    box.appendChild(act(kind === "homework" ? "compile it now" : "export it now",
                        "pushed-get", function () {
      closePaper();
      if (kind === "homework") doExportHomework();
      else doExport("lesson");
    }));
    return;
  }
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

function paperSay(html) {
  els.paperPages.innerHTML = '<div class="paper-say">' + html + "</div>";
}

function closePaper() {
  /* The pen goes with the panel. Leaving annotate mode on when the document
     closes drops somebody back into the lesson with the pen out and the
     toolbar up, which is a mode they did not ask for and did not turn on. */
  if (window.Annotate && window.Annotate.isOn()) {
    setAnnotating(false);
  }
  paperOpen = null;
  closeKeep();
  if (els.paperKeep) els.paperKeep.hidden = true;
  els.paper.hidden = true;
  document.body.classList.remove("papering");
  mapRemember();               /* and the address stops naming the document */
  /* The pictures go with it. A hundred decoded pages held behind a closed
     panel is memory the iPad wants for the lesson. */
  els.paperPages.innerHTML = "";
}

/* The whole conversation as one document.

   Asked for from the device: something to show a professor. A print of the
   board is a screenshot of a scroll; this is the lesson typeset -- the tutor's
   cards and the pages that were handed in, in the order they happened -- kept
   in the repository under a numbered name, because "which one is the latest"
   should not mean reading a timestamp. */
/* The written-up work, compiled and kept -- and then handed over.

   `board hw build` is the compile, unchanged: the same one the tutor runs and
   the same one a push runs before it commits a stale PDF, so there is one
   compiler and one record of what LaTeX said. This only presses the button, and
   then offers the result the same way the lesson export does.

   `kind: "hw"` is what tells the banner which of the two documents it is
   looking at, and therefore which download to offer. */
function doExportHomework() {
  els.pushed.hidden = false;
  els.pushed.className = "pushed";
  els.pushedIcon.textContent = "…";
  els.pushedText.textContent = "compiling the write-up — LaTeX takes a moment…";
  offerDocument(null);
  return fetch("/hw/build", {
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

/* THIS LESSON, AS IT WAS READ. AND THE WHOLE COURSE, TYPESET.

   Two documents, and the difference is not a preference. Asked for from the
   iPad: "for the tutor session export, I don't want the latex dump it currently
   gives; I want it as if it were a screenshot of the entire iPad screen scrolled
   down over the whole tutoring session."

   So `lesson` is now the board's own pixels, photographed here, by the thing
   that drew them -- `shot.js` explains why it cannot be anywhere else. `all`
   stays the typeset transcript, and that is not laziness either: a past sitting
   is not on the glass, so there is nothing on this device to photograph. The
   server owns the name, the version, the repository copy and the git staging in
   both cases, which is what keeps one numbered series in `transcripts/` rather
   than two.

   Photographing an evening's lesson is real work on a tablet -- a card at a
   time, each one laid out, rasterised and drawn -- so it says which card it is
   on. A progress count is not decoration here: this is the one button on the
   page that can take twenty seconds, and a button that goes quiet for twenty
   seconds is a button somebody presses again. */
function doExport(scope, which) {
  els.pushed.hidden = false;
  els.pushed.className = "pushed";
  els.pushedIcon.textContent = "…";
  offerDocument(null);           /* not the last document's buttons, while this builds */

  /* THE PHOTOGRAPH IS OF WHAT IS ON THE GLASS, so it is only ever the lesson
     that is open. A chapter or a filed sitting is not on the glass; asking the
     camera for one would photograph this evening and label it last Tuesday. */
  if ((!scope || scope === "lesson") && global_TutorShot()) {
    els.pushedText.textContent = "photographing the lesson…";
    return global_TutorShot().send(function (done, total) {
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

  els.pushedText.textContent = scope === "all"
    ? "building the whole course — LaTeX takes a moment…"
    : scope === "chapter"
      ? "building this chapter — every sitting on it, in order…"
      : scope === "sitting"
        ? "building that sitting as a PDF…"
        : "building this lesson as a PDF…";
  return fetch("/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scope: scope || "lesson", which: which || "" })
  }).then(function (r) { return r.json(); })
    .then(function (rec) { paintBanner(null, rec, null); })
    .catch(function () {
      els.pushed.className = "pushed bad";
      els.pushedIcon.textContent = "✕";
      els.pushedText.textContent = "Export failed — could not reach the board";
    });
}

/* Asked for rather than captured at load: `shot.js` is a separate file and a
   deferred script, so a board that got here from a cache without it must fall
   back to the typeset export rather than throw. */
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
  return fetch("/push", {
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
  fetch("/dismiss-finish", { method: "POST" }).catch(function () {});
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
  var node = newestCardNode();
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
  else window.scrollTo(0, top);
}

/* A CARD IS TYPED OUT, AND NOTHING MOVES WHILE IT IS.

   Asked for in these words: "let's instead have it get typed out character by
   character at a nice quick pace that outpaces reading but not outpacing my
   eyes seeing it getting written". A card is a file and it arrives whole, so
   there is nothing to stream; this is a reveal of something already in hand,
   which is the honest version of the effect and the only one that cannot show a
   half-parsed formula.

   WHAT MAKES IT SMOOTH IS THAT THE CARD IS ITS FINAL SIZE FROM THE FIRST FRAME.
   The version before this hid each block outright, so the card was one paragraph
   tall when it landed and grew by a paragraph at a time -- and everything below
   it, the writing surface included, was shoved down on every step. Reported from
   the device: "the next board just shows up right underneath the board I was
   writing on, and then a jarring change occurs and suddenly all of the tutor
   response between the two shows up". That is the card growing, seen from
   behind the glass.

   So nothing is ever removed from the layout. Every character of the card is
   laid out the moment it arrives; what changes is only whether a character is
   PAINTED. A run of text is split into the part already said and the part not
   said yet, the second carrying `visibility: hidden` -- which occupies its space
   exactly, to the pixel, and wraps exactly where it will wrap. Moving one
   character from one to the other cannot reflow anything, in the card or under
   it. The clip-path wipe it replaces could not do this: a clip is a rectangle,
   and text does not arrive in rectangles.

   MATHEMATICS, CODE AND FIGURES ARE ATOMS. Splitting the characters of a KaTeX
   subtree destroys it, and a formula half-typed is nonsense to read anyway. Each
   one is hidden whole and appears whole when the cursor reaches it, costing
   TYPE_ATOM characters of time so it lands in its place in the sentence rather
   than out of nowhere. This runs after the typesetting pass, never before:
   KaTeX cannot measure what is not laid out.

   NOTHING CANCELS IT. A hand on the page used to dump the remainder instantly,
   which on a tablet is every reader every time -- a touch to scroll is a touch.
   The cap on the whole card is the protection instead: a long card is typed
   faster, never skipped.

   It runs whether or not the card is on the glass. Typing below the fold costs
   nothing, changes no height above the reader, and is over by the time somebody
   scrolls down to it. */
var TYPE_CPS = 110;        /* characters a second: past reading speed, still a hand */
var TYPE_MIN = 420;        /* even one line is typed, not placed */
var TYPE_ALL = 4200;       /* and the longest card there can be is over in four seconds */
var TYPE_ATOM = 10;        /* what a formula or a figure costs, in characters */

/* What is never cut into characters. A KaTeX subtree is one object; so is a
   table, a compiled diagram, a picture and a block of code, where the alignment
   is the meaning. */
var TYPE_ATOMIC = ".katex, .katex-display, pre, table, svg, img, figure";

/* Whether anything is being typed at this moment. The writing surface and the
   receipt above it both read it: see `replyArriving`.

   A COUNT AND A DEADLINE, BECAUSE A HELD SURFACE THAT NEVER COMES BACK IS WORSE
   THAN NO HOLD AT ALL. `requestAnimationFrame` does not run in a backgrounded
   tab, so a card that arrives while the app is in the background stops
   mid-sentence -- and a counter alone would keep the writing surface parked
   until somebody came back and watched it finish.

   THE DEADLINE IS A WATCHDOG AND NOT A BUDGET, which is the whole of the
   difference: it measures SILENCE rather than elapsed time. A budget cannot be
   set, because the card that runs longer in wall-clock than its own animation
   asked for is precisely the longest one -- KaTeX measuring, a figure decoding,
   and a tablet's main thread putting real milliseconds between frames -- so any
   budget lets go in the middle of the card it is most needed for. Every frame
   that lands pushes the deadline out again instead: a card making progress holds
   for however long it takes, and a tab that has stopped animating lets go
   `TYPE_STALL` after its last frame. */
var typingNow = 0;
var typingUntil = 0;
var TYPE_STALL = 2500;     /* silence, not elapsed time, is what releases a hold */
/* And how long a card that is NOT animated holds the surface anyway. Short
   enough that nobody waits, long enough that the answer and the next board are
   two events rather than one. See the `!ms` branch of `typeOut`. */
var TYPE_SETTLE = 250;
var settleTimer = null;

/* AND A HOLD NEVER SURVIVES INTO THE NEXT PAYLOAD.

   The settle is held against ONE arriving card. A payload drawn while it is
   still running is a newer picture of the lesson, and holding the surface out of
   place against a card that has already been superseded is a hold that has
   outlived its reason -- which is how a surface ends up parked somewhere nobody
   asked for and stays there. So `render` drops it on the way in.

   `again` is false from there, because the render that is dropping it is about
   to place the surface itself; calling back into `render` would be a loop. */
function settleEnd(again) {
  if (!settleTimer) return;
  clearTimeout(settleTimer);
  settleTimer = null;
  if (typingNow > 0) typingNow--;
  if (again && !typingNow && lastLive) render(lastLive);
}

function typingCards() { return typingNow > 0 && Date.now() < typingUntil; }

/* One hold on the page, taken and given back in pairs. */
function holdTyping() {
  typingNow++;
  keepTyping();
}

/* Still going. Called on every frame the animation actually gets. */
function keepTyping() {
  var now = Date.now();
  /* AND THE WATCHDOG HAD ALREADY LET GO, which is the one thing here that
     nobody can report and nobody can see. A frame arriving AFTER the deadline
     means the main thread was away for longer than `TYPE_STALL`, so the hold
     was released while this card was still half painted -- the surface came
     down, the next board arrived, and the rest of the card appeared in one go
     when the thread came back. That is the reported glitch exactly, and it is
     indistinguishable from every other cause without this line. */
  if (typingNow > 0 && typingUntil && now > typingUntil) {
    trace("stall", { late: now - typingUntil, held: typingNow });
  }
  typingUntil = now + TYPE_STALL;
}

function releaseTyping() {
  if (typingNow > 0) typingNow--;
  /* And now the writing surface may come down under it, and the receipt above
     it may stop talking. `placeWriter` and `paintSent` held for exactly this
     long; one more render is what moves them. */
  if (!typingNow && lastLive) render(lastLive);
}

/* THE ONE QUESTION BOTH SURFACES ASK: HAS THE REPLY ACTUALLY LANDED.

   A reply has landed when its node is in the document, its mathematics is
   typeset and the type-out has finished -- not when its RECORD arrived in a
   payload. Two surfaces answer that question and they used to answer it
   differently. The writing surface asked `typingCards()` and held. The busy
   receipt asked whether a CARD EXISTED, and let go the instant one did.

   So the pulse stopped, the next board came down, and the answer filled in
   afterwards. Reported from the iPad: "the response appeared how I wanted it to,
   but before it did, the second board showed up right underneath the last
   board, and I was left hanging." The specification is in the same words: no
   next board until the whole response is rendered, and the pulse visible at all
   times until it is.

   A picture inside the card needs no second mechanism: `img` is in
   `TYPE_ATOMIC`, so a figure's box is laid out and its contents are invisible
   until its own characters come due, which gives it the whole animation to
   decode in. */
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

  /* Somebody who has asked for less movement gets the card, whole, now. The
     pacing is a flourish and they have said they do not want flourishes. */
  var still = false;
  try {
    still = !!(window.matchMedia
               && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  } catch (e) { /* no matchMedia: type it */ }

  var ms = still ? 0
    : Math.max(TYPE_MIN, Math.min(TYPE_ALL, Math.round(total / TYPE_CPS * 1000)));
  var rate = total / Math.max(1, ms);          /* characters per millisecond */
  var t0 = null, at = 0;

  var done = function () {
    units.forEach(typeUndress);
    try { body.normalize(); } catch (e) { /* not fatal */ }
    body.classList.remove("typing");
  };

  /* THE HOLD IS NOT THE ANIMATION, AND CONFLATING THEM COST THE WHOLE FEATURE.

     This used to say "nothing typed is nothing held, and it happens now", and
     return without taking a hold at all. Somebody who asks for less movement
     gets the card whole and immediately -- that part is right, and the pacing is
     a flourish. What they must not ALSO get is the next board arriving on top of
     the answer, because that is not a flourish: it is the whole of "no next
     board showing up until the AI response has been COMPLETELY rendered".

     So with Reduce Motion on, the hold was never taken, `replyArriving()` was
     false on the one frame that matters, and the surface came down beside a card
     that had appeared in the same breath. Reported as the next board landing over
     the pulsing strip and "then the AI response just all showed up at once
     between the boards" -- and NO SUITE EVER SAW IT, because jsdom has no
     `matchMedia`, so every test in this repository runs with the animation on.

     `TYPE_SETTLE` is the hold, and it is not an animation: nothing moves during
     it and nothing is faded. It is the gap that makes "the answer, and then the
     board" legible instead of simultaneous, which is the thing that was asked
     for. Reduce Motion is about movement, not about latency, and a quarter of a
     second in which the page is perfectly still is neither. One animation frame
     was tried and is not enough -- it lands inside the same tick, so the two
     arrive together and the complaint stands. */
  if (!ms) {
    /* ONLY FOR A CARD THAT IS ANSWERING A SEND. A question arriving on a cold
       board is answering nothing and nobody is waiting on it, so holding its
       surface shut buys a beat of nothing; the hold is for the case the
       complaint was about, which is a reply landing on work just handed in. */
    /* ONE SETTLE PER FRAME, NOT PER CARD. A reply and the next question arrive
       in the same payload and both are fresh, so both come through here -- and
       with a hold each and one timer to release them, the second overwrote the
       first and left a hold nothing could ever give back. The surface then
       stayed where it was and the receipt went on saying `arriving` until the
       watchdog expired. The settle is a property of the frame the reply landed
       on, so `settleTimer` is both the timer and the flag. */
    if (replyLanding && !settleTimer) {
      holdTyping();
      settleTimer = setTimeout(function () { settleEnd(true); }, TYPE_SETTLE);
    }
    units.forEach(function (u) { typeShow(u, u.n); });
    done();
    trace("whole", { card: which, why: "reduced motion",
                     held: !!settleTimer });
    return;
  }

  holdTyping();
  body.classList.add("typing");
  var began = Date.now();
  trace("type", { card: which, ms: ms, units: units.length, chars: total });

  var finish = function () {
    done();
    /* How long it ACTUALLY took beside what it asked for. The two being far
       apart is a stalled main thread, which is the difference between a card
       that typed and a card that appeared. */
    trace("typed", { card: which, asked: ms, took: Date.now() - began });
    releaseTyping();
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
       taking its time from a tab that stopped animating. */
    keepTyping();
    var want = ms ? Math.min(total, Math.ceil((now - t0) * rate)) : total;
    while (at < units.length && units[at].start < want) {
      var u = units[at];
      var take = Math.min(u.n, want - u.start);
      typeShow(u, take);
      if (take >= u.n) at++;
      else break;
    }
    if (at < units.length) { window.requestAnimationFrame(step); return; }
    finish();
  };
  window.requestAnimationFrame(step);
}

/* ------------------------------------------------------- keeping the place --

   NOTHING THAT ARRIVES ABOVE THE READER MAY MOVE THE READER.

   Reported as: "intermittently, after I submit a response, it glitches and
   scrolls me up above the last board I wrote my response on." Nothing scrolled.
   The transcript grew ABOVE the writing surface and took the page down with it,
   which from behind the glass is indistinguishable from being scrolled up.

   Two things do that on a send. The answer becomes a turn, and it is rendered
   into the transcript in its proper place -- above the surface -- unless it
   happens to be the very last item, which it is only while the question being
   answered is also the last card the tutor has written. And the frozen picture
   of it is an `img` with a width and no height, so it occupies nothing at all
   until it has decoded and then suddenly occupies a screenful.

   Safari has no scroll anchoring, so this is it: note which node the reader is
   actually looking at and where on the glass it sits, and after the lesson has
   been rebuilt around it, put it back. Anchored by card or turn id rather than
   by render key, because a key carries a version and the node the reader is
   looking at is very often the one that was just rebuilt. */
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
     the reader rather than giving up.

     `revealSent` parks them at the FOOT of the writing surface, and the surface
     is the tail of the run and carries no card or turn id of its own -- so every
     keyed node is above the top of the glass and the walk above found nothing,
     and gave up. Reported from that exact position: "just submitted another board
     written response and got scrolled UP again to the middle of the last tutor
     response." The receipt for the answer is inserted with the QUESTION it
     answers, which an hour into an exercise is several cards up the page, so the
     surface went down the page with it and what filled the glass instead was the
     bottom of the card above.

     Not the surface itself, though it is the thing being looked at: when the
     tutor replies the surface MOVES, because the next board opens under the
     newest word, and an anchor by that name would follow it down the page. It
     does not need to be held. The place it occupied is taken by this question's
     own board, frozen with the same ink in the same box -- the rule every dormant
     board is built on -- so holding anything above it leaves the student's working
     exactly where it was, which is the whole of what a reply needs. */
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
  window.scrollBy(0, moved);
}

/* And the same again for one late-decoding picture, which arrives long after any
   render has finished. */
function holdBelow(node, before) {
  var r = node.getBoundingClientRect();
  var grew = r.height - before;
  if (grew > 1 && r.top < 0) window.scrollBy(0, grew);
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
    els.scratchList.innerHTML = '<p class="name">nothing dropped yet. '
      + 'What you write goes into the lesson itself.</p>';
    return;
  }

  function tile(url, label, bust) {
    var a = document.createElement("a");
    a.href = url;
    /* Never a new context. Installed to the home screen there is no browser
       chrome, so a raw image opened this way has no back button and no way out
       of it short of killing the app. Images open in a viewer this page owns
       and can close; anything else is left to the system. */
    var isImage = /\.(png|jpe?g|gif|webp|heic)(\?|$)/i.test(url);
    if (isImage) {
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
    tile(u.url, u.name);
  });
}

/* ------------------------------------------------------------ past lessons */
/* Reading an old lesson is reading the same transcript, so it goes through the
   same renderer. The live stream is what is suspended, not the page: whatever
   arrives while you are reading is still there when you come back. */
var reading = null;
var lastLive = null;

function openHistory() {
  var panel = document.getElementById("history");
  var list = document.getElementById("history-list");
  panel.hidden = false;
  list.innerHTML = '<p class="name">looking…</p>';
  fetch("/archive").then(function (r) { return r.json(); }).then(function (d) {
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

      /* TAKE IT AWAY, from the one place a person is already looking at the
         sitting they want. A filed lesson could only be got out of here by
         exporting the whole course, which is the wrong document by two orders
         of magnitude when what is wanted is one evening's work. `sitting` is a
         scope, not a second exporter -- the numbering, the reading order and
         the whole-conversation rule are the ones every other document gets. */
      var keep = document.createElement("button");
      keep.type = "button";
      keep.className = "session-keep pushed-get";
      keep.textContent = "PDF";
      keep.title = "this sitting as a document";
      keep.addEventListener("click", function (ev) {
        ev.stopPropagation();          /* not also "open it to read" */
        document.getElementById("history").hidden = true;
        doExport("sitting", s.id);
      });
      row.appendChild(keep);

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
  fetch("/archive/" + encodeURIComponent(id))
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
  viewer.querySelector("img").src = url;
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

function saveNotes(send) {
  if (!window.Annotate) return Promise.resolve([]);
  /* Sending re-sent every mark on the board, so a card marked up yesterday and
     already delivered came back to the tutor as a fresh turn every time
     anything else was sent. Send what has not been sent. */
  var ids = send ? window.Annotate.unsent() : window.Annotate.unsaved();
  if (!ids.length) return Promise.resolve([]);
  return Promise.all(ids.map(function (id) {
    var body = window.Annotate.payload(id, send);
    return fetch("/annotate/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function () {
      window.Annotate.clean(id);
      if (send) window.Annotate.sent(id);
    });
  }));
}

/* Not while a hand is on the glass.

   `payload` no longer encodes a picture, but it still serialises every mark on
   the card, and `JSON.stringify` of a well-annotated card is real main-thread
   time -- landing, by construction, about a second after a stroke, which is the
   middle of the next one. Same rule as the slate's own autosave: nothing about
   getting ink to disk has to happen in a particular second, and the strokes are
   still written the moment the hand stops. `pagehide` is the backstop. */
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
    saveNotes(false);
  }, 900);
}

if (window.Annotate) {
  window.Annotate.onChange(function () {
    queueNoteSave();
    paintAnnTools();
    paintNotesSend();
    /* The offer to keep this writing appears the moment there IS writing, and
       goes away when the last stroke is erased. Same signal the autosave uses. */
    paintKeep();
  });
  /* The clipboard is shared with both writing surfaces, so it fills up without
     anything on the lesson being touched: copying on the slate is what makes
     Paste worth offering on a card. */
  if (window.InkClip) window.InkClip.onChange(function () { paintAnnTools(); });
  /* A closing tab must not take the last stroke with it -- or the last sentence
     still being typed. */
  window.addEventListener("pagehide", function () { saveNotes(false); });
  window.addEventListener("pagehide", function () { flushTextDraft(); });
}

function setAnnotating(next) {
  if (!window.Annotate) return;
  window.Annotate.setOn(next);
  els.annbar.hidden = !next;
  els.annotate.setAttribute("aria-pressed", next ? "true" : "false");
  els.annotate.title = next ? "stop writing on the lesson"
                            : "write on the lesson itself";
  /* The same mode, reported on whichever control is actually reachable. A
     document is read full-screen over the chrome, so while one is open the pen
     on the paper bar is the only one of the two anybody can see. */
  if (els.paperInk) {
    els.paperInk.setAttribute("aria-pressed", next ? "true" : "false");
    els.paperInk.title = next ? "stop writing on this page"
                              : "write on this page";
  }
  paintAnnTools();
}

els.annotate.onclick = function () {
  setAnnotating(!window.Annotate.isOn());
};

/* The tools are only meaningful while the mode is on, and a control that looks
   available but does nothing is worse than one that is plainly disabled. */
function paintAnnTools() {
  if (!window.Annotate) return;
  var mode = window.Annotate.tool();
  els.annPen.classList.toggle("on", mode === "pen");
  els.annErase.classList.toggle("on", mode === "erase");
  els.annSelect.classList.toggle("on", mode === "lasso");
  els.annUndo.disabled = !window.Annotate.canUndo();
  els.annRedo.disabled = !window.Annotate.canRedo();
  els.annClear.disabled = !window.Annotate.marked().length;
  /* The clip controls exist while they can do something: with a loop drawn
     round something, or with ink on the clipboard and a card to put it on. A
     Paste that is offered with an empty clipboard is a button that answers
     "nothing copied yet", which is not an answer worth a tap. */
  var picked = window.Annotate.picked();
  var held = !!(window.InkClip && window.InkClip.has());
  els.annClip.hidden = !(picked || held);
  els.annCopy.disabled = !picked;
  els.annCut.disabled = !picked;
  els.annDel.disabled = !picked;
  els.annPaste.disabled = !held;
  Array.prototype.forEach.call(document.querySelectorAll(".ann-ink"), function (b) {
    b.style.background = b.dataset.ink;
    b.classList.toggle("on", b.dataset.ink === window.Annotate.colour());
  });
}

els.annPen.onclick = function () { window.Annotate.setTool("pen"); paintAnnTools(); };
els.annErase.onclick = function () { window.Annotate.setTool("erase"); paintAnnTools(); };
els.annSelect.onclick = function () { window.Annotate.setTool("lasso"); paintAnnTools(); };
/* A word in the bar that did the thing, because copying has no visible result
   and a control with no visible result reads as a broken one. */
var annSayTimer = null;

function annSay(text) {
  if (!els.annSay) return;
  els.annSay.textContent = text;
  els.annSay.hidden = !text;
  clearTimeout(annSayTimer);
  if (text) {
    annSayTimer = setTimeout(function () {
      els.annSay.hidden = true;
      els.annSay.textContent = "";
    }, 2800);
  }
}

/* Why nothing happened, when nothing happened: either there is no loop, or the
   loop holds more ink than the clipboard will carry. A control that answers
   neither reads as a broken one. */
function annWhyNot() {
  return window.Annotate.picked() ? "that is more ink than the clipboard will carry"
                                  : "loop round something first";
}

els.annCopy.onclick = function () {
  var n = window.Annotate.copy();
  annSay(n ? n + " copied — paste it on a card or on your own board" : annWhyNot());
  paintAnnTools();
};
els.annCut.onclick = function () {
  var n = window.Annotate.cut();
  annSay(n ? n + " cut" : annWhyNot());
  paintAnnTools();
};
els.annPaste.onclick = function () {
  var n = window.Annotate.paste();
  annSay(n ? n + " pasted — drag it where you want it" : "nothing copied yet");
  paintAnnTools();
};
els.annDel.onclick = function () { window.Annotate.erase(); paintAnnTools(); };
els.annUndo.onclick = function () { window.Annotate.undo(); paintAnnTools(); };
els.annRedo.onclick = function () { window.Annotate.redo(); paintAnnTools(); };
els.annClear.onclick = function () { window.Annotate.clearCurrent(); paintAnnTools(); };
els.annDone.onclick = function () { setAnnotating(false); };
Array.prototype.forEach.call(document.querySelectorAll(".ann-ink"), function (b) {
  b.onclick = function () {
    window.Annotate.setPen(b.dataset.ink);
    window.Annotate.setTool("pen");
    paintAnnTools();
  };
});

/* ------------------------------------------------------------ send chooser */
/* Only asked when there is genuinely a choice: working on the slate AND marks
   on the lesson. One of the two alone just sends. */

function haveNotes() {
  return !!(window.Annotate && window.Annotate.unsent().length);
}

/* What Send does, and what it must never do.

   It used to ask first: with marks anywhere on the board, tapping Send on the
   writing surface issued no request at all and raised a "Send what?" bar
   instead, and the answer only went out on a second tap. That is a Send button
   that does nothing, and it cost a real answer -- an evening's working sat in
   live/slate/ for two days while the student believed they had handed it in,
   and the board's own receipt never appeared because the code that writes it
   was never reached. Nothing on the surface said a decision was outstanding.

   So the working goes first, unconditionally. The button sits on the surface
   holding the working; that is what it means. Marks on the lesson are then
   offered as a follow-up, which cannot lose anything, because by then the
   working is already gone.

   The one exception is an empty surface: with nothing written and marks that
   have not been sent, the marks ARE the answer, and handing the tutor a blank
   sheet alongside them is noise. */
function askWhatToSend(sendWork) {
  var marks = haveNotes();
  var written = !writer || writer.strokes() > 0;
  if (!written && marks) {
    saveNotes(true).then(function () { paintNotesSend(); toastSent(); });
    return;
  }
  sendWork();
  if (marks && !notesOff()) els.sendwhat.hidden = false;
}

/* Whether the student has said "no, and don't ask again". Persisted, so it
   survives the app being put down, and re-armed from the ⋯ menu when they change
   their mind and want to hand the marks over after all. */
var NOTES_OFF = "notes-off";

function notesOff() {
  try { return localStorage.getItem(NOTES_OFF) === "1"; } catch (e) { return false; }
}

function setNotesOff(v) {
  try {
    if (v) localStorage.setItem(NOTES_OFF, "1");
    else localStorage.removeItem(NOTES_OFF);
  } catch (e) {}
  paintNotesSend();
}

function closeChooser() {
  els.sendwhat.hidden = true;
}

els.sendNotes.onclick = function () {
  closeChooser();
  saveNotes(true).then(function () { paintNotesSend(); toastSent(); });
};
els.sendCancel.onclick = closeChooser;
els.sendNoAsk.onclick = function () {
  closeChooser();
  setNotesOff(true);
};

if (els.notesAgain) {
  els.notesAgain.onclick = function () {
    setNotesOff(false);
    paintNotesSend();
  };
}

els.notesend.onclick = function () {
  els.notesend.disabled = true;
  /* Same rule as the board's Send: say something on the frame the button was
     pressed. This one encodes a picture of the marks and then waits on a request
     per marked card. */
  saySending();
  saveNotes(true).then(function () {
    els.notesend.disabled = false;
    paintNotesSend();
    toastSent();
  }, function () { els.notesend.disabled = false; });
};

window.askWhatToSend = askWhatToSend;


/* Marks can be made at any time -- on a card from ten minutes ago, with no
   question owed and therefore no writing surface and no Send button anywhere on
   the page. Without this they would sit there unsendable, which is the same dead
   end the cold start had. */
function paintNotesSend() {
  var any = haveNotes();
  var owedSurface = !els.writer.hidden;
  els.notesend.hidden = !(any && !owedSurface && !notesOff());
  /* The re-arm control is only meaningful while the offer is actually off, and
     only if there are marks to hand over. */
  if (els.notesAgain) {
    els.notesAgain.hidden = !(notesOff() && any);
  }
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
  els.save.textContent = has ? "⤓ save " + unsaved : "⤓ save";
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
  saveNotes(false);
  window.location.href = to;
}

els.home.addEventListener("click", function (e) {
  e.preventDefault();
  askBeforeLeaving(els.home.getAttribute("href") || "/");
});

els.finishLeave.onclick = goLeave;


/* ------------------------------------------------------- lecture or homework */
/* Which kind of sitting this is was a terminal-only decision, so a student who
   wanted help with a problem set had to find a keyboard to say so. The badge in
   the title bar already names the kind; making it the control is the whole
   change. The sets offered are the ones the repository actually has -- nothing
   is typed, so nothing invented can reach the filesystem. */
var knownSets = [];
var sittingKind = "lecture";

function paintKindChooser() {
  els.kindLecture.classList.toggle("on", sittingKind === "lecture");
  els.kindReview.classList.toggle("on", sittingKind === "review");
  els.kindWalk.classList.toggle("on", sittingKind === "walk");
  /* Offered only where there is something to review. A repository with no
     chapters and no parts would open a picker with nothing in it. */
  els.kindReview.hidden = !(reviewInfo && (reviewInfo.units || []).length);
  /* And only where there is source to walk through. A narrative repository --
     all prose, no machinery -- has nothing to trace. */
  els.kindWalk.hidden = !(walkInfo && (walkInfo.units || []).length);
  /* WHO WRITES THE CODE, for this sitting. Not offered in the two sittings that
     read rather than write: a review asks questions and a walkthrough traces
     code that is already there, so neither has a stance to take and offering
     one would suggest they did. */
  paintStance();
  /* AND WHAT THE SITTING IS FOR, which is the other question and the one that
     could not be answered at all once a sitting was open. */
  paintAim();
  /* AND WHO WRITES IT, which is a third question and is answered for the
     sitting being OPENED rather than the one that is. */
  paintWho();
  els.kindSets.innerHTML = "";
  if (!knownSets.length) {
    var none = document.createElement("span");
    none.className = "muted";
    none.textContent = "no problem sets in this course";
    els.kindSets.appendChild(none);
    return;
  }
  knownSets.forEach(function (name) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = name;
    if (sittingKind === "homework" && currentSet === name) b.classList.add("on");
    b.onclick = function () { setSitting("homework", name); };
    els.kindSets.appendChild(b);
  });
}

var currentSet = null;

function setSitting(kind, name, chapter) {
  els.kind.hidden = true;
  fetch("/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session: kind, hw: name || null, chapter: chapter || null,
      /* Sent every time, including as null. A stance belongs to the sitting
         being opened, so opening one without choosing a stance is how the
         repository's own answer comes back -- and it has to be said rather than
         omitted, or the last sitting's choice would outlive it. */
      stance: takeStance(),
      /* And the same for the assistant, for the same reason and with the same
         shape: chosen for the sitting being opened, cleared by opening one that
         does not name it. */
      agent: takeAgent()
    })
  }).catch(function () { /* the payload will say what actually happened */ });
}


/* ------------------------------------------------ who writes it, this sitting */
/* CHOSEN AS A SITTING OPENS, AND THAT IS THE DECISION RATHER THAN THE EASIER
   ROUTE. The aim beside it changes in place, because it changes what the next
   card is. An assistant changes WHO WRITES IT, and the conversation the
   outgoing one was holding does not transfer -- which on the local model is a
   15,900-token preamble re-paid at a few tokens a second, in hours. So this is
   held like a stance and travels with the next sitting.

   It is offered at all because none of the four layers that used to resolve it
   can be reached from a tablet: `--agent` on a command line, a line in the
   workspace's `tutorboard.json` that is a statement about it for ever, a
   hostname, and a machine default. */
var agentPick = null;       /* what they tapped, for the sitting about to open */
var assistants = null;      /* what this machine has; null means it could not say */
var colibriNow = null;      /* and what the local model's server is doing */

function takeAgent() {
  var chosen = agentPick;
  agentPick = null;
  return chosen;
}

function paintWho() {
  /* Nothing to choose between, or nobody could say what there is: no row. A
     chooser offering one name is furniture. */
  var have = (assistants && assistants.agents || []).filter(function (a) {
    return a.headless && !a.missing;
  });
  var reading = sittingKind === "review" || sittingKind === "walk";
  els.kindWho.hidden = reading || have.length < 2;
  if (els.kindWho.hidden) return;

  var now = agentPick || currentAgent || (assistants && assistants["default"]);
  var host = els.kindWhoWays;
  host.innerHTML = "";
  have.forEach(function (a) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = a.name;
    /* Its own reason for refusing, before the tap rather than after it: one
       sitting at a time, and cards that must not be committed. Both come off
       the recipe, so the button says whatever the table says. */
    b.title = a.exclusive ? ("one sitting at a time — " + a.exclusive) : a.cmd;
    if (a.name === now) {
      b.className = "on" + (a.exclusive ? " local" : "");
    }
    /* A local model with no server is still the right thing to tap -- the tap
       is what starts one -- so it is dimmed rather than disabled. */
    if (a.exclusive && colibriNow && colibriNow.state !== "warm") {
      b.classList.add("away");
    }
    b.onclick = function () {
      agentPick = a.name;
      paintWho();
    };
    host.appendChild(b);
  });

  /* AND WHAT THE LOCAL MODEL'S SERVER IS DOING, which is the half no button can
     express. Four states off `squeue`: nothing submitted, queued behind an
     allocation, loading 429 GB off the filer, warm. Only while it is the one
     picked -- a sentence about a Slurm job is noise over a hosted assistant. */
  var local = have.filter(function (a) { return a.exclusive; })[0];
  var picked = local && now === local.name;
  if (!picked || !colibriNow) {
    els.kindWhoNote.textContent = "";
    els.kindWhoUp.hidden = true;
    return;
  }
  els.kindWhoNote.textContent =
      colibriNow.state === "warm" ? "the server is " + colibriNow.detail
    : colibriNow.state === "queued" ? "the server is queued — " + colibriNow.detail
    : colibriNow.state === "loading" ? "the server is coming up — " + colibriNow.detail
    : colibriNow.detail + ". Starting one takes seven or eight minutes, and the "
      + "first turn is hours of prefill — start it before you stop for the day.";
  els.kindWhoUp.hidden = colibriNow.state !== "off";
}

/* The tap that starts it, and it returns at once: an allocation, a 429 GB load
   and a warm-up generation cannot be reported by the request that asked for
   them. The payload says what happened next. */
els.kindWhoUp.onclick = function () {
  els.kindWhoUp.hidden = true;
  els.kindWhoNote.textContent = "submitting the job\u2026";
  fetch("/colibri", { method: "POST" })
    .then(function (r) { return r.json(); })
    .then(function (got) {
      if (got && got.colibri) colibriNow = got.colibri;
      paintWho();
      /* ONE VOICE, AND IT IS THE STATE. The reply carries a receipt for the
         tap, and the state that comes back with it is strictly better -- a job
         number and Slurm's own reason beat "submitting". The receipt is kept
         only for the answer no state can express: this machine has not got
         `coli-up` at all. */
      if (got && got.started === false && got.detail && !colibriNow) {
        els.kindWhoNote.textContent = got.detail;
      }
    })
    .catch(function () { /* the payload will say what actually happened */ });
};

var currentAgent = null;    /* what the sitting says, if it says anything */

/* The pick, and then there is no pick. It belongs to the sitting being opened
   and must not survive it: leaving it set would make the next tap on `lecture`
   silently carry an override chosen an hour ago for something else. */
function takeStance() {
  var chosen = stancePick;
  stancePick = null;
  return chosen;
}

/* --------------------------------------------------------- who writes it */
/* A repository says once, in writing, whether the tutor is here to teach the
   work or to do it, and that is right for a course and wrong for a project: the
   grid-search plumbing around a bake-off and the one algorithm its owner needs
   to understand live in the same repository and want opposite answers. So the
   repository's word is the default and a SITTING may say otherwise -- chosen
   here, in the open, beside the kind of sitting it belongs to.

   It is never inferred and never sticky: `stancePick` is what the person tapped
   for the sitting they are about to open, and it goes back to null the moment
   one is open, because the next sitting starts from the repository again. */
var stancePick = null;
/* What the repository declares, from the payload. It was a hard-coded "teach"
   here, so the chooser showed the wrong thing in every repository whose standing
   answer is `do` -- and the busy strip could not tell a doing turn from a
   teaching one unless the sitting had overridden it. */
var declaredStance = "teach";

function paintStance() {
  var reading = sittingKind === "review" || sittingKind === "walk";
  els.kindStance.hidden = reading;
  if (reading) return;
  /* What is showing as chosen is what the sitting is actually running under:
     the tap if there has been one, otherwise what the board says is in force. */
  var now = stancePick || currentStance || declaredStance;
  els.stanceTeach.classList.toggle("on", now !== "do");
  els.stanceDo.classList.toggle("on", now === "do");
}

var currentStance = null;

/* ------------------------------------------ what this sitting is FOR */
/* THE ONE CONTROL THAT CHANGES A SITTING WITHOUT LOSING IT.

   Everything else on this panel opens a NEW sitting, which files the lesson
   away. The aim was chosen once, on the map, at the moment of opening -- so
   "wait, now teach me how this works", said three hours into building
   something, cost the evening it was said in. This is the way out of that: the
   aim of the sitting that is open, changed in place, with the transcript, the
   cards and the tutor all left exactly where they are.

   THE FIVE ARE THE FIVE `WORK` ALREADY NAMES, and the labels are the strings
   that table already carries -- one set of words for the map's sheet and for
   this, or the two drift. The two aims with a `needs` are left out on purpose:
   each is held over a scope, and choosing one is choosing what it is over,
   which is a tap on a box and a new sitting.

   THE TAP IS THE INSTRUCTION, so it is sent at once rather than held like a
   stance pick -- `/aim` writes it, puts it in the transcript and wakes a turn.
   See `_aim` in `routes/lesson.py`. */
var currentAim = null;            /* what the sitting says, if it says anything */
var aimNow = "";                  /* what it is running under, workspace or family */

function aimWays() {
  return WORK.filter(function (way) {
    return way.aim !== "show" && !way.needs;
  });
}

function paintAim() {
  /* Hidden in the two sittings that read rather than write, for the reason the
     stance chooser is: a review asks and a walkthrough traces, and neither is
     a sitting whose style is anybody's to change mid-way. */
  var reading = sittingKind === "review" || sittingKind === "walk";
  els.kindAim.hidden = reading;
  if (reading) return;
  var now = currentAim || aimNow || "";
  var host = els.kindAimWays;
  host.innerHTML = "";
  aimWays().forEach(function (way) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = way.label;
    b.title = way.sub;
    if (way.aim === now) b.className = "on" + (way.does ? " does" : "");
    b.onclick = function () { setAim(way.aim); };
    host.appendChild(b);
  });
}

/* One step, written for them, and the sitting stays a coaching one. Painted
   before the answer comes back for the reason `setAim` is: the payload that
   carries it is a poll away, and a control that does nothing for a second is a
   control somebody taps again. */
function handOver(card, button) {
  if (button) {
    button.disabled = true;
    button.textContent = "handed over";
  }
  fetch("/handover", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ card: card })
  }).catch(function () { /* the payload will say what actually happened */ });
}

function setAim(aim) {
  els.kind.hidden = true;
  /* Painted before the answer comes back, because the payload that carries it
     is a poll away and a control that does nothing for a second is a control
     somebody taps again. The next payload is the truth either way. */
  currentAim = aim;
  fetch("/aim", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ aim: aim })
  }).catch(function () { /* the payload will say what actually happened */ });
}

els.stanceTeach.onclick = function () {
  stancePick = "teach";
  paintStance();
};
els.stanceDo.onclick = function () {
  stancePick = "do";
  paintStance();
};

els.session.onclick = function () {
  paintKindChooser();
  els.kind.hidden = false;
};
els.kindLecture.onclick = function () { setSitting("lecture"); };
els.kindReview.onclick = function () { els.kind.hidden = true; openPicker("review"); };
els.kindWalk.onclick = function () { els.kind.hidden = true; openPicker("walk"); };
els.kindCancel.onclick = function () { els.kind.hidden = true; };


/* --------------------------------------------- a sitting held over a scope */
/* Two sittings ask before they start, because in both the student is the only
   one who knows the answer: a test review over chapters they are being examined
   on, and a walkthrough over machinery they do not understand. Neither can begin
   from a single tap the way a lecture does, and neither may take a name nobody
   chose -- everything offered is discovered from the repository itself, so
   nothing typed reaches the filesystem and nothing invented reaches the tutor's
   prompt.

   ONE panel serves both. They are the same decision in the same shape -- a list
   of what exists, ticked, and one request at the end of it -- and a second copy
   of this would be a second copy to keep in step. `pickerKind` says which, and
   the title, the noun and the button follow from it.

   The picks are held here rather than sent one at a time: a review over four
   chapters is one decision, and sending it four times would file the lesson away
   four times over. */
var reviewInfo = null;              /* what the payload says can be reviewed */
var walkInfo = null;                /* and what can be walked through */
var pickerKind = "review";          /* which of the two the panel is open for */
var reviewPick = [];                /* names ticked but not yet started */

function pickerInfo() {
  return pickerKind === "walk" ? walkInfo : reviewInfo;
}

function paintReview(state, info, walk) {
  reviewInfo = info || null;
  walkInfo = walk || null;
  var kind = state.session || "lecture";
  var walking = kind === "walk";
  var on = walking || kind === "review";
  /* What the sitting is running under, so the chooser opens showing the truth
     rather than showing the repository's answer over the top of an override. */
  currentStance = state.stance || null;
  declaredStance = state.declared_stance || "teach";
  /* What the sitting says, and what it is actually running under -- which are
     different whenever nobody chose, and the second is the workspace's or its
     family's answer. Resolved by the server (`config.aim_for`), never here: two
     places deciding a precedence is one of them being wrong. */
  currentAim = state.aim || null;
  aimNow = state.aim_now || "";
  /* And who this sitting asked for, which is the fifth layer of a resolution
     the other four of which no tablet can reach. */
  currentAgent = state.agent || null;
  var live = walking ? walkInfo : reviewInfo;
  var scope = (live && live.scope) || [];
  els.rvbar.hidden = !on;
  if (!on) return;
  els.rvLead.textContent = walking ? "walking through" : "test review";
  var by = {};
  ((live && live.units) || []).forEach(function (u) { by[u.name] = u; });
  els.rvScope.textContent = scope.length
    ? scope.map(function (n) { return (by[n] && by[n].label) || n; }).join(" · ")
    /* Reachable from a terminal, not from this page. Say what is missing rather
       than showing an empty strip that reads as "nothing to see". */
    : "nothing chosen yet — tap change";
}

function reviewNoun(info) {
  if (pickerKind === "walk") return "files";
  return (info && info.of) === "parts" ? "parts of the project" : "chapters";
}

function paintReviewPicker() {
  var host = els.reviewList;
  var info = pickerInfo();
  var walking = pickerKind === "walk";
  host.innerHTML = "";
  var units = (info && info.units) || [];
  els.reviewTitle.textContent = walking
    ? "Which file should the walkthrough cover?"
    : "Which " + reviewNoun(info) + " is the test over?";
  els.reviewStart.textContent = walking ? "start walkthrough" : "start review";
  els.reviewNote.textContent = walking
    ? "Nothing is written in a walkthrough — you trace it and the tutor asks. "
      + "Starting one files the lesson you are in; it stays readable under ◷."
    : "The questions are the tutor's; the scope is yours. "
      + "Starting one files the lesson you are in — it stays readable under ◷.";

  if (!units.length) {
    var p = document.createElement("p");
    p.className = "none";
    p.textContent = walking
      ? "There is no source in this repository to walk through."
      : "There is nothing here to review: this repository has no "
        + "chapters and no parts to ask over.";
    host.appendChild(p);
    els.reviewStart.disabled = true;
    els.reviewCount.textContent = "";
    return;
  }

  /* A walkthrough's list is files, and a repository has a hundred of them where
     it has eleven chapters. Reading a flat hundred is not a thing anybody does,
     so they are headed by the directory they are in -- which is how the person
     choosing already thinks of them -- and each row is then the bare filename. */
  var last = null;
  units.forEach(function (u) {
    if (walking && u.dir !== last) {
      last = u.dir;
      var head = document.createElement("div");
      head.className = "pick-dir";
      head.textContent = last === "." ? "(top level)" : last + "/";
      host.appendChild(head);
    }
    var b = document.createElement("button");
    b.type = "button";
    /* Its own name on it, so an address naming a file can find its row rather
       than counting from the top of a hundred. */
    b.dataset.unit = u.name;
    b.innerHTML = '<span class="tick">✓</span><span class="what"></span>';
    b.querySelector(".what").textContent = walking ? u.short : u.label;
    if (reviewPick.indexOf(u.name) >= 0) b.classList.add("on");
    b.onclick = function () {
      var at = reviewPick.indexOf(u.name);
      if (at >= 0) reviewPick.splice(at, 1); else reviewPick.push(u.name);
      paintReviewPicker();
    };
    host.appendChild(b);
  });

  els.reviewCount.textContent = reviewPick.length
    ? reviewPick.length + " of " + units.length + " chosen"
    : "nothing chosen yet";
  els.reviewAll.textContent = reviewPick.length === units.length
    ? "clear" : "select all";
  /* Select-all over a hundred files is not a walkthrough anybody wants and is
     one tap away from being an accident. It belongs to the review, where the
     list is a course's eleven chapters. */
  els.reviewAll.hidden = walking;
  /* A sitting over nothing is not a sitting, and starting one would file the
     lesson they are in away for no reason. */
  els.reviewStart.disabled = reviewPick.length === 0;
}

function openPicker(kind) {
  pickerKind = kind === "walk" ? "walk" : "review";
  /* Reopening starts from what the sitting already covers, so "change" is an
     edit rather than a fresh decision. */
  var info = pickerInfo();
  reviewPick = ((info && info.scope) || []).slice();
  paintReviewPicker();
  els.review.hidden = false;
}

function openReview() { openPicker("review"); }

els.reviewAll.onclick = function () {
  var units = (pickerInfo() && pickerInfo().units) || [];
  reviewPick = reviewPick.length === units.length
    ? [] : units.map(function (u) { return u.name; });
  paintReviewPicker();
};

els.reviewStart.onclick = function () {
  if (!reviewPick.length) return;
  els.review.hidden = true;
  fetch("/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session: pickerKind, over: reviewPick })
  }).catch(function () { /* the payload will say what actually happened */ });
};

/* The strip's own change button reopens the picker for the sitting that is
   actually open, not for whichever was opened last. */
els.rvChange.onclick = function () {
  openPicker(sittingKind === "walk" ? "walk" : "review");
};
document.getElementById("btn-review-close").onclick = function () {
  els.review.hidden = true;
};


/* -------------------------------------------------------------------- map */
/* THE FRONT DOOR OF A COURSE: what the repository IS, and the work drawn on it.

   The boxes are the repository's own parts and the arrows are what imports what
   -- an entity-relationship diagram of a working system. The outstanding work
   sits ON that picture as numbered chips, coloured by where each step falls in
   the order, so "what is left" and "where it lives" are one thing you look at.
   The server's half is `tutorboard/course/map.py`; nothing here invents a box,
   an arrow or a chip.

   Four decisions everything below follows from.

   THE TEXT IS MEASURED, NOT ESTIMATED. The first version wrapped labels by
   counting characters against an assumed width, and a line of capitals is half
   again as wide as that assumption -- so the words ran out of their boxes. A
   canvas measures the real face at the real size; the results are cached, so a
   box is measured once and not on every frame.

   THE LAYOUT IS A LAYERED GRAPH, NOT A COLUMN. Ranks come from the dependency
   depth (import cycles are real, so the cycle-closing edges are found and left
   out of the ranking rather than allowed to run it away), and the order within a
   rank is four passes of barycentre ordering. That is deterministic: the same
   repository lays out identically every time, on every device, which is what
   makes a map something you learn the shape of rather than something you re-read.

   NOTHING IS LAID OUT BY A LIBRARY. There is no package manager at runtime and a
   force-directed graph settles somewhere different on every open.

   AND A GESTURE NEVER REDRAWS IT. The SVG is built once per payload that changes
   it; panning and pinching are a transform on one wrapper. */

/* One box. `MAP_W` is the width every box shares -- a ragged right edge on a
   diagram reads as a mistake -- and the text is wrapped to what is left after
   the padding and the status stripe. */
var MAP_W = 226;
var MAP_PAD = 13;
var MAP_MARK = 5;            /* the status stripe down the left edge */
var MAP_GAP_X = 92;          /* the gutter an arrow turns in */
var MAP_GAP_Y = 22;
var MAP_MARGIN = 34;
var MAP_NAME = 15, MAP_ALSO = 11, MAP_DOES = 12;
var MAP_NAME_LINES = 2, MAP_DOES_LINES = 3;
var MAP_CHIP_R = 11;         /* a numbered step, on the box it is about */
var MAP_CHIP_GAP = 6;
/* Below this the ranks stop being columns and become one column: a wide graph
   on a phone is a graph nobody can follow, and a pipeline read downward is
   still a pipeline. */
var MAP_STACK_AT = 640;
/* HOW MANY RANKS GO ACROSS BEFORE THE PICTURE WRAPS.

   A dependency graph is a few ranks deep and this never fires on one. A CHAIN
   is the case it exists for: twenty chapters, each pointing at the next, is
   twenty ranks and came out six and a half thousand pixels wide -- a ribbon you
   read in one direction, which is the failure the column layout was rejected
   for, turned on its side. So a long sequence is wrapped into bands and read
   the way a page of text is.

   A FIXED number rather than one worked out from the width of the glass,
   because the same repository has to lay out identically on every device: a map
   whose shape depends on which iPad you opened it on is not a map you can
   learn. Six ranks is a little under two thousand units, which fits a fitted
   view without shrinking the labels past reading. */
var MAP_RANKS_ACROSS = 6;

var mapInfo = null;          /* the payload's map block, as it arrived */
var mapDrawn = "";           /* the signature of what is on the plane now */
var mapBox = { x0: 0, y0: 0, x1: 0, y1: 0 };
var mapHere = "";            /* the box last opened -- where you are */
var mapView = { k: 1, fit: 1, ox: 0, oy: 0, held: false };

function mapEl(tag, attrs) { return window.Gauge.el(tag, attrs); }

/* ------------------------------------------------------------ measuring */
/* How wide this string actually is, in the face the board actually ships.

   The measuring itself lives in `gauge.js`, because there are two planes that
   draw text into boxes now -- this map, and the atlas on the front door -- and
   two surfaces measuring text two slightly different ways is two spellings of
   one answer. Read that file for why an estimate is not good enough; the short
   version is that a line of capitals is half again wider than characters times
   a constant, and the labels ran out of their boxes.

   These four are the names the rest of this file already calls. They stay. */
function mapUiFace() { return window.Gauge.uiFace(); }
function mapFont(size, weight) { return window.Gauge.font(size, weight); }
function mapWidth(text, size, weight) { return window.Gauge.width(text, size, weight); }
function mapWrap(text, size, weight, room, maxLines) {
  return window.Gauge.wrap(text, size, weight, room, maxLines);
}

function mapShape(node) {
  var room = MAP_W - MAP_PAD * 2 - MAP_MARK;
  var name = mapWrap(node.name, MAP_NAME, 650, room, MAP_NAME_LINES);
  var also = node.also ? mapWrap(node.also, MAP_ALSO, 400, room, 1) : [];
  var does = node.does ? mapWrap(node.does, MAP_DOES, 400, room, MAP_DOES_LINES) : [];
  var chips = (node.steps || []).length;
  var h = MAP_PAD + name.length * 19
        + (also.length ? 15 : 0)
        + (does.length ? 5 + does.length * 16 : 0)
        + (chips ? 8 + MAP_CHIP_R * 2 : 0)
        + MAP_PAD;
  return { name: name, also: also, does: does, h: Math.max(60, h) };
}

/* ---------------------------------------------------------- the layout */
/* Which arrows close a cycle. Imports go round in circles in real code, and a
   depth computed over a cycle runs away -- every node in it one deeper than the
   last, for ever. The edges that close one are found here and left out of the
   ranking; they are still DRAWN, because a cycle is a true thing about the
   repository and hiding it would make the picture a lie. */
function mapAcyclic(n, pairs) {
  var adj = [], state = [], keep = [], i;
  for (i = 0; i < n; i++) { adj.push([]); state.push(0); }
  pairs.forEach(function (e, k) { keep.push(true); adj[e[0]].push(k); });
  function visit(v) {
    state[v] = 1;
    adj[v].forEach(function (k) {
      var w = pairs[k][1];
      if (state[w] === 1) { keep[k] = false; return; }
      if (state[w] === 0) visit(w);
    });
    state[v] = 2;
  }
  for (i = 0; i < n; i++) if (!state[i]) visit(i);
  return keep;
}

/* How deep into the dependencies each box sits: one past the deepest thing that
   depends on it. That is the left-to-right reading of the diagram -- what is
   used by everything sits on the right, what nothing else uses sits on the
   left -- and it is the reading people already have of a pipeline. */
function mapRanks(n, pairs, keep) {
  var rank = [], i;
  for (i = 0; i < n; i++) rank.push(0);
  for (var pass = 0; pass < n + 1; pass++) {
    var moved = false;
    for (i = 0; i < pairs.length; i++) {
      if (!keep[i]) continue;
      if (rank[pairs[i][1]] < rank[pairs[i][0]] + 1) {
        rank[pairs[i][1]] = rank[pairs[i][0]] + 1;
        moved = true;
      }
    }
    if (!moved) break;
  }
  return rank;
}

/* The order within a column: each box beside the average position of the boxes
   it is joined to. Four passes, alternating direction, and every sort is stable
   -- so two boxes with the same barycentre keep the order the repository gave
   them, and the whole thing is arithmetic with one answer. */
function mapOrder(byRank, pairs, keep) {
  var pos = {};
  function reindex() {
    byRank.forEach(function (col) {
      col.forEach(function (v, i) { pos[v] = i; });
    });
  }
  reindex();
  var into = {}, from = {};
  pairs.forEach(function (e, k) {
    if (!keep[k]) return;
    (into[e[1]] = into[e[1]] || []).push(e[0]);
    (from[e[0]] = from[e[0]] || []).push(e[1]);
  });
  function bary(v, side) {
    var mates = side[v] || [];
    if (!mates.length) return null;
    var sum = 0;
    mates.forEach(function (m) { sum += pos[m] || 0; });
    return sum / mates.length;
  }
  function sweep(side, order) {
    order.forEach(function (r) {
      var col = byRank[r];
      if (!col || col.length < 2) return;
      var keyed = col.map(function (v, i) { return { v: v, i: i, b: bary(v, side) }; });
      keyed.sort(function (a, b) {
        if (a.b === null && b.b === null) return a.i - b.i;
        if (a.b === null) return 1;
        if (b.b === null) return -1;
        return a.b === b.b ? a.i - b.i : a.b - b.b;
      });
      byRank[r] = keyed.map(function (x) { return x.v; });
    });
    reindex();
  }
  var down = [], up = [], r;
  for (r = 0; r < byRank.length; r++) { down.push(r); up.unshift(r); }
  for (var pass = 0; pass < 2; pass++) {
    sweep(into, down);
    sweep(from, up);
  }
}

function mapLayout(info, wide) {
  var nodes = (info.nodes || []).slice();
  var idx = {};
  nodes.forEach(function (n, k) { idx[n.id] = k; });
  var pairs = [], drawn = [];
  (info.edges || []).forEach(function (e) {
    var a = idx[e.from], b = idx[e.to];
    /* An arrow naming a box that is not here is not an arrow. Dropped rather
       than drawn to nowhere: an arrow is read as a dependency. */
    if (a === undefined || b === undefined || a === b) return;
    pairs.push([a, b]);
    drawn.push(e);
  });

  var joined = {};
  pairs.forEach(function (e) { joined[e[0]] = true; joined[e[1]] = true; });

  var keep = mapAcyclic(nodes.length, pairs);
  var rank = mapRanks(nodes.length, pairs, keep);

  var shapes = nodes.map(mapShape);
  var placed = [];
  var i;

  if (!wide) {
    /* One column, deepest last: the pipeline read downward. */
    var order = nodes.map(function (n, k) { return k; });
    order.sort(function (a, b) { return rank[a] === rank[b] ? a - b : rank[a] - rank[b]; });
    var y = MAP_MARGIN;
    order.forEach(function (v) {
      placed[v] = { node: nodes[v], shape: shapes[v], x: MAP_MARGIN, y: y,
                    w: MAP_W, h: shapes[v].h };
      y += shapes[v].h + MAP_GAP_Y;
    });
  } else {
    var byRank = [];
    for (i = 0; i < nodes.length; i++) {
      if (!joined[i]) continue;                 /* placed in the band below */
      while (byRank.length <= rank[i]) byRank.push([]);
      byRank[rank[i]].push(i);
    }
    mapOrder(byRank, pairs, keep);

    /* The ranks, in bands. One band unless the graph is long enough to need
       more, in which case the reading is the reading of a page: left to right
       along a band, then back to the left of the next one down. */
    var high = byRank.map(function (col) {
      var h = 0;
      col.forEach(function (v) { h += shapes[v].h + MAP_GAP_Y; });
      return Math.max(0, h - MAP_GAP_Y);
    });
    var bandTop = MAP_MARGIN, tall = 0;
    for (var b = 0; b < byRank.length; b += MAP_RANKS_ACROSS) {
      var band = byRank.slice(b, b + MAP_RANKS_ACROSS);
      var deep = 0;
      band.forEach(function (col, k) { deep = Math.max(deep, high[b + k]); });
      band.forEach(function (col, k) {
        /* Columns in a band share a centre line, which is what makes a rank
           read as a rank rather than as a column of boxes that happen to be
           side by side. */
        var y = bandTop + (deep - high[b + k]) / 2;
        var x = MAP_MARGIN + k * (MAP_W + MAP_GAP_X);
        col.forEach(function (v) {
          placed[v] = { node: nodes[v], shape: shapes[v], x: x, y: y,
                        w: MAP_W, h: shapes[v].h };
          y += shapes[v].h + MAP_GAP_Y;
        });
      });
      bandTop += deep + MAP_GAP_Y * 3;
      tall = bandTop - MAP_MARGIN - MAP_GAP_Y * 3;
    }

    /* WHAT NOTHING IS JOINED TO. Documents, and any part that neither imports
       nor is imported. They are content and they belong on the map, but wiring
       them into the graph would assert a relationship that is not there -- so
       they sit in a band underneath it, packed across the width the graph
       already takes rather than stretching the picture into a longer column. */
    var loose = [];
    for (i = 0; i < nodes.length; i++) if (!joined[i]) loose.push(i);
    if (loose.length) {
      var across = Math.max(1, Math.min(MAP_RANKS_ACROSS, byRank.length || 1));
      var rowTop = MAP_MARGIN + tall + MAP_GAP_Y * 3 + (byRank.length ? 20 : 0);
      var rowHigh = 0;
      loose.forEach(function (v, k) {
        var col = k % across;
        if (col === 0 && k) { rowTop += rowHigh + MAP_GAP_Y; rowHigh = 0; }
        placed[v] = { node: nodes[v], shape: shapes[v],
                      x: MAP_MARGIN + col * (MAP_W + MAP_GAP_X), y: rowTop,
                      w: MAP_W, h: shapes[v].h, apart: true };
        rowHigh = Math.max(rowHigh, shapes[v].h);
      });
    }
  }

  var box = { x0: 0, y0: 0, x1: MAP_MARGIN, y1: MAP_MARGIN };
  placed.forEach(function (p) {
    if (!p) return;
    box.x1 = Math.max(box.x1, p.x + p.w + MAP_MARGIN);
    box.y1 = Math.max(box.y1, p.y + p.h + MAP_MARGIN);
  });
  return { placed: placed, edges: drawn, pairs: pairs, box: box, wide: wide };
}

/* An arrow. Forward along the ranks it leaves the right edge and enters the
   left, as a gentle cubic through the gutter -- which is empty by construction,
   because the gutter is where a rank boundary is. An arrow that goes BACK is a
   cycle, and it is drawn under the boxes rather than through them: a curve that
   dips below both ends reads as a return path, which is what it is. */
function mapEdgePath(a, b) {
  var gap = 8;
  if (b.x > a.x) {
    var ax = a.x + a.w, ay = a.y + a.h / 2;
    var bx = b.x - gap, by = b.y + b.h / 2;
    var d = Math.max(34, (bx - ax) / 2);
    return { d: "M" + ax + "," + ay + " C" + (ax + d) + "," + ay
                + " " + (bx - d) + "," + by + " " + bx + "," + by,
             hx: bx, hy: by, dir: "right",
             /* IN THE GUTTER, which is empty by construction -- a rank boundary
                is exactly where there are no boxes. That is the only place on
                this picture a word can go without covering something. */
             mx: (ax + bx) / 2, my: (ay + by) / 2 };
  }
  if (Math.abs(b.x - a.x) < 1 && b.y > a.y) {
    var cx = a.x + a.w / 2;
    return { d: "M" + cx + "," + (a.y + a.h) + " L" + cx + "," + (b.y - gap),
             hx: cx, hy: b.y - gap, dir: "down",
             mx: cx, my: (a.y + a.h + b.y - gap) / 2 };
  }
  var sx = a.x + a.w / 2, sy = a.y + a.h;
  var tx = b.x + b.w / 2, ty = b.y + b.h + gap;
  var dip = Math.max(36, Math.abs(tx - sx) / 4);
  return { d: "M" + sx + "," + sy + " C" + sx + "," + (sy + dip)
              + " " + tx + "," + (ty + dip) + " " + tx + "," + ty,
           hx: tx, hy: ty, dir: "up",
           /* A back edge dips below both ends, so the bottom of the dip is
              below every box it passes. `0.75` rather than half because a cubic
              does not reach its control points. */
           mx: (sx + tx) / 2, my: Math.max(sy, ty) + dip * 0.75 };
}

function mapArrow(head) {
  var s = 5;
  if (head.dir === "right") {
    return [head.hx, head.hy, head.hx - s * 1.6, head.hy - s,
            head.hx - s * 1.6, head.hy + s];
  }
  if (head.dir === "down") {
    return [head.hx, head.hy, head.hx - s, head.hy - s * 1.6,
            head.hx + s, head.hy - s * 1.6];
  }
  return [head.hx, head.hy - s * 0.2, head.hx - s, head.hy + s * 1.4,
          head.hx + s, head.hy + s * 1.4];
}

/* WHEN A STEP SHOULD BE DONE, as a colour. The plan's own order is the order;
   the chips run hot to cold along it, so the shape of what is left is visible
   without reading a single number. Four bands rather than a continuous ramp,
   because four colours on an eleven-pixel circle can be told apart and a
   gradient cannot. It is never a schedule: every chip is tappable, and which
   one to do is the person's. */
function mapWhen(order) {
  if (order <= 1) return "now";
  if (order <= 3) return "soon";
  if (order <= 6) return "later";
  return "some";
}

/* Build the whole picture. Once per payload that changes it, never per frame. */
function mapDraw(info) {
  var wide = (els.mapPlane.clientWidth || 0) >= MAP_STACK_AT;
  var out = mapLayout(info, wide);
  mapBox = out.box;

  var svg = mapEl("svg", {
    width: out.box.x1, height: out.box.y1,
    viewBox: "0 0 " + out.box.x1 + " " + out.box.y1
  });

  out.edges.forEach(function (e, k) {
    var a = out.placed[out.pairs[k][0]], b = out.placed[out.pairs[k][1]];
    if (!a || !b) return;
    var path = mapEdgePath(a, b);
    var line = mapEl("path", { "class": "edge", d: path.d });
    /* An arrow eleven imports thick is a different fact from one that carries a
       single mention, and the thickness is the only place to say it without
       another label on the picture. */
    if ((e.weight || 1) >= 5) line.setAttribute("class", "edge strong");
    svg.appendChild(line);
    svg.appendChild(mapEl("polygon", { "class": "edge-head",
                                       points: mapArrow(path).join(" ") }));
    /* WHAT FLOWS ALONG IT, where a written map says. `words`, `turns`, `a
       graded transcript` -- the noun, not a sentence: an arrow that has to be
       read as prose is a arrow nobody reads. A derived map has no labels and
       never will, because an import is not a thing that flows; it is a
       dependency, and the thickness already says how much of one.

       Painted on a plate the colour of the plane, because a word laid straight
       over a curve is unreadable and this picture is looked at while somebody
       is thinking about something else. */
    if (e.label && path.mx !== undefined) {
      var w = mapWidth(e.label, 10.5, 500) + 10;
      svg.appendChild(mapEl("rect", { "class": "edge-plate",
                                      x: path.mx - w / 2, y: path.my - 8,
                                      width: w, height: 16, rx: 5 }));
      var t = mapEl("text", { "class": "edge-label",
                              x: path.mx, y: path.my + 3.5 });
      t.textContent = e.label;
      svg.appendChild(t);
    }
  });

  out.placed.forEach(function (p) {
    if (!p) return;
    var n = p.node;
    var g = mapEl("g", {
      "class": "node " + (n.kind || "part") + " " + (n.status || "unknown")
               + (n.id === mapHere ? " here" : "") + (p.apart ? " apart" : ""),
      "data-id": n.id, tabindex: "0", role: "button",
      "aria-label": n.name + ", " + (n.status || "unknown")
    });
    g.appendChild(mapEl("rect", { "class": "box", x: p.x, y: p.y,
                                  width: p.w, height: p.h, rx: 11 }));
    g.appendChild(mapEl("rect", { "class": "mark", x: p.x + 1.5, y: p.y + 9,
                                  width: MAP_MARK, height: p.h - 18, rx: 2.5 }));
    var tx = p.x + MAP_PAD + MAP_MARK;
    var ty = p.y + MAP_PAD + 13;
    p.shape.name.forEach(function (line) {
      var t = mapEl("text", { "class": "name", x: tx, y: ty });
      t.textContent = line;
      g.appendChild(t);
      ty += 19;
    });
    p.shape.also.forEach(function (line) {
      var t = mapEl("text", { "class": "also", x: tx, y: ty + 1 });
      t.textContent = line;
      g.appendChild(t);
      ty += 15;
    });
    if (p.shape.does.length) {
      ty += 5;
      p.shape.does.forEach(function (line) {
        var t = mapEl("text", { "class": "does", x: tx, y: ty });
        t.textContent = line;
        g.appendChild(t);
        ty += 16;
      });
    }
    /* THE WORK, ON THE THING IT IS ABOUT. A numbered chip per step of the plan
       that names this part, in the plan's order, coloured by how soon. Its own
       tap, because a step is a sitting and the box is a different sitting. */
    (n.steps || []).forEach(function (step, i) {
      var cx = p.x + MAP_PAD + MAP_MARK + MAP_CHIP_R
             + i * (MAP_CHIP_R * 2 + MAP_CHIP_GAP);
      var cy = p.y + p.h - MAP_PAD - MAP_CHIP_R + 2;
      var chip = mapEl("g", { "class": "chip " + mapWhen(step.order),
                              "data-step": step.label, tabindex: "0",
                              role: "button",
                              "aria-label": "step " + step.num + ", " + step.title });
      chip.appendChild(mapEl("circle", { cx: cx, cy: cy, r: MAP_CHIP_R }));
      var t = mapEl("text", { x: cx, y: cy + 4, "text-anchor": "middle" });
      t.textContent = step.num;
      chip.appendChild(t);
      chip.addEventListener("click", function (ev) {
        ev.stopPropagation();
        openWork(n.id, step.label);
      });
      chip.addEventListener("keydown", function (ev) {
        if (ev.key !== "Enter" && ev.key !== " ") return;
        ev.preventDefault();
        ev.stopPropagation();
        openWork(n.id, step.label);
      });
      g.appendChild(chip);
    });
    g.addEventListener("click", function () { openWork(n.id, ""); });
    g.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openWork(n.id, ""); }
    });
    svg.appendChild(g);
  });

  els.mapSheet.innerHTML = "";
  els.mapSheet.style.width = out.box.x1 + "px";
  els.mapSheet.style.height = out.box.y1 + "px";
  els.mapSheet.appendChild(svg);
  return out.placed.length;
}

/* What the payload says, painted. The plane is NOT moved: a map that jumps back
   to the origin because the tutor wrote a card is a map nobody can read while a
   lesson is running.

   Wrapped, and this is not defensive habit. This runs inside `render`, which is
   what paints the lesson, and a map that threw on a payload would stop the
   lesson painting at all -- a blank board in the middle of somebody's proof,
   caused by the one surface on this page they were not using. A map that cannot
   be drawn is a map that is not there; the lesson is untouched either way. */
function paintMap(info, state) {
  try { paintMapNow(info, state); }
  catch (e) { mapDrawn = ""; }
}

/* AND DRAWN AGAIN THE MOMENT THE READING FACE ARRIVES.

   Every box on this map is sized by measuring its label, and until the web font
   has loaded that measurement is of a fallback face that is far narrower than
   the one the label will be painted in -- so the first map of a cold load is
   laid out for the wrong face and its words run out of their boxes. `gauge.js`
   throws its cached answers away when the fonts settle and calls this; the
   signature is cleared so the plane rebuilds rather than deciding nothing has
   changed. Nothing is fetched and no payload is involved. */
if (window.Gauge && window.Gauge.onFace) {
  window.Gauge.onFace(function () {
    if (!mapInfo) return;
    mapDrawn = "";
    paintMap(mapInfo, (lastLive && lastLive.state) || {});
  });
}

function paintMapNow(info, state) {
  mapInfo = info || null;
  var can = !!(mapInfo && (mapInfo.nodes || []).length);
  if (els.mapCount) {
    els.mapCount.textContent = can
      ? (mapInfo.nodes.length + (mapInfo.nodes.length === 1 ? " part" : " parts")
         + (mapInfo.steps ? " · " + mapInfo.steps
            + (mapInfo.steps === 1 ? " step" : " steps") : ""))
      : "";
  }
  if (els.mapTitle) {
    els.mapTitle.textContent = (state && state.course) || "the map";
  }
  if (els.mapWhy) els.mapWhy.textContent = (mapInfo && mapInfo.why) || "";
  mapControls(can);
  paintLoose();
  if (!can) { mapDrawn = ""; return; }

  var wide = (els.mapPlane.clientWidth || 0) >= MAP_STACK_AT;
  var sign = JSON.stringify(mapInfo) + "|" + (wide ? "wide" : "stacked");
  if (sign === mapDrawn) return;
  mapDraw(mapInfo);
  mapDrawn = sign;
  if (!mapView.held) mapFit();
  else mapClamp();
  mapPaint();
}

/* THE STEPS THIS COULD NOT PLACE, and they are not dropped.

   A step names no file, or names one that has moved, and there is nowhere
   honest to put it on the picture. Putting it on a box anyway would be a claim
   about where the work is; leaving it out would take a choice away from the
   person whose plan it is. So it goes in a tray under the bar, in the plan's
   own order, coloured and numbered like every other chip and opening the same
   sitting. */
function paintLoose() {
  var host = els.mapLoose;
  if (!host) return;
  var loose = (mapInfo && mapInfo.loose) || [];
  host.innerHTML = "";
  host.hidden = !loose.length;
  if (!loose.length) return;
  var lead = document.createElement("span");
  lead.className = "muted";
  lead.textContent = "not on a box yet:";
  host.appendChild(lead);
  loose.forEach(function (step) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "loose-chip " + mapWhen(step.order);
    b.innerHTML = '<span class="n"></span><span class="t"></span>';
    b.querySelector(".n").textContent = step.num;
    b.querySelector(".t").textContent = step.title;
    b.onclick = function () { openWork("", step.label); };
    host.appendChild(b);
  });
}

function mapControls(can) {
  var title = can ? "the map of this course"
                  : "there is nothing in this repository to draw yet";
  mapButtons().forEach(function (b) { b.title = title; });
}

/* Every control that opens the map: the one in the title bar, one in the head of
   each drawer, and one on the document viewer. Found once -- they are all in the
   markup, none of them is built at runtime, and this is read on every payload. */
var mapWays = null;
function mapButtons() {
  if (!mapWays) {
    mapWays = [];
    var found = document.querySelectorAll(".to-map");
    for (var i = 0; i < found.length; i++) mapWays.push(found[i]);
  }
  return mapWays;
}

/* ------------------------------------------------------------- the plane */
/* Pan, pinch, wheel. The contact bookkeeping is `plane-core.js`, which the
   writing surface uses too: which contacts are LIVE decides what a gesture is,
   and a map that counted a finger whose lift was never delivered would zoom on
   one finger and do nothing on two, exactly as the slate once did.

   Made on the first contact rather than at load. Nothing on this page may fail
   to start because a script that is not the lesson did not arrive: a board.js
   that throws while loading is a blank screen, and the lesson has to be
   reachable from every state this application can be in. */
var mapHand = null;
function mapFingers() {
  if (!mapHand && window.Plane) mapHand = window.Plane.contacts({});
  return mapHand;
}

function mapRoom() {
  if (!window.Plane) return mapBox;
  /* A third of a viewport of slack beyond the picture. Enough that a box at the
     edge is not pinned against the glass; not so much that a flick leaves the
     map off-screen, which looks exactly like a crash. */
  return window.Plane.room(mapBox, els.mapPlane.clientWidth,
                           els.mapPlane.clientHeight, mapView.k, 0.35);
}

function mapLimits() {
  return { lo: Math.min(mapView.fit, 1) * 0.35,
           hi: Math.max(mapView.fit, 1) * 3 };
}

function mapClamp() {
  if (!window.Plane) return;
  window.Plane.clamp(mapView, mapRoom(),
                     els.mapPlane.clientWidth, els.mapPlane.clientHeight);
}

function mapPaint() {
  els.mapSheet.style.transform =
    "translate(" + mapView.ox + "px," + mapView.oy + "px) scale(" + mapView.k + ")";
}

/* WHERE THE MAP OPENS, and it is not "everything on the glass".

   Fitting the whole picture by area is what makes a tall map unreadable: a
   repository with twenty boxes in a column is a ribbon a thousand units long,
   and squeezing that into an iPad's height puts it on screen at 68% -- legible
   to nobody. The writing surface learned this first and the rule is written on
   it: fit by WIDTH, never by area, and scroll the height. Capped at 1, because a
   picture narrower than the glass is not one to magnify. ⤢ is there for the
   other question, which is "show me all of it". */
function mapFit() {
  var cw = els.mapPlane.clientWidth, ch = els.mapPlane.clientHeight;
  if (!cw || !ch || !(mapBox.x1 > 0) || !window.Plane) return;
  /* Floored, because there is a size past which shrinking to fit stops being a
     view of anything: a label at half size on a tablet is a grey smear, and a
     map that opens as a grey smear is worse than one that opens at a readable
     size with a pan to do. Wider than this and it opens legible and partly off
     the glass -- ⤢ is one tap away for the whole shape. */
  mapView.fit = Math.max(0.5, Math.min(1, cw / mapBox.x1));
  mapView.k = mapView.fit;
  mapView.ox = 0;
  mapView.oy = 0;                      /* the top of it; clamp centres if short */
  mapView.held = false;
  mapClamp();
  mapPaint();
  /* And NOT remembered. A fit runs by itself whenever the picture is rebuilt or
     the glass changes shape, and a view nobody chose must not overwrite the one
     they did -- least of all before the landing rule has had a chance to read
     it, which is how a course left on the map reopened in the lesson. */
}

/* ⤢ -- all of it, however small that has to be. The one gesture that answers
   "where am I in this" rather than "what does this box say". */
function mapWhole() {
  var cw = els.mapPlane.clientWidth, ch = els.mapPlane.clientHeight;
  if (!cw || !ch || !(mapBox.x1 > 0) || !window.Plane) return;
  var lim = mapLimits();
  window.Plane.frame(mapView, { x0: 0, y0: 0, x1: mapBox.x1, y1: mapBox.y1 },
                     cw, ch, 12, lim.lo, lim.hi);
  mapView.held = true;
  mapClamp();
  mapPaint();
  mapRemember();
}

function mapZoom(k, cx, cy) {
  if (!window.Plane) return;
  var lim = mapLimits();
  window.Plane.zoomAbout(mapView, k, cx, cy, lim.lo, lim.hi);
  mapClamp();
  mapPaint();
  mapSettle();
}

els.mapPlane.addEventListener("pointerdown", function (ev) {
  if (ev.pointerType === "mouse" && ev.button !== 0) return;
  var hand = mapFingers();
  if (!hand) return;
  try { els.mapPlane.setPointerCapture(ev.pointerId); } catch (e) { /* not fatal */ }
  hand.note(ev.pointerId, ev.clientX, ev.clientY);
  hand.begin(mapView.k);
});

els.mapPlane.addEventListener("pointermove", function (ev) {
  var hand = mapFingers();
  if (!hand || !hand.has(ev.pointerId)) return;
  var prev = hand.note(ev.pointerId, ev.clientX, ev.clientY);
  var spread = hand.spread();
  if (spread) {
    var r = els.mapPlane.getBoundingClientRect();
    mapZoom(spread.k, spread.cx - r.left, spread.cy - r.top);
    return;
  }
  if (hand.live().length !== 1 || !prev) return;
  mapView.ox += ev.clientX - prev.x;
  mapView.oy += ev.clientY - prev.y;
  mapView.held = true;
  mapClamp();
  mapPaint();
  mapSettle();
});

/* A lift is caught at the window as well as at the plane. A finger that leaves
   past the edge never delivers one to the element, and a contact that stays in
   the map for ever is a phantom the next gesture is counted against. */
["pointerup", "pointercancel"].forEach(function (t) {
  window.addEventListener(t, function (ev) {
    if (mapHand) mapHand.forget(ev.pointerId);
  }, true);
});

els.mapPlane.addEventListener("wheel", function (e) {
  e.preventDefault();
  if (e.ctrlKey || e.metaKey) {
    var r = els.mapPlane.getBoundingClientRect();
    mapZoom(mapView.k * (e.deltaY < 0 ? 1.08 : 0.93),
            e.clientX - r.left, e.clientY - r.top);
    return;
  }
  mapView.ox -= e.deltaX;
  mapView.oy -= e.deltaY;
  mapView.held = true;
  mapClamp();
  mapPaint();
  mapSettle();
}, { passive: false });

window.addEventListener("resize", function () {
  if (els.map.hidden) return;
  /* Crossing the width at which the ranks become one column is a different
     picture, and `paintMap` already knows: the layout mode is part of the
     signature it compares, so this rebuilds only when it has actually changed. */
  paintMap(mapInfo, (lastLive && lastLive.state) || {});
  if (mapView.held) { mapClamp(); mapPaint(); } else { mapFit(); }
});

/* --------------------------------------------------- opening and leaving */
function openMap(why) {
  if (!(mapInfo && (mapInfo.nodes || []).length)) {
    /* THE LESSON MUST ALWAYS BE REACHABLE, and a map with nothing on it is a
       blank screen between somebody and their work. */
    return false;
  }
  els.map.hidden = false;
  document.body.classList.add("mapping");
  /* The way back out of the picture's own pan and zoom, while there is a picture
     to be lost in. */
  if (els.mapback) { els.mapback.hidden = false; panicRemeasure(); }
  mapDrawn = "";                       /* the plane had no size while hidden */
  paintMap(mapInfo, (lastLive && lastLive.state) || {});
  if (why !== "restored") mapRemember();
  return true;
}

function closeMap() {
  els.map.hidden = true;
  els.work.hidden = true;
  document.body.classList.remove("mapping");
  if (els.mapback) { els.mapback.hidden = true; panicRemeasure(); }
  mapRemember();
}

els.mapClose.onclick = function () { closeMap(); };
els.mapFit.onclick = function () { mapWhole(); };
mapButtons().forEach(function (b) {
  b.onclick = function () {
    /* Whatever is over the lesson goes with it. A drawer left open behind the
       map is a drawer sitting on top of the lesson when the map closes. */
    [els.contents, els.review, els.scratch, els.papersPanel,
     document.getElementById("history"), els.kind, els.steer].forEach(function (panel) {
      if (panel) panel.hidden = true;
    });
    if (els.paper && !els.paper.hidden) closePaper();
    openMap();
  };
});


/* --------------------------------------------------------- ways to work */
/* WHAT A TAP ON THE MAP OFFERS, and it is the whole point of the map.

   A box is a part of the repository and a chip is a step of the plan, and
   tapping either asks the same question: what do you want to do about this.
   Every answer opens a sitting already pointed at that part, so nothing has to
   be typed and the tutor is not left to guess what the sitting is about.

   The six are the person's own words made imperative, and they are NOT named
   after the sitting kinds underneath -- nobody taps "lecture, stance do". Only
   what the thing can actually support is offered: there is no walkthrough of a
   box with no files in it, and no "show me the slides" where there is no deck.

   `aim` is what makes this more than a relabelled chooser. It rides in
   `state.json` and into the line the tutor is woken with, so a sitting opened
   as "tell me what to write" is a sitting the tutor knows is that. */
var workNode = "";
var workStep = "";

var WORK = [
  { aim: "teach", label: "Teach me how this works",
    sub: "Worked through, with the mathematics done properly.",
    session: "lecture" },
  { aim: "build", label: "Write the code for me",
    sub: "The tutor does the work and reports what it changed.",
    /* `does` is a PAINT HINT and is never sent: the three aims whose product is
       a change are marked the way a doing stance is, because that is the state
       in which the tutor writes what the person would otherwise have written.
       Who actually writes the code is `config.AIM_STANCE`, on the server. */
    session: "lecture", does: true },
  { aim: "coach", label: "Tell me what to write, I'll code it",
    sub: "One step at a time, in English. You type it.",
    session: "lecture" },
  { aim: "trace", label: "Walk me through the code",
    sub: "Line by line, through what is already there.",
    session: "walk", needs: "files" },
  { aim: "drill", label: "Set me problems on it",
    sub: "Asked cold, over this part of the repository.",
    session: "review", needs: "part" },
  { aim: "paper", label: "Write it up as a paper",
    sub: "A document rather than an answer, kept in writeups/.",
    session: "make", makes: "paper", does: true },
  { aim: "slides", label: "Build me a deck about it",
    sub: "Slides you can then read on the board.",
    session: "make", makes: "slides", does: true },
  { aim: "show", label: "Show me the document",
    sub: "On the glass, a page at a time.",
    session: "", needs: "doc" }
];

function workOn(id) {
  var found = null;
  ((mapInfo && mapInfo.nodes) || []).forEach(function (n) {
    if (n.id === id) found = n;
  });
  return found;
}

/* THE STEP, IN FULL, AND IT IS FETCHED ON THE TAP.

   The chip carries a 240-character blurb, which is what a chip on the map wants
   and is not what this sheet wants: a person tapping a step is about to choose
   how to work on it, and the choice was being made against three sentences and
   an ellipsis.

   Fetched rather than carried, because the payload is polled four times a
   second and a plan's twelve whole steps is tens of kilobytes of it, on every
   poll, for a panel that is open for as long as it takes to tap one of seven
   buttons.

   A second tap while the first is in flight is the ordinary case — somebody
   opens the wrong chip and opens the right one — so the answer is dropped
   unless it is still the step being asked about. And a request that fails falls
   back to the blurb rather than to an empty box: the blurb is already here and
   nothing is gained by hiding it because the network did not answer. */
var stepWanted = "";

function showStep(chip) {
  var box = els.workText;
  if (!box) return;
  stepWanted = (chip && chip.label) || "";
  box.textContent = "";
  box.hidden = true;
  if (!stepWanted) return;
  var asked = stepWanted;
  var blurb = (chip && chip.summary) || "";
  box.textContent = "reading the plan…";
  box.hidden = false;

  function settle(text) {
    if (asked !== stepWanted) return;
    box.textContent = text;
    box.hidden = !text;
    box.scrollTop = 0;
  }
  fetch("/plan/step", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ step: asked })
  }).then(function (r) {
    return r.json().catch(function () { return {}; });
  }).then(function (got) {
    settle((got && got.ok !== false && got.text) ? got.text : blurb);
  }).catch(function () {
    settle(blurb);
  });
}

function openWork(id, step) {
  /* Last time's "waiting on" line goes before this time's is worked out. The
     sheet's list is rebuilt from scratch every open; this line is not in the
     list, so it would otherwise stack. */
  var stale = els.work.querySelector(".work-blocked");
  if (stale && stale.parentNode) stale.parentNode.removeChild(stale);
  var node = workOn(id);
  workNode = node ? node.id : "";
  workStep = step || "";
  mapHere = workNode;
  var boxes = els.mapSheet.querySelectorAll(".node");
  for (var i = 0; i < boxes.length; i++) {
    boxes[i].classList.toggle("here", boxes[i].getAttribute("data-id") === workNode);
  }

  var chip = null;
  if (workStep) {
    var pool = node ? (node.steps || []) : ((mapInfo && mapInfo.loose) || []);
    pool.forEach(function (s) { if (s.label === workStep) chip = s; });
  }

  els.workTitle.textContent = chip ? chip.title : (node ? node.name : "this course");
  var sub = [];
  if (chip) sub.push("step " + chip.num + (node ? " · " + node.name : ""));
  else if (node && node.also) sub.push(node.also);
  if (node && node.does && !chip) sub.push(node.does);
  els.workSub.textContent = sub.join(" — ");
  showStep(chip);

  /* WHAT THIS ONE IS WAITING ON, and it is the field nothing could set until a
     map could be written by hand. Discovery can see that a directory exists and
     what it imports; it cannot see that the scorer is stuck behind a seam that
     has not been built yet, because there is nothing on disk that says so.

     It goes HERE rather than on the box. A box is eleven characters wide at the
     zoom somebody actually reads the map at, and "a list is not a diagram" was
     paid for once already -- but this is the sheet that opens when a person taps
     a box intending to work on it, which is the exact moment "you cannot, yet,
     and here is why" is worth saying. Named by the plain names of the boxes it
     names, never their ids, because the ids are not what anybody calls them. */
  var why = (node && node.blockedBy) || [];
  if (why.length) {
    var names = why.map(function (id) {
      var on = workOn(id);
      return on ? on.name : id;
    });
    var line = document.createElement("p");
    line.className = "work-blocked";
    line.textContent = "waiting on " + names.join(" and ")
                     + (names.length === 1 ? "" : "");
    els.workSub.insertAdjacentElement("afterend", line);
  }

  var host = els.workList;
  host.innerHTML = "";
  var files = (node && node.files) || [];
  var doc = (node && node.doc) || "";
  WORK.forEach(function (way) {
    if (way.needs === "files" && !files.length) return;
    if (way.needs === "doc" && !doc) return;
    if (way.needs === "part" && !(node && node.dir)) return;
    var b = document.createElement("button");
    b.type = "button";
    b.className = "work-way";
    b.innerHTML = '<strong></strong><span></span>';
    b.querySelector("strong").textContent = way.label;
    b.querySelector("span").textContent = way.sub;
    b.onclick = function () { takeWork(way, node, chip); };
    host.appendChild(b);
  });
  mapRemember();
  els.work.hidden = false;
}

function takeWork(way, node, chip) {
  els.work.hidden = true;
  if (way.aim === "show") {
    var name = node ? node.name : "document";
    closeMap();
    openDoc(node.doc, name);
    return;
  }
  /* A NAME FROM THE BROWSER IS NEVER CONSTRUCTED INTO ANYTHING. What goes over
     the wire is the box's id and the step's label, and the server looks both up
     in what discovery found before either reaches a filesystem or a prompt. The
     sitting's own label is built there too, for the same reason. */
  var body = {
    session: way.session,
    aim: way.aim,
    node: (node && node.id) || null,
    step: (chip && chip.label) || null,
    /* NO STANCE. The aim answers it -- `build` with a stance of `teach` is a
       contradiction -- and `config.AIM_STANCE` is where that answer lives. The
       browser was sending both, which made it the thing deciding, on its own
       authority, something the repository and its family had already said. */
    makes: way.makes || null,
    /* AND GET ON WITH IT. Choosing a way to work is the instruction; a second
       tap on "ask the tutor to begin", on the lesson behind the map they were
       just looking at, is the ceremony this replaces. Asked as a question,
       which is the worst way to find out: "do I ask the tutor to begin?" */
    begin: true
  };
  if (way.session === "walk") body.over = (node && node.files) || [];
  if (way.session === "review") body.over = [node.dir + "/"];
  fetch("/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  }).then(function (r) {
    return r.json().catch(function () { return {}; });
  }).then(function (got) {
    if (got && got.ok === false) {
      els.workSub.textContent = "That could not be opened: "
        + (got.error || "the board refused it") + ".";
      els.work.hidden = false;
      return;
    }
    /* The sitting is open and the tutor has been asked to start. Leaving the
       map is the point of having tapped, and what is behind it is the lesson
       with the request already on it. */
    closeMap();
  }).catch(function () {
    /* The payload will say what actually happened; the board is not the place
       to guess at a network. */
    closeMap();
  });
}

els.workClose.onclick = function () { els.work.hidden = true; };


/* ---------------------------------------- where a course opens, and why */
/* A COURSE OPENS WHERE YOU LEFT IT.

   Not always on the map. On the surface you were last on in this course, and if
   that was the map, on the part of the map you were looking at -- the same pan
   and zoom, with the box you last opened still marked. Somebody three steps into
   a derivation who taps their course must land in the derivation.

   A course nobody has opened on this device yet, or one whose remembered
   surface no longer exists, opens on the map. That is the default, and it is
   the only time the map is put in front of anybody.

   `localStorage`, and deliberately not `state.json`: two devices reading the
   same course are two people looking at different parts of it, and that is
   correct. It is a per-viewer convenience rather than state -- it can throw, it
   can come back empty, and a private window or cleared site data wipes it -- so
   every read and write is wrapped and the fallback is the map, which is the
   default anyway. */
var MAP_WHERE = "board.where.";
/* Old enough to be a different week's intention rather than this evening's. */
var MAP_WHERE_FRESH = 30 * 24 * 3600 * 1000;
var mapLanded = false;
var mapSettleTimer = null;

function mapCourse() {
  return ((lastLive && lastLive.state && lastLive.state.course) || "").trim();
}

function mapRemember() {
  var course = mapCourse();
  if (!course) return;
  var here = { at: Date.now() };
  if (!els.map.hidden) {
    here.surface = "map";
    here.x = mapView.ox; here.y = mapView.oy; here.k = mapView.k;
    here.node = mapHere;
  } else if (els.paper && !els.paper.hidden && paperOpen) {
    here.surface = "document:" + paperOpen;
  } else {
    here.surface = "lesson";
  }
  try {
    window.localStorage.setItem(MAP_WHERE + course, JSON.stringify(here));
  } catch (e) { /* a private window, or no room. The map is the fallback. */ }
  /* AND THE SAME PLACE, SPELLED AS AN ADDRESS. An address nobody can obtain is
     a feature nobody uses: this is where one is got from -- off the bar, by
     being somewhere. Only the three surfaces `here.surface` already names, and
     always `replaceState`, so the back button still leaves the board rather
     than walking backwards through a pan. */
  addrShow(here);
}

/* Writing on every frame of a pan would be a JSON encode and a storage write
   sixty times a second. The plane is remembered once it has stopped moving. */
function mapSettle() {
  if (mapSettleTimer) clearTimeout(mapSettleTimer);
  mapSettleTimer = setTimeout(function () {
    mapSettleTimer = null;
    mapRemember();
  }, 400);
}

function mapRecall() {
  var course = mapCourse();
  if (!course) return null;
  try {
    var raw = window.localStorage.getItem(MAP_WHERE + course);
    if (!raw) return null;
    var here = JSON.parse(raw);
    if (!here || typeof here !== "object") return null;
    if (!here.at || Date.now() - here.at > MAP_WHERE_FRESH) return null;
    return here;
  } catch (e) { return null; }
}

/* Once per load, on the first payload that knows which course this is. */
function mapLand() {
  if (mapLanded || !mapCourse()) return;
  /* AN ADDRESS IN THE BAR OUTRANKS EVERYTHING, and it is the one thing here
     that cannot be acted on the moment a payload arrives: until `/health` has
     said which workspace this board IS, an address naming another one cannot
     be told apart from one naming this one. Landing is not marked done, so the
     next payload tries again -- and `addrReady` runs this by hand the moment
     the answer lands, because a board whose lesson is already on screen gets no
     further payload to be prompted by. */
  if (addrWanted && !boardIdKnown) return;
  mapLanded = true;
  if (addrWanted) {
    var asked = addrWanted;
    addrWanted = null;
    addrGo(asked);
    return;
  }
  /* An address that asks for the map outranks anything remembered: it is
     somebody tapping "map" on the writing surface a second ago. */
  if (mapAsked()) { openMap(); return; }
  var here = mapRecall();
  if (!here) { openMap(); return; }          /* never opened here: the default */
  if (here.surface === "lesson") return;     /* they were working; leave them */
  if (typeof here.surface === "string" && here.surface.indexOf("document:") === 0) {
    var kind = here.surface.slice("document:".length);
    var id = kind.indexOf("doc/") === 0 ? kind.slice(4) : "";
    var known = (readingInfo && readingInfo.documents || []).filter(function (d) {
      return d.id === id;
    })[0];
    /* A document that has since moved is a surface that no longer exists, and
       the rule for that is the map. */
    if (known) { openDoc(known.id, known.name); return; }
    openMap();
    return;
  }
  if (here.surface !== "map") { openMap(); return; }
  mapHere = here.node || "";
  if (!openMap("restored")) return;
  /* The same part of the map, at the same magnification. Only if the numbers
     are numbers: a record half-written by a browser that ran out of room must
     not leave the plane somewhere it cannot be panned back from. */
  if (typeof here.k === "number" && here.k > 0
      && typeof here.x === "number" && typeof here.y === "number") {
    mapView.k = here.k;
    mapView.ox = here.x;
    mapView.oy = here.y;
    mapView.held = true;
    mapClamp();
    mapPaint();
  }
}

/* `/board?map=1`, which is what the slate's own map link is. Read once and then
   taken out of the address, so a reload is not a second instruction. */
function mapAsked() {
  var asked = false;
  try {
    asked = /(^|[?&])map=1(&|$)/.test(window.location.search || "");
    if (asked && window.history && window.history.replaceState) {
      window.history.replaceState({}, "",
        window.location.pathname
        + (window.location.search || "").replace(/([?&])map=1(&|$)/, "$1")
                                        .replace(/[?&]$/, "")
        /* The fragment survives. It is the address, and rewriting the bar to
           drop `map=1` used to take it with it. */
        + (window.location.hash || ""));
    }
  } catch (e) { return false; }
  return asked;
}


/* ------------------------------------------------------------- addresses */
/* ONE RESOLVER. `address.js` is the grammar and has no opinion about browsers;
   this is the only thing anywhere that takes an address and puts the board on
   the surface it names.

       #/w/<family>/<workspace>[/…]

   Three rules, and they are the whole of why this is one function:

     1. A NAME FROM A BROWSER NEVER REACHES A FILESYSTEM. Every component is
        looked up in what discovery already found and handed to this page --
        `mapInfo.nodes`, `lastLive.cards`, `readingInfo.documents`,
        `walkInfo.units`, `knownSets`, `lastLive.slate`, and for a past sitting
        the archive's own list. A miss is a miss, said as "that is not here any
        more", never as an error and never as something near it.
     2. A LINK THAT NO LONGER RESOLVES SAYS SO WHERE IT IS WRITTEN. Meeting
        notes from March open in September and half of what they point at has
        moved. `markAddresses` checks every address written into the lesson
        against the same payload this resolver uses, so a dead one reads as dead
        in the sentence it is in rather than after the tap.
     3. TWO SPELLINGS OF AN ADDRESS IS TWO BUGS. `spell` is the only thing on
        this page that builds one, and it is what puts the current surface in
        the bar so that an address can be copied off the glass at all.

   Two surfaces the grammar names are finer than anything the board can paint
   today: one function inside a file, and one problem inside a set. Neither is
   dropped and neither is faked -- the address lands on the thing that CONTAINS
   it and says in one line what it was pointing at. See §2.4 of the handoff. */

var boardId = "";              /* this board's own `family/workspace` */
var boardIdKnown = false;      /* whether `/health` has answered at all */
var addrWanted = null;         /* an address waiting for the first payload */
var addrGoneSaid = Object.create(null);   /* address text -> why it is dead */
var BOUNCED = "board.addr.bounced";

function ADDR() { return window.Address || null; }

function addrParse(text) {
  var g = ADDR();
  if (!g) return null;
  try { return g.parse(text); } catch (e) { return null; }
}

/* The one link speller on this page. Everything it is given is placed in THIS
   workspace, because a board can only make an address for where it is. */
function spell(spec) {
  var g = ADDR();
  if (!g || !boardId || boardId.indexOf("/") < 0) return "";
  var out = { ws: boardId }, k;
  for (k in spec) {
    if (Object.prototype.hasOwnProperty.call(spec, k)) out[k] = spec[k];
  }
  return g.format(out);
}

/* Where the board is now, in the bar. `mapRemember` already decides what "here"
   means and is called from every place that changes it, so this rides along
   rather than growing a second idea of the same thing. Always `replaceState`:
   a pan is not a page, and the back button must still leave the board. */
function addrShow(here) {
  if (!here || !window.history || !window.history.replaceState) return;
  var want;
  if (here.surface === "map") {
    want = spell(here.node ? { surface: "node", node: here.node }
                           : { surface: "workspace" });
  } else if (typeof here.surface === "string"
             && here.surface.indexOf("document:doc/") === 0) {
    want = spell({ surface: "doc",
                   doc: here.surface.slice("document:doc/".length) });
  } else {
    /* THE LESSON, WITH NOTHING OVER IT -- and the bar may already name a card,
       a past sitting, a problem or a page of handwriting. Every one of those IS
       the lesson with something pointed out on it, none of them can be spelled
       from `here`, and overwriting one with the bare workspace takes a link off
       the glass a second after it was followed. Never downgrade. */
    var now = addrParse(window.location.hash || "");
    if (now && now.ws === boardId && now.surface !== "workspace") return;
    want = spell({ surface: "workspace" });
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
  try { window.sessionStorage.removeItem(BOUNCED); } catch (e) {}
  markAddresses();
  return "ok";
}

/* Everything over the lesson goes, because an address is somebody saying where
   they want to be and a drawer left open is a drawer sitting on top of it. */
function addrShut() {
  [els.contents, els.review, els.scratch, els.papersPanel,
   document.getElementById("history"), els.kind, els.work,
   els.steer].forEach(function (p) {
    if (p) p.hidden = true;
  });
  if (els.paper && !els.paper.hidden) closePaper();
  closeViewer();
  if (!els.map.hidden) closeMap();
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

function addrRow(host, attr, value) {
  var rows, i;
  try { rows = host.querySelectorAll("[" + attr + "]"); } catch (e) { return null; }
  for (i = 0; i < rows.length; i++) {
    if (rows[i].getAttribute(attr) === value) return rows[i];
  }
  return null;
}

/* ANOTHER WORKSPACE IS ANOTHER BOARD ON ANOTHER PORT, and the one thing that
   can move the single address between them is the front door. Hand it the whole
   thing: it switches, then comes back to it.

   Once, and recorded, because if the switch does not land this is still the
   wrong board -- and sending it back would be a page bouncing between two
   surfaces for as long as anybody watched it. */
function addrElsewhere(a) {
  var tried = "";
  try { tried = window.sessionStorage.getItem(BOUNCED) || ""; } catch (e) {}
  if (tried === a.text) {
    return addrDead(a, "that is in " + a.ws
                    + ", and this board could not be moved there");
  }
  try { window.sessionStorage.setItem(BOUNCED, a.text); } catch (e) {}
  window.location.href = "/" + a.text;
  return "elsewhere";
}

function addrGo(a) {
  if (!a) return "bad";
  if (boardId && a.ws !== boardId) return addrElsewhere(a);

  addrShut();
  /* A past lesson is left for every surface but one, because every other
     surface is about the lesson that is open. */
  if (reading && a.surface !== "archive") backToLesson();

  var surface = a.surface;

  if (surface === "workspace") {
    if (!openMap()) {
      addrSaid("↳", "this workspace has no map drawn yet — here is the lesson");
    }
    return addrArrived(a);
  }

  if (surface === "node") {
    var box = null;
    ((mapInfo && mapInfo.nodes) || []).forEach(function (n) {
      if (n.id === a.node) box = n;
    });
    if (!box) return addrDead(a, "that box is not on this map any more");
    if (!openMap()) return addrDead(a, "this workspace has no map to open");
    openWork(box.id, "");
    return addrArrived(a);
  }

  if (surface === "card") {
    var have = false;
    ((lastLive && lastLive.cards) || []).forEach(function (c) {
      if (c.id === a.card) have = true;
    });
    if (!have) {
      return addrDead(a, "card " + a.card
                      + " is not in the lesson that is open");
    }
    addrToCard(a.card);
    return addrArrived(a);
  }

  if (surface === "archive") {
    showSession(a.sitting, function (d) {
      if (!d) {
        addrDead(a, "that sitting is not in this workspace's history");
        return;
      }
      var inIt = false;
      (d.cards || []).forEach(function (c) { if (c.id === a.card) inIt = true; });
      if (!inIt) {
        addrDead(a, "card " + a.card + " is not in that sitting");
        return;
      }
      addrToCard(a.card);
      addrArrived(a);
    });
    return "ok";
  }

  if (surface === "doc") {
    var known = null;
    ((readingInfo && readingInfo.documents) || []).forEach(function (d) {
      if (d.id === a.doc) known = d;
    });
    if (!known) {
      return addrDead(a, "that document is not in this workspace any more");
    }
    openDoc(known.id, known.name, function (got) {
      if (!got) return;              /* `openPaper` has already said why */
      if (!a.page) { addrArrived(a); return; }
      var pages = els.paperPages.querySelectorAll("img");
      if (a.page > pages.length) {
        addrDead(a, known.name + " has "
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

  if (surface === "code") {
    var unit = null;
    ((walkInfo && walkInfo.units) || []).forEach(function (u) {
      if (u.path === a.path) unit = u;
    });
    if (!unit) {
      return addrDead(a, "there is no " + a.path + " in this workspace");
    }
    openPicker("walk");
    /* Chosen, so the one tap left is "start walkthrough". Reopening the picker
       normally starts from what the sitting already covers; an address is a
       person naming one file, which outranks that. */
    reviewPick = [unit.name];
    paintReviewPicker();
    /* NOT `row`: this file already has a top-level `row()` that builds the
       drawer's buttons, and shadowing it inside a function that may one day
       call it is the same trap `paths` and `map` have already sprung here. */
    var unitRow = addrRow(els.reviewList, "data-unit", unit.name);
    if (unitRow && unitRow.scrollIntoView) unitRow.scrollIntoView({ block: "center" });
    addrSaid("↳", a.symbol
      ? "the board cannot open one function on its own yet — this is "
        + unit.short + ", which " + a.symbol + " is in"
      : unit.path + ", ready to walk through");
    return addrArrived(a);
  }

  if (surface === "hw") {
    if ((knownSets || []).indexOf(a.set) < 0) {
      return addrDead(a, "there is no problem set called " + a.set + " here");
    }
    var hw = (lastLive && lastLive.hw) || null;
    /* The problems of a set are only in the payload while that set is the
       sitting. Where they are, an address naming one that is not there is
       dead; where they are not, the set is as far as this can honestly check. */
    if (hw && hw.name === a.set) {
      var found = false;
      (hw.problems || []).forEach(function (p) {
        if (p.label === a.problem) found = true;
      });
      if (!found) return addrDead(a, a.set + " has no problem " + a.problem);
    }
    openContents();
    var srow = addrRow(els.contentsList, "data-set", a.set);
    if (srow) {
      srow.classList.add("here");
      if (srow.scrollIntoView) srow.scrollIntoView({ block: "center" });
    }
    addrSaid("↳", "problem " + a.problem + " of " + a.set
             + " — the board opens a set, not yet one problem inside one");
    return addrArrived(a);
  }

  if (surface === "slate") {
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
   why not. The same lookups `addrGo` makes, against the same payload, so the
   mark on a link and what happens when it is tapped cannot disagree. A
   workspace and a past sitting are not pre-checked: the first always resolves,
   and the second is only answerable by asking the archive. */
function addrMisses(a) {
  var why = "";
  if (!boardId || a.ws !== boardId) return "";   /* another board's to answer */
  if (a.surface === "node") {
    why = "that box is not on this map any more";
    ((mapInfo && mapInfo.nodes) || []).forEach(function (n) {
      if (n.id === a.node) why = "";
    });
  } else if (a.surface === "card") {
    why = "card " + a.card + " is not in the lesson that is open";
    ((lastLive && lastLive.cards) || []).forEach(function (c) {
      if (c.id === a.card) why = "";
    });
  } else if (a.surface === "doc") {
    why = "that document is not in this workspace any more";
    ((readingInfo && readingInfo.documents) || []).forEach(function (d) {
      if (d.id === a.doc) why = "";
    });
  } else if (a.surface === "code") {
    why = "there is no " + a.path + " in this workspace";
    ((walkInfo && walkInfo.units) || []).forEach(function (u) {
      if (u.path === a.path) why = "";
    });
  } else if (a.surface === "hw") {
    if ((knownSets || []).indexOf(a.set) < 0) {
      why = "there is no problem set called " + a.set + " here";
    }
  } else if (a.surface === "slate") {
    why = "there is no page " + a.page + " on the slate";
    ((lastLive && lastLive.slate) || []).forEach(function (p) {
      if (p.page === a.page) why = "";
    });
  }
  return why;
}

/* EVERY ADDRESS WRITTEN INTO THE LESSON, MARKED WHERE IT IS WRITTEN. A dead
   link reads as dead in its own sentence; it never quietly lands somewhere
   near. Gibberish is a third thing again and says so. */
function markAddresses() {
  var links, i, el, a, why;
  try { links = els.cards.querySelectorAll('a[href^="#/w/"]'); }
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

fetch("/health", { cache: "no-store" })
  .then(function (r) { return r.json(); })
  .then(function (h) { boardId = (h && h.id) || ""; })
  .catch(function () {
    /* Then this board cannot tell its own workspace from another's, and an
       address is treated as its own rather than bouncing somebody out of a
       lesson over a request that failed. */
  })
  .then(function () {
    boardIdKnown = true;
    mapLand();
  });

window.addEventListener("hashchange", function () {
  var a = addrParse(window.location.hash || "");
  if (!a) return;               /* not an address; the bar is not ours to mind */
  if (!boardIdKnown) { addrWanted = a; return; }
  addrGo(a);
});


/* --------------------------------------------------------------- contents */
/* A course is chapters and problem sets, and until now the board showed neither:
   the only way to a different chapter was somebody typing `board open` in a
   terminal. Everything listed here is discovered from the repository itself, so
   there is no index to keep in step and nothing that can go stale.

   Opening one files the current lesson away whole -- cards, turns and answers
   together -- so what is being left stays readable under the history button
   rather than being written over by what comes next. */
var contents = { chapters: [], sets: [] };
var planInfo = null;        /* what this project says it is doing next */
var readingInfo = null;     /* and what it can be shown */
var resultsInfo = null;     /* and what its own pipeline produced */
var pastCount = 0;

function row(label, sub, current, go) {
  var b = document.createElement("button");
  b.type = "button";
  b.textContent = label;
  if (sub) {
    var s2 = document.createElement("span");
    s2.className = "sub";
    s2.textContent = "  " + sub;
    b.appendChild(s2);
  }
  if (current) b.classList.add("here");
  b.onclick = go;
  return b;
}

function group(title) {
  var d = document.createElement("div");
  d.className = "group";
  d.textContent = title;
  return d;
}

function openContents() {
  var host = els.contentsList;
  host.innerHTML = "";
  var here = (lastLive && lastLive.state && lastLive.state.chapter) || "";

  if (contents.chapters.length) {
    host.appendChild(group("Chapters"));
    contents.chapters.forEach(function (c) {
      host.appendChild(row(c.label, "", c.label === here, function () {
        els.contents.hidden = true;
        setSitting("lecture", null, c.label);
      }));
    });
  }

  if (contents.sets.length) {
    host.appendChild(group("Problem sets"));
    contents.sets.forEach(function (x) {
      var r = row(x.name, x.rel, currentSet === x.name, function () {
        els.contents.hidden = true;
        setSitting("homework", x.name);
      });
      r.dataset.set = x.name;      /* what an address to a problem lands on */
      host.appendChild(r);
    });
  }

  /* WHAT THIS PROJECT SAYS COMES NEXT, which is a book course's chapter list in
     the only form a project has one. This group is the whole reason a project
     was harder to work in than a course: the drawer used to say "sittings here
     are made as you go", which reads as helpful and means *you decide, at a
     keyboard, every time*. A project does write down what is next -- it just
     does not call it a syllabus and does not keep it in this repository. Tapping
     one opens a lecture labelled with that step, and the tutor is woken having
     already been told which step and where the plan is. */
  if (planInfo && (planInfo.steps || []).length) {
    host.appendChild(group("What's next"));
    planInfo.steps.forEach(function (x) {
      host.appendChild(row(x.label, "", x.label === here, function () {
        els.contents.hidden = true;
        setSitting("lecture", null, x.label);
      }));
    });
    var note = document.createElement("p");
    note.className = "none";
    note.textContent = "from " + planInfo.where;
    host.appendChild(note);
  }

  /* Machinery that already exists, which is most of what has to be understood
     in a project and had nowhere to be taught. */
  if (walkInfo && (walkInfo.units || []).length) {
    host.appendChild(group("Walk through"));
    var scope = walkInfo.scope || [];
    host.appendChild(row(
      scope.length ? "change what this walkthrough covers"
                   : "walk me through some code",
      scope.length ? scope.join(" · ")
                   : walkInfo.units.length + " files",
      sittingKind === "walk",
      function () { els.contents.hidden = true; openPicker("walk"); }));
  }

  /* The documents somebody already wrote about how this works. A deck is often
     the best explanation in the repository and the board could not show a page
     of one, so it was read on a laptop beside a lesson on an iPad. */
  if (readingInfo && (readingInfo.documents || []).length) {
    host.appendChild(group("Read"));
    readingInfo.documents.forEach(function (d) {
      host.appendChild(row(d.name, d.iso || "", false, function () {
        els.contents.hidden = true;
        openDoc(d.id, d.name);
      }));
    });
  }

  /* And what the project PRODUCED. A figure the pipeline wrote had no route to
     the glass at all -- the only one was copying it into the lesson inbox, a
     second copy of a file the next job overwrites. Newest first, because the
     one being asked about is the one that has just changed. It opens in the
     viewer this page owns, not in a tab with no way back out of it. */
  if (resultsInfo && (resultsInfo.figures || []).length) {
    host.appendChild(group("Figures"));
    resultsInfo.figures.forEach(function (f) {
      var sub = f.where ? f.where : (f.iso || "");
      host.appendChild(row(f.name, sub, false, function () {
        els.contents.hidden = true;
        openViewer("/result/" + f.id, f.where ? f.name + " — " + f.where : f.name);
      }));
    });
  }

  if (!contents.chapters.length && !contents.sets.length
      && !(planInfo && (planInfo.steps || []).length)) {
    /* A repository with no book AND no plan. Not an error to report -- it says
       where to look instead. Sittings there are made as they go and stay
       readable under ◷ like any other. */
    host.appendChild(group("This course"));
    var p = document.createElement("p");
    p.className = "none";
    p.textContent = "No chapters, problem sets or task list in this repository, "
      + "so sittings here are made as you go. Each one stays readable under ◷.";
    host.appendChild(p);
  }

  /* A test review is a way around the course too -- it is just one that covers
     several chapters at once instead of opening one. */
  if (reviewInfo && (reviewInfo.units || []).length) {
    host.appendChild(group("Test review"));
    var scope = reviewInfo.scope || [];
    host.appendChild(row(
      scope.length ? "change what this review covers" : "revise for a test",
      scope.length ? scope.length + " chosen"
                   : reviewInfo.units.length + " " + reviewNoun(reviewInfo),
      sittingKind === "review",
      function () { els.contents.hidden = true; openReview(); }));
  }

  host.appendChild(group("Past lessons"));
  if (pastCount > 0) {
    host.appendChild(row("open the history", pastCount + " filed", false, function () {
      els.contents.hidden = true;
      openHistory();
    }));
  } else {
    var q = document.createElement("p");
    q.className = "none";
    q.textContent = "Nothing filed yet.";
    host.appendChild(q);
  }

  els.contents.hidden = false;
}

document.getElementById("btn-contents").onclick = function () {
  if (els.contents.hidden) openContents(); else els.contents.hidden = true;
};
document.getElementById("btn-contents-close").onclick = function () {
  els.contents.hidden = true;
};


/* The overflow menu. Closing on any choice matters more than it looks: on a
   tablet a menu that stays open after a tap is a menu that swallows the next
   one. */
document.getElementById("btn-more").onclick = function (e) {
  e.stopPropagation();
  els.barmenu.hidden = !els.barmenu.hidden;
  if (!els.barmenu.hidden) placeMenu();
};

/* WHERE THE MENU GOES AND HOW MUCH ROOM IT HAS, measured against the glass.

   Reported as "I can't see the refresh button when I tap the '...' menu", and
   then, once it had been capped and made scrollable, as "that isn't scrollable
   -- or at least when I try to scroll it, the main session page behind it is
   what scrolls instead". Two defects, and the second one had two halves.

   The first half is where the element LIVES, and that is fixed in `board.html`:
   it hung inside `#chrome`, which is `position: sticky`, and WebKit does not
   reliably hand a touch drag to a scroller nested in a sticky element.

   The second half is this function, which measured with `window.innerHeight`.
   That is the LAYOUT viewport, and the layout viewport is not what you can see.
   The iPad keyboard comes up and takes half the glass while `innerHeight` does
   not move; a pinch magnifies the page and `innerHeight` does not move. The cap
   was then bigger than the screen, so the last entries were off the bottom AND
   the menu did not overflow its own box -- and a box that does not overflow is
   not a scroller, so iOS correctly gave the gesture to the page. That is both
   halves of the complaint from one wrong number.

   `window.visualViewport` is the honest one, and this file already knows it:
   `panicPlace` is placed from it for exactly this reason. So the menu hangs
   from the real bottom of the chrome stack -- which grows and shrinks with the
   banners in it, a save offer and an export result being most of an inch, and
   both up at the moment somebody goes looking for the reload -- and is capped
   at the room left on the VISIBLE viewport below that. */
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
   landing on this one. Both are read by `typeOut`, which is the only thing that
   can tell a card that answers a send from a card that merely arrived. */
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

/* NOT WHILE THE NIB IS DOWN.

   A payload repaints the whole lesson: the transcript is reconciled, cards are
   laid out, and KaTeX typesets whatever changed. That is a few hundred
   milliseconds of main thread, and the main thread is also what turns pen
   samples into ink -- so a payload landing mid-stroke is felt in the hand as the
   surface going dead for half a second. And payloads land constantly WHILE
   writing, because the writing itself is what produces them: the slate saves,
   the server notices, the hub pushes.

   Reported as: "sometimes when I'm writing on the board, touchscreen response
   sometimes glitches out for half a second, which isn't the worst but is...
   annoying."

   So a payload that arrives with a nib down is held, and the NEWEST one is drawn
   the moment the nib lifts. Only the newest: they are whole pictures of the
   lesson, not increments, so an older one has nothing in it the newer lacks.

   The window is deliberately the stroke itself and not `busy()`, whose tail runs
   for seconds after the last sample -- that tail is right for "may I spend a
   hundred milliseconds encoding a PNG" and much too generous for "may I show
   what just arrived". A card must appear the moment the hand stops, not two and
   a half seconds later. */
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

function connect() {
  if (source) source.close();
  source = new EventSource("/events");
  source.onopen = function () { paintLink(false); };
  source.onerror = function () { paintLink(true); };
  source.onmessage = function (ev) {
    if (!ev.data) return;
    everGotData = true;
    paintLink(false);
    try { renderOrHold(JSON.parse(ev.data)); } catch (e) { /* ignore a torn frame */ }
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
   which question was newest when they went. Going back is a deliberate excursion
   and the tutor asking something NEW ends it -- the same rule `reopenedFor` has
   had from the start, and for the same reason: a request must not outlive what
   it was made for.

   Without the second half of that, going back to an earlier board pinned the
   live surface there for the rest of the sitting. A new question then arrived to
   find the surface parked several cards above it and no page of its own, so it
   got no board at all -- a question posed with nowhere to answer it, which is
   the worst state this board has. Reported from the device the evening the
   boards became reachable enough for anyone to hit it. */
var workingOn = null;
var workingOnAt = null;
/* The board the surface is standing in for, as `render` last worked it out.
   `workingOn` is a request; this is the answer to it, and it is what
   `restoreAnswer` puts under the pen. */
var liveSlot = null;
/* Which slate page belongs to which board.

   A question is not one board. It is a CHAIN of them, and that is what an
   exercise actually looks like: you write, you hand it in, the tutor answers
   underneath, and the next attempt carries on below the answer. Each of those
   attempts is a board of its own -- it stays where it was written, it keeps what
   was on it, and it can still be written on, because going back up an exercise
   to add a line to an earlier attempt is ordinary work.

   It used to be one page per question, and the single board slid down the run to
   sit under the newest card. So the earlier attempts did not persist: there was
   never more than one board per question to persist. Reported from a Galois
   sitting, in these words: "the previous board for this same question that I
   have not yet completed doesn't persist... I want ALL boards to persist and to
   operate independently of each other."

   Independently is the load-bearing word, and it is why a new attempt opens on a
   COPY of the one before it rather than on the same sheet. The working carries
   forward -- what is under the pen is everything written so far, which is what
   a correction needs -- and the board above keeps what it had, for ever, because
   they are two pages from the moment the copy is taken.

   No page is ever destroyed. The surface used to be cleared whenever a new
   question arrived -- with the reasoning that the next answer should not start
   on top of the last one, which is true, and with the consequence that a page of
   somebody's proof was deleted because the tutor asked something else, which is
   not acceptable. Two hours of Exercise 1.3 went that way.

   The record is one entry per BOARD, kept per course because the pages are:

       "<question>#<attempt>": { p: <page index>, a: <card it sits under> }

   `p` is missing on a board nobody has written on yet -- it is cut the moment
   somebody touches it, so a question the student never reached does not leave a
   sheet behind. `a` is where the board sits: the newest board of a question
   floats to the end of that question's run, because an answer belongs under the
   feedback it is answering, and it stops floating the moment it is frozen. */
/* `p` IS A PAGE NUMBER NOW, NOT AN INDEX INTO THE SURFACE'S ARRAY.

   It was an index, and an index is a position in a list this record outlives:
   the list comes back from the server on every reload with only the pages that
   were ever SAVED in it, so one page cut and never written on slid every board
   after it onto its neighbour's sheet. Reported as "none of the boards have my
   preserved written work on them", with the working sitting on disk the whole
   time. `lesson/slate.py` carries the measurements.

   The key is versioned because of it: every record written before this line was
   an index, there is nothing in it that says so, and reading one as a number is
   the same class of mistake in the other direction. A bumped key throws them
   away and `repairPages` builds the mapping back out of the turns on disk,
   which is where the authority always was. */
var PAGES_KEY = "board.pages.n";
var boardPage = {};
var pagesLoaded = false;

function pagesKey() {
  var st = (lastLive && lastLive.state) || {};
  return PAGES_KEY + ":" + (st.course || "?") + ":" + (st.chapter || "-");
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

/* The last board before this one that somebody has actually written on.

   A follow-up question is a new question, so it gets a board of its own and that
   board is blank -- right for a new exercise, wrong three cards into one, where
   the proof being asked about is on the board above and the answer belongs with
   it. The board cannot tell those two apart (a question card is a question card)
   and guessing would be worse than asking: a new exercise opened on a copy of
   the last one is somebody else's proof under your pen, and every board after it
   carries every stroke of the evening. So the working is brought forward by the
   person who knows, in one tap. */
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

/* Bring that working onto this board, as a copy of it.

   A copy, not the same sheet: from here the two go their own ways, which is the
   rule every board on this page follows. Never over ink -- a board with anything
   on it is somebody's work, and this would replace it. */
function carryOver(key) {
  if (!writer || !writer.clone) return;
  var rec = boardPage[key];
  if (!rec || (rec.p !== undefined && writer.inkOn(rec.p) > 0)) return;
  var from = prevInkSlot(key);
  var src = pageOf(from);
  if (src === undefined) return;
  rec.p = writer.clone(src);
  savePages();
  loadedTurn = null;
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

/* Does any OTHER board already own this page?

   One board per page is the rule and nothing enforced it. The slate hands back a
   trailing blank page rather than cutting a new one every time -- right, or
   every board leaves an empty sheet behind it -- but two boards that reach it
   before either is written on both get the same index. From then on they are the
   same sheet: writing on the earlier one changes the later one, which is what it
   looks like from the outside and is exactly what it is. The slate cannot know;
   it deals in ink, not in questions. */
function pageOwnedByOther(n, key) {
  if (n === undefined || !n) return false;
  for (var k in boardPage) {
    if (k !== key && boardPage[k].p === n) return true;
  }
  return false;
}

/* The chain of boards, brought up to date with the transcript.

   A board is frozen -- left exactly where it is, with what is on it -- as soon
   as two things are true of it: what it holds has been handed in, and the tutor
   has written something since. The next attempt then opens on a copy, so the
   working carries forward and the two go their own ways from there.

   Both halves are needed. Freezing on the send alone would cut a board every
   time somebody pressed Send to check their working, and freezing on the
   tutor's card alone would cut one for a hint about working that has not been
   handed in yet. It is the reply to an answer that ends an attempt. */
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
      boardPage[slotKey(q, slotN(key) + 1)] = { p: writer.clone(rec.p), a: end };
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

/* Has the page this board points at stopped being the answer that came off it?

   Fewer strokes than were handed in is the test, and it is the honest one: a
   page can only lose strokes by being cleared, reused or cloned over, and any of
   those means it is somebody else's sheet now. MORE strokes is the ordinary case
   of carrying on writing after sending, and the live page is then the better
   picture -- it holds the answer and the work since.

   Returns the answer that came off it, which is the thing to show and the thing
   to put back. */
function lostAnswer(key, share) {
  if (!writer || !writer.pages || !writer.hasPage) return null;
  var q = slotQ(key);
  var answer = sentAnswers()[q];
  if (!answer) return null;
  var page = pageOf(key);
  /* AND ONLY THE BOARD IT WAS HANDED IN OFF.

     An answer is keyed by QUESTION, and a question has as many boards as it took
     attempts. The next attempt opens on a COPY of the one that was handed in --
     that is what carrying the working forward means -- so it starts life holding
     every stroke of that answer while never having been the sheet the answer came
     off. Ask this of it and the reply is nonsense: erase the copy, which is the
     first thing anybody does with it, and the board concludes its answer has been
     destroyed and hands it back, on a page of its own, under the pen.

     Reported from the iPad, in exactly that shape: "I got a new board to answer
     the next prompt, and I elected to erase my copied over previous board work,
     and started writing new work. Then all of a sudden, the old previous board
     work showed up again and the new work I started on got wiped." Nothing was
     lost -- `adoptInk` cuts a new page rather than writing over one -- but the
     new working was orphaned on a sheet with nothing pointing at it, which from
     behind a pen is the same thing.

     The record says which sheet the answer came off, so the test is whether this
     board is on it. If some OTHER board of this question is, the answer is
     accounted for and this one is a copy: it is the student's, and erasing it
     means what it says. The guard is the same one `repairPages` applies before it
     moves anything -- if a board of the question already holds what the record
     names, there is nothing to repair and nothing to reclaim. Where NO board
     holds it the record has genuinely rotted, and the old behaviour is right. */
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

/* The frozen strokes of an answer, by the URL the turn carries.

   `live/answers/<turn>.json` is written once, beside the picture, and never
   touched again -- so unlike the slate page it came off, it cannot move. It is
   what a past board is DRAWN from, and what comes back under the pen when the
   sheet it was written on has been reused since.

   Fetched once per URL. A failure is remembered as a failure rather than
   retried, because the board falls back to the picture and a board that re-asks
   for a file that is not there on every render is a board that spends the
   evening asking. */
var frozenInk = {};
function frozenFor(url) {
  if (!url) return null;
  if (Object.prototype.hasOwnProperty.call(frozenInk, url)) {
    var have = frozenInk[url];
    return have === "asking" ? null : have;
  }
  frozenInk[url] = "asking";
  fetch(url).then(function (r) { return r.json(); }).then(function (d) {
    frozenInk[url] = (d && d.strokes && d.strokes.length) ? d : null;
    if (lastLive) render(lastLive);
  }).catch(function () { frozenInk[url] = null; });
  return null;
}

/* A board whose sheet no longer holds what was handed in off it, given that
   answer back on a page of its own.

   Without this, touching such a board opened the sheet as it is NOW -- cleared,
   or reused by a later question -- so the working vanished and the pen landed on
   what read as a brand new surface. Reported from the iPad: the boards whose
   colour was wrong were the same boards that "clear everything to be a new
   writing surface" when you write on them, and they are the same boards for the
   same reason: both halves were the frozen answer being shown by a picture
   drawn for somebody else, over a page that had moved on.

   Once per board per sitting, and never over ink: `adoptInk` cuts a new page, so
   the sheet that had been reused keeps whatever is on it and belongs to whoever
   is using it now. */
var reclaimed = {};
/* What the sheet held when its answer was first ruled gone. See below. */
var reclaimFrom = {};
/* ASKED WHEN A BOARD IS OPENED, NOT WHILE SOMEBODY IS SITTING ON IT.

   This is a question about a board you are coming BACK to and finding changed --
   "touching one opened the sheet as it is now, cleared or reused, so an evening's
   working appeared to go". It is not a question about the board under your hand,
   and asking it there is how the answer came back over a fresh start: clear your
   own answer's sheet to write it again, which is an ordinary thing to do, and the
   next render ruled the answer destroyed and handed it back on a page of its own.
   Reported from the iPad alongside the carried-over copy: "I elected to erase my
   ... board work, and started writing new work. Then all of a sudden, the old
   previous board work showed up again and the new work I started on got wiped."

   So the judgement is made once per board per opening. `reclaimSeen` is the slot
   that was live last time round; when it changes, the new one is OWED a
   judgement, and it stays owed until one is actually reached -- the frozen
   strokes have to be fetched first, and a hand has to come off the glass, and
   neither of those is a decision. Once judged, nothing the student then does to
   that sheet re-opens the question. */
var reclaimSeen = null;
var reclaimOwed = null;
function reclaimAnswer(key) {
  if (!writer || !writer.adoptInk || reclaimed[key]) { reclaimOwed = null; return; }
  /* A HALF of what was handed in, where showing the frozen picture asks only for
     one stroke fewer -- and the difference is deliberate. Showing a picture is
     reversible and costs nothing when it is wrong. Moving the page under the pen
     is neither: somebody who sends an answer and then rubs two lines out of it
     is on that sheet, editing it, and cutting a fresh copy from the send would
     orphan the very edit they are making. A cleared or reused sheet holds a
     handful of strokes out of hundreds; an edited one holds nearly all of them.
     Only the first is a board whose answer has gone. */
  var answer = lostAnswer(key, 0.5);
  /* Judged: the answer is where it was handed in, or there is nothing frozen to
     put back. Either way the question is closed until this board is opened
     again. */
  if (!answer || !answer.ink) { delete reclaimFrom[key]; reclaimOwed = null; return; }
  /* A SHEET THAT IS GAINING INK IS A SHEET SOMEBODY IS USING.

     Between ruling the answer gone and being able to act on it there are two
     waits -- the frozen strokes have to be fetched, and a hand has to come off
     the glass -- and a person does not stand still through them. Somebody who
     clears a sheet and starts writing on it has answered the question this was
     about: the sheet is theirs and they are on it. Moving the pen to a fresh
     copy of the send then orphans exactly the working they are in the middle
     of, which is the second half of what was reported.

     So the judgement is made once, against what the sheet held when it was
     first ruled gone, and abandoned if the sheet has grown since. It never
     comes back for that board, because the count it is compared against does
     not rise -- which is right: there is nothing here that has to happen, and
     the frozen answer is still on disk, still drawn on the dormant board, and
     still one tap away. */
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
   this browser has rotted.

   `boardPage` lives in localStorage and there is nothing in a browser that
   can tell a stale entry from a live one -- the pattern this repository keeps
   relearning, one more time: a record with no way to expire. And it CAN rot: an
   evening where the surface was told its page count too early was an evening
   where question after question was refiled against a page it was never written
   on, and the entry outlived the reload that made it.

   The server knows better, and always did. Every answer handed in carries the
   page it was sent from, so for any question that has been sent at all there is
   an authority for where its working is, on disk, surviving this browser
   entirely.

   It is applied conservatively, because the record is not the whole truth: a
   board written on and never sent has no record at all, and a page CLONED out of
   a shared sheet has moved since the send that named it. So the record is taken
   only where the entry in hand is already untrustworthy -- absent, past the end
   of the pages, sharing a sheet with another board, or pointing at a blank page
   when the record points at a written-on one. A healthy mapping is left exactly
   as it is.

   Which board of a question the record is about is not in doubt: an answer is
   versioned rather than re-sent, so a question has one turn and its page is the
   page of the attempt in hand. If any board of that question already holds it --
   they went back and handed in an earlier attempt -- there is nothing to repair
   and nothing to move. */
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
  /* Which question the RECORD says each page was sent for. A board sitting on a
     page that belongs to somebody else's question is wrong on evidence, not on
     suspicion -- and it is the one kind of wrong the conservative tests above
     cannot see, because such an entry looks perfectly healthy: the page exists,
     no other board claims it in this browser, and there is ink on it. It is just
     somebody else's ink.

     Reported from the board, looking back over a lesson: "their recordings are
     out of wack. My writing from one section is wrong and came from a later
     section, vice versa." Both halves of that are this: two boards swapped, each
     looking fine on its own. */
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

/* Every question has a board under it, and one of them is real.

   The board wanted, in the words it was asked for: it should LOOK like there
   are several live infinite canvases on the page. It cannot be several -- a live
   surface is two canvases at device resolution, about seventeen megabytes an
   iPad, and iPadOS answers an exceeded canvas budget with blank canvases or a
   reloaded tab. A dozen of those is not a slow board, it is a board that loses
   your working.

   So there is one live surface and the rest are photographs of themselves,
   drawn by the same paint code with the same paper and the same ink, at CSS
   resolution because nothing is going to be zoomed into them. Touch one and it
   becomes the live one -- including under a pen already coming down, which is
   handed straight through so its first stroke is not eaten by the swap. The
   difference is invisible until you write, which is exactly when it stops
   existing. */
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
    carryOver(key);
    workingOn = key;                 /* carrying it over is asking to write here */
    workingOnAt = lastNewestQ;
    if (lastLive) render(lastLive);
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
  /* The answer each question actually handed in, newest revision.

     A past board used to be a picture of a SLATE PAGE, taken now -- and a slate
     page is live. It gets written on again, cleared, cloned, reused. So a board
     under an old question showed whatever had happened to that sheet since,
     which from the iPad is: "their recordings are out of wack. My writing from
     one section is wrong and came from a later section" and later "the very
     latest few are just repeats of my earliest".

     Measured on this lesson rather than guessed: the answer to question 6 was
     handed in off page 7 with 279 strokes, and page 7 now holds one; question
     7's came off page 9 with 279, and page 9 now holds a different 228. Pages 4
     and 12 are byte-identical. Every FROZEN answer was correct and distinct the
     whole time -- nothing was ever lost -- and the boards were pointing at a
     moving target.

     What was handed in cannot move: it is written once, into live/answers/, and
     never touched again. So a board whose page no longer holds the answer that
     came off it shows the answer instead. */
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
      /* Drawn from the frozen STROKES, by the slate, on the paper in hand.

         It used to be the answer's own PNG, and that file is written for a
         different reader: always dark ink on white, cropped to the writing,
         because its job is to be legible to whatever agent opens it. Among the
         boards it read as exactly what it is -- a white sheet in a run of black
         ones, at a magnification of its own. "The color is inverted", from the
         iPad, mid-proof. The strokes were on disk beside it the whole time, so
         a past board can be drawn by the same code as a live one and is then
         indistinguishable from it, which is the rule every board here follows.

         The picture stays as the fallback for an answer with no frozen strokes
         -- one handed in before they were kept -- because an inverted board
         still shows the working, and a blank one does not. */
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
          frozen.src = drawn || answer.png;
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
/* WHAT THE TURN WAS WOKEN FOR, off the daemon's own record. One value matters
   so far and it is `direction`: the turn a direction change wakes spends its
   first ten seconds writing a card that says it is re-planning, and then several
   minutes reading the plan, rewriting it and redrawing the map. The strip's
   ordinary rule -- a card landed, so the answer is here, so stop talking -- is
   exactly wrong over that card. Reported as: "I got left hanging for a bit while
   it was thinking and modifying the plan." */
var busySignal = "";
var busyTimer = null;
/* WHEN SEND WAS TAPPED, AND WHETHER ANYTHING HAS ANSWERED YET.

   Between the tap and the board saying "the tutor is writing" there is a PNG
   encode, a round trip, the server waking the tutor, and the next payload. On a
   worked page and a busy node that is comfortably a second, and it can be much
   longer. Nothing on the board changed in that gap. Reported: "make the time
   between me hitting 'send' and something else happening more snappy so I don't
   get tempted to double send. If it takes a minute for it to say 'tutor is
   responding', say 'sending to tutor' until that happens. I want immediate
   feedback."

   So the strip that says what the tutor is doing says this too, from the tap
   until the tutor picks it up. It expires: an inbox nobody is reading must not
   leave "sending" on the screen for the rest of the evening. */
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
  /* AND GO AND LOOK AT IT, NOW.

     The strip lives under the writing surface, and at the moment of the tap the
     reader is wherever they finished writing -- halfway up a page of working,
     with the foot of the surface and everything under it off the bottom of the
     glass. So the message was being posted somewhere nobody was looking, and by
     the time `revealSent` brought them down to it -- after the round trip -- the
     tutor had often already reported working, and what they arrived to was "the
     tutor is writing". Reported as: "I want to IMMEDIATELY see a message like
     'sending to tutor' in the time before the 'tutor is writing' message shows
     up." It was there. They were not.

     The landing was always going to happen; this is only it happening on the tap
     rather than on the reply to it. `revealSentSettling` still re-lands once the
     receipt has settled, and still stands down the moment a card arrives. */
  revealSent();
}

/* The newest card's mtime -- a correction to an existing card counts as much as
   a new one, since either way something appeared for them to read. */
/* IS THIS A TURN THAT DOES THE WORK, rather than one that teaches it.

   The four ways of saying so are the four `sense.session_sense` reads, because
   they live in different places and a person taps one without knowing which:
   the aim they chose on the map, a stance chosen for the sitting, a sitting
   whose product is a document, or a repository whose standing answer is `do`.

   The board needs this for one reason and it is the whole of why the strip
   below was wrong: in a doing turn, a card landing does NOT mean the work is
   finished. */
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
  var newest = 0;
  (data.cards || []).forEach(function (c) {
    if (c.mtime > newest) newest = c.mtime;
  });
  return newest;
}

/* NOTHING THE READER CAN BE WAITING ON IS ALLOWED TO BE SILENT.

   This strip used to know two things: the wire (`sending to the tutor`) and the
   turn (`the tutor is writing`). Between them sat every state that actually
   goes wrong, and the strip's answer to all of them was to hide itself:

   - A tutor still coming up. The send lands in the inbox, nothing takes it, and
     after a hundred seconds the strip vanished. A blank space where "sending"
     was is indistinguishable from a send that never left.
   - A turn that FAILED. The daemon writes `last_error` and goes back to
     waiting, so the chrome says "claude listening", the strip goes, and the
     student is looking at their own working with nothing coming and no way to
     know it. "I don't ever want to be left hanging" is this one.
   - A course with no tutor attached at all, where the work is being filed into
     an inbox nobody is reading.

   All three are now the same question -- IS THERE SOMETHING IN THE INBOX THAT
   NOTHING HAS PICKED UP -- and the server answers it off disk (`notes.waiting`),
   which is what makes it survive a reload, a second device and the daemon being
   restarted underneath it. The browser's own `sendingAt` covers only the
   sub-second before the first payload comes back, which is all it was ever
   qualified to talk about.

   The order below is the order of urgency, and it is deliberate: a turn in
   progress beats a failure that is now being retried, which beats work sitting
   unclaimed, which beats the wire. */
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

  /* A FAILED TURN IS NEWS ON ITS OWN, AND CANNOT WAIT ON THE INBOX TO SAY SO.

     `board wait` marks a message read the moment it hands it over, which is
     what consuming it means -- so by the time a turn fails, the message it
     failed on is READ and there is nothing sitting in the inbox to notice. The
     daemon also re-queues it internally rather than marking it unread again.
     So this is asked first and asked independently: the one state where the
     student has handed work in, the tutor took it, and no card is ever coming
     is precisely the state that leaves no trace anywhere else.

     Timed from the failure rather than from the send, because that is the fact
     -- how long ago it fell over -- and it is the one a person can act on. */
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

  /* NEWEST FACT WINS. Somebody who sends again after a failure has made the
     send the newer thing that happened, and going on about the old failure over
     the top of it is the board talking about the past. The other way round -- a
     failure since the last unclaimed send -- and the failure is the news. */
  if (!waiting) return failed;
  if (failed && (st.failure.at || 0) >= (waiting.since || 0)) return failed;
  var held = Date.now() - (waiting.since || 0) * 1000;
  /* The first couple of seconds belong to the wire and to the daemon's quarter
     second poll. Announcing a stall there would make every ordinary send flash
     a warning -- but not at the cost of dropping a failure that is still the
     standing fact about this tutor. */
  if (held < 4000) return failed;
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

/* A daemon's error string is for a log. This is for somebody holding an iPad. */
function failWord(err) {
  var e = String(err || "");
  if (/allowance/i.test(e)) return "its usage allowance has run out here";
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
      : stalledWord(st, data.waiting, data.unsaved || 0);
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
      /* THE LINK IS THE FIRST THING THAT COULD BE WRONG, AND IT IS THE ONE
         THING THE STRIP USED TO BE UNABLE TO SAY.

         "Sending" is a claim about a message being carried, and with the stream
         down nothing is carrying it: the send may never have left, and no
         payload is coming to correct the word. The board it was sent to can go
         down underneath a send -- a restart, a node change, a dropped tailnet
         link -- and what the person saw was "sending to the tutor" for the rest
         of the evening. Reported as: "now 'sending to the tutor' is hanging". */
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
  /* ...AND THAT IS A TEACHING TURN'S RULE TOO.

     In a turn that DOES the work, the card landing is the opposite signal. The
     turn opens with one sentence saying what it is about to do -- so the board
     is not blank while it works -- and then writes code, runs it, and replaces
     that sentence with the report. Hiding the strip when the sentence lands
     takes the indicator away at precisely the moment there is most to say, and
     leaves somebody looking at a one-line card for several minutes with nothing
     on screen saying anything is happening. Reported as: "is claude going to
     town in the background? If so, I'd like an indication that this is what's
     happening on the app."

     So in a doing turn the strip stays for as long as the tutor says it is
     working, and says what kind of work it is.

     A RE-PLANNING TURN IS THE SAME SHAPE, whatever the sitting is. The turn a
     direction change wakes is told, in order: write one sentence so the board is
     not blank, read the plan, rewrite it, redraw the map, then write the report
     over that sentence. Its opening card is a receipt, not an answer, and hiding
     the strip on it leaves the several minutes that follow silent. */
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
    /* WHAT the work is, and only where the sitting has said. A turn that does
       the work is not always a turn that writes code: `doingTurn` is true for a
       paper and for a deck as well, and it is true for a repository whose
       standing answer is `do` without naming any aim at all. Saying "writing
       the code and running it" over a sitting that is doing none of those is a
       sentence about somebody else's evening -- reported, from the wrong board,
       as "that doesn't make much sense as a message". So the aim chooses the
       words and the fallback claims nothing. */
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

/* ------------------------------------------- an answer waiting somewhere else

   THE PROBLEM, in the words it was reported in: "maybe something I give the
   agent to do or think about is going to take a while. I want to be able to go
   into a different section of a project, or a different fucking project
   completely, and put other agents to work on other things while the first one
   is working. We should set up a notification system where if a response that
   takes a while comes back in a session, I'll get notified somewhere in the app
   and can click that notification to take me back to that tutoring session."

   A turn set going in PSYCH-ASR goes on running while its person works in
   Galois-Theory, and until this there was nothing anywhere that said it had
   finished: the only way to find out was to switch back and look, which is the
   one thing somebody doing other work will not do. The server answers the whole
   of the question off the shared filesystem -- see `tutorboard/news.py` -- and
   what is here is the strip and the way back.

   TWO THINGS THIS IS NOT.

   It is not over the lesson. A notification about somewhere else that lands on
   top of the proof somebody is reading has made their evening worse to tell them
   about a card. It is a strip in the chrome, under the bar, with everything else
   that is true but not what they are doing.

   And it is not a queue of things to dismiss. The row goes when the answer is
   read, which means going THERE -- and `✕` mutes this particular answer rather
   than marking it read, because a person who taps it has not read anything. The
   next card in that workspace brings the row back. */

/* Answers the reader has waved away, by workspace and by the answer's own time:
   muting `research/PSYCH-ASR` at 10:04 does not mute the card it writes at 10:30.
   In the page rather than on disk, deliberately -- it is a gesture about this
   sitting, not a fact about the workspace. */
var newsMuted = Object.create(null);

function newsKey(item) {
  return item.id + "@" + Math.round(item.when || 0);
}

/* The way back, and it is the SAME way the front door uses. A workspace other
   than this one is another board on another port, and the installed app has one
   origin baked into it -- so the browser cannot navigate there. The front door
   is what moves the single name, and an address is how it is told where to.

   A LINK, not a button with a handler. It is a link to a place: it belongs in
   the address bar, it can be held down and opened in a tab, and the URL it goes
   to is readable on the row rather than buried in a closure. Its own name is the
   fallback when the grammar cannot spell the workspace -- better a front door
   than a notification that does nothing. */
function newsHref(item) {
  var at = "";
  if (window.Address && item && item.id) {
    at = window.Address.format({ ws: item.id, surface: "workspace" });
  }
  return at ? "/" + at : "/";
}

function newsAgo(when) {
  var ms = Date.now() - (when || 0) * 1000;
  if (ms < 60000) return "just now";
  return longAgo(ms) + " ago";
}

function paintNews(data) {
  if (!els.newsBar) return;
  var items = (data && data.news) || [];
  var show = [];
  items.forEach(function (n) {
    if (!newsMuted[newsKey(n)]) show.push(n);
  });
  /* Three at a time. A fourth is a list, and a list in the chrome is a page
     somebody has to scroll past to reach their own lesson. */
  show = show.slice(0, 3);
  if (!show.length) {
    els.newsBar.hidden = true;
    els.newsList.textContent = "";
    newsShown = "";
    return;
  }
  var sig = show.map(newsKey).join("~");
  els.newsBar.hidden = false;
  els.newsLead.textContent = show.length === 1
    ? "An answer is waiting in another workspace"
    : show.length + " answers are waiting elsewhere";
  /* Rebuilt only when the list has actually changed. This is painted on every
     payload, which is several times a second while a turn runs, and replacing
     the rows under a thumb is a tap that lands on nothing. */
  if (sig === newsShown) return;
  newsShown = sig;
  els.newsList.textContent = "";
  show.forEach(function (n) {
    var row = document.createElement("a");
    row.className = "news-row";
    row.href = newsHref(n);
    row.dataset.ws = n.id;
    var where = document.createElement("span");
    where.className = "news-where";
    where.textContent = n.course || n.repo || n.id;
    var what = document.createElement("span");
    what.className = "news-what";
    /* What it says it is, and failing that where it is. A card with no title is
       ordinary -- most of them have none -- so the chapter is the fallback and
       the plain fact is the last resort. */
    what.textContent = n.title || n.chapter || "the tutor wrote a card";
    var when = document.createElement("span");
    when.className = "news-when";
    when.textContent = newsAgo(n.when);
    var go = document.createElement("span");
    go.className = "news-go";
    go.textContent = "→";
    row.appendChild(where);
    row.appendChild(what);
    row.appendChild(when);
    row.appendChild(go);
    els.newsList.appendChild(row);
  });
}

var newsShown = "";

if (els.newsHide) {
  els.newsHide.onclick = function () {
    ((lastLive && lastLive.news) || []).forEach(function (n) {
      newsMuted[newsKey(n)] = true;
    });
    els.newsBar.hidden = true;
    newsShown = "";
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
    fetch("/seen", { method: "POST", keepalive: true }).catch(function () {});
  } catch (e) { /* offline; the marker is a convenience, not the lesson */ }
}

document.addEventListener("visibilitychange", function () {
  if (!document.hidden) markSeen(true);
});

/* The writing surface used to be capped against the visual viewport here, so
   that pinch-zooming the page could not make it swallow the glass. The cap
   worked and was still wrong: it was a fraction of what could be SEEN, so it
   shrank by exactly the factor the page was magnified by -- and zooming in on
   the writing therefore did nothing at all, because the block got smaller as
   fast as the page got bigger. A surface for reading handwriting that cannot be
   zoomed into is worse than one you can occasionally get lost in.

   The button is the answer instead. It rides on the visual viewport, so it
   cannot be zoomed off the glass, and one tap puts the magnification back. That
   makes zooming safe without making it useless, which is the trade the cap had
   backwards. What is left in the layout is `--gap` on `#writer`: the strip of
   page down each side that is there to put a thumb on. */

/* Whether the surface is shut only because something is still being typed into
   the lesson -- rather than because nothing is owed. `paintBoards` needs the
   difference; see its call. */
var writerHeldShut = false;
/* What the hold was last time the surface was placed, so the trace records the
   change rather than the state four times a second. */
var traceHeld = false;

function placeWriter(owed, questionNode, live, hold) {
  /* A BOARD THAT IS NOT OPEN YET DOES NOT OPEN WHILE A CARD IS STILL TYPING.

     "I want the next board to not show up until all of the tutor response has
      been written", and then again: "no next board showing up until the agent's
      response is rendered."

     Holding a surface WHERE IT IS answers that for a sitting that already has
     one open. It answers nothing at all when there is none -- a tutor that asks
     its first question in the same payload as the answer to the last one opens a
     board, and the board opened the instant the card existed, which is while the
     card was still blank. The objection to hiding it does not apply here: what
     hiding costs is the tool bar going off the bottom of the screen and coming
     back, and a surface that was never open has no tool bar to take away. It
     simply arrives a beat later, under a response that has finished.

     `typeOut` renders once more when the last character lands, which is what
     opens it. */
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
  /* AND IT DOES NOT MOVE UNDER A CARD THAT IS STILL BEING WRITTEN.

     Asked for in these words: "I want the next board to not show up until all of
     the tutor response has been written." It used to come down the instant the
     card existed, which was while the card was one paragraph tall -- so the next
     board appeared directly under the last one and the tutor's answer then
     filled in between them.

     Held where it is, rather than hidden: hiding it would take the tool bar off
     the bottom of the screen and put it back a few seconds later, which is a
     bigger movement than the one being removed. The card types out BELOW it --
     new cards land at the end of the lesson and this surface has no key, so the
     reconcile steps over it -- and the surface comes down under the card in one
     move when the last character lands. `typeOut` renders once more to do it. */
  var host = questionNode && questionNode.parentNode;
  if (hold) {
    /* HELD -- BUT ONLY AGAINST THE CARD THAT IS TYPING.

       "Leave it exactly where it is" was the whole of this, and it left the
       surface above things that belong above IT. The receipt for the answer just
       sent is a turn, not a card: it is never typed, it is the student's own
       working, and the reconcile steps over an unkeyed surface -- so it landed
       BELOW the board it had just been written on and hopped above it a couple
       of seconds later when the reply finished. A shuffle is the thing this hold
       exists to remove, not a thing for it to add.

       So the surface comes down as far as the first card that is still being
       typed and no further. Everything above that -- the receipt, an older card,
       a figure that finished -- reconciles into its proper place immediately;
       only the writing that is still arriving stays below.

       The card says so itself: `typeOut` marks the body it is painting into. */
    var kids = els.cards.children;
    var below = null, passed = false;
    for (var k = 0; k < kids.length; k++) {
      if (kids[k] === els.writer) { passed = true; continue; }
      if (passed && kids[k].querySelector
          && kids[k].querySelector(".body.typing")) { below = kids[k]; break; }
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
          toastSent();
          revealSentSettling();
        },
        /* The tap itself, before the picture is encoded and before the wire is
           touched. The only job here is to put something on the glass on the
           frame the button was pressed. */
        onSending: saySending,
        /* Marks on the lesson are a second thing that can be sent. Ask which,
           but only when both actually exist. */
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
  /* Not until the surface knows what its pages actually are.

     It is usable before the network answers -- one blank sheet, so a stroke made
     in the first half-second is not thrown away -- and for that half-second the
     page count is a lie. Acting on it did two kinds of damage, both silent.
     A question recorded against a page past the end of that lie was ruled gone,
     given a fresh page, and WRITTEN DOWN there: a reload refiled question after
     question onto page 0, and an evening's working ended up on one sheet with
     the mapping to it destroyed. And loading a sent answer onto the stand-in
     page put strokes on it, which is exactly the condition under which the saved
     pages are then refused adoption -- so the real working never arrived at all.

     Waiting costs nothing: `onPages` calls this the moment the count is real. */
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
  fetch(answering.turn.ink).then(function (r) { return r.json(); })
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
/* The student writes on the slate or types, whichever they used last. A typed
   draft is kept per question the way the slate keeps a page per question, so
   flipping between the two does not lose either half. */

var ANSWER_KIND = "answer-kind";
var textDrafts = {};            /* question id -> typed draft */
var textDraftsSeeded = false;
var lastTextQuestion = null;
var textSaveTimer = null;

function answerKind() {
  try {
    if (localStorage.getItem(ANSWER_KIND) === "type") return "type";
  } catch (e) {}
  return "write";
}

function setAnswerKind(kind) {
  try { localStorage.setItem(ANSWER_KIND, kind); } catch (e) {}
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
  fetch("/text/save", {
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
    fetch("/text/save", {
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
  loadedTextTurn = null;    /* a different question is a different answer */
  correctingTurn = null;
  els.saybox.value = textDrafts[answering.question] || "";
  autosize();
}

/* Which surface a question opens on: what the person actually asked for on THIS
   question, else the one it was answered with, else the remembered choice.

   The order matters and it was wrong. A question already answered in ink
   returned "write" from its history whatever the tabs were told, so pressing
   *type* on a question you had written an answer to did nothing at all -- it set
   the remembered kind, repainted, and the history overruled it again on the way
   back. Which is every question worth typing about: you write the proof, the
   tutor asks what you meant by a line of it, and the answer to that is a
   sentence.

   Same shape as `chosen.json` on the other side of the wire: a decision
   outranks an inference drawn from what happens to be on disk, and the decision
   is the one thing the files cannot tell you. */
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
  /* THE BOX BELONGS TO THE QUESTION, NOT TO WHICHEVER TAB IS SHOWING.
     Both of these were asked only when the type half happened to be up, so a
     question that opened on the slate left the previous question's words in the
     box -- and `restoreTextAnswer` refuses a box that is not empty. Asking them
     whenever the panel is open is what makes the two halves behave the same:
     the ink comes back on the slate, the words come back in the box, and
     neither depends on which tab you were last on. Reported as "my typed
     response doesn't get saved on the appearance unlike previously writing
     boards."

     The height is measured only where it can be: `scrollHeight` on a hidden
     textarea is zero, and a box sized while it was hidden stays collapsed when
     the tab brings it out. */
  if (open) { restoreTextDraft(); restoreTextAnswer(); }
  if (typing) autosize();
  else if (writer) requestAnimationFrame(writer.relayout);
}

/* The typed answer already sent against this question, brought back for
   correction -- the typed counterpart of the slate restoring its page of ink.
   Guarded like the ink: the turn just sent is not loaded back over the empty
   box, and newer local typing wins. */
var loadedTextTurn = null;

/* Which typed answer the box is CORRECTING -- as opposed to which one it last
   sent, which is what `loadedTextTurn` remembers so that a send is not
   immediately loaded back over the empty box it left. Two different questions,
   and answering the second with the first is what made every typed answer
   overwrite the one before it. Set here and nowhere else: the box is correcting
   an answer exactly when an answer was put into it. */
var correctingTurn = null;

function restoreTextAnswer() {
  var t = answering.latest;
  if (!t || t.kind !== "text" || t.signal || !t.text) return;
  var id = t.id + ":r" + (t.rev || 1);
  if (id === loadedTextTurn) return;
  /* NEWER TYPING OF THEIR OWN WINS -- AND THE BOX CANNOT SAY WHOSE IT IS.
     This asked whether the box was empty, which is wrong by exactly the margin
     that made it fail: a box still holding words typed against ANOTHER question
     is not a reason to refuse this one its answer. Measured twice in
     `test/mine.js`, and both times the box held a value from an earlier
     question. `textDrafts` is the narrower and right question -- what the person
     typed and did not send, kept per question -- which is the same correction
     `correctingTurn` is on the send side. */
  if ((textDrafts[answering.question] || "").trim()) return;
  loadedTextTurn = id;
  correctingTurn = t.id;
  els.saybox.value = t.text;
  autosize();
}

function autosize() {
  els.saybox.style.height = "auto";
  els.saybox.style.height = Math.min(els.saybox.scrollHeight, 9 * 16) + "px";
}

function say(signal) {
  var text = els.saybox.value.trim();
  if (!text && !signal) return;
  saySending();
  els.saybox.value = "";
  if (answering.question) { textDrafts[answering.question] = ""; }
  autosize();
  /* A CORRECTION REVISES; A SECOND ANSWER IS A SECOND ANSWER.

     This asked `answering.latest` -- the newest turn on this question, of any
     kind -- so EVERY typed answer after the first one overwrote the one before
     it. A question stays open for an evening, and the whole of a Galois sitting
     answered card 0001: three typed answers, hours apart, each a reply to a
     different piece of feedback, and the transcript held the last of them. It
     landed as "when I type a response and send it... it disappears once the
     tutor response comes in", beside the comparison that says what is owed:
     "just like previous writing boards, previous text prompts should be
     preserved too". Ink keeps every attempt -- a board apiece, down the page --
     and typing kept one.

     `correctingTurn` is the narrower question and the right one: is the box
     holding an answer it was HANDED, to fix. Only then is a send a new revision
     of that answer, which is what keeps a correction in the place of the thing
     it corrects. Anything typed into an empty box is new, and new is kept.
     Signals always start fresh. */
  var revise = (!signal && correctingTurn) ? correctingTurn : null;
  return fetch("/say", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: text, signal: signal || null,
                           answers: answering.question, turn: revise })
  }).then(function (r) { return r.json(); }).then(function (data) {
    if (data && data.turn) loadedTextTurn = data.turn + ":r" + (data.rev || 1);
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
  say(null).then(function () {
    /* A typed answer can still have marks sitting on the lesson, and those are
       worth offering too -- the same follow-up the slate send raises. */
    if (haveNotes() && !notesOff()) els.sendwhat.hidden = false;
  });
}

els.sendType.onclick = sendTyped;

els.saybox.addEventListener("input", function () {
  /* Cleared by hand is starting over, not correcting what was in it. */
  if (!els.saybox.value.trim()) correctingTurn = null;
  autosize();
  saveTextDraft();
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

function upload(files) {
  if (!files || !files.length) return;
  var form = new FormData();
  for (var i = 0; i < files.length; i++) form.append("f" + i, files[i], files[i].name);
  fetch("/upload", { method: "POST", body: form }).catch(function () {});
}

els.file.addEventListener("change", function () { upload(els.file.files); els.file.value = ""; });

/* paste an image straight from the iPad clipboard */
document.addEventListener("paste", function (e) {
  if (!e.clipboardData || !e.clipboardData.files || !e.clipboardData.files.length) return;
  upload(e.clipboardData.files);
});

/* drag and drop anywhere.

   Two things make this need more care than the usual depth counter. iPadOS
   raises dragenter for gestures that are not file drags at all -- the
   app-switcher swipe among them -- and it does not reliably raise the matching
   dragleave when the gesture ends outside the page. Left alone, the overlay
   sticks on and covers the lesson.

   So: only open it for a drag that actually carries files, close it on every
   event that means the drag is over, and keep a watchdog for the times none of
   those arrive. The overlay is pointer-events: none as well, so even a stuck
   one is cosmetic rather than a wall across the board. */
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
var THEME_KEY = "board.theme";

function setFontSize(px) {
  px = Math.max(14, Math.min(30, px));
  document.documentElement.style.setProperty("--fs", px + "px");
  try { localStorage.setItem(FS_KEY, String(px)); } catch (e) {}
}
function currentFontSize() {
  var v = parseInt(getComputedStyle(document.documentElement).getPropertyValue("--fs"), 10);
  return isNaN(v) ? 18 : v;
}
function applyTheme(mode) {
  document.body.dataset.mode = mode;
  syncSystemTheme();
  try { localStorage.setItem(THEME_KEY, mode); } catch (e) {}
}
function syncSystemTheme() {
  var dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.body.classList.toggle("sys-dark", dark);
}

document.getElementById("btn-bigger").onclick = function () { setFontSize(currentFontSize() + 1); };
document.getElementById("btn-smaller").onclick = function () { setFontSize(currentFontSize() - 1); };
document.getElementById("btn-theme").onclick = function () {
  var order = ["auto", "light", "dark"];
  var next = order[(order.indexOf(document.body.dataset.mode) + 1) % 3];
  applyTheme(next);
};
document.getElementById("btn-print").onclick = function () { window.print(); };
/* HOW MUCH IS ON THE LIVE SURFACE, for the photograph.

   `shot.js` skips the live board when nothing has been written on it -- a foot
   of blank dark paper as the last page of a document somebody is emailing to
   their professor reads as a document that went wrong -- but working drawn and
   not yet sent is the student's and belongs in it. `strokes()` is the same
   question Send already asks before it hands the tutor an empty sheet.

   Set HERE, at the top level, and not where the slate is mounted: `#writer` is
   static markup in the page and the slate is mounted into it lazily, so the
   surface is on the glass and in the export long before there is anything to
   ask. Set from inside the mount, this never ran at all and every photograph
   ended with a blank page.

   No writer mounted is nothing written. A writer that cannot answer is kept --
   "I could not tell" must never be the reason an evening's unsent working is
   left out of the record. */
if (window.TutorShot) {
  window.TutorShot.liveInk = function () {
    if (!writer || !writer.strokes) return 0;
    try { return writer.strokes(); } catch (e) { return 1; }
  };
}

/* Three controls, one document, and none of them navigates this window. */
els.pushedGet.onclick = function (e) { saveCopy(bannerKind, e.currentTarget); };
els.pushedView.onclick = function () { openPaper(bannerKind); };
if (els.paperInk) {
  els.paperInk.onclick = function () {
    setAnnotating(!(window.Annotate && window.Annotate.isOn()));
    paintKeep();
  };
}

/* ------------------------------------------------- keeping what was written */

/* Ink on the document that is open, counted off the annotation store. The keys
   are the ones `openPaper` put on the page boxes, so this asks the same
   question the burner will ask on the server: is there anything on this
   document at all. */
function inkOnPaper(kind) {
  if (!kind || !window.Annotate) return 0;
  var ident = kind.indexOf("doc/") === 0 ? kind.slice(4) : kind;
  var prefix = "doc/" + ident + "/p";
  return window.Annotate.marked().filter(function (id) {
    return id.indexOf(prefix) === 0;
  }).length;
}

/* The button appears when there is something to keep and goes away when there
   is not. Offering it over a clean document would be offering to write a file
   identical to the one already there. */
function paintKeep() {
  if (!els.paperKeep) return;
  var n = paperOpen ? inkOnPaper(paperOpen) : 0;
  els.paperKeep.hidden = !n;
  els.paperKeep.textContent = n === 1 ? "keep writing (1 page)"
                                      : "keep writing (" + n + " pages)";
}

function closeKeep() { if (els.keepwhat) els.keepwhat.hidden = true; }

/* The outcome, in the viewer's own subtitle, which is where this panel already
   says how many pages a document has. Not `paperSay`: that one replaces the
   pages with a message, and the pages are what somebody is looking at. */
var keepSaidTimer = null;
function keepSaid(text) {
  if (!els.paperSub) return;
  var was = els.paperSub.dataset.was || els.paperSub.textContent;
  els.paperSub.dataset.was = was;
  els.paperSub.textContent = text;
  clearTimeout(keepSaidTimer);
  keepSaidTimer = setTimeout(function () {
    els.paperSub.textContent = els.paperSub.dataset.was || "";
    delete els.paperSub.dataset.was;
  }, 4000);
}

function keepWriting(mode) {
  closeKeep();
  var kind = paperOpen;
  if (!kind) return;
  if (mode === "none") {
    /* Answered here as well as on the server, so that the one choice which
       writes nothing also costs nothing -- no request, no page drawn, and the
       marks left exactly where they are. */
    keepSaid("Kept on the board. Nothing written to a file.");
    return;
  }
  els.paperKeep.disabled = true;
  var was = els.paperKeep.textContent;
  els.paperKeep.textContent = "writing…";
  fetch("/annotate/burn", {
    method: "POST", credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind: kind, mode: mode })
  }).then(function (r) { return r.json(); }).then(function (got) {
    els.paperKeep.disabled = false;
    els.paperKeep.textContent = was;
    if (!got || !got.ok) {
      keepSaid((got && got.detail) || "That did not work.");
      return;
    }
    keepSaid(got.detail || "Saved.");
    /* The pages under the viewer are now a render of a file that has changed,
       so the one that was overwritten is reopened rather than left showing the
       version from before the ink went in. */
    if (got.mode === "same") openPaper(kind, els.paperName.textContent);
  }).catch(function () {
    els.paperKeep.disabled = false;
    els.paperKeep.textContent = was;
    keepSaid("The board did not answer.");
  });
}

if (els.paperKeep) {
  els.paperKeep.onclick = function () {
    if (!els.keepwhat) return keepWriting("new");
    els.keepwhat.hidden = false;
  };
}
if (els.keepwhat) {
  document.getElementById("keep-same").onclick = function () { keepWriting("same"); };
  document.getElementById("keep-new").onclick = function () { keepWriting("new"); };
  document.getElementById("keep-none").onclick = function () { keepWriting("none"); };
}

els.paperGet.onclick = function (e) { saveCopy(paperOpen, e.currentTarget); };
document.getElementById("paper-close").onclick = closePaper;
document.getElementById("btn-papers").onclick = openPapers;
/* A PAGE, so it is a navigation rather than a panel -- and a plain one, the way
   the slate is: the lesson is files and is still here when you come back, and
   nothing on the library page can change it. */
document.getElementById("btn-library").onclick = function () {
  window.location.href = "/library";
};


/* --------------------------------------- putting one to work somewhere else */
/* THE OTHER HALF OF THE SENTENCE THE NEWSBAR ANSWERS. Asked for in these words:
   *"I want to be able to go into a different section of a project, or a
   different fucking project completely, and put other agents to work on other
   things while the first one is working."* The bar at the top of the page is how
   it comes back, hours later, on whichever board is open then. This is how it
   goes out, from the board you happen to have in front of you, without leaving
   the lesson you are in the middle of.

   A PANEL RATHER THAN A PAGE, deliberately, and the opposite choice to the
   library's: nothing here touches this workspace. It hands another one a job and
   closes, and the lesson behind it is exactly where it was.

   The list is every workspace this machine has -- `/atlas.json`, which is a
   directory walk rather than a registry, so a host with half the tree checked
   out offers half of it and no list anywhere has to be edited. */
var elsewhereList = null;       /* the workspaces, once asked for */
var elsewherePick = null;       /* which one, by its bare directory name */
var elsewhereAgent = null;      /* and who, or nothing for whatever is there */

function openElsewhere() {
  els.elsewhere.hidden = false;
  els.elsewhereSaid.textContent = "";
  els.elsewhereSaid.classList.remove("bad");
  paintElsewhere();
  if (elsewhereList) return;
  fetch("/atlas.json").then(function (r) { return r.json(); })
    .then(function (got) {
      elsewhereList = (got && got.workspaces) || (got && got.courses) || [];
      paintElsewhere();
    })
    .catch(function () {
      els.elsewhereSaid.textContent = "could not read what this machine has";
      els.elsewhereSaid.classList.add("bad");
    });
}

function paintElsewhere() {
  var host = els.elsewhereList;
  host.textContent = "";
  if (!elsewhereList) {
    var wait = document.createElement("div");
    wait.className = "group";
    wait.textContent = "reading the tree\u2026";
    host.appendChild(wait);
  } else {
    var family = "";
    elsewhereList.forEach(function (w) {
      /* Not the one you are looking at. Handing this board a job is what the
         box you are already in is for. */
      if (w.current) return;
      if ((w.family_name || w.family || "") !== family) {
        family = w.family_name || w.family || "";
        var head = document.createElement("div");
        head.className = "group";
        head.textContent = family || "workspaces";
        host.appendChild(head);
      }
      var b = document.createElement("button");
      b.type = "button";
      if (w.repo === elsewherePick) b.className = "on";
      var name = document.createElement("span");
      name.textContent = w.course || w.repo;
      var where = document.createElement("span");
      where.className = "where";
      /* What is already happening there, because handing a job to a workspace
         mid-lesson is a different thing from handing one to an idle box. */
      where.textContent = w.chapter || "";
      b.appendChild(name);
      b.appendChild(where);
      b.onclick = function () { elsewherePick = w.repo; paintElsewhere(); };
      host.appendChild(b);
    });
  }

  /* And who. Empty means "whatever is listening there, or whatever that
     workspace resolves to" -- which is the honest default, because a workspace
     may already have a tutor and a start against one is a no-op that says so. */
  var who = els.elsewhereWho;
  who.textContent = "";
  var have = (assistants && assistants.agents || []).filter(function (a) {
    return a.headless && !a.missing;
  });
  if (have.length > 1) {
    var lead = document.createElement("span");
    lead.textContent = "who:";
    who.appendChild(lead);
    [null].concat(have).forEach(function (a) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = a ? a.name : "whatever is there";
      if ((a && a.name) === elsewhereAgent) b.className = "on";
      if (a && a.exclusive) {
        b.title = "one sitting at a time — " + a.exclusive;
      }
      b.onclick = function () {
        elsewhereAgent = a ? a.name : null;
        paintElsewhere();
      };
      who.appendChild(b);
    });
  }
  els.elsewhereGo.disabled = !elsewherePick || !els.elsewhereTask.value.trim();
}

els.elsewhereTask.addEventListener("input", function () {
  els.elsewhereGo.disabled = !elsewherePick || !els.elsewhereTask.value.trim();
});

els.elsewhereGo.onclick = function () {
  if (!elsewherePick || !els.elsewhereTask.value.trim()) return;
  els.elsewhereGo.disabled = true;
  els.elsewhereSaid.classList.remove("bad");
  els.elsewhereSaid.textContent = "starting it\u2026";
  fetch("/elsewhere", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo: elsewherePick, agent: elsewhereAgent,
                           task: els.elsewhereTask.value.trim() })
  }).then(function (r) { return r.json(); }).then(function (got) {
    /* A REFUSAL IS AN ANSWER AND IT GOES ON THE GLASS. One colibri sitting at a
       time machine-wide, and cards that must not be committed: both are refused
       by name, both name the workspace or the line that changes it, and neither
       is any use in a log. */
    if (!got || got.ok === false) {
      els.elsewhereSaid.textContent = (got && got.error)
        || "that could not be started";
      els.elsewhereSaid.classList.add("bad");
      els.elsewhereGo.disabled = false;
      return;
    }
    els.elsewhereTask.value = "";
    els.elsewhere.hidden = true;
  }).catch(function () {
    els.elsewhereSaid.textContent = "the board did not answer";
    els.elsewhereSaid.classList.add("bad");
    els.elsewhereGo.disabled = false;
  });
};

document.getElementById("btn-work-elsewhere").onclick = openElsewhere;
document.getElementById("elsewhere-close").onclick = function () {
  els.elsewhere.hidden = true;
};
/* Escape leaves the document, the way it leaves the picture viewer. A panel
   that covers the whole glass needs more than one way out of it. */
document.addEventListener("keydown", function (e) {
  if (e.key !== "Escape") return;
  if (els.map && !els.map.hidden) closeMap();
  else if (els.paper && !els.paper.hidden) closePaper();
  else if (els.papersPanel && !els.papersPanel.hidden) els.papersPanel.hidden = true;
});
document.getElementById("btn-papers-close").onclick = function () {
  els.papersPanel.hidden = true;
};
document.getElementById("btn-export").onclick = function () { doExport("lesson"); };
document.getElementById("btn-export-all").onclick = function () { doExport("all"); };
document.getElementById("btn-export-hw").onclick = doExportHomework;
/* WHAT JUST HAPPENED, read on the device that saw it. Built only when it is
   opened: the whole design of the buffer is that it costs nothing until then. */
function paintTrace() {
  var host = document.getElementById("trace-list");
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
     question before it is read line by line. A stall is the hold letting go
     while a card was still painting; a skip is a card that never held at all. */
  var stalls = traceLog.filter(function (e) { return e.what === "stall"; }).length;
  var skips = traceLog.filter(function (e) { return e.what === "skip"; }).length;
  document.getElementById("trace-said").textContent =
      stalls ? stalls + " stall(s): the hold let go while a card was still being "
                      + "painted, so the next board came down early."
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
  var text = traceLog.map(function (x) {
    return x.at + "\t" + x.what + "\t" + (x.of ? traceSay(x.of) : "");
  }).join("\n");
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
  els.carry.onclick = function () { carryOver(liveSlot); };
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

document.getElementById("btn-scratch").onclick = function () { els.scratch.hidden = !els.scratch.hidden; };
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

   A pinch-zoomed page has no reverse gear that can be relied on: the writing
   surface is as wide as the glass by design, so at any real magnification it
   covers everything there was to pinch on, and it swallows touches because a
   pen stroke is a touch. The first answer was to cap the surface against what
   could be seen, and that made zooming into the writing pointless -- the block
   shrank as fast as the page grew. So the surface is left alone and this is the
   way back instead: one tap puts the magnification where it started.

   Where the stack sits, how it is dragged, and what the first tap does are all
   in `recentre.js`, because the front door has the same two ways of being lost
   and needed the same answer. What is here is which buttons this page has and
   what the ones under the first one do.

   Four, in order down the glass:

     #panic     the page's own magnification, put back. The one that is dragged.
     #findink   the view, put back over the writing. A surface with a zoom of
                its own that `#panic` knows nothing about.
     #mapback   the same, for the map of this workspace -- which is a plane with
                its own pan and zoom, covers the whole glass, and until now was
                painted OVER the way out of both.
     #redirect  the way out of the whole plan. The only one that changes what
                the work is rather than where you are looking at it from. */
function panicSoon() { if (window.Recentre) window.Recentre.soon(); }
function panicPlace() { if (window.Recentre) window.Recentre.place(); }
function panicRemeasure() { if (window.Recentre) window.Recentre.remeasure(); }

if (els.panic && window.Recentre) {
  window.Recentre.mount({
    key: "board.panic",
    buttons: [
      { el: els.panic },
      { el: els.findink, onTap: function (el) {
          if (!writer || !writer.fitInk) return;
          writer.fitInk();
          window.Recentre.flash(el);
        } },
      /* THE MAP IS A PLANE, AND A PLANE CAN BE PANNED INTO NOTHING.

         Its own ways back -- the ⤢ in the map's head, and the fit it opens on
         -- are page chrome, and page chrome is exactly what a pinch pans off
         the glass. So the map got the same treatment the writing surface
         already had: a button in the stack that puts the picture back where it
         opens, at the size it opens at, with the top of it on screen. */
      { el: els.mapback, onTap: function (el) {
          if (els.map && els.map.hidden) return;
          mapView.held = false;
          mapFit();
          mapRemember();
          window.Recentre.flash(el);
        } },
      /* Its tap is registered here rather than as a `click` listener of its
         own, because `Recentre` has to tell a tap from a press-and-hold to move
         the button -- two listeners would fire one after the other. */
      { el: els.redirect, w: 96, onTap: function () {
          if (els.steer.hidden) steerOpen(); else steerShut();
        } },
    ],
  });
}


/* ------------------------------------------------ changing the direction */
/* The plan was wrong, and saying so is one tap from wherever they are.

   Everything this does is on the server -- `/direction` writes it down, files
   the lesson away, and replaces the running assistant, which is the half no
   prompt can do. What is here is the sheet, and the sheet's whole job is to say
   what is about to happen BEFORE it happens: four irreversible-looking things at
   once, and somebody who taps it not knowing that is somebody who never taps it
   again.

   It does not ask "are you sure". The confirmation is the sentence they have to
   write. */
function steerOpen() {
  var now = (lastLive && lastLive.direction) || null;
  if (now && now.text) {
    els.steerNow.hidden = false;
    els.steerNow.textContent = "In force" + (now.when ? " since " + now.when : "")
      + ":\n" + now.text;
  } else {
    els.steerNow.hidden = true;
    els.steerNow.textContent = "";
  }
  els.steer.hidden = false;
  steerReady();
  /* Not on a tablet: focusing raises the keyboard over the sheet before they
     have read what it says. They tap the box when they are ready to write. */
  if (!("ontouchstart" in window)) {
    try { els.steerBox.focus(); } catch (e) {}
  }
}

function steerShut() {
  els.steer.hidden = true;
}

/* Nothing to send until there is a sentence. A direction of "" would archive the
   lesson and wake a tutor with nothing to act on. */
function steerReady() {
  els.steerGo.disabled = !els.steerBox.value.trim();
}

function steerSend() {
  var text = els.steerBox.value.trim();
  if (!text) return;
  els.steerGo.disabled = true;
  els.steerGo.textContent = "changing…";
  /* NOT SILENT WHILE IT HAPPENS. Everything this tap sets off is on the server
     and none of it is quick: the lesson is filed, a new sitting is opened, and
     the running tutor is stopped and another started in its place. The sheet
     shuts, the board comes back empty because the old lesson has just gone, and
     until the new tutor writes its first card there is nothing on the glass at
     all. Reported as: "I did get a response, but I had to wait a bit and it
     didn't give me any kind of 'tutor is working' visual confirmation — I was
     left hanging."

     The strip already exists for exactly this and the direction change was the
     one send that never lit it. Said on the tap rather than on the reply, for
     the same reason the ordinary send is. */
  saySending("changing direction — replacing the tutor");
  fetch("/direction", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: text })
  }).then(function (r) { return r.json(); }).then(function (data) {
    els.steerGo.textContent = "change direction";
    if (!data || !data.ok) {
      sendingAt = 0;
      sendingWord = "";
      if (lastLive) paintBusy(lastLive);
      steerReady();
      return;
    }
    els.steerBox.value = "";
    steerShut();
    /* Back to the lesson, whatever was over it. The board it comes back to is
       empty for a moment -- the old lesson has just been filed -- and then the
       new tutor writes into it. */
    addrShut();
  }).catch(function () {
    els.steerGo.textContent = "change direction";
    sendingAt = 0;
    sendingWord = "";
    if (lastLive) paintBusy(lastLive);
    steerReady();
  });
}

/* `#redirect`'s tap is wired where the stack is mounted, at the top of this
   file: every button up there can also be pressed and held to move the trio, so
   a second listener here would fire alongside it. */
if (els.steerBox) {
  els.steerBox.addEventListener("input", steerReady);
  els.steerBox.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      steerSend();
    }
  });
}
if (els.steerGo) els.steerGo.onclick = steerSend;
if (els.steerClose) els.steerClose.onclick = steerShut;
if (els.steerCancel) els.steerCancel.onclick = steerShut;
window.addEventListener("scroll", function () {
  /* `following` reads a rectangle, which forces layout, and this fires for
     every frame of a flick. It is only ever asked while there is a button to
     put away. */
  if (els.jump.hidden) return;
  if (following()) els.jump.hidden = true;
});
if (window.matchMedia) {
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", syncSystemTheme);
}

try {
  var savedFs = localStorage.getItem(FS_KEY);
  if (savedFs) setFontSize(parseInt(savedFs, 10));
  applyTheme(localStorage.getItem(THEME_KEY) || "auto");
} catch (e) { applyTheme("auto"); }

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
  /* Swiping out of an installed iOS app and back in RESUMES it -- the document
     is restored from memory and never re-executes. Without an explicit check,
     a fixed bug stays on screen until the app is force-quit, which is not
     something anyone should have to know. So: ask for an update every time the
     app comes back to the foreground, and take a new worker when there is one.

     BUT NEVER OUT FROM UNDER SOMEBODY WHO IS READING IT.

     Reported from the iPad: "there are a few times when after I sent a response,
     the whole screen went white, and then the page reloaded with the tutor
     response and all prior responses collapsed (though reachable) and all prior
     boards only yielding the frozen canvas of my work." Every part of that is
     one `location.reload()`, fired the instant a new service worker claimed the
     page, with no regard for what the page was in the middle of. A reload is
     cheap for the code and expensive for the person: the scroll position goes,
     every card folds back to how it renders on a first visit, the live surface
     is replaced by the picture of the last thing sent, and there is a white
     flash in the middle of a proof. And a new worker arrives at a moment nobody
     chose -- an update is asked for on every return to the foreground, and
     sending a response is exactly when an app comes back to the foreground.

     So a new worker is now NEWS, not an event. Taken at once when the page is
     hidden, because then it costs nothing and the app is on the new code the
     moment it is picked up again. Offered, otherwise, in a strip that says what
     it is -- so somebody who wants the fix now can have it, and somebody in the
     middle of an exercise is not interrupted by one. And never while there is
     ink the disk has not been told about, whichever way it is taken. */
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
