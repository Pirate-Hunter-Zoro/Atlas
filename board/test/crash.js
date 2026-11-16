// Two ways the board used to become silently unusable.
//
//   1. Send disabled itself and then called the host's `onSending` hook. If
//      that hook threw, the button stayed disabled for the rest of the lesson:
//      no request, no retry, which reads on the iPad as the tutor crashing.
//   2. The board page told nobody when a script threw. home.js has a beacon to
//      /client-error; the board had none, so a freeze left no trace at all.
//
// Both are asserted on the real files in a real DOM. jsdom is a
// development-only dependency: without it this suite skips.

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
const HTML = fs.readFileSync(path.join(WEB, 'board.html'), 'utf8');
const errors = [];
const ok = (m) => console.log('ok   ' + m);
const fail = (m) => { errors.push(m); console.log('FAIL ' + m); };

function boot() {
  const dom = new JSDOM(HTML, {
    runScripts: 'outside-only', pretendToBeVisual: true,
    url: 'https://board.test/board',
  });
  const { window } = dom;

  window.HTMLCanvasElement.prototype.getContext = () =>
    new Proxy({}, { get: () => () => {}, set: () => true });
  window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
  Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => 900 });
  Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 500 });
  window.HTMLElement.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: 900, height: 500, right: 900, bottom: 500, x: 0, y: 0 };
  };
  window.Element.prototype.scrollIntoView = function () {};
  window.Element.prototype.setPointerCapture = function () {};
  window.Element.prototype.releasePointerCapture = function () {};

  window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  window.renderMathInElement = () => {};
  window.scrollTo = function () {};
  window.fetch = (u) => (/slate\/state/.test(String(u))
    ? Promise.resolve({ json: () => Promise.resolve({ pages: [] }) })
    : Promise.resolve({ json: () => Promise.resolve({ ok: true }) }));
  window.EventSource = function () {
    this.readyState = 1;
    this.close = function () {};
    this.addEventListener = function () {};
  };

  for (const f of ['typeface.js', 'macros.js', 'plane-core.js',
                   'ink-core.js', 'slate-core.js', 'board.js']) {
    try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
    catch (e) { fail(f + ': ' + e.message); }
  }
  return { window, doc: window.document, dom };
}

const { window: w, doc: d } = boot();

// --- 1. Send always comes back -------------------------------------------
// A surface of its own, with a hook that throws exactly as a board bug would.
function slateWith(onSending) {
  const root = d.createElement('div');
  const bar = d.createElement('div');
  d.body.appendChild(root);
  d.body.appendChild(bar);
  let btn = null;
  const slate = w.Slate.create({
    root: root, bar: bar, compact: true,
    stateUrl: '/slate/state', saveUrl: '/slate/save',
    onSending: function () { if (onSending) onSending(btn); },
  });
  btn = bar.querySelector('.sl-send');
  return { slate, btn, root, bar };
}

{
  let wasDisabled = null;
  const { btn } = slateWith(function (b) {
    wasDisabled = b && b.disabled;
    throw new Error('the host hook blew up');
  });
  btn ? ok('the test surface has a Send button') : fail('no Send button to press');
  let threw = null;
  try { btn.onclick(); } catch (e) { threw = e; }
  threw && /blew up/.test(threw.message)
    ? ok('a throw from onSending is not swallowed, so the board can report it')
    : fail('the onSending throw vanished');
  wasDisabled === true
    ? ok('and Send was disabled while the hook ran, so a second tap still cannot send twice')
    : fail('Send was not disabled during the hook');
  btn.disabled === false
    ? ok('but the button is enabled again, so the student can tap and retry')
    : fail('Send is stuck disabled — the lesson can no longer be sent');
}

{
  const { btn } = slateWith(function () {});
  const realFetch = w.fetch;
  w.fetch = (u) => {
    if (/slate\/state/.test(String(u))) {
      return Promise.resolve({ json: () => Promise.resolve({ pages: [] }) });
    }
    throw new Error('the wire is gone');
  };
  const realRaf = w.requestAnimationFrame;
  w.requestAnimationFrame = (fn) => fn();
  let threw = null;
  try { btn.onclick(); } catch (e) { threw = e; }
  w.requestAnimationFrame = realRaf;
  w.fetch = realFetch;
  threw && /wire is gone/.test(threw.message)
    ? ok('a throw in the send chain is not swallowed either')
    : fail('a send-chain throw vanished');
  btn.disabled === false
    ? ok('and that throw frees Send at once instead of waiting out the timer')
    : fail('a send-chain throw left Send disabled');
}

// --- 2. The board page reports what broke ---------------------------------
{
  const asked = [];
  w.fetch = (u, init) => {
    asked.push({ url: String(u), method: (init && init.method) || 'GET',
                 body: init && init.body ? JSON.parse(init.body) : null,
                 keepalive: !!(init && init.keepalive) });
    return Promise.resolve({ json: () => Promise.resolve({ ok: true }) });
  };
  const beacons = () => asked.filter((r) => r.url === '/client-error');

  w.dispatchEvent(new w.ErrorEvent('error', { message: 'boom',
    filename: 'https://board.test/static/x.js', lineno: 3, error: new w.Error('boom') }));
  w.dispatchEvent(new w.ErrorEvent('error', { message: 'boom',
    filename: 'https://board.test/static/x.js', lineno: 3 }));
  let got = beacons();
  got.length === 1 && got[0].body.page === 'board' && got[0].body.what === 'error'
    && got[0].body.msg === 'boom'
    && got[0].body.src === 'https://board.test/static/x.js:3'
    && typeof got[0].body.ua === 'string' && got[0].keepalive
    ? ok('an uncaught error is posted to /client-error once, with where it was')
    : fail('the board did not report an uncaught error (' + JSON.stringify(got) + ')');

  const img = d.createElement('img');
  img.setAttribute('src', '/static/gone.png');
  d.body.appendChild(img);
  img.dispatchEvent(new w.Event('error'));
  got = beacons();
  got.length === 2 && got[1].body.what === 'load' && /\/static\/gone\.png$/.test(got[1].body.src)
    ? ok('a resource that did not load is caught on its way down, by its URL')
    : fail('a resource load failure was not reported');

  const rej = new w.Event('unhandledrejection');
  rej.reason = new w.Error('nope');
  w.dispatchEvent(rej);
  got = beacons();
  got.length === 3 && got[2].body.what === 'rejection' && got[2].body.msg === 'nope'
    ? ok('an unhandled rejection is told too')
    : fail('an unhandled rejection was not reported');

  for (let i = 0; i < 20; i++) {
    w.dispatchEvent(new w.ErrorEvent('error', { message: 'storm ' + i,
                                                filename: 'y.js', lineno: i }));
  }
  beacons().length === 6
    ? ok('and a storm is cut short: a handful a minute, not twenty')
    : fail('the beacon storm cap is wrong (' + beacons().length + ' sent)');

  w.fetch = () => { throw new Error('no fetch here'); };
  let threw = null;
  try {
    w.dispatchEvent(new w.ErrorEvent('error', { message: 'later', filename: 'z.js', lineno: 1 }));
  } catch (e) { threw = e; }
  threw ? fail('the beacon threw when fetch was gone') : ok('telling never throws, even with no fetch');
}

console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                          : '\na crash on the board is visible, and Send recovers');
w.close();
process.exit(errors.length ? 1 : 0);