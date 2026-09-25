/* ==========================================================================
   annbar.js -- the annotation tool bar, for a page that is not the board.

   The library and the meeting deck draw on a document with the board's own
   `annotate.js`, and had nothing but a pen switch: one colour, one nib, no
   eraser, no loop, no clipboard, no undo. Marking up a slide is the same act
   as marking up a card, so it gets the same tools -- the board's bar, built
   here in the same markup and classes so `board.css` dresses both alike, plus
   the slate's nibs and its any-colour well, because a white page wants a
   darker ink than a dark card does and nobody should need a second surface to
   get one.

   The page keeps its own pen switch and its own save. It calls `show` when the
   switch flips and `paint` from its `Annotate.onChange`, which holds exactly
   one listener and is the page's.
   ========================================================================== */

(function () {
"use strict";

var INKS = [["#e0b45c", "amber"], ["#e8746c", "red"], ["#6fc3f7", "blue"],
            ["#7fc79a", "green"], ["#16171a", "black"]];
/* The slate's three nibs, scaled to the annotation layer's own default of 2.2
   as the middle one. */
var NIBS = [[1.4, "Fine"], [2.2, "Medium"], [4.0, "Broad"]];

function el(tag, cls, text) {
  var n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

function button(parent, cls, text, title) {
  var b = el("button", cls, text);
  b.type = "button";
  if (title) b.title = title;
  parent.appendChild(b);
  return b;
}

function mount(opts) {
  opts = opts || {};
  var A = window.Annotate;
  if (!A) return { show: function () {}, paint: function () {} };

  var bar = el("div", "annbar annbar-doc");
  bar.hidden = true;

  var bPen = button(bar, "anntool on", "Pen");
  var bErase = button(bar, "anntool", "Erase");
  var bSelect = button(bar, "anntool", "Select", "loop round something to copy, cut or move it");

  var nibBox = el("span", "ann-nibs");
  bar.appendChild(nibBox);
  var nibs = NIBS.map(function (n) {
    var b = button(nibBox, "ann-nib", n[1], n[1].toLowerCase() + " nib");
    b.dataset.w = n[0];
    return b;
  });

  var inkBox = el("span", "ann-inks");
  bar.appendChild(inkBox);
  var inks = INKS.map(function (i) {
    var b = button(inkBox, "ann-ink", null, i[1]);
    b.dataset.ink = i[0];
    b.style.background = i[0];
    return b;
  });
  var well = el("label", "ann-ink ann-custom");
  well.title = "any colour";
  var picker = el("input");
  picker.type = "color";
  picker.value = "#c792ea";
  well.appendChild(picker);
  inkBox.appendChild(well);

  var clip = el("span", "ann-clip");
  clip.hidden = true;
  bar.appendChild(clip);
  var bCopy = button(clip, "", "Copy", "copy what is looped");
  var bCut = button(clip, "", "Cut", "cut what is looped");
  var bPaste = button(clip, "", "Paste", "paste onto this page");
  var bDel = button(clip, "danger", "Delete", "delete what is looped");

  var sayBox = el("span", "ann-say");
  sayBox.hidden = true;
  bar.appendChild(sayBox);

  var bUndo = button(bar, "", "↶", "undo");
  var bRedo = button(bar, "", "↷", "redo");
  var bClear = button(bar, "", "clear", "remove every mark");
  var bDone = button(bar, "primary", "done");

  document.body.appendChild(bar);

  var width = 2.2;
  A.setPen(null, width);

  function paint() {
    var mode = A.tool();
    bPen.classList.toggle("on", mode === "pen");
    bErase.classList.toggle("on", mode === "erase");
    bSelect.classList.toggle("on", mode === "lasso");
    nibs.forEach(function (b) { b.classList.toggle("on", +b.dataset.w === width); });
    var colour = A.colour();
    var stock = false;
    inks.forEach(function (b) {
      var hit = b.dataset.ink === colour;
      if (hit) stock = true;
      b.classList.toggle("on", hit);
    });
    well.classList.toggle("on", !stock);
    well.style.background = picker.value;
    bUndo.disabled = !A.canUndo();
    bRedo.disabled = !A.canRedo();
    bClear.disabled = !A.marked().length;
    /* The clip controls exist while they can do something, as on the board. */
    var picked = A.picked();
    var held = !!(window.InkClip && window.InkClip.has());
    clip.hidden = !(picked || held);
    bCopy.disabled = !picked;
    bCut.disabled = !picked;
    bDel.disabled = !picked;
    bPaste.disabled = !held;
  }

  /* A word in the bar that did the thing: copying has no visible result. */
  var sayTimer = null;
  function say(text) {
    sayBox.textContent = text;
    sayBox.hidden = !text;
    clearTimeout(sayTimer);
    if (text) sayTimer = setTimeout(function () { say(""); }, 2800);
  }
  function whyNot() {
    return A.picked() ? "that is more ink than the clipboard will carry"
                      : "loop round something first";
  }

  function ink(colour) {
    A.setPen(colour, width);
    A.setTool("pen");
    paint();
  }

  bPen.onclick = function () { A.setTool("pen"); paint(); };
  bErase.onclick = function () { A.setTool("erase"); paint(); };
  bSelect.onclick = function () { A.setTool("lasso"); paint(); };
  nibs.forEach(function (b) {
    b.onclick = function () {
      width = +b.dataset.w;
      A.setPen(null, width);
      if (A.tool() !== "pen") A.setTool("pen");
      paint();
    };
  });
  inks.forEach(function (b) { b.onclick = function () { ink(b.dataset.ink); }; });
  picker.addEventListener("input", function () { ink(picker.value); });
  /* Tapping the well when its colour is already chosen is still a choice of
     it, not only an invitation to change it. */
  well.addEventListener("click", function () { ink(picker.value); });

  bCopy.onclick = function () {
    var n = A.copy();
    say(n ? n + " copied — paste it on a page or on your own board" : whyNot());
    paint();
  };
  bCut.onclick = function () { var n = A.cut(); say(n ? n + " cut" : whyNot()); paint(); };
  bPaste.onclick = function () {
    var n = A.paste();
    say(n ? n + " pasted — drag it where you want it" : "nothing copied yet");
    paint();
  };
  bDel.onclick = function () { A.erase(); paint(); };
  bUndo.onclick = function () { A.undo(); paint(); };
  bRedo.onclick = function () { A.redo(); paint(); };
  bClear.onclick = function () { A.clearCurrent(); paint(); };
  bDone.onclick = function () { if (opts.onDone) opts.onDone(); };

  /* The clipboard is shared with the board and the slate, so Paste can become
     worth offering without anything on this page being touched. */
  if (window.InkClip && window.InkClip.onChange) window.InkClip.onChange(paint);

  paint();
  return {
    show: function (on) { bar.hidden = !on; if (on) paint(); },
    paint: paint,
    node: bar
  };
}

window.AnnBar = { mount: mount };
})();
