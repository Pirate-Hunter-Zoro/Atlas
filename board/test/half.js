// WHICH HALF OF THE ANSWER PANEL A QUESTION OPENS ON.
//
// Reported from the device, in two halves. The first is about which surface is
// in front of you:
//
//   "the spot for the next user response defaults to the 'typed' response, even
//    if the last response that I gave was a board-written one. The default that
//    shows up should be whatever last one I used was. If I wrote last, a board
//    should show up. If I typed last, a typing thing should show up."
//
// What was remembered was the last TAB anybody had pressed -- the write of it
// ran from `pickKind` and nowhere else -- so pressing *type* once and then
// writing in ink for a month opened every new question on the box. The half is
// recorded on the two SEND paths now, and a sitting's first question, which has
// no last half at all, is opened by its aim: "If the AI mode is math teacher or
// code coaching, then it should be the board... If the AI mode is vibe coding,
// then it should be the keyboard."
//
// The second half is what is IN the box: "typed responses should not carry over
// -- there's no way I'm going to type the same thing again... All new typed
// input boxes should render empty."
//
// Four windows, because the remembered half lives in `localStorage` and a
// browser that has never been used is the state most of these assertions are
// about. jsdom, because every one of them is about what is on the glass.

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

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// A browser with a remembered half already in it, or none at all. `remembered`
// is the raw string, because what a value written by an older board looks like
// is one of the things asserted.
function boot(remembered) {
  const dom = new JSDOM(HTML, {
    runScripts: 'outside-only', pretendToBeVisual: true,
    url: 'https://board.test/board',
  });
  const { window } = dom;
  const doc = window.document;

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

  const posted = [];
  window.fetch = (u, opt) => {
    posted.push({ url: String(u), body: opt && opt.body ? JSON.parse(opt.body) : null });
    if (/slate\/state/.test(String(u))) {
      return Promise.resolve({ json: () => Promise.resolve({ pages: [] }) });
    }
    return Promise.resolve({ json: () => Promise.resolve({ ok: true, page: 1,
                                                           turn: 't0900', rev: 1 }) });
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

  if (remembered !== undefined) {
    window.localStorage.setItem('answer-kind', remembered);
  }

  for (const f of ['typeface.js', 'macros.js', 'gauge.js', 'plane-core.js',
                   'slate-core.js', 'annotate.js', 'board.js']) {
    try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
    catch (e) { fail(f + ': ' + e.message); }
  }
  if (!window.__es) { console.log('FAIL board.js never opened a stream'); process.exit(1); }
  return { window, doc, es: window.__es, posted };
}

const t0 = Date.now() / 1000 - 3600;

// A sitting that teaches, and the same one told to do the work instead. Both
// carry `opened`, because that is half of what names a sitting.
const TEACHING = { course: 'Galois Theory', opened: '2026-09-17 19:40',
                   session: 'lecture', aim: 'teach', stance: 'teach',
                   stance_now: 'teach', declared_stance: 'teach' };
const DOING = { course: 'PSYCH-ASR', opened: '2026-09-17 19:55',
                session: 'lecture', aim: 'build', stance: 'do',
                stance_now: 'do', declared_stance: 'do' };

// A half remembered somewhere else entirely: another workspace, another evening.
const ELSEWHERE = (kind) =>
  JSON.stringify({ kind: kind, sitting: 'Probability @ 2026-08-02 11:00' });

const frame = (state, cards, turns) => JSON.stringify({
  state: state, cards: cards, turns: turns || [], messages: [], uploads: [],
  slate: [], history: 0, agent: { agent: 'claude', state: 'listening' },
});

const question = (id, at) => ({ id: id, kind: 'question', title: 'Exercise ' + id,
                                body: 'and the tower law', mtime: at });
const typedTurn = (id, q, at, text) => ({ id: id, rev: 1, kind: 'text',
                                          answers: q, t: at, text: text });

// The surface takes its time: a question new to the page types itself out, and
// the writing surface is deliberately held shut until it has finished.
const waitForPanel = async (doc) => {
  for (let i = 0; i < 80 && doc.getElementById('writer').hidden; i++) await sleep(50);
  await sleep(60);
};

// Which half is up, read off the page rather than out of the code.
const halfOf = (doc) => {
  const w = doc.getElementById('writer');
  if (!w || w.hidden) return '(the panel is shut)';
  const typing = !doc.getElementById('typebox').hidden;
  const slate = doc.getElementById('slate');
  const board = slate && !slate.hidden;
  if (typing && !board) return 'type';
  if (board && !typing) return 'write';
  return '(both halves at once)';
};

(async () => {

// ------------------------------------------------- a sitting that teaches
//
// The first question of it, in a browser that remembers typing from another
// workspace last month. The aim answers this one and the stale half does not.
const teach = boot(ELSEWHERE('type'));
teach.es.onmessage({ data: frame(TEACHING, [question('0001', t0)]) });
await waitForPanel(teach.doc);

halfOf(teach.doc) === 'write'
  ? ok('the first question of a teaching sitting opens on the board, with a '
       + 'half remembered in another workspace saying otherwise')
  : fail('the first question opened on the ' + halfOf(teach.doc));

// ------------------------------- and then they type, and typing is remembered
//
// No tab is pressed here on purpose. The point of the report is that the SEND
// is what says which half was used, and a send into the box is a typed answer
// whichever tab happens to be showing.
{
  const say = teach.doc.getElementById('saybox');
  say.value = 'because the degrees multiply';
  say.dispatchEvent(new teach.window.Event('input'));
  teach.doc.getElementById('send-type').click();
  await sleep(60);

  teach.es.onmessage({ data: frame(TEACHING,
    [question('0001', t0), question('0002', t0 + 300)],
    [typedTurn('t0055', '0001', t0 + 200, 'because the degrees multiply')]) });
  await waitForPanel(teach.doc);

  halfOf(teach.doc) === 'type'
    ? ok('and after a typed answer the next question opens on the box, with no '
         + 'tab having been pressed at all')
    : fail('a typed answer did not carry the box to the next question: opened '
           + 'on the ' + halfOf(teach.doc));
}

// ------------------------------------------- and the new box renders empty
{
  const say = teach.doc.getElementById('saybox');
  say.value === ''
    ? ok('and it renders empty: the words that were sent are not typed twice')
    : fail('the new box arrived with words in it: "' + say.value + '"');

  // Typing they have not sent, which belongs to the question they typed it
  // against and follows them nowhere.
  say.value = 'wait, it is Q(i)';
  say.dispatchEvent(new teach.window.Event('input'));
  await sleep(60);

  teach.es.onmessage({ data: frame(TEACHING,
    [question('0001', t0), question('0002', t0 + 300), question('0003', t0 + 600)],
    [typedTurn('t0055', '0001', t0 + 200, 'because the degrees multiply')]) });
  await waitForPanel(teach.doc);

  say.value === ''
    ? ok('and an unsent draft does not follow them to the next question either')
    : fail('the draft carried over: "' + say.value + '"');

  // It is kept, though. Going back to the question it was typed against gives
  // it back -- which is the difference between not carrying over and losing it.
  const back = teach.doc.querySelector('.board[data-board="0002"]');
  if (!back) {
    fail('the question typed against kept no board to go back to');
  } else {
    const down = new teach.window.Event('pointerdown', { bubbles: true, cancelable: true });
    Object.assign(down, { pointerId: 2, pointerType: 'touch', clientX: 10, clientY: 10,
                          isPrimary: true });
    down.getCoalescedEvents = () => [down];
    back.dispatchEvent(down);
    await sleep(200);
  }
  say.value === 'wait, it is Q(i)'
    ? ok('and going back to the question it was typed against gives it back')
    : fail('the draft was lost rather than kept: "' + say.value + '"');
}

// ------------------------------------------------- a sitting that does the work
//
// Same first question, opposite aim, and a browser remembering ink from
// somewhere else.
const doing = boot(ELSEWHERE('write'));
doing.es.onmessage({ data: frame(DOING, [question('0001', t0)]) });
await waitForPanel(doing.doc);

halfOf(doing.doc) === 'type'
  ? ok('the first question of a sitting that does the work opens on the box')
  : fail('a doing sitting opened on the ' + halfOf(doing.doc));

// -------------------------------------------- and then they write, in ink
//
// The discriminating case, and the report itself: the aim says box, the ink says
// board, and the answer that was actually SENT is the one that decides. Pressing
// Send for real, on strokes that are really on the surface, because the hook
// that records the half is the surface's own.
{
  const canvas = doing.doc.querySelector('#slate canvas');
  const bar = doing.doc.getElementById('drawbar');
  const send = bar && bar.querySelector('.sl-send');
  if (!canvas || !send) {
    fail('the writing surface never built itself, so no ink can be sent');
  } else {
    // The box is showing, so put the board up first: this is a person switching
    // halves and then answering, which is the state the report describes.
    doing.doc.getElementById('tab-write').click();
    await sleep(60);
    const pen = (type, x, y) => {
      const ev = new doing.window.Event(type, { bubbles: true, cancelable: true });
      Object.assign(ev, { pointerId: 1, pointerType: 'pen', pressure: 0.6,
                          clientX: x, clientY: y, isPrimary: true });
      ev.getCoalescedEvents = () => [ev];
      canvas.dispatchEvent(ev);
    };
    pen('pointerdown', 100, 100);
    for (let i = 0; i < 20; i++) pen('pointermove', 100 + i * 6, 100 + i * 2);
    pen('pointerup', 220, 140);

    const raf = doing.window.requestAnimationFrame;
    doing.window.requestAnimationFrame = (fn) => fn();
    send.onclick();
    doing.window.requestAnimationFrame = raf;
    await sleep(120);

    doing.posted.some((r) => /\/slate\/save$/.test(r.url) && r.body && r.body.send)
      ? ok('the ink went out')
      : fail('nothing was sent, so what follows asserts nothing');

    doing.es.onmessage({ data: frame(DOING,
      [question('0001', t0), question('0002', t0 + 300)],
      [{ id: 't0054', rev: 1, kind: 'ink', answers: '0001', t: t0 + 200,
         page: 1, strokes: 20, png: '/answers/t0054-r1.png' }]) });
    await waitForPanel(doing.doc);

    halfOf(doing.doc) === 'write'
      ? ok('and the next question opens on the board — an answer given in ink '
           + 'outranks the aim that opened the box, which is the report')
      : fail('the ink answer was forgotten: the next question opened on the '
             + halfOf(doing.doc));
  }
}

// ----------------------------------------- a tab press still wins where it lands
{
  doing.doc.getElementById('tab-type').click();
  await sleep(60);
  halfOf(doing.doc) === 'type'
    ? ok('a tab press opens the half it names')
    : fail('pressing *type* did not open the box: ' + halfOf(doing.doc));

  // A heartbeat carrying nothing new must not take it away again, which is what
  // a remembered half would do if it outranked the tap.
  doing.es.onmessage({ data: frame(DOING,
    [question('0001', t0), question('0002', t0 + 300)],
    [{ id: 't0054', rev: 1, kind: 'ink', answers: '0001', t: t0 + 200,
       page: 1, strokes: 20, png: '/answers/t0054-r1.png' }]) });
  await sleep(120);
  halfOf(doing.doc) === 'type'
    ? ok('and it stays through a repaint: the tap is about this question and '
         + 'nothing repaints it away')
    : fail('a repaint threw away the half they asked for: ' + halfOf(doing.doc));
}

// ------------------------------------- a half with no sitting on it is ignored
//
// What a board older than this rule wrote: the bare word, with nothing saying
// which evening it came from. It cannot outrank the aim, because nothing can
// say whether it is this evening's answer or last month's.
{
  const old = boot('type');
  old.es.onmessage({ data: frame(TEACHING, [question('0001', t0)]) });
  await waitForPanel(old.doc);
  halfOf(old.doc) === 'write'
    ? ok('an untagged remembered half is ignored, and the aim answers instead')
    : fail('a value that names no sitting was honoured: ' + halfOf(old.doc));
}

// ----------------------------------- and a browser that has never been used
{
  const fresh = boot();
  fresh.es.onmessage({ data: frame(TEACHING, [question('0001', t0)]) });
  await waitForPanel(fresh.doc);
  halfOf(fresh.doc) === 'write'
    ? ok('and a browser with nothing remembered at all opens on the aim')
    : fail('an empty browser opened on the ' + halfOf(fresh.doc));
}

console.log(errors.length
  ? errors.length + ' FAILURES'
  : 'the panel opens on the half they answered with');
process.exit(errors.length ? 1 : 0);
})();
