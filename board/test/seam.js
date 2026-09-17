// ONE WINDOW, THE WHOLE FLOW: WRITE, SEND, AND THE REPLY TYPES OUT ABOVE THE
// NEXT BOARD.
//
// Reported from a live sitting, after two fixes that were believed: "I just
// submitted a written board response, and the recurring issue of the next
// written board appearing right below it, and then seconds later the entire
// tutor response spontaneously completely showing up in between the boards at
// once occured AGAIN. It should have been fixed so that the tutor response would
// show up character by character and then the next writing board wouldn't show
// up until AFTER the tutor response was COMPLETELY rendered."
//
// THE FAULT LIVED IN A SEAM BETWEEN TWO SUITES, WHICH IS WHY IT SURVIVED THREE
// REPORTS. `test/interactive.js` presses the real Send with real strokes and
// never delivers a reply. `test/typed.js` delivers replies as frames and never
// sends anything. So the one flow a person actually performs -- ink on the glass,
// Send, the receipt, the reply, the next question -- was driven by nothing, and
// an ink send is precisely the case that leaves the writing surface OPEN, which
// is the branch of `placeWriter` the other suites never take.
//
// What is asserted here is the invariant and not the implementation: THE SURFACE
// NEVER COMES DOWN PAST A CARD THAT IS STILL HALF PAINTED. Every insertion of
// the surface is watched, in three windows -- the ordinary one, one with Reduce
// Motion on, and one whose animation frames arrive too late to be proof of
// anything.
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
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const FILES = ['typeface.js', 'macros.js', 'gauge.js', 'plane-core.js',
               'slate-core.js', 'annotate.js', 'board.js'];

// A board with a question owed, a surface open on it, and the wire stubbed. The
// canvas is given a real size, because a canvas that was never sized reports the
// browser default and nothing can be drawn on it -- which is the fault
// `test/interactive.js` exists for and is a precondition of this one.
function board(opts) {
  const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
    runScripts: 'outside-only', pretendToBeVisual: true,
    url: 'https://board.test/board',
  });
  const w = dom.window;
  const d = w.document;
  w.HTMLCanvasElement.prototype.getContext = () =>
    new Proxy({}, { get: () => () => {}, set: () => true });
  w.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
  Object.defineProperty(w.HTMLElement.prototype, 'clientWidth', { get: () => 900 });
  Object.defineProperty(w.HTMLElement.prototype, 'clientHeight', { get: () => 500 });
  w.HTMLElement.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: 900, height: 500, right: 900, bottom: 500, x: 0, y: 0 };
  };
  w.Element.prototype.scrollIntoView = function () {};
  w.Element.prototype.setPointerCapture = function () {};
  w.Element.prototype.releasePointerCapture = function () {};
  w.scrollTo = function () {};
  w.renderMathInElement = () => {};
  w.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  w.EventSource = function () {
    w.__es = this;
    this.readyState = 1;
    this.close = function () {};
    this.addEventListener = function () {};
  };
  // The saved-pages answer has to resolve: the board waits for it before it has
  // a page to write on, and a promise that never settles models a board that
  // never found out, which is a different test.
  const wire = [];
  w.fetch = (u, o) => {
    const url = String(u);
    if (/slate\/state/.test(url)) {
      return Promise.resolve({ json: () => Promise.resolve({ pages: [] }) });
    }
    wire.push({ url: url, body: o && o.body ? JSON.parse(o.body) : null });
    return Promise.resolve({
      json: () => Promise.resolve({ ok: true, page: 1, turn: 't0001', rev: 1 }),
    });
  };
  // THE WHOLE POINT OF THE SECOND WINDOW. jsdom has no `matchMedia`, so every
  // other suite in this repository runs with the animation on.
  if (opts && opts.reduceMotion) {
    w.matchMedia = (q) => ({ matches: /prefers-reduced-motion/.test(String(q)),
      media: String(q), addListener() {}, removeListener() {},
      addEventListener() {}, removeEventListener() {} });
  }
  w.addEventListener('error', (e) => fail('uncaught: ' + e.message));
  for (const f of FILES) {
    try { w.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
    catch (e) { fail(f + ': ' + e.message); }
  }
  return { w: w, d: d, es: w.__es, wire: wire };
}

const REPLY = 'Right, and the union is the part that was missing. Each set of '
            + 'roots is finite, the index set is countable, and a countable '
            + 'union of finite sets is countable. ';

async function flow(name, opts) {
  const { w, d, es, wire } = board(opts);
  if (!es) { fail(name + ': board.js never opened a stream'); return; }

  const u0 = Date.now() / 1000 - 600;
  const asked = { id: '0001', kind: 'question', title: 'Exercise 4.7',
                  body: 'Show that $L$ is countable.', mtime: u0 };
  const reply = { id: '0002', kind: 'correct', title: 'the union lands',
                  body: REPLY.repeat(2), mtime: u0 + 120 };
  const nextQ = { id: '0003', kind: 'question', title: 'the second half',
                  body: 'Now a transcendental real.', mtime: u0 + 121 };
  const ink = { id: 't0001', rev: 1, kind: 'ink', answers: '0001', t: u0 + 60,
                page: 1, strokes: 74, png: '/answers/t0001-r1.png',
                ink: '/answers/t0001-r1.json' };
  const frame = (cards, turns) => JSON.stringify({
    state: { course: 'Galois Theory', session: 'lecture', mode: 'math' },
    cards: cards, turns: turns || [], history: 0,
    agent: { agent: 'claude', state: 'working', turns: 2, turn_started: u0 },
  });

  es.onmessage({ data: frame([asked]) });
  await sleep(120);

  const writer = () => d.getElementById('writer');
  const at = (what) => {
    const kids = d.getElementById('cards').children;
    for (let i = 0; i < kids.length; i++) {
      if (what === 'writer' ? kids[i].id === 'writer'
                            : kids[i].dataset.card === what) return i;
    }
    return -1;
  };
  const replyBody = () => {
    const n = d.querySelector('[data-card="0002"] .body');
    return n || null;
  };
  const half = () => {
    const b = replyBody();
    return !!(b && b.querySelector('.tw-soon'));
  };

  writer() && !writer().hidden
    ? ok(name + ': the surface is open on the question, which is where a written '
         + 'answer starts from')
    : fail(name + ': no writing surface to answer on');

  // ---------------------------------------------------------------- the ink
  const canvas = d.querySelector('#slate canvas');
  if (!canvas) { fail(name + ': no canvas to write on'); return; }
  canvas.width > 300 && canvas.height > 150
    ? ok(name + ': and its canvas was sized to its box')
    : fail(name + ': the canvas is the unsized default — nothing can be drawn');

  const pen = (type, x, y) => {
    const ev = new w.Event(type, { bubbles: true, cancelable: true });
    Object.assign(ev, { pointerId: 1, pointerType: 'pen', pressure: 0.6,
                        clientX: x, clientY: y, isPrimary: true });
    ev.getCoalescedEvents = () => [ev];
    canvas.dispatchEvent(ev);
  };
  pen('pointerdown', 80, 90);
  for (let i = 0; i < 40; i++) pen('pointermove', 80 + i * 5, 90 + Math.sin(i / 4) * 18);
  pen('pointerup', 280, 90);

  const send = d.getElementById('drawbar').querySelector('.sl-send');
  if (!send || !send.onclick) { fail(name + ': no Send to press'); return; }
  send.onclick();                        /* the tap */
  await sleep(40);
  send.onclick();                        /* and the frame after it, which posts */
  await sleep(80);

  wire.filter((r) => /slate\/save/.test(r.url) && r.body && r.body.send).length
    ? ok(name + ': pressing Send posts the working')
    : fail(name + ': pressing Send posted nothing, so the flow under test never '
           + 'started');

  // The payload that answers the send: their ink is a turn now, and the tutor is
  // still writing. This is the frame the receipt is for.
  es.onmessage({ data: frame([asked], [ink]) });
  await sleep(80);

  // EVERY MOVE OF THE SURFACE FROM HERE, AND WHETHER THE REPLY WAS WHOLE WHEN IT
  // HAPPENED. This is the invariant, and it does not depend on any timing: the
  // surface may sit anywhere it likes ABOVE a card that is still arriving, and
  // must never be inserted below one.
  const host = d.getElementById('cards');
  const realInsert = host.insertBefore.bind(host);
  const realAppend = host.appendChild.bind(host);
  const moves = [];
  const watch = (n) => {
    if (!n || n.id !== 'writer') return;
    moves.push({ half: half(), below: at('writer') > at('0002') && at('0002') !== -1 });
  };
  host.insertBefore = function (n, r) { const out = realInsert(n, r); watch(n); return out; };
  host.appendChild = function (n) { const out = realAppend(n); watch(n); return out; };

  // ------------------------------------------- the reply, and the next question
  //
  // One payload, which is what a teaching turn sends: the answer to what was
  // handed in, and the next thing to do.
  es.onmessage({ data: frame([asked, reply, nextQ], [ink]) });
  await sleep(20);

  half()
    ? ok(name + ': the reply is TYPED — what has not been said yet is laid out '
         + 'and unpainted')
    : fail(name + ': the reply landed whole, which is the reported fault');
  {
    const said = replyBody() && replyBody().querySelector('.tw-said');
    said && said.textContent.length < reply.body.length
      ? ok(name + ': with only the part already said painted')
      : fail(name + ': the whole of it is painted at once');
  }
  at('writer') !== -1 && at('0003') !== -1 && at('writer') < at('0003')
    ? ok(name + ': and the next board has NOT come down under the new question '
         + 'while the reply is still arriving')
    : fail(name + ': the next board arrived between the answer and the reply, '
           + 'which is the geometry the report describes');
  !d.querySelector('[data-slot^="0003"]')
    ? ok(name + ': and nothing is drawn in its place, so the new question is not '
         + 'answered by a photograph of an empty board')
    : fail(name + ': a dormant board was painted where the held surface belongs');

  // --------------------------------------------------- and then it lets go
  await sleep(5200);                     /* past TYPE_ALL and the settle */

  !half()
    ? ok(name + ': the reply finishes and takes its scaffolding out of the lesson')
    : fail(name + ': the reply is still half painted');
  at('writer') > at('0002')
    ? ok(name + ': and only then does the surface come down past it')
    : fail(name + ': the surface never came down after the reply finished');

  const bad = moves.filter((m) => m.below && m.half);
  !bad.length
    ? ok(name + ': AND THE SURFACE WAS NEVER ONCE INSERTED BELOW A HALF PAINTED '
         + 'REPLY (' + moves.length + ' move(s) watched)')
    : fail(name + ': the surface was moved below a reply that was still being '
           + 'painted, ' + bad.length + ' time(s) of ' + moves.length);

  return { w: w, d: d };
}

(async () => {

await flow('sent', null);
await flow('reduce motion', { reduceMotion: true });

// ----------------------------------------------------- AND WHEN IT STALLS
//
// `TYPE_STALL` is 2500ms of silence, pushed out by every frame, and a frame that
// arrives after it means the main thread was away. Letting go beats parking the
// surface for ever -- that is not in question. What letting go used to MEAN is
// the reported fault arriving out of its own safety valve: the rest of the card
// was painted in one go and the surface came down in the same breath.
//
// So a stall now finishes the card WHOLE and keeps a settle: the pacing is lost,
// the order is not. Staged by starving the animation frame, which is the real
// cause rather than a stand-in for it -- `typingUntil` lives inside board.js's
// own closure, and reaching into it would test the variable instead of the
// behaviour.
//
// ONE FRESH CARD IN THE PAYLOAD, WHICH IS WHAT MAKES THIS SHARP. The reply has
// to be the only thing holding: with a second card still arriving, the surface
// stays where it is for that card's sake and the assertion passes without ever
// touching the stall. What is measured is the GAP -- the moment the card became
// whole, against the moment the surface came down past it. Nothing else here can
// tell "the answer, then the board" from "both at once".
{
  const { w, d, es } = board(null);
  const u0 = Date.now() / 1000 - 600;
  const asked = { id: '0001', kind: 'question', title: 'Exercise 4.7',
                  body: 'Show that $L$ is countable.', mtime: u0 };
  /* FEEDBACK, NOT A NEW QUESTION: the same exercise goes back for a revision, so
     the surface is still owed and has somewhere to come down to, and the reply
     is the only card arriving. That is the shape that makes the gap measurable
     at all -- with a second card in flight the surface is held for ITS sake and
     the stall is never reached. */
  const reply = { id: '0002', kind: 'wrong', title: 'the union, except f = 0',
                  body: REPLY.repeat(2), mtime: u0 + 120 };
  const ink = { id: 't0001', rev: 1, kind: 'ink', answers: '0001', t: u0 + 60,
                page: 1, strokes: 74, png: '/answers/t0001-r1.png',
                ink: '/answers/t0001-r1.json' };
  const frame = (cards, turns) => JSON.stringify({
    state: { course: 'Galois Theory', session: 'lecture', mode: 'math' },
    cards: cards, turns: turns || [], history: 0,
    agent: { agent: 'claude', state: 'working', turns: 2, turn_started: u0 },
  });

  es.onmessage({ data: frame([asked]) });
  await sleep(120);
  es.onmessage({ data: frame([asked], [ink]) });
  await sleep(80);

  const at = (what) => {
    const kids = d.getElementById('cards').children;
    for (let i = 0; i < kids.length; i++) {
      if (what === 'writer' ? kids[i].id === 'writer'
                            : kids[i].dataset.card === what) return i;
    }
    return -1;
  };
  const half = () => {
    const b = d.querySelector('[data-card="0002"] .body');
    return !!(b && b.querySelector('.tw-soon'));
  };

  let wholeAt = null, movedAt = null;
  const host = d.getElementById('cards');
  const realInsert = host.insertBefore.bind(host);
  const realAppend = host.appendChild.bind(host);
  const watch = (n) => {
    if (!n || n.id !== 'writer' || movedAt !== null) return;
    if (at('0002') !== -1 && at('writer') > at('0002')) movedAt = Date.now();
  };
  host.insertBefore = function (n, r) { const o = realInsert(n, r); watch(n); return o; };
  host.appendChild = function (n) { const o = realAppend(n); watch(n); return o; };
  const poll = setInterval(function () {
    if (wholeAt === null && d.querySelector('[data-card="0002"]') && !half()) {
      wholeAt = Date.now();
    }
  }, 5);

  /* The thread goes away: one frame, arriving well past the watchdog. */
  w.requestAnimationFrame = (fn) => setTimeout(fn, 2700);
  es.onmessage({ data: frame([asked, reply], [ink]) });
  await sleep(2780);

  !half()
    ? ok('stall: the card whose frames stopped coming is finished WHOLE rather '
         + 'than left half painted')
    : fail('stall: the card is still half painted after the watchdog let go');
  movedAt === null
    ? ok('stall: and the surface has NOT come down in the same breath, because '
         + 'the hold moved to the settle instead of being given back')
    : fail('stall: the rest of the card and the next board arrived as one event, '
           + 'which is the reported fault coming out of its own watchdog');

  await sleep(600);                      /* past TYPE_SETTLE */
  clearInterval(poll);

  movedAt !== null
    ? ok('stall: and a beat later it comes down, so a hold that is lost is still '
         + 'given back — parking the surface for ever is worse')
    : fail('stall: the surface is parked, which is what the watchdog exists to '
           + 'prevent');
  movedAt !== null && wholeAt !== null && movedAt - wholeAt >= 100
    ? ok('stall: and the gap between the card landing and the board arriving is '
         + (movedAt - wholeAt) + 'ms — two events, one of which is no longer '
         + 'pretty')
    : fail('stall: the card and the board landed together ('
           + (movedAt - wholeAt) + 'ms apart), which reads as one event');
}

console.log(errors.length ? '\n' + errors.length + ' FAILURES'
  : '\nthe answer is sent, the reply types above the next board, and a stall '
    + 'loses the pacing and not the order');
process.exit(errors.length ? 1 : 0);

})();
