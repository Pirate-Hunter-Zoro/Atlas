/* ==========================================================================
   keyguard.js -- FINGERS TYPE, THE PENCIL DRAWS.

   On an iPad a text field touched by the Apple Pencil belongs to Scribble, and
   Scribble's palette opens the small floating keyboard, which ignores the
   pinch. Once it has, the whole app process keeps choosing it, so later taps
   with a finger get it too. Nothing a page says chooses the keyboard; what a
   page can choose is whether Scribble ever sees a field.

   Scribble looks for fields in a rectangle round the stroke, so writing NEAR a
   box takes it as surely as writing on it, and it skips a field that is
   `readonly`. So on a touch device every text field is readonly while it does
   not have the focus, and a finger takes the lock off as it lands, before the
   tap focuses it: a field readonly at the moment it is focused gets no
   keyboard at all, and one that is not gets the full one.

     a finger       unlocks the field it lands on and any within reach of it;
                    locked again once it lifts if nothing took the focus
     a palm         the Pencil, while the nib is down
     the Pencil     on a field, refused outright (no focus, no Scribble); and
                    anywhere at all, it takes the focus off a field that has it,
                    because the focused field is a Scribble target wherever the
                    stroke is, and picking the Pencil up means drawing
     a trackpad     a finger
     a hardware Tab the field unlocks as the focus lands on it
     a field focused  every field stays open until the focus leaves them all,
                    so the keyboard's previous and next arrows land unlocked

   OWNED, NOT FOUND. A field readonly in its markup, or made readonly before it
   reached the page (problem.js's copy box, the board's `#code-cmd`), is never
   touched: only a field this file locked carries `data-keyguard`, and only
   those are ever unlocked.

   A FOCUS THE PAGE GIVES goes through `KeyGuard.focus`, which takes the lock
   off first and refuses after a Pencil contact, so no page path can open the
   keyboard Scribble's way. On a device with no touch (a Mac, a laptop) this
   whole file is a plain `focus()`; nothing else here runs.

   Loaded before every page script that focuses a field.
   ========================================================================== */

(function () {
"use strict";

var MARK = "data-keyguard";
/* The input types that bring up a keyboard. A file picker, a checkbox or a
   colour well is not a place to type, and Scribble does not want it. */
var TYPED = /^(text|search|url|email|number|password|tel)$/;
/* How long after the last finger lifts a field it unlocked stays open. A tap
   focuses as the finger lifts, so this only has to outlast the click; past it,
   the touch was a scroll and the field is locked again. */
var SETTLE_MS = 600;
/* How far outside a field a finger can land and still be given it: WebKit
   aims a tap that misses at the nearest thing it can focus. */
var NEAR = 40;

var touchy = (navigator.maxTouchPoints || 0) > 0 && "ontouchstart" in window;
/* What last touched the glass, or pressed a key: "pen", "touch", "mouse",
   "key", or "" before anything has. */
var last = "";
var settle = 0;

function isField(el) {
  if (!el || el.nodeType !== 1) return false;
  var tag = el.tagName;
  if (tag === "TEXTAREA") return true;
  if (tag !== "INPUT") return false;
  var type = (el.getAttribute("type") || "text").toLowerCase();
  return TYPED.test(type);
}

function owned(el) {
  return !!(el && el.nodeType === 1 && el.hasAttribute(MARK));
}

function lock(el) {
  if (owned(el) && !el.hasAttribute("readonly")) el.setAttribute("readonly", "");
}

function unlock(el) {
  if (owned(el) && el.hasAttribute("readonly")) el.removeAttribute("readonly");
}

/* Taken over the first time it is seen, unless the page made it readonly
   itself. One that already has the focus stays open until it loses it, and so
   does every other while one of them has it (`openAll`). The Pencil is refused
   on the field and on its labels by a listener of their own, so only those
   rectangles hold a touch up waiting for the page; everywhere else a finger
   scrolls without asking. */
function guard(el) {
  if (!isField(el) || owned(el) || el.hasAttribute("readonly")) return;
  el.setAttribute(MARK, "");
  refuseOn(el);
  var labels = el.labels || [];
  for (var i = 0; i < labels.length; i++) refuseOn(labels[i]);
  if (!owned(document.activeElement)) lock(el);
}

function refuseOn(el) {
  el.addEventListener("touchstart", refusePen, { passive: false });
  el.addEventListener("pointerdown", refusePen, { passive: false });
}

/* No focus from the Pencil, on the field or on a label that would give it. */
function refusePen(ev) {
  var pen = ev.type === "pointerdown" ? ev.pointerType === "pen" : stylusIn(ev);
  if (pen && ev.cancelable) ev.preventDefault();
}

function guardIn(node) {
  if (!node || node.nodeType !== 1) return;
  if (isField(node)) { guard(node); return; }
  if (!node.querySelectorAll) return;
  var found = node.querySelectorAll("textarea, input");
  for (var i = 0; i < found.length; i++) guard(found[i]);
  /* A label that arrives after its field is refused too. */
  var labels = node.tagName === "LABEL" ? [node] : node.querySelectorAll("label");
  for (var j = 0; j < labels.length; j++) {
    if (owned(labels[j].control)) refuseOn(labels[j]);
  }
}

/* Every field this file holds, locked again except the one with the focus. */
function lockAll() {
  var all = document.querySelectorAll("[" + MARK + "]");
  for (var i = 0; i < all.length; i++) {
    if (all[i] !== document.activeElement) lock(all[i]);
  }
}

/* WHILE ONE HAS THE FOCUS, ALL ARE OPEN. The keyboard's previous and next
   arrows move the focus with no touch at all, and a field locked as the focus
   lands gets no keyboard. The Pencil locks them all again as it comes down. */
function openAll() {
  var all = document.querySelectorAll("[" + MARK + "]");
  for (var i = 0; i < all.length; i++) unlock(all[i]);
}

/* After the last finger lifts: a tap has focused its field by now, and
   whatever is still open with nothing focused was a scroll. */
function relock() {
  if (!owned(document.activeElement)) lockAll();
}

/* The field a touch would focus: the field itself, or a label for one. */
function fieldOf(target) {
  var t = target && target.nodeType === 1 ? target : target && target.parentElement;
  if (!t) return null;
  if (isField(t)) { guard(t); return owned(t) ? t : null; }
  var label = t.closest ? t.closest("label") : null;
  var ctl = label && label.control;
  if (ctl && isField(ctl)) { guard(ctl); return owned(ctl) ? ctl : null; }
  return null;
}

/* THE PENCIL WENT DOWN. Nothing is focused by it, and nothing stays open
   round it. Its touch on a field is refused by the field's own listener; ink
   anywhere else is left alone, because the slate and the annotation layer read
   the same touch. */
function penDown() {
  last = "pen";
  clearTimeout(settle);
  var had = document.activeElement;
  if (owned(had)) had.blur();
  lockAll();
}

/* A FINGER WENT DOWN. It unlocks the field it lands on and every field within
   `NEAR` of it: the tap is aimed by WebKit, which gives a near miss to the
   nearest field, and a field focused while still locked gets no keyboard at
   all. The settle locks again whatever the tap did not focus. */
function fingerDown(ev, kind, x, y, reach) {
  last = kind;
  var f = fieldOf(ev.target);
  if (f) unlock(f);
  if (typeof x !== "number" || typeof y !== "number") return;
  var pad = NEAR + (reach || 0);
  var all = document.querySelectorAll("[" + MARK + "]");
  for (var i = 0; i < all.length; i++) {
    if (!all[i].hasAttribute("readonly")) continue;
    var r = all[i].getBoundingClientRect();
    if (!r.width && !r.height) continue;
    if (x >= r.left - pad && x <= r.right + pad && y >= r.top - pad && y <= r.bottom + pad) {
      unlock(all[i]);
    }
  }
}

function settleSoon() {
  clearTimeout(settle);
  settle = setTimeout(relock, SETTLE_MS);
}

/* Whether the Pencil is on the glass for this touch: the touch itself, or a
   palm that came down while the nib was already there. A palm is not a finger,
   and opening the field under it would give Scribble a target mid-stroke. */
function stylusIn(ev) {
  var lists = [ev.changedTouches, ev.touches];
  for (var l = 0; l < lists.length; l++) {
    var list = lists[l] || [];
    for (var i = 0; i < list.length; i++) {
      if (list[i] && list[i].touchType === "stylus") return true;
    }
  }
  return false;
}

/* The one way a page focuses a field. It refuses after a Pencil contact:
   a keyboard opened from a Pencil gesture is Scribble's. Returns whether the
   field has the focus. */
function focusField(el, opts) {
  if (!el) return false;
  if (!touchy) { el.focus(opts); return document.activeElement === el; }
  if (last === "pen") return false;
  guard(el);
  unlock(el);
  el.focus(opts);
  if (document.activeElement !== el) { relock(); return false; }
  return true;
}

window.KeyGuard = {
  on: touchy,
  focus: focusField,
  /* What last touched the glass, for a page that needs to know. */
  contact: function () { return last; },
};

if (!touchy) return;

guardIn(document.documentElement);
document.addEventListener("DOMContentLoaded", function () { guardIn(document.body); });
/* Fields arrive all lesson long -- a card's controls, a panel built on first
   open -- and one left unlocked is a Scribble target for as long as it is on
   the page. */
if (window.MutationObserver) {
  new MutationObserver(function (records) {
    for (var r = 0; r < records.length; r++) {
      var added = records[r].addedNodes;
      for (var i = 0; i < added.length; i++) guardIn(added[i]);
    }
  }).observe(document.documentElement, { childList: true, subtree: true });
}

/* Passive: bookkeeping only. The refusal is the field's own listener, so a
   finger anywhere else scrolls without waiting on the page. */
document.addEventListener("touchstart", function (ev) {
  if (stylusIn(ev)) { penDown(); return; }
  var t = ev.changedTouches && ev.changedTouches[0];
  fingerDown(ev, "touch", t && t.clientX, t && t.clientY,
             t ? Math.max(t.radiusX || 0, t.radiusY || 0) : 0);
}, { capture: true, passive: true });

["touchend", "touchcancel"].forEach(function (type) {
  document.addEventListener(type, function (ev) {
    if (!ev.touches || ev.touches.length === 0) settleSoon();
  }, { capture: true, passive: true });
});

/* Pointer events carry the same news where touch events do not: the Pencil as
   "pen", a trackpad on an iPad as "mouse". `pointerType` here is reliable, as
   a click's is not. A "touch" that lands while a pen is down is the palm. */
var pens = {};
var pensDown = 0;
document.addEventListener("pointerdown", function (ev) {
  if (ev.pointerType === "pen") {
    if (!pens[ev.pointerId]) { pens[ev.pointerId] = true; pensDown++; }
    penDown();
  } else if (ev.pointerType === "touch" && pensDown > 0) {
    last = "pen";
  } else if (ev.pointerType === "mouse" || ev.pointerType === "touch") {
    fingerDown(ev, ev.pointerType, ev.clientX, ev.clientY,
               Math.max(ev.width || 0, ev.height || 0) / 2);
  }
}, { capture: true, passive: true });

["pointerup", "pointercancel"].forEach(function (type) {
  document.addEventListener(type, function (ev) {
    if (ev.pointerType === "pen" && pens[ev.pointerId]) {
      delete pens[ev.pointerId];
      pensDown--;
    }
    if (ev.pointerType === "mouse") settleSoon();
  }, { capture: true, passive: true });
});

/* A hardware keyboard's Tab moves the focus with no touch at all. */
document.addEventListener("keydown", function () { last = "key"; }, true);

/* The focus going from one field to another leaves them open; going anywhere
   else locks them all. */
document.addEventListener("focusout", function (ev) {
  if (!owned(ev.target) || owned(ev.relatedTarget)) return;
  var all = document.querySelectorAll("[" + MARK + "]");
  for (var i = 0; i < all.length; i++) lock(all[i]);
}, true);

/* A focus that arrived with the field still locked came by a road that does
   not unlock: a Tab, or a page path not routed through `KeyGuard.focus`. It is
   opened, so typing works -- unless the Pencil was the last thing on the
   glass, which makes it a Pencil focus and not one to keep. */
document.addEventListener("focusin", function (ev) {
  var t = ev.target;
  if (!isField(t)) return;
  guard(t);
  if (!owned(t)) return;
  if (t.hasAttribute("readonly") && last === "pen") { t.blur(); return; }
  openAll();
}, true);

})();
