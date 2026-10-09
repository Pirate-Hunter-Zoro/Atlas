// A DOCUMENT ON THE BOARD PINCHES ITSELF, AND THE PAGE NEVER DOES.
//
// Asked as: *"I can't zoom in with my fingers when opening the manuscript, and
// when I try to zoom out it does the whole Safari zoom out."*
//
// Two halves, both driven through the real pages in a real DOM:
//
//   * THE BOARD'S READER (`reader.js`, built over the board: every paper,
//     deck and write-up a box, a card or the contents drawer opens) zooms with
//     `readerzoom.js`, the one reader's pinch. The board refuses the page
//     pinch outright (`html { touch-action: pan-x pan-y }`), so without it a
//     pinch on a document would do nothing at all.
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
// And the ink stays on its words through a pinch on the reader: `inkzoom.js`,
// the case the library and the deck already run.
//
// THE ONE READER ON THE BOARD, too: a document opened from a card goes
// through `Reader.open`, old ink stored with the retired direction field loads
// in place, and every save of ink -- a card's and a page's -- goes through
// `inkkeep.js`, which retries a save that failed.

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
const OLD_KEY = 'doc/paper1-trd-prediction/p1';
const VIEW = {
  ok: true, name: 'Paper 1', n: 2,
  pages: ['/paper/m-1.png', '/paper/m-2.png'],
  /* Ink as a retired reader stored it: the stroke carries the old kind
     field. It loads as ordinary ink, in place. */
  ink: { [OLD_KEY]: [JSON.parse('{"c":"#3366cc","w":2,"pg":1,"dir":1,'
                                + '"p":[0.2,0.6,0.5,0.6],"pr":[0.5,0.5]}')] },
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
/* `/annotate/save` answers as `net.save` says: ok, or a 500. */
const net = { save: 'ok', saves: [] };
window.fetch = (u, o) => {
  const url = String(u);
  if (/annotate\/save/.test(url)) {
    net.saves.push({ url: url, body: JSON.parse((o && o.body) || '{}'), was: net.save });
    if (net.save === 'refused') {
      return Promise.resolve({ ok: false, status: 500,
                               json: () => Promise.resolve({ ok: false }) });
    }
    return json({ ok: true });
  }
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
  && SCRIPTS.indexOf('reader.js') > SCRIPTS.indexOf('inkkeep.js')
  && SCRIPTS.indexOf('inkkeep.js') > SCRIPTS.indexOf('annotate.js')
  ? ok('board.html loads the one reader, its pinch and its save, after the pen they ask about')
  : fail('board.html does not load reader.js, inkkeep.js and readerzoom.js: ' + SCRIPTS.join(', '));
window.INK_RETRY_MS = 60;
for (const f of SCRIPTS) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
try {
  let src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
  src = src.replace('})();',
    'window.__openDoc = openDoc;\nwindow.__closeReader = closeReader;\n})();');
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

  /* ---- the board's reader --------------------------------------------- */
  const opened = [];
  const realOpen = window.Reader.open;
  const mounted = window.Reader.els();
  const inst = mounted && window.Reader.mount();
  const instOpen = inst.open;
  inst.open = function (o) { opened.push(o); return instOpen.call(this, o); };
  window.__openDoc('paper1-trd-prediction', 'Paper 1');
  await sleep(20);
  inst.open = instOpen;
  window.Reader.open = realOpen;
  const pages = el('reader-pages');
  const chip = el('reader-zoom');
  const boxes = pages.querySelectorAll('.lib-page');
  opened.length === 1 && opened[0].pagesUrl === '/view/doc/paper1-trd-prediction'
    && opened[0].inkKey === 'doc/paper1-trd-prediction' && opened[0].burn === 'doc/paper1-trd-prediction'
    ? ok('a document opened from a card goes through Reader.open, with its ink key and its burn kind')
    : fail('the board opened a document without Reader.open: ' + JSON.stringify(opened));
  boxes.length === 2 && !el('reader').hidden && el('reader').classList.contains('reader-over')
    && boxes[0].dataset.ann === 'doc/paper1-trd-prediction/p1'
    ? ok('a document opens on the board in the built reader, a box per page')
    : fail('the document did not open: ' + boxes.length + ' pages');
  !el('paper') && !el('paper-pages') && !el('keepwhat')
    ? ok('the board has no panel of its own: #paper and keep writing are gone')
    : fail('the old document panel is still in board.html');
  const oldInk = window.Annotate.marked().indexOf(OLD_KEY) >= 0
    && window.Annotate.payload(OLD_KEY, false).strokes.length === 1;
  oldInk
    ? ok('old ink stored with the retired direction field loads in place, as ordinary ink')
    : fail('old ink did not load: ' + window.Annotate.marked().join(', '));
  const keep = el('reader-keep');
  keep && !keep.hidden && !keep.disabled && /marked copy/.test(keep.textContent)
    ? ok('keep writing is the marked copy: one button, live once there is ink')
    : fail('the marked-copy button: ' + (keep ? keep.hidden + '/' + keep.disabled : 'missing'));

  /* EVERY SAVE GOES THROUGH INKKEEP. A page's ink and a card's: a save the
     board answers 500 stays owed and is retried, and only the retry that
     lands cleans it. */
  {
    const S = { c: '#e8746c', w: 2, pg: 1, p: [0.1, 0.1, 0.3, 0.4], pr: [0.5, 0.5] };
    const P2 = 'doc/paper1-trd-prediction/p2';
    const draw = (key, s) => { window.Annotate.load({ [key]: [s] }); window.Annotate.clear(key); window.Annotate.undo(); };
    net.save = 'refused';
    net.saves.length = 0;
    draw(P2, S);
    draw('0001', { c: '#e8746c', w: 2, p: [0.1, 0.1, 0.3, 0.4], pr: [0.5, 0.5] });
    await sleep(1000);
    const first = net.saves.filter((x) => x.was === 'refused').map((x) => x.body.card);
    const owed = window.Annotate.unsaved();
    first.indexOf(P2) >= 0 && first.indexOf('0001') >= 0
      && owed.indexOf(P2) >= 0 && owed.indexOf('0001') >= 0
      ? ok('a refused save of a page and of a card both stay owed')
      : fail('after a 500: tried ' + JSON.stringify(first) + ', owed ' + JSON.stringify(owed));
    net.save = 'ok';
    await sleep(200);
    const retried = net.saves.filter((x) => x.was === 'ok').map((x) => x.body.card);
    retried.indexOf(P2) >= 0 && retried.indexOf('0001') >= 0
      && window.Annotate.unsaved().length === 0
      && net.saves.every((x) => /^\/annotate\/save$/.test(x.url) && !x.body.send)
      ? ok('and the keeper retries them on its own, cleans them once they land, and sends nothing')
      : fail('the retry: ' + JSON.stringify(retried) + ', still owed '
             + JSON.stringify(window.Annotate.unsaved()));
    window.Annotate.clear(P2);
    window.Annotate.clear('0001');
    await sleep(1000);
  }
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
    && !pages.contains(el('reader-bar'))
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
    const bar = el('reader-bar');
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
     once the finger lifts as a tap: unmoved, the pair's gap unchanged, however
     long it was held. */
  {
    const btn = el('reader-pen');
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
    touch(btn, 'touchmove', [thumb, [403, 42, 'direct', 10, 2]], undefined, { ts: 1500 });
    touch(btn, 'touchend', [thumb], undefined, { changed: [2], ts: 1900 });
    touch(pages, 'touchend', [], undefined, { changed: [1], ts: 1950 });
    clicks === 2 && zoom() === '1' && !pages.style.transform
      ? ok('a deliberate press on a bar button, held 890 ms beside a thumb, clicks it once, and zooms nothing')
      : fail('a held press on a bar button beside a thumb: clicks ' + clicks + ' (want 2), --zoom='
             + zoom() + ', transform ' + JSON.stringify(pages.style.transform));
    touch(pages, 'touchstart', [thumb], undefined, { changed: [1] });
    touch(btn, 'touchstart', [thumb, [400, 40, 'direct', 10, 2]], undefined, { changed: [2] });
    touch(btn, 'touchmove', [[175, 235, 'direct', 10, 1], [325, 105, 'direct', 10, 2]]);
    touch(btn, 'touchend', [[175, 235, 'direct', 10, 1]], undefined, { changed: [2] });
    touch(pages, 'touchend', [], undefined, { changed: [1] });
    clicks === 2 && Number(zoom()) < 0.6
      ? ok('a finger pinched from a bar button clicks nothing')
      : fail('a pinch from a bar button clicked it: clicks ' + clicks
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
    const half = touch(doc.querySelector('.annbar-board'), 'touchstart', [[100, 300], [400, 300]]);
    const halfMove = touch(doc.querySelector('.annbar-board'), 'touchmove', [[150, 300], [350, 300]], 0.5);
    touch(doc.querySelector('.annbar-board'), 'touchend', []);
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
    const bar = el('reader-bar');
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

  /* The latch refuses a pan on the whole reader (`body.pen-writing
     #reader-pages.zoomable`), its bare strips too, so a finger landing on one
     of those is scrolled by hand like a finger on an ink layer. */
  {
    const sheet = doc.createElement('style');
    sheet.textContent = '#reader-pages { overflow-y: auto; }';
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

  /* THE WHOLE PANEL IS THE READER'S, not only its pages and bar: a second
     finger on the panel itself, between the two, is cancelled at its
     touchstart and pinches the document. */
  {
    chip.click();
    touch(pages, 'touchstart', [[100, 300]]);
    const s2 = touch(el('reader'), 'touchstart', [[100, 300], [300, 300]]);
    const m2 = touch(el('reader'), 'touchmove', [[50, 300], [350, 300]]);
    touch(el('reader'), 'touchend', []);
    s2.defaultPrevented && m2.defaultPrevented && zoom() === '1.5'
      ? ok('a finger on the panel outside its pages and bar is the reader\'s from its touchstart')
      : fail('a finger on #reader itself: start refused ' + s2.defaultPrevented + ', move '
             + m2.defaultPrevented + ', --zoom=' + zoom());
  }

  chip.click();
  zoom() === '1' && chip.hidden
    ? ok('a tap on the chip puts the page width back')
    : fail('the zoom chip does not reset: --zoom=' + zoom());

  touch(pages, 'touchstart', [[100, 300], [200, 300]]);
  touch(pages, 'touchmove', [[50, 300], [250, 300]]);
  touch(pages, 'touchend', []);
  /* A PAGE ZOOM IN EFFECT WHEN A DOCUMENT OPENS IS PUT BACK, through
     `recentre.js`'s clamp on the viewport declaration. */
  const vp = doc.querySelector('meta[name="viewport"]');
  const vpWas = vp.getAttribute('content');
  window.visualViewport = Object.assign(new window.EventTarget(),
    { scale: 1.6, width: 640, height: 480, offsetLeft: 0, offsetTop: 0 });
  window.__openDoc('paper1-trd-prediction', 'Paper 1');
  await sleep(20);
  zoom() === '1' && chip.hidden
    ? ok('and every document opens at the page width, whatever the last was left at')
    : fail('a document opened at the last one\'s zoom: ' + zoom());
  /maximum-scale=1/.test(vp.getAttribute('content'))
    ? ok('a document opening on a page Safari has zoomed to 160% asks for the page\'s scale back')
    : fail('a document opened over a page zoom and left it: ' + vp.getAttribute('content'));
  const magnifiedHtml = () => doc.documentElement.classList.contains('page-magnified');
  magnifiedHtml()
    ? ok('a document open on a page at 160% gives <html> page-magnified, the pinch back out')
    : fail('a document open on a magnified page: <html> has no page-magnified');
  const gs = gesture(pages, 'gesturestart');
  !gs.defaultPrevented
    ? ok('and under it board.js refuses Safari no gesture event')
    : fail('a gesture under page-magnified is refused: Safari cannot pinch the page back out');
  window.visualViewport.scale = 1;
  window.dispatchEvent(new window.Event('pointerdown'));
  vp.getAttribute('content') === vpWas
    ? ok('and the clamp is lifted again, so the page is not left unzoomable')
    : fail('the viewport clamp stayed: ' + vp.getAttribute('content'));

  const css = fs.readFileSync(path.join(WEB, 'board.css'), 'utf8');
  const rcss = fs.readFileSync(path.join(WEB, 'reader.css'), 'utf8');
  /width: calc\(min\(100%, 54rem\) \* var\(--zoom, 1\)\)/.test(rcss)
    && /body\.pen-writing #reader-pages\.zoomable \{ touch-action: none; \}/.test(rcss)
    && !/touch-action:[^;]*pinch-zoom/.test(css + rcss)
    ? ok('reader.css lays a page out at the zoom, and nothing gives the page its pinch back')
    : fail('reader.css does not lay the reader\'s pages out at --zoom');
  /html\.page-magnified \{ touch-action: manipulation; \}/.test(css)
    && /html\.page-magnified body:not\(\.pen-writing\) #reader \* \{\s*touch-action: manipulation !important;/.test(css)
    ? ok('board.css gives the page and the reader the pinch back under page-magnified, and only there')
    : fail('board.css has no page-magnified rule for the page and the reader');

  /* ---- the ink stays on its words through a pinch ---------------------- */
  boxes.length && await require('./inkzoom')(window, {
    ok, fail, name: 'board document', naturalHeight: 1604,
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
    window.__closeReader();
    doc.removeEventListener = rem;
    const s2 = touch(doc.body, 'touchstart', [[100, 300], [400, 300]]);
    const m2 = touch(doc.body, 'touchmove', [[150, 300], [350, 300]]);
    touch(doc.body, 'touchend', []);
    !doc.documentElement.classList.contains('page-magnified')
      ? ok('closing the document takes page-magnified off <html>')
      : fail('a shut document left page-magnified on <html>');
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

  /* ---- the library page: its strips, a page zoom, and the record ------- */
  {
    const LIB_HTML = fs.readFileSync(path.join(WEB, 'library.html'), 'utf8');
    const order = (LIB_HTML.match(/src="\/static\/[\w.-]+"/g) || [])
      .map((m) => /static\/([\w.-]+)/.exec(m)[1]);
    order.indexOf('recentre.js') >= 0 && order.indexOf('recentre.js') < order.indexOf('readerzoom.js')
      ? ok('library.html loads recentre.js, the way back from a page zoom, before the reader')
      : fail('library.html does not load recentre.js before readerzoom.js: ' + order.join(', '));
    const lib = new JSDOM(LIB_HTML,
      { runScripts: 'outside-only', pretendToBeVisual: true, virtualConsole: vc });
    const w = lib.window;
    const ld = w.document;
    const vv = Object.assign(new w.EventTarget(),
      { scale: 1.6, width: 640, height: 480, offsetLeft: 0, offsetTop: 0 });
    w.visualViewport = vv;
    let redraws = 0, commits = 0;
    w.Annotate = { isOn: () => false, redrawAll: () => { redraws++; } };
    w.eval(fs.readFileSync(path.join(WEB, 'recentre.js'), 'utf8'));
    w.eval(fs.readFileSync(path.join(WEB, 'readerzoom.js'), 'utf8'));
    const sc = ld.getElementById('reader-pages');
    const reader = ld.getElementById('reader');
    let isOpen = false;
    const z = w.ReaderZoom.make({ scroller: sc, surface: reader,
      bar: ld.getElementById('reader-bar'), chip: ld.getElementById('reader-zoom'),
      open: () => isOpen, committed: () => { commits++; } });
    const meta = ld.querySelector('meta[name="viewport"]');
    const was = meta.getAttribute('content');
    const clamped = () => /maximum-scale=1/.test(meta.getAttribute('content'));
    /* Safari obliging the clamp: the scale drops, and the next touch lifts it. */
    const obliged = () => {
      vv.scale = 1;
      vv.dispatchEvent(new w.Event('resize'));
      w.dispatchEvent(new w.Event('pointerdown'));
    };
    const mag = () => ld.documentElement.classList.contains('page-magnified');
    /* `pts` are [x, y, id]; `o.changed` the ids it is for, `o.cancelable` false
       for a move WebKit will not let be cancelled. */
    const t = (name, pts, at, o) => {
      o = o || {};
      const ev = new w.Event(name, { bubbles: true, cancelable: o.cancelable !== false });
      const list = pts.map(([x, y, id], i) => ({ identifier: id === undefined ? i : id,
        clientX: x, clientY: y, touchType: 'direct', radiusX: 10 }));
      Object.defineProperty(ev, 'touches', { value: list });
      if (o.changed) Object.defineProperty(ev, 'changedTouches', { value: o.changed.map(
        (id) => list.find((p) => p.identifier === id) || { identifier: id }) });
      (at || sc).dispatchEvent(ev);
      return ev;
    };
    const lz = () => sc.style.getPropertyValue('--zoom');

    /* A PAGE ZOOM IN EFFECT IS PUT BACK, on opening and whenever it appears. */
    reader.hidden = false;
    isOpen = true;
    z.live(true);
    clamped()
      ? ok('a document opening at visualViewport.scale 1.6 resets the page zoom')
      : fail('a document opened over a 160% page zoom and left it: ' + meta.getAttribute('content'));
    const magAt16 = mag();
    obliged();
    const magAt1 = mag();
    magAt16 && !magAt1
      ? ok('<html> is page-magnified at scale 1.6, and not once the scale is back to 1.0')
      : fail('page-magnified: at 1.6 ' + magAt16 + ', at 1.0 ' + magAt1);
    meta.getAttribute('content') === was
      ? ok('and the clamp is lifted, so the page can still be zoomed later')
      : fail('the viewport clamp stayed: ' + meta.getAttribute('content'));
    vv.scale = 1.5;
    vv.dispatchEvent(new w.Event('resize'));
    clamped() && mag()
      ? ok('a page zoom appearing while the document is open is reset as it appears, and marked')
      : fail('a scale change while open was left: ' + meta.getAttribute('content')
             + ', page-magnified ' + mag());
    {
      /* Safari's own pinch back out fires a resize every frame. */
      const from = w.ReaderZoom.trace().length;
      for (let i = 0; i < 20; i++) {
        vv.scale = 1.5 - i * 0.02;
        vv.dispatchEvent(new w.Event('resize'));
      }
      const said = w.ReaderZoom.trace().slice(from)
        .filter((r) => r.what === 'page-zoom').length;
      said === 0
        ? ok('a spell of magnification is written down once, not once a frame')
        : fail('a pinch back out wrote ' + said + ' more page-zoom entries');
    }
    obliged();
    const note = ld.getElementById('note-text');
    ld.getElementById('note').hidden = false;
    note.focus();
    vv.scale = 1.4;
    vv.dispatchEvent(new w.Event('resize'));
    const typing = !clamped() && ld.activeElement === note;
    note.blur();
    await sleep(5);
    typing && clamped()
      ? ok('a field being typed in keeps Safari\'s zoom until it lets go, and then the page is reset')
      : fail('a focused field: kept its zoom and focus ' + typing + ', reset after the blur '
             + clamped());
    obliged();
    ld.getElementById('note').hidden = true;

    /* WHERE SAFARI IGNORES THE CLAMP, a gesture on the magnified page is
       Safari's own, so its pinch out is a way back; at 100% it is the reader's. */
    vv.scale = 1.5;
    const asideMag = (() => {
      const ev = new w.Event('touchstart', { bubbles: true, cancelable: true });
      Object.defineProperty(ev, 'touches', { value: [
        { identifier: 7, clientX: 300, clientY: 400, touchType: 'direct', radiusX: 80 }] });
      const was = w.Annotate.isOn;
      w.Annotate.isOn = () => true;
      sc.dispatchEvent(ev);
      w.Annotate.isOn = was;
      const lift = new w.Event('touchend', { bubbles: true, cancelable: true });
      Object.defineProperty(lift, 'touches', { value: [] });
      sc.dispatchEvent(lift);
      return { refused: ev.defaultPrevented, mag: mag() };
    })();
    !asideMag.refused && asideMag.mag
      ? ok('on a magnified page nothing is refused, a palm with the pen on included, and <html> is page-magnified')
      : fail('a palm on a magnified page: refused ' + asideMag.refused + ', page-magnified '
             + asideMag.mag);
    const a1 = t('touchstart', [[100, 300], [200, 300]]);
    const a2 = t('touchmove', [[150, 300], [160, 300]]);
    const ag = new w.Event('gesturestart', { bubbles: true, cancelable: true });
    ld.dispatchEvent(ag);
    t('touchend', []);
    obliged();
    const b1 = t('touchstart', [[100, 300], [200, 300]]);
    t('touchend', []);
    !a1.defaultPrevented && !a2.defaultPrevented && !ag.defaultPrevented && lz() === ''
      && b1.defaultPrevented
      ? ok('a gesture beginning on a magnified page is left to Safari, to pinch it back out')
      : fail('a gesture on a magnified page: refused ' + a1.defaultPrevented + '/'
             + a2.defaultPrevented + '/' + ag.defaultPrevented + ', --zoom=' + lz()
             + ', the next at 100% refused ' + b1.defaultPrevented);

    /* THE STRIPS UNDER THE BAR ARE THE READER'S: a second finger on one is
       cancelled at its touchstart and pinches the document. */
    for (const id of ['reader-said', 'reader-copy', 'reader-rebuilt']) {
      const strip = ld.getElementById(id);
      strip.hidden = false;
      z.set(1);
      t('touchstart', [[100, 300]]);
      const s2 = t('touchstart', [[100, 300], [300, 300]], strip);
      const m2 = t('touchmove', [[50, 300], [350, 300]], strip);
      t('touchend', [], strip);
      strip.hidden = true;
      s2.defaultPrevented && m2.defaultPrevented && lz() === '1.5'
        ? ok('a second finger on #' + id + ' is the reader\'s from its touchstart, and pinches it')
        : fail('a finger on #' + id + ': start refused ' + s2.defaultPrevented + ', move '
               + m2.defaultPrevented + ', --zoom=' + lz());
    }

    /* A TAP BESIDE A RESTING FINGERTIP COMMITS NOTHING: no re-draw of the
       ink, no `committed` (the library's place is not given up). */
    z.set(1);
    redraws = 0;
    commits = 0;
    const btn = ld.getElementById('reader-say');
    let clicks = 0;
    w.addEventListener('click', (e) => { if (e.target === btn) clicks++; }, true);
    t('touchstart', [[100, 300, 1]], sc, { changed: [1] });
    t('touchstart', [[100, 300, 1], [400, 40, 2]], btn, { changed: [2] });
    t('touchmove', [[101, 301, 1], [403, 42, 2]], btn);
    t('touchend', [[101, 301, 1]], btn, { changed: [2] });
    t('touchend', [], sc, { changed: [1] });
    clicks === 1 && redraws === 0 && commits === 0 && lz() === '1' && !sc.style.transform
      ? ok('a tap beside a resting fingertip clicks once and commits no zoom: no re-draw, no committed()')
      : fail('a tap beside a fingertip: clicks ' + clicks + ', re-draws ' + redraws
             + ', commits ' + commits + ', --zoom=' + lz());
    t('touchstart', [[100, 300, 1]], sc, { changed: [1] });
    t('touchstart', [[100, 300, 1], [400, 40, 2]], btn, { changed: [2] });
    t('touchmove', [[100, 330, 1], [400, 70, 2]], btn);
    t('touchend', [[100, 330, 1]], btn, { changed: [2] });
    t('touchend', [], sc, { changed: [1] });
    t('touchstart', [[100, 300], [200, 300]]);
    t('touchmove', [[50, 300], [250, 300]]);
    t('touchend', []);
    clicks === 1 && commits === 2 && redraws === 2 && lz() === '2'
      ? ok('a button finger dragged with its pair clicks nothing, and a real pinch commits once')
      : fail('after a drag and a pinch: clicks ' + clicks + ', commits ' + commits
             + ', re-draws ' + redraws + ', --zoom=' + lz());

    /* THE RECORD: with no `BoardTrace` on the page, every cancelled touchstart
       and the cancelled moves are still written down, with whether WebKit
       let each be cancelled. */
    const from = w.ReaderZoom.trace().length;
    t('touchstart', [[100, 300], [200, 300]]);
    t('touchmove', [[90, 300], [210, 300]]);
    t('touchmove', [[80, 300], [220, 300]]);
    const stuck = t('touchmove', [[70, 300], [230, 300]], sc, { cancelable: false });
    t('touchend', []);
    const rec = w.ReaderZoom.trace().slice(from);
    const starts = rec.filter((r) => r.what === 'zoom-start');
    const moves = rec.filter((r) => r.what === 'zoom-refuse' && r.of.on === 'touchmove');
    !w.BoardTrace && starts.length === 1 && starts[0].of.cancelable && starts[0].of.prevented
      && moves.length === 2 && moves[0].of.cancelable && moves[0].of.prevented
      && !moves[1].of.cancelable && !moves[1].of.prevented && !stuck.defaultPrevented
      && rec.some((r) => r.what === 'page-zoom') === false
      && w.ReaderZoom.trace().some((r) => r.what === 'page-zoom' && r.of.reset)
      ? ok('the library page keeps its own record: each cancelled touch, and whether WebKit let it be cancelled')
      : fail('the reader\'s record: ' + JSON.stringify(rec));

    /* A RESTING FINGER SLIDING SQUARE TO THE GAP moves the pair's midpoint
       12 px and its gap under 1 px: no longer a tap, so nothing is clicked. */
    {
      z.set(1);
      let perp = 0;
      const count = (e) => { if (e.target === btn) perp++; };
      w.addEventListener('click', count, true);
      t('touchstart', [[100, 300, 1]], sc, { changed: [1] });
      t('touchstart', [[100, 300, 1], [400, 40, 2]], btn, { changed: [2] });
      t('touchmove', [[116, 318, 1], [400, 40, 2]], btn);
      t('touchend', [[116, 318, 1]], btn, { changed: [2] });
      t('touchend', [], sc, { changed: [1] });
      w.removeEventListener('click', count, true);
      perp === 0
        ? ok('a resting finger sliding square to the gap, the midpoint 12 px on, clicks nothing')
        : fail('a perpendicular slide beside a bar button clicked it ' + perp + ' time(s)');
    }

    /* THE PAGES FOLLOW THE FINGERS FROM WHERE THEY LAND: under the 10 px
       bounds the transform is already the fingers' ratio, so crossing them
       is no jump; a pinch that stays under them still commits nothing. */
    {
      z.set(1);
      commits = 0;
      t('touchstart', [[100, 300], [200, 300]]);
      t('touchmove', [[96, 300], [204, 300]]);
      const under = sc.style.transform;
      t('touchend', []);
      const kept = commits === 0 && lz() === '1' && !sc.style.transform;
      t('touchstart', [[100, 300], [200, 300]]);
      t('touchmove', [[96, 300], [204, 300]]);
      const before = sc.style.transform;
      t('touchmove', [[94, 300], [206, 300]]);
      const past = sc.style.transform;
      t('touchend', []);
      /scale\(1\.08\)/.test(under) && kept && /scale\(1\.08\)/.test(before)
        && /scale\(1\.12\)/.test(past) && lz() === '1.12' && commits === 1
        ? ok('a pinch follows the fingers from landing (108 px gap: 1.08, 112 px: 1.12), with no jump at 10 px, and only a moved one commits')
        : fail('a pinch across the bounds: under ' + JSON.stringify(under) + ', kept ' + kept
               + ', then ' + JSON.stringify(before) + ' -> ' + JSON.stringify(past)
               + ', --zoom=' + lz() + ', commits ' + commits);
      z.set(1);
    }

    /* A HAND WRITING IS NOT WRITTEN DOWN: fifty Pencil strokes with the pen
       on, each with a palm resting beside the nib, add nothing to the record,
       though every palm is still refused. */
    {
      const was = w.Annotate.isOn;
      w.Annotate.isOn = () => true;
      const pt = (name, list) => {
        const ev = new w.Event(name, { bubbles: true, cancelable: true });
        Object.defineProperty(ev, 'touches', { value: list });
        sc.dispatchEvent(ev);
        return ev;
      };
      const nib = (x, y) => ({ identifier: 1, clientX: x, clientY: y, touchType: 'stylus', radiusX: 1 });
      const heel = { identifier: 2, clientX: 600, clientY: 700, touchType: 'direct', radiusX: 80 };
      const n0 = w.ReaderZoom.trace().length;
      let refused = 0;
      for (let i = 0; i < 50; i++) {
        if (pt('touchstart', [nib(100, 300 + i)]).defaultPrevented) refused++;
        if (pt('touchstart', [nib(100, 300 + i), heel]).defaultPrevented) refused++;
        pt('touchmove', [nib(160, 310 + i), heel]);
        pt('touchend', [heel]);
        pt('touchend', []);
      }
      w.Annotate.isOn = was;
      const added = w.ReaderZoom.trace().length - n0;
      added === 0 && refused === 100
        ? ok('fifty Pencil strokes with a palm beside the nib add 0 entries to the record, and every touch is still refused')
        : fail('pen strokes: ' + added + ' entries added, ' + refused + ' of 100 touches refused');
    }

    z.live(false);
    !mag()
      ? ok('a document shutting takes page-magnified off <html>')
      : fail('page-magnified outlived the document');
  }

  console.log(errors.length ? errors.length + ' failed' : 'all passed');
  process.exit(errors.length ? 1 : 0);
})();
