/* ==========================================================================
   meeting.js -- the one meeting deck, read on the glass and marked up on it.

   The deck is the artifact `projects/Meetings/docs/meeting/` (`briefs.py`):
   one deck, replaced rather than versioned. This page is the one reader
   (`reader.js`) over it, with the two things the library's page does not
   have: the check of every number and figure against the brief, and a way
   back to the front door.

   Three rules:

     1. THE SAME READER. Page images drawn by the machine holding the PDF, the
        same `.lib-page` boxes, the same `data-ann` anchors, the same pen and
        the same save (`inkkeep.js`). What differs is only how the file was
        found.
     2. NO NAME GOES OVER THE WIRE for the pages. There is one deck, so
        `/meeting/view` takes no argument at all.
     3. A MARK IS FEEDBACK ON THE DECK, like ink on any document. The ink is
        kept in the Meetings subject (`/annotate/save?subject=`), and *say
        what is wrong* files one round on the deck through `/library/feedback`
        there, which queues a `[revise]` turn in a Meetings session. That turn
        edits the deck or writes TUTOR.md, its choice.
   ========================================================================== */
(function () {
"use strict";

var MEETINGS = "projects/Meetings";
var DECK_ID = "meeting";

var els = {};
[
  "deck-back", "deck-count",
  "reader-pen", "reader-said", "reader-kept", "reader-rebuilt",
  "reader-pages", "reader-close", "deck-send", "deck-pdf",
  "note", "deck-ask-list", "deck-ask-text", "deck-ask-said", "deck-ask-cancel",
  "deck-ask-go", "deck-check", "deck-check-head", "deck-check-list",
].forEach(function (id) {
  els[id.replace(/-(\w)/g, function (_, c) { return c.toUpperCase(); })] =
    document.getElementById(id);
});

function inMeetings(path) {
  return path + (path.indexOf("?") < 0 ? "?" : "&")
    + "subject=" + encodeURIComponent(MEETINGS);
}

var DECK_KEY = /^doc\/meeting\/p\d+$/;
var openPages = 0;
var openBuild = null;    /* the build on the glass: `got.build` */
var openDeck = null;     /* which deck it is: `got.deck` */

/* ---------------------------------------------------------- the reader */
/* WHERE THE INK IS, and it is kept until the board says it has it: the one
   save path, made by `reader.js`. `send` is never set on these saves; ink
   becomes a turn when *say what is wrong* files it. */
var reader = window.Reader ? window.Reader.mount({
  keep: {
    url: inMeetings("/annotate/save"),
    build: function (id) {
      return openBuild && DECK_KEY.test(id) ? openBuild : null;
    },
    /* WHICH DECK, so a page left open over a new one cannot write this
       deck's rings onto that one's slides: the board answers `gone`. */
    stamp: function (id) {
      return openDeck && DECK_KEY.test(id) ? { deck: openDeck } : null;
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
  }
}) : null;
var keeper = reader ? reader.keeper : null;

/* ------------------------------------------------------------- the pages */
function load() {
  if (!reader) return;
  reader.open({
    pagesUrl: "/meeting/view",
    id: DECK_ID, title: "Meeting deck", alt: "slide",
    wait: "drawing the slides…",
    count: function (got) {
      var n = (got.pages || []).length;
      return n + (n === 1 ? " slide" : " slides")
        + (got.period ? " · " + got.period : got.since ? " · " + got.since : "");
    },
    drawn: drawn,
    failed: failed
  });
}

function drawn(got, h) {
  openPages = h.pages;
  var subjects = (got.workspaces || []).length;
  els.deckCount.textContent = subjects
    ? subjects + " project" + (subjects === 1 ? "" : "s") : "";
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

function failed(got) {
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
}

/* INK KNOWS ITS BUILD. A new deck clears the old one's ink, so this is only
   ever a deck recompiled in place: its slides moved under the marks. */
function paintRebuilt(flag) {
  if (!els.readerRebuilt) return;
  if (!flag) { els.readerRebuilt.hidden = true; return; }
  els.readerRebuilt.hidden = false;
  els.readerRebuilt.textContent = "These marks were drawn on the "
    + (flag.when || "an earlier") + " build; the deck has been rebuilt since, "
    + "so check each one is still on the slide it was meant for.";
}

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
function slidesMarked() {
  if (!window.Annotate) return [];
  return window.Annotate.marked().filter(function (id) {
    return DECK_KEY.test(id);
  }).map(function (id) { return Number(/p(\d+)$/.exec(id)[1]); })
    .sort(function (a, b) { return a - b; });
}

function paintSaid() {
  var marked = slidesMarked();
  var said = "";
  if (!openPages) {
    said = "There is no deck to read. Make one from the front door.";
  } else if (marked.length) {
    said = "Marked on slide" + (marked.length === 1 ? " " : "s ")
      + marked.join(", ") + ". Say what is wrong sends the marks, with "
      + "anything you type, to the Meetings tutor as one round of feedback: "
      + "it edits the deck or writes down where the work goes next.";
  }
  els.readerSaid.textContent = said;
  els.readerSaid.hidden = !said;
  els.deckSend.disabled = !openPages;
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
  if (!next && keeper) keeper.save();
  paintPen();
}

/* THE BOARD'S OWN TOOLS, on the page. Pen, eraser, loop, clipboard, colours,
   nibs and undo, built by `annbar.js`; its "done" is this switch turned off. */
var annBar = window.AnnBar && window.Annotate
  ? window.AnnBar.mount({ onDone: function () { setPen(false); } })
  : null;

/* AND BOTH BARS STAY ON THE GLASS WHILE A SLIDE IS PINCHED -- `viewpin.js`. */
if (window.ViewPin) {
  window.ViewPin.pin(document.getElementById("reader-bar"),
                     { edge: "top", spacer: document.getElementById("reader"), z: "5" });
  if (annBar) window.ViewPin.pin(annBar.node, { edge: "bottom" });
}

function paintKept() {
  if (!els.readerKept) return;
  var said = keeper
    ? window.InkKeep.words(keeper.owed(), keeper.failed(), slidesMarked().length)
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

/* --------------------------------------------------- saying what is wrong */
/* ONE ROUND ON THE DECK, filed where every document's is: `/library/feedback`
   in the Meetings subject, which writes the note beside the deck and queues a
   `[revise]` turn in a Meetings session. */
function paintAsk() {
  var marked = slidesMarked();
  els.deckAskList.textContent = marked.length
    ? "Your marks on slide" + (marked.length === 1 ? " " : "s ")
      + marked.join(", ") + " go with it."
    : "No slide is marked: what you type is the feedback.";
  els.deckAskGo.disabled = !marked.length && !els.deckAskText.value.trim();
}

els.deckSend.onclick = function () {
  if (!openPages) return;
  els.deckAskSaid.hidden = true;
  els.deckAskGo.textContent = "send it";
  paintAsk();
  els.note.hidden = false;
  if (els.deckAskText.focus) els.deckAskText.focus();
};

els.deckAskText.addEventListener("input", paintAsk);
els.deckAskCancel.onclick = function () { els.note.hidden = true; };

els.deckAskGo.onclick = function () {
  var text = els.deckAskText.value.trim();
  var page = reader ? reader.pageInView() : 0;
  els.deckAskGo.disabled = true;
  els.deckAskGo.textContent = "sending…";
  /* WHATEVER IS OWED GOES FIRST. The server reads the marks off disk, so a
     stroke that has not been saved yet would not be in the round. */
  (keeper ? keeper.settle() : Promise.resolve(null)).then(function () {
    if (keeper && keeper.failed() && keeper.owed()) {
      var stop = new Error("unsaved");
      stop.said = "The ink is not saved yet, so the round would not carry all "
        + "of it. It is retrying; send once it says saved.";
      throw stop;
    }
    return fetch(inMeetings("/library/feedback"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ document: DECK_ID, text: text, page: page })
    });
  }).then(function (r) {
    return r.json().catch(function () { return {}; });
  }).then(function (got) {
    els.deckAskSaid.hidden = false;
    if (!got || got.ok === false) {
      els.deckAskSaid.className = "note-said bad";
      els.deckAskSaid.textContent = ((got && (got.error || got.detail))
        || "the board refused it") + ".";
      els.deckAskGo.disabled = false;
      els.deckAskGo.textContent = "send it";
      return;
    }
    els.deckAskSaid.className = "note-said";
    els.deckAskSaid.textContent = "Filed at " + got.rel + ". " + (got.detail || "");
    els.deckAskGo.textContent = "sent";
    els.deckAskText.value = "";
    paintSaid();
  }).catch(function (err) {
    els.deckAskSaid.hidden = false;
    els.deckAskSaid.className = "note-said bad";
    els.deckAskSaid.textContent = (err && err.said)
      || "The board is not answering; nothing was sent.";
    els.deckAskGo.disabled = false;
    els.deckAskGo.textContent = "send it";
  });
};

/* CLOSE WAITS FOR THE INK, and leaves for the front door. A close is a click,
   not a lid: leaving at once cancels a save already in the air and drops what
   the page still owes. Ink that will not save is said on the bar, and a second
   close leaves anyway. */
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
