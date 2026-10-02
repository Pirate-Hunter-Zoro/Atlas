// A DOCUMENT ON THE BOARD PINCHES ITSELF, AND THE PAGE NEVER DOES.
//
// Asked as: *"I can't zoom in with my fingers when opening the manuscript, and
// when I try to zoom out it does the whole Safari zoom out."*
//
// Two halves, both driven through the real pages in a real DOM:
//
//   * THE BOARD'S DOCUMENT PANEL (`#paper`, every paper, deck and write-up a
//     box or the contents drawer opens) zooms with `readerzoom.js`, the
//     library reader's own pinch. The board refuses the page pinch outright
//     (`html { touch-action: pan-x pan-y }`), so before this a pinch on a
//     document did nothing at all.
//   * THE BROWSER GETS NO SHARE OF A PINCH, on the panel or in the library
//     reader the map's documents region opens. The touch that makes two
//     fingers, any touch joining a live pinch and the gesture events are
//     cancelled, and the pinch's moves through a non-passive listener that
//     exists only while it lasts. One finger is never cancelled: it scrolls
//     natively.
//
// And the ink stays on its words through a pinch on the panel: `inkzoom.js`,
// the case the library and the deck already run, on `.paper-page`.

const fs = require('fs');
const path = require('path');

let JSDOM, VirtualConsole;
try {
  ({ JSDOM, VirtualConsole } = require('jsdom'));
} catch (e) {
  console.log('skip  jsdom is not installed — `npm install jsdom` to run this test');
  process.exit(0);
}

const WEB = path.join(__dirname, '..', 'web');
const errors = [];
const ok = (m) => console.log('ok   ' + m);
const fail = (m) => { errors.push(m); console.log('FAIL ' + m); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const HEALTH = { ok: true, id: 'research/TRD-EHR', dir: 'TRD-EHR' };
const VIEW = {
  ok: true, name: 'Paper 1', n: 2,
  pages: ['/paper/m-1.png', '/paper/m-2.png'],
};
const LIVE = {
  state: { course: 'TRD-EHR', session: 'lecture', mode: 'research' },
  cards: [], turns: [], messages: [], uploads: [], notes: {}, notes_sent: {},
  push: null, agent: null, history: 1,
};

const vc = new VirtualConsole();
vc.on('jsdomError', () => {});
const HTML = fs.readFileSync(path.join(WEB, 'board.html'), 'utf8');
const dom = new JSDOM(HTML, {
  runScripts: 'outside-only', pretendToBeVisual: true, virtualConsole: vc,
  url: 'https://board.test/board',
});
const { window } = dom;
const doc = window.document;

window.HTMLCanvasElement.prototype.getContext = () =>
  new Proxy({}, { get: () => function () {}, set: () => true });
window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
window.Element.prototype.scrollIntoView = function () {};
window.renderMathInElement = () => {};
window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
window.scrollTo = () => {};
window.scrollBy = () => {};
window.addEventListener('error', (e) => fail('uncaught: ' + e.message));

const json = (v) => Promise.resolve({ json: () => Promise.resolve(v), ok: true });
window.fetch = (u) => {
  const url = String(u);
  if (/slate\/state/.test(url)) return json({ pages: [] });
  if (url.indexOf('/health') === 0) return json(HEALTH);
  if (url.indexOf('/view/') === 0) return json(VIEW);
  return new Promise(() => {});
};
window.EventSource = function () {
  this.readyState = 1;
  this.close = function () {};
  this.addEventListener = function () {};
};

/* The page's own scripts, in the page's own order, so a reader the page does
   not load is a reader this test does not have either. */
const SCRIPTS = (HTML.match(/src="\/static\/[\w.-]+"/g) || [])
  .map((m) => /static\/([\w.-]+)/.exec(m)[1])
  .filter((f) => f !== 'board.js' && f !== 'typeface.js');
SCRIPTS.indexOf('readerzoom.js') >= 0
  && SCRIPTS.indexOf('readerzoom.js') > SCRIPTS.indexOf('annotate.js')
  ? ok('board.html loads the library reader\'s pinch, after the pen it asks about')
  : fail('board.html does not load readerzoom.js: ' + SCRIPTS.join(', '));
for (const f of SCRIPTS) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
try {
  let src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
  src = src.replace('})();',
    'window.__openDoc = openDoc;\nwindow.__closePaper = closePaper;\n})();');
  window.eval(src);
} catch (e) { fail('board.js: ' + e.message); }

const el = (id) => doc.getElementById(id);

function touch(target, name, pts, scale) {
  const ev = new window.Event(name, { bubbles: true, cancelable: true });
  Object.defineProperty(ev, 'touches', { value: pts.map(([x, y, type, r]) => ({
    clientX: x, clientY: y, touchType: type || 'direct', radiusX: r || 10 })) });
  if (scale !== undefined) Object.defineProperty(ev, 'scale', { value: scale });
  target.dispatchEvent(ev);
  return ev;
}
function gesture(target, name) {
  const ev = new window.Event(name, { bubbles: true, cancelable: true });
  target.dispatchEvent(ev);
  return ev;
}

(async function () {
  await sleep(20);
  if (window.__live) window.__live(LIVE);

  /* ---- the board's document panel ------------------------------------- */
  window.__openDoc('paper1-trd-prediction', 'Paper 1');
  await sleep(20);
  const pages = el('paper-pages');
  const chip = el('paper-zoom');
  const boxes = pages.querySelectorAll('.paper-page');
  boxes.length === 2 && !el('paper').hidden
    ? ok('a document opens on the board, a box per page')
    : fail('the document did not open: ' + boxes.length + ' pages');
  pages.classList.contains('zoomable') && chip
    ? ok('the panel pinches itself, with a chip that says the zoom')
    : fail('the document panel is not wired to readerzoom.js');

  const zoom = () => pages.style.getPropertyValue('--zoom');
  const htmlBefore = doc.documentElement.getAttribute('style') || '';
  const bodyBefore = doc.body.style.transform || '';

  const start = touch(pages, 'touchstart', [[100, 300], [200, 300]]);
  const move = touch(pages, 'touchmove', [[50, 300], [250, 300]], 2);
  start.defaultPrevented && move.defaultPrevented
    ? ok('the browser gets no share of a pinch: the touch and its moves are refused')
    : fail('Safari can still take the pinch: start ' + start.defaultPrevented
           + ', move ' + move.defaultPrevented);
  /scale\(2\)/.test(pages.style.transform)
    ? ok('a pinch on a document follows the fingers while they are down')
    : fail('nothing moves during a pinch: ' + JSON.stringify(pages.style.transform));
  touch(pages, 'touchend', [[250, 300]]);
  zoom() === '2' && !pages.style.transform
    ? ok('and the lift lays the pages out at twice the width')
    : fail('the pinch did not commit: --zoom=' + zoom());
  !chip.hidden && chip.textContent === '200%'
    ? ok('the bar says 200%, and only when it is not the fit')
    : fail('the zoom is not said: ' + chip.hidden + ' ' + chip.textContent);

  /* Zoom OUT: the pinch that went to Safari. */
  touch(pages, 'touchstart', [[50, 300], [250, 300]]);
  const shut = touch(pages, 'touchmove', [[125, 300], [175, 300]], 0.25);
  touch(pages, 'touchend', []);
  shut.defaultPrevented && zoom() === '0.5'
    ? ok('a pinch shut zooms the document out, to half, and not the page')
    : fail('a pinch shut: refused ' + shut.defaultPrevented + ', --zoom=' + zoom());

  (doc.documentElement.getAttribute('style') || '') === htmlBefore
    && (doc.body.style.transform || '') === bodyBefore
    && !pages.contains(doc.querySelector('.paper-bar'))
    ? ok('nothing outside the pages is scaled: the bar and the page stay put')
    : fail('a pinch on a document touched the page or its bar');

  ['gesturestart', 'gesturechange', 'gestureend'].every((n) => gesture(pages, n).defaultPrevented)
    ? ok('Safari\'s own pinch (iOS gesture events) is refused on a document')
    : fail('a gesture event on a document is not refused');

  /* A palm beside a finger is not a pinch: nothing zooms, and with no pinch
     in hand no move is refused (the board's `touch-action` and the refused
     gesture events keep Safari's pinch off the page). */
  touch(pages, 'touchstart', [[100, 300], [300, 300, 'direct', 80]]);
  const palm = touch(pages, 'touchmove', [[50, 300], [350, 300, 'direct', 80]], 1.4);
  touch(pages, 'touchend', []);
  !palm.defaultPrevented && zoom() === '0.5'
    ? ok('a palm beside a finger zooms nothing')
    : fail('a palm zoomed: refused ' + palm.defaultPrevented + ', --zoom=' + zoom());

  /* A touch joining a live pinch is the pinch's, and the non-passive move
     exists only while the pinch lasts. */
  const live = [];
  const add = pages.addEventListener, rem = pages.removeEventListener;
  pages.addEventListener = function (n, fn, o) {
    if (n === 'touchmove' && o && o.passive === false) live.push(fn);
    return add.call(this, n, fn, o);
  };
  pages.removeEventListener = function (n, fn, o) {
    if (n === 'touchmove') { const i = live.indexOf(fn); if (i >= 0) live.splice(i, 1); }
    return rem.call(this, n, fn, o);
  };
  const before = live.length;
  touch(pages, 'touchstart', [[100, 300], [200, 300]]);
  const during = live.length;
  const third = touch(pages, 'touchstart', [[100, 300], [200, 300], [300, 400]]);
  touch(pages, 'touchmove', [[100, 320], [200, 320], [300, 400]]);
  touch(pages, 'touchend', []);
  const after = live.length;
  const loose = touch(pages, 'touchmove', [[50, 300], [250, 300]], 2);
  pages.addEventListener = add; pages.removeEventListener = rem;
  before === 0 && during === 1 && after === 0
    ? ok('a non-passive touchmove exists only while a pinch lasts')
    : fail('the pinch\'s move listener: before ' + before + ', during ' + during
           + ', after ' + after);
  third.defaultPrevented && !loose.defaultPrevented
    ? ok('a touch joining a live pinch is refused, and a move after it is not')
    : fail('joining touch refused ' + third.defaultPrevented + ', loose move refused '
           + loose.defaultPrevented);

  const one = touch(pages, 'touchstart', [[100, 300]]);
  const oneMove = touch(pages, 'touchmove', [[100, 200]]);
  touch(pages, 'touchend', []);
  !one.defaultPrevented && !oneMove.defaultPrevented
    ? ok('one finger is never refused: it scrolls the document natively')
    : fail('one finger cannot scroll the document');

  const A = window.Annotate;
  A.setOn(true);
  const nib = touch(pages, 'touchstart', [[100, 300]]);
  touch(pages, 'touchend', []);
  const hand = touch(pages, 'touchstart', [[100, 300, 'direct', 80]]);
  touch(pages, 'touchend', []);
  const beside = touch(pages, 'touchstart', [[100, 300], [300, 300, 'stylus']]);
  touch(pages, 'touchend', []);
  !nib.defaultPrevented && hand.defaultPrevented && beside.defaultPrevented
    && zoom() === '0.5'
    ? ok('with the pen on, a finger scrolls and a palm or a hand beside the Pencil moves nothing')
    : fail('palm rejection on a document: finger ' + nib.defaultPrevented + ', palm '
           + hand.defaultPrevented + ', beside the Pencil ' + beside.defaultPrevented);

  /* The latch refuses a pan on the whole panel (`body.pen-writing
     .paper-pages.zoomable`), its bare strips too, so a finger landing on one
     of those is scrolled by hand like a finger on an ink layer. */
  {
    const sheet = doc.createElement('style');
    sheet.textContent = '#paper-pages { overflow-y: auto; }';
    doc.head.appendChild(sheet);
    Object.defineProperty(pages, 'scrollHeight', { configurable: true, value: 5000 });
    Object.defineProperty(pages, 'clientHeight', { configurable: true, value: 700 });
    pages.scrollTop = 100;
    doc.body.classList.add('pen-writing');
    const tp = (name, target, y) => {
      const ev = new window.Event(name, { bubbles: true, cancelable: true });
      const t = { identifier: 3, clientX: 400, clientY: y, touchType: 'direct', radiusX: 10 };
      Object.defineProperty(ev, 'touches', { value: name === 'touchend' ? [] : [t] });
      Object.defineProperty(ev, 'changedTouches', { value: [t] });
      target.dispatchEvent(ev);
    };
    tp('touchstart', pages, 400);
    tp('touchmove', pages, 380);
    tp('touchmove', pages, 340);
    tp('touchend', pages, 340);
    const moved = pages.scrollTop;
    doc.body.classList.remove('pen-writing');
    delete pages.scrollHeight; delete pages.clientHeight;
    pages.scrollTop = 0;
    sheet.remove();
    moved === 160
      ? ok('a finger on the panel between the pages, with the latch shut, still scrolls it')
      : fail('a finger on the bare panel with the latch shut does not scroll: scrollTop '
             + moved + ', not 160');
  }
  A.setOn(false);

  /* A pinch whose lift never came is not left standing: a cancel ends it,
     and so does a finger landing on its own. */
  {
    touch(pages, 'touchstart', [[100, 300], [200, 300]]);
    touch(pages, 'touchcancel', [[100, 300], [200, 300]]);
    const after = touch(pages, 'touchstart', [[100, 300]]);
    touch(pages, 'touchend', []);
    touch(pages, 'touchstart', [[100, 300], [200, 300]]);
    const lone = touch(pages, 'touchstart', [[100, 300]]);
    const loneMove = touch(pages, 'touchmove', [[100, 200]]);
    touch(pages, 'touchend', []);
    !after.defaultPrevented && !lone.defaultPrevented && !loneMove.defaultPrevented
      && !pages.classList.contains('pinching')
      ? ok('a cancelled or orphaned pinch ends, and the next finger scrolls')
      : fail('a pinch outlived its fingers: after cancel ' + after.defaultPrevented
             + ', lone ' + lone.defaultPrevented + ', move ' + loneMove.defaultPrevented);
  }

  chip.click();
  zoom() === '1' && chip.hidden
    ? ok('a tap on the chip puts the page width back')
    : fail('the zoom chip does not reset: --zoom=' + zoom());

  touch(pages, 'touchstart', [[100, 300], [200, 300]]);
  touch(pages, 'touchmove', [[50, 300], [250, 300]]);
  touch(pages, 'touchend', []);
  window.__openDoc('paper1-trd-prediction', 'Paper 1');
  await sleep(20);
  zoom() === '1' && chip.hidden
    ? ok('and every document opens at the page width, whatever the last was left at')
    : fail('a document opened at the last one\'s zoom: ' + zoom());

  const css = fs.readFileSync(path.join(WEB, 'board.css'), 'utf8');
  /width: calc\(min\(100%, 46rem\) \* var\(--zoom, 1\)\)/.test(css)
    && /body\.pen-writing \.paper-pages\.zoomable \{ touch-action: none; \}/.test(css)
    && !/touch-action:[^;]*pinch-zoom/.test(css)
    ? ok('board.css lays a page out at the zoom, and nothing gives the page its pinch back')
    : fail('board.css does not lay the panel\'s pages out at --zoom');

  /* ---- the ink stays on its words through a pinch ---------------------- */
  boxes.length && await require('./inkzoom')(window, {
    ok, fail, name: 'board document', scroller: 'paper-pages', page: '.paper-page',
    css: 'board.css', fit: 736, naturalHeight: 1604,
  });

  window.__closePaper();

  /* ---- the library reader, which the map's documents region opens ------- */
  {
    const lib = new JSDOM('<!doctype html><body><div id="reader">'
      + '<div id="reader-pages"></div><button id="reader-zoom" hidden></button></div>',
      { runScripts: 'outside-only', pretendToBeVisual: true });
    const w = lib.window;
    w.eval(fs.readFileSync(path.join(WEB, 'readerzoom.js'), 'utf8'));
    const sc = w.document.getElementById('reader-pages');
    w.ReaderZoom.make({ scroller: sc, chip: w.document.getElementById('reader-zoom'),
                        open: () => true });
    const t = (name, pts, scale) => {
      const ev = new w.Event(name, { bubbles: true, cancelable: true });
      Object.defineProperty(ev, 'touches', { value: pts.map(([x, y]) => (
        { clientX: x, clientY: y, touchType: 'direct', radiusX: 10 })) });
      if (scale !== undefined) Object.defineProperty(ev, 'scale', { value: scale });
      sc.dispatchEvent(ev);
      return ev;
    };
    const s0 = t('touchstart', [[100, 300], [200, 300]]);
    const m0 = t('touchmove', [[125, 300], [175, 300]], 0.5);
    t('touchend', []);
    s0.defaultPrevented && m0.defaultPrevented
      && sc.style.getPropertyValue('--zoom') === '0.5'
      ? ok('in the library reader too, a pinch shut is the document\'s and not Safari\'s')
      : fail('the library reader still hands a pinch to Safari: start '
             + s0.defaultPrevented + ', move ' + m0.defaultPrevented);
    const f0 = t('touchmove', [[100, 200]]);
    !f0.defaultPrevented
      ? ok('and one finger there still scrolls natively')
      : fail('one finger cannot scroll the library reader');
  }

  console.log(errors.length ? errors.length + ' failed' : 'all passed');
  process.exit(errors.length ? 1 : 0);
})();
