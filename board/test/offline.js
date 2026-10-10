// A board that is not there must still paint something.
//
// The address the installed app has baked into it is served by whichever
// machine currently holds the board, and on a cluster that machine's allocation
// ends. Open the app after that and every request fails. The worker's fallback
// was `caches.match(req)` and then `caches.match("/")` -- and when neither is in
// the cache that resolves to `undefined`, which `respondWith` treats as a
// network error, which paints a blank white screen. Nothing on it says what
// happened, there is no way to retry from inside a standalone app, and the
// board's own "cannot reach the board" banner never runs because nothing runs.
//
// The worker is exercised directly: there is no browser here, and this is
// precisely the class of defect a stub DOM reports as fine.

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const SRC = fs.readFileSync(path.join(__dirname, '..', 'web', 'sw.js'), 'utf8');
const errors = [];
const ok = (m) => console.log('ok   ' + m);
const fail = (m) => { errors.push(m); console.log('FAIL ' + m); };

// A worker global with nothing cached and no network -- the state after the
// machine serving the board has gone.
function scope(cached) {
  const handlers = {};
  const store = cached || {};
  const ctx = {
    self: {
      addEventListener: (t, fn) => { handlers[t] = fn; },
      location: { origin: 'https://board.example.ts.net' },
      skipWaiting: () => Promise.resolve(),
      clients: { claim: () => Promise.resolve() },
    },
    caches: {
      open: () => Promise.resolve({ put() {}, add: () => Promise.resolve() }),
      keys: () => Promise.resolve([]),
      delete: () => Promise.resolve(true),
      match: (req) => {
        const url = typeof req === 'string' ? req : req.url;
        const key = new URL(url, 'https://board.example.ts.net').pathname;
        return Promise.resolve(store[key]);
      },
    },
    fetch: () => Promise.reject(new Error('offline')),
    Response, Request, URL,
    console,
  };
  ctx.self.addEventListener = (t, fn) => { handlers[t] = fn; };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return { handlers, ctx };
}

function ask(handlers, url, init) {
  const req = new Request(url, init || {});
  // jsdom-free: Request.mode is not settable, so carry it alongside.
  if (init && init.navigate) Object.defineProperty(req, 'mode', { value: 'navigate' });
  let out;
  handlers.fetch({ request: req, respondWith: (p) => { out = p; } });
  return out;
}

(async () => {
  const base = 'https://board.example.ts.net';

  // 1. Nothing cached, the board is gone, the app opens on a session's board.
  let { handlers } = scope({});
  let res = await ask(handlers, base + '/s/20261008-210000/board', { navigate: true });
  if (!res) {
    fail('the worker resolved with nothing at all — that is the blank screen');
  } else {
    res.status === 503
      ? ok('an unreachable board answers a page request')
      : fail('unexpected status ' + res.status);
    const body = await res.text();
    body.length > 0
      ? ok('and the page has something on it')
      : fail('the page is empty, which is the blank screen by another route');
    /not answering|cannot reach|unreachable/i.test(body)
      ? ok('and it says the board is not answering')
      : fail('the page does not say what is wrong');
    /location\.reload|Try again/i.test(body)
      ? ok('and offers a way to retry, which a standalone app has no chrome for')
      : fail('there is no way to retry from inside the app');
    /<style/i.test(body) && !/src=|href=/i.test(body)
      ? ok('and is self-contained, since nothing can be fetched by definition')
      : fail('the offline page depends on something it cannot load');
  }

  // 2. The shell IS cached: hand it over, because the board's own banner is
  //    better than a generic page -- it keeps the lesson readable behind it.
  //    A session's board is board.html whatever the id, cached once under its
  //    /static/ name, so any session URL falls back to the one copy.
  ({ handlers } = scope({ '/static/board.html': new Response('<html>the board</html>', {
    headers: { 'Content-Type': 'text/html' } }) }));
  res = await ask(handlers, base + '/s/20261008-210000/board', { navigate: true });
  const cachedBody = res ? await res.text() : '';
  /the board/.test(cachedBody)
    ? ok('a cached shell is preferred, so the board can say so itself')
    : fail('the cached shell was not used');
  for (const p of ['/s/X/board', '/s/X/', '/s/X', '/s/X/board/']) {
    ({ handlers } = scope({ '/static/board.html': new Response('<html>the board</html>') }));
    res = await ask(handlers, base + p, { navigate: true });
    /the board/.test(res ? await res.text() : '')
      ? ok('offline, ' + p + ' shows the cached board')
      : fail('offline, ' + p + ' did not show the cached board');
  }
  ({ handlers } = scope({ '/static/slate.html': new Response('<html>the slate</html>') }));
  res = await ask(handlers, base + '/s/X/slate', { navigate: true });
  /the slate/.test(res ? await res.text() : '')
    ? ok('and /s/X/slate shows the cached slate')
    : fail('/s/X/slate did not show the cached slate');
  ({ handlers } = scope({}));
  res = await ask(handlers, base + '/s/X/slate', { navigate: true });
  res && res.status === 503 && /not answering/.test(await res.text())
    ? ok('and with nothing cached it shows the unreachable page')
    : fail('an uncached /s/X/slate did not show the unreachable page');
  /"\/static\/board\.html"/.test(SRC) && /"\/static\/slate\.html"/.test(SRC)
    ? ok('both shell pages are precached under their /static/ names')
    : fail('the board or the slate page is not in SHELL');

  //    Reachable, the session's own page comes off the network.
  let s0;
  ({ handlers, ctx: s0 } = scope({ '/static/board.html': new Response('cached') }));
  s0.fetch = () => Promise.resolve(new Response('<html>live</html>'));
  res = await ask(handlers, base + '/s/X/board', { navigate: true });
  /live/.test(res ? await res.text() : '')
    ? ok('online, a session page is the network\'s')
    : fail('online, a session page came from the cache');

  //    Only pages: a session's data is the network's, untouched.
  for (const p of ['/s/X/board.json', '/s/X/events', '/s/X/slate/state',
                   '/s/X/result/r1', '/s/X/board']) {
    ({ handlers } = scope({ '/static/board.html': new Response('stale') }));
    res = ask(handlers, base + p);
    res === undefined
      ? ok(p + ' (not a navigation) is left to the network')
      : fail('the worker answered ' + p);
  }

  // 3. A home-screen icon can carry a query string.
  ({ handlers } = scope({ '/static/board.html': new Response('<html>the board</html>') }));
  res = await ask(handlers, base + '/s/X/board?from=homescreen', { navigate: true });
  const q = res ? await res.text() : '';
  /the board/.test(q)
    ? ok('and a query string does not miss the very page that was cached')
    : fail('a query string defeats the cache lookup');

  // 4. An asset with no cache must still be a response, not undefined.
  ({ handlers } = scope({}));
  res = await ask(handlers, base + '/static/board.js');
  if (!res) fail('a missing asset resolves with undefined, which is a network error');
  else res.status >= 500
    ? ok('a missing asset fails as a failure rather than as a blank document')
    : fail('unexpected status for a missing asset: ' + res.status);

  // 5. Live data is never intercepted at all, cached or not.
  ({ handlers } = scope({}));
  res = ask(handlers, base + '/board.json');
  res === undefined
    ? ok('live data is left to the network, as it must be')
    : fail('the worker intercepted a live request');

  // 6. A DOCUMENT'S PAGES ARE LIVE. `/doc/<id>/<page>.png` is deliberately the
  //    STABLE address of a page -- the server refuses to cache it for exactly
  //    that reason, so a card written last month survives the deck being
  //    rebuilt -- which meant it fell through to the shell rule, the one that
  //    caches any 200 it sees. A document revised on feedback is rebuilt at the
  //    same name, and the person who asked for the change was served the page
  //    they asked to have changed.
  ({ handlers } = scope({}));
  res = ask(handlers, base + '/doc/stage2-reference-walkthrough/24.png');
  res === undefined
    ? ok('a page of a document is left to the network, so a revised one is not stale')
    : fail('the worker cached a document page');

  // And the library with it: the list, and the pages of a document read from it.
  ({ handlers } = scope({}));
  res = ask(handlers, base + '/library.json');
  res === undefined
    ? ok('and so is the list of what a workspace has written')
    : fail('the worker cached the library list');
  ({ handlers } = scope({}));
  res = ask(handlers, base + '/library/view/serve-harness');
  res === undefined
    ? ok('and a document opened from it')
    : fail('the worker cached a library document');

  // 7. The library PAGE is shell, though, like the board and the slate: it has
  //    to open on an iPad that cannot reach the node yet.
  ({ handlers } = scope({ '/library': new Response('<html>the library</html>', {
    headers: { 'Content-Type': 'text/html' } }) }));
  res = await ask(handlers, base + '/library', { navigate: true });
  /the library/.test(res ? await res.text() : '')
    ? ok('while the library page itself is cached, like the board and the slate')
    : fail('the library page is not part of the shell');
  /"\/library"/.test(SRC)
    ? ok('and is listed in the shell, so it is there after one visit')
    : fail('/library is not in SHELL');

  // 8. AN ALLOWLIST: only an exact SHELL path, a font or KaTeX is ever matched
  //    against the cache. Anything else is the network's, even with a copy of
  //    it sitting in the cache and the network gone.
  const stale = new Response('stale');
  const tried = [];
  for (const p of ['/archive/x', '/atlas.json', '/map/inside/x', '/notes/what',
                   '/board/extra', '/static/mathjs/math.js', '/static/unlisted.js']) {
    const store = {};
    store[p] = stale;
    let s;
    ({ handlers, ctx: s } = scope(store));
    const match = s.caches.match;
    s.caches.match = (...a) => { tried.push(p); return match(...a); };
    res = ask(handlers, base + p, { navigate: true });
    res === undefined
      ? ok(p + ' is never answered by the worker')
      : fail('the worker answered ' + p);
  }
  tried.length === 0
    ? ok('and none of them was ever matched against the cache')
    : fail('cache-matched: ' + tried.join(', '));

  // While the fonts and KaTeX are answered from the cache first.
  ({ handlers } = scope({ '/static/katex/fonts/KaTeX_Main-Regular.woff2':
                          new Response('font') }));
  res = await ask(handlers, base + '/static/katex/fonts/KaTeX_Main-Regular.woff2');
  /font/.test(res ? await res.text() : '')
    ? ok('a KaTeX font is answered from the cache')
    : fail('a cached KaTeX font was not used');

  // VERSION is the server's to write; the source holds the placeholder it replaces.
  /var VERSION = "board-shell-dev";/.test(SRC)
    ? ok('VERSION is a placeholder the server fills with a hash of the shell')
    : fail('sw.js lost its VERSION placeholder');
  !/mathjs/.test(SRC)
    ? ok('and math.js is not precached; the calculator loads it when opened')
    : fail('math.js is still precached');

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\nan unreachable board still paints something');
  process.exit(errors.length ? 1 : 0);
})();
