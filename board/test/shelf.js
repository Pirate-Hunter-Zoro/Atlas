// The way back to a document is the MAP, and the drawer it opens is HTML.
//
// The server's half is `test/shelf.py`. This is the half that decides whether
// somebody can actually reach their own homework on an iPad, and it is driven
// in a real DOM because every defect in this family is one a stub reports as
// fine.
//
//   * THE PANEL THAT USED TO ANSWER THIS LISTED TWO DOCUMENTS. The last lesson
//     exported and the last write-up compiled -- a record of the last thing
//     BUILT, not an inventory. It is gone, and the assertion is that it stays
//     gone: a deletion that can silently come back is a deletion that will.
//   * A BADGE MUST NOT SIT ON A STEP CHIP. Both are taps, on the same row, at
//     opposite ends of a box 226px wide. A box with seven steps reaches the
//     badge, and a chip drawn under it is a step nobody can start. The chips
//     wrap and the box grows; the badge does not move.
//   * A DIAGRAM IS NOT A LIST. The documents are rows in a drawer, never boxes
//     on the plane -- forty PDFs spliced into a forty-box picture is the grid
//     the map was drawn to replace.
//   * THE LIST IS FETCHED ON A TAP. The payload is rebuilt four times a second
//     and carries the COUNT per box. A list on it is the one thing the map's
//     own rule forbids.
//   * READ AND SAVE MUST WORK OVER A DOCUMENT THE BOARD DID NOT BUILD, which
//     is what `shelf/<sid>` as a fourth document KIND buys -- and a kind is
//     never a path.
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

// What the board asked for, and what it posted. The second list is the one
// that says a tap on the badge opened a drawer rather than starting a sitting.
const asks = [];
const posts = [];
// The answer `/shelf.json` gives, swappable so a board can be asked twice.
let answer = null;

// ------------------------------------------------------------------ the shelf
function shelfJson() {
  return {
    ok: true,
    workspace: 'Galois-Theory',
    total: 5,
    groups: [
      { node: 'ch-04', box: 'Ch 04 — Field extensions', docs: [
        { sid: 'ch04-homework', title: 'Chapter 4 homework', kind: 'homework',
          pages: 12, at: 1758553200, iso: '2026-09-22', size: 284133,
          pdf: true, stale: false, theirs: false,
          rel: 'chapters/ch04-field-extensions/build/ch04-homework.pdf' },
        // WRITTEN AND NEVER COMPILED. There is a source on disk and no PDF
        // anywhere, and both of the buttons would fail, so it carries neither.
        { sid: 'ch04-notes', title: 'Chapter 4 notes', kind: 'notes',
          pages: 0, at: 1758553100, iso: '2026-09-22', size: 0,
          pdf: false, stale: false, theirs: false,
          rel: 'chapters/ch04-field-extensions/notes/ch04-notes.tex' },
        { sid: 'garling-ch4', title: 'garling ch4', kind: 'reading',
          pages: 24, at: 1757000000, iso: '2026-09-04', size: 990000,
          pdf: true, stale: false, theirs: true,
          rel: 'chapters/ch04-field-extensions/reading/garling-ch4.pdf' },
      ] },
      { node: 'ch-05', box: 'Ch 05 — Galois groups', docs: [
        { sid: 'ch05-notes', title: 'Chapter 5 notes', kind: 'notes',
          pages: 6, at: 1757600000, iso: '2026-09-11', size: 120000,
          pdf: true, stale: true, theirs: false,
          rel: 'chapters/ch005-galois-groups/build/ch05-notes.pdf' },
      ] },
      // LAST, AND THE SERVER PUT IT THERE. The client draws the array in the
      // order it arrived and moves nothing.
      { node: '', box: 'Unfiled', docs: [
        { sid: 'a-course-in-galois-theory', title: 'a course in galois theory',
          kind: 'textbook', pages: 320, at: 1740000000, iso: '2026-02-19',
          size: 8400000, pdf: true, stale: false, theirs: false,
          rel: 'textbook/A Course in Galois Theory.pdf' },
      ] },
    ],
  };
}

// ------------------------------------------------------------------ the board
function board() {
  const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
    runScripts: 'outside-only', pretendToBeVisual: true,
    url: 'https://board.test/board',
  });
  const { window } = dom;
  // A canvas that MEASURES, because the badge's width is measured text and the
  // question below is whether it collides with a chip. A stub that answers
  // nothing tests the fallback and never the thing.
  window.HTMLCanvasElement.prototype.getContext = function (kind) {
    if (kind !== '2d') return new Proxy({}, { get: () => () => {}, set: () => true });
    const ctx = {
      font: '',
      measureText(s) {
        const size = parseFloat(/(\d+(?:\.\d+)?)px/.exec(ctx.font || '15px')[1]);
        let w = 0;
        for (const ch of String(s)) {
          w += size * (ch === ch.toUpperCase() && ch !== ch.toLowerCase() ? 0.72
                       : ch === ' ' ? 0.28 : 0.52);
        }
        return { width: w };
      },
    };
    return new Proxy(ctx, {
      get: (t, k) => (k in t ? t[k] : () => {}),
      set: (t, k, v) => { t[k] = v; return true; },
    });
  };
  window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
  Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => 980 });
  Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 620 });
  window.HTMLElement.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: 980, height: 620,
             right: 980, bottom: 620, x: 0, y: 0 };
  };
  window.Element.prototype.scrollIntoView = function () {};
  window.Element.prototype.setPointerCapture = function () {};
  window.Element.prototype.releasePointerCapture = function () {};
  window.fetch = (u, opts) => {
    const url = String(u);
    asks.push(url);
    if (opts && opts.body) {
      posts.push({ url: url, body: JSON.parse(opts.body) });
      return Promise.resolve({ json: () => Promise.resolve({ ok: true }) });
    }
    if (/slate\/state/.test(url)) {
      return Promise.resolve({ json: () => Promise.resolve({ pages: [] }) });
    }
    if (/^\/shelf\.json/.test(url)) {
      return Promise.resolve({ json: () => Promise.resolve(answer || shelfJson()) });
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
  // The two handovers are asked of the CODE rather than of the network,
  // because what is being checked is which KIND was named -- a kind is the
  // tail of the route and the thing the client is allowed to send. Both are
  // function declarations, so both can be stood in for from out here.
  src = src.replace('})();',
    'window.__render = render;\n'
    + 'window.__openShelf = openShelf;\n'
    + 'window.__paperIdent = paperIdent;\n'
    + 'window.__paperUrl = paperUrl;\n'
    + 'window.__paperViewUrl = paperViewUrl;\n'
    + 'window.__papers = function () { return papers; };\n'
    + 'window.__standIn = function (name, fn) {\n'
    + '  if (name === "openPaper") openPaper = fn;\n'
    + '  if (name === "saveCopy") saveCopy = fn;\n'
    + '};\n})();');
  try { window.eval(src); }
  catch (e) { fail('board.js: ' + e.message); }
  return window;
}

function node(over) {
  const out = Object.assign({
    id: 'x', name: 'x', also: '', kind: 'chapter', does: '', status: 'unknown',
    files: [], dir: '', steps: [], doc: '', slide: null, note: '', hw: '',
    chapter: '', docs: 0,
  }, over);
  if (out.inside === undefined) out.inside = (out.files || []).length;
  return out;
}

function steps(n) {
  const out = [];
  for (let i = 1; i <= n; i++) {
    out.push({ num: String(i), title: 'STEP ' + i, label: i + '. STEP ' + i,
               summary: 'Do it.', order: i, from: 'Galois-Theory' });
  }
  return out;
}

function payload(over) {
  return Object.assign({
    state: { course: 'Galois-Theory', session: 'lecture', chapter: '' },
    cards: [], turns: [], messages: [], uploads: [], slate: null,
    notes: [], notes_sent: [], text_drafts: {}, unsaved: 0,
    push: null, export: null, papers: {}, agent: null, waiting: 0,
    history: 0, sets: [], contents: { chapters: [], sets: [] },
    review: null, walk: null, plan: null, reading: { documents: [] },
    map: {
      version: 2, title: '', steps: 10, total: 3,
      why: "Drawn from this course's own chapter table.",
      nodes: [
        // THE CROWDED ONE. Seven steps on a box 226px wide, and a badge at the
        // right end of the same row.
        node({ id: 'ch-04', name: 'Ch 04 — Field extensions', kind: 'chapter',
               also: 'Chapter 04', chapter: 'Ch 04 — Field extensions',
               docs: 3, steps: steps(7) }),
        node({ id: 'ch-05', name: 'Ch 05 — Galois groups', kind: 'chapter',
               also: 'Chapter 05', chapter: 'Ch 05 — Galois groups',
               docs: 1, steps: steps(2) }),
        node({ id: 'ch-06', name: 'Ch 06 — Ruler and compass', kind: 'chapter',
               also: 'Chapter 06', chapter: 'Ch 06 — Ruler and compass',
               docs: 0, steps: steps(1) }),
      ],
      edges: [{ from: 'ch-04', to: 'ch-05', weight: 1, label: '' },
              { from: 'ch-05', to: 'ch-06', weight: 1, label: '' }],
      loose: [],
    },
  }, over || {});
}

const plateOf = (doc, id) =>
  doc.querySelector('#map-sheet .node[data-id="' + id + '"] g.docs[data-docs="' + id + '"]');

(async function () {
  // ------------------------------------------------ the deletion stays done
  {
    const html = fs.readFileSync(path.join(WEB, 'board.html'), 'utf8');
    const js = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
    !/id="btn-papers"/.test(html) && !/id="papers"/.test(html)
      ? ok('the two-document panel is gone from board.html')
      : fail('board.html still carries the panel that listed the last two builds');
    !/function openPapers\s*\(/.test(js) && !/function renderPapers\s*\(/.test(js)
      ? ok('and nothing in board.js still draws it')
      : fail('openPapers/renderPapers survive in board.js, so the panel can '
             + 'come back without anybody deciding to bring it back');
  }

  // ------------------------------------------------------ the drawer's shape
  {
    const css = fs.readFileSync(path.join(WEB, 'board.css'), 'utf8')
                  .replace(/\/\*[\s\S]*?\*\//g, '')
                  .replace(/@media[^{]*\{(?:[^{}]*\{[^{}]*\}\s*)*\}/g, '');
    let body = '', m;
    const re = /(^|[},])\s*#shelf-list\s*\{([^}]*)\}/mg;
    while ((m = re.exec(css)) !== null) body += ';' + m[2];
    /flex:\s*1\b/.test(body) && /overflow-y:\s*(auto|scroll)/.test(body)
      ? ok('the drawer\'s list takes the room between head and foot, and scrolls')
      : fail('#shelf-list does not both grow and scroll — its last rows fall '
             + 'off the bottom: ' + JSON.stringify(body));
    const html = fs.readFileSync(path.join(WEB, 'board.html'), 'utf8');
    const aside = /<aside id="shelf"[\s\S]*?<\/aside>/.exec(html);
    aside && /class="to-map"/.test(aside[0])
      ? ok('and it carries a way back to the map, which it was opened from')
      : fail('the documents drawer has no .to-map button');
  }

  // ------------------------------------------------------------- the badge
  const w = board();
  const doc = w.document;
  w.__render(payload());
  await sleep(20);

  {
    !doc.getElementById('map').hidden
      ? ok('the map is on the glass')
      : fail('the map did not open');

    const three = plateOf(doc, 'ch-04');
    const one = plateOf(doc, 'ch-05');
    const none = plateOf(doc, 'ch-06');
    three && /3/.test(three.querySelector('text').textContent)
      ? ok('a box holding three documents carries a badge reading 3')
      : fail('the badge on a box with three documents reads '
             + (three ? three.textContent : 'nothing at all'));
    one ? ok('and a box holding one carries one')
        : fail('a box with a document carries no badge');
    !none
      ? ok('a box holding none carries no badge, which is a plate nobody '
           + 'learns to ignore')
      : fail('a box with no documents drew a badge anyway');
    three && three.getAttribute('role') === 'button'
             && three.getAttribute('tabindex') === '0'
      ? ok('and it is a control rather than a decoration')
      : fail('the badge is not reachable from a keyboard');
  }

  // THE COLLISION. Seven chips and a badge, on a box 226 wide.
  {
    const g = doc.querySelector('#map-sheet .node[data-id="ch-04"]');
    const box = g.querySelector('rect.box');
    const bx = +box.getAttribute('x'), by = +box.getAttribute('y');
    const bw = +box.getAttribute('width'), bh = +box.getAttribute('height');
    const plate = plateOf(doc, 'ch-04').querySelector('rect');
    const pr = { x: +plate.getAttribute('x'), y: +plate.getAttribute('y'),
                 w: +plate.getAttribute('width'), h: +plate.getAttribute('height') };
    const chips = Array.prototype.map.call(
      g.querySelectorAll('g.chip circle'),
      (c) => ({ x: +c.getAttribute('cx') - +c.getAttribute('r'),
                y: +c.getAttribute('cy') - +c.getAttribute('r'),
                w: +c.getAttribute('r') * 2, h: +c.getAttribute('r') * 2 }));
    chips.length === 7
      ? ok('all seven steps are still drawn')
      : fail('the box drew ' + chips.length + ' chips rather than 7');
    const hits = chips.filter((c) => c.x < pr.x + pr.w && c.x + c.w > pr.x
                                     && c.y < pr.y + pr.h && c.y + c.h > pr.y);
    !hits.length
      ? ok('and not one of them is under the badge')
      : fail(hits.length + ' step chips are drawn under the badge, and a step '
             + 'nobody can tap is a step nobody can start');
    const out = chips.filter((c) => c.x < bx || c.x + c.w > bx + bw
                                    || c.y < by || c.y + c.h > by + bh);
    !out.length
      ? ok('and every one of them is inside the box that owns it')
      : fail(out.length + ' chips escaped the box');

    const small = doc.querySelector('#map-sheet .node[data-id="ch-06"] rect.box');
    bh > +small.getAttribute('height')
      ? ok('the box grew to hold the row they wrapped onto (' + bh + ' against '
           + small.getAttribute('height') + ')')
      : fail('the chips wrapped and the box did not grow, so they are drawn '
             + 'outside it');
  }

  // ----------------------------------------------------------- the map bar
  {
    const bar = doc.getElementById('map-docs');
    !bar.hidden && /4/.test(bar.textContent)
      ? ok('the map bar says how many the boxes hold (' + bar.textContent + ')')
      : fail('the map bar control reads "' + bar.textContent + '", hidden='
             + bar.hidden);
  }

  // ------------------------------------------- a tap on the badge, scoped
  {
    const before = asks.length, posted = posts.length;
    plateOf(doc, 'ch-04').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    const shelf = doc.getElementById('shelf');
    !shelf.hidden
      ? ok('a tap on the badge opens the drawer')
      : fail('the badge does nothing');
    posts.length === posted
      ? ok('and starts no sitting: the box is one tap and the badge is another')
      : fail('tapping the badge posted ' + JSON.stringify(posts.slice(posted)));
    const wanted = asks.slice(before).filter((u) => /^\/shelf\.json/.test(u));
    wanted.length === 1
      ? ok('and asks the server once, because the list is not on the payload')
      : fail('the drawer asked ' + wanted.length + ' times for /shelf.json');

    await sleep(20);
    doc.getElementById('shelf-title').textContent === 'Ch 04 — Field extensions'
      ? ok('the drawer is headed with the box it was opened from')
      : fail('the drawer says "' + doc.getElementById('shelf-title').textContent
             + '" rather than the name of the box');
    const rows = doc.querySelectorAll('#shelf-list .shelf-row');
    const heads = doc.querySelectorAll('#shelf-list .group');
    rows.length === 3 && heads.length === 1
      ? ok('and draws that box\'s three documents and nothing else')
      : fail('the drawer drew ' + rows.length + ' rows under ' + heads.length
             + ' headings, rather than 3 under 1');
    // A DIAGRAM IS NOT A LIST. The documents are rows in HTML; not one of them
    // became a box on the plane.
    doc.querySelectorAll('#map-sheet .node').length === 3
      ? ok('and not one document became a box on the map')
      : fail('the map now draws '
             + doc.querySelectorAll('#map-sheet .node').length + ' boxes');

    // The one with no PDF: greyed, and neither button, because both would fail.
    const unbuilt = doc.querySelector('#shelf-list .shelf-row.unbuilt');
    unbuilt && !unbuilt.querySelector('button')
      ? ok('a document with no compiled PDF offers neither read nor save')
      : fail('the unbuilt row offers '
             + (unbuilt ? unbuilt.querySelectorAll('button').length : 'no row at all'));
    const flags = Array.prototype.map.call(
      doc.querySelectorAll('#shelf-list .flag'), (f) => f.textContent);
    flags.indexOf('theirs') !== -1
      ? ok('and a sheet somebody else wrote says so')
      : fail('nothing marks the material this course did not write: '
             + JSON.stringify(flags));
  }

  // ------------------------------------------------- read it, and save it
  {
    const opened = [], saved = [];
    w.__standIn('openPaper', (kind, label) => opened.push([kind, label]));
    w.__standIn('saveCopy', (kind) => saved.push(kind));
    const row = doc.querySelectorAll('#shelf-list .shelf-row')[0];
    const acts = Array.prototype.map.call(row.querySelectorAll('.shelf-acts button'),
                                          (b) => b.textContent);
    acts.join('|') === 'read it here|save a copy'
      ? ok('a built document offers both ways to have it')
      : fail('the row offers ' + JSON.stringify(acts));
    row.querySelectorAll('.shelf-acts button')[0].onclick
      ? row.querySelectorAll('.shelf-acts button')[0].onclick()
      : row.querySelectorAll('.shelf-acts button')[0]
           .dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    opened.length === 1 && opened[0][0] === 'shelf/ch04-homework'
      ? ok('"read it here" names the KIND shelf/ch04-homework, never a path')
      : fail('read handed over ' + JSON.stringify(opened));
    doc.getElementById('shelf').hidden
      ? ok('and the drawer gets out of the way of the pages')
      : fail('the drawer stayed open under the document');

    // The drawer has to be back up for the second button.
    w.__openShelf('ch-04');
    await sleep(20);
    const row2 = doc.querySelectorAll('#shelf-list .shelf-row')[0];
    row2.querySelectorAll('.shelf-acts button')[1]
        .dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    saved.length === 1 && saved[0] === 'shelf/ch04-homework'
      ? ok('and "save a copy" names the same kind')
      : fail('save handed over ' + JSON.stringify(saved));
    // WHAT MAKES READ AND SAVE WORK AT ALL: the record goes into `papers`
    // under its own kind, which is the table every one of those asks.
    const have = w.__papers()['shelf/ch04-homework'];
    have && have.at === 1758553200
      ? ok('the document is in `papers` under that kind, with the PDF\'s own '
           + 'mtime, so a rebuild invalidates the warm copy')
      : fail('nothing put the document where warmPaper and saveCopy look: '
             + JSON.stringify(have));
    w.__paperViewUrl('shelf/ch04-homework') === '/view/shelf/ch04-homework'
      && w.__paperUrl('shelf/ch04-homework') === '/download/shelf/ch04-homework'
      ? ok('and the kind is the tail of both routes, so there is no fifth '
           + 'place that glues a URL together')
      : fail('the shelf kind does not address the routes it was named for');
    // THE INK ANCHOR IS NOT THE CACHE TAG. `/view/shelf/<sid>` answers with
    // `kind: "shelf"` so the render cache does not collide with `/view/doc`'s
    // -- but a mark is anchored on `doc/<sid>/p<n>`, which `writing.ANN_DOC`
    // is the only pattern that accepts. One PDF found two ways is one set of
    // marks.
    w.__paperIdent('shelf/ch04-homework') === 'ch04-homework'
      && w.__paperIdent('doc/ch04-homework') === 'ch04-homework'
      ? ok('and ink anchors under doc/<sid>, however the document was reached')
      : fail('a document read from the drawer anchors its marks at '
             + w.__paperIdent('shelf/ch04-homework')
             + ', which writing.ANN_DOC refuses');
  }

  // ---------------------------------------------------- the whole workspace
  {
    doc.getElementById('map-docs')
       .dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    await sleep(20);
    const shelf = doc.getElementById('shelf');
    !shelf.hidden && /Every document/.test(doc.getElementById('shelf-title').textContent)
      ? ok('the map bar opens the whole shelf, unscoped')
      : fail('the bar control heads the drawer "'
             + doc.getElementById('shelf-title').textContent + '"');
    const heads = Array.prototype.map.call(
      doc.querySelectorAll('#shelf-list .group'), (h) => h.textContent);
    heads.join(' | ') === 'Ch 04 — Field extensions | Ch 05 — Galois groups | Unfiled'
      ? ok('grouped in the order the server sent, with Unfiled where it put it')
      : fail('the groups came out ' + JSON.stringify(heads));
    doc.querySelectorAll('#shelf-list .shelf-row').length === 5
      ? ok('and every document in the workspace is in it (5)')
      : fail('the whole shelf drew '
             + doc.querySelectorAll('#shelf-list .shelf-row').length + ' rows');
    const stale = doc.querySelector('#shelf-list .flag.stale');
    stale ? ok('a PDF older than its source says so, before either button')
          : fail('nothing marks a document whose source has moved on');
    doc.getElementById('btn-shelf-close')
       .dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    shelf.hidden ? ok('and the drawer closes')
                 : fail('the documents drawer cannot be closed');
  }

  console.log('');
  if (errors.length) {
    console.log(errors.length + ' failed');
    process.exit(1);
  }
  console.log('a document is reachable from the box its source lives in');
})();
