/* ==========================================================================
   ink-clip.js -- one clipboard, for every surface that holds handwriting.

   Ink cut from a proof belongs to the person holding the pen, not to the
   surface it came from, so the slate instances and the annotation layer share
   this one clipboard.

   What is on it is geometry, not a surface's own coordinates: the slate
   stores logical page units and the annotation layer fractions of a card, so
   a clip is CSS pixels with its top-left at the origin, which both convert to
   and from, keeping the size it looked on the glass.

   It is also written to `localStorage` (`tutor-board.clip`), which is how
   board.html, library.html and slate.html -- separate documents -- share it.

   THE NEWEST COPY WINS, WHEREVER IT WAS MADE. Every clip carries `seq`, which
   is the time it was made or one past the newest clip this document has seen,
   whichever is larger, so two copies in the same millisecond still have an
   order. Old clips have only `at`, which stands in for it. On a tie the stored
   copy wins, except over this document's own stub.

   A CLIP TOO BIG FOR THE DISK STILL TELLS THE DISK IT HAPPENED. It is held in
   memory here and the key holds a stub (`big: true`, no strokes), so another
   page pastes nothing rather than the older clip a big copy replaced, and
   `why()` there says "big".
   ========================================================================== */

(function () {
"use strict";

var KEY = "tutor-board.clip";
/* What will be written to disk. A clip is ink somebody is carrying between two
   surfaces in the next few seconds; it has no business filling the origin's
   storage allowance, which the app itself lives in. Over this, the full clip
   stays in this document and the disk gets the stub. */
var MAX_BYTES = 300000;
/* And what will be held at all. Selecting a whole page of a proof and copying it
   is a legitimate thing to do; holding a hundred thousand points of it in a
   string is not, and pasting it would be a second page nobody can draw. */
var MAX_PTS = 60000;

/* The clip this document made or last read, decoded. */
var held = null;
/* The newest stamp seen anywhere, so a copy made here always outranks it. */
var seen = 0;
/* Whether `held` exists in this document only: too big for the disk, or the
   disk refused it. */
var local = false;
var listeners = [];
/* The last raw string read and what it decoded to: `peek` runs on every
   repaint of every bar, and a v2 clip is decoded, not merely parsed. */
var lastRaw = null, lastClip = null;

function fire() {
  for (var i = 0; i < listeners.length; i++) {
    try { listeners[i](); } catch (e) { /* a bar that cannot repaint is not fatal */ }
  }
}

function stamp(clip) {
  if (!clip) return 0;
  return typeof clip.seq === "number" ? clip.seq : (+clip.at || 0);
}

/* v1 stores points as [x, y, pressure] triples. v2 stores each stroke as one
   flat list of integers: x and y in tenths, pressure in hundredths, the first
   point absolute and every later one a difference from the one before. Ink is
   continuous, so the differences are short numbers, and the clip about a third
   the size. */
function encode(clip) {
  var out = {};
  for (var k in clip) if (Object.prototype.hasOwnProperty.call(clip, k)) out[k] = clip[k];
  out.v = 2;
  out.strokes = clip.strokes.map(function (s) {
    var d = [], px = 0, py = 0, pp = 0;
    for (var i = 0; i < s.pts.length; i++) {
      var q = s.pts[i];
      var x = Math.round(q[0] * 10), y = Math.round(q[1] * 10);
      var p = Math.round((q.length > 2 ? q[2] : 0.5) * 100);
      d.push(x - px, y - py, p - pp);
      px = x; py = y; pp = p;
    }
    return { c: s.c, w: s.w, hl: !!s.hl, d: d };
  });
  return out;
}

function decode(clip) {
  if (!clip || typeof clip !== "object") return null;
  if (clip.v === 1) return clip;
  if (clip.v !== 2) return null;
  if (clip.big) return clip;
  var out = {};
  for (var k in clip) if (Object.prototype.hasOwnProperty.call(clip, k)) out[k] = clip[k];
  out.strokes = (clip.strokes || []).map(function (s) {
    var d = s.d || [], pts = [], x = 0, y = 0, p = 0;
    for (var i = 0; i + 2 < d.length; i += 3) {
      x += d[i]; y += d[i + 1]; p += d[i + 2];
      pts.push([x / 10, y / 10, p / 100]);
    }
    return { c: s.c, w: s.w, hl: !!s.hl, pts: pts };
  });
  return out;
}

function stored() {
  try {
    var raw = window.localStorage.getItem(KEY);
    if (!raw) { lastRaw = lastClip = null; return null; }
    if (raw !== lastRaw) {
      lastRaw = raw;
      lastClip = decode(JSON.parse(raw));
    }
    var clip = lastClip;
    if (!valid(clip)) return null;
    if (stamp(clip) > seen) seen = stamp(clip);
    return clip;
  } catch (e) { return null; }   /* private mode, or somebody else's key */
}

/* A clip, or a stub saying one was made that the disk could not carry. */
function valid(clip) {
  if (!clip || (clip.v !== 1 && clip.v !== 2) || !clip.strokes) return false;
  return clip.big ? true : clip.strokes.length > 0;
}

function usable(clip) { return valid(clip) && !clip.big; }

/* The clipboard: whichever of the held and the stored copy is newer. A tie
   goes to the disk, which is what every other document sees -- unless the disk
   holds this document's own stub for the clip held here. */
function newest() {
  var disk = stored();
  if (!disk) return valid(held) ? held : null;
  if (!valid(held)) return disk;
  var a = stamp(disk), b = stamp(held);
  if (a > b) return disk;
  if (a < b) return held;
  if (disk.big && !held.big && local) return held;
  return disk;
}

function count(clip) {
  var n = 0;
  for (var i = 0; i < clip.strokes.length; i++) {
    n += ((clip.strokes[i].pts || []).length);
  }
  return n;
}

/* The extent of the ink, so the clip can be normalised to its own corner. Every
   surface places a paste by where it wants the CORNER of the thing to land, and
   none of them cares where it came from. */
function boxOf(strokes) {
  var x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (var i = 0; i < strokes.length; i++) {
    var pts = strokes[i].pts || [];
    for (var n = 0; n < pts.length; n++) {
      if (pts[n][0] < x0) x0 = pts[n][0];
      if (pts[n][0] > x1) x1 = pts[n][0];
      if (pts[n][1] < y0) y0 = pts[n][1];
      if (pts[n][1] > y1) y1 = pts[n][1];
    }
  }
  if (!isFinite(x0)) return null;
  return { x0: x0, y0: y0, x1: x1, y1: y1 };
}

/* Write the clip, or failing that its stub. The old key goes first, so a stub
   that cannot be written either leaves nothing rather than the older clip. */
function save(clip) {
  var body = "";
  try { body = JSON.stringify(encode(clip)); } catch (e) { body = ""; }
  if (body && body.length <= MAX_BYTES) {
    try { window.localStorage.setItem(KEY, body); return true; } catch (e) { /* full */ }
  }
  try { window.localStorage.removeItem(KEY); } catch (e) {}
  var stub = { v: 2, seq: clip.seq, at: clip.at, kind: clip.kind, src: clip.src,
               big: true, n: clip.strokes.length, strokes: [] };
  try { window.localStorage.setItem(KEY, JSON.stringify(stub)); } catch (e) {}
  return false;
}

window.InkClip = {
  /* Put ink on the clipboard.
  
     `strokes` are in CSS pixels, in whatever frame the caller measured them in;
     they are moved to their own corner here so that nothing downstream has to
     know where they were. `kind` and `src` are the surface and the instance they
     came from, and they exist for one reason: a paste back into the SAME surface
     is a duplicate, which wants to land beside the original, and a paste into a
     different one wants to land where the person is looking. */
  put: function (strokes, meta) {
    strokes = (strokes || []).filter(function (s) {
      return s && s.pts && s.pts.length;
    });
    if (!strokes.length) return null;
    var b = boxOf(strokes);
    if (!b) return null;
    meta = meta || {};
    stored();
    if (held && stamp(held) > seen) seen = stamp(held);
    var now = Date.now();
    var clip = {
      v: 2, seq: Math.max(now, seen + 1), at: now,
      kind: meta.kind || "slate", src: meta.src || "",
      /* Where it was, in the source's own units, so a duplicate can be offset
         from the original rather than dropped in the middle of the view. */
      ox: b.x0, oy: b.y0,
      w: Math.max(1, b.x1 - b.x0), h: Math.max(1, b.y1 - b.y0),
      strokes: strokes.map(function (s) {
        return {
          c: s.c, w: s.w, hl: !!s.hl,
          pts: s.pts.map(function (q) {
            return [Math.round((q[0] - b.x0) * 10) / 10,
                    Math.round((q[1] - b.y0) * 10) / 10,
                    q.length > 2 ? Math.round(q[2] * 100) / 100 : 0.5];
          }),
        };
      }),
    };
    if (count(clip) > MAX_PTS) return null;
    seen = clip.seq;
    held = clip;
    local = !save(clip);
    fire();
    return clip;
  },

  /* What is on the clipboard, or null. Deep-copied on the way out: a paste
     mutates what it is given -- it is placed, and then it is dragged -- and the
     clipboard has to be able to be pasted twice. A stub is not a clip: it
     pastes nothing, and `why()` says so. */
  get: function () {
    var clip = newest();
    if (!usable(clip)) return null;
    if (clip !== held) { held = clip; local = false; }
    return JSON.parse(JSON.stringify(clip));
  },

  /* For a bar deciding whether to offer Paste at all. A stub counts: Paste is
     offered, and answers that the copy has to be made again here. */
  has: function () { return !!window.InkClip.peek(); },
  peek: function () { return newest(); },
  count: function () {
    var clip = newest();
    return usable(clip) ? clip.strokes.length : 0;
  },
  /* Why there is nothing to paste: "big" when the newest copy was made on
     another page and was too large to carry here, "empty" when there is none,
     and "" when there is something to paste. */
  why: function () {
    var clip = newest();
    if (!clip) return "empty";
    return clip.big ? "big" : "";
  },
  /* Whether the clip on the clipboard exists in this document only, because the
     disk could not carry it. */
  local: function () {
    return !!(local && held && newest() === held);
  },
  clear: function () {
    held = null;
    local = false;
    try { window.localStorage.removeItem(KEY); } catch (e) {}
    fire();
  },
  onChange: function (fn) { if (typeof fn === "function") listeners.push(fn); },
};

/* Another document in this browser copied something, or cleared the key on
   its way to a stub it could not write. Either way what is held here is older
   than the news, so it goes, and the bars repaint. */
window.addEventListener("storage", function (ev) {
  if (ev && ev.key && ev.key !== KEY) return;
  held = null;
  local = false;
  fire();
});

/* Back from the back-forward cache: the page is as it was left, and another
   page may have copied in the meantime without this one hearing of it. */
window.addEventListener("pageshow", function (ev) {
  if (ev && ev.persisted) fire();
});
})();
