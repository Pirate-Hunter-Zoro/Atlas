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

/* A CANVAS is a session whose view is `slate`: this page is the whole of it,
   written on with no tutor. It never sends (`writer.sendable(false)`); it is
   filed with "Save to…", handed over whole with "Give to the tutor", kept as
   a PDF or a PNG from the menu, and ended in one of three ways. What is owed
   to the disk goes first, every time. */
var endBtn = document.getElementById("notes-end");
var saveBtn = document.getElementById("canvas-save");
var giveBtn = document.getElementById("canvas-give");
var endPanel = document.getElementById("canvas-end");
var notesState = {};
var subjectName = "";

function getJson(url) {
  return fetch(url, { credentials: "same-origin" }).then(function (r) { return r.json(); });
}

function postJson(url, body) {
  return fetch(url, {
    method: "POST", credentials: "same-origin",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {})
  }).then(function (r) { return r.json(); });
}

/* Every page's picture on disk before anything reads the pages: the last
   page of an evening is the one whose picture is still waiting for a gap. */
function settled() {
  var settle = writer && writer.flush ? writer.flush() : null;
  return Promise.resolve(settle).catch(function () {});
}

function paintNotes(state) {
  notesState = state;
  var name = document.getElementById("notes-name");
  name.textContent = state.title || "Canvas";
  name.hidden = false;
  if (writer.sendable) writer.sendable(false);
  if (writer.canvasMenu && BASE) writer.canvasMenu(BASE + "/canvas.pdf");
  endBtn.hidden = false;
  giveBtn.hidden = false;
  saveBtn.hidden = !!state.ended;
  paintSave();
  if (state.ended) {
    endBtn.disabled = true;
    endBtn.textContent = "ended";
  }
}

function paintSave() {
  var bound = notesState.subject;
  saveBtn.textContent = bound ? "in " + (subjectName || bound) : "Save to…";
  saveBtn.title = bound ? "filed in " + (subjectName || bound) + "; tap to move it"
                        : "file these pages in a course or project; the canvas stays open";
}

/* GIVE TO THE TUTOR, after a second tap within four seconds: one turn reads
   every page (POST /give, which reopens an ended canvas), and the board it
   is taught on opens. */
var giveArmed = null;
var giving = false;
function giveCanvas() {
  if (giving) return;
  if (!giveArmed) {
    giveBtn.textContent = "tap again to give it";
    giveBtn.classList.add("armed");
    giveArmed = setTimeout(function () {
      giveArmed = null;
      giveBtn.textContent = "Give to the tutor";
      giveBtn.classList.remove("armed");
    }, 4000);
    return;
  }
  clearTimeout(giveArmed);
  giveArmed = null;
  giveBtn.classList.remove("armed");
  giving = true;
  giveBtn.disabled = true;
  giveBtn.textContent = "giving…";
  settled().then(function () {
    return postJson(BASE + "/give", {});
  }).then(function (got) {
    if (!got || !got.ok) throw new Error((got && got.error) || "not given");
    giveBtn.textContent = "given";
    go(got.url || BASE + "/board");
  }).catch(function (e) {
    giving = false;
    giveBtn.disabled = false;
    giveBtn.textContent = "Give to the tutor (" + ((e && e.message) || "the board did not answer") + ")";
  });
}
function go(url) { window.location.href = url; }

/* END: the three ways a canvas ends. Bound, "End, keep the pages" and "End
   and transcribe" end it at once; bound to nothing, each first asks where
   the pages go. "Keep it unfiled" is offered only while it is bound to
   nothing. */
function openEnd() {
  if (ending) return;
  if (sendPanel) sendPanel.hidden = true;
  document.getElementById("canvas-end-unfiled").hidden = !!notesState.subject;
  endPanel.hidden = false;
}

function endAs(how) {
  endPanel.hidden = true;
  if (how === "unfiled") { finishEnd({ transcribe: false }); return; }
  var transcribe = how === "transcribe";
  if (notesState.subject) { finishEnd({ transcribe: transcribe }); return; }
  openSend(transcribe ? "transcribe" : "keep");
}

/* POST /end with `body`, once the pages are on disk. Refused, the canvas
   stays open and says why. One at a time: a second tap while one is asked
   (a row tapped twice, or another row) does nothing. */
var ending = false;
function finishEnd(body) {
  if (ending) return;
  ending = true;
  endBtn.disabled = true;
  endBtn.textContent = "ending…";
  settled().then(function () {
    return postJson(BASE + "/end", body);
  }).then(function (got) {
    if (!got || !got.ok) throw new Error((got && got.error) || "not ended");
    if (sendPanel) sendPanel.hidden = true;
    var where = got.sent ? got.sent.name : subjectName || notesState.subject;
    saveBtn.hidden = true;
    endBtn.textContent = body.transcribe === false
      ? (where ? "ended: the pages are in " + where : "ended: the pages stay in this session")
      : "ended: the tutor is transcribing it into notes.md" + (where ? " in " + where : "");
  }).catch(function (e) {
    var why = (e && e.message) || "the board did not answer";
    ending = false;
    endBtn.disabled = false;
    endBtn.textContent = "End (" + why + ")";
    if (sendPanel && !sendPanel.hidden) sendSaid("Not ended: " + why);
  });
}

/* SAVE TO…: bind the canvas to a course or project (POST /bind), which files
   its pages there; it neither ends nor wakes anything. A move off a subject
   it has already filed pages in comes back `confirm`, and only a second tap
   on the same subject moves it. */
var bindArmed = null;
var binding = false;
function bindTo(id) {
  if (binding) return;
  var force = bindArmed === id;
  bindArmed = null;
  binding = true;
  sendSaid("saving…");
  settled().then(function () {
    return postJson(BASE + "/bind", { subject: id, force: force });
  }).then(function (got) {
    binding = false;
    if (got && got.confirm) {
      bindArmed = id;
      sendSaid(got.error + " Tap it again to move it.");
      return;
    }
    if (!got || !got.ok) { sendSaid((got && got.error) || "Not saved."); return; }
    notesState.subject = got.subject.id;
    subjectName = got.subject.name || got.subject.id;
    paintSave();
    sendPanel.hidden = true;
  }, function () { binding = false; sendSaid("Not saved: the board did not answer."); });
}

if (endBtn) {
  endBtn.onclick = openEnd;
  saveBtn.onclick = function () { openSend("bind"); };
  giveBtn.onclick = giveCanvas;
  Array.prototype.forEach.call(endPanel.querySelectorAll("button[data-end]"), function (b) {
    b.onclick = function () { endAs(b.getAttribute("data-end")); };
  });
  document.getElementById("canvas-end-back").onclick = function () { endPanel.hidden = true; };
}

/* WHERE THE CANVAS GOES: the one picker order (Random lessons, the
   catch-all, first; then Recent; then every course, then every project, from
   /subjects.json and /sessions.json), and a new one (a project says whether
   it holds patient data). `sendMode` is what a tap does: "bind" (Save to…),
   or "keep" / "transcribe", which end it there. Ending, it closes on "keep
   it unfiled", which ends it with no turn and leaves the pages in the
   session. */
var sendPanel = document.getElementById("notes-send");
var sendList = document.getElementById("notes-send-list");
var sendForm = document.getElementById("notes-send-form");
var sendName = document.getElementById("notes-send-name");
var sendPhi = document.getElementById("notes-send-phi");
var sendMaking = null;
var sendMakingPhi = null;
var sendMode = "transcribe";
var RECENT = 4;
var SEND_HEAD = {
  bind: "Save this canvas to a course or project",
  keep: "Keep the pages in a course or project, then end",
  transcribe: "Transcribe the pages into a course or project, then end"
};
var SEND_GO = { bind: "make it and save there", keep: "make it, keep them there and end",
                transcribe: "make it, transcribe them there and end" };

function sendSaid(text) { document.getElementById("notes-send-said").textContent = text || ""; }

/* `[[heading, [subject...]]]` in the one order; the catch-all under none. */
function pickGroups(list, scratch, recentIds) {
  var byId = {};
  list.forEach(function (one) { byId[one.id] = one; });
  var top = scratch && byId[scratch] ? [byId[scratch]] : [];
  var recent = [];
  [notesState.subject].concat(recentIds).forEach(function (id) {
    var one = byId[id];
    if (one && top.indexOf(one) < 0 && recent.indexOf(one) < 0 && recent.length < RECENT) {
      recent.push(one);
    }
  });
  var rest = list.filter(function (one) { return top.indexOf(one) < 0 && recent.indexOf(one) < 0; });
  return [["", top], ["Recent", recent],
          ["Courses", rest.filter(function (one) { return one.kind !== "project"; })],
          ["Projects", rest.filter(function (one) { return one.kind === "project"; })]]
    .filter(function (g) { return g[1].length; });
}

/* What a tap on a subject does, in the panel's mode. */
function chosen(id) {
  if (sendMode === "bind") { bindTo(id); return; }
  sendSaid("sending…");
  finishEnd({ subject: id, transcribe: sendMode === "transcribe" });
}

/* The list is painted once /subjects.json comes, and again when
   /sessions.json says what was used recently; that second may come later, or
   never. */
var sendSubjects = null;
var sendRecent = [];

function paintSend() {
  sendList.textContent = "";
  if (!sendSubjects) return;
  pickGroups(sendSubjects.subjects || [], sendSubjects.scratch, sendRecent).forEach(function (g) {
    if (g[0]) {
      var head = document.createElement("div");
      head.className = "notes-send-group";
      head.textContent = g[0];
      sendList.appendChild(head);
    }
    g[1].forEach(function (one) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = one.name || one.slug || one.id;
      b.dataset.subject = one.id;
      if (one.id === notesState.subject) b.className = "on";
      b.onclick = function () { chosen(one.id); };
      sendList.appendChild(b);
    });
  });
  if (!sendList.firstChild) sendSaid("No courses or projects yet: make one below.");
}

function openSend(mode) {
  sendMode = mode || "transcribe";
  sendMaking = null;
  sendMakingPhi = null;
  bindArmed = null;
  sendForm.hidden = true;
  endPanel.hidden = true;
  document.getElementById("notes-send-head").textContent = SEND_HEAD[sendMode];
  document.getElementById("notes-send-go").textContent = SEND_GO[sendMode];
  document.getElementById("notes-send-skip").hidden = sendMode === "bind";
  sendSaid("");
  sendList.textContent = "";
  sendSubjects = null;
  sendPanel.hidden = false;
  getJson("/subjects.json").then(function (got) {
    sendSubjects = got || {};
    paintSend();
  }, function () { sendSaid("The list of courses and projects did not come."); });
  getJson("/sessions.json").then(function (got) {
    sendRecent = ((got && got.sessions) || []).map(function (one) { return one.subject; })
      .filter(Boolean);
    if (sendSubjects && !sendPanel.hidden && !ending) paintSend();
  }, function () { /* the list stands without them */ });
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
    postJson("/subjects/new", body).then(function (got) {
      if (!got || !got.ok) { sendSaid((got && got.error) || "Not made."); return; }
      sendName.value = "";
      chosen(got.subject.id);
    }, function () { sendSaid("Not made: the board did not answer."); });
  };
  document.getElementById("notes-send-skip").onclick = function () {
    finishEnd({ transcribe: false });
  };
  document.getElementById("notes-send-back").onclick = function () { sendPanel.hidden = true; };
}

/* Show which question is being answered, so the full-screen view is not
   context-free. A canvas answers none: it shows its title and its buttons. */
fetch(BASE + "/board.json").then(function (r) { return r.json(); }).then(function (d) {
  var state = d.state || {};
  if (state.view === "slate") {
    subjectName = state.subject ? state.course || "" : "";
    paintNotes(state);
    return;
  }
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
