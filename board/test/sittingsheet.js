// SLIDES FROM SITTINGS, FROM THE FRONT DOOR.
//
//     "I just want to be able to select from tutoring sessions what we've done
//      over all sessions and get to pick a list of the things I want to include
//      in the presentation. I leave it up to the AI tutor to actually decide
//      what slides are dedicated to which things accomplished... I don't want
//      to be limited to one slide per project."
//
// The client half. What it guards:
//
//   * IT IS AT THE DOOR, and says what it makes rather than drawing a glyph.
//   * THREE STEPS IN ONE SHEET -- which sittings, what goes in, being written --
//     each replacing the last, and Back walks them in reverse.
//   * EVERY SITTING, GROUPED BY WORKSPACE, with what each one holds beside it;
//     past the fold the older ones are one tap away, and tickable.
//   * WHAT THEY DID ARRIVES TICKED, so the list narrows a decision, and one tap
//     unticks a whole sitting's worth.
//   * THE ASK CARRIES IDS AND NOTHING ELSE: the sittings picked and the items
//     left ticked. Nothing about slides is decided here.
//   * A REFUSAL REACHES THE GLASS in the words it came in.
//   * THE SHEET SAYS WHEN THE DECK IS THERE, and "Read the deck" moves the board
//     to the workspace it was written in and opens it in that library.
//   * A LATE ANSWER CANNOT REPAINT A STEP THAT WAS LEFT.
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
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const js = fs.readFileSync(path.join(WEB, 'home.js'), 'utf8');
const html = fs.readFileSync(path.join(WEB, 'home.html'), 'utf8');

// ---- the sheet's own markup ----------------------------------------------
const block = html.slice(html.indexOf('<div id="sittings" class="sheet"'),
                         html.indexOf('<div id="sheet" class="sheet"'));
check('the sheet is built in the conventions of the ones beside it',
      /class="sheet-box"/.test(block) && /class="eyebrow">Slides from sittings</.test(block)
      && /class="sheet-line"/.test(block) && /class="sheet-actions"/.test(block));

// A switch ends in `location.href`, which jsdom reports as a navigation it has
// not implemented. Counted, because that is the only trace a navigation leaves.
let navigations = 0;
const { VirtualConsole } = require('jsdom');
const virtualConsole = new VirtualConsole();
virtualConsole.on('jsdomError', (e) => {
  if (/navigation/i.test(String(e && e.message))) navigations += 1;
});

const dom = new JSDOM(html, {
  runScripts: 'outside-only', pretendToBeVisual: true, url: 'https://board.test/',
  virtualConsole: virtualConsole,
});
const { window } = dom;
window.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
Object.defineProperty(window.HTMLElement.prototype, 'clientWidth',
                      { configurable: true, get() { return 900; } });
Object.defineProperty(window.HTMLElement.prototype, 'clientHeight',
                      { configurable: true, get() { return 500; } });
window.HTMLElement.prototype.getBoundingClientRect = function () {
  return { left: 0, top: 0, right: 900, bottom: 500, width: 900, height: 500 };
};

// THE POLL, taken in hand. It runs every ten seconds in the page; here it is
// run when the test says, so "being written" and "Ready" are two checks rather
// than a race against a clock.
const intervals = [];
const realInterval = window.setInterval.bind(window);
window.setInterval = (fn, ms) => {
  if (ms === 10000) { intervals.push(fn); return 99; }
  return realInterval(fn, ms);
};

const payload = {
  families: [{ id: 'courses', name: 'Courses' }, { id: 'research', name: 'Research' }],
  workspaces: [
    { id: 'courses/Galois-Theory', family: 'courses', repo: 'Galois-Theory',
      course: 'Galois Theory', chapter: 'Ch 05', cards: 17, running: false,
      current: true, kind: 'book', open: 3, next: '', next_label: '', touched: 1 },
    { id: 'research/TRD-EHR', family: 'research', repo: 'TRD-EHR',
      course: 'TRD-EHR', chapter: 'predictions', cards: 5, running: false,
      current: false, kind: 'project', open: 4, next: '', next_label: '', touched: 1 },
  ],
  trees: [],
};

const SITTINGS = {
  ok: true, fold: 2,
  sittings: [
    { id: 'research/TRD-EHR@live', ws: 'research/TRD-EHR', ws_name: 'TRD-EHR',
      label: 'predictions (open now)', cards: 5, commits: 0, fenced: [] },
    { id: 'research/TRD-EHR@20260920-110649-predictions', ws: 'research/TRD-EHR',
      ws_name: 'TRD-EHR', label: 'predictions (3 sittings, 2026-09-20 to 2026-09-24)',
      cards: 9, commits: 3, fenced: [] },
    { id: 'research/TRD-EHR@20260901-100000-knn', ws: 'research/TRD-EHR',
      ws_name: 'TRD-EHR', label: 'knn (2026-09-01)', cards: 4, commits: 2,
      fenced: [] },
    { id: 'courses/Galois-Theory@live', ws: 'courses/Galois-Theory',
      ws_name: 'Galois Theory', label: 'Ch 05 — Tests for irreducibility (open now)',
      cards: 17, commits: 1, fenced: [] },
  ],
};
const GROUPS = {
  ok: true,
  groups: [{
    sitting: 'research/TRD-EHR@20260920-110649-predictions', ws_name: 'TRD-EHR',
    label: 'predictions (3 sittings, 2026-09-20 to 2026-09-24)',
    items: [
      { id: 'aaaaaaaaaa', sitting: 'x', kind: 'commit', detail: 'c267ec57',
        text: 'Weight the KNN metric by logistic-regression importance, and sweep k' },
      { id: 'bbbbbbbbbb', sitting: 'x', kind: 'handoff', detail: 'Where this got to',
        text: 'ROC AUC 0.625 against plain cosine\'s 0.594.' },
      { id: 'cccccccccc', sitting: 'x', kind: 'whole', detail: '',
        text: 'Everything this sitting covered (9 cards)' },
    ],
  }],
};

const posted = [];
let deckAnswer = { ok: false, error: 'claude is on a mission in TRD-EHR -- ask '
                                    + 'again when it lands' };
let decksAnswer = { ok: true, decks: [
  { title: 'Rings, briefly', slug: 'deck-260901-1000', host: 'Galois-Theory',
    host_id: 'courses/Galois-Theory', host_name: 'Galois Theory', state: 'ready',
    doc: 'writeups-deck-260901-1000-deck-260901-10', at: 1 },
] };
let itemsDelay = 0;
window.fetch = (url, opts) => {
  const body = opts && opts.body ? JSON.parse(opts.body) : null;
  const answer = (x, wait) => new Promise((go) => setTimeout(
    () => go({ json: () => Promise.resolve(x) }), wait || 0));
  if (/^\/sittings/.test(String(url)) || url === '/switch') {
    posted.push({ to: url, body });
  }
  if (url === '/sittings') return answer(SITTINGS);
  if (url === '/sittings/items') return answer(GROUPS, itemsDelay);
  if (url === '/sittings/deck') return answer(deckAnswer);
  if (url === '/sittings/decks') return answer(decksAnswer);
  if (url === '/switch') return answer({ ok: true });
  if (/^\/health/.test(String(url))) return answer({ dir: 'TRD-EHR' });
  if (url === '/meeting/deck.json') return answer({ ok: true, built: false });
  return answer(url === '/atlas.json' ? payload
    : url === '/courses.json' ? { courses: [], where: 'compute303' }
    : { state: { course: 'Galois Theory', chapter: 'Ch 05' },
        cards: [], messages: [], slate: [] });
};

for (const f of ['typeface.js', 'recentre.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
try { window.eval(js); }
catch (e) { fail('home.js threw on load: ' + e.message); }

const doc = window.document;
const el = (id) => doc.getElementById(id);
const rows = (id) => [...el(id).querySelectorAll('button[data-id]')];
const sent = (to) => posted.filter((p) => p.to === to);
const poll = () => intervals.forEach((fn) => fn());

(async function () {
  window.dispatchEvent(new window.Event('focus'));
  await sleep(60);

  // ---- it is at the door --------------------------------------------------
  const tool = el('atlas-sittings');
  check('slides from sittings is a tool on the front door, beside the other two',
        !!tool && tool.parentNode.className === 'atlas-tools'
        && tool.previousElementSibling === el('atlas-doc'));
  check('and it says what it makes', tool.textContent === 'slides from sittings');
  check('nothing is open until it is tapped', el('sittings').hidden === true);

  tool.click();
  check('tapping it opens the sheet on the first question',
        el('sittings').hidden === false
        && el('sittings-title').textContent === 'Which sittings?');
  check('and asks the server for every sitting', sent('/sittings').length === 1);
  await sleep(30);

  // ---- step one: which sittings -------------------------------------------
  const heads = [...el('sittings-list').querySelectorAll('.sittings-group')]
    .map((h) => h.textContent);
  check('the sittings are grouped under their workspace, in the order sent',
        heads.join('|') === 'TRD-EHR|Galois Theory');
  check('each row says what it holds',
        /9 cards · 3 commits/.test(rows('sittings-list')[1].textContent)
        && /5 cards$/.test(rows('sittings-list')[0].textContent));
  const fold = el('sittings-list').querySelector('button.sittings-more');
  check('past the fold a workspace\'s older sittings are folded, one tap away',
        rows('sittings-list').length === 3 && !!fold
        && fold.textContent === 'show 1 older sitting'
        && !/knn \(2026-09-01\)/.test(el('sittings-list').textContent));
  fold.click();
  check('and the tap shows them under their own workspace, tickable',
        rows('sittings-list').length === 4
        && rows('sittings-list')[2].getAttribute('data-id')
           === 'research/TRD-EHR@20260901-100000-knn'
        && !el('sittings-list').querySelector('button.sittings-more'));
  rows('sittings-list')[2].click();
  check('an old sitting ticks like any other',
        el('sittings-go-name').textContent === 'Show what was done in 1 sitting');
  rows('sittings-list')[2].click();
  check('the decks already made are offered first, with a way to read one',
        el('sittings-decks').hidden === false
        && /Rings, briefly · Galois Theory · ready/.test(el('sittings-decks').textContent)
        && [...el('sittings-decks').querySelectorAll('button')]
          .some((b) => b.textContent === 'Read it'));
  check('nothing is ticked, and the way on says so',
        el('sittings-go').disabled === true
        && el('sittings-go-name').textContent === 'Show what was done in 0 sittings');

  rows('sittings-list')[1].click();
  check('ticking one says how many and lets the sheet go on',
        el('sittings-go').disabled === false
        && el('sittings-go-name').textContent === 'Show what was done in 1 sitting'
        && rows('sittings-list')[1].getAttribute('aria-pressed') === 'true');

  // ---- a late answer cannot repaint a step that was left -------------------
  itemsDelay = 60;
  el('sittings-go').click();
  check('the ask carries the picks and nothing else',
        sent('/sittings/items').length === 1
        && JSON.stringify(sent('/sittings/items')[0].body)
        === JSON.stringify({ picks: ['research/TRD-EHR@20260920-110649-predictions'] }));
  el('sittings-close').click();
  tool.click();
  await sleep(120);
  check('an answer for a sheet that was closed and opened again is dropped',
        el('sittings-title').textContent === 'Which sittings?'
        && el('sittings-what').hidden === true);
  itemsDelay = 0;

  // ---- step two: what goes in -----------------------------------------------
  rows('sittings-list')[1].click();
  el('sittings-go').click();
  await sleep(30);
  check('what they did replaces the list, under its own question',
        el('sittings-title').textContent === 'What goes in the deck?'
        && el('sittings-pick').hidden === true && el('sittings-what').hidden === false);
  check('every item arrives ticked',
        rows('sittings-items').length === 3
        && rows('sittings-items').every((b) => b.getAttribute('aria-pressed') === 'true'));
  const all = el('sittings-items').querySelector('button.sittings-all');
  check('each sitting has one tap to untick all of it',
        !!all && all.textContent === 'untick all of these');
  all.click();
  check('which unticks every item under it and says the way on is shut',
        rows('sittings-items').every((b) => b.getAttribute('aria-pressed') === 'false')
        && el('sittings-go').disabled === true
        && all.textContent === 'tick all of these');
  all.click();
  check('and taps back to all of them',
        rows('sittings-items').every((b) => b.getAttribute('aria-pressed') === 'true')
        && el('sittings-go-name').textContent === 'Write the deck (3 things)');
  check('each says where it came from',
        /commit c267ec57/.test(rows('sittings-items')[0].textContent)
        && /from the handoff · Where this got to/.test(rows('sittings-items')[1].textContent));
  check('the way on says how many things will go in',
        el('sittings-go-name').textContent === 'Write the deck (3 things)');
  rows('sittings-items')[2].click();
  check('unticking one leaves it out',
        el('sittings-go-name').textContent === 'Write the deck (2 things)');

  // ---- Back walks them in reverse -----------------------------------------
  el('sittings-back').click();
  check('Back from the second step is the first, with the tick kept',
        el('sittings-title').textContent === 'Which sittings?'
        && rows('sittings-list')[1].getAttribute('aria-pressed') === 'true');
  el('sittings-go').click();
  await sleep(30);
  rows('sittings-items')[2].click();

  // ---- a refusal reaches the glass --------------------------------------
  el('sittings-go').click();
  check('the deck is asked for with the picks and the ticked items, and '
        + 'nothing about slides',
        sent('/sittings/deck').length === 1
        && Object.keys(sent('/sittings/deck')[0].body).sort().join('|') === 'items|picks'
        && sent('/sittings/deck')[0].body.items.join('|') === 'aaaaaaaaaa|bbbbbbbbbb');
  await sleep(30);
  check('a refusal is painted in the words it came in, as one',
        /on a mission in TRD-EHR/.test(el('sittings-said').textContent)
        && /\bbad\b/.test(el('sittings-said').className)
        && el('sittings-title').textContent === 'What goes in the deck?');

  // ---- step three: being written, then ready ---------------------------
  deckAnswer = { ok: true, id: 't0050', slug: 'deck-260924-1830',
                 host: 'research/TRD-EHR', repo: 'TRD-EHR', where: 'TRD-EHR',
                 detail: 'The tutor is writing it in TRD-EHR. It takes several '
                   + 'minutes and this sheet says when it is ready.' };
  decksAnswer = { ok: true, decks: [
    { title: 'TRD-EHR: 2 things from 1 sitting', slug: 'deck-260924-1830',
      host: 'TRD-EHR', host_id: 'research/TRD-EHR', host_name: 'TRD-EHR',
      state: 'being written', doc: '', at: 2 },
  ] };
  el('sittings-go').click();
  await sleep(30);
  check('an accepted ask says it is being written, in the reply\'s words',
        el('sittings-title').textContent === 'Being written'
        && /writing it in TRD-EHR/.test(el('sittings-line').textContent)
        && el('sittings-go').hidden === true && el('sittings-read').hidden === true);
  poll();
  await sleep(30);
  check('while the deck is being written, the sheet goes on saying so',
        el('sittings-title').textContent === 'Being written');
  decksAnswer = { ok: true, decks: [
    { title: 'What knn bought', slug: 'deck-260924-1830', host: 'TRD-EHR',
      host_id: 'research/TRD-EHR', host_name: 'TRD-EHR', state: 'ready',
      doc: 'writeups-deck-260924-1830-deck-260924-18', at: 2 },
  ] };
  poll();
  await sleep(30);
  check('and when it is there the sheet says Ready, with the way to read it',
        el('sittings-title').textContent === 'Ready'
        && el('sittings-read').hidden === false
        && el('sittings-how').hidden === false
        && /✎ mark it up/.test(el('sittings-how').textContent)
        && /✎ done marking, then say what is\s+wrong/.test(el('sittings-how').textContent));

  navigations = 0;
  el('sittings-read').click();
  check('Read the deck moves the board to the workspace it was written in',
        sent('/switch').length === 1 && sent('/switch')[0].body.repo === 'TRD-EHR');
  check('and the sheet closes behind it', el('sittings').hidden === true);
  await sleep(200);
  check('then goes to that library, on the deck itself',
        navigations >= 1
        && /"\/library\?from=home&doc=" \+ encodeURIComponent\(d\.doc\)/.test(js));
  el('busy').click();

  // ---- a deck that did not land is said as one --------------------------
  decksAnswer = { ok: true, decks: [
    { title: 'Nothing', slug: 'deck-260924-1830', host: 'TRD-EHR',
      host_id: 'research/TRD-EHR', host_name: 'TRD-EHR', state: 'did not land',
      why: 'The deck was written but did not build. Ask for it again.',
      doc: '', at: 2 },
  ] };
  tool.click();
  await sleep(30);
  check('a deck that did not land is listed as one, marked, with why',
        /did not land/.test(el('sittings-decks').textContent)
        && /written but did not build/.test(el('sittings-decks').textContent)
        && el('sittings-decks').querySelector('.sittings-deck.bad') !== null);

  // ---- Escape and the backdrop -----------------------------------------
  doc.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape' }));
  check('Escape takes the sheet off, one layer', el('sittings').hidden === true);
  tool.click();
  el('sittings').dispatchEvent(new window.Event('click', { bubbles: true }));
  check('and so does a tap on the backdrop', el('sittings').hidden === true);

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\nthe sittings are ticked, the tutor plans the '
                              + 'slides, and the sheet says when it is there');
  process.exit(errors.length ? 1 : 0);
})();
