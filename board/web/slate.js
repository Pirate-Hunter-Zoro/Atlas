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

/* NOTHING HERE WAITS FOR EVER. The iPad's link can hold every request for
   minutes and then deliver them all at once -- the board's log once showed
   nothing from it for twelve, autosaves included -- and a request that never
   answered left the picker blank and Save on "saving…" until a reload. So
   a read gets WAIT_MS, then is abandoned (aborted, where the browser can)
   and whatever waited on it says so and can be asked again. A POST is never
   abandoned: one the page gave up on still lands, and a /give or an /end
   taken twice is two turns. Past WAIT_MS it says it is still waiting, keeps
   its button held, and acts on the answer whenever it comes. */
var WAIT_MS = 10000;

function late() {
  var e = new Error("the board did not answer in time");
  e.late = true;
  return e;
}

/* `promise`, or a `late()` refusal after `ms`, `ctl` aborted then if given. */
function within(promise, ms, ctl) {
  return new Promise(function (resolve, reject) {
    var t = setTimeout(function () {
      if (ctl) { try { ctl.abort(); } catch (e) {} }
      reject(late());
    }, ms);
    promise.then(function (v) { clearTimeout(t); resolve(v); },
                 function (e) { clearTimeout(t); reject(e); });
  });
}

/* A JSON read with the wait on it, the reading of the body included. */
function getJson(url) {
  var ctl = typeof AbortController === "function" ? new AbortController() : null;
  var init = { credentials: "same-origin" };
  if (ctl) init.signal = ctl.signal;
  return within(fetch(url, init).then(function (r) { return r.json(); }), WAIT_MS, ctl);
}

/* A JSON POST, waited on until it answers; `slow`, if given, is called once
   it has not answered in WAIT_MS. */
function postJson(url, body, slow) {
  var t = slow ? setTimeout(slow, WAIT_MS) : null;
  return fetch(url, {
    method: "POST", credentials: "same-origin",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {})
  }).then(function (r) { return r.json(); }).then(function (got) {
    clearTimeout(t);
    return got;
  }, function (e) {
    clearTimeout(t);
    throw e;
  });
}

/* Every page's picture on disk before anything reads the pages: the last
   page of an evening is the one whose picture is still waiting for a gap.
   Waited on for WAIT_MS at most. Filing goes ahead regardless, because End
   files the pages again; ending and giving (`strict`) do not, while anything
   is still owed -- not come in time, or a refused save waiting to be tried
   again (`flush` false) -- because an ended canvas refuses the save still on
   its way and a tutor given the pages reads them as they are. */
function settled(strict) {
  var settle = writer && writer.flush ? writer.flush() : null;
  var owed = new Error("the pages are still on their way to the board");
  return within(Promise.resolve(settle), WAIT_MS).then(function (done) {
    if (strict && (done === false || (writer.owed && writer.owed()))) throw owed;
  }, function () {
    if (strict) throw owed;
  });
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
    return;
  }
  /* Asked now, so the picker is usually ready before the first tap. */
  askSubjects();
  askRecent();
}

function paintSave() {
  var bound = notesState.subject;
  saveBtn.textContent = bound ? "in " + (subjectName || bound) : "Save to…";
  saveBtn.title = bound ? "filed in " + (subjectName || bound) + "; tap to move it"
                        : "file these pages in a course or project; the canvas stays open";
}

/* GIVE TO THE TUTOR, after a second tap within four seconds: one turn reads
   every page (POST /give, which reopens an ended canvas), and the board it
   is taught on opens. Not while an End or a Save to… is held: a /give on
   top of an /end that lands reopens the canvas it ended and wakes a turn on
   top of the wrap-up, and the board it opens leaves this page, which drops
   the held /bind. The button says what it waits for until that answers
   (`unheld`). */
var giveArmed = null;
var giving = false;
var GIVE = "Give to the tutor";
function giveCanvas() {
  if (giving) return;
  var held = ending && !ended ? "End" : binding ? "Save to…" : "";
  if (held) {
    giveBtn.textContent = GIVE + " (wait: " + held + " has not been answered yet)";
    return;
  }
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
  settled(true).then(function () {
    /* Held until it answers: a second /give is a second turn. */
    return postJson(BASE + "/give", {}, function () {
      giveBtn.textContent = "giving… (the board has not answered yet)";
    });
  }).then(function (got) {
    if (!got || !got.ok) throw new Error((got && got.error) || "not given");
    giveBtn.textContent = "given";
    go(got.url || BASE + "/board");
  }).catch(function (e) {
    giving = false;
    giveBtn.disabled = false;
    giveBtn.textContent = GIVE + " (" + ((e && e.message) || "the board did not answer") + ")";
    unheld();
  });
}
function go(url) { window.location.href = url; }

/* End and Give, once what they said they wait for has answered, say their
   own names again. */
function unheld() {
  var wait = /\(wait: /;
  if (!(ending && !ended) && !binding && wait.test(giveBtn.textContent)) giveBtn.textContent = GIVE;
  if (!giving && !binding && wait.test(endBtn.textContent)) endBtn.textContent = "End";
}

/* END: the three ways a canvas ends. Bound, "End, keep the pages" and "End
   and transcribe" end it at once; bound to nothing, each first asks where
   the pages go. "Keep it unfiled" is offered only while it is bound to
   nothing.
   A Save to… still held, on a canvas bound to nothing (or to the subject it
   names), is not waited for: End names that subject, so the canvas ends
   there whichever of the two the board takes first, and a bind that never
   answers cannot hold End for ever. A held Save to… that moves it off the
   subject it is bound to is waited for, since which subject it ends in is
   not known until that answers; so is a held Give, which leaves the page. */
function openEnd() {
  if (ending) return;
  var held = giving ? "Give" : binding && notesState.subject && binding !== notesState.subject
    ? "Save to…" : "";
  if (held) {
    endBtn.textContent = "End (wait: " + held + " has not been answered yet)";
    return;
  }
  if (sendPanel) sendPanel.hidden = true;
  document.getElementById("canvas-end-unfiled").hidden = !!(notesState.subject || binding);
  endPanel.hidden = false;
}

function endAs(how) {
  endPanel.hidden = true;
  if (how === "unfiled") { finishEnd({ transcribe: false }); return; }
  var transcribe = how === "transcribe";
  if (notesState.subject) { finishEnd({ transcribe: transcribe }); return; }
  if (binding) { finishEnd({ subject: binding, transcribe: transcribe }); return; }
  openSend(transcribe ? "transcribe" : "keep");
}

/* POST /end with `body`, once the pages are on disk. Refused, the canvas
   stays open and says why. One at a time: a second tap while one is asked
   (a row tapped twice, or another row) does nothing, and so does one while
   an End not yet answered is still held, so there is never a second End on
   top of one that landed. The list is not repainted while it is asked, so
   it is repainted when it stays open. */
var ending = false;
var ended = false;            /* the /end answered ok */
function finishEnd(body) {
  if (ending) return;
  if (giving) {
    endBtn.textContent = "End (wait: Give has not been answered yet)";
    if (sendPanel && !sendPanel.hidden) sendSaid("Not ended: Give has not been answered yet.");
    return;
  }
  ending = true;
  endBtn.disabled = true;
  endBtn.textContent = "ending…";
  settled(true).then(function () {
    return postJson(BASE + "/end", body, function () {
      endBtn.textContent = "ending… (the board has not answered yet)";
    });
  }).then(function (got) {
    if (!got || !got.ok) throw new Error((got && got.error) || "not ended");
    var where = got.sent ? got.sent.name : subjectName || notesState.subject;
    ended = true;
    if (got.sent) {
      notesState.subject = got.sent.id;
      subjectName = got.sent.name || got.sent.id;
    }
    if (sendPanel) sendPanel.hidden = true;
    saveBtn.hidden = true;
    endBtn.textContent = body.transcribe === false
      ? (where ? "ended: the pages are in " + where : "ended: the pages stay in this session")
      : "ended: the tutor is transcribing it into notes.md" + (where ? " in " + where : "");
    unheld();
  }).catch(function (e) {
    var why = (e && e.message) || "the board did not answer";
    ending = false;
    endBtn.disabled = false;
    endBtn.textContent = "End (" + why + ")";
    unheld();
    if (sendPanel && !sendPanel.hidden) {
      paintSend();
      sendSaid("Not ended: " + why + ".");
    }
  });
}

/* SAVE TO…: bind the canvas to a course or project (POST /bind), which files
   its pages there; it neither ends nor wakes anything. A move off a subject
   it has already filed pages in comes back `confirm`, and only a second tap
   on the same subject moves it. One at a time, held until it answers, so
   the answer that comes is the one the page shows; failed, it may have
   landed all the same, and a tap again is harmless, because a /bind to the
   subject it is already bound to changes nothing. `binding` is the subject
   a held /bind names, or "". A tap on another subject while one is held is
   refused, saying so: the held one may still land after it. Not over a held
   End or Give either. */
var bindArmed = null;
var binding = "";
var BIND_SLOW = "saving… The board has not answered yet; it is saved when it does.";
function bindTo(id) {
  if (binding === id) { sendSaid(BIND_SLOW); return; }
  if (binding) {
    sendSaid("Not saved in " + nameOf(id) + ": the board has not answered the save in "
             + nameOf(binding) + " yet. Tap " + nameOf(id) + " again once it has.");
    return;
  }
  if (ending || giving) {
    sendSaid("Not saved: " + (ending ? "End" : "Give") + " has not been answered yet.");
    return;
  }
  var force = bindArmed === id;
  bindArmed = null;
  binding = id;
  sendSaid("saving…");
  settled(false).then(function () {
    return postJson(BASE + "/bind", { subject: id, force: force }, function () {
      if (binding === id && !ended) sendSaid(BIND_SLOW);
    });
  }).then(function (got) {
    binding = "";
    unheld();
    /* Ended meanwhile, by an End that named this same subject. */
    if (ended) return;
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
  }, function () {
    binding = "";
    unheld();
    if (ended) return;
    sendSaid("The board did not answer, so it may not be saved. Tap it again to make sure.");
  });
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
   /subjects.json and /sessions.json), and a new one. `sendMode` is what a tap does: "bind" (Save to…),
   or "keep" / "transcribe", which end it there. Ending, it closes on "keep
   it unfiled", which ends it with no turn and leaves the pages in the
   session. */
var sendPanel = document.getElementById("notes-send");
var sendList = document.getElementById("notes-send-list");
var sendForm = document.getElementById("notes-send-form");
var sendName = document.getElementById("notes-send-name");
var sendMaking = null;
var sendOpened = 0;           /* bumped each time the panel opens */
var making = "";              /* the name a /subjects/new is held for, or "" */
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

/* A subject's name, from the list, or its id. */
function nameOf(id) {
  var all = (sendSubjects && sendSubjects.subjects) || [];
  for (var i = 0; i < all.length; i++) if (all[i].id === id) return all[i].name || id;
  return id;
}

/* What a tap on a subject does, in the panel's mode. */
function chosen(id) {
  if (sendMode === "bind") { bindTo(id); return; }
  sendSaid("sending…");
  finishEnd({ subject: id, transcribe: sendMode === "transcribe" });
}

/* THE LIST IS NEVER BLANK WHILE IT IS ASKED FOR. The last /subjects.json
   that came is kept on this device (`board.subjects`, which home keeps too)
   and painted the instant the panel opens; the fresh one repaints it when it
   comes, and again when /sessions.json says what was used recently, which
   may come later, or never. With nothing kept the panel says it is asking,
   and a list that fails, or does not come in WAIT_MS, is said plainly with
   "try again" under it. */
var SUBJECTS_KEY = "board.subjects";
var sendSubjects = keptSubjects();
var sendAsking = null;        /* the /subjects.json on the wire, or null */
var sendFailed = "";          /* why the last one did not come, or "" */
var sendRecent = [];

function keptSubjects() {
  try {
    var got = JSON.parse(localStorage.getItem(SUBJECTS_KEY) || "null");
    return got && Array.isArray(got.subjects) ? got : null;
  } catch (e) {
    return null;
  }
}

function keepSubjects(got) {
  try {
    localStorage.setItem(SUBJECTS_KEY, JSON.stringify({ scratch: got.scratch || null,
                                                       subjects: got.subjects }));
  } catch (e) { /* this page's copy, then */ }
}

function askSubjects() {
  if (sendAsking) return sendAsking;
  sendFailed = "";
  sendAsking = getJson("/subjects.json").then(function (got) {
    if (!got || !Array.isArray(got.subjects)) throw new Error("not a list");
    sendSubjects = got;
    keepSubjects(got);
  }).catch(function (e) {
    sendFailed = e && e.late ? "The list of courses and projects did not come in time."
                             : "The list of courses and projects did not come.";
  }).then(function () {
    sendAsking = null;
    if (!sendPanel.hidden && !ending) paintSend();
  });
  if (!sendPanel.hidden) paintSend();
  return sendAsking;
}

function askRecent() {
  getJson("/sessions.json").then(function (got) {
    sendRecent = ((got && got.sessions) || []).map(function (one) { return one.subject; })
      .filter(Boolean);
    if (sendSubjects && !sendPanel.hidden && !ending) paintSend();
  }, function () { /* the list stands without them */ });
}

/* A line under the rows: asking, or not come, with "try again". */
function sendWaitLine(text, again) {
  var p = document.createElement("p");
  p.className = "notes-send-wait";
  p.textContent = text;
  sendList.appendChild(p);
  if (!again) return;
  var b = document.createElement("button");
  b.type = "button";
  b.className = "notes-send-again";
  b.textContent = "try again";
  b.onclick = function () { askSubjects(); };
  sendList.appendChild(b);
}

function paintSend() {
  sendList.textContent = "";
  var rows = sendSubjects
    ? pickGroups(sendSubjects.subjects || [], sendSubjects.scratch, sendRecent) : [];
  rows.forEach(function (g) {
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
  if (sendFailed) {
    sendWaitLine(sendFailed + (rows.length ? " These are the ones that came last time." : ""),
                 true);
  } else if (sendAsking && !rows.length) {
    sendWaitLine("Getting the courses and projects…", false);
  } else if (!sendAsking && !rows.length) {
    sendSaid("No courses or projects yet: make one below.");
  }
}

function openSend(mode) {
  sendOpened++;
  sendMode = mode || "transcribe";
  sendMaking = null;
  bindArmed = null;
  sendForm.hidden = true;
  endPanel.hidden = true;
  document.getElementById("notes-send-head").textContent = SEND_HEAD[sendMode];
  document.getElementById("notes-send-go").textContent = SEND_GO[sendMode];
  document.getElementById("notes-send-skip").hidden = sendMode === "bind";
  sendSaid("");
  sendPanel.hidden = false;
  paintSend();
  askSubjects();
  askRecent();
}

function startSendMaking(kind) {
  sendMaking = kind;
  sendForm.hidden = false;
  sendName.placeholder = kind === "project" ? "the project's name" : "the course's name";
  sendSaid("");
}

if (sendPanel) {
  document.getElementById("notes-new-course").onclick = function () { startSendMaking("course"); };
  document.getElementById("notes-new-project").onclick = function () { startSendMaking("project"); };
  document.getElementById("notes-send-go").onclick = function () {
    var name = (sendName.value || "").trim();
    if (!sendMaking) return;
    if (!name) { sendSaid("Name it first."); return; }
    /* One at a time, held until it answers: a second would be refused as
       already there once the first lands. Answered after the panel was
       closed or opened again, it is not filed into: the list shows it. */
    function slow() {
      sendSaid("making " + making + "… The board has not answered yet; it goes on when it does.");
    }
    if (making) { slow(); return; }
    var body = { kind: sendMaking, name: name };
    var opened = sendOpened;
    making = name;
    sendSaid("making " + name + "…");
    postJson("/subjects/new", body, slow).then(function (got) {
      making = "";
      if (!got || !got.ok) { sendSaid((got && got.error) || "Not made."); return; }
      sendName.value = "";
      /* In the list at once, whatever /subjects.json is on the wire. */
      var made = got.subject.name || got.subject.id;
      if (!sendSubjects) sendSubjects = { scratch: null, subjects: [] };
      if (nameOf(got.subject.id) === got.subject.id) sendSubjects.subjects.push(got.subject);
      if (!sendPanel.hidden && opened === sendOpened) {
        /* A Save to… still held is not overridden: the made one is offered. */
        if (sendMode === "bind" && binding) {
          if (!ending) paintSend();
          sendSaid(made + " is made, but the board has not answered the save in "
                   + nameOf(binding) + " yet. Tap " + made + " once it has, to save it there.");
          askSubjects();
          return;
        }
        chosen(got.subject.id);
        return;
      }
      askSubjects();
    }, function () {
      /* It may have been made all the same, so the list is asked again and
         shows it if it was. */
      making = "";
      sendSaid("The board did not answer, so " + name + " may not be made. "
               + "It is in the list if it was.");
      askSubjects();
    });
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
