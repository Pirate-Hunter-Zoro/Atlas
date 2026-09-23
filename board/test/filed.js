// A FILED SITTING TAKES ITS SLATE WITH IT.
//
// Reported from the iPad: "The most recent new writing board showed up with
// writing from an unrelated problem; not blank with an option to carry over
// from the last board, which is what should always happen."
//
// `board archive` renames every `page-NN.json` out of `live/slate/` and into
// the archive. That is correct and it is only half of it, because the pages are
// ALSO in the browser: the surface holds them in memory and its save is
// debounced, so the next one writes them straight back under their old numbers.
//
// Measured in Probability on 23 September 2026. The sitting was filed at
// 09:29:06 -- `live/archive/20260923-092906-hw03/slate/` has fourteen pages in
// it -- and `live/slate/page-02.json`, 479 strokes of the previous problem, was
// back on disk at 09:52. A new board then opened onto a sheet that already had
// somebody else's working on it, which is the one thing a new board must not
// do, and the carry-over button stayed hidden because that button is only
// offered on a board that is BLANK.
//
// The epoch is `history`, the number of archived sittings, which is already on
// every payload and goes up by one exactly when the archive runs. What must go
// with it is both halves: the pages, and the board-to-page map, whose every
// number now names a sheet that has moved.
//
// jsdom, because this is the surface and the board disagreeing about which
// lesson they are in.

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
const check = (m, c) => (c ? ok(m) : fail(m));

const stroke = (n) => ({ c: '#eee', w: 3, pts: [[10 * n, 10], [10 * n, 90]] });
// The previous sitting, on disk when the page loads: two sheets with real
// working on them.
const saved = [2, 3].map((n) => ({
  page: n, w: 1130, h: 1514,
  strokes: Array.from({ length: 5 * n }, (_, i) => stroke(n + i / 100)),
}));

const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
  runScripts: 'outside-only', pretendToBeVisual: true, url: 'https://board.test/board',
});
const { window } = dom;
const doc = window.document;

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

const posted = [];
window.fetch = (u, init) => {
  const url = String(u);
  if (/slate\/state/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve({ pages: saved }) });
  }
  if (/slate\/save/.test(url)) {
    let body = {};
    try { body = JSON.parse((init && init.body) || '{}'); } catch (e) {}
    posted.push(body);
    return Promise.resolve({ json: () => Promise.resolve({ ok: true, page: body.page }) });
  }
  return new Promise(() => {});
};
window.renderMathInElement = () => {};
window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
window.scrollTo = function () {};
window.addEventListener('error', (e) => fail('uncaught: ' + e.message));
window.EventSource = function () {
  window.__es = this;
  this.readyState = 1;
  this.close = function () {};
  this.addEventListener = function () {};
};

for (const f of ['typeface.js', 'macros.js', 'gauge.js', 'plane-core.js',
                 'slate-core.js', 'annotate.js', 'who.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
const realCreate = window.Slate && window.Slate.create;
if (realCreate) {
  window.Slate.create = function (opts) {
    const api = realCreate(opts);
    window.__slate = api;
    return api;
  };
}
try {
  /* `showSession` reaches `render` directly rather than through the stream, and
     the regression below is exactly that path, so it has to be callable. */
  let src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
  src = src.replace('})();', 'window.__render = render;\n})();');
  window.eval(src);
} catch (e) { fail('board.js: ' + e.message); }

const es = window.__es;
if (!es) { console.log('FAIL board.js never opened a stream'); process.exit(1); }

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const t0 = 1788400000;
const KEY = 'board.pages.n:Probability:-';
const mapping = () => {
  try { return JSON.parse(window.localStorage.getItem(KEY) || '{}'); }
  catch (e) { return {}; }
};
const frame = (cards, history) => {
  const f = { state: { course: 'Probability', session: 'homework' },
              cards: cards, turns: [] };
  if (history !== undefined) f.history = history;
  return JSON.stringify(f);
};
// Exactly what `showSession` hands `render` when a past sitting is opened to be
// read: built by hand, `archived`, and carrying NO `history` at all.
const archivedFrame = () => JSON.stringify({
  state: { course: 'Probability', chapter: 'hw03' },
  cards: [q('0001', 'a filed question', 1)], turns: [],
  notes: {}, uploads: [], messages: [], archived: true,
});
const q = (id, title, n) =>
  ({ id: id, kind: 'question', title: title, body: 'the ' + title + ' body',
     mtime: t0 + n * 100 });

(async () => {

// ---- the sitting that is about to be filed ---------------------------------
es.onmessage({ data: frame([q('0001', 'Problem 12', 1)], 3) });
await sleep(100);
const slate = window.__slate;
if (!slate) { console.log('FAIL no slate instance was captured'); process.exit(1); }

check('the previous sitting is on the surface, with working on it',
      slate.pages() >= 2 && slate.hasPage(2) && slate.hasPage(3));
check('and the board recorded which sheet its question is on',
      Object.keys(mapping()).length > 0);

// A page count of three archived lessons is not three lessons being filed now.
check('ARRIVING at a course with a history is not the same as a lesson being '
      + 'filed while you watch -- the first payload resets nothing',
      slate.hasPage(2) && slate.hasPage(3));

// ---- `board archive` runs --------------------------------------------------
// On disk every page has been renamed into the archive, and `history` is one
// higher. This is the whole of the signal.
es.onmessage({ data: frame([q('0001', 'Problem 61', 1)], 4) });
await sleep(120);

check('THE FILED SITTING\'S PAGES ARE GONE FROM THE SURFACE. Left in memory, a '
      + 'debounced save writes them back under their old numbers and a new '
      + 'board opens onto somebody else\'s working',
      !slate.hasPage(2) && !slate.hasPage(3));
check('and what is left is exactly one sheet', slate.pages() === 1);
check('which is blank', slate.strokes() === 0);
check('with the numbering started again, because the sheets it would otherwise '
      + 'count are in the archive', slate.at() === 1);
// The map is rebuilt immediately for the board that is now open -- that is the
// point of it -- so what matters is not that it is empty but that NOTHING IN IT
// STILL NAMES A FILED SHEET.
const pointsAt = Object.keys(mapping()).map((k) => mapping()[k].p);
check('AND NO BOARD IS LEFT POINTING AT A FILED SHEET -- every number the old '
      + 'map held names a page that has moved to the archive',
      !pointsAt.some((n) => n === 2 || n === 3));
check('while the board that is open now has a sheet of its own, which is the '
      + 'map doing its job rather than being wiped',
      pointsAt.length === 1 && pointsAt[0] === 1);

// ---- and nothing of the old lesson is written back -------------------------
posted.length = 0;
await sleep(150);
check('no page of the filed sitting is saved back into the live slate',
      !posted.some((p) => p.page === 2 || p.page === 3));

// ---- READING A PAST SITTING IS NOT FILING THE CURRENT ONE ------------------
//
// This is the regression that made the board unusable for a few minutes, and it
// is the whole reason the guard is on PRESENCE rather than on value. `render` is
// called with frames built by hand -- `showSession` passes an archived sitting
// with no `history` key at all -- and reading a missing field as zero turns the
// next real frame into an archive that never happened.
es.onmessage({ data: frame([q('0002', 'Problem 61', 2)], 4) });
await sleep(100);
// Put real working on the sheet in hand, so a wipe is visible rather than
// theoretical.
slate.load({ w: 1130, h: 1514, strokes: [stroke(7), stroke(8), stroke(9)] });
await sleep(40);
const before = slate.at();
check('there is working on the board before the archive is opened',
      slate.strokes() === 3);

window.__render(JSON.parse(archivedFrame()));
await sleep(80);
check('opening a FILED sitting to read it leaves the live slate alone -- that '
      + 'frame is about another lesson and carries no `history` at all',
      slate.strokes() === 3 && slate.at() === before);

// And coming back. This is the pair that broke it: the archived frame drove the
// count to zero and the live one then read as a rise.
es.onmessage({ data: frame([q('0002', 'Problem 61', 2)], 4) });
await sleep(100);
check('AND COMING BACK TO THE LESSON DOES NOT WIPE IT EITHER',
      slate.strokes() === 3 && slate.at() === before);

// A frame that simply omits the field says nothing, rather than saying none.
es.onmessage({ data: frame([q('0002', 'Problem 61', 2)], undefined) });
await sleep(60);
es.onmessage({ data: frame([q('0002', 'Problem 61', 2)], 4) });
await sleep(80);
check('a frame that omits `history` says nothing about it, so the next one that '
      + 'carries it is not a rise', slate.strokes() === 3);

// ---- the source, for the two halves that are easy to drop ------------------
const core = fs.readFileSync(path.join(WEB, 'slate-core.js'), 'utf8');
const bjs = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
check('the reset does not SAVE what it drops -- the archive holds the copy that '
      + 'matters, and writing it back is the defect itself',
      !/api\.reset[\s\S]{0,900}?markDirty\(\)/.test(core));
check('it is driven off a rise in `history` rather than off an empty slate, '
      + 'which a failed read also looks like',
      /data\.history > pastCount/.test(bjs));
check('and the field is required to be PRESENT and numeric before it counts, '
      + 'because `|| 0` on a hand-built frame is what broke the board',
      /typeof data\.history === "number" && !data\.archived/.test(bjs));
check('and `pastCount` starts null, so the first payload is not a rise',
      /var pastCount = null;/.test(bjs));

console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                          : '\na filed sitting takes its slate with it');
process.exit(errors.length ? 1 : 0);
})();
