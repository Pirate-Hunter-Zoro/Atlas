// THE STUDENT'S OWN ANSWER: WHAT COLOUR IT IS, AND WHETHER IT IS STILL THERE.
//
// Two reports from the same iPad, about the same half of the page — the half
// that holds what the person themselves put on the board.
//
//   "if I'm right in my response, put a nice green sidebar down the response as
//    it comes back. Red if I'm wrong. Yellow if it's not really a right/wrong
//    situation — like if we're vibe-coding or I ask a question."
//
//   "when I type a response and send it, I want to see my typed response
//    preserved — it disappears in the text box after I send it and disappears
//    once the tutor response comes in. Just like previous writing boards,
//    previous text prompts should be preserved too."
//
// The verdict existed and was painted on the tutor's card, which is not where
// anybody is looking: they are looking at their own answer. And the typing was
// not preserved because every typed answer revised the one before it — one
// question open for an evening collected three, hours apart, and the transcript
// kept the last. Ink never lost one: every attempt keeps a board of its own,
// which is the comparison the request makes.
//
// jsdom, because both assertions are about what is on the glass.

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

// Every request the page makes, so the send can be read back out of it.
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

const question = { id: '0001', kind: 'question', title: 'Exercise 4.10',
                   body: 'show gamma is algebraic', mtime: t0 };
const ink = { id: 't0054', rev: 1, kind: 'ink', answers: '0001', t: t0 + 60,
              page: 1, strokes: 67, png: '/answers/t0054-r1.png',
              ink: '/answers/t0054-r1.json' };

const frame = (cards, turns) => JSON.stringify({
  state: { course: 'Galois Theory', session: 'lecture' },
  cards: cards, turns: turns, history: 0,
  agent: { agent: 'claude', state: 'listening' },
});

const mineFor = (id) => doc.querySelector('.mine[data-turn="' + id + '"]');
const boardFor = (qid) => doc.querySelector('.board[data-board="' + qid + '"]');

(async () => {

// --------------------------------------------------- a verdict, in colour
es.onmessage({ data: frame([question], [ink]) });
await sleep(60);

// The newest unanswered answer stands on the writing surface rather than in the
// transcript, so the one asserted here is the one with a reply under it. Give
// it a reply of every kind in turn.
const withCard = async (kind) => {
  const card = { id: '0002', kind: kind, body: 'a word about it', mtime: t0 + 120 };
  es.onmessage({ data: frame([question, card], [ink]) });
  await sleep(60);
  const n = mineFor('t0054');
  return n ? (n.dataset.verdict || '') : '(the answer is not on the page)';
};

(await withCard('correct')) === 'correct'
  ? ok('a correct card paints the answer that earned it green')
  : fail('a correct card left the answer unpainted');

(await withCard('wrong')) === 'wrong'
  ? ok('and a wrong card paints it red')
  : fail('a wrong card left the answer unpainted');

(await withCard('note')) === 'open'
  ? ok('and an aside — neither right nor wrong — paints it amber')
  : fail('a note did not paint the answer amber');

(await withCard('review')) === 'open'
  ? ok('as does a review, which is the same kind of reply')
  : fail('a review did not paint the answer amber');

(await withCard('lesson')) === ''
  ? ok('teaching that stands on its own is not a verdict on anything')
  : fail('a lesson card was read as a verdict');

// The board carrying the same working says the same thing. It is what a person
// scrolls back to; the one-line receipt above it is not.
const bd = boardFor('0001');
if (!bd) {
  fail('the question kept no board to paint');
} else {
  (await withCard('wrong')) && bd.dataset.verdict === 'wrong'
    ? ok('and the board that holds the working is painted with it')
    : fail('the board was left unpainted: "' + bd.dataset.verdict + '"');
}

// ------------------------------------------------------- waiting is not amber
es.onmessage({ data: frame([question], [ink, { id: 't0055', rev: 1, kind: 'text',
                                               answers: '0001', t: t0 + 200,
                                               text: 'I get zero' }]) });
await sleep(60);
const waiting = mineFor('t0055');
waiting && !waiting.dataset.verdict
  ? ok('an answer with no reply yet is not painted at all — waiting is not a verdict')
  : fail('an unanswered turn was given a colour: "'
         + (waiting && waiting.dataset.verdict) + '"');

// And the colour arrives when the reply does, on a node that was already there.
es.onmessage({ data: frame([question, { id: '0003', kind: 'correct',
                                        body: 'yes', mtime: t0 + 260 }],
                           [ink, { id: 't0055', rev: 1, kind: 'text',
                                   answers: '0001', t: t0 + 200,
                                   text: 'I get zero' }]) });
await sleep(60);
(mineFor('t0055') || {}).dataset && mineFor('t0055').dataset.verdict === 'correct'
  ? ok('and it lands on the answer the moment the reply does')
  : fail('the verdict never reached an answer that was already on the page');

// ------------------------------------------- every typed answer is kept
const typed = (id, t, text) => ({ id: id, rev: 1, kind: 'text', answers: '0001',
                                  t: t, text: text });
es.onmessage({ data: frame(
  [question,
   { id: '0003', kind: 'note', body: 'not quite — why is q non-zero?', mtime: t0 + 260 },
   { id: '0004', kind: 'correct', body: 'that is it', mtime: t0 + 400 }],
  [typed('t0055', t0 + 200, 'because it evaluates to zero'),
   typed('t0056', t0 + 320, 'because the degrees multiply')]) });
await sleep(60);

const first = mineFor('t0055');
const second = mineFor('t0056');
first && /evaluates to zero/.test(first.textContent)
  ? ok('a typed answer is still on the page after the next one is sent')
  : fail('the earlier typed answer is gone');
second && /degrees multiply/.test(second.textContent)
  ? ok('and so is the one that followed it')
  : fail('the later typed answer is gone');
first && /answer 1 of 2/.test(first.textContent)
  ? ok('and each says which answer to that question it is')
  : fail('the answers are unlabelled: "' + (first && first.textContent) + '"');

// In the order they were given, under the feedback each was replying to — not
// stacked hours above it because they all name the same question card.
const seq = Array.prototype.map.call(
  doc.getElementById('cards').querySelectorAll('[data-card], [data-turn]'),
  (n) => n.dataset.card || n.dataset.turn);
seq.indexOf('t0055') > seq.indexOf('0001')
  && seq.indexOf('0003') > seq.indexOf('t0055')
  && seq.indexOf('t0056') > seq.indexOf('0003')
  ? ok('and they read in the order the evening happened in')
  : fail('the page reads out of order: ' + seq.join(' '));

// ------------------------------- a correction revises; a second answer does not
// The panel opens on the question, on its type half, because that is what the
// last answer was given with.
// A question of its own, so the panel arrives at it the way it arrives at a
// new question in a lesson: the box empties on the way in and the answer to
// THIS question is what comes back into it.
const later = { id: '0009', kind: 'question', title: 'Exercise 4.11',
                body: 'and the tower law', mtime: t0 + 500 };
es.onmessage({ data: frame([question, later],
                           [{ id: 't0057', rev: 1, kind: 'text', answers: '0009',
                              t: t0 + 560, text: 'my first go' }]) });
// Long enough for the new question to finish typing itself out: the writing
// surface is deliberately held shut until it has, so a board never arrives
// under a half-written card.
for (let i = 0; i < 60 && doc.getElementById('writer').hidden; i++) await sleep(50);
doc.getElementById('tab-type').click();
await sleep(40);

const say = doc.getElementById('saybox');
const sendOf = () => {
  for (let i = posted.length - 1; i >= 0; i--) {
    if (/\/say$/.test(posted[i].url)) return posted[i].body;
  }
  return null;
};

// Reopened for correction: the words come back, and sending them revises the
// answer they came from rather than landing beside it.
say.value === 'my first go'
  ? ok('reopening a question you typed an answer to puts the words back')
  : fail('the typed answer did not come back: "' + say.value + '"');
say.dispatchEvent(new window.Event('input'));
doc.getElementById('send-type').click();
await sleep(40);
(sendOf() || {}).turn === 't0057'
  ? ok('and correcting it revises that answer, in its place')
  : fail('a correction started a new answer: ' + JSON.stringify(sendOf()));

// Then a genuinely new answer, typed into the box the send emptied.
say.value = 'and here is the next thing I thought';
say.dispatchEvent(new window.Event('input'));
doc.getElementById('send-type').click();
await sleep(40);
(sendOf() || {}).turn === null
  ? ok('but the next thing typed is a new answer, and is kept')
  : fail('a second answer overwrote the first: ' + JSON.stringify(sendOf()));

// ------------------------- and the two halves of the panel behave the same way
//
// "my typed response doesn't get saved on the appearance unlike previously
// writing boards." Going back to a question answered in ink gives the page of
// ink back; going back to one answered by typing did not give the words back.
// The restore existed — `restoreTextAnswer` is written, named and commented as
// exactly this — so the defect was in WHEN it runs. Two gates: it was asked only
// while the type half happened to be showing, and it refused any box that was
// not empty, including one holding another question's words.

// A third question, answered by typing, reached with a box that is NOT empty:
// the box still holds the sentence typed into it for 0009 a moment ago.
const third = { id: '0011', kind: 'question', title: 'Exercise 4.12',
                body: 'and the fixed field', mtime: t0 + 700 };
say.value = 'still typing about the tower law';
say.dispatchEvent(new window.Event('input'));
es.onmessage({ data: frame([question, later, third],
                           [{ id: 't0057', rev: 1, kind: 'text', answers: '0009',
                              t: t0 + 560, text: 'my first go' },
                            { id: 't0060', rev: 1, kind: 'text', answers: '0011',
                              t: t0 + 760, text: 'the fixed field is Q' }]) });
for (let i = 0; i < 60 && doc.getElementById('writer').hidden; i++) await sleep(50);
await sleep(60);
doc.getElementById('tab-type').click();
await sleep(40);

say.value === 'the fixed field is Q'
  ? ok('a box holding another question\'s words is no reason to refuse this one '
       + 'its answer back')
  : fail('the answer to the question now open did not come back: "'
         + say.value + '"');

// And unsent typing of their own, on THIS question, still wins: that is what
// the guard is for, and it is the draft that says so rather than the box.
say.value = 'wait, it is Q(i)';
say.dispatchEvent(new window.Event('input'));
doc.getElementById('tab-write').click();
await sleep(40);
doc.getElementById('tab-type').click();
await sleep(40);
say.value === 'wait, it is Q(i)'
  ? ok('and typing they have not sent yet is never written over by the restore')
  : fail('unsent typing was replaced by the answer already sent: "'
         + say.value + '"');

console.log(errors.length
  ? errors.length + ' FAILURES'
  : 'the answer is theirs, coloured and kept');
process.exit(errors.length ? 1 : 0);
})();
