/* ==========================================================================
   ledger.js -- what each request was, and what was done about it, as PINS.

   The owner's words: "I need some nifty way to keep track of what each edit
   request was, and what was done to address it, so that I don't have to read
   the whole fucking paper again." So after a round lands the reader has a
   CHANGES mode: a numbered pin in the margin at every changed spot, coloured
   by what was done, with the changed passage lightly boxed. A tap on a pin is
   a card -- the ink or the words the request was, what was done, and the old
   and new wording side by side -- and the card is where a request is ACCEPTED
   or REOPENED with a line of why. A list orders the same requests by page, and
   `next change ›` steps through them.

   The server does the work (`course/ledger.py`): it split the round into
   requests when it was filed, validated the turn's answers, and placed each
   one on the build that is on disk now. This draws what `GET /library/ledger/
   <id>` says, onto the reader's own `.lib-page` boxes, in fractions of the
   page -- the frame the ink is in, so a pin follows the zoom the way ink does.

   One module for both readers that load it. The meeting deck loads it and asks
   nothing of it: its direction route changes nothing, so it has no ledger.

     Ledger.make({ pages, button, changed }) -> { open(doc, on), refresh(),
                                                  toggle(), next(), close() }
     Ledger.preview(el, items, merged, onMerge)   the filing panel's split
   ========================================================================== */

(function () {
"use strict";

var WORDS = { "done": "done", "partly": "partly done", "not done": "not done",
              "pushed back": "pushed back" };

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

/* Which colour a request is: what was done, or that nothing was said. */
function tone(item) {
  if (item.answer) return item.answer.disposition.replace(/ /g, "-");
  return item.status === "waiting" ? "waiting" : "none";
}

function said(item) {
  if (item.answer) return WORDS[item.answer.disposition] || item.answer.disposition;
  return item.status === "waiting" ? "waiting for the revision" : "not answered";
}

function short(id) { return String(id || "").replace(/^R/, ""); }

function where(item) {
  var p = item.placed;
  if (!p || !p.page) return item.page ? "was on page " + item.page : "";
  return "page " + p.page + (p.by === "page" ? " (placed by page only)"
    : p.by === "anchor" ? " (where it was restructured)" : "");
}

function make(opts) {
  var pages = opts.pages;
  var btn = opts.button || null;
  var doc = null;
  var data = null;
  var pick = 0;               /* which round: 0 is the newest */
  var on = false;
  var at = -1;                /* where `next change ›` is */
  var asked = 0;

  /* THE BAR, the LIST and the CARD are this module's own, built once. */
  var bar = el("p", "reader-said lg-bar");
  bar.id = "lg-bar";
  bar.hidden = true;
  var sum = el("span", "lg-sum");
  var pickRound = el("select", "lg-round");
  pickRound.title = "which round";
  pickRound.addEventListener("change", function () {
    pick = +pickRound.value || 0;
    at = -1;
    paint();
  });
  var listBtn = button("☰ every request", "lg-list-btn", function () { showList(); });
  var nextBtn = button("next change ›", "lg-next", function () { next(); });
  bar.appendChild(sum);
  bar.appendChild(pickRound);
  bar.appendChild(listBtn);
  bar.appendChild(nextBtn);
  if (pages && pages.parentNode) pages.parentNode.insertBefore(bar, pages);

  var list = el("div", "lg-over");
  list.id = "lg-list";
  list.hidden = true;
  var listBox = el("div", "lg-box-panel");
  list.appendChild(listBox);
  document.body.appendChild(list);

  /* THE CARD IS A SHEET AT THE FOOT OF THE GLASS, not a veil over it: a jump
     to a change must leave the change in sight, and the sheet steps on to the
     next one itself. Only the panel takes a touch; the pages above it scroll. */
  var card = el("div", "lg-over lg-sheet");
  card.id = "lg-card";
  card.hidden = true;
  var cardBox = el("div", "lg-box-panel");
  card.appendChild(cardBox);
  document.body.appendChild(card);
  [list].forEach(function (o) {
    o.addEventListener("click", function (ev) { if (ev.target === o) o.hidden = true; });
  });

  if (btn) btn.addEventListener("click", function () { toggle(); });
  if (btn) btn.hidden = true;

  function round() { return (data && data.rounds && data.rounds[pick]) || null; }

  function has(d) { return !!(d && d.ledger && d.ledger.rounds); }

  /* A document opened, or -- the same document with `want` unsaid -- its
     record come back from a reload of the list, which keeps the mode. */
  function open(d, want) {
    if (doc && d && doc.id === d.id && want === undefined) {
      doc = d;
      label();
      if (has(d)) refresh();
      return;
    }
    doc = d;
    data = null;
    pick = 0;
    at = -1;
    on = !!want;
    label();
    paint();
    if (has(d)) refresh();
  }

  function label() {
    if (!btn) return;
    btn.hidden = !has(doc);
    btn.classList.toggle("on", on);
    btn.textContent = "◉ changes" + (has(doc) && doc.ledger.open
      ? " · " + doc.ledger.open + " open" : "");
  }

  /* Escape closes the card or the list, and says whether it did. */
  function escape() {
    if (!card.hidden) { card.hidden = true; return true; }
    if (!list.hidden) { list.hidden = true; return true; }
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
        data = got && got.ok ? got : null;
        if (pick >= ((data && data.rounds) || []).length) pick = 0;
        paint();
      })
      .catch(function () { /* the pins are extra; the pages are still there */ });
  }

  function toggle() {
    on = !on;
    label();
    at = -1;
    paint();
  }

  function close() {
    doc = null;
    data = null;
    on = false;
    card.hidden = true;
    list.hidden = true;
    if (btn) { btn.hidden = true; btn.classList.remove("on"); }
    paint();
  }

  /* The requests with a pin, in the order a reader meets them: by page, then
     down the page. */
  function pinned() {
    var r = round();
    if (!r) return [];
    return r.items.filter(function (i) { return i.placed && i.placed.page >= 1; })
      .sort(function (a, b) {
        return (a.placed.page - b.placed.page)
          || (((a.placed.box || [0, 0])[1]) - ((b.placed.box || [0, 0])[1]));
      });
  }

  function paint() {
    if (!pages) return;
    Array.prototype.forEach.call(pages.querySelectorAll(".lg-pin, .lg-mark"),
      function (n) { n.parentNode.removeChild(n); });
    var r = round();
    bar.hidden = !on || !r;
    if (!on || !r) return;
    var counts = {};
    r.items.forEach(function (i) { var t = said(i); counts[t] = (counts[t] || 0) + 1; });
    sum.textContent = "Round " + r.round + ": " + r.items.length
      + (r.items.length === 1 ? " request" : " requests") + " — "
      + Object.keys(counts).map(function (k) { return counts[k] + " " + k; }).join(", ")
      + (r.landed ? "." : ". The revision has not come back yet.")
      + (r.broken ? " The revision left its ledger unreadable, so nothing in it "
         + "counts as an answer." : "");
    pickRound.innerHTML = "";
    (data.rounds || []).forEach(function (x, n) {
      var o = el("option", "", "round " + x.round + " · " + x.note.replace(/\.md$/, ""));
      o.value = String(n);
      if (n === pick) o.selected = true;
      pickRound.appendChild(o);
    });
    pickRound.hidden = (data.rounds || []).length < 2;
    var order = pinned();
    nextBtn.disabled = !order.length;
    order.forEach(function (item) {
      var fig = pages.querySelector('.lib-page[data-page="' + item.placed.page + '"]');
      if (!fig) return;
      var box = item.placed.box;
      var top = box ? box[1] : 0.01;
      var pin = button(short(item.id), "lg-pin lg-" + tone(item), function (ev) {
        ev.stopPropagation();
        at = order.indexOf(item);
        show(item);
      });
      pin.dataset.id = item.id;
      pin.title = item.id + " — " + said(item);
      pin.style.top = (top * 100).toFixed(2) + "%";
      fig.appendChild(pin);
      if (box) {
        var m = el("div", "lg-mark lg-" + tone(item));
        m.dataset.id = item.id;
        m.style.left = (box[0] * 100).toFixed(2) + "%";
        m.style.top = (box[1] * 100).toFixed(2) + "%";
        m.style.width = ((box[2] - box[0]) * 100).toFixed(2) + "%";
        m.style.height = ((box[3] - box[1]) * 100).toFixed(2) + "%";
        fig.appendChild(m);
      }
    });
  }

  /* The next pin, by page, brought onto the glass and opened. */
  function next() {
    var order = pinned();
    if (!order.length) return null;
    at = (at + 1) % order.length;
    var item = order[at];
    goTo(item);
    show(item);
    return item;
  }

  function goTo(item) {
    if (!item.placed || !item.placed.page) return;
    var pin = pages.querySelector('.lg-pin[data-id="' + item.id + '"]');
    var target = pin || pages.querySelector(
      '.lib-page[data-page="' + item.placed.page + '"]');
    if (!target) return;
    pages.scrollTop += target.getBoundingClientRect().top
      - pages.getBoundingClientRect().top - 80;
  }

  function section(title) {
    var s = el("div", "lg-sec");
    s.appendChild(el("div", "lg-head", title));
    return s;
  }

  /* ONE REQUEST: what it was, what was done, old beside new, and the tap that
     closes it or sends it back. */
  function show(item) {
    var r = round();
    cardBox.innerHTML = "";
    var top = el("div", "lg-top");
    top.appendChild(el("strong", "lg-id", item.id));
    top.appendChild(el("span", "lg-chip lg-" + tone(item), said(item)));
    var w = where(item);
    if (w) top.appendChild(el("span", "muted lg-where", w));
    cardBox.appendChild(top);

    var req = section(item.kind === "reopened" ? "What was asked, reopened"
                                               : "What you asked");
    if (item.crop) {
      var img = el("img", "lg-crop");
      img.src = item.crop;
      img.alt = "your ink for " + item.id;
      req.appendChild(img);
    }
    if (!item.crop && item.marked) {
      /* No region to cut (ink the parser could not read): the whole marked
         page the round kept, which is still the complaint, located. */
      var pic = el("img", "lg-crop lg-marked");
      pic.src = item.marked;
      pic.alt = "your marks on page " + item.page + " for " + item.id;
      req.appendChild(pic);
    }
    if (item.text) req.appendChild(el("p", "lg-words", item.text));
    if (!item.crop && !item.marked && !item.text) {
      req.appendChild(el("p", "muted", item.kind === "ink"
        ? "Ink on page " + item.page + "." : "(nothing kept)"));
    }
    if (item.why) req.appendChild(el("p", "lg-why", "Reopened because: " + item.why));
    if (item.previous) req.appendChild(el("p", "muted", "Last time: " + item.previous));
    cardBox.appendChild(req);

    var did = section("What was done");
    if (item.answer) {
      did.appendChild(el("p", "lg-did", item.answer.did || "(no sentence given)"));
    } else {
      did.appendChild(el("p", "lg-did muted", item.status === "waiting"
        ? "The revision has not come back yet."
        : "Not answered: the revision said nothing about this request."));
    }
    (item.problems || []).forEach(function (p) {
      did.appendChild(el("p", "lg-problem", "But " + p + "."));
    });
    if (item.placed && item.placed.by === "page") {
      did.appendChild(el("p", "muted", "Placed by page only: the new wording was "
        + "not found on the pages, so the pin is at the top of the page."));
    }
    cardBox.appendChild(did);

    if (item.answer && (item.answer.old || item.answer.new)) {
      var two = el("div", "lg-two");
      var was = el("div", "lg-was");
      was.appendChild(el("div", "lg-head", item.answer.old_from === "turn"
        ? "Before (as the revision remembered it)" : "Before"));
      was.appendChild(el("pre", "lg-text", item.answer.old || "(nothing changed in "
        + "the source)"));
      var now = el("div", "lg-now");
      now.appendChild(el("div", "lg-head", "Now"));
      now.appendChild(el("pre", "lg-text", item.answer.new || "(no new wording given)"));
      two.appendChild(was);
      two.appendChild(now);
      cardBox.appendChild(two);
    }

    var acts = el("div", "lg-acts");
    var reason = el("input", "lg-reason");
    reason.type = "text";
    reason.placeholder = "Why is it not done yet? One line.";
    reason.hidden = item.state !== "reopened";
    reason.value = item.state === "reopened" ? (item.state_why || "") : "";
    var msg = el("p", "note-said lg-msg");
    msg.hidden = true;
    if (item.carried) {
      acts.appendChild(el("span", "muted", "Reopened: it rides the round "
        + item.carried.replace(/\.md$/, "") + " now."));
    } else if (!r || !r.landed) {
      /* NOTHING TO CLOSE YET. A request the revision is still working on is
         neither done nor undone. */
      acts.appendChild(el("span", "muted lg-wait",
        "Accept or reopen it once the revision has come back."));
    } else {
      var accept = button(item.state === "accepted" ? "✓ accepted" : "accept",
                          "lg-accept" + (item.state === "accepted" ? " on" : ""),
                          function () { setState(r, item, "accepted", "", msg); });
      var reopen = button(item.state === "reopened" ? "↺ reopened" : "reopen",
                          "lg-reopen" + (item.state === "reopened" ? " on" : ""),
                          function () {
        if (reason.hidden) { reason.hidden = false; reason.focus(); return; }
        setState(r, item, "reopened", reason.value, msg);
      });
      acts.appendChild(accept);
      acts.appendChild(reopen);
    }
    if (pinned().length) {
      acts.appendChild(button("next change ›", "lg-card-next", function () { next(); }));
    }
    acts.appendChild(button("close", "quiet lg-close", function () { card.hidden = true; }));
    cardBox.appendChild(reason);
    cardBox.appendChild(msg);
    cardBox.appendChild(acts);
    list.hidden = true;
    card.hidden = false;
    card.dataset.id = item.id;
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
        msg.hidden = false;
        msg.className = "note-said bad lg-msg";
        msg.textContent = ((got && got.error) || "the board refused it") + ".";
        return;
      }
      item.state = state;
      item.state_why = why;
      /* The card is drawn again, so its buttons say what is true now. */
      if (!card.hidden && card.dataset.id === item.id) show(item);
      msg = cardBox.querySelector(".lg-msg") || msg;
      msg.hidden = false;
      msg.className = "note-said lg-msg";
      msg.textContent = state === "reopened"
        ? "Reopened. It rides the next round you send, as " + item.id + "."
        : "Accepted.";
      refresh();
      if (opts.changed) opts.changed();
    }).catch(function () {
      msg.hidden = false;
      msg.className = "note-said bad lg-msg";
      msg.textContent = "The board is not answering.";
    });
  }

  /* EVERY REQUEST OF THE ROUND, BY PAGE. The ones with no page -- typed about
     the document as a whole, and not found on the pages -- come last. */
  function showList() {
    var r = round();
    if (!r) return;
    listBox.innerHTML = "";
    listBox.appendChild(el("strong", "", "Round " + r.round + ", by page"));
    var rows = r.items.slice().sort(function (a, b) {
      var pa = (a.placed && a.placed.page) || 1e6;
      var pb = (b.placed && b.placed.page) || 1e6;
      return pa - pb || String(a.id).localeCompare(String(b.id));
    });
    rows.forEach(function (item) {
      var b = button("", "lg-row", function () {
        goTo(item);
        at = pinned().indexOf(item);
        show(item);
      });
      b.dataset.id = item.id;
      b.appendChild(el("span", "lg-chip lg-" + tone(item), short(item.id)));
      b.appendChild(el("span", "lg-row-what", (item.text || (item.kind === "ink"
        ? "ink on page " + item.page : item.kind)).slice(0, 90)));
      b.appendChild(el("span", "muted lg-row-where",
        (where(item) || "no page") + " · " + said(item)
        + (item.state !== "open" ? " · " + item.state : "")));
      listBox.appendChild(b);
    });
    (r.extra || []).forEach(function (x) {
      listBox.appendChild(el("p", "muted lg-extra", "The factory's own change: "
        + x.issue));
    });
    listBox.appendChild(button("close", "quiet lg-close", function () { list.hidden = true; }));
    list.hidden = false;
  }

  return { open: open, refresh: refresh, toggle: toggle, next: next, close: close,
           redraw: paint, escape: escape, bar: bar, isOn: function () { return on; },
           showing: function () { return card.hidden ? "" : card.dataset.id; } };
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
    line.appendChild(el("span", "lg-chip lg-waiting", short(it.id)));
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
