/* ==========================================================================
   shot.js -- the lesson as the pixels it was actually read as.

   The export is a screenshot of the whole session as the iPad drew it, not a
   typeset paraphrase. It is made here because only the page that drew the
   lesson knows how it looks: the iPad rasterises, and the server owns the
   name, version, repository copy and git staging, the parts a client must
   not be trusted with.

   A DOM becomes pixels through an SVG `foreignObject` drawn into a canvas.
   Two rules keep that honest:

     - An SVG loaded as an image cannot fetch anything, so fonts, stylesheets
       (read from the CSSOM, every `url()` made a data URI) and pictures are
       all inlined; one missed font sets the whole lesson in Times.
     - A cloned `<canvas>` is blank, so every live surface and annotation
       layer is replaced by an image of the original's pixels.

   Pagination is decided here, because only the side holding the pixels can
   cut a card taller than a page without a JPEG decoder. The server receives
   finished, same-size pages and wraps each in a PDF page.
   ========================================================================== */

(function (global) {
  "use strict";

  /* A4 portrait, because that is what a professor prints. The pixels are
     whatever the board's own column is, times the device's ratio, so the type
     is the size it was read at rather than the size a page happens to want. */
  var A4_RATIO = 841.89 / 595.28;
  /* Capped at 2. A ratio-3 iPad on a long lesson is nine times the pixels for a
     difference nobody can see in a PDF, and canvas budget on iPadOS is answered
     with blank canvases rather than an error. */
  var MAX_SCALE = 2;
  var QUALITY = 0.9;
  /* The server's body limit is 64MB. Stop well short of it and say so, rather
     than sending something that is refused after the whole evening's work has
     been encoded. */
  var MAX_BYTES = 40 * 1024 * 1024;

  /* Controls, and things that were never on the glass. A screenshot with a live
     Send button in it is not a screenshot of anything -- it is a picture of a
     control that does nothing, in a document somebody is emailing to their
     professor. The ink and the words stay; the furniture goes. */
  var FURNITURE = ".board-send, .board-carry, .to-board, #skip, .drawbar,"
                + " #drawbar, .annbar, .sendwhat, .notesend, #notepick, .jump,"
                + " #writer-head .tabs, #typebox button, #said-label";

  /* ------------------------------------------------------------ the styles */

  var styleCache = null;
  var urlCache = Object.create(null);

  function fetchDataUri(url) {
    if (urlCache[url]) return urlCache[url];
    urlCache[url] = fetch(url, { credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.blob();
      })
      .then(blobToDataUri)
      .catch(function () { return null; });
    return urlCache[url];
  }

  function blobToDataUri(blob) {
    return new Promise(function (resolve, reject) {
      var fr = new FileReader();
      fr.onload = function () { resolve(fr.result); };
      fr.onerror = function () { reject(fr.error || new Error("unreadable")); };
      fr.readAsDataURL(blob);
    });
  }

  /* Every `url()` in a sheet, resolved against the sheet it came from.
     `cssText` hands back the URL as it was AUTHORED, and katex.min.css writes
     `url(fonts/KaTeX_Main-Regular.woff2)` -- relative to /static/katex/, which
     is not where this page is. Resolving against the document instead is how
     you get a lesson with no mathematics in it. */
  function inlineUrls(cssText, base) {
    var jobs = [];
    var seen = Object.create(null);
    cssText.replace(/url\(\s*(['"]?)([^'")]+)\1\s*\)/g, function (all, q, raw) {
      if (/^(data|blob):/i.test(raw) || seen[raw]) return all;
      seen[raw] = true;
      var abs;
      try { abs = new URL(raw, base).href; } catch (e) { return all; }
      jobs.push(fetchDataUri(abs).then(function (uri) {
        return { raw: raw, uri: uri };
      }));
      return all;
    });
    return Promise.all(jobs).then(function (got) {
      got.forEach(function (g) {
        if (!g.uri) return;
        /* Replace the authored form wherever it appears, quoted or not. */
        cssText = cssText.split("url(" + g.raw + ")").join("url(" + g.uri + ")")
                         .split('url("' + g.raw + '")').join('url("' + g.uri + '")')
                         .split("url('" + g.raw + "')").join("url('" + g.uri + "')");
      });
      return cssText;
    });
  }

  /* `html`, `:root` and `body` all become the wrapper.
     The clone cannot be a document -- a `foreignObject` holds an element, not a
     page -- so the element standing in for the page has to answer to the
     selectors written about one. `body[data-face="serif"]`, `body.annotating`
     and `:root{--paper:...}` are all real rules in board.css and all three
     decide what the lesson looks like.

     The lookahead is what keeps `.card .body` alone: `body` there is preceded by
     a `.`, which is not one of the characters a selector boundary can be. */
  function rootward(selector) {
    return selector
      .replace(/(^|[\s,>+~(])(?:html|body)(?![\w-])/g, "$1.tb-shot")
      .replace(/(^|[\s,>+~(]):root(?![\w-])/g, "$1.tb-shot");
  }

  /* Every selector is scoped under the wrapper, and that is what lets the
     bundle be attached to the LIVE DOCUMENT for the measurement.

     The measurement and the render have to agree about layout to the pixel --
     a picture's position is measured against one and drawn against the other --
     and the only way to be sure of that is for both to be the same stylesheet
     over the same structure. Unscoped, a `<style>` in the body would restyle
     the lesson the student is reading while the export runs. Scoped, nothing in
     it can match anything outside the wrapper. */
  function scope(selector) {
    return selector.split(",").map(function (part) {
      part = rootward(part).trim();
      if (!part) return part;
      return part.indexOf(".tb-shot") === 0 ? part : ".tb-shot " + part;
    }).join(", ");
  }

  /* REM AND THE VIEWPORT UNITS BECOME PIXELS, and this is the difference
     between a photograph and a near-miss.

     `rem` is the font size of the DOCUMENT ROOT, and the fragment in a
     `foreignObject` has no `<html>` -- the root of that document is the `<svg>`
     element, so every `rem` in the sheet resolved to the initial 16px instead of
     the board's own 18. Everything sized in rem came out an eighth small, which
     on `.mine { max-width: 32rem }` moved every right-aligned student turn
     sixty-three pixels -- and dragged the handwriting drawn into it out of its
     box. It looked like a compositing bug and was a units bug.

     Viewport units are the same story with a different cause: they resolve
     against the SVG's viewport rather than the window, and the writing surface
     is sized `clamp(18rem, 74svh, 60rem)`.

     Both are settled by resolving them HERE, against the window the lesson is
     actually being read in -- which is also the honest answer to what a
     screenshot is. */
  var UNIT = /(-?[\d.]+)(rem|svh|lvh|dvh|svw|lvw|dvw|vmin|vmax|vh|vw)\b/g;
  /* NOT INSIDE A `url()`, and this cost an afternoon. The bundle carries every
     font inlined as base64, and base64 is full of things that look exactly like
     a length: `...9vh+...` is a digit, one of these unit names, and then a
     non-word character, which is a word boundary. Converting it rewrote the
     middle of the font file -- so the reading face silently fell back to a
     system sans, and the corrupted declaration took the rules after it with it.
     Everything looked plausible and nothing was right. */
  var URLSPAN = /url\(\s*(?:'[^']*'|"[^"]*"|[^)]*)\s*\)/g;

  function unitsToPx(text) {
    var root = parseFloat(
      global.getComputedStyle(document.documentElement).fontSize) || 16;
    var vw = (global.innerWidth || 1024) / 100;
    var vh = (global.innerHeight || 1366) / 100;
    var vmin = Math.min(vw, vh), vmax = Math.max(vw, vh);

    function convert(chunk) {
      return chunk.replace(UNIT, function (all, n, unit) {
        var v = parseFloat(n);
        if (!isFinite(v)) return all;
        var per = unit === "rem" ? root
                : unit === "vmin" ? vmin
                : unit === "vmax" ? vmax
                : /w$/.test(unit) ? vw : vh;
        return (v * per).toFixed(3).replace(/\.?0+$/, "").replace(/\.$/, "") + "px";
      });
    }

    var out = "";
    var at = 0;
    var m;
    URLSPAN.lastIndex = 0;
    while ((m = URLSPAN.exec(text)) !== null) {
      out += convert(text.slice(at, m.index)) + m[0];
      at = m.index + m[0].length;
    }
    return out + convert(text.slice(at));
  }

  /* A STILL CANNOT ANIMATE, AND `both` MEANS IT RENDERS THE FIRST FRAME.
     `.card.fresh { animation: rise .28s ease-out both }` and
     `@keyframes rise { from { opacity: 0 } }`. Nothing animates inside an SVG
     loaded as an image, so a card that had just arrived would export at the
     start of its entrance -- transparent. The newest thing the tutor wrote is
     the likeliest thing somebody exports, so this is not a corner. */
  var STILL = ".tb-shot, .tb-shot *"
            + "{animation:none!important;transition:none!important}";

  /* AND A BOARD IS BROUGHT BACK INSIDE THE COLUMN.

     `#writer, .board` carry a negative margin -- `--bleed`, computed from
     `50% - 50vw` -- so a writing surface is WIDER than the prose it sits under
     and spills into the margins of the glass. That is right on a tablet, where
     the margin is dead space and a hand wants the room.

     On a page it is not: the document would have to be as wide as the widest
     board, which means two hundred pixels of empty paper down each side of every
     page of prose, a bigger file, and smaller type when it is printed. Left
     alone it is worse still -- the photograph is the column wide, so the bleed
     was simply CUT: the answer panel came out reading "R ANSWER".

     So the paper is the column, and a board is the column wide. It is the one
     place this deliberately photographs something other than what the glass
     shows, and the reason is that paper has edges and a tablet does not. */
  var FLAT = ".tb-shot #writer, .tb-shot .board"
           + "{margin-left:0!important;margin-right:0!important}";

  var customProps = [];

  function readSheets() {
    var parts = [];
    var props = Object.create(null);
    Array.prototype.forEach.call(document.styleSheets, function (sheet) {
      var rules;
      try { rules = sheet.cssRules; } catch (e) { return; }   /* cross-origin */
      if (!rules) return;
      var text = [];
      Array.prototype.forEach.call(rules, function (rule) { walk(rule, text, props); });
      if (!text.length) return;
      parts.push({ css: text.join("\n"), base: sheet.href || document.baseURI });
    });
    customProps = Object.keys(props);
    return parts;
  }

  function walk(rule, out, props) {
    /* A style rule: scope its selector, keep its body, and note any custom
       property it declares so the palette can be pinned afterwards. */
    if (rule.type === 1 /* STYLE_RULE */ && rule.style) {
      for (var i = 0; i < rule.style.length; i++) {
        var name = rule.style[i];
        if (name.slice(0, 2) === "--") props[name] = true;
      }
      out.push(scope(rule.selectorText) + "{" + rule.style.cssText + "}");
      return;
    }
    /* A CONDITION IS RESOLVED HERE, NOT IN THE SVG.
       `print` is dropped -- there is a print stylesheet on this page that turns
       the board into black on white, and it is not what is being photographed.
       Everything else is asked of THIS window and then flattened away, because
       a media query left in place would be re-evaluated against the SVG's own
       viewport and colour scheme: a board read in dark could photograph itself
       in the light rules, and a 792-pixel SVG could take the narrow-screen
       layout of a phone. Flat, there is nothing left to disagree about. */
    if (rule.type === 4 /* MEDIA_RULE */) {
      var cond = rule.conditionText || (rule.media && rule.media.mediaText) || "";
      if (/\bprint\b/.test(cond)) return;
      var on = true;
      try { on = global.matchMedia(cond).matches; } catch (e) { on = true; }
      if (!on) return;
      Array.prototype.forEach.call(rule.cssRules || [], function (r) {
        walk(r, out, props);
      });
      return;
    }
    if (rule.type === 12 /* SUPPORTS_RULE */) {
      var yes = true;
      try {
        yes = !global.CSS || !global.CSS.supports
            || global.CSS.supports(rule.conditionText);
      } catch (e) { yes = true; }
      if (!yes) return;
      Array.prototype.forEach.call(rule.cssRules || [], function (r) {
        walk(r, out, props);
      });
      return;
    }
    /* @font-face and @keyframes: verbatim. A font-face is the whole ballgame,
       and a keyframe is inert in a still. */
    if (rule.cssText) out.push(rule.cssText);
  }

  function styles() {
    if (styleCache) return styleCache;
    var parts = readSheets();
    styleCache = Promise.all(parts.map(function (p) {
      return inlineUrls(p.css, p.base);
    })).then(function (done) {
      return unitsToPx(done.join("\n")) + "\n" + STILL + "\n" + FLAT;
    });
    return styleCache;
  }

  /* ------------------------------------------------------- the clone itself */

  /* What the live page resolved the palette and the face to, as an inline
     style. Belt and braces now that the bundle is flattened -- but the braces
     still earn their place: custom properties inherit, so pinning them on the
     wrapper settles the paper, the ink, every accent, the reading face and the
     leading in one declaration that nothing downstream can argue with. */
  function pinnedProps() {
    var cs = global.getComputedStyle(document.body);
    var out = [];
    customProps.forEach(function (name) {
      var v = cs.getPropertyValue(name);
      /* Raw tokens, not resolved lengths: a custom property whose value is
         written in rem would resolve against the SVG's root. Same conversion,
         same reason. */
      if (v && v.trim()) out.push(name + ":" + unitsToPx(v.trim()));
    });
    return out.join(";") + (out.length ? ";" : "");
  }

  function copyIdentity(from, to) {
    if (!from) return;
    Array.prototype.forEach.call(from.attributes, function (a) {
      if (a.name === "id" || a.name === "style") return;
      if (a.name === "class") {
        to.className = (to.className ? to.className + " " : "") + a.value;
        return;
      }
      try { to.setAttribute(a.name, a.value); } catch (e) { /* invalid here */ }
    });
  }

  /* ------------------------------------------------------------- pictures */

  /* No picture ever goes through the SVG. WebKit does not paint an `<img>`,
     a background, an SVG `<image>` or a cloned canvas inside a `foreignObject`
     of an SVG loaded as an image (Blink does, which is how it hides). So the
     pictures are composited directly onto the page with `drawImage`, from the
     elements the board already shows (same-origin, already decoded), and the
     SVG carries a same-size hole so the words wrap as on the glass. Nothing is
     fetched or base64'd. */

  function px(value) {
    var n = parseFloat(value);
    return isFinite(n) ? n : 0;
  }

  /* Where the picture actually sits inside the box CSS gave it.

     `.board-shot` -- every dormant board, which is to say every past answer --
     is `object-fit: cover; object-position: top left`, so a straight stretch to
     the box would squash an evening's working. `contain` is here because the
     rule exists in the sheet; `fill` is the default and the common case. */
  function fitBox(fit, position, box, natural) {
    var out = { bx: box.x, by: box.y, bw: box.w, bh: box.h,
                sx: 0, sy: 0, sw: natural.w, sh: natural.h };
    if (!natural.w || !natural.h || !box.w || !box.h) return out;
    var boxAR = box.w / box.h;
    var srcAR = natural.w / natural.h;
    var top = /top/.test(position || "");
    var left = /left/.test(position || "");

    if (fit === "cover") {
      /* Crop the source to the box's shape. */
      if (srcAR > boxAR) {
        out.sw = natural.h * boxAR;
        out.sx = left ? 0 : (natural.w - out.sw) / 2;
      } else {
        out.sh = natural.w / boxAR;
        out.sy = top ? 0 : (natural.h - out.sh) / 2;
      }
      return out;
    }
    if (fit === "contain" || fit === "scale-down") {
      /* Inset the destination instead, and fold the inset into the box so the
         page-splitting arithmetic downstream stays one rule. */
      if (srcAR > boxAR) {
        var h = box.w / srcAR;
        out.bh = h;
        out.by = box.y + (top ? 0 : (box.h - h) / 2);
      } else {
        var w = box.h * srcAR;
        out.bw = w;
        out.bx = box.x + (left ? 0 : (box.w - w) / 2);
      }
      return out;
    }
    return out;                       /* fill: stretch, which is the default */
  }

  /* A `loading="lazy"` picture below the fold is not loaded and cannot be
     drawn, so the export loads its own copy rather than touch the lesson
     being read. */
  function drawable(node) {
    if (node.tagName === "CANVAS") {
      return Promise.resolve((node.width && node.height) ? node : null);
    }
    if (node.complete && node.naturalWidth) return Promise.resolve(node);
    var src = node.currentSrc || node.getAttribute("src") || "";
    if (!src) return Promise.resolve(null);
    return new Promise(function (resolve) {
      var copy = new Image();
      copy.onload = function () { resolve(copy); };
      copy.onerror = function () { resolve(null); };
      copy.src = src;
    });
  }

  /* Every picture in the block, left where it is and remembered, because a
     stand-in box changes a shrink-to-fit block's width. WebKit lays an `<img>`
     out inside the SVG and only refuses to paint it, so the layout stays and
     the picture is drawn over the space it left. On the clone `alt` is cleared
     (no alt text where a picture will go) and the natural size is written as
     attributes, so an unfetchable image still knows its size; CSS still wins. */
  function findPictures(original, clone) {
    var src = original.querySelectorAll ? original.querySelectorAll("img, canvas") : [];
    var dst = clone.querySelectorAll("img, canvas");
    var found = [];
    for (var i = 0; i < dst.length && i < src.length; i++) {
      var was = src[i], now = dst[i];
      if (!now.parentNode) continue;
      var cs = global.getComputedStyle(was);
      if (cs.display === "none" || cs.visibility === "hidden") continue;

      if (now.tagName === "IMG") {
        now.setAttribute("alt", "");
        var nw = was.naturalWidth || 0, nh = was.naturalHeight || 0;
        if (nw && nh && !now.hasAttribute("width")) {
          now.setAttribute("width", nw);
          now.setAttribute("height", nh);
        }
      }
      found.push({
        node: now,
        source: was,
        fit: cs.objectFit || "fill",
        position: cs.objectPosition || "50% 50%",
      });
    }
    return found;
  }

  /* Their rectangles, relative to the column, once the clone has been laid out --
     and the loaded picture to draw into each.

     The rectangle is the border box and a picture paints in the CONTENT box, so
     the border and any padding come off. One pixel of border, on the frozen
     answers, which is exactly the kind of edge that shows as a hairline of the
     wrong colour along the top of an evening's handwriting. */
  function placePictures(found, origin) {
    return Promise.all(found.map(function (item) {
      var r = item.node.getBoundingClientRect();
      var cs = global.getComputedStyle(item.node);
      var l = px(cs.borderLeftWidth) + px(cs.paddingLeft);
      var t = px(cs.borderTopWidth) + px(cs.paddingTop);
      var rr = px(cs.borderRightWidth) + px(cs.paddingRight);
      var b = px(cs.borderBottomWidth) + px(cs.paddingBottom);
      var box = { x: r.left - origin.left + l, y: r.top - origin.top + t,
                  w: r.width - l - rr, h: r.height - t - b };
      if (box.w < 1 || box.h < 1) return null;
      return drawable(item.source).then(function (img) {
        if (!img) return null;
        var natural = { w: img.naturalWidth || img.width || 0,
                        h: img.naturalHeight || img.height || 0 };
        if (!natural.w || !natural.h) return null;
        var place = fitBox(item.fit, item.position, box, natural);
        place.img = img;
        return place;
      });
    })).then(function (all) { return all.filter(Boolean); });
  }

  function stripFurniture(clone) {
    Array.prototype.forEach.call(clone.querySelectorAll(FURNITURE), function (n) {
      if (n.parentNode) n.parentNode.removeChild(n);
    });
    Array.prototype.forEach.call(clone.querySelectorAll("[hidden]"), function (n) {
      if (n.parentNode) n.parentNode.removeChild(n);
    });
    Array.prototype.forEach.call(clone.querySelectorAll("script"), function (n) {
      if (n.parentNode) n.parentNode.removeChild(n);
    });
    stripComments(clone);
  }

  /* AND EVERY COMMENT, because XML forbids a double hyphen inside one.

     Diagnosed by parsing the serialised SVG and reading the error: "Double
     hyphen within comment: <!-- A follow-up question is a new board, and a new
     bo...". `board.html` explains itself at length and in prose, so its
     comments are full of dashes -- this very sentence would break one -- and
     any block whose markup came from the page rather than from `render` failed
     to parse and rasterised to nothing.

     Which is why it was the WRITING SURFACE that went missing, and only that: a
     card is built by JavaScript and carries no comments, so the export looked
     entirely correct while the one block holding the student's unsent working
     was silently absent. A comment is not a pixel; none of them belong here. */
  function stripComments(node) {
    var kids = node.childNodes;
    for (var i = kids.length - 1; i >= 0; i--) {
      var kid = kids[i];
      if (kid.nodeType === 8 /* COMMENT_NODE */) node.removeChild(kid);
      else if (kid.nodeType === 1 /* ELEMENT_NODE */) stripComments(kid);
    }
  }

  /* The board's own column, so a block is laid out at the width it was read at
     rather than at whatever an SVG decides. Read off the live element: the
     measure is `46rem` capped by the window, and which of those wins depends on
     the device this is running on. */
  function columnBox() {
    var board = document.getElementById("board");
    var cs = board ? global.getComputedStyle(board) : null;
    var inner = board ? board.clientWidth : 720;
    if (cs) {
      inner -= parseFloat(cs.paddingLeft || 0) + parseFloat(cs.paddingRight || 0);
    }
    return {
      width: Math.max(320, Math.round(inner)),
      pad: cs ? Math.round(parseFloat(cs.paddingLeft || 0)) : 16,
      paper: cs ? cs.backgroundColor : "#16171a",
      font: cs ? cs.fontSize : "16px",
    };
  }

  /* ------------------------------------------------------ a block, as pixels */

  /* The clone is serialised as XML, not HTML: the SVG is parsed as XML, where
     an unclosed `<img>` is a parse error that blanks the whole block (exactly
     the blocks holding handwriting or annotations). `XMLSerializer` closes
     void elements, declares the XHTML namespace and escapes text, and the
     escaping round-trips through the SVG's own parser. */
  function serialize(node) {
    return new XMLSerializer().serializeToString(node);
  }

  /* RASTERISED AT THE DEVICE'S RESOLUTION, not at the column's.

     The lesson is laid out in CSS pixels and the page is drawn in device ones,
     and an SVG is only resolution-independent if it is ASKED for the larger
     size. Given its intrinsic size and then scaled up by `drawImage`, a browser
     is free to rasterise once at the small size and stretch the bitmap -- which
     on a retina tablet is a document of soft type, and soft type is the one
     thing a photograph of a screen cannot be forgiven.

     So the SVG is `scale` times as big and its contents are scaled to match.
     The foreignObject keeps the CSS box, so the layout is identical; only the
     grid it is drawn on gets finer. The blit onto the page is then 1:1. */
  /* CSS size, and `drawImage` does the enlarging: WebKit re-rasterises an SVG
     image at the size it is drawn, so the result is sharp on a retina tablet.
     Asking for the larger size inside the SVG (a scaling group, or a smaller
     viewBox) loses KaTeX glyphs while the prose survives. */
  function svgFor(body, width, height) {
    return '<svg xmlns="http://www.w3.org/2000/svg" width="' + width
      + '" height="' + height + '" viewBox="0 0 ' + width + " " + height + '">'
      + '<foreignObject x="0" y="0" width="' + width + '" height="' + height + '">'
      + body
      + "</foreignObject></svg>";
  }

  /* The element that stands in for the page, with the lesson inside it.
     Built as a NODE rather than as a string so the serialiser can do its work
     on the whole thing at once.

     `overflow:hidden` is not tidiness: it establishes a block formatting
     context, so a card's own top margin stays INSIDE this box instead of
     collapsing through it. The measuring stage carries the same rule for the
     same reason, and the two have to agree exactly -- every picture's position
     is measured against one of them and drawn against the other. */
  /* THE WRAPPER STANDS IN FOR `body`'S LOOK, NEVER FOR ITS SIZE.

     It carries body's classes and attributes so the reading face and the
     palette are the page's own -- and that means body's own rules land on it,
     including `body { min-height: 100vh }`, which exists so there is something
     to paint the bottom of a screen with. Pixelised to the window's height,
     that made every single card exactly one page tall: a seven-page document
     for four cards, each of them floating at the top of a sheet of empty paper.
     Which looked like a pagination bug and was a stylesheet doing exactly what
     it says.

     So the box is stated inline, where it beats the sheet, and it is stated
     completely: `height`, `min-height` and `max-height` together, because
     overriding one of the three leaves the others to decide. */
  function boxStyle(width, extra) {
    return "display:block;overflow:hidden;box-sizing:content-box;"
      + "width:" + width + "px;padding:0;border:0;margin:0;"
      + "height:auto;min-height:0;max-height:none;min-width:0;max-width:none;"
      + (extra || "");
  }

  function wrapperFor(clone, css, width, pinned, identity) {
    var wrap = document.createElement("div");
    wrap.className = "tb-shot" + (identity.cls ? " " + identity.cls : "");
    identity.attrs.forEach(function (a) {
      try { wrap.setAttribute(a.name, a.value); } catch (e) { /* invalid here */ }
    });
    wrap.setAttribute("style", boxStyle(width, pinned || ""));
    var style = document.createElement("style");
    style.textContent = css;
    /* A `<style>` in flow would be a box if a UA stylesheet did not hide it,
       and this fragment is not a document with a head to put it in. */
    style.setAttribute("style", "display:none");
    wrap.appendChild(style);
    wrap.appendChild(clone);
    return wrap;
  }

  /* A data URL, not a blob URL: a `blob:` SVG taints the canvas and
     `toDataURL` then throws. Percent-encoded rather than base64, because
     `btoa` throws outside Latin-1 and KaTeX emits U+2061 and friends. */
  function loadImage(svg) {
    return new Promise(function (resolve, reject) {
      var img = new Image();
      img.decoding = "sync";
      img.onload = function () { resolve(img); };
      img.onerror = function () {
        reject(new Error("the browser would not rasterise the lesson"));
      };
      img.src = "data:image/svg+xml;charset=utf-8,"
        + encodeURIComponent(svg).replace(/'/g, "%27");
    });
  }

  /* ------------------------------------------------------------ the pages */

  /* The blocks of the lesson, in reading order: the tutor's cards, the
     student's turns, and the boards under them. `#cards`' own children, which is
     what the transcript is -- and skipping anything not on the glass, because a
     hidden node has a rectangle of zeros and would come out as a blank page. */
  function blocks() {
    var host = document.getElementById("cards");
    if (!host) return [];
    return Array.prototype.filter.call(host.children, function (n) {
      if (n.hidden) return false;
      var cs = global.getComputedStyle(n);
      if (cs.display === "none" || cs.visibility === "hidden") return false;
      if (n.getBoundingClientRect().height <= 1) return false;
      /* A BLANK SHEET IS NOT PART OF THE RECORD.

         The live writing surface is on the glass and is a foot of dark paper
         with nothing on it -- as the last thing in a document somebody is
         emailing to their professor, it reads as a page that went wrong. But
         working that has been drawn and not yet sent is the student's and
         belongs in the photograph, so the question is not "is this the live
         board" but "has anything been written on it". The slate already answers
         exactly that, for exactly this reason: `strokes()` is what stops Send
         handing the tutor an empty sheet. The board hands it over here. */
      if (n.id === "writer" && typeof api.liveInk === "function") {
        try { if (!api.liveInk()) return false; } catch (e) { /* then keep it */ }
      }
      return true;
    });
  }

  /* One block, as an image of itself at the column's width. Its height is
     measured by laying the clone out in this document, since the SVG honours
     whatever height it is told. */
  /* What the page IS, as an element can carry it: every attribute of `html` and
     `body` merged onto one node, so `body.annotating` and `[data-face]` still
     decide. Read once -- it cannot change between two blocks of the same
     photograph, and reading it per block is a forced style resolution per card
     on the device least able to afford one. */
  function identityOf() {
    var probe = document.createElement("div");
    copyIdentity(document.documentElement, probe);
    copyIdentity(document.body, probe);
    var attrs = [];
    Array.prototype.forEach.call(probe.attributes, function (a) {
      if (a.name === "class") return;
      attrs.push({ name: a.name, value: a.value });
    });
    return { cls: probe.className, attrs: attrs };
  }

  function shootBlock(node, css, box, pinned, identity) {
    var clone = node.cloneNode(true);
    stripFurniture(clone);
    var pictures = findPictures(node, clone);

    /* Measured without the bundled stylesheet, attached to the live document so
       the page's own CSS lays it out: a `<style>` in `<body>` is global and
       would restyle the lesson being read. `visibility:hidden`, not
       `display:none`, which measures as zero height. */
    /* MEASURED THROUGH THE VERY WRAPPER THAT WILL BE RENDERED.
       Not a stand-in for it: the same element, the same scoped stylesheet, the
       same structure, attached to this document so the engine lays it out. A
       position measured against anything else is a position that can disagree
       with where the picture ends up, and every disagreement of that kind is
       invisible until a page is rendered and looked at. */
    var wrapper = wrapperFor(clone, css, box.width, pinned, identity);
    var stage = document.createElement("div");
    stage.setAttribute("style",
      boxStyle(box.width,
               "position:fixed;left:0;top:0;z-index:-1;pointer-events:none;"
               + "visibility:hidden;font-size:" + box.font + ";"));
    stage.appendChild(wrapper);
    document.body.appendChild(stage);
    /* MEASURED AGAINST THE COLUMN, NOT AGAINST THE BLOCK.
       The picture is drawn onto the page at the column's left edge, because that
       is where the SVG is drawn -- so a position measured from the block's own
       left edge is wrong by however far the block is inset. A student's turn is
       right-aligned in the column, which put every piece of handwriting a
       couple of hundred pixels to the left of the box left for it. Visible, and
       only visible, in a rendered page. */
    var rect = wrapper.getBoundingClientRect();
    var height = Math.max(1, Math.ceil(rect.height));
    /* The holes are measured while the clone is still laid out -- their
       positions are the whole of what "where does the handwriting go" means,
       and a detached node has none. */
    var placing = placePictures(pictures, rect);
    document.body.removeChild(stage);

    var svg = svgFor(serialize(wrapper), box.width, height);
    /* Everything downstream is in CSS pixels -- the slice source rows and the
       picture boxes alike -- and the enlargement to the page happens once, in
       the `drawImage` that puts it there. One coordinate system, or the
       arithmetic is a guess. */
    return Promise.all([loadImage(svg), placing]).then(function (both) {
      return { img: both[0], pictures: both[1], w: box.width, h: height };
    });
  }

  /* The pictures of one block, over the slice of it just drawn.

     `at` is the block row this slice starts at and `rows` how many of them it
     covers; everything below is the intersection of a picture's box with that
     band, mapped back into the picture's own pixels. Nothing here rounds: a
     rounded source row on a scaled picture is a half-pixel seam across an
     evening's handwriting, once per page break. */
  function paintPictures(ctx, shot, at, rows, k, left, top) {
    var band0 = at, band1 = at + rows;
    for (var i = 0; i < shot.pictures.length; i++) {
      var p = shot.pictures[i];
      if (p.bh < 0.5 || p.bw < 0.5) continue;
      var y0 = Math.max(p.by, band0);
      var y1 = Math.min(p.by + p.bh, band1);
      if (y1 - y0 < 0.5) continue;
      var f0 = (y0 - p.by) / p.bh;
      var f1 = (y1 - p.by) / p.bh;
      try {
        ctx.drawImage(p.img,
          p.sx, p.sy + f0 * p.sh, p.sw, (f1 - f0) * p.sh,
          left + p.bx * k, top + (y0 - band0) * k, p.bw * k, (y1 - y0) * k);
      } catch (e) {
        /* A picture that will not draw is a gap in one card. It is not a reason
           to lose the document, and it cannot be one: a `drawImage` that throws
           has already left the canvas alone. */
        if (global.console && console.warn) console.warn("shot: picture skipped", e);
      }
    }
  }

  /* The whole lesson, packed into pages of one size.

     A block that does not fit in what is left of a page starts a new one, and a
     block taller than a whole page is cut across pages rather than shrunk --
     shrinking is how a card with a long proof in it becomes unreadable, and the
     cut is invisible in a document nobody scrolls sideways. */
  function pages(progress) {
    var box = columnBox();
    var scale = Math.min(MAX_SCALE, Math.max(1, global.devicePixelRatio || 1));
    var pageW = Math.round((box.width + box.pad * 2) * scale);
    var pageH = Math.round(pageW * A4_RATIO);
    var margin = Math.round(box.pad * scale);
    var innerW = pageW - margin * 2;
    var innerH = pageH - margin * 2;
    var gap = Math.round(10 * scale);

    var list = blocks();
    if (!list.length) return Promise.reject(new Error("there is nothing on the board to photograph yet"));

    var out = [];
    var canvas = null, ctx = null, cursor = 0, drawn = false;

    function fresh() {
      canvas = document.createElement("canvas");
      canvas.width = pageW;
      canvas.height = pageH;
      ctx = canvas.getContext("2d");
      ctx.fillStyle = box.paper || "#16171a";
      ctx.fillRect(0, 0, pageW, pageH);
      cursor = margin;
      drawn = false;
    }

    /* A page nobody drew on is not a page. The pack starts a fresh sheet the
       moment one fills, so a lesson whose last card ends flush with the bottom
       would otherwise finish with a sheet of empty paper -- and an empty last
       page in a document somebody is emailing reads as a document that went
       wrong. */
    function close() {
      if (!canvas) return;
      if (drawn) out.push(canvas.toDataURL("image/jpeg", QUALITY).split(",")[1]);
      canvas = null;
      ctx = null;
    }

    fresh();

    return styles().then(function (css) {
      /* After `styles()`, never before: reading the sheets is what discovers
         which custom properties exist to be pinned. */
      var pinned = pinnedProps();
      var identity = identityOf();
      var i = 0;
      function step() {
        if (i >= list.length) {
          close();
          return out;
        }
        var node = list[i++];
        if (progress) progress(i, list.length);
        return shootBlock(node, css, box, pinned, identity).then(function (shot) {
          /* Scaled to the page's inner width, which is the same width it was
             laid out at times the scale -- so this is 1:1, not a resample. */
          var drawW = innerW;
          var srcY = 0;
          while (srcY < shot.h) {
            var room = innerH - (cursor - margin);
            if (room < Math.round(24 * scale)) { close(); fresh(); continue; }
            var takeDrawn = Math.min((shot.h - srcY) * (drawW / shot.w), room);
            /* Sub-pixel remainder. Without this the loop can take nothing,
               advance nothing, and never end -- on the device, silently. */
            if (takeDrawn < 0.5) break;
            var takeSrc = takeDrawn * (shot.w / drawW);
            ctx.drawImage(shot.img, 0, srcY, shot.w, takeSrc,
                          margin, cursor, drawW, takeDrawn);
            /* ...and then the pictures, over the holes left for them, clipped
               to the same slice of the block. A picture that straddles a page
               break is cut where the block is cut, from its own pixels, so half
               of an answer finishes the page and the other half opens the next
               one -- which is what a scroll does. */
            paintPictures(ctx, shot, srcY, takeSrc, drawW / shot.w,
                          margin, cursor);
            drawn = true;
            cursor += takeDrawn;
            srcY += takeSrc;
            if (srcY < shot.h - 0.5) { close(); fresh(); }
          }
          cursor += gap;
          if (cursor - margin >= innerH) { close(); fresh(); }
          return step();
        }, function (err) {
          /* One card the browser refused is a gap, not a lost evening. */
          if (global.console && console.warn) console.warn("shot: block skipped", err);
          return step();
        });
      }
      return Promise.resolve().then(step);
    });
  }

  /* Everything, sent. The server owns the name, the version, the repository
     copy and the git staging -- the same as the LaTeX export -- so all that
     goes up is the pixels and the shape of a page. */
  function send(progress) {
    return pages(progress).then(function (jpegs) {
      if (!jpegs.length) throw new Error("nothing came out of the lesson");
      var bytes = jpegs.reduce(function (n, s) { return n + s.length * 0.75; }, 0);
      if (bytes > MAX_BYTES) {
        throw new Error("this lesson is too long to photograph in one go ("
          + Math.round(bytes / 1048576) + "MB) — export the whole course instead");
      }
      return fetch(api.url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          /* A4 portrait in points, which is what the server writes into the
             MediaBox. The pixels are whatever this device reads at; the paper
             is what a professor prints on. */
          page: { w: 595.28, h: 841.89 },
          pages: jpegs,
        }),
      }).then(function (r) { return r.json(); });
    });
  }

  /* Named, because `blocks` asks it whether the live surface has anything on
     it -- and the board is what knows, so the board sets it. */
  var api = {
    send: send,
    pages: pages,
    blocks: blocks,
    styles: styles,
    /* For the suite, which cannot rasterise anything in jsdom but can check
       every rule the rasterising depends on -- and each of these was a real
       defect found by rendering a page and looking at it. */
    rootward: rootward,
    scope: scope,
    unitsToPx: unitsToPx,
    fitBox: fitBox,
    boxStyle: boxStyle,
    STILL: STILL,
    stripFurniture: stripFurniture,
    serialize: serialize,
    svgFor: svgFor,
    FURNITURE: FURNITURE,
    FLAT: FLAT,
    /* Set by the board, which is the side that knows: how much is written on
       the live surface. `blocks` skips a blank one. */
    liveInk: null,
    /* Where the pictures go: the board sets it to its session's route. */
    url: "/export/shot",
  };

  global.TutorShot = api;
}(typeof window !== "undefined" ? window : this));
