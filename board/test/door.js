// A PAPER OR A DECK, COMMISSIONED FROM THE FRONT DOOR.
//
//     "These are tutoring styles that if you recall I don't want to be
//      selecting when I open up a lesson; I want to just change tutoring styles
//      to anything any time... The ability to write a paper or a slide deck
//      should just be an option on the homescreen, and from there I want to be
//      able to specify which projects/course, and which sections/results."
//
// A DOCUMENT IS NOT AN AIM. `paper` and `slides` were ways a sitting could be
// run, so asking for one meant being in a sitting in the workspace it is about
// -- and that workspace is usually not the one the board is serving. The ask
// cost a switch, a sitting, and a change to what the sitting was for, to
// produce a thing that never touches the lesson.
//
// So what this file guards is the client half of the front door's version:
//
//   * THREE QUESTIONS AND NOTHING ELSE -- which product, which workspace, what
//     it is over -- each replacing the last in one sheet, with a Back that
//     walks them in reverse.
//   * THE WORKSPACE LIST IS THE PAYLOAD THIS PAGE ALREADY POLLS. No request
//     behind it, and no vendor tree in it: nothing is handed in to somebody
//     else's repository.
//   * THE ASK CARRIES THE THREE ANSWERS AND INVENTS NOTHING. The scope is a key
//     the workspace handed out; the sentence it means is the server's to write.
//   * A REFUSAL REACHES THE GLASS. An assistant already busy answers 409 with a
//     sentence somebody can act on, and swallowing it leaves a tap that did
//     nothing.
//   * AND IT IS ONE MORE LAYER, NOT A REPLACEMENT. Escape takes the sheet off
//     and leaves the family under it open.
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

// ---- the sheet's own markup ----------------------------------------------
const block = html.slice(html.indexOf('<div id="doc" class="sheet"'),
                        html.indexOf('<div id="sheet" class="sheet"'));
check('the sheet is built in the conventions of the one beside it',
      /class="sheet-box"/.test(block) && /class="eyebrow"/.test(block)
      && /class="sheet-line"/.test(block) && /class="sheet-actions"/.test(block));
check('and its way out is an action rather than the dead class the deck closes '
      + 'with', !/sheet-open/.test(block)
      && /id="doc-close" class="action"/.test(block));

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
check('every colour this sheet uses is defined in the dark palette too',
      [...used].filter((n) => light.includes('--' + n + ':')
                           && !dark.includes('--' + n + ':')).length === 0);

// ---- drive the real page --------------------------------------------------
// A switch that lands ends in `location.href`, and jsdom has nowhere to
// navigate to -- it reports that as a jsdomError, which is noise rather than a
// failure.
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

// `address.js` is deliberately NOT loaded, for the reason `test/hub.js` leaves
// it out: with a grammar in the window, opening a workspace routes through the
// hash and lands a turn of the event loop later, which makes every count here a
// race. What is guarded is that the tap reaches `/switch` at all.
for (const f of ['typeface.js', 'recentre.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
try { window.eval(js); }
catch (e) { fail('home.js threw on load: ' + e.message); }

// The payload the real `/atlas.json` serves: two families of workspaces, the
// board's own with nothing under it, and a vendor family, which has TREES.
const payload = {
  families: [
    { id: 'courses', name: 'Courses',
      blurb: 'Graduate coursework, taught chapter by chapter.' },
    { id: 'research', name: 'Research', blurb: 'The projects that become papers.' },
    { id: 'board', name: 'The board', blurb: 'What does the offering.', tool: true },
    { id: 'vendor', name: 'Vendor', blurb: 'Pulled, not written.', vendor: true },
  ],
  workspaces: [
    { id: 'courses/Galois-Theory', family: 'courses', repo: 'Galois-Theory',
      course: 'Galois Theory', chapter: 'Ch 04 — Field extensions', cards: 9,
      running: false, current: true, kind: 'book', open: 16,
      next: 'Ch 05', next_label: 'Ch 05', touched: 1789256459 },
    { id: 'research/PSYCH-ASR', family: 'research', repo: 'PSYCH-ASR',
      course: 'PSYCH-ASR', chapter: '', cards: 12, running: false,
      current: false, kind: 'project', open: 7, next: 'the bake-off',
      next_label: '1. the bake-off', touched: 1789398000, stance: 'do' },
    // A VENDOR FAMILY'S WORKSPACE, in the list paintDocWhere actually reads.
    // Putting colibri only in `trees` made the check below pass whatever the
    // filter did: nothing on this page draws from that list.
    { id: 'vendor/colibri', family: 'vendor', repo: 'colibri',
      course: 'colibri', chapter: '', cards: 0, running: false,
      current: false, kind: 'project', open: 0, next: '', next_label: '',
      touched: 1789475941 },
  ],
  trees: [
    { id: 'vendor/colibri', family: 'vendor', repo: 'colibri', name: 'colibri',
      files: 250, capped: true, at: 'a8f2ca6', touched: 1789475941 },
  ],
};

// The two routes this sheet posts to, against the contract they are being built
// to. `/writeup/scopes` is what one workspace has to write up; `/writeup` is
// the ask itself.
const SCOPES = [
  { key: 'evening', label: 'the evening just taught',
    what: '4 cards since 18:02' },
  { key: 'results', label: 'the results', what: '3 figures, 2 tables' },
  { key: 'ch3', label: 'Ch 03 — Conditional probability', what: '11 cards' },
];
const posted = [];
let writeupAnswer = { ok: true, id: '0007', makes: 'slides', about: 'the results',
                      state: 'asked', detail: '', repo: 'PSYCH-ASR',
                      where: 'PSYCH-ASR' };
// HOW SLOWLY EACH WORKSPACE ANSWERS, so the two replies can be made to land in
// the order the disk gives them rather than the order they were asked in. A
// course with a plan and forty documents is genuinely slower than a project.
const scopeDelay = {};
let scopeAnswer = (id) => ({
  ok: true, repo: id.split('/').pop(), id: id,
  name: id.split('/').pop(), scopes: SCOPES });
window.fetch = (url, opts) => {
  const body = opts && opts.body ? JSON.parse(opts.body) : null;
  if (url === '/writeup/scopes') {
    posted.push({ to: url, body });
    const answer = scopeAnswer(body.repo);
    const wait = scopeDelay[body.repo] || 0;
    return new Promise((go) => setTimeout(
      () => go({ json: () => Promise.resolve(answer) }), wait));
  }
  if (url === '/writeup') {
    posted.push({ to: url, body });
    return Promise.resolve({ json: () => Promise.resolve(writeupAnswer) });
  }
  if (url === '/switch') {
    posted.push({ to: url, body });
    return Promise.resolve({ json: () => Promise.resolve({ ok: true }) });
  }
  if (/^\/health/.test(String(url))) {
    return Promise.resolve({ json: () => Promise.resolve({ dir: 'Galois-Theory' }) });
  }
  if (url === '/meeting/deck.json') {
    return Promise.resolve({ json: () => Promise.resolve({ ok: true, built: false }) });
  }
  return Promise.resolve({
    json: () => Promise.resolve(
      url === '/atlas.json' ? payload
      : url === '/courses.json' ? { courses: [], where: 'compute303' }
      : { state: { course: 'Galois Theory', chapter: 'Ch 04' },
          cards: [], messages: [], slate: [] }),
  });
};

const doc = window.document;
const el = (id) => doc.getElementById(id);
const rowsOf = (id) => [...el(id).querySelectorAll('button')];
const named = (b) => b.firstChild.textContent;

window.dispatchEvent(new window.Event('focus'));
setTimeout(step, 80);

function step() {
  // ---- it is at the door -------------------------------------------------
  const tool = el('atlas-doc');
  check('a paper or a deck is a tool on the front door, beside the notes',
        !!tool && tool.parentNode.className === 'atlas-tools');
  check('and it says what it makes rather than drawing a glyph',
        /paper/.test(tool.textContent) && /deck/.test(tool.textContent));
  const sheet = el('doc');
  check('nothing is open until it is tapped', sheet.hidden === true);
  tool.click();
  check('tapping it opens the sheet', sheet.hidden === false);

  // ---- question one: which of the two ------------------------------------
  const makes = rowsOf('doc-makes');
  check('the first question is which of the two, and it is two buttons rather '
        + 'than a question asked after the tap',
        makes.map((b) => b.getAttribute('data-makes')).join('|') === 'paper|slides');
  check('and nothing else is on the sheet yet',
        el('doc-where').hidden === true && el('doc-scopes').hidden === true);
  check('there is nowhere to go back to from the first question',
        el('doc-back').hidden === true);

  // ---- question two: which workspace -------------------------------------
  makes[1].click();
  check('choosing one asks which workspace, in place of the question before it',
        el('doc-where').hidden === false && el('doc-makes').hidden === true);
  check('and the title says which question is being asked',
        /workspace/i.test(el('doc-title').textContent));
  let where = rowsOf('doc-where');
  check('the workspaces are the payload this page already polls',
        where.map(named).join('|') === 'Galois Theory|PSYCH-ASR');
  check('and each one says which family it is in, because a name on its own is '
        + 'not a place', /Research/.test(where[1].textContent));
  check('the one the board is already serving says so',
        /where the board is/.test(where[0].textContent));
  check('no vendor tree is offered -- nothing is handed in to somebody else\'s '
        + 'repository', !/colibri/.test(el('doc-where').textContent));
  check('and nothing was fetched for a list that is already in memory',
        posted.length === 0);

  // ---- Back walks them in reverse ----------------------------------------
  el('doc-back').click();
  check('Back from the second question is the first one again, not the sheet '
        + 'closing',
        el('doc-makes').hidden === false && el('doc-where').hidden === true
        && sheet.hidden === false && el('doc-back').hidden === true);

  // ---- question three: what it is over -----------------------------------
  rowsOf('doc-makes')[1].click();
  where = rowsOf('doc-where');
  where[1].click();
  check('choosing a workspace asks it what it has to write up',
        posted.length === 1 && posted[0].to === '/writeup/scopes'
        && posted[0].body.repo === 'research/PSYCH-ASR');
  check('and says which workspace is being asked while it answers',
        el('doc-said').hidden === false
        && /PSYCH-ASR/.test(el('doc-said').textContent));
  setTimeout(scopes, 20);
}

function scopes() {
  check('what comes back is one button per scope, in the order it was given',
        rowsOf('doc-scopes').map((b) => b.getAttribute('data-scope')).join('|')
        === 'evening|results|ch3');
  check('and each says what it covers, not only its name',
        /3 figures, 2 tables/.test(rowsOf('doc-scopes')[1].textContent));
  check('the question before it is off the sheet',
        el('doc-where').hidden === true && el('doc-scopes').hidden === false);

  // Back again, one question at a time.
  el('doc-back').click();
  check('Back from the third question is the second, not the first',
        el('doc-where').hidden === false && el('doc-scopes').hidden === true
        && el('doc-makes').hidden === true);

  rowsOf('doc-where')[1].click();
  setTimeout(ask, 20);
}

function ask() {
  posted.length = 0;
  rowsOf('doc-scopes')[1].click();
  check('the ask carries what was chosen and nothing else',
        posted.length === 1 && posted[0].to === '/writeup'
        && Object.keys(posted[0].body).sort().join('|') === 'makes|repo|scope');
  check('which product, which workspace, which scope',
        posted[0].body.makes === 'slides'
        && posted[0].body.scope === 'results');
  // THE QUALIFIED NAME, NOT THE BARE DIRECTORY. A workspace is discovered
  // rather than registered, so two families can hold the same directory name
  // and both routes take the first walk hit for a bare one. The fixture's card
  // and its reply spell it differently on purpose: `family/name` is the
  // spelling the ask must carry, and it is the one the scopes reply gave.
  check('and the workspace is named the one way that cannot mean two places',
        posted[0].body.repo === 'research/PSYCH-ASR');
  check('nothing is written about what the scope MEANS -- that sentence is the '
        + 'server\'s', posted[0].body.about === undefined);
  setTimeout(landed, 20);
}

function landed() {
  check('what happened is said plainly: it is being written in that workspace',
        /being written in PSYCH-ASR/.test(el('doc-said').textContent));
  check('and that it will appear in that workspace\'s library rather than here',
        /library/.test(el('doc-said').textContent)
        && /not on this board/.test(el('doc-said').textContent));
  const read = el('doc-read');
  check('with the one tap that gets there',
        read.hidden === false
        && /moves the board/.test(el('doc-read-sub').textContent));
  posted.length = 0;
  read.click();
  check('and that tap moves the board first, the way Papers & decks does',
        posted.length === 1 && posted[0].to === '/switch'
        && posted[0].body.repo === 'PSYCH-ASR');
  check('the sheet closes behind it', el('doc').hidden === true);

  // ---- a refusal is painted rather than swallowed ------------------------
  // An assistant already busy in that workspace answers 409 with a sentence
  // about what it is doing, and that is something a person can act on.
  writeupAnswer = { ok: false,
                    error: 'PSYCH-ASR is mid-run on the bake-off; ask again '
                           + 'when it lands' };
  el('atlas-doc').click();
  rowsOf('doc-makes')[0].click();
  rowsOf('doc-where')[1].click();
  setTimeout(() => {
    rowsOf('doc-scopes')[0].click();
    setTimeout(() => {
      check('a refusal reaches the glass in the words it came in',
            /mid-run on the bake-off/.test(el('doc-said').textContent));
      check('and is marked as one rather than read as progress',
            /\bbad\b/.test(el('doc-said').className)
            && el('doc-read').hidden === true);
      check('the scopes are tappable again, because the ask can be made twice',
            rowsOf('doc-scopes').every((b) => b.disabled === false));
      race();
    }, 20);
  }, 20);
}

// ---- two workspaces asked, and the slow one cannot repaint the fast one ----
//
// Opening the wrong workspace and then the right one is two taps and is the
// ordinary case. The replies come back in whatever order the disk gives them,
// so without a token the late one repaints the list and the ask goes to a
// workspace whose name is nowhere on the glass.
function race() {
  el('doc-close').click();
  el('atlas-doc').click();
  rowsOf('doc-makes')[0].click();
  scopeDelay['courses/Galois-Theory'] = 60;
  scopeAnswer = (id) => (id === 'courses/Galois-Theory'
    ? { ok: true, repo: 'Galois-Theory', id: 'courses/Galois-Theory',
        name: 'Galois Theory',
        scopes: [{ key: 'ch04', label: 'Ch 04', what: 'a chapter' }] }
    : { ok: true, repo: 'PSYCH-ASR', id: 'research/PSYCH-ASR',
        name: 'PSYCH-ASR', scopes: SCOPES });
  rowsOf('doc-where')[0].click();          // the slow one
  el('doc-back').click();
  rowsOf('doc-where')[1].click();          // the one actually wanted
  setTimeout(() => {
    check('the workspace that was abandoned cannot repaint the list it left',
          rowsOf('doc-scopes').map((b) => b.getAttribute('data-scope'))
            .join('|') === 'evening|results|ch3');
    posted.length = 0;
    rowsOf('doc-scopes')[0].click();
    check('and the ask goes to the workspace whose scopes are on the glass',
          posted.length === 1 && posted[0].body.repo === 'research/PSYCH-ASR');
    scopeDelay['courses/Galois-Theory'] = 0;
    setTimeout(capped, 20);
  }, 120);
}

// ---- and a list that stops short says so ----------------------------------
function capped() {
  el('doc-close').click();
  scopeAnswer = () => ({ ok: true, repo: 'PSYCH-ASR', id: 'research/PSYCH-ASR',
                         name: 'PSYCH-ASR', scopes: SCOPES, more: 8 });
  el('atlas-doc').click();
  rowsOf('doc-makes')[0].click();
  rowsOf('doc-where')[1].click();
  setTimeout(() => {
    check('a picker that stops at a cap says how much it is not offering',
          /8 more are not offered/.test(el('doc-said').textContent));
    check('and still offers what it has', rowsOf('doc-scopes').length === 3);
    rest();
  }, 20);
}

function rest() {
  // ---- it is one more layer, not a replacement --------------------------
  // Escape unwinds one thing at a time. Taking the family off with the sheet is
  // how somebody ends up two screens from where they were and cannot say which
  // tap did it.
  el('doc-close').click();
  [...doc.querySelectorAll('#doors .door')]
    .filter((b) => b.querySelector('.door-name').textContent === 'Research')[0]
    .dispatchEvent(new window.Event('click'));
  el('atlas-doc').click();
  doc.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape' }));
  check('Escape takes the sheet off',
        el('doc').hidden === true);
  check('and leaves the family that was open under it open',
        el('cards').hidden === false && el('doors').hidden === true);
  doc.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape' }));
  check('the next one comes out of the family, which is the order the chain '
        + 'was in before this sheet joined it',
        el('doors').hidden === false && el('cards').hidden === true);

  // ---- and the paint is still the paint ---------------------------------
  check('nothing here is painted from anything but the atlas payload',
        !/\/atlas\.json/.test(js.slice(js.indexOf('function paintDocWhere'),
                                       js.indexOf('function docAskScopes'))));

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\nthree questions, and the document is written '
                              + 'where the work is');
  process.exit(errors.length ? 1 : 0);
}
