// THE ADDRESS GRAMMAR, AND THE ONE RESOLVER THAT OPENS IT.
//
// Nothing in this system had an address until now, and three features are
// waiting on this one: meeting notes whose links land where the notes say they
// do, a paper that cites its own figures, and an annotation that points at a
// line of code. All three are only as good as the rule that an address means
// exactly one place and says so when that place has gone.
//
// So this suite holds three things, and they are the three rules §2.1 of the
// handoff is written around:
//
//   1. EVERY FORM RESOLVES, AND EVERY MALFORMED FORM FAILS SAFELY. `parse`
//      never throws, never half-reads, and is strict about spelling -- a card
//      is four digits, never one and never seven -- because two spellings of an
//      address is two bugs.
//   2. EVERY SURFACE THE GRAMMAR NAMES CAN BE REACHED AND LEFT. Driven through
//      the real board in a real DOM: an address goes in, a surface comes up,
//      and the next address takes it down again. A surface somebody can be
//      stranded on mid-proof is the failure this board exists not to have.
//   3. A NAME FROM A BROWSER NEVER REACHES A FILESYSTEM, and a link that no
//      longer resolves says so where it is written. Every component is looked
//      up in the payload the board was given; a miss is reported, in the
//      sentence the link is in, and nothing near it is opened instead.

const fs = require('fs');
const path = require('path');

let JSDOM, VirtualConsole;
try {
  ({ JSDOM, VirtualConsole } = require('jsdom'));
} catch (e) {
  console.log('skip  jsdom is not installed — `npm install jsdom` to run this test');
  process.exit(0);
}

const WEB = path.join(__dirname, '..', 'web');
const errors = [];
const ok = (m) => console.log('ok   ' + m);
const fail = (m) => { errors.push(m); console.log('FAIL ' + m); };

// ---------------------------------------------------------------------------
// 1. The grammar, with no browser at all. `address.js` touches no DOM and makes
//    no request, which is exactly what makes this half cheap to keep honest.
// ---------------------------------------------------------------------------
const bare = { window: {} };
new Function('window', fs.readFileSync(path.join(WEB, 'address.js'), 'utf8'))(bare.window);
const A = bare.window.Address;

if (!A) { fail('address.js defined no Address'); process.exit(1); }

const FORMS = [
  ['#/w/courses/Probability', 'workspace', {}],
  ['#/w/research/PSYCH-ASR/node/typist', 'node', { node: 'typist' }],
  ['#/w/courses/Galois-Theory/card/0007', 'card', { card: '0007' }],
  ['#/w/courses/Galois-Theory/archive/20260912-183613-ch-03-rings/0003', 'archive',
   { sitting: '20260912-183613-ch-03-rings', card: '0003' }],
  ['#/w/research/PSYCH-ASR/doc/stage2-walkthrough', 'doc',
   { doc: 'stage2-walkthrough', page: 0 }],
  ['#/w/research/PSYCH-ASR/doc/stage2-walkthrough/p7', 'doc',
   { doc: 'stage2-walkthrough', page: 7 }],
  ['#/w/research/PSYCH-ASR/code/psych_asr/cli/run_asr.py', 'code',
   { path: 'psych_asr/cli/run_asr.py', symbol: '' }],
  ['#/w/research/PSYCH-ASR/code/psych_asr/evaluate/grade.py::grade', 'code',
   { path: 'psych_asr/evaluate/grade.py', symbol: 'grade' }],
  ['#/w/courses/Probability/hw/ch07/4.1', 'hw', { set: 'ch07', problem: '4.1' }],
  // A VENDOR TREE IS A SURFACE OF THE WORKSPACE THAT READS IT. There is no
  // board in somebody else's repository, so the address names the workspace the
  // sitting would be held in and the tree it is held over -- which is also what
  // lets the front door route it: move the board, then draw the tree.
  ['#/w/research/PSYCH-ASR/tree/vendor/colibri', 'tree',
   { tree: 'vendor/colibri' }],
  ['#/w/courses/Probability/slate/0012', 'slate', { page: 12 }],
  // A workspace directory with spaces in its name is a real one -- `To Turn In`
  // -- and it is percent-encoded, never split.
  ['#/w/courses/To%20Turn%20In', 'workspace', { workspace: 'To Turn In' }],
  // A HAND-OFF CARD'S ADDRESS, spelled by `tutorboard/spell.py` on the other
  // side of the wall: a component boundary is a stopping point, and the card
  // that says so names the next box as a link rather than as an errand. The
  // workspace name is percent-encoded there by the same rule as here, so the
  // form that has to parse is this one and not the pretty one.
  ['#/w/courses/To%20Turn%20In/node/grader', 'node',
   { workspace: 'To Turn In', node: 'grader' }],
];

let formsOk = true;
for (const [text, surface, want] of FORMS) {
  const a = A.parse(text);
  if (!a) { fail('did not parse: ' + text); formsOk = false; continue; }
  if (a.surface !== surface) {
    fail(text + ' read as ' + a.surface + ', not ' + surface);
    formsOk = false;
    continue;
  }
  for (const k of Object.keys(want)) {
    if (a[k] !== want[k]) {
      fail(text + ': ' + k + ' is ' + JSON.stringify(a[k]) + ', wanted '
           + JSON.stringify(want[k]));
      formsOk = false;
    }
  }
  // ONE SPELLING. What comes back out is what went in, and re-reading it gives
  // the same address again -- so a link written today and a link written by a
  // different caller tomorrow are the same string.
  const again = A.format(a);
  if (again !== a.text || A.parse(again).text !== a.text) {
    fail(text + ' does not round-trip: ' + again);
    formsOk = false;
  }
}
if (formsOk) ok('every form in the grammar parses, and round-trips to one spelling');

// Malformed, and every one of them a thing somebody's string concatenation
// actually produces. None may throw and none may resolve to something near.
const BAD = [
  '', '#', '/board', '#/board', 'https://board.test/#/w/courses/P',
  '#/w/', '#/w/courses', '#/w/courses/', '#/w/courses//Probability',
  '#/w/courses/Probability/',
  '#/w/../etc/passwd', '#/w/courses/../../etc/passwd',
  '#/w/courses/%2e%2e/x', '#/w/courses/Probability/code/../../etc/passwd',
  '#/w/courses/Probability/%E0%A4%A',          // a broken escape
  '#/w/courses/Probability/node/Typist',       // ids are lower case
  '#/w/courses/Probability/node/' + 'x'.repeat(41),
  '#/w/courses/Probability/card/7',            // one spelling: four digits
  '#/w/courses/Probability/card/00007',
  '#/w/courses/Probability/card/0007/extra',
  '#/w/courses/Probability/archive/sitting',   // a sitting alone is not a form
  '#/w/courses/Probability/doc/x/p0',
  '#/w/courses/Probability/doc/x/9',
  '#/w/courses/Probability/doc/x/p1/p2',
  '#/w/courses/Probability/code/',
  '#/w/courses/Probability/code/a.py::1bad',
  '#/w/courses/Probability/hw/ch07',           // a set alone is not a form
  '#/w/courses/Probability/slate/12',
  '#/w/courses/Probability/tree/vendor',          // a tree is family and name
  '#/w/courses/Probability/tree/vendor/colibri/bin',
  '#/w/courses/Probability/tree/../../etc',
  '#/w/courses/Probability/nope/x',
];
let badOk = true;
for (const text of BAD) {
  let got;
  try { got = A.parse(text); }
  catch (e) { fail('threw on ' + JSON.stringify(text) + ': ' + e.message); badOk = false; continue; }
  if (got) {
    fail(JSON.stringify(text) + ' resolved to ' + got.text);
    badOk = false;
  }
}
if (badOk) ok('every malformed form fails safely — no throw, no near miss');

if (A.parse(1) === null && A.parse(null) === null && A.parse(undefined) === null) {
  ok('a non-string is not an address either');
} else fail('parse accepted something that is not a string');

// `format` refuses to spell what it could not then read back. A speller that
// can emit what its own parser rejects is a dead-link factory.
const UNSPELLABLE = [
  { ws: 'courses/Probability', surface: 'node', node: 'Typist' },
  { ws: 'courses/Probability', surface: 'nope' },
  { surface: 'workspace' },
  { ws: 'Probability', surface: 'workspace' },
];
let spellOk = true;
for (const spec of UNSPELLABLE) {
  if (A.format(spec) !== '') {
    fail('format spelled something unreadable: ' + JSON.stringify(spec));
    spellOk = false;
  }
}
if (spellOk) ok('format refuses anything it could not read back');

if (A.format({ ws: 'courses/To Turn In', surface: 'card', card: 7 })
    === '#/w/courses/To%20Turn%20In/card/0007') {
  ok('format encodes a space and pads a card to its one spelling');
} else fail('format got the canonical spelling wrong: '
            + A.format({ ws: 'courses/To Turn In', surface: 'card', card: 7 }));

// ---------------------------------------------------------------------------
// 2. The resolver, in a real DOM, on the real board.
// ---------------------------------------------------------------------------
const HEALTH = { ok: true, id: 'courses/Galois-Theory', dir: 'Galois-Theory' };
const SITTING = '20260912-183613-ch-03-rings';

const PAST = {
  state: { course: 'Galois Theory', chapter: 'Ch 3 — Rings' },
  cards: [{ id: '0003', kind: 'lesson', title: 'Rings', body: 'old words' }],
  turns: [],
};

const VIEW = {
  ok: true, name: 'The Stage 2 deck', n: 2,
  pages: ['/paper/a.png', '/paper/b.png'],
};

// Every address the lesson itself carries: one live, one dead, one gibberish.
const BODY = [
  'See [the typist](#/w/courses/Galois-Theory/node/typist).',
  'And [a card that has gone](#/w/courses/Galois-Theory/card/0099).',
  'And [not an address at all](#/w/courses/Galois-Theory/card/99).',
  'And [somewhere else](#/w/research/PSYCH-ASR/node/typist).',
  // The hand-off itself: the work has left this box, so the card names the box
  // it continues in. Written the way `node_sense` hands the address over.
  'The grader is where this continues: [the grader](#/w/courses/Galois-Theory/node/grader).',
].join('\n\n');

const LIVE = {
  state: { course: 'Galois Theory', session: 'lecture', mode: 'math' },
  cards: [{ id: '0007', kind: 'lesson', title: 'A first card', body: BODY,
            mtime: Date.now() / 1000 }],
  turns: [], messages: [], uploads: [], notes: [], notes_sent: [],
  slate: [{ page: 12, name: 'page-12.png', url: '/slate/page-12.png' }],
  push: null, agent: null, history: 1,
  map: { nodes: [{ id: 'typist', name: 'the typist', kind: 'part',
                   status: 'working', does: 'Turns the waveform into words.',
                   files: ['psych_asr/asr.py'], dir: 'psych_asr', steps: [] },
                 { id: 'grader', name: 'the grader', kind: 'part',
                   status: 'unknown', does: 'Scores a transcript.',
                   files: ['psych_asr/grade.py'], dir: 'psych_asr/grade',
                   steps: [] }],
         edges: [], loose: [] },
  reading: { documents: [{ id: 'stage2-deck', name: 'The Stage 2 deck' }] },
  walk: { units: [{ name: 'psych_asr/asr.py', label: 'psych_asr/asr.py',
                    path: 'psych_asr/asr.py', short: 'asr.py', dir: 'psych_asr',
                    kind: 'file', symbol: '' }], scope: [] },
  sets: ['ch07'],
  hw: { name: 'ch07', total: 1, written: 0, problems: [{ label: '4.1' }] },
  contents: { chapters: [], sets: [{ name: 'ch07', rel: 'hw/ch07.tex' }] },
};

// jsdom will not navigate, and says so loudly. That is the one thing this test
// deliberately provokes -- an address for another workspace goes to the front
// door -- so the noise is swallowed and the fact is asserted instead.
const vc = new VirtualConsole();
vc.on('jsdomError', () => {});

const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
  runScripts: 'outside-only', pretendToBeVisual: true, virtualConsole: vc,
  // COLD, ON A LINK. The address is in the bar before a line of the board has
  // run, which is the case a person sending somebody a link actually creates.
  url: 'https://board.test/board#/w/courses/Galois-Theory/card/0007',
});
const { window } = dom;
const doc = window.document;

window.__paints = {};
window.HTMLCanvasElement.prototype.getContext = () =>
  new Proxy({}, { get: () => function () {}, set: () => true });
window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => 900 });
Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 500 });
window.HTMLElement.prototype.getBoundingClientRect = function () {
  return { left: 0, top: 0, width: 900, height: 500, right: 900, bottom: 500, x: 0, y: 0 };
};
let scrolled = [];
window.Element.prototype.scrollIntoView = function () { scrolled.push(this); };
window.renderMathInElement = () => {};
window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
window.scrollTo = () => {};
window.scrollBy = () => {};
window.addEventListener('error', (e) => fail('uncaught: ' + e.message));

// What the board is handed for a tree: the shape `map.inside` answers in, with
// the tree named on it so a scope taken off a box is spelt `@vendor/colibri/…`.
const TREE = {
  ok: true, of: '', name: 'colibri', depth: 'tree', kind: 'tree', up: '',
  tree: 'vendor/colibri', exact: true, total: 1, capped: false,
  why: 'colibri is pulled and not written here: read it and trace it, and '
     + 'change nothing in it.',
  nodes: [{ id: 'bin', name: 'bin', also: 'bin', kind: 'part', does: 'The driver commands.',
            status: 'unknown', files: ['bin/coli-up'], dir: 'bin', steps: [],
            doc: '', slide: null, note: '', inside: 1 }],
  edges: [],
};

const json = (v) => Promise.resolve({ json: () => Promise.resolve(v), ok: true });
let asked = [];
window.fetch = (u) => {
  const url = String(u);
  asked.push(url);
  if (/slate\/state/.test(url)) return json({ pages: [] });
  if (url.indexOf('/health') === 0) return json(HEALTH);
  if (url === '/archive') return json({ sessions: [{ id: SITTING, cards: 1, turns: 0 }] });
  if (url === '/archive/' + SITTING) return json(PAST);
  if (url.indexOf('/archive/') === 0) return json({ ok: false, error: 'no such session' });
  if (url.indexOf('/view/') === 0) return json(VIEW);
  // A VENDOR TREE'S PICTURE. Fetched on the tap, like the inside of a box, and
  // answered under the tree's own name because a box id from somebody else's
  // repository means nothing to this workspace's discovery.
  if (url === '/map/tree/vendor/colibri') return json(TREE);
  if (url.indexOf('/map/tree/') === 0) {
    return json({ ok: false, error: 'no such tree' });
  }
  return new Promise(() => {});          // everything else never answers
};

window.EventSource = function () {
  window.__es = this;
  this.readyState = 1;
  this.close = function () {};
  this.addEventListener = function () {};
};

for (const f of ['address.js', 'typeface.js', 'macros.js', 'gauge.js',
                 'plane-core.js', 'slate-core.js', 'annotate.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}

try {
  let src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
  src = src.replace('})();',
    'window.__addrGo = addrGo;\n'
    + 'window.__spell = spell;\n'
    + 'window.__boardId = function () { return boardId; };\n'
    + '})();');
  window.eval(src);
  ok('loaded board.js with the grammar beside it');
} catch (e) { fail('board.js: ' + e.message); }

const el = (id) => doc.getElementById(id);
const tick = (n) => new Promise((go) => setTimeout(go, n || 0));
const said = () => (el('pushed').hidden ? '' : el('pushed-text').textContent);

(async function () {
  const es = window.__es;
  if (!es) { fail('board.js never opened a stream'); return done(); }

  await tick();                       // `/health` answers
  if (window.__boardId() === 'courses/Galois-Theory') {
    ok('the board knows which workspace it is, from /health');
  } else fail('the board never learned its own id: ' + window.__boardId());

  // -- the cold landing. The address was in the bar before board.js ran.
  es.onmessage({ data: JSON.stringify(LIVE) });
  await tick();
  const card = doc.querySelector('[data-card="0007"]');
  if (card && card.classList.contains('landed')) {
    ok('a cold start on #/…/card/0007 lands on that card and marks it');
  } else fail('the address in the bar did not put the board on the card');

  // -- rule 3, where it is written: three links in one card, three answers.
  const links = Array.from(card.querySelectorAll('a'));
  const live = links.find((a) => /typist/.test(a.getAttribute('href') || '')
                                && /Galois/.test(a.getAttribute('href') || ''));
  const gone = links.find((a) => /card\/0099/.test(a.getAttribute('href') || ''));
  const junk = links.find((a) => /card\/99$/.test(a.getAttribute('href') || ''));
  if (live && !live.classList.contains('dead') && !live.classList.contains('bad')) {
    ok('a link that still resolves reads as an ordinary link');
  } else fail('a live address was marked dead');
  if (gone && gone.classList.contains('dead') && /not in the lesson/.test(gone.title)) {
    ok('a link to a card that has gone reads as dead where it is written');
  } else fail('a dead address was not marked in the sentence it is in');
  if (junk && junk.classList.contains('bad')) {
    ok('text that is not an address is a third thing, and says so');
  } else fail('gibberish was treated as an address');
  if (live && !live.hasAttribute('target')) {
    ok('an address opens in this board, not in a second tab');
  } else fail('an address link would open a second board');

  // -- every surface, reached and then left.
  const at = (frag) => window.__addrGo(A.parse(frag));
  const W = '#/w/courses/Galois-Theory';

  at(W);
  if (!el('map').hidden) ok('the workspace address opens the map');
  else fail('the workspace address did not open the map');

  at(W + '/node/typist');
  if (!el('map').hidden && !el('work').hidden
      && /typist/.test(el('work-title').textContent)) {
    ok('a node address selects that box and opens its sheet');
  } else fail('a node address did not open the box: ' + el('work-title').textContent);

  if (at(W + '/node/nowhere') === 'gone' && /not on this map/.test(said())) {
    ok('a node that is not on the map is a miss, said plainly');
  } else fail('a missing node was not reported: ' + said());

  // -- THE HAND-OFF LANDS. A component boundary is a stopping point, and the
  //    card that stops names the box the work continues in. What makes that a
  //    tap rather than an errand is only this: the address in the card resolves
  //    and opens that box. `tutorboard/spell.py` spells it and `test/aiming.py`
  //    asserts the string it hands the turn; this is the other end of it.
  const hand = Array.from(card.querySelectorAll('a'))
    .find((a) => /node\/grader/.test(a.getAttribute('href') || ''));
  if (hand && !hand.classList.contains('dead') && !hand.classList.contains('bad')) {
    ok('a hand-off to another box reads as a live link where it is written');
  } else fail('the hand-off link was not marked live');
  at(W + '/node/grader');
  if (!el('map').hidden && !el('work').hidden
      && /grader/.test(el('work-title').textContent)) {
    ok('and the box it names opens, which is what makes it a tap');
  } else fail('the hand-off address did not open the box: '
              + el('work-title').textContent);

  at(W + '/doc/stage2-deck');
  await tick();
  if (!el('paper').hidden && el('map').hidden) {
    ok('a document address opens the viewer, and the map it was over closes');
  } else fail('the document did not open, or the map stayed over it');

  scrolled = [];
  at(W + '/doc/stage2-deck/p2');
  await tick();
  if (scrolled.some((n) => n.tagName === 'IMG')) {
    ok('a page address scrolls the viewer to that page');
  } else fail('a page address did not reach the page');

  at(W + '/doc/stage2-deck/p9');
  await tick();
  if (/no page 9/.test(said())) ok('a page past the end of a document says so');
  else fail('a page that does not exist was not reported: ' + said());

  if (at(W + '/doc/nothing-here') === 'gone'
      && /not in this workspace/.test(said())) {
    ok('a document that has moved is a miss, not an error');
  } else fail('a missing document was not reported: ' + said());

  at(W + '/code/psych_asr/asr.py::run');
  if (!el('review').hidden
      && el('review-list').querySelector('[data-unit="psych_asr/asr.py"]')
      && /asr\.py/.test(said())) {
    ok('a code address opens the walkthrough picker on that file');
  } else fail('a code address did not reach the file: ' + said());

  if (at(W + '/code/psych_asr/nowhere.py') === 'gone'
      && /no psych_asr\/nowhere\.py/.test(said())) {
    ok('a file that is not in the repository is a miss');
  } else fail('a missing file was not reported: ' + said());

  at(W + '/hw/ch07/4.1');
  if (!el('contents').hidden
      && el('contents-list').querySelector('[data-set="ch07"]')
      && /4\.1/.test(said())) {
    ok('a homework address opens the set it is in and names the problem');
  } else fail('a homework address did not land: ' + said());

  if (at(W + '/hw/ch07/9.9') === 'gone' && /no problem 9\.9/.test(said())) {
    ok('a problem that is not in the set is a miss');
  } else fail('a missing problem was not reported: ' + said());

  if (at(W + '/hw/ch99/1.1') === 'gone' && /no problem set/.test(said())) {
    ok('a problem set that is not here is a miss');
  } else fail('a missing set was not reported: ' + said());

  at(W + '/slate/0012');
  if (el('viewer') && !el('viewer').hidden) {
    ok('a slate address opens that page of handwriting');
  } else fail('a slate address did not open the page');

  if (at(W + '/slate/0099') === 'gone' && /no page 99/.test(said())) {
    ok('a page of handwriting that was never written is a miss');
  } else fail('a missing slate page was not reported: ' + said());

  // -- a past sitting, which is the one lookup that has to ask the server.
  scrolled = [];
  at(W + '/archive/' + SITTING + '/0003');
  await tick(5);
  const old = doc.querySelector('[data-card="0003"]');
  if (old && old.classList.contains('landed') && !el('reading').hidden) {
    ok('an archive address opens that sitting and lands on the card');
  } else fail('an archive address did not reach the card in the past sitting');

  at(W + '/archive/nothing-was-filed-then/0003');
  await tick(5);
  if (/not in this workspace's history/.test(said())) {
    ok('a sitting that is not in the history is a miss');
  } else fail('a missing sitting was not reported: ' + said());

  at(W + '/archive/' + SITTING + '/0009');
  await tick(5);
  if (/not in that sitting/.test(said())) {
    ok('a card that is not in that sitting is a miss');
  } else fail('a missing card in a sitting was not reported: ' + said());

  // -- a vendor tree, which is the one surface that is not in this workspace.
  // Somebody tracing colibrì is doing it FOR this workspace: the address names
  // the workspace, the board is already serving it, and all that is left is to
  // draw the foreign picture on the map surface this page already has.
  at(W + '/tree/vendor/colibri');
  await tick(5);
  if (!el('map').hidden && /colibri/.test(el('map-title').textContent)) {
    ok('a tree address draws that tree on this board\'s map');
  } else fail('a tree address did not draw the tree: ' + el('map-title').textContent);
  if (/pulled and not written/.test(el('map-why').textContent)) {
    ok('and the picture says the rule, where somebody is looking at it');
  } else fail('the tree picture did not say whose it is: ' + el('map-why').textContent);
  const crumbs = [...el('map-crumb').querySelectorAll('.crumb')]
    .map((b) => b.textContent);
  if (crumbs[0] === 'Galois Theory' && crumbs[crumbs.length - 1] === 'colibri') {
    ok('and the way back out of it is the workspace, which is where the '
       + 'sitting would be held');
  } else fail('the crumb does not lead back to the workspace: ' + crumbs.join('|'));

  at(W + '/tree/vendor/nothing');
  await tick(5);
  if (/no vendor\/nothing in this repository/.test(said())) {
    ok('a tree this repository does not pull is a miss, not an empty picture');
  } else fail('a missing tree was not reported: ' + said());

  // -- and left. Going back to the workspace takes down whatever was up.
  at(W + '/doc/stage2-deck');
  await tick();
  at(W);
  if (el('paper').hidden && el('contents').hidden && el('review').hidden
      && !el('map').hidden) {
    ok('every surface can be left: one address takes down what another put up');
  } else fail('a surface was left open over the one the address named');

  // -- another workspace is another board, and only the front door moves it.
  if (window.__addrGo(A.parse('#/w/research/PSYCH-ASR/node/typist')) === 'elsewhere') {
    ok('an address for another workspace is handed to the front door');
  } else fail('an address for another workspace was opened here');

  // -- the bar carries the address of wherever the board is, or a link is a
  //    thing nobody can obtain.
  if (window.__spell({ surface: 'card', card: '0007' })
      === '#/w/courses/Galois-Theory/card/0007') {
    ok('the board spells addresses for its own workspace, one way');
  } else fail('the board spelled a wrong address: '
              + window.__spell({ surface: 'card', card: '0007' }));

  at(W + '/node/typist');
  if (window.location.hash === W + '/node/typist') {
    ok('and puts where it is in the bar, so an address can be copied off it');
  } else fail('the bar does not name the surface: ' + window.location.hash);

  // -- the wiring. The hash IS the way in: a tap on a link in a card changes
  //    it and nothing else happens, so if the resolver is not listening there
  //    the link does nothing at all. And the address has to SURVIVE the
  //    landing -- a bar that reverts to the workspace a second after a card
  //    link was followed is a link nobody can copy off the glass.
  doc.querySelector('[data-card="0007"]').classList.remove('landed');
  window.location.hash = W + '/card/0007';
  await tick(5);
  if (doc.querySelector('[data-card="0007"]').classList.contains('landed')) {
    ok('changing the hash resolves: a tap on a link in a card is the way in');
  } else fail('a hash change never reached the resolver');
  if (window.location.hash === W + '/card/0007') {
    ok('and the address it landed on stays in the bar');
  } else fail('the bar was overwritten after landing: ' + window.location.hash);

  done();
})();

function done() {
  if (errors.length) {
    console.log(errors.length + ' failed');
    process.exit(1);
  }
  console.log('the grammar holds and every surface it names opens and closes');
}
