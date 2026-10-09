/* ==========================================================================
   recentre.js -- the way back, from anywhere, on every surface that has one.

   There are two ways to be lost on this application and they are not the same
   way. The PAGE can be pinch-zoomed, which is the browser's own magnification
   and nothing in the app can set it directly. And a PLANE -- the writing
   surface, the map of a workspace, the atlas of all of them -- has a pan and a
   zoom of its own that the browser knows nothing about. Both of them end
   somewhere with nothing recognisable on the glass, and neither can be undone
   by the gesture that caused it once the surface fills the screen.

   So there are a few small buttons floating over the page, and this file is all
   of it: where each one sits, how each one is moved, and what a tap on the first
   one does. Each is its own widget -- its own place, remembered on its own -- so
   putting one somewhere does not drag the others along behind it.

   THE ONE THING THAT IS EASY TO GET WRONG. `position: fixed` is fixed to the
   LAYOUT viewport, and pinching moves the VISUAL one -- so a control placed by
   CSS alone slides off the glass at exactly the moment it is needed, and looks
   perfect in every test that never zooms. Everything here is placed from
   JavaScript against `visualViewport`, with a counter-scale so the button stays
   the same size under a thumb however far the page has been zoomed in.

   Extracted from board.js because the front door needs it too: a way back
   that exists on one page and not the other is a way back nobody can rely on.

   Loaded before board.js, home.js and readerzoom.js, which asks `unzoom` to
   put a page zoom back when a document opens over one.
   ========================================================================== */

(function () {
"use strict";

/* Of the visible window, its centre. Hard against the right edge and high up:
   clear of the prose measure, and above the writing tools. Wherever it lands it
   is in somebody's way eventually, which is what the press and hold is for. */
var DEFAULT_AT = { x: .975, y: .1 };
var HOLD_MS = 380;               /* a press, rather than a tap: held by TIME */
var ROW = .07;                   /* where the next one starts out, down the glass */

/* Each button is its own widget with its own place on the glass: re-centring
   the zoom, finding your writing and abandoning the plan have nothing to do
   with each other, so each carries its own anchor and remembered position
   under its own key. */
var items = [];                  /* [{ el, onTap, size, fallback, at, key }] */
var base = "";
var held = null;
var frame = 0;
var wired = false;

function forget() {
  for (var i = 0; i < items.length; i++) items[i].size = null;
}

function remember(one) {
  try { localStorage.setItem(one.key, JSON.stringify(one.at)); } catch (e) {}
}

/* Coalesced to one placement per frame, and each button's own size measured
   only when something could have changed it. This is hung off every scroll and
   every visual-viewport event, which during a flick on a tablet is every frame
   -- and reading two offsets and writing a transform each time is a forced
   layout per scroll event, which is how a page that is merely scrolling starts
   to stutter. A control that stutters while everything else moves smoothly
   reads as the whole screen misbehaving. */
function soon() {
  if (frame) return;
  frame = window.requestAnimationFrame(function () {
    frame = 0;
    place();
  });
}

function place() {
  if (!items.length) return;
  var vv = window.visualViewport;
  var w = vv ? vv.width : window.innerWidth;
  var h = vv ? vv.height : window.innerHeight;
  var ox = vv ? vv.offsetLeft : 0;
  var oy = vv ? vv.offsetTop : 0;
  var k = (vv && vv.scale) ? vv.scale : 1;
  var pad = 6 / k;

  for (var i = 0; i < items.length; i++) {
    var one = items[i];
    if (!one.el || one.el.hidden) continue;
    if (!one.size || !one.size.w) {
      one.size = { w: one.el.offsetWidth || one.fallback.w,
                   h: one.el.offsetHeight || one.fallback.h };
    }
    /* Drawn at 1/k, so the room it takes in the page's own units is its CSS
       size divided by the magnification. */
    var bw = one.size.w / k;
    var bh = one.size.h / k;
    var x = ox + one.at.x * w - bw / 2;
    var y = oy + one.at.y * h - bh / 2;
    /* Clamped into the visible window, and NOT written back into the anchor: a
       button parked off the edge of a phone comes back where it was put when
       the same board is opened on a tablet. */
    x = Math.min(Math.max(x, ox + pad), ox + w - bw - pad);
    y = Math.min(Math.max(y, oy + pad), oy + h - bh - pad);
    one.el.style.transform =
      "translate(" + x + "px," + y + "px) scale(" + (1 / k) + ")";
  }
}

/* Acknowledge the tap. What these buttons do is a change of SCALE and not a
   change of content, which is easy to miss on a page you were lost in. */
function flash(el) {
  if (!el) return;
  el.classList.add("hit");
  setTimeout(function () { el.classList.remove("hit"); }, 420);
}

/* There is no way to set the page's magnification directly -- it is the user's,
   and rightly so. What some browsers honour is a change to the viewport
   declaration: clamping the scale to 1 makes them zoom out to fit. The clamp is
   lifted again a moment later, or the page could never be zoomed in again, which
   would be a cure worse than the disease.

   SAFARI ON AN IPAD IGNORES THE CLAMP. It treats `maximum-scale` and
   `user-scalable` as advisory, so there the declaration changes and the zoom does
   not. Every limit is set at once anyway, because the declaration is all a page
   has, and the focused field is let go because a field Safari zoomed into holds
   the zoom. What happens when the zoom stays is `stuck`, below. */
var wasViewport = null;

function restore() {
  if (wasViewport === null) return;
  var meta = document.querySelector('meta[name="viewport"]');
  if (meta) meta.setAttribute("content", wasViewport);
  wasViewport = null;
}

function unzoom() {
  var meta = document.querySelector('meta[name="viewport"]');
  if (!meta) return;
  var was = meta.getAttribute("content") || "";
  if (/maximum-scale/.test(was)) return;         /* a reset is already running */
  wasViewport = was;
  var el = document.activeElement;
  if (el && el !== document.body && el.blur) el.blur();
  meta.setAttribute("content",
                    was + ", minimum-scale=1, maximum-scale=1, user-scalable=no");
  /* Put it back, and mean it. A clamp left in place is a page that can never be
     zoomed again -- a worse state than the one this exists to leave, and one
     with no button of its own. So the restore hangs off everything that could
     plausibly happen next, not off a single timer that a backgrounded app is
     free to drop on the floor. */
  setTimeout(restore, 450);
  window.addEventListener("pointerdown", restore, { once: true });
  document.addEventListener("visibilitychange", restore, { once: true });
}

/* The page's magnification, put back. It does NOT move the content.

   It did at first, and that was a misreading of what "lost" means here: being
   zoomed too far into the writing is not the same as being in the wrong part of
   the transcript, and answering the first with the second takes the page away
   from somebody who was looking at exactly the right thing. The zoom is the
   thing that cannot be undone by hand once the surface fills the glass; the
   scrolling never needed help. */
function pageBack(el) {
  unzoom();
  flash(el);
  /* The magnification settles over the next few frames, and every one of them
     changes what "the visible window" means. */
  [0, 120, 300, 500].forEach(function (ms) { setTimeout(place, ms); });
  forget();
  setTimeout(stuck, 650);
}

/* The browser kept its zoom. Then the page's own `onStuck` runs, if it gave
   one: the one thing left that a page can do is move the content under the
   glass, and only the page knows what is worth moving to. Only on failure,
   because a zoom that did drop left the reader looking at the right thing. */
var onStuck = null;

function stuck() {
  var vv = window.visualViewport;
  if (!vv || !(vv.scale > 1.05) || !onStuck) return;
  onStuck();
  [120, 400].forEach(function (ms) { setTimeout(place, ms); });
}

/* Every button moves itself, and only itself: a press and hold picks up that
   one, since a control that moves something else cannot be aimed. */
function drag(one) {
  one.el.addEventListener("pointerdown", function (ev) {
    ev.preventDefault();
    try { one.el.setPointerCapture(ev.pointerId); } catch (e) { /* not fatal */ }
    /* Where this button sits relative to the anchor, as a fraction of the
       visible window, measured before anything moves. */
    var vv0 = window.visualViewport;
    var w0 = vv0 ? vv0.width : window.innerWidth;
    var h0 = vv0 ? vv0.height : window.innerHeight;
    var ox0 = vv0 ? vv0.offsetLeft : 0;
    var oy0 = vv0 ? vv0.offsetTop : 0;
    held = {
      id: ev.pointerId, drag: false, one: one,
      dx: (ev.clientX - ox0) / w0 - one.at.x,
      dy: (ev.clientY - oy0) / h0 - one.at.y,
      timer: setTimeout(function () {
        if (!held) return;
        held.drag = true;
        one.el.classList.add("holding");
        if (navigator.vibrate) { try { navigator.vibrate(8); } catch (e) {} }
      }, HOLD_MS),
    };
  });

  one.el.addEventListener("pointermove", function (ev) {
    if (!held || ev.pointerId !== held.id || !held.drag) return;
    var vv = window.visualViewport;
    var w = vv ? vv.width : window.innerWidth;
    var h = vv ? vv.height : window.innerHeight;
    var ox = vv ? vv.offsetLeft : 0;
    var oy = vv ? vv.offsetTop : 0;
    /* clientX is in the layout viewport's units, which is what the offsets
       convert out of. `dx`/`dy` hold where on the button the finger landed, so
       it does not jump under the thumb the moment it comes free. */
    one.at.x = Math.min(Math.max((ev.clientX - ox) / w - held.dx, 0), 1);
    one.at.y = Math.min(Math.max((ev.clientY - oy) / h - held.dy, 0), 1);
    place();
  });

  /* A tap on a tablet always travels a few pixels, so a tap is told from a drag
     by TIME and never by distance: by distance the button sometimes moves when
     it was meant to act, and sometimes acts when it was meant to move. */
  var release = function (ev) {
    if (!held || ev.pointerId !== held.id) return;
    clearTimeout(held.timer);
    var moved = held.drag;
    held = null;
    one.el.classList.remove("holding");
    if (moved) {
      remember(one);
      return;
    }
    if (ev.type !== "pointercancel" && one.onTap) one.onTap(one.el);
  };
  one.el.addEventListener("pointerup", release);
  one.el.addEventListener("pointercancel", release);
}

/* A remembered position, or nothing. */
function saved(k) {
  try {
    var got = JSON.parse(localStorage.getItem(k) || "null");
    if (got && typeof got.x === "number" && typeof got.y === "number") {
      return { x: got.x, y: got.y };
    }
  } catch (e) { /* a corrupt preference is not worth a broken board */ }
  return null;
}

/* mount({ key, onStuck, at, buttons: [{ el, onTap, w, h }] })

   `at` is where a page wants the stack to start when nothing was ever saved, for
   a page whose top right corner is already somebody's controls.

   The first button's tap puts the page's magnification back, which is what it is
   for on every surface; the rest say what they do. Every one of them is placed
   on its own and remembered on its own, under `<key>.<id>`. */
function mount(spec) {
  spec = spec || {};
  base = spec.key || "board.panic";
  onStuck = spec.onStuck || null;
  items = [];
  /* The old shared group position, read once, so buttons first appear where
     the group was left rather than back in the corner. */
  var wasGroup = saved(base);
  (spec.buttons || []).forEach(function (b, i) {
    if (!b || !b.el) return;
    var id = b.el.id || ("b" + i);
    /* The handle's tap puts the page back unless it is told otherwise. A button
       with no `onTap` is one that carries its own listener already -- it is here
       to be PLACED, and a second listener would fire alongside its own. */
    var one = {
      el: b.el,
      onTap: b.onTap || (i === 0 ? pageBack : null),
      size: null,
      fallback: { w: b.w || 108, h: b.h || 32 },
      key: base + "." + id,
      at: null,
    };
    one.at = saved(one.key);
    if (!one.at) {
      /* Down the right-hand edge in the order they were given, which is where
         the stack put them -- from wherever the group was last left, if it was
         ever moved. */
      var from = wasGroup || spec.at || DEFAULT_AT;
      one.at = { x: from.x, y: Math.min(from.y + i * ROW, 1) };
    }
    items.push(one);
  });
  if (!items.length) return;

  for (var i = 0; i < items.length; i++) drag(items[i]);

  if (!wired) {
    wired = true;
    ["resize", "scroll"].forEach(function (ev) {
      if (window.visualViewport) window.visualViewport.addEventListener(ev, soon);
      window.addEventListener(ev, soon, { passive: true });
    });
    window.addEventListener("resize", forget);
    window.addEventListener("orientationchange", function () {
      forget();
      setTimeout(place, 120);
    });
  }
  place();
}

window.Recentre = {
  mount: mount,
  place: place,
  soon: soon,
  /* A button that has appeared or gone changes the height of everything under
     it, and a stale height leaves a gap or an overlap in the stack. */
  remeasure: function () { forget(); soon(); },
  unzoom: unzoom,
  flash: flash,
  pageBack: pageBack,
};

})();
