/* ==========================================================================
   typeface.js -- pick the reading face and the theme, and remember both.

   Shared by every page so the choice follows you from the hub to the lesson to
   the slate. Runs before anything else on the page, so there is no flash of the
   wrong face while the rest of the script boots.

   THE THEME IS ONE FUNCTION, `Typeface.theme(mode)`: "auto", "light" or
   "dark" sets `body[data-mode]` and remembers it under `board.theme`; "next"
   steps through the three; no argument re-applies what is remembered. `sys-dark`
   on the body follows the system while the mode is auto (`syncSystemTheme`,
   the only one). Every page's sheet reads those two and nothing else.
   ========================================================================== */

(function () {
"use strict";

var KEY = "board.face";
var ORDER = ["dyslexic", "hyperlegible", "serif"];
var LABEL = { dyslexic: "OpenDyslexic", hyperlegible: "Hyperlegible", serif: "Serif" };

function apply(face) {
  if (ORDER.indexOf(face) === -1) face = ORDER[0];
  document.body.dataset.face = face;
  try { localStorage.setItem(KEY, face); } catch (e) {}
  var btn = document.getElementById("btn-face");
  if (btn) btn.title = "typeface: " + LABEL[face] + " — tap to change";
  return face;
}

function current() {
  try {
    return localStorage.getItem(KEY) || ORDER[0];
  } catch (e) {
    return ORDER[0];
  }
}

var THEME_KEY = "board.theme";
var THEMES = ["auto", "light", "dark"];

function syncSystemTheme() {
  if (!document.body) return;
  var dark = false;
  try {
    dark = !!(window.matchMedia
              && window.matchMedia("(prefers-color-scheme: dark)").matches);
  } catch (e) { dark = false; }
  document.body.classList.toggle("sys-dark", dark);
}

function remembered() {
  try {
    var got = localStorage.getItem(THEME_KEY);
    return THEMES.indexOf(got) === -1 ? "auto" : got;
  } catch (e) {
    return "auto";
  }
}

function theme(mode) {
  if (!document.body) return remembered();
  if (mode === "next") {
    var at = THEMES.indexOf(document.body.dataset.mode);
    mode = THEMES[(at + 1) % THEMES.length];
  }
  if (THEMES.indexOf(mode) === -1) {
    mode = remembered();
  } else {
    try { localStorage.setItem(THEME_KEY, mode); } catch (e) {}
  }
  document.body.dataset.mode = mode;
  syncSystemTheme();
  return mode;
}

var watching = false;
function watchSystem() {
  if (watching || !window.matchMedia) return;
  watching = true;
  try {
    var q = window.matchMedia("(prefers-color-scheme: dark)");
    if (q.addEventListener) q.addEventListener("change", syncSystemTheme);
    else if (q.addListener) q.addListener(syncSystemTheme);
  } catch (e) { /* the state at load is still right */ }
}

window.BoardTypeface = {
  init: function () {
    var face = apply(current());
    var btn = document.getElementById("btn-face");
    if (btn) {
      btn.onclick = function () {
        apply(ORDER[(ORDER.indexOf(document.body.dataset.face) + 1) % ORDER.length]);
      };
    }
    theme();
    watchSystem();
    return face;
  },
};
window.Typeface = { theme: theme };

/* The body may not exist yet depending on where this is included. */
if (document.body) window.BoardTypeface.init();
else document.addEventListener("DOMContentLoaded", function () { window.BoardTypeface.init(); });
})();
