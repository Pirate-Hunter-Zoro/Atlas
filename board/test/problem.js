// The problem stays on screen, and its givens go anywhere in one tap.
//
// The real board in a real DOM, painted from the payload `problem` that
// `state.load_problem` builds off hw04 as committed at 0a591419: the strip in the
// chrome, the statement opening and closing in one tap, a given's chip into
// the calculator (p*P^3 then reads in fractions), into the typed answer and
// onto the clipboard, and the picker switching problems with POST /problem.
//
// jsdom is a development-only dependency; without it this test skips.

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

let JSDOM;
try {
  ({ JSDOM } = require('jsdom'));
} catch (e) {
  console.log('skip  jsdom is not installed — `npm install jsdom` to run this test');
  process.exit(0);
}

const BOARD = path.join(__dirname, '..');
const WEB = path.join(BOARD, 'web');
const errors = [];
const ok = (m) => console.log('ok   ' + m);
const fail = (m) => { errors.push(m); console.log('FAIL ' + m); };

const HTML = fs.readFileSync(path.join(WEB, 'board.html'), 'utf8');
const CSS = fs.readFileSync(path.join(WEB, 'board.css'), 'utf8');
const SW = fs.readFileSync(path.join(WEB, 'sw.js'), 'utf8');

// ---- the page's own wiring --------------------------------------------------
const at = (s) => HTML.indexOf(s);
at('src="/static/problem.js"') > 0 && at('src="/static/problem.js"') < at('src="/static/board.js"')
  ? ok('problem.js loads before board.js') : fail('problem.js does not load before board.js');
/"\/static\/problem\.js"/.test(SW) ? ok('and it is in the service worker\'s shell')
  : fail('problem.js is not in sw.js SHELL');
const chromeStart = at('<div id="chrome">'), chromeEnd = at('</div><!-- /#chrome -->');
const bar = at('id="probbar"');
bar > at('id="hwbar"') && bar < chromeEnd && bar > chromeStart
  ? ok('#probbar sits in #chrome after #hwbar') : fail('#probbar is not in #chrome after #hwbar');
(at('id="probpanel"') > chromeEnd && at('id="probmenu"') > chromeEnd)
  ? ok('the statement and the chip menu are outside #chrome')
  : fail('#probpanel or #probmenu is inside the sticky chrome, where it cannot scroll');
const rule = (sel) => {
  const flat = CSS.replace(/\/\*[\s\S]*?\*\//g, '');
  const m = new RegExp('(^|})\\s*' + sel.replace(/[.#]/g, '\\$&') + '\\s*\\{([^}]*)\\}', 'm').exec(flat);
  return m ? m[2] : '';
};
const panelRule = rule('.probpanel');
/position:\s*fixed/.test(panelRule) && /max-height:\s*45d?vh/.test(panelRule)
  && /overflow-y:\s*auto/.test(panelRule)
  ? ok('#probpanel is fixed, about 45vh, and scrolls on its own')
  : fail('#probpanel rule: ' + panelRule);

// ---- the payload, off the tracked write-up ----------------------------------
const PY = `
import json, os, sys, tempfile
sys.path.insert(0, ${JSON.stringify(BOARD)})
from tutorboard.course import repo as course_repo
from tutorboard.lesson import state
import subprocess
root = tempfile.mkdtemp(prefix="tutor-problem-js-course-")
os.makedirs(os.path.join(root, "homework", "hw04"))
with open(os.path.join(root, "homework", "hw04", "hw04.tex"), "wb") as fh:
    fh.write(subprocess.run(["git", "-C", ${JSON.stringify(path.dirname(BOARD))}, "show",
                             "0a591419:courses/Probability/homework/hw04/hw04.tex"],
                            capture_output=True, check=True).stdout)
with open(os.path.join(root, "tutorboard.json"), "w") as fh:
    json.dump({"name": "Probability"}, fh)
r = course_repo.Repo(root, tempfile.mkdtemp(prefix="tutor-problem-js-"))
print(json.dumps(state.load_problem(r, {"hw": "homework/hw04/hw04.tex", "problem": "5"})))
`;
let problem = null;
try {
  problem = JSON.parse(execFileSync('python3', ['-c', PY], { encoding: 'utf8' }));
  problem && problem.label === '5' && problem.givens.length === 2
    ? ok('load_problem gives hw04 problem 5 and its two givens')
    : fail('unexpected problem payload: ' + JSON.stringify(problem));
} catch (e) { fail('load_problem: ' + e.message); }

// ---- the board ----------------------------------------------------------------
const dom = new JSDOM(HTML, {
  runScripts: 'outside-only', pretendToBeVisual: true, url: 'https://board.test/s/20261023-120000/board',
});
const { window } = dom;
const d = window.document;
window.HTMLCanvasElement.prototype.getContext = () =>
  new Proxy({}, { get: () => () => {}, set: () => true });
window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
window.Element.prototype.scrollIntoView = function () {};
const posted = [];
window.fetch = (u, init) => {
  if (init && init.method === 'POST') {
    posted.push({ url: String(u), body: JSON.parse(init.body || '{}') });
    return Promise.resolve({ json: () => Promise.resolve({ ok: true, changed: true }) });
  }
  return /slate\/state/.test(String(u))
    ? Promise.resolve({ json: () => Promise.resolve({ pages: [] }) })
    : new Promise(() => {});
};
window.EventSource = function () { return { close() {}, readyState: 1, addEventListener() {} }; };
window.renderMathInElement = () => {};
window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
window.scrollTo = () => {};
let copied = null;
Object.defineProperty(window.navigator, 'clipboard', {
  value: { writeText: (t) => { copied = t; return Promise.resolve(); } }, configurable: true,
});
window.addEventListener('error', (e) => fail('uncaught: ' + e.message));
// A figure loads as a 134 by 75 picture, whatever its digest.
window.Image = function () {
  const img = { naturalWidth: 0, naturalHeight: 0 };
  Object.defineProperty(img, 'src', {
    get: () => img.__src,
    set: (u) => {
      img.__src = u;
      setTimeout(() => { img.naturalWidth = 134; img.naturalHeight = 75; img.onload && img.onload(); }, 1);
    },
  });
  return img;
};
Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => 900 });
Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 500 });

for (const f of ['katex/katex.min.js', 'typeface.js', 'macros.js', 'plane-core.js', 'ink-core.js',
                 'slate-core.js', 'mathjs/math.js', 'calc-core.js', 'calc.js', 'problem.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); } catch (e) { fail(f + ': ' + e.message); }
}
try {
  let src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
  src = src.replace('})();', 'window.__render = render;\n})();');
  window.eval(src);
  ok('loaded the board with problem.js');
} catch (e) { fail('board.js: ' + e.message); }

const now = Date.now() / 1000;
const frame = (p) => ({
  state: { course: 'Probability', mode: 'teach' },
  cards: [{ id: '0001', kind: 'question', title: 'Q', body: 'Problem 5.', mtime: now }],
  messages: [], uploads: [], slate: [], problem: p,
});

try {
  window.__render(frame(null));
  d.getElementById('probbar').hidden ? ok('with no problem the strip is not drawn')
                                     : fail('an empty strip is drawn');
  window.__render(frame(problem));
  const strip = d.getElementById('probbar');
  !strip.hidden && d.getElementById('prob-label').textContent === 'Problem 5'
    ? ok('the strip names the problem on their screen') : fail('the strip says ' + strip.textContent);
  const chips = d.querySelectorAll('#prob-chips .prob-chip');
  chips.length === 2 && chips[0].querySelector('.katex') && chips[0].dataset.id === 'P'
    && chips[1].dataset.id === 'p'
    ? ok('one KaTeX chip per given: P and p') : fail('chips: ' + chips.length);
  const opts = Array.prototype.map.call(d.querySelectorAll('#prob-pick option'), (o) => o.value)
    .filter(Boolean);
  opts.join(',') === '2,3,5,14' && d.getElementById('prob-pick').value === '5'
    ? ok('the picker lists every problem in the set, on 5')
    : fail('picker: ' + opts.join(','));

  // One tap opens the statement, one tap closes it.
  const opener = d.getElementById('prob-open');
  const panel = d.getElementById('probpanel');
  opener.click();
  !panel.hidden && /Find \$E\[X_3\]\$/.test(panel.textContent)
    && /\\begin\{pmatrix\}/.test(panel.textContent)
    ? ok('one tap opens the whole statement') : fail('the statement did not open: ' + panel.textContent.slice(0, 80));
  opener.getAttribute('aria-expanded') === 'true' ? ok('and the label says it is open')
    : fail('aria-expanded not set');
  opener.click();
  panel.hidden ? ok('and one tap closes it') : fail('the statement did not close');

  // A payload that changes nothing leaves the strip alone.
  const chip0 = d.querySelector('#prob-chips .prob-chip');
  window.__render(frame(JSON.parse(JSON.stringify(problem))));
  d.querySelector('#prob-chips .prob-chip') === chip0
    ? ok('an unchanged problem is not repainted') : fail('the chips were rebuilt for nothing');

  // P to the calculator, p too, then p*P^3 reads in fractions.
  const menu = d.getElementById('probmenu');
  chip0.click();
  !menu.hidden && !d.getElementById('probmenu-calc').hidden
    ? ok('a chip opens its menu, to calculator offered') : fail('the chip menu did not open');
  d.getElementById('probmenu-calc').click();
  const calc = d.getElementById('calc');
  calc && !calc.hidden && /P = \[1\/2, 1\/3, 1\/6; 0, 1\/3, 2\/3; 1\/2, 0, 1\/2\]/
    .test(d.getElementById('calc-log').textContent)
    ? ok('to calculator opens it and defines P') : fail('P did not reach the calculator');
  menu.hidden ? ok('and the menu lets go') : fail('the menu stayed open');
  d.querySelectorAll('#prob-chips .prob-chip')[1].click();
  d.getElementById('probmenu-calc').click();
  window.Calc.run('p*P^3');
  /59\/144, 43\/216, 169\/432/.test(d.getElementById('calc-log').textContent)
    ? ok('p*P^3 then shows fractions') : fail('log: ' + d.getElementById('calc-log').textContent);

  // Into the typed answer, at the caret.
  const box = d.getElementById('saybox');
  box.value = 'so  is the matrix';
  box.setSelectionRange(3, 3);
  chip0.click();
  d.getElementById('probmenu-say').click();
  box.value.indexOf('so $P=\\begin{pmatrix}') === 0 && /\\end\{pmatrix\}\$ is the matrix$/.test(box.value)
    ? ok('into typed answer puts $tex$ at the caret') : fail('typed answer: ' + box.value);

  // Copy TeX. The menu still says what the last tap did; Escape lets it go.
  d.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  menu.hidden ? ok('Escape lets the menu go') : fail('Escape left the menu open');
  chip0.click();
  d.getElementById('probmenu-copy').click();
  copied === problem.givens[0].tex ? ok('copy TeX puts the TeX on the clipboard')
                                   : fail('copied: ' + copied);

  // A symbolic given keeps its chip, without the calculator.
  const sym = JSON.parse(JSON.stringify(problem));
  sym.givens[1].calc = null;
  window.__render(frame(sym));
  d.querySelectorAll('#prob-chips .prob-chip')[1].click();
  d.querySelectorAll('#prob-chips .prob-chip').length === 2
    && d.getElementById('probmenu-calc').hidden && !d.getElementById('probmenu-say').hidden
    ? ok('a symbolic given still shows, without "to calculator"')
    : fail('symbolic given handled wrongly');

  // The picker switches the problem.
  const pick = d.getElementById('prob-pick');
  pick.value = '14';
  pick.dispatchEvent(new window.Event('change', { bubbles: true }));
  const last = posted[posted.length - 1] || {};
  /\/s\/20261023-120000\/problem$/.test(last.url) && last.body.label === '14'
    ? ok('the picker posts the session\'s /problem with the label')
    : fail('picker posted ' + JSON.stringify(last));
} catch (e) { fail('problem bar: ' + (e.stack || e.message)); }

// Onto the page: the given, typeset, on the open answer's surface.
setTimeout(() => {
  try {
    window.__render(frame(problem));
    const chip = d.querySelector('#prob-chips .prob-chip');
    d.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    chip.click();
    const page = d.getElementById('probmenu-page');
    page && !page.hidden ? ok('a chip with a figure offers "onto the page"')
                         : fail('no "onto the page" in the chip menu');
    page.click();
    setTimeout(() => {
      const said = d.getElementById('probmenu-said').textContent;
      /P is on the page/.test(said) && window.__writerDebug
        ? ok('and it lands on the writing surface: ' + said)
        : fail('onto the page said: ' + said);
      console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                                : '\nthe problem stays on screen, and its givens go anywhere');
      process.exit(errors.length ? 1 : 0);
    }, 300);
  } catch (e) {
    fail('onto the page: ' + (e.stack || e.message));
    process.exit(1);
  }
}, 100);
