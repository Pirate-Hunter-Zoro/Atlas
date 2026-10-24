/* ==========================================================================
   problem.js -- the problem on their screen, and its givens in one tap.

   The payload's `problem` (`lesson/state.load_problem`) is the problem the
   session has pinned, or the next one once it is stated: its label, every
   label in the set, its statement as card markdown and its givens, each
   `{id, name, tex, calc, fig}`, `fig` naming its typeset figure.

   #probbar sits in #chrome under #hwbar: the label, which opens and closes
   the whole statement in one tap, a picker over every problem in the set
   (POST /problem), and one KaTeX chip per given. The statement and the chip
   menu are fixed layers OUTSIDE #chrome, because a scroller inside a sticky
   element does not scroll on WebKit (see #barmenu in board.html).

   A chip's menu puts the given wherever it is wanted:
     to calculator      Calc.enter(calc) defines it; absent while calc is null
     into typed answer  `$tex$` at #saybox's caret
     copy TeX           the TeX on the clipboard
     onto the page      typeset on the writing surface (`hooks.place`), where
                        the lasso moves it and a send carries it

   board.js owns the page and hands over what this needs (`init`): its
   session fetch, its markdown and KaTeX, the course's macros and the
   writing surface. Loaded before board.js.
   ========================================================================== */

(function () {
"use strict";

var hooks = {};
var els = {};
var shown = null;        /* the problem painted, as JSON: a repaint is a change */
var problem = null;
var menuFor = null;      /* the given whose menu is open */

function $(id) { return document.getElementById(id); }

function init(h) {
  hooks = h || {};
  els = {
    bar: $("probbar"), open: $("prob-open"), label: $("prob-label"),
    pick: $("prob-pick"), chips: $("prob-chips"),
    panel: $("probpanel"), body: $("probpanel-body"), shut: $("probpanel-close"),
    menu: $("probmenu"), head: $("probmenu-head"), calc: $("probmenu-calc"),
    say: $("probmenu-say"), copy: $("probmenu-copy"), page: $("probmenu-page"),
    said: $("probmenu-said"), chrome: $("chrome"),
  };
  if (!els.bar) return;
  els.open.onclick = function () { setOpen(els.panel.hidden); };
  if (els.shut) els.shut.onclick = function () { setOpen(false); };
  els.pick.onchange = function () { choose(els.pick.value); };
  els.chips.addEventListener("click", function (e) {
    var chip = e.target.closest ? e.target.closest(".prob-chip") : null;
    if (!chip || !problem) return;
    var g = (problem.givens || [])[+chip.dataset.i];
    if (!g) return;
    if (menuFor === g && !els.menu.hidden) closeMenu();
    else openMenu(g, chip);
  });
  els.calc.onclick = function () { act(toCalculator); };
  els.say.onclick = function () { act(intoTyped); };
  els.copy.onclick = function () { act(copyTex); };
  if (els.page) els.page.onclick = function () { act(ontoPage); };
  /* A tap anywhere else lets the menu go; Escape does too. */
  document.addEventListener("pointerdown", function (e) {
    if (els.menu.hidden) return;
    if (els.menu.contains(e.target)) return;
    if (e.target.closest && e.target.closest(".prob-chip")) return;
    closeMenu();
  }, true);
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (!els.menu.hidden) closeMenu();
    else if (!els.panel.hidden) setOpen(false);
  });
  window.addEventListener("resize", hang);
}

/* ------------------------------------------------------------------ paint */

function paint(p) {
  if (!els.bar) return;
  var blob = JSON.stringify(p || null);
  if (blob === shown) { hang(); return; }
  shown = blob;
  problem = p && p.labels && p.labels.length ? p : null;
  if (!problem) {
    els.bar.hidden = true;
    setOpen(false);
    closeMenu();
    return;
  }
  els.bar.hidden = false;
  els.label.textContent = problem.label ? "Problem " + problem.label : "which problem?";
  els.open.disabled = !problem.label;
  paintPicker();
  paintChips();
  paintStatement();
  if (menuFor) closeMenu();
  hang();
}

function paintPicker() {
  var have = Array.prototype.map.call(els.pick.options, function (o) { return o.value; });
  var want = [""].concat(problem.labels);
  if (have.join("\n") !== want.join("\n")) {
    els.pick.textContent = "";
    want.forEach(function (l) {
      var o = document.createElement("option");
      o.value = l;
      o.textContent = l ? "Problem " + l : "switch problem…";
      if (!l) o.disabled = true;
      els.pick.appendChild(o);
    });
  }
  els.pick.value = problem.label || "";
  els.pick.disabled = !!(hooks.ended && hooks.ended());
}

function typesetInto(node, tex) {
  node.textContent = tex;
  if (!window.katex) return;
  try {
    window.katex.render(tex, node, {
      throwOnError: false, strict: false,
      macros: hooks.macros ? hooks.macros() : {},
    });
  } catch (e) { node.textContent = tex; }
}

function paintChips() {
  els.chips.textContent = "";
  (problem.givens || []).forEach(function (g, i) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "prob-chip";
    b.dataset.i = String(i);
    b.dataset.id = g.id;
    b.title = g.calc ? g.calc : "put " + g.id + " somewhere";
    typesetInto(b, g.name);
    els.chips.appendChild(b);
  });
}

function paintStatement() {
  if (!els.body) return;
  if (!problem.label) {
    els.body.textContent = "";
    return;
  }
  if (!problem.stated || !problem.card) {
    els.body.innerHTML = "<p class=\"muted\">The statement of problem " +
      escapeHtml(problem.label) + " is not transcribed yet.</p>";
    return;
  }
  els.body.innerHTML = hooks.markdown ? hooks.markdown(problem.card)
                                      : "<p>" + escapeHtml(problem.card) + "</p>";
  if (hooks.typeset) hooks.typeset(els.body);
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/* Under the chrome, whatever is in it this frame: the banners above the bar
   come and go, and the panel must never sit over the label that closes it. */
function hang() {
  if (!els.chrome) return;
  var top = Math.max(0, els.chrome.getBoundingClientRect().bottom);
  if (!els.panel.hidden) els.panel.style.top = top + "px";
}

function setOpen(on) {
  if (!els.panel) return;
  on = !!on && !!(problem && problem.label);
  els.panel.hidden = !on;
  els.open.setAttribute("aria-expanded", on ? "true" : "false");
  els.bar.classList.toggle("open", on);
  if (on) { hang(); els.panel.scrollTop = 0; }
}

/* ----------------------------------------------------------- the picker */

function choose(label) {
  if (!label || !problem || label === problem.label) return;
  var post = hooks.post || function (url, body) {
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(body) }).then(function (r) { return r.json(); });
  };
  els.pick.disabled = true;
  post("/problem", { label: label }).then(function (res) {
    els.pick.disabled = !!(hooks.ended && hooks.ended());
    if (!res || !res.ok) {
      els.pick.value = problem.label || "";
      els.label.textContent = (res && res.error) || "could not switch";
    }
    /* The payload that follows paints the new problem. */
  }).catch(function () {
    els.pick.disabled = false;
    els.pick.value = problem.label || "";
  });
}

/* --------------------------------------------------------- the chip menu */

function openMenu(g, chip) {
  menuFor = g;
  typesetInto(els.head, g.tex);
  els.calc.hidden = !g.calc;
  if (els.page) els.page.hidden = !(hooks.place && g.fig);
  els.said.textContent = "";
  els.menu.hidden = false;
  var r = chip.getBoundingClientRect();
  var vw = window.innerWidth || 1024;
  var w = els.menu.offsetWidth || 240;
  els.menu.style.right = "auto";
  els.menu.style.top = Math.round(r.bottom + 6) + "px";
  els.menu.style.left = Math.round(Math.max(6, Math.min(vw - w - 6, r.left))) + "px";
}

function closeMenu() {
  menuFor = null;
  if (els.menu) els.menu.hidden = true;
}

function act(fn) {
  var g = menuFor;
  if (!g) return;
  var said = fn(g);
  if (said) {
    els.said.textContent = said;
    setTimeout(function () { if (menuFor === g) closeMenu(); }, 900);
  } else {
    closeMenu();
  }
}

function toCalculator(g) {
  if (!g.calc || !window.Calc || !window.Calc.enter) return "no calculator here";
  window.Calc.enter(g.calc);
  return null;
}

/* At the caret, or at the end when the box has never had one. The input
   event is what board.js saves a draft on. */
function intoTyped(g) {
  var box = $("saybox");
  if (!box) return "no answer box here";
  var text = "$" + g.tex + "$";
  var v = box.value;
  var s = typeof box.selectionStart === "number" ? box.selectionStart : v.length;
  var e = typeof box.selectionEnd === "number" ? box.selectionEnd : s;
  var before = v.slice(0, s), after = v.slice(e);
  if (before && !/\s$/.test(before)) text = " " + text;
  if (after && !/^\s/.test(after)) text = text + " ";
  box.value = before + text + after;
  var at = before.length + text.length;
  try { box.setSelectionRange(at, at); } catch (err) { /* not fatal */ }
  box.dispatchEvent(new Event("input", { bubbles: true }));
  return g.id + " is in your typed answer";
}

function copyTex(g) {
  var done = false;
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(g.tex).catch(function () { legacyCopy(g.tex); });
      done = true;
    }
  } catch (e) { done = false; }
  if (!done) legacyCopy(g.tex);
  return "copied";
}

function legacyCopy(text) {
  var t = document.createElement("textarea");
  t.value = text;
  t.setAttribute("readonly", "");
  t.style.position = "fixed";
  t.style.opacity = "0";
  document.body.appendChild(t);
  t.select();
  try { document.execCommand("copy"); } catch (e) { /* nothing more to try */ }
  document.body.removeChild(t);
}

/* The surface answers when the figure has landed, or why it could not. */
function ontoPage(g) {
  if (!hooks.place) return "no page here";
  var said = hooks.place(g);
  if (said && typeof said.then === "function") {
    said.then(function (msg) {
      if (typeof msg === "string" && els.said) els.said.textContent = msg;
    });
    return "placing " + g.id + "…";
  }
  return typeof said === "string" ? said : null;
}

window.Problem = {
  init: init,
  paint: paint,
  open: function () { setOpen(true); },
  close: function () { setOpen(false); },
  isOpen: function () { return !!(els.panel && !els.panel.hidden); },
  /* For the tests: the chip menu's actions, as a tap on them would run them. */
  act: function (id, what) {
    var g = ((problem && problem.givens) || []).filter(function (x) { return x.id === id; })[0];
    if (!g) return null;
    menuFor = g;
    return { calc: toCalculator, say: intoTyped, copy: copyTex, page: ontoPage }[what](g);
  },
};

})();
