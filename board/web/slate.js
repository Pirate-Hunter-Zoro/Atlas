/* ==========================================================================
   slate.js -- the full-screen host for the writing surface.

   Everything that matters is in slate-core.js. This page exists for the times a
   derivation wants the whole screen; the usual place to write is the drawer
   under the question on the board, where you can still see what you are
   answering.
   ========================================================================== */

(function () {
"use strict";

/* The session this page is in: `/s/<id>/slate` reads and saves that session's
   pages, and its links go back to that session's board. Outside one the prefix
   is empty. */
function sessionBase() {
  var m = /^\/s\/[^\/]+/.exec(location.pathname || "");
  return m ? m[0] : "";
}
var BASE = sessionBase();
if (BASE) {
  Array.prototype.forEach.call(document.querySelectorAll('a[href^="/board"]'),
    function (a) { a.setAttribute("href", BASE + a.getAttribute("href")); });
}

var writer = window.Slate.create({ root: document.getElementById("slate"),
                                   compact: false,
                                   stateUrl: BASE + "/slate/state",
                                   saveUrl: BASE + "/slate/save",
                                   fullUrl: BASE + "/slate" });

/* Show which question is being answered, so the full-screen view is not
   context-free. */
fetch(BASE + "/board.json").then(function (r) { return r.json(); }).then(function (d) {
  var cards = d.cards || [];
  for (var i = cards.length - 1; i >= 0; i--) {
    if (cards[i].kind === "question") {
      var el = document.getElementById("prompt");
      el.querySelector(".kind").textContent = "answering";
      el.querySelector(".text").textContent = cards[i].title || ("card " + cards[i].id);
      el.hidden = false;
      return;
    }
  }
}).catch(function () {});

if ("serviceWorker" in navigator && window.isSecureContext) {
  var hadController = !!navigator.serviceWorker.controller, reloading = false;
  var updateWaiting = false;

  /* A RELOAD OF THIS PAGE IS A PAGE OF HANDWRITING AT RISK, so it waits until
     the surface owes the disk nothing and nobody is looking at it. The board
     has the same rule and the reason it is written up there: a reload taken
     unasked is a white screen in the middle of a proof. Here the stakes are
     higher, because what would be lost is ink. */
  function take() {
    if (reloading) return;
    try { if (writer && writer.owed && writer.owed()) return; } catch (e) {}
    reloading = true;
    location.reload();
  }
  navigator.serviceWorker.addEventListener("controllerchange", function () {
    if (!hadController || reloading) return;
    updateWaiting = true;
    if (document.hidden) take();
  });
  document.addEventListener("visibilitychange", function () {
    if (updateWaiting && document.hidden) take();
  });
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).then(function (reg) {
      function check() { if (!document.hidden) { try { reg.update(); } catch (e) {} } }
      document.addEventListener("visibilitychange", check);
      window.addEventListener("pageshow", check);
    }).catch(function () {});
  });
}
})();
