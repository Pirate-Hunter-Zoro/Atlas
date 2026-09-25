/* ==========================================================================
   meeting.js -- the one meeting deck, read on the glass and marked up on it.

   The library's reader over a document that belongs to the REPOSITORY. There
   is one deck at one path, it is replaced rather than versioned, and it is in
   no workspace's library -- `meetings/` is at the root on purpose, because a
   note about five workspaces filed under one of them is misfiled.

   Four rules, and the last is the one the whole page exists for:

     1. THE SAME READER. Page images drawn by the machine holding the PDF, the
        same `.lib-page` boxes, the same `data-ann` anchors, the same pen out
        of `annotate.js`. What differs is only how the file was found.
     2. NO NAME GOES OVER THE WIRE. There is one deck, so `/meeting/view`
        takes no argument at all. Nothing here builds a path and nothing here
        names a document.
     3. EVERY SLIDE SAYS WHOSE IT IS. One frame per workspace, and the caption
        under each page names it -- because the page is how a mark finds its
        project, and marking the wrong slide has to be visibly the wrong slide
        rather than silently the wrong project.
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
  "reader-pages", "deck-send", "deck-pdf",
  "note", "deck-ask-list", "deck-ask-said", "deck-ask-cancel", "deck-ask-go",
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
    paintPen();
    paintSaid();
    return;
  }
  pagesOf = got.pages_of || {};
  names = got.names || {};
  openPages = (got.pages || []).length;
  els.readerSub.textContent = openPages
    + (openPages === 1 ? " slide" : " slides")
    + (got.since ? " · " + got.since : "");
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
      : n + " · the whole repository";
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
  paintPen();
  paintSaid();
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
if (window.ViewPin) {
  window.ViewPin.pin(document.getElementById("reader-bar"),
                     { edge: "top", spacer: document.getElementById("reader"), z: "5" });
  if (annBar) window.ViewPin.pin(annBar.node, { edge: "bottom" });
}

/* Saved shortly after the pen lifts, never mid-stroke: serialising a
   well-marked page is real main-thread time, and it lands by construction in
   the middle of the next stroke. */
var penTimer = null;

function savePen() {
  if (!window.Annotate) return Promise.resolve([]);
  var ids = window.Annotate.unsaved();
  if (!ids.length) return Promise.resolve([]);
  return Promise.all(ids.map(function (id) {
    /* `send` is NEVER set from here. Ink on a slide becomes a turn when the
       marks are sent as direction, and that is a different route with a
       different shape: one turn per WORKSPACE, in that workspace, rather than
       one turn per page on this board. Sending on every stroke would wake a
       tutor per ring drawn. */
    var body = window.Annotate.payload(id, false);
    return fetch("/annotate/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body)
    }).then(function () { window.Annotate.clean(id); });
  }));
}

function queuePenSave() {
  if (penTimer) clearTimeout(penTimer);
  penTimer = setTimeout(function () {
    penTimer = null;
    /* Not under a moving nib. Deferred, not dropped. */
    if (window.Annotate.busy()) { queuePenSave(); return; }
    savePen();
  }, 900);
}

if (window.Annotate) {
  window.Annotate.onChange(function () {
    queuePenSave();
    paintPen();
    paintSaid();
  });
  window.addEventListener("pagehide", function () { savePen(); });
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
  savePen().then(function () {
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
  }).catch(function () {
    els.deckAskSaid.hidden = false;
    els.deckAskSaid.className = "note-said bad";
    els.deckAskSaid.textContent = "The board is not answering; nothing was sent.";
    els.deckAskGo.disabled = false;
    els.deckAskGo.textContent = "send them";
  });
};

els.readerClose.onclick = function () {
  /* Whatever is owed goes now. A page closed with ink that never reached disk
     is ink somebody drew and the board silently dropped. */
  savePen();
  location.href = "/";
};

document.addEventListener("keydown", function (ev) {
  if (ev.key !== "Escape") return;
  if (!els.note.hidden) els.deckAskCancel.onclick();
});

paintPen();
load();
})();
