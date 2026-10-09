// A PAGE UNDER /s/<id>/ ASKS ONLY ABOUT ITS OWN SESSION.
//
// One server serves every session at `/s/<id>/`, so the board, the slate and
// the library each find their prefix in the address and send every session
// request under it: `api()` in board.js, the slate's URLs as options, the
// library's `libUrl`. Static assets stay absolute, and a URL the server or the
// tutor wrote (`![x](/result/r1)`, `/answers/...`, a document's pages) is put
// under the prefix where it is shown.
//
// jsdom loads each page at a session URL and records every request it makes.
// A source check backs it: no session route is fetched by a bare literal, so a
// request added later cannot quietly skip the prefix.

const fs = require('fs');
const path = require('path');

let JSDOM;
try {
  ({ JSDOM } = require('jsdom'));
} catch (e) {
  console.log('skip  jsdom is not installed — `npm install jsdom` to run this test');
  process.exit(0);
}

const WEB = path.join(__dirname, '..', 'web');
const errors = [];
const ok = (m) => console.log('ok   ' + m);
const fail = (m) => { errors.push(m); console.log('FAIL ' + m); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const json = (obj) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(obj) });

// Every <script src> a page loads, in order. KaTeX is stubbed; typeface.js is
// deferred and harmless either way.
function scriptsOf(html) {
  const out = [];
  const re = /<script src="\/static\/([^"]+)"/g;
  let m;
  while ((m = re.exec(html))) {
    if (!/^katex\//.test(m[1])) out.push(m[1]);
  }
  return out;
}

function page(file, url, answer) {
  const html = fs.readFileSync(path.join(WEB, file), 'utf8');
  const dom = new JSDOM(html, { runScripts: 'outside-only', pretendToBeVisual: true, url });
  const { window } = dom;
  const asked = [];
  window.HTMLCanvasElement.prototype.getContext = () =>
    new Proxy({}, { get: () => () => {}, set: () => true });
  window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
  Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => 900 });
  Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 500 });
  window.HTMLElement.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: 900, height: 120, right: 900, bottom: 120, x: 0, y: 0 };
  };
  window.Element.prototype.scrollIntoView = function () {};
  window.Element.prototype.setPointerCapture = function () {};
  window.Element.prototype.releasePointerCapture = function () {};
  window.renderMathInElement = () => {};
  window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  window.scrollTo = function () {};
  window.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {},
                                addEventListener() {}, removeEventListener() {} });
  window.caches = { keys: () => Promise.resolve([]) };
  window.fetch = (u, init) => {
    const url = String(u);
    asked.push({ url, init: init || {} });
    const got = answer(url, init || {});
    return got || new Promise(() => {});
  };
  window.EventSource = function (u) {
    asked.push({ url: String(u), init: { stream: true } });
    window.__es = this;
    this.readyState = 1;
    this.close = function () {};
    this.addEventListener = function () {};
  };
  window.addEventListener('error', (e) => fail(file + ' uncaught: ' + e.message));
  for (const f of scriptsOf(html)) {
    try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
    catch (e) { fail(file + ' ' + f + ': ' + e.message); }
  }
  return { window, doc: window.document, asked };
}

// Under /s/A/ or a static asset; nothing else.
function strays(asked, prefix) {
  return asked.map((r) => r.url).filter((u) => {
    const p = new URL(u, 'https://board.test').pathname;
    return !(p.indexOf(prefix) === 0 || p.indexOf('/static/') === 0);
  });
}

(async () => {
  // ------------------------------------------------------------- the board
  const board = page('board.html', 'https://board.test/s/A/board', (url) => {
    if (/\/slate\/state$/.test(url)) return json({ pages: [] });
    if (/\/health/.test(url)) return json({ ok: true });
    return null;
  });
  const w = board.window;
  const bdoc = board.doc;
  const es = w.__es;
  board.asked.some((r) => r.url === '/s/A/events')
    ? ok('the stream is /s/A/events')
    : fail('the stream is ' + JSON.stringify(board.asked.filter((r) => r.init.stream)));

  const now = Date.now() / 1000;
  const BODY = 'Here is the figure.\n\n![x](/result/r1)\n\n'
    + 'The [deck](/doc/d1/1.png), the [paper](https://example.org/p), '
    + 'a [page](/slate/page-0001.png) and ![icon](/static/icon-192.png).';
  if (es && es.onmessage) {
    es.onmessage({ data: JSON.stringify({
      state: { course: 'Galois-Theory', session: 'lecture', chapter: 'ch01',
               opened: '2026-10-08 21:00:00' },
      cards: [{ id: '0001', kind: 'lesson', title: 'A figure', body: BODY,
                mtime: now - 600 }],
      turns: [], agent: { agent: 'claude', state: 'listening', turns: 1 },
      waiting: null, history: 0,
    }) });
  } else {
    fail('board.js never opened a stream');
  }
  await sleep(150);

  const card = bdoc.querySelector('[data-card="0001"]');
  const img = card && card.querySelector('img.card-img[alt="x"]');
  img && img.getAttribute('src') === '/s/A/result/r1'
    ? ok('![x](/result/r1) renders /s/A/result/r1')
    : fail('the result image is ' + (img ? img.getAttribute('src') : 'missing'));
  const link = (text) => Array.prototype.find.call(card ? card.querySelectorAll('a') : [],
                                                   (a) => a.textContent === text);
  (link('deck') || {}).getAttribute && link('deck').getAttribute('href') === '/s/A/doc/d1/1.png'
    ? ok('and a link to /doc/ goes under the session')
    : fail('the /doc/ link is ' + (link('deck') && link('deck').getAttribute('href')));
  link('page') && link('page').getAttribute('href') === '/s/A/slate/page-0001.png'
    ? ok('and so does one to /slate/')
    : fail('the /slate/ link is ' + (link('page') && link('page').getAttribute('href')));
  link('paper') && link('paper').getAttribute('href') === 'https://example.org/p'
    ? ok('while the web stays the web')
    : fail('an outside link was rewritten');
  const icon = card && card.querySelector('img.card-img[alt="icon"]');
  icon && icon.getAttribute('src') === '/static/icon-192.png'
    ? ok('and a static asset stays absolute')
    : fail('a static image is ' + (icon && icon.getAttribute('src')));

  const slateBtn = bdoc.getElementById('btn-slate');
  slateBtn && slateBtn.getAttribute('href') === '/s/A/slate'
    ? ok('the slate button opens /s/A/slate')
    : fail('the slate button opens ' + (slateBtn && slateBtn.getAttribute('href')));
  bdoc.getElementById('btn-home').getAttribute('href') === '/'
    ? ok('and home is still the front door')
    : fail('home was prefixed');

  board.asked.length && board.asked.some((r) => r.url === '/s/A/slate/state')
    ? ok('the slate under the lesson reads /s/A/slate/state')
    : fail('the slate read ' + board.asked.map((r) => r.url).join(' '));
  board.asked.some((r) => /^\/s\/A\/health/.test(r.url))
    ? ok('the board asks /s/A/health about itself')
    : fail('the board did not ask its own health');

  const stray = strays(board.asked, '/s/A/');
  stray.length === 0
    ? ok('every request the board made is under /s/A/ or /static/ ('
         + board.asked.length + ' requests)')
    : fail('requests outside the session: ' + stray.join(' '));

  w.TutorShot && w.TutorShot.url === '/s/A/export/shot'
    ? ok('the screenshot export posts to /s/A/export/shot')
    : fail('the screenshot export posts to ' + (w.TutorShot && w.TutorShot.url));

  // Per-session memory: what the board writes to this device names the session.
  const keys = [];
  for (let i = 0; i < w.localStorage.length; i++) keys.push(w.localStorage.key(i));
  !keys.some((k) => /Galois-Theory/.test(k))
    ? ok('nothing this device remembers is keyed by the course (' + keys.join(', ') + ')')
    : fail('a course-keyed entry: ' + keys.join(', '));

  // ------------------------------------------------------------- the slate
  const slate = page('slate.html', 'https://board.test/s/A/slate', (url) => {
    if (/\/slate\/state$/.test(url)) return json({ pages: [] });
    if (/\/board\.json$/.test(url)) return json({ cards: [] });
    return null;
  });
  await sleep(50);
  const surls = slate.asked.map((r) => r.url);
  surls.indexOf('/s/A/slate/state') !== -1 && surls.indexOf('/s/A/board.json') !== -1
    ? ok('the full-screen slate reads /s/A/slate/state and /s/A/board.json')
    : fail('the slate asked ' + surls.join(' '));
  strays(slate.asked, '/s/A/').length === 0
    ? ok('and nothing outside the session')
    : fail('slate requests outside the session: ' + strays(slate.asked, '/s/A/').join(' '));
  slate.doc.getElementById('back').getAttribute('href') === '/s/A/board'
    ? ok('and its way back is /s/A/board')
    : fail('the slate goes back to ' + slate.doc.getElementById('back').getAttribute('href'));

  // ----------------------------------------------------------- the library
  const LIB = { ok: true, subject: 'courses/Galois-Theory', workspace: 'Galois-Theory',
                documents: [{ id: 'hw1', dir: 'homework', stem: 'hw1', title: 'Homework 1',
                              kind: 'paper', formats: ['pdf', 'tex'], pages: 1, pdf: true,
                              iso: '2026-10-01', notes: [] }] };
  const libAnswer = (url) => {
    if (/library\.json/.test(url)) return json(LIB);
    if (/library\/stamp/.test(url)) return json({ ok: true, documents: {} });
    if (/library\/results\.json/.test(url)) return json({ ok: true, results: [] });
    if (/library\/view\//.test(url)) return json({ ok: true, pages: ['/doc/hw1/1.png'], ink: {} });
    if (/library\/ledger\//.test(url)) return json({ ok: false });
    return null;
  };
  const lib = page('library.html', 'https://board.test/s/A/library', libAnswer);
  await sleep(80);
  const name = lib.doc.querySelector('.lib-name');
  if (name) name.click();
  await sleep(80);
  const lurls = lib.asked.map((r) => r.url);
  lurls.indexOf('/s/A/library.json') !== -1 && lurls.indexOf('/s/A/library/view/hw1') !== -1
    ? ok('the library under a session reads /s/A/library.json and /s/A/library/view/<id>')
    : fail('the library asked ' + lurls.join(' '));
  strays(lib.asked, '/s/A/').length === 0
    ? ok('and nothing outside the session')
    : fail('library requests outside the session: ' + strays(lib.asked, '/s/A/').join(' '));
  const pg = lib.doc.querySelector('.lib-page img');
  pg && pg.getAttribute('src') === '/s/A/doc/hw1/1.png'
    ? ok('and a document page it shows is /s/A/doc/hw1/1.png')
    : fail('the page image is ' + (pg && pg.getAttribute('src')));
  lib.doc.getElementById('lib-back').getAttribute('href') === '/s/A/board'
    ? ok('and its way back is the session\'s board')
    : fail('the library goes back to ' + lib.doc.getElementById('lib-back').getAttribute('href'));

  const open = page('library.html',
                    'https://board.test/library?subject=courses%2FGalois-Theory', libAnswer);
  await sleep(80);
  const ourls = open.asked.map((r) => r.url);
  ourls.indexOf('/library.json?subject=courses%2FGalois-Theory') !== -1
    && ourls.every((u) => /[?&]subject=courses%2FGalois-Theory/.test(u))
    ? ok('outside a session the library names its subject on every request')
    : fail('the unprefixed library asked ' + ourls.join(' '));
  open.doc.getElementById('lib-back').getAttribute('href') === '/'
    ? ok('and goes back to everything, since there is no board to go back to')
    : fail('the unprefixed library goes back to '
           + open.doc.getElementById('lib-back').getAttribute('href'));

  // ------------------------------------------------- and in the source
  // Every session route is fetched through the page's prefix. A bare literal
  // is allowed only for the cross-subject routes the server answers unprefixed.
  const CROSS = /^\/(colibri|elsewhere|atlas\.json|mission|sw\.js)\b/;
  for (const f of ['board.js', 'slate.js', 'slate-core.js', 'inkkeep.js', 'shot.js',
                   'library.js', 'ledger.js']) {
    const src = fs.readFileSync(path.join(WEB, f), 'utf8');
    const bare = [];
    const re = /(?:[^.\w]|^)(?:fetch|EventSource)\(\s*"(\/[^"]*)"/g;
    let m;
    while ((m = re.exec(src))) if (!CROSS.test(m[1])) bare.push(m[1]);
    bare.length === 0
      ? ok(f + ' fetches no session route by a bare path')
      : fail(f + ' fetches by a bare path: ' + bare.join(' '));
  }

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\na page under /s/<id>/ asks only about its own session');
  process.exit(errors.length ? 1 : 0);
})();
