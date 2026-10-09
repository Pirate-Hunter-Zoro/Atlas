/* ==========================================================================
   reader.js -- the one reader: every PDF on the glass, and the ink on it.

   ONE READER FOR EVERY PDF VIEW. The library's documents, the meeting deck
   and a document opened from a card on the board are the same thing: page
   pictures drawn by the machine holding the PDF (`course/paper.py` says why
   it is pictures), one `figure.lib-page` per page carrying
   `data-ann="<inkKey>/p<n>"`, the pen out of `annotate.js`, the pinch out of
   `readerzoom.js`, and every save of the ink through `inkkeep.js`. A page
   with `#reader` markup of its own (the library, the meeting deck) has it
   adopted; a page without one (the board) gets it built, the same ids, over
   everything else (`reader-over`).

   ONE KIND OF INK. A stroke stored with a retired kind field loads as
   ordinary ink, in place; nothing here reads it.

   `Reader.mount(opts)` once per page, before the first open, takes:
     keeper       an `InkKeep` already made (the board's, which also keeps the
                  cards' ink); otherwise one is made from `keep`
     keep         `InkKeep.make` options: build, stamp, paint, saved, url
     url(path)    where this page asks for a server path (`libUrl`, the
                  board's session prefix); the burn and a kept copy use it
     committed()  a pinch has landed (`ReaderZoom`'s)
     tools        nodes put on a built bar, before the zoom chip
   and answers the reader: `{els, zoomer, keeper, open, close, redraw,
   pageInView, keepCopy, showCopy, paintKeep, say, keeping, current}`. The
   page owns `Annotate.onChange` (one listener) and the pen button.

   `Reader.open(o)` draws one document and answers its handle. `o`:
     pagesUrl     the pages, as `/library/view`, `/view` and `/meeting/view`
                  answer: {ok, pages, truncated, ink, ink_sent, ...}
     id, title    the document
     inkKey       the anchor's head, `doc/<id>` unless said
     onClose(h)   after the reader has shut
     burn         the kind `/annotate/burn` makes a marked copy of, or none
     place, at    the page to come back to and its offset, for a re-draw
     wait         what the subtitle says while the pages are drawn
     alt          "page" or "slide"
     src(url)     a page picture's URL from the reply's
     caption(n, got), count(got)   a page's caption, the subtitle's count
     page(fig, img, n)            each page box as it is made
     ink(got, h)  puts the reply's ink on the glass (default `Annotate.load`)
     drawing(h, place, at), drawn(got, h), failed(got, h)
     paint()      repaint the page's own bar after a keep
   ========================================================================== */
(function () {
"use strict";

var A = function () { return window.Annotate; };

var IDS = ["reader", "reader-bar", "reader-name", "reader-sub", "reader-pen",
           "reader-kept", "reader-keep", "reader-zoom", "reader-close",
           "reader-copy", "reader-copy-said", "reader-copy-save", "reader-pages"];

function key(id) {
  if (id === "reader") return "root";
  return id.slice("reader-".length).replace(/-(\w)/g, function (_, c) {
    return c.toUpperCase();
  });
}

/* THE MARKUP, for a page that has none. The same ids the library's and the
   meeting deck's own markup carry, so one sheet (`reader.css`) and one set of
   tests read all three. */
function build() {
  var root = document.createElement("div");
  root.id = "reader";
  root.className = "reader-over";
  root.hidden = true;
  root.innerHTML =
    '<div id="reader-bar">'
    + '<strong id="reader-name"></strong>'
    + '<span id="reader-sub" class="muted"></span>'
    + '<button id="reader-pen" type="button" aria-pressed="false"'
    + ' title="write on this page">✎ mark it up</button>'
    + '<span id="reader-kept" class="reader-kept" role="status"'
    + ' aria-live="polite" hidden></span>'
    + '<button id="reader-keep" type="button" disabled'
    + ' title="burn your marks into a new copy of this document; the original'
    + ' is not touched">⤓ keep a marked copy</button>'
    + '<button id="reader-zoom" type="button" title="back to the page width"'
    + ' hidden>100%</button>'
    + '<button id="reader-close" type="button" title="close">✕</button>'
    + '</div>'
    + '<p id="reader-copy" class="reader-copy" hidden>'
    + '<span id="reader-copy-said"></span>'
    + '<button id="reader-copy-save" type="button" hidden>save a copy</button>'
    + '</p>'
    + '<div id="reader-pages"></div>';
  document.body.appendChild(root);
  return root;
}

var R = null;

function mount(opts) {
  if (R) return R;
  opts = opts || {};
  var built = !document.getElementById("reader");
  if (built) build();
  var els = {};
  IDS.forEach(function (id) { els[key(id)] = document.getElementById(id); });
  if (built) {
    (opts.tools || []).forEach(function (n) {
      els.bar.insertBefore(n, els.zoom || null);
    });
  }
  R = {
    els: els, built: built, current: null,
    url: opts.url || function (p) { return p; },
    open: open, close: close, redraw: redraw, pageInView: pageInView,
    keepCopy: keepCopy, showCopy: showCopy, paintKeep: paintKeep, say: say,
    keeping: function () { return keeping; },
  };
  R.zoomer = window.ReaderZoom && els.pages ? window.ReaderZoom.make({
    scroller: els.pages, surface: els.root, bar: els.bar, chip: els.zoom,
    page: ".lib-page",
    open: function () { return !!R.current; },
    committed: opts.committed,
  }) : null;
  R.keeper = opts.keeper || (window.InkKeep && A()
    ? window.InkKeep.make(opts.keep || {}) : null);
  if (els.close) els.close.onclick = function () { close(); };
  if (els.keep) els.keep.onclick = function () { keepCopy(); };
  if (els.copySave) els.copySave.onclick = saveTap;
  return R;
}

/* ------------------------------------------------------------ one document */
function open(o) {
  var r = mount();
  o = o || {};
  var was = r.current;
  var h = {
    id: String(o.id || ""), title: o.title || o.id || "",
    inkKey: o.inkKey || ("doc/" + o.id), opts: o,
    got: null, pages: 0, asks: 0, shut: false,
  };
  r.current = h;
  if (!was || was.id !== h.id) showCopy(null);
  r.els.root.hidden = false;
  /* THE PAGE BEHIND THE READER DOES NOT SCROLL. A finger on the bar would
     otherwise pan what is under it, and a pan already under way makes the
     second finger of a pinch one the page can no longer refuse. */
  document.body.classList.add("reading");
  if (r.zoomer) { r.zoomer.live(true); r.zoomer.set(1); }
  r.els.pages.scrollTop = 0;
  draw(h, o.place || 0, o.at || 0);
  return h;
}

/* THE SAME DOCUMENT AGAIN, its bytes having moved: the zoom stays, and the
   page somebody was on is put back by the caller's `page` and `drawn`. */
function redraw(place, at) {
  if (!R || !R.current) return;
  draw(R.current, place || 0, at || 0);
}

function draw(h, place, at) {
  var o = h.opts;
  var els = R.els;
  var ask = ++h.asks;
  els.name.textContent = h.title;
  els.sub.textContent = o.wait || (place ? "re-drawing the pages…"
                                         : "drawing the pages…");
  els.pages.innerHTML = "";
  if (!place) els.pages.scrollTop = 0;
  if (o.drawing) o.drawing(h, place, at);
  fetch(o.pagesUrl, { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (got) {
      if (R.current !== h || h.asks !== ask) return;   /* closed, or another */
      if (!got || !got.ok) {
        els.sub.textContent = (got && got.detail) || "The pages could not be drawn.";
        if (o.failed) o.failed(got || {}, h);
        return;
      }
      h.got = got;
      h.pages = (got.pages || []).length;
      els.sub.textContent = o.count ? o.count(got)
        : h.pages + (h.pages === 1 ? " page" : " pages")
          + (got.truncated ? " (the first of a longer document)" : "");
      els.pages.innerHTML = "";
      (got.pages || []).forEach(function (url, i) {
        var n = i + 1;
        var fig = document.createElement("figure");
        fig.className = "lib-page";
        fig.setAttribute("data-page", String(n));
        /* THE ANCHOR, and it is the tail of a §2.1 address. Ink is stored in
           fractions of this box rather than in page pixels, so it is in the
           same place on the page after a rotation or a zoom. A page, so its
           ink zooms with it (`annotate.js`, `PAGE_REF`); the box is the
           picture alone, the caption hangs below it (`reader.css`). */
        fig.dataset.ann = h.inkKey + "/p" + n;
        fig.setAttribute("data-ann-page", "");
        var img = document.createElement("img");
        img.src = o.src ? o.src(url) : url;
        img.alt = (o.alt || "page") + " " + n;
        /* Lazily past the second: a hundred-page transcript is a hundred
           pictures, and the person is reading page one. */
        img.setAttribute("loading", i < 2 ? "eager" : "lazy");
        fig.appendChild(img);
        var cap = document.createElement("figcaption");
        cap.textContent = o.caption ? o.caption(n, got) : String(n);
        fig.appendChild(cap);
        els.pages.appendChild(fig);
        if (o.page) o.page(fig, img, n);
        if (A()) {
          A().attach(fig);
          /* A picture has no height until it has decoded, and a layer sized
             against a zero-height box covers nothing. */
          img.addEventListener("load", function () { A().redrawAll(); });
        }
      });
      /* The marks made on it before, put back with the pages: a reader holds
         no other payload to read them out of. */
      if (o.ink) o.ink(got, h);
      else if (A()) {
        A().load(got.ink || {});
        if (got.ink_sent) A().loadSent(got.ink_sent);
      }
      paintKeep();
      if (o.drawn) o.drawn(got, h);
    })
    .catch(function () {
      if (R.current !== h || h.asks !== ask) return;
      els.sub.textContent = "The board is not answering.";
      if (o.failed) o.failed({ detail: "the board did not answer" }, h);
    });
}

/* Shut. Whatever is owed goes first: a page closed with ink that never
   reached disk is ink somebody drew and the board silently dropped. */
function close() {
  if (!R || !R.current) return;
  var h = R.current;
  if (R.keeper) R.keeper.save();
  R.current = null;
  h.shut = true;
  R.els.root.hidden = true;
  document.body.classList.remove("reading");
  if (R.zoomer) R.zoomer.live(false);
  showCopy(null);
  /* The pictures go with it. A hundred decoded pages held behind a closed
     reader is memory the page wants for everything else. */
  R.els.pages.innerHTML = "";
  if (h.opts.onClose) h.opts.onClose(h);
}

/* A SENTENCE IN THE PAGES' PLACE, for a document that could not be drawn:
   `html` is the page's own (escaped by it), and the box is answered so the
   page can put what can still be done under it. */
function say(html) {
  if (!R) return null;
  R.els.pages.innerHTML = '<div class="reader-say">' + html + "</div>";
  return R.els.pages.querySelector(".reader-say");
}

/* WHICH PAGE IS BEING READ: the last whose top edge has passed the top of the
   window, against the SCROLLER'S OWN rectangle rather than `offsetTop`, which
   is measured from whichever ancestor happens to be positioned. */
function pageInView() {
  if (!R) return 0;
  var pages = R.els.pages.querySelectorAll(".lib-page");
  if (!pages.length) return 0;
  var top = R.els.pages.getBoundingClientRect().top + 80;
  var best = 1;
  for (var i = 0; i < pages.length; i++) {
    if (pages[i].getBoundingClientRect().top <= top) best = i + 1;
  }
  return best;
}

/* ------------------------------------------------ ⤓ keep a marked copy */
/* THE INK, BURNED INTO A NEW PDF, never over the original: `POST
   /annotate/burn` with the document's `burn` kind and `new`. Keeping a copy is
   not sending: the ink stays on the page. Where the reply names a `url`, the
   copy is fetched at once and handed over by the share sheet on the tap. */
var keeping = false;
var keptCopy = null;                 /* { id, name, url, got } */

function marked(h) {
  if (!A() || !h) return 0;
  var head = h.inkKey + "/";
  return A().marked().filter(function (id) { return id.indexOf(head) === 0; }).length;
}

/* The keep button: there only for a document that can be burned, live only
   with ink on it and no keep already under way. */
function paintKeep() {
  if (!R || !R.els.keep) return;
  var h = R.current;
  R.els.keep.hidden = !h || !h.opts.burn;
  R.els.keep.disabled = keeping || !marked(h);
}

function keepCopy() {
  var h = R && R.current;
  if (!h || !h.opts.burn || keeping) return Promise.resolve(null);
  keeping = true;
  var btn = R.els.keep;
  var was = btn ? btn.textContent : "";
  if (btn) { btn.textContent = "keeping…"; btn.disabled = true; }
  if (h.opts.paint) h.opts.paint();
  /* What is on the glass goes to disk first: the copy is burned from disk. */
  var settle = R.keeper ? R.keeper.settle() : Promise.resolve(null);
  return settle.then(function () {
    if (R.keeper && R.keeper.failed() && R.keeper.owed()) {
      throw new Error("The ink is not saved yet, so a copy would be missing "
                      + "some of it. It is retrying; keep the copy once it says saved.");
    }
    return fetch(R.url("/annotate/burn"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ kind: h.opts.burn, mode: "new" })
    });
  }).then(function (r) {
    return r.json().catch(function () { return {}; });
  }).then(function (got) {
    if (!got || !got.ok) throw new Error((got && got.detail) || "The board refused it.");
    keptCopy = got.url ? { id: h.id, name: got.name, url: got.url, got: null } : null;
    showCopy(got.detail || ("Kept as " + got.name + "."));
    if (keptCopy) warmCopy(keptCopy);
    return got;
  }).catch(function (err) {
    showCopy((err && err.message) || "The board is not answering.", true);
    return null;
  }).then(function (got) {
    keeping = false;
    if (btn) btn.textContent = was;
    paintKeep();
    if (h.opts.paint) h.opts.paint();
    return got;
  });
}

/* Fetched as soon as it exists, so the tap on *save a copy* can share it in the
   same gesture -- the only moment Safari allows the share sheet. */
function warmCopy(copy) {
  fetch(R.url(copy.url), { credentials: "same-origin" }).then(function (res) {
    if (res.ok === false) throw new Error("the board would not give it up");
    return res.blob();
  }).then(function (blob) {
    var file = null;
    try { file = new File([blob], copy.name, { type: "application/pdf" }); }
    catch (e) { file = null; }
    copy.got = { blob: blob, name: copy.name, file: file, url: R.url(copy.url) };
  }).catch(function () { /* the tap fetches it again and says so */ });
}

function showCopy(text, bad) {
  if (!R || !R.els.copy) return;
  if (!text) { R.els.copy.hidden = true; keptCopy = null; return; }
  R.els.copy.hidden = false;
  R.els.copy.className = "reader-copy" + (bad ? " bad" : "");
  R.els.copySaid.textContent = text;
  R.els.copySave.hidden = !!bad || !keptCopy;
  R.els.copySave.textContent = "save a copy";
  R.els.copySave.disabled = false;
}

function standalone() {
  if (navigator.standalone === true) return true;
  try {
    return !!(window.matchMedia && window.matchMedia("(display-mode: standalone)").matches);
  } catch (e) { return false; }
}

/* The share sheet first; a blob download where there is none; and in the
   installed app, which ignores `download`, a new context -- never a navigation
   of this one. */
function handOver(got, btn) {
  var done = function (label) { if (btn) btn.textContent = label || "save a copy"; };
  if (got.file && navigator.share && navigator.canShare
      && navigator.canShare({ files: [got.file] })) {
    try {
      var p = navigator.share({ files: [got.file], title: got.name });
      if (p && p.then) {
        p.then(function () { done("saved"); }, function (err) {
          if (err && err.name === "AbortError") { done(); return; }
          saveBlob(got, done);
        });
        return;
      }
    } catch (e) { /* refused outright; save instead */ }
  }
  saveBlob(got, done);
}

function saveBlob(got, done) {
  var a = document.createElement("a");
  if (standalone() || !("download" in a) || !got.blob) {
    window.open(got.url, "_blank", "noopener");
    done();
    return;
  }
  var href = URL.createObjectURL(got.blob);
  a.href = href;
  a.download = got.name;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(function () { URL.revokeObjectURL(href); }, 60000);
  done("saved");
}

function saveTap(e) {
  var copy = keptCopy;
  var btn = e.currentTarget;
  if (!copy) return;
  if (copy.got) { handOver(copy.got, btn); return; }
  btn.disabled = true;
  btn.textContent = "getting it…";
  warmCopy(copy);
  /* No gesture left by the time it arrives, so this is the download route. */
  setTimeout(function wait(n) {
    n = n || 0;
    if (copy.got || n > 40) {
      btn.disabled = false;
      if (copy.got) handOver(copy.got, btn);
      else btn.textContent = "could not get it";
      return;
    }
    setTimeout(function () { wait(n + 1); }, 150);
  }, 150);
}

window.Reader = {
  mount: mount,
  open: function (o) { return mount().open(o); },
  close: close,
  current: function () { return R ? R.current : null; },
  els: function () { return R ? R.els : null; },
};
})();
