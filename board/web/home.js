/* ==========================================================================
   home.js -- the start screen.

   Top to bottom: the open sessions (Continue), New session and New canvas,
   who tutors, notices, a search, the courses and the projects (most recently
   used first), past sessions (the newest ten), the actions, and settings.

   Everything it reads is unprefixed and one of these: GET /sessions.json,
   /subjects.json, /notices.json, /sync.json (the sync health),
   /assistants.json and /subject/delete?subject=<id> (whether a subject can
   be deleted, and why not). Everything it writes is one of: POST
   /sessions/new, /subjects/new, /subject/delete, /session/delete,
   /default-agent,
   /artifact?subject=<id> (a deck or a paper from a subject's row),
   /client-error (what broke on this page, for the board's log), a past
   session's /s/<id>/send (an unbound one, sent to a course or project), and
   for Annotate a PDF the new session's own /s/<id>/bind, /upload (a file from
   the iPad) or /fetch (an address), and /file.
   New canvas opens a new session at /s/<id>/slate, a canvas; a canvas's row
   offers "give to the tutor", its /s/<id>/give.
   A session opens at /s/<id>/board; a subject's page is its library,
   /library?subject=<id>.

   AN ADDRESS IN THE BAR IS FOLLOWED. `#/s/<id>/...` goes to that session's
   board with the address carried whole. Nothing else is an address.

   Nothing in the paint may throw: this page is the way into every lesson.
   What does throw, a script or an image that did not arrive, and a list the
   board did not answer for are told to the board (`beacon`), and a refresh
   that failed is tried again, further apart each time.
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
  pastMore: $("past-more"),
  find: $("find"),
  panic: $("panic"),
  actNotes: $("act-notes"),
  actNotesSub: $("act-notes-sub"),
  actAnnotate: $("act-annotate"),
  annot: $("annot"),
  annotFile: $("annot-file"),
  annotUrl: $("annot-url"),
  annotSubject: $("annot-subject"),
  annotBar: $("annot-bar"),
  annotSaid: $("annot-said"),
  annotGo: $("annot-go"),
  annotGoSub: $("annot-go-sub"),
  annotClose: $("annot-close"),
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
  makerBook: $("maker-book"),
  makerBookFile: $("maker-book-file"),
  makerBar: $("maker-bar"),
  makerSaid: $("maker-said"),
  makerGo: $("maker-go"),
  makerGoSub: $("maker-go-sub"),
  makerClose: $("maker-close"),
  artmaker: $("artmaker"),
  artmakerWhere: $("artmaker-where"),
  artmakerMake: $("artmaker-make"),
  artmakerAbout: $("artmaker-about"),
  artmakerSaid: $("artmaker-said"),
  artmakerGo: $("artmaker-go"),
  artmakerGoSub: $("artmaker-go-sub"),
  artmakerClose: $("artmaker-close"),
  artmakerOpen: $("artmaker-open"),
  health: $("health"),
  dropper: $("dropper"),
  dropperKind: $("dropper-kind"),
  dropperTitle: $("dropper-title"),
  dropperWhy: $("dropper-why"),
  dropperAsk: $("dropper-ask"),
  dropperSlug: $("dropper-slug"),
  dropperName: $("dropper-name"),
  dropperSaid: $("dropper-said"),
  dropperGo: $("dropper-go"),
  dropperGoSub: $("dropper-go-sub"),
  dropperClose: $("dropper-close"),
  sender: $("sender"),
  senderTitle: $("sender-title"),
  senderFind: $("sender-find"),
  senderList: $("sender-list"),
  senderNewCourse: $("sender-new-course"),
  senderNewProject: $("sender-new-project"),
  senderSaid: $("sender-said"),
  senderClose: $("sender-close")
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

/* ------------------------------------------------------------- the beacon */
/* WHAT BROKE ON THIS PAGE, told to the board: POST /client-error, which puts
   one line in its log. A script or an image that did not arrive, an error
   nothing caught, a rejected promise, a list the board did not answer for.
   The iPad has no console anybody reads, and a request the proxy dropped
   never reached the board, so this is the only way it hears. `keepalive`
   lets it outlive a reload. Rate-limited -- the same line once per page, and
   at most BEACON_BURST a minute -- and it never throws. */
var BEACON_BURST = 6;
var beaconSent = {};
var beaconMinute = { at: 0, n: 0 };

function cut(s, n) { return String(s === undefined || s === null ? "" : s).slice(0, n); }

function beacon(what, src, msg, stack) {
  try {
    var key = what + "|" + src + "|" + msg;
    if (beaconSent[key]) return;
    var now = Date.now();
    if (now - beaconMinute.at > 60000) beaconMinute = { at: now, n: 0 };
    if (beaconMinute.n >= BEACON_BURST) return;
    beaconMinute.n += 1;
    beaconSent[key] = true;
    var p = fetch("/client-error", {
      method: "POST",
      keepalive: true,
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page: "home", what: cut(what, 40), src: cut(src, 300),
                             msg: cut(msg, 500), stack: cut(stack, 2000),
                             ua: cut(navigator.userAgent, 200) })
    });
    if (p && p.catch) p.catch(function () { /* the board is down: nothing to tell */ });
  } catch (e) { /* telling must never be what breaks the page */ }
}

/* Capture phase, because a script, a stylesheet or an image that failed to
   load fires its error on the element and it does not bubble. */
window.addEventListener("error", function (ev) {
  var t = ev && ev.target;
  if (t && t !== window && (t.src || t.href)) {
    beacon("load", t.src || t.href, "did not load (" + cut(t.tagName, 20).toLowerCase() + ")");
    return;
  }
  beacon("error", ev && ev.filename ? ev.filename + ":" + (ev.lineno || 0) : "",
         ev && ev.message, ev && ev.error && ev.error.stack);
}, true);

window.addEventListener("unhandledrejection", function (ev) {
  var r = ev && ev.reason;
  beacon("rejection", "", r && r.message ? r.message : r, r && r.stack);
});

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

/* A session row with its delete beside it: the first tap arms it for 4 s,
   the second posts /session/delete and the session goes to the trash. A past
   session bound to nothing also has "send to…", the sheet that gives it a
   course or project, disabled while its wrap-up is running (`wrapping`):
   that wrap-up may be choosing a subject itself. */
function withDelete(row, rec) {
  var wrap = el("div", "row-wrap");
  wrap.appendChild(row);
  if (rec.view === "slate") wrap.appendChild(giveButton(rec));
  if (rec.ended && !rec.subject) {
    var send = el("button", "row-make", "send to…");
    send.type = "button";
    send.title = "send this session to a course or project";
    send.setAttribute("data-send-for", rec.id);
    send.onclick = function () { openSender(rec); };
    if (rec.wrapping) {
      send.disabled = true;
      send.title = "its wrap-up is running; send it once that is done";
    }
    wrap.appendChild(send);
  }
  var b = el("button", "row-delete", "delete");
  b.type = "button";
  b.title = "delete this session";
  b.setAttribute("data-delete", rec.id);
  var armed = null;
  b.onclick = function () {
    if (!armed) {
      b.textContent = "tap again";
      b.classList.add("armed");
      armed = setTimeout(function () {
        armed = null;
        b.textContent = "delete";
        b.classList.remove("armed");
      }, 4000);
      return;
    }
    clearTimeout(armed);
    armed = null;
    b.disabled = true;
    b.textContent = "deleting";
    postJSON("/session/delete", { id: rec.id }).then(function (got) {
      if (got && got.ok) { wrap.remove(); refresh(); return; }
      b.disabled = false;
      b.classList.remove("armed");
      b.textContent = "delete";
      say((got && got.error) || "the session was not deleted");
    }).catch(function () {
      b.disabled = false;
      b.classList.remove("armed");
      b.textContent = "delete";
      say("the board did not answer; nothing was deleted");
    });
  };
  wrap.appendChild(b);
  return wrap;
}

/* GIVE TO THE TUTOR, on a canvas's row, open or past: a second tap within
   four seconds posts /s/<id>/give, which reopens an ended canvas and wakes
   one turn on all its pages, then opens its board. */
function giveButton(rec) {
  var b = el("button", "row-make", "give to the tutor");
  b.type = "button";
  b.title = "one turn reads every page of this canvas";
  b.setAttribute("data-give-for", rec.id);
  var armed = null;
  b.onclick = function () {
    if (!armed) {
      b.textContent = "tap again";
      b.classList.add("armed");
      armed = setTimeout(function () {
        armed = null;
        b.textContent = "give to the tutor";
        b.classList.remove("armed");
      }, 4000);
      return;
    }
    clearTimeout(armed);
    armed = null;
    b.disabled = true;
    b.textContent = "giving";
    postJSON("/s/" + enc(rec.id) + "/give", {}).then(function (got) {
      if (got && got.ok) { go(got.url || "/s/" + enc(rec.id) + "/board"); return; }
      b.disabled = false;
      b.classList.remove("armed");
      b.textContent = "give to the tutor";
      say((got && got.error) || "the canvas was not given");
    }).catch(function () {
      b.disabled = false;
      b.classList.remove("armed");
      b.textContent = "give to the tutor";
      say("the board did not answer; nothing was given");
    });
  };
  return b;
}

/* PAST SESSIONS, the newest PAST_SHOWN of them, narrowed by the search; the
   rest are one tap away ("show all"), until the page is loaded again. */
var PAST_SHOWN = 10;
var pastAll = false;

function sessionFound(rec, q) {
  return !q || [sessionTitle(rec), rec.subject_name, rec.subject, rec.id]
    .some(function (v) { return v && String(v).toLowerCase().indexOf(q) >= 0; });
}

function paintSessions(data) {
  var list = (data && data.sessions) || [];
  var q = query();
  var open = list.filter(function (r) { return !r.ended; });
  var past = list.filter(function (r) { return !!r.ended && sessionFound(r, q); });
  els.openList.innerHTML = "";
  open.forEach(function (r) { els.openList.appendChild(withDelete(openRow(r), r)); });
  els.openNone.hidden = open.length > 0;
  els.pastList.innerHTML = "";
  var shown = pastAll ? past : past.slice(0, PAST_SHOWN);
  shown.forEach(function (r) { els.pastList.appendChild(withDelete(pastRow(r), r)); });
  els.pastNone.textContent = q ? "No past session matches." : "No session has ended yet.";
  els.pastNone.hidden = past.length > 0;
  els.pastMore.hidden = shown.length >= past.length;
  els.pastMore.textContent = "show all (" + past.length + ")";
}

/* The search, as the lists compare it. */
function query() { return String(els.find.value || "").trim().toLowerCase(); }

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

/* ------------------------------------------------------------------ canvas */
/* A CANVAS is a session in full-slate view (`view: slate`), titled by the
   day: written on with no tutor, filed or handed to one later. */
function today() {
  var d = new Date();
  function two(n) { return (n < 10 ? "0" : "") + n; }
  return d.getFullYear() + "-" + two(d.getMonth() + 1) + "-" + two(d.getDate());
}

function newNotes() {
  if (starting) return;
  starting = true;
  els.actNotes.disabled = true;
  els.actNotesSub.textContent = "opening…";
  postJSON("/sessions/new", { view: "slate", title: "Canvas " + today() })
    .then(function (got) {
      if (got && got.ok && got.url) { go(got.url); return; }
      throw new Error((got && got.error) || "the canvas was not made");
    }).catch(function (e) {
      starting = false;
      els.actNotes.disabled = false;
      els.actNotesSub.textContent = e.message || "the board did not answer";
    });
}

/* ---------------------------------------------------------- annotate a PDF */
/* ONE PDF, INTO A NEW SESSION. It lands in the session's uploads/ with a line
   that wakes nothing (D21); with a subject picked the session is bound to it
   and the upload filed straight into its materials/, its ink id following.
   The session's board then opens it in the reader, by its `doc` address. */
var annotBusy = false;

function annotSay(text, bad) {
  els.annotSaid.hidden = !text;
  els.annotSaid.className = "sheet-line" + (bad ? " bad" : "");
  els.annotSaid.textContent = text || "";
}

/* The address typed into `#annot-url`, when it is one; a file chosen wins. */
function annotAddress() {
  var said = String(els.annotUrl.value || "").trim();
  return /^https?:\/\/[^\s]+$/i.test(said) ? said : "";
}

function paintAnnot() {
  var f = els.annotFile.files && els.annotFile.files[0];
  var u = !f && annotAddress();
  els.annotGo.disabled = annotBusy || !(f || u);
  els.annotGoSub.textContent = annotBusy ? (u ? "fetching…" : "uploading…")
    : f || u ? (els.annotSubject.value ? "into " + els.annotSubject.value
                                       : "into a new session")
    : "choose a PDF, or give its address";
}

/* The subjects in the one picker order (`pickGroups`), Random lessons
   preselected, and "not yet: it stays in the session" last. */
function openAnnot() {
  annotBusy = false;
  annotSay("");
  els.annotBar.hidden = true;
  els.annotFile.value = "";
  els.annotUrl.value = "";
  els.annotSubject.innerHTML = "";
  pickGroups((subjectsData && subjectsData.subjects) || []).forEach(function (g) {
    var host = els.annotSubject;
    if (g[0]) {
      host = el("optgroup");
      host.label = g[0];
      els.annotSubject.appendChild(host);
    }
    g[1].forEach(function (s) {
      var o = el("option", "", subjectName(s));
      o.value = s.id;
      host.appendChild(o);
    });
  });
  var none = el("option", "", "not yet: it stays in the session");
  none.value = "";
  els.annotSubject.appendChild(none);
  els.annotSubject.value = scratchId() || "";
  if (els.annotSubject.value !== (scratchId() || "")) els.annotSubject.value = "";
  paintAnnot();
  els.annot.hidden = false;
}

function closeAnnot() {
  if (annotBusy) return;
  els.annot.hidden = true;
}

/* One XHR, because fetch says nothing about progress. `bar` is the
   <progress> it fills: the annotate sheet's unless another is given. */
function uploadTo(base, file, bar) {
  bar = bar || els.annotBar;
  return new Promise(function (resolve, reject) {
    var form = new FormData();
    form.append("f0", file, file.name);
    var xhr = new XMLHttpRequest();
    xhr.open("POST", base + "/upload");
    xhr.upload.onprogress = function (e) {
      if (!e.lengthComputable || !e.total) return;
      bar.value = Math.floor(100 * e.loaded / e.total);
    };
    xhr.onload = function () {
      var got = {};
      try { got = JSON.parse(xhr.responseText || "{}"); } catch (e) { got = {}; }
      if (xhr.status === 200 && got.ok && (got.files || []).length) {
        resolve(got.files[0]);
        return;
      }
      reject(new Error("the upload failed (" + xhr.status + "): "
                       + (got.error || "the board refused it")));
    };
    xhr.onerror = function () {
      reject(new Error("the upload failed: the board did not answer"));
    };
    xhr.send(form);
  });
}

/* The name a PDF fetched from `url` is shown under before it lands: the
   address's last part, else its host. */
function urlName(url) {
  var m = /^https?:\/\/([^\/?#]+)([^?#]*)/i.exec(url);
  if (!m) return url;
  var last = m[2].split("/").filter(Boolean).pop();
  try { last = last ? decodeURIComponent(last) : ""; } catch (e) { /* as it is */ }
  return last || m[1];
}

/* A file from the iPad goes up with /upload; an address is fetched by the
   board, with /fetch, and answers the same. */
function annotate() {
  var file = els.annotFile.files && els.annotFile.files[0];
  var url = file ? "" : annotAddress();
  var subject = els.annotSubject.value;
  if ((!file && !url) || annotBusy) return;
  if (file && !/\.pdf$/i.test(file.name || "")) {
    annotSay("That is not a PDF.", true);
    return;
  }
  annotBusy = true;
  annotSay("");
  els.annotBar.value = 0;
  els.annotBar.hidden = !!url;
  paintAnnot();
  var sid = "", base = "";
  postJSON("/sessions/new", { title: "Annotate " + (file ? file.name : urlName(url)) })
    .then(function (got) {
      if (!got || !got.ok) throw new Error((got && got.error) || "the session was not made");
      sid = got.id;
      base = "/s/" + enc(sid);
      if (!subject) return null;
      return postJSON(base + "/bind", { subject: subject }).then(function (b) {
        if (!b || !b.ok) throw new Error((b && b.error) || "the session was not bound");
      });
    }).then(function () {
      if (file) return uploadTo(base, file);
      return postJSON(base + "/fetch", { url: url }).then(function (got) {
        if (got && got.ok && (got.files || []).length) return got.files[0];
        throw new Error("it was not fetched: " + ((got && got.error) || "the board refused it"));
      });
    }).then(function (up) {
      if (!subject) return up.doc;
      return postJSON(base + "/file", { upload: up.name }).then(function (f) {
        if (!f || !f.ok) throw new Error((f && f.error) || "it was not filed");
        return f.doc;
      });
    }).then(function (doc) {
      if (!doc) throw new Error("the board cannot read that PDF");
      go(base + "/board" + window.Address.format(
        { session: sid, surface: "doc", doc: doc }));
    }).catch(function (e) {
      annotBusy = false;
      els.annotBar.hidden = true;
      annotSay((e && e.message) || "the board did not answer", true);
      paintAnnot();
    });
}

/* ---------------------------------------------------------------- subjects */
var subjectsData = null;      /* the last /subjects.json */

function subjectRow(s, last) {
  var box = el("div", "subj");
  box.appendChild(subjectLink(s, last));
  var make = el("button", "row-make", "make");
  make.type = "button";
  make.title = "a deck or a paper about " + (s.name || s.id);
  make.setAttribute("data-make-for", s.id);
  make.onclick = function () { openArtmaker(s); };
  box.appendChild(make);
  var drop = el("button", "row-delete", "delete");
  drop.type = "button";
  drop.title = "delete " + (s.name || s.id);
  drop.setAttribute("data-drop-for", s.id);
  drop.onclick = function () { openDropper(s); };
  box.appendChild(drop);
  return box;
}

function subjectLink(s, last) {
  var a = el("a", "row");
  a.href = "/library?subject=" + enc(s.id) + "&from=home";
  a.setAttribute("data-subject", s.id);
  a.appendChild(el("span", "row-name", subjectName(s)));
  var open = ((sessionsData && sessionsData.sessions) || []).filter(function (r) {
    return !r.ended && r.subject === s.id;
  }).length;
  var bits = [];
  if (open) bits.push(plural(open, "open session", "open sessions"));
  if (last) bits.push("last: " + day(last));
  a.appendChild(el("span", "row-sub", bits.length ? bits.join("  ·  ") : s.id));
  return a;
}

function subjectName(s) { return s.name || s.slug || s.id; }

/* THE ONE ORDER every picker offers subjects in, here and on the board and
   the canvas: Random lessons, the catch-all (/subjects.json `scratch`), first
   and under no heading; then Recent, the RECENT most recently used; then
   every other course, then every other project, each most recently used
   first. `[[heading, [subject...]]]`, empty groups left out. */
var RECENT = 4;

function scratchId() { return (subjectsData && subjectsData.scratch) || null; }

function pickGroups(list) {
  var last = activity();
  var sorted = byUse(list);
  var top = sorted.filter(function (s) { return s.id === scratchId(); });
  var rest = sorted.filter(function (s) { return s.id !== scratchId(); });
  var recent = rest.filter(function (s) { return !!last[s.id]; }).slice(0, RECENT);
  rest = rest.filter(function (s) { return recent.indexOf(s) < 0; });
  return [["", top], ["Recent", recent],
          ["Courses", rest.filter(function (s) { return s.kind !== "project"; })],
          ["Projects", rest.filter(function (s) { return s.kind === "project"; })]]
    .filter(function (g) { return g[1].length; });
}

/* THE MOST RECENT SESSION ON EACH SUBJECT, by subject id: the later of when
   it opened and when it ended, as session.json writes them, which compare as
   text. A subject no session has touched is not in it. */
function activity() {
  var out = {};
  ((sessionsData && sessionsData.sessions) || []).forEach(function (r) {
    if (!r.subject) return;
    var at = [r.opened, r.ended].filter(Boolean).sort().pop();
    if (at && (!out[r.subject] || at > out[r.subject])) out[r.subject] = at;
  });
  return out;
}

/* Every subject, the most recently used first, then the untouched ones by
   name. Shared by the lists and the send sheet. */
function byUse(list) {
  var last = activity();
  return list.slice().sort(function (a, b) {
    var x = last[a.id] || "", y = last[b.id] || "";
    if (x !== y) return x > y ? -1 : 1;
    var m = subjectName(a).toLowerCase(), n = subjectName(b).toLowerCase();
    return m < n ? -1 : m > n ? 1 : 0;
  });
}

function subjectFound(s, q) {
  return !q || [s.name, s.slug, s.id]
    .some(function (v) { return v && String(v).toLowerCase().indexOf(q) >= 0; });
}

function paintSubjects(data) {
  var q = query();
  var last = activity();
  var list = byUse((data && data.subjects) || []).filter(function (s) {
    return subjectFound(s, q);
  });
  var courses = list.filter(function (s) { return s.kind === "course"; });
  var projects = list.filter(function (s) { return s.kind === "project"; });
  els.courseList.innerHTML = "";
  courses.forEach(function (s) { els.courseList.appendChild(subjectRow(s, last[s.id])); });
  els.courseNone.textContent = q ? "No course matches." : "No course yet.";
  els.courseNone.hidden = courses.length > 0;
  els.projectList.innerHTML = "";
  projects.forEach(function (s) { els.projectList.appendChild(subjectRow(s, last[s.id])); });
  els.projectNone.textContent = q ? "No project matches." : "No project yet.";
  els.projectNone.hidden = projects.length > 0;
}

/* --------------------------------------------- deleting a subject, the sheet */
/* `GET /subject/delete?subject=` first, which is read-only: whether it may
   hold patient data (`phi` at HEAD), and everything else in the way, all of
   it in `blocker`. Only when nothing is in the way is the slug asked for, and
   Go wakes only on it typed exactly. The server decides again on the POST. */
var dropFor = null;
var dropOpen = false;         /* the check said nothing is in the way */
var dropping = false;

var PHI_WHY = "It may hold patient data, so the iPad never removes it. It is "
  + "removed on the cluster: move its fenced data where its agreement says, "
  + "then git rm it and push from the cluster checkout.";

function openDropper(s) {
  dropFor = s;
  dropOpen = false;
  dropping = false;
  els.dropperKind.textContent = "delete " + (s.kind === "project" ? "project" : "course");
  els.dropperTitle.textContent = subjectName(s);
  els.dropperSlug.textContent = s.slug || "";
  els.dropperName.value = "";
  els.dropperAsk.hidden = true;
  els.dropperWhy.textContent = "Asking the board whether it can go…";
  dropSay("");
  paintDropper();
  els.dropper.hidden = false;
  getJSON("/subject/delete?subject=" + enc(s.id)).then(function (got) {
    if (dropFor === s) paintDropCheck(got || {});
  }).catch(function () {
    if (dropFor !== s) return;
    els.dropperWhy.textContent = "The board did not say whether it can go, so "
      + "nothing can be deleted yet.";
  });
}

function paintDropCheck(got) {
  var why = got.why || "";
  var blocker = got.blocker || "";
  var held = got.sessions || [];
  els.dropperWhy.innerHTML = "";
  if (got.ok === false && !why) {
    els.dropperWhy.textContent = got.error || "The board would not say whether it can go.";
  } else if (why === "phi" && got.phi === true) {
    /* Patient data said at HEAD. Not said at all (`phi` null: no
       tutorboard.json there, or no phi key) falls to the board's sentence,
       which names what is missing. */
    els.dropperWhy.textContent = PHI_WHY;
  } else if (why === "open-session" && held.length) {
    els.dropperWhy.appendChild(document.createTextNode("Open on it: "));
    held.forEach(function (sid, i) {
      if (i) els.dropperWhy.appendChild(document.createTextNode(", "));
      var a = el("a", "", sessionLabel(sid));
      a.href = "/s/" + enc(sid) + "/board";
      els.dropperWhy.appendChild(a);
    });
    els.dropperWhy.appendChild(document.createTextNode(
      ". End or delete " + (held.length === 1 ? "it" : "them") + " first."));
    /* An open session is only the first thing in the way; the board's
       sentence names every one, so it follows the links. */
    if (blocker) {
      els.dropperWhy.appendChild(el("br", ""));
      els.dropperWhy.appendChild(document.createTextNode(blocker));
    }
  } else if (why || blocker) {
    els.dropperWhy.textContent = blocker || why;
  } else {
    dropOpen = true;
    if (got.slug) els.dropperSlug.textContent = got.slug;
    els.dropperWhy.textContent = "Nothing is open on it.";
    els.dropperAsk.hidden = false;
    try { els.dropperName.focus(); } catch (e) { /* a page without focus */ }
  }
  paintDropper();
}

/* A session as the sheet names it: its title too, when this page has it. */
function sessionLabel(sid) {
  var rec = ((sessionsData && sessionsData.sessions) || []).filter(function (r) {
    return r.id === sid;
  })[0];
  return rec ? sessionTitle(rec) + " (" + sid + ")" : sid;
}

function closeDropper() {
  if (dropping) return;
  dropFor = null;
  els.dropper.hidden = true;
}

function dropSay(text, bad) {
  els.dropperSaid.hidden = !text;
  els.dropperSaid.className = "sheet-line" + (bad ? " bad" : "");
  els.dropperSaid.textContent = text || "";
}

function dropTyped() {
  var slug = els.dropperSlug.textContent || "";
  return !!slug && els.dropperName.value === slug;
}

function paintDropper() {
  els.dropperGo.hidden = !dropOpen;
  els.dropperGo.disabled = dropping || !dropOpen || !dropTyped();
  els.dropperGoSub.textContent = dropping ? "deleting…"
    : dropTyped() ? "to the trash, in one commit" : "type its name first";
}

function dropSubject() {
  var s = dropFor;
  if (!s || dropping || !dropOpen || !dropTyped()) return;
  dropping = true;
  dropSay("");
  paintDropper();
  postJSON("/subject/delete", { subject: s.id, typed: els.dropperName.value })
    .then(function (got) {
      dropping = false;
      if (!got || !got.ok) {
        paintDropper();
        dropSay((got && got.error) || "it was not deleted", true);
        return;
      }
      closeDropper();
      say(subjectName(s) + " is in the trash" + (got.trash ? " (" + got.trash + ")" : "") + ".");
      return refresh();
    }).catch(function () {
      dropping = false;
      paintDropper();
      dropSay("the board did not answer; nothing was deleted", true);
    });
}

/* --------------------------------------- sending a past session, the sheet */
/* An unbound session that has ended goes to a course or project with POST
   /s/<id>/send: bound, its uploads filed into that subject's materials/, and
   its wrap-up (write-ups from the recap, TUTOR.md) written there. Every
   subject is offered, the most recently used first, narrowed by the sheet's
   own search; + new makes one through the maker sheet and sends it there. */
var sendFor = null;
var sending = false;

function openSender(rec) {
  sendFor = rec;
  sending = false;
  els.senderTitle.textContent = sessionTitle(rec);
  els.senderFind.value = "";
  senderSay("");
  paintSender();
  els.sender.hidden = false;
}

function closeSender() {
  if (sending) return;
  els.sender.hidden = true;
}

function senderSay(text, bad) {
  els.senderSaid.hidden = !text;
  els.senderSaid.className = "sheet-line" + (bad ? " bad" : "");
  els.senderSaid.textContent = text || "";
}

function paintSender() {
  var q = String(els.senderFind.value || "").trim().toLowerCase();
  els.senderList.innerHTML = "";
  var found = ((subjectsData && subjectsData.subjects) || []).filter(function (s) {
    return subjectFound(s, q);
  });
  pickGroups(found).forEach(function (g) {
    if (g[0]) els.senderList.appendChild(el("p", "sender-group", g[0]));
    g[1].forEach(function (s) {
      var b = el("button");
      b.type = "button";
      b.disabled = sending;
      b.setAttribute("data-id", s.id);
      b.appendChild(el("span", "sender-kind", s.kind === "project" ? "project" : "course"));
      b.appendChild(el("span", "", subjectName(s)));
      b.onclick = function () { sendTo(s.id, subjectName(s)); };
      els.senderList.appendChild(b);
    });
  });
  if (!els.senderList.children.length) {
    els.senderList.appendChild(el("p", "hint", q ? "None matches." : "No course or project yet."));
  }
  els.senderNewCourse.disabled = sending;
  els.senderNewProject.disabled = sending;
}

function sendTo(subject, name) {
  var rec = sendFor;
  if (!rec || sending) return;
  sending = true;
  els.sender.hidden = false;
  senderSay("sending it to " + name + "…");
  paintSender();
  postJSON("/s/" + enc(rec.id) + "/send", { subject: subject }).then(function (got) {
    sending = false;
    if (!got || !got.ok) {
      paintSender();
      senderSay((got && (got.error || got.detail)) || "it was not sent", true);
      return;
    }
    closeSender();
    var filed = got.filed && typeof got.filed === "object" ? got.filed.length : got.filed;
    var left = (got.refused || []).map(function (r) { return r.upload; });
    say(sessionTitle(rec) + " went to " + ((got.sent && got.sent.name) || name)
        + (filed ? ", with " + plural(filed, "upload", "uploads") + " filed" : "") + "."
        + (left.length ? " " + left.join(", ") + " stayed in the session: a file of "
           + "that name is already in its materials." : ""));
    return refresh();
  }).catch(function () {
    sending = false;
    paintSender();
    senderSay("the board did not answer; it was not sent", true);
  });
}

/* + new from the send sheet: the maker sheet, then the session sent to what
   it made. Closing the maker instead leaves the session where it was. */
function senderNew(kind) {
  var rec = sendFor;
  if (!rec || sending) return;
  els.sender.hidden = true;
  openMaker(kind, function (made) {
    if (!made || !made.id) return;
    sendFor = rec;
    sendTo(made.id, made.name || made.id);
  });
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
var makerThen = null;         /* what is done with the subject once made */

/* `then(subject)` runs once the subject is made: the send sheet's + new,
   which sends its session there. */
function openMaker(kind, then) {
  makerKind = kind === "project" ? "project" : "course";
  makerPhi = null;
  making = false;
  makerThen = then || null;
  els.makerKind.textContent = "new " + makerKind
    + (makerThen ? ", and the session sent to it" : "");
  els.makerName.value = "";
  els.makerName.placeholder = makerKind === "course" ? "Linear Algebra" : "Diarization";
  els.makerPhi.hidden = makerKind !== "project";
  /* A textbook only for a course made from + new: the send sheet's maker
     sends an existing session there instead. */
  els.makerBook.hidden = makerKind !== "course" || !!makerThen;
  els.makerBookFile.value = "";
  els.makerBar.hidden = true;
  els.makerSaid.hidden = true;
  paintMaker();
  els.maker.hidden = false;
  try { els.makerName.focus(); } catch (e) { /* a page without focus */ }
}

function closeMaker() { makerThen = null; els.maker.hidden = true; }

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
  var book = makerBook();
  els.makerGo.disabled = making || !!want;
  els.makerGoSub.textContent = making ? (book ? "uploading the textbook…" : "making it…")
    : want || (book ? "then its textbook is indexed" : "")
    || (makerKind === "project" && makerPhi
        ? "a project holding patient data: phi/ and results/ ignored"
        : "one commit: tutorboard.json and TUTOR.md");
}

/* The textbook PDF chosen on the sheet, or null. */
function makerBook() {
  if (els.makerBook.hidden) return null;
  var f = els.makerBookFile.files && els.makerBookFile.files[0];
  return f || null;
}

/* A NEW COURSE WITH ITS BOOK: annotate()'s chain -- a session, bound to the
   course, the PDF uploaded into it -- then `/textbook`, which files it into
   textbook/ and indexes it; the session's board opens, and a `[textbook]`
   card arrives there when the index is done. */
function bookInto(subject, file) {
  var base = "";
  els.makerBar.value = 0;
  els.makerBar.hidden = false;
  return postJSON("/sessions/new", { title: "Textbook " + (subject.name || subject.id) })
    .then(function (got) {
      if (!got || !got.ok) throw new Error((got && got.error) || "the session was not made");
      base = "/s/" + enc(got.id);
      return postJSON(base + "/bind", { subject: subject.id });
    }).then(function (b) {
      if (!b || !b.ok) throw new Error((b && b.error) || "the session was not bound");
      return uploadTo(base, file, els.makerBar);
    }).then(function (up) {
      return postJSON(base + "/textbook", { upload: up.name });
    }).then(function (t) {
      if (!t || !t.ok) throw new Error((t && t.error) || "the textbook was not taken");
      go(base + "/board");
    });
}

function makeSubject() {
  var name = els.makerName.value.trim();
  if (!name || making) return;
  if (makerKind === "project" && makerPhi === null) return;
  var book = makerBook();
  if (book && !/\.pdf$/i.test(book.name || "")) {
    makerSay("The textbook is not a PDF.", true);
    return;
  }
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
    if (book) {
      making = true;
      paintMaker();
      return bookInto(got.subject, book).catch(function (e) {
        making = false;
        els.makerBar.hidden = true;
        paintMaker();
        makerSay((e && e.message || "the board did not answer")
                 + ". The course is made; add the textbook from its library.", true);
        refresh();
      });
    }
    var then = makerThen;
    closeMaker();
    if (then) then(got.subject);
    return refresh();
  }).catch(function () {
    making = false;
    paintMaker();
    makerSay("the board did not answer", true);
  });
}

/* ---------------------------------------------------------------- notices */
/* A machinery line with no session to wake (D16). Dismissing one is this
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

/* ------------------------------------------------------- the sync health */
/* GET /sync.json: `lines` are the sentences, worst first (`sync.health`):
   not synced, then the machine's brew and tools lines. */
function paintHealth(data) {
  var lines = (data && data.lines) || [];
  els.health.innerHTML = "";
  lines.forEach(function (l) { els.health.appendChild(el("div", "health-line", l)); });
  els.health.hidden = lines.length === 0;
}

function loadHealth() {
  return getJSON("/sync.json").then(function (got) {
    paintHealth(got || null);
  }).catch(function () { /* the next refresh asks again */ });
}

/* -------------------------------------------------------------- addresses */
var routed = "";              /* the address text this page last followed */

function say(text) {
  els.said.hidden = !text;
  els.said.textContent = text || "";
}

function route() {
  if (!window.Address) return;
  var a = null;
  try { a = window.Address.parse(window.location.hash || ""); } catch (e) { a = null; }
  if (!a || a.text === routed) return;
  routed = a.text;
  go("/s/" + enc(a.session) + "/board" + a.text);
}

window.addEventListener("hashchange", route);

/* ------------------------------------------------------------------- tutor */
/* The machine's one provider setting, set with POST /default-agent: every
   session's next turn goes to it, or to its fallback when it cannot. Drawn by
   `who.js`. The note under the buttons always says who takes the next turn
   (the listing's `machine`, or its `why` when that is not the provider);
   what a tap said stands in for it until the listing is read again, which
   is every refresh. */
var lastAssistants = null;
var whoSaved = null;
var whoTold = "";

function agentLabel(assistants, name) {
  var a = ((assistants && assistants.agents) || []).filter(function (x) {
    return x.name === name;
  })[0];
  return (a && a.label) || name;
}

function sentence(s) { s = String(s || ""); return /[.!?]$/.test(s) ? s : s + "."; }

function nextTurn(assistants) {
  if (assistants.why) return sentence(assistants.why);
  if (assistants.machine) {
    return agentLabel(assistants, assistants.machine) + " takes the next turn in every session.";
  }
  return "Nobody can take a turn here right now.";
}

function paintWho(assistants) {
  if (!window.WhoChoice || !assistants) { els.who.hidden = true; return; }
  var have = window.WhoChoice.offerable(assistants);
  els.who.hidden = have.length < 2;
  if (els.who.hidden) return;
  window.WhoChoice.draw(els.whoWays, have, whoSaved || assistants["default"], {
    say: function (m) { whoTold = m; els.whoNote.textContent = sentence(m); },
    pick: function (a) { setDefaultAgent(a.name); }
  });
  els.whoNote.textContent = whoTold ? sentence(whoTold)
    : whoSaved ? "asking for " + agentLabel(assistants, whoSaved) + "…"
    : nextTurn(assistants);
}

function setDefaultAgent(name) {
  whoSaved = name;
  whoTold = "";
  paintWho(lastAssistants);
  postJSON("/default-agent", { agent: name }).then(function (got) {
    if (got && got.ok) {
      if (got.assistants) {
        lastAssistants = got.assistants;
        if (lastAssistants["default"] === whoSaved) whoSaved = null;
      } else {
        /* Who takes the next turn: the provider, or the fallback and why. */
        whoTold = got.why || agentLabel(lastAssistants, got.machine || name)
          + " takes the next turn in every session";
      }
    } else {
      whoSaved = null;
      whoTold = (got && (got.detail || got.error)) || "that did not take";
    }
    paintWho(lastAssistants);
  }).catch(function () {
    whoSaved = null;
    whoTold = "the board did not answer";
    paintWho(lastAssistants);
  });
}

function loadAssistants() {
  return getJSON("/assistants.json").then(function (got) {
    lastAssistants = (got && got.assistants) || null;
    if (whoSaved && lastAssistants && lastAssistants["default"] === whoSaved) whoSaved = null;
    whoTold = "";
    paintWho(lastAssistants);
  }).catch(function () { paintWho(lastAssistants); });
}

/* ------------------------------------------------------------------- theme */
/* The theme is `typeface.js`'s (`Typeface.theme`); this only says which. */
function paintTheme() {
  els.themeNow.textContent = document.body.dataset.mode || "auto";
}

/* -------------------------------------------------------------------- load */
/* A list the page cannot do without: a proxy's 502 (an empty body) or an
   answer that is not JSON is a failure, told to the board by its URL. */
function needed(url) {
  return fetch(url, { credentials: "same-origin", cache: "no-store" }).then(function (r) {
    if (r.status && r.status >= 400) throw new Error(url + " answered " + r.status);
    return r.json().catch(function () { throw new Error(url + " was not JSON"); });
  }).catch(function (e) {
    var told = new Error((e && e.message) || url + " failed");
    told.told = true;
    beacon("fetch", url, told.message);
    throw told;
  });
}

/* A refresh that failed is tried again RETRY_FIRST later, then twice as long
   each time up to RETRY_MOST, the dot dead meanwhile; one that lands puts the
   wait back. The 20 s poll goes on beside it. */
var RETRY_FIRST = 2000;
var RETRY_MOST = 60000;
var retryWait = RETRY_FIRST;
var retryTimer = null;

function refresh() {
  return Promise.all([
    needed("/sessions.json"),
    needed("/subjects.json"),
    getJSON("/notices.json").catch(function () { return null; })
  ]).then(function (all) {
    els.dot.className = "dot live";
    retryWait = RETRY_FIRST;
    sessionsData = all[0] || { sessions: [] };
    subjectsData = all[1] || { subjects: [] };
    paintSessions(sessionsData);
    paintSubjects(subjectsData);
    if (all[2]) paintNotices(all[2]);
    route();
    loadHealth();
    loadAssistants();
  }).catch(function (e) {
    /* A paint that threw is this page's bug, and the board hears it too. */
    if (!e || !e.told) beacon("paint", "refresh", e && e.message, e && e.stack);
    els.dot.className = "dot dead";
    if (retryTimer) return;
    retryTimer = setTimeout(function () {
      retryTimer = null;
      refresh();
    }, retryWait);
    retryWait = Math.min(retryWait * 2, RETRY_MOST);
  });
}

/* The lists again, as they were last read, with the search applied. */
function repaint() {
  if (sessionsData) paintSessions(sessionsData);
  if (subjectsData) paintSubjects(subjectsData);
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
els.makerBookFile.onchange = paintMaker;
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
els.actNotes.onclick = newNotes;
els.actAnnotate.onclick = openAnnot;
els.annotFile.addEventListener("change", function () { annotSay(""); paintAnnot(); });
els.annotUrl.addEventListener("input", function () { annotSay(""); paintAnnot(); });
els.annotSubject.addEventListener("change", paintAnnot);
els.annotGo.onclick = annotate;
els.annotClose.onclick = closeAnnot;
els.annot.addEventListener("click", function (ev) {
  if (ev.target === els.annot) closeAnnot();
});
els.themeBtn.onclick = function () {
  if (window.Typeface) window.Typeface.theme("next");
  paintTheme();
};
els.reload.onclick = function () { window.location.reload(); };
els.find.addEventListener("input", repaint);
els.pastMore.onclick = function () { pastAll = true; repaint(); };
els.dropperName.addEventListener("input", function () { dropSay(""); paintDropper(); });
els.dropperName.addEventListener("keydown", function (ev) {
  if (ev.key === "Enter") dropSubject();
});
els.dropperGo.onclick = dropSubject;
els.dropperClose.onclick = closeDropper;
els.dropper.addEventListener("click", function (ev) {
  if (ev.target === els.dropper) closeDropper();
});
els.senderFind.addEventListener("input", paintSender);
els.senderNewCourse.onclick = function () { senderNew("course"); };
els.senderNewProject.onclick = function () { senderNew("project"); };
els.senderClose.onclick = closeSender;
els.sender.addEventListener("click", function (ev) {
  if (ev.target === els.sender) closeSender();
});
document.addEventListener("keydown", function (ev) {
  if (ev.key !== "Escape") return;
  if (!els.maker.hidden) closeMaker();
  if (!els.artmaker.hidden) closeArtmaker();
  if (!els.annot.hidden) closeAnnot();
  if (!els.dropper.hidden) closeDropper();
  if (!els.sender.hidden) closeSender();
});
paintTheme();
document.addEventListener("DOMContentLoaded", paintTheme);

/* THE WAY BACK from a pinched page, placed by `recentre.js` as on the board,
   under its own key so where it is put is kept; it starts down the right
   edge, below the bar, so the dot and the wordmark are never under it.
   Shown only here: unplaced, it would sit at the bar's top-left. */
if (els.panic && window.Recentre) {
  els.panic.hidden = false;
  window.Recentre.mount({ key: "home.panic", at: { x: .975, y: .16 },
                          buttons: [{ el: els.panic }] });
}

refresh();
/* The boot check at the end of home.html reads this: the lists were asked
   for, so the page is running. */
window.HomeBooted = true;
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
