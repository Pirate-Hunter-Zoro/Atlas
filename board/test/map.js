// The map on the glass: a picture of the repository, the work drawn on it, and
// the ways to work on any part of it.
//
// The server's half is `test/map.py`. This is the half that decides whether it
// is any good on an iPad, and it is driven in a real DOM because every defect in
// this family is one a stub reports as fine:
//
//   * THE TEXT MUST FIT ITS BOX. The first version wrapped labels by counting
//     characters against an assumed width, and a line of capitals is half again
//     wider than that assumption -- so the words ran out of their boxes. It was
//     reported as the visual being "shit", which it was.
//   * THE LAYOUT MUST BE A GRAPH, NOT A COLUMN. Ranks across, boxes down, and a
//     long chain wrapped into bands rather than drawn as a six-thousand-pixel
//     ribbon -- which is the same one-direction failure the column was rejected
//     for, turned on its side.
//   * THE SAME REPOSITORY MUST LAY OUT THE SAME WAY TWICE. A picture that
//     settles somewhere different on each open is not one you can learn.
//   * A TAP MUST OPEN THE RIGHT SITTING. The sheet is the whole point of the
//     map, and an option that posts the wrong body is a sitting about the wrong
//     thing with no way to tell from the outside.
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

// One store, shared by every board in this file, so "what was remembered" is a
// thing the next board can be asked about.
const store = {};
let storeThrows = false;
const posts = [];
// What the board is told when it asks for a sitting. Empty means yes; set it to
// a reason and `/session` refuses, which is the one thing that puts the sheet
// in front of somebody who only tapped a box.
let refuse = '';
const insideAsks = [];
const treeAsks = [];
// What `map.inside` answers with, keyed by the id that was asked for. `evaluate`
// is two Python files with a real import between them; `slurm_jobs` is a shell
// script, which nothing here parses -- so it reports its definitions, draws no
// arrows, and says `exact` is false.
const insides = {
  evaluate: {
    ok: true, of: 'evaluate', name: 'evaluate', depth: 'module', up: '',
    exact: true, total: 2, capped: false,
    why: 'The files in evaluate, and what they import.',
    nodes: [
      { id: 'in-grade-py', name: 'grade.py', also: 'psych_asr/evaluate',
        kind: 'module', does: 'Grade a candidate.', status: 'unknown',
        files: ['psych_asr/evaluate/grade.py'], dir: 'psych_asr/evaluate',
        steps: [], doc: '', slide: null, note: '', exact: true, inside: 1 },
      { id: 'in-score-py', name: 'score.py', also: 'psych_asr/evaluate',
        kind: 'module', does: 'The score.', status: 'unknown',
        files: ['psych_asr/evaluate/score.py'], dir: 'psych_asr/evaluate',
        steps: [], doc: '', slide: null, note: '', exact: true, inside: 1 },
      { id: 'artifacts', name: 'artifacts', also: 'psych_asr/artifacts',
        kind: 'part', does: 'The Stage 1 filename convention.',
        status: 'unknown', files: [], dir: '', steps: [], doc: '',
        slide: null, note: '', outside: true },
    ],
    edges: [{ from: 'in-grade-py', to: 'in-score-py', weight: 2, label: '' },
            { from: 'in-grade-py', to: 'artifacts', weight: 5, label: '' }],
  },
  'in-grade-py': {
    ok: true, of: 'in-grade-py', name: 'grade.py', depth: 'symbol',
    up: 'evaluate', exact: true, total: 2, capped: false,
    why: 'What grade.py defines, and what each definition uses.',
    nodes: [
      { id: 'at-grade-finding', name: 'Finding', also: 'class', kind: 'symbol',
        does: 'One disagreement.', status: 'unknown',
        files: ['psych_asr/evaluate/grade.py'], dir: 'psych_asr/evaluate',
        steps: [], doc: '', slide: null, note: '', symbol: 'Finding',
        exact: true, line: 4 },
      { id: 'at-grade-grade', name: 'grade', also: 'function', kind: 'symbol',
        does: 'Grade a candidate against the reference.', status: 'unknown',
        files: ['psych_asr/evaluate/grade.py'], dir: 'psych_asr/evaluate',
        steps: [], doc: '', slide: null, note: '', symbol: 'grade',
        exact: true, line: 9 },
    ],
    edges: [{ from: 'at-grade-grade', to: 'at-grade-finding', weight: 1,
              label: '' }],
  },
  apart: {
    ok: true, of: 'apart', name: 'slurm_jobs', depth: 'module', up: '',
    exact: true, total: 1, capped: false, why: 'The files in slurm_jobs.',
    nodes: [
      { id: 'in-run-sh', name: 'run.sh', also: 'slurm_jobs', kind: 'module',
        does: '', status: 'unknown', files: ['slurm_jobs/run.sh'],
        dir: 'slurm_jobs', steps: [], doc: '', slide: null, note: '',
        exact: false, inside: 1 },
    ],
    edges: [],
  },
  'in-run-sh': {
    ok: true, of: 'in-run-sh', name: 'run.sh', depth: 'symbol', up: 'apart',
    exact: false, total: 1, capped: false,
    why: 'found by pattern rather than parsed, so its arrows are not drawn',
    nodes: [
      { id: 'at-run-stage', name: 'stage', also: 'function', kind: 'symbol',
        does: 'Stage the model.', status: 'unknown',
        files: ['slurm_jobs/run.sh'], dir: 'slurm_jobs', steps: [], doc: '',
        slide: null, note: '', symbol: 'stage', exact: false, line: 12 },
    ],
    edges: [],
  },
};
// A vendor tree: its own top-level picture, and one box of it opened. The ids
// are deliberately ones this workspace's map also has -- `evaluate` is a box of
// PSYCH-ASR's — because the failure to catch is a tap in a foreign picture being
// answered out of the local one.
const trees = {
  'vendor/colibri': {
    ok: true, of: '', name: 'colibri', depth: 'tree', kind: 'tree', up: '',
    tree: 'vendor/colibri', exact: true, total: 2, capped: false,
    why: 'colibri is pulled and not written here: read it and trace it, and '
       + 'change nothing in it.',
    nodes: [
      { id: 'bin', name: 'bin', also: 'bin', kind: 'part',
        does: 'The driver commands.', status: 'unknown', files: ['bin/coli-up'],
        dir: 'bin', steps: [], doc: '', slide: null, note: '', inside: 1 },
      { id: 'evaluate', name: 'src', also: 'src', kind: 'part',
        does: 'The engine.', status: 'unknown', files: ['src/engine.c'],
        dir: 'src', steps: [], doc: '', slide: null, note: '', inside: 1 },
    ],
    edges: [],
  },
  'vendor/colibri/inside/bin': {
    ok: true, of: 'bin', name: 'bin', depth: 'module', up: '',
    tree: 'vendor/colibri', exact: false, total: 1, capped: false,
    why: 'The files in bin.',
    nodes: [
      { id: 'in-coli-up', name: 'coli-up', also: 'bin', kind: 'module',
        does: 'Warm the server.', status: 'unknown', files: ['bin/coli-up'],
        dir: 'bin', steps: [], doc: '', slide: null, note: '', exact: false,
        inside: 1 },
    ],
    edges: [],
  },
};

function board(W, H, face) {
  const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
    runScripts: 'outside-only', pretendToBeVisual: true,
    url: 'https://board.test/board',
  });
  const { window } = dom;
  // A canvas that MEASURES. The whole point of the wrapping change is that the
  // text is measured rather than guessed, so a stub that returns nothing would
  // test the fallback and never the thing. This one is proportional and gives
  // capitals their real extra width, which is what broke the estimate.
  window.HTMLCanvasElement.prototype.getContext = function (kind) {
    if (kind !== '2d') return new Proxy({}, { get: () => () => {}, set: () => true });
    const ctx = {
      font: '',
      measureText(s) {
        const size = parseFloat(/(\d+(?:\.\d+)?)px/.exec(ctx.font || '15px') [1]);
        let w = 0;
        for (const ch of String(s)) {
          w += size * (ch === ch.toUpperCase() && ch !== ch.toLowerCase() ? 0.72
                       : ch === ' ' ? 0.28 : 0.52);
        }
        // A canvas answers in the face it can resolve AT THAT MOMENT. Before the
        // web font has loaded that is the fallback, which is narrower than the
        // face the label will actually be painted in.
        return { width: face && !face.loaded ? w * 0.7 : w };
      },
    };
    return new Proxy(ctx, {
      get: (t, k) => (k in t ? t[k] : () => {}),
      set: (t, k, v) => { t[k] = v; return true; },
    });
  };
  window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
  Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => W || 980 });
  Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => H || 620 });
  window.HTMLElement.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: W || 980, height: H || 620,
             right: W || 980, bottom: H || 620, x: 0, y: 0 };
  };
  window.Element.prototype.scrollIntoView = function () {};
  window.Element.prototype.setPointerCapture = function () {};
  window.Element.prototype.releasePointerCapture = function () {};
  window.fetch = (u, opts) => {
    if (/slate\/state/.test(String(u))) {
      return Promise.resolve({ json: () => Promise.resolve({ pages: [] }) });
    }
    // ONE LEVEL DOWN THE MAP. Derived on the tap rather than carried on the
    // payload, because the payload is polled four times a second and this
    // parses files whole.
    const deep = /^\/map\/inside\/(.+)$/.exec(String(u));
    if (deep) {
      insideAsks.push(decodeURIComponent(deep[1]));
      const answer = insides[decodeURIComponent(deep[1])];
      return Promise.resolve({
        json: () => Promise.resolve(answer
          || { ok: false, error: 'there is nothing inside that' }),
      });
    }
    // A VENDOR TREE, DRAWN ON THIS BOARD. It is not this workspace's picture
    // and there is no board in somebody else's repository, so it arrives in
    // the shape `map.inside` answers in and is asked for under its own name.
    const foreign = /^\/map\/tree\/([^?]+)$/.exec(String(u));
    if (foreign) {
      treeAsks.push(decodeURIComponent(foreign[1]));
      const answer = trees[decodeURIComponent(foreign[1])];
      return Promise.resolve({
        json: () => Promise.resolve(answer || { ok: false, error: 'no such tree' }),
      });
    }
    if (opts && opts.body) {
      posts.push({ url: String(u), body: JSON.parse(opts.body) });
      const said = refuse && /\/session$/.test(String(u))
        ? { ok: false, error: refuse } : { ok: true };
      return Promise.resolve({ json: () => Promise.resolve(said) });
    }
    return new Promise(() => {});
  };
  window.renderMathInElement = () => {};
  window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  window.scrollTo = () => {};
  if (face) {
    // A FontFaceSet that has not settled yet, and a way to say when it does.
    const dones = [];
    let settle;
    const ready = new Promise((r) => { settle = r; });
    Object.defineProperty(window.document, 'fonts', {
      configurable: true,
      value: {
        ready,
        addEventListener: (kind, fn) => { if (kind === 'loadingdone') dones.push(fn); },
      },
    });
    face.land = () => {
      face.loaded = true;
      settle();
      dones.forEach((fn) => { try { fn(); } catch (e) {} });
    };
  }
  window.EventSource = function () {
    this.readyState = 1; this.close = function () {}; this.addEventListener = function () {};
  };
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      getItem: (k) => {
        if (storeThrows) throw new Error('the site data is blocked');
        return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null;
      },
      setItem: (k, v) => {
        if (storeThrows) throw new Error('the site data is blocked');
        store[k] = String(v);
      },
      removeItem: (k) => { delete store[k]; },
    },
  });
  for (const f of ['typeface.js', 'macros.js', 'gauge.js', 'plane-core.js', 'slate-core.js',
                   'annotate.js', 'shot.js']) {
    try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
    catch (e) { fail(f + ': ' + e.message); }
  }
  let src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
  src = src.replace('})();',
    'window.__render = render;\nwindow.__openMap = openMap;\n'
    + 'window.__closeMap = closeMap;\nwindow.__mapView = function () { return mapView; };\n'
    + 'window.__openWork = openWork;\nwindow.__wrap = mapWrap;\n'
    + 'window.__width = mapWidth;\nwindow.__mapDig = mapDig;\n'
    + 'window.__mapOut = mapOut;\nwindow.__takeWork = takeWork;\n'
    + 'window.__mapTreeOpen = mapTreeOpen;\n})();');
  try { window.eval(src); }
  catch (e) { fail('board.js: ' + e.message); }
  return window;
}

function node(over) {
  const out = Object.assign({
    id: 'x', name: 'x', also: '', kind: 'part', does: '', status: 'unknown',
    files: [], dir: '', steps: [], doc: '', slide: null, note: '',
  }, over);
  // WHETHER THERE IS ANYTHING UNDER THIS BOX, said on the box rather than
  // discovered by tapping it and getting nothing. `map.status` computes it the
  // same way, off the files the box carries.
  if (out.inside === undefined) out.inside = (out.files || []).length;
  return out;
}

// A project: four parts, a real dependency chain, a cycle, a document, and the
// plan's steps sitting on the boxes they name.
function makeMap() {
  return {
    version: 2,
    title: '',
    why: "Drawn from this repository's own source and what it imports.",
    steps: 4,
    total: 5,
    nodes: [
      node({ id: 'cli', name: 'cli', also: 'psych_asr/cli', dir: 'psych_asr/cli',
             does: 'Stage 2: apply the QC error log to the baseline transcript.',
             status: 'next', files: ['psych_asr/cli/grade_arms.py'],
             steps: [
               { num: '1', title: 'THE TYPIST BAKE-OFF — VARY THE ASR MODEL',
                 label: '1. THE TYPIST BAKE-OFF', summary: 'Grade each candidate.',
                 order: 1, from: 'PSYCH-ASR' },
               { num: '4', title: 'CALIBRATE THE SCORER',
                 label: '4. CALIBRATE THE SCORER', summary: 'Assistant-side.',
                 order: 4, from: 'PSYCH-ASR' },
             ] }),
      node({ id: 'evaluate', name: 'evaluate', also: 'psych_asr/evaluate',
             dir: 'psych_asr/evaluate',
             does: 'Grading a machine transcript the way the annotator graded the first.',
             status: 'later', files: ['psych_asr/evaluate/grade.py',
                                      'psych_asr/evaluate/score.py'],
             steps: [{ num: '2', title: 'THE STOPWATCH', label: '2. THE STOPWATCH',
                       summary: 'Re-align.', order: 2, from: 'PSYCH-ASR' }] }),
      node({ id: 'artifacts', name: 'artifacts', also: 'psych_asr/artifacts',
             dir: 'psych_asr/artifacts', does: 'The Stage 1 filename convention.',
             files: ['psych_asr/artifacts/naming.py'] }),
      node({ id: 'apart', name: 'slurm_jobs', also: 'slurm_jobs', dir: 'slurm_jobs',
             does: 'Job scripts.', files: ['slurm_jobs/run.sh'] }),
      node({ id: 'doc-deck', name: 'Stage 2 walkthrough', also: 'document',
             kind: 'doc', doc: 'stage2-deck',
             does: 'Written about how this works.' }),
      // A PROBLEM SET, which is the one box whose tap is a different KIND of
      // sitting rather than a differently scoped one. It carries the set by
      // the name the course gave it -- the derived map takes that from
      // `homework.sets` and a written map declares it.
      node({ id: 'hw-one', name: 'hw01', also: 'problem set', kind: 'set',
             hw: 'hw01' }),
    ],
    edges: [
      { from: 'cli', to: 'evaluate', weight: 3, label: '' },
      { from: 'evaluate', to: 'artifacts', weight: 11, label: '' },
      { from: 'artifacts', to: 'evaluate', weight: 1, label: '' },   // a cycle
      { from: 'cli', to: 'nowhere', weight: 1, label: '' },          // names nothing
    ],
    loose: [{ num: '9', title: 'BUY A BIGGER DESK', label: '9. BUY A BIGGER DESK',
              summary: 'Nothing in this repository.', order: 9, from: 'PSYCH-ASR' }],
  };
}

// A long chain: twenty chapters, each pointing at the next. This is the shape
// that came out six and a half thousand pixels wide.
function makeChain() {
  const nodes = [], edges = [];
  for (let i = 1; i <= 20; i++) {
    nodes.push(node({ id: 'ch-' + i, name: 'Ch ' + i + ' — a chapter with a title',
                      kind: 'chapter', also: 'Chapter ' + i }));
    if (i > 1) edges.push({ from: 'ch-' + (i - 1), to: 'ch-' + i, weight: 1, label: '' });
  }
  return { version: 2, title: '', why: '', steps: 0, total: 20,
           nodes: nodes, edges: edges, loose: [] };
}

function payload(over) {
  return Object.assign({
    state: { course: 'PSYCH-ASR', session: 'lecture', chapter: '' },
    cards: [], turns: [], messages: [], uploads: [], slate: null,
    notes: [], notes_sent: [], text_drafts: {}, unsaved: 0,
    push: null, export: null, papers: {}, agent: null, waiting: 0,
    history: 0, sets: [], contents: { chapters: [], sets: [] },
    review: null, walk: null, plan: null,
    reading: { documents: [{ id: 'stage2-deck', name: 'Stage 2 walkthrough' }] },
    map: makeMap(),
  }, over || {});
}

const at = (doc, id) => {
  const r = doc.querySelector('#map-sheet .node[data-id="' + id + '"] rect.box');
  return r ? { x: +r.getAttribute('x'), y: +r.getAttribute('y'),
               w: +r.getAttribute('width'), h: +r.getAttribute('height') } : null;
};

(async function () {
  // ------------------------------------------------- the picture, measured
  {
    const w = board();
    const doc = w.document;
    w.__render(payload());
    await sleep(15);

    !doc.getElementById('map').hidden
      ? ok('a course nobody has opened on this device opens on the map')
      : fail('the default landing is not the map');

    const boxes = doc.querySelectorAll('#map-sheet .node');
    boxes.length === 6
      ? ok('every part of the repository is a box (6)')
      : fail('the map drew ' + boxes.length + ' boxes, not 6');

    // THE DEFECT THIS FILE EXISTS FOR. Every line of text must fit inside the
    // box it is drawn in, measured in the same face at the same size.
    let widest = 0, over = [];
    boxes.forEach((g) => {
      const box = +g.querySelector('rect.box').getAttribute('width');
      g.querySelectorAll('text').forEach((t) => {
        if (t.parentNode !== g) return;                 // chip numerals are centred
        const cls = t.getAttribute('class');
        const size = cls === 'name' ? 15 : cls === 'also' ? 11 : 12;
        const weight = cls === 'name' ? 650 : 400;
        const wide = w.__width(t.textContent, size, weight);
        widest = Math.max(widest, wide);
        // The padding either side, plus the status stripe.
        if (wide > box - 13 * 2 - 5 + 0.5) over.push(t.textContent);
      });
    });
    !over.length
      ? ok('every label fits inside its own box (widest ' + Math.round(widest) + 'px)')
      : fail('text runs out of the box: ' + JSON.stringify(over.slice(0, 3)));

    // ...including SHOUTED text, which is what the character estimate got wrong.
    {
      const room = 226 - 13 * 2 - 5;
      const lines = w.__wrap('THE TYPIST BAKE-OFF — VARY THE ASR MODEL', 15, 650, room, 2);
      const fits = lines.every((l) => w.__width(l, 15, 650) <= room + 0.5);
      fits && lines.length <= 2
        ? ok('and a line of capitals wraps to what it actually measures')
        : fail('capitals still overflow: ' + JSON.stringify(lines));
    }
    {
      const room = 226 - 13 * 2 - 5;
      const lines = w.__wrap('psych_asr/artifacts/naming_conventions_and_more.py',
                             12, 400, room, 2);
      lines.every((l) => w.__width(l, 12, 400) <= room + 0.5)
        ? ok('and one word wider than the box is broken rather than let run')
        : fail('a long unbroken token overflowed: ' + JSON.stringify(lines));
    }

    // ------------------------------------------------------------- the graph
    const cli = at(doc, 'cli'), ev = at(doc, 'evaluate'), art = at(doc, 'artifacts');
    cli && ev && art && ev.x > cli.x && art.x > ev.x
      ? ok('the ranks run across: what everything depends on sits downstream')
      : fail('the graph did not lay out in ranks');
    const apart = at(doc, 'apart'), deck = at(doc, 'doc-deck');
    apart && deck && apart.y > cli.y && Math.abs(apart.y - deck.y) < 1
      ? ok('and what nothing is joined to stands apart, in a band of its own')
      : fail('the unattached parts were wired into the graph or lost');

    const edges = doc.querySelectorAll('#map-sheet path.edge');
    edges.length === 3
      ? ok('an arrow naming a box that is not here is dropped, not drawn to nowhere')
      : fail('drew ' + edges.length + ' arrows; one of the four names nothing');
    doc.querySelectorAll('#map-sheet path.edge.strong').length === 1
      ? ok('and an arrow carrying eleven imports is drawn heavier than one carrying three')
      : fail('nothing distinguishes a heavy dependency from a passing mention');
    doc.querySelectorAll('#map-sheet polygon.edge-head').length === 3
      ? ok('every arrow has a head, so the direction is readable')
      : fail('an arrow was drawn without a head');

    // ------------------------------------------------------------ the chips
    const chips = doc.querySelectorAll('#map-sheet .chip');
    chips.length === 3
      ? ok('each step of the plan is a numbered chip on the box it is about')
      : fail('drew ' + chips.length + ' chips, not 3');
    const nums = [];
    chips.forEach((c) => nums.push(c.querySelector('text').textContent));
    nums.join(',') === '1,4,2'
      ? ok('numbered with the plan\'s own numbers, in the plan\'s own order')
      : fail('chips came out as ' + nums.join(','));
    const hot = doc.querySelector('#map-sheet .chip[data-step="1. THE TYPIST BAKE-OFF"]');
    const cold = doc.querySelector('#map-sheet .chip[data-step="4. CALIBRATE THE SCORER"]');
    /\bnow\b/.test(hot.getAttribute('class')) && /\blater\b/.test(cold.getAttribute('class'))
      ? ok('and coloured by when it should be done, first to last')
      : fail('chips are not coloured in order: ' + hot.getAttribute('class')
             + ' / ' + cold.getAttribute('class'));
    {
      const inside = chips[0].querySelector('circle');
      const box = at(doc, 'cli');
      const cx = +inside.getAttribute('cx'), cy = +inside.getAttribute('cy');
      cx > box.x && cx < box.x + box.w && cy > box.y && cy < box.y + box.h
        ? ok('and drawn inside the box it belongs to')
        : fail('a chip landed outside its box');
    }

    // The steps nothing could place are offered rather than dropped.
    const tray = doc.getElementById('map-loose');
    !tray.hidden && tray.querySelectorAll('.loose-chip').length === 1
      ? ok('a step that names nothing is offered in the tray, not dropped')
      : fail('the unplaced step is not reachable');

    // ------------------------------------------------- the same, twice over
    const was = at(doc, 'evaluate');
    w.__render(payload({ state: { course: 'PSYCH-ASR', session: 'lecture', chapter: 'x' } }));
    await sleep(15);
    const again = at(doc, 'evaluate');
    was.x === again.x && was.y === again.y
      ? ok('the same repository lays out identically every time')
      : fail('the layout moved between two paints of the same map');

    // ------------------------------------------------ panning and pinching
    const plane = doc.getElementById('map-plane');
    const sheet = doc.getElementById('map-sheet');
    const before = w.__mapView().ox;
    const touch = (type, id, x, y) => {
      const ev = new w.Event(type, { bubbles: true });
      ev.pointerId = id; ev.pointerType = 'touch';
      ev.clientX = x; ev.clientY = y;
      (type === 'pointerup' ? w : plane).dispatchEvent(ev);
    };
    touch('pointerdown', 1, 400, 300);
    touch('pointermove', 1, 460, 340);
    await sleep(5);
    Math.abs(w.__mapView().ox - before - 60) < 1e-6
      ? ok('one finger pans the plane')
      : fail('a finger did not pan: ' + before + ' -> ' + w.__mapView().ox);
    /translate\(/.test(sheet.style.transform)
      ? ok('and panning is a transform on the wrapper, never a redraw')
      : fail('the plane does not move by transform: ' + sheet.style.transform);

    const drawnAt = doc.querySelector('#map-sheet svg');
    const k0 = w.__mapView().k;
    touch('pointerdown', 2, 300, 300);
    touch('pointermove', 1, 200, 300);
    touch('pointermove', 2, 700, 300);
    await sleep(5);
    w.__mapView().k > k0
      ? ok('two fingers pinch it')
      : fail('a pinch did nothing: k stayed at ' + k0);
    doc.querySelector('#map-sheet svg') === drawnAt
      ? ok('and a gesture never regenerates the picture')
      : fail('the SVG was rebuilt during a gesture');
    touch('pointerup', 1, 200, 300);
    touch('pointerup', 2, 700, 300);
    const k1 = w.__mapView().k;
    touch('pointerdown', 3, 400, 300);
    touch('pointermove', 3, 500, 300);
    await sleep(5);
    Math.abs(w.__mapView().k - k1) < 1e-9
      ? ok('and one finger after a pinch pans rather than zooming')
      : fail('a lifted finger is still in the map: one finger is zooming');

    w.close();
  }

  // ------------------------------------------------- what a tap on a box does
  //
  // IT OPENS THE SITTING. The style a sitting is run in -- teaching, building,
  // coaching -- is set in the `for:` row and changed there at any moment, so a
  // panel asking for it at the moment of opening was asking a question whose
  // answer was already given: *"these are tutoring styles that I don't want to
  // be selecting when I open up a lesson."* What is left for a box is one
  // sitting, and the tap is it.
  {
    const w = board();
    const doc = w.document;
    w.__render(payload());
    await sleep(15);

    posts.length = 0;
    doc.querySelector('#map-sheet .node[data-id="evaluate"]')
      .dispatchEvent(new w.Event('click', { bubbles: true }));
    await sleep(10);
    const sat = posts.filter((x) => /\/session$/.test(x.url))[0];
    sat && sat.body.session === 'lecture' && sat.body.node === 'evaluate'
      ? ok('a tap on a box opens the sitting for that box')
      : fail('a tap posted ' + JSON.stringify(sat && sat.body));
    sat && !('aim' in sat.body) && !('makes' in sat.body)
      ? ok('and names neither a style nor a product, because a tap chooses neither')
      : fail('the tap carried one of them: ' + JSON.stringify(sat && sat.body));
    // AND SENDS NO STANCE. Who writes the code is the workspace's answer --
    // `config.AIM_STANCE` -- and a browser sending one is the browser deciding,
    // on its own authority, something the repository and its family have said.
    sat && sat.body.stance === undefined
      ? ok('and sends no stance beside it')
      : fail('the browser sent a stance of its own: ' + JSON.stringify(sat.body));
    // THE TAP IS THE INSTRUCTION. Landing on the lesson behind the map and
    // having to find a second button saying "ask the tutor to begin" is the
    // ceremony this replaces, and it was found as a question rather than as a
    // complaint: "do I ask the tutor to begin?"
    sat && sat.body.begin === true
      ? ok('and asks the tutor to start, without a second tap')
      : fail('the sitting opens but nothing starts it');
    doc.getElementById('work').hidden
      ? ok('and no sheet is put in the way of it')
      : fail('the tap still asks a question first');
    doc.getElementById('map').hidden
      ? ok('and the map is left for the lesson the tap opened')
      : fail('the map stayed up over the sitting it opened');

    // A CHIP IS A SITTING TOO, carrying the step as well as the box, so the
    // tutor is told which piece of work it is and not merely which part.
    w.__openMap('tapped');
    await sleep(15);
    posts.length = 0;
    doc.querySelector('#map-sheet .chip[data-step="2. THE STOPWATCH"]')
      .dispatchEvent(new w.Event('click', { bubbles: true }));
    await sleep(10);
    let p = posts.filter((x) => /\/session$/.test(x.url))[0];
    p && p.body.step === '2. THE STOPWATCH' && p.body.node === 'evaluate'
      && p.body.session === 'lecture' && !('aim' in p.body)
      ? ok('tapping a numbered step opens a sitting on that step of that box')
      : fail('the chip posted ' + JSON.stringify(p && p.body));

    // A step in the tray has no box, and still opens.
    w.__openMap('tapped');
    await sleep(15);
    posts.length = 0;
    doc.querySelector('#map-loose .loose-chip')
      .dispatchEvent(new w.Event('click', { bubbles: true }));
    await sleep(10);
    p = posts.filter((x) => /\/session$/.test(x.url))[0];
    p && p.body.step === '9. BUY A BIGGER DESK' && !p.body.node
      ? ok('a step nothing could place still opens a sitting of its own')
      : fail('the loose chip posted ' + JSON.stringify(p && p.body));

    // A PROBLEM SET IS A HOMEWORK SITTING, which is the one thing that box has
    // ever meant. It is the only tap that changes the KIND of sitting rather
    // than what it is scoped to, and the set goes over by the name discovery
    // gave it -- the server looks that up in what the course actually has.
    w.__openMap('tapped');
    await sleep(15);
    posts.length = 0;
    doc.querySelector('#map-sheet .node[data-id="hw-one"]')
      .dispatchEvent(new w.Event('click', { bubbles: true }));
    await sleep(10);
    p = posts.filter((x) => /\/session$/.test(x.url))[0];
    p && p.body.session === 'homework' && p.body.hw === 'hw01'
      && p.body.begin === true && !('aim' in p.body)
      ? ok('a tap on a problem set opens a homework sitting on that set')
      : fail('the set box posted ' + JSON.stringify(p && p.body));

    // A DOCUMENT IS READ. There is no sitting to open about a box that is a
    // write-up and nothing else, so the tap is the reading.
    w.__openMap('tapped');
    await sleep(15);
    posts.length = 0;
    doc.querySelector('#map-sheet .node[data-id="doc-deck"]')
      .dispatchEvent(new w.Event('click', { bubbles: true }));
    await sleep(10);
    !posts.filter((x) => /\/session$/.test(x.url)).length
      ? ok('a tap on a document opens no sitting at all')
      : fail('a document box asked for a sitting: '
             + JSON.stringify(posts.map((x) => x.url)));
    !doc.getElementById('paper').hidden && doc.getElementById('work').hidden
      ? ok('and puts the document on the glass instead')
      : fail('the document was not opened');

    w.close();
  }

  // ------------------------------------------------------- the other ways
  //
  // What the sheet holds is the ways that are CHOSEN OVER SOMETHING: a
  // walkthrough over files, a drill over a part, a document to be shown. A
  // style is never in it -- that row is elsewhere and changes in place -- and
  // neither is a paper or a deck, which are commissioned from the front door.
  {
    const w = board();
    const doc = w.document;
    w.__render(payload());
    await sleep(15);

    const ways = Array.from(doc.querySelectorAll('#map-sheet .ways'))
      .map((g) => g.getAttribute('data-ways'));
    ways.includes('evaluate') && ways.includes('artifacts')
      ? ok('a box with more than one way to work on it carries a control for them')
      : fail('nothing on the picture opens the other ways: ' + JSON.stringify(ways));
    !ways.includes('doc-deck')
      ? ok('and a document does not, because its tap is its one way')
      : fail('a document was given a sheet it has nothing to put in');
    {
      const box = at(doc, 'evaluate');
      const g = doc.querySelector('#map-sheet .ways[data-ways="evaluate"] circle');
      const cx = +g.getAttribute('cx'), cy = +g.getAttribute('cy');
      const dig = doc.querySelector('#map-sheet .dig[data-dig="evaluate"] circle');
      cx > box.x + box.w / 2 && cy > box.y + box.h / 2
        && +dig.getAttribute('cy') < cy
        ? ok('drawn at the bottom right, opposite the one that goes down a level')
        : fail('the two controls are not at opposite corners');
    }

    doc.querySelector('#map-sheet .ways[data-ways="evaluate"]')
      .dispatchEvent(new w.Event('click', { bubbles: true }));
    await sleep(5);
    !doc.getElementById('work').hidden
      ? ok('tapping it asks what else you want to do about that box')
      : fail('the control opened nothing');
    doc.getElementById('work-title').textContent === 'evaluate'
      ? ok('and the sheet is about the box it was tapped on')
      : fail('the sheet named ' + doc.getElementById('work-title').textContent);
    const offered = Array.from(
      doc.querySelectorAll('#work-list .work-way strong')).map((n) => n.textContent);
    offered.join('|') === 'Walk me through the code|Set me problems on it'
      ? ok('offering only the ways held over a scope, and only the ones this box has')
      : fail('the sheet offered ' + JSON.stringify(offered));
    !offered.some((x) => /Teach me|Write the code|Tell me what to write/.test(x))
      ? ok('and never a style, which is changed in the lesson rather than chosen here')
      : fail('a style is still being chosen at the moment of opening');
    !offered.some((x) => /paper|deck/i.test(x))
      ? ok('and never a paper or a deck, which are asked for from the front door')
      : fail('a product is still offered as a way of working');

    const pick = async (id, label) => {
      posts.length = 0;
      w.__openWork(id, '');
      await sleep(5);
      let hit = null;
      doc.querySelectorAll('#work-list .work-way').forEach((b) => {
        if (b.querySelector('strong').textContent === label) hit = b;
      });
      if (!hit) return null;
      hit.dispatchEvent(new w.Event('click', { bubbles: true }));
      await sleep(10);
      return posts.filter((x) => /\/session$/.test(x.url))[0] || null;
    };

    let p = await pick('evaluate', 'Walk me through the code');
    p && p.body.session === 'walk' && p.body.aim === 'trace'
      && p.body.over.join(',') === 'psych_asr/evaluate/grade.py,psych_asr/evaluate/score.py'
      ? ok('“walk me through it” opens a walkthrough over that box\'s own files')
      : fail('wrong body: ' + JSON.stringify(p && p.body));
    p = await pick('evaluate', 'Set me problems on it');
    p && p.body.session === 'review' && p.body.aim === 'drill'
      && p.body.over.join(',') === 'psych_asr/evaluate/'
      ? ok('“set me problems” opens a review scoped to that part')
      : fail('wrong body: ' + JSON.stringify(p && p.body));
    p = await pick('doc-deck', 'Show me the document');
    p === null && !doc.getElementById('paper').hidden
      ? ok('and a document box, asked from the sheet, is read rather than posted')
      : fail('showing a document asked the server for a sitting');

    // WHAT THIS BOX IS WAITING ON is the other thing the sheet says, and it is
    // the reason a box with no way left can still carry the control.
    w.__render(payload({ map: (() => {
      const m = makeMap();
      m.nodes.forEach((n) => { if (n.id === 'cli') n.blockedBy = ['evaluate']; });
      return m;
    })() }));
    await sleep(15);
    doc.querySelector('#map-sheet .ways[data-ways="cli"]')
      .dispatchEvent(new w.Event('click', { bubbles: true }));
    await sleep(5);
    /waiting on evaluate/.test(doc.querySelector('#work .work-blocked').textContent)
      ? ok('and says what the box is waiting on, by the name anybody calls it')
      : fail('the sheet does not say what is blocking the box');

    w.close();
  }

  // ------------------------------------------------------- a refused tap
  //
  // The server is the only thing that can say no -- a box that has moved, a
  // scope that resolves to nothing -- and a tap that silently does nothing is
  // the worst answer available. The reason goes where the question was asked.
  {
    delete store['board.where.PSYCH-ASR'];
    const w = board();
    const doc = w.document;
    w.__render(payload());
    await sleep(15);
    refuse = 'no such part of the map';
    doc.querySelector('#map-sheet .node[data-id="evaluate"]')
      .dispatchEvent(new w.Event('click', { bubbles: true }));
    await sleep(10);
    !doc.getElementById('work').hidden
    && /no such part of the map/.test(doc.getElementById('work-sub').textContent)
      ? ok('a tap the board refuses says why, on the box it was refused about')
      : fail('a refusal left the tap looking broken: '
             + doc.getElementById('work-sub').textContent);
    !doc.getElementById('map').hidden
      ? ok('and the map is still there, with the ways left to try on it')
      : fail('a refusal took the picture away');
    refuse = '';
    w.close();
  }

  // ------------------------------------------ a long chain is not a ribbon
  {
    const w = board(1180, 620);
    const doc = w.document;
    w.__render(payload({ map: makeChain() }));
    await sleep(15);
    const sheet = doc.getElementById('map-sheet');
    const wide = parseFloat(sheet.style.width);
    wide < 2200
      ? ok('twenty chapters in a chain wrap into bands (' + Math.round(wide) + 'px wide)')
      : fail('a chain still draws as a ' + Math.round(wide) + 'px ribbon');
    const first = at(doc, 'ch-1'), seventh = at(doc, 'ch-7');
    seventh && first && seventh.y > first.y && seventh.x <= first.x + 1
      ? ok('and the next band starts back at the left, the way a page is read')
      : fail('the bands did not wrap: ch-7 is at ' + JSON.stringify(seventh));
    w.__mapView().k >= 0.5
      ? ok('and it opens at a size somebody can read (' + w.__mapView().k.toFixed(2) + ')')
      : fail('the map opened at ' + w.__mapView().k.toFixed(2) + ' — a grey smear');
    w.close();
  }

  // ------------------------------------------------------------ phone width
  {
    const w = board(390, 700);
    const doc = w.document;
    w.__render(payload());
    await sleep(15);
    const a = at(doc, 'cli'), b = at(doc, 'evaluate');
    a && b && a.x === b.x && b.y > a.y
      ? ok('at phone width the ranks become one column, read downward')
      : fail('the graph is still ranked across on a 390px screen');
    parseFloat(doc.getElementById('map-sheet').style.width) <= 391
      ? ok('and the picture is no wider than the glass')
      : fail('the map is wider than a 390px screen');
    w.close();
  }

  // ---------------------------------------- a course opens where it was left
  //
  // Set up here rather than relied on from an earlier block: what a test leaves
  // behind is not what a person leaves behind, and a check that passes because
  // of the block above it is a check that stops meaning anything the day
  // somebody reorders the file.
  {
    const w = board();
    const doc = w.document;
    delete store['board.where.PSYCH-ASR'];
    w.__render(payload());
    await sleep(15);
    const plane = doc.getElementById('map-plane');
    const touch = (type, id, x, y) => {
      const ev = new w.Event(type, { bubbles: true });
      ev.pointerId = id; ev.pointerType = 'touch';
      ev.clientX = x; ev.clientY = y;
      (type === 'pointerup' ? w : plane).dispatchEvent(ev);
    };
    touch('pointerdown', 1, 400, 300);
    touch('pointermove', 1, 330, 250);           /* they panned somewhere */
    touch('pointerup', 1, 330, 250);
    /* The control rather than the box: a tap on the box opens its sitting and
       leaves the map, which is a person going somewhere else. Opening a box's
       other ways is a person still reading the picture, and that is the state
       this remembers. */
    doc.querySelector('#map-sheet .ways[data-ways="artifacts"]')
      .dispatchEvent(new w.Event('click', { bubbles: true }));
    await sleep(450);                            /* the plane is remembered once it settles */
    w.close();
  }

  {
    const w = board();
    const doc = w.document;
    w.__render(payload());
    await sleep(15);
    !doc.getElementById('map').hidden
      ? ok('a course left on the map reopens on the map')
      : fail('the remembered surface was not honoured');
    const kept = JSON.parse(store['board.where.PSYCH-ASR'] || '{}');
    const v = w.__mapView();
    Math.abs(v.ox - kept.x) < 1e-6 && Math.abs(v.k - kept.k) < 1e-9
      ? ok('at the part of the map it was left at, and the same magnification')
      : fail('the plane did not come back where it was');
    kept.node === 'artifacts'
      ? ok('with the box last opened still marked as where you are')
      : fail('the box last opened was not remembered: ' + kept.node);
    /\bhere\b/.test((doc.querySelector('#map-sheet .node[data-id="artifacts"]')
                     .getAttribute('class') || ''))
      ? ok('and that box is marked on the picture, not merely recorded')
      : fail('nothing on the map says which box they were on');
    w.__closeMap();
    JSON.parse(store['board.where.PSYCH-ASR'] || '{}').surface === 'lesson'
      ? ok('closing the map remembers that the lesson is where they went')
      : fail('leaving the map was not recorded');
    w.close();
  }

  {
    const w = board();
    w.__render(payload());
    await sleep(15);
    w.document.getElementById('map').hidden
      ? ok('and a course left in a lesson reopens in the lesson, not through the map')
      : fail('a lesson in progress was made to go through the map to get back to it');
    w.close();
  }

  // ---------------------------------------- when the store will not answer
  {
    storeThrows = true;
    const w = board();
    let threw = null;
    w.addEventListener('error', (e) => { threw = e.message; });
    w.__render(payload());
    await sleep(15);
    !threw ? ok('a browser that refuses site data does not break the board')
           : fail('localStorage throwing reached the page: ' + threw);
    !w.document.getElementById('map').hidden
      ? ok('and with nothing remembered, the course opens on the map')
      : fail('a refused store left the board on no surface at all');
    w.close();
    storeThrows = false;
  }

  {
    store['board.where.PSYCH-ASR'] = JSON.stringify({
      surface: 'map', at: Date.now(), x: 'over there', y: null, k: 0, node: 'cli' });
    const w = board();
    w.__render(payload());
    await sleep(15);
    const view = w.__mapView();
    typeof view.k === 'number' && view.k > 0
      ? ok('a half-written record is ignored rather than obeyed')
      : fail('the plane took a scale of ' + view.k + ' out of a bad record');
    w.close();
  }

  {
    store['board.where.PSYCH-ASR'] = JSON.stringify({
      surface: 'lesson', at: Date.now() - 400 * 24 * 3600 * 1000 });
    const w = board();
    w.__render(payload());
    await sleep(15);
    !w.document.getElementById('map').hidden
      ? ok('a record from last year is ignored, and the map is the default')
      : fail('a year-old record was obeyed');
    w.close();
    delete store['board.where.PSYCH-ASR'];
  }

  // ------------------------------------- a repository with nothing in it
  {
    const w = board();
    const doc = w.document;
    w.__render(payload({ map: null }));
    await sleep(15);
    doc.getElementById('map').hidden
      ? ok('a repository with nothing to draw is never sent to an empty plane')
      : fail('the map opened with nothing on it');
    w.__openMap() === false && doc.getElementById('map').hidden
      ? ok('and asking for it says no rather than showing a blank screen')
      : fail('the map opened anyway when there was nothing to draw');
    doc.getElementById('btn-map').hidden
      ? fail('the way to the map was taken away — a guarantee with a condition '
             + 'on it is not a guarantee')
      : ok('the way to the map is still there, and says there is nothing behind it');
    w.close();
  }

  // -------------------------------------------- the map is not the drawer
  {
    const html = fs.readFileSync(path.join(WEB, 'board.html'), 'utf8');
    const right = /<div class="bar-right">([\s\S]*?)<\/div>/.exec(html);
    const controls = right ? (right[1].match(/<(?:button|a|label)\b/g) || []).length : 99;
    controls <= 6
      ? ok('the title bar still carries only what a lesson uses (' + controls + ')')
      : fail('the bar is crowded again: ' + controls + ' controls');
    /id="btn-map"/.test(right ? right[1] : '')
      ? ok('and the way to the map is one of them')
      : fail('the map has no control in the title bar');
    // A glyph on its own is not a label. Asked for as "make that button that
    // takes me back to the map more obvious as something that would take me
    // back to the map".
    /<button id="btn-map"[^>]*>[^<]*\bmap\b/.test(right ? right[1] : '')
      ? ok('and it says what it is rather than being a bare glyph')
      : fail('the map control carries no word');
    (html.match(/class="to-map"[^>]*>[^<]*\bmap\b/g) || []).length >= 6
      ? ok('every copy of it, in every drawer and on the document viewer, says so too')
      : fail('some ways to the map are still unlabelled glyphs');
    /id="barmenu"[\s\S]*id="btn-contents"/.test(html)
      ? ok('the contents drawer kept every entry and moved one tap away')
      : fail('the contents drawer was removed rather than moved');
  }

  // ------------------------------------- measured in the face it is painted in
  //
  // The reading face is a web font, served from this repository and declared
  // `font-display: swap`. Until it has loaded, a canvas measures the FALLBACK --
  // a much narrower face -- so a map drawn on a cold load is laid out for a font
  // it is not painted in, and the words run out of their boxes. That is the
  // defect this whole family of checks exists for, surviving in the one paint
  // everybody sees. Reported as: "words are overflowing each box".
  {
    const face = { loaded: false };
    const w = board(980, 620, face);
    const doc = w.document;
    w.__render(payload());
    await sleep(15);

    // Measured HERE, in the real face, and never through the gauge: the whole
    // defect is that the gauge is holding numbers taken in the wrong one, so
    // asking it whether they fit is asking the accused.
    const realWidth = (text, size) => {
      let x = 0;
      for (const ch of String(text)) {
        x += size * (ch === ch.toUpperCase() && ch !== ch.toLowerCase() ? 0.72
                     : ch === ' ' ? 0.28 : 0.52);
      }
      return x;
    };
    const fits = () => {
      const over = [];
      doc.querySelectorAll('#map-sheet .node').forEach((g) => {
        const box = +g.querySelector('rect.box').getAttribute('width');
        g.querySelectorAll('text').forEach((t) => {
          if (t.parentNode !== g) return;
          const cls = t.getAttribute('class');
          const size = cls === 'name' ? 15 : cls === 'also' ? 11 : 12;
          if (realWidth(t.textContent, size) > box - 13 * 2 - 5 + 0.5) {
            over.push(t.textContent);
          }
        });
      });
      return over;
    };

    // Before the face lands the map IS laid out wrong -- that is not a bug in
    // the map, it is the browser answering with what it has. What must not
    // happen is it staying that way.
    const wrongBefore = fits().length;

    // While the fallback is what is being measured, the lines it produced are
    // too long for the real face -- which is the state the map used to be left
    // in for good.
    const before = doc.querySelectorAll('#map-sheet .node text').length;
    face.land();
    await sleep(25);

    const over = fits();
    wrongBefore > 0
      ? ok('a map drawn before the font loaded does overflow, measured honestly '
           + '(' + wrongBefore + ' line(s))')
      : fail('the fallback face was not narrow enough to reproduce the defect, '
             + 'so this check proves nothing');
    !over.length
      ? ok('once the reading face arrives, every label fits the box it is in')
      : fail('the map kept the measurements it took before the font loaded: '
             + JSON.stringify(over.slice(0, 3)));
    doc.querySelectorAll('#map-sheet .node').length === 6
      ? ok('and the map is still the same map, redrawn rather than rebuilt from a payload')
      : fail('the redraw lost the picture');
    before > 0
      ? ok('and it had been drawn before the face landed, so nothing waited on the font')
      : fail('the map did not draw at all until the font loaded');
    w.Gauge.faceReady()
      ? ok('and the gauge knows its answers are now in the right face')
      : fail('the gauge still believes it is measuring a fallback');
  }

  // ---- THREE DEPTHS: THE PACKAGE, THE MODULE, THE SYMBOL ----------------
  //
  // The boxes on the picture above are DIRECTORIES, and a directory is not a
  // moving part. *"Just looking at it should communicate everything one needs
  // to know to understand how the project works, and when we work on a TODO,
  // it's obvious what moving parts we'll be affecting."* So a box opens into
  // its files and a file opens into what it defines.
  //
  // AN EXPANSION IS A NEW PICTURE, NOT A BIGGER ONE. Splicing a package's
  // twelve modules into a forty-box diagram is the ugly grid the whole
  // complaint started with. What this guards is that the new picture arrives,
  // that there is a way back out of it, and that a picture found by pattern
  // rather than parsed says so -- because a Lean box nobody may trust as far
  // as a Python one must not look identical to it.
  {
    const w = board(980, 620);
    const doc = w.document;
    w.__render(payload());
    w.__openMap('tapped');
    await sleep(15);
    insideAsks.length = 0;

    const digs = Array.from(doc.querySelectorAll('#map-sheet .dig'))
      .map((g) => g.getAttribute('data-dig'));
    digs.includes('evaluate') && digs.includes('artifacts')
      ? ok('a box with files in it offers to be opened')
      : fail('nothing on the picture says a box has anything under it: '
             + JSON.stringify(digs));
    !digs.includes('doc-deck')
      ? ok('and a document does not, because there is nothing under a document')
      : fail('a document was offered an inside it does not have');

    // The box's own tap means "work in this", and the inside has a control of
    // its own because one target cannot mean both.
    posts.length = 0;
    const box = doc.querySelector('#map-sheet .node[data-id="evaluate"]');
    box.dispatchEvent(new w.Event('click'));
    await sleep(10);
    posts.filter((x) => /\/session$/.test(x.url)).length && !insideAsks.length
      ? ok('and the box itself still opens the sitting, not the level below it')
      : fail('tapping the box went somewhere new; the two taps are one target '
             + 'again');
    w.__openMap('tapped');
    await sleep(15);

    doc.querySelector('#map-sheet .dig[data-dig="evaluate"]')
       .dispatchEvent(new w.Event('click'));
    await sleep(20);
    insideAsks.join('|') === 'evaluate'
      ? ok('looking inside asks the server for that one box, by the id '
           + 'discovery gave it')
      : fail('the inside was not asked for: ' + JSON.stringify(insideAsks));

    let names = Array.from(doc.querySelectorAll('#map-sheet .node .name'))
      .map((n) => n.textContent);
    names.includes('grade.py') && names.includes('score.py')
      ? ok('and the picture becomes the files in it')
      : fail('the files did not replace the picture: ' + JSON.stringify(names));
    names.includes('artifacts')
      ? ok('with an arrow that LEAVES drawn to the sibling it lands in, rolled '
           + 'up to the depth showing')
      : fail('an arrow out of the box went nowhere');
    doc.querySelector('#map-sheet .node.outside')
      ? ok('and that sibling marked as elsewhere rather than as part of what '
           + 'is being read')
      : fail('the wall is drawn as though it were inside the box');
    doc.getElementById('map-loose').hidden === true
      ? ok('and the plan\'s unplaced steps are not shown under a picture they '
           + 'are not about')
      : fail('the tray of loose steps is still under a diagram of one package');

    // THE WAY BACK. A crumb read off the payload rather than remembered from
    // the taps: a trail kept as history is wrong after a sideways step, a
    // reload, or a second tap that landed out of order.
    let crumbs = Array.from(doc.querySelectorAll('#map-crumb .crumb'))
      .map((b) => b.textContent);
    crumbs.join(' › ') === 'PSYCH-ASR › evaluate'
      ? ok('the crumb says where you are, and the repository is the way out')
      : fail('the crumb reads ' + JSON.stringify(crumbs));
    doc.querySelector('#map-crumb .crumb.here').textContent === 'evaluate'
      ? ok('and the last of it is where you are rather than a link to it')
      : fail('the crumb offers a link to the picture already on the glass');

    // ---- and one more depth: the symbols -------------------------------
    doc.querySelector('#map-sheet .dig[data-dig="in-grade-py"]')
       .dispatchEvent(new w.Event('click'));
    await sleep(20);
    names = Array.from(doc.querySelectorAll('#map-sheet .node .name'))
      .map((n) => n.textContent);
    names.join('|') === 'Finding|grade'
      ? ok('a file opens into what it defines, which is the depth the ask was '
           + 'about')
      : fail('the definitions are not the picture: ' + JSON.stringify(names));
    Array.from(doc.querySelectorAll('#map-sheet .node .also'))
      .map((n) => n.textContent).join('|') === 'class|function'
      ? ok('and each one says whether it is a class or a function')
      : fail('a definition does not say which of the two it is');
    doc.querySelectorAll('#map-sheet path.edge').length === 1
      ? ok('and an arrow between two of them is one really using the other')
      : fail('the uses are not drawn');
    crumbs = Array.from(doc.querySelectorAll('#map-crumb .crumb'))
      .map((b) => b.textContent);
    crumbs.join(' › ') === 'PSYCH-ASR › evaluate › grade.py'
      ? ok('and the crumb is three deep, with the box above it a way back')
      : fail('the crumb reads ' + JSON.stringify(crumbs));
    !doc.querySelector('#map-sheet .dig')
      ? ok('a symbol is the leaf: there is nothing under a function to open')
      : fail('a function was offered an inside');

    // A SYMBOL OPENS A WALKTHROUGH OVER THAT SYMBOL, which is the whole payoff
    // of a diagram whose nodes are the things -- and it opens it on the tap,
    // because a walkthrough is the one thing a definition supports and a sheet
    // offering one option is a question with one answer. `map.find` has no box
    // by this id, so the id must NOT be sent: the scope is what says what this
    // is about, and it is spelt the way `walk.label` spells it.
    posts.length = 0;
    doc.querySelector('#map-sheet .node[data-id="at-grade-grade"]')
       .dispatchEvent(new w.Event('click'));
    await sleep(10);
    doc.getElementById('work').hidden && !doc.querySelector('#map-sheet .ways')
      ? ok('and a definition is never asked how: the tap is its one way')
      : fail('a function was offered a sheet');
    const sent = posts.filter((p) => /\/session$/.test(p.url))[0];
    sent && sent.body.session === 'walk' && sent.body.node === null
         && !('aim' in sent.body)
         && JSON.stringify(sent.body.over)
            === JSON.stringify(['psych_asr/evaluate/grade.py::grade'])
      ? ok('over exactly that function, and with no box id, because the server '
           + 'has no box by that name')
      : fail('the walkthrough was asked for as '
             + JSON.stringify(sent && sent.body));

    // ---- back out, and the payload cannot drag you there ---------------
    w.__openMap('tapped');
    await sleep(5);
    w.__mapOut();
    await sleep(10);
    doc.getElementById('map-crumb').hidden === true
    && Array.from(doc.querySelectorAll('#map-sheet .node .name'))
         .map((n) => n.textContent).includes('evaluate')
      ? ok('and the way out puts the repository\'s own picture back')
      : fail('there is no way back to the top');

    // A POLL MUST NOT DRAG SOMEBODY BACK UP. The payload arrives four times a
    // second while a person is two boxes deep, and it is the top-level picture
    // every time.
    doc.querySelector('#map-sheet .dig[data-dig="evaluate"]')
       .dispatchEvent(new w.Event('click'));
    await sleep(20);
    w.__render(payload());
    await sleep(15);
    Array.from(doc.querySelectorAll('#map-sheet .node .name'))
      .map((n) => n.textContent).includes('grade.py')
      ? ok('a payload arriving while somebody is inside a box leaves them there')
      : fail('the poll dragged the picture back to the top');

    // ---- a picture found by pattern says so ----------------------------
    w.__mapOut();
    await sleep(10);
    doc.querySelector('#map-sheet .dig[data-dig="apart"]')
       .dispatchEvent(new w.Event('click'));
    await sleep(20);
    doc.querySelector('#map-sheet .dig[data-dig="in-run-sh"]')
       .dispatchEvent(new w.Event('click'));
    await sleep(20);
    /pattern rather than parsed/.test(doc.getElementById('map-why').textContent)
    && /trust it less/.test(doc.getElementById('map-why').textContent)
      ? ok('a picture a pattern found rather than a parser says so on the '
           + 'picture, because it may not be trusted as far as the one above it')
      : fail('a grepped diagram looks identical to a parsed one: '
             + doc.getElementById('map-why').textContent);
    !doc.querySelectorAll('#map-sheet path.edge').length
      ? ok('and draws no arrows at all, because a pattern is a liar about calls')
      : fail('arrows were drawn from a pattern');

    // ---- an id that is nothing is said, not thrown ----------------------
    w.__mapOut();
    await sleep(10);
    w.__mapDig('nothing-of-the-sort');
    await sleep(20);
    /nothing inside that/.test(doc.getElementById('map-crumb').textContent)
      ? ok('an id that is neither a box nor a module of one is said rather '
           + 'than leaving the tap looking broken')
      : fail('a miss said nothing: '
             + doc.getElementById('map-crumb').textContent);
    Array.from(doc.querySelectorAll('#map-sheet .node .name'))
      .map((n) => n.textContent).includes('evaluate')
      ? ok('and the picture that was there is untouched')
      : fail('a miss took the picture away');
  }

  // ---- one level SIDEWAYS: a vendor tree, drawn on this board -----------
  // `atlas.trees()` is read and drawn and is never handed work, so there is no
  // board to switch to -- the picture goes on the one map surface this page
  // has, and a trace taken off it is a sitting in THIS workspace with the tree
  // named in the scope. What has to hold is that every tap made while it is up
  // knows which repository it is in.
  {
    const w = board(980, 620);
    const doc = w.document;
    w.__render(payload());
    w.__openMap('tapped');
    await sleep(15);
    treeAsks.length = 0;
    insideAsks.length = 0;
    w.__mapTreeOpen('vendor/colibri');
    await sleep(20);
    treeAsks.join('|') === 'vendor/colibri'
      ? ok('a tree is fetched by name, on the tap')
      : fail('the tree was asked for as ' + JSON.stringify(treeAsks));
    Array.from(doc.querySelectorAll('#map-sheet .node .name'))
      .map((n) => n.textContent).sort().join('|') === 'bin|src'
      ? ok('and its boxes are drawn by the renderer this page already has')
      : fail('the tree was not drawn: '
             + Array.from(doc.querySelectorAll('#map-sheet .node .name'))
                 .map((n) => n.textContent).join('|'));
    /pulled and not written/.test(doc.getElementById('map-why').textContent)
      ? ok('with the rule on the picture, where somebody is looking at it')
      : fail('the tree picture did not say whose it is: '
             + doc.getElementById('map-why').textContent);
    const crumb = Array.from(doc.querySelectorAll('#map-crumb .crumb'))
      .map((b) => b.textContent);
    crumb[0] === 'PSYCH-ASR' && crumb[crumb.length - 1] === 'colibri'
      ? ok('and the way out of it is the workspace, which is where a sitting '
           + 'over it would be held')
      : fail('the crumb does not lead back to the workspace: ' + crumb.join('|'));

    // A BOX OF A TREE IS ASKED FOR UNDER THE TREE. The foreign picture carries
    // a box called `evaluate`, and so does this workspace's own map -- asking
    // the local route for it would open a picture of somewhere else entirely
    // and nothing on the glass would say so.
    insideAsks.length = 0;
    treeAsks.length = 0;
    doc.querySelector('#map-sheet .dig[data-dig="bin"]')
       .dispatchEvent(new w.Event('click'));
    await sleep(20);
    !insideAsks.length && treeAsks.join('|') === 'vendor/colibri/inside/bin'
      ? ok('a box of a tree is opened under the tree, never down this '
           + 'workspace\'s own route')
      : fail('a foreign box was looked up locally: '
             + JSON.stringify(insideAsks) + ' / ' + JSON.stringify(treeAsks));
    Array.from(doc.querySelectorAll('#map-sheet .node .name'))
      .map((n) => n.textContent).join('|') === 'coli-up'
      ? ok('and what is in it is drawn the way the inside of a local box is')
      : fail('the inside of a foreign box was not drawn');
    Array.from(doc.querySelectorAll('#map-crumb .crumb')).map((b) => b.textContent)
      .join('|') === 'PSYCH-ASR|colibri|bin'
      ? ok('with the tree still in the crumb, so two steps back is still the '
           + 'workspace')
      : fail('the crumb lost the tree: '
             + Array.from(doc.querySelectorAll('#map-crumb .crumb'))
                 .map((b) => b.textContent).join('|'));

    treeAsks.length = 0;
    w.__mapTreeOpen('vendor/colibri');
    await sleep(20);
    posts.length = 0;
    doc.querySelector('#map-sheet .node[data-id="bin"]')
       .dispatchEvent(new w.Event('click'));
    await sleep(10);
    doc.getElementById('work').hidden && !doc.querySelector('#map-sheet .ways')
      ? ok('and the one thing a tap on it can mean is a trace: nothing is '
           + 'handed in to somebody else\'s repository, so there is nothing '
           + 'else honest to ask')
      : fail('a vendor box was offered a sheet');
    const traced = posts.filter((p) => /\/session$/.test(p.url))[0];
    traced && traced.body.session === 'walk' && traced.body.node === null
           && !('aim' in traced.body)
           && JSON.stringify(traced.body.over)
              === JSON.stringify(['@vendor/colibri/bin/coli-up'])
      ? ok('over the tree and the file together, and with no box id, because '
           + 'this workspace has no box by that name')
      : fail('the trace was asked for as ' + JSON.stringify(traced && traced.body));

    w.__mapOut();
    await sleep(10);
    doc.getElementById('map-crumb').hidden === true
    && Array.from(doc.querySelectorAll('#map-sheet .node .name'))
         .map((n) => n.textContent).includes('evaluate')
      ? ok('and the way out puts this workspace\'s own picture back')
      : fail('there is no way back out of a tree');
  }

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\nthe repository has a picture, and it is the way in');
  process.exit(errors.length ? 1 : 0);
})();
