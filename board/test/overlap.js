// Nothing on the map may be drawn on top of anything else that is read or
// tapped.
//
// SVG text does not wrap, ellipsize or clip, so every collision on this picture
// is one the layout has to prevent by measuring. These are the places it did
// not, each found on a real workspace:
//
//   * THE REGION'S TITLE RAN UNDER ITS BUTTON. "Papers & presentations · 46"
//     was drawn where it started and never measured, and "＋ new paper or deck"
//     was right-aligned on the same baseline -- so on Galois Theory the count
//     sat under the button, and on a phone the button covered the whole title.
//   * A STACKED REGION'S ROWS STUCK OUT OF ITS PLATE. One column wide with no
//     right padding, so a row's highlight ran past the border.
//   * A NAME RAN UNDER THE LOOK-INSIDE ARROW, and a last line of text under the
//     other-ways dots. Both are filled circles, drawn after the text.
//   * AN ARROW'S WORD WAS BURIED UNDER THE BOXES at its ends, or behind a box it
//     passes on a phone.
//
// The canvas here measures WIDE, roughly as OpenDyslexic does, because the
// default face is the one the defect was reported in. A narrow measurer is how
// the region-header overlap sailed through `test/shelf.js`.
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
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// One measurer, used by the page and by the checks, so "how wide is this text"
// has a single answer on both sides.
function measure(s, size) {
  let w = 0;
  for (const ch of String(s)) {
    w += size * (ch === ch.toUpperCase() && ch !== ch.toLowerCase() ? 1.0
                 : ch === ' ' ? 0.42 : 0.78);
  }
  return w;
}

function board(plane) {
  const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
    runScripts: 'outside-only', pretendToBeVisual: true,
    url: 'https://board.test/board',
  });
  const { window } = dom;
  window.HTMLCanvasElement.prototype.getContext = function (kind) {
    if (kind !== '2d') return new Proxy({}, { get: () => () => {}, set: () => true });
    const ctx = {
      font: '',
      measureText(s) {
        const size = parseFloat(/(\d+(?:\.\d+)?)px/.exec(ctx.font || '15px')[1]);
        return { width: measure(s, size) };
      },
    };
    return new Proxy(ctx, {
      get: (t, k) => (k in t ? t[k] : () => {}),
      set: (t, k, v) => { t[k] = v; return true; },
    });
  };
  window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
  Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => plane });
  Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 620 });
  window.HTMLElement.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: plane, height: 620,
             right: plane, bottom: 620, x: 0, y: 0 };
  };
  window.Element.prototype.scrollIntoView = function () {};
  window.Element.prototype.setPointerCapture = function () {};
  window.Element.prototype.releasePointerCapture = function () {};
  window.fetch = (u, opts) => {
    if (opts && opts.body) {
      return Promise.resolve({ json: () => Promise.resolve({ ok: true }) });
    }
    if (/slate\/state/.test(String(u))) {
      return Promise.resolve({ json: () => Promise.resolve({ pages: [] }) });
    }
    return new Promise(() => {});
  };
  window.renderMathInElement = () => {};
  window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  window.scrollTo = () => {};
  window.EventSource = function () {
    this.readyState = 1; this.close = function () {};
    this.addEventListener = function () {};
  };
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
  });
  for (const f of ['typeface.js', 'macros.js', 'gauge.js', 'plane-core.js',
                   'slate-core.js', 'annotate.js', 'shot.js']) {
    try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
    catch (e) { fail(f + ': ' + e.message); }
  }
  let src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
  src = src.replace('})();', 'window.__render = render;\n})();');
  try { window.eval(src); }
  catch (e) { fail('board.js: ' + e.message); }
  return window;
}

function node(over) {
  const out = Object.assign({
    id: 'x', name: 'x', also: '', kind: 'part', does: '', status: 'unknown',
    files: [], dir: '', steps: [], doc: '', slide: null, note: '', hw: '',
    chapter: '', docs: 0,
  }, over);
  if (out.inside === undefined) out.inside = (out.files || []).length;
  return out;
}

function docs(n, stem) {
  return Array.from({ length: n }, (_, i) => (
    { id: stem + '-' + i, name: 'Doc ' + i,
      file: 'ch06 ruler and compass constructions notes ' + i,
      kind: 'paper', pdf: true }));
}

// The Galois Theory region: forty-six documents in two groups.
function payload(groups) {
  const total = groups.reduce((n, g) => n + g.docs.length, 0);
  return {
    state: { course: 'Galois-Theory', session: 'lecture', chapter: '' },
    cards: [], turns: [], messages: [], uploads: [], slate: null,
    notes: [], notes_sent: [], text_drafts: {}, unsaved: 0,
    push: null, export: null, papers: {}, agent: null, waiting: 0,
    history: 0, sets: [], contents: { chapters: [], sets: [] },
    review: null, walk: null, plan: null, reading: { documents: [] },
    map: {
      version: 2, title: '', steps: 0, total: 3,
      why: 'Written for this workspace.',
      nodes: [
        // A part that opens AND has other ways: both top-right and bottom-right
        // controls, with a name and a description that fill their lines.
        // The name is one long token, which the wrap breaks at the full room;
        // the description is short words, so every line fills to the edge.
        node({ id: 'typist', name: 'measurement_campaign_for_every_typist.py',
               does: 'run it on a set of the wav and keep the words and the turns '
                     + 'so a b c d e f g h i j k l m n o p q r s t u v w x y z',

               files: ['psych_asr/typist/run.py', 'psych_asr/typist/io.py'],
               dir: 'psych_asr/typist' }),
        node({ id: 'joiner', name: 'the joiner', does: 'Join words to turns.',
               files: ['psych_asr/joiner.py'], dir: 'psych_asr' }),
        node({ id: 'grader', name: 'the grader', does: 'Grade it.',
               files: ['psych_asr/grader.py'], dir: 'psych_asr' }),
      ],
      edges: [
        { from: 'typist', to: 'joiner', weight: 1, label: 'the reference' },
        { from: 'joiner', to: 'grader', weight: 1, label: 'a graded transcript' },
        // Skips the joiner: stacked, its midpoint is inside the joiner's box.
        { from: 'typist', to: 'grader', weight: 1, label: 'timed words' },
      ],
      loose: [],
      documents: { total: total, groups: groups },
    },
  };
}

const num = (el, k) => +el.getAttribute(k);
const rect = (el) => ({ x: num(el, 'x'), y: num(el, 'y'),
                        w: num(el, 'width'), h: num(el, 'height') });
const meets = (a, b) => a.x < b.x + b.w && a.x + a.w > b.x
                        && a.y < b.y + b.h && a.y + a.h > b.y;
// A line of text as the box its glyphs fill: baseline less the cap height.
const textBox = (t, size) => {
  const anchor = t.getAttribute('text-anchor');
  const w = measure(t.textContent, size);
  const x = num(t, 'x') - (anchor === 'middle' ? w / 2 : 0);
  return { x: x, y: num(t, 'y') - size * 0.75, w: w, h: size * 0.75 };
};

async function region(label, plane, groups) {
  const w = board(plane);
  const doc = w.document;
  w.__render(payload(groups));
  await sleep(20);
  const g = doc.querySelector('#map-sheet .docs-region');
  if (!g) { fail(label + ': there is no documents region'); return null; }
  const plate = rect(g.querySelector('rect.region'));
  const title = g.querySelector('.region-name');
  const btn = rect(g.querySelector('.region-new rect'));
  const tb = textBox(title, 15);

  !meets(tb, btn) && (tb.x + tb.w <= btn.x - 8 || btn.y >= tb.y + tb.h)
    ? ok(label + ': the title and "new paper or deck" do not overlap ('
         + title.textContent + ')')
    : fail(label + ': the title ends at ' + Math.round(tb.x + tb.w)
           + ' and the button starts at ' + Math.round(btn.x)
           + ' on the same row -- the count is under the button');
  /· \d+$/.test(title.textContent)
    ? ok(label + ': and the count is still there to read')
    : fail(label + ': the title lost its count: ' + title.textContent);
  tb.x + tb.w <= plate.x + plate.w - 8 && btn.x >= plate.x
    && btn.x + btn.w <= plate.x + plate.w
    ? ok(label + ': both sit inside the plate')
    : fail(label + ': the head runs out of the plate ' + JSON.stringify(
        { title: [tb.x, tb.x + tb.w], btn: [btn.x, btn.x + btn.w],
          plate: [plate.x, plate.x + plate.w] }));
  const first = g.querySelector('.region-group');
  num(first, 'y') - 10.5 * 0.75 > btn.y + btn.h
    ? ok(label + ': the first group starts below the button')
    : fail(label + ': the first group heading is drawn into the head');

  const rows = Array.prototype.slice.call(g.querySelectorAll('.region-doc'));
  const out = rows.filter((r) => {
    const hi = rect(r.querySelector('rect'));
    const tx = textBox(r.querySelector('text'), 12.5);
    return hi.x + hi.w > plate.x + plate.w || tx.x + tx.w > hi.x + hi.w
           || hi.y + hi.h > plate.y + plate.h;
  });
  rows.length && !out.length
    ? ok(label + ': every document row and its label stay inside the plate')
    : fail(label + ': ' + out.length + ' of ' + rows.length
           + ' rows run past the plate');
  return w;
}

(async function () {
  const two = [{ key: 'papers', label: 'papers', docs: docs(40, 'p') },
               { key: 'writeups', label: 'write-ups', docs: docs(6, 'w') }];
  const one = [{ key: 'papers', label: 'papers', docs: docs(46, 'p') }];

  // ------------------------------------------- the region's head, everywhere
  await region('two groups, wide', 980, two);
  await region('one group, wide', 980, one);
  const phone = await region('stacked on a phone', 390, two);

  // ---------------------------------------- the boxes' corners and arrows
  for (const [label, w] of [['wide', board(980)], ['stacked', phone]]) {
    const doc = w.document;
    if (label === 'wide') { w.__render(payload(two)); await sleep(20); }
    const box = doc.querySelector('#map-sheet .node[data-id="typist"]');
    const b = rect(box.querySelector('rect.box'));
    const dig = box.querySelector('.dig circle');
    const ways = box.querySelector('.ways circle');
    const circ = (c) => ({ x: num(c, 'cx') - 10, y: num(c, 'cy') - 10, w: 20, h: 20 });
    const lines = [];
    box.querySelectorAll('text.name').forEach((t) => lines.push(textBox(t, 15)));
    box.querySelectorAll('text.also').forEach((t) => lines.push(textBox(t, 11)));
    box.querySelectorAll('text.does').forEach((t) => lines.push(textBox(t, 12)));
    dig && !lines.some((l) => meets(l, circ(dig)))
      ? ok(label + ': no line of the name runs under the look-inside arrow')
      : fail(label + ': a name line runs under the look-inside arrow');
    ways && !lines.some((l) => meets(l, circ(ways)))
      ? ok(label + ': no line of text runs under the other-ways dots')
      : fail(label + ': the last line of text runs under the other-ways dots');
    lines.every((l) => l.x + l.w <= b.x + b.w)
      ? ok(label + ': and every line ends inside its box')
      : fail(label + ': a line of text runs out of its box');

    const boxes = Array.prototype.map.call(
      doc.querySelectorAll('#map-sheet .node rect.box'), rect);
    const plates = Array.prototype.map.call(
      doc.querySelectorAll('#map-sheet rect.edge-plate'), rect);
    // A plate between two stacked boxes touches their borders by a pixel; that
    // is a plate in the gap, not a word under a box.
    const inset = (p) => ({ x: p.x + 2, y: p.y + 2, w: p.w - 4, h: p.h - 4 });
    const buried = plates.filter((p) => boxes.some((q) => meets(inset(p), q)));
    !buried.length
      ? ok(label + ': no arrow\'s word is drawn under a box ('
           + plates.length + ' drawn)')
      : fail(label + ': ' + buried.length + ' arrow labels are under a box');
    const tips = Array.prototype.map.call(
      doc.querySelectorAll('#map-sheet path.edge title'), (t) => t.textContent);
    const shown = Array.prototype.map.call(
      doc.querySelectorAll('#map-sheet text.edge-label'), (t) => t.textContent);
    ['the reference', 'a graded transcript', 'timed words'].every(
      (word) => shown.indexOf(word) !== -1 || tips.indexOf(word) !== -1)
      ? ok(label + ': and a word that is cut or dropped is still the arrow\'s tooltip')
      : fail(label + ': an arrow lost its word: shown ' + JSON.stringify(shown)
             + ', tips ' + JSON.stringify(tips));
  }

  if (errors.length) {
    console.log('\n' + errors.length + ' failed');
    process.exit(1);
  }
  console.log('\nall overlap checks passed');
})();
