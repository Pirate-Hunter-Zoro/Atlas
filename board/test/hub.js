// THE FRONT DOOR, AND IT IS THREE LEVELS RATHER THAN A PLANE.
//
// This page used to end in ONE SVG plane -- a region per family, a card per
// workspace -- panned and pinched, with a `fit` button because it could not be
// seen at once. That was rejected in these terms:
//
//     "It's just an ugly grid of projects in an inner box that has wacky
//      zooming. On the homescreen, I want a nice 'Research' option, 'Courses'
//      option, and 'Projects' option, and honestly something pertaining to
//      vendor/ as well... When I select one of those four options, I want to
//      see all available projects/courses/research projects/vendor tools
//      portrayed in again a visually pleasing way, and then we can go into an
//      individual project map."
//
// Six families and a dozen workspaces is a list of six, and drawing a list on a
// plane is what produced the wacky zooming: the gesture layer was solving a
// problem the content did not have. So what this file guards is:
//
//   * THREE LEVELS, AND THE TOP TWO ARE NOT PLANES. The door is the families,
//     the family is its workspaces, and the project map -- which is the one
//     thing here whose shape needs a plane -- is on the board. No pan, no
//     pinch, no fit, and no measuring on either of the two here.
//   * THE SENTENCES IN `atlas.json` REACH THE GLASS. They existed all along and
//     the drawn version used them as nothing but a heading.
//   * A SHOUTED PLAN STEP STILL FITS. It used to be measured through `gauge.js`
//     and clipped; the browser wraps it now, which is why this level stopped
//     being a plane, and a regression here is a label out of its box again.
//   * A VENDOR TREE IS DRAWN AND IS NOT A WORKSPACE. Read and diagrammed, never
//     handed work: no board to move, no library, nothing to open.
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
const html = fs.readFileSync(path.join(WEB, 'home.html'), 'utf8');

// ---- neither of the two levels here is a plane ----------------------------
// Asserted against the source, because a jsdom window has one size and could
// never catch this by rendering. A plane is three things -- a surface that owns
// its own gestures, the code that reads them, and the scripts that provide them
// -- and all three had to go, or the next change puts one of them back.
check('the front door loads no gesture layer at all',
      !/plane-core\.js/.test(html));
check('and no text measurer, because the browser wraps the text now',
      !/gauge\.js/.test(html) && !/Gauge\./.test(js));
check('no surface on the front door takes the browser\'s touches away',
      !/touch-action:\s*none/.test(css.replace(/#panic \{[^}]*\}/g, '')));
check('nothing here pans, pinches or wheels',
      !/pointerdown|pointermove|zoomAbout|Plane\./.test(js));
check('and there is no fit button, because there is nothing to fit',
      !/atlas-fit/.test(html) && !/atlasback/.test(html));

// The number of things across is the browser's business. The old plane worked
// it out itself so the picture would lay out identically on every device, which
// is the right promise kept by the wrong thing.
check('how many go across is a media query, not a constant in JavaScript',
      /@media \(min-width: [\d.]+rem\) \{ \.doors/.test(css)
      && /@media \(min-width: [\d.]+rem\) \{ \.cards/.test(css)
      && !/A_ACROSS/.test(js));

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

const dom = new JSDOM(html, {
  runScripts: 'outside-only', pretendToBeVisual: true, url: 'https://board.test/',
  virtualConsole: virtualConsole,
});
const { window } = dom;
window.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
window.fetch = () => new Promise(() => {});

// jsdom lays nothing out, so every element is zero by zero.
Object.defineProperty(window.HTMLElement.prototype, 'clientWidth',
                      { configurable: true, get() { return 900; } });
Object.defineProperty(window.HTMLElement.prototype, 'clientHeight',
                      { configurable: true, get() { return 500; } });
window.HTMLElement.prototype.getBoundingClientRect = function () {
  return { left: 0, top: 0, right: 900, bottom: 500, width: 900, height: 500 };
};
window.HTMLElement.prototype.setPointerCapture = function () {};

// `address.js` is deliberately NOT loaded. With a grammar in the window,
// opening a workspace goes through the hash and lands one turn of the event
// loop later, which is correct behaviour and makes every count below a race.
// The grammar has `test/address.js`; what is guarded here is that the button
// reaches `/switch` at all, which is the half that matters when a cached older
// shell has no grammar to route through.
for (const f of ['typeface.js', 'recentre.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
try { window.eval(js); }
catch (e) { fail('home.js threw on load: ' + e.message); }

// The payload the real `/atlas.json` serves. Four families -- one of them the
// board's own, which has nothing under it, and one of them vendor, which has
// TREES rather than workspaces -- and deliberately awkward content: a SHOUTED
// plan step, a workspace with no plan at all, one live on another node, and the
// one the board is in.
const LOUD = 'THE TYPIST BAKE-OFF — VARY THE ASR MODEL AND GRADE EACH CANDIDATE';
const payload = {
  families: [
    { id: 'courses', name: 'Courses',
      blurb: 'Graduate coursework, taught chapter by chapter.' },
    { id: 'research', name: 'Research',
      blurb: 'The projects that become papers.' },
    { id: 'board', name: 'The board', blurb: 'What does the offering.', tool: true },
    { id: 'vendor', name: 'Vendor',
      blurb: 'Pulled, not written. Tracked by pointer at a commit.', vendor: true },
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
      touched: 1789398000, stance: 'do', news: true, news_at: 1789398000 },
    { id: 'research/TRD-EHR', family: 'research', repo: 'TRD-EHR',
      course: 'TRD-EHR', chapter: '', cards: 0, running: false,
      current: false, kind: 'project', open: 0, next: '', touched: 0 },
  ],
  trees: [
    { id: 'vendor/colibri', family: 'vendor', repo: 'colibri', name: 'colibri',
      files: 250, capped: true, at: 'a8f2ca6', touched: 1789475941 },
    { id: 'vendor/colibri-build', family: 'vendor', repo: 'colibri-build',
      name: 'colibri-build', files: 118, capped: false, at: 'fd93c41',
      touched: 1788716809 },
  ],
};

const posted = [];
let answer = { ok: true, address: true };
let serving = { dir: 'Probability' };
window.fetch = (url, opts) => {
  if (url === '/switch') {
    posted.push(JSON.parse(opts.body));
    return Promise.resolve({ json: () => Promise.resolve(answer) });
  }
  if (/^\/health/.test(String(url))) {
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

  // ---- LEVEL ONE: the door ----------------------------------------------
  const doors = [...doc.querySelectorAll('#doors .door')];
  const names = doors.map((b) => b.querySelector('.door-name').textContent);
  check('the door is the families, drawn in the order atlas.json gives them',
        names.join('|') === 'Courses|Research|Vendor');
  check('and a family with nothing in it is not a door -- the board is what '
        + 'does the offering, not one of the things offered',
        !names.includes('The board'));

  // THE SENTENCES THAT WERE ALREADY IN `atlas.json`. They existed and the drawn
  // version used them as nothing but a heading.
  const blurbs = doors.map((b) => (b.querySelector('.door-blurb') || {}).textContent);
  check('each door says what the family is, in the sentence atlas.json carries',
        blurbs[0] === 'Graduate coursework, taught chapter by chapter.'
        && blurbs[1] === 'The projects that become papers.');
  check('and what is true inside it right now, in names and numbers',
        /3 courses/.test(doors[0].querySelector('.door-line').textContent)
        && /1 live/.test(doors[0].querySelector('.door-line').textContent)
        && /an answer waiting/.test(doors[1].querySelector('.door-line').textContent));
  check('the family holding the workspace the board is in is marked, and only '
        + 'that one, so the way back is visible before the first tap',
        doors.filter((b) => b.classList.contains('here')).length === 1
        && doors[0].classList.contains('here'));
  check('nothing below the door is showing until one is tapped',
        doc.getElementById('cards').hidden === true
        && doc.getElementById('atlas-up').hidden === true);

  // ---- LEVEL TWO: one family --------------------------------------------
  doors[1].dispatchEvent(new window.Event('click'));
  check('tapping a door shows that family and hides the others',
        doc.getElementById('doors').hidden === true
        && doc.getElementById('cards').hidden === false);
  check('and the head says which family you are in, with its own sentence',
        doc.getElementById('atlas-what').textContent === 'Research'
        && doc.getElementById('atlas-blurb').textContent
           === 'The projects that become papers.');
  check('and there is a way back to all of it',
        doc.getElementById('atlas-up').hidden === false);

  let cards = [...doc.querySelectorAll('#cards .ws-card')];
  check('every workspace in that family is a card, and only that family\'s',
        cards.map((c) => c.querySelector('.ws-name').textContent).join('|')
        === 'PSYCH-ASR|TRD-EHR');

  const text = doc.getElementById('cards').textContent;
  check('a card says what is next in it', /TYPIST BAKE-OFF/.test(text));
  check('and how much is outstanding', /7 open/.test(text) && /12 cards/.test(text));
  check('and when it was last touched, not merely that it was',
        /ago|just now/.test(text));
  check('and a workspace nobody has opened says "never" rather than nothing',
        /never/.test(text));
  check('an answer nobody has read is marked on the card it landed in',
        cards[0].classList.contains('news')
        && !!cards[0].querySelector('.ws-dot.news'));

  // THE SHOUTED STEP. It used to be measured through `gauge.js` and clipped to
  // two lines, and a line of capitals is half again wider than characters times
  // a constant -- which is exactly how the labels came to run out of their
  // boxes. The browser wraps it now, so the whole of it is on the card and the
  // clamp that keeps it to three lines is CSS.
  const loud = cards[0].querySelector('.ws-next').textContent;
  check('a SHOUTED plan step reaches the card whole rather than being measured '
        + 'and cut', loud === LOUD);
  check('and it is the browser that decides how many lines of it fit',
        /-webkit-line-clamp: 3/.test(css)
        && /\.ws-next \{[^}]*overflow: hidden/.test(css));

  // ---- the sheet, which is how a card is read on a phone -----------------
  const sheet = doc.getElementById('sheet');
  check('nothing is open before a card is tapped', sheet.hidden === true);
  cards[0].dispatchEvent(new window.Event('click'));
  check('tapping a card opens the sheet', sheet.hidden === false);
  check('and the sheet says which family it is in',
        doc.getElementById('sheet-family').textContent === 'Research');
  check('and gives the step in full, not the truncation the card had room for',
        doc.getElementById('sheet-next-text').textContent.indexOf('1. ') === 0);
  check('and says what opening it will do, because it moves the board',
        /address does not change/.test(doc.getElementById('sheet-open-sub').textContent));

  doc.getElementById('sheet-open').onclick();
  check('opening from the sheet asks the server to move the board',
        posted.length === 1 && posted[0].repo === 'PSYCH-ASR');
  check('and the sheet closes rather than sitting over the overlay',
        sheet.hidden === true);
  check('the overlay asks nothing: no buttons at all',
        !doc.querySelector('#busy button'));

  // ---- a vendor tree is drawn, and is not a workspace -------------------
  // `atlas.json` made one claim out of two: the family was skipped because
  // nothing in it is the person's to be GRADED on. The ask was about TRACING.
  // The two are split, and this is the half that reaches the glass.
  doc.getElementById('atlas-up').onclick();
  const vendor = [...doc.querySelectorAll('#doors .door')]
    .filter((b) => b.querySelector('.door-name').textContent === 'Vendor')[0];
  check('vendor is a door like any other, which it was not before',
        !!vendor && /2 trees/.test(vendor.querySelector('.door-line').textContent));
  vendor.dispatchEvent(new window.Event('click'));
  cards = [...doc.querySelectorAll('#cards .ws-card')];
  check('and its trees are drawn',
        cards.map((c) => c.querySelector('.ws-name').textContent).join('|')
        === 'colibri|colibri-build');
  const tree = cards[0].querySelector('.ws-meta').textContent;
  check('a tree says the commit it is at and how much source is in it, which '
        + 'is all that is true about something pulled rather than written',
        /at a8f2ca6/.test(tree) && /250\+ source files/.test(tree));
  check('and a cap is said rather than quoted as a count',
        /250\+/.test(tree)
        && /118 source files/.test(cards[1].querySelector('.ws-meta').textContent));
  cards[0].dispatchEvent(new window.Event('click'));
  check('its sheet offers no board to move and no library, because nothing is '
        + 'handed in to somebody else\'s repository',
        doc.getElementById('sheet-open').hidden === true
        && doc.getElementById('sheet-library').hidden === true);
  check('and says so in words rather than leaving it to be discovered',
        /pulled, not written/.test(doc.getElementById('sheet-meta').textContent)
        && /never handed work/.test(doc.getElementById('sheet-meta').textContent));
  doc.getElementById('sheet-close').onclick();

  // ---- it is still a door ----------------------------------------------
  check('the way back into the lesson is a plain link, not something that '
        + 'needs a level to have painted',
        !!doc.querySelector('.action.primary[href="/board"]'));
  check('and the writing surface is one tap away too',
        !!doc.querySelector('.action[href="/slate"]'));

  // ---- the meeting deck: two questions, in this order ------------------
  doc.getElementById('atlas-up').onclick();
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
    check('every project is offered, whether or not it moved', rows.length === 2);
    check('and each row says what it has, not just its name -- ticking bare '
          + 'names ten minutes before a meeting is guessing',
          /3 commits/.test(rows[0].textContent)
          && /nothing since/.test(rows[1].textContent));
    check('the ones that moved are chosen already, because that is what the '
          + 'deck covers when nobody says anything',
          rows[0].getAttribute('aria-pressed') === 'true'
          && rows[1].getAttribute('aria-pressed') === 'false');

    rows[1].click();
    posted.length = 0;
    doc.getElementById('notes-make').onclick();
    setTimeout(() => {
      check('making the deck carries the projects that were ticked',
            posted.length === 1 && posted[0].to === '/notes'
            && posted[0].body.want.length === 2
            && posted[0].body.want.indexOf('courses/Galois-Theory') !== -1);
      check('and the period goes with them', posted[0].body.since === '7d');
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
}, 80);

function rest() {
  // ---- a board on an older tool serves no atlas ------------------------
  // Draw nothing and say so. The door above still works, which is the half
  // that matters, and a front door that throws is a blank screen.
  check('a missing atlas payload is said rather than thrown',
        /older version of the tool/.test(js));
  check('and the paint is wrapped, so one bad workspace cannot blank the page',
        /function paintAtlas\(payload\) \{[\s\S]{0,600}try \{/.test(js));
  check('and what it said survives the next poll rather than being wiped by it',
        /atlasSaid/.test(js));

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\nthree levels, and the top two are not planes');
  process.exit(errors.length ? 1 : 0);
}
