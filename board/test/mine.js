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
const cardFor = (id) => doc.querySelector('.card[data-card="' + id + '"]');

(async () => {

// --------------------------------------------------- a verdict, in colour
es.onmessage({ data: frame([question], [ink]) });
await sleep(60);

// The newest unanswered answer stands on the writing surface rather than in the
// transcript, so the one asserted here is the one with a reply under it. Give
// it a reply of every kind in turn, and read BOTH halves back: what the reply
// says on the student's own answer, and what it says on the card itself.
//
// THE TWO HALVES USED TO DISAGREE, AND ONLY IN THE AMBER CASE. The answer took
// the verdict; the card took its band from its own KIND. So a reply that was
// neither right nor wrong painted the answer amber and the card grey, a finger's
// width apart. "If the user asks a question, or we're not really in a 'right or
// wrong' scenario, then the response should be highlighted with a yellow kind of
// band" -- so the card is painted from the verdict now, and these read as pairs.
const withCard = async (kind) => {
  const card = { id: '0002', kind: kind, body: 'a word about it', mtime: t0 + 120 };
  es.onmessage({ data: frame([question, card], [ink]) });
  await sleep(60);
  const n = mineFor('t0054');
  const c = cardFor('0002');
  return { answer: n ? (n.dataset.verdict || '') : '(the answer is not on the page)',
           card: c ? (c.dataset.verdict || '') : '(the card is not on the page)' };
};
const agree = async (kind, want, what) => {
  const got = await withCard(kind);
  got.answer === want && got.card === want
    ? ok(what)
    : fail('a ' + kind + ' card: the answer says "' + got.answer + '" and the '
           + 'card says "' + got.card + '", wanted "' + want + '" on both');
};

await agree('correct', 'correct',
  'a correct card paints the answer that earned it green — and paints itself');
await agree('wrong', 'wrong',
  'and a wrong card paints both of them red');
await agree('note', 'open',
  'and an aside — neither right nor wrong — paints both amber, which is the '
  + 'half the card used to get wrong: it went grey, from its kind');
await agree('review', 'open',
  'as does a review, which is the same kind of reply');

// AND A LESSON CARD REPLYING TO WORK THAT WAS HANDED IN IS A REPLY. It is the
// commonest one in a sitting that DOES the work — the student sends "it runs
// now", the turn reports what it found — and `REPLY_KIND` does not contain
// `lesson`, so in exactly the sittings where "we're not really in a
// right-or-wrong scenario" is the normal case there was no band at all.
await agree('lesson', 'open',
  'and a lesson card answering what was just sent is the reply, so it carries '
  + 'the amber band — the case a kind-keyed rule could not see');

// BUT NOT A LESSON CARD THAT IS TEACHING. A page tinted end to end says nothing
// at all, so the band belongs to the card that replied and not to everything
// downstream of an answer: 0003 is separated from the ink by the card that
// already answered it.
{
  es.onmessage({ data: frame(
    [question,
     { id: '0002', kind: 'note', body: 'why is q non-zero?', mtime: t0 + 120 },
     { id: '0003', kind: 'lesson', body: 'now, Chapter 5', mtime: t0 + 180 }],
    [ink]) });
  await sleep(60);
  const reply = cardFor('0002');
  const teaching = cardFor('0003');
  reply && reply.dataset.verdict === 'open'
  && teaching && !teaching.dataset.verdict
    ? ok('and the lesson card AFTER the one that replied is teaching, and stays '
         + 'plain — the reply is the first card after the answer, not every card '
         + 'that follows one')
    : fail('the band ran on past the reply: 0002 "'
           + (reply && reply.dataset.verdict) + '", 0003 "'
           + (teaching && teaching.dataset.verdict) + '"');
}

// And a lesson card with nothing handed in above it at all.
{
  const unanswered = { id: '0005', kind: 'question', title: 'Exercise 4.20',
                       body: 'and this one', mtime: t0 + 240 };
  es.onmessage({ data: frame(
    [question,
     { id: '0002', kind: 'note', body: 'why is q non-zero?', mtime: t0 + 120 },
     unanswered,
     { id: '0006', kind: 'lesson', body: 'some more reading', mtime: t0 + 300 }],
    [ink]) });
  await sleep(60);
  const c = cardFor('0006');
  c && !c.dataset.verdict
    ? ok('and teaching under a question nobody has answered yet is not a verdict '
         + 'on anything')
    : fail('a lesson card was read as a verdict with no answer above it: "'
           + (c && c.dataset.verdict) + '"');
}

// And a recap never is, wherever it falls: it is the reading of what already
// happened, and a recap that went amber because an answer preceded it is a page
// tinted for nothing.
{
  es.onmessage({ data: frame(
    [question, { id: '0002', kind: 'recap', body: 'where we are', mtime: t0 + 120 }],
    [ink]) });
  await sleep(60);
  const c = cardFor('0002');
  c && !c.dataset.verdict
    ? ok('and a recap is never a reply, however it falls')
    : fail('a recap took a verdict: "' + (c && c.dataset.verdict) + '"');
}

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

// ------------------------------------------- AMBER IS A TOKEN, NOT A GREY
//
// The band is `--ask` and the verdict outranks the kind, and both of those are
// in the stylesheet rather than in the page, because the card's colour is one
// custom property and jsdom resolves neither `var()` nor `color-mix()`. What is
// checkable here is that the rules exist and that they are in the order that
// makes the verdict win: same specificity, so the later one does.
{
  const sheet = fs.readFileSync(path.join(WEB, 'board.css'), 'utf8');
  const amber = sheet.indexOf('.card[data-verdict="open"]');
  const green = sheet.indexOf('.card[data-verdict="correct"]');
  const red = sheet.indexOf('.card[data-verdict="wrong"]');
  const kind = sheet.lastIndexOf('.card[data-kind="note"]     { --accent:');
  amber !== -1 && /\.card\[data-verdict="open"\]\s*{\s*--accent: var\(--ask\)/.test(sheet)
    ? ok('the open case is the amber token and not a grey')
    : fail('no rule paints an open verdict from --ask');
  green !== -1 && red !== -1 && kind !== -1 && amber > kind && green > kind && red > kind
    ? ok('and the verdict rules come after the kind rules, so the verdict wins')
    : fail('the kind still outranks the verdict in board.css');
  /\.card\[data-verdict\] \.body/.test(sheet)
    ? ok('and the band itself is keyed on the verdict')
    : fail('the panel is still keyed on the kind alone');
}

// --------------------------------- AND HOW MANY RIGHT IN A ROW, WHICH IS THE
// reward the colour was standing in for. "Dopamine for the user when they answer
// correctly": one right answer is a tick, and four in a row is a piece of work
// going well. The chip exists from the second one and a wrong answer resets it.
{
  const q = (n, t) => ({ id: n, kind: 'question', title: 'Ex ' + n, body: 'go',
                         mtime: t });
  const ans = (n, qid, t) => ({ id: n, rev: 1, kind: 'text', answers: qid, t: t,
                                text: 'my answer' });
  const yes = (n, t) => ({ id: n, kind: 'correct', body: 'that is it', mtime: t });
  es.onmessage({ data: frame(
    [q('0101', t0), yes('0102', t0 + 20),
     q('0103', t0 + 30), yes('0104', t0 + 50),
     q('0105', t0 + 60), yes('0106', t0 + 80),
     q('0107', t0 + 90), { id: '0108', kind: 'wrong', body: 'no', mtime: t0 + 110 },
     q('0109', t0 + 120), yes('0110', t0 + 140)],
    [ans('t0101', '0101', t0 + 10), ans('t0103', '0103', t0 + 40),
     ans('t0105', '0105', t0 + 70), ans('t0107', '0107', t0 + 100),
     ans('t0109', '0109', t0 + 130)]) });
  await sleep(60);
  const runOf = (id) => {
    const c = cardFor(id);
    return c ? (c.dataset.streak || '') : '(not on the page)';
  };
  const chip = (id) => {
    const c = cardFor(id);
    const n = c && c.querySelector('.streak');
    return n ? n.textContent : '';
  };
  runOf('0102') === '' && runOf('0104') === '2' && runOf('0106') === '3'
    ? ok('one right answer is a tick; the second says two in a row and the third '
         + 'says three')
    : fail('the run is miscounted: ' + runOf('0102') + ' ' + runOf('0104') + ' '
           + runOf('0106'));
  chip('0106') === '3 in a row'
    ? ok('and it says so in words, on the card where it happened')
    : fail('the streak chip is not on the card: "' + chip('0106') + '"');
  runOf('0110') === '' && runOf('0108') === ''
    ? ok('and a wrong answer resets it — the next right one starts again at one')
    : fail('the run survived a wrong answer: 0108 "' + runOf('0108') + '", 0110 "'
           + runOf('0110') + '"');
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

// ------------- WHAT WAS SENT STAYS WHERE IT WAS TYPED, AND A TAP CORRECTS IT
//
// "The typed prompt also disappears after I send it, unlike the written board
// when I send that." Sent ink stays where it was made -- a board per attempt,
// down the page, with the ink still on it -- and a sent sentence left the box
// empty and nothing else behind. So the typed half now keeps its answer in a
// rendered block directly above the box, which is what makes the two halves of
// this panel symmetrical, and the box goes back to holding only what has not
// been sent.
//
// The box used to open pre-filled with the sent answer, because the box was the
// only place a correction could be made. It is not any more, and that is the
// whole reason the restore moved out of the panel's paint and into the tap.
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
const said = doc.getElementById('said');
const saidText = doc.getElementById('said-text');
const sendOf = () => {
  for (let i = posted.length - 1; i >= 0; i--) {
    if (/\/say$/.test(posted[i].url)) return posted[i].body;
  }
  return null;
};

say.value === ''
  ? ok('the box opens empty on a question already answered by typing — it holds '
       + 'what has not been sent yet, and nothing else')
  : fail('the box opened pre-filled: "' + say.value + '"');
!said.hidden && /my first go/.test(saidText.textContent)
  ? ok('and the answer that WAS sent is above it, rendered, where it was typed')
  : fail('the sent answer is nowhere on the typed half: "'
         + saidText.textContent + '"');
said.dataset.state === 'sent'
  ? ok('and it says which of its two jobs it is doing, so the tap is offered')
  : fail('the block is not in its sent state: "' + said.dataset.state + '"');

// A tap hands it back to the box, and the box is then correcting THAT answer
// rather than answering beside it -- the typed counterpart of going back to a
// board and adding a line to the ink on it.
said.click();
await sleep(40);
say.value === 'my first go'
  ? ok('a tap on it loads it back into the box for correction')
  : fail('the tap did not hand the answer back: "' + say.value + '"');
doc.getElementById('send-type').click();

// ON THE FRAME AFTER THE SEND, with no payload back yet. That is the half of
// the report a round trip cannot cover: the box empties immediately, so if the
// block waited for the turn to come back there would be a moment -- the moment
// somebody is looking -- with the answer nowhere on the page.
!said.hidden && /my first go/.test(saidText.textContent) && say.value === ''
  ? ok('and the send empties the box and leaves the words above it on the same '
       + 'frame, rendered, with no round trip in between')
  : fail('the words left the glass on the send: box "' + say.value + '", block "'
         + saidText.textContent + '"');

await sleep(40);
(sendOf() || {}).turn === 't0057'
  ? ok('and correcting it revises that answer, in its place')
  : fail('a correction started a new answer: ' + JSON.stringify(sendOf()));

// Then a genuinely new answer, typed into the box the send emptied. With
// mathematics in it, because the next assertion is about the renderer.
const NEXT = 'so $\\gamma^2 = 2$ and the degree is 2';
say.value = NEXT;
say.dispatchEvent(new window.Event('input'));
doc.getElementById('send-type').click();
const shownOnSend = saidText.innerHTML;
await sleep(40);
(sendOf() || {}).turn === null
  ? ok('but the next thing typed is a new answer, and is kept')
  : fail('a second answer overwrote the first: ' + JSON.stringify(sendOf()));

// ONE RENDERER, OR THE BLOCK LIES. What it shows before and after the send is
// what the transcript shows once the turn comes back, because it is the same
// pair of calls -- `renderMarkdown` then `typeset`. Two renderers would differ
// on exactly the input somebody is squinting at.
es.onmessage({ data: frame([question, later],
                           [{ id: 't0057', rev: 1, kind: 'text', answers: '0009',
                              t: t0 + 560, text: 'my first go' },
                            { id: 't0061', rev: 1, kind: 'text', answers: '0009',
                              t: t0 + 600, text: NEXT }]) });
await sleep(60);
{
  const entry = mineFor('t0061');
  const inTranscript = entry && entry.querySelector('.text').innerHTML;
  inTranscript && inTranscript === shownOnSend
    ? ok('and what the block showed is character for character what the '
         + 'transcript shows, because one renderer made both')
    : fail('the block and the transcript disagree:\n   block      ' + shownOnSend
           + '\n   transcript ' + inTranscript);
  /\bmath-raw\b/.test(shownOnSend)
    ? ok('with the mathematics parked for KaTeX rather than escaped as prose')
    : fail('the block did not park the formula: ' + shownOnSend);
}

// ------------------------- and the two halves of the panel behave the same way
//
// "my typed response doesn't get saved on the appearance unlike previously
// writing boards." Going back to a question answered in ink gives the page of
// ink back; going back to one answered by typing has to give the words back too,
// and it no longer matters what happens to be in the box when you arrive --
// which is what used to gate it. The words come back ABOVE the box, and the box
// arrives empty, as it does on any other question.

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

/my first go/.test(saidText.textContent) === false
&& /the fixed field is Q/.test(saidText.textContent)
  ? ok('a box holding another question\'s words is no reason to refuse this one '
       + 'its answer back — and the answer shown is this question\'s, not the '
       + 'one before it')
  : fail('the answer to the question now open is not above the box: "'
         + saidText.textContent + '"');
say.value === ''
  ? ok('with the box itself empty, on this question as on every other')
  : fail('the box arrived holding something: "' + say.value + '"');

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
