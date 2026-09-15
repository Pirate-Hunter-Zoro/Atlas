// The way out of the whole plan, and it has to be there when the plan is wrong.
//
// Asked for in these words: *"we may be balls deep in a project and I might
// realize we need a massive direction change and overhaul... I want maximum
// power, minimum pain."* The moment that happens is a moment somebody is
// looking at something — a map, a document, a lesson zoomed in on a proof — and
// a button that is only on one of those surfaces is a button that is missing
// when it is wanted.
//
// Three things here are invisible in a screenshot and each has stranded
// somebody before, on the two controls this one rides beside:
//
//   1. `position: fixed` is fixed to the LAYOUT viewport. Pinching moves the
//      VISUAL one, so a control placed by CSS alone slides off the glass.
//   2. The map and the document viewer cover the whole screen at z-index 96 and
//      95. A control under those is not "always available".
//   3. A sheet that changes four things at once has to say so before it does
//      them, or it gets tapped once and never again.

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

const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
  runScripts: 'outside-only', pretendToBeVisual: true, url: 'https://board.test/board',
});
const { window } = dom;

window.HTMLCanvasElement.prototype.getContext = () =>
  new Proxy({}, { get: () => () => {}, set: () => true });
window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => 800 });
Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 600 });
window.HTMLElement.prototype.getBoundingClientRect = function () {
  return { left: 0, top: 0, width: 800, height: 40, right: 800, bottom: 40, x: 0, y: 0 };
};
window.Element.prototype.scrollIntoView = function () {};

// Every request the board makes, so what the button actually sends is checked
// on the wire rather than in the intention.
const sent = [];
window.fetch = (u, opts) => {
  sent.push({ url: String(u), opts: opts || {} });
  if (/slate\/state/.test(String(u))) {
    return Promise.resolve({ json: () => Promise.resolve({ pages: [] }) });
  }
  if (/\/direction/.test(String(u))) {
    return Promise.resolve({ json: () => Promise.resolve({ ok: true,
                                                           chapter: 'New direction — x' }) });
  }
  return new Promise(() => {});
};
window.renderMathInElement = () => {};
window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
window.EventSource = function () {
  window.__es = this;
  this.readyState = 1; this.close = function () {}; this.addEventListener = function () {};
};

const vv = new window.EventTarget();
vv.width = 800; vv.height = 600; vv.offsetLeft = 0; vv.offsetTop = 0; vv.scale = 1;
Object.defineProperty(window, 'visualViewport', { value: vv, configurable: true });
const zoomTo = async (scale, offsetLeft, offsetTop) => {
  vv.scale = scale;
  vv.width = 800 / scale;
  vv.height = 600 / scale;
  vv.offsetLeft = offsetLeft;
  vv.offsetTop = offsetTop;
  vv.dispatchEvent(new window.Event('resize'));
  await sleep(10);
};

window.addEventListener('error', (e) => fail('uncaught: ' + e.message));

for (const f of ['typeface.js', 'macros.js', 'gauge.js', 'recentre.js', 'plane-core.js', 'slate-core.js', 'annotate.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
try { window.eval(fs.readFileSync(path.join(WEB, 'board.js'), 'utf8')); }
catch (e) { fail('board.js: ' + e.message); }

const doc = window.document;
const btn = doc.getElementById('redirect');
const sheet = doc.getElementById('steer');
const box = doc.getElementById('steerbox');
const go = doc.getElementById('steer-go');
const css = fs.readFileSync(path.join(WEB, 'board.css'), 'utf8');
const js = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');

const at = (el) => {
  const m = /translate\(([-\d.]+)px,\s*([-\d.]+)px\)\s*scale\(([\d.]+)\)/
    .exec(el.style.transform || '');
  return m ? { x: +m[1], y: +m[2], k: +m[3] } : null;
};
// The z-index of a rule whose selector list STARTS a line. Anchored, because a
// comment above a rule may name another selector and an unanchored search then
// reads the wrong block — which it did, and reported a button as covering the
// menu it sits under.
const zOf = (sel) => {
  const rule = new RegExp('^' + sel + '(?![\\w-])[^{}\n]*\\{[^}]*\\}', 'm').exec(css);
  const z = rule && /z-index:\s*(\d+)/.exec(rule[0]);
  return z ? +z[1] : null;
};

(async function () {
  if (!btn || !sheet) {
    fail('there is no way to change direction from the board at all');
    console.log('\n' + errors.length + ' FAILURES');
    process.exit(1);
  }
  ok('the board carries a way to change the direction of the work');

  // 1. Always there. Not in a menu, not behind a sitting, not conditional on
  //    anything — the state it exists for is one that arrives without warning.
  !btn.hidden ? ok('and it is present without being asked for')
              : fail('the button starts hidden, so it is not there when it is wanted');
  !/els\.redirect\.hidden\s*=/.test(js)
    ? ok('and nothing on the board ever takes it away')
    : fail('something hides the button; the promise is then conditional');

  // 2. Over the two surfaces that cover the whole screen. The moment somebody
  //    decides the plan is wrong is usually the moment they are looking at the
  //    map of it.
  {
    const mine = zOf('#redirect');
    const map = zOf('#map');
    const paper = zOf('#paper');
    const menu = zOf('\\.barmenu');
    mine && map && mine > map
      ? ok('it sits over the map (' + mine + ' against ' + map + ')')
      : fail('the map covers the button: ' + mine + ' against ' + map);
    mine && paper && mine > paper
      ? ok('and over a document being read')
      : fail('a document being read covers the button: ' + mine + ' against ' + paper);
    !menu || mine < menu
      ? ok('and under the bar menu, which is the most recent thing anybody asked for')
      : fail('the button covers the bar menu');
    const shz = zOf('#steer');
    shz && mine && shz > mine
      ? ok('and what it opens is over everything the button is over')
      : fail('the sheet opens under the map it was tapped from: ' + shz);
  }

  // 3. Placed against the visual viewport, like the two controls it rides with.
  const first = at(btn);
  first ? ok('it is placed from JavaScript: ' + btn.style.transform)
        : fail('nothing positioned the button — CSS alone cannot follow a pinch');

  await zoomTo(2, 300, 200);
  const zoomed = at(btn);
  if (!zoomed) {
    fail('the button lost its position when the page was zoomed');
  } else {
    Math.abs(zoomed.k - 0.5) < 0.001
      ? ok('zoomed to 2×, it counter-scales and stays a thumb wide')
      : fail('the button scales with the page: at 2× it is drawn at ' + zoomed.k);
    zoomed.x >= vv.offsetLeft && zoomed.x <= vv.offsetLeft + vv.width &&
    zoomed.y >= vv.offsetTop && zoomed.y <= vv.offsetTop + vv.height
      ? ok('and followed the visible window into the corner it was panned to')
      : fail('the button is outside the visible window at ' + zoomed.x + ',' + zoomed.y);
  }
  // It rides UNDER the re-centre rather than on top of it: one stack, one place
  // to look, and nothing overlapping the control that gets you out of a zoom.
  {
    const panic = at(doc.getElementById('panic'));
    const mine = at(btn);
    panic && mine && mine.y > panic.y
      ? ok('and rides under the re-centre, in the same stack')
      : fail('the two controls are drawn on top of each other');
  }
  await zoomTo(1, 0, 0);

  // 4. The sheet says what is about to happen. Four things at once, one of them
  //    archiving the lesson they are in.
  btn.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  !sheet.hidden ? ok('tapping it opens the sheet')
                : fail('the button did nothing');
  {
    const words = sheet.textContent.replace(/\s+/g, ' ');
    /filed away/.test(words) && /◷/.test(words)
      ? ok('which says the lesson is filed rather than lost')
      : fail('nothing says what happens to the lesson they are in: ' + words);
    /plan and the map are rewritten/.test(words)
      ? ok('and that the plan and the map are redone to match')
      : fail('nothing says the plan is rewritten');
    /new tutor/.test(words)
      ? ok('and that the assistant is replaced, not persuaded')
      : fail('nothing says the tutor is replaced');
  }

  // 5. Nothing is sent until there is a sentence. A direction of "" would
  //    archive the lesson and wake a tutor with nothing to act on.
  go.disabled ? ok('with nothing written, there is nothing to send')
              : fail('an empty direction can be sent');
  sent.length = 0;
  go.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  !sent.filter((r) => /direction/.test(r.url)).length
    ? ok('and tapping it anyway sends nothing')
    : fail('an empty direction reached the server');

  box.value = 'Drop the bake-off. This is about calibration now.';
  box.dispatchEvent(new window.Event('input', { bubbles: true }));
  !go.disabled ? ok('a sentence makes it sendable')
               : fail('the button stays disabled with a sentence written');

  sent.length = 0;
  go.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await sleep(10);
  {
    const call = sent.filter((r) => /\/direction/.test(r.url))[0];
    if (!call) {
      fail('nothing was sent to the board');
    } else {
      ok('it posts to /direction');
      const body = JSON.parse(call.opts.body || '{}');
      body.text === 'Drop the bake-off. This is about calibration now.'
        ? ok('carrying their words as written, not a summary of them')
        : fail('the wrong thing was sent: ' + call.opts.body);
      (call.opts.method || '').toUpperCase() === 'POST'
        ? ok('as a POST, so no cache anywhere can replay it')
        : fail('the direction was sent as a ' + call.opts.method);
    }
  }
  sheet.hidden ? ok('and the sheet closes, back to the board it changed')
               : fail('the sheet stayed open over the lesson it just replaced');

  // 6. And it closes with everything else. A sheet left open behind the map is
  //    a sheet sitting on top of the lesson when the map closes.
  /els\.steer/.test(js) && /addrShut/.test(js)
    ? ok('and goes away with every other panel when an address says where to be')
    : fail('the sheet is not in the list of things that close');

  console.log('');
  if (errors.length) {
    console.log(errors.length + ' FAILURES');
    process.exit(1);
  }
  console.log('the plan can be wrong, and saying so is one tap from anywhere');
})();
