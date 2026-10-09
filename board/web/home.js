/* ==========================================================================
   home.js -- the start screen.

   Top to bottom: the open sessions (Continue), New session, notices, the
   courses and the projects, past sessions, three actions, and settings.

   Everything it reads is unprefixed and one of these: GET /sessions.json,
   /subjects.json, /notices.json, /assistants.json and, for the meeting deck,
   /library.json?subject=projects/Meetings. Everything it writes is
   one of: POST /sessions/new, /subjects/new, /meeting, /default-agent and
   /artifact?subject=<id> (a deck or a paper from a subject's row).
   A session opens at /s/<id>/board; a subject's page is its library,
   /library?subject=<id>.

   AN ADDRESS IN THE BAR IS FOLLOWED. `#/s/<id>/...` goes to that session's
   board with the address carried whole. An old `#/w/<family>/<ws>/...` link
   is read through `imported` in /sessions.json (sessions/.imported.json):
   the session that workspace's live/ became, and the same card in it. With
   no match it lands on the subject's page with a note that the link was to
   an archived sitting. T55 deletes that shim.

   Nothing in the paint may throw: this page is the way into every lesson.
   ========================================================================== */

(function () {
"use strict";

function $(id) { return document.getElementById(id); }

var els = {
  dot: $("dot"),
  said: $("said"),
  openList: $("open-list"),
  openNone: $("open-none"),
  newSession: $("new-session"),
  newSessionSub: $("new-session-sub"),
  notices: $("notices"),
  noticeList: $("notice-list"),
  courseList: $("course-list"),
  courseNone: $("course-none"),
  projectList: $("project-list"),
  projectNone: $("project-none"),
  newCourse: $("new-course"),
  newProject: $("new-project"),
  pastList: $("past-list"),
  pastNone: $("past-none"),
  actMeeting: $("act-meeting"),
  themeBtn: $("btn-theme"),
  themeNow: $("theme-now"),
  reload: $("btn-reload"),
  who: $("who"),
  whoWays: $("who-ways"),
  whoNote: $("who-note"),
  maker: $("maker"),
  makerKind: $("maker-kind"),
  makerName: $("maker-name"),
  makerPhi: $("maker-phi"),
  makerSaid: $("maker-said"),
  makerGo: $("maker-go"),
  makerGoSub: $("maker-go-sub"),
  makerClose: $("maker-close"),
  notes: $("notes"),
  notesSince: $("notes-since"),
  notesList: $("notes-list"),
  notesMake: $("notes-make"),
  notesMakeSub: $("notes-make-sub"),
  notesClose: $("notes-close"),
  notesSaid: $("notes-said"),
  notesRead: $("notes-read"),
  notesReadSub: $("notes-read-sub"),
  artmaker: $("artmaker"),
  artmakerWhere: $("artmaker-where"),
  artmakerMake: $("artmaker-make"),
  artmakerAbout: $("artmaker-about"),
  artmakerSaid: $("artmaker-said"),
  artmakerGo: $("artmaker-go"),
  artmakerGoSub: $("artmaker-go-sub"),
  artmakerClose: $("artmaker-close"),
  artmakerOpen: $("artmaker-open")
};

/* Every navigation goes through here, so there is one place it happens. */
function go(url) { window.location.href = url; }

function el(tag, cls, text) {
  var e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined && text !== null) e.textContent = text;
  return e;
}

function getJSON(url) {
  return fetch(url, { credentials: "same-origin", cache: "no-store" })
    .then(function (r) { return r.json(); });
}

function postJSON(url, body) {
  return fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {})
  }).then(function (r) {
    return r.json().catch(function () { return { ok: false }; });
  });
}

function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }

/* `YYYY-MM-DD HH:MM:SS`, as session.json writes it, as a short date. */
function day(when) {
  var s = String(when || "");
  return s.length >= 10 ? s.slice(0, 10) : s;
}

function enc(s) { return encodeURIComponent(s); }

/* ---------------------------------------------------------------- sessions */
var sessionsData = null;      /* the last /sessions.json */

function sessionTitle(rec) {
  return rec.title || (rec.subject_name ? rec.subject_name : "Untitled session");
}

function openRow(rec) {
  var a = el("a", "row");
  a.href = rec.url || "/s/" + enc(rec.id) + "/board";
  a.setAttribute("data-session", rec.id);
  var top = el("span", "row-top");
  top.appendChild(el("span", "row-name", sessionTitle(rec)));
  if (rec.new_cards) {
    top.appendChild(el("span", "badge", rec.new_cards + " new"));
  }
  a.appendChild(top);
  var bits = [rec.subject_name || rec.subject || "unbound"];
  if (rec.mode === "do") bits.push("do");
  a.appendChild(el("span", "row-sub", bits.join("  ·  ")));
  var last = rec.last_card;
  a.appendChild(el("span", "row-last", last
    ? "last: " + (last.title || "card " + last.id)
    : "nothing on the board yet"));
  return a;
}

/* A past session opens its board to read; nothing on this row changes it. */
function pastRow(rec) {
  var a = el("a", "row past");
  a.href = rec.url || "/s/" + enc(rec.id) + "/board";
  a.title = "read only";
  a.setAttribute("data-session", rec.id);
  a.appendChild(el("span", "row-name", sessionTitle(rec)));
  a.appendChild(el("span", "row-sub",
    (rec.subject_name || rec.subject || "unbound") + "  ·  "
    + day(rec.opened) + (rec.ended ? " to " + day(rec.ended) : "")));
  return a;
}

function paintSessions(data) {
  var list = (data && data.sessions) || [];
  var open = list.filter(function (r) { return !r.ended; });
  var past = list.filter(function (r) { return !!r.ended; });
  els.openList.innerHTML = "";
  open.forEach(function (r) { els.openList.appendChild(openRow(r)); });
  els.openNone.hidden = open.length > 0;
  els.pastList.innerHTML = "";
  past.forEach(function (r) { els.pastList.appendChild(pastRow(r)); });
  els.pastNone.hidden = past.length > 0;
}

var starting = false;

function newSession() {
  if (starting) return;
  starting = true;
  els.newSession.disabled = true;
  els.newSessionSub.textContent = "opening…";
  postJSON("/sessions/new", {}).then(function (got) {
    if (got && got.ok && got.url) { go(got.url); return; }
    throw new Error((got && got.error) || "the session was not made");
  }).catch(function (e) {
    starting = false;
    els.newSession.disabled = false;
    els.newSessionSub.textContent = e.message || "the board did not answer";
  });
}

/* ---------------------------------------------------------------- subjects */
var subjectsData = null;      /* the last /subjects.json */

function subjectRow(s) {
  var box = el("div", "subj");
  box.appendChild(subjectLink(s));
  var make = el("button", "row-make", "make");
  make.type = "button";
  make.title = "a deck or a paper about " + (s.name || s.id);
  make.setAttribute("data-make-for", s.id);
  make.onclick = function () { openArtmaker(s); };
  box.appendChild(make);
  return box;
}

function subjectLink(s) {
  var a = el("a", "row");
  a.href = "/library?subject=" + enc(s.id) + "&from=home";
  a.setAttribute("data-subject", s.id);
  a.appendChild(el("span", "row-name", s.name || s.slug || s.id));
  var open = ((sessionsData && sessionsData.sessions) || []).filter(function (r) {
    return !r.ended && r.subject === s.id;
  }).length;
  a.appendChild(el("span", "row-sub", open
    ? plural(open, "open session", "open sessions") : s.id));
  return a;
}

function paintSubjects(data) {
  var list = (data && data.subjects) || [];
  var courses = list.filter(function (s) { return s.kind === "course"; });
  var projects = list.filter(function (s) { return s.kind === "project"; });
  els.courseList.innerHTML = "";
  courses.forEach(function (s) { els.courseList.appendChild(subjectRow(s)); });
  els.courseNone.hidden = courses.length > 0;
  els.projectList.innerHTML = "";
  projects.forEach(function (s) { els.projectList.appendChild(subjectRow(s)); });
  els.projectNone.hidden = projects.length > 0;
}

/* ------------------------------------- a deck or a paper, from a subject */
/* `POST /artifact?subject=<id>`: the server makes the doc.json and the
   newest open session on that subject (else a new one bound to it) writes
   and builds it. The reply names the session, which is where it is seen
   being written. */
var artFor = null;
var artMake = "deck";
var artAsking = false;

function openArtmaker(s) {
  artFor = s;
  artMake = "deck";
  artAsking = false;
  els.artmakerWhere.textContent = s.name || s.id;
  els.artmakerAbout.value = "";
  els.artmakerOpen.hidden = true;
  artSay("");
  paintArtmaker();
  els.artmaker.hidden = false;
  try { els.artmakerAbout.focus(); } catch (e) { /* a page without focus */ }
}

function closeArtmaker() { els.artmaker.hidden = true; }

function artSay(text, bad) {
  els.artmakerSaid.hidden = !text;
  els.artmakerSaid.className = "sheet-line" + (bad ? " bad" : "");
  els.artmakerSaid.textContent = text || "";
}

function paintArtmaker() {
  Array.prototype.forEach.call(els.artmakerMake.querySelectorAll("button[data-make]"),
    function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-make") === artMake ? "true" : "false");
    });
  var about = els.artmakerAbout.value.trim();
  els.artmakerGo.disabled = artAsking || !about;
  els.artmakerGoSub.textContent = artAsking ? "asking…"
    : !about ? "say what it is about"
    : artMake === "deck" ? "a beamer deck, built to PDF" : "a Markdown paper, built to .docx";
}

function askArtifact() {
  var about = els.artmakerAbout.value.trim();
  if (!artFor || !about || artAsking) return;
  artAsking = true;
  paintArtmaker();
  postJSON("/artifact?subject=" + enc(artFor.id), { make: artMake, about: about })
    .then(function (got) {
      artAsking = false;
      if (!got || !got.ok) {
        paintArtmaker();
        artSay((got && got.error) || "it was not asked for", true);
        return;
      }
      els.artmakerAbout.value = "";
      paintArtmaker();
      artSay((artMake === "deck" ? "A deck" : "A paper") + " is being written: "
             + (got.source || "its file") + ".");
      if (got.session) {
        els.artmakerOpen.href = "/s/" + enc(got.session) + "/board";
        els.artmakerOpen.hidden = false;
      }
    }).catch(function () {
      artAsking = false;
      paintArtmaker();
      artSay("the board did not answer", true);
    });
}

/* ------------------------------------------------------- + new, the sheet */
var makerKind = "course";
var makerPhi = null;          /* a project's answer: true, false, or unasked */
var making = false;

function openMaker(kind) {
  makerKind = kind === "project" ? "project" : "course";
  makerPhi = null;
  making = false;
  els.makerKind.textContent = "new " + makerKind;
  els.makerName.value = "";
  els.makerName.placeholder = makerKind === "course" ? "Linear Algebra" : "Diarization";
  els.makerPhi.hidden = makerKind !== "project";
  els.makerSaid.hidden = true;
  paintMaker();
  els.maker.hidden = false;
  try { els.makerName.focus(); } catch (e) { /* a page without focus */ }
}

function closeMaker() { els.maker.hidden = true; }

function makerSay(text, bad) {
  els.makerSaid.hidden = !text;
  els.makerSaid.className = "sheet-line" + (bad ? " bad" : "");
  els.makerSaid.textContent = text || "";
}

function paintMaker() {
  Array.prototype.forEach.call(els.makerPhi.querySelectorAll("button[data-phi]"),
    function (b) {
      var said = b.getAttribute("data-phi") === "yes";
      b.setAttribute("aria-pressed", makerPhi === said ? "true" : "false");
    });
  var name = els.makerName.value.trim();
  var want = !name ? "name it first"
    : makerKind === "project" && makerPhi === null ? "say whether it holds patient data"
    : "";
  els.makerGo.disabled = making || !!want;
  els.makerGoSub.textContent = making ? "making it…" : want
    || (makerKind === "project" && makerPhi
        ? "a project holding patient data: phi/ and results/ ignored"
        : "one commit: tutorboard.json and TUTOR.md");
}

function makeSubject() {
  var name = els.makerName.value.trim();
  if (!name || making) return;
  if (makerKind === "project" && makerPhi === null) return;
  making = true;
  paintMaker();
  var body = { kind: makerKind, name: name };
  if (makerKind === "project") body.phi = makerPhi;
  postJSON("/subjects/new", body).then(function (got) {
    making = false;
    if (!got || !got.ok) {
      paintMaker();
      makerSay((got && got.error) || "it was not made", true);
      return;
    }
    closeMaker();
    return refresh();
  }).catch(function () {
    making = false;
    paintMaker();
    makerSay("the board did not answer", true);
  });
}

/* ---------------------------------------------------------------- notices */
/* A cluster report with no session to wake (D16). Dismissing one is this
   device's own record, kept in localStorage by the notice's key. */
var DISMISSED = "board.notices.dismissed";

function noticeKey(n) {
  return String(n.id || ((n.t || n.at || "") + "|" + noticeText(n)));
}

function noticeText(n) {
  return String(n.text || n.line || n.title || n.what || "");
}

function dismissed() {
  try {
    var got = JSON.parse(localStorage.getItem(DISMISSED) || "[]");
    return Array.isArray(got) ? got : [];
  } catch (e) { return []; }
}

function dismiss(key) {
  var keep = dismissed().filter(function (k) { return k !== key; });
  keep.push(key);
  try { localStorage.setItem(DISMISSED, JSON.stringify(keep.slice(-200))); }
  catch (e) { /* private browsing: it comes back on the next load */ }
}

var lastNotices = [];

function paintNotices(data) {
  if (data) lastNotices = (data.notices || []).filter(function (n) { return n; });
  var gone = dismissed();
  var show = lastNotices.filter(function (n) {
    return gone.indexOf(noticeKey(n)) < 0;
  });
  els.noticeList.innerHTML = "";
  show.forEach(function (n) {
    var row = el("div", "row notice");
    var body = el("span", "row-main");
    body.appendChild(el("span", "row-name", noticeText(n) || "a report came back"));
    var where = [n.subject, n.iso || n.when].filter(Boolean).join("  ·  ");
    if (where) body.appendChild(el("span", "row-sub", where));
    row.appendChild(body);
    var x = el("button", "dismiss", "✕");
    x.type = "button";
    x.title = "dismiss";
    x.onclick = function () { dismiss(noticeKey(n)); paintNotices(null); };
    row.appendChild(x);
    els.noticeList.appendChild(row);
  });
  els.notices.hidden = show.length === 0;
}

/* -------------------------------------------------------------- addresses */
var routed = "";              /* the address text this page last followed */

function say(text) {
  els.said.hidden = !text;
  els.said.textContent = text || "";
}

/* The session an old workspace's live/ became, matched without regard to
   case: links spelled the family `Courses` where the id says `courses`. */
function importedSession(a) {
  var map = (sessionsData && sessionsData.imported) || {};
  var want = (a.family + "/" + a.workspace).toLowerCase();
  var keys = Object.keys(map);
  for (var i = 0; i < keys.length; i++) {
    if (keys[i].toLowerCase() === want) return map[keys[i]];
  }
  return "";
}

/* A subject by its directory name, for an old link with no session. */
function subjectFor(a) {
  var want = String(a.workspace || "").toLowerCase();
  var found = null;
  ((subjectsData && subjectsData.subjects) || []).forEach(function (s) {
    if (!found && String(s.slug || "").toLowerCase() === want) found = s;
  });
  return found;
}

/* Where an address in the bar goes, or "" when it goes nowhere. */
function destination(a) {
  if (!a) return "";
  if (a.session) return "/s/" + enc(a.session) + "/board" + a.text;
  var sid = importedSession(a);
  if (sid) {
    var spec = { session: sid, surface: "session" };
    if (a.surface === "card") { spec.surface = "card"; spec.card = a.card; }
    return "/s/" + enc(sid) + "/board" + window.Address.format(spec);
  }
  var s = subjectFor(a);
  if (s) return "/library?subject=" + enc(s.id) + "&from=archived";
  return "";
}

function route() {
  if (!window.Address) return;
  var a = null;
  try { a = window.Address.parse(window.location.hash || ""); } catch (e) { a = null; }
  if (!a || a.text === routed) return;
  /* An old link needs the sessions and the subjects to be read. */
  if (!a.session && (!sessionsData || !subjectsData)) return;
  routed = a.text;
  var to = destination(a);
  if (to) { go(to); return; }
  say("That link is to an archived sitting of " + a.workspace
      + ", and nothing here holds it now.");
}

window.addEventListener("hashchange", route);

/* ------------------------------------------------------- the meeting deck */
/* ONE DECK, replaced by each ask; git history keeps every `meeting.tex`. A
   writer turn takes minutes, so the sheet watches the Meetings library, whose
   payload carries the deck's record as `meeting`. "Read the deck" is that
   library with the deck opened (`?doc=`): `Reader.open`, and "say what is
   wrong" files a round that queues a `[revise]` turn in a Meetings session. */
var notesSince = "";
var notesWant = {};
var MEETINGS = "projects/Meetings";
var MEETINGS_Q = "subject=" + encodeURIComponent(MEETINGS);
var notesTimer = null;
var NOTES_POLL = 10000;

function openNotes() {
  els.notesSaid.hidden = true;
  notesSince = "";
  notesWant = {};
  paintSince();
  paintWhich();
  els.notesRead.hidden = true;
  pollNotes(true);
  els.notes.hidden = false;
}

function closeNotes() {
  els.notes.hidden = true;
  if (notesTimer) { clearInterval(notesTimer); notesTimer = null; }
}

function notesSay(text, bad) {
  els.notesSaid.hidden = false;
  els.notesSaid.className = "sheet-line" + (bad ? " bad" : "");
  els.notesSaid.textContent = text;
}

function pollNotes(quiet) {
  return getJSON("/library.json?" + MEETINGS_Q)
    .then(function (got) { paintNotesState(got || {}, quiet); })
    .catch(function () { /* a poll is quiet; the next one asks again */ });
}

/* THE DECK'S ROW in the Meetings library: the document carrying `meeting`. */
function deckRow(got) {
  var out = null;
  (got.documents || []).forEach(function (d) { if (d.meeting && !out) out = d; });
  return out;
}

function watchNotes() {
  if (notesTimer) clearInterval(notesTimer);
  notesTimer = setInterval(function () {
    if (els.notes.hidden || document.hidden) return;
    pollNotes(false);
  }, NOTES_POLL);
}

function paintNotesState(got, quiet) {
  var rec = got.meeting;
  if (!rec) return;
  var n = (rec.subjects || []).length;
  var what = plural(n, "subject", "subjects")
    + (rec.period ? ", " + rec.period : rec.since ? ", " + rec.since : "");
  if (rec.state === "being written") {
    els.notesRead.hidden = true;
    notesSay("Being written in Meetings: " + what + ". This sheet says when it is ready.");
    watchNotes();
    return;
  }
  if (notesTimer) { clearInterval(notesTimer); notesTimer = null; }
  if (rec.state === "did not land") {
    if (!quiet) notesSay(rec.why || "The deck did not land. Ask for it again.", true);
    return;
  }
  var row = deckRow(got);
  if (!rec.ready || !row) return;
  var check = rec.check || {};
  var unsupported = (check.numbers || []).length + (check.figures || []).length
    + (check.internal || []).length;
  els.notesRead.setAttribute("href", "/library?" + MEETINGS_Q + "&doc="
    + encodeURIComponent(row.id) + "&from=home");
  els.notesRead.hidden = false;
  els.notesReadSub.textContent = what
    + (unsupported ? " · " + unsupported + " to check" : "")
    + (row.marks && row.marks.pages ? " · marked up" : "");
  if (!quiet) {
    notesSay("Ready: " + plural(rec.pages || row.pages || 0, "slide", "slides")
             + " about " + what + ". It replaced the one before it.");
  }
}

function paintSince() {
  Array.prototype.forEach.call(els.notesSince.querySelectorAll("button[data-since]"),
    function (b) {
      b.setAttribute("aria-pressed",
                     b.getAttribute("data-since") === notesSince ? "true" : "false");
    });
  paintTicks();
}

/* Every course and project but Meetings itself, which is where the deck goes. */
function paintWhich() {
  els.notesList.innerHTML = "";
  ((subjectsData && subjectsData.subjects) || []).forEach(function (s) {
    if (s.id === MEETINGS) return;
    var b = el("button");
    b.type = "button";
    b.setAttribute("data-id", s.id);
    b.appendChild(el("span", "tick"));
    b.appendChild(el("span", "", s.name || s.id));
    b.onclick = function () {
      notesWant[s.id] = !notesWant[s.id];
      paintTicks();
    };
    els.notesList.appendChild(b);
  });
  paintTicks();
}

function chosen() {
  return Object.keys(notesWant).filter(function (id) { return notesWant[id]; });
}

function paintTicks() {
  Array.prototype.forEach.call(els.notesList.querySelectorAll("button"), function (b) {
    var on = !!notesWant[b.getAttribute("data-id")];
    b.setAttribute("aria-pressed", on ? "true" : "false");
    b.querySelector(".tick").textContent = on ? "✓" : "·";
  });
  var n = chosen().length;
  els.notesMake.disabled = !notesSince;
  els.notesMakeSub.textContent = !notesSince ? "choose a period"
    : (n ? plural(n, "subject", "subjects") : "every subject that moved")
      + ", replacing the last deck";
}

function makeDeck() {
  if (!notesSince) return;
  els.notesMake.disabled = true;
  notesSay("asking for it…");
  postJSON("/meeting", { since: notesSince, items: chosen() }).then(function (rec) {
    rec = rec || {};
    els.notesMake.disabled = false;
    if (!rec.ok) {
      notesSay(rec.detail || rec.error || "the deck could not be asked for", true);
      return;
    }
    notesSay(rec.detail || "Being written in Meetings.");
    els.notesRead.hidden = true;
    pollNotes(false);
    watchNotes();
  }).catch(function (e) {
    els.notesMake.disabled = false;
    notesSay(e.message || "the board did not answer", true);
  });
}

/* ------------------------------------------------------- default assistant */
/* The machine's one provider setting, set with POST /default-agent: every
   session's next turn goes to it, or to its fallback when it cannot. Drawn by
   `who.js`, the rules the board's own chooser uses. */
var lastAssistants = null;
var whoSaved = null;

function paintWho(assistants) {
  if (!window.WhoChoice || !assistants) { els.who.hidden = true; return; }
  var have = window.WhoChoice.offerable(assistants);
  els.who.hidden = have.length < 2;
  if (els.who.hidden) return;
  window.WhoChoice.draw(els.whoWays, have, whoSaved || assistants["default"], {
    say: function (m) { els.whoNote.textContent = m; },
    pick: function (a) { setDefaultAgent(a.name); }
  });
}

function setDefaultAgent(name) {
  whoSaved = name;
  els.whoNote.textContent = "";
  paintWho(lastAssistants);
  postJSON("/default-agent", { agent: name }).then(function (got) {
    if (got && got.ok) {
      lastAssistants = got.assistants || lastAssistants;
      /* Who takes the next turn: the provider, or the fallback and why. */
      els.whoNote.textContent = got.why
        ? got.why + "."
        : name + " writes the next card in every session.";
    } else {
      whoSaved = null;
      els.whoNote.textContent = (got && (got.detail || got.error)) || "that did not take.";
    }
    paintWho(lastAssistants);
  }).catch(function () {
    whoSaved = null;
    els.whoNote.textContent = "the board did not answer.";
    paintWho(lastAssistants);
  });
}

function loadAssistants() {
  return getJSON("/assistants.json").then(function (got) {
    lastAssistants = (got && got.assistants) || null;
    if (whoSaved && lastAssistants && lastAssistants["default"] === whoSaved) whoSaved = null;
    paintWho(lastAssistants);
  }).catch(function () { paintWho(null); });
}

/* ------------------------------------------------------------------- theme */
/* The theme is `typeface.js`'s (`Typeface.theme`); this only says which. */
function paintTheme() {
  els.themeNow.textContent = document.body.dataset.mode || "auto";
}

/* -------------------------------------------------------------------- load */
function refresh() {
  return Promise.all([
    getJSON("/sessions.json"),
    getJSON("/subjects.json"),
    getJSON("/notices.json").catch(function () { return null; })
  ]).then(function (all) {
    els.dot.className = "dot live";
    sessionsData = all[0] || { sessions: [] };
    subjectsData = all[1] || { subjects: [] };
    paintSessions(sessionsData);
    paintSubjects(subjectsData);
    if (all[2]) paintNotices(all[2]);
    route();
  }).catch(function () {
    els.dot.className = "dot dead";
  });
}

els.newSession.onclick = newSession;
els.newCourse.onclick = function () { openMaker("course"); };
els.newProject.onclick = function () { openMaker("project"); };
els.makerName.addEventListener("input", function () { makerSay(""); paintMaker(); });
els.makerName.addEventListener("keydown", function (ev) {
  if (ev.key === "Enter") makeSubject();
});
els.makerPhi.addEventListener("click", function (ev) {
  var b = ev.target.closest ? ev.target.closest("button[data-phi]") : null;
  if (!b) return;
  makerPhi = b.getAttribute("data-phi") === "yes";
  paintMaker();
});
els.makerGo.onclick = makeSubject;
els.makerClose.onclick = closeMaker;
els.maker.addEventListener("click", function (ev) {
  if (ev.target === els.maker) closeMaker();
});
els.artmakerMake.addEventListener("click", function (ev) {
  var b = ev.target.closest ? ev.target.closest("button[data-make]") : null;
  if (!b) return;
  artMake = b.getAttribute("data-make") === "paper" ? "paper" : "deck";
  paintArtmaker();
});
els.artmakerAbout.addEventListener("input", function () { artSay(""); paintArtmaker(); });
els.artmakerAbout.addEventListener("keydown", function (ev) {
  if (ev.key === "Enter") askArtifact();
});
els.artmakerGo.onclick = askArtifact;
els.artmakerClose.onclick = closeArtmaker;
els.artmaker.addEventListener("click", function (ev) {
  if (ev.target === els.artmaker) closeArtmaker();
});
els.actMeeting.onclick = openNotes;
els.notesClose.onclick = closeNotes;
els.notesMake.onclick = makeDeck;
els.notes.addEventListener("click", function (ev) {
  if (ev.target === els.notes) closeNotes();
});
els.notesSince.addEventListener("click", function (ev) {
  var b = ev.target.closest ? ev.target.closest("button[data-since]") : null;
  if (!b) return;
  notesSince = b.getAttribute("data-since");
  paintSince();
});
els.themeBtn.onclick = function () {
  if (window.Typeface) window.Typeface.theme("next");
  paintTheme();
};
els.reload.onclick = function () { window.location.reload(); };
document.addEventListener("keydown", function (ev) {
  if (ev.key !== "Escape") return;
  if (!els.maker.hidden) closeMaker();
  if (!els.notes.hidden) closeNotes();
  if (!els.artmaker.hidden) closeArtmaker();
});
paintTheme();
document.addEventListener("DOMContentLoaded", paintTheme);

refresh();
loadAssistants();
setInterval(function () { if (!document.hidden) refresh(); }, 20000);
document.addEventListener("visibilitychange", function () {
  if (!document.hidden) refresh();
});
window.addEventListener("pageshow", function (ev) { if (ev && ev.persisted) refresh(); });

/* --------------------------------------------------------------------- PWA */
if ("serviceWorker" in navigator && window.isSecureContext) {
  var hadController = !!navigator.serviceWorker.controller;
  var reloading = false;
  navigator.serviceWorker.addEventListener("controllerchange", function () {
    if (!hadController || reloading) return;
    reloading = true;
    window.location.reload();
  });
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).then(function (reg) {
      function check() { if (!document.hidden) { try { reg.update(); } catch (e) {} } }
      document.addEventListener("visibilitychange", check);
      window.addEventListener("focus", check);
    }).catch(function () {});
  });
}
})();
