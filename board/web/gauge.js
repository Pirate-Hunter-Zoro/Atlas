/* ==========================================================================
   gauge.js -- how wide a string actually is, and how to wrap it to a box.

   There are two planes that draw text into boxes now: the board's MAP, which
   is a picture of one workspace, and the ATLAS, which is a picture of all of
   them. Both have to answer the same question before they can lay out a single
   box, and it is a question that has already been got wrong once, expensively:

       THE FIRST MAP ESTIMATED LABEL WIDTHS FROM CHARACTER COUNTS.

   That estimate is about right for lower-case prose and badly wrong for the
   SHOUTED headings these plans are written in -- a line of capitals is half
   again wider than the estimate -- so the words ran out of their boxes, and the
   verdict was "that visual is shit", which it was.

   A 2D canvas context measures the real font. The answers are cached, because a
   payload re-measures the same forty labels on every repaint. Where there is no
   canvas at all -- an old browser, a stubbed DOM -- the estimate comes back as
   the fallback, and a fallback that wraps EARLY is a box with room to spare
   rather than one that overflows.

   This file exists so there is one copy of that. Two surfaces measuring text
   two slightly different ways is two spellings of one answer, which is two
   bugs, and the one that would show up first is the one nobody notices: a box
   that is right on the map and a card that is wrong on the atlas.

   Loaded before board.js and before home.js.
   ========================================================================== */

(function () {
"use strict";

var face = null, ctx = null, widths = null;
var faceSaid = null;             /* body[data-face] when `face` was read */
var tracking = 0;                /* --prose-tracking, in em */
var watchers = [];               /* surfaces to tell when the answers change */
var faceReady = false;           /* has the real face actually arrived yet */

/* The face the board actually ships, off the page's own `--ui` token rather
   than guessed: the fallback stack and the real one do not measure the same.

   READ AGAIN WHENEVER THE READING FACE CHANGES. The "Aa" button swaps `--ui` by
   setting `body[data-face]`, and a family read once and kept for the life of
   the page measured every label in the face it was switched away from -- so
   going from Serif to OpenDyslexic wrapped the map for a narrow face and
   painted it in a wide one. The letter-spacing the face carries is read with
   it: SVG text inherits it and a canvas does not measure it. */
function uiFace() {
  var now = null;
  try { now = (document.body && document.body.dataset.face) || ""; }
  catch (e) { now = ""; }
  if (face && now === faceSaid) return face;
  if (face) widths = null;
  faceSaid = now;
  face = "system-ui, -apple-system, 'Segoe UI', sans-serif";
  tracking = 0;
  try {
    var css = window.getComputedStyle(document.body);
    var said = css.getPropertyValue("--ui");
    if (said && said.trim()) face = said.trim();
    var em = /^\s*(-?[\d.]+)em\s*$/.exec(css.getPropertyValue("--prose-tracking") || "");
    if (em) tracking = parseFloat(em[1]) || 0;
  } catch (e) { /* the default stack is a fair guess */ }
  return face;
}

function font(size, weight) {
  return (weight || 400) + " " + size + "px " + uiFace();
}

/* THE ANSWER IS WRONG UNTIL THE FACE HAS LOADED, AND NOTHING SAID SO.

   `measureText` measures the font the canvas can resolve AT THAT MOMENT. The
   board's reading face is OpenDyslexic, a web font served from this repository
   and declared `font-display: swap` -- so for the first fraction of a second
   after a cold load the family does not exist yet, the canvas quietly falls back
   to the next name in the stack, and it answers in system-ui. That is a much
   narrower face: the wrap is computed against it, the boxes are laid out to fit
   it, and then the labels are PAINTED in OpenDyslexic and run straight out of
   their boxes. The measuring was put here to end exactly that defect and it had
   half of it left -- the half that only shows on the first paint after a load,
   which is the paint everybody sees.

   Worse, every answer is cached for the life of the page, so the wrong numbers
   outlived the moment that produced them.

   So: when the fonts settle, throw the cache away and tell whoever is drawing.
   A plane redraws from its own data, which is cheap and already happens on every
   payload. Where there is no `document.fonts` at all the cache simply stands, as
   it did before, and the estimate remains the fallback. */
function faceLoaded() {
  if (faceReady) return;
  faceReady = true;
  widths = null;
  var list = watchers.slice();
  for (var i = 0; i < list.length; i++) {
    try { list[i](); } catch (e) { /* one surface must not stop another */ }
  }
}

function watchFace() {
  var fonts = null;
  try { fonts = document.fonts; } catch (e) { fonts = null; }
  if (!fonts || !fonts.ready || !fonts.ready.then) { faceReady = true; return; }
  try {
    fonts.ready.then(faceLoaded, faceLoaded);
  } catch (e) { faceReady = true; return; }
  /* A face can also arrive later than `ready` settles -- it is loaded when it is
     first USED, and a box drawn in a weight nothing else on the page uses is
     exactly that case. */
  try {
    fonts.addEventListener("loadingdone", function () {
      faceReady = false;
      faceLoaded();
    });
  } catch (e) { /* older browsers: `ready` is all there is */ }
}

/* THE READING FACE WAS SWITCHED. Said by `typeface.js` the moment it sets the
   new face, so the surfaces redraw at once -- a face already loaded fires no
   `loadingdone`, and without this nothing redrew at all. A face that still has
   to load redraws again when it arrives. */
function faceChanged() {
  face = null;
  widths = null;
  faceReady = false;
  faceLoaded();
}

/* Told when the measurements change under it. A surface registers once and
   redraws from its own data; there is no payload involved and nothing to fetch. */
function onFace(fn) {
  if (typeof fn !== "function") return;
  watchers.push(fn);
  if (!watchers.wired) { watchers.wired = true; watchFace(); }
}

function width(text, size, weight) {
  var f = font(size, weight);
  if (!widths) widths = Object.create(null);
  var key = f + " " + text;
  var got = widths[key];
  if (got !== undefined) return got;
  var w = 0;
  try {
    if (ctx === null) {
      var c = document.createElement("canvas");
      ctx = (c && c.getContext) ? c.getContext("2d") : false;
    }
    if (ctx) {
      ctx.font = f;
      var m = ctx.measureText(text);
      w = (m && typeof m.width === "number") ? m.width : 0;
    }
  } catch (e) { w = 0; }
  if (!(w > 0)) w = text.length * size * 0.62;
  else if (tracking) w += tracking * size * String(text).length;
  widths[key] = w;
  return w;
}

/* Wrap to a measured width, and tell the truth when it does not fit.

   A WORD MAY BREAK AT ITS OWN JOINTS. "Logistic-regression-weighted" is one
   word to a space-splitter and wider than a box, and cutting it by characters
   came out as "Logistic-regressi-" over "on-weighted" -- a hyphen nobody wrote,
   in the middle of a syllable. So a word is split after every hyphen, dash,
   underscore and slash first, and the pieces are laid like words that need no
   space between them. A piece that still does not fit is cut, as before. */
function pieces(text) {
  var out = [];
  String(text || "").trim().split(/\s+/).filter(Boolean).forEach(function (w) {
    /* No lookbehind: an iPad a few versions old refuses the whole file. */
    (w.match(/[^\-\u2010-\u2014_\/]*[\-\u2010-\u2014_\/]+|[^\-\u2010-\u2014_\/]+/g)
     || [w]).forEach(function (bit, i) {
      out.push({ s: bit, glued: i > 0 });
    });
  });
  return out;
}

function wrap(text, size, weight, room, maxLines) {
  var words = pieces(text);
  var lines = [], line = "";
  while (words.length && lines.length < maxLines) {
    var word = words[0];
    var probe = line ? line + (word.glued ? "" : " ") + word.s : word.s;
    if (width(probe, size, weight) <= room) {
      line = probe;
      words.shift();
      continue;
    }
    if (!line) {
      /* One piece wider than the box -- a long path, usually. Break it rather
         than let it run out of the box, which is the whole defect this
         measuring exists to fix. */
      var cut = word.s;
      while (cut.length > 1 && width(cut + "-", size, weight) > room) {
        cut = cut.slice(0, -1);
      }
      words[0] = { s: word.s.slice(cut.length), glued: true };
      line = cut + "-";
    }
    lines.push(line);
    line = "";
  }
  if (line && lines.length < maxLines) lines.push(line);
  if (words.length && lines.length) {
    var last = lines[lines.length - 1];
    while (last && width(last + "…", size, weight) > room) {
      last = last.slice(0, -1);
    }
    lines[lines.length - 1] = last.replace(/[ ,;:.\-]+$/, "") + "…";
  }
  return lines;
}

/* Does this text fit in `room` within `maxLines`, whole -- no ellipsis and no
   piece cut by characters? */
function fits(text, size, weight, room, maxLines) {
  var lines = wrap(text, size, weight, room, maxLines);
  var last = lines[lines.length - 1] || "";
  if (/…$/.test(last) && !/…$/.test(String(text || "").trim())) return false;
  var joined = lines.join("").replace(/\s+/g, "");
  return joined === String(text || "").replace(/\s+/g, "");
}

/* The same lines, balanced: the narrowest room that still takes the text in
   as few lines as `room` does. A two-line title reads as two halves rather
   than a full line over a single word. Where the text does not fit whole it is
   left as `wrap` gives it -- balancing an ellipsis only moves where it falls. */
function balance(text, size, weight, room, maxLines) {
  var lines = wrap(text, size, weight, room, maxLines);
  if (lines.length < 2 || !fits(text, size, weight, room, maxLines)) return lines;
  var n = lines.length, lo = room / n, hi = room;
  for (var k = 0; k < 12 && hi - lo > 1; k++) {
    var mid = (lo + hi) / 2;
    var got = wrap(text, size, weight, mid, n);
    if (got.length <= n && fits(text, size, weight, mid, n)) hi = mid; else lo = mid;
  }
  return wrap(text, size, weight, hi, n);
}

/* An SVG element with its attributes set. Every plane builds its picture out
   of these, and `createElementNS` with the namespace spelled out is the part
   that is easy to get wrong once and then copy. */
function el(tag, attrs) {
  var node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (var key in attrs) {
    if (Object.prototype.hasOwnProperty.call(attrs, key)) {
      node.setAttribute(key, attrs[key]);
    }
  }
  return node;
}

window.Gauge = {
  uiFace: uiFace,
  font: font,
  width: width,
  wrap: wrap,
  fits: fits,
  balance: balance,
  el: el,
  onFace: onFace,
  faceChanged: faceChanged,
  /* For the suites, and for anything that needs to know whether the numbers it
     is holding were measured in the face they will be painted in. */
  faceReady: function () { return faceReady; }
};

})();
