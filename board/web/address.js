/* ==========================================================================
   address.js -- ONE GRAMMAR FOR NAMING A PLACE, AND ONE WAY TO SPELL IT.

   Nothing in this system had an address. A meeting note could say "the grid
   search is blocked", a paper could cite its own figure, an annotation could
   be about line 74 -- and none of them could point AT the thing. A link needs
   a name for a place, and a name is only worth having if exactly one spelling
   of it exists.

       #/w/<family>/<workspace>                the workspace, on its map
       #/w/…/node/<id>                         one box on that map
       #/w/…/card/<nnnn>                       one card in the current lesson
       #/w/…/archive/<sitting>/<nnnn>          one card in a finished sitting
       #/w/…/doc/<ident>[/p<n>]                a document, optionally one page
       #/w/…/code/<path>[::<symbol>]           a walk unit
       #/w/…/tree/<family>/<name>              a vendor tree, drawn, read here
       #/w/…/hw/<set>/<problem>                one problem of a problem set
       #/w/…/slate/<nnnn>                      one page of handwriting

   This file is the grammar and NOTHING else. It parses, it spells, and it has
   no opinion about what a browser should then do -- `board.js` owns that, in
   one function, because two things that open an address is two behaviours that
   drift. It touches no DOM, makes no request, and reads no state, so both
   pages can load it and a test can drive it with no browser at all.

   Three rules it exists to make keepable:

     1. A NAME FROM A BROWSER NEVER REACHES A FILESYSTEM. Nothing here builds a
        path. It hands back components that the resolver looks up in what
        discovery already found, and a miss is a miss.
     2. A LINK THAT NO LONGER RESOLVES SAYS SO WHERE IT IS WRITTEN. That is the
        resolver's job, but it is only possible because a dead address still
        PARSES: an address naming a card that has gone is well formed and
        unresolvable, which is a different answer from gibberish, and the two
        are reported differently.
     3. ONE SPELLING. `parse` is strict on purpose -- a card is four digits,
        never seven and never one -- and `format` is the only thing anywhere
        that builds an address. Every link in the system goes through it, and
        it refuses to spell anything it could not then read back.
   ========================================================================== */

(function (host) {
"use strict";

var PREFIX = "/w/";

/* A family or a workspace is a DIRECTORY NAME, and one of them is `To Turn In`,
   so spaces are in and are percent-encoded on the way out. Backslashes, control
   characters, `.` and `..` are out, here and in every other component: none of
   these ever becomes a path, and a component that looks like a path traversal
   is a bug being written rather than an address. */
var PLACE   = /^[A-Za-z0-9][A-Za-z0-9 ._-]{0,79}$/;
var NODE    = /^[a-z0-9-]{1,40}$/;      /* `map.py`'s own rule for an id */
var NNNN    = /^[0-9]{4}$/;             /* a card, and a page of the slate */
var SITTING = /^[A-Za-z0-9._-]{1,80}$/; /* `20260912-183613-ch-03-rings`     */
var IDENT   = /^[a-z0-9-]{1,40}$/;      /* `reading.ident`'s own charset     */
var PAGE    = /^p([0-9]{1,4})$/;
var SET     = /^[A-Za-z0-9._-]{1,60}$/;
var PROBLEM = /^[A-Za-z0-9.()_-]{1,24}$/;
var SYMBOL  = /^[A-Za-z_][A-Za-z0-9_.]{0,80}$/;
var SEG     = /^[A-Za-z0-9._-]{1,100}$/; /* one segment of a source path */

var SURFACES = ["workspace", "node", "card", "archive", "doc", "code", "hw",
                "slate", "tree"];

/* A malformed escape throws, and an address that throws is a page that goes
   blank. Every decode in here is this one. */
function decode(s) {
  try { return decodeURIComponent(s); } catch (e) { return null; }
}

function clean(s) {
  if (s === null) return null;
  if (s === "." || s === ".." || s.indexOf("/") >= 0 || s.indexOf("\\") >= 0) {
    return null;
  }
  /* Control characters, whatever they came in as. A tab inside a workspace
     name is not a workspace name. */
  for (var c = 0; c < s.length; c++) {
    var code = s.charCodeAt(c);
    if (code < 0x20 || code === 0x7f) return null;
  }
  return s;
}

/* -------------------------------------------------------------------- parse */
/* An address, or `null`. Never an exception and never a half-read one: a form
   this does not recognise is not an address at all, which is what lets a link
   in a card be marked bad where it is written rather than opening something
   near what it said. */
function parse(text) {
  if (typeof text !== "string") return null;
  var s = text;
  if (s.charAt(0) === "#") s = s.slice(1);
  if (s.indexOf(PREFIX) !== 0) return null;

  var raw = s.slice(PREFIX.length).split("/");
  var parts = [];
  for (var i = 0; i < raw.length; i++) {
    /* An empty component is `//` or a trailing slash. Both are somebody's
       string concatenation, not an address. */
    if (raw[i] === "") return null;
    var one = clean(decode(raw[i]));
    if (one === null) return null;
    parts.push(one);
  }
  if (parts.length < 2) return null;
  if (!PLACE.test(parts[0]) || !PLACE.test(parts[1])) return null;

  var a = {
    ws: parts[0] + "/" + parts[1],
    family: parts[0],
    workspace: parts[1],
    surface: "workspace",
    node: "", card: "", sitting: "", doc: "", page: 0,
    path: "", symbol: "", set: "", problem: "", tree: ""
  };

  var rest = parts.slice(2);
  if (rest.length) {
    var what = rest[0];
    var arg = rest.slice(1);
    var m, j;
    if (what === "node") {
      if (arg.length !== 1 || !NODE.test(arg[0])) return null;
      a.surface = "node";
      a.node = arg[0];
    } else if (what === "card") {
      if (arg.length !== 1 || !NNNN.test(arg[0])) return null;
      a.surface = "card";
      a.card = arg[0];
    } else if (what === "archive") {
      if (arg.length !== 2 || !SITTING.test(arg[0]) || !NNNN.test(arg[1])) {
        return null;
      }
      a.surface = "archive";
      a.sitting = arg[0];
      a.card = arg[1];
    } else if (what === "doc") {
      if (!arg.length || arg.length > 2 || !IDENT.test(arg[0])) return null;
      a.surface = "doc";
      a.doc = arg[0];
      if (arg.length === 2) {
        m = PAGE.exec(arg[1]);
        if (!m || Number(m[1]) < 1) return null;
        a.page = Number(m[1]);
      }
    } else if (what === "code") {
      if (!arg.length) return null;
      /* The path keeps its slashes -- it IS a path, relative to the workspace,
         and it is the one component that spans several. A symbol rides on the
         last segment after `::`, which is the spelling `walk.label` already
         uses everywhere else: in `state.json`, on the strip, and in the
         tutor's prompt. One spelling there and here. */
      var last = arg[arg.length - 1];
      var cut = last.indexOf("::");
      if (cut >= 0) {
        a.symbol = last.slice(cut + 2);
        last = last.slice(0, cut);
        if (!SYMBOL.test(a.symbol)) return null;
      }
      arg = arg.slice(0, arg.length - 1).concat([last]);
      for (j = 0; j < arg.length; j++) {
        if (!SEG.test(arg[j])) return null;
      }
      a.surface = "code";
      a.path = arg.join("/");
    } else if (what === "tree") {
      /* A VENDOR TREE IS READ IN A WORKSPACE, SO IT IS A SURFACE OF ONE.
         Somebody tracing colibrì is doing it for PSYCH-ASR, and the sitting,
         the cards and the marks are PSYCH-ASR's -- so the address names the
         workspace first and the tree second, which is also what makes the
         front door able to route it: it moves the board to the workspace, and
         the board then draws the tree. Two components, because that is how
         `atlas.trees` spells one: a vendor family holding a directory. */
      if (arg.length !== 2 || !PLACE.test(arg[0]) || !PLACE.test(arg[1])) {
        return null;
      }
      a.surface = "tree";
      a.tree = arg[0] + "/" + arg[1];
    } else if (what === "hw") {
      if (arg.length !== 2 || !SET.test(arg[0]) || !PROBLEM.test(arg[1])) {
        return null;
      }
      a.surface = "hw";
      a.set = arg[0];
      a.problem = arg[1];
    } else if (what === "slate") {
      if (arg.length !== 1 || !NNNN.test(arg[0])) return null;
      a.surface = "slate";
      a.page = Number(arg[0]);
    } else {
      return null;
    }
  }

  /* Its own canonical spelling, carried with it. Everything that echoes an
     address back at a person -- "that is not here any more" most of all --
     prints this rather than whatever was typed. */
  a.text = spell(a);
  return a.text ? a : null;
}

/* ------------------------------------------------------------------- format */
/* THE ONLY THING ANYWHERE THAT BUILDS AN ADDRESS. Two spellings of one place
   is two bugs, so every link goes through here, and anything this cannot spell
   is not linked at all rather than linked approximately. */
function format(spec) {
  if (!spec) return "";
  var out = spell(spec);
  /* Read it back before handing it over. A speller that can emit something its
     own parser rejects is a dead link factory. */
  return out && parse(out) ? out : "";
}

function pad4(n) {
  var s = String(n);
  while (s.length < 4) s = "0" + s;
  return s;
}

/* The unchecked half of `format`, shared with `parse` so that an address and
   its canonical text are built by one piece of code. */
function spell(spec) {
  var ws = spec.ws || "";
  var family = spec.family || ws.split("/")[0] || "";
  var workspace = spec.workspace || ws.split("/").slice(1).join("/") || "";
  if (!family || !workspace) return "";

  var bits = [encodeURIComponent(family), encodeURIComponent(workspace)];
  var surface = spec.surface || "workspace";
  var i;

  if (surface === "workspace") {
    /* nothing more */
  } else if (surface === "node") {
    bits.push("node", encodeURIComponent(spec.node || ""));
  } else if (surface === "card") {
    bits.push("card", pad4(spec.card || ""));
  } else if (surface === "archive") {
    bits.push("archive", encodeURIComponent(spec.sitting || ""),
              pad4(spec.card || ""));
  } else if (surface === "doc") {
    bits.push("doc", encodeURIComponent(spec.doc || ""));
    if (spec.page) bits.push("p" + Number(spec.page));
  } else if (surface === "code") {
    var segs = String(spec.path || "").split("/");
    for (i = 0; i < segs.length; i++) segs[i] = encodeURIComponent(segs[i]);
    if (spec.symbol) segs[segs.length - 1] += "::" + spec.symbol;
    bits.push("code");
    bits = bits.concat(segs);
  } else if (surface === "tree") {
    var t = String(spec.tree || "").split("/");
    if (t.length !== 2) return "";
    bits.push("tree", encodeURIComponent(t[0]), encodeURIComponent(t[1]));
  } else if (surface === "hw") {
    bits.push("hw", encodeURIComponent(spec.set || ""),
              encodeURIComponent(spec.problem || ""));
  } else if (surface === "slate") {
    bits.push("slate", pad4(spec.page || ""));
  } else {
    return "";
  }
  return "#" + PREFIX + bits.join("/");
}

/* Two addresses in the same workspace. The one comparison anything outside
   this file needs to make by hand, so it is made here once. */
function same(a, b) {
  return !!a && !!b && a.ws === b.ws;
}

/* What a workspace is called on the wire. `atlas.identify` spells it
   `family/name` and `/health` publishes it under `id`; this is the same string
   and the resolver compares against it rather than against a course's
   human-readable name, which is not unique and not stable. */
function idOf(a) { return a ? a.ws : ""; }

host.Address = {
  PREFIX: PREFIX,
  SURFACES: SURFACES,
  parse: parse,
  format: format,
  same: same,
  idOf: idOf
};

})(typeof window !== "undefined" ? window : this);
