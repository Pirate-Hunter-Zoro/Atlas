/* ==========================================================================
   calc.js -- the calculator that floats over the lesson.

   A panel, not a page: it sits on top of the board, is dragged by its head,
   shrinks to its input row, and closes with ✕ or Escape. Nothing under it is
   blocked -- it is as big as itself and no bigger, and the lesson scrolls
   behind it.

   The mathematics is calc-core.js on top of math.js. math.js is 650 KB, so it
   is fetched the first time the panel opens rather than with the page; sw.js
   precaches it, so that fetch works offline.

   History, variables, Ans, DEG/RAD, where the panel was and whether it was
   open are kept in localStorage under one key. Storage that refuses (a
   private tab, a full quota) costs the memory and nothing else.

   board.js owns the ⋯ menu entry and calls Calc.toggle(); this file owns the
   panel. Loaded before board.js.
   ========================================================================== */

(function () {
"use strict";

var KEY = "board-calc";
var MATH_SRC = "/static/mathjs/math.js";
var MAX_HIST = 100;

var panel = null, els = {}, engine = null, loading = false, failed = false, waiting = [];
var hist = [], recall = -1, caret = null, listeners = [];
var saved = read();

function read() {
  try { return JSON.parse(localStorage.getItem(KEY) || "{}") || {}; }
  catch (e) { return {}; }
}
function write() {
  var s = {
    hist: hist.slice(-MAX_HIST),
    engine: engine ? engine.save() : saved.engine,
    pos: saved.pos || null,
    small: !!saved.small,
    open: isOpen(),
  };
  saved = s;
  try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) { /* memory only */ }
}

hist = Array.isArray(saved.hist) ? saved.hist.slice(-MAX_HIST) : [];

/* ------------------------------------------------------------------ the maths */

function makeEngine() {
  try {
    engine = window.CalcCore.create(window.math, {});
    engine.restore(saved.engine);
  } catch (e) {
    engine = null; failed = true;
  }
}

/* A press that lands while math.js is still arriving waits for it rather
   than vanishing: every caller is queued and all of them run on load. */
function ensureEngine(done) {
  if (engine) return done();
  if (window.math && window.CalcCore) { makeEngine(); return done(); }
  waiting.push(done);
  if (loading) return;
  loading = true;
  var drain = function () {
    loading = false;
    var q = waiting; waiting = [];
    q.forEach(function (cb) { try { cb(); } catch (e) { /* one caller's fault is its own */ } });
  };
  var s = document.createElement("script");
  s.src = MATH_SRC;
  s.onload = function () { makeEngine(); drain(); };
  s.onerror = function () { failed = true; drain(); };
  document.head.appendChild(s);
}

/* --------------------------------------------------------------------- the panel */

var KEYS = [
  ["(", "("], [")", ")"], ["^", "^"], ["√", "sqrt("], ["π", "pi"], ["e", "e"],
  ["nCr", " nCr "], ["nPr", " nPr "], ["!", "!"], [",", ", "], ["Ans", "Ans"], ["x", "x"],
  ["x²", "^2"], ["x⁻¹", "^-1"], ["|x|", "abs("], ["mod", " mod "], ["⌫", null, "back"], ["ƒ", null, "fns"],
];

var FNS = [
  ["distributions", [
    ["normalpdf", "x[, μ, σ]"], ["normalcdf", "lower, upper[, μ, σ]"], ["invNorm", "area[, μ, σ]"],
    ["tpdf", "x, df"], ["tcdf", "lower, upper, df"], ["invT", "area, df"],
    ["chi2pdf", "x, df"], ["chi2cdf", "lower, upper, df"],
    ["Fpdf", "x, df1, df2"], ["Fcdf", "lower, upper, df1, df2"],
    ["binompdf", "n, p[, x]"], ["binomcdf", "n, p[, x]"],
    ["poissonpdf", "λ, x"], ["poissoncdf", "λ, x"],
    ["geometpdf", "p, x"], ["geometcdf", "p, x"]]],
  ["calculus", [
    ["fnInt", "expr, x, a, b — ±inf allowed"], ["nDeriv", "expr, x, value"],
    ["derivative", "expr, x[, value] — symbolic, radians"], ["solve", "expr, x, guess[, {lo, hi}]"],
    ["sum", "expr, k, from, to"], ["seq", "expr, k, from, to[, step]"]]],
  ["lists & stats", [
    ["mean", "list"], ["median", "list"], ["std", "list — sample"], ["stdp", "list — population"],
    ["variance", "list — sample"], ["varp", "list — population"], ["sum", "list"], ["prod", "list"],
    ["min", "list"], ["max", "list"], ["sort", "list"]]],
  ["matrices", [
    ["det", "[1, 2; 3, 4]"], ["inv", "matrix"], ["transpose", "matrix"], ["multiply", "A, B — or A * B"],
    ["identity", "n"]]],
  ["numbers", [
    ["frac", "x — as a fraction"], ["round", "x[, digits]"], ["floor", "x"], ["ceil", "x"],
    ["gcd", "a, b"], ["lcm", "a, b"], ["nthRoot", "x, n"], ["log", "x[, base] — base 10"],
    ["ln", "x"], ["exp", "x"], ["gamma", "x"], ["factorial", "n"], ["nCr", "n, r"], ["nPr", "n, r"]]],
  ["trig", [
    ["sin", "x"], ["cos", "x"], ["tan", "x"], ["asin", "x"], ["acos", "x"], ["atan", "x"],
    ["sinh", "x"], ["cosh", "x"], ["tanh", "x"], ["sec", "x"], ["csc", "x"], ["cot", "x"]]],
];

function el(tag, attrs, text) {
  var n = document.createElement(tag);
  if (attrs) Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
  if (text !== undefined) n.textContent = text;
  return n;
}

function build() {
  panel = el("aside", { id: "calc", role: "dialog", "aria-label": "calculator" });
  panel.hidden = true;

  var head = el("div", { id: "calc-head", "class": "calc-head" });
  head.appendChild(el("strong", null, "calculator"));
  var acts = el("span", { "class": "calc-acts" });
  els.angle = el("button", { id: "calc-angle", type: "button", title: "degrees or radians" });
  els.small = el("button", { id: "calc-small", type: "button", title: "shrink to the input line" }, "▁");
  els.clear = el("button", { id: "calc-clear", type: "button", title: "clear the history and the variables" }, "clear");
  els.close = el("button", { id: "calc-close", type: "button", title: "close the calculator" }, "✕");
  [els.angle, els.small, els.clear, els.close].forEach(function (b) { acts.appendChild(b); });
  head.appendChild(acts);

  els.log = el("div", { id: "calc-log", "aria-live": "polite" });
  els.err = el("div", { id: "calc-err", role: "status" });
  els.err.hidden = true;

  var row = el("div", { "class": "calc-row" });
  els.input = el("input", {
    id: "calc-in", type: "text", inputmode: "text", autocomplete: "off",
    autocapitalize: "off", autocorrect: "off", spellcheck: "false",
    enterkeyhint: "go", "aria-label": "expression",
    placeholder: "2^10, 10 nCr 3, normalcdf(-1, 1)",
  });
  els.go = el("button", { id: "calc-go", type: "button", title: "evaluate" }, "=");
  row.appendChild(els.input); row.appendChild(els.go);

  els.keys = el("div", { id: "calc-keys" });
  KEYS.forEach(function (k) {
    var b = el("button", { type: "button", "class": "calc-key" }, k[0]);
    if (k[1] !== null) b.dataset.ins = k[1];
    if (k[2]) b.dataset.act = k[2];
    els.keys.appendChild(b);
  });

  els.fns = el("div", { id: "calc-fns" });
  els.fns.hidden = true;
  FNS.forEach(function (group) {
    els.fns.appendChild(el("div", { "class": "calc-fn-group" }, group[0]));
    group[1].forEach(function (f) {
      var b = el("button", { type: "button", "class": "calc-fn" });
      b.dataset.ins = f[0] + "(";
      b.dataset.sig = f[0] + "(" + f[1] + ")";
      b.appendChild(el("span", { "class": "calc-fn-name" }, f[0]));
      b.appendChild(el("span", { "class": "calc-fn-sig" }, f[1]));
      els.fns.appendChild(b);
    });
  });

  panel.appendChild(head);
  panel.appendChild(els.log);
  panel.appendChild(els.err);
  panel.appendChild(row);
  panel.appendChild(els.keys);
  panel.appendChild(els.fns);
  document.body.appendChild(panel);
  wire(head);
  paintLog();
  paintAngle();
  panel.classList.toggle("small", !!saved.small);
  if (saved.small) els.small.textContent = "▢";
}

function wire(head) {
  els.close.onclick = function () { close(); };
  els.small.onclick = function () {
    saved.small = !saved.small;
    panel.classList.toggle("small", saved.small);
    els.small.textContent = saved.small ? "▢" : "▁";
    els.small.title = saved.small ? "show the history and the keys" : "shrink to the input line";
    place();
    write();
  };
  els.angle.onclick = function () {
    ensureEngine(function () {
      if (!engine) return;
      engine.setAngle(engine.angle() === "deg" ? "rad" : "deg");
      paintAngle();
      write();
    });
  };
  els.clear.onclick = function () {
    hist = [];
    if (engine) engine.clearVars();
    else saved.engine = null;
    say("");
    paintLog();
    write();
  };
  els.go.onclick = function () { run(); };

  els.input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); run(); }
    else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(); }
    else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
      if (!hist.length) return;
      e.preventDefault();
      if (recall < 0) recall = hist.length;
      recall += e.key === "ArrowUp" ? -1 : 1;
      recall = Math.max(0, Math.min(hist.length, recall));
      els.input.value = recall < hist.length ? hist[recall].q : "";
      caret = null;
    }
  });
  ["keyup", "click", "select", "input"].forEach(function (t) {
    els.input.addEventListener(t, function () {
      caret = [els.input.selectionStart, els.input.selectionEnd];
    });
  });

  /* A key must not take focus from the input: on an iPad that drops the
     keyboard the person was typing on. */
  [els.go].forEach(function (b) {
    b.addEventListener("pointerdown", function (e) { e.preventDefault(); });
    b.addEventListener("mousedown", function (e) { e.preventDefault(); });
  });
  [els.keys, els.fns].forEach(function (box) {
    box.addEventListener("pointerdown", function (e) {
      if (e.target.closest("button")) e.preventDefault();
    });
    box.addEventListener("mousedown", function (e) {
      if (e.target.closest("button")) e.preventDefault();
    });
    box.addEventListener("click", function (e) {
      var b = e.target.closest("button");
      if (!b) return;
      if (b.dataset.act === "back") return back();
      if (b.dataset.act === "fns") {
        els.fns.hidden = !els.fns.hidden;
        b.classList.toggle("on", !els.fns.hidden);
        return;
      }
      if (b.dataset.ins !== undefined) insert(b.dataset.ins);
      if (b.dataset.sig) say(b.dataset.sig, "hint");
    });
  });

  els.log.addEventListener("click", function (e) {
    var b = e.target.closest("button");
    if (!b || b.dataset.i === undefined) return;
    var h = hist[+b.dataset.i];
    if (!h) return;
    if (b.classList.contains("calc-q")) { els.input.value = h.q; caret = null; }
    else insert(h.a);
  });

  panel.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { e.stopPropagation(); close(); }
  });

  drag(head);
  window.addEventListener("resize", function () { if (isOpen()) place(); });
}

/* Dragged by its head, and kept on the glass: a panel dragged off-screen is
   one nobody can close. */
function drag(head) {
  var start = null;
  head.addEventListener("pointerdown", function (e) {
    if (e.target.closest("button")) return;
    var r = panel.getBoundingClientRect();
    start = { id: e.pointerId, dx: e.clientX - r.left, dy: e.clientY - r.top };
    try { head.setPointerCapture(e.pointerId); } catch (err) { /* not fatal */ }
    e.preventDefault();
  });
  head.addEventListener("pointermove", function (e) {
    if (!start || e.pointerId !== start.id) return;
    saved.pos = { x: e.clientX - start.dx, y: e.clientY - start.dy };
    place();
  });
  var end = function (e) {
    if (!start || (e && e.pointerId !== start.id)) return;
    start = null;
    write();
  };
  head.addEventListener("pointerup", end);
  head.addEventListener("pointercancel", end);
  head.addEventListener("lostpointercapture", end);
}

function place() {
  if (!panel) return;
  var pos = saved.pos;
  if (!pos) { panel.style.left = ""; panel.style.top = ""; panel.style.right = ""; return; }
  var w = panel.offsetWidth || 320, h = panel.offsetHeight || 200;
  var vw = window.innerWidth || 1024, vh = window.innerHeight || 768;
  var x = Math.max(4, Math.min(vw - Math.min(w, vw) - 4, pos.x));
  var y = Math.max(4, Math.min(vh - 48, pos.y));
  panel.style.right = "auto";
  panel.style.left = x + "px";
  panel.style.top = y + "px";
}

function paintAngle() {
  var a = engine ? engine.angle() : (saved.engine && saved.engine.angle) || "rad";
  els.angle.textContent = a === "deg" ? "DEG" : "RAD";
  els.angle.setAttribute("aria-pressed", a === "deg" ? "true" : "false");
}

function paintLog() {
  els.log.textContent = "";
  if (!hist.length) {
    els.log.appendChild(el("div", { "class": "calc-none" },
      "Type an expression and press =. Tap a line to reuse it; ƒ lists the functions."));
    return;
  }
  hist.forEach(function (h, i) {
    var row = el("div", { "class": "calc-entry" });
    var q = el("button", { type: "button", "class": "calc-q", title: "use this expression again" }, h.q);
    var a = el("button", { type: "button", "class": "calc-a", title: "insert this result" }, h.a);
    q.dataset.i = a.dataset.i = String(i);
    row.appendChild(q);
    row.appendChild(a);
    if (h.f) row.appendChild(el("span", { "class": "calc-frac" }, "= " + h.f));
    els.log.appendChild(row);
  });
  els.log.scrollTop = els.log.scrollHeight;
}

function say(text, kind) {
  els.err.textContent = text || "";
  els.err.hidden = !text;
  els.err.className = kind || "";
}

function insert(text) {
  var v = els.input.value;
  var focused = document.activeElement === els.input;
  var s = focused ? els.input.selectionStart : (caret ? caret[0] : v.length);
  var e = focused ? els.input.selectionEnd : (caret ? caret[1] : v.length);
  if (s === null || s === undefined) { s = v.length; e = v.length; }
  els.input.value = v.slice(0, s) + text + v.slice(e);
  var at = s + text.length;
  caret = [at, at];
  try { if (focused) els.input.setSelectionRange(at, at); } catch (err) { /* not fatal */ }
}

function back() {
  var v = els.input.value;
  var focused = document.activeElement === els.input;
  var s = focused ? els.input.selectionStart : (caret ? caret[0] : v.length);
  var e = focused ? els.input.selectionEnd : (caret ? caret[1] : v.length);
  if (s === null || s === undefined) { s = v.length; e = v.length; }
  if (s === e && s > 0) s -= 1;
  els.input.value = v.slice(0, s) + v.slice(e);
  caret = [s, s];
  try { if (focused) els.input.setSelectionRange(s, s); } catch (err) { /* not fatal */ }
}

function run() {
  var text = els.input.value;
  if (!text.trim()) return;
  if (!engine && loading) say("loading the maths library…", "hint");
  ensureEngine(function () {
    if (els.input.value !== text) return;      // a second press queued behind the first
    if (!engine) {
      say("the calculator's maths library did not load — reload the app while online", "bad");
      return;
    }
    var r;
    try { r = engine.evaluate(text); }
    catch (e) { r = { ok: false, error: String(e && e.message || e) }; }
    if (!r.ok) { say(r.error, "bad"); return; }
    hist.push({ q: r.input, a: r.text, f: r.frac || null });
    if (hist.length > MAX_HIST) hist = hist.slice(-MAX_HIST);
    recall = -1;
    els.input.value = "";
    caret = null;
    say("");
    paintLog();
    write();
  });
}

/* ------------------------------------------------------------------ open / close */

function isOpen() { return !!(panel && !panel.hidden); }

function notify() {
  listeners.forEach(function (cb) { try { cb(isOpen()); } catch (e) { /* not ours */ } });
}

function open() {
  if (!panel) build();
  panel.hidden = false;
  place();
  if (!engine && !failed) {
    els.input.placeholder = "loading…";
    ensureEngine(function () {
      els.input.placeholder = engine ? "2^10, 10 nCr 3, normalcdf(-1, 1)" : "the maths library did not load";
      if (!engine) say("the calculator's maths library did not load — reload the app while online", "bad");
      paintAngle();
    });
  }
  write();
  notify();
}

function close() {
  if (!panel || panel.hidden) return;
  panel.hidden = true;
  if (document.activeElement && panel.contains(document.activeElement)) {
    try { document.activeElement.blur(); } catch (e) { /* not fatal */ }
  }
  write();
  notify();
}

window.Calc = {
  open: open,
  close: close,
  toggle: function () { if (isOpen()) close(); else open(); },
  isOpen: isOpen,
  onChange: function (cb) { listeners.push(cb); },
  /* for the test suite: evaluate as if typed and pressed = */
  run: function (text) { if (!panel) build(); els.input.value = text; run(); },
  wasOpen: function () { return !!saved.open; },
};

})();
