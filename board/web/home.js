/* ==========================================================================
   home.js -- the front door, and the ATLAS on it.

       "Every time I open the application, I want to be taken to a very visually
        pleasing map of EVERYTHING. I can choose what course or project I want to
        go to next."

   So this page does two things. Above the fold it is a DOOR: the workspace the
   board is in, what it is waiting on, and one tap back into the lesson somebody
   was in twenty seconds ago. That half is unchanged and it is the half that
   must never get slower or cleverer.

   Below it is the atlas. It used to be two lists -- "Other courses" and
   "Earlier" -- and a list is not a map. The same objection that killed the
   first version of the per-workspace map applies word for word to a column of
   names: "I don't want just a list of all the TODOs. I want a map of the
   CONTENT." So it is drawn: one plane, a region per family, a card per
   workspace, each saying what is next in it and how much is outstanding.

   Three rules it inherits, each paid for once already:

     * TEXT IS MEASURED, NEVER ESTIMATED. `gauge.js`, shared with the map. A
       line of capitals is half again wider than characters times a constant,
       and that is how labels came to run out of their boxes.
     * THE LAYOUT IS DETERMINISTIC. Three cards across, always, computed from a
       constant rather than from the width of the glass. A picture that settles
       somewhere different on each device is not one anybody can learn. What
       adapts is the VIEW: a narrow screen opens framed on the card you are in
       rather than on the whole plane, and a tap opens the sheet, so nothing
       depends on reading twelve-point text on a phone.
     * NOTHING IN THE PAINT MAY THROW. A front door that throws is a blank
       screen where the app used to be, and this one is the way back into a
       lesson.

   Switching is the other clever part and it is unchanged: a workspace other
   than the current one lives on a different port, and the installed app has
   exactly one origin baked into it, so the browser cannot simply navigate
   there. It asks the server to move the board -- start that workspace's server
   and re-point the HTTPS proxy at it -- and then reloads. The address never
   changes.
   ========================================================================== */

(function () {
"use strict";

var els = {
  dot: document.getElementById("dot"),
  eyebrow: document.getElementById("hero-eyebrow"),
  course: document.getElementById("hero-course"),
  chapter: document.getElementById("hero-chapter"),
  count: document.getElementById("hero-count"),
  slateSub: document.getElementById("hero-slate"),
  waiting: document.getElementById("waiting"),
  waitingText: document.getElementById("waiting-text"),
  answers: document.getElementById("answers"),
  answersLead: document.getElementById("answers-lead"),
  answersList: document.getElementById("answers-list"),
  missions: document.getElementById("missions"),
  missionsLead: document.getElementById("missions-lead"),
  missionsList: document.getElementById("missions-list"),
  atlasWrap: document.getElementById("atlas-wrap"),
  atlasEmpty: document.getElementById("atlas-empty"),
  atlasWhat: document.getElementById("atlas-what"),
  atlasBlurb: document.getElementById("atlas-blurb"),
  atlasUp: document.getElementById("atlas-up"),
  doors: document.getElementById("doors"),
  cards: document.getElementById("cards"),
  found: document.getElementById("found"),
  atlasQ: document.getElementById("atlas-q"),
  atlasQClear: document.getElementById("atlas-q-clear"),
  panic: document.getElementById("panic"),
  sheet: document.getElementById("sheet"),
  sheetFamily: document.getElementById("sheet-family"),
  sheetName: document.getElementById("sheet-name"),
  sheetWhere: document.getElementById("sheet-where"),
  sheetNext: document.getElementById("sheet-next"),
  sheetNextText: document.getElementById("sheet-next-text"),
  sheetMeta: document.getElementById("sheet-meta"),
  sheetOpen: document.getElementById("sheet-open"),
  sheetOpenSub: document.getElementById("sheet-open-sub"),
  sheetClose: document.getElementById("sheet-close"),
  sheetLibrary: document.getElementById("sheet-library"),
  sheetLibrarySub: document.getElementById("sheet-library-sub"),
  sheetTrace: document.getElementById("sheet-trace"),
  sheetTraceSub: document.getElementById("sheet-trace-sub"),
  where: document.getElementById("where"),
  notes: document.getElementById("notes"),
  notesSince: document.getElementById("notes-since"),
  notesSaid: document.getElementById("notes-said"),
  notesClose: document.getElementById("notes-close"),
  notesBtn: document.getElementById("atlas-notes"),
  notesWhich: document.getElementById("notes-which"),
  notesWhichLine: document.getElementById("notes-which-line"),
  notesList: document.getElementById("notes-list"),
  notesMake: document.getElementById("notes-make"),
  notesMakeSub: document.getElementById("notes-make-sub"),
  notesBack: document.getElementById("notes-back"),
  notesRead: document.getElementById("notes-read"),
  notesReadSub: document.getElementById("notes-read-sub"),
  notesTitle: document.getElementById("notes-title"),
  doc: document.getElementById("doc"),
  docBtn: document.getElementById("atlas-doc"),
  docTitle: document.getElementById("doc-title"),
  docLine: document.getElementById("doc-line"),
  docMakes: document.getElementById("doc-makes"),
  docWhere: document.getElementById("doc-where"),
  docScopes: document.getElementById("doc-scopes"),
  docSaid: document.getElementById("doc-said"),
  docRead: document.getElementById("doc-read"),
  docReadSub: document.getElementById("doc-read-sub"),
  docBack: document.getElementById("doc-back"),
  docBackSub: document.getElementById("doc-back-sub"),
  docClose: document.getElementById("doc-close"),
  busy: document.getElementById("busy"),
  busyText: document.getElementById("busy-text"),
  busySub: document.getElementById("busy-sub")
};

function plural(n, one, many) {
  return n + " " + (n === 1 ? one : many);
}

function ago(t) {
  if (!t) return "";
  var s = Math.max(0, Date.now() / 1000 - t);
  if (s < 90) return "just now";
  if (s < 3600) return Math.round(s / 60) + " min ago";
  if (s < 86400) return Math.round(s / 3600) + " h ago";
  return Math.round(s / 86400) + " d ago";
}

/* ------------------------------------------------------------ the current */
function paintBoard(d) {
  var st = d.state || {};
  var cards = d.cards || [];

  els.course.textContent = st.course || "No lesson open";
  els.chapter.textContent = st.chapter || "";
  document.title = st.course ? st.course + " · Board" : "Board";

  if (cards.length) {
    var last = cards[cards.length - 1];
    els.count.textContent = plural(cards.length, "card", "cards") + " · " + ago(last.mtime);
    els.eyebrow.textContent = "current";
  } else {
    els.count.textContent = "nothing on the board yet";
    els.eyebrow.textContent = "ready";
  }

  /* A question with nothing sent after it is still owed an answer. */
  var lastQuestion = null;
  for (var i = cards.length - 1; i >= 0; i--) {
    if (cards[i].kind === "question") { lastQuestion = cards[i]; break; }
  }
  var msgs = d.messages || [];
  var lastReply = msgs.length ? msgs[msgs.length - 1].t : 0;
  if (lastQuestion && lastQuestion.mtime > lastReply) {
    els.waitingText.textContent = lastQuestion.title || ("card " + lastQuestion.id);
    els.waiting.hidden = false;
  } else {
    els.waiting.hidden = true;
  }

  var push = d.push;
  if (push) {
    var line = document.getElementById("pushline");
    if (!line) {
      line = document.createElement("p");
      line.id = "pushline";
      line.className = "pushline";
      document.getElementById("current").appendChild(line);
    }
    line.className = "pushline " + (push.ok ? "ok" : "bad");
    line.textContent = (push.ok ? "✓ pushed " : "✕ push failed ") + push.iso
                     + (push.ok ? "" : " — " + (push.detail || "").split("\n").slice(-1)[0]);
  }

  if (st.session) els.eyebrow.textContent = st.session;

  var slate = d.slate || [];
  els.slateSub.textContent = slate.length
    ? plural(slate.length, "page", "pages") + " written"
    : "the slate";
}

/* ============================================================== the atlas
   THREE LEVELS, AND ONLY THE LAST OF THEM IS A PLANE.

       "It's just an ugly grid of projects in an inner box that has wacky
        zooming. On the homescreen, I want a nice 'Research' option, 'Courses'
        option, and 'Projects' option, and honestly something pertaining to
        vendor/ as well... When I select one of those four options, I want to
        see all available projects/courses/research projects/vendor tools
        portrayed in again a visually pleasing way, and then we can go into an
        individual project map."

   This page used to build ONE SVG plane -- a region per family, a card per
   workspace -- and hand it to `plane-core.js` to be panned and pinched, with a
   `fit` button because it could not be seen at once. Six families and a dozen
   workspaces is A LIST OF SIX. A list is not a diagram, and drawing it on a
   plane is what produced the wacky zooming: the gesture layer was solving a
   problem the content did not have, and the page it sat on could be pinched
   over the top of it, which is two ways to be lost.

   So:

     1. THE DOOR -- the families, as large tappable things. `atlas.json`
        already carries them in the order they should be drawn with a sentence
        each, and those sentences are what a door says.
     2. THE FAMILY -- its workspaces, each with what it is and what is
        happening in it. Every field was already in the payload and was being
        drawn as a small card on a plane.
     3. THE PROJECT MAP -- a diagram, which is the one thing here that
        genuinely needs a plane. It lives on the board, `plane-core.js` still
        draws it, and it finally has content whose shape justifies it.

   NEITHER OF THE TWO LEVELS HERE IS A PLANE. No pan, no pinch, no fit, and no
   measuring: these are HTML elements in a CSS grid, so the browser lays the
   text out and a label cannot run out of a box it was not measured for. The
   constant that used to matter -- three across, always, never from the width of
   the glass -- is a media query now, which is the same promise kept by the
   thing whose job it is.

   ONE RULE SURVIVES UNCHANGED AND IT IS THE IMPORTANT ONE: nothing in the
   paint may throw. A front door that throws is a blank screen where the app
   used to be, and this one is the way back into a lesson. */

var atlas = null;                    /* the payload, as it arrived */
var atlasFamily = "";                /* the family being read, or "" for the door */
/* A sentence the atlas is showing INSTEAD of a level -- an address that no
   longer resolves, a board too old to serve a payload. Kept in a variable so a
   poll twenty seconds later does not wipe it off the screen. */
var atlasSaid = "";

function aAgo(t) {
  if (!t) return "never";
  var s = Math.max(0, Date.now() / 1000 - t);
  if (s < 3600) return "just now";
  if (s < 86400) return Math.round(s / 3600) + "h ago";
  if (s < 86400 * 14) return Math.round(s / 86400) + "d ago";
  return Math.round(s / 604800) + "w ago";
}

/* The one line under a card: how much is outstanding, whether a board is up,
   and when it was last committed to. Names and numbers, never adjectives. */
function aMeta(c) {
  var bits = [];
  if (c.open) {
    bits.push(c.open + (c.kind === "book" ? " chapters left" : " open"));
  }
  if (c.cards) bits.push(c.cards + (c.cards === 1 ? " card" : " cards"));
  bits.push(aAgo(c.touched));
  return bits.join("  ·  ");
}

/* And the same line for a vendor tree, which has none of those things. Nothing
   is outstanding in somebody else's repository, and no cards are written
   against it -- what it has is a commit and some source. */
function aTreeMeta(t) {
  var bits = [];
  if (t.at) bits.push("at " + t.at);
  if (t.files) {
    bits.push(t.files + (t.capped ? "+" : "")
              + (t.files === 1 ? " source file" : " source files"));
  }
  bits.push(aAgo(t.touched));
  return bits.join("  ·  ");
}

/* What is in one family, whichever list it comes from. A vendor family holds
   TREES and every other family holds WORKSPACES, and the two are separate
   lists on purpose: `atlas.trees()` is read and drawn and is never something
   work is handed in to. This is the one place that has to know both. */
function aIn(fam) {
  if (!atlas) return [];
  if (fam.vendor) {
    return (atlas.trees || []).filter(function (t) { return t.family === fam.id; });
  }
  return (atlas.workspaces || []).filter(function (c) { return c.family === fam.id; });
}

function aFamily(id) {
  var found = null;
  ((atlas && atlas.families) || []).forEach(function (f) {
    if (f.id === id) found = f;
  });
  return found;
}

function aEl(tag, cls, text) {
  var el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text !== undefined && text !== null) el.textContent = text;
  return el;
}

/* ------------------------------------------------------------ level one */
/* WHAT A DOOR SAYS. Its name and the sentence `atlas.json` already carries for
   it -- "Graduate coursework, taught chapter by chapter.", "The projects that
   become papers." -- and then what is true inside it right now. The sentences
   existed and the old front door used them as nothing but a heading. */
function aDoorLine(fam, mine) {
  var bits = [];
  var word = fam.vendor ? "tree" : fam.id === "courses" ? "course"
           : fam.id === "practice" ? "set" : "project";
  bits.push(mine.length + " " + word + (mine.length === 1 ? "" : "s"));
  var live = mine.filter(function (c) { return c.running; }).length;
  if (live) bits.push(live + " live");
  var news = mine.filter(function (c) { return c.news; }).length;
  if (news) bits.push(news === 1 ? "an answer waiting" : news + " answers waiting");
  var going = mine.filter(function (c) {
    return c.mission && c.mission.state === "running";
  }).length;
  if (going) bits.push(going === 1 ? "one still going" : going + " still going");
  return bits.join("  ·  ");
}

function paintDoors() {
  var host = els.doors;
  host.innerHTML = "";
  var drawn = 0;
  ((atlas && atlas.families) || []).forEach(function (fam) {
    var mine = aIn(fam);
    /* A FAMILY WITH NOTHING IN IT IS NOT A DOOR. `board` is the tool doing the
       offering rather than one of the things offered, and a heading over empty
       space reads as something missing rather than as something absent on
       purpose. */
    if (!mine.length) return;
    drawn += 1;
    var b = aEl("button", "door" + (fam.vendor ? " vendor" : ""));
    b.type = "button";
    b.appendChild(aEl("span", "door-name", fam.name || fam.id));
    if (fam.blurb) b.appendChild(aEl("span", "door-blurb", fam.blurb));
    b.appendChild(aEl("span", "door-line", aDoorLine(fam, mine)));
    /* WHERE YOU ARE, on the door rather than only on the card behind it: the
       one thing somebody wants from the front door is the way back into the
       lesson they were in, and that has to be visible before the first tap. */
    if (mine.some(function (c) { return c.current; })) {
      b.classList.add("here");
      b.appendChild(aEl("span", "door-tag", "you are in here"));
    }
    b.onclick = function () { openFamily(fam.id); };
    host.appendChild(b);
  });
  return drawn;
}

/* ------------------------------------------------------------ level two */
/* A CARD, IN HTML. Every field it carries was already in the payload and was
   already on the plane; what has changed is that the browser wraps the text
   instead of `gauge.js` measuring it, which is why a SHOUTED plan step can no
   longer run out of its box. */
function aCard(c, fam, withFamily) {
  var b = aEl("button", "ws-card");
  b.type = "button";
  if (c.current) b.classList.add("here");
  var news = !!c.news && !c.current;
  if (news) b.classList.add("news");

  /* WHERE IT CAME FROM, in the flat read only. Behind a door the family is the
     heading above the grid and repeating it on every card is furniture; in a
     list drawn from all six it is the one thing the card is missing. */
  if (withFamily) b.appendChild(aEl("span", "ws-family", fam.name || fam.id || ""));

  var top = aEl("div", "ws-top");
  top.appendChild(aEl("strong", "ws-name", c.course || c.repo || c.name));
  if (news) top.appendChild(aEl("span", "ws-dot news", ""));
  var job = c.mission && c.mission.state;
  if (job === "running" || job === "failed") {
    top.appendChild(aEl("span", "ws-dot mission " + job, ""));
  }
  b.appendChild(top);

  if (c.current) b.appendChild(aEl("span", "ws-tag here", "you are here"));

  if (c.next) {
    var lead = aEl("span", "ws-tag", c.kind === "book" ? "NEXT CHAPTER" : "NEXT");
    b.appendChild(lead);
    b.appendChild(aEl("span", "ws-next", c.next));
  }

  if (fam.vendor) {
    b.appendChild(aEl("span", "ws-meta", aTreeMeta(c)));
  } else if (c.running) {
    var live = aEl("span", "ws-meta live");
    live.appendChild(aEl("span", "ws-dot live", ""));
    live.appendChild(aEl("span", "", (c.node ? "live on " + c.node + "  ·  "
                                             : "live  ·  ") + aMeta(c)));
    b.appendChild(live);
  } else {
    b.appendChild(aEl("span", "ws-meta", aMeta(c)));
  }

  b.onclick = function () { openSheet(c, fam); };
  return b;
}

function paintFamily() {
  var fam = aFamily(atlasFamily);
  var host = els.cards;
  host.innerHTML = "";
  if (!fam) return 0;
  var mine = aIn(fam);
  mine.forEach(function (c) { host.appendChild(aCard(c, fam)); });
  return mine.length;
}

/* ------------------------------------------------------------ the levels */
/* GOING IN IS A TAP AND COMING BACK OUT HAS TO BE ONE TOO, and for most of this
   page's life it was not: the control was a small pill in the corner of the
   head, worded "all of it", and the head scrolled away with the page -- so
   somebody reading a family's cards had nothing on the glass that led back to
   the doors, and the only route out was to open a workspace and let the reload
   land on them.

   Three things carry it now. The button is first in the head, thumb-sized and
   named after where it goes; the head is sticky, so it is reachable from the
   bottom of the longest family; and going IN pushes a history entry, so the
   back gesture and the laptop's Escape key both come out.

   THE HISTORY ENTRY CARRIES NO URL OF ITS OWN, and that is deliberate: the hash
   on this page belongs to `address.js` and naming a family in it would put two
   grammars in one address. `pushState` with no url pushes an entry and leaves
   the address exactly as it was. */
var atlasPushed = false;   /* this page owns the entry the open family sits on */

function showFamily(id, scroll) {
  atlasFamily = id || "";
  paintLevels();
  if (!scroll) return;
  /* The head of the section, so the first card is where the eye already is. A
     family opened from a door two screens down would otherwise land with the
     cards below the fold -- and coming back out from the bottom of a long list
     would leave the doors above the top of the window. */
  try { els.atlasWrap.scrollIntoView({ block: "start", behavior: "smooth" }); }
  catch (e) { /* an older browser scrolls or it does not; neither is fatal */ }
}

function openFamily(id) {
  showFamily(id, true);
  try {
    history.pushState({ atlasFam: id }, "");
    atlasPushed = true;
  } catch (e) { /* no history is a page that still works, one tap at a time */ }
}

function closeFamily() {
  /* PAINTED FIRST, ADDRESSED SECOND. `history.back()` answers when the browser
     feels like it and the tap has to land now; the popstate that follows asks
     for the level this already painted, so it is a repaint of the same thing. */
  showFamily("", true);
  if (atlasPushed) {
    atlasPushed = false;
    try { history.back(); return; } catch (e) { /* then just leave the entry */ }
  }
  try { history.replaceState(null, ""); } catch (e) {}
}

/* The back gesture, and the browser's own button where there is one. A popped
   entry that names a family is that family; anything else is the doors. */
window.addEventListener("popstate", function (ev) {
  var st = (ev && ev.state) || null;
  var fam = st && st.atlasFam && aFamily(st.atlasFam) ? st.atlasFam : "";
  atlasPushed = !!fam;
  showFamily(fam, false);
});

/* ------------------------------------------------------------- flat read */
/* WHAT THE HIERARCHY CANNOT ANSWER. Two levels answer "what is in Courses";
   they cannot answer "where is the thing called colibri", because at the door
   no workspace is drawn at all and inside a family every other family's is
   hidden. This is the same payload read flat, and a match carries the family it
   came out of so the answer includes the way back to it. */
function atlasQuery() {
  return ((els.atlasQ && els.atlasQ.value) || "").trim().toLowerCase();
}

/* Everything one card could be called. The id and the repo are in here on
   purpose: a directory name is what somebody types when the pretty name has
   gone out of their head, and it is the name the rest of the board uses. */
function aHay(c, fam) {
  return [c.course, c.repo, c.name, c.id, c.chapter, c.drawn, c.next,
          fam.name, fam.id].filter(Boolean).join("  ").toLowerCase();
}

function aMatches(q) {
  var out = [];
  ((atlas && atlas.families) || []).forEach(function (fam) {
    aIn(fam).forEach(function (c) {
      if (aHay(c, fam).indexOf(q) >= 0) out.push({ c: c, fam: fam });
    });
  });
  /* The one you are in first, then anything with an answer waiting, then by
     when it was last touched. A list of matches is still a list of places to
     go, and the order is the same one the rest of the page uses. */
  out.sort(function (a, b) {
    var w = function (m) { return (m.c.current ? 2 : 0) + (m.c.news ? 1 : 0); };
    return (w(b) - w(a)) || ((b.c.touched || 0) - (a.c.touched || 0));
  });
  return out;
}

function paintFound(q) {
  var host = els.found;
  host.innerHTML = "";
  var hits = aMatches(q);
  hits.forEach(function (m) { host.appendChild(aCard(m.c, m.fam, true)); });
  return hits.length;
}

function clearFind() {
  if (els.atlasQ) els.atlasQ.value = "";
  paintLevels();
}

/* WHICH LEVEL IS ON THE GLASS. One function, because two things deciding which
   of three surfaces is showing is two states that drift apart. */
function paintLevels() {
  var q = atlasQuery();
  var fam = atlasFamily ? aFamily(atlasFamily) : null;
  if (!fam) atlasFamily = "";
  var doors = paintDoors();
  var here = fam ? paintFamily() : 0;
  var hits = q ? paintFound(q) : 0;
  /* A QUERY IS A LEVEL OF ITS OWN and it is drawn over whichever of the other
     two was showing. It does not close the family: clearing the field puts you
     back where you were typing, which is what a filter means. */
  els.doors.hidden = !!fam || !!q;
  els.cards.hidden = !fam || !!q;
  els.found.hidden = !q;
  els.atlasUp.hidden = !fam || !!q;
  if (els.atlasQClear) els.atlasQClear.hidden = !q;
  els.atlasWhat.textContent = q ? (hits + (hits === 1 ? " match" : " matches"))
                                : fam ? (fam.name || fam.id) : "Everything";
  els.atlasBlurb.textContent = q
    ? "everywhere, not just " + (fam ? (fam.name || fam.id) : "one family")
    : (fam ? (fam.blurb || "") : "");
  els.atlasBlurb.hidden = !(q || (fam && fam.blurb));
  els.atlasWrap.hidden = false;
  if (q && !hits) {
    els.atlasEmpty.hidden = false;
    els.atlasEmpty.textContent = "Nothing here is called that.";
  } else if (!q && !doors && !here) {
    els.atlasEmpty.hidden = false;
    els.atlasEmpty.textContent = "Nothing to draw yet.";
  } else if (!atlasSaid) {
    els.atlasEmpty.hidden = true;
  }
}

function atlasSay(text) {
  atlasSaid = text || "";
  els.atlasEmpty.hidden = !atlasSaid;
  if (atlasSaid) els.atlasEmpty.textContent = atlasSaid;
}

/* ------------------------------------------ an answer waiting somewhere else

   The board carries this strip too, and for the same reason; this is the half
   that is on screen when somebody comes back to the app rather than to a
   lesson. A turn set going before dinner finishes into an empty room, and the
   only thing that made it findable was remembering which workspace it was in.

   The fact comes off the atlas payload -- `news` per workspace, computed by
   `tutorboard/news.py` -- so this costs no request of its own. */
function answerAgo(when) {
  var secs = Math.max(0, Math.round(Date.now() / 1000 - (when || 0)));
  if (secs < 60) return "just now";
  var mins = Math.round(secs / 60);
  if (mins < 60) return mins + "m ago";
  var hrs = Math.round(mins / 60);
  if (hrs < 24) return hrs + "h ago";
  return Math.round(hrs / 24) + "d ago";
}

var answersShown = "";

function paintAnswers(payload) {
  if (!els.answers) return;
  var waiting = [];
  ((payload && payload.workspaces) || []).forEach(function (c) {
    if (c.news && !c.current) waiting.push(c);
  });
  waiting.sort(function (a, b) { return (b.news_at || 0) - (a.news_at || 0); });
  waiting = waiting.slice(0, 4);
  if (!waiting.length) {
    els.answers.hidden = true;
    els.answersList.textContent = "";
    answersShown = "";
    return;
  }
  var sig = waiting.map(function (c) {
    return c.id + "@" + Math.round(c.news_at || 0);
  }).join("~");
  els.answers.hidden = false;
  els.answersLead.textContent = waiting.length === 1
    ? "an answer is waiting"
    : waiting.length + " answers are waiting";
  if (sig === answersShown) return;
  answersShown = sig;
  els.answersList.textContent = "";
  waiting.forEach(function (c) {
    var row = document.createElement("button");
    row.type = "button";
    row.className = "answer-row";
    row.dataset.ws = c.id;
    var where = document.createElement("span");
    where.className = "answer-where";
    where.textContent = c.course || c.repo || c.id;
    var what = document.createElement("span");
    what.className = "answer-what";
    what.textContent = c.news_title || c.chapter || "the tutor wrote a card";
    var when = document.createElement("span");
    when.className = "answer-when";
    when.textContent = answerAgo(c.news_at);
    row.appendChild(where);
    row.appendChild(what);
    row.appendChild(when);
    /* THE SAME DOOR THE CARD OPENS. A notification that took a second route
       into a workspace would be a second behaviour to keep true; this is the
       sheet's own button, minus the sheet. */
    row.addEventListener("click", function () { openWorkspace(c); });
    els.answersList.appendChild(row);
  });
}

/* WHAT IS STILL RUNNING SOMEWHERE NOBODY IS LOOKING.

   "when I put colibri or anything on a mission, just because I close the iPad
    doesn't mean that should end. Next time I open the iPad and access the board,
    that mission should still be going or notify me somewhere if it's done."

   The panel above is a turn that finished. This is one that has not, and the
   front door is where it matters most: this page is what is open when somebody
   comes back to the app, so a job set going before bed is read from here rather
   than from the lesson it was left in.

   THE CURRENT WORKSPACE IS NOT EXCLUDED, and that is the one rule this panel
   does not share with the answers above it. A badge about an answer in the
   workspace you are standing in is furniture -- the lesson is one tap away. A
   mission is not: it was set going hours ago, the board does not open by
   itself, and "still going" about the workspace you are about to enter is
   exactly what somebody needs to know before they enter it. */
var MISSION_WORD = { running: "still going", done: "done", failed: "failed" };
var missionsShown = "";

function paintMissions(payload) {
  if (!els.missions) return;
  var going = [];
  ((payload && payload.workspaces) || []).forEach(function (c) {
    if (c.mission && c.mission.state) {
      going.push({ ws: c, m: c.mission });
    }
  });
  going.sort(function (a, b) { return (b.m.at || 0) - (a.m.at || 0); });
  going = going.slice(0, 4);
  if (!going.length) {
    els.missions.hidden = true;
    els.missionsList.textContent = "";
    missionsShown = "";
    return;
  }
  var sig = going.map(function (g) {
    return g.ws.id + "/" + g.m.id + "@" + g.m.state;
  }).join("~");
  var live = going.filter(function (g) { return g.m.state === "running"; }).length;
  els.missions.hidden = false;
  els.missionsLead.textContent = live === going.length
    ? (live === 1 ? "a mission is still going"
                  : live + " missions are still going")
    : (going.length === 1 ? "a mission has ended"
                          : going.length + " missions, and not all are running");
  if (sig === missionsShown) return;
  missionsShown = sig;
  els.missionsList.textContent = "";
  going.forEach(function (g) {
    var row = document.createElement("button");
    row.type = "button";
    row.className = "answer-row mission-row";
    row.dataset.ws = g.ws.id;
    row.dataset.state = g.m.state;
    var pill = document.createElement("span");
    pill.className = "mission-state";
    pill.textContent = MISSION_WORD[g.m.state] || g.m.state;
    var where = document.createElement("span");
    where.className = "answer-where";
    where.textContent = g.ws.course || g.ws.repo || g.ws.id;
    var what = document.createElement("span");
    what.className = "answer-what";
    what.textContent = (g.m.agent ? g.m.agent + ": " : "") + (g.m.task || "");
    var when = document.createElement("span");
    when.className = "answer-when";
    when.textContent = answerAgo(g.m.at);
    row.appendChild(pill);
    row.appendChild(where);
    row.appendChild(what);
    row.appendChild(when);
    if (g.m.state === "failed" && g.m.reason) {
      var why = document.createElement("span");
      why.className = "mission-why";
      why.textContent = g.m.reason;
      row.appendChild(why);
    }
    /* THE SAME DOOR EVERYTHING ELSE ON THIS PAGE OPENS. A mission that failed
       is one somebody has to go and look at, and a row that says so and cannot
       take them there is half a notification. */
    row.addEventListener("click", function () { openWorkspace(g.ws); });
    els.missionsList.appendChild(row);
  });
}


function paintAtlas(payload) {
  /* Outside the try below and before it: a picture that could not be drawn is
     not a reason to lose the one row that says work has come back. */
  try { paintAnswers(payload); } catch (e) { /* not the way back; the row is */ }
  try { paintMissions(payload); } catch (e) { /* likewise */ }
  /* NOTHING IN HERE MAY THROW. A front door that throws is a blank screen
     where the app used to be, and this one is the way back into a lesson. */
  try {
    atlas = payload || { families: [], workspaces: [], trees: [] };
    paintLevels();
  } catch (e) {
    try {
      atlasSay("the atlas could not be drawn; the door above still works");
    } catch (e2) { /* then there is nothing left to say it with */ }
  }
}

els.atlasUp.onclick = closeFamily;

/* The field repaints on every keystroke. There is no request behind it -- the
   atlas is already in memory -- so there is nothing to debounce and a delay
   would only be a list that lags the thumb. */
if (els.atlasQ) {
  els.atlasQ.addEventListener("input", function () {
    try { paintLevels(); } catch (e) { /* never a blank front door */ }
  });
  /* Enter on a single match opens it: the whole point of typing a name is that
     you already know which one you mean. */
  els.atlasQ.addEventListener("keydown", function (ev) {
    if (ev.key !== "Enter") return;
    var q = atlasQuery();
    if (!q) return;
    var hits = aMatches(q);
    if (hits.length === 1) { ev.preventDefault(); openSheet(hits[0].c, hits[0].fam); }
  });
}
if (els.atlasQClear) els.atlasQClear.onclick = clearFind;

/* THE WAY BACK, and there is one of them now rather than two.

   `recentre.js` owns the button: where it sits against the VISUAL viewport,
   how it is dragged, and what putting the page's own magnification back means.
   The atlas used to be a plane, which could be panned into empty space on top
   of that, and the control answering the first was page chrome a pinch took
   off the glass. Neither level here is a plane, so there is one way to be lost
   and one button for it. */
if (els.panic && window.Recentre) {
  window.Recentre.mount({ key: "board.panic", buttons: [{ el: els.panic }] });
}

/* ---------------------------------------------------------- the sheet */
var sheetFor = null;
var sheetTree = false;
var sheetTraceAt = "";      /* the address Trace it goes to, or "" */

function openSheet(c, fam) {
  sheetFor = c;
  fam = fam || aFamily(c.family) || {};
  /* A VENDOR TREE IS NOT A WORKSPACE, and the sheet is where that stops being
     an abstraction. There is no board to move, nothing to write up and nothing
     to hand in -- so the two buttons that do those things are not offered, and
     the sheet says plainly what this one is instead of leaving somebody to
     discover it by tapping. */
  var tree = !!fam.vendor;
  sheetTree = tree;
  sheetTraceAt = "";
  if (els.sheetTrace) els.sheetTrace.hidden = true;
  els.sheetFamily.textContent = fam.name || fam.id || "";
  els.sheetName.textContent = c.course || c.repo || c.name;
  els.sheetOpen.hidden = tree;
  els.sheetLibrary.hidden = tree;
  if (tree) {
    els.sheetWhere.textContent = c.id;
    els.sheetNextText.textContent = "";
    els.sheetNext.hidden = true;
    els.sheetMeta.textContent = aTreeMeta(c)
      + "  ·  pulled, not written: read and drawn, never handed work";
    /* AND THE ONE THING THAT CAN BE DONE WITH IT. A trace over a tree is a
       sitting in the workspace that is READING it -- there is no board in
       somebody else's repository, and the cards belong where the work is. So
       this is an address into the workspace the board is already serving, and
       where it is serving none of them there is nowhere to hold the sitting and
       the sheet says that instead of offering a button that cannot work. */
    var reading = aReading();
    sheetTraceAt = aTreeAddr(reading, c);
    if (els.sheetTrace) {
      els.sheetTrace.hidden = !sheetTraceAt;
      els.sheetTraceSub.textContent = sheetTraceAt
        ? "drawn in " + (reading.course || reading.repo)
          + ", where the board is — nothing is written to it"
        : "";
    }
    if (!sheetTraceAt) {
      els.sheetMeta.textContent += "  ·  open a workspace first: a trace over "
                                 + "it is a sitting in the one reading it";
    }
    els.sheet.hidden = false;
    return;
  }
  els.sheetWhere.textContent = c.id + (c.chapter ? "  ·  " + c.chapter : "");
  /* WHAT THE PERSON CALLS THIS WHOLE WORKSPACE, where they have drawn it. The
     one field the written map lends the front door, and it belongs on the sheet
     rather than on the card: a card already carries a name, what is next and
     how much is outstanding, and a fourth line on it is a paragraph. */
  if (c.drawn) {
    els.sheetWhere.textContent += "  ·  " + c.drawn;
  }
  if (c.next) {
    els.sheetNextText.textContent = c.next_label || c.next;
    els.sheetNext.hidden = false;
  } else {
    els.sheetNext.hidden = true;
  }
  els.sheetMeta.textContent = aMeta(c)
    + (c.running ? "  ·  live" + (c.node ? " on " + c.node : "") : "")
    + (c.stance === "do" ? "  ·  writes the code" : "");
  els.sheetOpenSub.textContent = c.current
    ? "you are already here"
    : "moves the board; the address does not change";
  els.sheetLibrarySub.textContent = c.current
    ? "everything written up in here"
    : "moves the board, then opens its library";
  els.sheet.hidden = false;
}

/* WHICH WORKSPACE IS READING, and it is the one the board is serving. A tree
   is not a workspace and has no board of its own, so the sitting a trace opens
   has to be held somewhere -- and "where the board already is" is the only
   answer that needs no second question asked of somebody holding a tablet. */
function aReading() {
  var found = null;
  ((atlas && atlas.workspaces) || []).forEach(function (c) {
    if (c.current) found = c;
  });
  return found;
}

/* The address of a tree, read in a workspace. Through the grammar like every
   other link on this page: an older cached shell with no `address.js` gets no
   button rather than a hand-built hash, because two spellings of a place is
   the one thing that file exists to prevent. */
function aTreeAddr(reading, tree) {
  if (!reading || !tree || !window.Address) return "";
  return window.Address.format({ ws: reading.id, surface: "tree",
                                 tree: tree.id });
}

function closeSheet() {
  els.sheet.hidden = true;
  sheetFor = null;
  sheetTree = false;
  sheetTraceAt = "";
}

els.sheetClose.onclick = closeSheet;
els.sheet.addEventListener("click", function (ev) {
  if (ev.target === els.sheet) closeSheet();
});
/* ONE WAY INTO A WORKSPACE. The sheet's button, a notification row, and
   anything else that opens one all come here: two routes in is two behaviours
   that drift, and the one that rots is the one used less often. */
function openWorkspace(c) {
  if (!c) return;
  /* THROUGH THE ADDRESS, not around it. A tap and a link have to do the same
     thing or there are two ways into a workspace and one of them will rot;
     `addrRoute` is the single one, and it reproduces exactly what this button
     did before. A shell with no grammar -- an older cached one -- falls back to
     the switch, which is the half that matters. */
  var at = addrOf(c);
  if (at) {
    addrDone = "";
    if (window.location.hash === at) addrRoute();
    else window.location.hash = at;
    return;
  }
  /* Already here: this is the door, not a switch. Going through /switch for a
     board that is already serving is a restart somebody did not ask for. */
  if (c.current) { location.href = "/board"; return; }
  switchTo(c.repo);
}

els.sheetOpen.onclick = function () {
  var c = sheetFor;
  closeSheet();
  openWorkspace(c);
};

/* The library of a workspace, from the front door. It is served by whichever
   board is answering at this address, so a workspace that is not the one being
   served has to be switched to first -- which is the same journey Open this
   makes, ending on a different page.

   ONE ROUTE TO A LIBRARY, for the reason `openWorkspace` is one route into a
   workspace: the sheet offers this and so does a commissioned document, and two
   spellings of the same journey is one of them rotting. */
function openLibrary(c) {
  if (!c) return;
  /* WHERE THIS CAME FROM, carried into the page, so its way back leads here
     rather than into a lesson nobody opened. The library's own default is
     `/board`, which is right when a lesson stepped sideways into it and wrong
     for every tap made from this sheet. */
  if (c.current) { location.href = "/library?from=home"; return; }
  switchTo(c.repo, "", "/library?from=home");
}

els.sheetLibrary.onclick = function () {
  var c = sheetFor;
  closeSheet();
  openLibrary(c);
};

/* THROUGH THE ADDRESS, the same way a workspace is opened. The board is already
   serving the workspace this names -- that is how the address was built -- so
   `addrRoute` sends it straight to the board, which draws the tree. */
if (els.sheetTrace) {
  els.sheetTrace.onclick = function () {
    var at = sheetTraceAt;
    closeSheet();
    if (!at) return;
    addrDone = "";
    if (window.location.hash === at) addrRoute();
    else window.location.hash = at;
  };
}

/* ------------------------------------------------------- the meeting deck */
/* "I have generally two — sometimes three — meetings per week to talk about my
    research… I want to be able to select which projects meeting notes are
    generated for… I want a presentation like the ones made for PSYCH-ASR
    created and rendered for me."

   The front door is what is open when somebody remembers they have a meeting
   in ten minutes, so it is where this lives. TWO QUESTIONS, in this order:
   how far back, and then which projects — with what each one HAS to report
   since that date beside it, because ticking bare names is guessing.

   ONE DECK. Making a new one REPLACES the one before it, which is what was
   asked for: this is a one-off communication tool and the only one worth
   keeping is the most recent. Nothing is lost by that — `meetings/` is
   tracked, so `git log` holds every deck there has ever been while the tree
   holds one.

   A build is LaTeX and takes a few seconds, so the button says what it is
   doing. Nothing a reader can be waiting on may be silent. */
var notesSince = "";       /* the period they chose */
var notesWant = {};        /* workspace id -> ticked */

function openNotes() {
  els.notesSaid.hidden = true;
  els.notesWhich.hidden = true;
  els.notesSince.hidden = false;
  els.notesTitle.textContent = "How far back?";
  notesSince = "";
  notesWant = {};
  sinceButtons(false);
  /* THE ONE FROM BEFORE, offered first, because that is what you want in the
     ten minutes before the meeting. */
  els.notesRead.hidden = true;
  fetch("/meeting/deck.json", { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (rec) {
      if (!rec || !rec.ok || !rec.built) return;
      els.notesRead.hidden = false;
      var n = (rec.workspaces || []).length;
      els.notesReadSub.textContent = n + (n === 1 ? " project" : " projects")
        + (rec.since ? ", " + rec.since : "")
        + ((rec.marked || []).length ? " · marked up" : "");
    })
    .catch(function () { /* no deck to offer is not an error worth painting */ });
  els.notes.hidden = false;
}

function closeNotes() { els.notes.hidden = true; }

function sinceButtons(off) {
  Array.prototype.forEach.call(
    els.notesSince.querySelectorAll("button"),
    function (b) { b.disabled = !!off; });
}

function notesSay(text, bad) {
  els.notesSaid.hidden = false;
  els.notesSaid.className = "sheet-line" + (bad ? " bad" : "");
  els.notesSaid.textContent = text;
}

/* WHICH PROJECTS, WITH WHAT EACH ONE HAS. `/notes/what` is `gather`'s own
   output per workspace — the same counts the deck itself is assembled from, so
   the list cannot disagree with the deck it produces. */
function askWhich(since) {
  notesSince = since;
  sinceButtons(true);
  notesSay("looking at what has landed…");
  fetch("/notes/what", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ since: since })
  }).then(function (r) { return r.json(); }).then(function (got) {
    sinceButtons(false);
    if (!got || !got.ok) {
      notesSay((got && got.detail) || "that period could not be read", true);
      return;
    }
    els.notesSaid.hidden = true;
    els.notesRead.hidden = true;
    els.notesSince.hidden = true;
    els.notesWhich.hidden = false;
    els.notesTitle.textContent = "Which projects?";
    els.notesWhichLine.textContent = "Since " + got.since
      + ". The ones that moved are already chosen.";
    paintWhich(got.workspaces || []);
  }).catch(function (e) {
    sinceButtons(false);
    notesSay(e.message || "the board did not answer", true);
  });
}

function paintWhich(list) {
  notesWant = {};
  els.notesList.innerHTML = "";
  list.forEach(function (w) {
    /* TICKED WHERE IT MOVED. That is what the deck covers when nobody says
       anything, so the default state of the list is the default behaviour. */
    notesWant[w.id] = !!w.moved;
    var b = document.createElement("button");
    b.type = "button";
    b.setAttribute("data-id", w.id);
    b.setAttribute("data-moved", w.moved ? "1" : "0");
    var tick = document.createElement("span");
    tick.className = "tick";
    var name = document.createElement("span");
    name.textContent = w.name;
    var what = document.createElement("span");
    what.className = "what";
    what.textContent = whatOf(w);
    b.appendChild(tick);
    b.appendChild(name);
    b.appendChild(what);
    b.onclick = function () {
      notesWant[w.id] = !notesWant[w.id];
      paintTicks();
    };
    els.notesList.appendChild(b);
  });
  paintTicks();
}

function whatOf(w) {
  if (!w.moved) return "nothing since";
  var bits = [];
  if (w.commits) bits.push(w.commits + (w.commits === 1 ? " commit" : " commits"));
  if (w.closed) bits.push(w.closed + (w.closed === 1 ? " step" : " steps") + " closed");
  if (!bits.length && w.files) bits.push(w.files + " files");
  return bits.join(", ");
}

function paintTicks() {
  var n = 0;
  Array.prototype.forEach.call(
    els.notesList.querySelectorAll("button"), function (b) {
      var on = !!notesWant[b.getAttribute("data-id")];
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.querySelector(".tick").textContent = on ? "✓" : "·";
      if (on) n += 1;
    });
  els.notesMake.disabled = !n;
  els.notesMakeSub.textContent = n
    ? n + (n === 1 ? " slide" : " slides") + ", replacing the last deck"
    : "choose at least one";
}

function makeDeck() {
  var want = Object.keys(notesWant).filter(function (id) { return notesWant[id]; });
  if (!want.length) return;
  els.notesMake.disabled = true;
  notesSay("writing it… LaTeX takes a moment.");
  fetch("/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ since: notesSince, want: want })
  }).then(function (r) { return r.json(); }).then(function (rec) {
    rec = rec || {};
    els.notesMake.disabled = false;
    if (!rec.ok && !rec.name) {
      notesSay(rec.detail || "the deck could not be written", true);
      return;
    }
    var covered = (rec.workspaces || []).length;
    /* THE DECK IS WRITTEN EVEN WHEN LaTeX IS NOT HAPPY. Saying only "failed"
       sends somebody off to write it again by hand, when the .tex is sitting
       there. */
    if (!rec.ok) {
      notesSay("It is written, but LaTeX would not typeset it. The source is "
               + "in " + rec.tex + ".", true);
      return;
    }
    notesSay(covered + (covered === 1 ? " slide" : " slides")
             + ". It is in meetings/, it replaced the one before it, and it is "
             + "staged for the next save.");
    els.notesRead.hidden = false;
    els.notesReadSub.textContent = covered
      + (covered === 1 ? " project" : " projects") + ", " + notesSince;
  }).catch(function (e) {
    els.notesMake.disabled = false;
    notesSay(e.message || "the board did not answer", true);
  });
}

if (els.notesBtn) els.notesBtn.onclick = openNotes;
if (els.notesClose) els.notesClose.onclick = closeNotes;
if (els.notesMake) els.notesMake.onclick = makeDeck;
if (els.notesBack) {
  els.notesBack.onclick = function () {
    els.notesWhich.hidden = true;
    els.notesSince.hidden = false;
    els.notesSaid.hidden = true;
    els.notesTitle.textContent = "How far back?";
  };
}
if (els.notes) {
  els.notes.addEventListener("click", function (ev) {
    if (ev.target === els.notes) closeNotes();
  });
}
if (els.notesSince) {
  els.notesSince.addEventListener("click", function (ev) {
    var b = ev.target.closest ? ev.target.closest("button[data-since]") : null;
    if (b && !b.disabled) askWhich(b.getAttribute("data-since"));
  });
}


/* --------------------------------------------- a paper or a deck, at the door */
/* "The ability to write a paper or a slide deck should just be an option on the
    homescreen, and from there I want to be able to specify which
    projects/course, and which sections/results."

   A PRODUCT IS NOT AN AIM, and this is where that stops being a slogan. Asking
   for a document used to mean being in a sitting in the workspace it is about,
   and the workspace it is about is usually not the one the board is serving --
   so the ask cost a switch, a sitting and a change to what that sitting was
   for, to produce something that never touches the lesson.

   THREE QUESTIONS, each replacing the last in one sheet: which product, which
   workspace, what it is over. They are in that order because each one narrows
   the next -- only the workspace knows what it has to write up -- and Back
   walks them in reverse.

   THE ASK IS WRITTEN WHERE THE WORK IS. `POST /writeup` with a `repo` puts it
   in that workspace's inbox, where its own assistant picks it up; the document
   lands in ITS library. Nothing appears on this board, and the sheet says so
   rather than leaving somebody watching for it here. */
var docProduct = "";      /* "paper" or "slides" */
var docAt = 1;            /* which of the three questions is on the glass */
var docWs = null;         /* the workspace it is being asked of */
var docRepo = "";         /* the bare directory that workspace lives in */
var docCalled = "";       /* what to call that workspace in a sentence */

function closeDoc() { els.doc.hidden = true; }

function docSay(text, bad) {
  els.docSaid.hidden = false;
  els.docSaid.className = "sheet-line" + (bad ? " bad" : "");
  els.docSaid.textContent = text;
}

function docButtons(host, off) {
  Array.prototype.forEach.call(host.querySelectorAll("button"),
    function (b) { b.disabled = !!off; });
}

/* WHICH QUESTION IS BEING ASKED, and only ever one of them. The title carries
   it: a sheet whose heading never changes is three screens wearing one. */
function docStep(n) {
  docAt = n;
  els.docMakes.hidden = n !== 1;
  els.docWhere.hidden = n !== 2;
  els.docScopes.hidden = n !== 3;
  els.docBack.hidden = n === 1;
  els.docSaid.hidden = true;
  els.docRead.hidden = true;
  if (n === 1) {
    els.docTitle.textContent = "Which one?";
    els.docLine.textContent = "Written where the work is, by whoever is working "
      + "there. It lands in that workspace's library.";
    return;
  }
  var word = docProduct === "slides" ? "deck" : "paper";
  if (n === 2) {
    els.docTitle.textContent = "Which workspace?";
    els.docLine.textContent = "The " + word + " is written in the workspace it "
      + "is about, not here.";
    els.docBackSub.textContent = "a paper or a deck";
    return;
  }
  els.docTitle.textContent = "What is it over?";
  els.docLine.textContent = "One " + word + ", about one part of " + docCalled + ".";
  els.docBackSub.textContent = "a different workspace";
}

function openDoc() {
  docProduct = "";
  docWs = null;
  docRepo = "";
  docCalled = "";
  docButtons(els.docMakes, false);
  docStep(1);
  els.doc.hidden = false;
}

/* WHICH WORKSPACE, OUT OF THE PAYLOAD THIS PAGE ALREADY POLLS. The atlas is in
   memory by the time anything here is tappable, so there is no request behind
   this list -- and a second source for it is a second list to go stale.

   A VENDOR TREE IS NOT OFFERED. Trees are a separate list for exactly this
   reason, and the family is asked as well, because a list that is right only
   because of how the payload happens to be shaped is right by accident. */
function paintDocWhere() {
  var host = els.docWhere;
  host.innerHTML = "";
  var drawn = 0;
  ((atlas && atlas.workspaces) || []).forEach(function (c) {
    var fam = aFamily(c.family) || {};
    if (fam.vendor) return;
    var b = document.createElement("button");
    b.type = "button";
    b.setAttribute("data-id", c.id);
    var name = document.createElement("span");
    name.textContent = c.course || c.repo || c.id;
    var sub = document.createElement("span");
    sub.className = "doc-sub";
    sub.textContent = (fam.name || c.family || "")
      + (c.current ? "  ·  where the board is" : "");
    b.appendChild(name);
    b.appendChild(sub);
    b.onclick = function () { docAskScopes(c); };
    host.appendChild(b);
    drawn += 1;
  });
  if (!drawn) {
    docSay("nothing is drawn yet to write one about", true);
  }
  return drawn;
}

/* WHAT IT IS OVER, ASKED OF THE WORKSPACE ITSELF. Only it knows what it has --
   its sections, its results, the evening just taught -- so the keys come from
   there and the order they arrive in is theirs. The wait says which workspace
   is being asked, and so does the failure: "it could not be read" beside three
   workspaces is a sentence about none of them. */
function docAskScopes(c) {
  docWs = c;
  docRepo = c.repo || "";
  docCalled = c.course || c.repo || c.id;
  els.docScopes.innerHTML = "";
  docStep(3);
  docSay("reading what " + docCalled + " has to write up…");
  fetch("/writeup/scopes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ repo: c.id })
  }).then(function (r) { return r.json(); }).then(function (got) {
    got = got || {};
    if (!got.ok) {
      docSay(got.error || (docCalled + " could not say what it has to write "
                           + "up"), true);
      return;
    }
    /* WHAT THE SERVER CALLS IT, from here on. The ask names the workspace the
       same way the answer did, rather than the page deriving a second spelling
       out of the atlas. */
    docRepo = got.repo || docRepo;
    docCalled = got.name || docCalled;
    els.docSaid.hidden = true;
    paintDocScopes(got.scopes || []);
  }).catch(function (e) {
    docSay(e.message || (docCalled + " did not answer"), true);
  });
}

function paintDocScopes(list) {
  var host = els.docScopes;
  host.innerHTML = "";
  if (!list.length) {
    docSay(docCalled + " has nothing to be written up yet", true);
    return;
  }
  list.forEach(function (sc) {
    var b = document.createElement("button");
    b.type = "button";
    b.setAttribute("data-scope", sc.key);
    var name = document.createElement("span");
    name.textContent = sc.label;
    b.appendChild(name);
    if (sc.what) {
      var sub = document.createElement("span");
      sub.className = "doc-sub";
      sub.textContent = sc.what;
      b.appendChild(sub);
    }
    b.onclick = function () { docAsk(sc.key); };
    host.appendChild(b);
  });
}

/* THE ASK ITSELF, and it carries the three answers and nothing else. The scope
   is a key the workspace handed out a moment ago; the server turns it back into
   the sentence the document is written to, because the page inventing that
   sentence is the page deciding what the scope means. */
function docAsk(scope) {
  docButtons(els.docScopes, true);
  docSay("asking " + docCalled + "…");
  fetch("/writeup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ makes: docProduct, repo: docRepo, scope: scope })
  }).then(function (r) { return r.json(); }).then(function (rec) {
    rec = rec || {};
    docButtons(els.docScopes, false);
    /* A REFUSAL IS PAINTED, NOT SWALLOWED. An assistant already busy in that
       workspace answers 409 with a sentence about what it is doing, and that is
       something a person can act on -- come back, or ask somewhere else. */
    if (!rec.ok) {
      docSay(rec.error || rec.detail || "it could not be asked for", true);
      return;
    }
    var where = rec.where || docCalled;
    var word = docProduct === "slides" ? "The deck" : "The paper";
    docSay(docWs && docWs.current
      ? word + " is being written in " + where + ". It appears in its library "
        + "rather than on the board."
      : word + " is being written in " + where + ". It appears in that "
        + "workspace's library, not on this board.");
    els.docRead.hidden = false;
    els.docReadSub.textContent = docWs && docWs.current
      ? "everything written up in " + where
      : "moves the board, then opens its library";
  }).catch(function (e) {
    docButtons(els.docScopes, false);
    docSay(e.message || "the board did not answer", true);
  });
}

if (els.docBtn) els.docBtn.onclick = openDoc;
if (els.docClose) els.docClose.onclick = closeDoc;
if (els.docRead) {
  els.docRead.onclick = function () {
    var c = docWs;
    closeDoc();
    openLibrary(c);
  };
}
if (els.docMakes) {
  els.docMakes.addEventListener("click", function (ev) {
    var b = ev.target.closest ? ev.target.closest("button[data-makes]") : null;
    if (!b || b.disabled) return;
    docProduct = b.getAttribute("data-makes");
    /* The step first, then the list: `docStep` clears what was said, and an
       empty atlas has something to say. */
    docStep(2);
    paintDocWhere();
  });
}
/* BACK WALKS THEM IN REVERSE, one question at a time, the way the deck's does.
   A Back that returns to the first question from the third is a Back nobody can
   predict. */
if (els.docBack) {
  els.docBack.onclick = function () {
    if (docAt === 3) { docStep(2); return; }
    docProduct = "";
    docStep(1);
  };
}
if (els.doc) {
  els.doc.addEventListener("click", function (ev) {
    if (ev.target === els.doc) closeDoc();
  });
}


/* ------------------------------------------------------------ the address */
/* THE FRONT DOOR IS THE ONLY THING THAT CAN MOVE THE ONE ADDRESS between two
   workspaces, so it is where every cross-workspace link lands. A board handed
   an address for somewhere else sends it here; this switches, and then goes on
   to the surface the address named.

   `address.js` is the grammar and `board.js` the resolver for surfaces inside a
   workspace. All this page decides is WHICH workspace, which is the one
   question it is the only page able to answer. */
var addrDone = "";          /* the address this page has already acted on */

function addrOf(c) {
  if (!window.Address || !c || !c.id) return "";
  return window.Address.format({ ws: c.id, surface: "workspace" });
}

function addrNow() {
  if (!window.Address) return null;
  try { return window.Address.parse(window.location.hash || ""); }
  catch (e) { return null; }
}

function addrRoute() {
  var a = addrNow();
  /* Not until the atlas has arrived: which workspaces exist is the whole of
     what this has to decide, and guessing is how a link opens the wrong one. */
  if (!a || !atlas) return;
  if (a.text === addrDone) return;
  addrDone = a.text;

  atlasSay("");
  var mine = null;
  (atlas.workspaces || []).forEach(function (c) { if (c.id === a.ws) mine = c; });
  if (!mine) {
    /* A MISS IS A MISS. Said on the atlas, where the person is looking, and the
       door above it still works. */
    atlasSay("there is no " + a.ws + " in this repository any more — "
             + "everything that is here is below");
    return;
  }

  /* A bare workspace address is the sheet's own "open", and lands exactly
     where that landed: the lesson if the board is already serving it, the
     front door of the workspace that was just opened otherwise. An address
     naming a SURFACE goes to the board, because that is where surfaces are. */
  var deep = a.surface !== "workspace";
  if (mine.current) {
    location.href = "/board" + (deep ? a.text : "");
    return;
  }
  switchTo(mine.repo, deep ? a.text : "");
}

window.addEventListener("hashchange", addrRoute);
/* ESCAPE UNWINDS ONE THING AT A TIME, outermost first: the sheet over the
   level, the document over the level, the deck, then the query, then the
   family. Closing two surfaces on one key is how somebody ends up two screens
   from where they were and cannot say which tap did it. */
document.addEventListener("keydown", function (ev) {
  if (ev.key !== "Escape") return;
  if (!els.sheet.hidden) closeSheet();
  else if (els.doc && !els.doc.hidden) closeDoc();
  else if (els.notes && !els.notes.hidden) closeNotes();
  else if (atlasQuery()) clearFind();
  else if (atlasFamily) closeFamily();
});

/* `addr`, when there is one, is where to go once the board has moved: the
   surface the link named, on the board itself. Without one this lands exactly
   where it always did.

   `page` is the other kind of destination: a whole page of the board's rather
   than a surface inside the lesson. `/library` is the one that wanted it, and
   it wanted it for the reason the address grammar does not cover it -- the
   library is not a place in a lesson. */
function switchTo(repo, addr, page) {
  if (moving) return;                 /* one at a time; a second tap is a queue */
  moving = { repo: repo };
  showBusy("opening " + repo + "…", "asking");
  fetch("/switch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo: repo })
  }).then(function (r) { return r.json(); }).then(function (res) {
    if (!res.ok) throw new Error(res.error || "switch failed");
    return waitForAddress(repo, Date.now());
  }).then(function () {
    /* Landed or not, this goes to the lesson. The board re-pointed the address
       at the course before it answered, so by here the switch has happened; the
       poll is only how we know not to reload too early. There is nothing to ask
       a person about, and asking was worse than useless -- from the iPad it read
       as a switch that could not be made. */
    location.href = page || (addr ? "/board" + addr : "/");
  }).catch(function (e) {
    showBusy("could not open " + repo, e.message || String(e));
    moving = null;
  });
}

/* Which course is answering at this address RIGHT NOW. Asking is the only
   honest way to know a switch has landed: the name is re-pointed by the board
   that took it, and the page cannot see that happen. */
function serving() {
  return fetch("/health?t=" + Date.now(), { cache: "no-store" })
    .then(function (r) { return r.json(); })
    .catch(function () { return null; });   /* mid-move the socket is closed */
}

/* Poll until the address actually serves what was asked for.

   This is the whole of the fix for "I had to tap it ten times": reloading the
   instant `/switch` answers lands on the board you were trying to leave, which
   reads exactly like a tap that did nothing — so you tap again, and every one
   of those taps was working. A board that has just taken the name answers this
   within a second or two; the ceiling is only there so a reload eventually
   happens whatever the network did. */
function waitForAddress(repo, began) {
  return serving().then(function (h) {
    if (h && h.dir === repo) return true;
    var waited = Math.round((Date.now() - began) / 1000);
    if (waited >= SWITCH_PATIENCE) return false;
    showBusy("opening " + repo + "…", waited > 2 ? "starting the board · "
             + waited + "s" : "starting the board");
    return new Promise(function (go) { setTimeout(go, 600); })
      .then(function () { return waitForAddress(repo, began); });
  });
}

var SWITCH_PATIENCE = 45;             /* seconds. A cold board start is slow. */
var moving = null;

/* One message, no questions. The overlay used to end in "ask again" / "stay
   here", which is a dead end wearing the clothes of a choice: the switch had
   in fact been made and the only thing wrong was that nothing had moved the
   address. Tapping the overlay dismisses it; that is all it does. */
function showBusy(text, sub) {
  els.busy.hidden = false;
  els.busyText.textContent = text;
  els.busySub.textContent = sub || "";
}

els.busy.onclick = function () {
  els.busy.hidden = true;
  moving = null;
  refresh();
};

/* ------------------------------------------------------------------ load */
function refresh() {
  if (moving) return Promise.resolve();   /* not while the address is in flight */
  return Promise.all([
    fetch("/board.json").then(function (r) { return r.json(); }),
    fetch("/atlas.json").then(function (r) { return r.json(); })
      .catch(function () { return null; }),
    fetch("/courses.json").then(function (r) { return r.json(); })
      .catch(function () { return {}; })
  ]).then(function (all) {
    els.dot.className = "dot live";
    paintBoard(all[0] || {});
    /* A board on an older tool serves no `/atlas.json`. Draw nothing rather
       than throw: the door above still works, which is the half that matters. */
    if (all[1]) paintAtlas(all[1]);
    else {
      atlasSay("this board is on an older version of the tool and has no "
               + "atlas to draw");
    }
    var w = (all[2] || {}).where;
    els.where.textContent = w || "";
    /* Only now: the atlas is what says which workspaces exist, and an address
       cannot be routed before that is known. */
    addrRoute();
  }).catch(function () {
    els.dot.className = "dot dead";
  });
}

refresh();
setInterval(function () { if (!document.hidden) refresh(); }, 20000);
document.addEventListener("visibilitychange", function () { if (!document.hidden) refresh(); });
window.addEventListener("focus", refresh);
window.addEventListener("pageshow", refresh);

/* ---------------------------------------------------------------- chrome */
var THEME_KEY = "board.theme";
function applyTheme(mode) {
  document.body.dataset.mode = mode;
  syncSystemTheme();
  try { localStorage.setItem(THEME_KEY, mode); } catch (e) {}
}
function syncSystemTheme() {
  var dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.body.classList.toggle("sys-dark", dark);
}
document.getElementById("btn-theme").onclick = function () {
  var order = ["auto", "light", "dark"];
  applyTheme(order[(order.indexOf(document.body.dataset.mode) + 1) % 3]);
};
document.getElementById("btn-reload").onclick = function () { location.reload(); };
if (window.matchMedia) {
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", syncSystemTheme);
}
try { applyTheme(localStorage.getItem(THEME_KEY) || "auto"); } catch (e) { applyTheme("auto"); }

/* ------------------------------------------------------------------ PWA */
if ("serviceWorker" in navigator && window.isSecureContext) {
  var hadController = !!navigator.serviceWorker.controller;
  var reloading = false;
  navigator.serviceWorker.addEventListener("controllerchange", function () {
    if (!hadController || reloading) return;
    reloading = true;
    location.reload();
  });
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).then(function (reg) {
      function check() { if (!document.hidden) { try { reg.update(); } catch (e) {} } }
      document.addEventListener("visibilitychange", check);
      window.addEventListener("pageshow", check);
      window.addEventListener("focus", check);
    }).catch(function () {});
  });
}
})();
