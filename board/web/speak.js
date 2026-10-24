/* ==========================================================================
   speak.js -- the board speaks, listens and shows what it heard.

   THE THIRD ANSWER TAB. `#tab-speak` opens `#speakbox` in the answer panel:
   record and stop, a level meter while recording, the phrase being aimed at,
   and the last heard block -- "heard: ..." with a chip per syllable saying the
   tone heard against the tone wanted. A take is posted as multipart to
   `/s/<id>/speech/say` (`routes/speaking.py`), which answers with the heard
   record; the tutor is given words, never the audio.

   THE MICROPHONE IS ASKED FOR ON A TAP AND LET GO AFTER EVERY TAKE.
   `getUserMedia` runs only from the record button, and every track of the
   stream is stopped when the take ends, so the iPad's recording light goes
   out between takes. The recording is `audio/mp4` where the browser can make
   it (Safari), else `audio/webm;codecs=opus` (Chrome, Firefox), else
   whatever MediaRecorder picks. A take stops itself at MAX_TAKE_MS, the
   longest the hosted assessors read.

   A take aims at the newest `say` phrase on the question, when it has one.

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
var target = null;         /* {text, lang, pinyin} a take aims at */
var lastHeard = "";        /* the heard block painted, as JSON */

var take = null;           /* the take being recorded */

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
    target: $("speak-target"),
    heard: $("heard"),
  };
  if (started) return;
  started = true;
  if (els.rec) els.rec.addEventListener("click", function () {
    if (take) stop(); else record();
  });
}

/* ------------------------------------------------------------ the target */

function phraseOf(node) {
  if (!node) return null;
  return { sha: node.dataset.sha, lang: node.dataset.lang,
           text: node.dataset.text || "", pinyin: node.dataset.pinyin || "" };
}

/* A phrase's play button: play it and aim the next take at it. */

function aim(p) {
  target = p && p.text ? { text: p.text, lang: p.lang || "", pinyin: p.pinyin || "" } : null;
  paintTarget();
}

function paintTarget() {
  if (!els.target) return;
  if (!target) {
    els.target.hidden = true;
    els.target.textContent = "";
    return;
  }
  els.target.hidden = false;
  els.target.textContent = "say: " + target.text
    + (target.pinyin ? "  [" + target.pinyin + "]" : "");
}

/* The newest `say` phrase on the question being answered, else on the newest
   card that has one. */
function aimDefault() {
  var q = hooks.question ? hooks.question() : null;
  var node = q ? document.querySelector('[data-card="' + q + '"] .say-phrase') : null;
  if (!node) {
    var all = document.querySelectorAll("[data-card] .say-phrase");
    node = all.length ? all[all.length - 1] : null;
  }
  if (node) aim(phraseOf(node));
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
  if (!target) aimDefault();
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
  var lang = (target && target.lang) || (defaults && defaults.lang)
             || navigator.language || "en-US";
  form.append("lang", lang);
  if (target) {
    form.append("ref", target.text);
    if (target.pinyin) form.append("pinyin", target.pinyin);
  }
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
  var got = rec.assess || {};
  return { text: rec.heard || "", target: rec.target || "", pinyin: rec.pinyin || "",
           verdict: rec.verdict || "", tones: got.syllables || [],
           prototype: !!got.prototype };
}

/* A speech turn (`routes/speaking.say`'s record) as the block draws it. */
function fromTurn(t) {
  return { text: t.text || "", target: t.target || "", pinyin: t.pinyin || "",
           verdict: t.verdict || "", tones: t.tones || [], prototype: !!t.prototype };
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
  if (h.target) {
    var aimLine = document.createElement("div");
    aimLine.className = "heard-target";
    aimLine.textContent = "target: " + h.target + (h.pinyin ? "  [" + h.pinyin + "]" : "");
    els.heard.appendChild(aimLine);
  }
  if (h.tones && h.tones.length) {
    var row = document.createElement("div");
    row.className = "tones";
    h.tones.forEach(function (s) {
      var chip = document.createElement("span");
      var heard = s.heard || "unknown";
      var state = heard === "unknown" || !s.expect ? "unknown"
                : heard === s.expect ? "ok" : "off";
      chip.className = "tone " + state;
      chip.dataset.expect = s.expect || "";
      chip.dataset.heard = heard;
      chip.title = "wanted " + (s.expect || "?") + ", heard " + heard
        + (typeof s.confidence === "number" ? " (" + Math.round(s.confidence * 100) + "%)" : "");
      var syl = document.createElement("span");
      syl.className = "syl";
      syl.textContent = s.syllable || s.pinyin || "?";
      var tone = document.createElement("span");
      tone.className = "t";
      tone.textContent = heard === "unknown" ? "?" : heard;
      chip.appendChild(syl);
      chip.appendChild(tone);
      row.appendChild(chip);
    });
    els.heard.appendChild(row);
  }
  if (h.verdict) {
    var v = document.createElement("div");
    v.className = "heard-verdict";
    v.textContent = h.verdict;
    els.heard.appendChild(v);
  }
}

/* --------------------------------------------------------------- per frame */

/* Every frame: the subject's defaults and the newest speech turn as the
   heard block. */
function paint(data) {
  data = data || {};
  if (data.speech !== undefined) defaults = data.speech || null;
  var newest = null;
  (data.turns || []).forEach(function (t) {
    if (t.kind === "speech" && (!newest || (t.t || 0) >= (newest.t || 0))) newest = t;
  });
  if (newest) showHeard(fromTurn(newest));
  if (!target) aimDefault();
}

/* The tab is the board's: this only shows or hides the box. */
function show(on) {
  if (els.box) els.box.hidden = !on;
  if (els.tab) els.tab.classList.toggle("on", !!on);
  if (on && !target) aimDefault();
  if (!on && take) stop();
}

window.Speak = {
  init: init,
  paint: paint,
  show: show,
  record: record,
  stop: stop,
  mime: mime,
  aim: aim,
};
})();
