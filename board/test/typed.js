// EVERY RESPONSE IS TYPED OUT, WHATEVER WROTE IT AND HOWEVER IT LANDED.
//
// Reported from a direction change in PSYCH-ASR, in two halves:
//
//   "when the response from the agent came back, it just showed up suddenly and
//    the next board, etc. was there before it, so I was left hanging for a bit.
//    We fixed this yesterday in the math tutoring, I believe. But looks like
//    that's not showing up here for some reason. The behavior where I see the
//    text start to show up character by character in a visually pleasing way, as
//    well as no next board showing up until the agent's response is rendered.
//    This behavior needs to be adopted in all responses, no matter what we're
//    doing or how we're operating (vibe code, coach code, math, etc.)"
//
// It had been fixed, and it was fixed for exactly one of the two ways a card
// lands. A card written ONCE was fresh, so it typed. A card written OVER was
// not: the reconcile keyed freshness on the card's identity alone, so a card
// that already existed had already been seen, and was rebuilt in place with its
// new contents painted whole.
//
// That is not an edge case. It is how every turn that DOES the work answers, and
// the assistant is told to answer that way: `board write` one sentence so the
// board is not blank, then several minutes of work, then `board write --over`
// with the report. So in a teaching sitting the effect worked and in a doing
// sitting it had never once run -- which is precisely the difference between
// "the math tutoring" and "PSYCH-ASR".
//
// The fix is the card's mtime in the stamp, which is the same thing `rev` is for
// a turn. What is asserted here is the behaviour, not the line: a response that
// replaces one is typed, and the next board waits for it.
//
// jsdom, because every assertion is about what a person sees on the glass.

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
window.fetch = (u) => (/slate\/state/.test(String(u))
  ? Promise.resolve({ json: () => Promise.resolve({ pages: [] }) })
  : new Promise(() => {}));
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
const t0 = Date.now() / 1000;

const nodeFor = (id) => doc.querySelector('[data-card="' + id + '"]');
const bodyOf = (id) => { const n = nodeFor(id); return n && n.querySelector('.body'); };
const soonOf = (id) => { const b = bodyOf(id); return b && b.querySelector('.tw-soon'); };

// A sitting that DOES the work, which is where this had never run. The opening
// card is the one sentence the turn writes before it starts, exactly as the
// briefing tells it to.
const OPENING = 'About to split the correction pass in two. Back shortly.';
const REPORT = 'The pass is split. The corrections reader now takes the log and '
             + 'writes one file per session, and the four typists agree on all '
             + 'but two turns. What is left is the tie-break rule, which is '
             + 'yours to choose.';

const frame = (cards, agent) => JSON.stringify({
  state: { course: 'PSYCH-ASR', session: 'lecture', chapter: 'cli',
           aim: 'build', stance: 'do', declared_stance: 'do' },
  cards: cards,
  turns: [],
  agent: agent || { agent: 'claude', state: 'listening', turns: 3 },
  waiting: null, history: 0,
});

const opening = { id: '0007', kind: 'lesson', title: '', body: OPENING,
                  mtime: t0 - 300 };
const report = { id: '0007', kind: 'lesson', title: '', body: REPORT,
                 mtime: t0 };
const question = { id: '0008', kind: 'question', title: 'the tie-break',
                   body: 'Which typist wins a tie, and why that one?',
                   mtime: t0 };

(async () => {

// The lesson as it stood while the turn ran: the opening sentence, nothing else.
es.onmessage({ data: frame([opening],
                           { agent: 'claude', state: 'working', turns: 3,
                             turn_started: t0 - 280 }) });
await sleep(60);

(bodyOf('0007') || {}).textContent === OPENING
  ? ok('the sentence a doing turn opens with is on the board')
  : fail('the opening card is not on the board: "'
         + ((bodyOf('0007') || {}).textContent || '') + '"');
!soonOf('0007')
  ? ok('and it is not typed, because it was already there when the page opened')
  : fail('the first paint typed out a lesson that was already written');

// ------------------------------------------------- and then the report lands
//
// Same card, same id, new contents -- `board write --over`. This is the payload
// that used to change the board from one sentence to four hundred words between
// two frames, with no typing and with the next board already under it.
es.onmessage({ data: frame([report, question],
                           { agent: 'claude', state: 'working', turns: 3,
                             turn_started: t0 - 280 }) });
await sleep(60);

{
  const body = bodyOf('0007');
  const soon = soonOf('0007');
  body && body.textContent.indexOf('The pass is split') === 0
    ? ok('a card written over shows its new contents')
    : fail('the overwrite did not reach the board');
  soon && soon.textContent.length
    ? ok('and it is TYPED -- the part not said yet is laid out and unpainted, '
         + 'which is the whole of the effect')
    : fail('a card written over appeared whole and instantly, which is the '
           + 'report this test exists for');
  const said = body.querySelector('.tw-said');
  said && said.textContent.length < REPORT.length
    ? ok('with only the part already said painted')
    : fail('everything is painted at once');
}

// ---------------------------------------- and the next board waits for it
//
// "no next board showing up until the agent's response is rendered". The
// question that came with the report opens a board to answer it on, and that
// board must not come down until the last character of the response has landed.
{
  const writer = doc.getElementById('writer');
  const qNode = nodeFor('0008');
  writer && writer.hidden
    ? ok('the next board has not opened -- a surface that was not already there '
         + 'does not appear while the response is still being written')
    : fail('the next board came down before the response had finished');
  qNode && !doc.querySelector('[data-slot^="0008"]')
    ? ok('and nothing is drawn in its place either, so the question is not '
         + 'answered by a photograph of an empty board')
    : fail('a dormant board was painted where the held surface belongs');
}

// The card is a fixed size from the first frame, so nothing under it moves while
// it fills in. That is what makes the hold above a hold rather than a jump.
const tall = nodeFor('0007').offsetHeight;

await sleep(2800);            // past TYPE_MIN and past this card's own time

{
  const body = bodyOf('0007');
  !body.querySelector('.tw-soon')
    ? ok('the typing finishes and takes its scaffolding out of the lesson')
    : fail('the card is still half painted');
  body.textContent === REPORT
    ? ok('and what is left is exactly what the tutor wrote')
    : fail('the card does not read as written: "' + body.textContent + '"');
  nodeFor('0007').offsetHeight === tall
    ? ok('and the card never changed height, so nothing under it was pushed')
    : fail('the card grew while it typed');
  const writer = doc.getElementById('writer');
  writer && !writer.hidden && writer.previousElementSibling === nodeFor('0008')
    ? ok('and now -- and only now -- the next board opens under the question')
    : fail('the board never arrived under the question it is for');
}

// ------------------------------------------------ and a heartbeat is not news
//
// The tutor's record changes every thirty seconds while it works, and the
// uncommitted count changes whenever a file does. Neither is a card, and putting
// the mtime in the stamp must not make either of them retype the lesson.
{
  es.onmessage({ data: frame([report, question],
                             { agent: 'claude', state: 'working', turns: 3,
                               turn_started: t0 - 280 }) });
  await sleep(60);
  !soonOf('0007') && !soonOf('0008')
    ? ok('a payload carrying no new writing retypes nothing')
    : fail('the lesson typed itself out again on a heartbeat');
}

console.log(errors.length ? '\n' + errors.length + ' FAILURES'
  : '\nevery response is typed, and the next board waits for it');
process.exit(errors.length ? 1 : 0);

})();
