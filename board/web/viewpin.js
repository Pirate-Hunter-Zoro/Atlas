/* ==========================================================================
   viewpin.js -- a bar that stays on the glass while the page is pinched.

   `position: fixed` follows the layout viewport, and a pinch moves only the
   visual one, so a zoomed reader would lose its bars (and every way to finish
   marking or send). A pinned bar, while zoomed, is placed over the visual
   viewport and scaled down by the zoom; at no zoom its inline styles are
   cleared. The same problem for single buttons is `recentre.js`.
   ========================================================================== */

(function () {
"use strict";

var PROPS = ["position", "left", "top", "right", "bottom", "width", "margin",
             "transform", "transformOrigin", "zIndex"];
var GAP = 8;
var pins = [];

function vv() { return window.visualViewport || null; }

function unpin(p) {
  PROPS.forEach(function (k) { p.el.style[k] = ""; });
  if (p.spacer) p.spacer.style.paddingTop = "";
  p.on = false;
}

function place(p) {
  var v = vv();
  var s = v ? v.scale : 1;
  if (!v || !(s > 1.02) || p.el.hidden || !p.el.isConnected) {
    if (p.on) unpin(p);
    return;
  }
  var st = p.el.style;
  if (!p.on) {
    /* The bar leaves the flow when it is pinned, and what was under it would
       jump up by its height -- under a hand that is zoomed in on it. */
    if (p.spacer) p.spacer.style.paddingTop = p.el.offsetHeight + "px";
    p.on = true;
  }
  var k = 1 / s;
  st.position = "fixed";
  st.margin = "0";
  st.right = "auto";
  st.bottom = "auto";
  if (p.z) st.zIndex = p.z;
  if (p.edge === "top") {
    st.left = v.offsetLeft + "px";
    st.top = v.offsetTop + "px";
    /* Laid out at the width it will fill once scaled down to the glass. */
    st.width = (v.width * s) + "px";
    st.transformOrigin = "0 0";
    st.transform = "scale(" + k + ")";
  } else {
    st.left = (v.offsetLeft + v.width / 2) + "px";
    st.top = (v.offsetTop + v.height - GAP * k) + "px";
    st.transformOrigin = "50% 100%";
    st.transform = "translate(-50%, -100%) scale(" + k + ")";
  }
}

var queued = false;
function update() {
  if (queued) return;
  queued = true;
  var run = function () { queued = false; pins.forEach(place); };
  if (window.requestAnimationFrame) window.requestAnimationFrame(run);
  else setTimeout(run, 0);
}

function pin(el, opts) {
  if (!el) return;
  opts = opts || {};
  pins.push({ el: el, edge: opts.edge === "bottom" ? "bottom" : "top",
              spacer: opts.spacer || null, z: opts.z || "", on: false });
  update();
}

var v0 = vv();
if (v0) {
  v0.addEventListener("resize", update);
  v0.addEventListener("scroll", update);
}
window.addEventListener("orientationchange", update);

window.ViewPin = { pin: pin, update: update };
})();
