// The map, on the glass: a picture of the repository, and the way back to it.
//
// The server's half is `test/map.py`. This is the half that decides whether any
// of it is any good on an iPad, and it is driven in a real DOM because every
// defect in this family is one a stub reports as fine:
//
//   * a box is an <svg> group with a status CLASS on it, and the whole visual
//     language lives in board.css -- so a status that arrives as a word and is
//     never turned into a class paints forty identical grey boxes and nothing
//     says anything is wrong;
//   * the plane is a CSS transform on one wrapper, and a pan that regenerates
//     the picture instead is a map that stutters under a thumb;
//   * a course opens where it was left, out of localStorage, which can throw,
//     come back empty, or come back half-written -- and the fallback for every
//     one of those is the map, not a stranded board.
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

function board(url) {
  const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
    runScripts: 'outside-only', pretendToBeVisual: true,
    url: url || 'https://board.test/board',
  });
  const { window } = dom;
  window.HTMLCanvasElement.prototype.getContext = () =>
    new Proxy({}, { get: () => () => {}, set: () => true });
  window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
  // A plane wide enough for lanes to be columns. The narrow case gets its own
  // board further down.
  Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => 900 });
  Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 600 });
  window.HTMLElement.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: 900, height: 600, right: 900, bottom: 600, x: 0, y: 0 };
  };
  window.Element.prototype.scrollIntoView = function () {};
  window.Element.prototype.setPointerCapture = function () {};
  window.Element.prototype.releasePointerCapture = function () {};
  window.fetch = (u) => (/slate\/state/.test(String(u))
    ? Promise.resolve({ json: () => Promise.resolve({ pages: [] }) })
    : new Promise(() => {}));
  window.renderMathInElement = () => {};
  window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  window.scrollTo = () => {};
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
  for (const f of ['typeface.js', 'macros.js', 'plane-core.js', 'slate-core.js',
                   'annotate.js', 'shot.js']) {
    try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
    catch (e) { fail(f + ': ' + e.message); }
  }
  let src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
  src = src.replace('})();',
    'window.__render = render;\nwindow.__openMap = openMap;\n'
    + 'window.__closeMap = closeMap;\nwindow.__mapView = function () { return mapView; };\n'
    + 'window.__mapTap = mapTap;\n})();');
  try { window.eval(src); }
  catch (e) { fail('board.js: ' + e.message); }
  return window;
}

const now = Date.now() / 1000;

// A project's map: two lanes, five boxes, one edge, and a box in every state
// the board can actually know something about.
const MAP = {
  version: 1,
  title: 'What this project says comes next',
  lanes: ['stage 1', 'evaluation'],
  fallback: true,
  why: 'Drawn from PSYCH-ASR_TODO.txt.',
  total: 5,
  nodes: [
    { id: 'typist', name: 'the typist', also: 'faster-whisper large-v3',
      lane: 'stage 1', does: 'Turns the waveform into words. One candidate, never compared.',
      status: 'working', files: ['psych_asr/cli/run_asr.py'], step: '1',
      doc: '', slide: null, note: '' },
    { id: 'stopwatch', name: 'the stopwatch', also: '', lane: 'stage 1',
      does: 'Re-aligns the corrected words to the waveform.',
      status: 'next', files: [], step: '2', doc: '', slide: null, note: '' },
    { id: 'grid', name: 'the grid, which is a cube', also: 'Step 3',
      lane: 'stage 1', does: '', status: 'later', files: [], step: '3',
      doc: '', slide: null, note: '' },
    { id: 'scorer', name: 'the scorer', also: '', lane: 'evaluation',
      does: 'Grades a candidate against the corrected reference.',
      status: 'done', files: ['psych_asr/evaluate/grade.py', 'psych_asr/evaluate/io.py'],
      step: '', doc: '', slide: null, note: '' },
    { id: 'seam', name: 'the seam', also: '', lane: 'evaluation', does: '',
      status: 'blocked', files: [], step: '', doc: '', slide: null, note: '' },
  ],
  edges: [
    { from: 'typist', to: 'stopwatch', label: 'words' },
    { from: 'stopwatch', to: 'scorer', label: '' },
    // An edge to a box that is not on this map. It must be dropped rather than
    // drawn to nowhere: an arrow is read as a dependency.
    { from: 'typist', to: 'nothing-of-the-sort', label: '' },
  ],
};

function payload(over) {
  return Object.assign({
    state: { course: 'PSYCH-ASR', session: 'lecture', chapter: '' },
    cards: [], turns: [], messages: [], uploads: [], slate: null,
    notes: [], notes_sent: [], text_drafts: {}, unsaved: 0,
    push: null, export: null, papers: {}, agent: null, waiting: 0,
    history: 0, sets: [], contents: { chapters: [], sets: [] },
    review: null, walk: null, plan: null,
    reading: { documents: [{ id: 'stage2-deck', name: 'Stage 2 walkthrough' }] },
    map: JSON.parse(JSON.stringify(MAP)),
  }, over || {});
}

(async function () {
  // ---------------------------------------------- the picture, on the plane
  {
    const w = board();
    const doc = w.document;
    w.__render(payload());
    await sleep(10);

    const map = doc.getElementById('map');
    !map.hidden
      ? ok('a course nobody has opened on this device opens on the map')
      : fail('the default landing is not the map');

    const svg = doc.querySelector('#map-sheet svg');
    svg ? ok('the map is inline SVG the page owns')
        : fail('nothing was drawn into the plane');

    // No <foreignObject>: Safari renders it inconsistently, so the labels are
    // wrapped by hand and are real text.
    !doc.querySelector('#map-sheet foreignObject')
      ? ok('and no <foreignObject>, which Safari renders inconsistently')
      : fail('a label is in a <foreignObject>; it will render differently on the iPad');

    const boxes = doc.querySelectorAll('#map-sheet .node');
    boxes.length === 5
      ? ok('every part of the repository is a box (5)')
      : fail('the map drew ' + boxes.length + ' boxes, not 5');

    // The whole visual language is in board.css and the status is a class. A
    // status that arrives as a word and never becomes a class paints five
    // identical boxes with nothing saying anything is wrong.
    const had = {};
    boxes.forEach((b) => { had[b.getAttribute('data-id')] = b.getAttribute('class'); });
    /\bworking\b/.test(had.typist || '') && /\bdone\b/.test(had.scorer || '')
      && /\bblocked\b/.test(had.seam || '') && /\blater\b/.test(had.grid || '')
      ? ok('and its status is a class on the box, not a word drawn into it')
      : fail('status did not become a class: ' + JSON.stringify(had));

    const names = [];
    boxes.forEach((b) => {
      const t = b.querySelector('text.name');
      if (t) names.push(t.textContent);
    });
    names.indexOf('the typist') >= 0
      ? ok('a box is named in plain English, the way the repository names it')
      : fail('the plain name is not on the box: ' + JSON.stringify(names));

    const also = doc.querySelector('#map-sheet .node[data-id="typist"] text.also');
    also && also.textContent === 'faster-whisper large-v3'
      ? ok('and the real identifier rides underneath it')
      : fail('the identifier under the plain name is missing');

    // An arrow to a box that is not on the map is an arrow somebody will read a
    // dependency out of.
    const edges = doc.querySelectorAll('#map-sheet path.edge');
    edges.length === 2
      ? ok('an edge naming a box that is not here is dropped, not drawn to nowhere')
      : fail('drew ' + edges.length + ' edges; one of the three names nothing');

    const lanes = [];
    doc.querySelectorAll('#map-sheet text.lane').forEach((t) => lanes.push(t.textContent));
    JSON.stringify(lanes) === JSON.stringify(['stage 1', 'evaluation'])
      ? ok('the lanes are headed, in the order the map gives them')
      : fail('lanes came out as ' + JSON.stringify(lanes));

    // Lanes are columns when there is room. Two boxes in one lane share an x;
    // two lanes do not.
    const at = (id) => {
      const r = doc.querySelector('#map-sheet .node[data-id="' + id + '"] rect.box');
      return { x: +r.getAttribute('x'), y: +r.getAttribute('y') };
    };
    at('typist').x === at('stopwatch').x && at('scorer').x > at('typist').x
      ? ok('a lane is a column, and the next lane is the next column')
      : fail('the lanes did not lay out as columns');
    at('stopwatch').y > at('typist').y
      ? ok('and order within a lane is the order the nodes arrive in')
      : fail('the boxes in a lane are not in the file\'s order');

    // The same map, laid out again, must land in the same place. A layout that
    // settles differently on each open is the opposite of a map you learn.
    const was = at('grid');
    w.__render(payload({ state: { course: 'PSYCH-ASR', session: 'lecture', chapter: 'x' } }));
    await sleep(10);
    const again = at('grid');
    was.x === again.x && was.y === again.y
      ? ok('and the same map lays out identically every time')
      : fail('the layout moved between two paints of the same map');

    // --------------------------------------------- panning and pinching
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

    // A lift is caught at the window, because a finger that leaves past the
    // edge never delivers one to the plane -- and a phantom contact turns one
    // finger into a pinch.
    touch('pointerup', 1, 200, 300);
    touch('pointerup', 2, 700, 300);
    const k1 = w.__mapView().k;
    touch('pointerdown', 3, 400, 300);
    touch('pointermove', 3, 500, 300);
    await sleep(5);
    Math.abs(w.__mapView().k - k1) < 1e-9
      ? ok('and one finger after a pinch pans rather than zooming')
      : fail('a lifted finger is still in the map: one finger is zooming');

    // ------------------------------------------------------- tapping a box
    const say = doc.getElementById('map-say');
    w.__mapTap('scorer');
    /scorer/.test(say.textContent) && /done/.test(say.textContent)
      ? ok('a tap says what the box is and what state it is in')
      : fail('a tap said: ' + say.textContent);
    /2 files/.test(say.textContent)
      ? ok('and what it is made of')
      : fail('the files behind the box are not named: ' + say.textContent);
    /\bhere\b/.test(doc.querySelector('#map-sheet .node[data-id="scorer"]')
                       .getAttribute('class'))
      ? ok('and the box is marked as where you are')
      : fail('nothing marks the box that was tapped');

    // ------------------------------------------- the quiet note, said once
    const why = doc.getElementById('map-why');
    /Drawn from PSYCH-ASR_TODO\.txt/.test(why.textContent)
      && /draw a real one/.test(why.textContent)
      ? ok('a derived map says so, quietly, and says a real one can be drawn')
      : fail('a fallback map does not say it is one: ' + why.textContent);

    w.close();
  }

  // ------------------------------------------------ a course opens where it was left
  {
    // The board above was left on the map, panned and pinched, with `scorer`
    // tapped. A second board on the same device must land there.
    const w = board();
    const doc = w.document;
    w.__render(payload());
    await sleep(10);
    !doc.getElementById('map').hidden
      ? ok('a course left on the map reopens on the map')
      : fail('the remembered surface was not honoured');
    const v = w.__mapView();
    const kept = JSON.parse(store['board.where.PSYCH-ASR'] || '{}');
    Math.abs(v.ox - kept.x) < 1e-6 && Math.abs(v.k - kept.k) < 1e-9
      ? ok('at the part of the map it was left at, and the same magnification')
      : fail('the plane did not come back where it was');
    kept.node === 'scorer'
      ? ok('with the box last tapped still marked as where you are')
      : fail('the box last tapped was not remembered: ' + kept.node);

    // And leaving it is remembered too: somebody who closed the map to work is
    // not sent back through it next time.
    w.__closeMap();
    JSON.parse(store['board.where.PSYCH-ASR'] || '{}').surface === 'lesson'
      ? ok('closing the map remembers that the lesson is where they went')
      : fail('leaving the map was not recorded');
    w.close();
  }

  {
    const w = board();
    const doc = w.document;
    w.__render(payload());
    await sleep(10);
    doc.getElementById('map').hidden
      ? ok('and a course left in a lesson reopens in the lesson, not through the map')
      : fail('a lesson in progress was made to go through the map to get back to it');
    w.close();
  }

  // ------------------------------------------------ when the store will not answer
  {
    storeThrows = true;
    const w = board();
    const doc = w.document;
    let threw = null;
    w.addEventListener('error', (e) => { threw = e.message; });
    w.__render(payload());
    await sleep(10);
    !threw ? ok('a browser that refuses site data does not break the board')
           : fail('localStorage throwing reached the page: ' + threw);
    !doc.getElementById('map').hidden
      ? ok('and with nothing remembered, the course opens on the map')
      : fail('a refused store left the board on no surface at all');
    w.close();
    storeThrows = false;
  }

  // A record half-written, or written by something else entirely. The plane
  // must not end up somewhere it cannot be panned back from.
  {
    store['board.where.PSYCH-ASR'] = JSON.stringify({
      surface: 'map', at: Date.now(), x: 'over there', y: null, k: 0, node: 'typist' });
    const w = board();
    const v = w.__mapView.bind(w);
    w.__render(payload());
    await sleep(10);
    const view = v();
    typeof view.k === 'number' && view.k > 0
      ? ok('a half-written record is ignored rather than obeyed')
      : fail('the plane took a scale of ' + view.k + ' out of a bad record');
    w.close();
  }

  // Something absurdly old is history rather than an instruction.
  {
    store['board.where.PSYCH-ASR'] = JSON.stringify({
      surface: 'lesson', at: Date.now() - 400 * 24 * 3600 * 1000 });
    const w = board();
    w.__render(payload());
    await sleep(10);
    !w.document.getElementById('map').hidden
      ? ok('a record from last year is ignored, and the map is the default')
      : fail('a year-old record was obeyed');
    w.close();
    delete store['board.where.PSYCH-ASR'];
  }

  // ------------------------------------------------ a repository with nothing in it
  {
    const w = board();
    const doc = w.document;
    w.__render(payload({ map: null }));
    await sleep(10);
    doc.getElementById('map').hidden
      ? ok('a repository with nothing to draw is never sent to an empty plane')
      : fail('the map opened with nothing on it');
    const opened = w.__openMap();
    opened === false && doc.getElementById('map').hidden
      ? ok('and asking for it says no rather than showing a blank screen')
      : fail('the map opened anyway when there was nothing to draw');
    doc.getElementById('btn-map').hidden
      ? fail('the way to the map was taken away — a guarantee with a condition '
             + 'on it is not a guarantee')
      : ok('the way to the map is still there, and says there is nothing behind it');
    w.close();
  }

  // ------------------------------------------------------------ phone width
  {
    const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
      runScripts: 'outside-only', pretendToBeVisual: true, url: 'https://board.test/board',
    });
    const w = dom.window;
    w.HTMLCanvasElement.prototype.getContext = () =>
      new Proxy({}, { get: () => () => {}, set: () => true });
    w.HTMLCanvasElement.prototype.toDataURL = () => '';
    Object.defineProperty(w.HTMLElement.prototype, 'clientWidth', { get: () => 390 });
    Object.defineProperty(w.HTMLElement.prototype, 'clientHeight', { get: () => 700 });
    w.HTMLElement.prototype.getBoundingClientRect = () =>
      ({ left: 0, top: 0, width: 390, height: 700, right: 390, bottom: 700, x: 0, y: 0 });
    w.Element.prototype.scrollIntoView = function () {};
    w.Element.prototype.setPointerCapture = function () {};
    w.fetch = () => new Promise(() => {});
    w.renderMathInElement = () => {};
    w.requestAnimationFrame = (fn) => setTimeout(fn, 0);
    w.scrollTo = () => {};
    w.EventSource = function () {
      this.readyState = 1; this.close = function () {}; this.addEventListener = function () {};
    };
    Object.defineProperty(w, 'localStorage', {
      configurable: true, value: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
    });
    for (const f of ['typeface.js', 'macros.js', 'plane-core.js', 'slate-core.js',
                     'annotate.js', 'shot.js']) {
      try { w.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
      catch (e) { fail('phone ' + f + ': ' + e.message); }
    }
    let src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
    src = src.replace('})();', 'window.__render = render;\nwindow.__mapView = function () { return mapView; };\n})();');
    try { w.eval(src); } catch (e) { fail('phone board.js: ' + e.message); }
    w.__render(payload());
    await sleep(10);
    const at = (id) => {
      const r = w.document.querySelector('#map-sheet .node[data-id="' + id + '"] rect.box');
      return r ? { x: +r.getAttribute('x'), y: +r.getAttribute('y') } : null;
    };
    const a = at('typist'), b = at('scorer');
    a && b && a.x === b.x && b.y > a.y
      ? ok('at phone width the lanes become rows: a pipeline read downward')
      : fail('two lanes are still two columns on a 390px screen');
    const sheet = w.document.getElementById('map-sheet');
    parseFloat(sheet.style.width) <= 390 + 1
      ? ok('and the picture is no wider than the glass')
      : fail('the map is ' + sheet.style.width + ' wide on a 390px screen');
    w.close();
  }

  // ----------------------------------------------- the map is not the drawer
  {
    const html = fs.readFileSync(path.join(WEB, 'board.html'), 'utf8');
    const right = /<div class="bar-right">([\s\S]*?)<\/div>/.exec(html);
    const controls = right ? (right[1].match(/<(?:button|a|label)\b/g) || []).length : 99;
    controls <= 6
      ? ok('the title bar still carries only what a lesson uses (' + controls + ')')
      : fail('the bar is crowded again: ' + controls + ' controls');
    /id="btn-map"[\s\S]*?class="to-map"|class="to-map"[\s\S]*?id="btn-map"/.test(right ? right[1] : '')
      ? ok('and the way to the map is one of them')
      : fail('the map has no control in the title bar');
    /id="barmenu"[\s\S]*id="btn-contents"/.test(html)
      ? ok('the contents drawer kept every entry and moved one tap away')
      : fail('the contents drawer was removed rather than moved');
  }

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\nthe repository has a picture, and it is the way in');
  process.exit(errors.length ? 1 : 0);
})();
