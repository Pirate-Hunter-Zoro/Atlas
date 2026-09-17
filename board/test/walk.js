// Choosing what a walkthrough covers, and who writes the code in a sitting.
//
// A lecture starts from one tap, because somebody else already decided what the
// work is. A walkthrough cannot: the student is the only one who knows which
// machinery they do not understand, so the sitting asks first, and it asks with
// a list of what the repository actually has rather than a text box -- a name
// nobody chose must never reach the filesystem or the tutor's prompt.
//
// It shares the review's panel on purpose. They are the same decision in the
// same shape, and two copies of it would be two copies to keep in step; what is
// checked here is that sharing it did not make either one wrong.
//
// The second half is the stance control, which is the other half of why these
// repositories were being worked in a terminal: one word in tutorboard.json can
// only answer for the whole repository, and a project has both kinds of work in
// it. What must hold is that a stance chosen for a sitting is visible while it
// is in force and gone the moment the sitting is.

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const WEB = path.join(__dirname, '..', 'web');
const html = fs.readFileSync(path.join(WEB, 'board.html'), 'utf8');

const ids = new Set();
{
  const re = /\bid="([\w-]+)"/g;
  let m;
  while ((m = re.exec(html)) !== null) ids.add(m[1]);
}

function stub(tag) {
  const el = {
    tagName: tag || 'div', dataset: {}, _classes: new Set(),
    style: { setProperty() {}, removeProperty() {} },
    hidden: false, disabled: false, value: '', textContent: '',
    children: [], childNodes: [], files: [], scrollHeight: 20, type: '',
    addEventListener() {}, removeChild() {}, after() {},
    insertBefore() {}, firstChild: null,
    setPointerCapture() {}, releasePointerCapture() {}, remove() {},
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 900, height: 600 }),
    getContext: () => new Proxy({}, { get: () => () => {}, set: () => true }),
  };
  el.classList = {
    add: (c) => el._classes.add(c),
    remove: (c) => el._classes.delete(c),
    toggle: (c, on) => (on === undefined
      ? (el._classes.has(c) ? el._classes.delete(c) : el._classes.add(c))
      : (on ? el._classes.add(c) : el._classes.delete(c))),
    contains: (c) => el._classes.has(c),
  };
  el.appendChild = (kid) => { el.children.push(kid); return kid; };
  // A real element's className and classList are two views of one thing, and
  // the picker sets a row's class one way and reads it back the other. A stub
  // that keeps them apart reports every row as carrying no class at all.
  let cls = '';
  Object.defineProperty(el, 'className', {
    get: () => cls,
    set: (v) => {
      cls = v || '';
      el._classes.clear();
      cls.split(/\s+/).filter(Boolean).forEach((c) => el._classes.add(c));
    },
  });
  let markup = '';
  Object.defineProperty(el, 'innerHTML', {
    get: () => markup,
    set: (v) => { markup = v; if (!v) el.children.length = 0; },
  });
  el.querySelector = (sel) => {
    const want = sel.replace(/^\./, '');
    if (!el._parts) el._parts = {};
    return (el._parts[want] = el._parts[want] || stub('span'));
  };
  el.querySelectorAll = () => [];
  return el;
}

const registry = {};
const posts = [];
const sandbox = {
  console,
  setTimeout, clearTimeout, setInterval, clearInterval,
  document: {
    getElementById(id) {
      if (!ids.has(id)) return null;
      return (registry[id] = registry[id] || stub());
    },
    createElement: (t) => stub(t),
    createDocumentFragment: () => stub(),
    querySelector: () => stub(), querySelectorAll: () => [],
    addEventListener() {},
    body: stub('body'), documentElement: stub('html'),
    title: '', hidden: false,
  },
  localStorage: { getItem: () => null, setItem() {} },
  EventSource: function () { return { close() {}, readyState: 1 }; },
  fetch: (url, opts) => {
    posts.push({ url, body: JSON.parse((opts && opts.body) || '{}') });
    return new Promise(() => {});
  },
  FormData: function () { this.append = () => {}; },
  matchMedia: () => ({ matches: false, addEventListener() {} }),
  getComputedStyle: () => ({ getPropertyValue: () => '18px' }),
  navigator: { serviceWorker: undefined },
  isSecureContext: false,
  innerHeight: 800, scrollY: 0, devicePixelRatio: 2,
  scrollTo() {}, addEventListener() {}, print() {},
  location: { reload() {}, protocol: 'https:' },
  renderMathInElement: () => {},
  requestAnimationFrame: (fn) => setTimeout(fn, 0),
  ResizeObserver: function () { return { observe() {}, disconnect() {} }; },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);

let src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
src = src.replace('})();',
  'window.__render = render;\nwindow.__openPicker = openPicker;\n'
  + 'window.__paintKindChooser = paintKindChooser;\n})();');
vm.runInContext(fs.readFileSync(path.join(WEB, 'macros.js'), 'utf8'), sandbox);
vm.runInContext(fs.readFileSync(path.join(WEB, 'plane-core.js'), 'utf8'), sandbox);
vm.runInContext(fs.readFileSync(path.join(WEB, 'slate-core.js'), 'utf8'), sandbox);
vm.runInContext(src, sandbox, { filename: 'board.js' });

const render = sandbox.window.__render;
const openPicker = sandbox.window.__openPicker;
const paintKindChooser = sandbox.window.__paintKindChooser;
const now = Date.now() / 1000;

let fails = 0;
function check(name, cond) {
  if (cond) console.log('ok   ' + name);
  else { fails++; console.log('FAIL ' + name); }
}

const FILES = [
  { name: 'psych_asr/config.py', label: 'psych_asr/config.py',
    short: 'config.py', dir: 'psych_asr', kind: 'file' },
  { name: 'psych_asr/evaluate/grade.py', label: 'psych_asr/evaluate/grade.py',
    short: 'grade.py', dir: 'psych_asr/evaluate', kind: 'file' },
  { name: 'psych_asr/evaluate/score.py', label: 'psych_asr/evaluate/score.py',
    short: 'score.py', dir: 'psych_asr/evaluate', kind: 'file' },
];
const CHAPTERS = [
  { name: 'Ch 01 — Groups', label: 'Ch 01 — Groups', short: 'Ch 01', kind: 'chapter' },
  { name: 'Ch 07 — Fields', label: 'Ch 07 — Fields', short: 'Ch 07', kind: 'chapter' },
];

function paint(session, opts) {
  const o = opts || {};
  render({
    state: {
      course: 'PSYCH-ASR', session,
      chapter: session === 'walk' ? 'Walkthrough — grade.py' : 'the grid sweep',
      stance: o.stance || undefined,
    },
    cards: [{ id: '0001', kind: 'lesson', body: 'x', mtime: now }],
    turns: [], messages: [], uploads: [], slate: [],
    review: o.noReview ? null
      : { of: 'chapters', units: CHAPTERS, scope: o.reviewScope || [], total: 2 },
    walk: o.noWalk ? null
      : { of: 'files', units: FILES, scope: o.walkScope || [], total: 3 },
  });
}

// --- the strip ---------------------------------------------------------------
// One strip for both sittings: they are the same fact about the sitting, and the
// bar has room for one of them at a time.
paint('lecture', {});
check('a lecture carries no scope strip', registry.rvbar.hidden === true);

paint('walk', { walkScope: ['psych_asr/evaluate/grade.py'] });
check('a walkthrough carries one', registry.rvbar.hidden === false);
check('and it says walking through, not test review',
      registry['rv-lead'].textContent === 'walking through');
check('naming the file it is over',
      /grade\.py/.test(registry['rv-scope'].textContent));
check('and the badge stays short enough for the bar it is in',
      registry.session.textContent === 'walk'
      && registry.session.textContent.length <= 'homework'.length
      && registry.session.dataset.kind === 'walk');

// Reachable from a terminal, never from the picker, which refuses to start one.
paint('walk', { walkScope: [] });
check('a walkthrough with nothing named says so rather than showing a blank',
      /nothing chosen/.test(registry['rv-scope'].textContent));

// The strip is shared, so the review must not have been left saying the wrong
// word by the sitting before it.
paint('review', { reviewScope: ['Ch 01 — Groups'] });
check('a review sitting still says test review',
      registry['rv-lead'].textContent === 'test review'
      && /Ch 01/.test(registry['rv-scope'].textContent));

// --- what is offered ---------------------------------------------------------
paint('lecture', {});
paintKindChooser();
check('a repository with source offers a walkthrough',
      registry['kind-walk'].hidden === false);
check('and one with chapters offers a review too',
      registry['kind-review'].hidden === false);
paint('lecture', { noWalk: true });
paintKindChooser();
check('a repository with no source does not offer one',
      registry['kind-walk'].hidden === true);

// --- the picker --------------------------------------------------------------
paint('lecture', {});
openPicker('walk');
check('the picker opens', registry.review.hidden === false);
check('and asks about files rather than chapters',
      /file/.test(registry['review-title'].textContent)
      && !/chapter/.test(registry['review-title'].textContent));
check('and the button says what it starts',
      /walkthrough/.test(registry['review-start'].textContent));
check('and says nothing is written in one',
      /Nothing is written/.test(registry['review-note'].textContent));

// A hundred filenames in a flat list is not a list anybody reads. Each row is
// the bare filename under the directory it sits in, which is how the person
// choosing already thinks of it.
const kids = () => registry['review-list'].children;
const dirs = () => kids().filter((k) => k.classList.contains('pick-dir'));
const rows = () => kids().filter((k) => !k.classList.contains('pick-dir'));
check('every file is offered', rows().length === 3);
check('headed by the directory it is in, once each',
      dirs().length === 2
      && dirs()[0].textContent === 'psych_asr/'
      && dirs()[1].textContent === 'psych_asr/evaluate/');
check('and a row is the filename, not the path again',
      rows()[1].querySelector('.what').textContent === 'grade.py');
// Select-all over a hundred files is not a walkthrough anybody wants, and is one
// tap away from being an accident.
check('there is no select-all over a repository of files',
      registry['review-all'].hidden === true);
check('with nothing ticked there is nothing to start',
      registry['review-start'].disabled === true);

rows()[1].onclick();
check('ticking one arms the start', registry['review-start'].disabled === false);
check('and the row shows it is ticked', rows()[1].classList.contains('on'));

posts.length = 0;
registry['review-start'].onclick();
check('starting one asks for a walkthrough, not a review',
      posts.length === 1 && posts[0].url === '/session'
      && posts[0].body.session === 'walk');
check('over exactly what was ticked, by the name the board was given',
      JSON.stringify(posts[0].body.over) === JSON.stringify(['psych_asr/evaluate/grade.py']));
check('and the panel closes behind it', registry.review.hidden === true);

// The same panel, the other sitting: sharing it must not have broken the review.
openPicker('review');
check('the review picker still asks about chapters',
      /chapters/.test(registry['review-title'].textContent)
      && rows().length === 2 && dirs().length === 0);
check('and offers select-all, where the list is a course rather than a tree',
      registry['review-all'].hidden === false);
check('and its button says review', /review/.test(registry['review-start'].textContent));
rows()[0].onclick();
posts.length = 0;
registry['review-start'].onclick();
check('and starting it asks for a review',
      posts.length === 1 && posts[0].body.session === 'review');

// Reopening starts from what the sitting already covers, so "change" is an edit
// rather than a fresh decision -- and it must read the right sitting's scope.
paint('walk', { walkScope: ['psych_asr/evaluate/score.py'] });
registry['rv-change'].onclick();
check('the strip reopens the picker for the sitting that is actually open',
      rows().length === 3
      && rows()[2].classList.contains('on')
      && !rows()[1].classList.contains('on'));

// --- who writes the code in this sitting -------------------------------------
paint('lecture', {});
paintKindChooser();
check('a lecture is asked who writes the code',
      registry['kind-stance'].hidden === false);
check('and starts on teaching, which is what the repository says',
      registry['stance-teach'].classList.contains('on')
      && registry['stance-do'].classList.contains('on') === false);

// The two sittings that read rather than write have no stance to take, and
// offering one would suggest they did.
paint('walk', { walkScope: ['psych_asr/evaluate/grade.py'] });
paintKindChooser();
check('a walkthrough is not asked', registry['kind-stance'].hidden === true);
paint('review', { reviewScope: ['Ch 01 — Groups'] });
paintKindChooser();
check('and neither is a review', registry['kind-stance'].hidden === true);

// --- but a DOCUMENT can be asked for in either of them -----------------------
// A paper or a deck is a PRODUCT, not an aim. Tapping `paper` in the `for:` row
// changes the SITTING -- every card after it is a make card -- and that row is
// hidden in exactly these two sittings, so in the two where a write-up is worth
// the most there was no way to ask for one at all. Asked as a question: *"at any
// point can I have a presentation or paper written up going through the things we
// talked about in that tutoring session? Can I do that in ANY tutoring
// session?"*
//
// TWO CONTROLS, NOT ONE, AND NOT A SECOND QUESTION AFTER THE TAP. Which of the
// two is known at the moment of tapping, and the words are `WORK`'s own.
check('a review is still asked whether it should produce a document',
      registry['kind-doc'].hidden === false
      && registry['kind-doc-ways'].children.length === 2);
paint('walk', { walkScope: ['psych_asr/evaluate/grade.py'] });
paintKindChooser();
check('and so is a walkthrough',
      registry['kind-doc'].hidden === false
      && registry['kind-doc-ways'].children.length === 2);
check('and the two are a paper and a deck, in the map sheet’s own words',
      /paper/i.test(registry['kind-doc-ways'].children[0].textContent)
      && /deck/i.test(registry['kind-doc-ways'].children[1].textContent));
posts.length = 0;
registry['kind-doc-ways'].children[1].onclick();
check('tapping one asks for it and says which product, without touching the aim',
      posts.length === 1 && posts[0].url === '/writeup'
      && posts[0].body.makes === 'slides'
      && !('aim' in posts[0].body) && !('session' in posts[0].body));

paint('lecture', {});
paintKindChooser();
registry['stance-do'].onclick();
check('tapping shows which one is in force',
      registry['stance-do'].classList.contains('on')
      && registry['stance-teach'].classList.contains('on') === false);
posts.length = 0;
registry['kind-lecture'].onclick();
check('and the sitting is opened under it',
      posts.length === 1 && posts[0].body.session === 'lecture'
      && posts[0].body.stance === 'do');

// A stance belongs to the sitting being opened and must not survive it: leaving
// it set would make the next tap carry an override chosen an hour ago for
// something else.
posts.length = 0;
registry['kind-lecture'].onclick();
check('the next sitting opened without a tap carries no stance',
      posts.length === 1 && !posts[0].body.stance);

// What is showing as chosen is what the sitting is actually running under, not
// what the repository says -- or the chooser paints an override away.
paint('lecture', { stance: 'do' });
paintKindChooser();
check('a sitting already running under a doing stance opens showing it',
      registry['stance-do'].classList.contains('on'));

console.log(fails ? '\n' + fails + ' FAILURES'
  : '\na walkthrough is chosen from what exists, and a stance is a sitting’s');
process.exit(fails ? 1 : 0);
