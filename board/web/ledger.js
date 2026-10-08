/* ==========================================================================
   ledger.js -- a round of feedback as PAIRS: what you wrote, and what was done.

   The owner's words: "I need some nifty way to keep track of what each edit
   request was, and what was done to address it, so that I don't have to read
   the whole fucking paper again." And once a round was answered: the ink
   still on the page "feels a little... messy". So an answered round takes its
   ink OFF the page and puts it in a panel, a pair to a row: the ink as drawn
   (its crop) or the words typed, and under it the revision -- the changed
   wording with what went struck and what came in marked, or the turn's
   one-line reply where it answered without an edit.

   ON THE PAGE, a numbered pip in the margin where each pair is, the number its
   row carries. A tap on a row brings its place onto the glass (zoomed to at
   least `ZOOM_AT_LEAST`, centred), flashes the revised passage and lays a
   faint ghost of the ink over it; a tap on a pip opens the panel at its row.
   A pair is marked FINE (its pip goes) or NOT FIXED with a line of why (it
   rides the next round under its id, and its ink stays at full strength). A
   round with every pair fine is one line, "Round 3 done".

   The server does the work (`course/ledger.py`): it filed the round, validated
   the answers, and placed each pair on the build on disk -- `at` for the pip,
   `ink_at` for the ghost, both in fractions of the page, so both scale with
   the zoom exactly as the ink does. Nothing here is in pixels of the page.

   THE PANEL NEVER COVERS THE JUMPED-TO PASSAGE: a rail at the right on a wide
   landscape glass, with the pages narrowed beside it, and a sheet at the foot
   otherwise, with the passage centred in what is left above it.

     Ledger.make({ pages, button, changed, zoom, send, scrolled })
       -> { open(doc, on), refresh(), toggle(), next(), close(), redraw(),
            escape(), select(id), isOn(), showing() }
     Ledger.preview(el, items, merged, onMerge)   the filing panel's split
   ========================================================================== */

(function () {
"use strict";

var WORDS = { "done": "done", "partly": "partly done", "not done": "not done",
              "pushed back": "pushed back" };
/* A jump brings the passage up to at least this zoom: at the fit a sentence
   on a letter page is small enough to need a second look. */
var ZOOM_AT_LEAST = 1.25;
var FLASH_MS = 1200;
/* `annotate.js` `PAGE_REF`: a page stroke's width is stored against it. */
var PAGE_REF = 1240;
/* The least distance between two pips' tops, in widths of the page: the
   disc is 3.2cqw across, so 3.6 leaves a hair between them. */
var PIP_GAP = 0.036;
var RAIL = "(min-width: 56rem) and (orientation: landscape)";
var SVG = "http://www.w3.org/2000/svg";

function el(tag, cls, text) {
  var e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined && text !== null) e.textContent = text;
  return e;
}

function button(label, cls, fn) {
  var b = el("button", cls, label);
  b.type = "button";
  b.addEventListener("click", fn);
  return b;
}

/* Which colour a pair is: what was done, or that nothing was said. */
function tone(item) {
  if (item.answer) return item.answer.disposition.replace(/ /g, "-");
  return item.status === "waiting" ? "waiting" : "none";
}

function said(item) {
  if (item.answer) return WORDS[item.answer.disposition] || item.answer.disposition;
  return item.status === "waiting" ? "waiting for the revision" : "not answered";
}

/* INK THAT IS STILL OWED stays at full strength until it is judged: nothing
   answered it, the turn could not do it, or it was sent back as not fixed. */
function owed(item) {
  if (item.carried) return false;
  if (item.state === "reopened") return true;
  if (item.state !== "open") return false;
  return item.status === "not answered"
    || !!(item.answer && item.answer.disposition === "not done");
}

function penOn() { return !!(window.Annotate && window.Annotate.isOn && window.Annotate.isOn()); }

function make(opts) {
  var pages = opts.pages;
  var btn = opts.button || null;
  var zoomer = opts.zoom || null;
  var host = (pages && pages.parentNode) || document.body;
  var doc = null;
  var data = null;
  var pick = 0;               /* which round: 0 is the newest */
  var shown = false;          /* the panel */
  var want = false;           /* open the panel once the round is in */
  var sel = "";               /* the selected pair's id */
  var full = "";              /* the pair whose full wording is out */
  var unfold = {};            /* finished rounds opened anyway, by note */
  var asked = 0;
  var flashing = 0;

  /* THE PANEL, built once, kept beside the reader. */
  var panel = el("aside", "lg-panel");
  panel.id = "lg-panel";
  panel.hidden = true;
  panel.setAttribute("aria-label", "the round's notes and what was done");
  var head = el("div", "lg-ph");
  var title = el("strong", "lg-title");
  var sub = el("span", "lg-sub");
  var shut = button("✕", "lg-x", function () { hide(); });
  shut.title = "close";
  head.appendChild(title);
  head.appendChild(sub);
  head.appendChild(shut);
  var body = el("div", "lg-scroll");
  var foot = el("div", "lg-foot");
  foot.hidden = true;
  panel.appendChild(head);
  panel.appendChild(body);
  panel.appendChild(foot);
  document.body.appendChild(panel);

  if (btn) btn.addEventListener("click", function () { toggle(); });
  if (btn) btn.hidden = true;

  var rail = null;
  try { rail = window.matchMedia ? window.matchMedia(RAIL) : null; } catch (e) { rail = null; }
  function railed() { return !!(rail && rail.matches); }
  if (rail && rail.addEventListener) rail.addEventListener("change", function () { place(); });
  window.addEventListener("resize", function () { place(); });

  function round() { return (data && data.rounds && data.rounds[pick]) || null; }

  function has(d) { return !!(d && d.ledger && d.ledger.rounds); }

  /* The round the glass opens on: the newest that came back and still has a
     pair nobody has judged, else the newest. */
  function first() {
    var rs = (data && data.rounds) || [];
    for (var i = 0; i < rs.length; i++) {
      if (rs[i].landed && !rs[i].done) return i;
    }
    return 0;
  }

  function rows(r) {
    return ((r && r.items) || []).slice().sort(function (a, b) {
      return (a.n || 0) - (b.n || 0);
    });
  }

  function find(id) {
    var r = round();
    return ((r && r.items) || []).filter(function (i) { return i.id === id; })[0] || null;
  }

  /* A document opened, or -- the same document with `on` unsaid -- its record
     come back from a reload of the list, which keeps what is showing. */
  function open(d, on) {
    if (doc && d && doc.id === d.id && on === undefined) {
      doc = d;
      label();
      if (has(d)) refresh();
      return;
    }
    doc = d;
    data = null;
    pick = 0;
    sel = "";
    full = "";
    unfold = {};
    want = !!on;
    if (!on) hide(true);
    label();
    paint();
    if (has(d)) refresh();
  }

  function label() {
    if (!btn) return;
    btn.hidden = !has(doc);
    btn.classList.toggle("on", shown);
    var r = data && data.rounds && data.rounds[0];
    var t = "◉ notes";
    if (r) {
      var n = r.items.length;
      t = "Round " + r.round + (!r.landed ? " · revising"
        : r.done ? " done"
        : r.judged ? " · " + r.open + " open"
        : " · " + n + (n === 1 ? " note" : " notes"));
    }
    btn.textContent = t;
  }

  /* Escape closes the panel, and says whether it did. */
  function escape() {
    if (shown) { hide(); return true; }
    return false;
  }

  function refresh() {
    if (!doc || !has(doc)) return Promise.resolve();
    var mine = ++asked;
    var id = doc.id;
    return fetch("/library/ledger/" + encodeURIComponent(id),
                 { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (got) {
        if (mine !== asked || !doc || doc.id !== id) return;
        var had = !!data;
        data = got && got.ok ? got : null;
        if (!had || pick >= ((data && data.rounds) || []).length) pick = first();
        if (sel && !find(sel)) sel = "";
        label();
        if (want && data) { want = false; show(); }
        paint();
      })
      .catch(function () { /* the pairs are extra; the pages are still there */ });
  }

  function toggle() {
    if (shown) hide(); else show();
  }

  function show() {
    shown = true;
    panel.hidden = false;
    label();
    place();
    paint();
  }

  function hide(quiet) {
    shown = false;
    panel.hidden = true;
    sel = "";
    full = "";
    host.classList.remove("lg-railed", "lg-sheeted");
    label();
    if (!quiet) paint();
  }

  function close() {
    doc = null;
    data = null;
    hide(true);
    if (btn) { btn.hidden = true; btn.classList.remove("on"); }
    paint();
  }

  /* Rail or sheet, and the pages making room for whichever it is. */
  function place() {
    var r = railed();
    panel.classList.toggle("lg-rail", r);
    panel.classList.toggle("lg-sheet", !r);
    host.classList.toggle("lg-railed", shown && r);
    host.classList.toggle("lg-sheeted", shown && !r);
    if (pages && r) {
      var top = pages.getBoundingClientRect().top;
      panel.style.top = Math.max(0, Math.round(top)) + "px";
    } else {
      panel.style.top = "";
    }
  }

  /* ---------------------------------------------------------- the pages */
  function figure(page) {
    return pages ? pages.querySelector('.lib-page[data-page="' + page + '"]') : null;
  }

  /* A pip shows while its round has come back, is not finished, and the pair
     has not been said to be fine. */
  function pipped(r, item) {
    return !!(r && r.landed && !r.done && item.at && item.state !== "accepted"
              && !item.carried);
  }

  function paint() {
    if (!pages) return;
    Array.prototype.forEach.call(
      pages.querySelectorAll(".lg-pip, .lg-mark, .lg-ghost"),
      function (n) { n.parentNode.removeChild(n); });
    var r = round();
    if (r && doc) {
      var pips = rows(r).filter(function (item) { return pipped(r, item); });
      apart(pips).forEach(function (p) { pip(p[0], p[1]); });
      /* OWED INK FROM EVERY ROUND, not only the one the panel shows: the live
         ink went when its round landed, so this is the only place it is still
         on the page. A not-fixed pair riding a round still being revised is
         owed too -- its ink must not vanish while the turn works on it. */
      (data.rounds || []).forEach(function (x) {
        (x.items || []).forEach(function (item) {
          if (x.landed ? owed(item) : item.kind === "reopened") ghost(item, "lg-full");
        });
      });
      var s = sel ? find(sel) : null;
      if (s) {
        if (!(r.landed && owed(s))) ghost(s, "lg-faint");
        mark(s);
      }
    }
    panelPaint();
  }

  /* The page's height over its width, from the picture where it has loaded. */
  function aspect(fig) {
    var img = fig.querySelector("img");
    return img && img.naturalWidth && img.naturalHeight
      ? img.naturalHeight / img.naturalWidth
      : (fig.offsetWidth && fig.offsetHeight ? fig.offsetHeight / fig.offsetWidth : 11 / 8.5);
  }

  /* PIPS NEVER SIT ON EACH OTHER. Two pairs a line apart would put one disc
     over the other, and neither number could be read or tapped. Down each
     page, a pip closer than `PIP_GAP` of the page's width to the one above is
     pushed down to that gap. The gap is a fraction of the page, so the
     spacing scales with the zoom like everything else on it. -> [[item, y]] */
  function apart(list) {
    var out = [], last = {};
    list.slice().sort(function (a, b) {
      return a.at.page - b.at.page || a.at.y - b.at.y;
    }).forEach(function (item) {
      var fig = figure(item.at.page);
      if (!fig) return;
      var gap = PIP_GAP / aspect(fig);
      var y = item.at.y;
      var above = last[item.at.page];
      if (above !== undefined && y < above + gap) y = above + gap;
      last[item.at.page] = y;
      out.push([item, y]);
    });
    return out;
  }

  function pip(item, y) {
    var fig = figure(item.at.page);
    if (!fig) return;
    var p = button("", "lg-pip lg-" + tone(item)
      + (item.id === sel ? " lg-on" : "") + (item.state === "reopened" ? " lg-back" : ""),
      function (ev) {
        ev.stopPropagation();
        /* With the pen out a page is for writing on, and a pip is not a
           button under the nib. */
        if (penOn()) return;
        select(item.id, "pip");
      });
    p.appendChild(el("span", "", String(item.n)));
    p.dataset.id = item.id;
    p.title = item.n + ". " + said(item);
    p.style.top = ((y === undefined ? item.at.y : y) * 100).toFixed(2) + "%";
    fig.appendChild(p);
  }

  /* The revised passage, boxed while its pair is selected. */
  function mark(item) {
    if (!item.at || !item.at.box) return;
    var fig = figure(item.at.page);
    if (!fig) return;
    var b = item.at.box;
    var m = el("div", "lg-mark lg-" + tone(item) + (flashing ? " lg-flash" : ""));
    m.dataset.id = item.id;
    m.style.left = (b[0] * 100).toFixed(2) + "%";
    m.style.top = (b[1] * 100).toFixed(2) + "%";
    m.style.width = ((b[2] - b[0]) * 100).toFixed(2) + "%";
    m.style.height = ((b[3] - b[1]) * 100).toFixed(2) + "%";
    fig.appendChild(m);
  }

  /* THE INK AS IT WAS DRAWN, archived with the round and laid back on the
     page: in the page's own units (`PAGE_REF` across), shifted by however far
     its words moved, so it scales with the zoom the way live ink does. */
  function ghost(item, strength) {
    var ink = item.ink;
    var at = item.ink_at;
    if (!ink || !ink.strokes || !ink.strokes.length || !at || at.by === "gone") return;
    var fig = figure(at.page || ink.page);
    if (!fig) return;
    var W = PAGE_REF, H = W * aspect(fig);
    var svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("class", "lg-ghost " + strength);
    svg.setAttribute("viewBox", "0 0 " + W + " " + H.toFixed(1));
    svg.setAttribute("preserveAspectRatio", "none");
    svg.setAttribute("aria-hidden", "true");
    svg.dataset.id = item.id;
    var g = document.createElementNS(SVG, "g");
    g.setAttribute("transform", "translate(" + ((at.dx || 0) * W).toFixed(1) + " "
                   + ((at.dy || 0) * H).toFixed(1) + ")");
    ink.strokes.forEach(function (s) {
      var p = s.p || [];
      var pts = [];
      for (var i = 0; i + 1 < p.length; i += 2) {
        pts.push((p[i] * W).toFixed(1) + "," + (p[i + 1] * H).toFixed(1));
      }
      if (!pts.length) return;
      var line = document.createElementNS(SVG, "polyline");
      line.setAttribute("points", pts.join(" "));
      line.setAttribute("fill", "none");
      line.setAttribute("stroke", s.c || "#e8746c");
      line.setAttribute("stroke-width", String(s.pg ? (s.w || 2) : (s.w || 2) * W / 800));
      line.setAttribute("stroke-linecap", "round");
      line.setAttribute("stroke-linejoin", "round");
      g.appendChild(line);
    });
    svg.appendChild(g);
    fig.appendChild(svg);
  }

  /* ONE PAIR, SELECTED. From a row or `next`, its place is brought onto the
     glass; from a pip it is already there, and only the panel moves. */
  function select(id, how) {
    var item = find(id);
    if (!item) return null;
    sel = id;
    full = "";
    if (!shown) {
      shown = true;
      panel.hidden = false;
      label();
      place();
    }
    flashing = Date.now();
    var mine = flashing;
    paint();
    setTimeout(function () {
      if (flashing !== mine) return;
      flashing = 0;
      Array.prototype.forEach.call(pages.querySelectorAll(".lg-mark.lg-flash"),
        function (m) { m.classList.remove("lg-flash"); });
    }, FLASH_MS);
    if (how !== "pip") goTo(item);
    /* The row to the top of the panel, inside the panel only: the pages
       have just been put where they should be. */
    var row = body.querySelector('.lg-row[data-id="' + id + '"]');
    if (row) {
      body.scrollTop += row.getBoundingClientRect().top
        - body.getBoundingClientRect().top - 6;
    }
    return item;
  }

  function deselect() {
    sel = "";
    full = "";
    paint();
  }

  /* The pair's place, centred in what the panel leaves of the glass. */
  function goTo(item) {
    if (!item.at || !pages) return;
    if (zoomer && zoomer.zoom && zoomer.zoom() < ZOOM_AT_LEAST) zoomer.set(ZOOM_AT_LEAST);
    var fig = figure(item.at.page);
    if (!fig) return;
    var fr = fig.getBoundingClientRect();
    var pr = pages.getBoundingClientRect();
    var b = item.at.box || [0.1, item.at.y, 0.9, item.at.y + 0.04];
    var cx = fr.left + (b[0] + b[2]) / 2 * fr.width;
    var cy = fr.top + (b[1] + b[3]) / 2 * fr.height;
    var bottom = pr.bottom;
    if (shown && !railed()) {
      var t = panel.getBoundingClientRect().top;
      if (t > pr.top && t < bottom) bottom = t;
    }
    pages.scrollTop += cy - (pr.top + (bottom - pr.top) / 2);
    pages.scrollLeft += cx - (pr.left + pr.width / 2);
    if (opts.scrolled) opts.scrolled();
  }

  /* The next pair, in document order, round again at the end. */
  function next() {
    var r = round();
    var list = rows(r);
    if (!list.length) return null;
    var at = -1;
    list.forEach(function (x, i) { if (x.id === sel) at = i; });
    return select(list[(at + 1) % list.length].id, "next");
  }

  /* ---------------------------------------------------------- the panel */
  function heading(r) {
    var n = r.items.length;
    return "Round " + r.round + (r.done ? " done · " : " · ") + n + (n === 1 ? " note" : " notes");
  }

  function panelPaint() {
    var r = round();
    body.innerHTML = "";
    foot.innerHTML = "";
    foot.hidden = true;
    if (!r) {
      title.textContent = "No rounds yet";
      sub.textContent = "";
      return;
    }
    title.textContent = heading(r);
    sub.textContent = !r.landed ? "waiting for the revision"
      : r.done ? "every note is fine"
      : r.open + " open";
    if (r.broken) {
      body.appendChild(el("p", "lg-note lg-bad", "The revision left its ledger "
        + "unreadable, so nothing in it counts as an answer."));
    }
    if (r.done && !unfold[r.note]) {
      body.appendChild(button("show the " + r.items.length + " notes", "lg-unfold",
        function () { unfold[r.note] = true; panelPaint(); }));
    } else {
      var list = el("ol", "lg-rows");
      rows(r).forEach(function (item) { list.appendChild(row(r, item)); });
      body.appendChild(list);
    }
    var others = (data.rounds || []).map(function (x, i) { return [x, i]; })
      .filter(function (p) { return p[1] !== pick; });
    if (others.length) {
      var box = el("div", "lg-rounds");
      box.appendChild(el("div", "lg-head", "Other rounds"));
      others.forEach(function (p) {
        var x = p[0];
        var b = button(heading(x) + (x.done ? "" : !x.landed ? " · revising"
          : " · " + x.open + " open"), "lg-round" + (x.done ? " lg-done-round" : ""),
          function () {
            pick = p[1];
            sel = "";
            full = "";
            paint();
          });
        b.dataset.note = x.note;
        box.appendChild(b);
      });
      body.appendChild(box);
    }
    var back = 0;
    (data.rounds || []).forEach(function (x) {
      if (!x.landed) return;
      x.items.forEach(function (i) { if (i.state === "reopened" && !i.carried) back++; });
    });
    if (back && opts.send) {
      foot.hidden = false;
      foot.appendChild(button(back + " not fixed — send them", "lg-send", function () {
        opts.send(doc);
      }));
    }
  }

  /* What was asked: the crop of the ink as drawn, or the words typed. */
  function asked_(item) {
    var box = el("div", "lg-ask");
    if (item.crop) {
      var img = el("img", "lg-crop");
      img.loading = "lazy";
      img.src = item.crop;
      img.alt = "what you wrote, note " + item.n;
      box.appendChild(img);
    } else if (item.marked) {
      var pic = el("img", "lg-crop lg-marked");
      pic.loading = "lazy";
      pic.src = item.marked;
      pic.alt = "your marks on page " + item.page;
      box.appendChild(pic);
    }
    if (item.text) box.appendChild(el("blockquote", "lg-quote", item.text));
    if (!item.crop && !item.marked && !item.text) {
      box.appendChild(el("p", "lg-note", item.kind === "ink"
        ? "Ink on page " + item.page + "." : "(nothing kept)"));
    }
    if (item.why) box.appendChild(el("p", "lg-why", "Not fixed last time: " + item.why));
    return box;
  }

  /* What was done: the changed wording, or the reply. */
  function revision(item) {
    var box = el("div", "lg-rev");
    if (!item.answer) {
      box.appendChild(el("p", "lg-note", item.status === "waiting"
        ? "The revision has not come back yet."
        : "Not answered: the revision said nothing about this note."));
      return box;
    }
    if (item.reply) {
      var p = el("p", "lg-reply");
      p.appendChild(el("span", "lg-tag", item.answer.disposition === "pushed back"
        ? "Pushed back" : "Not done"));
      p.appendChild(document.createTextNode(" " + item.reply));
      box.appendChild(p);
    }
    if (item.diff && item.diff.length) {
      var d = el("p", "lg-diff");
      item.diff.forEach(function (op, i) {
        if (i) d.appendChild(document.createTextNode(" "));
        if (op[0] === "-") d.appendChild(el("del", "", op[1]));
        else if (op[0] === "+") d.appendChild(el("ins", "", op[1]));
        else d.appendChild(document.createTextNode(op[1]));
      });
      box.appendChild(d);
    } else if (!item.reply) {
      box.appendChild(el("p", "lg-did", item.answer.did || "(no sentence given)"));
    }
    return box;
  }

  function row(r, item) {
    var li = el("li", "lg-row lg-" + tone(item) + (item.id === sel ? " lg-sel" : "")
      + (item.state === "accepted" ? " lg-fine" : "")
      + (item.state === "reopened" ? " lg-back" : ""));
    li.dataset.id = item.id;
    var hit = button("", "lg-hit", function () {
      if (sel === item.id) deselect();
      else select(item.id, "row");
    });
    hit.setAttribute("aria-expanded", item.id === sel ? "true" : "false");
    hit.appendChild(el("span", "lg-n", String(item.n)));
    var main = el("span", "lg-main");
    main.appendChild(asked_(item));
    main.appendChild(revision(item));
    if (item.gone) {
      main.appendChild(el("p", "lg-gone",
        "The words this was written on are no longer in the document."));
    } else if (item.at && item.at.by === "page") {
      main.appendChild(el("p", "lg-note", "Placed by page only: the new wording "
        + "was not found on page " + item.at.page + "."));
    } else if (!item.at && r.landed) {
      main.appendChild(el("p", "lg-note", "Not on the pages."));
    }
    hit.appendChild(main);
    if (item.state !== "open" || item.carried) {
      hit.appendChild(el("span", "lg-state", item.carried ? "in a later round"
        : item.state === "accepted" ? "fine ✓" : "not fixed"));
    }
    li.appendChild(hit);
    if (item.id === sel) li.appendChild(more(r, item));
    return li;
  }

  /* THE SELECTED ROW, opened: what was done in a sentence, the judgement,
     the full wording on request, and on to the next. */
  function more(r, item) {
    var box = el("div", "lg-more");
    if (item.answer && item.answer.did && !item.reply && item.diff && item.diff.length) {
      box.appendChild(el("p", "lg-did", item.answer.did));
    }
    (item.problems || []).forEach(function (p) {
      box.appendChild(el("p", "lg-note lg-bad", "But " + p + "."));
    });
    if (full === item.id && item.answer) {
      var two = el("div", "lg-two");
      var was = el("div", "lg-was");
      was.appendChild(el("div", "lg-head", item.answer.old_from === "turn"
        ? "Before (as the revision remembered it)" : "Before"));
      was.appendChild(el("pre", "lg-text", item.answer.old || "(nothing found)"));
      var now = el("div", "lg-now");
      now.appendChild(el("div", "lg-head", "Now"));
      now.appendChild(el("pre", "lg-text", item.answer.new || "(no new wording given)"));
      two.appendChild(was);
      two.appendChild(now);
      box.appendChild(two);
    }
    var reason = el("input", "lg-reason");
    reason.type = "text";
    reason.placeholder = "What is still wrong? One line.";
    reason.hidden = true;
    var msg = el("p", "lg-msg");
    msg.hidden = true;
    var acts = el("div", "lg-acts");
    if (item.carried) {
      acts.appendChild(el("span", "lg-note", "It rides the round "
        + item.carried.replace(/\.md$/, "") + " now."));
    } else if (!r.landed) {
      acts.appendChild(el("span", "lg-note", "Judge it once the revision has come back."));
    } else {
      acts.appendChild(button(item.state === "accepted" ? "fine ✓" : "fine",
        "lg-fine-btn" + (item.state === "accepted" ? " on" : ""), function () {
          setState(r, item, "accepted", "", msg);
        }));
      acts.appendChild(button(item.state === "reopened" ? "not fixed ↺" : "not fixed",
        "lg-back-btn" + (item.state === "reopened" ? " on" : ""), function () {
          if (reason.hidden) { reason.hidden = false; reason.focus(); return; }
          var why = reason.value.trim();
          if (why.length < 3) {
            say(msg, "Say in a line what is still wrong.", true);
            reason.focus();
            return;
          }
          setState(r, item, "reopened", why, msg);
        }));
    }
    if (item.answer && (item.answer.old || item.answer.new)) {
      acts.appendChild(button(full === item.id ? "hide wording" : "full wording",
        "lg-full-btn", function () {
          full = full === item.id ? "" : item.id;
          panelPaint();
        }));
    }
    acts.appendChild(button("next ›", "lg-next", function () { next(); }));
    box.appendChild(reason);
    box.appendChild(acts);
    box.appendChild(msg);
    reason.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") {
        var b = acts.querySelector(".lg-back-btn");
        if (b) b.click();
      }
    });
    return box;
  }

  function say(msg, text, bad) {
    msg.hidden = false;
    msg.className = "lg-msg" + (bad ? " lg-bad" : "");
    msg.textContent = text;
  }

  function setState(r, item, state, why, msg) {
    if (!doc || !r) return;
    fetch("/library/ledger/state", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document: doc.id, note: r.note, id: item.id,
                             state: state, why: why })
    }).then(function (res) { return res.json(); }).then(function (got) {
      if (!got || !got.ok) {
        say(msg, ((got && got.error) || "the board refused it") + ".", true);
        return;
      }
      item.state = state;
      item.state_why = why;
      var open_ = 0, judged = 0;
      r.items.forEach(function (x) {
        if (x.state !== "accepted" && !x.carried) open_++;
        if (x.state !== "open") judged++;
      });
      r.open = open_;
      r.judged = judged;
      r.done = r.landed && !open_;
      label();
      paint();
      var m = body.querySelector(".lg-row.lg-sel .lg-msg");
      if (m) {
        say(m, state === "reopened"
          ? "Not fixed. It rides the next round you send, as " + item.id + "."
          : "Fine.");
      }
      refresh();
      if (opts.changed) opts.changed();
    }).catch(function () {
      say(msg, "The board is not answering.", true);
    });
  }

  return { open: open, refresh: refresh, toggle: toggle, next: next, close: close,
           redraw: paint, escape: escape, select: select, bar: null,
           isOn: function () { return shown; },
           showing: function () { return sel; } };
}

/* THE SPLIT, BEFORE IT IS SENT. What the filing panel's words and the page's
   ink would become as requests -- so "that was one request, not three" is a
   tap now rather than a round later. `onMerge(page)` toggles a page's ink
   between one request per region and one request for the page. */
function preview(box, items, merged, onMerge) {
  if (!box) return;
  box.innerHTML = "";
  box.hidden = !items || !items.length;
  if (box.hidden) return;
  box.appendChild(el("div", "lg-head", items.length === 1
    ? "This goes as 1 request:" : "This goes as " + items.length + " requests:"));
  var offered = {};
  items.forEach(function (it) {
    var line = el("div", "lg-pre");
    line.dataset.id = it.id;
    line.appendChild(el("span", "lg-chip lg-waiting", String(it.id || "").replace(/^R/, "")));
    line.appendChild(el("span", "", it.kind === "ink"
      ? "ink on page " + it.page + (it.merged ? " (all of it, as one)" : "")
      : it.kind === "reopened" ? "reopened: " + it.text
      : "“" + it.text.slice(0, 70) + (it.text.length > 70 ? "…" : "") + "”"));
    if (it.kind === "ink" && (it.together > 1 || it.merged) && !offered[it.page]) {
      offered[it.page] = true;
      line.appendChild(button(it.merged ? "split page " + it.page + " again"
                                        : "these " + it.together + " are one request",
                              "quiet lg-merge", function () { onMerge(it.page); }));
    }
    box.appendChild(line);
  });
}

window.Ledger = { make: make, preview: preview };
})();
