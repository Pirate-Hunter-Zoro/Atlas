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
    if (opts && opts.body) {
      posts.push({ url: String(u), body: JSON.parse(opts.body) });
      return Promise.resolve({ json: () => Promise.resolve({ ok: true }) });
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
    + 'window.__width = mapWidth;\n})();');
  try { window.eval(src); }
  catch (e) { fail('board.js: ' + e.message); }
  return window;
}

function node(over) {
  return Object.assign({
    id: 'x', name: 'x', also: '', kind: 'part', does: '', status: 'unknown',
    files: [], dir: '', steps: [], doc: '', slide: null, note: '',
  }, over);
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
    boxes.length === 5
      ? ok('every part of the repository is a box (5)')
      : fail('the map drew ' + boxes.length + ' boxes, not 5');

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

  // ------------------------------------------------------ the ways to work
  {
    const w = board();
    const doc = w.document;
    w.__render(payload());
    await sleep(15);

    doc.querySelector('#map-sheet .node[data-id="evaluate"]')
      .dispatchEvent(new w.Event('click', { bubbles: true }));
    await sleep(5);
    const sheet = doc.getElementById('work');
    !sheet.hidden ? ok('tapping a box asks what you want to do about it')
                  : fail('a tap on a box opened nothing');
    doc.getElementById('work-title').textContent === 'evaluate'
      ? ok('and the sheet is about the box that was tapped')
      : fail('the sheet named ' + doc.getElementById('work-title').textContent);

    const ways = [];
    doc.querySelectorAll('#work-list .work-way').forEach((b) =>
      ways.push(b.querySelector('strong').textContent));
    const wanted = ['Teach me how this works', 'Write the code for me',
                    'Tell me what to write, I\'ll code it', 'Walk me through the code',
                    'Set me problems on it', 'Write it up as a paper',
                    'Build me a deck about it'];
    wanted.every((x) => ways.indexOf(x) >= 0)
      ? ok('every way of working on it is offered: ' + ways.length)
      : fail('missing a way to work: ' + JSON.stringify(ways));
    ways.indexOf('Show me the document') < 0
      ? ok('and nothing is offered that this box cannot support')
      : fail('offered to show a document for a box that has none');

    // Only what it can support: a box with no files has no walkthrough, and the
    // document box has a document.
    doc.querySelector('#map-sheet .node[data-id="doc-deck"]')
      .dispatchEvent(new w.Event('click', { bubbles: true }));
    await sleep(5);
    const docWays = [];
    doc.querySelectorAll('#work-list .work-way').forEach((b) =>
      docWays.push(b.querySelector('strong').textContent));
    docWays.indexOf('Show me the document') >= 0
      && docWays.indexOf('Walk me through the code') < 0
      ? ok('a document offers to be shown, and not to be traced as code')
      : fail('the document sheet offered: ' + JSON.stringify(docWays));

    // Each option posts the sitting it says it does. The box's id and the
    // step's label go over the wire; the server looks both up.
    const pick = async (id, step, label) => {
      posts.length = 0;
      w.__openWork(id, step || '');
      await sleep(5);
      let hit = null;
      doc.querySelectorAll('#work-list .work-way').forEach((b) => {
        if (b.querySelector('strong').textContent === label) hit = b;
      });
      if (!hit) return null;
      hit.dispatchEvent(new w.Event('click', { bubbles: true }));
      await sleep(10);
      return posts[0] || null;
    };

    let p = await pick('evaluate', '', 'Write the code for me');
    p && p.body.session === 'lecture' && p.body.stance === 'do'
      && p.body.aim === 'build' && p.body.node === 'evaluate'
      ? ok('“write the code for me” opens a lecture the tutor writes in')
      : fail('wrong body: ' + JSON.stringify(p && p.body));
    // THE TAP IS THE INSTRUCTION. Landing on the lesson behind the map and
    // having to find a second button saying "ask the tutor to begin" is the
    // ceremony this replaces, and it was found as a question rather than as a
    // complaint: "do I ask the tutor to begin?"
    p && p.body.begin === true
      ? ok('and asks the tutor to start, without a second tap')
      : fail('the sitting opens but nothing starts it');

    p = await pick('evaluate', '', 'Tell me what to write, I\'ll code it');
    p && p.body.stance === 'teach' && p.body.aim === 'coach'
      ? ok('“tell me what to write” is the same sitting with a different job')
      : fail('wrong body: ' + JSON.stringify(p && p.body));

    p = await pick('evaluate', '', 'Walk me through the code');
    p && p.body.session === 'walk'
      && p.body.over.join(',') === 'psych_asr/evaluate/grade.py,psych_asr/evaluate/score.py'
      ? ok('“walk me through it” opens a walkthrough over that box\'s own files')
      : fail('wrong body: ' + JSON.stringify(p && p.body));

    p = await pick('evaluate', '', 'Set me problems on it');
    p && p.body.session === 'review' && p.body.aim === 'drill'
      ? ok('“set me problems” opens a review scoped to that part')
      : fail('wrong body: ' + JSON.stringify(p && p.body));

    p = await pick('evaluate', '', 'Write it up as a paper');
    p && p.body.session === 'make' && p.body.makes === 'paper'
      ? ok('“write it up” opens a sitting whose product is a document')
      : fail('wrong body: ' + JSON.stringify(p && p.body));

    p = await pick('evaluate', '', 'Build me a deck about it');
    p && p.body.session === 'make' && p.body.makes === 'slides'
      ? ok('and “build me a deck” asks for slides instead')
      : fail('wrong body: ' + JSON.stringify(p && p.body));

    // A CHIP IS A SITTING. Tapping one carries the step as well as the box, so
    // the tutor is told which piece of work it is, not merely which part.
    posts.length = 0;
    doc.querySelector('#map-sheet .chip[data-step="2. THE STOPWATCH"]')
      .dispatchEvent(new w.Event('click', { bubbles: true }));
    await sleep(5);
    const title = doc.getElementById('work-title').textContent;
    title === 'THE STOPWATCH'
      ? ok('tapping a numbered step asks the same question about that step')
      : fail('the chip sheet is headed ' + JSON.stringify(title));
    p = await pick('evaluate', '2. THE STOPWATCH', 'Teach me how this works');
    p && p.body.step === '2. THE STOPWATCH' && p.body.node === 'evaluate'
      ? ok('and opens a sitting carrying both the step and the part it is on')
      : fail('wrong body: ' + JSON.stringify(p && p.body));

    // A step in the tray has no box, and still opens.
    posts.length = 0;
    doc.querySelector('#map-loose .loose-chip')
      .dispatchEvent(new w.Event('click', { bubbles: true }));
    await sleep(5);
    p = await pick('', '9. BUY A BIGGER DESK', 'Teach me how this works');
    p && p.body.step === '9. BUY A BIGGER DESK' && !p.body.node
      ? ok('a step nothing could place still opens a sitting of its own')
      : fail('wrong body: ' + JSON.stringify(p && p.body));

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
    doc.querySelector('#map-sheet .node[data-id="artifacts"]')
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
    doc.querySelectorAll('#map-sheet .node').length === 5
      ? ok('and the map is still the same map, redrawn rather than rebuilt from a payload')
      : fail('the redraw lost the picture');
    before > 0
      ? ok('and it had been drawn before the face landed, so nothing waited on the font')
      : fail('the map did not draw at all until the font loaded');
    w.Gauge.faceReady()
      ? ok('and the gauge knows its answers are now in the right face')
      : fail('the gauge still believes it is measuring a fallback');
  }

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\nthe repository has a picture, and it is the way in');
  process.exit(errors.length ? 1 : 0);
})();
