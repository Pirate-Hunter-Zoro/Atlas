/* ==========================================================================
   sw.js -- service worker.

   Its only job is to make the app shell open instantly and survive a dropped
   connection: HTML, CSS, JS, icons, and the KaTeX fonts are cached, so the
   board opens on the iPad even before the Tailscale link has come back up.

   It deliberately does NOT touch anything live. The SSE stream, the board
   payload, uploads, slate saves, and compiled figures all go straight to the
   network -- a cached lesson is a stale lesson, which is worse than none.
   ========================================================================== */

var VERSION = "board-shell-v154";

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
  "/static/typeface.css",
  "/static/typeface.js",
  "/static/board.css",
  "/static/board.js",
  "/static/library.css",
  "/static/library.js",
  "/static/meeting.js",
  "/static/shot.js",
  "/static/macros.js",
  "/static/slate.css",
  "/static/plane-core.js",
  "/static/slate-core.js",
  "/static/ink-clip.js",
  "/static/annotate.js",
  "/static/slate.js",
  "/static/katex/katex.min.css",
  "/static/katex/katex.min.js",
  "/static/katex/auto-render.min.js",
  "/manifest.webmanifest",
  "/icon-180.png",
  "/icon-192.png",
  "/icon-512.png",
];

/* KaTeX pulls its fonts lazily; they are cached on first use rather than
   listed here, because which faces a lesson needs depends on the mathematics. */
var RUNTIME = /\/static\/(katex\/fonts|fonts)\//;

/* Never intercepted. Live data, or a stream that must not be buffered. */
/* `health` and `hosts.json` are here for the same reason as the rest: the hub
   polls /health to find out whether a switch has actually landed, and an
   answer out of a cache would say the address is still where it was. */
/* AND THE DOCUMENTS, which had been falling through to the shell rule -- the
   one that caches any 200 it sees. Two things wrong with that and both of them
   bite the person holding the iPad. A lesson transcript is megabytes, and the
   shell cache is inside the origin's storage allowance alongside the app itself,
   so a few exports could push the app out of its own cache. And a document is
   rebuilt at the SAME URL every time: `/download/homework` is whatever the last
   compile produced, so a cached one served while the link is briefly down is
   last week's write-up wearing this week's name. That is the same mistake as a
   cached lesson, made one layer down, and this file's own rule against it is
   the reason it is here. `/view/` renders and `/paper/` is content-addressed by
   the PDF's modification time -- neither wants the shell's cache-then-serve. */
/* AND `/doc/`, WHICH IS THE SAME MISTAKE IN THE THIRD PLACE, and the one every
   change above makes bite. `/doc/<id>/<page>.png` is deliberately the STABLE
   address of a page -- `routes/taking.py` refuses to cache it server-side for
   exactly that reason, because a card written last month has to survive the deck
   being rebuilt -- so it fell through to the shell rule, which caches any 200 it
   sees. A document revised on feedback is rebuilt at the same name, and the
   person who asked for the change was then served the page they asked to have
   changed. `/library/` goes with it: the list, and the pages of a document read
   from it, are live for the same reason. */
/* AND `/result/`, which is the same mistake waiting in a third place. A figure
   out of a workspace is REBUILT AT THE SAME NAME by the next job -- the id is
   derived from the path, so `propensity_by_arm.png` is a new picture under an
   old address every time the pipeline runs. A cached one is last week's result
   wearing this week's label, which is the one failure a figure on a board must
   not have: it is being looked at to decide something. */
/* AND THE DECK'S OWN DATA, which is the same mistake again. There is one
   deck at one path and it is REPLACED rather than versioned, so
   `/meeting/view`, `/meeting/deck.json` and `/meeting/pdf` are all stable
   addresses whose contents change under them -- a cached one is last week's
   meeting wearing this week's name, in front of this week's mentors. The
   page `/meeting` itself is shell and is cached; its contents are not. */
/* AND A MISSION'S PROGRESS, for the same reason. `/mission` and `/missions` are
   stable addresses whose contents change under them every few minutes -- what a
   job has done since you last looked is the whole point of asking -- and a
   cached one says the mission has been idle for an hour when it has not. */
var LIVE = /^\/(events|board\.json|courses\.json|hosts\.json|health|switch|chose|start|say|aim|upload|mission|slate\/(save|state)|figure\/|result\/|uploads\/|slate\/page-|download\/|view\/|paper\/|doc\/|library\.json|library\/|shelf\.json|meeting\/)/;

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
  if (LIVE.test(url.pathname)) return;

  if (RUNTIME.test(url.pathname)) {
    e.respondWith(
      caches.match(req).then(function (hit) {
        return hit || fetch(req).then(function (res) {
          var copy = res.clone();
          caches.open(VERSION).then(function (c) { c.put(req, copy); });
          return res;
        });
      })
    );
    return;
  }

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
