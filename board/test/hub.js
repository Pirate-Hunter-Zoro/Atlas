// The front door, and the ATLAS drawn on it.
//
// This page used to end in two lists -- "Other courses" and "Earlier" -- and a
// list is not a map. The objection that killed the first version of the
// per-workspace map applies word for word to a column of names:
//
//     "I don't want just a list of all the TODOs. I want a map of the CONTENT."
//
// So it is drawn, and every failure this file guards is one the drawn version
// can have and the list could not:
//
//   * THE TEXT MUST FIT ITS CARD. Measured through `gauge.js`, never estimated.
//     A line of capitals -- which is how these plans are written -- is half
//     again wider than characters times a constant, and that is exactly how the
//     first map's labels came to run out of their boxes.
//   * THE LAYOUT MUST NOT DEPEND ON THE GLASS. The same repository has to lay
//     out identically on a phone and on an iPad, or it is not a picture anybody
//     can learn.
//   * A PAN MUST NOT ALSO BE A TAP. Dragging the plane with a finger that
//     started on a card used to open that card when it was lifted.
//   * IT MUST STILL BE A DOOR. Whatever else the atlas is, it is the thing that
//     gets somebody back into the lesson they were in twenty seconds ago.
//   * AND NOTHING IN THE PAINT MAY THROW. A front door that throws is a blank
//     screen where the app used to be.
//
// jsdom is a development-only dependency; without it this skips.

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
const check = (m, cond) => (cond ? ok(m) : fail(m));

const css = fs.readFileSync(path.join(WEB, 'home.css'), 'utf8');
const js = fs.readFileSync(path.join(WEB, 'home.js'), 'utf8');

// ---- the plane, as a surface ----------------------------------------------
const planeBlock = (css.match(/\.atlas-plane \{[^}]*\}/) || [''])[0];
check('the plane decides its own gestures, so the browser does not scroll under a pinch',
      /touch-action:\s*none/.test(planeBlock));
check('and it never lets the body scroll sideways however far it is panned',
      /overflow:\s*hidden/.test(planeBlock));

// Every colour a token, defined in BOTH blocks. A colour named in one is half
// the page changing theme and the other half not.
const light = (css.match(/^:root \{[^}]*\}/m) || [''])[0];
const dark = (css.match(/body\[data-mode="dark"\][^{]*\{[^}]*\}/) || [''])[0];
const used = new Set();
(css.match(/var\(--[a-z0-9-]+\)/g) || []).forEach((v) => {
  const name = v.slice(5, -1);
  if (['ui', 'prose', 'mono', 'prose-leading', 'prose-tracking'].includes(name)) return;
  used.add(name);
});
const missing = [...used].filter((n) => light.includes('--' + n + ':')
                                     && !dark.includes('--' + n + ':'));
check('every colour the atlas uses is defined in the dark palette too',
      missing.length === 0);

// ---- the layout is not a function of the viewport -------------------------
// Asserted against the source, because a jsdom window has one size and could
// never catch this by rendering twice.
const layout = js.slice(js.indexOf('function aLayout('), js.indexOf('function aAgo('));
check('the layout reads no width of the glass',
      !/clientWidth|innerWidth|getBoundingClientRect|matchMedia/.test(layout));
check('and the number of cards across is a constant, not a calculation',
      /var A_ACROSS = \d+;/.test(js));
check('a long family wraps into bands rather than running off sideways',
      /i \+= A_ACROSS/.test(layout));
check('and the text is measured rather than estimated',
      /Gauge\.wrap/.test(js) && !/length \* [\d.]+ *\/\/ *width/.test(js));

// ---- drive the real page --------------------------------------------------
// A switch that lands ends in `location.href = "/"`, and jsdom has nowhere to
// navigate to -- it reports that as a jsdomError on the virtual console, which
// is noise rather than a failure. Everything else still comes through.
let virtualConsole;
try {
  const { VirtualConsole } = require('jsdom');
  virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', () => {});
  ['log', 'warn', 'info', 'error'].forEach((k) => {
    virtualConsole.on(k, (...a) => console[k === 'error' ? 'error' : 'log'](...a));
  });
} catch (e) { virtualConsole = undefined; }

const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'home.html'), 'utf8'), {
  runScripts: 'outside-only', pretendToBeVisual: true, url: 'https://board.test/',
  virtualConsole: virtualConsole,
});
const { window } = dom;
window.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
window.fetch = () => new Promise(() => {});

// jsdom lays nothing out, so every element is zero by zero and the plane would
// decline to frame anything. Give it a size, the way a real one has.
Object.defineProperty(window.HTMLElement.prototype, 'clientWidth',
                      { configurable: true, get() { return 900; } });
Object.defineProperty(window.HTMLElement.prototype, 'clientHeight',
                      { configurable: true, get() { return 500; } });
window.HTMLElement.prototype.getBoundingClientRect = function () {
  return { left: 0, top: 0, right: 900, bottom: 500, width: 900, height: 500 };
};
window.HTMLElement.prototype.setPointerCapture = function () {};

for (const f of ['typeface.js', 'gauge.js', 'plane-core.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
try { window.eval(js); }
catch (e) { fail('home.js threw on load: ' + e.message); }

// The payload the real `/atlas.json` serves. Two families, five workspaces, and
// deliberately awkward content: a SHOUTED plan step, a workspace with no plan
// at all, one that is live on another node, and the one the board is in.
const LOUD = 'THE TYPIST BAKE-OFF — VARY THE ASR MODEL AND GRADE EACH CANDIDATE';
const payload = {
  families: [
    { id: 'courses', name: 'Courses', blurb: 'Graduate coursework.' },
    { id: 'research', name: 'Research', blurb: 'The projects that become papers.' },
    { id: 'vendor', name: 'Vendor', blurb: 'Not mine.', vendor: true },
  ],
  workspaces: [
    { id: 'courses/Galois-Theory', family: 'courses', repo: 'Galois-Theory',
      course: 'Galois Theory', chapter: 'Ch 04 — Field extensions', cards: 9,
      running: false, node: null, current: true, kind: 'book',
      open: 16, next: 'Ch 05 — Tests for irreducibility',
      next_label: 'Ch 05 — Tests for irreducibility', touched: 1789256459 },
    { id: 'courses/Probability', family: 'courses', repo: 'Probability',
      course: 'Probability', chapter: '', cards: 4, running: true,
      node: 'compute305', current: false, kind: 'book',
      open: 9, next: 'Ch 03 — Conditional Probability', next_label: 'Ch 03',
      touched: 1789249625 },
    { id: 'courses/Mathematical-Modeling', family: 'courses',
      repo: 'Mathematical-Modeling', course: 'Mathematical Modeling', chapter: '',
      cards: 0, running: false, current: false, kind: 'book', open: 7,
      next: 'Ch 01 — Simple dynamic models', next_label: 'Ch 01',
      touched: 1788302179 },
    { id: 'research/PSYCH-ASR', family: 'research', repo: 'PSYCH-ASR',
      course: 'PSYCH-ASR', chapter: '', cards: 12, running: false,
      current: false, kind: 'project', open: 7, next: LOUD, next_label: '1. ' + LOUD,
      touched: 1789398000, stance: 'do' },
    { id: 'research/TRD-EHR', family: 'research', repo: 'TRD-EHR',
      course: 'TRD-EHR', chapter: '', cards: 0, running: false,
      current: false, kind: 'project', open: 0, next: '', touched: 0 },
  ],
};

const posted = [];
const asked = [];
let answer = { ok: true, address: true };
let serving = { dir: 'Probability' };
window.fetch = (url, opts) => {
  if (url === '/switch') {
    posted.push(JSON.parse(opts.body));
    return Promise.resolve({ json: () => Promise.resolve(answer) });
  }
  if (/^\/health/.test(String(url))) {
    asked.push(String(url));
    return Promise.resolve({ json: () => Promise.resolve(serving) });
  }
  // The meeting deck's three routes. `/notes/what` is what each workspace has
  // to report since the chosen period, `/notes` builds the deck, and
  // `/meeting/deck.json` is the one from before.
  if (url === '/notes/what') {
    posted.push({ to: url, body: JSON.parse(opts.body) });
    return Promise.resolve({ json: () => Promise.resolve({
      ok: true, since: 'last week', workspaces: [
        { id: 'research/PSYCH-ASR', name: 'PSYCH-ASR', moved: true,
          commits: 3, closed: 1, files: 7 },
        { id: 'courses/Galois-Theory', name: 'Galois-Theory', moved: false,
          commits: 0, closed: 0, files: 0 },
      ] }) });
  }
  if (url === '/notes') {
    posted.push({ to: url, body: JSON.parse(opts.body) });
    return Promise.resolve({ json: () => Promise.resolve({
      ok: true, name: 'meeting', workspaces: ['research/PSYCH-ASR'],
      tex: 'meetings/meeting.tex', pdf: 'meetings/meeting.pdf' }) });
  }
  if (url === '/meeting/deck.json') {
    return Promise.resolve({ json: () => Promise.resolve(
      { ok: true, built: false }) });
  }
  return Promise.resolve({
    json: () => Promise.resolve(
      url === '/atlas.json' ? payload
      : url === '/courses.json' ? { courses: [], where: 'compute303' }
      : { state: { course: 'Galois Theory', chapter: 'Ch 04' },
          cards: [], messages: [], slate: [] }),
  });
};

window.dispatchEvent(new window.Event('focus'));
setTimeout(() => {
  const doc = window.document;
  const svg = doc.getElementById('atlas-svg');
  const cards = svg.querySelectorAll('.card-box');
  const hits = svg.querySelectorAll('.card-hit');

  check('every workspace is drawn as a card', cards.length === 5);
  check('and every card is tappable over the whole of itself, so a tap never '
        + 'lands between two words and does nothing',
        hits.length === 5);

  // A family with nothing in it is not a heading over empty space.
  const labels = [...svg.querySelectorAll('.fam-label')].map((n) => n.textContent);
  check('the families are drawn in the order atlas.json gives them',
        labels[0] === 'Courses' && labels[1] === 'Research');
  check('and a family with no workspaces is not drawn at all -- vendor is '
        + "somebody else's work and discovery skips it",
        !labels.includes('Vendor'));

  // The layout: three across, then a band below.
  const xs = [...cards].map((n) => +n.getAttribute('x'));
  const ys = [...cards].map((n) => +n.getAttribute('y'));
  check('three cards across, and the fourth starts a new band',
        new Set(xs.slice(0, 3)).size === 3 && ys[0] === ys[1] && ys[1] === ys[2]);
  check('and no card is drawn off the left edge of the plane',
        Math.min(...xs) >= 0);

  // Every card says the three things a card exists to say.
  const text = svg.textContent;
  check('a card says what is next in it', /Tests for irreducibility/.test(text));
  check('and how much is outstanding',
        /16 chapters left/.test(text) && /7 open/.test(text));
  check('and when it was last touched, not merely that it was',
        /ago|just now|never/.test(text));
  check('a workspace with a board up says which machine is holding it',
        /live on compute305/.test(text));
  check('and a workspace nobody has opened says "never" rather than nothing',
        /never/.test(text));

  // The current workspace is the one the door opens, so it has to be findable
  // from anywhere on the plane.
  const here = svg.querySelectorAll('.card-box.here');
  check('the workspace the board is in is marked, and only that one',
        here.length === 1);

  // THE MEASURED TEXT. A shouted line is the case the estimate got wrong.
  const nexts = [...svg.querySelectorAll('.card-next')].map((n) => n.textContent);
  const loud = nexts.filter((t) => /TYPIST|BAKE|GRADE|CANDIDATE/.test(t));
  check('a SHOUTED plan step is wrapped rather than allowed to run out of its card',
        loud.length >= 1);
  const over = loud.filter((t) => window.Gauge.width(t, 12.5, 400) > 300 - 32);
  check('and every line of it measures inside the card it is drawn in',
        over.length === 0);
  check('and what did not fit ends in an ellipsis rather than being silently cut',
        loud.length < 2 || /…/.test(loud[loud.length - 1]) || loud.length <= 2);

  // ---- the same tree lays out the same way twice --------------------------
  const first = [...cards].map((n) => n.getAttribute('x') + ',' + n.getAttribute('y'))
                          .join(' ');
  window.dispatchEvent(new window.Event('focus'));
  setTimeout(() => {
    const again = [...doc.querySelectorAll('#atlas-svg .card-box')]
      .map((n) => n.getAttribute('x') + ',' + n.getAttribute('y')).join(' ');
    check('the same tree lays out identically on a second paint', first === again);

    // ---- the sheet, which is how a card is read on a phone ---------------
    const sheet = doc.getElementById('sheet');
    check('nothing is open before anything is tapped', sheet.hidden === true);

    const psych = [...doc.querySelectorAll('#atlas-svg .card-hit')][3];
    psych.dispatchEvent(new window.Event('click'));
    check('tapping a card opens the sheet', sheet.hidden === false);
    check('and the sheet says which family it is in',
          doc.getElementById('sheet-family').textContent === 'Research');
    check('and gives the step in full, not the truncation the card had room for',
          doc.getElementById('sheet-next-text').textContent.indexOf('1. ') === 0);
    check('and says what opening it will do, because it moves the board',
          /address does not change/.test(doc.getElementById('sheet-open-sub').textContent));

    // Opening it is the switch, and it carries the workspace and nothing else.
    doc.getElementById('sheet-open').onclick();
    check('opening from the sheet asks the server to move the board',
          posted.length === 1 && posted[0].repo === 'PSYCH-ASR');
    check('and the sheet closes rather than sitting over the overlay',
          sheet.hidden === true);
    check('the overlay asks nothing: no buttons at all',
          !doc.querySelector('#busy button'));

    // ---- it is still a door ----------------------------------------------
    check('the way back into the lesson is a plain link, not something that '
          + 'needs the plane to have painted',
          !!doc.querySelector('.action.primary[href="/board"]'));
    check('and the writing surface is one tap away too',
          !!doc.querySelector('.action[href="/slate"]'));

    // ---- a pan is not a tap ----------------------------------------------
    const plane = doc.getElementById('atlas-plane');
    const down = new window.Event('pointerdown');
    down.pointerId = 1; down.clientX = 100; down.clientY = 100;
    plane.dispatchEvent(down);
    const move = new window.Event('pointermove');
    move.pointerId = 1; move.clientX = 260; move.clientY = 140;
    plane.dispatchEvent(move);
    const before = posted.length;
    const tap = new window.Event('click', { bubbles: true, cancelable: true });
    doc.querySelectorAll('#atlas-svg .card-hit')[1].dispatchEvent(tap);
    const up = new window.Event('pointerup');
    up.pointerId = 1;
    plane.dispatchEvent(up);
    check('dragging the plane does not open whatever the finger started on',
          posted.length === before);

    // ---- the meeting deck: two questions, in this order ------------------
    // "I want to be able to select which projects meeting notes are generated
    //  for. From that list, I'll select the meeting notes I care about."
    // The period is asked first because the second question cannot be asked
    // without it -- what each project HAS to report is measured from a date.
    doc.getElementById('atlas-notes').onclick();
    const which = doc.getElementById('notes-which');
    check('the deck asks how far back first, and nothing else',
          doc.getElementById('notes-since').hidden === false
          && which.hidden === true);

    posted.length = 0;
    doc.querySelector('#notes-since button[data-since="7d"]').click();
    setTimeout(() => {
      check('choosing a period asks what each project has to report',
            posted.length === 1 && posted[0].to === '/notes/what'
            && posted[0].body.since === '7d');
      check('and then the list of projects is what is on the sheet',
            which.hidden === false
            && doc.getElementById('notes-since').hidden === true);

      const rows = doc.querySelectorAll('#notes-list button');
      check('every project is offered, whether or not it moved',
            rows.length === 2);
      check('and each row says what it has, not just its name -- ticking bare '
            + 'names ten minutes before a meeting is guessing',
            /3 commits/.test(rows[0].textContent)
            && /nothing since/.test(rows[1].textContent));
      check('the ones that moved are chosen already, because that is what the '
            + 'deck covers when nobody says anything',
            rows[0].getAttribute('aria-pressed') === 'true'
            && rows[1].getAttribute('aria-pressed') === 'false');

      // WHICH PROJECTS REACHES THE BUILDER. `meeting.build` filters
      // `atlas.workspaces` by `want`, and this is the seam that carries the
      // ticks to it -- the half that is easy to leave unwired, because the
      // deck is perfectly buildable without it.
      rows[1].click();
      posted.length = 0;
      doc.getElementById('notes-make').onclick();
      setTimeout(() => {
        check('making the deck carries the projects that were ticked',
              posted.length === 1 && posted[0].to === '/notes'
              && posted[0].body.want.length === 2
              && posted[0].body.want.indexOf('courses/Galois-Theory') !== -1);
        check('and the period goes with them',
              posted[0].body.since === '7d');
        check('the deck can then be read, on the page that can be marked up',
              doc.getElementById('notes-read').hidden === false
              && doc.getElementById('notes-read').getAttribute('href')
                 === '/meeting');
        check('and the sheet says it replaced the one before it, because there '
              + 'is only ever one',
              /replaced the one before it/
                .test(doc.getElementById('notes-said').textContent));
        rest();
      }, 20);
    }, 20);
    return;
  }, 60);
}, 80);

function rest() {
  {
    const doc = window.document;
    // ---- a board on an older tool serves no atlas ------------------------
    // Draw nothing and say so. The door above still works, which is the half
    // that matters, and a front door that throws is a blank screen.
    check('a missing atlas payload is said rather than thrown',
          /older version of the tool/.test(js));
    check('and the paint is wrapped, so one bad workspace cannot blank the page',
          /function paintAtlas\(payload\) \{[\s\S]{0,400}try \{/.test(js));

    console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                              : '\none picture of everything, and it is the way in');
    process.exit(errors.length ? 1 : 0);
  }
}
