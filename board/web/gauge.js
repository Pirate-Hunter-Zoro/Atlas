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

/* The face the board actually ships, off the page's own `--ui` token rather
   than guessed: the fallback stack and the real one do not measure the same. */
function uiFace() {
  if (face) return face;
  face = "system-ui, -apple-system, 'Segoe UI', sans-serif";
  try {
    var said = window.getComputedStyle(document.body).getPropertyValue("--ui");
    if (said && said.trim()) face = said.trim();
  } catch (e) { /* the default stack is a fair guess */ }
  return face;
}

function font(size, weight) {
  return (weight || 400) + " " + size + "px " + uiFace();
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
  widths[key] = w;
  return w;
}

/* Wrap to a measured width, and tell the truth when it does not fit. */
function wrap(text, size, weight, room, maxLines) {
  var words = String(text || "").trim().split(/\s+/).filter(Boolean);
  var lines = [], line = "";
  while (words.length && lines.length < maxLines) {
    var word = words[0];
    var probe = line ? line + " " + word : word;
    if (width(probe, size, weight) <= room) {
      line = probe;
      words.shift();
      continue;
    }
    if (!line) {
      /* One word wider than the box -- a long path, usually. Break it rather
         than let it run out of the box, which is the whole defect this
         measuring exists to fix. */
      var cut = word;
      while (cut.length > 1 && width(cut + "-", size, weight) > room) {
        cut = cut.slice(0, -1);
      }
      words[0] = word.slice(cut.length);
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
  el: el
};

})();
