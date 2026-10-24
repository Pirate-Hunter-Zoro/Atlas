/* ==========================================================================
   address.js -- ONE GRAMMAR FOR NAMING A PLACE, AND ONE WAY TO SPELL IT.

   A link needs a name for a place, and a name is only worth having if exactly
   one spelling of it exists:

       #/s/<session>                           a session, on its board
       #/s/…/card/<nnnn>                       one card in that session
       #/s/…/doc/<ident>[/p<n>]                a document, optionally one page
       #/s/…/slate/<nnnn>                      one page of its handwriting

   Nothing else is an address: `#/w/…`, the workspace grammar, parses as none.

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

var SESSION_PREFIX = "/s/";
/* `sessions.ID_RE`: the local time to the second, and `-2`... on a clash. */
var SESSION = /^[0-9]{8}-[0-9]{6}(?:-[0-9]{1,4})?$/;
/* What a session address may name after its id. */
var SESSION_SURFACES = ["session", "card", "doc", "slate"];

var NNNN    = /^[0-9]{4}$/;             /* a card, and a page of the slate */
var IDENT   = /^[a-z0-9-]{1,40}$/;      /* a document id's charset (library) */
var PAGE    = /^p([0-9]{1,4})$/;

/* A malformed escape throws, and an address that throws is a page that goes
   blank. Every decode in here is this one. */
function decode(s) {
  try { return decodeURIComponent(s); } catch (e) { return null; }
}

/* `.`, `..`, slashes, backslashes and control characters are out of every
   component: none of these ever becomes a path, and a component that looks
   like a path traversal is a bug being written rather than an address. */
function clean(s) {
  if (s === null) return null;
  if (s === "." || s === ".." || s.indexOf("/") >= 0 || s.indexOf("\\") >= 0) {
    return null;
  }
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
  if (s.indexOf(SESSION_PREFIX) !== 0) return null;

  var raw = s.slice(SESSION_PREFIX.length).split("/");
  var parts = [];
  for (var i = 0; i < raw.length; i++) {
    /* An empty component is `//` or a trailing slash. Both are somebody's
       string concatenation, not an address. */
    if (raw[i] === "") return null;
    var one = clean(decode(raw[i]));
    if (one === null) return null;
    parts.push(one);
  }

  /* A SESSION, by its id and nothing else: the id is the directory name
     `sessions.ID_RE` allows, and the server looks it up rather than building
     a path from it. */
  if (!parts.length || !SESSION.test(parts[0])) return null;
  var a = { session: parts[0], surface: "session", card: "", doc: "", page: 0 };
  var rest = parts.slice(1);
  if (rest.length && !readSurface(a, rest)) return null;

  /* Its own canonical spelling, carried with it. Everything that echoes an
     address back at a person -- "that is not here any more" most of all --
     prints this rather than whatever was typed. */
  a.text = spell(a);
  return a.text ? a : null;
}

/* What follows the session: `rest[0]` names the surface and the rest are its
   arguments. Fills `a` and says whether it was well formed. */
function readSurface(a, rest) {
  var what = rest[0];
  var arg = rest.slice(1);
  var m;
  if (what === "card") {
    if (arg.length !== 1 || !NNNN.test(arg[0])) return false;
    a.surface = "card";
    a.card = arg[0];
  } else if (what === "doc") {
    if (!arg.length || arg.length > 2 || !IDENT.test(arg[0])) return false;
    a.surface = "doc";
    a.doc = arg[0];
    if (arg.length === 2) {
      m = PAGE.exec(arg[1]);
      if (!m || Number(m[1]) < 1) return false;
      a.page = Number(m[1]);
    }
  } else if (what === "slate") {
    if (arg.length !== 1 || !NNNN.test(arg[0])) return false;
    a.surface = "slate";
    a.page = Number(arg[0]);
  } else {
    return false;
  }
  return true;
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
   its canonical text are built by one piece of code. Only the surfaces a
   session has; anything else is not spelled at all. */
function spell(spec) {
  var sid = String(spec.session || "");
  if (!SESSION.test(sid)) return "";
  var bits = [sid];
  var surface = spec.surface || "session";
  if (surface === "session") {
    /* nothing more */
  } else if (surface === "card") {
    bits.push("card", pad4(spec.card || ""));
  } else if (surface === "doc") {
    bits.push("doc", encodeURIComponent(spec.doc || ""));
    if (spec.page) bits.push("p" + Number(spec.page));
  } else if (surface === "slate") {
    bits.push("slate", pad4(spec.page || ""));
  } else {
    return "";
  }
  return "#" + SESSION_PREFIX + bits.join("/");
}

host.Address = {
  SESSION_PREFIX: SESSION_PREFIX,
  SESSION_SURFACES: SESSION_SURFACES,
  parse: parse,
  format: format
};

})(typeof window !== "undefined" ? window : this);
