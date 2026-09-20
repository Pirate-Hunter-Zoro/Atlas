/* ==========================================================================
   library.js -- every document this workspace has written, on one surface.

   The ⋯ menu's document panel offers the two documents the BOARD makes: the
   exported lesson and the compiled write-up. The contents drawer offers what
   `reading.py` found, as things to put on a card. Neither is "every paper and
   presentation in this project", neither was reachable without opening a lesson
   first, and there was nowhere at all to say what was wrong with one.

   Seven rules this page keeps, and each of them was paid for elsewhere first:

     1. AN ID, NEVER A PATH. What goes over the wire is the id `library.py`
        handed out, and the server looks it up in what it discovered. Nothing
        here builds a path, and a miss is a miss.
     2. IT NEVER TOUCHES THE LESSON. No card, no sitting, no `state.json`.
        Somebody mid-proof on an iPad is not interrupted by somebody correcting
        a deck, which is the whole reason this is a page rather than a panel.
     3. FEEDBACK IS NOT JUST FILED. One tap writes the note where the document
        is and asks for the revision, and the reply says which machinery took
        it -- the board for a document it compiled, the manuscript factory for
        one it delivered.
     4. A DOCUMENT THAT HAS BEEN MARKED UP HAS ALREADY SAID SOMETHING. Ink on
        its pages goes into the note as the pages it is on and a picture of
        each, so the send button is live with an empty textarea and says so.
        Asking somebody to type out a ring they have already drawn round a
        figure is the translation this whole surface exists to avoid.
     5. NOTHING THE READER IS WAITING ON IS SILENT. A note dispatches the
        revision in the same request, and the only thing that used to change on
        the glass afterwards was a line saying the note was filed. So the page
        holds a STAMP -- `GET /library/stamp`, stats only -- asks for it every
        few seconds while it is in front of somebody, says the turn is running,
        and re-draws the open document the moment its bytes move. Not the hub's
        stream: that payload is the LESSON's, and this page opens no sitting on
        purpose.
     6. A RE-DRAW KEEPS THE READER'S PLACE, and the ink stays on. Throwing a
        33-page deck back to page 1 after a one-line fix is its own defect. The
        marks are kept rather than cleared, because a ring somebody drew is
        theirs -- and where the page count moved, the page says out loud that
        they were drawn on an older version rather than pretending page 7 is
        still page 7.
     7. AND THE RING IS DRAWN HERE. The pen is on the page being read, not on
        a second surface: each page carries `data-ann="doc/<id>/p<n>"`, which
        is the anchor `annotate.js` has taken since the board's own viewer
        first drew a document, and the strokes go to `/annotate/save` the same
        way a mark on a card does. `send` is never set from this page -- ink
        made here is a complaint about a document, and it becomes a turn when
        the note goes, not the moment the pen lifts.
   ========================================================================== */

var els = {
  back: document.getElementById("lib-back"),
  where: document.getElementById("lib-where"),
  count: document.getElementById("lib-count"),
  list: document.getElementById("lib-list"),
  none: document.getElementById("lib-none"),
  reader: document.getElementById("reader"),
  readerName: document.getElementById("reader-name"),
  readerSub: document.getElementById("reader-sub"),
  readerPages: document.getElementById("reader-pages"),
  readerPen: document.getElementById("reader-pen"),
  readerSay: document.getElementById("reader-say"),
  readerClose: document.getElementById("reader-close"),
  readerSaid: document.getElementById("reader-said"),
  note: document.getElementById("note"),
  noteTitle: document.getElementById("note-title"),
  noteWhere: document.getElementById("note-where"),
  noteText: document.getElementById("note-text"),
  notePage: document.getElementById("note-page"),
  noteMarks: document.getElementById("note-marks"),
  noteSaid: document.getElementById("note-said"),
  noteCancel: document.getElementById("note-cancel"),
  noteSend: document.getElementById("note-send"),
  askRevise: document.getElementById("ask-revise"),
  askRework: document.getElementById("ask-rework"),
  purposeBox: document.getElementById("note-purpose-box"),
  purpose: document.getElementById("note-purpose"),
  round: document.getElementById("round"),
  roundTitle: document.getElementById("round-title"),
  roundList: document.getElementById("round-list"),
  roundText: document.getElementById("round-text"),
  roundClose: document.getElementById("round-close"),
  res: document.getElementById("res"),
  resCount: document.getElementById("res-count"),
  resFenced: document.getElementById("res-fenced"),
  resFind: document.getElementById("res-find"),
  resNone: document.getElementById("res-none"),
  resList: document.getElementById("res-list"),
  shown: document.getElementById("shown"),
  shownName: document.getElementById("shown-name"),
  shownSub: document.getElementById("shown-sub"),
  shownBody: document.getElementById("shown-body"),
  shownClose: document.getElementById("shown-close")
};

/* THE WAY BACK GOES WHERE YOU CAME FROM.

   This page is reached from two places and used to lead back to one of them.
   The board's own row into it is a lesson stepping sideways, so `/board` is
   right there. The FRONT DOOR's *Papers & decks* is not: reading a document
   nobody is teaching from has nothing to do with the lesson -- that is the
   whole reason the button exists -- and landing somebody in a sitting they did
   not open, to get back to the door they tapped from, is the front door's own
   trapped-level defect wearing a different page.

   So the caller says where it came from and this says so in the label. One
   query parameter, not a stored flag: it survives a reload, a share and a
   cached shell, and there is no second copy of it to go stale. */
var CAME_FROM = { home: { href: "/", text: "\u2039 Everything",
                          title: "back to everything" } };

(function backWhereYouCameFrom() {
  var el = els.back;
  if (!el) return;
  var from = "";
  try { from = new URLSearchParams(location.search).get("from") || ""; }
  catch (e) { from = ""; }
  var want = CAME_FROM[from];
  if (!want) return;
  el.href = want.href;
  el.textContent = want.text;
  el.title = want.title;
})();

/* The board's own theme, read the way the board reads it: one choice, made
   once, that follows the person from surface to surface. */
var THEME_KEY = "board.theme";
try { document.body.dataset.mode = localStorage.getItem(THEME_KEY) || "auto"; }
catch (e) { document.body.dataset.mode = "auto"; }
function syncSystemTheme() {
  var dark = window.matchMedia
    && window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.body.classList.toggle("sys-dark", !!dark);
}
syncSystemTheme();
if (window.matchMedia) {
  var watch = window.matchMedia("(prefers-color-scheme: dark)");
  if (watch.addEventListener) watch.addEventListener("change", syncSystemTheme);
  else if (watch.addListener) watch.addListener(syncSystemTheme);
}

var docs = [];
var openDoc = null;          /* the document being read */
var openPages = 0;           /* how many pages it turned out to have */
var drawnPages = 0;          /* how many it had when the ink on it was drawn */
var noteFor = null;          /* the document a note is being written about */
var notePage = 0;
var noteAsk = "revise";      /* which of the two asks the panel is on */

/* HOW OFTEN THE CHEAP QUESTION IS ASKED, and only while the page is visible.
   The stamp is a walk and a stat per document with no `pdfinfo` in it, so this
   is affordable where `/library.json` -- which reads titles out of sources --
   is not. A backgrounded tab asks nothing at all. */
var STAMP_EVERY = 4000;
var stampTimer = null;
var stamps = {};             /* id -> hash of where that document is and when */
var stampAll = "";           /* one hash of all of it */

/* WHAT WAS ASKED FOR AND HAS NOT LANDED. A turn was dispatched in the same
   request that filed the note, and it runs for a minute or for an hour. Kept
   where a reload finds it again, because a tablet put down and picked up is the
   normal case and "the board forgot you asked" is the silence this removes. */
var FLIGHT_KEY = "library.flight";
var flight = null;           /* {id, ask, at, stamp} */

/* HOW SHORT A PURPOSE MAY BE. The server is the rule -- `library.PURPOSE_LEAST`
   -- and this is the same number so the button is dead rather than the send
   being refused. */
var PURPOSE_LEAST = 25;

try { flight = JSON.parse(localStorage.getItem(FLIGHT_KEY) || "null"); }
catch (e) { flight = null; }

function remember(what) {
  flight = what;
  try {
    if (what) localStorage.setItem(FLIGHT_KEY, JSON.stringify(what));
    else localStorage.removeItem(FLIGHT_KEY);
  } catch (e) { /* a private window. The state still holds for this page. */ }
}

/* HOW LONG AGO, in the largest unit that is still true. A line that says "asked
   1440 minutes ago" is a line nobody reads, and this one is read while waiting. */
function since(at) {
  var mins = Math.max(0, Math.round((Date.now() - (at || 0)) / 60000));
  if (!mins) return "just now";
  if (mins === 1) return "a minute ago";
  if (mins < 60) return mins + " minutes ago";
  var hours = Math.round(mins / 60);
  if (hours < 24) return hours === 1 ? "an hour ago" : hours + " hours ago";
  var days = Math.round(hours / 24);
  return days === 1 ? "yesterday" : days + " days ago";
}

function load() {
  fetch("/library.json", { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (got) { paint(got || {}); })
    .catch(function () {
      /* The board is not answering. Say so here rather than leaving an empty
         page, which reads as a workspace with nothing in it. */
      els.none.hidden = false;
      els.none.textContent = "The board is not answering. Nothing is serving "
        + "this address at the moment.";
    });
}

function paint(got) {
  docs = got.documents || [];
  /* THE OPEN DOCUMENT IS A RECORD, AND THIS IS A NEW ONE OF IT. The reader
     stays open across a reload -- ink saved while drawing asks for the list
     again, so the row's mark count is right a second later -- and the record
     `say` reads to decide whether an empty note can be sent is whichever one
     was captured when the document was tapped. Leaving it stale is a page you
     have just drawn on refusing to send the ink. */
  if (openDoc) {
    docs.forEach(function (d) { if (d.id === openDoc.id) openDoc = d; });
  }
  if (noteFor) {
    docs.forEach(function (d) { if (d.id === noteFor.id) noteFor = d; });
  }
  els.where.textContent = got.workspace || "this workspace";
  els.count.textContent = docs.length
    ? docs.length + (docs.length === 1 ? " document" : " documents")
    : "";
  els.list.innerHTML = "";
  els.none.hidden = !!docs.length;
  if (!docs.length) {
    els.none.textContent = "Nothing has been written up in this workspace yet. "
      + "A make sitting keeps what it writes in " + (got.writeups || "writeups")
      + "/, one directory per document, and it appears here.";
    return;
  }

  /* GROUPED BY DIRECTORY, because the directory is the group: four stems in
     `paper1-trd-prediction/` are one piece of work, and a flat list of fifty
     rows says nothing about which those four are. */
  var here = null;
  docs.forEach(function (doc) {
    if (doc.dir !== here) {
      here = doc.dir;
      var head = document.createElement("div");
      head.className = "lib-dir";
      head.textContent = here || "(top level)";
      els.list.appendChild(head);
    }
    els.list.appendChild(row(doc));
  });
}

/* ------------------------------------------------- has anything moved yet */
/* ONE HASH, ASKED OFTEN. `/library.json` walks the workspace, reads a title out
   of every source and runs `pdfinfo` per PDF, and is cached for thirty seconds
   for that reason -- it is the wrong thing to poll. `/library/stamp` is stats
   only: where each document is, when its source and its PDF last changed, and
   how big they are. Nothing else is in it, so filing a note cannot move it and
   the page cannot redraw on its own feedback.

   DO NOT REACH FOR THE HUB'S STREAM HERE. `/events` carries the LESSON's
   payload, and this page opens no sitting on purpose. */
function poll() {
  if (stampTimer) clearTimeout(stampTimer);
  stampTimer = null;
  if (document.hidden) return;       /* a backgrounded tab asks nothing */
  fetch("/library/stamp", { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (got) { moved(got || {}); })
    .catch(function () { /* the poll is quiet about a board that is down; the
                            list's own fetch is what says so on the glass. */ })
    .then(function () {
      if (!document.hidden) stampTimer = setTimeout(poll, STAMP_EVERY);
    });
}

function moved(got) {
  if (!got.ok) return;
  var was = stamps;
  var now = got.documents || {};
  var first = !stampAll;
  stamps = now;
  /* WHAT LANDED. The overall hash says "ask for the list again"; the
     per-document one says "the document being read is the one that moved", and
     redrawing a 33-page deck because a different document was rebuilt is its
     own defect. */
  var changed = got.stamp !== stampAll;
  stampAll = got.stamp;
  if (first) { paintFlight(); return; }   /* the first answer is the baseline */
  if (!changed) { paintFlight(); return; }
  load();
  if (openDoc && now[openDoc.id] !== was[openDoc.id]) redraw();
  paintFlight();
}

/* WHAT WAS ASKED FOR, AND WHETHER IT HAS LANDED. Cleared by the document's own
   bytes moving -- not by a timer and not by the reply to the send, which says
   only that the turn was woken. */
function paintFlight() {
  if (flight && stamps[flight.id] && flight.stamp
      && stamps[flight.id] !== flight.stamp) {
    remember(null);
  }
  /* THE DOCUMENT IS GONE. An overhaul may rename the source it was written
     from, and there is then nothing left to wait for -- an unlanded turn held
     against a document that no longer exists would sit on the page for ever.
     Only once a stamp has actually been read, or the very first pass clears
     what a reload just restored. */
  if (flight && stampAll && !stamps[flight.id]) remember(null);
  if (flight && !flight.stamp && stamps[flight.id]) {
    /* The send landed before the first stamp did. Take this one as the
       baseline, or the very next poll reads as the revision arriving. */
    flight.stamp = stamps[flight.id];
    remember(flight);
  }
  paintReaderSaid();
  var rows = els.list.querySelectorAll(".lib-flight");
  for (var i = 0; i < rows.length; i++) {
    rows[i].textContent = flightWords(rows[i].dataset.id);
    rows[i].hidden = !rows[i].textContent;
  }
}

function flightWords(id) {
  if (!flight || flight.id !== id) return "";
  return (flight.ask === "rework"
    ? "being overhauled — asked " : "being revised — asked ")
    + since(flight.at)
    + ". This page re-draws it the moment the file changes.";
}

/* THE ONE LINE IN THE READER, and it carries both things a reader can be owed:
   that a turn is running on this document, and that the ink on it was drawn on
   a version with a different number of pages. */
function paintReaderSaid() {
  if (!openDoc) { els.readerSaid.hidden = true; return; }
  var said = [];
  var running = flightWords(openDoc.id);
  if (running) said.push(running);
  if (drawnPages && openPages && drawnPages !== openPages
      && window.Annotate && window.Annotate.marked().length) {
    /* KEPT, NOT CLEARED. A ring somebody drew is theirs, and a document that
       reflowed is not a reason to throw it away -- but the mark on page 7 is
       about something that may no longer be on page 7, and the page says so
       rather than pretending otherwise. */
    said.push("Your marks were drawn on a version with " + drawnPages
      + (drawnPages === 1 ? " page" : " pages")
      + "; this one has " + openPages
      + ". They are still here, on the page numbers they were made on.");
  }
  els.readerSaid.textContent = said.join(" ");
  els.readerSaid.hidden = !said.length;
}

function row(doc) {
  var box = document.createElement("div");
  box.className = "lib-row";

  var name = document.createElement("button");
  name.type = "button";
  name.className = "lib-name";
  name.textContent = doc.title || doc.stem;
  /* A document with no PDF cannot be read on the glass, and saying so on the
     button beats a viewer that opens empty. */
  name.disabled = !doc.pdf;
  name.onclick = function () { read(doc); };
  box.appendChild(name);

  var meta = document.createElement("span");
  meta.className = "lib-meta";
  meta.textContent = [
    doc.kind === "deck" ? "deck" : "paper",
    doc.stem,
    (doc.formats || []).join(" · "),
    doc.pages ? doc.pages + (doc.pages === 1 ? " page" : " pages") : "",
    doc.pdf ? (doc.iso ? "built " + doc.iso : "") : "no PDF yet"
  ].filter(Boolean).join("  ·  ");
  box.appendChild(meta);

  /* STALE IS ARITHMETIC, not a record: the source is newer than the PDF, so
     what is on the glass is not what the file says any more. */
  if (doc.stale) {
    var old = document.createElement("span");
    old.className = "lib-stale";
    old.textContent = "the source has changed since this PDF was built";
    box.appendChild(old);
  }

  if (doc.marks && doc.marks.pages) {
    var ink = document.createElement("span");
    ink.className = "lib-marks";
    ink.textContent = "marked up on " + doc.marks.pages
      + (doc.marks.pages === 1 ? " page" : " pages")
      + ", " + doc.marks.strokes
      + (doc.marks.strokes === 1 ? " stroke" : " strokes");
    box.appendChild(ink);
  }

  /* THE ROUNDS ARE READABLE. The turn writes `## What was changed` at the
     bottom of the feedback file, which is the answer to *did it do what I
     asked* -- and the row could say a document had had three rounds and not a
     word of what any of them did. */
  if ((doc.notes || []).length) {
    var rounds = document.createElement("button");
    rounds.type = "button";
    rounds.className = "lib-rounds";
    rounds.textContent = doc.notes.length
      + (doc.notes.length === 1 ? " round of feedback" : " rounds of feedback")
      + ", last on " + doc.notes[doc.notes.length - 1].day
      + " — read what changed";
    rounds.addEventListener("click", function () { openRounds(doc); });
    box.appendChild(rounds);
  }

  /* WHAT IS RUNNING ON IT. Painted from the row rather than only from the
     reader, because the document being worked on is usually not the one open. */
  var going = document.createElement("span");
  going.className = "lib-flight";
  going.dataset.id = doc.id;
  going.textContent = flightWords(doc.id);
  going.hidden = !going.textContent;
  box.appendChild(going);

  var acts = document.createElement("div");
  acts.className = "lib-acts";
  if (doc.pdf) {
    acts.appendChild(act("read it", "quiet", function () { read(doc); }));
  }
  acts.appendChild(act("say what is wrong", "quiet", function () {
    say(doc, 0);
  }));
  box.appendChild(acts);
  return box;
}

function act(label, cls, fn) {
  var b = document.createElement("button");
  b.type = "button";
  b.className = cls;
  b.textContent = label;
  b.addEventListener("click", fn);
  return b;
}

/* ------------------------------------------------------- reading one */
function read(doc) {
  openDoc = doc;
  openPages = 0;
  drawnPages = 0;
  els.reader.hidden = false;
  els.readerPages.scrollTop = 0;
  draw(doc, 0);
}

/* THE SAME DOCUMENT AGAIN, BECAUSE ITS BYTES MOVED. Asked for by the stamp
   poll, never by the reader: a revision was dispatched in the same request that
   filed the note, and this is the half where it appears in front of you.

   The render cache is keyed on the PDF's own modification time -- `paper._digest`
   -- so a re-fetch gets the new pages rather than the old ones out of a cache.
   Nothing had to change there; nothing asked. */
function redraw() {
  if (!openDoc || els.reader.hidden) return;
  draw(openDoc, pageInView());
}

/* WHERE THE READER WAS, PUT BACK. A picture has no height until it has decoded,
   so a scroll position set the instant the markup exists lands nowhere: the
   page is restored as the images above it arrive, and stops being restored once
   they all have. Otherwise a 33-page deck comes back at page 1 after a one-line
   fix, which is its own defect. */
var placeWanted = 0;
var placeUntil = 0;

function keepPlace() {
  if (!placeWanted || Date.now() > placeUntil) { placeWanted = 0; return; }
  var want = els.readerPages.querySelector(
    '.lib-page[data-page="' + placeWanted + '"]');
  if (!want) return;
  /* Against the SCROLLER'S OWN rectangle, for the reason `pageInView` gives:
     `offsetTop` is measured from whichever ancestor happens to be positioned. */
  var top = els.readerPages.getBoundingClientRect().top;
  els.readerPages.scrollTop += want.getBoundingClientRect().top - top;
}

function draw(doc, place) {
  openPages = 0;
  placeWanted = place || 0;
  /* Eight seconds is the whole budget for putting somebody back where they
     were. Past that they have scrolled somewhere themselves and a jump is
     the page taking the document off them. */
  placeUntil = Date.now() + 8000;
  els.readerName.textContent = doc.title || doc.stem;
  els.readerSub.textContent = place ? "re-drawing the pages…" : "drawing the pages…";
  els.readerPages.innerHTML = "";
  if (!place) els.readerPages.scrollTop = 0;
  paintReaderSaid();
  var asked = doc.id;
  fetch("/library/view/" + encodeURIComponent(doc.id),
        { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (got) {
      if (!openDoc || openDoc.id !== asked) return;   /* closed, or another */
      if (!got || !got.ok) {
        els.readerSub.textContent = (got && got.detail)
          || "The pages could not be drawn.";
        return;
      }
      openPages = (got.pages || []).length;
      els.readerSub.textContent = openPages
        + (openPages === 1 ? " page" : " pages")
        + (got.truncated ? " (the first of a longer document)" : "");
      (got.pages || []).forEach(function (url, i) {
        var fig = document.createElement("figure");
        fig.className = "lib-page";
        fig.setAttribute("data-page", String(i + 1));
        /* THE ANCHOR, and it is the tail of a §2.1 address. Ink is stored in
           fractions of this box rather than in page pixels, so it is in the
           same place on the page after a rotation or a zoom -- the trick
           `annotate.js` already plays on cards, one level in. */
        fig.dataset.ann = "doc/" + doc.id + "/p" + (i + 1);
        var img = document.createElement("img");
        img.src = url;
        img.alt = "page " + (i + 1);
        img.loading = i < 2 ? "eager" : "lazy";
        fig.appendChild(img);
        var n = document.createElement("figcaption");
        n.textContent = i + 1;
        fig.appendChild(n);
        els.readerPages.appendChild(fig);
        img.addEventListener("load", keepPlace);
        if (window.Annotate) {
          window.Annotate.attach(fig);
          /* A picture has no height until it has decoded, and a layer sized
             against a zero-height box covers nothing. */
          img.addEventListener("load", function () {
            window.Annotate.redrawAll();
          });
        }
      });
      /* Marks made on this document before, put back. They came with the
         pages: this page holds no live payload to read them out of, because
         it opens no sitting. KEPT ACROSS A RE-DRAW for the same reason -- the
         keys are `doc/<id>/p<n>` and are the document's, not this drawing's. */
      if (window.Annotate) window.Annotate.load(got.ink || {});
      /* HOW MANY PAGES THE INK WAS DRAWN ON. Taken the first time this document
         is drawn with marks on it, so a later re-draw can say out loud that the
         deck reflowed under them. */
      if (!drawnPages && window.Annotate && window.Annotate.marked().length) {
        drawnPages = openPages;
      }
      keepPlace();
      paintPen();
      paintReaderSaid();
    })
    .catch(function () {
      els.readerSub.textContent = "The board is not answering.";
    });
}

function closeReader() {
  /* Whatever is owed goes now. A page closed with ink that never reached disk
     is ink somebody drew and the board silently dropped. */
  savePen();
  if (window.Annotate) {
    window.Annotate.setOn(false);
    /* The store outlives the document, and the next one opened has its own
       page 1. Keeping last document's ink keyed against it would draw one
       paper's marks over another's. */
    window.Annotate.forget();
  }
  openDoc = null;
  openPages = 0;
  drawnPages = 0;
  placeWanted = 0;
  els.reader.hidden = true;
  els.readerSaid.hidden = true;
  paintPen();
}

/* ------------------------------------------------------------- the pen */
/* ON THE PAGE, NOT ON A SECOND SURFACE. The layer is inert until this is on,
   so scrolling a long document behaves exactly as it did before. */
function paintPen() {
  var on = !!(window.Annotate && window.Annotate.isOn());
  els.readerPen.disabled = !window.Annotate || !openPages;
  els.readerPen.classList.toggle("on", on);
  els.readerPen.textContent = on ? "✎ done marking" : "✎ mark it up";
}

els.readerPen.onclick = function () {
  if (!window.Annotate) return;
  var next = !window.Annotate.isOn();
  window.Annotate.setOn(next);
  if (!next) savePen();
  paintPen();
};

/* Saved shortly after the pen lifts, never mid-stroke: serialising a
   well-marked page is real main-thread time, and it lands by construction in
   the middle of the next stroke. The board's own autosave holds the same rule
   for the same reason. */
var penTimer = null;

function savePen() {
  if (!window.Annotate) return Promise.resolve([]);
  var ids = window.Annotate.unsaved();
  if (!ids.length) return Promise.resolve([]);
  return Promise.all(ids.map(function (id) {
    /* `send` is NEVER set from here. Ink on a document is a complaint about
       the document, and it becomes a turn when the note goes -- the feedback
       route reads the marks where it reads the textarea. Sending on every
       stroke would wake a tutor per ring drawn. */
    var body = window.Annotate.payload(id, false);
    return fetch("/annotate/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body)
    }).then(function () { window.Annotate.clean(id); });
  })).then(function (done) {
    /* The row carries how many pages are marked, and the note dialog decides
       whether the send button is live off the same number. Both are worth
       being right about a second after a ring is drawn. */
    if (done.length) load();
    return done;
  });
}

function queuePenSave() {
  if (penTimer) clearTimeout(penTimer);
  penTimer = setTimeout(function () {
    penTimer = null;
    /* Not under a moving nib. Deferred, not dropped: the hand lifts and the
       next tick takes it. */
    if (window.Annotate.busy()) { queuePenSave(); return; }
    savePen();
  }, 900);
}

if (window.Annotate) {
  window.Annotate.onChange(function () {
    queuePenSave();
    paintPen();
  });
  /* A closing tab must not take the last stroke with it. */
  window.addEventListener("pagehide", function () { savePen(); });
}

els.readerClose.onclick = closeReader;
/* WHICH PAGE THEY ARE LOOKING AT. A note written while reading page 14 is
   about page 14, and asking for the number is a question whose answer is on the
   screen already -- so it is read off the scroll rather than typed. */
els.readerSay.onclick = function () { say(openDoc, pageInView()); };

function pageInView() {
  var pages = els.readerPages.querySelectorAll(".lib-page");
  if (!pages.length) return 0;
  /* Against the SCROLLER'S OWN rectangle rather than `offsetTop`, which is
     measured from whichever ancestor happens to be positioned and is therefore
     off by the height of the bar. The last page whose top edge has passed the
     top of the window is the one being read. */
  var top = els.readerPages.getBoundingClientRect().top + 80;
  var best = 1;
  for (var i = 0; i < pages.length; i++) {
    if (pages[i].getBoundingClientRect().top <= top) best = i + 1;
  }
  return best;
}

/* ---------------------------------------------------- saying what is wrong */
function say(doc, page) {
  if (!doc) return;
  noteFor = doc;
  notePage = page || 0;
  els.noteTitle.textContent = doc.title || doc.stem;
  els.noteWhere.textContent = doc.rel;
  els.noteText.value = "";
  els.purpose.value = "";
  els.noteSaid.hidden = true;
  els.notePage.hidden = !notePage;
  if (notePage) els.notePage.textContent = "about page " + notePage;
  var ink = (doc.marks && doc.marks.pages) || 0;
  els.noteMarks.hidden = !ink;
  if (ink) {
    els.noteMarks.textContent = "Your marks on " + ink
      + (ink === 1 ? " page" : " pages")
      + " go with this. Send it with nothing typed and the ink is the feedback.";
  }
  /* A document the board did not write is corrected by the factory that did,
     and an overhaul does not come back through here -- so the ask is not
     offered rather than offered and refused. `rework_refused` is the rule; this
     is the same sentence one surface up. */
  els.askRework.disabled = doc.made === "paper-writer";
  els.askRework.title = els.askRework.disabled
    ? "the manuscript factory wrote this one, and an overhaul is asked for there"
    : "restructure, cut and rewrite it to a new purpose";
  setAsk("revise");
  els.note.hidden = false;
  els.noteText.focus();
}

/* WHICH OF THE TWO ASKS. Not a second question after the tap: the panel is on
   one of them at all times, and which one is visible before anything is typed.
   A correction keeps the document's structure, its names for things and its
   claims; an overhaul may restructure, cut, reorder and rewrite, and costs a
   sentence saying what the document is for now. */
function setAsk(which) {
  noteAsk = which === "rework" ? "rework" : "revise";
  els.askRevise.classList.toggle("on", noteAsk === "revise");
  els.askRework.classList.toggle("on", noteAsk === "rework");
  els.purposeBox.hidden = noteAsk !== "rework";
  els.noteText.placeholder = noteAsk === "rework"
    ? "Anything else about it — what to keep, what to drop. Optional."
    : "What is wrong with it, and what should it say instead.";
  els.noteSend.textContent = noteAsk === "rework" ? "overhaul it" : "send it";
  paintSend();
  if (noteAsk === "rework") els.purpose.focus();
}

els.askRevise.onclick = function () { setAsk("revise"); };
els.askRework.onclick = function () { setAsk("rework"); };

/* Live as soon as there is either half of a complaint. The marks are already
   on disk, so nothing has to be collected here -- the server reads them where
   it reads the text. An overhaul is live on its PURPOSE instead: the words are
   optional there and the sentence saying what the document is for is not. */
function paintSend() {
  var ink = (noteFor && noteFor.marks && noteFor.marks.pages) || 0;
  els.noteSend.disabled = noteAsk === "rework"
    ? els.purpose.value.trim().length < PURPOSE_LEAST
    : !els.noteText.value.trim() && !ink;
}

els.noteText.addEventListener("input", paintSend);
els.purpose.addEventListener("input", paintSend);

els.noteCancel.onclick = function () {
  els.note.hidden = true;
  noteFor = null;
};

/* ------------------------------------------------- reading a round back */
function openRounds(doc) {
  els.roundTitle.textContent = doc.title || doc.stem;
  els.roundList.innerHTML = "";
  els.roundText.textContent = "";
  var rounds = (doc.notes || []).slice().reverse();      /* newest first */
  rounds.forEach(function (note, i) {
    var b = act(note.day + " · v" + note.v, "quiet", function () {
      showRound(doc, note, b);
    });
    els.roundList.appendChild(b);
    if (!i) showRound(doc, note, b);
  });
  els.round.hidden = false;
}

function showRound(doc, note, button) {
  var all = els.roundList.querySelectorAll("button");
  for (var i = 0; i < all.length; i++) all[i].classList.remove("on");
  if (button) button.classList.add("on");
  els.roundText.textContent = "reading…";
  /* THE ID AND THE NAME, both matched on the server against what discovery
     found beside this document. Never a path -- the server holds the only
     mapping from one to the other. */
  fetch("/library/note/" + encodeURIComponent(doc.id) + "/"
        + encodeURIComponent(note.name), { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (got) {
      els.roundText.textContent = (got && got.ok)
        ? (got.text || "") + (got.truncated ? "\n\n… (longer than this)" : "")
        : "That round could not be read: "
          + ((got && got.error) || "the board refused it") + ".";
    })
    .catch(function () {
      els.roundText.textContent = "The board is not answering.";
    });
}

els.roundClose.onclick = function () { els.round.hidden = true; };

els.noteSend.onclick = function () {
  var said = els.noteText.value.trim();
  var aim = els.purpose.value.trim();
  var ink = (noteFor && noteFor.marks && noteFor.marks.pages) || 0;
  if (!noteFor) return;
  if (noteAsk === "rework" ? aim.length < PURPOSE_LEAST : (!said && !ink)) return;
  var asked = noteAsk;
  var was = els.noteSend.textContent;
  var forDoc = noteFor.id;
  els.noteSend.disabled = true;
  els.noteSend.textContent = asked === "rework" ? "overhauling…" : "sending…";
  fetch("/library/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    /* THE ID, and the page if there is one. Never the path -- the server holds
       the only mapping from one to the other. `ask` is which of the two this
       is, and `purpose` is what an overhaul is written to. */
    body: JSON.stringify({ document: forDoc, text: said, page: notePage,
                           ask: asked, purpose: aim })
  }).then(function (r) {
    return r.json().catch(function () { return {}; });
  }).then(function (got) {
    els.noteSaid.hidden = false;
    if (!got || got.ok === false) {
      els.noteSaid.className = "note-said bad";
      /* A REFUSAL NAMES WHAT IS IN THE WAY and nothing was written -- an
         overhaul against an uncommitted source is the one that matters, since
         git is the only undo it has. Said here in the server's own words. */
      els.noteSaid.textContent = ((got && got.error)
        || "the board refused it") + ".";
      els.noteSend.disabled = false;
      els.noteSend.textContent = was;
      return;
    }
    els.noteSaid.className = "note-said";
    els.noteSaid.textContent = "Filed at " + got.rel + ". "
      + (got.marks
         ? "Your marks on " + got.marks
           + (got.marks === 1 ? " page went" : " pages went") + " with it. "
         : "")
      + (got.detail || "");
    els.noteSend.textContent = "sent";
    els.noteText.value = "";
    els.purpose.value = "";
    /* WHAT IS NOW IN FLIGHT. The reply says a turn was woken, which is not the
       same as the document having changed -- so this is held against the
       document's own stamp and is cleared by its bytes moving, nothing else. */
    if (got.asked) {
      remember({ id: forDoc, ask: asked, at: Date.now(),
                 stamp: stamps[forDoc] || "" });
      paintFlight();
    }
    /* The list carries how many rounds a document has had, so it is worth
       being right about a second after one lands. */
    load();
  }).catch(function () {
    els.noteSaid.hidden = false;
    els.noteSaid.className = "note-said bad";
    els.noteSaid.textContent = "The board is not answering; nothing was written.";
    els.noteSend.disabled = false;
    els.noteSend.textContent = was;
  });
};

/* ==========================================================================
   WHAT THIS WORKSPACE HAS PRODUCED
   ==========================================================================
   A mission's card ends by naming what it wrote -- "figure
   `neighbor_count_sweep.png` and four tables are in ..." -- and there was
   nowhere to look at any of it. `course/results.py` already knew where every
   one of them was: the board's drawer puts a figure in a card, and what was
   missing was the list.

   Three things this keeps, and none of them is new:

     1. AN ID, NEVER A PATH, the same as everything else on this page. A figure
        is `/result/<id>` -- the route the drawer already uses -- and a table is
        `/library/table/<id>`. Nothing here builds a path and nothing here has
        ever seen one: the server drops `rel` before it sends a row.
     2. THE DIRECTORY IS THE GROUP, closed until it is opened. Sixty-eight
        directories and six hundred figures is not a list; sixty-eight headings
        is. The newest is open on arrival, because the result somebody has come
        to look at is the one that just landed.
     3. A TABLE IS READ, NOT DOWNLOADED. A CSV handed to an iPad is a file
        nobody can find again. The server reads the head of it and sends rows.
   ========================================================================== */
var groups = [];
var openGroup = null;        /* the directory whose rows are drawn */
var findWords = "";

function loadResults() {
  fetch("/library/results.json", { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (got) { paintResults(got || {}); })
    .catch(function () {
      /* Silent rather than shouting: the documents half of this page has its
         own way of saying the board is not answering, and two copies of that
         sentence on one screen is one fault reported twice. */
      els.res.hidden = true;
    });
}

function paintResults(got) {
  groups = got.groups || [];
  els.res.hidden = false;
  if (openGroup === null && groups.length) openGroup = groups[0].where;
  var figs = got.figures || 0;
  var tabs = got.tables || 0;
  els.resCount.textContent = groups.length
    ? [groups.length + (groups.length === 1 ? " directory" : " directories"),
       figs + (figs === 1 ? " figure" : " figures"),
       tabs + (tabs === 1 ? " table" : " tables"),
       /* A CAP THAT SAYS NOTHING READS AS "this is all there is", which is
          `scopes.offered`'s reason for carrying its count and is this one. */
       got.more ? got.more + " more directories are not listed" : ""
      ].filter(Boolean).join("  ·  ")
    : "";
  els.resFind.hidden = !groups.length;
  /* THE FENCE IS SAID OUT LOUD EVEN WHERE THERE IS A LIST. A page that quietly
     leaves a directory out is a page somebody scrolls looking for what they
     know is on disk. `tutorboard/fenced.py` is the one list, and this is it
     said where the missing rows would have been. */
  var sealed = got.fenced || [];
  els.resFenced.hidden = !sealed.length;
  els.resFenced.textContent = sealed.length
    ? (sealed.length === 1 ? "The directory " : "The directories ")
        + sealed.map(function (n) { return n + "/"; }).join(", ") + " "
        + (sealed.length === 1 ? "is" : "are")
        + " session content. Nothing on this board looks inside, so nothing in "
        + (sealed.length === 1 ? "it" : "them") + " is listed here."
    : "";
  els.resNone.hidden = !!groups.length;
  if (!groups.length) {
    /* WHY IT IS EMPTY, in the server's own words. The two reasons are
       different enough to matter: a course has no results directory, and a
       workspace whose output is session content has one nothing may look
       inside. An empty box explains neither. */
    els.resNone.textContent = got.why
      || "Nothing in this workspace has produced a figure or a table yet.";
  }
  drawGroups();
}

/* MATCHED ON THE FILENAME AS THE CARD WROTE IT, and on the directory. A card
   says `neighbor_count_sweep.png`; typing that has to land on the row. */
function hit(rec) {
  if (!findWords) return true;
  return (rec.file + " " + rec.name + " " + rec.where)
    .toLowerCase().indexOf(findWords) >= 0;
}

function drawGroups() {
  els.resList.innerHTML = "";
  var shownAny = 0;
  groups.forEach(function (g) {
    var figs = (g.figures || []).filter(hit);
    var tabs = (g.tables || []).filter(hit);
    if (!figs.length && !tabs.length) return;
    shownAny += 1;
    var box = document.createElement("div");
    box.className = "res-group";

    var head = document.createElement("button");
    head.type = "button";
    head.className = "res-dir";
    head.dataset.where = g.where;
    /* Open where the search put it: a filter that hides the matches inside a
       closed heading is a search that says "found it" and shows nothing. */
    var open = findWords ? true : (openGroup === g.where);
    head.setAttribute("aria-expanded", open ? "true" : "false");
    head.textContent = g.where;
    var tail = document.createElement("span");
    tail.className = "res-dir-sub";
    tail.textContent = [
      figs.length + (figs.length === 1 ? " figure" : " figures"),
      tabs.length ? tabs.length + (tabs.length === 1 ? " table" : " tables") : "",
      g.iso || "",
      g.more ? g.more + " more not listed" : ""
    ].filter(Boolean).join("  ·  ");
    head.appendChild(tail);
    head.addEventListener("click", function () {
      openGroup = (openGroup === g.where) ? "" : g.where;
      drawGroups();
    });
    box.appendChild(head);

    if (open) {
      var rows = document.createElement("div");
      rows.className = "res-rows";
      figs.concat(tabs).forEach(function (rec) {
        rows.appendChild(resultRow(rec));
      });
      box.appendChild(rows);
    }
    els.resList.appendChild(box);
  });
  if (!shownAny && groups.length) {
    var said = document.createElement("p");
    said.className = "lib-none";
    said.textContent = "Nothing here is called “" + findWords + "”.";
    els.resList.appendChild(said);
  }
}

function resultRow(rec) {
  var b = document.createElement("button");
  b.type = "button";
  b.className = "res-row res-" + rec.kind;
  b.dataset.id = rec.id;
  var name = document.createElement("span");
  name.className = "res-name";
  /* THE FILENAME, NOT THE PRETTIED ONE. `_pretty` is right for a drawer, where
     a figure is being chosen; here the reader arrived holding a filename a
     card gave them, and a row that has quietly renamed it is a row they scroll
     straight past. */
  name.textContent = rec.file;
  b.appendChild(name);
  var meta = document.createElement("span");
  meta.className = "res-meta";
  meta.textContent = [rec.kind === "figure" ? "figure" : rec.format,
                      size(rec.size), rec.iso].filter(Boolean).join("  ·  ");
  b.appendChild(meta);
  b.addEventListener("click", function () { show(rec); });
  return b;
}

function size(n) {
  if (!n) return "";
  if (n < 1000) return n + " B";
  if (n < 1000000) return Math.round(n / 1000) + " kB";
  return (n / 1000000).toFixed(1) + " MB";
}

/* ------------------------------------------------- one result, on the glass */
function show(rec) {
  els.shown.hidden = false;
  els.shownName.textContent = rec.file;
  els.shownSub.textContent = rec.where;
  els.shownBody.innerHTML = "";
  els.shownBody.scrollTop = 0;
  if (rec.kind === "figure") {
    var img = document.createElement("img");
    img.className = "res-figure";
    img.alt = rec.name;
    /* `/result/<id>`, which is the route the board's own drawer uses and which
       `sw.js` sends to the network always -- the next job rewrites a figure at
       the same name, so a cached one is last week's result under this week's
       label. */
    img.src = "/result/" + encodeURIComponent(rec.id);
    img.onerror = function () {
      els.shownBody.innerHTML = "";
      els.shownBody.appendChild(saidLine(
        "That figure is not there any more. A job rewrites this directory, so "
          + "reload the page to see what is in it now."));
    };
    els.shownBody.appendChild(img);
    return;
  }
  els.shownBody.appendChild(saidLine("Reading it…"));
  fetch("/library/table/" + encodeURIComponent(rec.id),
        { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (got) { drawTable(rec, got || {}); })
    .catch(function () {
      els.shownBody.innerHTML = "";
      els.shownBody.appendChild(saidLine("The board is not answering."));
    });
}

function saidLine(text) {
  var p = document.createElement("p");
  p.className = "res-said";
  p.textContent = text;
  return p;
}

function drawTable(rec, got) {
  els.shownBody.innerHTML = "";
  if (!got.ok) {
    els.shownBody.appendChild(saidLine(got.detail || "That is not readable."));
    return;
  }
  if (got.shape === "rows") {
    var t = document.createElement("table");
    t.className = "res-table";
    if ((got.columns || []).length) {
      var thead = document.createElement("thead");
      var hr = document.createElement("tr");
      got.columns.forEach(function (c) {
        var th = document.createElement("th");
        th.textContent = c;
        hr.appendChild(th);
      });
      thead.appendChild(hr);
      t.appendChild(thead);
    }
    var body = document.createElement("tbody");
    (got.rows || []).forEach(function (row) {
      var tr = document.createElement("tr");
      row.forEach(function (c) {
        var td = document.createElement("td");
        td.textContent = c;
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
    t.appendChild(body);
    /* HOW MUCH OF IT THIS IS. `sweep_curve.csv` is a hundred thousand rows and
       three hundred of them are on the glass; a page that shows the head and
       says nothing has shown somebody a different table. */
    if (got.more) {
      els.shownBody.appendChild(saidLine(
        (got.rows || []).length + " rows of "
          + (got.capped ? "at least " : "")
          + ((got.rows || []).length + got.more) + "."));
    }
    els.shownBody.appendChild(t);
    return;
  }
  if (got.why === "big") {
    els.shownBody.appendChild(saidLine(got.detail || "That is too big to show."));
    return;
  }
  if (got.more) {
    els.shownBody.appendChild(saidLine("The first part of it; it is "
      + size(got.size) + " altogether."));
  }
  var pre = document.createElement("pre");
  pre.className = "res-text";
  pre.textContent = got.text || "";
  els.shownBody.appendChild(pre);
}

function closeShown() {
  els.shown.hidden = true;
  els.shownBody.innerHTML = "";
}

els.shownClose.onclick = closeShown;
els.resFind.addEventListener("input", function () {
  findWords = (els.resFind.value || "").trim().toLowerCase();
  drawGroups();
});

document.addEventListener("keydown", function (ev) {
  if (ev.key !== "Escape") return;
  if (!els.shown.hidden) closeShown();
  else if (!els.round.hidden) els.roundClose.onclick();
  else if (!els.note.hidden) els.noteCancel.onclick();
  else if (!els.reader.hidden) closeReader();
});

paintPen();
load();
loadResults();
poll();
/* A document is rebuilt by a job, a compile, or the revision this page just
   asked for. While the page is in front of somebody the stamp poll is what
   notices; coming BACK to it after it was backgrounded re-asks both, because
   the poll stops when the tab does. */
document.addEventListener("visibilitychange", function () {
  if (document.hidden) {
    if (stampTimer) clearTimeout(stampTimer);
    stampTimer = null;
    return;
  }
  load();
  /* The results too: a job that finished while the lid was shut is exactly the
     thing somebody comes back to this page to look at. */
  loadResults();
  poll();
});
