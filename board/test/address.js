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

const SID = '20261009-120000';
const S = '#/s/' + SID;

const FORMS = [
  [S, 'session', { session: SID }],
  [S + '/card/0007', 'card', { card: '0007' }],
  [S + '/doc/stage2-walkthrough', 'doc', { doc: 'stage2-walkthrough', page: 0 }],
  [S + '/doc/stage2-walkthrough/p7', 'doc', { doc: 'stage2-walkthrough', page: 7 }],
  [S + '/slate/0012', 'slate', { page: 12 }],
  // A clash suffix on the id is the same session grammar.
  ['#/s/' + SID + '-2/card/0001', 'card', { session: SID + '-2', card: '0001' }],
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
  // the same address again.
  const again = A.format(a);
  if (again !== a.text || A.parse(again).text !== a.text) {
    fail(text + ' does not round-trip: ' + again);
    formsOk = false;
  }
}
if (formsOk) ok('every form in the grammar parses, and round-trips to one spelling');

// THE WORKSPACE GRAMMAR IS NO ADDRESS. Every `#/w/...` form that once parsed,
// and the session grammar's own malformed forms. None may throw and none may
// resolve to something near.
const BAD = [
  '#/w/courses/Probability',
  '#/w/courses/Galois-Theory/card/0007',
  '#/w/courses/Galois-Theory/archive/20260912-183613-ch-03-rings/0003',
  '#/w/research/PSYCH-ASR/doc/stage2-walkthrough/p7',
  '#/w/courses/Probability/hw/ch07/4.1',
  '#/w/courses/Probability/slate/0012',
  '#/w/research/PSYCH-ASR/node/typist',
  '', '#', '/board', '#/board', 'https://board.test/' + S,
  '#/s/', '#/s', S + '/', '#/s//' + SID,
  '#/s/2026-10-09', '#/s/../etc/passwd', '#/s/%2e%2e/card/0001',
  S + '/%E0%A4%A',                  // a broken escape
  S + '/card/7',                    // one spelling: four digits
  S + '/card/00007',
  S + '/card/0007/extra',
  S + '/doc/x/p0', S + '/doc/x/9', S + '/doc/x/p1/p2', S + '/doc/X',
  S + '/slate/12',
  S + '/node/typist', S + '/hw/ch07/4.1', S + '/archive/x/0003',
  S + '/code/a.py', S + '/nope/x',
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
if (badOk) ok('#/w/... parses as no address, and every malformed form fails safely');

if (A.parse(1) === null && A.parse(null) === null && A.parse(undefined) === null) {
  ok('a non-string is not an address either');
} else fail('parse accepted something that is not a string');

// `format` refuses to spell what it could not then read back. A speller that
// can emit what its own parser rejects is a dead-link factory.
const UNSPELLABLE = [
  { ws: 'courses/Probability', surface: 'workspace' },
  { ws: 'courses/Probability', surface: 'card', card: 7 },
  { session: SID, surface: 'node', node: 'typist' },
  { session: SID, surface: 'nope' },
  { session: 'not-an-id', surface: 'card', card: 7 },
  { surface: 'session' },
];
let spellOk = true;
for (const spec of UNSPELLABLE) {
  if (A.format(spec) !== '') {
    fail('format spelled something unreadable: ' + JSON.stringify(spec));
    spellOk = false;
  }
}
if (spellOk) ok('format refuses anything it could not read back');

if (A.format({ session: SID, surface: 'card', card: 7 }) === S + '/card/0007') {
  ok('format pads a card to its one spelling');
} else fail('format got the canonical spelling wrong: '
            + A.format({ session: SID, surface: 'card', card: 7 }));

// ---------------------------------------------------------------------------
// 2. The resolver, in a real DOM, on the real board.
// ---------------------------------------------------------------------------
const VIEW = {
  ok: true, name: 'The Stage 2 deck', n: 2,
  pages: ['/paper/a.png', '/paper/b.png'],
};

// Every address the lesson itself carries: one live, one dead, one gibberish,
// and one in the workspace grammar, which is no address.
const BODY = [
  'See [the deck](' + S + '/doc/stage2-deck).',
  'And [a card that has gone](' + S + '/card/0099).',
  'And [not an address at all](' + S + '/card/99).',
  'And [an old link](#/w/courses/Galois-Theory/card/0007).',
].join('\n\n');

const LIVE = {
  state: { course: 'Galois Theory', session: 'lecture', mode: 'math' },
  cards: [{ id: '0007', kind: 'lesson', title: 'A first card', body: BODY,
            mtime: Date.now() / 1000 }],
  turns: [], messages: [], uploads: [], notes: [], notes_sent: [],
  slate: [{ page: 12, name: 'page-12.png', url: '/slate/page-12.png' }],
  push: null, agent: null,
};

// jsdom will not navigate, and says so loudly. That is the one thing this test
// deliberately provokes -- an address for another session goes to that
// session's board -- so the noise is swallowed and the fact is asserted instead.
const vc = new VirtualConsole();
vc.on('jsdomError', () => {});

const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
  runScripts: 'outside-only', pretendToBeVisual: true, virtualConsole: vc,
  // COLD, ON A LINK. The address is in the bar before a line of the board has
  // run, which is the case a person sending somebody a link actually creates.
  url: 'https://board.test/s/' + SID + '/board' + S + '/card/0007',
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

const json = (v) => Promise.resolve({ json: () => Promise.resolve(v), ok: true });
let asked = [];
window.fetch = (u) => {
  const url = String(u);
  asked.push(url);
  if (/slate\/state/.test(url)) return json({ pages: [] });
  if (url.indexOf('/s/' + SID + '/view/doc/stage2-deck') === 0) return json(VIEW);
  if (url.indexOf('/s/' + SID + '/view/') === 0) {
    return json({ ok: false, error: 'no such document' });
  }
  return new Promise(() => {});          // everything else never answers
};

window.EventSource = function () {
  window.__es = this;
  this.readyState = 1;
  this.close = function () {};
  this.addEventListener = function () {};
};

for (const f of ['address.js', 'typeface.js', 'macros.js',
                 'plane-core.js', 'ink-core.js', 'slate-core.js', 'annotate.js',
                 'reader.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}

try {
  let src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
  src = src.replace('})();',
    'window.__addrGo = addrGo;\n'
    + 'window.__spell = spell;\n'
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

  // -- the cold landing. The address was in the bar before board.js ran.
  es.onmessage({ data: JSON.stringify(LIVE) });
  await tick();
  const card = doc.querySelector('[data-card="0007"]');
  if (card && card.classList.contains('landed')) {
    ok('a cold start on #/s/…/card/0007 lands on that card and marks it');
  } else fail('the address in the bar did not put the board on the card');
  if (!asked.some((u) => /\/health/.test(u))) {
    ok('landing asks the server nothing: the session is in the address');
  } else fail('the board asked /health before landing: ' + asked.join(' '));

  // -- rule 3, where it is written: four links in one card, three answers.
  const links = Array.from(card.querySelectorAll('a'));
  const live = links.find((a) => /doc\/stage2-deck/.test(a.getAttribute('href') || ''));
  const gone = links.find((a) => /card\/0099/.test(a.getAttribute('href') || ''));
  const junk = links.find((a) => /card\/99$/.test(a.getAttribute('href') || ''));
  const old = links.find((a) => /^#\/w\//.test(a.getAttribute('href') || ''));
  if (live && !live.classList.contains('dead') && !live.classList.contains('bad')) {
    ok('a link that still resolves reads as an ordinary link');
  } else fail('a live address was marked dead');
  if (gone && gone.classList.contains('dead') && /not in this session/.test(gone.title)) {
    ok('a link to a card that has gone reads as dead where it is written');
  } else fail('a dead address was not marked in the sentence it is in');
  if (junk && junk.classList.contains('bad')) {
    ok('text that is not an address is a third thing, and says so');
  } else fail('gibberish was treated as an address');
  if (old && old.classList.contains('bad') && !old.hasAttribute('target')) {
    ok('an old #/w/ link is marked as no address, in place');
  } else fail('an old #/w/ link was not marked bad: ' + (old && old.className));
  if (live && !live.hasAttribute('target')) {
    ok('an address opens in this board, not in a second tab');
  } else fail('an address link would open a second board');

  // -- every surface, reached and then left.
  const at = (frag) => window.__addrGo(A.parse(frag));

  if (at(S) === 'ok') ok('the session address is the lesson');
  else fail('the session address did not land on the lesson');
  if (window.__addrGo(A.parse('#/w/courses/Galois-Theory')) === 'bad') {
    ok('a workspace address goes nowhere: it is not an address');
  } else fail('a workspace address was followed');

  at(S + '/doc/stage2-deck');
  await tick();
  if (!el('reader').hidden) {
    ok('a document address opens the viewer');
  } else fail('the document did not open');
  if (window.location.hash === S + '/doc/stage2-deck') {
    ok('and puts where it is in the bar, so an address can be copied off it');
  } else fail('the bar does not name the surface: ' + window.location.hash);

  scrolled = [];
  at(S + '/doc/stage2-deck/p2');
  await tick();
  if (scrolled.some((n) => n.tagName === 'IMG')) {
    ok('a page address scrolls the viewer to that page');
  } else fail('a page address did not reach the page');

  at(S + '/doc/stage2-deck/p9');
  await tick();
  if (/no page 9/.test(said())) ok('a page past the end of a document says so');
  else fail('a page that does not exist was not reported: ' + said());

  at(S + '/slate/0012');
  if (el('viewer') && !el('viewer').hidden) {
    ok('a slate address opens that page of handwriting');
  } else fail('a slate address did not open the page');

  if (at(S + '/slate/0099') === 'gone' && /no page 99/.test(said())) {
    ok('a page of handwriting that was never written is a miss');
  } else fail('a missing slate page was not reported: ' + said());

  at(S + '/card/0099');
  await tick(5);
  if (/card 0099 is not in this session/.test(said())) {
    ok('a card that is not in the session is a miss');
  } else fail('a missing card was not reported: ' + said());

  // -- and left. Going back to the card takes down whatever was up.
  at(S + '/doc/stage2-deck');
  await tick();
  at(S + '/card/0007');
  await tick(5);
  if (el('reader').hidden) {
    ok('every surface can be left: one address takes down what another put up');
  } else fail('a surface was left open over the one the address named');

  // -- another session is another board, with the address carried whole.
  if (window.__addrGo(A.parse('#/s/20261001-090000/card/0002')) === 'elsewhere') {
    ok('an address for another session goes to that session\'s board');
  } else fail('an address for another session was opened here');

  // -- the bar carries the address of wherever the board is, or a link is a
  //    thing nobody can obtain.
  if (window.__spell({ surface: 'card', card: '0007' }) === S + '/card/0007') {
    ok('the board spells addresses for its own session, one way');
  } else fail('the board spelled a wrong address: '
              + window.__spell({ surface: 'card', card: '0007' }));

  // -- the wiring. The hash IS the way in: a tap on a link in a card changes
  //    it and nothing else happens, so if the resolver is not listening there
  //    the link does nothing at all. And the address has to SURVIVE the
  //    landing.
  doc.querySelector('[data-card="0007"]').classList.remove('landed');
  window.location.hash = S + '/card/0007';
  await tick(5);
  window.location.hash = S + '/slate/0012';
  await tick(5);
  window.location.hash = S + '/card/0007';
  await tick(5);
  if (doc.querySelector('[data-card="0007"]').classList.contains('landed')) {
    ok('changing the hash resolves: a tap on a link in a card is the way in');
  } else fail('a hash change never reached the resolver');
  if (window.location.hash === S + '/card/0007') {
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
