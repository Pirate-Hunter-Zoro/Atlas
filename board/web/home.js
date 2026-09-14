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
  atlasWrap: document.getElementById("atlas-wrap"),
  atlasPlane: document.getElementById("atlas-plane"),
  atlasSvg: document.getElementById("atlas-svg"),
  atlasEmpty: document.getElementById("atlas-empty"),
  atlasFit: document.getElementById("atlas-fit"),
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
  where: document.getElementById("where"),
  notes: document.getElementById("notes"),
  notesSince: document.getElementById("notes-since"),
  notesSaid: document.getElementById("notes-said"),
  notesClose: document.getElementById("notes-close"),
  notesBtn: document.getElementById("atlas-notes"),
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

/* ------------------------------------------------------------- the atlas */
/* GEOMETRY. Every number here is a constant, and that is the point: the same
   repository has to lay out identically on every device, or it is not a picture
   anybody can learn. Nothing below reads the width of the glass. */
var A_W = 300;              /* a card */
var A_GAP = 22;
var A_PAD = 16;             /* inside a card */
var A_ACROSS = 3;           /* cards per row, wrapping into bands below it */
var A_FAM_TOP = 46;         /* the family heading above its first row */
var A_FAM_GAP = 40;         /* between one family and the next */
var A_EDGE = 24;            /* around the whole plane */
var A_NAME = 16, A_NEXT = 12.5, A_META = 11.5, A_TAG = 9.5;
var A_NAME_LINES = 2, A_NEXT_LINES = 2;
var A_MIN_H = 118;

/* Below this the plane opens framed on the card you are IN rather than on the
   whole picture. The layout does not change -- only which part of it is in
   front of you when the page arrives. */
var A_NARROW = 640;

var atlas = null;                    /* the payload, as it arrived */
var atlasCards = [];                 /* laid out, with their boxes */
var atlasBox = { x0: 0, y0: 0, x1: 0, y1: 0 };
var atlasView = { k: 1, fit: 1, ox: 0, oy: 0, held: false };
var atlasHand = null;
var atlasDrawn = "";                 /* the signature of what is on the plane */
var A_LO = 0.35, A_HI = 2.2;

function aWrap(text, size, weight, room, lines) {
  return window.Gauge.wrap(text, size, weight, room, lines);
}

/* What a card is made of, and therefore how tall it is. Measured before
   anything is positioned, because the height of a row is the tallest card in
   it and that cannot be known by looking at one. */
function aShape(c) {
  var room = A_W - A_PAD * 2;
  var name = aWrap(c.course || c.repo, A_NAME, 650, room, A_NAME_LINES);
  var next = c.next ? aWrap(c.next, A_NEXT, 400, room, A_NEXT_LINES) : [];
  var h = A_PAD
        + name.length * 21
        + (next.length ? 16 + next.length * 17 : 6)
        + 22                                   /* the meta line */
        + A_PAD;
  return { name: name, next: next, h: Math.max(A_MIN_H, h) };
}

/* Where every card goes. Families in the order `atlas.json` gives them, cards
   alphabetical inside one, three across, wrapping into bands. */
function aLayout(payload) {
  var fams = (payload && payload.families) || [];
  var all = (payload && payload.workspaces) || [];
  var out = [], marks = [];
  var y = A_EDGE;
  var widest = A_EDGE + A_W;

  fams.forEach(function (fam) {
    var mine = all.filter(function (c) { return c.family === fam.id; });
    /* A family with nothing in it is not drawn. `vendor` and `board` have no
       workspaces by construction -- discovery skips them -- and a heading over
       empty space reads as something missing rather than as something absent
       on purpose. */
    if (!mine.length) return;

    marks.push({ fam: fam, x: A_EDGE, y: y });
    var top = y + A_FAM_TOP;

    for (var i = 0; i < mine.length; i += A_ACROSS) {
      var row = mine.slice(i, i + A_ACROSS);
      var tall = 0;
      row.forEach(function (c) {
        c._shape = aShape(c);
        if (c._shape.h > tall) tall = c._shape.h;
      });
      row.forEach(function (c, k) {
        var x = A_EDGE + k * (A_W + A_GAP);
        c._x = x; c._y = top; c._w = A_W; c._h = tall;
        out.push(c);
        if (x + A_W > widest) widest = x + A_W;
      });
      top += tall + A_GAP;
    }
    y = top - A_GAP + A_FAM_GAP;
  });

  atlasBox = { x0: 0, y0: 0, x1: widest + A_EDGE, y1: Math.max(y, A_EDGE) + A_EDGE };
  return { cards: out, marks: marks };
}

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

function aText(x, y, cls, text) {
  var t = window.Gauge.el("text", { x: x, y: y, class: cls });
  t.textContent = text;
  return t;
}

function paintAtlas(payload) {
  /* NOTHING IN HERE MAY THROW. A front door that throws is a blank screen
     where the app used to be, and this one is the way back into a lesson. The
     same wrapping `paintMap` has, for the same reason. */
  try {
    paintAtlasNow(payload);
  } catch (e) {
    try {
      els.atlasEmpty.hidden = false;
      els.atlasEmpty.textContent = "the atlas could not be drawn; the door above "
                                 + "still works";
    } catch (e2) { /* then there is nothing left to say it with */ }
  }
}

function paintAtlasNow(payload) {
  atlas = payload || { families: [], workspaces: [] };
  var laid = aLayout(atlas);
  atlasCards = laid.cards;

  els.atlasEmpty.hidden = !!atlasCards.length;
  els.atlasWrap.hidden = false;

  /* Repaint only when the picture has actually changed. The page polls every
     twenty seconds and an SVG rebuilt under a finger is a pan that stutters. */
  var sig = atlasCards.map(function (c) {
    return [c.id, c.course, c.next, c.open, c.cards, c.running, c.node,
            Math.round((c.touched || 0) / 60), c.current].join("|");
  }).join("~");
  if (sig === atlasDrawn) return;
  atlasDrawn = sig;

  var svg = els.atlasSvg;
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  var g = window.Gauge.el("g", { id: "atlas-g" });
  svg.appendChild(g);

  laid.marks.forEach(function (m) {
    g.appendChild(aText(m.x, m.y + 13, "fam-label", m.fam.name || m.fam.id));
    if (m.fam.blurb) {
      g.appendChild(aText(m.x, m.y + 31, "fam-blurb", m.fam.blurb));
    }
    g.appendChild(window.Gauge.el("line", {
      x1: m.x, y1: m.y + 38, x2: atlasBox.x1 - A_EDGE, y2: m.y + 38,
      class: "fam-rule"
    }));
  });

  atlasCards.forEach(function (c) {
    var here = !!c.current;
    g.appendChild(window.Gauge.el("rect", {
      x: c._x, y: c._y, width: c._w, height: c._h, rx: 10,
      class: "card-box" + (here ? " here" : "")
    }));

    var tx = c._x + A_PAD;
    var ty = c._y + A_PAD + 14;
    c._shape.name.forEach(function (line) {
      g.appendChild(aText(tx, ty, "card-name" + (here ? " here" : ""), line));
      ty += 21;
    });

    if (c._shape.next.length) {
      ty += 12;
      g.appendChild(aText(tx, ty, "card-tag", c.kind === "book" ? "NEXT CHAPTER" : "NEXT"));
      ty += 14;
      c._shape.next.forEach(function (line) {
        g.appendChild(aText(tx, ty, "card-next", line));
        ty += 17;
      });
    }

    /* A board that is up, drawn as a dot rather than written as a word: it is
       the one thing on a card somebody looks for rather than reads. */
    var my = c._y + c._h - A_PAD - 2;
    if (c.running) {
      g.appendChild(window.Gauge.el("circle", {
        cx: tx + 4, cy: my - 4, r: 4, class: "card-live"
      }));
      g.appendChild(aText(tx + 14, my, "card-meta",
                          (c.node ? "live on " + c.node + "  ·  " : "live  ·  ") + aMeta(c)));
    } else {
      g.appendChild(aText(tx, my, "card-meta", aMeta(c)));
    }

    /* The whole card is the target, over the top of everything, so a tap never
       lands between two words and does nothing. */
    var hit = window.Gauge.el("rect", {
      x: c._x, y: c._y, width: c._w, height: c._h, rx: 10, class: "card-hit"
    });
    hit.addEventListener("click", function () { openSheet(c); });
    g.appendChild(hit);
  });

  if (!atlasView.held) atlasFrame();
  atlasApply();
}

/* ---------------------------------------------------------- the plane */
function atlasSize() {
  return { w: els.atlasPlane.clientWidth || 1, h: els.atlasPlane.clientHeight || 1 };
}

function atlasRoom() {
  var s = atlasSize();
  return window.Plane.room(atlasBox, s.w, s.h, atlasView.k, 0.35);
}

function atlasApply() {
  var s = atlasSize();
  window.Plane.clamp(atlasView, atlasRoom(), s.w, s.h);
  var g = document.getElementById("atlas-g");
  if (g) {
    g.setAttribute("transform", "translate(" + atlasView.ox + "," + atlasView.oy
                                + ") scale(" + atlasView.k + ")");
  }
}

/* Frame the whole plane -- or, on a narrow screen, the card you are IN.
   The layout is the same picture either way; this only decides which part of
   it the page opens on, because a 300-unit card fitted to a 390-unit phone is
   a picture nobody can read. */
function atlasFrame(force) {
  var s = atlasSize();
  if (!s.w || !s.h) return;
  var mine = null;
  for (var i = 0; i < atlasCards.length; i++) {
    if (atlasCards[i].current) { mine = atlasCards[i]; break; }
  }
  if (!force && mine && s.w < A_NARROW) {
    window.Plane.frame(atlasView,
      { x0: mine._x, y0: mine._y, x1: mine._x + mine._w, y1: mine._y + mine._h },
      s.w, s.h, 18, A_LO, A_HI);
  } else {
    window.Plane.frame(atlasView, atlasBox, s.w, s.h, 12, A_LO, A_HI);
  }
  atlasView.fit = atlasView.k;
  atlasView.held = false;
  atlasApply();
}

els.atlasFit.onclick = function () { atlasFrame(true); };

/* The gestures. `plane-core.js` owns what a gesture IS -- which contacts are
   live, which two a pinch is between, when a refusal expires -- so this is only
   the bookkeeping of moving one surface. Read that file before changing a line
   of it. */
var atlasDrag = null;

els.atlasPlane.addEventListener("pointerdown", function (ev) {
  if (!window.Plane) return;
  if (!atlasHand) atlasHand = window.Plane.contacts({});
  atlasHand.note(ev.pointerId, ev.clientX, ev.clientY);
  try { els.atlasPlane.setPointerCapture(ev.pointerId); } catch (e) { /* not fatal */ }
  var live = atlasHand.live();
  if (live.length >= 2) {
    atlasDrag = null;
    atlasHand.begin(atlasView.k);
  } else {
    atlasDrag = { x: ev.clientX, y: ev.clientY, ox: atlasView.ox, oy: atlasView.oy,
                  moved: false };
  }
});

els.atlasPlane.addEventListener("pointermove", function (ev) {
  if (!atlasHand) return;
  atlasHand.note(ev.pointerId, ev.clientX, ev.clientY);
  var spread = atlasHand.spread();
  if (spread) {
    var r = els.atlasPlane.getBoundingClientRect();
    window.Plane.zoomAbout(atlasView, spread.k, spread.cx - r.left, spread.cy - r.top,
                           A_LO, A_HI);
    atlasApply();
    return;
  }
  if (atlasDrag && atlasHand.live().length === 1) {
    var dx = ev.clientX - atlasDrag.x, dy = ev.clientY - atlasDrag.y;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) atlasDrag.moved = true;
    atlasView.ox = atlasDrag.ox + dx;
    atlasView.oy = atlasDrag.oy + dy;
    atlasView.held = true;
    atlasApply();
  }
});

function atlasRelease(ev) {
  if (!atlasHand) return;
  atlasHand.forget(ev.pointerId);
  if (!atlasHand.live().length) atlasDrag = null;
}
els.atlasPlane.addEventListener("pointerup", atlasRelease);
els.atlasPlane.addEventListener("pointercancel", atlasRelease);
window.addEventListener("pointerup", atlasRelease);

/* A pan must not also be a tap. Without this, dragging the plane with a finger
   that started on a card opened that card when it was lifted. */
els.atlasPlane.addEventListener("click", function (ev) {
  if (atlasDrag && atlasDrag.moved) {
    ev.stopPropagation();
    ev.preventDefault();
  }
}, true);

els.atlasPlane.addEventListener("wheel", function (ev) {
  if (!window.Plane) return;
  ev.preventDefault();
  var r = els.atlasPlane.getBoundingClientRect();
  var k = atlasView.k * (ev.deltaY < 0 ? 1.12 : 1 / 1.12);
  window.Plane.zoomAbout(atlasView, k, ev.clientX - r.left, ev.clientY - r.top,
                         A_LO, A_HI);
  atlasApply();
}, { passive: false });

window.addEventListener("resize", function () {
  if (!atlasView.held) atlasFrame();
  else atlasApply();
});

/* ---------------------------------------------------------- the sheet */
var sheetFor = null;

function openSheet(c) {
  sheetFor = c;
  var fam = "";
  (atlas.families || []).forEach(function (f) {
    if (f.id === c.family) fam = f.name || f.id;
  });
  els.sheetFamily.textContent = fam;
  els.sheetName.textContent = c.course || c.repo;
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
  els.sheet.hidden = false;
}

function closeSheet() {
  els.sheet.hidden = true;
  sheetFor = null;
}

els.sheetClose.onclick = closeSheet;
els.sheet.addEventListener("click", function (ev) {
  if (ev.target === els.sheet) closeSheet();
});
els.sheetOpen.onclick = function () {
  var c = sheetFor;
  closeSheet();
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
};

/* ------------------------------------------------------ notes for a meeting */
/* "have functionality to produce 'meeting notes' for me with in-built links
    that will take me to those results/code/sections of my board writing to
    explain those notes."

   The front door is what is open when somebody remembers they have a meeting in
   ten minutes, so it is where this lives. One question is asked -- how far back
   -- because it is the only one whose answer the person actually has. WHICH
   workspaces is not asked: the answer is "the ones that moved", and that is
   what the note does anyway.

   A build is LaTeX and can take a few seconds, so the button says what it is
   doing and the panel stays open until there is something to say. Nothing a
   reader can be waiting on may be silent. */
function openNotes() {
  els.notesSaid.hidden = true;
  Array.prototype.forEach.call(
    els.notesSince.querySelectorAll("button"),
    function (b) { b.disabled = false; });
  els.notes.hidden = false;
}

function closeNotes() { els.notes.hidden = true; }

function notesSay(text, bad) {
  els.notesSaid.hidden = false;
  els.notesSaid.className = "sheet-line" + (bad ? " bad" : "");
  els.notesSaid.textContent = text;
}

function makeNotes(since) {
  Array.prototype.forEach.call(
    els.notesSince.querySelectorAll("button"),
    function (b) { b.disabled = true; });
  notesSay("writing them… LaTeX takes a moment.");
  fetch("/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ since: since })
  }).then(function (r) { return r.json(); }).then(function (rec) {
    rec = rec || {};
    if (!rec.ok && !rec.name) {
      notesSay(rec.detail || "the notes could not be written", true);
      Array.prototype.forEach.call(
        els.notesSince.querySelectorAll("button"),
        function (b) { b.disabled = false; });
      return;
    }
    var covered = (rec.workspaces || []).length;
    /* THE NOTE IS WRITTEN EVEN WHEN LaTeX IS NOT HAPPY. Saying only "failed"
       sends somebody off to write it again by hand, when the markdown and the
       .tex are both sitting there. */
    if (!rec.ok) {
      notesSay(rec.name + " is written, but LaTeX would not typeset it. "
               + "The text of it is in " + rec.tex + ".", true);
      return;
    }
    notesSay(rec.name + " — " + covered
             + (covered === 1 ? " workspace" : " workspaces")
             + ". It is in meetings/, and staged for the next save.");
    if (rec.pdf) {
      var a = document.createElement("a");
      a.className = "action primary";
      a.href = "/meeting/" + encodeURIComponent(rec.name);
      a.target = "_blank";
      a.rel = "noopener";
      a.innerHTML = '<span class="action-name">Read it</span>';
      els.notesSaid.insertAdjacentElement("afterend", a);
    }
  }).catch(function (e) {
    notesSay(e.message || "the board did not answer", true);
    Array.prototype.forEach.call(
      els.notesSince.querySelectorAll("button"),
      function (b) { b.disabled = false; });
  });
}

if (els.notesBtn) els.notesBtn.onclick = openNotes;
if (els.notesClose) els.notesClose.onclick = closeNotes;
if (els.notes) {
  els.notes.addEventListener("click", function (ev) {
    if (ev.target === els.notes) closeNotes();
  });
}
if (els.notesSince) {
  els.notesSince.addEventListener("click", function (ev) {
    var b = ev.target.closest ? ev.target.closest("button[data-since]") : null;
    if (b && !b.disabled) makeNotes(b.getAttribute("data-since"));
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

  var mine = null;
  (atlas.workspaces || []).forEach(function (c) { if (c.id === a.ws) mine = c; });
  if (!mine) {
    /* A MISS IS A MISS. Said on the atlas, where the person is looking, and the
       door above it still works. */
    els.atlasEmpty.hidden = false;
    els.atlasEmpty.textContent = "there is no " + a.ws + " in this repository "
                               + "any more — everything that is here is below";
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
document.addEventListener("keydown", function (ev) {
  if (ev.key !== "Escape") return;
  if (!els.sheet.hidden) closeSheet();
  else if (els.notes && !els.notes.hidden) closeNotes();
});

/* `addr`, when there is one, is where to go once the board has moved: the
   surface the link named, on the board itself. Without one this lands exactly
   where it always did. */
function switchTo(repo, addr) {
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
    location.href = addr ? "/board" + addr : "/";
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
      els.atlasEmpty.hidden = false;
      els.atlasEmpty.textContent = "this board is on an older version of the tool "
                                 + "and has no atlas to draw";
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
