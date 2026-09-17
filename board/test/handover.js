// "FUCK THIS, YOU DO THIS STEP" — the tap that hands ONE step over.
//
// A coach card names the calls, the arguments and the order and lets you type
// it, and there was no way out of any one of them. The only escape was the aim
// chooser, which changes the WHOLE sitting to `build`: the way to get one step
// written for you was to stop being coached, and every card after it was
// written the new way.
//
// Asked for in these words: "in coach coding mode, I still want to be able to
// have a 'fuck this, you do this step' option."
//
// What is guarded here is where the button is and where it is NOT. It belongs
// on the step — the newest card — and nowhere else: a button on a step that has
// already been typed means nothing, and a button in a sitting whose tutor is
// already writing the code means less than nothing. jsdom, because all of that
// is a fact about what is on the glass.

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
window.fetch = (u, opt) => {
  posted.push({ url: String(u), body: opt && opt.body ? JSON.parse(opt.body) : null });
  if (/slate\/state/.test(String(u))) {
    return Promise.resolve({ json: () => Promise.resolve({ pages: [] }) });
  }
  return Promise.resolve({ json: () => Promise.resolve({ ok: true }) });
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
                 'slate-core.js', 'annotate.js', 'board.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
const es = window.__es;
if (!es) { console.log('FAIL board.js never opened a stream'); process.exit(1); }

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const t0 = Date.now() / 1000 - 3600;

// Three steps of a coached build, the third being the one in front of them.
const steps = [
  { id: '0001', kind: 'lesson', body: 'Step one: make the module.', mtime: t0 },
  { id: '0002', kind: 'lesson', body: 'Step two: name the route.', mtime: t0 + 60 },
  { id: '0003', kind: 'lesson', body: 'Step three: wire the clock.', mtime: t0 + 120 },
];

const frame = (aim, extra) => JSON.stringify(Object.assign({
  state: { course: 'Harness', session: 'lecture', aim: aim, aim_now: aim },
  cards: steps, turns: [], history: 0,
  agent: { agent: 'claude', state: 'listening' },
}, extra || {}));

const taps = () => doc.querySelectorAll('.card .hand-over');
const tapOn = (id) =>
  doc.querySelector('.card[data-card="' + id + '"] .hand-over');

(async () => {

// ------------------------------------------------ where the tap is, and is not
es.onmessage({ data: frame('coach') });
await sleep(60);

taps().length === 1
  ? ok('a coaching sitting offers the tap exactly once')
  : fail('the tap appeared ' + taps().length + ' times');
tapOn('0003')
  ? ok('and it is on the step they are looking at')
  : fail('the newest card has no tap on it');
!tapOn('0001') && !tapOn('0002')
  ? ok('steps already typed do not offer to be written')
  : fail('an old step offered to be handed over');

// ------------------------------------------------------- what the tap sends
posted.length = 0;
tapOn('0003').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(20);
const sent = posted.filter((p) => /\/handover$/.test(p.url));
sent.length === 1 && sent[0].body && sent[0].body.card === '0003'
  ? ok('tapping it names the card and nothing else')
  : fail('what went out was ' + JSON.stringify(sent));
tapOn('0003').disabled
  ? ok('and the control says so before the payload comes back')
  : fail('the tap stayed live, so it can be sent twice');

// -------------------------------------------- the sittings that do not get it
const noneFor = async (aim, why) => {
  es.onmessage({ data: frame(aim) });
  await sleep(60);
  taps().length === 0 ? ok(why) : fail('the tap showed up in a ' + aim + ' sitting');
};
await noneFor('build', 'a sitting whose tutor already writes the code has nothing to hand over');
await noneFor('teach', 'and a sitting being taught the mathematics is not offered it');

// A past lesson is read-only. Handing over a step of an evening that is already
// filed away is not a thing that can happen.
es.onmessage({ data: frame('coach', { archived: true }) });
await sleep(60);
taps().length === 0
  ? ok('a filed lesson offers nothing to hand over')
  : fail('a past lesson offered a step');

// And the transcript says what was done, in words rather than a bare tag.
es.onmessage({ data: frame('coach', { turns: [
  { id: 't0007', rev: 1, kind: 'text', t: t0 + 130, card: '0003',
    text: 'You write this step.', signal: 'handover' }] }) });
await sleep(60);
const chip = doc.querySelector('.mine[data-turn="t0007"] .signal');
chip && /handed this step over/.test(chip.textContent)
  ? ok('the transcript says the step was handed over')
  : fail('the turn carried no label: "' + (chip && chip.textContent) + '"');

console.log();
if (errors.length) { console.log(errors.length + ' FAILURES'); process.exit(1); }
console.log('one step goes over, and the sitting is still a coaching one');
})();
