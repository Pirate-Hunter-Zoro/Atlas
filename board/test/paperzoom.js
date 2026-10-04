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
//   * SAFARI GETS NO PINCH WHILE A DOCUMENT IS OPEN, on the panel or in the
//     library reader the map's documents region opens. Two fingertips on the
//     pages or the bar are the reader's from their touchstart -- fingers
//     landing one at a time, a second finger on a bar button, whose tap is
//     clicked back -- and a pinch is built from them unless the second lands
//     mid-scroll. A palm beside a finger, or fingers on an overlay, keep
//     their touchstart and have their moves refused once the gap changes, so
//     a finger beside a resting palm and two fingers in a textarea scroll.
//     A non-passive move is armed at a gesture's first touch and dropped once
//     a lone finger passes 10 px, so one finger scrolls natively.
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

/* `pts` are [x, y, type, radius, id]; a touch's id is its place unless one is
   given. `o.ts` is the event's timeStamp, `o.changed` the ids it is for. */
function touch(target, name, pts, scale, o) {
  o = o || {};
  const ev = new window.Event(name, { bubbles: true, cancelable: true });
  const list = pts.map(([x, y, type, r, id], i) => ({
    identifier: id === undefined ? i : id,
    clientX: x, clientY: y, touchType: type || 'direct', radiusX: r || 10 }));
  Object.defineProperty(ev, 'touches', { value: list });
  if (o.changed) {
    Object.defineProperty(ev, 'changedTouches', { value: o.changed.map((id) => (
      list.find((t) => t.identifier === id) || { identifier: id, clientX: 0, clientY: 0 })) });
  }
  if (o.ts !== undefined) Object.defineProperty(ev, 'timeStamp', { value: o.ts });
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

  /* A SHUT LANDS ONE FINGER AT A TIME. Fingers that start far apart touch
     down tens of ms apart, and iOS fixes the native gesture from the first.
     The first finger is a scroll until a second lands, so it is not refused;
     but the move that will refuse the second is already armed when it does. */
  {
    chip.click();
    touch(pages, 'touchstart', [[100, 300], [200, 300]]);
    touch(pages, 'touchmove', [[50, 300], [250, 300]]);
    touch(pages, 'touchend', []);
    const s1 = touch(pages, 'touchstart', [[100, 300]]);
    const m1 = touch(pages, 'touchmove', [[103, 300]]);
    const s2 = touch(pages, 'touchstart', [[103, 300], [503, 300]]);
    const m2 = touch(pages, 'touchmove', [[203, 300], [403, 300]]);
    touch(pages, 'touchend', []);
    !s1.defaultPrevented && !m1.defaultPrevented && s2.defaultPrevented
      && m2.defaultPrevented && zoom() === '1'
      ? ok('a shut whose fingers land one at a time is the document\'s: 200% to 100%')
      : fail('a staggered shut: first ' + s1.defaultPrevented + '/' + m1.defaultPrevented
             + ', second ' + s2.defaultPrevented + '/' + m2.defaultPrevented
             + ', --zoom=' + zoom());
  }

  /* A WIDE SHUT PUTS A FINGER ON THE BAR. Its touches go to the bar, not the
     pages, and they are still the reader's. */
  {
    const bar = doc.querySelector('.paper-bar');
    touch(pages, 'touchstart', [[100, 300]]);
    const s2 = touch(bar, 'touchstart', [[100, 300], [400, 40]]);
    const m2 = touch(bar, 'touchmove', [[175, 235], [325, 105]]);
    touch(bar, 'touchend', []);
    s2.defaultPrevented && m2.defaultPrevented && Number(zoom()) < 0.6
      ? ok('a second finger landing on the bar is refused to Safari, and the shut zooms out')
      : fail('a finger on the bar: start ' + s2.defaultPrevented + ', move '
             + m2.defaultPrevented + ', --zoom=' + zoom());
    chip.click();
  }

  /* A TAP ON A BAR BUTTON BESIDE A RESTING THUMB. Its touch is cancelled like
     any other two-fingertip touch on the document -- a second finger on the
     bar is how a wide shut starts -- and the click that costs is given back
     once the finger lifts as a tap: soon, unmoved, and no pinch made of it. */
  {
    const btn = el('paper-ink');
    let clicks = 0;
    const count = (e) => { if (e.target === btn) { clicks++; e.stopPropagation(); } };
    window.addEventListener('click', count, true);
    const thumb = [100, 300, 'direct', 10, 1];
    touch(pages, 'touchstart', [thumb], undefined, { changed: [1] });
    const s2 = touch(btn, 'touchstart', [thumb, [400, 40, 'direct', 10, 2]], undefined,
                     { changed: [2] });
    const lift = touch(btn, 'touchend', [thumb], undefined, { changed: [2] });
    touch(pages, 'touchend', [], undefined, { changed: [1] });
    s2.defaultPrevented && lift.defaultPrevented && clicks === 1 && zoom() === '1'
      ? ok('a second finger on a bar button is refused to Safari, and a tap there clicks it once')
      : fail('a tap on a bar button beside a thumb: start refused ' + s2.defaultPrevented
             + ', clicks ' + clicks + ', --zoom=' + zoom());

    touch(pages, 'touchstart', [thumb], undefined, { changed: [1], ts: 1000 });
    touch(btn, 'touchstart', [thumb, [400, 40, 'direct', 10, 2]], undefined,
          { changed: [2], ts: 1010 });
    touch(btn, 'touchend', [thumb], undefined, { changed: [2], ts: 1900 });
    touch(pages, 'touchend', [], undefined, { changed: [1], ts: 1950 });
    touch(pages, 'touchstart', [thumb], undefined, { changed: [1] });
    touch(btn, 'touchstart', [thumb, [400, 40, 'direct', 10, 2]], undefined, { changed: [2] });
    touch(btn, 'touchmove', [[175, 235, 'direct', 10, 1], [325, 105, 'direct', 10, 2]]);
    touch(btn, 'touchend', [[175, 235, 'direct', 10, 1]], undefined, { changed: [2] });
    touch(pages, 'touchend', [], undefined, { changed: [1] });
    clicks === 1 && Number(zoom()) < 0.6
      ? ok('a finger held on a bar button, or pinched from it, clicks nothing')
      : fail('a hold or a pinch on a bar button clicked it: clicks ' + clicks
             + ', --zoom=' + zoom());
    window.removeEventListener('click', count, true);
    chip.click();
  }

  /* A PALM IS NOT A PINCH, AND WITH THE PEN OFF IT DOES NOT STOP A FINGER
     SCROLLING. Its touch is the browser's; only a palm and a finger closing
     on each other -- a flat thumb in a wide shut -- have their moves refused. */
  {
    const rest = touch(pages, 'touchstart', [[400, 500, 'direct', 80], [100, 300]]);
    const r1 = touch(pages, 'touchmove', [[401, 501, 'direct', 80], [100, 250]]);
    const r2 = touch(pages, 'touchmove', [[403, 499, 'direct', 80], [100, 150]]);
    touch(pages, 'touchend', []);
    touch(pages, 'touchstart', [[100, 300, 'direct', 10, 1]], undefined, { changed: [1] });
    touch(pages, 'touchmove', [[100, 270, 'direct', 10, 1]]);
    const joins = touch(pages, 'touchstart', [[100, 270, 'direct', 10, 1],
                                              [500, 500, 'direct', 80, 2]], undefined,
                        { changed: [2] });
    const r3 = touch(pages, 'touchmove', [[100, 200, 'direct', 10, 1],
                                          [502, 501, 'direct', 80, 2]]);
    touch(pages, 'touchend', []);
    !rest.defaultPrevented && !r1.defaultPrevented && !r2.defaultPrevented
      && !joins.defaultPrevented && !r3.defaultPrevented && zoom() === '1'
      ? ok('with the pen off, a finger beside a resting palm scrolls natively')
      : fail('a palm stops a finger scrolling: start ' + rest.defaultPrevented + ', moves '
             + r1.defaultPrevented + '/' + r2.defaultPrevented + ', palm joining '
             + joins.defaultPrevented + '/' + r3.defaultPrevented + ', --zoom=' + zoom());
  }
  /* WITH A PALM IN THE PAIR, THE PALM MUST BE DOING THE PINCHING. A palm that
     wobbles sideways as the hand scrolls is still resting; a flat thumb
     sweeping in on a fingertip that holds still is a shut, and Safari's. */
  {
    touch(pages, 'touchstart', [[100, 300], [400, 300, 'direct', 80]]);
    const wobble = touch(pages, 'touchmove', [[100, 220], [400, 292, 'direct', 80]]);
    const wobble2 = touch(pages, 'touchmove', [[100, 150], [401, 291, 'direct', 80]]);
    touch(pages, 'touchend', []);
    touch(pages, 'touchstart', [[100, 300], [400, 300, 'direct', 80]]);
    const sweep = touch(pages, 'touchmove', [[100, 300], [330, 300, 'direct', 80]], 0.75);
    touch(pages, 'touchend', []);
    !wobble.defaultPrevented && !wobble2.defaultPrevented && sweep.defaultPrevented
      && zoom() === '1'
      ? ok('a palm wobbling beside a scrolling finger is a scroll; a flat thumb sweeping in on a still finger is refused')
      : fail('a palm pair: wobble refused ' + wobble.defaultPrevented + '/' + wobble2.defaultPrevented
             + ', thumb sweeping in refused ' + sweep.defaultPrevented + ', --zoom=' + zoom());
  }
  const palmStart = touch(pages, 'touchstart', [[100, 300], [400, 300, 'direct', 80]]);
  const palm = touch(pages, 'touchmove', [[160, 300], [340, 300, 'direct', 80]], 0.6);
  touch(pages, 'touchend', []);
  !palmStart.defaultPrevented && palm.defaultPrevented && zoom() === '1'
    ? ok('a flat thumb and a finger closing zoom nothing, and Safari gets none of it')
    : fail('a palm shut: start refused ' + palmStart.defaultPrevented + ', move refused '
           + palm.defaultPrevented + ', --zoom=' + zoom());

  /* AN OVERLAY ABOVE THE DOCUMENT IS NOT THE DOCUMENT. Two fingers on the
     steer panel's box scroll it, and pinch nothing behind it; Safari still
     gets no zoom, because a pair whose gap changes is refused anywhere. */
  {
    const box = el('steerbox');
    const s = touch(box, 'touchstart', [[100, 300], [160, 300]]);
    const pan = touch(box, 'touchmove', [[100, 250], [160, 250]]);
    const built = pages.classList.contains('pinching');
    const spreadOut = touch(box, 'touchmove', [[60, 250], [220, 250]], 2.7);
    touch(box, 'touchend', []);
    touch(pages, 'touchstart', [[100, 300]]);
    const half = touch(el('annbar'), 'touchstart', [[100, 300], [400, 300]]);
    const halfMove = touch(el('annbar'), 'touchmove', [[150, 300], [350, 300]], 0.5);
    touch(el('annbar'), 'touchend', []);
    !s.defaultPrevented && !pan.defaultPrevented && !built && spreadOut.defaultPrevented
      && !half.defaultPrevented && halfMove.defaultPrevented && zoom() === '1'
      ? ok('two fingers on an overlay scroll it and pinch nothing under it, and Safari zooms nothing')
      : fail('an overlay: start refused ' + s.defaultPrevented + ', two-finger scroll refused '
             + pan.defaultPrevented + ', pinch built ' + built + ', spread refused '
             + spreadOut.defaultPrevented + ', one finger on the annotation bar '
             + half.defaultPrevented + '/' + halfMove.defaultPrevented + ', --zoom=' + zoom());
  }

  /* A THUMB LANDING DURING A SCROLL IS REFUSED, NOT TURNED INTO A ZOOM. A pinch
     is built only from fingers that land within PAIR_MS of each other, or
     beside a first finger that has not begun to scroll. */
  {
    const bar = doc.querySelector('.paper-bar');
    touch(pages, 'touchstart', [[300, 400]], undefined, { ts: 5000 });
    touch(pages, 'touchmove', [[300, 370]], undefined, { ts: 5040 });
    const late = touch(bar, 'touchstart', [[300, 370], [600, 40]], undefined, { ts: 5600 });
    const built = pages.classList.contains('pinching');
    const lateMove = touch(bar, 'touchmove', [[350, 300], [550, 100]], 0.5, { ts: 5640 });
    touch(bar, 'touchend', [], undefined, { ts: 5700 });
    late.defaultPrevented && lateMove.defaultPrevented && !built && zoom() === '1'
      ? ok('a thumb landing on the bar mid-scroll is refused to Safari and zooms nothing')
      : fail('a thumb mid-scroll: start refused ' + late.defaultPrevented + ', move refused '
             + lateMove.defaultPrevented + ', pinch built ' + built + ', --zoom=' + zoom());
    touch(pages, 'touchstart', [[300, 400]], undefined, { ts: 8000 });
    touch(pages, 'touchmove', [[300, 380]], undefined, { ts: 8030 });
    const quick = touch(pages, 'touchstart', [[300, 380], [600, 380]], undefined, { ts: 8120 });
    touch(pages, 'touchmove', [[375, 380], [525, 380]], 0.5, { ts: 8150 });
    touch(pages, 'touchend', [], undefined, { ts: 8200 });
    quick.defaultPrevented && zoom() === '0.5'
      ? ok('but a shut whose first finger drifted before the second landed, 120 ms on, still zooms')
      : fail('a quick staggered shut with a drifting first finger: --zoom=' + zoom());
    chip.click();
  }

  /* A touch joining a live pinch is the pinch's. The non-passive move is
     armed at a gesture's first touch, before a second finger can land, and
     dropped when every finger lifts or a lone finger is plainly scrolling. */
  const live = [];
  const add = doc.addEventListener, rem = doc.removeEventListener;
  doc.addEventListener = function (n, fn, o) {
    if (n === 'touchmove' && o && o.passive === false && o.capture) live.push(fn);
    return add.call(this, n, fn, o);
  };
  doc.removeEventListener = function (n, fn, o) {
    if (n === 'touchmove') { const i = live.indexOf(fn); if (i >= 0) live.splice(i, 1); }
    return rem.call(this, n, fn, o);
  };
  const before = live.length;
  touch(pages, 'touchstart', [[100, 300]]);
  const first = live.length;
  touch(pages, 'touchstart', [[100, 300], [200, 300]]);
  const third = touch(pages, 'touchstart', [[100, 300], [200, 300], [300, 400]]);
  touch(pages, 'touchmove', [[100, 320], [200, 320], [300, 400]]);
  touch(pages, 'touchend', []);
  const after = live.length;
  const loose = touch(pages, 'touchmove', [[50, 300], [250, 300]], 2);
  touch(pages, 'touchstart', [[100, 300]]);
  const scroll = touch(pages, 'touchmove', [[100, 280]]);
  const scrolling = live.length;
  touch(pages, 'touchend', []);
  doc.addEventListener = add; doc.removeEventListener = rem;
  before === 0 && first === 1 && after === 0 && scrolling === 0 && !scroll.defaultPrevented
    ? ok('a non-passive touchmove is armed at the first touch, and gone once the fingers lift or one scrolls')
    : fail('the guard: before ' + before + ', at the first touch ' + first + ', after the lift '
           + after + ', a lone finger 20 px on ' + scrolling + ' (refused '
           + scroll.defaultPrevented + ')');
  third.defaultPrevented && !loose.defaultPrevented
    ? ok('a touch joining a live pinch is refused, and a move after it is not')
    : fail('joining touch refused ' + third.defaultPrevented + ', loose move refused '
           + loose.defaultPrevented);
  /* Back to half, which the pen's cases below expect to be left alone. */
  chip.click();
  touch(pages, 'touchstart', [[50, 300], [250, 300]]);
  touch(pages, 'touchmove', [[125, 300], [175, 300]], 0.25);
  touch(pages, 'touchend', []);

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

  /* A shut panel leaves nothing on the page that refuses a touch: the lesson
     under it keeps the scroll it had before any document was opened. */
  {
    const gone = [];
    const rem = doc.removeEventListener;
    doc.removeEventListener = function (n, fn, o) {
      if (n === 'touchstart' && o && o.capture) gone.push(fn);
      return rem.call(this, n, fn, o);
    };
    window.__closePaper();
    doc.removeEventListener = rem;
    const s2 = touch(doc.body, 'touchstart', [[100, 300], [400, 300]]);
    const m2 = touch(doc.body, 'touchmove', [[150, 300], [350, 300]]);
    touch(doc.body, 'touchend', []);
    gone.length === 1 && !s2.defaultPrevented && !m2.defaultPrevented
      ? ok('closing the document takes its touch listeners with it')
      : fail('a shut panel still listens: ' + gone.length + ' removed, start refused '
             + s2.defaultPrevented + ', move refused ' + m2.defaultPrevented);
  }

  /* ---- the library reader, which the map's documents region opens ------- */
  {
    /* The library's own markup, so the bar and its buttons and the note
       panel above the reader are the real ones; only the pinch is loaded. */
    const lib = new JSDOM(fs.readFileSync(path.join(WEB, 'library.html'), 'utf8'),
      { runScripts: 'outside-only', pretendToBeVisual: true, virtualConsole: vc });
    const w = lib.window;
    w.eval(fs.readFileSync(path.join(WEB, 'readerzoom.js'), 'utf8'));
    const ld = w.document;
    const sc = ld.getElementById('reader-pages');
    const rbar = ld.getElementById('reader-bar');
    const z = w.ReaderZoom.make({ scroller: sc, bar: rbar, chip: ld.getElementById('reader-zoom'),
                                  open: () => true });
    if (z.live) z.live(true);
    /* `pts` are [x, y, id]; `o` as `touch` above. */
    const t = (name, pts, scale, at, o) => {
      o = o || {};
      const ev = new w.Event(name, { bubbles: true, cancelable: true });
      const list = pts.map(([x, y, id], i) => ({ identifier: id === undefined ? i : id,
        clientX: x, clientY: y, touchType: 'direct', radiusX: 10 }));
      Object.defineProperty(ev, 'touches', { value: list });
      if (o.changed) Object.defineProperty(ev, 'changedTouches', { value: o.changed.map(
        (id) => list.find((p) => p.identifier === id) || { identifier: id }) });
      if (scale !== undefined) Object.defineProperty(ev, 'scale', { value: scale });
      (at || sc).dispatchEvent(ev);
      return ev;
    };
    const lz = () => sc.style.getPropertyValue('--zoom');
    const s0 = t('touchstart', [[100, 300], [200, 300]]);
    const m0 = t('touchmove', [[125, 300], [175, 300]], 0.5);
    t('touchend', []);
    s0.defaultPrevented && m0.defaultPrevented && lz() === '0.5'
      ? ok('in the library reader too, a pinch shut is the document\'s and not Safari\'s')
      : fail('the library reader still hands a pinch to Safari: start '
             + s0.defaultPrevented + ', move ' + m0.defaultPrevented);
    const f0 = t('touchmove', [[100, 200]]);
    !f0.defaultPrevented
      ? ok('and one finger there still scrolls natively')
      : fail('one finger cannot scroll the library reader');

    z.set(2);
    const a1 = t('touchstart', [[100, 300]]);
    t('touchmove', [[104, 300]]);
    const a2 = t('touchstart', [[104, 300], [504, 300]]);
    const a3 = t('touchmove', [[204, 300], [404, 300]]);
    t('touchend', []);
    !a1.defaultPrevented && a2.defaultPrevented && a3.defaultPrevented && lz() === '1'
      ? ok('a shut landing one finger at a time zooms the library reader out')
      : fail('a staggered shut in the library reader: first ' + a1.defaultPrevented
             + ', second ' + a2.defaultPrevented + ', move ' + a3.defaultPrevented
             + ', --zoom=' + lz());

    t('touchstart', [[100, 300]]);
    const b2 = t('touchstart', [[100, 300], [400, 40]], undefined, rbar);
    const b3 = t('touchmove', [[175, 235], [325, 105]], undefined, rbar);
    t('touchend', [], undefined, rbar);
    b2.defaultPrevented && b3.defaultPrevented && Number(lz()) < 0.6
      ? ok('and a second finger on #reader-bar is the reader\'s, not Safari\'s')
      : fail('a finger on the library reader\'s bar: start ' + b2.defaultPrevented
             + ', move ' + b3.defaultPrevented + ', --zoom=' + lz());

    /* The bar is nearly all buttons: a second finger on one is refused like
       any other, and a tap there still clicks it, once. */
    z.set(1);
    const say = ld.getElementById('reader-say');
    let clicks = 0;
    w.addEventListener('click', (e) => { if (e.target === say) clicks++; }, true);
    t('touchstart', [[100, 300, 1]], undefined, sc, { changed: [1] });
    const c2 = t('touchstart', [[100, 300, 1], [400, 40, 2]], undefined, say, { changed: [2] });
    t('touchend', [[100, 300, 1]], undefined, say, { changed: [2] });
    t('touchend', [], undefined, sc, { changed: [1] });
    t('touchstart', [[100, 300, 1]], undefined, sc, { changed: [1] });
    const c3 = t('touchstart', [[100, 300, 1], [400, 40, 2]], undefined, say, { changed: [2] });
    t('touchmove', [[175, 235, 1], [325, 105, 2]], undefined, say);
    t('touchend', [], undefined, say, { changed: [1, 2] });
    c2.defaultPrevented && c3.defaultPrevented && clicks === 1 && Number(lz()) < 0.6
      ? ok('a second finger on a #reader-bar button is refused; a tap there clicks once, a pinch from it does not')
      : fail('a #reader-bar button beside a thumb: refused ' + c2.defaultPrevented + '/'
             + c3.defaultPrevented + ', clicks ' + clicks + ', --zoom=' + lz());

    /* The note panel sits over the reader: two fingers in its box scroll it. */
    z.set(1);
    const note = ld.getElementById('note-text');
    const n1 = t('touchstart', [[100, 300], [160, 300]], undefined, note);
    const n2 = t('touchmove', [[100, 240], [160, 240]], undefined, note);
    const n3 = t('touchmove', [[40, 240], [220, 240]], 3, note);
    t('touchend', [], undefined, note);
    !n1.defaultPrevented && !n2.defaultPrevented && n3.defaultPrevented && lz() === '1'
      ? ok('two fingers in the note panel over the reader scroll it and zoom nothing, theirs or Safari\'s')
      : fail('the note panel over the reader: start ' + n1.defaultPrevented + ', scroll '
             + n2.defaultPrevented + ', spread ' + n3.defaultPrevented + ', --zoom=' + lz());
  }

  console.log(errors.length ? errors.length + ' failed' : 'all passed');
  process.exit(errors.length ? 1 : 0);
})();
