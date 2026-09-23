// An exercise is a chain of boards, and every one of them stays.
//
// Reported from a Galois sitting, in these words: "For one exercise/question, I
// write down one thing, get feedback on it, and then get another board with all
// my prior work on it which is great, but the previous board for this same
// question that I have not yet completed doesn't persist... I want ALL boards to
// persist and to operate independently of each other."
//
// The board that "appeared" under the feedback was not another board. It was the
// same one, slid down the run to sit under the newest card — a question had
// exactly one board, so there was never a second one to keep. Only the last
// board of a finished question survived into the rest of the lesson, which is
// exactly what was described.
//
// So a question is a chain: one board per attempt. A board is frozen where it
// is as soon as what it holds has been handed in AND the tutor has written
// something since — both halves, or pressing Send to check your working would
// cut a board, and so would a hint about working nobody has sent. The next
// attempt opens on a COPY, which is what makes "all my prior work is on it" and
// "independently of each other" true at the same time.
//
// jsdom, because this is about what is actually in the document and how many
// pages the surface has.

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
Object.defineProperty(window.HTMLElement.prototype, 'scrollHeight', { get: () => 4000 });
window.HTMLElement.prototype.getBoundingClientRect = function () {
  return { left: 0, top: 0, width: 900, height: 120, right: 900, bottom: 120, x: 0, y: 0 };
};
window.Element.prototype.scrollIntoView = function () {};
window.Element.prototype.setPointerCapture = function () {};
window.Element.prototype.releasePointerCapture = function () {};
// The frozen ink of an answer is a real file, served the way the board serves
// it: `live/answers/<turn>.json`, written once beside the picture and never
// touched again. A past board is DRAWN from it, so a harness that cannot answer
// for it cannot see what a past board looks like.
const frozen = {};
window.fetch = (u) => {
  const url = String(u);
  if (/slate\/state/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve({ pages: [] }) });
  }
  if (frozen[url]) {
    return Promise.resolve({ json: () => Promise.resolve(frozen[url]) });
  }
  return new Promise(() => {});
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

// PREVIOUS SITTINGS ON THIS CHAPTER, STILL IN LOCALSTORAGE.
//
// Cards are numbered from 0001 within a sitting, so yesterday's keys are also
// today's keys, and a mapping keyed by chapter alone hands them straight back.
// That is the second half of the report, in two parts. A record for an attempt
// this sitting never reached paints a board above the live one on a page the
// surface does not hold -- an empty box: "the last board shows up but it's a
// page I can't write on, and right underneath it a NEW new board". And a record
// nothing on the screen names can own a page number this sitting is about to
// use, so a board is found sharing a sheet the moment it opens and is copied off
// it again: one tap, two boards holding the same strokes. On disk that was pages
// 68 and 69, the same 114 strokes, 1.2 s apart.
//
// Every page number this sitting reaches is seeded as owned, and `0002#1` is the
// phantom attempt. Both keys are written: the chapter-wide one every browser
// already has, and a named sitting that is not this one. Seeded before the
// scripts load, because load is the only time the board reads this -- a stale
// record is a new session's problem, not a mid-lesson edit.
const STALE = JSON.stringify({
  '0001#0': { p: 1, a: '0001' }, '0001#1': { p: 2, a: '0001' },
  '0002#0': { p: 3, a: '0002' }, '0002#1': { p: 4, a: '0002' },
  '0009#0': { p: 5, a: '0009' },
});
window.localStorage.setItem('board.pages.n:Galois Theory:-', STALE);
window.localStorage.setItem('board.pages.n:Galois Theory:-:2026-02-10 19:00', STALE);
// And a sitting on ANOTHER chapter, which is nobody's business here: a second
// tab can be open on it, and a sweep that took it would empty a board in use.
window.localStorage.setItem('board.pages.n:Galois Theory:Ch 2:2026-02-10 19:00',
                            JSON.stringify({ '0001#0': { p: 7, a: '0001' } }));

for (const f of ['typeface.js', 'macros.js', 'gauge.js', 'plane-core.js', 'slate-core.js', 'annotate.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
const realCreate = window.Slate && window.Slate.create;
if (realCreate) {
  window.Slate.create = function (opts) {
    const api = realCreate(opts);
    window.__slate = api;
    return api;
  };
}
try { window.eval(fs.readFileSync(path.join(WEB, 'board.js'), 'utf8')); }
catch (e) { fail('board.js: ' + e.message); }

const es = window.__es;
if (!es) { console.log('FAIL board.js never opened a stream'); process.exit(1); }

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const t0 = 1788000000;
const card = (id, kind, title, n) =>
  ({ id, kind, title, body: 'the ' + title + ' body', mtime: t0 + n * 100 });
const writer = () => doc.getElementById('writer');
const boards = () => Array.from(doc.querySelectorAll('[data-board="0001"]'));
// One stroke, standing in for a hand: what matters here is that the page has ink
// on it and that the ink is not shared with another page.
const ink = (n) => ({ c: '#eee', w: 3, pts: [[10 + n, 10 + n], [90 + n, 90 + n]] });

// The record of which sheet each board is on, as a reload of THIS sitting will
// read it, and every sheet the surface is actually holding. A page no record
// names is a page nothing can ever open again.
//
// The key carries the sitting, so what is read back is only what this sitting
// wrote: a record from another evening cannot make a stranded page look owned.
const OPENED = '2026-02-11 19:00';
const PAGES_KEY = 'board.pages.n:Galois Theory:-:' + OPENED;
const records = () => {
  try { return JSON.parse(window.localStorage.getItem(PAGES_KEY) || '{}'); }
  catch (e) { return {}; }
};
const owned = () => Object.keys(records()).map((k) => records()[k].p);
// Walked to the highest number the surface holds rather than to a fixed ceiling:
// the real sitting this came from was on page 69, and a check that stops
// counting reports no orphans instead of failing.
const pagesHeld = () => {
  const out = [];
  for (let n = 1; n <= window.__slate.lastPage(); n++) {
    if (window.__slate.hasPage(n)) out.push(n);
  }
  return out;
};

// The pen goes back on the glass for each of these, and comes off again: a
// synthetic pointerdown with no lift leaves the surface believing a hand is on
// it -- and the board will not move a page under a hand, nor repaint the lesson
// under one, which is what keeps a payload from landing mid-stroke.
const lift = () => {
  const ev = new window.Event('pointerup', { bubbles: true, cancelable: true });
  Object.assign(ev, { pointerId: 91, pointerType: 'pen', pressure: 0,
                      clientX: 200, clientY: 200, isPrimary: true });
  const sheet = doc.querySelector('#writer canvas.sl-sheet');
  if (sheet) sheet.dispatchEvent(ev);
};

// The lesson: one exercise, worked over several attempts.
const lesson = (cards, turns) => JSON.stringify({
  state: { course: 'Galois Theory', session: 'lecture', mode: 'math',
           opened: OPENED },
  cards, turns: turns || [], history: 0,
});
const q1 = card('0001', 'question', 'Exercise 1.3', 1);

(async () => {

// ------------------------------------------------------------ the first board
es.onmessage({ data: lesson([q1]) });
await sleep(40);

const slate = window.__slate;
slate ? ok('the surface is reachable') : fail('no slate instance was captured');

!writer().hidden
  ? ok('a question opens a board to answer it on')
  : fail('the question has nowhere to be answered');
boards().length === 0
  ? ok('and it is the live one, so there is no picture of it as well')
  : fail('the live board is also being shown as a photograph of itself');

// ------------------------------- and last night's records are not this sitting's
//
// The seeded mapping says question 0001 has two attempts and is on pages 1 and
// 2, and that a question 0002 nobody here has asked owns two more. None of it
// is about this evening. Read back, it puts a board on the screen for an attempt
// that does not exist, on a page the surface does not hold -- which draws as an
// empty box above the live one.
Object.keys(records()).length === 1 && records()['0001#0']
  ? ok('a previous sitting on this chapter leaves no boards in this one')
  : fail('last night\'s records came back under tonight\'s card numbers: '
         + Object.keys(records()).sort().join(', '));
doc.querySelectorAll('[data-slot]').length <= 1
  ? ok('so the question has one board and not a phantom above it')
  : fail('a second board was painted for an attempt this sitting never reached');
!window.localStorage.getItem('board.pages.n:Galois Theory:-')
  && !window.localStorage.getItem('board.pages.n:Galois Theory:-:2026-02-10 19:00')
  ? ok('and the sittings this chapter is finished with are dropped, not kept '
       + 'against a card number that will come round again')
  : fail('a mapping no sitting will ever read again is still in the store');
window.localStorage.getItem('board.pages.n:Galois Theory:Ch 2:2026-02-10 19:00')
  ? ok('while another chapter, which a second tab may be sitting on, is left '
       + 'alone')
  : fail('the sweep took a mapping that is not this chapter\'s to take');

// Something is written on it.
slate.load({ w: 1130, h: 1514, strokes: [ink(1)] });
const firstPage = slate.at();        // its number, which is what a turn records

// ------------------------------------- sending, on its own, does not end it
es.onmessage({ data: lesson([q1], [
  { id: 't0001', rev: 1, kind: 'ink', answers: '0001', t: t0 + 150, page: firstPage,
    strokes: 1, png: '/answers/t0001-r1.png', ink: '/answers/t0001-r1.json' },
]) });
await sleep(40);

boards().length === 0 && slate.pages() === 1
  ? ok('handing it in does not cut a new board — Send is also how you check '
       + 'your working, and it must not fork the page under your hand')
  : fail('a send on its own started a second board (' + boards().length
         + ' pictures, ' + slate.pages() + ' pages)');

// --------------------------------- the tutor answers, and the attempt is over
const fb = card('0002', 'note', 'the third line does not follow', 2);
es.onmessage({ data: lesson([q1, fb], [
  { id: 't0001', rev: 1, kind: 'ink', answers: '0001', t: t0 + 150, page: firstPage,
    strokes: 1, png: '/answers/t0001-r1.png', ink: '/answers/t0001-r1.json' },
]) });
await sleep(40);

const kept = boards();
kept.length === 1
  ? ok('the board that was answered is still on the page, as a board')
  : fail('the previous board for this question did not persist (' + kept.length
         + ' of them) — which is the whole report');
kept.length === 1 && doc.querySelector('[data-card="0001"]').nextElementSibling === kept[0]
  ? ok('and it is still where it was written, under the question')
  : fail('the kept board moved somewhere other than where it was written');

// AND THE REPLY IS WRITTEN ABOVE IT, NOT BELOW IT.
//
// "no next board showing up until the agent's response is rendered." The reply
// types out in the place it will keep -- above the board the next attempt is
// made on -- so the board is where it always was and the last character moves
// nothing. Holding the surface in place while the card typed BELOW it is what
// the previous four attempts at this did, and a card typing under a full-height
// board is a card nobody sees until the board moves off it.
doc.querySelector('[data-card="0002"] .body.typing')
  ? ok('the reply is being typed out')
  : fail('the reply landed whole, with no typing at all');
doc.querySelector('[data-card="0002"]').nextElementSibling === writer()
  ? ok('and it is above the live surface while it is written, where the reader '
       + 'can watch it arrive')
  : fail('the reply is not above the surface, so it types out underneath it');

await sleep(900);                       // past this card's own typing time

doc.querySelector('[data-card="0002"]').nextElementSibling === writer()
  ? ok('and the last character moves nothing: the next attempt is still live '
       + 'under the feedback it answers')
  : fail('the live surface is not under the tutor\'s reply');

slate.pages() === 2
  ? ok('the next attempt is a page of its own')
  : fail('the next attempt did not get its own page (' + slate.pages() + ')');
slate.inkOn(2) === 1 && slate.at() === 2
  ? ok('opened on a copy, so everything written so far is still under the pen')
  : fail('the new board came up blank, losing the working it should carry '
         + '(page ' + slate.at() + ', ' + slate.inkOn(2) + ' strokes)');

// ------------------------------------------------------------- independently
slate.load({ w: 1130, h: 1514, strokes: [ink(2), ink(3)] });
await sleep(20);
slate.inkOn(1) === 1 && slate.inkOn(2) === 2
  ? ok('and writing on it leaves the board above exactly as it was')
  : fail('the two boards are one sheet: writing on the later one changed the '
         + 'earlier (' + slate.inkOn(1) + ' and ' + slate.inkOn(2) + ' strokes)');

// A second reply with nothing handed in since does NOT cut a third board: it is
// the answer to an attempt that ends it, not any card at all.
es.onmessage({ data: lesson([q1, fb, card('0003', 'note', 'and check the sign', 3)], [
  { id: 't0001', rev: 1, kind: 'ink', answers: '0001', t: t0 + 150, page: firstPage,
    strokes: 1, png: '/answers/t0001-r1.png', ink: '/answers/t0001-r1.json' },
]) });
await sleep(40);
boards().length === 1 && slate.pages() === 2
  ? ok('a second remark about working nobody has re-sent cuts nothing')
  : fail('every card the tutor writes is starting a new board');

// ------------------------------------------------- and the chain keeps going
const run3 = [q1, fb, card('0003', 'note', 'and check the sign', 3),
              card('0004', 'note', 'nearly — the sign on the second term', 4)];
const sent2 = [{ id: 't0001', rev: 2, kind: 'ink', answers: '0001', t: t0 + 350,
                 page: 2, strokes: 2, png: '/answers/t0001-r2.png',
                 ink: '/answers/t0001-r2.json' }];
es.onmessage({ data: lesson(run3, sent2) });
await sleep(40);

boards().length === 2
  ? ok('a second attempt answered leaves a second board behind it')
  : fail('the chain stopped at one (' + boards().length + ' kept)');
slate.pages() === 3 && slate.inkOn(3) === 2
  ? ok('and the third attempt opens on a copy of the second')
  : fail('the third attempt did not carry the working forward ('
         + slate.pages() + ' pages, ' + slate.inkOn(3) + ' strokes on the last)');

// Every board in the chain says which attempt it is, so two pictures of similar
// working are not two mysteries.
const labelled = boards().filter((b) =>
  /attempt \d+ of \d+/.test(b.querySelector('.board-hint').textContent));
labelled.length === boards().length
  ? ok('each board says which attempt it is')
  : fail('the boards in a chain are captioned identically');

// Getting it right closes the panel, and every board in the chain stays: the
// picture of an answer is a record, and what was asked for is somewhere to
// carry on working.
es.onmessage({ data: lesson(run3.concat([card('0005', 'correct', 'that is the proof', 5)]),
                            sent2) });
await sleep(40);
writer().hidden && boards().length === 3
  ? ok('and finishing the exercise keeps all three, panel shut')
  : fail('marking it right lost boards (' + boards().length + ' kept, panel '
         + (writer().hidden ? 'shut' : 'open') + ')');
es.onmessage({ data: lesson(run3, sent2) });
await sleep(40);

// ------------------------------------------ and any of them can be written on
{
  const first = boards()[0];
  first.dispatchEvent(new window.MouseEvent('pointerdown', { bubbles: true }));
  await sleep(40);
  !writer().hidden && slate.at() === 1
    ? ok('touching an earlier attempt opens the real surface on that page')
    : fail('an earlier board cannot be written on (page ' + slate.at() + ')');
  doc.querySelector('[data-card="0001"]').nextElementSibling === writer()
    ? ok('and the surface goes where that board was, not to the end of the run')
    : fail('the surface opened somewhere other than the board that was touched');
  boards().length === 2
    ? ok('while the attempts it was not opened on stay where they are')
    : fail('opening one board disturbed the others (' + boards().length + ')');
  lift();
}

// -------------------------------------- a follow-up question is a blank board
{
  // What was reported the evening the chain shipped: "my writing didn't get
  // saved when a new board came up - same question". Nothing was lost -- the
  // working was on the board above, 180 strokes of it, and still is. But the
  // tutor's follow-up was a QUESTION card, and a question card is a new
  // question, and a new question gets a board of its own, which is blank.
  //
  // That is right for a new exercise and wrong three cards into one. The board
  // cannot tell those apart, and guessing would be worse than asking: a new
  // exercise opened on a copy is somebody else's proof under your pen, and every
  // board after it carries every stroke of the evening. So the offer is made and
  // the person decides.
  const followUp = card('0002', 'question', 'contrapositive or contradiction?', 6);
  es.onmessage({ data: lesson(run3.concat([followUp]), sent2) });
  await sleep(40);

  const carry = doc.getElementById('carry');
  !carry.hidden
    ? ok('a blank board with working behind it offers to carry it over')
    : fail('a follow-up question lands on a blank sheet with no way back to the '
           + 'proof it is asking about');
  /question 0001/.test(carry.textContent)
    ? ok('and says which board it would come from')
    : fail('"carry over" with no "from where": ' + carry.textContent);

  const before = slate.pages();
  const held = slate.at();             // the sheet this board was dealt
  const already = slate.inkOn(slate.at());
  already === 0
    ? ok('the new board really is blank until it is asked for')
    : fail('the follow-up board came up with ' + already
           + ' strokes on it already');

  // NOT UNDER A PEN THAT IS DOWN.
  //
  // The fill replaces what a page holds where it lies, and `clone` decides the
  // page is free by counting COMMITTED strokes -- a stroke still being drawn is
  // not one of them. So the carry waits, and it has to come back: the tap is all
  // there is, and a pen lift the sheet never saw would otherwise leave the
  // button dead for the rest of the evening.
  {
    const down = new window.Event('pointerdown', { bubbles: true, cancelable: true });
    Object.assign(down, { pointerId: 91, pointerType: 'pen', pressure: 0.5,
                          clientX: 200, clientY: 200, isPrimary: true });
    doc.querySelector('#writer canvas.sl-sheet').dispatchEvent(down);
    slate.writing()
      ? ok('a nib on the glass is a hand at work')
      : fail('the surface does not know the pen is down');
    carry.onclick();
    await sleep(40);
    slate.inkOn(slate.at()) === 0 && slate.pages() === before
      ? ok('and the carry waits rather than replacing a page mid-word')
      : fail('the working landed under a pen that was still writing');
    !doc.getElementById('carry').hidden
      ? ok('with the offer still standing, so the tap can be made again')
      : fail('the carry was refused and the offer withdrawn, so there is no way '
             + 'to ask for it again');
    lift();
    // The nib touching down and lifting again leaves a dot behind, which is a
    // board with something on it and no longer one the offer is made over. Back
    // to the blank sheet the tap was made on.
    slate.load({ w: 1130, h: 1514, strokes: [] });
    await sleep(20);
  }

  carry.onclick();
  await sleep(40);
  // "A copy, not a move" was read off the page COUNT, and the count does not
  // grow: the copy lands on the sheet this board was already holding. What that
  // proxy stood for is the three assertions below it -- the working is under the
  // pen, the board it came from still has it, and the offer withdraws.
  //
  // The count is what the report was made of: "the last board shows up but it's
  // a page I can't write on, and right underneath it a NEW new board". The sheet
  // the board opened on was abandoned where it lay, and `fresh` hands back only
  // the TRAILING blank, so nothing could reach it again.
  slate.pages() === before
    ? ok('and the carry cuts no sheet: the working fills the page this board '
         + 'was already holding')
    : fail('the carry cut a sheet (' + before + ' -> ' + slate.pages()
           + ' pages), abandoning the one the board opened on');
  const stranded = pagesHeld().filter((n) => owned().indexOf(n) === -1);
  stranded.length === 0
    ? ok('and every page the surface holds is a board somebody can open')
    : fail('pages no record names, so nothing reaches them again: '
           + stranded.join(', '));
  slate.at() === held
    ? ok('and the pen stays on the sheet the board was dealt')
    : fail('the board moved off the page it opened on (' + held + ' -> '
           + slate.at() + '), leaving it behind');
  // ONE TAP, ONE COPY. Both numbers this sitting could reach are owned by a
  // record from another evening in the seed at the top of this file -- the sheet
  // the board is holding and the one a cut would mint. Neither is read, so
  // neither collides, and nothing is copied a second time.
  Object.keys(records()).filter((k) => records()[k].p === slate.at()).length === 1
    ? ok('and exactly one board names the page the working is on')
    : fail('two boards name the carried page, so the next render copies it '
           + 'again: ' + Object.keys(records()).sort().join(', '));
  slate.inkOn(slate.at()) === 2
    ? ok('and the working is under the pen')
    : fail('the carried board is empty (' + slate.inkOn(slate.at()) + ' strokes)');
  slate.inkOn(3) === 2
    ? ok('while the board it came from is untouched')
    : fail('carrying the working over took it away from where it was');
  doc.getElementById('carry').hidden
    ? ok('and the offer goes once there is something on the board')
    : fail('the offer is still standing over somebody\'s working, where taking '
           + 'it would replace it');
  // A COPY, WHICH IS WHAT "INDEPENDENTLY OF EACH OTHER" MEANS. The count no
  // longer says so -- the fill cuts no sheet -- and a source left with its ink
  // would also be satisfied by two boards sharing one stroke list. Writing on
  // the carried page is the only thing that tells them apart.
  slate.load({ w: 1130, h: 1514, strokes: [ink(4), ink(5), ink(6)] });
  await sleep(20);
  slate.inkOn(3) === 2 && slate.inkOn(slate.at()) === 3
    ? ok('and writing on the carried working leaves the board it came from '
         + 'exactly as it was')
    : fail('the carry aliased the strokes: the two boards are one sheet ('
           + slate.inkOn(3) + ' and ' + slate.inkOn(slate.at()) + ' strokes)');
}

// ------------------------------------------------- and the record survives it
{
  const map = records();
  const mine = Object.keys(map).filter((k) => k.indexOf('0001#') === 0).sort();
  mine.length === 3
    ? ok('all three boards are written down, so a reload finds them again')
    : fail('the chain is not persisted (' + mine.join(', ') + ')');
  const pages = mine.map((k) => map[k].p);
  new Set(pages).size === pages.length
    ? ok('each on a page of its own')
    : fail('two boards are filed onto one page: ' + pages.join(', '));
  mine.every((k) => !!map[k].a)
    ? ok('each remembering the card it sits under')
    : fail('a board does not know where it goes, so a reload cannot place it');
}

// ------------------------- a handed-in answer is not a picture of a live page
//
// Reported from the board, twice, in different words: "my writing from one
// section is wrong and came from a later section" and then "the very latest few
// board recordings are just repeats of my earliest".
//
// A dormant board was a picture of a SLATE PAGE, taken now -- and a slate page
// is live: it gets written on again, cleared, cloned, reused. Measured on the
// real lesson: the answer to one question was handed in off page 7 with 279
// strokes and page 7 now holds one; another came off page 9 with 279 and page 9
// holds a different 228. Every frozen answer was correct and distinct the whole
// time. The boards were pointing at a moving target.
const mapping = records;

{
  const q9 = card('0009', 'question', 'Exercise 3.4', 9);
  // Handed in off the board's own page, with three strokes on it.
  es.onmessage({ data: lesson([q1, q9], []) });
  await sleep(40);
  const p9 = mapping()['0009#0'] ? mapping()['0009#0'].p : slate.at();
  slate.go(p9);
  slate.load({ w: 1130, h: 1514, strokes: [ink(1), ink(2), ink(3)] });
  const sent = { id: 't0009', rev: 1, kind: 'ink', answers: '0009', t: t0 + 900,
                 page: p9, strokes: 3,
                 png: '/answers/t0009-r1.png', ink: '/answers/t0009-r1.json' };
  frozen['/answers/t0009-r1.json'] =
    { w: 1130, h: 1514, strokes: [ink(1), ink(2), ink(3)] };
  es.onmessage({ data: lesson([q1, q9], [sent]) });
  await sleep(40);
  lift();

  // ...and then that sheet is reused, leaving one stroke on it. The mapping is
  // perfectly healthy -- the board points where the record says the answer came
  // from -- and the sheet simply is not that answer any more.
  slate.go(p9);
  slate.load({ w: 1130, h: 1514, strokes: [ink(7)] });
  const q11 = card('0011', 'question', 'Exercise 3.6', 11);
  es.onmessage({ data: lesson([q1, q9, q11], [sent]) });
  await sleep(60);
  lift();

  const slot = doc.querySelector('[data-slot^="0009"]');
  if (!slot) {
    fail('question 0009 has no board at all');
  } else {
    const shot = slot.querySelector('.board-shot');
    const src = (shot && shot.getAttribute('src')) || '';
    /^data:image\/png/.test(src)
      ? ok('a board whose page has been reused shows the answer that was handed '
           + 'in, which cannot move')
      : fail('the board shows ' + src + ', so it is showing somebody else\'s writing');
    // And it is DRAWN, not the answer's own PNG. That file is written for a
    // different reader -- always dark ink on white, cropped to the writing --
    // and dropped into the run of boards it reads as a white sheet among black
    // ones. "The color is inverted", from the iPad, mid-proof.
    src !== '/answers/t0009-r1.png'
      ? ok('drawn by the slate, on the paper in hand, like every other board')
      : fail('the board shows the answer PNG, which is dark ink on white however '
             + 'dark the surface is: an inverted board in a run of black ones');
    /^.*handed in/.test(slot.querySelector('.board-hint').textContent)
      ? ok('and says that is what it is')
      : fail('it shows the frozen answer without saying so: '
             + slot.querySelector('.board-hint').textContent);
  }

  // ------------------------------------------- and writing on it writes on IT
  //
  // The same boards, reported in the same breath: "the color is inverted and
  // when I try to write on them, it clears everything to be a new writing
  // surface". Both halves are one defect: the board pointed at a sheet that no
  // longer held the answer, so touching it opened that sheet AS IT IS NOW --
  // reused, or cleared -- and an evening's working appeared to go.
  //
  // What was handed in cannot move, so it is what comes back under the pen.
  if (slot) {
    const before = slate.pages();
    const ev = new window.Event('pointerdown', { bubbles: true, cancelable: true });
    Object.assign(ev, { pointerId: 91, pointerType: 'pen', pressure: 0.5,
                        clientX: 200, clientY: 200, isPrimary: true });
    ev.getCoalescedEvents = () => [ev];
    slot.dispatchEvent(ev);
    await sleep(60);

    slate.inkOn(slate.at()) === 3
      ? ok('touching it puts the answer that was handed in back under the pen')
      : fail('the pen landed on a page with ' + slate.inkOn(slate.at())
             + ' strokes on it — the reused sheet, not the answer, which is the '
             + '"it clears everything to be a new writing surface" report');
    slate.pages() === before + 1
      ? ok('on a page of its own, so the sheet it was reusing keeps its own ink')
      : fail('the answer came back over the top of a page somebody else is using');
    slate.inkOn(p9) === 1
      ? ok('and the sheet that reused it is untouched')
      : fail('the reused page changed (' + slate.inkOn(p9) + ' strokes)');
    lift();
  }
}

// ------------------------ an answer being EDITED is not an answer that is gone
//
// The other side of the same rule, and the reason the two tests are not the same
// test: somebody who sends an answer and then rubs a line out of it is on that
// sheet, editing it. Cutting them a fresh copy of what was sent would orphan the
// edit they are in the middle of making.
{
  const q15 = card('0015', 'question', 'Exercise 5.1', 15);
  es.onmessage({ data: lesson([q1, q15], []) });
  await sleep(40);
  const p15 = mapping()['0015#0'] ? mapping()['0015#0'].p : slate.at();
  slate.go(p15);
  slate.load({ w: 1130, h: 1514, strokes: [ink(1), ink(2), ink(3), ink(4)] });
  const sent15 = { id: 't0015', rev: 1, kind: 'ink', answers: '0015', t: t0 + 1500,
                   page: p15, strokes: 4,
                   png: '/answers/t0015-r1.png', ink: '/answers/t0015-r1.json' };
  frozen['/answers/t0015-r1.json'] =
    { w: 1130, h: 1514, strokes: [ink(1), ink(2), ink(3), ink(4)] };
  es.onmessage({ data: lesson([q1, q15], [sent15]) });
  await sleep(40);
  lift();

  // One line rubbed out of four, on the same sheet.
  slate.go(p15);
  slate.load({ w: 1130, h: 1514, strokes: [ink(1), ink(2), ink(3)] });
  const pages15 = slate.pages();
  es.onmessage({ data: lesson([q1, q15], [sent15]) });
  await sleep(60);

  slate.pages() === pages15 && slate.at() === p15
    ? ok('rubbing a line out of an answer leaves you on the sheet you are editing')
    : fail('the board cut a fresh copy of what was sent and moved the pen to it, '
           + 'which orphans the edit being made (page ' + slate.at() + ' of '
           + slate.pages() + ')');
  slate.inkOn(p15) === 3
    ? ok('and the edit stands')
    : fail('the edited page was written back over (' + slate.inkOn(p15) + ' strokes)');
  lift();
}

// ------------------------------- an answer from before the strokes were frozen
//
// The picture is the fallback and has to stay one: an inverted board still shows
// the working, and a blank board does not.
{
  const q13 = card('0013', 'question', 'Exercise 4.1', 13);
  es.onmessage({ data: lesson([q1, q13], []) });
  await sleep(40);
  const p13 = mapping()['0013#0'] ? mapping()['0013#0'].p : slate.at();
  slate.go(p13);
  slate.load({ w: 1130, h: 1514, strokes: [ink(4), ink(5)] });
  const older = { id: 't0013', rev: 1, kind: 'ink', answers: '0013', t: t0 + 1300,
                  page: p13, strokes: 2, png: '/answers/t0013-r1.png' };
  es.onmessage({ data: lesson([q1, q13], [older]) });
  await sleep(40);
  lift();
  slate.go(p13);
  slate.clear();                                   /* the sheet is wiped */
  const q14 = card('0014', 'question', 'Exercise 4.2', 14);
  es.onmessage({ data: lesson([q1, q13, q14], [older]) });
  await sleep(60);
  lift();

  const slot = doc.querySelector('[data-slot^="0013"]');
  const shot = slot && slot.querySelector('.board-shot');
  shot && shot.getAttribute('src') === '/answers/t0013-r1.png'
    ? ok('an answer with no frozen strokes still shows its picture')
    : fail('a board with no strokes to draw from shows nothing at all ('
           + (shot && shot.getAttribute('src')) + ')');
}

// ------------- a carried-over copy is the student's, and erasing it means it
//
// The next attempt of a question opens on a COPY of the one that was handed in.
// So it begins life holding every stroke of that answer while never having been
// the sheet the answer came off -- and "has this sheet lost its answer" was asked
// of it anyway, because an answer is keyed by question and a question has as many
// boards as it took attempts. Erase the copy, which is the first thing anybody
// does with one, and the board concluded the answer had been destroyed and handed
// it back on a page of its own, under the pen.
//
// Reported from the iPad: "I got a new board to answer the next prompt, and I
// elected to erase my copied over previous board work, and started writing new
// work. Then all of a sudden, the old previous board work showed up again and the
// new work I started on got wiped."
{
  const q17 = card('0017', 'question', 'Exercise 6.1', 17);
  es.onmessage({ data: lesson([q1, q17], []) });
  await sleep(40);
  const p17 = mapping()['0017#0'] ? mapping()['0017#0'].p : slate.at();
  slate.go(p17);
  const many = [];
  for (let i = 0; i < 12; i++) many.push(ink(i));
  slate.load({ w: 1130, h: 1514, strokes: many });
  const sent17 = { id: 't0017', rev: 1, kind: 'ink', answers: '0017', t: t0 + 1700,
                   page: p17, strokes: 12,
                   png: '/answers/t0017-r1.png', ink: '/answers/t0017-r1.json' };
  frozen['/answers/t0017-r1.json'] = { w: 1130, h: 1514, strokes: many };

  // Handed in, and answered underneath: this attempt is finished with, and the
  // next opens on a copy of it.
  const fb17 = card('0018', 'note', 'try the third line again', 18);
  es.onmessage({ data: lesson([q1, q17, fb17], [sent17]) });
  await sleep(60);
  lift();

  const copy = mapping()['0017#1'] && mapping()['0017#1'].p;
  copy !== undefined && copy !== p17 && slate.inkOn(copy) === 12
    ? ok('the next attempt opens on a copy of what was handed in')
    : fail('no second attempt on a copy of the answer (page ' + copy + ')');

  if (copy !== undefined) {
    // Erased, and then written on. Two payloads, because the reported failure
    // needed only one to land in between.
    slate.go(copy);
    slate.clear();
    es.onmessage({ data: lesson([q1, q17, fb17], [sent17]) });
    await sleep(60);
    lift();
    slate.go(copy);
    slate.load({ w: 1130, h: 1514, strokes: [ink(50), ink(51)] });
    es.onmessage({ data: lesson([q1, q17, fb17], [sent17]) });
    await sleep(60);
    lift();

    slate.at() === copy
      ? ok('erasing a carried-over copy and writing on it leaves you on it')
      : fail('the pen was moved from the copy (page ' + copy + ') to page '
             + slate.at() + ' — the old answer handed back over new working');
    slate.inkOn(copy) === 2
      ? ok('and the new working is what is on it')
      : fail('the copy holds ' + slate.inkOn(copy) + ' strokes, not the 2 just '
             + 'written: the answer was put back over them');
    mapping()['0017#1'] && mapping()['0017#1'].p === copy
      ? ok('and the board still points at the sheet the working is on')
      : fail('the board was moved off the working to page '
             + (mapping()['0017#1'] || {}).p);
    // The answer itself is not lost by any of this: it is on disk, and the
    // attempt it came off still points at the sheet it came off.
    slate.inkOn(p17) === 12
      ? ok('while the attempt that was handed in keeps what was handed in')
      : fail('the first attempt lost its ink (' + slate.inkOn(p17) + ' strokes)');

    // AND COMING BACK TO IT.
    //
    // The judgement is made when a board is opened, so the interesting moment is
    // the next opening -- a reload, or walking away and tapping it again. The
    // copy is by then a sheet holding two strokes where the record says twelve
    // were handed in, which is exactly the shape of a board whose answer has
    // gone. It is not one: this board never held that answer, and the board that
    // did still points at it.
    const q20 = card('0020', 'question', 'Exercise 6.2', 20);
    es.onmessage({ data: lesson([q1, q17, fb17, q20], [sent17]) });
    await sleep(60);
    lift();
    const back = doc.querySelector('[data-slot="0017#1"]');
    if (!back) {
      fail('the erased attempt has no board to come back to');
    } else {
      const tap = new window.Event('pointerdown', { bubbles: true, cancelable: true });
      Object.assign(tap, { pointerId: 91, pointerType: 'pen', pressure: 0.5,
                           clientX: 200, clientY: 200, isPrimary: true });
      tap.getCoalescedEvents = () => [tap];
      back.dispatchEvent(tap);
      await sleep(80);
      slate.at() === copy && slate.inkOn(copy) === 2
        ? ok('and coming back to it opens what you wrote, not what you erased')
        : fail('coming back to the erased copy opened page ' + slate.at()
               + ' with ' + slate.inkOn(slate.at()) + ' strokes — the old answer '
               + 'put back over working that was never it');
      lift();
    }
  }
}

// ------------------ a sheet that is gaining ink is a sheet somebody is using
//
// The other half of the same report, on the board the answer really did come off.
// Somebody who clears their own answer's sheet to start it over is on that sheet.
// Between ruling the answer gone and being able to act on it there are two waits
// -- the frozen strokes have to be fetched, and a hand has to come off the glass
// -- and the judgement used to be re-made from scratch after them, by which time
// there was new working underneath it to be orphaned.
{
  const q19 = card('0019', 'question', 'Exercise 7.1', 19);
  es.onmessage({ data: lesson([q1, q19], []) });
  await sleep(40);
  const p19 = mapping()['0019#0'] ? mapping()['0019#0'].p : slate.at();
  slate.go(p19);
  const lot = [];
  for (let i = 0; i < 12; i++) lot.push(ink(60 + i));
  slate.load({ w: 1130, h: 1514, strokes: lot });
  const sent19 = { id: 't0019', rev: 1, kind: 'ink', answers: '0019', t: t0 + 1900,
                   page: p19, strokes: 12,
                   png: '/answers/t0019-r1.png', ink: '/answers/t0019-r1.json' };
  frozen['/answers/t0019-r1.json'] = { w: 1130, h: 1514, strokes: lot };
  es.onmessage({ data: lesson([q1, q19], [sent19]) });
  await sleep(40);
  lift();

  // Cleared to start over, and a payload lands in the gap -- which is the moment
  // the answer is ruled gone, and the moment the sheet is empty.
  slate.go(p19);
  slate.clear();
  es.onmessage({ data: lesson([q1, q19], [sent19]) });
  await sleep(60);
  lift();
  // And then the new version of the answer starts going down.
  slate.go(p19);
  slate.load({ w: 1130, h: 1514, strokes: [ink(90), ink(91), ink(92)] });
  es.onmessage({ data: lesson([q1, q19], [sent19]) });
  await sleep(60);
  lift();

  slate.at() === p19 && slate.inkOn(p19) === 3
    ? ok('clearing your own answer to start it over leaves you on the sheet')
    : fail('the send was handed back over a fresh start (page ' + slate.at()
           + ' of ' + slate.pages() + ', ' + slate.inkOn(p19) + ' strokes on '
           + p19 + ')');
}

// ----------------------------------------------------------------------------
// AND A CARD THAT ASKS WITHOUT SAYING SO STILL KEEPS ITS BOARDS.
//
// All of the above hangs off `kind: question`. A tutor that poses the exercise
// in a `lesson` card and asks at the foot of it breaks nothing visible on the
// board -- and used to take the whole chain with it: the ink froze into a
// picture the moment it was sent, no board was kept, and there was nothing to
// revise in place. Reported from a Galois sitting: "my written response was
// frozen in an image above ... ALL boards were independent of each other and I
// could edit them any time. Where did this feature go?"
//
// The student's own work is the authority. A card somebody has written an
// answer against was a question, whatever it called itself.
{
  const l1 = card('0100', 'lesson', 'the whole run, and the first exercise', 30);
  const l2 = card('0101', 'lesson', 'where the seven comes from', 31);
  const kept2 = () => Array.from(doc.querySelectorAll('[data-board="0101"]'));

  es.onmessage({ data: lesson([l1, l2]) });
  await sleep(40);

  // Nothing is owed -- no card asked -- so the way onto a board is the button
  // that exists for exactly that.
  const re = doc.getElementById('reopen');
  re && !re.hidden
    ? ok('a lesson that asked nothing still offers a board to write on')
    : fail('a lesson card asked in prose and there was no way to answer it');
  re.onclick();
  await sleep(40);
  !writer().hidden
    ? ok('and it opens')
    : fail('the board was asked for and did not open');

  slate.load({ w: 1130, h: 1514, strokes: [ink(40)] });
  const page = slate.at();
  const sent = { id: 't0100', rev: 1, kind: 'ink', answers: '0101', t: t0 + 3200,
                 page, strokes: 1, png: '/answers/t0100-r1.png',
                 ink: '/answers/t0100-r1.json' };
  es.onmessage({ data: lesson([l1, l2], [sent]) });
  await sleep(40);

  kept2().length === 0 && !writer().hidden
    ? ok('and what was handed in is the live board, not a photograph of one')
    : fail('the answer froze the moment it was sent: ' + kept2().length
           + ' kept, writer ' + (writer().hidden ? 'gone' : 'open'));

  // And the chain runs from there exactly as it does under a question card: the
  // attempt is kept where it was written, and the next one opens under the
  // feedback with the working carried onto it.
  const pagesBefore = slate.pages();
  const back = card('0102', 'note', 'the second line is where it goes', 32);
  es.onmessage({ data: lesson([l1, l2, back], [sent]) });
  await sleep(40);
  kept2().length === 1
    ? ok('and after the feedback lands it is kept, as a board')
    : fail('the attempt did not persist (' + kept2().length + ' of them)');
  doc.querySelector('[data-card="0102"]').nextElementSibling === writer()
    ? ok('while the next attempt is live under the feedback it answers')
    : fail('the live surface is not under the reply');
  slate.pages() === pagesBefore + 1 && slate.inkOn(slate.at()) === 1
    ? ok('opened on a copy, so the working so far is still under the pen')
    : fail('the next board came up blank or shared a sheet (page ' + slate.at()
           + ' of ' + slate.pages() + ')');
}

// ----------------------------------------------------------------------------
// AND A TURN RECORDED BEFORE ANY OF THIS STILL GETS ITS BOARD BACK.
//
// A page handed in when nothing had declared itself a question was written down
// answering NOTHING, and a turn about nothing can never be given a board: it is
// a picture for ever, and the lesson has no working between one response and the
// next. Those turns are on disk in sittings that are already under way, so the
// fix has to reach them rather than only the next send.
{
  const m1 = card('0200', 'lesson', 'the exercise, and the first rung', 40);
  const m2 = card('0201', 'lesson', 'what the degree actually counts', 41);
  const kept3 = () => Array.from(doc.querySelectorAll('[data-board="0201"]'));
  const reply = card('0202', 'note', 'the second line is where it goes', 42);

  es.onmessage({ data: lesson([m1, m2]) });
  await sleep(40);
  doc.getElementById('reopen').onclick();
  await sleep(40);
  slate.load({ w: 1130, h: 1514, strokes: [ink(50)] });

  // Sent while 0201 was the newest card, and recorded against nothing -- which
  // is how every page handed in under a lesson card used to be written down.
  const orphan = { id: 't0200', rev: 1, kind: 'ink', answers: null,
                   t: t0 + 4150, page: slate.at(), strokes: 1,
                   png: '/answers/t0200-r1.png', ink: '/answers/t0200-r1.json' };

  es.onmessage({ data: lesson([m1, m2, reply], [orphan]) });
  await sleep(40);

  kept3().length === 1
    ? ok('a turn that named nothing is adopted by the card it was written under')
    : fail('the orphaned answer is still a picture with no board (' + kept3().length
           + ' kept)');
  doc.querySelector('[data-card="0202"]').nextElementSibling === writer()
    ? ok('and the next board opens under the response, as it always did')
    : fail('there is still no board between one response and the next');
}

console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                          : '\nan exercise is a chain of boards, and every one of them stays');
process.exit(errors.length ? 1 : 0);
})();
