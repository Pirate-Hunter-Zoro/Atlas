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

   The library reader and the meeting deck both use it:
     ReaderZoom.make({ scroller, chip, open(), committed() }) -> { set(z) }
   ========================================================================== */

(function () {
"use strict";

var ZOOM_MIN = 0.5;
var ZOOM_MAX = 3;           /* the pages are drawn 1240 px wide; past this, blur */
/* A contact wider than a fingertip is the side of a hand. */
var PALM_RADIUS = 40;

function clamp(z) { return Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, z)); }

function penIsOn() { return !!(window.Annotate && window.Annotate.isOn()); }

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
  var chip = opts.chip || null;
  var open = opts.open || function () { return true; };
  var zoom = 1;
  var pinch = null;

  el.classList.add("zoomable");

  /* Where on which page a point on the glass is, as fractions of that page,
     so it can be found again after the pages are laid out at another width. */
  function pointAt(x, y) {
    var pages = el.querySelectorAll(".lib-page");
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
    set(p.z, p.at, p.now.x, p.now.y);
  }

  el.addEventListener("touchstart", function (ev) {
    var f = fingers(ev);
    if (pinch && writing(ev)) { end(); return; }
    if (f.length >= 2 && !pinch && !writing(ev)) {
      var s = spread(f[0], f[1]);
      var box = el.getBoundingClientRect();
      pinch = { d0: s.d, x: s.x, y: s.y, now: s, z0: zoom, z: zoom,
                sl: el.scrollLeft, st: el.scrollTop, at: pointAt(s.x, s.y) };
      el.style.transformOrigin = (s.x - box.left) + "px " + (s.y - box.top) + "px";
      el.classList.add("pinching");
      return;
    }
    /* The palm: with the pen on, a contact wider than a fingertip, or anything
       landing beside a nib that is down or only just lifted, moves nothing. A
       fingertip on its own is a scroll. */
    if (penIsOn() && ev.cancelable && (writing(ev) || !f.length))
      ev.preventDefault();
  }, { passive: false });

  el.addEventListener("touchmove", function (ev) {
    if (pinch) frame(ev);
  }, { passive: true });

  function done(ev) { if (pinch && fingers(ev).length < 2) end(); }
  el.addEventListener("touchend", done);
  el.addEventListener("touchcancel", done);

  /* Safari's own pinch, refused while a document is open: two zooms at once is
     the page scaling under a reader that is also re-laying it out. */
  ["gesturestart", "gesturechange"].forEach(function (name) {
    document.addEventListener(name, function (ev) {
      if (open() && ev.cancelable) ev.preventDefault();
    }, { passive: false });
  });

  if (chip) {
    chip.onclick = function () {
      var box = el.getBoundingClientRect();
      var x = box.left + box.width / 2, y = box.top + box.height / 2;
      set(1, pointAt(x, y), x, y);
    };
  }

  return { set: function (z) { set(z); }, zoom: function () { return zoom; } };
}

window.ReaderZoom = { make: make };
})();
