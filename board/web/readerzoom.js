/* ==========================================================================
   readerzoom.js -- a reader that zooms itself, and a palm that does not scroll.

   THE READER ZOOMS ITSELF, AND SAFARI DOES NOT. Safari's own pinch scales the
   whole page -- bar and all -- and leaves the reader scrolling a layout that
   thinks nothing happened. Here a pinch changes the WIDTH the pages are laid
   out at (`--zoom` on the scroller, read by `.lib-page` in `library.css`): the
   pictures and the ink are re-laid out rather than magnified, the pen measures
   real pixels at any zoom, and ink kept in fractions of a page lands where it
   was drawn. While the fingers are down the scroller is only transformed,
   because re-laying out every page every frame is a stutter; the lift commits
   the width, with the point first under the fingers put back under them.

   AND A PALM DOES NOT SCROLL, BUT A FINGER DOES. With the pen on or off, one
   finger scrolls and two pan and pinch. What is refused is a hand writing: a
   contact wider than a fingertip, anything landing while the Pencil is on the
   glass, or anything landing while the nib has only just lifted (`pen-writing`,
   `annotate.js`'s latch, which also sets `touch-action: none` on the pages in
   `library.css`). A hand writing is never a pinch either.

   AND SAFARI NEVER GETS A PINCH WHILE A DOCUMENT IS OPEN. A pinch the reader
   does not take is Safari's, and a shut it takes bounces the whole page. A
   wide shut lands one finger at a time, often one on the bar, sometimes a
   flat thumb over the palm radius, so every listener is on the document, in
   the capture phase, and only while a document is open (`live`). Three
   rules, from the most certain to the least:
     * Two fingertips on the document's own surface -- the whole reader
       (`surface`: its bar, the strips under the bar, the scroller), minus an
       overlay above it (`OVERLAY`) -- are the reader's. The touch that makes
       them is cancelled whatever it lands on, a bar button included, and so
       is every move while they last. A control whose touch that cancels gets
       its click back when it lifts, however long it was held, if its contact
       has not moved past `SCROLL_SLOP` and the pair's gap has not changed by
       `PINCH_SLOP`: the pinch built beside it is then one that never moved,
       and a pinch that never moved commits nothing.
     * A pinch is BUILT only from those, and only if the second landed within
       `PAIR_MS` of the first or the first has not begun a native scroll: a
       thumb landing during a scroll is refused, not turned into a zoom.
     * Anything else with two contacts -- a palm beside a finger, a finger on
       an overlay (the note panel, `#steer`, `#calc`, the annotation bar) --
       keeps its touchstart, because a palm resting while one finger scrolls
       is a scroll, and two fingers scrolling a textarea are a scroll. Its
       moves are cancelled once the pair is PINCHING: the gap between the two
       has changed by over `PINCH_SLOP`, and if one is a palm, the palm's own
       move made that change, since a resting palm stays put while the finger
       beside it scrolls and a flat thumb in a shut sweeps (`pinching`).
   The iOS gesture events are refused throughout. iOS fixes a gesture's
   native handling from its FIRST touch, so the non-passive `touchmove` that
   does the refusing is armed at that touch and dropped once every finger
   lifts or a lone finger passes `SCROLL_SLOP`: that finger is a scroll, and
   the rest of its moves never wait on the main thread. A second contact arms
   it again.

   AND A PAGE ZOOM ALREADY IN EFFECT IS PUT BACK. However Safari came to
   magnify the page -- a double tap, a focused field, a pinch on the list
   before the document opened -- a reader fixed to the layout viewport, with
   every pinch refused, leaves no way out of it. So a document opening, and
   `visualViewport` reporting a scale over `PAGE_ZOOMED` while one is open,
   asks `recentre.js` for the page's scale back (`Recentre.unzoom`, the clamp
   `#panic` uses). A focused field keeps its zoom until it lets go of focus,
   because the reset blurs it. Where Safari ignores the clamp, a gesture that
   begins on a magnified page is left to Safari (`aside`): its pinch out is
   then the only way back, and nothing here refuses it.

   WHAT IT DID IS WRITTEN DOWN, for the device that saw it: every touchstart
   it cancels, the first touchmove of a gesture it cancels and any it could
   not (`ev.cancelable` false, WebKit having already taken the gesture), each
   page-zoom reset, and each gesture left to Safari. Into `window.BoardTrace`
   when the page has one (the board), and always into `ReaderZoom.trace()`,
   the last `TRACE_MAX`, read from Web Inspector. Nothing leaves the page.

   The library reader, the meeting deck and the board's document panel use it:
     ReaderZoom.make({ scroller, surface, bar, chip, page, open(), committed() })
       -> { set(z), zoom(), live(on) }
   `page` is the selector of one page box (`.lib-page` by default). A surface
   with an `open` says when its document opens and shuts with `live`; one
   without (the meeting deck) is always open and is live from the start.
   ========================================================================== */

(function () {
"use strict";

var ZOOM_MIN = 0.5;
var ZOOM_MAX = 3;           /* the pages are drawn 1240 px wide; past this, blur */
/* A contact wider than a fingertip is the side of a hand. */
var PALM_RADIUS = 40;

function clamp(z) { return Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, z)); }

function penIsOn() { return !!(window.Annotate && window.Annotate.isOn()); }

/* A lone finger that has moved this far is a scroll (`annotate.js`'s
   `HAND_SLOP`), and a control's contact that has is not a tap. */
var SCROLL_SLOP = 10;
/* Two contacts whose gap has changed this much are pinching. */
var PINCH_SLOP = 10;
/* A second fingertip this soon after the first is one gesture, however far
   the first has moved: a shut lands its fingers tens of ms apart. */
var PAIR_MS = 200;
var CONTROL = "button, a, input, select, textarea, label, summary";
/* Above the reader and not of it: two fingers here are not the reader's. */
var OVERLAY = "#note, #steer, #calc, .annbar";
/* Safari's page magnification past this is a page zoom to put back. */
var PAGE_ZOOMED = 1.01;

function pageScale() {
  var vv = window.visualViewport;
  return vv && vv.scale ? vv.scale : 1;
}

/* A field being typed in: Safari zoomed into it, and a reset blurs it. */
function editing() {
  var a = document.activeElement;
  return !!(a && a !== document.body
            && (a.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(a.nodeName)));
}

var TRACE_MAX = 120;
var traced = [];
function trace(what, of) {
  traced.push({ at: Date.now(), what: what, of: of || null });
  if (traced.length > TRACE_MAX) traced.shift();
  if (!window.BoardTrace) return;
  try { window.BoardTrace(what, of); } catch (e) { /* a record is never worth an exception */ }
}

/* Every contact that is not the Pencil, palms and thumbs included, with a key
   that finds the same contact in a later event. `fingers` is what may pinch. */
function contacts(ev) {
  var out = [];
  for (var i = 0; i < ev.touches.length; i++) {
    var t = ev.touches[i];
    if (t.touchType !== "stylus") out.push({ t: t, k: keyOf(t, i) });
  }
  return out;
}

function keyOf(t, i) {
  return t.identifier !== undefined && t.identifier !== null ? "id" + t.identifier : "at" + i;
}

function find(ev, k) {
  for (var i = 0; i < ev.touches.length; i++) {
    if (keyOf(ev.touches[i], i) === k) return ev.touches[i];
  }
  return null;
}

function apart(a, b) { return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY); }

function fingers(ev) {
  var out = [];
  for (var i = 0; i < ev.touches.length; i++) {
    var t = ev.touches[i];
    if (t.touchType !== "stylus" && !((t.radiusX || 0) > PALM_RADIUS)) out.push(t);
  }
  return out;
}

/* A hand writing is not a hand pinching: the Pencil on the glass, a stroke
   under way, or the nib only just lifted (`pen-writing`, `annotate.js`'s own
   latch), and anything else touching is the palm under it. */
function writing(ev) {
  for (var i = 0; i < ev.touches.length; i++) {
    if (ev.touches[i].touchType === "stylus") return true;
  }
  return (window.Annotate && window.Annotate.busy && window.Annotate.busy())
    || document.body.classList.contains("pen-writing");
}

function spread(a, b) {
  return {
    d: Math.max(1, Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY)),
    x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2,
  };
}

function make(opts) {
  var el = opts.scroller;
  var surface = opts.surface || null;
  var bar = opts.bar || null;
  var chip = opts.chip || null;
  var open = opts.open || function () { return true; };
  var PAGE = opts.page || ".lib-page";
  var zoom = 1;
  var pinch = null;

  el.classList.add("zoomable");

  /* Where on which page a point on the glass is, as fractions of that page,
     so it can be found again after the pages are laid out at another width. */
  function pointAt(x, y) {
    var pages = el.querySelectorAll(PAGE);
    var best = null, gap = Infinity;
    for (var i = 0; i < pages.length; i++) {
      var r = pages[i].getBoundingClientRect();
      var d = y < r.top ? r.top - y : (y > r.bottom ? y - r.bottom : 0);
      if (d < gap) { gap = d; best = { el: pages[i], r: r }; }
      if (!d) break;
    }
    if (!best || !best.r.width || !best.r.height) return null;
    return { el: best.el, fx: (x - best.r.left) / best.r.width,
             fy: (y - best.r.top) / best.r.height };
  }

  /* The zoom, committed; `at` is a page point to put back under (x, y). */
  function set(z, at, x, y) {
    zoom = clamp(z);
    el.style.setProperty("--zoom", String(zoom));
    if (at && at.el.isConnected) {
      var r = at.el.getBoundingClientRect();
      el.scrollLeft += r.left + at.fx * r.width - x;
      el.scrollTop += r.top + at.fy * r.height - y;
    }
    /* THE COMMIT REPAINTS. Every page has just been laid out at a new width,
       and each ink layer is measured against its page: laid out again and
       repainted here, once, rather than left to a resize observer to find. */
    if (window.Annotate && window.Annotate.redrawAll) window.Annotate.redrawAll();
    if (chip) {
      chip.hidden = Math.abs(zoom - 1) < 0.02;
      chip.textContent = Math.round(zoom * 100) + "%";
    }
    if (opts.committed) opts.committed(zoom);
  }

  function frame(ev) {
    var f = fingers(ev);
    if (f.length < 2) return;
    var now = spread(f[0], f[1]);
    pinch.now = now;
    /* Not a pinch until the pair moves: a fingertip resting beside a tap
       on a bar button changes nothing on the glass. */
    if (!pinch.moved) {
      if (Math.abs(now.d - pinch.d0) <= PINCH_SLOP
          && Math.hypot(now.x - pinch.x, now.y - pinch.y) <= SCROLL_SLOP) return;
      pinch.moved = true;
    }
    pinch.z = clamp(pinch.z0 * now.d / pinch.d0);
    var s = pinch.z / pinch.z0;
    /* The point first under the fingers follows them, whether or not the
       browser also scrolled the pages under them: `dx`/`dy` is that scroll. */
    var dx = el.scrollLeft - pinch.sl, dy = el.scrollTop - pinch.st;
    var tx = now.x - pinch.x + s * dx, ty = now.y - pinch.y + s * dy;
    el.style.transform = "translate(" + tx + "px," + ty + "px) scale(" + s + ")";
  }

  function end() {
    var p = pinch;
    pinch = null;
    el.style.transform = "";
    el.style.transformOrigin = "";
    el.classList.remove("pinching");
    if (p.moved) set(p.z, p.at, p.now.x, p.now.y);
  }

  /* THE GUARD: a non-passive move, armed for one gesture. `from` is where a
     lone first finger landed, so the guard can stand down once it is
     plainly a scroll, and null once a second contact has joined. `scrolled`
     says it stood down that way, and `firstAt` when the gesture began. */
  var guarded = false;
  var from = null;
  var scrolled = false;
  var firstAt = 0;
  /* Nothing on the glass: the next touch begins a gesture. */
  var idle = true;
  var CAPTURE = { capture: true, passive: false };
  /* The two contacts on the glass: where each was when they became two, and
     whether their moves are refused (`refusing`). `own` is two fingertips
     on the document, refused from the touch that made them. */
  var pair = null;
  /* A control whose touch was cancelled, owed its click if it is a tap. */
  var tap = null;
  /* This gesture began on a page Safari has magnified, and is Safari's. */
  var aside = false;
  /* Cancelled moves of this gesture already written down. */
  var movesSaid = 0;

  /* Cancelled, and written down whether the cancel could take. A move is
     written down once per gesture, and again only when it could not be
     cancelled, so a pinch is a line or two and not one per frame. */
  function refuse(ev, why) {
    var could = !!ev.cancelable;
    if (could) ev.preventDefault();
    if (ev.type === "touchmove") {
      if (movesSaid && (could || movesSaid > 4)) return;
      movesSaid++;
    }
    trace("zoom-refuse", { on: ev.type, why: why, cancelable: could,
                           prevented: !!ev.defaultPrevented, touches: ev.touches.length });
  }

  function arm(t) {
    from = t ? { x: t.clientX, y: t.clientY } : null;
    if (guarded) return;
    guarded = true;
    document.addEventListener("touchmove", guard, CAPTURE);
  }

  function disarm() {
    from = null;
    if (!guarded) return;
    guarded = false;
    document.removeEventListener("touchmove", guard, CAPTURE);
  }

  /* Over the document's own surface, not an overlay above it: every
     contact's target is in the reader -- its scroller, its bar, or anything
     else in `surface` -- and in no overlay. */
  function ours(at) {
    if (!at || (at.closest && at.closest(OVERLAY))) return false;
    return el.contains(at) || !!(bar && bar.contains(at))
      || !!(surface && surface.contains(at));
  }
  function onSurface(ev, c) {
    for (var i = 0; i < c.length; i++) {
      if (!ours(c[i].t.target && c[i].t.target.nodeType ? c[i].t.target : ev.target)) return false;
    }
    return true;
  }

  /* The pair is two fingertips if there are two, else the first two contacts. */
  function pairUp(c) {
    var wide = function (t) { return (t.radiusX || 0) > PALM_RADIUS; };
    var tips = c.filter(function (x) { return !wide(x.t); });
    var two = tips.length >= 2 ? tips : c;
    var a = two[0], b = two[1];
    pair = {
      refusing: !!(pair && pair.refusing),
      a: { k: a.k, x: a.t.clientX, y: a.t.clientY, palm: wide(a.t) },
      b: { k: b.k, x: b.t.clientX, y: b.t.clientY, palm: wide(b.t) },
      d0: apart(a.t, b.t),
    };
    pair.own = false;
    pair.palm = pair.a.palm || pair.b.palm;
  }

  /* A pair is pinching once its gap has changed by more than PINCH_SLOP --
     a stable gap is a two-finger scroll, which is not Safari's zoom.
     WITH A PALM IN THE PAIR, THE PALM MUST BE DOING IT. A finger scrolling
     beside a resting palm changes the gap as much as a pinch does, and with
     the pen off that finger scrolls natively, which refusing its moves
     would stop. What tells the two apart is the wide contact
     itself: a resting palm stays put, while a flat thumb in a wide shut
     sweeps toward the fingertip. So the palm's own move must account for at
     least half the slop of the change, in the same sense -- closing in a
     shut, opening in a spread -- whether or not the fingertip moves. A palm
     drifting sideways as the hand scrolls changes the gap by almost nothing
     on its own, and is not a pinch. */
  function pinching(ev) {
    var a = find(ev, pair.a.k), b = find(ev, pair.b.k);
    if (!a || !b) return false;
    var change = apart(a, b) - pair.d0;
    if (Math.abs(change) <= PINCH_SLOP) return false;
    if (!pair.palm) return true;
    var aAt = { clientX: pair.a.x, clientY: pair.a.y };
    var bAt = { clientX: pair.b.x, clientY: pair.b.y };
    /* The change each contact makes moving alone, the other held where it
       was when the two became a pair. */
    var byA = apart(a, bAt) - pair.d0, byB = apart(aAt, b) - pair.d0;
    function sweeps(by) { return by * change > 0 && Math.abs(by) > PINCH_SLOP / 2; }
    return (pair.a.palm && sweeps(byA)) || (pair.b.palm && sweeps(byB));
  }

  /* Still a tap: the control's contact has not moved, and the pair has not
     changed its gap. */
  function stillTap(ev) {
    var t = find(ev, tap.k);
    if (t && apart(t, tap) > SCROLL_SLOP) return false;
    if (pair) {
      var a = find(ev, pair.a.k), b = find(ev, pair.b.k);
      if (a && b && Math.abs(apart(a, b) - pair.d0) > PINCH_SLOP) return false;
    }
    return true;
  }

  function guard(ev) {
    if (tap && !stillTap(ev)) tap = null;
    if (contacts(ev).length >= 2) {
      if (pinch) {
        refuse(ev, "pinch");
        frame(ev);
      } else if (pair && (pair.refusing || (pair.refusing = pinching(ev)))) {
        refuse(ev, pair.own ? "own" : "pinching");
      }
      return;
    }
    if (!pinch && from && ev.touches.length === 1) {
      var t = ev.touches[0];
      if (Math.hypot(t.clientX - from.x, t.clientY - from.y) > SCROLL_SLOP) {
        scrolled = true;
        disarm();
      }
    }
  }

  /* Two contacts landing: what they were, and whether the cancel took. */
  function say(ev, built) {
    var r = [];
    for (var i = 0; i < ev.touches.length; i++) r.push(Math.round(ev.touches[i].radiusX || 0));
    trace("zoom-start", {
      touches: ev.touches.length, radii: r.join(","), cancelable: !!ev.cancelable,
      prevented: !!ev.defaultPrevented,
      target: ev.target ? String(ev.target.id || ev.target.className || ev.target.nodeName) : "",
      pinch: !!built, own: !!(pair && pair.own),
    });
  }

  /* The page's magnification, put back if Safari has any. `why` is "open"
     for a document opening, which blurs a focused field to do it; anything
     later leaves a field being typed in alone until it lets go. */
  function level(why) {
    var k = pageScale();
    if (!(k > PAGE_ZOOMED) || (why !== "open" && editing())) return;
    var can = !!(window.Recentre && window.Recentre.unzoom);
    trace("page-zoom", { scale: Math.round(k * 100) / 100, why: why, reset: can });
    if (can) window.Recentre.unzoom();
  }
  function rescaled() { level("scale"); }
  function unfocused() { setTimeout(function () { if (listening) level("blur"); }, 0); }

  /* The contact this touchstart is for: the changed touch, or the newest. */
  function newest(ev, c) {
    var ch = ev.changedTouches && ev.changedTouches[0];
    if (ch) {
      for (var i = 0; i < c.length; i++) if (c[i].t === ch) return c[i];
      if (ch.identifier !== undefined) {
        for (var j = 0; j < c.length; j++) if (c[j].k === "id" + ch.identifier) return c[j];
      }
    }
    return c[c.length - 1];
  }

  function land(ev) {
    var c = contacts(ev);
    var f = fingers(ev);
    /* A pinch whose fingers are all gone without a lift reaching here is
       committed now, so a finger landing on its own scrolls. */
    if (pinch && ev.touches.length < 2) end();
    /* One touch on the glass is a gesture beginning: the guard goes on now,
       because by the time a second finger lands it is too late to add it. */
    if (idle || ev.touches.length === 1) {
      idle = false;
      pair = null;
      tap = null;
      scrolled = false;
      movesSaid = 0;
      firstAt = ev.timeStamp || 0;
      aside = pageScale() > PAGE_ZOOMED;
      if (aside) {
        trace("zoom-aside", { scale: Math.round(pageScale() * 100) / 100 });
        level("touch");
      }
    }
    /* A magnified page's gesture is Safari's, to pinch the page back out. */
    if (aside) { palm(ev, f); return; }
    if (ev.touches.length === 1) arm(ev.touches[0]);
    if (pinch) {
      /* Anything landing on a live pinch is the pinch's: a third finger, a
         palm. The Pencil ends it, and is still refused to the browser. */
      refuse(ev, "joins");
      tap = null;
      if (writing(ev)) end();
      return;
    }
    if (c.length >= 2) {
      arm(null);
      var own = f.length >= 2 && onSurface(ev, c);
      pairUp(c);
      if (own) pair.own = pair.refusing = true;
      tap = null;
      var built = false;
      if (own) {
        /* Cancelled whatever it landed on: a second finger on a bar button
           is the commonest way a shut starts. The click that cancels is
           given back in `done` if the touch turns out to be a tap. */
        if (ev.cancelable) ev.preventDefault();
        var hit = ev.target && ev.target.closest && ev.target.closest(CONTROL);
        if (hit && c.length === 2) {
          var n = newest(ev, c);
          tap = { el: hit, k: n.k, clientX: n.t.clientX, clientY: n.t.clientY };
        }
        built = !writing(ev) && (!scrolled || (ev.timeStamp || 0) - firstAt <= PAIR_MS);
      }
      if (built) {
        var s = spread(f[0], f[1]);
        var box = el.getBoundingClientRect();
        pinch = { d0: s.d, x: s.x, y: s.y, now: s, z0: zoom, z: zoom, moved: false,
                  sl: el.scrollLeft, st: el.scrollTop, at: pointAt(s.x, s.y) };
        el.style.transformOrigin = (s.x - box.left) + "px " + (s.y - box.top) + "px";
        el.classList.add("pinching");
      }
      say(ev, built);
      if (own) return;
    }
    palm(ev, f);
  }

  /* The palm: with the pen on, a contact wider than a fingertip, or anything
     landing beside a nib that is down or only just lifted, moves nothing. A
     fingertip on its own is a scroll. */
  function palm(ev, f) {
    if (!el.contains(ev.target)) return;
    if (penIsOn() && (writing(ev) || !f.length)) refuse(ev, "palm");
  }

  /* A control's contact lifting is a tap if every move on the way kept it
     one (`stillTap`), however long it was held. */
  function done(ev) {
    var owed = null;
    if (tap && !find(ev, tap.k)) {
      owed = tap.el;
      tap = null;
    }
    if (pinch && fingers(ev).length < 2) end();
    if (contacts(ev).length < 2) pair = null;
    if (!ev.touches.length) { idle = true; disarm(); }
    /* The tap a cancelled touchstart cost. Cancelling this touchend as well
       means iOS cannot also send its own, so the control clicks once. */
    if (owed) {
      if (ev.cancelable) ev.preventDefault();
      owed.click();
    }
  }
  /* A cancel is the system taking the gesture: the pinch ends with it,
     whatever the event says is still on the glass, and nothing is a tap. */
  function cancelled(ev) {
    tap = null;
    if (pinch) end();
    if (contacts(ev).length < 2) pair = null;
    if (!ev.touches.length) { idle = true; disarm(); }
  }

  /* LISTENING ONLY WHILE A DOCUMENT IS OPEN. A non-passive touchstart on the
     document makes every gesture on the page start on the main thread, which
     the lesson under a shut panel has no reason to pay. */
  var listening = false;
  function live(on) {
    on = !!on;
    if (on === listening) { if (on) level("open"); return; }
    listening = on;
    var vv = window.visualViewport;
    if (on) {
      document.addEventListener("touchstart", land, CAPTURE);
      document.addEventListener("touchend", done, CAPTURE);
      document.addEventListener("touchcancel", cancelled, true);
      document.addEventListener("focusout", unfocused, true);
      if (vv) vv.addEventListener("resize", rescaled);
      level("open");
    } else {
      document.removeEventListener("touchstart", land, CAPTURE);
      document.removeEventListener("touchend", done, CAPTURE);
      document.removeEventListener("touchcancel", cancelled, true);
      document.removeEventListener("focusout", unfocused, true);
      if (vv) vv.removeEventListener("resize", rescaled);
      disarm();
      idle = true;
      pair = null;
      tap = null;
      aside = false;
      if (pinch) end();
    }
  }

  /* Safari's own pinch, refused while a document is open: two zooms at once is
     the page scaling under a reader that is also re-laying it out. */
  ["gesturestart", "gesturechange", "gestureend"].forEach(function (name) {
    document.addEventListener(name, function (ev) {
      if (open() && !aside && ev.cancelable) ev.preventDefault();
    }, { passive: false });
  });

  if (chip) {
    chip.onclick = function () {
      var box = el.getBoundingClientRect();
      var x = box.left + box.width / 2, y = box.top + box.height / 2;
      set(1, pointAt(x, y), x, y);
    };
  }

  if (!opts.open) live(true);

  return { set: function (z) { set(z); }, zoom: function () { return zoom; }, live: live };
}

window.ReaderZoom = { make: make, trace: function () { return traced.slice(); } };
})();
