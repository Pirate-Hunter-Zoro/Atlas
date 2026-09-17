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

// ------------------------- AND WITH REDUCE MOTION ON, WHICH IS WHERE IT BROKE
//
// Reported after all of the above was shipped and believed: "the next board
// showed up over the yellow pulsing 'working on response' indicator, and then
// the AI response just all showed up at once between the boards."
//
// The hold and the animation are two different things and one branch treated
// them as one. With `prefers-reduced-motion: reduce` the card is painted whole
// -- which is right, the pacing is a flourish and they asked for less movement
// -- and that branch returned WITHOUT TAKING A HOLD. So the surface came down
// beside a card that had appeared in the same breath.
//
// And no suite saw it, because jsdom has no `matchMedia`: every test in this
// repository runs with the animation on. This one asks for it off, in its own
// window, which is the only honest way to assert the branch.
{
  const dom2 = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
    runScripts: 'outside-only', pretendToBeVisual: true,
    url: 'https://board.test/board',
  });
  const w2 = dom2.window;
  const d2 = w2.document;
  w2.HTMLCanvasElement.prototype.getContext = () =>
    new Proxy({}, { get: () => () => {}, set: () => true });
  w2.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
  Object.defineProperty(w2.HTMLElement.prototype, 'clientWidth', { get: () => 900 });
  Object.defineProperty(w2.HTMLElement.prototype, 'clientHeight', { get: () => 500 });
  w2.HTMLElement.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: 900, height: 120, right: 900, bottom: 120, x: 0, y: 0 };
  };
  w2.Element.prototype.scrollIntoView = function () {};
  w2.Element.prototype.setPointerCapture = function () {};
  w2.Element.prototype.releasePointerCapture = function () {};
  /* THE WHOLE POINT OF THIS WINDOW. */
  w2.matchMedia = (q) => ({ matches: /prefers-reduced-motion/.test(String(q)),
    media: String(q), addListener() {}, removeListener() {},
    addEventListener() {}, removeEventListener() {} });
  w2.fetch = (u) => (/slate\/state/.test(String(u))
    ? Promise.resolve({ json: () => Promise.resolve({ pages: [] }) })
    : new Promise(() => {}));
  w2.renderMathInElement = () => {};
  w2.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  w2.scrollTo = function () {};
  w2.EventSource = function () { w2.__es = this; this.readyState = 1;
    this.close = function () {}; this.addEventListener = function () {}; };
  for (const f of ['typeface.js', 'macros.js', 'gauge.js', 'plane-core.js',
                   'slate-core.js', 'annotate.js', 'board.js']) {
    w2.eval(fs.readFileSync(path.join(WEB, f), 'utf8'));
  }
  const es2 = w2.__es;
  const u0 = Date.now() / 1000 - 600;
  const asked = { id: '0001', kind: 'question', title: 'Exercise 1',
                  body: 'show it', mtime: u0 };
  const sent = { id: 't0001', rev: 1, kind: 'ink', answers: '0001', t: u0 + 60,
                 page: 1, strokes: 67, png: '/answers/t0001-r1.png',
                 ink: '/answers/t0001-r1.json' };
  const f2 = (cards) => JSON.stringify({
    state: { course: 'Galois Theory', session: 'lecture' },
    cards: cards, turns: [sent], history: 0,
    agent: { agent: 'claude', state: 'working', turns: 2, turn_started: u0 } });

  es2.onmessage({ data: f2([asked]) });
  await sleep(80);
  /* Where the surface sits, as an INDEX among the lesson's children. Not its
     previous sibling: the dormant board carrying the ink just sent legitimately
     appears above it on this very frame, so identity with what was there before
     is the wrong question. What is being asked is whether the surface has come
     down past the new question. */
  const at2 = (sel) => {
     const kids = d2.getElementById('cards').children;
     for (let i = 0; i < kids.length; i++) {
       if (sel === 'writer' ? kids[i].id === 'writer'
                            : kids[i].dataset.card === sel) return i;
     }
     return -1;
  };

  /* The reply and the next question in one payload, which is what a teaching
     turn sends. */
  const reply = { id: '0002', kind: 'note', body: 'a word about it '.repeat(30),
                  mtime: u0 + 120 };
  const nextQ = { id: '0003', kind: 'question', title: 'Exercise 2',
                  body: 'and now this', mtime: u0 + 121 };
  es2.onmessage({ data: f2([asked, reply, nextQ]) });
  await sleep(5);           /* the frame the records land on, before any rAF */

  d2.querySelector('[data-card="0002"] .body')
  && !/tw-soon/.test(d2.querySelector('[data-card="0002"] .body').innerHTML)
    ? ok('with Reduce Motion on the card is painted whole and at once, which is '
         + 'what was asked for — the pacing is the flourish, not the hold')
    : fail('the card is being animated for somebody who asked for less movement');

  at2('writer') < at2('0003') && at2('0003') !== -1
    ? ok('AND THE SURFACE HAS NOT COME DOWN under the new question on that '
         + 'frame, because the hold is taken whether or not there is an '
         + 'animation to wait for')
    : fail('the next board arrived in the same breath as the answer, which is '
           + 'the reported glitch: the hold was the animation');

  /* AND IT LETS GO. Asserted on the receipt rather than on the geometry: where
     the surface finally lands is the ordinary placement rule -- the end of the
     run it belongs to, which depends on which board page is live -- and that is
     `test/link.js`'s subject. What is this file's subject is that the hold is a
     hold and not a state: it is taken, and then it is over. */
  !d2.getElementById('sent').hidden
  && /arriving/.test(d2.getElementById('sent-text').textContent)
    ? ok('and the receipt says the answer is ARRIVING while it is held, which is '
         + 'the pulse staying up until there is something to read')
    : fail('nothing says the answer is on its way: "'
           + d2.getElementById('sent-text').textContent + '"');
  await sleep(500);
  d2.getElementById('sent').hidden
    ? ok('and lets go a moment later, so nothing is held for longer than the '
         + 'order requires')
    : fail('the receipt is still up after the answer landed: "'
           + d2.getElementById('sent-text').textContent + '"');
}

// ------------------------------------------- and a slug is not a title
//
// `board write` derives a card's filename from its title, so a tutor passing the
// slug where the title goes gets it drawn across the top of the card. Reported
// as `LESSON not-for-every-i-for-one-i-and-that-is-the-whole-fix` — "What an
// eyesore." It stays in the front matter, where it names the file; it is not
// drawn as a sentence somebody wrote for a reader.
{
  const slugged = { id: '0009', kind: 'lesson',
                    title: 'not-for-every-i-for-one-i-and-that-is-the-whole-fix',
                    body: 'The fix is one index.', mtime: t0 - 10 };
  const titled = { id: '0010', kind: 'lesson', title: 'Well-ordering, in one line',
                   body: 'Every non-empty subset has a least element.', mtime: t0 - 9 };
  es.onmessage({ data: frame([slugged, titled, report, question],
                             { agent: 'claude', state: 'listening', turns: 4 }) });
  await sleep(80);
  const sl = nodeFor('0009');
  sl && !sl.querySelector('.card-title')
    ? ok('a slug is not drawn as a title')
    : fail('the filename is on the glass: "'
           + (sl && sl.querySelector('.card-title').textContent) + '"');
  sl && !sl.querySelector('.card-head')
    ? ok('and a lesson card whose only title was a slug loses the whole head '
         + 'with it, kind label and all')
    : fail('the head is still there with nothing in it worth reading');
  const ti = nodeFor('0010');
  ti && ti.querySelector('.card-title')
     && /Well-ordering/.test(ti.querySelector('.card-title').textContent)
    ? ok('while a title a person wrote is drawn, hyphen and all')
    : fail('a real title was mistaken for a slug and thrown away');
}

console.log(errors.length ? '\n' + errors.length + ' FAILURES'
  : '\nevery response is typed, and the next board waits for it');
process.exit(errors.length ? 1 : 0);

})();
