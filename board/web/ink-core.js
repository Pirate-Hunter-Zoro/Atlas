/* ==========================================================================
   ink-core.js -- the geometry of a line of ink, for every surface that draws one.

   Raw pointer samples are jittery and arrive unevenly, and drawing them
   directly gives the faceted, granular line that makes handwriting look wrong.
   So: smooth the samples as they arrive, run a Catmull-Rom curve through them,
   resample that curve densely, and polish the stroke once on lift.

   The slate (`slate-core.js`) and the marks over cards and documents
   (`annotate.js`) both read this one copy. Load it before either. There is no
   fallback: a page without it fails to load its ink rather than drawing raw
   polylines.
   ========================================================================== */

(function () {
"use strict";

var SMOOTH = 0.30;          /* how much of each new sample to trust, at rest */
/* ...and how fast the pen has to be moving, in logical units per sample, before
   it is trusted completely. Smoothing buys steadiness by lagging the nib, and a
   fixed amount of it is wrong at both ends: at a crawl the hand's tremor is the
   whole signal and wants heavy averaging, while in a quick stroke the samples
   are far apart, carry little relative jitter, and the lag is the only thing you
   notice -- the ink visibly trails the pen. So the trust slides with speed. */
var TRACK = 8;
var RESAMPLE = 0.8;         /* logical units between rendered points */
var MIN_STEP = 0.5;         /* how far the pen must travel to record a point */
var POLISH = 2;             /* smoothing passes over a finished stroke */

function catmullRom(p0, p1, p2, p3, t) {
  var t2 = t * t, t3 = t2 * t;
  return [
    0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
           (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
           (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
    0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
           (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
           (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3),
    p1[2] + (p2[2] - p1[2]) * t,
  ];
}

/* A dense, evenly spaced path through the samples. Density is what removes the
   faceting: once consecutive points are about a pixel apart, the round joins
   between them read as one continuous edge. */
function densify(pts) {
  if (pts.length < 3) return pts.slice();
  var out = [pts[0]];
  for (var i = 0; i < pts.length - 1; i++) {
    var p0 = pts[i - 1] || pts[i];
    var p1 = pts[i], p2 = pts[i + 1];
    var p3 = pts[i + 2] || p2;
    var dist = Math.hypot(p2[0] - p1[0], p2[1] - p1[1]);
    var steps = Math.max(1, Math.min(24, Math.ceil(dist / RESAMPLE)));
    for (var s = 1; s <= steps; s++) out.push(catmullRom(p0, p1, p2, p3, s / steps));
  }
  return out;
}

/* How much of a new sample to believe, given how far it is from where the line
   has got to. */
function trust(dist) {
  if (dist >= TRACK) return 1;
  return SMOOTH + (1 - SMOOTH) * (dist / TRACK);
}

/* One-euro-style smoothing while the pen moves cannot remove tremor without
   adding lag you can feel. So the live path stays responsive and the stroke is
   polished once, on lift: a weighted three-point average over the interior,
   which pulls out hand tremor while leaving the endpoints and the overall shape
   exactly where they were put. Pressure is averaged with it, so the width stops
   flickering along a line that was drawn at a steady weight. */
function polish(pts, passes) {
  if (pts.length < 4) return pts;
  var cur = pts;
  for (var pass = 0; pass < passes; pass++) {
    var out = [cur[0]];
    for (var i = 1; i < cur.length - 1; i++) {
      var a = cur[i - 1], b = cur[i], c = cur[i + 1];
      out.push([Math.round((a[0] + 2 * b[0] + c[0]) / 4 * 10) / 10,
                Math.round((a[1] + 2 * b[1] + c[1]) / 4 * 10) / 10,
                Math.round((a[2] + 2 * b[2] + c[2]) / 4 * 100) / 100]);
    }
    out.push(cur[cur.length - 1]);
    cur = out;
  }
  return cur;
}

window.InkCore = {
  catmullRom: catmullRom,
  densify: densify,
  polish: polish,
  trust: trust,
  SMOOTH: SMOOTH,
  TRACK: TRACK,
  RESAMPLE: RESAMPLE,
  MIN_STEP: MIN_STEP,
  POLISH: POLISH,
};
})();
