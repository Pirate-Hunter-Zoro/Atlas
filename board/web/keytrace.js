/* ==========================================================================
   keytrace.js -- TEMPORARY. What a focused text box actually receives.

   Reported from the device: a text box shows its cursor and the Paste menu,
   but no keyboard appears and a paired keyboard types nothing -- in the
   library's note and in a sitting's typed answer alike. Nothing in the page's
   code cancels a key, so this shows, on the glass, every focus, key and input
   event and whether anything cancelled it. Remove once the cause is known.
   ========================================================================== */

(function () {
"use strict";

var box = null, lines = [];

function show() {
  if (!box) {
    box = document.createElement("pre");
    box.id = "keytrace";
    box.style.cssText = "position:fixed;left:6px;bottom:6px;z-index:2147483647;"
      + "max-width:46vw;max-height:40vh;overflow:hidden;margin:0;padding:6px 8px;"
      + "font:11px/1.35 ui-monospace,Menlo,monospace;letter-spacing:0;"
      + "background:rgba(0,0,0,.85);color:#9fe39f;border-radius:6px;"
      + "pointer-events:none;white-space:pre-wrap;";
    document.body.appendChild(box);
  }
  box.textContent = "KEY TRACE (temporary)\n" + state() + "\n" + lines.join("\n");
}

function name(el) {
  if (!el || !el.tagName) return String(el);
  return el.tagName.toLowerCase() + (el.id ? "#" + el.id : "");
}

function state() {
  var a = document.activeElement;
  if (!a) return "active: none";
  var cs = window.getComputedStyle ? getComputedStyle(a) : {};
  return "active: " + name(a)
    + " ro=" + !!a.readOnly + " dis=" + !!a.disabled
    + " sel=" + (cs.webkitUserSelect || cs.userSelect || "?")
    + " mod=" + (cs.webkitUserModify || "?")
    + " im=" + (a.getAttribute && a.getAttribute("inputmode") || "-");
}

function log(text) {
  lines.push(text);
  if (lines.length > 12) lines.shift();
  show();
}

function typing(el) {
  return el && (el.tagName === "TEXTAREA" || el.tagName === "INPUT"
                || el.isContentEditable);
}

["focusin", "focusout"].forEach(function (t) {
  window.addEventListener(t, function (e) {
    if (typing(e.target)) log(t + " " + name(e.target));
  }, true);
});

["keydown", "keyup", "beforeinput", "input", "compositionstart",
 "compositionend", "paste"].forEach(function (t) {
  window.addEventListener(t, function (e) {
    var what = t + (e.key ? " key=" + e.key : "")
      + (e.inputType ? " type=" + e.inputType : "")
      + " on " + name(e.target);
    /* Read after every other listener has run, so a cancel anywhere shows. */
    setTimeout(function () {
      log(what + (e.defaultPrevented ? "  CANCELLED" : "")
          + (t === "input" && "value" in e.target
             ? " len=" + e.target.value.length : ""));
    }, 0);
  }, true);
});

/* A tap that lands on a text box, and whether the touch was cancelled. */
["touchstart", "pointerdown"].forEach(function (t) {
  window.addEventListener(t, function (e) {
    if (!typing(e.target)) return;
    setTimeout(function () {
      log(t + " on " + name(e.target) + (e.defaultPrevented ? "  CANCELLED" : ""));
    }, 0);
  }, true);
});
})();
