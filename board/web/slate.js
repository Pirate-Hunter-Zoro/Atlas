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

/* A NOTES CANVAS is a session whose view is `slate`: this page is the whole
   of it. Its title, and End after a second tap within four seconds, which
   ends the session and queues the turn that transcribes these pages into
   notes.md (`runner.service._notes`). What is owed to the disk goes first.
   Bound to nothing, the second tap asks where the notes go first. */
var endBtn = document.getElementById("notes-end");
var endArmed = null;
var notesState = {};

function paintNotes(state) {
  notesState = state;
  var name = document.getElementById("notes-name");
  name.textContent = state.title || "Notes";
  name.hidden = false;
  endBtn.hidden = false;
  if (state.ended) {
    endBtn.disabled = true;
    endBtn.textContent = "ended";
  }
}

function endNotes() {
  if (!endArmed) {
    endBtn.textContent = "tap again to end";
    endBtn.classList.add("armed");
    endArmed = setTimeout(function () {
      endArmed = null;
      endBtn.textContent = "End";
      endBtn.classList.remove("armed");
    }, 4000);
    return;
  }
  clearTimeout(endArmed);
  endArmed = null;
  endBtn.classList.remove("armed");
  if (sendPanel && Object.prototype.hasOwnProperty.call(notesState, "subject")
      && !notesState.subject) {
    endBtn.textContent = "End";
    openSend();
    return;
  }
  finishEnd({});
}

/* POST /end with `body`, once the pages are on disk. Refused, the canvas
   stays open and says why. */
function finishEnd(body) {
  endBtn.disabled = true;
  endBtn.textContent = "ending…";
  var settle = writer && writer.flush ? writer.flush() : null;
  Promise.resolve(settle).catch(function () {}).then(function () {
    return fetch(BASE + "/end", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
    });
  }).then(function (r) { return r.json(); }).then(function (got) {
    if (!got || !got.ok) throw new Error((got && got.error) || "not ended");
    if (sendPanel) sendPanel.hidden = true;
    endBtn.textContent = "ended: the tutor is transcribing it into notes.md"
      + (got.sent ? " in " + got.sent.name : "");
  }).catch(function (e) {
    var why = (e && e.message) || "the board did not answer";
    endBtn.disabled = false;
    endBtn.textContent = "End (" + why + ")";
    if (sendPanel && !sendPanel.hidden) sendSaid("Not ended: " + why);
  });
}
if (endBtn) endBtn.onclick = endNotes;

/* WHERE THE NOTES GO, for a canvas bound to nothing: every course and
   project from /subjects.json, and a new one (a project says whether it holds
   patient data). A tap ends the canvas into it; "let the tutor choose" ends
   it as it is, and the transcribing turn picks one (`prompts/notes.md`). */
var sendPanel = document.getElementById("notes-send");
var sendList = document.getElementById("notes-send-list");
var sendForm = document.getElementById("notes-send-form");
var sendName = document.getElementById("notes-send-name");
var sendPhi = document.getElementById("notes-send-phi");
var sendMaking = null;
var sendMakingPhi = null;

function sendSaid(text) { document.getElementById("notes-send-said").textContent = text || ""; }

function openSend() {
  sendMaking = null;
  sendMakingPhi = null;
  sendForm.hidden = true;
  sendSaid("");
  sendList.textContent = "";
  sendPanel.hidden = false;
  fetch("/subjects.json", { credentials: "same-origin" }).then(function (r) {
    return r.json();
  }).then(function (got) {
    var list = (got && got.subjects) || [];
    [["course", "Courses"], ["project", "Projects"]].forEach(function (g) {
      var some = list.filter(function (one) { return one.kind === g[0]; });
      if (!some.length) return;
      var head = document.createElement("div");
      head.className = "notes-send-group";
      head.textContent = g[1];
      sendList.appendChild(head);
      some.forEach(function (one) {
        var b = document.createElement("button");
        b.type = "button";
        b.textContent = one.name || one.slug || one.id;
        b.dataset.subject = one.id;
        b.onclick = function () { sendSaid("sending…"); finishEnd({ subject: one.id }); };
        sendList.appendChild(b);
      });
    });
    if (!sendList.firstChild) sendSaid("No courses or projects yet: make one below.");
  }, function () { sendSaid("The list of courses and projects did not come."); });
}

function startSendMaking(kind) {
  sendMaking = kind;
  sendMakingPhi = null;
  sendForm.hidden = false;
  sendPhi.hidden = kind !== "project";
  Array.prototype.forEach.call(sendPhi.querySelectorAll("button"),
                               function (b) { b.classList.remove("on"); });
  sendName.placeholder = kind === "project" ? "the project's name" : "the course's name";
  sendSaid("");
}

if (sendPanel) {
  document.getElementById("notes-new-course").onclick = function () { startSendMaking("course"); };
  document.getElementById("notes-new-project").onclick = function () { startSendMaking("project"); };
  ["no", "yes"].forEach(function (word) {
    var b = document.getElementById("notes-phi-" + word);
    b.onclick = function () {
      sendMakingPhi = word === "yes";
      Array.prototype.forEach.call(sendPhi.querySelectorAll("button"),
                                   function (x) { x.classList.toggle("on", x === b); });
    };
  });
  document.getElementById("notes-send-go").onclick = function () {
    var name = (sendName.value || "").trim();
    if (!sendMaking) return;
    if (!name) { sendSaid("Name it first."); return; }
    if (sendMaking === "project" && sendMakingPhi === null) {
      sendSaid("Say whether it holds patient data."); return;
    }
    var body = { kind: sendMaking, name: name };
    if (sendMaking === "project") body.phi = sendMakingPhi;
    sendSaid("making " + name + "…");
    fetch("/subjects/new", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
    }).then(function (r) { return r.json(); }).then(function (got) {
      if (!got || !got.ok) { sendSaid((got && got.error) || "Not made."); return; }
      sendName.value = "";
      finishEnd({ subject: got.subject.id });
    }, function () { sendSaid("Not made: the board did not answer."); });
  };
  document.getElementById("notes-send-skip").onclick = function () { finishEnd({}); };
  document.getElementById("notes-send-back").onclick = function () { sendPanel.hidden = true; };
}

/* Show which question is being answered, so the full-screen view is not
   context-free. A notes canvas answers none: it shows its title and End. */
fetch(BASE + "/board.json").then(function (r) { return r.json(); }).then(function (d) {
  var state = d.state || {};
  if (state.view === "slate") { paintNotes(state); return; }
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
