/* ==========================================================================
   meeting.js -- the one meeting deck, read on the glass and marked up on it.

   The library's reader over a document about several workspaces. There is
   one deck, it is replaced rather than versioned, and it is in no workspace's
   library: it is written in its host's `writeups/meeting/`, and
   `meetings/meeting.json` at the root says where, because in a library ink
   would be a revision filed under one project.

   Four rules, and the last is the one the whole page exists for:

     1. THE SAME READER. Page images drawn by the machine holding the PDF, the
        same `.lib-page` boxes, the same `data-ann` anchors, the same pen out
        of `annotate.js`. What differs is only how the file was found.
     2. NO NAME GOES OVER THE WIRE. There is one deck, so `/meeting/view`
        takes no argument at all. Nothing here builds a path and nothing here
        names a document.
     3. EVERY SLIDE SAYS WHOSE IT IS. Every frame names its workspace, a
        project gets as many as it needs, and the caption under each page
        names it -- because the page is how a mark finds its project, and
        marking the wrong slide has to be visibly the wrong slide rather than
        silently the wrong project.
     4. A MARK IS DIRECTION, NOT FEEDBACK. It never goes to
        `/library/feedback`, which would spend a turn fixing the slides. It
        goes to `/meeting/direction`, which wakes one turn per marked
        workspace to PROPOSE what to do next, and applies nothing.
   ========================================================================== */
(function () {
"use strict";

var els = {};
[
  "deck-back", "deck-count",
  "reader-name", "reader-sub", "reader-pen", "reader-close", "reader-said",
  "reader-kept", "reader-rebuilt",
  "reader-pages", "reader-zoom", "deck-send", "deck-pdf",
  "note", "deck-ask-list", "deck-ask-said", "deck-ask-cancel", "deck-ask-go",
  "deck-check", "deck-check-head", "deck-check-list",
].forEach(function (id) {
  els[id.replace(/-(\w)/g, function (_, c) { return c.toUpperCase(); })] =
    document.getElementById(id);
});

/* The theme, the same three states the board keeps and in the same key, so a
   page opened from the front door is the colour the front door was. */
function syncSystemTheme() {
  var want = localStorage.getItem("board-theme") || "auto";
  var dark = want === "dark" || (want === "auto"
    && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", !!dark);
}
syncSystemTheme();
if (window.matchMedia) {
  try {
    window.matchMedia("(prefers-color-scheme: dark)")
      .addEventListener("change", syncSystemTheme);
  } catch (e) { /* older WebKit; the initial state is still right */ }
}

var pagesOf = {};        /* page number -> workspace id */
var names = {};          /* workspace id -> the name it is drawn under */
var openPages = 0;
var openBuild = null;    /* the build on the glass: `got.build` */
var openDeck = null;     /* which deck it is: `got.deck` */

/* ------------------------------------------------------------- the pages */
function load() {
  els.readerSub.textContent = "drawing the slides…";
  fetch("/meeting/view", { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (got) { paint(got || {}); })
    .catch(function () {
      els.readerSub.textContent = "The board is not answering.";
    });
}

function paint(got) {
  if (!got.ok) {
    els.readerSub.textContent = got.detail || "The slides could not be drawn.";
    els.readerPages.innerHTML = "";
    openPages = 0;
    openBuild = null;
    openDeck = null;
    paintCheck({});
    paintRebuilt(null);
    paintPen();
    paintSaid();
    paintKept();
    /* A deck being written is watched, not left: the page draws it when it
       has been built and read back. */
    if (got.why === "being written") setTimeout(load, 15000);
    return;
  }
  pagesOf = got.pages_of || {};
  names = got.names || {};
  openPages = (got.pages || []).length;
  els.readerSub.textContent = openPages
    + (openPages === 1 ? " slide" : " slides")
    + (got.period ? " · " + got.period : got.since ? " · " + got.since : "");
  els.deckCount.textContent = Object.keys(pagesOf).length
    + " project" + (Object.keys(pagesOf).length === 1 ? "" : "s");

  els.readerPages.innerHTML = "";
  (got.pages || []).forEach(function (url, i) {
    var n = i + 1;
    var fig = document.createElement("figure");
    fig.className = "lib-page";
    fig.setAttribute("data-page", String(n));
    /* THE ANCHOR, and it is the tail of a §2.1 address. Ink is stored in
       fractions of this box rather than in page pixels, so it is in the same
       place after a rotation or a zoom. `meeting.ANN_IDENT` is the other half
       of this string and is a constant for the same reason: there is one
       deck, so there is one ident. */
    fig.dataset.ann = "doc/meeting/p" + n;
    /* A page, so its ink zooms with it (`annotate.js`, `PAGE_REF`). */
    fig.setAttribute("data-ann-page", "");
    var img = document.createElement("img");
    img.src = url;
    img.alt = "slide " + n;
    img.loading = i < 2 ? "eager" : "lazy";
    fig.appendChild(img);
    var cap = document.createElement("figcaption");
    /* WHOSE SLIDE THIS IS. The page is how a mark finds its project, so the
       page says which project before anybody draws on it. */
    cap.textContent = pagesOf[String(n)]
      ? n + " · " + (names[pagesOf[String(n)]] || pagesOf[String(n)])
      : n + " · every project: a mark here goes nowhere";
    fig.appendChild(cap);
    els.readerPages.appendChild(fig);
    if (window.Annotate) {
      window.Annotate.attach(fig);
      /* A picture has no height until it has decoded, and a layer sized
         against a zero-height box covers nothing. */
      img.addEventListener("load", function () { window.Annotate.redrawAll(); });
    }
  });
  if (window.Annotate) window.Annotate.load(got.ink || {});
  /* THE BUILD ON THE GLASS, handed back with every save of this deck's ink
     -- and the flag, when ink on it was drawn on another. */
  openBuild = got.build || null;
  openDeck = got.deck || null;
  paintRebuilt(got.rebuilt || null);
  paintCheck(got.unsupported || {});
  paintPen();
  paintSaid();
  paintKept();
}

/* INK KNOWS ITS BUILD. A new deck clears the old one's ink, so this is only
   ever a deck recompiled in place: its slides moved under the marks, and a
   mark on page 4 may now be on another project's frame. */
function paintRebuilt(flag) {
  if (!els.readerRebuilt) return;
  if (!flag) { els.readerRebuilt.hidden = true; return; }
  els.readerRebuilt.hidden = false;
  els.readerRebuilt.textContent = "These marks were drawn on the "
    + (flag.when || "an earlier") + " build; the deck has been rebuilt since, "
    + "so check each one is still on the slide it was meant for.";
}

/* ---------------------------------------------------- what to check first */
/* THE SIDECAR, ON THE PAGE. A number no source gives, a figure the board did
   not copy, a plan heading copied as the plan types it: each is listed with
   the slide it is on, so it is checked before the meeting rather than found
   in it. */
function paintCheck(u) {
  var rows = [];
  (u.numbers || []).forEach(function (x) {
    rows.push("slide " + x.frame + (x.title ? " (" + x.title + ")" : "")
              + ": " + x.value + " is in no source — “" + x.context + "”");
  });
  (u.figures || []).forEach(function (x) {
    rows.push(x.file + " was not copied from any project's results");
  });
  (u.internal || []).forEach(function (x) {
    rows.push("“" + x.heading + "” is a plan heading, copied as the plan types it");
  });
  els.deckCheckList.innerHTML = "";
  rows.forEach(function (t) {
    var li = document.createElement("li");
    li.textContent = t;
    els.deckCheckList.appendChild(li);
  });
  els.deckCheckHead.textContent = rows.length + (rows.length === 1
    ? " thing on this deck is" : " things on this deck are")
    + " not in any source — check before the meeting";
  els.deckCheck.hidden = !rows.length;
}

/* ------------------------------------------------------------- the marks */
/* WHICH WORKSPACES ARE MARKED, off the store rather than off the server: the
   pen is in this tab and a round trip behind it would leave somebody who has
   just drawn a ring looking at a dead button. */
function markedWorkspaces() {
  if (!window.Annotate) return { ws: [], orphans: [] };
  var seen = {}, out = [], orphans = [];
  window.Annotate.marked().forEach(function (key) {
    var m = /^doc\/meeting\/p(\d+)$/.exec(key);
    if (!m) return;
    var id = pagesOf[m[1]];
    if (!id) { orphans.push(Number(m[1])); return; }
    if (seen[id]) return;
    seen[id] = true;
    out.push(id);
  });
  return { ws: out, orphans: orphans };
}

function paintSaid() {
  var found = markedWorkspaces();
  var said = [];
  if (found.ws.length) {
    said.push("Marked on " + found.ws.map(function (id) {
      return names[id] || id;
    }).join(", ") + ".");
    said.push("Sending asks each of them to PROPOSE a new direction on its own "
              + "board. Nothing is applied.");
  } else if (!openPages) {
    said.push("There is no deck. Make one from the front door.");
  } else {
    said.push("Draw on a project's slide and it becomes that project's "
              + "direction — not a note about the slide.");
  }
  if (found.orphans.length) {
    /* THE TITLE SLIDE BELONGS TO NOBODY, and a mark there has nowhere to go.
       Said here rather than silently dropped at the far end: it is on the
       glass, and somebody will believe it went. */
    said.push("The marks on slide " + found.orphans.join(", ")
              + " are about no single project, so they go nowhere.");
  }
  els.readerSaid.textContent = said.join(" ");
  els.readerSaid.hidden = !said.length;
  els.deckSend.disabled = !found.ws.length;
}

/* --------------------------------------------------------------- the pen */
function paintPen() {
  var on = !!(window.Annotate && window.Annotate.isOn());
  els.readerPen.disabled = !window.Annotate || !openPages;
  els.readerPen.classList.toggle("on", on);
  els.readerPen.textContent = on ? "✎ done marking" : "✎ mark it up";
  if (annBar) annBar.show(on);
  if (window.ViewPin) window.ViewPin.update();
}

els.readerPen.onclick = function () {
  if (!window.Annotate) return;
  setPen(!window.Annotate.isOn());
};

function setPen(next) {
  window.Annotate.setOn(next);
  if (!next) savePen();
  paintPen();
}

/* THE BOARD'S OWN TOOLS, on the page. Pen, eraser, loop, clipboard, colours,
   nibs and undo, built by `annbar.js`; its "done" is this switch turned off. */
var annBar = window.AnnBar && window.Annotate
  ? window.AnnBar.mount({ onDone: function () { setPen(false); } })
  : null;

/* AND BOTH BARS STAY ON THE GLASS WHILE A SLIDE IS PINCHED -- see `viewpin.js`.
   Zoomed in, they used to pan off with the page, and with them every way to
   finish marking or send it. */
/* A pinch is the deck's own, and a palm does not scroll it: `readerzoom.js`. */
if (window.ReaderZoom) {
  window.ReaderZoom.make({ scroller: els.readerPages, chip: els.readerZoom,
                          bar: document.getElementById("reader-bar") });
}

if (window.ViewPin) {
  window.ViewPin.pin(document.getElementById("reader-bar"),
                     { edge: "top", spacer: document.getElementById("reader"), z: "5" });
  if (annBar) window.ViewPin.pin(annBar.node, { edge: "bottom" });
}

/* WHERE THE INK IS, and it is kept until the board says it has it. The save
   -- 900 ms after the pen lifts, kept owed on a failure, retried on a timer,
   on `online` and on the page being looked at again, flushed with
   `keepalive` when the page goes hidden -- is `inkkeep.js`, the library
   reader's own path rather than a copy of it.

   `send` is NEVER set on these saves. Ink on a slide becomes a turn when the
   marks are sent as direction, and that is a different route with a
   different shape: one turn per WORKSPACE, in that workspace, rather than one
   turn per page on this board. */
var keeper = window.InkKeep && window.Annotate ? window.InkKeep.make({
  build: function (id) {
    return openBuild && /^doc\/meeting\/p\d+$/.test(id) ? openBuild : null;
  },
  /* WHICH DECK, so a page left open over a new one cannot write this
     deck's rings onto that one's slides: the board answers `gone`. */
  stamp: function (id) {
    return openDeck && /^doc\/meeting\/p\d+$/.test(id) ? { deck: openDeck } : null;
  },
  paint: function () { paintKept(); },
  saved: function (done) {
    /* A deck replaced under this page is drawn again. */
    if (done.some(function (d) { return d.gone; })) { load(); return; }
    /* A flag re-drawing may have cleared is asked again: stamped with this
       build, the marks are no longer on another. */
    if (els.readerRebuilt && !els.readerRebuilt.hidden
        && done.some(function (d) { return d.ok; })) refreshRebuilt();
  }
}) : null;

function refreshRebuilt() {
  fetch("/meeting/view", { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (got) {
      if (!got || !got.ok) return;
      if ((got.deck || null) !== openDeck) { load(); return; }
      paintRebuilt(got.rebuilt || null);
    })
    .catch(function () { /* the flag stays as it was */ });
}

function savePen(opts) {
  return keeper ? keeper.save(opts) : Promise.resolve([]);
}

function pagesMarked() {
  if (!window.Annotate) return 0;
  return window.Annotate.marked().filter(function (id) {
    return /^doc\/meeting\/p\d+$/.test(id);
  }).length;
}

function paintKept() {
  if (!els.readerKept) return;
  var said = keeper
    ? window.InkKeep.words(keeper.owed(), keeper.failed(), pagesMarked())
    : { text: "", cls: "" };
  els.readerKept.textContent = said.text;
  els.readerKept.className = "reader-kept" + (said.cls ? " " + said.cls : "");
  els.readerKept.hidden = !said.text;
}

if (keeper) {
  window.Annotate.onChange(function () {
    keeper.queue();
    paintPen();
    paintSaid();
    paintKept();
  });
}

/* --------------------------------------------- sending them as direction */
/* THE PANEL SAYS WHAT IS ABOUT TO HAPPEN BEFORE IT HAPPENS. This wakes a turn
   in every marked workspace, and a person who taps it not knowing that is a
   person who will not tap it a second time. It also says the thing that makes
   it safe: each turn PROPOSES and stops. */
els.deckSend.onclick = function () {
  var found = markedWorkspaces();
  if (!found.ws.length) return;
  els.deckAskList.textContent = found.ws.map(function (id) {
    return names[id] || id;
  }).join(", ") + ".";
  els.deckAskSaid.hidden = true;
  els.deckAskGo.disabled = false;
  els.deckAskGo.textContent = "send them";
  els.note.hidden = false;
};

els.deckAskCancel.onclick = function () { els.note.hidden = true; };

els.deckAskGo.onclick = function () {
  els.deckAskGo.disabled = true;
  els.deckAskGo.textContent = "sending…";
  /* WHATEVER IS OWED GOES FIRST. The server reads the marks off disk, so a
     stroke that has not been autosaved yet is a suggestion that would not be
     in the turn that was woken by it. */
  (keeper ? keeper.settle() : Promise.resolve(null)).then(function () {
    if (keeper && keeper.failed() && keeper.owed()) {
      var stop = new Error("unsaved");
      stop.said = "The ink is not saved yet, so the turns would not see all "
        + "of it. It is retrying; send once it says saved.";
      throw stop;
    }
    return fetch("/meeting/direction", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: "{}"
    });
  }).then(function (r) {
    return r.json().catch(function () { return {}; });
  }).then(function (got) {
    els.deckAskSaid.hidden = false;
    if (!got || !got.ok) {
      els.deckAskSaid.className = "note-said bad";
      els.deckAskSaid.textContent = (got && got.detail)
        || "the board refused it";
      els.deckAskGo.disabled = false;
      els.deckAskGo.textContent = "send them";
      return;
    }
    els.deckAskSaid.className = "note-said";
    els.deckAskSaid.textContent = got.detail
      + " You will be told on the front door when each card lands.";
    els.deckAskGo.textContent = "sent";
    /* The marks stay on the glass. They were consumed into a direction, and
       they go when the deck is replaced -- which is the only moment at which
       they stop meaning anything. */
    paintSaid();
  }).catch(function (err) {
    els.deckAskSaid.hidden = false;
    els.deckAskSaid.className = "note-said bad";
    els.deckAskSaid.textContent = (err && err.said)
      || "The board is not answering; nothing was sent.";
    els.deckAskGo.disabled = false;
    els.deckAskGo.textContent = "send them";
  });
};

/* CLOSE WAITS FOR THE INK. A close is a click, not a lid: leaving at once
   cancels a save already in the air and drops what the page still owes. Ink
   that will not save is said on the bar, and a second close leaves anyway. */
var closeAnyway = false;
els.readerClose.onclick = function () {
  if (!keeper || closeAnyway) { location.href = "/"; return; }
  els.readerClose.disabled = true;
  /* A board that does not answer is not waited on forever. */
  Promise.race([keeper.settle(), new Promise(function (ok) {
    setTimeout(ok, 8000);
  })]).then(function () {
    els.readerClose.disabled = false;
    if (keeper.owed()) {
      closeAnyway = true;
      els.readerKept.hidden = false;
      els.readerKept.className = "reader-kept bad";
      els.readerKept.textContent = "not saved — close again to leave without it";
      return;
    }
    location.href = "/";
  });
};

document.addEventListener("keydown", function (ev) {
  if (ev.key !== "Escape") return;
  if (!els.note.hidden) els.deckAskCancel.onclick();
});

paintPen();
paintKept();
load();
})();
