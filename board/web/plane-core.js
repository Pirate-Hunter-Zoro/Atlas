/* ==========================================================================
   plane-core.js -- what every surface that is a PLANE has to get right.

   There are two of them now. The writing surface has been a plane since the
   page stopped being a box, and the map is one from the day it ships. Both
   answer the same two questions on every frame -- what is the hand doing, and
   where is the view allowed to be -- and the answers are not obvious. Every
   rule in this file was written after a gesture stopped working on somebody's
   iPad in the middle of real work:

     * A GESTURE IS DECIDED BY WHICH CONTACTS ARE LIVE, never by the size of a
       map that may be holding a finger whose lift was never delivered. Two
       entries and one real finger made one moving finger zoom; three entries
       and two real fingers made a pinch do nothing at all. Reported in exactly
       that shape: "one finger acts as if I'm zooming with two fingers! And two
       fingers does nothing."
     * EVERY REFUSAL EXPIRES. A latch that cannot time out is a surface that
       stops answering with nothing to see from the outside.
     * A PINCH IS BETWEEN THE TWO CONTACTS IT STARTED BETWEEN, while both are
       still down -- not between whichever two the map happens to hold. A palm
       landing beside two fingers already pinching used to end the gesture.
     * THE VIEW IS CLAMPED TO THE CONTENT PLUS SLACK, not to a box. An
       unclamped plane flung into empty space looks exactly like a crash, and a
       hard edge a screen away is why the page stopped being a box.

   This file owns that machinery and nothing else. It knows nothing about ink,
   about nodes, or about what is being drawn -- it is arithmetic and
   bookkeeping, so the two surfaces cannot drift apart on the half of the
   problem that has already cost an evening.

   Loaded before slate-core.js and board.js, which both read it.
   ========================================================================== */

(function () {
"use strict";

/* How long a contact may sit in the map, unheard from, before it is taken to be
   one whose lift was never delivered. No gesture is held this long. */
var TOUCH_STALE = 20000;
/* And a much tighter bound for the arithmetic that decides what a gesture IS.
   A live contact reports on every frame it moves, and a hand holding a pinch
   still reports as it settles -- so a contact that has said nothing for this
   long while another is moving is not part of the gesture in hand. Long enough
   that a finger resting perfectly still through a slow pinch is kept. */
var GESTURE_STALE = 2500;

/* --------------------------------------------------------------- contacts */
/* The fingers on the glass, and what they add up to.

   `onPinchEnd` is called when a pinch ends because one of its OWN pair left --
   which is the moment a surface that showed a cheap stretched preview during
   the gesture has to pay for a proper repaint. */
function contacts(opts) {
  opts = opts || {};
  var map = {};
  var pinch = null;

  function now() { return Date.now(); }

  /* Record a contact, or move one. Same call for down and for move: a contact
     is defined by where it is and when it last said so. */
  function note(id, x, y) {
    var was = map[id];
    map[id] = { x: x, y: y, at: now() };
    return was || null;
  }

  function at(id) { return map[id] || null; }
  function has(id) { return !!map[id]; }

  /* WHICH CONTACTS ARE ACTUALLY PART OF THE GESTURE IN HAND.

     Everything downstream decides what a gesture is by counting this -- one
     contact pans, two pinch -- so a contact that should not be in it does not
     merely add noise, it changes the answer. Anything that has not reported
     since `GESTURE_STALE` is dropped before it is counted. */
  function live() {
    var t = now();
    var ids = Object.keys(map);
    var out = [];
    for (var i = 0; i < ids.length; i++) {
      var c = map[ids[i]];
      if (!c || t - (c.at || 0) > GESTURE_STALE) { delete map[ids[i]]; continue; }
      out.push(ids[i]);
    }
    return out;
  }

  /* Is anything resting on the glass at all, generously.

     Every other test a surface makes is a timestamp of the last thing the hand
     DID, and a finger held still does nothing -- which is how a pinch is held
     at the zoom you wanted, and how it is repositioned between two pinches. The
     bound is loose here and tight in `live` on purpose: this one answers "is
     somebody mid-gesture, keep expensive work away", and being wrong costs a
     stutter rather than a dead surface. */
  function onGlass() {
    var t = now();
    var ids = Object.keys(map);
    for (var i = 0; i < ids.length; i++) {
      var c = map[ids[i]];
      if (c && t - (c.at || 0) < TOUCH_STALE) return true;
    }
    return false;
  }

  /* The two contacts a pinch is between: the two most recently heard from, so a
     palm that lands beside two fingers already pinching cannot take the gesture
     over or stop it. Counting exactly two used to mean a third contact -- the
     heel of a hand arriving late -- silently ended the pinch. */
  function pair(ids) {
    var l = ids || live();
    if (l.length < 2) return null;
    var sorted = l.slice().sort(function (a, b) {
      return (map[b].at || 0) - (map[a].at || 0);
    });
    return [sorted[0], sorted[1]];
  }

  /* Start a pinch between the two most recent contacts, at the zoom showing
     now. Null when there are not two of them. */
  function begin(k) {
    var p = pair();
    if (!p) return null;
    var a = map[p[0]], b = map[p[1]];
    pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), k: k, ids: [p[0], p[1]] };
    return pinch;
  }

  /* The pinch in progress, and the two contacts making it -- or null. Read
     against the raw map rather than `live()`: the pair is fixed at the start of
     the gesture, and re-choosing on every move is how a third contact takes a
     gesture over halfway through. */
  function pinching() {
    if (!pinch || !pinch.ids) return null;
    var a = map[pinch.ids[0]], b = map[pinch.ids[1]];
    if (!a || !b) return null;
    return { pinch: pinch, a: a, b: b };
  }

  /* How much the fingers have spread since the pinch began, as a zoom, and
     where the middle of them is. */
  function spread() {
    var p = pinching();
    if (!p) return null;
    return {
      k: p.pinch.k * (Math.hypot(p.a.x - p.b.x, p.a.y - p.b.y) / p.pinch.d),
      cx: (p.a.x + p.b.x) / 2,
      cy: (p.a.y + p.b.y) / 2
    };
  }

  /* Forgetting one contact, and ending the pinch if it was one of the pair.

     A lift is caught in two places -- at the surface, and at the window for a
     finger that left past the surface's edge -- and the two must do the same
     thing. Idempotent, so whichever hears it first does the work and the other
     is a no-op. The pinch ends when one of ITS OWN pair leaves, not when the
     map happens to drop below two: a palm resting alongside kept the count up
     and left the surface soft after the fingers had gone. */
  function forget(id) {
    var had = !!map[id];
    if (had) delete map[id];
    if (pinch && !(map[pinch.ids[0]] && map[pinch.ids[1]])) {
      pinch = null;
      if (opts.onPinchEnd) opts.onPinchEnd();
    }
    return had;
  }

  /* Everything on the glass, dropped, and the ids handed back. The writing
     surface needs the ids: a contact that is merely forgotten gets re-read as a
     fresh finger by the next move it makes, so it condemns them as palms. */
  function clear() {
    var ids = Object.keys(map);
    map = {};
    pinch = null;
    return ids;
  }

  return {
    note: note, at: at, has: has, live: live, onGlass: onGlass,
    pair: pair, begin: begin, pinching: pinching, spread: spread,
    forget: forget, clear: clear,
    /* For a surface that has to ask whether a gesture is running at all. */
    active: function () { return !!pinching(); }
  };
}

/* ------------------------------------------------------------- the view */
/* A view is `{ k, fit, ox, oy, held }`: a scale, the scale that counts as
   fitted, an offset in screen units, and whether the person has set the zoom
   themselves. `held` is the one that is easy to leave out and expensive to:
   the board re-renders on every server event, and a re-render that throws away
   the zoom somebody just set makes a surface unusable. */

/* The region a view is allowed into: the content, plus this many viewports of
   clear space in every direction. Adding to the content grows it, so the plane
   has no edge -- but the clamp still exists, so a stray pinch cannot fling the
   surface into empty space a mile from the nearest thing on it. */
function room(box, cw, ch, k, viewports) {
  var mx = (cw / k) * viewports, my = (ch / k) * viewports;
  return { x0: box.x0 - mx, y0: box.y0 - my,
           x1: box.x1 + mx, y1: box.y1 + my };
}

/* Put the view back inside `r`, centring whichever axis has room to spare.
   Mutates and returns the view, which is what every caller wants. */
function clamp(view, r, cw, ch) {
  var w = (r.x1 - r.x0) * view.k, h = (r.y1 - r.y0) * view.k;
  if (w <= cw) view.ox = (cw - w) / 2 - r.x0 * view.k;
  else view.ox = Math.min(-r.x0 * view.k, Math.max(cw - r.x1 * view.k, view.ox));
  if (h <= ch) view.oy = (ch - h) / 2 - r.y0 * view.k;
  else view.oy = Math.min(-r.y0 * view.k, Math.max(ch - r.y1 * view.k, view.oy));
  return view;
}

/* Zoom to `k` about the point (cx, cy) in the surface's own coordinates, so
   what is under two fingers stays under them. Clamped between `lo` and `hi`
   before anything moves: zooming out of the allowed range and clamping
   afterwards drifts the centre. */
function zoomAbout(view, k, cx, cy, lo, hi) {
  k = Math.max(lo, Math.min(hi, k));
  var lx = (cx - view.ox) / view.k, ly = (cy - view.oy) / view.k;
  view.k = k;
  view.ox = cx - lx * view.k;
  view.oy = cy - ly * view.k;
  view.held = true;
  return view;
}

/* Frame a box in a viewport: the scale that fits it with padding, and the
   offsets that centre it. The scale is clamped, so framing something tiny does
   not magnify it past what the surface allows. */
function frame(view, box, cw, ch, pad, lo, hi) {
  var w = (box.x1 - box.x0) + pad * 2, h = (box.y1 - box.y0) + pad * 2;
  if (w <= 0 || h <= 0 || !cw || !ch) return view;
  var k = Math.min(cw / w, ch / h);
  view.k = Math.max(lo, Math.min(hi, k));
  view.ox = (cw - (box.x1 - box.x0) * view.k) / 2 - box.x0 * view.k;
  view.oy = (ch - (box.y1 - box.y0) * view.k) / 2 - box.y0 * view.k;
  return view;
}

window.Plane = {
  TOUCH_STALE: TOUCH_STALE,
  GESTURE_STALE: GESTURE_STALE,
  contacts: contacts,
  room: room,
  clamp: clamp,
  zoomAbout: zoomAbout,
  frame: frame
};

})();
