// ONE WINDOW, THE WHOLE FLOW: WRITE, SEND, AND THE REPLY TYPES OUT WHERE YOU
// ARE LOOKING.
//
// Reported from a live sitting, four times, and patched three times in the wrong
// place: "I just submitted a written board response, and the recurring issue of
// the next written board appearing right below it, and then seconds later the
// entire tutor response spontaneously completely showing up in between the
// boards at once occured AGAIN. It should have been fixed so that the tutor
// response would show up character by character and then the next writing board
// wouldn't show up until AFTER the tutor response was COMPLETELY rendered."
//
// THE SENTENCE SOUNDS LIKE A QUESTION ABOUT WHEN THE SURFACE MOVES, AND IT IS
// NOT. The board's own trace settled it: the card typed, for 4256ms, with the
// hold in force the whole time -- and nobody saw a character of it, because a
// new card was APPENDED to the lesson and the writing surface is the last child
// of a lesson with a board open on it. So the reply typed itself out underneath
// a full-height board, off the bottom of the glass. The jump at the end was the
// surface taking its proper place, which revealed the finished card all at once.
//
// So a card goes ABOVE the surface, from the frame it lands, and then nothing
// has to move at all. That is what this file asserts, in the flow a person
// actually performs -- ink on the glass, Send, the receipt, the reply, the next
// question -- which no suite drove: `test/interactive.js` presses the real Send
// and never delivers a reply, `test/typed.js` delivers replies as frames and
// never sends anything, and an ink send is the case that leaves the surface
// OPEN.
//
// THE INVARIANT IS THAT THE SURFACE DOES NOT MOVE. Every insertion of it is
// watched, in three windows: the ordinary one, one with Reduce Motion on, and
// one whose animation frames arrive too late to be proof of anything.
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

  // EVERY MOVE OF THE SURFACE FROM HERE. This is the invariant and it depends on
  // no timing at all: a reply lands above the board you would answer it on, so
  // there is nothing for the surface to do while the reply types, and a surface
  // that does not move cannot reveal a finished card by moving.
  const host = d.getElementById('cards');
  const realInsert = host.insertBefore.bind(host);
  const realAppend = host.appendChild.bind(host);
  const moves = [];
  const watch = (n) => { if (n && n.id === 'writer') moves.push(at('writer')); };
  host.insertBefore = function (n, r) { const out = realInsert(n, r); watch(n); return out; };
  host.appendChild = function (n) { const out = realAppend(n); watch(n); return out; };
  const sat = at('writer');

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
  at('0002') !== -1 && at('0002') < at('writer')
    ? ok(name + ': and it is ABOVE the board, in the order the transcript reads, '
         + 'from the frame it lands — which is the whole of this')
    : fail(name + ': the reply landed BELOW the writing surface, where it types '
           + 'out under a full-height board and nobody sees a character of it');
  at('0003') !== -1 && at('0003') < at('writer')
    ? ok(name + ': and so is the next question, so the surface is still the last '
         + 'thing in the lesson')
    : fail(name + ': the new question landed below the surface');
  !d.querySelector('[data-slot^="0003"]')
    ? ok(name + ': and nothing is drawn in its place, so the new question is not '
         + 'answered by a photograph of an empty board')
    : fail(name + ': a dormant board was painted where the surface already is');

  // --------------------------------------------------- and then it finishes
  const order = Array.prototype.map.call(host.children, (n) => n.id || n.dataset.card
    || n.dataset.slot || '?').join(',');
  await sleep(5200);                     /* past TYPE_ALL and the settle */

  !half()
    ? ok(name + ': the reply finishes and takes its scaffolding out of the lesson')
    : fail(name + ': the reply is still half painted');
  Array.prototype.map.call(host.children, (n) => n.id || n.dataset.card
    || n.dataset.slot || '?').join(',') === order
    ? ok(name + ': and the last character changes NOTHING on the page — the '
         + 'lesson is in the same order it was in while it typed')
    : fail(name + ': the page was rearranged when the card finished, and that '
           + 'rearrangement is what reads as the whole answer appearing at once');

  !moves.length
    ? ok(name + ': AND THE SURFACE WAS NEVER MOVED AT ALL, from the frame the '
         + 'reply landed to the last character of it')
    : fail(name + ': the surface was inserted ' + moves.length + ' time(s) while '
           + 'the reply arrived (indices ' + moves.join(',') + ', it was at '
           + sat + ')');

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
// painted in one go and the board moving in the same breath.
//
// Staged by starving the animation frame, which is the real cause rather than a
// stand-in for it -- `typingUntil` lives inside board.js's own closure, and
// reaching into it would test the variable instead of the behaviour.
{
  const { w, d, es } = board(null);
  const u0 = Date.now() / 1000 - 600;
  const asked = { id: '0001', kind: 'question', title: 'Exercise 4.7',
                  body: 'Show that $L$ is countable.', mtime: u0 };
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

  const host = d.getElementById('cards');
  const realInsert = host.insertBefore.bind(host);
  const moves = [];
  host.insertBefore = function (n, r) {
    const out = realInsert(n, r);
    if (n && n.id === 'writer') moves.push(at('writer'));
    return out;
  };

  /* The thread goes away: one frame, arriving well past the watchdog. */
  w.requestAnimationFrame = (fn) => setTimeout(fn, 2700);
  es.onmessage({ data: frame([asked, reply], [ink]) });
  await sleep(2780);

  !half()
    ? ok('stall: the card whose frames stopped coming is finished WHOLE rather '
         + 'than left half painted')
    : fail('stall: the card is still half painted after the watchdog let go');
  at('0002') < at('writer')
    ? ok('stall: and it is still above the board, so finishing it early moved '
         + 'nothing and revealed nothing')
    : fail('stall: the card is below the surface');
  !moves.length
    ? ok('stall: and the surface was never moved, which is what makes a lost '
         + 'animation a lost animation rather than a jump')
    : fail('stall: the surface moved ' + moves.length + ' time(s) when the '
           + 'watchdog let go');
}

// ------------------------------------ AND A BOARD THAT IS NOT OPEN YET WAITS
//
// The other half of `placeWriter`, and the one the settle still exists for. With
// no question owed there is no surface on the page, so there is nothing to hold
// in place -- what must not happen is one APPEARING beside a card that arrived
// in the same breath. `writerHeldShut` is that branch, and a stall is where it
// used to be lost: the hold was given back on the late frame, so the board came
// up in the same tick as the rest of the card.
//
// Measured as a GAP, because that is the thing being asked for: the card lands,
// and then the board does.
//
// ONE FRESH CARD, AND IT IS THE QUESTION ITSELF -- which is what makes this
// sharp rather than accidentally true. A question both types out AND is the
// thing that is owed, so the only hold on the page is its own: give it back on
// the late frame and the board comes up in the same tick as the last of the
// card. With a second card still arriving the surface would wait for THAT and
// the assertion would pass without ever touching the stall.
{
  const { w, d, es } = board(null);
  const u0 = Date.now() / 1000 - 600;
  const opening = { id: '0001', kind: 'lesson', title: '',
                    body: 'We are counting polynomials tonight.', mtime: u0 };
  const nextQ = { id: '0002', kind: 'question', title: 'your move',
                  body: REPLY.repeat(2), mtime: u0 + 120 };
  const frame = (cards) => JSON.stringify({
    state: { course: 'Galois Theory', session: 'lecture', mode: 'math' },
    cards: cards, turns: [], history: 0,
    agent: { agent: 'claude', state: 'working', turns: 2, turn_started: u0 },
  });

  es.onmessage({ data: frame([opening]) });
  await sleep(120);

  const writer = () => d.getElementById('writer');
  const half = () => {
    const b = d.querySelector('[data-card="0002"] .body');
    return !!(b && b.querySelector('.tw-soon'));
  };

  writer() && writer().hidden
    ? ok('shut: with nothing owed there is no board on the page')
    : fail('shut: a surface is open with no question to answer');

  let wholeAt = null, openAt = null;
  const poll = setInterval(function () {
    if (wholeAt === null && d.querySelector('[data-card="0002"]') && !half()) {
      wholeAt = Date.now();
    }
    if (openAt === null && writer() && !writer().hidden) openAt = Date.now();
  }, 5);

  w.requestAnimationFrame = (fn) => setTimeout(fn, 2700);
  es.onmessage({ data: frame([opening, nextQ]) });
  await sleep(2780);

  !half()
    ? ok('shut: a stalled card is finished whole')
    : fail('shut: the card is still half painted');
  writer().hidden
    ? ok('shut: and the board has NOT come up in the same breath — the hold moved '
         + 'to the settle rather than being given back')
    : fail('shut: the board appeared in the same tick as the rest of the card, '
           + 'which is the reported fault out of its own watchdog');

  await sleep(900);
  clearInterval(poll);

  writer() && !writer().hidden
    ? ok('shut: and a beat later it opens, so a hold that is lost is still given '
         + 'back — parking the page is worse')
    : fail('shut: no board ever opened for the new question');
  wholeAt !== null && openAt !== null && openAt - wholeAt >= 100
    ? ok('shut: with ' + (openAt - wholeAt) + 'ms between the card landing and '
         + 'the board arriving — two events, one of which is no longer pretty')
    : fail('shut: the card and the board landed together ('
           + (openAt - wholeAt) + 'ms apart), which reads as one event');
}

console.log(errors.length ? '\n' + errors.length + ' FAILURES'
  : '\nthe answer is sent, the reply types above the next board, and a stall '
    + 'loses the pacing and not the order');
process.exit(errors.length ? 1 : 0);

})();
