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
        is and asks for the revision.
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

/* WHOSE LIBRARY THIS IS. Under `/s/<id>/library` it is that session's subject,
   and every route goes back under the prefix. Unprefixed, `?subject=<id>`
   names the subject and rides on every subject route. `libUrl` is the one
   place either is added; `libFetch` fetches through it. */
function sessionBase() {
  var m = /^\/s\/[^\/]+/.exec(location.pathname || "");
  return m ? m[0] : "";
}
var BASE = sessionBase();
var SUBJECT = "";
try { SUBJECT = new URLSearchParams(location.search).get("subject") || ""; }
catch (e) { SUBJECT = ""; }

function libUrl(path) {
  if (typeof path !== "string" || path.charAt(0) !== "/" || path.charAt(1) === "/"
      || path.indexOf("/static/") === 0) return path;
  if (BASE) return path.indexOf(BASE + "/") === 0 ? path : BASE + path;
  if (!SUBJECT || /[?&]subject=/.test(path)) return path;
  return path + (path.indexOf("?") === -1 ? "?" : "&")
    + "subject=" + encodeURIComponent(SUBJECT);
}

function libFetch(path, init) { return fetch(libUrl(path), init); }

/* One origin serves every session and subject, so what this device remembers
   about a library is kept per session, or per subject outside one. `scoped`
   adds that to a key; with neither, the key is as written. */
var LIB_SCOPE = BASE ? "s:" + decodeURIComponent(BASE.slice(3))
              : SUBJECT ? "subject:" + SUBJECT : "";
function scoped(key) { return LIB_SCOPE ? key + LIB_SCOPE + ":" : key; }

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
  readerChanges: document.getElementById("reader-changes"),
  readerClose: document.getElementById("reader-close"),
  readerZoom: document.getElementById("reader-zoom"),
  readerSaid: document.getElementById("reader-said"),
  readerKept: document.getElementById("reader-kept"),
  readerKeep: document.getElementById("reader-keep"),
  readerCopy: document.getElementById("reader-copy"),
  readerCopySaid: document.getElementById("reader-copy-said"),
  readerCopySave: document.getElementById("reader-copy-save"),
  readerRebuilt: document.getElementById("reader-rebuilt"),
  readerRebuiltSaid: document.getElementById("reader-rebuilt-said"),
  readerRebuiltKeep: document.getElementById("reader-rebuilt-keep"),
  note: document.getElementById("note"),
  noteTitle: document.getElementById("note-title"),
  noteWhere: document.getElementById("note-where"),
  noteText: document.getElementById("note-text"),
  notePage: document.getElementById("note-page"),
  noteMarks: document.getElementById("note-marks"),
  noteItems: document.getElementById("note-items"),
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
  libFigures: document.getElementById("lib-figures"),
  resView: document.getElementById("res-view"),
  resAsGrid: document.getElementById("res-as-grid"),
  resAsList: document.getElementById("res-as-list"),
  resPick: document.getElementById("res-pick"),
  galDir: document.getElementById("gal-dir"),
  galOrder: document.getElementById("gal-order"),
  resGridCount: document.getElementById("res-grid-count"),
  resGrid: document.getElementById("res-grid"),
  shown: document.getElementById("shown"),
  shownName: document.getElementById("shown-name"),
  shownSub: document.getElementById("shown-sub"),
  shownBody: document.getElementById("shown-body"),
  shownNav: document.getElementById("shown-nav"),
  shownPrev: document.getElementById("shown-prev"),
  shownNext: document.getElementById("shown-next"),
  shownAt: document.getElementById("shown-at"),
  shownFit: document.getElementById("shown-fit"),
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
                          title: "back to everything" },
                  /* The board reopens on the map it was left on. */
                  map: { href: BASE + "/board", text: "\u2039 Map",
                         title: "back to the map" } };

(function backWhereYouCameFrom() {
  var el = els.back;
  if (!el) return;
  /* Under a session, its board; a subject's library outside one has no board
     to go back to, so it goes back to everything. */
  if (BASE) {
    Array.prototype.forEach.call(document.querySelectorAll('a[href^="/board"]'),
      function (a) { a.setAttribute("href", BASE + a.getAttribute("href")); });
  }
  var from = "";
  try { from = new URLSearchParams(location.search).get("from") || ""; }
  catch (e) { from = ""; }
  var want = CAME_FROM[from] || (!BASE && SUBJECT ? CAME_FROM.home : null);
  if (!want) return;
  el.href = want.href;
  el.textContent = want.text;
  el.title = want.title;
})();

/* The board's own theme is `typeface.js`'s (`Typeface.theme`), applied
   before this page draws: one choice that follows the person from surface to
   surface. */

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
var FLIGHT_KEY = LIB_SCOPE ? "library.flight:" + LIB_SCOPE : "library.flight";
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
  libFetch("/library.json", { credentials: "same-origin" })
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
    /* A WIPE CAN HAPPEN IN THIS VERY REPLY, with nothing moved on disk that
       would re-draw the reader, so what it took comes off the glass here. */
    if (openDoc.wiped) takeInk(openDoc, null, openDoc.wiped);
    if (ledger && !els.reader.hidden) ledger.open(openDoc);
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

  openWanted();

  /* THREE GROUPS, IN THE SERVER'S ORDER: what the board made (each with its
     doc.json), what was already here, and the materials put here to be read.
     A heading only once there is more than one of them. Inside each group,
     GROUPED BY DIRECTORY, because the directory is the group: four stems in
     `paper1-trd-prediction/` are one piece of work, and a flat list of fifty
     rows says nothing about which those four are. */
  subject = got.subject || "";
  var groups = {};
  docs.forEach(function (d) { groups[d.group || "legacy"] = true; });
  var many = Object.keys(groups).length > 1;
  var here = null, part = null;
  docs.forEach(function (doc) {
    var g = doc.group || "legacy";
    if (many && g !== part) {
      part = g;
      here = null;
      var gh = document.createElement("div");
      gh.className = "lib-group";
      gh.textContent = GROUP_WORDS[g] || g;
      els.list.appendChild(gh);
    }
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

/* THE DOCUMENT THE CALLER CAME FOR, opened once. The front door's deck from
   sittings lands here with `?doc=<id>`, because "Read the deck" that drops
   somebody on a list of forty documents has made them find it. An id the list
   does not have is a miss and opens nothing; asked once, so a reload of the
   list does not reopen a reader somebody has closed. */
var docAsked = null;
/* AND THE PAGE, where the caller named one: a thread sheet's write-up row asks
   for the page its heading is on, with `&page=<n>`. */
var pageAsked = 0;

function openWanted() {
  if (docAsked === null) {
    try {
      var q = new URLSearchParams(location.search);
      docAsked = q.get("doc") || "";
      pageAsked = Math.max(0, parseInt(q.get("page") || "0", 10) || 0);
    } catch (e) { docAsked = ""; }
  }
  if (!docAsked) return;
  var want = docAsked;
  docs.forEach(function (d) {
    if (d.id === want && d.pdf && docAsked) {
      docAsked = "";
      read(d, false, pageAsked);
      pageAsked = 0;
    }
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
  libFetch("/library/stamp", { credentials: "same-origin" })
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

var GROUP_WORDS = { artifact: "Made here", legacy: "Already here",
                    material: "Materials" };
var subject = "";            /* the subject this library is of, from the server */

/* WHERE AN ASKED-FOR DOCUMENT GOT TO, from its doc.json and mtimes. */
var STATUS_WORDS = { writing: "being written", failed: "did not land" };

function row(doc) {
  var box = document.createElement("div");
  box.className = "lib-row";
  box.dataset.group = doc.group || "legacy";

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
    doc.group === "material" ? "material"
      : (doc.type || (doc.kind === "deck" ? "deck" : "paper")),
    doc.stem,
    (doc.formats || []).join(" · "),
    doc.pages ? doc.pages + (doc.pages === 1 ? " page" : " pages") : "",
    doc.pdf ? (doc.iso ? "built " + doc.iso : "") : "no PDF yet"
  ].filter(Boolean).join("  ·  ");
  box.appendChild(meta);

  if (STATUS_WORDS[doc.status]) {
    var st = document.createElement("span");
    st.className = "lib-status";
    st.dataset.status = doc.status;
    st.textContent = STATUS_WORDS[doc.status];
    box.appendChild(st);
  }

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

  /* HOW MANY REQUESTS ARE STILL OPEN, and the way to them: the reader, with
     the changes pinned. A request is closed by accepting it, not by a round
     having happened. */
  if (doc.ledger && doc.ledger.rounds) {
    var open = document.createElement("button");
    open.type = "button";
    open.className = "lib-ledger";
    open.textContent = (doc.ledger.open
      ? doc.ledger.open + " of " + doc.ledger.items
        + (doc.ledger.items === 1 ? " request" : " requests") + " open"
      : "every request accepted")
      + (doc.pdf ? " — see the changes" : "");
    open.disabled = !doc.pdf;
    open.addEventListener("click", function () { read(doc, true); });
    box.appendChild(open);
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
  if (doc.group !== "material") {
    acts.appendChild(act("say what is wrong", "quiet", function () {
      say(doc, 0);
    }));
  }
  /* DELETE TAKES A SECOND TAP, and only a document with a doc.json offers it:
     what was already here is somebody's own tree. */
  if (doc.artifact) acts.appendChild(deleteButton(doc));
  box.appendChild(acts);
  return box;
}

function deleteButton(doc) {
  var armed = null;
  var b = act("delete", "quiet lib-delete", function () {
    if (!armed) {
      b.textContent = "tap again to delete";
      b.classList.add("armed");
      armed = setTimeout(function () {
        armed = null;
        b.textContent = "delete";
        b.classList.remove("armed");
      }, 4000);
      return;
    }
    clearTimeout(armed);
    armed = null;
    b.disabled = true;
    b.textContent = "deleting";
    libFetch("/doc/delete", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject: subject, id: doc.id })
    }).then(function (r) {
      return r.json().catch(function () { return {}; });
    }).then(function (got) {
      if (got && got.ok) {
        if (openDoc && openDoc.id === doc.id) closeReader();
        load();
        return;
      }
      b.disabled = false;
      b.classList.remove("armed");
      b.textContent = (got && got.error) || "could not delete";
    }).catch(function () {
      b.disabled = false;
      b.classList.remove("armed");
      b.textContent = "the board is not answering";
    });
  });
  return b;
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
/* THE ONE READER, `reader.js`: the pages, the pinch, the marked copy and every
   save of the ink are its. What is this page's own is the ledger's pins, the
   place kept across a re-draw, and the flag for ink drawn on another build. */
var reader = window.Reader ? window.Reader.mount({
  url: libUrl,
  /* A pinch takes the document off the re-draw's restore, and the page it
     lands on is the new anchor. */
  committed: function () { placeWanted = 0; noteAnchor(); },
  keep: {
    /* Only for the document on the glass: that is the only build this page
       knows it drew. */
    build: function (id) { return openBuild && mineKey(id) ? openBuild : null; },
    url: libUrl("/annotate/save"),
    paint: function () { paintKept(); },
    saved: function (done) {
      if (done.some(function (d) { return d.ok; })) load();
    }
  }
}) : null;
var zoomer = reader ? reader.zoomer : null;

function read(doc, changes, page) {
  openDoc = doc;
  /* THE ROUNDS' REQUESTS, as pins on these pages -- on from the row's "see the
     changes", off (and one tap away) otherwise. */
  if (ledger) ledger.open(doc, !!changes);
  openBuild = null;
  paintRebuilt(null);
  openPages = 0;
  drawnPages = 0;
  if (!reader) return;
  /* A page asked for is a place to be put, the way a re-draw puts the reader
     back: `keepPlace` lands on it as the pictures above it arrive. */
  reader.open({
    pagesUrl: libUrl("/library/view/" + encodeURIComponent(doc.id)),
    id: doc.id, title: doc.title || doc.stem,
    burn: "library/" + doc.id,
    place: page > 1 ? page : 0,
    src: libUrl,
    drawing: drawing, page: pageMade, ink: inkCame, drawn: drawn,
    paint: paintKept,
    onClose: closed
  });
}

/* THE SAME DOCUMENT AGAIN, BECAUSE ITS BYTES MOVED. Asked for by the stamp
   poll, never by the reader: a revision was dispatched in the same request that
   filed the note, and this is the half where it appears in front of you.

   The render cache is keyed on the PDF's own modification time -- `paper._digest`
   -- so a re-fetch gets the new pages rather than the old ones out of a cache. */
function redraw() {
  if (!openDoc || !reader || !reader.current) return;
  /* Never under a nib. Emptying the pages mid-stroke takes the page the stroke
     is on away from it, so the re-draw waits for the lift. */
  if (window.Annotate && window.Annotate.busy && window.Annotate.busy()) {
    setTimeout(redraw, 250);
    return;
  }
  var page = pageInView();
  reader.redraw(page, page ? pageOffset(page) : 0);
}

/* How far the page's top edge sits below the scroller's, so a re-draw puts it
   back to the pixel rather than to the top of the page. */
function pageOffset(n) {
  var el = els.readerPages.querySelector('.lib-page[data-page="' + n + '"]');
  if (!el) return 0;
  return el.getBoundingClientRect().top
    - els.readerPages.getBoundingClientRect().top;
}

/* WHERE THE READER WAS, PUT BACK. A picture has no height until it has decoded,
   so a scroll position set the instant the markup exists lands nowhere: the
   page is restored as the images above it arrive, and stops being restored once
   they all have. Otherwise a 33-page deck comes back at page 1 after a one-line
   fix, which is its own defect. */
var placeWanted = 0;
var placeAt = 0;
var placeUntil = 0;

function keepPlace() {
  if (!placeWanted || Date.now() > placeUntil) { placeWanted = 0; return; }
  var want = els.readerPages.querySelector(
    '.lib-page[data-page="' + placeWanted + '"]');
  if (!want) return;
  /* Against the SCROLLER'S OWN rectangle, for the reason `pageInView` gives:
     `offsetTop` is measured from whichever ancestor happens to be positioned. */
  var top = els.readerPages.getBoundingClientRect().top + placeAt;
  els.readerPages.scrollTop += want.getBoundingClientRect().top - top;
  noteAnchor();
}

/* THE PAGE STAYS UNDER THE PEN. The pen reads a page's rectangle once, when
   the nib lands (`annotate.js`, `follow`), and corrects it only for a scroll --
   so anything that moves the pages by LAYOUT puts the rest of the stroke off by
   exactly that much, and puts the next word somewhere the hand did not aim.
   Here the pages move by layout all the time: the bar re-wraps as *saved · 12
   pages* grows, a line above the pages appears or re-words itself on every
   stamp poll, and a picture that decodes above the glass pushes everything
   under it down. iOS Safari has no scroll anchoring, so this is it by hand:
   the page on the glass keeps its place on the screen, whatever above it
   changed size. `overflow-anchor: none` in `library.css` keeps a browser that
   has its own from correcting twice. */
var anchor = null;          /* { el, top }: a page and where it was on screen */
var anchorWatch = null;

function noteAnchor() {
  var pages = els.readerPages.querySelectorAll(".lib-page");
  var top = els.readerPages.getBoundingClientRect().top;
  anchor = null;
  for (var i = 0; i < pages.length; i++) {
    var r = pages[i].getBoundingClientRect();
    if (r.bottom > top) { anchor = { el: pages[i], top: r.top }; return; }
  }
}

function holdAnchor() {
  if (els.reader.hidden) return;
  if (placeWanted && Date.now() <= placeUntil) { keepPlace(); return; }
  if (!anchor || !anchor.el.isConnected) { noteAnchor(); return; }
  var moved = anchor.el.getBoundingClientRect().top - anchor.top;
  if (moved) els.readerPages.scrollTop += moved;
  noteAnchor();
}

function watchLayout(el) {
  if (!el) return;
  if (!anchorWatch) {
    if (typeof window.ResizeObserver !== "function") return;
    anchorWatch = new window.ResizeObserver(holdAnchor);
  }
  anchorWatch.observe(el);
}

els.readerPages.addEventListener("scroll", noteAnchor, { passive: true });
[document.getElementById("reader-bar"), els.readerSaid, els.readerRebuilt,
 els.readerCopy].forEach(watchLayout);

/* THE ROUND AS PAIRS -- what was written, and what was done -- with a pip on
   the page for each: `ledger.js`. A pair judged asks for the list again,
   because the row says how many are open; a jump is a scroll of our own, so
   the anchor is taken where it landed; and "not fixed — send them" is the
   filing panel, which carries every reopened pair. */
var ledger = window.Ledger ? window.Ledger.make({
  pages: els.readerPages, button: els.readerChanges, changed: load, url: libUrl,
  zoom: zoomer,
  send: function (doc) { say(doc, 0); },
  scrolled: function () { placeWanted = 0; noteAnchor(); },
}) : null;

/* The reader's hooks for one drawing of the open document. */
function drawing(h, place, at) {
  openPages = 0;
  placeWanted = place || 0;
  placeAt = at || 0;
  /* Eight seconds is the whole budget for putting somebody back where they
     were. Past that they have scrolled somewhere themselves and a jump is
     the page taking the document off them. */
  placeUntil = Date.now() + 8000;
  paintReaderSaid();
}

function pageMade(fig, img) {
  watchLayout(fig);
  img.addEventListener("load", keepPlace);
}

/* Marks made on this document before, put back. They came with the pages:
   this page holds no live payload to read them out of, because it opens no
   sitting. KEPT ACROSS A RE-DRAW for the same reason -- the keys are
   `doc/<id>/p<n>` and are the document's, not this drawing's. */
function inkCame(got) {
  if (openDoc) takeInk(openDoc, got.ink || {}, got.wiped || null);
}

function drawn(got, h) {
  openPages = h.pages;
  /* THE BUILD ON THE GLASS, handed back with every save of this document's
     ink -- and the flag, when ink on it was drawn on another. */
  openBuild = got.build || null;
  paintRebuilt(got.rebuilt || null);
  /* HOW MANY PAGES THE INK WAS DRAWN ON. Taken the first time this document
     is drawn with marks on it, so a later re-draw can say out loud that the
     deck reflowed under them. */
  if (!drawnPages && window.Annotate && window.Annotate.marked().length) {
    drawnPages = openPages;
  }
  keepPlace();
  paintPen();
  paintKept();
  paintReaderSaid();
  /* The pins go on the pages just drawn, and are asked for again: a re-draw
     is a rebuild, and a rebuild is where a round's answers land. */
  if (ledger) { ledger.redraw(); ledger.refresh(); }
}

/* ONE STROKE, COMPARABLE. Every field but the `_` caches, keys sorted: the
   glass's copy and the server's buried one both parse from the same JSON. */
function inkSig(s) {
  var o = {};
  Object.keys(s || {}).sort().forEach(function (k) {
    if (k.charAt(0) !== "_") o[k] = s[k];
  });
  return JSON.stringify(o);
}

/* THE SERVER'S INK FOR `doc`, put on the glass. SPENT INK GOES FROM IT TOO,
   because `load` never takes a mark away -- this device's copy wins. A saved
   page the server no longer has is dropped. A page the server still has keeps
   this device's copy, because a view can be older than the last save, unless
   the server says it changed it: `wiped`, the strokes a landed round's wipe
   took off (`library.wiped`). A saved page showing any of those is dropped
   and taken again. A page still owed a save keeps its new ink and loses just
   those strokes (`Annotate.shed`), so its save cannot write them back. With
   no `have` (the list's reply), every page sheds them. */
function takeInk(doc, have, wiped) {
  if (!window.Annotate) return;
  var A = window.Annotate;
  if (A.drop) {
    var owed = A.unsaved();
    var mine = "doc/" + doc.id + "/";
    A.marked().forEach(function (id) {
      if (id.indexOf(mine) !== 0) return;
      var gone = wiped && wiped[id] ? wiped[id].map(inkSig) : [];
      var taken = function (s) { return gone.indexOf(inkSig(s)) >= 0; };
      var shows = gone.length > 0 && A.payload(id, false).strokes.some(taken);
      if (!have || owed.indexOf(id) >= 0) {
        if (shows && A.shed) A.shed(id, taken);
        return;
      }
      if (!(id in have) || shows) {
        A.drop(id);
      }
    });
  }
  if (have) A.load(have);
}

/* Shut, by the reader's ✕ or Escape. What is owed is saved by the reader
   first; this is what is the page's to let go of. */
function closeReader() { if (reader) reader.close(); }

function closed() {
  if (window.Annotate) {
    window.Annotate.setOn(false);
    /* The store outlives the document, and the next one opened has its own
       page 1. Keeping last document's ink keyed against it would draw one
       paper's marks over another's. */
    window.Annotate.forget();
  }
  openDoc = null;
  openBuild = null;
  openPages = 0;
  drawnPages = 0;
  placeWanted = 0;
  if (ledger) ledger.close();
  els.readerSaid.hidden = true;
  paintRebuilt(null);
  paintPen();
  paintKept();
}

/* ------------------------------------------------------------- the pen */
/* ON THE PAGE, NOT ON A SECOND SURFACE. The layer is inert until this is on,
   so scrolling a long document behaves exactly as it did before. */
function paintPen() {
  var on = !!(window.Annotate && window.Annotate.isOn());
  els.readerPen.disabled = !window.Annotate || !openPages || !!penHeld;
  els.readerPen.classList.toggle("on", on);
  els.readerPen.classList.toggle("sending", !!penHeld);
  els.readerPen.textContent = penHeld ? "sending…"
    : on ? "✎ done marking" : "✎ mark it up";
  if (annBar) annBar.show(on);
  if (window.ViewPin) window.ViewPin.update();
}

els.readerPen.onclick = function () {
  if (!window.Annotate || penHeld) return;
  setPen(!window.Annotate.isOn());
};

/* THE PEN WAITS WHILE A SEND IS IN THE AIR, from its pictures to its reply.
   A stroke drawn then is either missing from a picture already taken or on a
   page the reply is about to take off the glass, and a second tap would send
   the same ink twice. So the pen is switched off and the button says
   *sending…*; it comes back on afterwards if it was on and the same document
   is still open. */
var penHeld = null;                  /* { doc, was }: the send holding the pen */

function holdPen() {
  if (!window.Annotate || penHeld) return;
  penHeld = { doc: openDoc ? openDoc.id : "", was: window.Annotate.isOn() };
  window.Annotate.setOn(false);
  paintPen();
}

function freePen() {
  if (!penHeld) return;
  var was = penHeld;
  penHeld = null;
  if (was.was && window.Annotate && openDoc && openDoc.id === was.doc) {
    window.Annotate.setOn(true);
  }
  paintPen();
}

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

/* HOW LONG A SEND WAITS FOR ONE PAGE'S IMAGE. A page is rendered by the board
   on first ask, so this is generous; past it the page goes without a picture,
   and the note goes without that page's picture.
   `window.PICTURE_WAIT_MS` overrides it. */
var PICTURE_WAIT = 10000;

function decoded(img) { return !!img && img.naturalWidth > 0; }

/* ONE PAGE'S IMAGE, LOADED AND DECODED, before a picture is made of it. Pages
   past the second are `loading="lazy"`, so one never scrolled to has no pixels
   and no height, and `Annotate.picture` makes nothing of it. So the image is
   asked for now and waited on, all within one `PICTURE_WAIT`. Switching lazy
   to eager can start a new request, which rejects a `decode()` already
   waiting; a rejection waits for the image's `load` and decodes once more.
   Resolves to whether it decoded. */
function decodePage(img) {
  if (!img) return Promise.resolve(false);
  if (decoded(img)) return Promise.resolve(true);
  img.setAttribute("loading", "eager");
  return new Promise(function (resolve) {
    var done = false;
    var finish = function () {
      if (done) return;
      done = true;
      clearTimeout(timer);
      img.removeEventListener("load", again);
      img.removeEventListener("error", finish);
      resolve(decoded(img));
    };
    var again = function () {
      img.removeEventListener("load", again);
      if (done) return;
      if (typeof img.decode !== "function") { finish(); return; }
      img.decode().then(finish, finish);
    };
    var timer = setTimeout(finish, window.PICTURE_WAIT_MS || PICTURE_WAIT);
    if (typeof img.decode === "function") {
      img.decode().then(finish, function () {
        if (done) return;
        if (img.complete && decoded(img)) again();
        else {
          img.addEventListener("load", again);
          img.addEventListener("error", finish);
        }
      });
    } else {
      img.addEventListener("load", finish);
      img.addEventListener("error", finish);
    }
  });
}

/* Each page of `docId` with ink on it, saved with a picture of the page and
   its ink (`Annotate.picture`), so the note's "open the image" has an image to
   open. EVERY SUCH PAGE IS DECODED FIRST (`decodePage`), and the layers are
   sized against the decoded pages, because a page with no picture is a page
   the send cannot carry. A page not drawn in the reader has no picture to make
   and is left alone: its strokes are already on disk. Never a send -- the
   note is the send. Resolves to the keys whose picture the board took. */
function savePictures(docId) {
  if (!window.Annotate || !window.Annotate.picture || !openDoc
      || openDoc.id !== docId) return Promise.resolve([]);
  var mine = "doc/" + docId + "/p";
  var imgOf = function (id) {
    var n = id.slice(mine.length);
    var fig = els.readerPages.querySelector('.lib-page[data-page="' + n + '"]');
    return fig && fig.querySelector("img");
  };
  var ids = window.Annotate.marked().filter(function (id) {
    return id.indexOf(mine) === 0;
  });
  var waited = ids.some(function (id) { return !decoded(imgOf(id)); });
  return Promise.all(ids.map(function (id) { return decodePage(imgOf(id)); }))
  .then(function () {
    if (waited) window.Annotate.redrawAll();
    return Promise.all(ids.map(function (id) {
      var img = imgOf(id);
      var png = img ? window.Annotate.picture(id, img) : "";
      if (!png) return Promise.resolve(null);
      var body = window.Annotate.payload(id, false);
      body.png = png;
      return libFetch("/annotate/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(body)
      }).then(function (r) { return r && r.ok ? id : null; },
              function () { return null; });
    }));
  }).then(function (got) { return got.filter(Boolean); });
}

/* WHERE THE INK IS, SAID ON THE BAR. The save itself -- kept owed on a
   failure, retried on a timer, on `online` and on the page being looked at
   again, flushed with `keepalive` when the page goes hidden -- is
   `inkkeep.js`, the one path every reader's ink takes, made by `reader.js`.
   What is this page's own is which build a key was drawn on, and the re-draw
   after a save lands: the row carries how many pages are marked, and the note
   dialog decides whether the send button is live off the same number. */
var openBuild = null;                /* the build on the glass: `got.build` */
var keeper = reader ? reader.keeper : null;

function mineKey(id) {
  return !!openDoc && id.indexOf("doc/" + openDoc.id + "/") === 0;
}

function savePen(opts) {
  return keeper ? keeper.save(opts) : Promise.resolve([]);
}

function inkOwed() { return !!keeper && keeper.owed(); }

function pagesMarked() {
  if (!window.Annotate || !openDoc) return 0;
  return window.Annotate.marked().filter(mineKey).length;
}

function paintKept() {
  if (!els.readerKept) return;
  var n = pagesMarked();
  var said = window.InkKeep
    ? window.InkKeep.words(inkOwed(), !!keeper && keeper.failed(), n)
    : { text: "", cls: "" };
  els.readerKept.textContent = said.text;
  els.readerKept.className = "reader-kept" + (said.cls ? " " + said.cls : "");
  els.readerKept.hidden = !said.text;
  if (reader) reader.paintKeep();
}

if (keeper) {
  window.Annotate.onChange(function () {
    keeper.queue();
    paintPen();
    paintKept();
  });
}
/* ------------------------------------------------ ⤓ keep a marked copy */
/* THE INK, BURNED INTO A NEW PDF, and never over the original: the reader's
   `keepCopy`, with `library/<id>`, which writes it where the library does not
   list it and git does not carry it. The rebuilt flag offers the same. */
if (els.readerRebuiltKeep) {
  els.readerRebuiltKeep.onclick = function () { if (reader) reader.keepCopy(); };
}

/* INK KNOWS ITS BUILD. A document rebuilt since its marks were drawn moves its
   text under them without a word, so the reader says so above the pages -- and
   offers the marked copy, which is burned from the build they were drawn on
   while that rendering is still in the page cache, and otherwise says it
   cannot be. */
function paintRebuilt(flag) {
  if (!els.readerRebuilt) return;
  if (!flag) { els.readerRebuilt.hidden = true; return; }
  els.readerRebuilt.hidden = false;
  els.readerRebuiltSaid.textContent = "These marks were drawn on the "
    + (flag.when || "an earlier") + " build; the document has been rebuilt since."
    + (flag.copy ? "" : " " + (flag.detail || "A marked copy of that build cannot be made."));
  els.readerRebuiltKeep.hidden = !flag.copy;
}

/* WHICH PAGE THEY ARE LOOKING AT. A note written while reading page 14 is
   about page 14, and asking for the number is a question whose answer is on the
   screen already -- so it is read off the scroll rather than typed. */
els.readerSay.onclick = function () { say(openDoc, pageInView()); };

function pageInView() { return reader ? reader.pageInView() : 0; }

/* ---------------------------------------------------- saying what is wrong */
/* ONE KIND OF INK, ONE SEND. The marks and the words go to `/library/feedback`
   as one round, and the `[revise]` turn it asks for decides what they are:
   an edit to the document's source, or where the work goes next, which it
   writes in the subject's TUTOR.md. */
function say(doc, page) {
  if (!doc) return;
  noteFor = doc;
  notePage = page || 0;
  els.noteTitle.textContent = doc.title || doc.stem;
  els.noteWhere.textContent = doc.rel;
  /* WHAT WAS BEING TYPED, BACK. Kept on this device per document on every
     keystroke, so a reload, a closed tab or an app evicted overnight costs
     nothing -- and gone only when the note is actually filed. */
  var draft = draftOf(doc.id);
  els.noteText.value = (draft && draft.text) || "";
  els.purpose.value = (draft && draft.purpose) || "";
  els.noteSaid.hidden = true;
  els.notePage.hidden = !notePage;
  if (notePage) els.notePage.textContent = "about page " + notePage;
  els.askRework.title = "restructure, cut and rewrite it to a new purpose";
  setAsk(draft && draft.ask === "rework" ? "rework" : "revise");
  noteMerge = [];
  noteSplit = [];
  askSplit();
  els.note.hidden = false;
  els.noteText.focus();
}

/* ------------------------------------------- the split, before it goes */
/* EACH INKED REGION AND EACH PARAGRAPH IS ONE REQUEST, and the panel shows
   the split the server would make -- `POST /library/ledger/preview`, which
   writes nothing -- with a tap to make a page's marks one request. Asked when
   the panel opens and again once the typing pauses. */
var noteMerge = [];
var noteSplit = [];
var splitTimer = null;
var splitAsked = 0;

function askSplit() {
  if (!noteFor) {
    noteSplit = [];
    if (window.Ledger) window.Ledger.preview(els.noteItems, [], noteMerge, toggleMerge);
    return;
  }
  var mine = ++splitAsked;
  var forDoc = noteFor.id;
  libFetch("/library/ledger/preview", {
    method: "POST", credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document: forDoc, text: els.noteText.value,
                           page: notePage, merge: noteMerge })
  }).then(function (r) { return r.json(); }).then(function (got) {
    if (mine !== splitAsked || !noteFor || noteFor.id !== forDoc) return;
    noteSplit = (got && got.ok && got.items) || [];
    if (window.Ledger) window.Ledger.preview(els.noteItems, noteSplit, noteMerge, toggleMerge);
    paintSend();
  }).catch(function () { /* the split is a courtesy; the send still works */ });
}

function toggleMerge(page) {
  var at = noteMerge.indexOf(page);
  if (at < 0) noteMerge.push(page);
  else noteMerge.splice(at, 1);
  askSplit();
}

function laterSplit() {
  if (splitTimer) clearTimeout(splitTimer);
  splitTimer = setTimeout(askSplit, window.SPLIT_WAIT || 600);
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
  paintMarksLine();
  paintSend();
  if (noteAsk === "rework") els.purpose.focus();
  if (noteFor && !els.note.hidden) askSplit();
}

// A tap on the ask is part of the draft, as a keystroke is.
els.askRevise.onclick = function () { setAsk("revise"); keepDraft(); };
els.askRework.onclick = function () { setAsk("rework"); keepDraft(); };

/* WHAT GOES WITH IT: every page of ink the note carries. */
function paintMarksLine() {
  var ink = inkWaiting(noteFor);
  els.noteMarks.hidden = !ink;
  if (ink) {
    els.noteMarks.textContent = "Your marks on " + ink
      + (ink === 1 ? " page" : " pages")
      + " go with this. Send it with nothing typed and the ink is the feedback.";
  }
}


/* Live as soon as there is either half of a complaint. The marks are already
   on disk, so nothing has to be collected here -- the server reads them where
   it reads the text. An overhaul is live on its PURPOSE instead: the words are
   optional there and the sentence saying what the document is for is not. */
/* HOW MANY PAGES OF INK A NOTE WOULD CARRY. On a deck made from sittings,
   ink an earlier round delivered is still drawn but does not go again
   (`library.carried`), so the panel counts the pages still waiting where the
   server says, and every marked page where an older server does not. */
function reopenedOn(doc) {
  return (doc && doc.ledger && doc.ledger.reopened) || 0;
}

function inkWaiting(doc) {
  var m = (doc && doc.marks) || {};
  return (typeof m.waiting === "number" ? m.waiting : m.pages) || 0;
}

function paintSend() {
  /* A REQUEST REOPENED ON AN EARLIER ROUND IS SOMETHING TO SEND, with nothing
     typed and nothing drawn: it rides the next round under its own id. */
  var ink = inkWaiting(noteFor);
  els.noteSend.disabled = noteAsk === "rework"
    ? els.purpose.value.trim().length < PURPOSE_LEAST
    : !els.noteText.value.trim() && !ink && !reopenedOn(noteFor);
}

/* ------------------------------------------------------ drafts, kept */
var DRAFT_KEY = scoped("library.draft:");

function draftKey(id) { return DRAFT_KEY + id; }

function draftOf(id) {
  try {
    var d = JSON.parse(localStorage.getItem(draftKey(id)) || "null");
    return d && typeof d === "object" ? d : null;
  } catch (e) { return null; }
}

function keepDraft() {
  if (!noteFor) return;
  var text = els.noteText.value;
  var aim = els.purpose.value;
  var key = draftKey(noteFor.id);
  try {
    if (!text.trim() && !aim.trim()) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(
      { text: text, purpose: aim, ask: noteAsk, at: Date.now() }));
  } catch (e) { /* private mode or full: the textarea still holds it */ }
}

function dropDraft(id) {
  try { localStorage.removeItem(draftKey(id)); } catch (e) {}
}

els.noteText.addEventListener("input", paintSend);
els.purpose.addEventListener("input", paintSend);
els.noteText.addEventListener("input", keepDraft);
els.noteText.addEventListener("input", laterSplit);
els.purpose.addEventListener("input", keepDraft);

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
  libFetch("/library/note/" + encodeURIComponent(doc.id) + "/"
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
  var ink = ((noteFor && noteFor.marks && noteFor.marks.pages) || 0)
    + reopenedOn(noteFor);
  if (!noteFor) return;
  if (noteAsk === "rework" ? aim.length < PURPOSE_LEAST : (!said && !ink)) return;
  var asked = noteAsk;
  var was = els.noteSend.textContent;
  var forDoc = noteFor.id;
  els.noteSend.disabled = true;
  els.noteSend.textContent = asked === "rework" ? "overhauling…" : "sending…";
  holdPen();
  /* THE PICTURES GO FIRST. The note tells the turn to open each page's image,
     and an autosave never carries one (`Annotate.payload` makes it only for a
     send). So each page of the open document carrying fix ink is saved once
     more with that ink drawn over the page itself, and only then is the note
     filed. */
  savePen().then(function () { return savePictures(forDoc); },
                 function () { return savePictures(forDoc); })
  .then(function () { return libFetch("/library/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    /* THE ID, and the page if there is one. Never the path -- the server holds
       the only mapping from one to the other. `ask` is which of the two this
       is, and `purpose` is what an overhaul is written to. */
    body: JSON.stringify({ document: forDoc, text: said, page: notePage,
                           ask: asked, purpose: aim, merge: noteMerge.slice() })
  }); }).then(function (r) {
    return r.json().catch(function () { return {}; });
  }).then(function (got) {
    freePen();
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
      + (got.items ? "It is " + got.items + (got.items === 1 ? " request" : " requests")
         + ", " + (got.ids || []).join(", ") + ", each answered by id. " : "")
      + (got.marks
         ? "Your marks on " + got.marks
           + (got.marks === 1 ? " page went" : " pages went") + " with it. "
         : "")
      + (got.detail || "");
    els.noteSend.textContent = "sent";
    els.noteText.value = "";
    els.purpose.value = "";
    /* FILED, so the draft goes -- here and nowhere earlier. A refusal above
       returned before this line, and its words are still waiting. */
    dropDraft(forDoc);
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
    freePen();
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
var resWhy = "";             /* the server's sentence for an empty walk */

function loadResults() {
  libFetch("/library/results.json", { credentials: "same-origin" })
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
  /* AND A WAY DOWN TO THEM FROM THE TOP OF THE PAGE. The documents come first
     -- forty-five of them in Galois-Theory -- so a gallery under that list is
     a surface somebody has to already know is there. */
  els.libFigures.hidden = !figs;
  els.libFigures.textContent = figs
    ? "▦ " + figs + (figs === 1 ? " figure" : " figures") : "";
  els.libFigures.title = figs
    ? "everything this workspace has produced" : "";
  /* THE SWITCH IS THERE WHATEVER THE WALK FOUND, because the gallery of a
     workspace with no figures is where the reason has to be readable too -- a
     fenced one that offered no way in would be a refusal nobody can see. */
  els.resView.hidden = false;
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
  /* WHY IT IS EMPTY, in the server's own words, and kept rather than only
     painted: the gallery needs the same sentence where its pictures would
     have been. The two reasons are different enough to matter -- a course has
     no results directory, and a workspace whose output is session content has
     one nothing may look inside. An empty box explains neither. */
  resWhy = got.why
    || "Nothing in this workspace has produced a figure or a table yet.";
  if (!groups.length) els.resNone.textContent = resWhy;
  drawPick();
  applyView();
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
/* WHICH FIGURES THIS IS ONE OF, AND WHERE IN THEM. A figure opened from either
   surface is opened as a position in the order showing, so the stepper can move
   without going back -- which is the whole reason to be in here rather than on
   the grid, because two figures are being compared. A table has nothing to step
   to and the stepper is not drawn for one. */
var shownOrder = [];
var shownAt = -1;

function show(rec) {
  var order = rec.kind === "figure" ? figuresNow() : [];
  var at = -1;
  for (var i = 0; i < order.length; i++) {
    if (order[i].id === rec.id) { at = i; break; }
  }
  shownOrder = order;
  shownAt = at;
  paintShown(rec, false);
}

/* A STEP KEEPS THE ZOOM. Somebody at 300% on the left-hand tail of one ROC
   curve is stepping in order to look at the same tail of the next one, and a
   step that refitted would put them back at the whole picture every time. */
function stepFigure(d) {
  if (shownAt < 0) return;
  var want = shownAt + d;
  if (want < 0 || want >= shownOrder.length) return;
  shownAt = want;
  paintShown(shownOrder[want], true);
}

function paintShown(rec, keep) {
  els.shown.hidden = false;
  els.shownName.textContent = rec.file;
  els.shownSub.textContent = rec.where;
  dropPlane();
  els.shownBody.innerHTML = "";
  els.shownBody.scrollTop = 0;
  var many = rec.kind === "figure" && shownOrder.length > 1 && shownAt >= 0;
  els.shownNav.hidden = !many;
  els.shownFit.hidden = rec.kind !== "figure";
  els.shown.classList.toggle("on-figure", rec.kind === "figure");
  if (many) {
    els.shownAt.textContent = (shownAt + 1) + " of " + shownOrder.length;
    els.shownPrev.disabled = shownAt <= 0;
    els.shownNext.disabled = shownAt >= shownOrder.length - 1;
  }
  if (rec.kind === "figure") {
    drawFigure(rec, keep);
    return;
  }
  els.shownBody.appendChild(saidLine("Reading it…"));
  libFetch("/library/table/" + encodeURIComponent(rec.id),
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
  dropPlane();
  els.shown.hidden = true;
  els.shown.classList.remove("on-figure");
  els.shownNav.hidden = true;
  els.shownFit.hidden = true;
  els.shownBody.innerHTML = "";
  shownOrder = [];
  shownAt = -1;
}

els.shownClose.onclick = closeShown;
els.shownPrev.onclick = function () { stepFigure(-1); };
els.shownNext.onclick = function () { stepFigure(1); };
els.shownFit.onclick = function () { fitPlane(true); };

/* ONE SEARCH BOX FOR BOTH VIEWS. It is the same question either way -- which
   of these am I looking for -- so a second box beside the first would be two
   to keep in step. */
els.resFind.addEventListener("input", function () {
  findWords = (els.resFind.value || "").trim().toLowerCase();
  if (resView === "grid") drawGrid();
  else drawGroups();
});

els.resAsGrid.onclick = function () { setView("grid"); };
els.resAsList.onclick = function () { setView("list"); };
els.galDir.addEventListener("change", function () {
  galDir = els.galDir.value || "";
  drawGrid();
});
els.galOrder.addEventListener("change", function () {
  galOrder = els.galOrder.value || "newest";
  drawGrid();
});

document.addEventListener("keydown", function (ev) {
  /* STEPPING FROM THE KEYBOARD TOO, because this page is read on a laptop as
     well as on the glass and the arrows are what a hand reaches for. */
  if (!els.shown.hidden && shownAt >= 0) {
    if (ev.key === "ArrowLeft") { stepFigure(-1); return; }
    if (ev.key === "ArrowRight") { stepFigure(1); return; }
  }
  if (ev.key !== "Escape") return;
  if (ledger && ledger.escape()) return;
  if (!els.shown.hidden) closeShown();
  else if (!els.round.hidden) els.roundClose.onclick();
  else if (!els.note.hidden) els.noteCancel.onclick();
  else if (!els.reader.hidden) closeReader();
});

/* ==========================================================================
   EVERY FIGURE, AS PICTURES
   ==========================================================================
   The list above answers *is the file that card named really there*. This
   answers *show me the figures*, and no list of six hundred filenames can:
   `propensity_by_arm.png` under sixty-eight directories is sixty-eight rows
   that say nothing about which one is the plot being looked for.

   It is a second VIEW rather than a second page, and it draws the payload
   `/library/results.json` already sent -- one walk, one fence, one set of ids.
   A gallery with its own fetch would be a second answer about which figures
   exist, which is the drift `results.py`'s own `_walk` exists to prevent.

   Four things it has to get right, and each one is a way a grid of six hundred
   pictures turns into a page an iPad gives up on:

     1. A TILE HAS NO PICTURE IN IT UNTIL IT COMES NEAR THE GLASS. The address
        is on the tile from the start; the `src` is set when the tile is close
        to the viewport, and at most `GRID_AT_ONCE` are in flight. Nothing is
        generated and nothing is cached on disk: there is no thumbnail, so
        there is no cache for git to see and no second copy of a figure the
        next job rewrites. What that costs is honest and is the reason for the
        third rule.
     2. A HEAVY FIGURE IS NOT FETCHED BY SCROLLING PAST IT. Above
        `GRID_HEAVY` the tile says its size and waits to be tapped, because a
        megabyte spent on something a thumb went past is a megabyte spent on
        nothing.
     3. THE FENCE IS SAID WHERE THE PICTURES WOULD HAVE BEEN. A gallery is the
        surface where a silently omitted directory does the most damage, so an
        empty grid carries the server's own sentence -- which names the
        directory and names `fenced.py`.
     4. AND CHOOSING IS THE POINT. The search box is the list's, unchanged; the
        directory and the order are two selects beside it, because the question
        *which of these do I want* is asked three ways and a gallery that can
        only be scrolled has answered none of them.
   ========================================================================== */

/* HOW MANY PICTURES MAY BE IN FLIGHT AT ONCE. A figure out of these pipelines
   is a median of 52 kB, so a screenful is under a megabyte -- but a thumb
   flicked down six hundred tiles would open six hundred connections against a
   board sharing a compute node with the job that wrote them. */
var GRID_AT_ONCE = 6;

/* HOW FAR AHEAD OF THE GLASS a tile is fetched, so a picture is there by the
   time it is looked at rather than arriving under the eye. */
var GRID_NEAR = "800px";

/* ABOVE THIS, SCROLLING PAST DOES NOT SPEND THE BYTES. Five of TRD-EHR's 628
   figures are over it and they are 3.4 MB between them. */
var GRID_HEAVY = 300000;

/* AND WHAT TO DO WITHOUT AN OBSERVER AT ALL: the first screenful and then
   nothing, which is wrong in one direction and catastrophic in the other. */
var GRID_BLIND = 24;

var resView = "list";
var VIEW_KEY = "library.results.view";
try {
  resView = localStorage.getItem(VIEW_KEY) === "grid" ? "grid" : "list";
} catch (e) { resView = "list"; }

var galDir = "";             /* "" is every directory */
var galOrder = "newest";
var galSeen = null;          /* the observer watching the tiles */
var galWaiting = [];         /* tiles near the glass, waiting their turn */
var galFlying = 0;

/* EVERY FIGURE THE FILTERS LEAVE, FLAT AND IN ORDER. This is what the grid
   draws and what the stepper walks, so they cannot disagree about what "the
   next figure" is. */
function figuresNow() {
  var out = [];
  groups.forEach(function (g) {
    if (galDir && g.where !== galDir) return;
    (g.figures || []).forEach(function (rec) { if (hit(rec)) out.push(rec); });
  });
  if (galOrder === "name") {
    out.sort(function (a, b) { return cmp(a.file, b.file); });
  } else if (galOrder === "dir") {
    out.sort(function (a, b) {
      return cmp(a.where, b.where) || cmp(a.file, b.file);
    });
  } else {
    /* Newest first, by the figure's own mtime rather than its directory's: the
       one somebody has come to look at is the one that just changed, and a
       directory rewritten in part is the case where those two differ. */
    out.sort(function (a, b) { return (b.at || 0) - (a.at || 0); });
  }
  return out;
}

function cmp(a, b) { return a < b ? -1 : a > b ? 1 : 0; }

/* WHICH DIRECTORIES HAVE FIGURES IN THEM, with a count each, in the order the
   server sent them -- newest first, which is the order somebody looks in. */
function drawPick() {
  var was = els.galDir.value;
  var all = 0;
  var rows = [];
  groups.forEach(function (g) {
    var n = (g.figures || []).length;
    if (!n) return;
    all += n;
    rows.push({ where: g.where, n: n });
  });
  els.galDir.innerHTML = "";
  els.galDir.appendChild(pickOption("", "every directory  ·  " + all
    + (all === 1 ? " figure" : " figures")));
  rows.forEach(function (r) {
    els.galDir.appendChild(pickOption(r.where, r.where + "  ·  " + r.n));
  });
  /* A REDRAW KEEPS THE CHOICE, unless the directory it named has gone -- a job
     rewrites this tree, and a chooser that reset itself on every poll would
     throw somebody out of the directory they were looking at. */
  var keep = was && rows.filter(function (r) { return r.where === was; }).length;
  galDir = keep ? was : "";
  els.galDir.value = galDir;
  els.galOrder.value = galOrder;
}

function pickOption(value, said) {
  var o = document.createElement("option");
  o.value = value;
  o.textContent = said;
  return o;
}

function setView(which) {
  resView = which === "grid" ? "grid" : "list";
  try { localStorage.setItem(VIEW_KEY, resView); }
  catch (e) { /* a private window. The choice still holds for this page. */ }
  applyView();
}

function applyView() {
  var grid = resView === "grid";
  els.resAsGrid.classList.toggle("on", grid);
  els.resAsList.classList.toggle("on", !grid);
  els.resPick.hidden = !grid;
  els.resGrid.hidden = !grid;
  els.resGridCount.hidden = !grid;
  els.resList.hidden = grid;
  /* A CHOOSER AND A COUNT OVER NOTHING ARE TWO LINES SAYING "0" above a
     sentence that has already said why. Dropped separately from the switch,
     which stays: the way into the gallery is how the reason gets read. */
  if (grid && !anyFigures()) {
    els.resPick.hidden = true;
    els.resGridCount.hidden = true;
  }
  /* The empty grid carries the reason itself, so the line above it would be
     the same sentence twice on one screen. */
  els.resNone.hidden = grid || !!groups.length;
  if (grid) drawGrid();
  else { stopWatching(); drawGroups(); }
}

function drawGrid() {
  stopWatching();
  els.resGrid.innerHTML = "";
  var rows = figuresNow();
  els.resGridCount.textContent = countLine(rows.length);
  if (!rows.length) {
    /* A SENTENCE WHERE THE PICTURES WOULD HAVE BEEN. An empty grid is a page
       that looks broken, and the reasons are different enough to be worth
       telling apart: a filter that matched nothing, a directory of tables, and
       a workspace whose output is session content. */
    els.resGrid.appendChild(saidLine(whyNoFigures()));
    return;
  }
  rows.forEach(function (rec, i) { els.resGrid.appendChild(figureTile(rec, i)); });
  startWatching();
}

function anyFigures() {
  for (var i = 0; i < groups.length; i++) {
    if ((groups[i].figures || []).length) return true;
  }
  return false;
}

function countLine(n) {
  var all = 0;
  groups.forEach(function (g) { all += (g.figures || []).length; });
  return [n === all ? (all + (all === 1 ? " figure" : " figures"))
                    : (n + " of " + all + " figures"),
          galDir || "",
          findWords ? "called “" + findWords + "”" : ""
         ].filter(Boolean).join("  ·  ");
}

function whyNoFigures() {
  if (findWords) return "No figure here is called “" + findWords + "”.";
  if (galDir) return "There are no figures in " + galDir + ".";
  if (groups.length) {
    return "This workspace has produced tables but no figures. The list has "
      + "them, and a table is read on the glass rather than downloaded.";
  }
  return resWhy;
}

/* ONE TILE. The address rides on the image from the start and the `src` does
   not: that is the whole of the lazy load, and it is why a grid of six hundred
   lays out once and fetches a screenful. */
function figureTile(rec, i) {
  var b = document.createElement("button");
  b.type = "button";
  b.className = "res-tile";
  b.dataset.id = rec.id;
  var frame = document.createElement("span");
  frame.className = "res-tile-frame";
  var img = document.createElement("img");
  img.className = "res-thumb";
  img.alt = rec.name;
  /* `decoding` only, and deliberately no `loading="lazy"`: the observer below
     is what decides when a picture is wanted, and the browser's own hint can
     defer an image whose `src` has already been set -- which would hold one of
     the queue's slots with no `load` and no `error` ever arriving. */
  img.decoding = "async";
  /* `/result/<id>`, which is the route the drawer and the viewer already use
     and which `sw.js` sends to the network always -- the next job rewrites a
     figure at the same name, so a cached one is last week's result under this
     week's label. */
  img.dataset.src = libUrl("/result/" + encodeURIComponent(rec.id));
  var wait = document.createElement("span");
  wait.className = "res-tile-wait";
  if (rec.size > GRID_HEAVY) {
    /* NOT FETCHED BY SCROLLING PAST IT. The tile says how big it is and opens
       up close on a tap, which is the point at which the bytes are wanted. */
    img.dataset.heavy = "1";
    wait.textContent = size(rec.size) + " — tap to see it";
  }
  frame.appendChild(img);
  frame.appendChild(wait);
  b.appendChild(frame);
  var name = document.createElement("span");
  name.className = "res-tile-name";
  /* THE FILENAME, for the list's reason: a card said this string, and a tile
     that has quietly renamed it is one the reader scrolls straight past. */
  name.textContent = rec.file;
  b.appendChild(name);
  var meta = document.createElement("span");
  meta.className = "res-tile-meta";
  meta.textContent = [rec.where, rec.iso].filter(Boolean).join("  ·  ");
  b.appendChild(meta);
  b.addEventListener("click", function () {
    shownOrder = figuresNow();
    shownAt = i;
    paintShown(rec, false);
  });
  return b;
}

/* ------------------------------------- what is near the glass, and only that */
function startWatching() {
  var tiles = els.resGrid.querySelectorAll(".res-tile img[data-src]");
  if (!window.IntersectionObserver) {
    /* No observer: a screenful and then nothing. Wrong in one direction, and
       six hundred fetches is wrong in the other. */
    for (var i = 0; i < tiles.length && i < GRID_BLIND; i++) wantThumb(tiles[i]);
    return;
  }
  galSeen = new window.IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      /* UNOBSERVED THE MOMENT IT COUNTS, so a tile scrolled back and forth is
         one fetch rather than one per pass. */
      galSeen.unobserve(e.target);
      wantThumb(e.target);
    });
  }, { root: null, rootMargin: GRID_NEAR, threshold: 0 });
  Array.prototype.forEach.call(tiles, function (img) { galSeen.observe(img); });
}

function stopWatching() {
  if (galSeen) galSeen.disconnect();
  galSeen = null;
  galWaiting = [];
  galFlying = 0;
}

function wantThumb(img) {
  if (!img || !img.dataset.src || img.dataset.heavy) return;
  galWaiting.push(img);
  pumpThumbs();
}

/* AND A SLOT IS NEVER HELD FOR EVER. `plane-core.js`'s own rule -- every
   refusal expires -- for the same reason it is written there: a picture that
   fires neither `load` nor `error` holds one of six slots, and six of those is
   a grid that has quietly stopped loading with nothing on the glass saying
   why. Long, because it is a floor rather than a deadline: a figure on a link
   that has just come back is worth waiting for. */
var GRID_WAIT = 20000;

function pumpThumbs() {
  while (galFlying < GRID_AT_ONCE && galWaiting.length) {
    var img = galWaiting.shift();
    if (!img.dataset.src) continue;
    galFlying += 1;
    img.addEventListener("load", thumbLanded);
    img.addEventListener("error", thumbLanded);
    img._slot = setTimeout(freeSlot(img, "slow"), GRID_WAIT);
    img.src = img.dataset.src;
    /* Dropped once it is asked for, so nothing asks twice. */
    delete img.dataset.src;
  }
}

function thumbLanded(ev) {
  freeSlot(ev.currentTarget, ev.type)();
}

function freeSlot(img, why) {
  return function () {
    if (!img._slot && why === "slow") return;
    if (img._slot) clearTimeout(img._slot);
    img._slot = null;
    img.removeEventListener("load", thumbLanded);
    img.removeEventListener("error", thumbLanded);
    var wait = img.parentNode && img.parentNode.querySelector(".res-tile-wait");
    if (wait && why !== "load") {
      /* A job rewrites this directory. A tile whose figure has gone says so
         rather than showing the browser's broken-image mark. */
      wait.textContent = why === "slow" ? "it is not answering"
                                        : "it has been rewritten";
    }
    galFlying = Math.max(0, galFlying - 1);
    pumpThumbs();
  };
}

/* ==========================================================================
   ONE FIGURE, UP CLOSE -- the one plane on this page
   ==========================================================================
   `plane-core.js` owns the arithmetic and the bookkeeping, and it is reused
   here rather than re-derived for the reason its own header gives: every rule
   in it was written after a gesture stopped working on somebody's iPad. A
   gesture is decided by which contacts are LIVE, a pinch stays between the two
   it started between, and the view is clamped to the content plus slack.

   AND THIS IS THE CASE IT IS RIGHT FOR. The front door deliberately is not a
   plane -- a list of six families on a pannable pinchable surface is the
   gesture layer solving a problem the content does not have, and it produced
   the wacky zooming. One large figure is the opposite: the content is bigger
   than the glass, the whole reason to open it is to read an axis label, and
   there is nothing else on the surface for a finger to mean.
   ========================================================================== */

/* No padding: the fit is the fit. A little slack around it so a zoomed figure
   can be dragged just past its edge rather than stopping dead. */
var PLANE_SLACK = 0.12;

/* The bounds `Plane.frame` is allowed to fit into -- wide, because the fit
   itself is the floor and is computed from the picture. */
var PLANE_FLOOR = 0.01;
var PLANE_CEIL = 40;

/* How far past the fit a pinch may go. Eight times a figure that filled the
   glass is well past its own pixels, which is where a plot stops carrying
   information; the 3 is the floor for a figure so small that fitting it is
   already a magnification. */
var PLANE_MOST = 8;

/* How close two taps have to be, in time and in space, to be a double. */
var TAP_APART = 320;
var TAP_NEAR = 40;

var plane = null;   /* the surface, the picture, the hand and the view */

function drawFigure(rec, keep) {
  var wrap = document.createElement("div");
  wrap.className = "res-plane";
  var img = document.createElement("img");
  img.className = "res-figure";
  img.alt = rec.name;
  img.src = libUrl("/result/" + encodeURIComponent(rec.id));
  img.onerror = function () {
    dropPlane();
    els.shownBody.innerHTML = "";
    els.shownFit.hidden = true;
    els.shown.classList.remove("on-figure");
    els.shownBody.appendChild(saidLine(
      "That figure is not there any more. A job rewrites this directory, so "
        + "reload the page to see what is in it now."));
  };
  wrap.appendChild(img);
  els.shownBody.appendChild(wrap);
  plane = {
    wrap: wrap, img: img, view: null, box: null, fit: 1, lo: 1, hi: 1,
    hand: window.Plane ? window.Plane.contacts({ onPinchEnd: renderPlane }) : null,
    drag: null, tapAt: 0, tapX: 0, tapY: 0, off: [], sized: false,
    /* The zoom a step arrives with, if there is one to keep. */
    carry: keep ? planeKept : null
  };
  armPlane();
  /* Fitted twice on purpose. A picture still on the wire has no size to fit
     to, so the first pass is a layout for the frame and the second -- when the
     bytes land -- is the one that is right. The carried zoom survives the
     first and is spent on the second, which is where the bounds are real. */
  img.addEventListener("load", function () { fitPlane(false); });
  fitPlane(false);
}

/* The zoom the last figure was left at, so a step can keep it. Held outside
   `plane`, which is thrown away between figures. */
var planeKept = null;

function fitPlane(force) {
  if (!plane) return;
  var wrap = plane.wrap, img = plane.img;
  if (force) plane.carry = null;
  var cw = wrap.clientWidth, ch = wrap.clientHeight;
  var real = !!(img.naturalWidth && img.naturalHeight);
  /* BEFORE THE BYTES LAND, THE PICTURE IS TAKEN TO BE THE SIZE OF THE GLASS,
     so the first fit is the identity. A made-up size here is a made-up fit,
     and the fit is what the zoom bounds are computed from -- a carried zoom
     clamped against a one-pixel picture comes out as whatever the ceiling is. */
  var nw = img.naturalWidth || cw || 1;
  var nh = img.naturalHeight || ch || 1;
  plane.box = { x0: 0, y0: 0, x1: nw, y1: nh };
  if (!window.Plane) {
    /* No plane machinery: the picture, at the size of the glass, which is what
       this surface did before it could be zoomed. */
    img.style.position = "static";
    img.style.maxWidth = "100%";
    img.style.maxHeight = "100%";
    return;
  }
  var fitted = window.Plane.frame(
    { k: 1, ox: 0, oy: 0, held: false }, plane.box, cw, ch, 0,
    PLANE_FLOOR, PLANE_CEIL);
  plane.fit = fitted.k;
  plane.lo = fitted.k;
  plane.hi = Math.max(fitted.k * PLANE_MOST, 3);
  var fresh = force || !plane.view || (real && !plane.sized);
  if (real) plane.sized = true;
  if (fresh) {
    plane.view = fitted;
    if (plane.carry) {
      /* A STEP KEEPS THE ZOOM, clamped into what THIS picture allows: the next
         plot is rarely the same pixel size, so a zoom carried over whole could
         be past its own bounds. */
      plane.view.k = Math.max(plane.lo, Math.min(plane.hi, plane.carry.k));
      plane.view.ox = plane.carry.ox;
      plane.view.oy = plane.carry.oy;
      plane.view.held = true;
      if (real) plane.carry = null;
    }
  }
  renderPlane();
}

function renderPlane() {
  if (!plane || !plane.view || !plane.box || !window.Plane) return;
  var wrap = plane.wrap;
  var cw = wrap.clientWidth, ch = wrap.clientHeight;
  window.Plane.clamp(
    plane.view,
    window.Plane.room(plane.box, cw, ch, plane.view.k, PLANE_SLACK), cw, ch);
  plane.img.style.transform = "translate(" + plane.view.ox + "px, "
    + plane.view.oy + "px) scale(" + plane.view.k + ")";
  planeKept = { k: plane.view.k, ox: plane.view.ox, oy: plane.view.oy };
  /* HOW FAR IN, AS A PERCENTAGE OF THE FIT, on the button that undoes it --
     so a hand that has lost the figure can see that it is at 400% and what
     to tap. */
  els.shownFit.textContent = plane.fit
    ? Math.round(plane.view.k / plane.fit * 100) + "%  fit"
    : "fit";
}

/* ------------------------------------------------------------- the gestures */
function armPlane() {
  var wrap = plane.wrap;
  onPlane(wrap, "touchstart", onDown, { passive: false });
  onPlane(wrap, "touchmove", onMove, { passive: false });
  onPlane(wrap, "touchend", onUp, { passive: false });
  onPlane(wrap, "touchcancel", onUp, { passive: false });
  /* AND AT THE WINDOW, for a finger that left past the edge of the surface.
     `Plane.contacts.forget` is idempotent, so whichever hears it first does
     the work -- which is the rule the writing surface and the map both keep. */
  onPlane(window, "touchend", onUp, true);
  onPlane(window, "touchcancel", onUp, true);
  onPlane(wrap, "wheel", onWheel, { passive: false });
  onPlane(wrap, "mousedown", onMouseDown, false);
  onPlane(window, "mousemove", onMouseMove, false);
  onPlane(window, "mouseup", onMouseUp, false);
  onPlane(wrap, "dblclick", function () { fitPlane(true); }, false);
}

function onPlane(target, type, fn, opts) {
  target.addEventListener(type, fn, opts);
  plane.off.push([target, type, fn, opts]);
}

function dropPlane() {
  if (!plane) return;
  plane.off.forEach(function (one) {
    one[0].removeEventListener(one[1], one[2], one[3]);
  });
  if (plane.hand) plane.hand.clear();
  plane = null;
}

function rectOf() { return plane.wrap.getBoundingClientRect(); }

function onDown(ev) {
  if (!plane || !plane.hand) return;
  var r = rectOf();
  var t = ev.changedTouches;
  for (var i = 0; i < t.length; i++) {
    plane.hand.note(t[i].identifier, t[i].clientX - r.left, t[i].clientY - r.top);
  }
  var live = plane.hand.live();
  if (live.length >= 2) {
    plane.hand.begin(plane.view ? plane.view.k : 1);
    plane.drag = null;
  } else if (live.length === 1) {
    var one = plane.hand.at(live[0]);
    plane.drag = plane.view
      ? { x: one.x, y: one.y, ox: plane.view.ox, oy: plane.view.oy } : null;
    /* TWO TAPS IN THE SAME PLACE IS THE WAY BACK OUT, which is what a hand
       reaches for before it finds a button. */
    var now = Date.now();
    if (now - plane.tapAt < TAP_APART
        && Math.abs(one.x - plane.tapX) < TAP_NEAR
        && Math.abs(one.y - plane.tapY) < TAP_NEAR) {
      plane.tapAt = 0;
      fitPlane(true);
    } else {
      plane.tapAt = now;
      plane.tapX = one.x;
      plane.tapY = one.y;
    }
  }
  /* The browser gets no share of this gesture: `touch-action: none` in the
     sheet and this here, because a pinch the page is also acting on is a pinch
     doing two things at once. */
  if (ev.cancelable) ev.preventDefault();
}

function onMove(ev) {
  if (!plane || !plane.hand || !plane.view) return;
  if (ev.cancelable) ev.preventDefault();
  var r = rectOf();
  var t = ev.changedTouches;
  for (var i = 0; i < t.length; i++) {
    plane.hand.note(t[i].identifier, t[i].clientX - r.left, t[i].clientY - r.top);
  }
  var got = plane.hand.spread();
  if (got) {
    window.Plane.zoomAbout(plane.view, got.k, got.cx, got.cy, plane.lo, plane.hi);
    plane.drag = null;
    renderPlane();
    return;
  }
  var live = plane.hand.live();
  if (live.length !== 1) return;
  var one = plane.hand.at(live[0]);
  if (!plane.drag) {
    plane.drag = { x: one.x, y: one.y, ox: plane.view.ox, oy: plane.view.oy };
    return;
  }
  plane.view.ox = plane.drag.ox + (one.x - plane.drag.x);
  plane.view.oy = plane.drag.oy + (one.y - plane.drag.y);
  renderPlane();
}

function onUp(ev) {
  if (!plane || !plane.hand) return;
  var t = ev.changedTouches;
  if (!t) return;
  for (var i = 0; i < t.length; i++) plane.hand.forget(t[i].identifier);
  plane.drag = null;
  renderPlane();
}

function onWheel(ev) {
  if (!plane || !plane.view || !window.Plane) return;
  if (ev.cancelable) ev.preventDefault();
  var r = rectOf();
  var k = plane.view.k * Math.exp(-(ev.deltaY || 0) / 300);
  window.Plane.zoomAbout(plane.view, k, ev.clientX - r.left, ev.clientY - r.top,
                         plane.lo, plane.hi);
  renderPlane();
}

function onMouseDown(ev) {
  if (!plane || !plane.view) return;
  ev.preventDefault();
  plane.drag = { x: ev.clientX, y: ev.clientY,
                 ox: plane.view.ox, oy: plane.view.oy, mouse: true };
}

function onMouseMove(ev) {
  if (!plane || !plane.drag || !plane.drag.mouse || !plane.view) return;
  plane.view.ox = plane.drag.ox + (ev.clientX - plane.drag.x);
  plane.view.oy = plane.drag.oy + (ev.clientY - plane.drag.y);
  plane.view.held = true;
  renderPlane();
}

function onMouseUp() {
  if (plane && plane.drag && plane.drag.mouse) plane.drag = null;
}

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
