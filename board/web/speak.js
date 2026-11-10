/* ==========================================================================
   speak.js -- the board speaks and listens.

   THE THIRD ANSWER TAB. `#tab-speak` opens `#speakbox` in the answer panel:
   record and stop, a level meter while recording, and the last heard block
   ("heard: ..."). A take is posted as multipart to `/s/<id>/speech/say`
   (`routes/speaking.py`), which answers with the heard record; the tutor is
   given words, never the audio.

   THE MICROPHONE IS ASKED FOR ON A TAP AND LET GO AFTER EVERY TAKE.
   `getUserMedia` runs only from the record button, and every track of the
   stream is stopped when the take ends, so the iPad's recording light goes
   out between takes. The recording is `audio/mp4` where the browser can make
   it (Safari), else `audio/webm;codecs=opus` (Chrome, Firefox), else
   whatever MediaRecorder picks. A take stops itself at MAX_TAKE_MS.

   SPEAKING. Every card gets a speak button (`.card-speak`, in its head, or on
   the card when it has none): POST `/speech/card` reads the card's prose and
   answers with a phrase URL. A card's `say` fence is rendered by board.js as
   `.say-phrase` with a play button; a tap plays it. Audio is fetched whole
   into a Blob and played from an object URL, because nothing on the server
   answers a Range request and Safari will not play an `<audio src>` that
   cannot seek. Nothing plays unasked.

   board.js owns the page and hands over what this needs (`init`): its
   session fetch, the question being answered, whether the session has ended,
   and what to do when a take is sent. Loaded before board.js.
   ========================================================================== */

(function () {
"use strict";

var MAX_TAKE_MS = 30000;
var MIMES = ["audio/mp4", "audio/webm;codecs=opus"];

var hooks = {};
var els = {};
var started = false;

var defaults = null;       /* the subject's `speech` block, or null */
var lastHeard = "";        /* the heard block painted, as JSON */

var take = null;           /* the take being recorded */
var player = null;         /* the one shared <audio> */
var playUrl = null;        /* its current object URL */
var playing = false;

function $(id) { return document.getElementById(id); }

function init(h) {
  hooks = h || {};
  els = {
    tab: $("tab-speak"),
    box: $("speakbox"),
    rec: $("speak-rec"),
    meter: $("speak-meter"),
    level: $("speak-level"),
    state: $("speak-state"),
    heard: $("heard"),
  };
  if (started) return;
  started = true;
  if (els.rec) els.rec.addEventListener("click", function () {
    if (take) stop(); else record();
  });
  /* A phrase's play button and a card's speak button, wherever they are:
     cards are rebuilt by the board's reconcile, so nothing is bound to them. */
  document.addEventListener("click", function (e) {
    var t = e.target && e.target.closest ? e.target : null;
    if (!t) return;
    var play = t.closest(".say-play");
    if (play) {
      e.preventDefault();
      e.stopPropagation();
      phrase(play.closest(".say-phrase"));
      return;
    }
    var card = t.closest(".card-speak");
    if (card) {
      e.preventDefault();
      e.stopPropagation();
      speakCard(card);
    }
  }, true);
}

/* -------------------------------------------------------------- the player */

function getPlayer() {
  if (!player) {
    player = new Audio();
    player.preload = "auto";
  }
  return player;
}

/* Fetched whole, then played from a Blob: no Range support on the server. */
function fetchBlob(url) {
  return fetch(url).then(function (r) {
    if (!r.ok) throw new Error(r.status === 404 ? "not made yet" : "HTTP " + r.status);
    return r.blob();
  });
}

/* Plays now: every play starts from a tap. */
function playNow(url) {
  return fetchBlob(url).then(function (blob) {
    var p = getPlayer();
    if (playUrl) { try { URL.revokeObjectURL(playUrl); } catch (e) {} }
    playUrl = URL.createObjectURL(blob);
    p.src = playUrl;
    playing = true;
    var got = p.play();
    if (got && got.catch) got.catch(function () { playing = false; });
  });
}

/* --------------------------------------------------------------- phrases */

function phraseOf(node) {
  if (!node) return null;
  return { sha: node.dataset.sha, lang: node.dataset.lang,
           text: node.dataset.text || "" };
}

/* A phrase's play button: play it. */
function phrase(node) {
  var p = phraseOf(node);
  if (!node || !p || !p.sha) return null;
  var url = "/speech/" + p.sha + ".m4a";
  node.classList.add("busy");
  return playNow(url).then(function () {
    node.classList.remove("busy");
    node.classList.remove("failed");
  }, function (err) {
    node.classList.remove("busy");
    node.classList.add("failed");
    node.title = String(err && err.message || err);
  });
}

/* ------------------------------------------------------------ a card read */

function speakCard(btn) {
  var card = btn.closest("[data-card]");
  if (!card || !hooks.api) return null;
  btn.classList.add("busy");
  return speakCardId(card.dataset.card).then(function () {
    btn.classList.remove("busy");
    btn.classList.remove("failed");
    btn.title = "read this card aloud";
  }, function (err) {
    btn.classList.remove("busy");
    btn.classList.add("failed");
    btn.title = String(err && err.message || err);
  });
}

function speakCardId(id) {
  return hooks.api("/speech/card", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ card: id }),
  }).then(function (r) {
    return r.json().catch(function () { return { ok: false, error: "HTTP " + r.status }; });
  }).then(function (got) {
    if (!got || !got.ok) throw new Error((got && got.error) || "could not be spoken");
    return playNow(got.url);
  });
}

/* One speak button per card. Idempotent: the reconcile keeps nodes. */
function decorate() {
  Array.prototype.forEach.call(document.querySelectorAll("article.card[data-card]"),
                               function (card) {
    if (card.dataset.kind === "pending") return;
    if (card.querySelector(".card-speak")) return;
    var b = document.createElement("button");
    b.type = "button";
    b.className = "card-speak";
    b.title = "read this card aloud";
    b.setAttribute("aria-label", "read this card aloud");
    b.textContent = "▶ speak";
    var head = card.querySelector(".card-head");
    if (head) {
      var num = head.querySelector(".card-num");
      head.insertBefore(b, num || null);
    } else {
      b.classList.add("bare");
      card.insertBefore(b, card.firstChild);
    }
  });
}

/* --------------------------------------------------------------- the take */

function mime() {
  var MR = window.MediaRecorder;
  if (!MR || typeof MR.isTypeSupported !== "function") return "";
  for (var i = 0; i < MIMES.length; i++) {
    try { if (MR.isTypeSupported(MIMES[i])) return MIMES[i]; } catch (e) {}
  }
  return "";
}

function say(text, cls) {
  if (!els.state) return;
  els.state.textContent = text || "";
  els.state.className = cls || "";
}

function record() {
  if (take) return Promise.resolve();
  if (hooks.ended && hooks.ended()) { say("this session has ended", "bad"); return Promise.resolve(); }
  var md = navigator.mediaDevices;
  if (!md || !md.getUserMedia || !window.MediaRecorder) {
    say("this browser cannot record", "bad");
    return Promise.resolve();
  }
  var t = { chunks: [], stream: null, rec: null, timer: null, ctx: null, raf: null };
  take = t;
  say("asking for the microphone…");
  return md.getUserMedia({ audio: true }).then(function (stream) {
    if (take !== t) { stopTracks(stream); return; }
    t.stream = stream;
    var type = mime();
    t.type = type;
    try {
      t.rec = type ? new window.MediaRecorder(stream, { mimeType: type })
                   : new window.MediaRecorder(stream);
    } catch (e) {
      take = null;
      stopTracks(stream);
      say("could not record: " + e.message, "bad");
      return;
    }
    t.rec.ondataavailable = function (e) { if (e.data && e.data.size) t.chunks.push(e.data); };
    t.rec.onstop = function () { finish(t); };
    t.rec.start();
    meter(t);
    t.timer = setTimeout(stop, MAX_TAKE_MS);
    paintRecording(true);
    say("recording — tap stop when done");
  }, function (err) {
    take = null;
    paintRecording(false);
    say("no microphone: " + ((err && (err.message || err.name)) || err), "bad");
  });
}

function stop() {
  var t = take;
  if (!t) return;
  clearTimeout(t.timer);
  if (t.rec && t.rec.state !== "inactive") {
    try { t.rec.stop(); return; } catch (e) {}
  }
  finish(t);
}

function stopTracks(stream) {
  if (!stream || !stream.getTracks) return;
  stream.getTracks().forEach(function (tr) { try { tr.stop(); } catch (e) {} });
}

/* The level meter: an analyser on the stream, read each frame. */
function meter(t) {
  var AC = window.AudioContext || window.webkitAudioContext;
  if (!AC || !els.level) return;
  try {
    t.ctx = new AC();
    var src = t.ctx.createMediaStreamSource(t.stream);
    var an = t.ctx.createAnalyser();
    an.fftSize = 512;
    src.connect(an);
    t.src = src;
    var buf = new Uint8Array(an.fftSize);
    var tick = function () {
      if (take !== t) return;
      an.getByteTimeDomainData(buf);
      var sum = 0;
      for (var i = 0; i < buf.length; i++) {
        var v = (buf[i] - 128) / 128;
        sum += v * v;
      }
      var rms = Math.sqrt(sum / buf.length);
      els.level.style.width = Math.min(100, Math.round(rms * 300)) + "%";
      t.raf = requestAnimationFrame(tick);
    };
    tick();
  } catch (e) { t.ctx = null; }
}

function finish(t) {
  if (t.done) return;
  t.done = true;
  clearTimeout(t.timer);
  if (t.raf) { try { cancelAnimationFrame(t.raf); } catch (e) {} }
  stopTracks(t.stream);
  if (t.src) { try { t.src.disconnect(); } catch (e) {} }
  if (t.ctx && t.ctx.close) { try { t.ctx.close(); } catch (e) {} }
  if (take === t) take = null;
  paintRecording(false);
  if (els.level) els.level.style.width = "0%";
  var type = (t.rec && t.rec.mimeType) || t.type || "audio/mp4";
  var blob = new Blob(t.chunks, { type: type });
  if (!blob.size) { say("nothing was recorded", "bad"); return; }
  send(blob, type);
}

function send(blob, type) {
  var ext = /webm/.test(type) ? "webm" : /ogg/.test(type) ? "ogg" : "m4a";
  var form = new FormData();
  form.append("audio", blob, "take." + ext);
  var q = hooks.question ? hooks.question() : null;
  if (q) form.append("answers", q);
  var lang = (defaults && defaults.lang) || "en-US";
  form.append("lang", lang);
  say("listening…");
  if (els.rec) els.rec.disabled = true;
  var began = Date.now();
  return hooks.api("/speech/say", { method: "POST", body: form }).then(function (r) {
    return r.json().catch(function () { return { ok: false, error: "HTTP " + r.status }; });
  }).then(function (got) {
    if (els.rec) els.rec.disabled = false;
    if (!got || !got.ok) {
      say((got && got.error) || "not heard", "bad");
      return;
    }
    say("heard in " + ((Date.now() - began) / 1000).toFixed(1) + " s");
    showHeard(fromRecord(got.heard));
    if (hooks.sent) hooks.sent();
  }, function (err) {
    if (els.rec) els.rec.disabled = false;
    say("not sent: " + ((err && err.message) || err), "bad");
  });
}

function paintRecording(on) {
  if (els.rec) {
    els.rec.classList.toggle("on", !!on);
    els.rec.textContent = on ? "■ stop" : "● record";
  }
  if (els.meter) els.meter.classList.toggle("on", !!on);
}

/* ------------------------------------------------------ the heard block */

/* What `/speech/say` answered (`hear.take`'s record) as the block draws it. */
function fromRecord(rec) {
  rec = rec || {};
  return { text: rec.heard || "" };
}

/* A speech turn (`routes/speaking.say`'s record) as the block draws it. */
function fromTurn(t) {
  return { text: t.text || "" };
}

function showHeard(h) {
  if (!els.heard) return;
  var key = JSON.stringify(h || null);
  if (key === lastHeard) return;
  lastHeard = key;
  els.heard.innerHTML = "";
  if (!h) { els.heard.hidden = true; return; }
  els.heard.hidden = false;
  var line = document.createElement("div");
  line.className = "heard-text";
  line.textContent = "heard: " + (h.text || "(nothing)");
  els.heard.appendChild(line);
}

/* --------------------------------------------------------------- per frame */

/* Every frame: the subject's defaults, the speak buttons, and the newest
   speech turn as the heard block. */
function paint(data) {
  data = data || {};
  if (data.speech !== undefined) defaults = data.speech || null;
  decorate();
  var newest = null;
  (data.turns || []).forEach(function (t) {
    if (t.kind === "speech" && (!newest || (t.t || 0) >= (newest.t || 0))) newest = t;
  });
  if (newest) showHeard(fromTurn(newest));
}

/* The tab is the board's: this only shows or hides the box. */
function show(on) {
  if (els.box) els.box.hidden = !on;
  if (els.tab) els.tab.classList.toggle("on", !!on);
  if (!on && take) stop();
}

window.Speak = {
  init: init,
  paint: paint,
  show: show,
  record: record,
  stop: stop,
  mime: mime,
  decorate: decorate,
  speakCard: speakCardId,
};
})();
