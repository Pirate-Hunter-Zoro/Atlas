/* ==========================================================================
   library.js -- every document this workspace has written, on one surface.

   The ⋯ menu's document panel offers the two documents the BOARD makes: the
   exported lesson and the compiled write-up. The contents drawer offers what
   `reading.py` found, as things to put on a card. Neither is "every paper and
   presentation in this project", neither was reachable without opening a lesson
   first, and there was nowhere at all to say what was wrong with one.

   Three rules this page keeps, and each of them was paid for elsewhere first:

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
   ========================================================================== */

var els = {
  where: document.getElementById("lib-where"),
  count: document.getElementById("lib-count"),
  list: document.getElementById("lib-list"),
  none: document.getElementById("lib-none"),
  reader: document.getElementById("reader"),
  readerName: document.getElementById("reader-name"),
  readerSub: document.getElementById("reader-sub"),
  readerPages: document.getElementById("reader-pages"),
  readerSay: document.getElementById("reader-say"),
  readerClose: document.getElementById("reader-close"),
  note: document.getElementById("note"),
  noteTitle: document.getElementById("note-title"),
  noteWhere: document.getElementById("note-where"),
  noteText: document.getElementById("note-text"),
  notePage: document.getElementById("note-page"),
  noteSaid: document.getElementById("note-said"),
  noteCancel: document.getElementById("note-cancel"),
  noteSend: document.getElementById("note-send")
};

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

  if ((doc.notes || []).length) {
    var rounds = document.createElement("span");
    rounds.className = "lib-rounds";
    rounds.textContent = doc.notes.length
      + (doc.notes.length === 1 ? " round of feedback" : " rounds of feedback")
      + ", last on " + doc.notes[doc.notes.length - 1].day;
    box.appendChild(rounds);
  }

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
  els.reader.hidden = false;
  els.readerName.textContent = doc.title || doc.stem;
  els.readerSub.textContent = "drawing the pages…";
  els.readerPages.innerHTML = "";
  els.readerPages.scrollTop = 0;
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
        var img = document.createElement("img");
        img.src = url;
        img.alt = "page " + (i + 1);
        img.loading = "lazy";
        fig.appendChild(img);
        var n = document.createElement("figcaption");
        n.textContent = i + 1;
        fig.appendChild(n);
        els.readerPages.appendChild(fig);
      });
    })
    .catch(function () {
      els.readerSub.textContent = "The board is not answering.";
    });
}

function closeReader() {
  openDoc = null;
  openPages = 0;
  els.reader.hidden = true;
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
var noteFor = null;
var notePage = 0;

function say(doc, page) {
  if (!doc) return;
  noteFor = doc;
  notePage = page || 0;
  els.noteTitle.textContent = doc.title || doc.stem;
  els.noteWhere.textContent = doc.rel;
  els.noteText.value = "";
  els.noteSaid.hidden = true;
  els.noteSend.disabled = true;
  els.noteSend.textContent = "send it";
  els.notePage.hidden = !notePage;
  if (notePage) els.notePage.textContent = "about page " + notePage;
  els.note.hidden = false;
  els.noteText.focus();
}

els.noteText.addEventListener("input", function () {
  els.noteSend.disabled = !els.noteText.value.trim();
});

els.noteCancel.onclick = function () {
  els.note.hidden = true;
  noteFor = null;
};

els.noteSend.onclick = function () {
  var said = els.noteText.value.trim();
  if (!noteFor || !said) return;
  els.noteSend.disabled = true;
  els.noteSend.textContent = "sending…";
  fetch("/library/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    /* THE ID, and the page if there is one. Never the path -- the server holds
       the only mapping from one to the other. */
    body: JSON.stringify({ document: noteFor.id, text: said, page: notePage })
  }).then(function (r) {
    return r.json().catch(function () { return {}; });
  }).then(function (got) {
    els.noteSaid.hidden = false;
    if (!got || got.ok === false) {
      els.noteSaid.className = "note-said bad";
      els.noteSaid.textContent = "That could not be written: "
        + ((got && got.error) || "the board refused it") + ".";
      els.noteSend.disabled = false;
      els.noteSend.textContent = "send it";
      return;
    }
    els.noteSaid.className = "note-said";
    els.noteSaid.textContent = "Filed at " + got.rel + ". "
      + (got.detail || "");
    els.noteSend.textContent = "sent";
    els.noteText.value = "";
    /* The list carries how many rounds a document has had, so it is worth
       being right about a second after one lands. */
    load();
  }).catch(function () {
    els.noteSaid.hidden = false;
    els.noteSaid.className = "note-said bad";
    els.noteSaid.textContent = "The board is not answering; nothing was written.";
    els.noteSend.disabled = false;
    els.noteSend.textContent = "send it";
  });
};

document.addEventListener("keydown", function (ev) {
  if (ev.key !== "Escape") return;
  if (!els.note.hidden) els.noteCancel.onclick();
  else if (!els.reader.hidden) closeReader();
});

load();
/* A document is rebuilt by a job, a compile, or the revision this page just
   asked for, and this page is left open on a desk. Not a poll: it is looked at
   again when somebody comes back to it. */
document.addEventListener("visibilitychange", function () {
  if (!document.hidden) load();
});
