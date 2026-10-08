/* ==========================================================================
   sw.js -- service worker.

   Its only job is to make the app shell open instantly and survive a dropped
   connection: the pages, CSS, JS and icons in SHELL, and the fonts and KaTeX,
   are cached, so the board opens on the iPad before the Tailscale link is back.

   AN ALLOWLIST, NOT A DENYLIST. Only an exact SHELL path, a font or a KaTeX
   file is ever answered here; every other request goes to the network
   untouched. A cached lesson, document or figure is a stale one, worse than
   none, and a new live route must not need a line here to be left alone.

   VERSION IS WRITTEN BY THE SERVER. `routes/pages.py` serves this file with
   the literal below replaced by a hash of every SHELL file, so any edit to the
   shell installs a new worker and a new cache by itself.
   ========================================================================== */

var VERSION = "board-shell-dev";

var SHELL = [
  "/",
  "/board",
  "/slate",
  "/library",
  "/meeting",
  "/static/home.css",
  "/static/home.js",
  "/static/gauge.js",
  "/static/recentre.js",
  "/static/address.js",
  "/static/mission.js",
  "/static/who.js",
  "/static/typeface.css",
  "/static/typeface.js",
  "/static/board.css",
  "/static/board.js",
  "/static/library.css",
  "/static/library.js",
  "/static/meeting.js",
  "/static/inkkeep.js",
  "/static/shot.js",
  "/static/macros.js",
  "/static/slate.css",
  "/static/plane-core.js",
  "/static/slate-core.js",
  "/static/ink-clip.js",
  "/static/annotate.js",
  "/static/annbar.js",
  "/static/viewpin.js",
  "/static/readerzoom.js",
  "/static/ledger.js",
  "/static/ledger.css",
  "/static/calc-core.js",
  "/static/calc.js",
  "/static/slate.js",
  "/static/katex/katex.min.css",
  "/static/katex/katex.min.js",
  "/static/katex/auto-render.min.js",
  "/manifest.webmanifest",
  "/icon-180.png",
  "/icon-192.png",
  "/icon-512.png",
];

/* Cache-first, and cached on first use rather than listed: they never change
   under one name, and which font faces a lesson needs depends on its maths. */
var RUNTIME = /^\/static\/(katex|fonts)\//;

/* SHELL as a set of exact pathnames. A query string is not part of the match,
   because a home-screen icon can carry one. */
var IN_SHELL = {};
SHELL.forEach(function (u) { IN_SHELL[u] = true; });

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(VERSION).then(function (c) {
      /* One failure must not abort the whole install. */
      return Promise.all(SHELL.map(function (u) {
        return c.add(new Request(u, { cache: "reload" })).catch(function () {});
      }));
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== VERSION; })
                             .map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;

  var url;
  try { url = new URL(req.url); } catch (err) { return; }
  if (url.origin !== self.location.origin) return;

  if (RUNTIME.test(url.pathname)) {
    e.respondWith(
      caches.match(req).then(function (hit) {
        return hit || fetch(req).then(function (res) {
          if (res && res.status === 200) {
            var copy = res.clone();
            caches.open(VERSION).then(function (c) { c.put(req, copy); });
          }
          return res;
        });
      })
    );
    return;
  }

  /* Anything not in the shell is the network's, untouched. */
  if (!IN_SHELL[url.pathname]) return;

  /* Shell: network first so a redeployed board is picked up on the next open,
     cache as the fallback when the node is unreachable. */
  e.respondWith(
    fetch(req).then(function (res) {
      if (res && res.status === 200) {
        var copy = res.clone();
        caches.open(VERSION).then(function (c) { c.put(req, copy); });
      }
      return res;
    }).catch(function () {
      /* Unreachable. `ignoreSearch`, because a home-screen icon can carry a
         query string and an exact match would miss the very page it cached. */
      return caches.match(req, { ignoreSearch: true }).then(function (hit) {
        if (hit) return hit;
        /* A page: say so. This is the hole that produced a blank white screen
           when the machine serving the board had gone -- `caches.match("/")`
           returns undefined when nothing was cached under "/", and resolving
           `respondWith` with undefined is a network error, which paints
           nothing at all. The board already says when it cannot reach its
           server; it can only do that if something renders. */
        if (isPage(req)) return unreachablePage();
        /* Anything else: a real response rather than undefined, so the failure
           is a failure and not a blank document. */
        return new Response("", { status: 504, statusText: "board unreachable" });
      });
    })
  );
});

function isPage(req) {
  if (req.mode === "navigate") return true;
  var accept = req.headers && req.headers.get ? req.headers.get("accept") : "";
  return !!accept && accept.indexOf("text/html") !== -1;
}

/* Self-contained by necessity: nothing it references can be fetched, because
   the reason it is being shown is that nothing can be fetched. */
function unreachablePage() {
  var html = [
    '<!doctype html><html lang="en"><head><meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
    '<title>The board is not answering</title><style>',
    ':root{color-scheme:light dark}',
    'body{margin:0;min-height:100vh;display:flex;align-items:center;',
    'justify-content:center;background:#fbf9f4;',
    'font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;',
    'padding:2rem;box-sizing:border-box;color:#262420}',
    '@media (prefers-color-scheme:dark){body{background:#15171a;color:#e8e6e1}}',
    'main{max-width:26rem}h1{font-size:1.25rem;margin:0 0 .8rem}',
    'p{margin:0 0 .9rem;opacity:.85}',
    'button{font:inherit;padding:.55rem 1.1rem;border-radius:.45rem;',
    'border:1px solid currentColor;background:transparent;color:inherit}',
    '</style></head><body><main>',
    '<h1>The board is not answering</h1>',
    '<p>Nothing is serving this address at the moment. The machine that was ',
    'holding the board has usually either gone to sleep or had its allocation ',
    'end.</p>',
    '<p>Start a board on whichever machine you are working on, then try again ',
    'from here \u2014 the address does not change.</p>',
    '<button onclick="location.reload()">Try again</button>',
    '</main></body></html>',
  ].join("");
  return new Response(html, {
    status: 503,
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
  });
}
