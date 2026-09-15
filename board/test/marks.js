// Marks belong to the sitting they were made in, and to no other.
//
// Reported from the iPad: "old annotations are showing up on new tutoring text
// blocks". They were not new marks and nothing had gone wrong with the pen. A
// card is numbered from 0001 inside its own sitting and an annotation record is
// named after that number, so `0001` means a different card the moment a
// section is filed -- and the browser's store is merged into, never replaced,
// so a page held open across an archive went on holding last night's ink under
// the key tonight's card 1 now answers to.
//
// The other half of the same defect is a past lesson opened from the history:
// the live lesson's marks were laid over cards they were never made on.
//
// The store is therefore dropped when the SITTING changes, and only then. Only
// then matters as much as the rule does: a lesson takes a payload several times
// a second, and a store dropped on any of them is ink vanishing under the nib.
//
// jsdom, because the assertion is about what is on the glass after a render.

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

const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
  runScripts: 'outside-only', pretendToBeVisual: true, url: 'https://board.test/board',
});
const { window } = dom;
const doc = window.document;

window.HTMLCanvasElement.prototype.getContext = () =>
  new Proxy({}, { get: () => () => {}, set: () => true });
window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => 800 });
Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 600 });
window.HTMLElement.prototype.getBoundingClientRect = function () {
  return { left: 0, top: 0, width: 800, height: 40, right: 800, bottom: 40, x: 0, y: 0 };
};
window.Element.prototype.scrollIntoView = function () {};
window.Element.prototype.setPointerCapture = function () {};
window.Element.prototype.releasePointerCapture = function () {};
window.fetch = (u) => (/slate\/state/.test(String(u))
  ? Promise.resolve({ json: () => Promise.resolve({ pages: [] }) })
  : new Promise(() => {}));
window.EventSource = function () { return { close() {}, readyState: 1, addEventListener() {} }; };
window.renderMathInElement = () => {};
window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
window.scrollTo = () => {};
window.addEventListener('error', (e) => fail('uncaught: ' + e.message));

for (const f of ['typeface.js', 'macros.js', 'gauge.js', 'plane-core.js',
                 'slate-core.js', 'annotate.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
try {
  let src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
  src = src.replace('})();', 'window.__render = render;\n})();');
  window.eval(src);
  ok('loaded the board');
} catch (e) { fail('board.js: ' + e.message); }

window.dispatchEvent(new window.Event('load'));

const INK = [{ c: '#ffd166', w: 3, pts: [[10, 10], [40, 40]] }];
const marked = () => (window.Annotate ? window.Annotate.marked() : []);

// One sitting's frame: its own `opened` stamp, its own card 1.
function frame(opened, chapter, notes, extra) {
  const at = Date.now() / 1000;
  return Object.assign({
    state: { course: 'Galois-Theory', chapter: chapter, opened: opened },
    cards: [{ id: '0001', kind: 'question', title: 'Which subfield is fixed?',
              body: 'Say which of the three it is.', mtime: at }],
    turns: [], messages: [], uploads: [], slate: [], notes: notes || {},
    notes_sent: {},
  }, extra || {});
}

(async function () {
  // ------------------------------------------------ the marks of this sitting
  window.__render(frame('2026-01-01 10:00', 'Chapter 7', { '0001': INK }));
  await sleep(40);
  marked().indexOf('0001') >= 0
    ? ok('the marks restored with a lesson are on its cards')
    : fail('the ink that came with the payload never reached the store');

  // ------------------------------- and a heartbeat does not take them away
  //
  // The hostile half. A lesson hears a payload several times a second, and the
  // fix for the defect above is one line away from wiping the page's own ink
  // between two strokes of the same word.
  window.__render(frame('2026-01-01 10:00', 'Chapter 7', {}));
  await sleep(40);
  marked().indexOf('0001') >= 0
    ? ok('and another payload for the same sitting leaves them alone')
    : fail('a heartbeat wiped the marks on the lesson being written on');

  // --------------------------------------------- a new sitting, a new card 1
  window.__render(frame('2026-01-02 19:30', 'Chapter 8', {}));
  await sleep(40);
  marked().length === 0
    ? ok('a section filed and the next one opened starts with a clean card 1')
    : fail('last night\'s ink is on tonight\'s card 1 — the reported defect: '
           + JSON.stringify(marked()));

  // ------------------------------------------------- and a past lesson's own
  window.__render(frame('2026-01-01 10:00', 'Chapter 7', { '0001': INK }));
  await sleep(40);
  window.__render(Object.assign(
    frame('2026-01-01 10:00', 'Chapter 7', {}), { archived: true }));
  await sleep(40);
  marked().length === 0
    ? ok('and a past lesson shows its own marks, not the live lesson\'s')
    : fail('the live lesson\'s ink was laid over a filed sitting\'s cards');

  window.close();
  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\nmarks belong to the sitting they were made in');
  process.exit(errors.length ? 1 : 0);
})();
