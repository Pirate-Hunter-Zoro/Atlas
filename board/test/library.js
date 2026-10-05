// The library page: every document a workspace has written, on one surface.
//
// Driven in a real DOM, because everything worth checking here is what the page
// actually SENDS and DRAWS:
//
//   * AN ID, NEVER A PATH. The server holds the only mapping from one to the
//     other, and a page that sends `docs/x.pdf` is a page that has invited a
//     name from a browser onto a filesystem.
//   * IT MUST NOT TOUCH THE LESSON. No `/say`, no `/session`, nothing that
//     writes a card -- somebody mid-proof on an iPad is not interrupted by
//     somebody correcting a deck, and that is the whole reason this is a page
//     rather than a panel over the board.
//   * A DOCUMENT WITH NO PDF CANNOT BE READ, and saying so on the button beats
//     a viewer that opens empty.
//   * INK IS A COMPLAINT. A document somebody has drawn on can be sent back with
//     nothing typed, because asking them to write out the ring they drew round a
//     figure is the translation this surface exists to remove.
//   * AND THE INK IS MADE HERE. A page carries `data-ann="doc/<id>/p<n>"` and
//     `annotate.js` takes it, so the ring is drawn on the document being read
//     rather than on the board's viewer and then written about on a third
//     surface. `send` is never set from this page: ink on a document is a
//     complaint about the document, and it becomes a turn when the note goes.
//   * NOTHING THE READER IS WAITING ON IS SILENT. The revision goes out in the
//     same request that files the note, and the only thing that used to change
//     afterwards was a line saying the note was filed. So the page polls a
//     STAMP, says the turn is running, and re-draws the open document when its
//     bytes move -- WITHOUT throwing a 33-page deck back to page 1, and without
//     reaching for the hub's stream, which carries the LESSON's payload.
//   * TWO ASKS, FROM ONE PANEL. A correction keeps the document's structure and
//     its claims; an overhaul may restructure, cut and rewrite, and costs a
//     sentence saying what the document is for now. The send is dead until that
//     sentence exists, because the refusal underneath it is the server's and a
//     button that sends and then apologises is worse than one that waits.

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

const LIBRARY = {
  workspace: 'research/PSYCH-ASR',
  writeups: 'writeups',
  documents: [
    {
      id: 'docs-stage1-pipeline-walkthrough', dir: 'docs',
      stem: 'stage1_pipeline_walkthrough', title: 'How Audio Becomes a Transcript',
      kind: 'deck', formats: ['pdf', 'tex'], rel: 'docs/stage1_pipeline_walkthrough.pdf',
      pages: 14, pdf: true, stale: false, iso: '2026-09-01', notes: [],
    },
    {
      id: 'docs-stage2-reference-walkthrough', dir: 'docs',
      stem: 'stage2_reference_walkthrough', title: 'Did the Computer Hear It Right?',
      kind: 'deck', formats: ['pdf', 'tex'], rel: 'docs/stage2_reference_walkthrough.pdf',
      pages: 33, pdf: true, stale: true, iso: '2026-08-02',
      notes: [{ name: '2026-09-10-v1.md', day: '2026-09-10', v: 1 }],
    },
    {
      id: 'writeups-serve-harness-serve-harness', dir: 'writeups/serve-harness',
      stem: 'serve-harness', title: 'How the serve harness works',
      kind: 'paper', formats: ['tex'], rel: 'writeups/serve-harness/serve-harness.tex',
      pages: 0, pdf: false, stale: false, iso: '', notes: [],
    },
    {
      id: 'writeups-batch-size-batch-size', dir: 'writeups/batch-size',
      stem: 'batch-size', title: 'What the batch size costs',
      kind: 'paper', formats: ['pdf', 'tex'], rel: 'writeups/batch-size/batch-size.pdf',
      pages: 6, pdf: true, stale: false, iso: '2026-09-14', notes: [],
      marks: { pages: 2, strokes: 9 },
    },
  ],
};

/* WHAT THE WORKSPACE HAS PRODUCED, which is the other half of this page and the
   half somebody asked for: "there's no easy way for me to browse through
   results and figures in this interface." A mission's card ends by naming a
   figure and four tables; this is what the page is handed so it can draw them.

   The shape is `course/results.py`'s, and the two things to notice are what is
   NOT in it: no `rel`, because the board addresses a result by id, and a
   `fenced` list, because a directory left out silently is one somebody scrolls
   looking for. */
const RESULTS = {
  ok: true, workspace: 'research/TRD-EHR',
  figures: 3, tables: 2, more: 1,
  looked: ['results', 'figures'], fenced: ['phi'],
  groups: [
    {
      where: 'Qwen-Qwen3-Embedding-8B/google_medgemma/neighbor_count_sweep',
      at: 1789000000, iso: '2026-09-20', more: 0,
      figures: [{ id: 'neighbor-count-sweep-2041a7cc', kind: 'figure',
                  name: 'neighbor count sweep', file: 'neighbor_count_sweep.png',
                  where: 'Qwen-Qwen3-Embedding-8B/google_medgemma/neighbor_count_sweep',
                  format: 'png', size: 262283, iso: '2026-09-20' }],
      tables: [
        { id: 'sweep-curve-3a65abff', kind: 'table', name: 'sweep curve',
          file: 'sweep_curve.csv', format: 'csv', size: 2907254,
          where: 'Qwen-Qwen3-Embedding-8B/google_medgemma/neighbor_count_sweep',
          iso: '2026-09-20' },
        { id: 'sweep-summary-83097fc3', kind: 'table', name: 'sweep summary',
          file: 'sweep_summary.json', format: 'json', size: 2056,
          where: 'Qwen-Qwen3-Embedding-8B/google_medgemma/neighbor_count_sweep',
          iso: '2026-09-20' },
      ],
    },
    {
      where: 'counterfactual_pipeline/bupropion_vs_ssri',
      at: 1788000000, iso: '2026-09-14', more: 11,
      figures: [
        { id: 'propensity-by-arm-11111111', kind: 'figure', name: 'propensity by arm',
          file: 'propensity_by_arm.png', format: 'png', size: 90000,
          where: 'counterfactual_pipeline/bupropion_vs_ssri', iso: '2026-09-14' },
        { id: 'love-plot-22222222', kind: 'figure', name: 'love plot',
          file: 'love_plot.png', format: 'png', size: 70000,
          where: 'counterfactual_pipeline/bupropion_vs_ssri', iso: '2026-09-14' },
      ],
      tables: [],
    },
  ],
};

const TABLE_ROWS = {
  ok: true, id: 'sweep-curve-3a65abff', shape: 'rows', format: 'csv',
  file: 'sweep_curve.csv', size: 2907254, capped: false, more: 101889,
  columns: ['alpha', 'n_neighbors', 'roc_auc'],
  rows: [['1.0', '1', '0.5163'], ['1.0', '2', '0.5309']],
};

const TABLE_TEXT = {
  ok: true, id: 'sweep-summary-83097fc3', shape: 'text', format: 'json',
  file: 'sweep_summary.json', size: 2056, more: 0,
  text: '{\n  "n_anchors": 8516,\n  "best_k": 40\n}',
};

/* WHERE EVERY DOCUMENT IS AND WHEN IT LAST CHANGED -- stats only, which is what
   lets the page ask it every few seconds. Mutated below to stand for a deck
   that has just been rebuilt on disk by the turn the note woke. */
let STAMP = {
  ok: true, stamp: 'all-1',
  documents: {
    'docs-stage1-pipeline-walkthrough': 'a1',
    'docs-stage2-reference-walkthrough': 'b1',
    'writeups-serve-harness-serve-harness': 'c1',
    'writeups-batch-size-batch-size': 'd1',
  },
};

/* HOW MANY PAGES THE DECK HAS. Moved below to stand for the other kind of
   revision: an overhaul that reflows the document, after which the ink on page
   7 is about something that may no longer be on page 7. */
let VIEW_PAGES = 2;
// The ink the server hands back with the pages; emptied once a round has
// landed and the server has wiped what it delivered.
let VIEW_INK = { 'doc/docs-stage1-pipeline-walkthrough/p2': [[[0.1, 0.1], [0.3, 0.4]]] };

/* What a turn wrote at the bottom of the feedback file, which is the answer to
   *did it do what I asked*. */
const NOTE = '# Feedback on Did the Computer Hear It Right?\n\n'
  + 'Slide 7 has the old sample rate on it.\n\n'
  + '## What was changed\n\nSlide 7 now says 16 kHz.\n';

const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'library.html'), 'utf8'), {
  runScripts: 'outside-only', pretendToBeVisual: true,
  url: 'https://board.test/library',
});
const { window } = dom;
const doc = window.document;

const sent = [];
/* EVERYTHING THE PAGE HAS EVER ASKED FOR, and nothing empties it. `sent` is
   cleared between checks so one of them can see a single request in isolation,
   which makes it the wrong list for *this was never asked for at all*: the
   first fetch of the page is gone from it by the second section. */
const everSent = [];
window.fetch = (u, opts) => {
  const url = String(u);
  sent.push({ url: url, opts: opts || {} });
  everSent.push(url);
  if (/library\.json/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve(LIBRARY) });
  }
  if (/library\/stamp/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve(STAMP) });
  }
  if (/library\/results\.json/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve(RESULTS) });
  }
  if (/library\/table\//.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve(
      /sweep-summary/.test(url) ? TABLE_TEXT : TABLE_ROWS) });
  }
  if (/library\/note\//.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve({
      ok: true, name: '2026-09-10-v1.md', text: NOTE, truncated: false,
    }) });
  }
  if (/library\/view\//.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve({
      ok: true, n: VIEW_PAGES, truncated: false,
      pages: ['/paper/abc123-1.png', '/paper/abc123-2.png',
              '/paper/abc123-3.png'].slice(0, VIEW_PAGES),
      /* Marks already on this document, sent WITH the pages: this page holds
         no live payload to read them out of, because it opens no sitting. */
      ink: VIEW_INK,
    }) });
  }
  if (/annotate\/save/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve({ ok: true }) });
  }
  if (/library\/direction/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve({
      ok: true, turn: 't0099', pages: [2], images: [],
      detail: 'Your marks on page 2 went as a proposed direction.',
    }) });
  }
  if (/library\/feedback/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve({
      ok: true, rel: 'writeups/serve-harness/feedback/2026-09-16-v1.md',
      revise: 'board', asked: true, detail: 'The tutor has been asked to revise it.',
    }) });
  }
  return new Promise(() => {});
};
window.addEventListener('error', (e) => fail('uncaught: ' + e.message));

// The pen is the board's own, unchanged, so it is loaded the way the page loads
// it. jsdom has no canvas, and everything `annotate.js` does with one is drawing
// -- which is not what is being asserted here.
window.HTMLCanvasElement.prototype.getContext = () =>
  new Proxy({}, { get: () => () => {}, set: () => true });
window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
window.Element.prototype.setPointerCapture = function () {};
window.Element.prototype.releasePointerCapture = function () {};
window.requestAnimationFrame = (fn) => setTimeout(fn, 0);

/* THE SCRIPTS THE PAGE ITSELF LOADS, in the order it loads them, read out of
   its own markup rather than listed here. A hand-kept list is how a suite ends
   up green against a page that is missing a file -- the pen was loaded by both
   for months, and the plane the figure viewer needs would have been loaded by
   only one of them. `library.js` is evaluated below, after the fixtures are in
   place; `typeface.js` is deferred and only picks a reading face. */
const LIB_HTML = fs.readFileSync(path.join(WEB, 'library.html'), 'utf8');
const LIB_SCRIPTS = (LIB_HTML.match(/src="\/static\/[\w.-]+"/g) || [])
  .map((m) => /static\/([\w.-]+)/.exec(m)[1])
  .filter((f) => f !== 'library.js' && f !== 'typeface.js');
LIB_SCRIPTS.includes('plane-core.js')
  ? ok('the page loads the board\'s own plane, which is what makes one figure '
       + 'pinchable without a second gesture layer written for it')
  : fail('library.html loads no plane: ' + LIB_SCRIPTS.join(', '));
for (const f of LIB_SCRIPTS) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}

/* A tablet picked up again would arrive with a turn already recorded as in
   flight -- the page keeps that where a reload finds it. Nothing is, here. And
   the results view is remembered the same way, so it is cleared for the same
   reason: the list is what a first visit opens on. */
try { window.localStorage.removeItem('library.flight'); } catch (e) {}
try { window.localStorage.removeItem('library.results.view'); } catch (e) {}

/* THE LAYOUT OBSERVER, STOOD IN FOR. jsdom has none; this keeps what the page
   observes, so a test can say "that changed size" the way a browser would. */
const resized = [];
window.ResizeObserver = function (cb) {
  this.observe = (el) => { resized.push({ el: el, cb: cb }); };
  this.disconnect = () => {};
};

try { window.eval(fs.readFileSync(path.join(WEB, 'library.js'), 'utf8')); }
catch (e) { fail('library.js: ' + e.message); }

/* The poll's own interval, turned down so a test can watch two passes of it
   rather than sitting out eight seconds. The page reads the global on every
   pass, so this is the same code path at a different cadence. */
window.STAMP_EVERY = 60;
/* And the wait for a page image to decode before a send pictures it: jsdom
   loads no image, so an undecoded page here waits out the whole of it. */
window.PICTURE_WAIT_MS = 20;

const tap = (el) => el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
const rows = () => Array.prototype.slice.call(doc.querySelectorAll('.lib-row'));
const named = (title) => rows().filter(
  (r) => r.querySelector('.lib-name').textContent === title)[0];

(async function () {
  await sleep(20);

  // 1. It asked for the list, and nothing else.
  sent.filter((r) => /library\.json/.test(r.url)).length === 1
    ? ok('the page asks the board what this workspace has written')
    : fail('the list was not fetched once: ' + JSON.stringify(sent.map((r) => r.url)));
  doc.getElementById('lib-where').textContent === 'research/PSYCH-ASR'
    ? ok('and says which workspace it is showing')
    : fail('the workspace is not named');

  // 2. Grouped by directory: the directory IS the group, and a flat list of
  //    fifty rows says nothing about which four are one piece of work.
  const heads = Array.prototype.map.call(
    doc.querySelectorAll('.lib-dir'), (d) => d.textContent);
  heads.join('|') === 'docs|writeups/serve-harness|writeups/batch-size'
    ? ok('the documents are grouped by the directory they live in')
    : fail('the groups are: ' + heads.join('|'));
  rows().length === 4
    ? ok('and every document is drawn once, whatever formats it has')
    : fail(rows().length + ' rows for four documents');

  // 3. The two states worth seeing without reading.
  /source has changed/.test(named('Did the Computer Hear It Right?').textContent)
    ? ok('a PDF older than its source is marked stale')
    : fail('nothing says the stale document is stale');
  /1 round of feedback/.test(named('Did the Computer Hear It Right?').textContent)
    ? ok('and a document already commented on says how many rounds it has had')
    : fail('the rounds of feedback are not shown');

  // 4. A document with no PDF cannot be read on the glass.
  named('How the serve harness works').querySelector('.lib-name').disabled
    ? ok('a document with no PDF is not offered to be read')
    : fail('a document with no pages can be opened');
  /no PDF yet/.test(named('How the serve harness works').textContent)
    ? ok('and says why')
    : fail('nothing says why it cannot be read');

  // 4b. INK IS A COMPLAINT, and a document carrying some says so before it is
  //     opened -- otherwise the only way to find out is to open the note panel.
  /marked up on 2 pages, 9 strokes/.test(named('What the batch size costs').textContent)
    ? ok('a document somebody has drawn on says so on its row')
    : fail('nothing says the document has been marked up');

  // 5. Reading one asks for its pages BY ID and draws them.
  tap(named('How Audio Becomes a Transcript').querySelector('.lib-name'));
  await sleep(20);
  const asked = sent.filter((r) => /library\/view\//.test(r.url)).pop();
  asked && asked.url === '/library/view/docs-stage1-pipeline-walkthrough'
    ? ok('the pages are asked for by the id, never by the path')
    : fail('the pages were asked for as: ' + (asked && asked.url));
  doc.querySelectorAll('#reader-pages .lib-page img').length === 2
    ? ok('and the pages are drawn as pictures, the way every other document is')
    : fail('the pages did not appear');

  // 5b. THE PEN, ON THE PAGE BEING READ. Every page is an anchor in the §2.1
  //     grammar, the marks already on the document are put back, and nothing
  //     from here is ever sent as a turn.
  const pages = Array.prototype.slice.call(
    doc.querySelectorAll('#reader-pages .lib-page'));
  pages.map((p) => p.dataset.ann).join('|')
    === 'doc/docs-stage1-pipeline-walkthrough/p1|doc/docs-stage1-pipeline-walkthrough/p2'
    ? ok('every page carries the address a mark on it would be anchored to')
    : fail('the pages are anchored to: ' + pages.map((p) => p.dataset.ann).join('|'));
  window.Annotate.marked().join('|') === 'doc/docs-stage1-pipeline-walkthrough/p2'
    ? ok('and the marks already on the document came back with its pages')
    : fail('restored marks: ' + window.Annotate.marked().join('|'));
  pages.every((p) => p.querySelector('canvas.ann-layer'))
    ? ok('and each one has a layer to take the ink')
    : fail('a page has no ink layer');

  const pen = doc.getElementById('reader-pen');
  !window.Annotate.isOn()
    ? ok('the pen is off until it is asked for, so a long document still scrolls')
    : fail('the page opened in annotate mode');
  tap(pen);
  window.Annotate.isOn() && /done marking/.test(pen.textContent)
    ? ok('one tap turns it on, and the button says which state it is in')
    : fail('the pen did not come on');

  {
    const bar = doc.querySelector('.annbar-doc');
    const has = (t) => bar && Array.prototype.some.call(bar.querySelectorAll('button'),
      (b) => b.textContent === t);
    bar && !bar.hidden && ['Pen', 'Erase', 'Select', 'Copy', 'Cut', 'Paste', 'Delete',
      '↶', '↷', 'clear', 'done', 'Fine', 'Medium', 'Broad'].every(has)
      ? ok('the pen brings the board\'s own tools: loop, clipboard, eraser, nibs, undo')
      : fail('the reader\'s tool bar is missing or short: '
             + (bar ? bar.textContent : 'no bar'));
    const red = bar && bar.querySelector('.ann-ink[data-ink="#e8746c"]');
    if (red) tap(red);
    window.Annotate.colour() === '#e8746c'
      ? ok('a colour on the bar is the colour the next stroke is drawn in')
      : fail('the red ink did not take: ' + window.Annotate.colour());
    bar && bar.querySelector('.ann-custom input[type="color"]')
      ? ok('and any colour at all, from the slate\'s own well')
      : fail('there is no any-colour well');
    const sel = Array.prototype.find.call(bar ? bar.querySelectorAll('button') : [],
      (b) => b.textContent === 'Select');
    if (sel) tap(sel);
    window.Annotate.tool() === 'lasso'
      ? ok('Select is the loop')
      : fail('Select left the tool at ' + window.Annotate.tool());
    window.Annotate.setTool('pen');

    // Pinched in on a slide: both bars come onto the visible part of the glass.
    const top = doc.getElementById('reader-bar');
    window.visualViewport = { scale: 2, offsetLeft: 300, offsetTop: 200,
                              width: 500, height: 350,
                              addEventListener() {} };
    window.ViewPin.update();
    await sleep(40);
    top.style.position === 'fixed' && top.style.top === '200px'
      && top.style.left === '300px' && /scale\(0\.5\)/.test(top.style.transform)
      && /scale\(0\.5\)/.test(bar.style.transform) && bar.style.top !== ''
      ? ok('zoomed in, the reader bar and the tool bar are pinned to what is visible')
      : fail('zoomed in, the bars stayed where the page put them: top '
             + top.style.cssText + ' | tools ' + bar.style.cssText);
    window.visualViewport.scale = 1;
    window.ViewPin.update();
    await sleep(40);
    top.style.position === '' && bar.style.transform === ''
      ? ok('and at no zoom the page places them as it always did')
      : fail('the pin outlived the zoom: ' + top.style.cssText);
    delete window.visualViewport;
  }

  sent.length = 0;
  window.Annotate.setPen('#e0b45c', 2);
  window.Annotate.clear('doc/docs-stage1-pipeline-walkthrough/p1');
  await sleep(1200);
  const saves = sent.filter((r) => /annotate\/save/.test(r.url));
  saves.length
    ? ok('ink reaches disk on its own, shortly after the pen lifts')
    : fail('nothing was saved: ' + JSON.stringify(sent.map((r) => r.url)));
  saves.every((r) => JSON.parse(r.opts.body || '{}').send === false)
    ? ok('and never as a turn -- the complaint goes when the note goes')
    : fail('the page sent ink at the tutor: ' + saves.map((r) => r.opts.body).join(' '));
  saves.every((r) => /^doc\//.test(JSON.parse(r.opts.body || '{}').card))
    ? ok('anchored to the page of the document, never to a card in the lesson')
    : fail('a mark was anchored to: '
           + saves.map((r) => JSON.parse(r.opts.body || '{}').card).join(' '));

  tap(pen);
  !window.Annotate.isOn()
    ? ok('and a second tap gives the document back to the reader')
    : fail('the pen would not turn off');

  // Saving asks for the list again, so the row's mark count is right a second
  // after a ring is drawn -- and the record `say` reads must be the NEW one.
  // Left stale, a page you have just drawn on refuses to send the ink.
  await sleep(20);
  const reread = sent.filter((r) => /library\.json/.test(r.url));
  reread.length >= 1
    ? ok('saving ink asks for the list again, so the row says how much is on it')
    : fail('the row would go on saying there is no ink on the document');

  // 6. Saying what is wrong: the id, the words, and the page they were on.
  tap(doc.getElementById('reader-say'));
  !doc.getElementById('note').hidden
    ? ok('a reader can say what is wrong with the page in front of them')
    : fail('there is no way to say anything about a document');
  doc.getElementById('note-send').disabled
    ? ok('with nothing written, there is nothing to send')
    : fail('empty feedback can be sent');

  // 6b. And on a document that HAS been marked up, an empty note is the ink.
  tap(named('What the batch size costs').querySelectorAll('.lib-acts button')[1]);
  !doc.getElementById('note-send').disabled
    ? ok('a marked-up document can be sent back with nothing typed')
    : fail('the ink could not be sent without typing something as well');
  /Your marks on 2 pages/.test(doc.getElementById('note-marks').textContent)
    && !doc.getElementById('note-marks').hidden
    ? ok('and the panel says the marks are going with it')
    : fail('nothing says what happens to the ink');
  doc.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape' }));
  tap(doc.getElementById('reader-say'));

  sent.length = 0;
  const box = doc.getElementById('note-text');
  box.value = 'The batch-size arithmetic is out by a factor of two.';
  box.dispatchEvent(new window.Event('input', { bubbles: true }));
  // A real stroke on page 2, and a page image with a size, so the picture of
  // the page with its ink over it can be made.
  const P2 = 'doc/docs-stage1-pipeline-walkthrough/p2';
  window.Annotate.drop(P2);
  window.Annotate.load({ [P2]: [{ c: '#e8746c', w: 2, p: [0.1, 0.1, 0.3, 0.4] }] });
  const img2 = doc.querySelector('.lib-page[data-page="2"] img');
  Object.defineProperty(img2, 'naturalWidth', { value: 1600 });
  img2.getBoundingClientRect = () => ({ left: 0, top: 0, width: 800, height: 450,
                                        right: 800, bottom: 450 });
  tap(doc.getElementById('note-send'));
  await sleep(60);
  const pic = sent.findIndex((r) => /annotate\/save/.test(r.url)
    && JSON.parse(r.opts.body || '{}').card === P2
    && /^data:image\/png/.test(JSON.parse(r.opts.body || '{}').png || ''));
  const filed = sent.findIndex((r) => /library\/feedback/.test(r.url));
  pic >= 0 && filed > pic
    ? ok('each marked page is saved with a picture of it before the note goes, '
         + 'so the turn has an image to open')
    : fail('no page picture went ahead of the note: '
           + sent.map((r) => r.url).join(' '));
  pic >= 0 && JSON.parse(sent[pic].opts.body).send === false
    ? ok('and the picture is a save, never a turn of its own')
    : fail('the page picture was sent as a turn');
  const post = sent.filter((r) => /library\/feedback/.test(r.url))[0];
  if (!post) {
    fail('the feedback was never sent');
  } else {
    const body = JSON.parse(post.opts.body || '{}');
    post.opts.method === 'POST'
      && body.document === 'docs-stage1-pipeline-walkthrough'
      ? ok('the note is sent against the document id')
      : fail('the note was sent as: ' + post.opts.body);
    /factor of two/.test(body.text)
      ? ok('with their words, not a summary of them')
      : fail('their words did not survive');
    typeof body.page === 'number'
      ? ok('and the page they were looking at, read off the scroll')
      : fail('no page number rode with the note');
    Object.keys(body).indexOf('rel') < 0 && !/\.pdf|\.tex/.test(post.opts.body)
      ? ok('and no path anywhere in it')
      : fail('the page sent a path: ' + post.opts.body);
  }
  /Filed at/.test(doc.getElementById('note-said').textContent)
    ? ok('the reply says where it landed')
    : fail('nothing says what became of the note');
  /asked to revise/.test(doc.getElementById('note-said').textContent)
    ? ok('and that something was asked to act on it')
    : fail('the note reads as filed and forgotten');

  // 6c. A TURN IS RUNNING, AND THE PAGE SAYS SO. The reply said a turn was
  //     woken, which is not the same as the document having changed -- so the
  //     line stays until the bytes move, and it is on the row as well as in the
  //     reader, because the document being worked on is usually not the open one.
  /being revised/.test(doc.getElementById('reader-said').textContent)
    && !doc.getElementById('reader-said').hidden
    ? ok('the reader says a revision is in flight, rather than going silent')
    : fail('nothing says the revision is running: '
           + doc.getElementById('reader-said').textContent);
  const onRow = doc.querySelector(
    '.lib-flight[data-id="docs-stage1-pipeline-walkthrough"]');
  onRow && !onRow.hidden && /being revised/.test(onRow.textContent)
    ? ok('and so does the row, without anything being opened')
    : fail('the row does not say a turn is running on that document');

  // 6d. THE STAMP IS POLLED, AND IT IS NOT THE LESSON'S STREAM. Section 7
  //     below is the other half of this: nothing is ever SENT at the lesson.
  sent.length = 0;
  await sleep(220);
  sent.filter((r) => /library\/stamp/.test(r.url)).length >= 2
    ? ok('the page keeps asking whether anything has moved')
    : fail('the stamp is asked '
           + sent.filter((r) => /library\/stamp/.test(r.url)).length + ' time(s)');
  !sent.filter((r) => /library\.json/.test(r.url)).length
    ? ok('and asks for the expensive list only when the stamp says to')
    : fail('the page is polling the whole list');
  !/EventSource/.test(fs.readFileSync(path.join(WEB, 'library.js'), 'utf8'))
    ? ok('never by subscribing to the lesson’s own stream, whose payload is the '
         + 'lesson’s')
    : fail('library.js opened the hub’s stream');

  // 6e. AND WHEN IT LANDS, THE OPEN DOCUMENT IS RE-DRAWN WHERE IT WAS.
  //     Throwing a 33-page deck back to page 1 after a one-line fix is its own
  //     defect, so the scroll is kept and the pages are rebuilt under it.
  doc.getElementById('reader-pages').scrollTop = 900;
  sent.length = 0;
  STAMP = {
    ok: true, stamp: 'all-2',
    documents: Object.assign({}, STAMP.documents,
                             { 'docs-stage1-pipeline-walkthrough': 'a2' }),
  };
  await sleep(300);
  const again = sent.filter((r) => /library\/view\//.test(r.url));
  again.length && again[0].url === '/library/view/docs-stage1-pipeline-walkthrough'
    ? ok('the open document is re-drawn the moment its bytes move')
    : fail('the reader never re-fetched: ' + JSON.stringify(sent.map((r) => r.url)));
  sent.filter((r) => /library\.json/.test(r.url)).length
    ? ok('and the list is asked for again, so every row is right as well')
    : fail('the list was not re-fetched when something moved');
  doc.getElementById('reader-pages').scrollTop !== 0
    ? ok('the reader keeps its place across the re-draw')
    : fail('a one-line fix threw the reader back to page 1');
  doc.querySelectorAll('#reader-pages .lib-page img').length === 2
    ? ok('and the pages are there again, drawn from the new render')
    : fail('the re-draw left the reader empty');
  window.Annotate.marked().length
    ? ok('the ink is still on it -- a ring somebody drew is theirs, not the '
         + 'render’s')
    : fail('the re-draw threw away the marks');
  doc.getElementById('reader-said').hidden
    || !/being revised/.test(doc.getElementById('reader-said').textContent)
    ? ok('and the in-flight line goes when the document itself changes')
    : fail('the page still says a revision is running after it landed');

  // 6e1. THE PAGE STAYS UNDER THE PEN. The pen reads a page's rectangle once,
  //      at the nib, so a page moved by LAYOUT mid-stroke is ink in the wrong
  //      place. The bar re-wrapping, a line appearing above the pages, a
  //      picture decoding above the glass: the page on the glass is put back.
  {
    const scroller = doc.getElementById('reader-pages');
    const fig = doc.querySelector('#reader-pages .lib-page');
    let figTop = 40;
    fig.getBoundingClientRect = () => ({ top: figTop, bottom: figTop + 900,
                                         left: 0, right: 600 });
    const realNow = window.Date.now;
    window.Date.now = () => realNow() + 60000;   /* past the re-draw's restore */
    scroller.scrollTop = 300;
    scroller.dispatchEvent(new window.Event('scroll'));
    const before = scroller.scrollTop;
    figTop = 72;                          /* the bar grew a row */
    const bar = doc.getElementById('reader-bar');
    const watched = resized.filter((r) => r.el === bar);
    watched.forEach((r) => r.cb([{ target: bar }]));
    window.Date.now = realNow;
    watched.length && scroller.scrollTop === before + 32
      ? ok('a bar that changes height does not move the page being written on')
      : fail('the page moved by layout and nothing put it back: scrollTop '
             + before + ' -> ' + scroller.scrollTop
             + (watched.length ? '' : ' (the bar is not watched)'));
    ['reader-said', 'reader-rebuilt', 'reader-copy'].every(
      (id) => resized.some((r) => r.el === doc.getElementById(id)))
      && resized.some((r) => r.el === fig)
      ? ok('and nor does a line above the pages, or a page that decodes')
      : fail('something above the pages can change size unwatched');
    delete fig.getBoundingClientRect;
  }

  // 6e1b. THE READER ZOOMS ITSELF, AND A PALM DOES NOT SCROLL. Safari's own
  //       pinch scaled the bar with the page; here a pinch re-lays the pages
  //       out at a wider width, and with the pen on one contact moves nothing.
  {
    const scroller = doc.getElementById('reader-pages');
    const touch = (name, pts) => {
      const ev = new window.Event(name, { bubbles: true, cancelable: true });
      const list = pts.map(([x, y, type, r]) => ({
        clientX: x, clientY: y, touchType: type || 'direct', radiusX: r || 10 }));
      Object.defineProperty(ev, 'touches', { value: list });
      scroller.dispatchEvent(ev);
      return ev;
    };
    touch('touchstart', [[100, 300], [200, 300]]);
    touch('touchmove', [[50, 300], [250, 300]]);
    /transform|scale\(2\)/.test(scroller.style.transform)
      ? ok('a pinch follows the fingers while they are down')
      : fail('nothing moves during a pinch: ' + JSON.stringify(scroller.style.transform));
    touch('touchend', [[250, 300]]);
    const zoomed = scroller.style.getPropertyValue('--zoom');
    const chip = doc.getElementById('reader-zoom');
    zoomed === '2' && !scroller.style.transform
      ? ok('and the lift lays the pages out at twice the width')
      : fail('the pinch did not commit: --zoom=' + zoomed);
    !chip.hidden && chip.textContent === '200%'
      ? ok('the bar says the zoom, and only when it is not the fit')
      : fail('the zoom is not said: ' + chip.hidden + ' ' + chip.textContent);
    tap(chip);
    scroller.style.getPropertyValue('--zoom') === '1' && chip.hidden
      ? ok('and a tap on it puts the page width back')
      : fail('the zoom chip does not reset');
    const palmStart = touch('touchstart', [[100, 300], [200, 300, 'direct', 80]]);
    const palmMove = touch('touchmove', [[50, 300], [250, 300, 'direct', 80]]);
    touch('touchend', []);
    scroller.style.getPropertyValue('--zoom') === '1'
      ? ok('a palm beside a finger is not a pinch')
      : fail('a palm zoomed the page');
    !palmStart.defaultPrevented && palmMove.defaultPrevented
      ? ok('and it is not Safari\'s either: its moves are refused once the pair spreads')
      : fail('a palm beside a finger: start refused ' + palmStart.defaultPrevented
             + ' (a resting palm must not stop a scroll), spreading move refused '
             + palmMove.defaultPrevented);
    const restStart = touch('touchstart', [[400, 500, 'direct', 80], [100, 300]]);
    const restMove = touch('touchmove', [[401, 500, 'direct', 80], [100, 180]]);
    touch('touchend', []);
    !restStart.defaultPrevented && !restMove.defaultPrevented
      ? ok('with the pen off, a finger beside a resting palm scrolls natively')
      : fail('a resting palm stops a finger scrolling: ' + restStart.defaultPrevented
             + '/' + restMove.defaultPrevented);
    /* A REAL BUTTON ON THE BAR. A second finger on it is refused to Safari
       like any other, and a tap there still clicks it, once. */
    {
      const btn = doc.getElementById('reader-say');
      const at = (target, name, pts, changed) => {
        const ev = new window.Event(name, { bubbles: true, cancelable: true });
        const list = pts.map(([x, y, id]) => ({ identifier: id, clientX: x, clientY: y,
                                               touchType: 'direct', radiusX: 10 }));
        Object.defineProperty(ev, 'touches', { value: list });
        Object.defineProperty(ev, 'changedTouches', { value: changed.map(
          (id) => list.find((p) => p.identifier === id) || { identifier: id }) });
        target.dispatchEvent(ev);
        return ev;
      };
      let clicks = 0;
      const count = (e) => { if (e.target === btn) { clicks++; e.stopPropagation(); } };
      window.addEventListener('click', count, true);
      at(scroller, 'touchstart', [[100, 300, 1]], [1]);
      const s2 = at(btn, 'touchstart', [[100, 300, 1], [400, 40, 2]], [2]);
      at(btn, 'touchend', [[100, 300, 1]], [2]);
      at(scroller, 'touchend', [], [1]);
      window.removeEventListener('click', count, true);
      s2.defaultPrevented && clicks === 1
        ? ok('a second finger on a #reader-bar button is refused to Safari, and a tap there clicks once')
        : fail('a #reader-bar button beside a thumb: start refused ' + s2.defaultPrevented
               + ', clicks ' + clicks);
    }
    doc.body.classList.contains('reading') && !doc.getElementById('reader').hidden
      ? ok('the library behind an open reader is locked, so a finger on the bar pans nothing')
      : fail('the page behind the reader can still scroll: body.reading '
             + doc.body.classList.contains('reading'));
    const g = new window.Event('gesturestart', { bubbles: true, cancelable: true });
    doc.dispatchEvent(g);
    g.defaultPrevented
      ? ok('Safari’s own zoom is refused while a document is open')
      : fail('Safari still zooms the whole page');
    const wasOn = window.Annotate.isOn();
    window.Annotate.setOn(false);
    !touch('touchstart', [[100, 300]]).defaultPrevented
      ? ok('with the pen off, one finger scrolls')
      : fail('one finger cannot scroll with the pen off');
    window.Annotate.setOn(true);
    !touch('touchstart', [[100, 300]]).defaultPrevented
      ? ok('with the pen on, one finger still scrolls')
      : fail('one finger cannot scroll with the pen on');
    touch('touchend', []);
    touch('touchstart', [[100, 300, 'direct', 80]]).defaultPrevented
      ? ok('with the pen on, a palm moves nothing')
      : fail('a palm can still scroll the page while marking');
    touch('touchend', []);
    touch('touchstart', [[100, 300], [300, 300, 'stylus']]).defaultPrevented
      ? ok('and a finger landing beside the Pencil moves nothing')
      : fail('a hand beside the Pencil scrolled the page');
    touch('touchend', []);
    doc.body.classList.add('pen-writing');
    touch('touchstart', [[100, 300]]).defaultPrevented
      ? ok('nor does one landing while the nib has only just lifted')
      : fail('a palm after a stroke scrolled the page');
    touch('touchend', []);
    doc.body.classList.remove('pen-writing');
    window.Annotate.setOn(wasOn);
    const css = fs.readFileSync(path.join(WEB, 'library.css'), 'utf8');
    /body\.pen-writing #reader-pages\.zoomable \{ touch-action: none; \}/.test(css)
      && !/body\.annotating #reader-pages\.zoomable \{ touch-action: none; \}/.test(css)
      ? ok('and the browser is told so before the gesture starts, and only then')
      : fail('library.css refuses a finger its scroll with the pen on');
  }

  // 6e2. THE INK IS KEPT, AND THE PAGE SAYS SO OUT LOUD. After a correction
  //      the mark on page 7 is still about page 7. After an overhaul that
  //      reflows the deck it is not -- and the marks are somebody's work, so
  //      they are kept and the page says which version they were drawn on
  //      rather than deleting them or pretending nothing moved.
  VIEW_PAGES = 3;
  STAMP = {
    ok: true, stamp: 'all-2b',
    documents: Object.assign({}, STAMP.documents,
                             { 'docs-stage1-pipeline-walkthrough': 'a3' }),
  };
  await sleep(300);
  doc.querySelectorAll('#reader-pages .lib-page img').length === 3
    ? ok('an overhaul that reflows the document is drawn at its new length')
    : fail('the reflowed document was not re-drawn');
  window.Annotate.marked().length
    ? ok('and the marks are still there, rather than deleted because it moved')
    : fail('a reflow threw away somebody’s ink');
  /drawn on a version with 2 pages/.test(
    doc.getElementById('reader-said').textContent)
    ? ok('with the page saying out loud which version they were drawn on')
    : fail('nothing says the ink is older than the document: '
           + doc.getElementById('reader-said').textContent);

  // 6e3. SPENT INK LEAVES THE GLASS. Once the round lands the server deletes
  //      the marks it delivered, and `Annotate.load` never takes a mark away --
  //      so the reader drops any saved mark the server no longer hands back.
  VIEW_INK = {};
  STAMP = {
    ok: true, stamp: 'all-2c',
    documents: Object.assign({}, STAMP.documents,
                             { 'docs-stage1-pipeline-walkthrough': 'a4' }),
  };
  await sleep(300);
  !window.Annotate.marked().some((id) => /^doc\/docs-stage1-pipeline-walkthrough\//.test(id))
    ? ok('ink the server wiped after a landed round is gone from the glass too')
    : fail('wiped ink is still on the reader: ' + window.Annotate.marked().join(','));
  !window.Annotate.unsaved().length
    ? ok('and dropping it saves nothing back, so it cannot come back to life')
    : fail('dropping wiped ink marked it unsaved: ' + window.Annotate.unsaved().join(','));

  // 6f. A DOCUMENT NOBODY TOUCHED IS NOT RE-DRAWN. A 33-page deck redrawn
  //     because a different document was built is the same defect the other way.
  sent.length = 0;
  STAMP = {
    ok: true, stamp: 'all-3',
    documents: Object.assign({}, STAMP.documents,
                             { 'writeups-batch-size-batch-size': 'd2' }),
  };
  await sleep(300);
  !sent.filter((r) => /library\/view\//.test(r.url)).length
    ? ok('and is left alone when it is a different document that moved')
    : fail('the reader re-drew for somebody else’s rebuild');

  // 6g. WHAT A ROUND ACTUALLY DID, read on the glass. The turn writes
  //     `## What was changed` into the feedback file, and the row could say
  //     "one round" and not a word of what it was.
  sent.length = 0;
  tap(named('Did the Computer Hear It Right?').querySelector('.lib-rounds'));
  await sleep(20);
  const asknote = sent.filter((r) => /library\/note\//.test(r.url))[0];
  asknote
    && asknote.url === '/library/note/docs-stage2-reference-walkthrough/2026-09-10-v1.md'
    ? ok('a round of feedback is asked for by the document id and the note name')
    : fail('the round was asked for as: ' + (asknote && asknote.url));
  /What was changed/.test(doc.getElementById('round-text').textContent)
    ? ok('and what the turn said it changed is on the glass')
    : fail('the round opened without its contents');
  doc.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape' }));
  doc.getElementById('round').hidden
    ? ok('escape closes it')
    : fail('the round panel would not close');

  // 6h. THE SECOND ASK. An overhaul may restructure, cut and rewrite, and the
  //     prompt a correction is woken with forbids exactly that -- so this is a
  //     different ask rather than a longer note.
  sent.length = 0;
  tap(named('Did the Computer Hear It Right?').querySelectorAll('.lib-acts button')[1]);
  tap(doc.getElementById('ask-rework'));
  !doc.getElementById('note-purpose-box').hidden
    ? ok('asking for an overhaul asks what the document is for now')
    : fail('the overhaul takes no purpose');
  doc.getElementById('note-send').disabled
    ? ok('and the send is dead until that sentence exists')
    : fail('an overhaul could be sent with no purpose in it');
  doc.getElementById('note-purpose').value = 'a short one';
  doc.getElementById('note-purpose')
     .dispatchEvent(new window.Event('input', { bubbles: true }));
  doc.getElementById('note-send').disabled
    ? ok('“make it better” is not a purpose, and is refused before it is sent')
    : fail('a three-word purpose armed the send');
  const AIM = 'a fifteen-minute briefing for the lab meeting on what colibri '
    + 'does to a transcript';
  doc.getElementById('note-purpose').value = AIM;
  doc.getElementById('note-purpose')
     .dispatchEvent(new window.Event('input', { bubbles: true }));
  !doc.getElementById('note-send').disabled
    ? ok('and with one, the overhaul can go with nothing else typed')
    : fail('a real purpose did not arm the send');
  tap(doc.getElementById('note-send'));
  await sleep(20);
  const over = sent.filter((r) => /library\/feedback/.test(r.url))[0];
  if (!over) {
    fail('the overhaul was never sent');
  } else {
    const body = JSON.parse(over.opts.body || '{}');
    body.ask === 'rework' && body.purpose === AIM
      ? ok('it is sent as an overhaul, carrying the purpose')
      : fail('the overhaul was sent as: ' + over.opts.body);
    body.document === 'docs-stage2-reference-walkthrough'
      && !/\.pdf|\.tex/.test(over.opts.body)
      ? ok('against the document id, with no path anywhere in it')
      : fail('the overhaul named a path: ' + over.opts.body);
  }
  tap(doc.getElementById('ask-revise'));
  doc.getElementById('note-purpose-box').hidden
    ? ok('and going back to a correction puts the purpose away again')
    : fail('the purpose box stayed open for a correction');
  doc.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape' }));

  // 7. NOTHING HERE TOUCHES THE LESSON.
  const lesson = sent.filter((r) => /\/(say|session|aim|direction|board\.json|events)/
    .test(r.url));
  !lesson.length
    ? ok('the page never sends anything at the lesson')
    : fail('the library touched the lesson: ' + lesson.map((r) => r.url).join(' '));
  const js = fs.readFileSync(path.join(WEB, 'library.js'), 'utf8');
  !/live\/cards|board\/write|\/session/.test(js)
    ? ok('and nothing in it knows how to write a card')
    : fail('library.js reaches for the lesson');

  // 7b. FIXES BEFORE THE MEETING, DIRECTIONS AFTER IT. One switch on the
  //     reader bar says what the NEXT ink on this document is for, and each
  //     kind has its own send: a direction never goes near `/library/feedback`.
  //     The ink itself is `inkHasAKind`, below.
  {
    const mode = doc.getElementById('reader-mode');
    const sayBtn = doc.getElementById('reader-say');
    const direct = doc.getElementById('reader-direct');
    /fixes/.test(mode.textContent) && /say what is wrong/.test(sayBtn.textContent)
      && direct.hidden
      ? ok('a document opens with its ink as fixes, and no directions to send')
      : fail('the ink mode opened as: ' + mode.textContent);
    tap(mode);
    /directions/.test(mode.textContent) && /say what is wrong/.test(sayBtn.textContent)
      && !direct.hidden && window.Annotate.kind() === 'dir'
      ? ok('one tap after the meeting draws directions, with a send of their own')
      : fail('the switch did not take: ' + mode.textContent + ' / ' + sayBtn.textContent
             + ' / ' + (direct.hidden ? 'no directions send' : direct.textContent));
    window.localStorage.getItem('library.inkmode:docs-stage1-pipeline-walkthrough')
      === 'directions'
      ? ok('and it is remembered for this document')
      : fail('the ink mode is not remembered');
    tap(sayBtn);
    !doc.getElementById('ask-revise').hidden && doc.getElementById('ask-direction').hidden
      ? ok('say what is wrong is a fix in either mode')
      : fail('say what is wrong opened the direction panel');
    doc.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape' }));
    sent.length = 0;
    tap(direct);
    !doc.getElementById('ask-direction').hidden
      && doc.getElementById('ask-revise').hidden
      && doc.getElementById('ask-rework').hidden
      && /propose it/.test(doc.getElementById('note-send').textContent)
      ? ok('the panel offers only a direction, never a fix, in that mode')
      : fail('the panel in directions mode still offers a fix');
    const words = doc.getElementById('note-text');
    words.value = 'Dr. Paulus: try the weighting on the MDD-only cohort. Not confirmed.';
    words.dispatchEvent(new window.Event('input', { bubbles: true }));
    tap(doc.getElementById('note-send'));
    await sleep(60);
    const dir = sent.filter((r) => /library\/direction/.test(r.url))[0];
    dir && JSON.parse(dir.opts.body).document === 'docs-stage1-pipeline-walkthrough'
      && /Paulus/.test(JSON.parse(dir.opts.body).text)
      ? ok('it goes to /library/direction with their words')
      : fail('the direction went as: ' + sent.map((r) => r.url).join(' '));
    !sent.some((r) => /library\/feedback/.test(r.url))
      ? ok('and no revision is asked for')
      : fail('a direction was filed as feedback on the document');
    /proposed direction/.test(doc.getElementById('note-said').textContent)
      ? ok('and the panel says what happened to it')
      : fail('nothing said the direction went');
    doc.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape' }));
    tap(mode);
    /fixes/.test(mode.textContent) && direct.hidden && window.Annotate.kind() === null
      ? ok('and the switch goes back to fixes, with no directions left to send')
      : fail('the switch would not go back');
    sent.length = 0;
  }

  // 8. The two ways out, because a full-screen surface needs them.
  doc.getElementById('lib-back').getAttribute('href') === '/board'
    && doc.getElementById('lib-map').getAttribute('href') === '/board?map=1'
    ? ok('the board and the map are both one tap away')
    : fail('there is no way back to the lesson');

  // 8b. AND IT GOES WHERE YOU CAME FROM.
  // The board's own row into this page is a lesson stepping sideways, so
  // `/board` is right. The FRONT DOOR's "Papers & decks" is not: reading a
  // document nobody is teaching from has nothing to do with the lesson, which
  // is the whole reason that button exists, and dropping somebody into a
  // sitting they never opened in order to get back to the door they tapped
  // from is the trapped-level defect on a different page. The caller says
  // where it came from; this says so in the label.
  const came = new JSDOM(fs.readFileSync(path.join(WEB, 'library.html'), 'utf8'), {
    runScripts: 'outside-only', pretendToBeVisual: true,
    url: 'https://board.test/library?from=home',
  });
  came.window.fetch = () => new Promise(() => {});
  came.window.HTMLCanvasElement.prototype.getContext = () =>
    new Proxy({}, { get: () => () => {}, set: () => true });
  try { came.window.eval(fs.readFileSync(path.join(WEB, 'library.js'), 'utf8')); }
  catch (e) { fail('library.js under ?from=home: ' + e.message); }
  const cameBack = came.window.document.getElementById('lib-back');
  cameBack.getAttribute('href') === '/'
    && /Everything/.test(cameBack.textContent)
    ? ok('reached from the front door, the way back is the front door, and it '
         + 'says Everything rather than naming a lesson nobody opened')
    : fail('the library still sends the front door into a lesson: '
           + cameBack.getAttribute('href') + ' / ' + cameBack.textContent);

  // 8c. AND IT OPENS THE DOCUMENT IT WAS SENT FOR. The front door's deck from
  // sittings lands here with `?doc=<id>`; "Read the deck" that drops somebody
  // on a list of documents has made them go and find it. An id the list does
  // not have opens nothing.
  const opener = (want) => {
    const w = new JSDOM(fs.readFileSync(path.join(WEB, 'library.html'), 'utf8'), {
      runScripts: 'outside-only', pretendToBeVisual: true,
      url: 'https://board.test/library?from=home&doc=' + want,
    });
    const asked = [];
    w.window.fetch = (u) => {
      const url = String(u);
      asked.push(url);
      if (/library\.json/.test(url)) {
        return Promise.resolve({ json: () => Promise.resolve(LIBRARY) });
      }
      return new Promise(() => {});
    };
    w.window.HTMLCanvasElement.prototype.getContext = () =>
      new Proxy({}, { get: () => () => {}, set: () => true });
    try { w.window.eval(fs.readFileSync(path.join(WEB, 'library.js'), 'utf8')); }
    catch (e) { fail('library.js under ?doc=: ' + e.message); }
    return { w: w, asked: asked };
  };
  const wanted = opener('writeups-batch-size-batch-size');
  const missed = opener('writeups-not-a-deck');
  await sleep(40);
  const wd = wanted.w.window.document;
  !wd.getElementById('reader').hidden
    && wd.getElementById('reader-name').textContent === 'What the batch size costs'
    && wanted.asked.some((u) => /library\/view\/writeups-batch-size-batch-size$/.test(u))
    ? ok('?doc=<id> opens that document in the reader, the way a tap on its '
         + 'row does')
    : fail('?doc= did not open the document: '
           + wd.getElementById('reader-name').textContent);
  missed.w.window.document.getElementById('reader').hidden
    && !missed.asked.some((u) => /library\/view\//.test(u))
    ? ok('and an id the list does not have opens nothing')
    : fail('?doc= with a miss opened something');
  // A THREAD SHEET'S WRITE-UP ROW sends the page its heading is on.
  const paged = opener('writeups-batch-size-batch-size&page=3');
  await sleep(40);
  !paged.w.window.document.getElementById('reader').hidden
    && paged.w.window.placeWanted === 3 && wanted.w.window.placeWanted === 0
    ? ok('&page=<n> opens the document to be put at that page')
    : fail('&page= asked for page ' + paged.w.window.placeWanted);

  const home = fs.readFileSync(path.join(WEB, 'home.js'), 'utf8');
  /\/library\?from=home/.test(home)
    ? ok('and the front door is what says so, on both routes in -- the one it '
         + 'is already serving and the one it has to switch to')
    : fail('home.js opens the library without saying where from');

  doc.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape' }));
  doc.getElementById('note').hidden
    ? ok('escape closes the note without sending it')
    : fail('escape left the panel open');

  // 9. WHAT THE WORKSPACE HAS PRODUCED, on the same page as what it has
  //    written. The ask, in the owner's words: "there's no easy way for me to
  //    browse through results and figures in this interface." A mission's card
  //    had just ended by naming a figure and four tables, and the only way to
  //    look at any of it was a terminal.
  const dirs = () => Array.prototype.slice.call(doc.querySelectorAll('.res-dir'));
  const resRows = () => Array.prototype.slice.call(doc.querySelectorAll('.res-row'));

  !doc.getElementById('res').hidden
    ? ok('the results section is drawn beside the documents, on one page')
    : fail('the results section never appeared');
  dirs().length === 2
    ? ok('the directory is the group, because a pipeline writes one filename '
         + 'once per contrast and the directory is what tells them apart')
    : fail(dirs().length + ' groups for two directories');
  const openness = () => dirs().map((d) => d.getAttribute('aria-expanded'));
  openness().join(',') === 'true,false'
    ? ok('the one that changed last is open and the rest are closed, because '
         + 'six hundred figures is not a list')
    : fail('the groups open on arrival are: ' + openness().join(','));
  /3 figures/.test(doc.getElementById('res-count').textContent)
    && /1 more director/.test(doc.getElementById('res-count').textContent)
    ? ok('and it says how many there are and how many it is not showing, '
         + 'because a silent cap reads as this is all there is')
    : fail('the count says: ' + doc.getElementById('res-count').textContent);
  const sealedLine = doc.getElementById('res-fenced');
  !sealedLine.hidden && /phi\/ is session content/.test(sealedLine.textContent)
    ? ok('a fenced directory is NAMED where its rows would have been, so a '
         + 'page cannot quietly leave one out')
    : fail('nothing visible on the page says the fence is there');

  // THE CARD NAMES THE FILE. Somebody reading "neighbor_count_sweep.png" has
  // to find the row by that string, so the row is that string -- not the
  // prettied name the drawer uses when a figure is being chosen.
  const byFile = (f) => resRows().filter(
    (r) => r.querySelector('.res-name').textContent === f)[0];
  byFile('neighbor_count_sweep.png')
    ? ok('a row is the filename the card named, not a prettied version of it')
    : fail('the figure the card names is not findable by its name: '
           + resRows().map((r) => r.textContent).join('|'));
  /11 more not listed/.test(dirs().map((d) => d.textContent).join('|'))
    ? ok('and a group says what it is holding back as well')
    : fail('no group says what it is holding back');

  // A FIGURE, OVER THE ROUTE THE DRAWER ALREADY USES. An id, never a path.
  tap(byFile('neighbor_count_sweep.png') || doc.createElement('button'));
  await sleep(10);
  const shot = doc.querySelector('#shown .res-figure');
  shot && shot.getAttribute('src') === '/result/neighbor-count-sweep-2041a7cc'
    ? ok('tapping a figure puts it on the glass, addressed by its id')
    : fail('the figure is at: ' + (shot && shot.getAttribute('src')));
  !/neighbor_count_sweep\.png/.test(shot ? shot.getAttribute('src') : '')
    ? ok('and never by a path, which is the rule the whole page keeps')
    : fail('the page sent a path for a figure');
  doc.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape' }));
  doc.getElementById('shown').hidden
    ? ok('escape closes it, the way it closes everything else here')
    : fail('escape left the figure open');

  // A TABLE IS READ, NOT DOWNLOADED. A CSV handed to an iPad is a file nobody
  // finds again.
  tap(byFile('sweep_curve.csv') || doc.createElement('button'));
  await sleep(10);
  const heads2 = Array.prototype.map.call(
    doc.querySelectorAll('#shown .res-table th'), (t) => t.textContent);
  heads2.join(',') === 'alpha,n_neighbors,roc_auc'
    ? ok('tapping a CSV draws it as a table rather than downloading a file')
    : fail('the table headings are: ' + heads2.join(','));
  doc.querySelectorAll('#shown .res-table tbody tr').length === 2
    ? ok('with the rows the board read')
    : fail('the rows did not land');
  const said = doc.querySelector('#shown .res-said');
  said && /2 rows of 101891/.test(said.textContent)
    ? ok('and says how much of a hundred-thousand-row file this is, because a '
         + 'head shown silently is a different table')
    : fail('it says: ' + (said ? said.textContent : 'nothing at all'));

  tap(doc.getElementById('shown-close'));
  tap(byFile('sweep_summary.json') || doc.createElement('button'));
  await sleep(10);
  /8516/.test((doc.querySelector('#shown .res-text') || {}).textContent || '')
    ? ok('and a JSON one is drawn as what it says, because it is not rows')
    : fail('the JSON table did not draw');
  tap(doc.getElementById('shown-close'));

  // FINDING ONE BY THE NAME A CARD GAVE. The highest-value single thing here:
  // a card says `neighbor_count_sweep.png` and typing that has to land on it.
  const find = doc.getElementById('res-find');
  find.value = 'neighbor_count_sweep.png';
  find.dispatchEvent(new window.Event('input', { bubbles: true }));
  resRows().length === 1 && byFile('neighbor_count_sweep.png')
    ? ok('typing the filename from a card leaves exactly that row')
    : fail(resRows().length + ' rows match the filename in a card');

  // AND IT OPENS THE DIRECTORY THE MATCH IS IN. Asked of a figure in a group
  // that was CLOSED, because a filter that only ever finds things inside the
  // one open heading has not been asked the question.
  find.value = 'love_plot.png';
  find.dispatchEvent(new window.Event('input', { bubbles: true }));
  openness().join(',') === 'true'
    && resRows().length === 1 && byFile('love_plot.png')
    ? ok('a match inside a closed directory opens it, because a search that '
         + 'says found it and shows nothing has found nothing')
    : fail('the closed group did not open for its match: '
           + dirs().length + ' groups, ' + resRows().length + ' rows');
  find.value = 'nothing called this';
  find.dispatchEvent(new window.Event('input', { bubbles: true }));
  /Nothing here is called/.test(doc.getElementById('res-list').textContent)
    ? ok('and a search with no match says so rather than emptying the page')
    : fail('an empty search result says nothing');

  // AND THE ONE THING IT MUST NOT DO, which is this page's whole premise.
  !sent.filter((r) => /\/(say|session|aim|start)\b/.test(r.url)).length
    ? ok('and none of it touches the lesson')
    : fail('the results list reached into a sitting');

  // 10. EVERY FIGURE, AS PICTURES, AND ONE OF THEM UP CLOSE. The ask: "an
  //     option to view all figures and nice UI to select which ones to view up
  //     close." A list of six hundred filenames answers neither half --
  //     `propensity_by_arm.png` under sixty-eight directories is sixty-eight
  //     rows that say nothing about which one is the plot being looked for.
  //
  //     What must hold, and each of them is a way a grid of six hundred
  //     pictures becomes a page an iPad gives up on:
  //
  //       * IT DOES NOT FETCH THEM ALL. A tile carries the address and no
  //         `src`; the picture is asked for when the tile comes near the glass,
  //         six at a time, and a heavy one waits to be tapped.
  //       * THE FENCE IS SAID WHERE THE PICTURES WOULD HAVE BEEN. A gallery is
  //         the worst surface for a directory quietly left out.
  //       * AN ID, NEVER A PATH, and the id the TILE carries is the id the
  //         VIEWER asks for -- two surfaces addressing one figure.
  //       * AND IT ZOOMS AND STEPS, because comparing two plots up close is the
  //         reason to open one at all.
  console.log('');

  /* THE OBSERVER, STOOD IN FOR. jsdom has none, which is the whole reason this
     can be asserted precisely: nothing is near the glass until this says so,
     so a tile with a `src` is a tile that was fetched on purpose. */
  let seen = [];
  let ioOpts = null;
  window.IntersectionObserver = function (cb, opts) {
    ioOpts = opts;
    this.observe = (el) => { seen.push({ el: el, cb: cb }); };
    this.unobserve = (el) => {
      const i = seen.findIndex((s) => s.el === el);
      if (i >= 0) seen.splice(i, 1);
    };
    this.disconnect = () => { seen = []; };
  };
  /* Scrolling: the first `n` tiles the observer is holding come into view. */
  const scrollBy = (n) => {
    const batch = seen.slice(0, n);
    batch.forEach((s) => s.cb([{ target: s.el, isIntersecting: true }]));
  };
  /* A picture arriving. jsdom fetches nothing, so the event is the only part of
     a load there is -- and it is the part the queue is waiting on. */
  const landed = (img) => img.dispatchEvent(new window.Event('load'));
  const thumbs = () => Array.prototype.slice.call(
    doc.querySelectorAll('#res-grid .res-thumb'));
  const tiles = () => Array.prototype.slice.call(
    doc.querySelectorAll('#res-grid .res-tile'));
  const fetched = () => thumbs().filter((i) => i.getAttribute('src'));

  /* A WORKSPACE THE SIZE OF THE ONE THIS IS FOR -- forty figures over three
     directories, one of them too heavy to spend on a thumbnail. The shape is
     `course/results.py`'s, sent down the same route, so this is the payload the
     page really gets and not a second idea of one. */
  const GAL = { ok: true, workspace: 'research/TRD-EHR', tables: 0, more: 0,
                looked: ['results'], fenced: [], figures: 0, groups: [] };
  [['sweep/alpha', 14, 1789000000], ['sweep/beta', 20, 1788000000],
   ['cohort', 6, 1787000000]].forEach(([where, n, at]) => {
    const figs = [];
    for (let i = 0; i < n; i++) {
      figs.push({
        id: where.replace(/\W+/g, '-') + '-plot-' + i + '-abcd000' + (i % 10),
        kind: 'figure', name: 'plot ' + i, file: 'plot_' + i + '.png',
        where: where, format: 'png', at: at - i,
        /* One that must not be spent on a thumbnail, and the rest well under. */
        size: (where === 'cohort' && i === 0) ? 900000 : 50000 + i,
        iso: '2026-09-20',
      });
    }
    GAL.figures += n;
    GAL.groups.push({ where: where, at: at, iso: '2026-09-20', more: 0,
                      figures: figs, tables: [] });
  });
  const HEAVY = GAL.groups[2].figures[0];

  /* The search above was left holding a string that matches nothing. */
  find.value = '';
  find.dispatchEvent(new window.Event('input', { bubbles: true }));
  window.paintResults(GAL);
  await sleep(10);

  // --- an option, and it is remembered -----------------------------------
  const jump = doc.getElementById('lib-figures');
  !jump.hidden && /40 figures/.test(jump.textContent)
      && jump.getAttribute('href') === '#res'
    ? ok('the bar at the top says how many figures there are and goes to them, '
         + 'because a gallery under forty-five documents is a surface nobody '
         + 'scrolls far enough to find')
    : fail('the bar does not offer the figures: ' + jump.textContent);

  const asGrid = doc.getElementById('res-as-grid');
  const asList = doc.getElementById('res-as-list');
  !doc.getElementById('res-view').hidden && asGrid && asList
    ? ok('the produced section offers two views of one walk, not one')
    : fail('there is no way to ask for the gallery');
  !doc.getElementById('res-grid').hidden === false && !doc.getElementById('res-list').hidden
    ? ok('and the list is what a first visit opens on')
    : fail('the gallery is showing before it was asked for');

  tap(asGrid);
  await sleep(10);
  !doc.getElementById('res-grid').hidden && doc.getElementById('res-list').hidden
    ? ok('tapping gallery puts the grid where the list was')
    : fail('the grid did not replace the list');
  window.localStorage.getItem('library.results.view') === 'grid'
    ? ok('and the choice is remembered, so the second visit opens on it')
    : fail('the view is not remembered: '
           + window.localStorage.getItem('library.results.view'));

  // --- EVERY figure, from every directory, in one grid --------------------
  tiles().length === 40
    ? ok('every figure in the workspace is a tile, across every directory -- '
         + 'which is what "all figures" means and what the grouped list is not')
    : fail(tiles().length + ' tiles for forty figures');
  new Set(tiles().map((t) => t.querySelector('.res-tile-meta').textContent
    .split('  ·  ')[0])).size === 3
    ? ok('and each says which directory it came out of, because a pipeline '
         + 'writes one filename once per contrast')
    : fail('the tiles do not say where they came from');

  // --- AND IT FETCHES NONE OF THEM YET -----------------------------------
  // The single highest-value assertion here. Six hundred figures is 46 MB in
  // TRD-EHR, and a grid that asked for them on paint is a page that never
  // finishes on a tablet.
  fetched().length === 0 && thumbs().every((i) => i.dataset.src)
    ? ok('THE GRID ASKS FOR NO PICTURE AT ALL until one comes near the glass, '
         + 'and every tile is holding its own address to ask with')
    : fail(fetched().length + ' of forty pictures were fetched on paint');
  seen.length === 40 && /px$/.test((ioOpts || {}).rootMargin || '')
    ? ok('all forty are watched, with a margin so a picture is there before it '
         + 'is looked at rather than arriving under the eye')
    : fail('watched: ' + seen.length + ', margin: ' + JSON.stringify(ioOpts));

  scrollBy(40);
  await sleep(5);
  fetched().length === window.GRID_AT_ONCE
    ? ok('and scrolling the whole grid past the glass still has only '
         + window.GRID_AT_ONCE + ' in flight, because a thumb flicked down six '
         + 'hundred tiles must not open six hundred connections')
    : fail(fetched().length + ' in flight at once, not ' + window.GRID_AT_ONCE);
  const wasFlying = fetched().length;
  landed(fetched()[0]);
  await sleep(5);
  fetched().length === wasFlying + 1
    ? ok('one landing admits the next, so the queue drains rather than stalls')
    : fail('a landed picture admitted ' + (fetched().length - wasFlying));

  // Drain the rest the way scrolling would.
  for (let pass = 0; pass < 60; pass++) {
    const flying = fetched().filter((i) => !i.dataset.done);
    if (!flying.length) break;
    flying.forEach((i) => { i.dataset.done = '1'; landed(i); });
    await sleep(2);
  }
  fetched().length === 39
    ? ok('and every tile that came near the glass ends up with its picture')
    : fail(fetched().length + ' of thirty-nine light ones were fetched');

  // --- a heavy one is not spent on a thumbnail ---------------------------
  const heavyTile = tiles().filter((t) => t.dataset.id === HEAVY.id)[0];
  const heavyImg = heavyTile && heavyTile.querySelector('.res-thumb');
  heavyImg && !heavyImg.getAttribute('src')
    ? ok('a figure too big to spend on a thumbnail is NOT fetched by scrolling '
         + 'past it, which is the one tile in forty that would cost a megabyte')
    : fail('the heavy figure was fetched as a thumbnail');
  /900 kB/.test(heavyTile ? heavyTile.textContent : '')
    ? ok('and its tile says how big it is rather than sitting there blank')
    : fail('the heavy tile says: ' + (heavyTile ? heavyTile.textContent : ''));

  // --- AN ID, NEVER A PATH, and the tile's id is the viewer's id ---------
  fetched().every((i) => /^\/result\/[a-z0-9-]+$/.test(i.getAttribute('src')))
    ? ok('every picture is asked for as /result/<id> and nothing else -- no '
         + 'path from this page ever reaches a filesystem')
    : fail('a thumbnail was asked for as: '
           + fetched().map((i) => i.getAttribute('src')).filter(
               (u) => !/^\/result\/[a-z0-9-]+$/.test(u)).join(','));

  const first = GAL.groups[0].figures[0];        // newest of the newest group
  const firstTile = tiles()[0];
  firstTile.dataset.id === first.id
    ? ok('newest first, so the figure a job just wrote is the first tile')
    : fail('the first tile is ' + firstTile.dataset.id + ', not ' + first.id);
  tap(firstTile);
  await sleep(10);
  const upClose = doc.querySelector('#shown .res-figure');
  upClose && upClose.getAttribute('src') === '/result/' + firstTile.dataset.id
    ? ok('THE ID THE TILE CARRIES IS THE ID THE VIEWER ASKS FOR, so the picture '
         + 'that opens is the picture that was tapped')
    : fail('the tile holds ' + firstTile.dataset.id + ' and the viewer asked '
           + 'for ' + (upClose && upClose.getAttribute('src')));

  // --- UP CLOSE: a plane, and it is the board's own ----------------------
  const wrap = doc.querySelector('#shown .res-plane');
  wrap && window.Plane && typeof window.Plane.contacts === 'function'
    ? ok('one figure is a plane, and it is plane-core.js rather than a second '
         + 'gesture layer -- every rule in that file was paid for on an iPad')
    : fail('the figure is not on the board\'s own plane');
  /touch-action:\s*none/.test(
    fs.readFileSync(path.join(WEB, 'library.css'), 'utf8')
      .split('.res-plane {')[1] || '')
    ? ok('and the browser gets no share of the gesture, because a pinch the '
         + 'page is also acting on is a pinch doing two things at once')
    : fail('the plane leaves the browser a share of the gesture');

  const touch = (el, type, pts) => {
    const ev = new window.Event(type, { bubbles: true, cancelable: true });
    const list = pts.map((p) => ({ identifier: p.id, clientX: p.x, clientY: p.y }));
    ev.touches = list;
    ev.changedTouches = list;
    el.dispatchEvent(ev);
  };
  const scaleOf = () => {
    const m = /scale\(([\d.]+)\)/.exec(upClose.style.transform || '');
    return m ? Number(m[1]) : null;
  };
  scaleOf() === 1
    ? ok('it opens at the whole figure')
    : fail('it opens at ' + scaleOf());
  touch(wrap, 'touchstart', [{ id: 1, x: 100, y: 100 }, { id: 2, x: 200, y: 100 }]);
  touch(wrap, 'touchmove', [{ id: 1, x: 50, y: 100 }, { id: 2, x: 350, y: 100 }]);
  scaleOf() === 3
    ? ok('TWO FINGERS SPREAD THREEFOLD ZOOM IT THREEFOLD, which is the whole '
         + 'reason to open one figure rather than look at the grid')
    : fail('a threefold pinch gave ' + scaleOf());
  /300%/.test(doc.getElementById('shown-fit').textContent)
    ? ok('and it says how far in it is, on the button that undoes it')
    : fail('the fit button says: ' + doc.getElementById('shown-fit').textContent);
  touch(wrap, 'touchend', [{ id: 1, x: 50, y: 100 }, { id: 2, x: 350, y: 100 }]);

  // --- STEPPING WITHOUT GOING BACK, AND AT THE ZOOM ALREADY SET ----------
  const nav = doc.getElementById('shown-nav');
  !nav.hidden && /^1 of 40$/.test(doc.getElementById('shown-at').textContent)
    ? ok('the viewer says which of the forty this is')
    : fail('it says: ' + doc.getElementById('shown-at').textContent);
  doc.getElementById('shown-prev').disabled
    && !doc.getElementById('shown-next').disabled
    ? ok('and there is nothing before the first one')
    : fail('the stepper offers a figure before the first');
  tap(doc.getElementById('shown-next'));
  await sleep(5);
  const second = doc.querySelector('#shown .res-figure');
  second.getAttribute('src') === '/result/' + GAL.groups[0].figures[1].id
    ? ok('next goes to the next figure in the order showing, without going '
         + 'back to the grid -- comparing two is why anyone is in here')
    : fail('next went to ' + second.getAttribute('src'));
  /scale\(3\)/.test(second.style.transform || '')
    ? ok('AND IT ARRIVES AT THE ZOOM ALREADY SET, so the same corner of the '
         + 'next plot is under the same finger')
    : fail('the step threw the zoom away: ' + second.style.transform);
  /^2 of 40$/.test(doc.getElementById('shown-at').textContent)
    ? ok('and the count moves with it')
    : fail('the count says: ' + doc.getElementById('shown-at').textContent);
  doc.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'ArrowLeft' }));
  await sleep(5);
  doc.querySelector('#shown .res-figure').getAttribute('src')
    === '/result/' + GAL.groups[0].figures[0].id
    ? ok('the arrow keys step it too, for the same page read on a laptop')
    : fail('ArrowLeft did not step back');
  tap(doc.getElementById('shown-fit'));
  await sleep(5);
  /scale\(1\)/.test(doc.querySelector('#shown .res-figure').style.transform || '')
    ? ok('and fit is the way out of a zoom, for a hand that has lost the figure')
    : fail('fit did not undo the zoom');

  tap(doc.getElementById('shown-close'));
  doc.getElementById('shown').hidden && doc.getElementById('shown-nav').hidden
    ? ok('closing it puts the stepper away with it')
    : fail('the viewer did not close');

  // --- CHOOSING WHICH TO LOOK AT -----------------------------------------
  const pick = doc.getElementById('gal-dir');
  pick.options.length === 4
    ? ok('the directories are a chooser: every one that has figures in it, and '
         + 'every directory as the first choice')
    : fail(pick.options.length + ' choices for three directories and an all');
  /every directory/.test(pick.options[0].textContent)
    && /40 figures/.test(pick.options[0].textContent)
    ? ok('and the first says how many there are altogether')
    : fail('the first choice says: ' + pick.options[0].textContent);
  pick.value = 'cohort';
  pick.dispatchEvent(new window.Event('change', { bubbles: true }));
  await sleep(5);
  tiles().length === 6
    ? ok('picking one leaves only its figures')
    : fail(tiles().length + ' tiles for the six in cohort');
  /6 of 40 figures/.test(doc.getElementById('res-grid-count').textContent)
    ? ok('and says it is showing six of forty, because a filter that says '
         + 'nothing reads as this is all there is')
    : fail('the count says: '
           + doc.getElementById('res-grid-count').textContent);
  tap(tiles()[0]);
  await sleep(5);
  /of 6$/.test(doc.getElementById('shown-at').textContent)
    ? ok('and the stepper walks what the filter left, not all forty')
    : fail('the stepper says: ' + doc.getElementById('shown-at').textContent);
  tap(doc.getElementById('shown-close'));

  pick.value = '';
  pick.dispatchEvent(new window.Event('change', { bubbles: true }));
  await sleep(5);
  const order = doc.getElementById('gal-order');
  order.value = 'name';
  order.dispatchEvent(new window.Event('change', { bubbles: true }));
  await sleep(5);
  const names = tiles().map((t) => t.querySelector('.res-tile-name').textContent);
  names.join(',') === names.slice().sort().join(',')
    ? ok('and the order can be the filename instead of the clock')
    : fail('by name gave: ' + names.slice(0, 6).join(','));
  order.value = 'newest';
  order.dispatchEvent(new window.Event('change', { bubbles: true }));
  await sleep(5);

  // THE SAME SEARCH BOX, because "which of these am I looking for" is one
  // question and a second box beside the first is two to keep in step.
  find.value = 'plot_3.png';
  find.dispatchEvent(new window.Event('input', { bubbles: true }));
  await sleep(5);
  tiles().length === 3 && tiles().every(
    (t) => t.querySelector('.res-tile-name').textContent === 'plot_3.png')
    ? ok('the list\'s own search narrows the gallery, one box for both views')
    : fail(tiles().length + ' tiles match a filename in three directories');
  find.value = 'nothing called this';
  find.dispatchEvent(new window.Event('input', { bubbles: true }));
  await sleep(5);
  !tiles().length && !doc.getElementById('res-grid').hidden
    && /No figure here is called/.test(doc.getElementById('res-grid').textContent)
    ? ok('and a search with no match says so where the pictures would have been')
    : fail('an empty gallery says: '
           + doc.getElementById('res-grid').textContent.slice(0, 80));
  find.value = '';
  find.dispatchEvent(new window.Event('input', { bubbles: true }));
  await sleep(5);

  // --- A FENCED WORKSPACE IS REFUSED BY NAME, IN THE GALLERY TOO ---------
  // The worst possible outcome of this whole change is a grid of thumbnails
  // out of `research/PSYCH-ASR/phi/`. This is that workspace's real payload
  // shape -- no result directory, a top-level fence, and the server's own
  // sentence -- and the gallery has to carry the refusal where the pictures
  // would have been rather than drawing an empty grid.
  const SEALED = {
    ok: true, workspace: 'research/PSYCH-ASR', figures: 0, tables: 0, more: 0,
    looked: [], fenced: ['phi'], groups: [],
    why: 'This workspace has no results directory. A job that writes one into '
      + '`results/`, `figures/`, `tables/`, `artifacts/`, `analysis/` appears '
      + 'here, with no registration of any kind. research/PSYCH-ASR also holds '
      + '`phi/`. Nothing on this board looks inside it -- it is session '
      + 'content, and the refusal is by name in `tutorboard/fenced.py` -- so '
      + 'nothing in there is listed here or anywhere else.',
  };
  window.paintResults(SEALED);
  await sleep(10);
  !doc.getElementById('res-grid').hidden && !tiles().length
    ? ok('a fenced workspace draws NO TILE AT ALL in the gallery')
    : fail(tiles().length + ' tiles for a workspace nothing may look inside');
  /* Read off a grid that is actually on the glass: a sentence inside a hidden
     element is a refusal nobody sees, which is the defect, not the fix. */
  const sealedSaid = doc.getElementById('res-grid').hidden
    ? '' : doc.getElementById('res-grid').textContent;
  /`phi\/`/.test(sealedSaid) && /fenced\.py/.test(sealedSaid)
    ? ok('AND THE GALLERY NAMES THE FENCE where the pictures would have been -- '
         + 'the directory by name and the file the rule lives in, so a grid '
         + 'cannot pass for a workspace that has produced nothing')
    : fail('the empty gallery says: ' + sealedSaid.slice(0, 200));
  doc.getElementById('res-pick').hidden
      && doc.getElementById('res-grid-count').hidden
      && !doc.getElementById('res-view').hidden
    ? ok('and the chooser and the count are put away rather than offering to '
         + 'sort nothing, while the way into the gallery stays -- that is how '
         + 'the reason gets read at all')
    : fail('an empty gallery still offers a chooser, or hides the way in');
  !doc.getElementById('res-fenced').hidden
    && /phi\/ is session content/.test(
         doc.getElementById('res-fenced').textContent)
    ? ok('and the line above it says the same thing, which is the list\'s rule '
         + 'kept on the second surface')
    : fail('the fence line is not on the page in gallery view');
  !everSent.filter((u) => /phi/.test(u)).length
    ? ok('and nothing the page has asked for, from its first fetch onwards, '
         + 'has ever named it')
    : fail('the page reached into the fence: '
           + everSent.filter((u) => /phi/.test(u)).join(','));

  // --- AND A WORKSPACE WITH TABLES AND NO FIGURES SAYS SO ----------------
  window.paintResults({
    ok: true, workspace: 'x', figures: 0, tables: 2, more: 0,
    looked: ['results'], fenced: [], groups: [{
      where: 'sweep', at: 1789000000, iso: '2026-09-20', more: 0, figures: [],
      tables: [{ id: 'sweep-curve-1', kind: 'table', name: 'sweep curve',
                 file: 'sweep_curve.csv', format: 'csv', size: 900,
                 where: 'sweep', iso: '2026-09-20' }],
    }],
  });
  await sleep(10);
  !tiles().length && !doc.getElementById('res-grid').hidden
    && /tables but no figures/.test(doc.getElementById('res-grid').textContent)
    ? ok('a workspace that has produced tables and no figures says so rather '
         + 'than drawing an empty box')
    : fail('a figureless gallery says: '
           + doc.getElementById('res-grid').textContent.slice(0, 120));
  doc.getElementById('lib-figures').hidden
    ? ok('and the bar offers no way to figures a workspace does not have')
    : fail('the bar offers figures where there are none: '
           + doc.getElementById('lib-figures').textContent);

  // --- AND A QUEUE SLOT IS NEVER HELD FOR EVER --------------------------
  // `plane-core.js`'s own rule, which this page now shares: every refusal
  // expires. A picture that fires neither `load` nor `error` holds one of six
  // slots, and six of those is a grid that has stopped loading with nothing on
  // the glass saying why.
  window.paintResults(GAL);
  await sleep(10);
  window.GRID_WAIT = 5;
  scrollBy(40);
  await sleep(80);
  fetched().length > window.GRID_AT_ONCE
    ? ok('a picture that answers neither way gives its slot up on a clock, so '
         + 'the grid cannot stop loading with nothing saying why')
    : fail('the queue stalled at ' + fetched().length + ' for ever');
  const stalled = tiles().filter(
    (t) => /not answering/.test(t.textContent))[0];
  stalled
    ? ok('and the tile says so where its picture would have been')
    : fail('a stalled tile says nothing');
  window.GRID_WAIT = 20000;

  // --- AND THE GALLERY TOUCHES THE LESSON AS LITTLE AS THE LIST DOES -----
  !everSent.filter((u) => /\/(say|session|aim|start)\b/.test(u)).length
    ? ok('and nothing the gallery has ever asked for touches the lesson')
    : fail('the gallery reached into a sitting: '
           + everSent.filter((u) => /\/(say|session|aim|start)\b/.test(u)).join(','));

  await inkFollowsZoom();
  await inkIsKept();
  await inkHasAKind();
  await lazyPagesArePictured();
  await changesArePins();
  await pipsAndOwedInk();

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\nthe library draws what a workspace wrote, and takes a word about one');
  process.exit(errors.length ? 1 : 0);
})();

/* ==========================================================================
   INK FOLLOWS THE READER'S ZOOM. The case is `test/inkzoom.js`, shared with
   the meeting deck; here it runs on a paper's pages, on a DOM of its own so
   nothing it draws is owed to the main page's saves.
   ========================================================================== */
async function inkFollowsZoom() {
  const ID = 'writeups-zoom-zoom';
  const LIB = { workspace: 'research/TRD-EHR', writeups: 'writeups', documents: [{
    id: ID, dir: 'writeups/zoom', stem: 'zoom', title: 'A paper to zoom',
    kind: 'paper', formats: ['pdf'], rel: 'writeups/zoom/zoom.pdf',
    pages: 2, pdf: true, stale: false, iso: '2026-09-29', notes: [],
  }] };
  const d = new JSDOM(LIB_HTML, { runScripts: 'outside-only', pretendToBeVisual: true,
                                 url: 'https://board.test/library' });
  const w = d.window;
  w.HTMLCanvasElement.prototype.getContext = () =>
    new Proxy({}, { get: () => () => {}, set: () => true });
  w.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
  w.Element.prototype.setPointerCapture = function () {};
  w.Element.prototype.releasePointerCapture = function () {};
  w.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  w.fetch = (u) => {
    const url = String(u);
    if (/library\.json/.test(url)) return Promise.resolve({ json: () => Promise.resolve(LIB) });
    if (/library\/view\//.test(url)) {
      return Promise.resolve({ json: () => Promise.resolve({
        ok: true, n: 2, truncated: false, digest: 'z1',
        pages: ['/paper/z-1.png', '/paper/z-2.png'], ink: {},
        build: { digest: 'z1', at: 1790000000, pages: 2 }, rebuilt: null }) });
    }
    if (/annotate\/save/.test(url)) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) });
    }
    return new Promise(() => {});
  };
  w.addEventListener('error', (e) => fail('uncaught (zoom page): ' + e.message));
  for (const f of LIB_SCRIPTS) {
    try { w.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
    catch (e) { fail(f + ': ' + e.message); }
  }
  w.STAMP_EVERY = 100000;
  w.PICTURE_WAIT_MS = 20;
  try { w.eval(fs.readFileSync(path.join(WEB, 'library.js'), 'utf8')); }
  catch (e) { fail('library.js (zoom page): ' + e.message); }
  await sleep(20);
  w.document.querySelector('.lib-row .lib-name')
    .dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  await sleep(30);
  await require('./inkzoom')(w, { ok, fail, name: 'paper', naturalHeight: 1604 });
}

/* ==========================================================================
   INK IN THE READER SAYS IT IS KEPT, AND CAN BE KEPT AS A COPY.

   Asked as: *"if I'm in the middle of marking up a paper ... but then I go to
   bed, is there a way to save my markups without overwriting the original?"*
   The strokes were already on disk a second after the pen lifted. What nobody
   could see was that, or a save that failed; the typed half was not kept at
   all; and there was no copy to take away.

   A page of its own, on a DOM of its own, because two of the things asserted
   are what survives a RELOAD -- a second page handed the first one's storage
   -- and what a network that says no does to the bar.
   ========================================================================== */
async function inkIsKept() {
  const ID = 'writeups-notes-notes';
  const P1 = 'doc/' + ID + '/p1';
  const P2 = 'doc/' + ID + '/p2';
  const LIB = { workspace: 'research/TRD-EHR', writeups: 'writeups', documents: [{
    id: ID, dir: 'writeups/notes', stem: 'notes', title: 'Notes on the cohort',
    kind: 'paper', formats: ['pdf', 'tex'], rel: 'writeups/notes/notes.pdf',
    pages: 2, pdf: true, stale: false, iso: '2026-09-28', notes: [],
    made: 'board', marks: { pages: 0, strokes: 0, waiting: 0 },
  }] };
  const BUILD = { digest: 'abc123def4567890', at: 1790000000, pages: 2 };
  const S = { c: '#e8746c', w: 2, p: [0.1, 0.1, 0.3, 0.4], pr: [0.5, 0.5] };
  const net = { save: 'ok', feedback: 'ok', rebuilt: null };
  let pageWin = null;

  function answer(url) {
    if (/library\.json/.test(url)) return Promise.resolve({ json: () => Promise.resolve(LIB) });
    if (/library\/stamp/.test(url)) {
      return Promise.resolve({ json: () => Promise.resolve(
        { ok: true, stamp: 's', documents: { [ID]: 'x' } }) });
    }
    if (/library\/view\//.test(url)) {
      return Promise.resolve({ json: () => Promise.resolve({
        ok: true, n: 2, truncated: false, digest: BUILD.digest,
        pages: ['/paper/abc-1.png', '/paper/abc-2.png'], ink: {},
        build: BUILD, rebuilt: net.rebuilt }) });
    }
    if (/annotate\/save/.test(url)) {
      if (net.save === 'down') return Promise.reject(new TypeError('Failed to fetch'));
      if (net.save === 'slow') {
        return new Promise((res) => { net.release = () => res(
          { ok: true, json: () => Promise.resolve({ ok: true }) }); });
      }
      if (net.save === 'refused') {
        return Promise.resolve({ ok: false, status: 500,
                                 json: () => Promise.resolve({ ok: false }) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) });
    }
    if (/annotate\/burn/.test(url)) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({
        ok: true, mode: 'new', name: 'notes-annotated-2026-09-28.pdf',
        url: '/library/marked/' + ID + '/notes-annotated-2026-09-28.pdf',
        path: 'live/marked/' + ID + '/notes-annotated-2026-09-28.pdf', pages: 2,
        detail: 'Kept as notes-annotated-2026-09-28.pdf. The ink stays on the '
          + 'page and still goes with the next note.' }) });
    }
    if (/library\/marked\//.test(url)) {
      return Promise.resolve({ ok: true, blob: () => Promise.resolve(
        new pageWin.Blob(['%PDF-1.4'], { type: 'application/pdf' })) });
    }
    if (/library\/feedback/.test(url)) {
      return Promise.resolve({ json: () => Promise.resolve(net.feedback === 'ok'
        ? { ok: true, rel: 'writeups/notes/feedback/2026-09-28-v1.md', asked: true,
            revise: 'board', detail: 'The tutor has been asked to revise it.' }
        : { ok: false, error: 'the tutor could not be started' }) });
    }
    return new Promise(() => {});
  }

  async function open(storage) {
    const d = new JSDOM(LIB_HTML, { runScripts: 'outside-only', pretendToBeVisual: true,
                                   url: 'https://board.test/library' });
    const w = d.window;
    pageWin = w;
    Object.keys(storage || {}).forEach((k) => w.localStorage.setItem(k, storage[k]));
    w.HTMLCanvasElement.prototype.getContext = () =>
      new Proxy({}, { get: () => () => {}, set: () => true });
    w.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
    w.Element.prototype.setPointerCapture = function () {};
    w.Element.prototype.releasePointerCapture = function () {};
    w.requestAnimationFrame = (fn) => setTimeout(fn, 0);
    let hidden = false;
    Object.defineProperty(w.document, 'visibilityState',
                          { configurable: true, get: () => (hidden ? 'hidden' : 'visible') });
    const log = [];
    w.fetch = (u, o) => { log.push({ url: String(u), opts: o || {} }); return answer(String(u)); };
    w.addEventListener('error', (e) => fail('uncaught (ink page): ' + e.message));
    for (const f of LIB_SCRIPTS) {
      try { w.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
      catch (e) { fail(f + ': ' + e.message); }
    }
    w.INK_RETRY_MS = 100000;
    w.STAMP_EVERY = 100000;
    w.PICTURE_WAIT_MS = 20;
    try { w.eval(fs.readFileSync(path.join(WEB, 'library.js'), 'utf8')); }
    catch (e) { fail('library.js (ink page): ' + e.message); }
    await sleep(20);
    const click = (el) => el.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    const row = w.document.querySelector('.lib-row .lib-name');
    if (row) click(row);
    await sleep(30);
    return {
      w, doc: w.document, log, click,
      byId(id) { return w.document.getElementById(id); },
      hide(v) { hidden = v; w.document.dispatchEvent(new w.Event('visibilitychange')); },
      saves() { return log.filter((r) => /annotate\/save/.test(r.url)); },
      kept() { const k = w.document.getElementById('reader-kept'); return k.hidden ? '' : k.textContent; },
      reopen() {
        click(w.document.getElementById('reader-close'));
        click(w.document.querySelector('.lib-row .lib-name'));
      },
      /* A stroke on a page, the way the pen leaves one: on the page, and owed. */
      draw(key) {
        w.Annotate.load({ [key]: [S] });
        w.Annotate.clear(key);
        w.Annotate.undo();
      },
      storage() {
        const out = {};
        for (let i = 0; i < w.localStorage.length; i++) {
          const k = w.localStorage.key(i);
          out[k] = w.localStorage.getItem(k);
        }
        return out;
      },
    };
  }

  // ---- 1. THE BAR SAYS WHERE THE INK IS --------------------------------
  const p = await open();
  !p.byId('reader').hidden && p.w.Annotate
    ? ok('ink: the reader is open on the document')
    : fail('ink: the reader did not open');
  p.kept() === ''
    ? ok('a document with no ink on it says nothing about ink')
    : fail('a clean document says: ' + p.kept());
  p.byId('reader-keep').disabled
    ? ok('and there is no marked copy to keep yet')
    : fail('a marked copy is offered of a document with no marks');

  p.draw(P1);
  /saving/.test(p.kept())
    ? ok('a stroke not yet on disk reads “saving…” on the bar')
    : fail('a fresh stroke reads: ' + p.kept());
  await sleep(1000);
  const first = p.saves().pop();
  first && (JSON.parse(first.opts.body).build || {}).digest === BUILD.digest
    ? ok('a saved page carries the build it was drawn on')
    : fail('the save named no build: ' + (first && first.opts.body));
  p.kept() === 'saved · 1 page marked'
    ? ok('and once it lands the bar says “saved · 1 page marked”')
    : fail('a landed save reads: ' + p.kept());
  !p.byId('reader-keep').disabled
    ? ok('and a marked copy can be kept now')
    : fail('the keep button is dead on a marked document');

  // ---- 2. A SAVE THAT FAILS IS SHOWN, KEPT OWED, AND RETRIED -----------
  net.save = 'down';
  p.draw(P2);
  await sleep(1000);
  p.kept() === 'not saved — retrying'
    ? ok('a save that fails is shown: “not saved — retrying”')
    : fail('a failed save reads: ' + p.kept());
  p.byId('reader-kept').classList.contains('bad')
    ? ok('in the colour that makes somebody look')
    : fail('the failure is not marked');
  p.w.Annotate.unsaved().indexOf(P2) >= 0
    ? ok('and the page stays unsaved rather than being counted as kept')
    : fail('a failed page was cleared from unsaved');

  net.save = 'refused';
  let before = p.saves().length;
  p.hide(false);                              // looked at again: a retry
  await sleep(30);
  p.saves().length > before && p.w.Annotate.unsaved().indexOf(P2) >= 0
    && p.kept() === 'not saved — retrying'
    ? ok('back to visible is a retry, and a board that answers 500 is still '
         + 'not a save')
    : fail('visible retry: ' + (p.saves().length - before) + ' saves, bar '
           + p.kept());

  net.save = 'ok';
  before = p.saves().length;
  p.w.dispatchEvent(new p.w.Event('online'));
  await sleep(30);
  p.saves().length > before
    ? ok('the network coming back is a retry')
    : fail('nothing was retried on `online`');
  p.w.Annotate.unsaved().indexOf(P2) < 0 && p.kept() === 'saved · 2 pages marked'
    ? ok('and only that success takes the page off unsaved')
    : fail('after a good retry: unsaved ' + p.w.Annotate.unsaved().join(',')
           + ', bar ' + p.kept());

  // On a timer, with nobody touching anything.
  p.w.INK_RETRY_MS = 40;
  net.save = 'down';
  p.draw(P1);
  await sleep(1000);
  before = p.saves().length;
  net.save = 'ok';
  await sleep(250);
  p.saves().length > before && !p.w.Annotate.unsaved().length
    ? ok('and a failed save is retried on a timer, on its own')
    : fail('no timed retry: ' + (p.saves().length - before) + ' saves');
  p.w.INK_RETRY_MS = 100000;

  // ---- 3. A HIDDEN PAGE FLUSHES WITH KEEPALIVE -------------------------
  p.draw(P2);
  before = p.saves().length;
  p.hide(true);
  await sleep(10);
  const flushed = p.saves().slice(before);
  flushed.length && flushed.every((r) => r.opts.keepalive === true)
    && JSON.parse(flushed[0].opts.body).card === P2
    ? ok('a page going hidden flushes what is owed at once, with keepalive -- '
         + 'the event iOS fires when the lid shuts')
    : fail('the hidden flush: ' + JSON.stringify(flushed.map((r) => r.opts.keepalive)));
  p.hide(false);
  await sleep(30);

  // A page too heavy for the browser's keepalive allowance still goes.
  const heavy = { c: '#e8746c', w: 2, p: Array.from({ length: 12000 }, (_, i) => (i % 97) / 97),
                  pr: [0.5] };
  const P3 = 'doc/' + ID + '/p3';
  p.w.Annotate.load({ [P3]: [heavy] });
  p.w.Annotate.clear(P3);
  p.w.Annotate.undo();
  before = p.saves().length;
  p.hide(true);
  await sleep(10);
  const big = p.saves().slice(before);
  big.length === 1 && big[0].opts.body.length > 64000 && !big[0].opts.keepalive
    ? ok('a hidden flush too heavy for keepalive goes as an ordinary request '
         + 'rather than being refused by the browser')
    : fail('the heavy flush: ' + JSON.stringify(big.map((r) => [r.opts.body.length, r.opts.keepalive])));
  p.hide(false);
  await sleep(30);

  // Closed while the board is down: the ink is still owed afterwards.
  net.save = 'down';
  p.draw(P1);
  p.click(p.byId('reader-close'));
  await sleep(30);
  p.byId('reader').hidden && !p.w.document.body.classList.contains('reading')
    ? ok('closing the reader gives the library its scroll back')
    : fail('the library stays locked after the reader closed');
  net.save = 'ok';
  before = p.saves().length;
  p.w.dispatchEvent(new p.w.Event('online'));
  await sleep(30);
  p.saves().slice(before).some((r) => JSON.parse(r.opts.body).card === P1
                                    && JSON.parse(r.opts.body).strokes.length)
    ? ok('ink whose save failed as the reader closed is still retried, not let go')
    : fail('closing the reader dropped the owed ink');

  // ---- 4. KEEP A MARKED COPY -------------------------------------------
  const share = [];
  Object.defineProperty(p.w.navigator, 'canShare', { configurable: true, value: () => true });
  Object.defineProperty(p.w.navigator, 'share', { configurable: true,
    value: (d) => { share.push(d); return Promise.resolve(); } });
  p.click(p.doc.querySelector('.lib-row .lib-name'));
  await sleep(30);
  p.draw(P1);
  before = p.log.length;
  p.click(p.byId('reader-keep'));
  await sleep(60);
  const after = p.log.slice(before);
  const burnAt = after.findIndex((r) => /annotate\/burn/.test(r.url));
  const saveAt = after.findIndex((r) => /annotate\/save/.test(r.url));
  burnAt >= 0 && saveAt >= 0 && saveAt < burnAt
    ? ok('⤓ keep a marked copy puts the ink on disk first, then burns it')
    : fail('keep a copy sent: ' + after.map((r) => r.url).join(' '));
  const burnBody = burnAt >= 0 ? JSON.parse(after[burnAt].opts.body) : {};
  burnBody.kind === 'library/' + ID && burnBody.mode === 'new'
    ? ok('as a NEW file of the library document, never over it')
    : fail('the burn asked for: ' + JSON.stringify(burnBody));
  !after.some((r) => /library\/feedback|library\/direction/.test(r.url))
    && after.every((r) => !/annotate\/save/.test(r.url)
                          || JSON.parse(r.opts.body).send === false)
    ? ok('and keeping a copy is not sending: no note, no turn')
    : fail('keeping a copy sent something: ' + after.map((r) => r.url).join(' '));
  const copyLine = p.byId('reader-copy');
  !copyLine.hidden && /Kept as notes-annotated/.test(copyLine.textContent)
    && /next note/.test(copyLine.textContent)
    ? ok('the reader names the copy, and says the ink still goes with the next note')
    : fail('after keeping a copy the reader says: ' + copyLine.textContent);
  after.some((r) => r.url === '/library/marked/' + ID + '/notes-annotated-2026-09-28.pdf')
    ? ok('and fetches it straight away, so the share sheet can open on the tap')
    : fail('the copy was never fetched');
  const saveBtn = p.byId('reader-copy-save');
  !saveBtn.hidden ? ok('it offers save a copy') : fail('there is no save a copy');
  p.click(saveBtn);
  await sleep(20);
  share.length === 1 && share[0].files
    && share[0].files[0].name === 'notes-annotated-2026-09-28.pdf'
    ? ok('save a copy hands the file to the share sheet, so it can go to Files')
    : fail('the share sheet got: ' + JSON.stringify(share.map((s) => s.title)));

  // A save still in the air when the copy is asked for: the burn waits for it.
  net.save = 'slow';
  p.draw(P2);
  await sleep(1000);                          // the pen's own save is now in flight
  before = p.log.length;
  p.click(p.byId('reader-keep'));
  await sleep(60);
  !p.log.slice(before).some((r) => /annotate\/burn/.test(r.url))
    ? ok('keep a marked copy waits for a save already in the air')
    : fail('the copy was burned before the ink in the air had landed');
  net.save = 'ok';
  if (net.release) net.release();
  await sleep(60);
  p.log.slice(before).some((r) => /annotate\/burn/.test(r.url))
    ? ok('and burns once it has landed')
    : fail('the copy never went after the save landed');
  net.release = null;

  // ---- 5. REBUILT SINCE ------------------------------------------------
  const flag = p.byId('reader-rebuilt');
  flag.hidden
    ? ok('a document whose marks were drawn on the build it is showing says nothing')
    : fail('a flag is up on an unrebuilt document: ' + flag.textContent);
  net.rebuilt = { at: 1790000000, when: '28 Sep 21:40', was: 2, pages: [1],
                  copy: true, detail: '' };
  p.reopen();
  await sleep(30);
  !flag.hidden && /these marks were drawn on the 28 Sep 21:40 build; the document has been rebuilt since/i
    .test(flag.textContent)
    ? ok('reopened after a rebuild, the reader says above the pages which build '
         + 'the marks were drawn on')
    : fail('the rebuilt flag reads: ' + (flag.hidden ? '(hidden)' : flag.textContent));
  !p.byId('reader-rebuilt-keep').hidden
    ? ok('and offers a marked copy of that build while it can be made')
    : fail('no copy of the older build is offered');
  flag.compareDocumentPosition(p.byId('reader-pages'))
    & p.w.Node.DOCUMENT_POSITION_FOLLOWING
    ? ok('above the pages, where it is read before the marks are')
    : fail('the flag is not above the pages');
  net.rebuilt = { at: 1790000000, when: '28 Sep 21:40', was: 2, pages: [1],
                  copy: false,
                  detail: 'The 28 Sep 21:40 build these marks were drawn on is no '
                    + 'longer in the page cache, so a marked copy of it cannot be made.' };
  p.reopen();
  await sleep(30);
  /cannot be made/.test(flag.textContent) && p.byId('reader-rebuilt-keep').hidden
    ? ok('and says a copy cannot be made once that build has left the page cache')
    : fail('an uncachable build reads: ' + flag.textContent);
  net.rebuilt = null;

  // ---- 6. DRAFTS ARE KEPT ----------------------------------------------
  p.click(p.byId('reader-say'));
  const box = p.byId('note-text');
  box.value = 'Table 2 still has the old cohort size.';
  box.dispatchEvent(new p.w.Event('input', { bubbles: true }));
  const p2 = await open(p.storage());         // a reload, with this device's storage
  p2.click(p2.byId('reader-say'));
  p2.byId('note-text').value === 'Table 2 still has the old cohort size.'
    ? ok('a draft typed and reloaded comes back when that document’s note opens')
    : fail('after a reload the note reads: ' + JSON.stringify(p2.byId('note-text').value));

  net.feedback = 'refused';
  p2.click(p2.byId('note-send'));
  await sleep(60);
  const p3 = await open(p2.storage());
  p3.click(p3.byId('reader-say'));
  p3.byId('note-text').value === 'Table 2 still has the old cohort size.'
    ? ok('and is still there after a send the board refused')
    : fail('a refused send lost the draft: ' + JSON.stringify(p3.byId('note-text').value));

  net.feedback = 'ok';
  p3.click(p3.byId('note-send'));
  await sleep(60);
  /Filed at/.test(p3.byId('note-said').textContent)
    ? ok('ink: the note was filed')
    : fail('the note was not filed: ' + p3.byId('note-said').textContent);
  const p4 = await open(p3.storage());
  p4.click(p4.byId('reader-say'));
  p4.byId('note-text').value === ''
    ? ok('and is gone after a send that was filed')
    : fail('a filed note came back as a draft: ' + JSON.stringify(p4.byId('note-text').value));

  // An overhaul's purpose is the other half of what is typed.
  p4.click(p4.byId('ask-rework'));
  const aim = p4.byId('note-purpose');
  aim.value = 'a two-page brief for the clinical partners on what the model is for';
  aim.dispatchEvent(new p4.w.Event('input', { bubbles: true }));
  const p5 = await open(p4.storage());
  p5.click(p5.byId('reader-say'));
  p5.byId('note-purpose').value === aim.value && !p5.byId('note-purpose-box').hidden
    ? ok('an overhaul’s purpose is kept too, and reopens as an overhaul')
    : fail('the purpose after a reload: ' + JSON.stringify(p5.byId('note-purpose').value));

  // Switching the ask with no keystroke after it is still part of the draft.
  p5.click(p5.byId('ask-revise'));
  const p6 = await open(p5.storage());
  p6.click(p6.byId('reader-say'));
  p6.byId('note-purpose-box').hidden && p6.byId('ask-revise').classList.contains('on')
    ? ok('a tap on the ask with nothing typed after it is kept with the draft')
    : fail('the ask switched without a keystroke came back as an overhaul');
}

/* ==========================================================================
   A SEND PICTURES EVERY PAGE IT CARRIES, LAZY ONES TOO. Pages from the third
   are `loading="lazy"`, so ink restored on a page nobody scrolled to sits on
   an image with no pixels. The send makes that image eager and waits for it
   to decode before the picture; a page that never decodes goes without one,
   the server keeps its ink (`kept`), and the panel says to send again. Only
   the pages the reply names `stripped` are taken again from the server, so a
   stale view never puts back an older copy of a page drawn on since.
   ========================================================================== */
async function lazyPagesArePictured() {
  const ID = 'writeups-lazy-lazy';
  const key = (n) => 'doc/' + ID + '/p' + n;
  const FIX = { c: '#e0b45c', w: 2, pg: 1, p: [0.2, 0.2, 0.5, 0.2], pr: [0.5, 0.5] };
  const DIR_C = '#3366cc';
  const DIR = { c: DIR_C, w: 2, pg: 1, dir: 1, p: [0.2, 0.6, 0.5, 0.6], pr: [0.5, 0.5] };
  const LIB = { workspace: 'research/TRD-EHR', writeups: 'writeups', documents: [{
    id: ID, dir: 'writeups/lazy', stem: 'lazy', title: 'A long deck',
    kind: 'deck', formats: ['pdf', 'tex'], rel: 'writeups/lazy/lazy.pdf',
    pages: 4, pdf: true, stale: false, iso: '2026-10-01', notes: [], made: 'board',
    marks: { pages: 1, strokes: 1, waiting: 1, dir: { pages: 3, strokes: 3 } },
  }] };
  const net = { view: { [key(1)]: [FIX], [key(3)]: [DIR], [key(4)]: [DIR], [key(5)]: [DIR] },
                wiped: null, save: 'ok', hold: null };
  const log = [];
  const d = new JSDOM(LIB_HTML, { runScripts: 'outside-only', pretendToBeVisual: true,
                                 url: 'https://board.test/library' });
  const w = d.window;
  const D = w.document;
  w.HTMLCanvasElement.prototype.getContext = function () {
    const cv = this;
    cv._ops = cv._ops || [];
    const st = { strokeStyle: '', fillStyle: '' };
    return new Proxy({}, {
      get: (o, k) => {
        if (k === 'stroke') return () => cv._ops.push(st.strokeStyle);
        if (k === 'fill') return () => cv._ops.push(st.fillStyle);
        return k in st ? st[k] : () => {};
      },
      set: (o, k, v) => { st[k] = v; return true; },
    });
  };
  w.HTMLCanvasElement.prototype.toDataURL = function () {
    return 'data:image/png;base64,'
      + Buffer.from(JSON.stringify(Array.from(new Set(this._ops || [])))).toString('base64');
  };
  w.Element.prototype.setPointerCapture = function () {};
  w.Element.prototype.releasePointerCapture = function () {};
  w.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  const saves = () => log.filter((r) => /annotate\/save/.test(r.url))
    .map((r) => JSON.parse(r.opts.body || '{}'));
  w.fetch = (u, o) => {
    const url = String(u);
    log.push({ url: url, opts: o || {} });
    const reply = (x) => Promise.resolve({ ok: true, json: () => Promise.resolve(x) });
    if (/library\.json/.test(url)) return reply(LIB);
    if (/library\/stamp/.test(url)) return reply({ ok: true, stamp: 's', documents: { [ID]: 'x' } });
    if (/library\/view\//.test(url)) {
      return reply({ ok: true, n: 5, truncated: false, digest: 'z1',
                     pages: [1, 2, 3, 4, 5].map((n) => '/paper/z-' + n + '.png'),
                     ink: JSON.parse(JSON.stringify(net.view)),
                     wiped: JSON.parse(JSON.stringify(net.wiped || {})),
                     build: { digest: 'z1', at: 1790000000, pages: 5 }, rebuilt: null });
    }
    if (/annotate\/save/.test(url)) {
      return net.save === 'down' ? Promise.reject(new Error('down')) : reply({ ok: true });
    }
    if (/library\/direction/.test(url) && net.hold) {
      // A send held in the air until the test lets it land.
      return new Promise((res) => { net.hold.land = () => res({ ok: true, json: () =>
        Promise.resolve({ ok: true, turn: 't0103', pages: [], kept: [], stripped: [],
                          images: [], detail: 'Your words went.',
                          ink: JSON.parse(JSON.stringify(net.view)) }) }); });
    }
    if (/library\/direction/.test(url)) {
      // The server's rule: a page the reader says it pictured for this send,
      // with the direction strokes it has now, is sent and stripped; any
      // other is kept.
      const body = JSON.parse((o && o.body) || '{}');
      net.pictured = body.pictured;
      const pictured = (body.pictured || []).filter((x) => (net.view[x.key] || [])
        .filter((y) => y.dir).length === x.n).map((x) => x.key);
      const dirs = Object.keys(net.view).filter((k) => net.view[k].some((x) => x.dir));
      const stripped = dirs.filter((k) => pictured.indexOf(k) >= 0);
      const kept = dirs.filter((k) => pictured.indexOf(k) < 0).map((k) => +k.split('/p')[1]);
      stripped.forEach((k) => {
        net.view[k] = net.view[k].filter((x) => !x.dir);
        if (!net.view[k].length) delete net.view[k];
      });
      return reply({ ok: true, turn: 't0102', pages: stripped.map((k) => +k.split('/p')[1]),
                     kept: kept, stripped: stripped, images: [],
                     detail: 'Your marks went as a proposed direction.',
                     ink: JSON.parse(JSON.stringify(net.view)) });
    }
    return new Promise(() => {});
  };
  w.addEventListener('error', (e) => fail('uncaught (lazy page): ' + e.message));
  for (const f of LIB_SCRIPTS) {
    try { w.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
    catch (e) { fail(f + ': ' + e.message); }
  }
  w.INK_RETRY_MS = 100000;
  w.STAMP_EVERY = 100000;
  w.PICTURE_WAIT_MS = 60;
  try { w.eval(fs.readFileSync(path.join(WEB, 'library.js'), 'utf8')); }
  catch (e) { fail('library.js (lazy page): ' + e.message); }
  await sleep(20);
  const click = (el) => el.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  const byId = (id) => D.getElementById(id);
  const A = w.Annotate;
  const kinds = (id) => JSON.stringify(A.kinds(id));
  const rect = (l, t, wd, ht) => ({ left: l, top: t, width: wd, height: ht,
                                    right: l + wd, bottom: t + ht, x: l, y: t });
  const fig = (n) => D.querySelector('.lib-page[data-page="' + n + '"]');
  const layer = (n) => fig(n).querySelector('canvas.ann-layer');
  const decodedPage = (n) => {
    const img = fig(n).querySelector('img');
    Object.defineProperty(img, 'naturalWidth', { configurable: true, value: 1240 });
    Object.defineProperty(img, 'naturalHeight', { configurable: true, value: 930 });
    fig(n).getBoundingClientRect = () => rect(50, 100 + (n - 1) * 700, 800, 600);
    img.getBoundingClientRect = () => rect(50, 100 + (n - 1) * 700, 800, 600);
  };
  /* A page as the browser holds it before its image arrives: no pixels and
     no height. `decodes` says whether asking for it eagerly brings it. */
  const lazyPage = (n, decodes) => {
    const img = fig(n).querySelector('img');
    fig(n).getBoundingClientRect = () => rect(50, 100 + (n - 1) * 700, 800, 0);
    img.getBoundingClientRect = () => rect(50, 100 + (n - 1) * 700, 800, 0);
    img.decode = () => {
      if (!decodes || img.getAttribute('loading') !== 'eager') return new Promise(() => {});
      decodedPage(n);
      return Promise.resolve();
    };
  };

  /* A page whose first decode is rejected -- switching lazy to eager started
     a new request -- and whose image then arrives: the send waits for its
     `load` and decodes it again. */
  const retryPage = (n) => {
    const img = fig(n).querySelector('img');
    fig(n).getBoundingClientRect = () => rect(50, 100 + (n - 1) * 700, 800, 0);
    img.getBoundingClientRect = () => rect(50, 100 + (n - 1) * 700, 800, 0);
    let asked = 0;
    img.decode = () => {
      asked += 1;
      if (asked === 1) {
        setTimeout(() => { decodedPage(n); img.dispatchEvent(new w.Event('load')); }, 10);
        return Promise.reject(new Error('EncodingError: a new request started'));
      }
      return Promise.resolve();
    };
    return () => asked;
  };

  click(D.querySelector('.lib-row .lib-name'));
  await sleep(30);
  decodedPage(1);
  decodedPage(2);
  lazyPage(3, true);
  lazyPage(4, false);
  const decodesOf5 = retryPage(5);
  A.redrawAll();
  const lazyAtFirst = fig(3).querySelector('img').getAttribute('loading') === 'lazy'
    && fig(4).querySelector('img').getAttribute('loading') === 'lazy';
  const flatAtFirst = layer(3)._h;
  const direct = byId('reader-direct');
  lazyAtFirst && !direct.hidden && direct.textContent === 'send directions · 3'
    ? ok('lazy: direction ink restored on pages never scrolled to is offered to send')
    : fail('lazy: pages 3, 4 load ' + fig(3).querySelector('img').getAttribute('loading')
           + '; the send reads ' + (direct.hidden ? 'hidden' : direct.textContent));

  log.length = 0;
  click(direct);
  click(byId('note-send'));
  await sleep(150);
  const dirPics = saves().filter((b) => b.png_kind === 'dir' && /^data:image\/png/.test(b.png || ''));
  fig(3).querySelector('img').getAttribute('loading') === 'eager'
    && fig(4).querySelector('img').getAttribute('loading') === 'eager'
    ? ok('lazy: the send asks for every page carrying direction ink at once')
    : fail('lazy: page 3 is ' + fig(3).querySelector('img').getAttribute('loading')
           + ', page 4 ' + fig(4).querySelector('img').getAttribute('loading'));
  dirPics.map((b) => b.card).sort().join('|') === key(3) + '|' + key(5)
    ? ok('lazy: the pages that decoded are pictured, and the one that never did is not')
    : fail('lazy: direction pictures were saved for ' + dirPics.map((b) => b.card).join(', '));
  decodesOf5() === 2
    ? ok('lazy: a decode rejected by the new request waits for the image and decodes once more')
    : fail('lazy: page 5 was decoded ' + decodesOf5() + ' times');
  JSON.stringify(net.pictured) === JSON.stringify([{ key: key(3), n: 1 }, { key: key(5), n: 1 }])
    ? ok('lazy: the send names the pages it pictured, each with its direction strokes then')
    : fail('lazy: the send named ' + JSON.stringify(net.pictured));
  flatAtFirst < 600 && layer(3)._h === 600
    ? ok('lazy: its layer is sized against the decoded page before the picture is made')
    : fail('lazy: page 3\'s layer was ' + flatAtFirst + ' tall and is ' + layer(3)._h);
  const at = (re) => log.findIndex((r) => re.test(r.url)
    && (!/annotate\/save/.test(r.url) || JSON.parse(r.opts.body || '{}').png_kind === 'dir'));
  at(/annotate\/save/) >= 0 && at(/library\/direction/) > at(/annotate\/save/)
    ? ok('lazy: and the picture is saved before the direction is asked')
    : fail('lazy: the order was ' + log.map((r) => r.url).join(' '));
  /1 page was not sent; send again/.test(byId('note-said').textContent)
    && !byId('note-send').disabled
    ? ok('lazy: the panel says the page left behind was not sent, and can send again')
    : fail('lazy: the panel says ' + JSON.stringify(byId('note-said').textContent)
           + (byId('note-send').disabled ? ' with the send dead' : ''));
  A.marked().indexOf(key(3)) < 0 && kinds(key(4)) === '{"fix":0,"dir":1}'
    && kinds(key(1)) === '{"fix":1,"dir":0}' && direct.textContent === 'send directions · 1'
    ? ok('lazy: the sent page leaves the glass, and the kept page\'s direction stays')
    : fail('lazy: after the send page 3 is ' + kinds(key(3)) + ', page 4 ' + kinds(key(4))
           + ', page 1 ' + kinds(key(1)) + '; the send reads ' + direct.textContent);
  D.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape' }));

  // ---- A STALE VIEW DOES NOT PUT BACK AN OLDER PAGE ----------------------
  // A stroke drawn on page 1 and saved; the view that comes back next was
  // read before that save landed, so it holds page 1 with one stroke.
  click(byId('reader-pen'));
  const pointer = (type, target, x, y) => {
    const e = new w.Event(type, { bubbles: true, cancelable: true });
    Object.defineProperties(e, {
      clientX: { value: x }, clientY: { value: y }, pointerType: { value: 'pen' },
      pointerId: { value: 9 }, pressure: { value: 0.5 },
    });
    target.dispatchEvent(e);
  };
  const r1 = fig(1).getBoundingClientRect();
  const cv1 = layer(1);
  pointer('pointerdown', cv1, r1.left + 200, r1.top + 400);
  for (let x = 220; x <= 400; x += 20) pointer('pointermove', cv1, r1.left + x, r1.top + 400);
  pointer('pointerup', w, r1.left + 400, r1.top + 400);
  await sleep(1300);
  const savedTwo = kinds(key(1)) === '{"fix":2,"dir":0}' && A.unsaved().indexOf(key(1)) < 0;
  net.view = { [key(1)]: [FIX], [key(4)]: [DIR] };
  click(D.querySelector('.lib-row .lib-name'));
  await sleep(40);
  savedTwo && kinds(key(1)) === '{"fix":2,"dir":0}' && kinds(key(4)) === '{"fix":0,"dir":1}'
    ? ok('lazy: a stale view of a page drawn on since leaves this device\'s newer copy')
    : fail('lazy: saved ' + savedTwo + '; after the stale view page 1 is ' + kinds(key(1)));
  net.view = { [key(4)]: [DIR] };
  click(D.querySelector('.lib-row .lib-name'));
  await sleep(40);
  A.marked().indexOf(key(1)) < 0
    ? ok('lazy: while a page the view no longer has is dropped')
    : fail('lazy: page 1 stayed after the view dropped it: ' + kinds(key(1)));

  // ---- A MIXED PAGE ACROSS A LANDED ROUND, THE READER LEFT OPEN ----------
  // Page 1 carries a delivered fix and a direction, saved. Page 2 the same,
  // and a new fix is drawn on it while the board is down, so it is owed. The
  // round lands: the view hands back each page's direction alone and names
  // the wiped fixes. The saved page is dropped and taken again; the owed page
  // keeps its new stroke and sheds the wiped one, so its save cannot write it
  // back.
  const F1 = { c: '#e0b45c', w: 2, pg: 1, p: [0.11, 0.21, 0.31, 0.21], pr: [0.5, 0.5] };
  const F2 = { c: '#e0b45c', w: 2, pg: 1, p: [0.12, 0.31, 0.42, 0.31], pr: [0.5, 0.5] };
  const D1 = { c: DIR_C, w: 2, pg: 1, dir: 1, p: [0.3, 0.7, 0.6, 0.7], pr: [0.5, 0.5] };
  const D2 = { c: DIR_C, w: 2, pg: 1, dir: 1, p: [0.3, 0.8, 0.6, 0.8], pr: [0.5, 0.5] };
  net.view = { [key(1)]: [F1, D1], [key(2)]: [F2, D2], [key(4)]: [DIR] };
  click(D.querySelector('.lib-row .lib-name'));
  await sleep(40);
  [1, 2, 3, 4, 5].forEach(decodedPage);
  A.redrawAll();
  if (A.kind()) click(byId('reader-mode'));     // the pen draws fixes
  net.save = 'down';
  const r2 = fig(2).getBoundingClientRect();
  const cv2 = layer(2);
  pointer('pointerdown', cv2, r2.left + 150, r2.top + 500);
  for (let x = 170; x <= 450; x += 20) pointer('pointermove', cv2, r2.left + x, r2.top + 500);
  pointer('pointerup', w, r2.left + 450, r2.top + 500);
  await sleep(1300);
  const owedBefore = A.unsaved().indexOf(key(2)) >= 0 && kinds(key(2)) === '{"fix":2,"dir":1}';
  net.view = { [key(1)]: [D1], [key(2)]: [D2], [key(4)]: [DIR] };
  net.wiped = { [key(1)]: [F1], [key(2)]: [F2] };
  click(D.querySelector('.lib-row .lib-name'));
  await sleep(40);
  const sig = (x) => JSON.stringify(x.p);
  const p2 = A.payload(key(2), false).strokes;
  owedBefore && kinds(key(1)) === '{"fix":0,"dir":1}'
    ? ok('lazy: a landed round\'s wiped fix leaves a saved mixed page, its direction kept')
    : fail('lazy: owed ' + owedBefore + '; page 1 after the landing is ' + kinds(key(1)));
  kinds(key(2)) === '{"fix":1,"dir":1}' && !p2.some((x) => sig(x) === sig(F2))
    && p2.some((x) => sig(x) === sig(D2)) && A.unsaved().indexOf(key(2)) >= 0
    ? ok('lazy: an owed mixed page sheds the wiped fix and keeps its new stroke, still owed')
    : fail('lazy: page 2 after the landing is ' + kinds(key(2)) + ': ' + JSON.stringify(p2));
  net.save = 'ok';
  log.length = 0;
  click(byId('reader-pen'));                    // done marking: the save goes
  await sleep(60);
  const p2saves = saves().filter((b) => b.card === key(2));
  const last2 = p2saves.length ? p2saves[p2saves.length - 1].strokes : [];
  p2saves.length && !last2.some((x) => sig(x) === sig(F2)) && last2.length === 2
    ? ok('lazy: and the save that follows does not write the wiped fix back')
    : fail('lazy: page 2 was saved as ' + JSON.stringify(last2));
  net.wiped = null;

  // ---- THE PEN WAITS WHILE A SEND IS IN THE AIR --------------------------
  click(byId('reader-pen'));                    // marking again
  const pen = byId('reader-pen');
  net.hold = {};
  click(direct);
  byId('note-text').value = 'one more thought';
  byId('note-text').dispatchEvent(new w.Event('input', { bubbles: true }));
  click(byId('note-send'));
  await sleep(30);
  const before3 = A.payload(key(2), false).strokes.length;
  pointer('pointerdown', cv2, r2.left + 150, r2.top + 300);
  for (let x = 170; x <= 450; x += 20) pointer('pointermove', cv2, r2.left + x, r2.top + 300);
  pointer('pointerup', w, r2.left + 450, r2.top + 300);
  const heldOff = !A.isOn() && pen.disabled && /sending/.test(pen.textContent);
  A.payload(key(2), false).strokes.length === before3 && heldOff
    ? ok('lazy: while a send is in the air the pen is off, says sending, and takes no stroke')
    : fail('lazy: during the send the pen is ' + (A.isOn() ? 'on' : 'off') + ', the button says '
           + JSON.stringify(pen.textContent) + (pen.disabled ? '' : ' and is live')
           + '; page 2 went from ' + before3 + ' to ' + A.payload(key(2), false).strokes.length);
  for (let i = 0; i < 50 && !net.hold.land; i++) await sleep(20);
  const landed = !!net.hold.land;
  if (landed) net.hold.land();
  net.hold = null;
  await sleep(30);
  if (!landed) fail('lazy: the held send never reached the board');
  A.isOn() && !pen.disabled && pen.textContent === '✎ done marking'
    ? ok('lazy: and once the reply lands the pen is back as it was')
    : fail('lazy: after the reply the pen is ' + (A.isOn() ? 'on' : 'off') + ' and says '
           + JSON.stringify(pen.textContent));
  D.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape' }));

  // ---- A WIPE IN THE LIST'S OWN REPLY ------------------------------------
  // The list can be the request a wipe happens in, with nothing moved that
  // would re-draw the reader; what it names comes off the glass all the same.
  LIB.documents[0].wiped = { [key(1)]: [D1] };
  pointer('pointerdown', cv2, r2.left + 150, r2.top + 200);
  for (let x = 170; x <= 450; x += 20) pointer('pointermove', cv2, r2.left + x, r2.top + 200);
  pointer('pointerup', w, r2.left + 450, r2.top + 200);
  await sleep(1400);
  A.marked().indexOf(key(1)) < 0
    ? ok('lazy: strokes the list names wiped leave the open reader too')
    : fail('lazy: after the list named it wiped page 1 is ' + kinds(key(1)));
  delete LIB.documents[0].wiped;
  click(byId('reader-close'));
}

/* ==========================================================================
   EDITS AND DIRECTIONS, EACH SENT ON ITS OWN. Asked as: "we know if ink
   corresponds to directions or edits because of the mode I was in at the
   time of making them. Give two different options to send in edits or to
   send in directions." So every stroke keeps the toggle it was drawn under
   (`dir: 1` on a direction), *say what is wrong* carries the edits and *send
   directions* the directions, each picture shows only its own kind, and a
   sent direction leaves the glass. On a DOM of its own, with real strokes
   drawn by the pen and a canvas that records the colours it paints.
   ========================================================================== */
async function inkHasAKind() {
  const ID = 'writeups-kinds-kinds';
  const P1 = 'doc/' + ID + '/p1';
  const P2 = 'doc/' + ID + '/p2';
  const P3 = 'doc/' + ID + '/p3';
  const OLD = { c: '#e8746c', w: 3, pg: 1, p: [0.1, 0.1, 0.3, 0.12], pr: [0.5, 0.5] };
  const FIX_C = '#e0b45c';
  const DIR_C = '#3366cc';
  const HALO = 'rgba(47,125,79,0.22)';
  const LIB = { workspace: 'research/TRD-EHR', writeups: 'writeups', documents: [{
    id: ID, dir: 'writeups/kinds', stem: 'kinds', title: 'A deck after the meeting',
    kind: 'deck', formats: ['pdf', 'tex'], rel: 'writeups/kinds/kinds.pdf',
    pages: 3, pdf: true, stale: false, iso: '2026-10-01', notes: [], made: 'board',
    marks: { pages: 1, strokes: 1, waiting: 1, dir: { pages: 2, strokes: 3 } },
  }] };
  const net = { save: 'ok', ink: {} };
  const log = [];
  const d = new JSDOM(LIB_HTML, { runScripts: 'outside-only', pretendToBeVisual: true,
                                 url: 'https://board.test/library' });
  const w = d.window;
  const D = w.document;
  /* A canvas that remembers every colour it stroked or filled with, and a
     picture of it that says which those were. */
  w.HTMLCanvasElement.prototype.getContext = function () {
    const cv = this;
    cv._ops = cv._ops || [];
    const st = { strokeStyle: '', fillStyle: '' };
    return new Proxy({}, {
      get: (o, k) => {
        if (k === 'stroke') return () => cv._ops.push(st.strokeStyle);
        if (k === 'fill') return () => cv._ops.push(st.fillStyle);
        return k in st ? st[k] : () => {};
      },
      set: (o, k, v) => { st[k] = v; return true; },
    });
  };
  w.HTMLCanvasElement.prototype.toDataURL = function () {
    return 'data:image/png;base64,'
      + Buffer.from(JSON.stringify(Array.from(new Set(this._ops || [])))).toString('base64');
  };
  const colours = (png) => {
    try { return JSON.parse(Buffer.from(String(png).split('base64,')[1], 'base64').toString()); }
    catch (e) { return null; }
  };
  w.Element.prototype.setPointerCapture = function () {};
  w.Element.prototype.releasePointerCapture = function () {};
  w.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  w.fetch = (u, o) => {
    const url = String(u);
    log.push({ url: url, opts: o || {} });
    const reply = (x) => Promise.resolve({ ok: true, json: () => Promise.resolve(x) });
    if (/library\.json/.test(url)) return reply(LIB);
    if (/library\/stamp/.test(url)) return reply({ ok: true, stamp: 's', documents: { [ID]: 'x' } });
    if (/library\/view\//.test(url)) {
      return reply({ ok: true, n: 3, truncated: false, digest: 'k1',
                     pages: ['/paper/k-1.png', '/paper/k-2.png', '/paper/k-3.png'],
                     ink: { [P1]: [OLD] }, build: { digest: 'k1', at: 1790000000, pages: 3 },
                     rebuilt: null });
    }
    if (/annotate\/save/.test(url)) {
      if (net.save === 'down') return Promise.reject(new TypeError('Failed to fetch'));
      return reply({ ok: true });
    }
    if (/library\/feedback/.test(url)) {
      return reply({ ok: true, rel: 'writeups/kinds/feedback/2026-10-01-v1.md', asked: true,
                     revise: 'board', detail: 'The tutor has been asked to revise it.' });
    }
    if (/library\/direction/.test(url)) {
      return reply({ ok: true, turn: 't0101', pages: [1, 3], images: [], kept: [],
                     stripped: net.stripped || [P1, P3],
                     detail: 'Your marks on pages 1, 3 went as a proposed direction.',
                     ink: net.ink });
    }
    return new Promise(() => {});
  };
  w.addEventListener('error', (e) => fail('uncaught (kinds page): ' + e.message));
  for (const f of LIB_SCRIPTS) {
    try { w.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
    catch (e) { fail(f + ': ' + e.message); }
  }
  w.INK_RETRY_MS = 100000;
  w.STAMP_EVERY = 100000;
  w.PICTURE_WAIT_MS = 20;
  try { w.eval(fs.readFileSync(path.join(WEB, 'library.js'), 'utf8')); }
  catch (e) { fail('library.js (kinds page): ' + e.message); }
  await sleep(20);
  const click = (el) => el.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  const byId = (id) => D.getElementById(id);
  const A = w.Annotate;

  /lib-marks/.test(D.querySelector('.lib-row').innerHTML)
    && /marked up on 1 page, 1 stroke, directions on 2 pages/.test(
      D.querySelector('.lib-row').textContent)
    ? ok('kinds: the row says how much of each kind of ink is on the document')
    : fail('kinds: the row reads ' + D.querySelector('.lib-row').textContent);

  click(D.querySelector('.lib-row .lib-name'));
  await sleep(30);
  const fig = (n) => D.querySelector('.lib-page[data-page="' + n + '"]');
  const rect = (l, t, wd, ht) => ({ left: l, top: t, width: wd, height: ht,
                                    right: l + wd, bottom: t + ht, x: l, y: t });
  [1, 2, 3].forEach((n) => {
    const f = fig(n);
    const img = f.querySelector('img');
    Object.defineProperty(img, 'naturalWidth', { configurable: true, value: 1240 });
    Object.defineProperty(img, 'naturalHeight', { configurable: true, value: 930 });
    Object.defineProperty(img, 'complete', { configurable: true, value: true });
    f.getBoundingClientRect = () => rect(50, 100 + (n - 1) * 700, 800, 600);
    img.getBoundingClientRect = () => rect(50, 100 + (n - 1) * 700, 800, 600);
  });
  A.redrawAll();
  click(byId('reader-pen'));
  function pointer(type, target, x, y) {
    const e = new w.Event(type, { bubbles: true, cancelable: true });
    Object.defineProperties(e, {
      clientX: { value: x }, clientY: { value: y }, pointerType: { value: 'pen' },
      pointerId: { value: 7 }, pressure: { value: 0.5 },
    });
    target.dispatchEvent(e);
  }
  /* A stroke through page fractions, the way the Pencil leaves one. */
  async function drawOn(n, fracs) {
    const r = fig(n).getBoundingClientRect();
    const at = fracs.map(([fx, fy]) => [r.left + fx * r.width, r.top + fy * r.height]);
    const cv = fig(n).querySelector('canvas.ann-layer');
    pointer('pointerdown', cv, at[0][0], at[0][1]);
    for (let i = 1; i < at.length; i++) pointer('pointermove', cv, at[i][0], at[i][1]);
    pointer('pointerup', w, at[at.length - 1][0], at[at.length - 1][1]);
    await sleep(15);
  }
  const line = (y) => [0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6].map((x) => [x, y]);
  const kinds = (id) => JSON.stringify(A.kinds(id));
  const mode = byId('reader-mode');
  const direct = byId('reader-direct');

  A.kind() === null && /fixes/.test(mode.textContent) && direct.hidden
    ? ok('kinds: a document opens drawing edits, with no directions to send')
    : fail('kinds: opened as ' + mode.textContent + ', kind ' + A.kind()
           + ', send directions ' + (direct.hidden ? 'hidden' : 'shown'));

  A.setPen(FIX_C, 2);
  await drawOn(2, line(0.5));
  const p2drawn = A.payload(P2, false).strokes;
  p2drawn.length === 1 && !('dir' in p2drawn[0])
    ? ok('kinds: a stroke drawn while the toggle says fixes carries no kind')
    : fail('kinds: the fix stroke saved as ' + JSON.stringify(p2drawn));

  click(mode);
  A.kind() === 'dir' && !direct.hidden && direct.textContent === 'send directions'
    && byId('reader-say').textContent === 'say what is wrong'
    ? ok('kinds: the toggle sets the kind of new ink, shows the directions\' own send, '
         + 'and leaves the edits\' send as it was')
    : fail('kinds: after the toggle: kind ' + A.kind() + ', ' + direct.textContent
           + ' / ' + byId('reader-say').textContent);

  A.setPen(DIR_C, 2);
  await drawOn(1, line(0.5));
  const p1drawn = A.payload(P1, false).strokes;
  p1drawn.length === 2 && p1drawn[1].dir === 1 && !('dir' in p1drawn[0])
    ? ok('kinds: a stroke drawn after the toggle is saved as a direction, the ink '
         + 'before it untouched')
    : fail('kinds: page 1 saves as ' + JSON.stringify(p1drawn));
  JSON.stringify(p1drawn[0]) === JSON.stringify(OLD)
    ? ok('kinds: ink from before kinds existed is saved back byte for byte, a fix')
    : fail('kinds: the old stroke came back as ' + JSON.stringify(p1drawn[0]));
  direct.textContent === 'send directions · 1'
    ? ok('kinds: the directions\' send counts the pages carrying them')
    : fail('kinds: the send reads ' + direct.textContent);
  const ops1 = fig(1).querySelector('canvas.ann-layer')._ops || [];
  const ops2 = fig(2).querySelector('canvas.ann-layer')._ops || [];
  ops1.indexOf(HALO) >= 0 && ops2.indexOf(HALO) < 0 && ops2.indexOf(FIX_C) >= 0
    ? ok('kinds: a direction is drawn over a green halo on the glass, and a fix is not')
    : fail('kinds: page 1 painted ' + JSON.stringify(Array.from(new Set(ops1)))
           + ', page 2 ' + JSON.stringify(Array.from(new Set(ops2))));

  await drawOn(3, line(0.5));
  // The rubber across the middle of page 1's direction: two pieces, still directions.
  A.setTool('erase');
  await drawOn(1, [[0.4, 0.4], [0.4, 0.45], [0.4, 0.5], [0.4, 0.55], [0.4, 0.6]]);
  A.setTool('pen');
  kinds(P1) === '{"fix":1,"dir":2}'
    ? ok('kinds: the pieces an erase leaves of a direction are directions')
    : fail('kinds: after the erase page 1 is ' + kinds(P1));

  click(mode);
  A.undo();
  const undone = kinds(P1);
  A.redo();
  undone === '{"fix":1,"dir":1}' && kinds(P1) === '{"fix":1,"dir":2}'
    ? ok('kinds: undo and redo after the toggle bring back the kinds the ink was drawn as')
    : fail('kinds: undo gave ' + undone + ', redo ' + kinds(P1));
  !direct.hidden && direct.textContent === 'send directions · 2'
    ? ok('kinds: back on edits, the directions\' send stays while directions are on the glass')
    : fail('kinds: on edits with directions drawn, the send reads '
           + (direct.hidden ? 'hidden' : direct.textContent));

  // A loop round page 3's direction, then a drag of it: still a direction.
  A.setTool('lasso');
  await drawOn(3, [[0.15, 0.4], [0.65, 0.4], [0.65, 0.6], [0.15, 0.6], [0.15, 0.42]]);
  const picked = A.picked();
  await drawOn(3, [[0.4, 0.5], [0.4, 0.53], [0.4, 0.56]]);
  const moved = A.payload(P3, false).strokes;
  picked === 1 && moved.length === 1 && moved[0].dir === 1 && moved[0].p[1] > 0.52
    ? ok('kinds: a direction moved with the loop is still a direction')
    : fail('kinds: picked ' + picked + ', page 3 after the move ' + JSON.stringify(moved));
  // Copied and pasted: a paste keeps the kind it was drawn as, whatever the
  // toggle says now. A direction pasted while drawing edits is a direction.
  A.copy();
  const clipped = w.InkClip.get();
  A.paste();
  const pastedOnEdits = kinds(P3);
  click(mode);
  A.paste();
  const pastedOnDirs = kinds(P3);
  A.undo();
  A.undo();
  A.deselect();
  clipped && clipped.strokes.length === 1 && clipped.strokes[0].dir === 1
    && pastedOnEdits === '{"fix":0,"dir":2}' && pastedOnDirs === '{"fix":0,"dir":3}'
    && kinds(P3) === '{"fix":0,"dir":1}'
    ? ok('kinds: a direction copied and pasted is a direction, with the toggle on edits or on directions')
    : fail('kinds: the clip ' + JSON.stringify(clipped && clipped.strokes.map((x) => x.dir))
           + ', pasted on edits ' + pastedOnEdits + ', on directions ' + pastedOnDirs
           + ', after undo ' + kinds(P3));
  // And an edit cut from page 2 and pasted back while drawing directions is
  // still an edit.
  await drawOn(2, [[0.15, 0.4], [0.65, 0.4], [0.65, 0.6], [0.15, 0.6], [0.15, 0.42]]);
  const cutN = A.cut();
  const afterCut = kinds(P2);
  A.paste();
  const p2pasted = A.payload(P2, false).strokes;
  A.deselect();
  A.setTool('pen');
  A.kind() === 'dir' && cutN === 1 && afterCut === '{"fix":0,"dir":0}'
    && p2pasted.length === 1 && !('dir' in p2pasted[0])
    ? ok('kinds: an edit cut and pasted while the toggle says directions is still an edit')
    : fail('kinds: cut ' + cutN + ' leaving ' + afterCut + ', page 2 after the paste '
           + JSON.stringify(p2pasted) + ', toggle ' + A.kind());
  await sleep(1100);

  // ---- THE EDITS GO, AND ONLY THE EDITS --------------------------------
  click(byId('reader-say'));
  !byId('ask-revise').hidden && !byId('ask-rework').hidden && byId('ask-direction').hidden
    ? ok('kinds: say what is wrong opens the fix panel though the toggle says directions')
    : fail('kinds: say what is wrong in directions mode opened the direction panel');
  log.length = 0;
  click(byId('note-send'));
  await sleep(60);
  const pics = (k) => log.filter((r) => /annotate\/save/.test(r.url))
    .map((r) => JSON.parse(r.opts.body || '{}'))
    .filter((b) => /^data:image\/png/.test(b.png || '') && (b.png_kind || 'fix') === k);
  const fixPics = pics('fix');
  const fp1 = fixPics.filter((b) => b.card === P1)[0];
  fixPics.map((b) => b.card).sort().join('|') === [P1, P2].join('|') && !pics('dir').length
    ? ok('kinds: the edits\' pictures are saved for the pages with edits on them, and '
         + 'a page of directions alone is left out')
    : fail('kinds: the fix send saved pictures for ' + fixPics.map((b) => b.card).join(', ')
           + ' and ' + pics('dir').length + ' direction pictures');
  fp1 && JSON.stringify(colours(fp1.png)) === JSON.stringify([OLD.c])
    ? ok('kinds: and a page carrying both shows the edits alone, with no halo')
    : fail('kinds: page 1\'s fix picture painted ' + JSON.stringify(fp1 && colours(fp1.png)));
  log.some((r) => /library\/feedback/.test(r.url)) && !log.some((r) => /library\/direction/.test(r.url))
    ? ok('kinds: and the edits go as a revision, never as a direction')
    : fail('kinds: the fix send asked ' + log.map((r) => r.url).join(' '));
  D.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape' }));

  // ---- THE DIRECTIONS GO, AND ONLY THE DIRECTIONS ----------------------
  // The server takes the sent directions off their pages and hands back what
  // is left; page 2's one edit is what this device already has.
  net.ink = { [P1]: [OLD], [P2]: [{ c: FIX_C, w: 2, pg: 1, p: [0.2, 0.5, 0.6, 0.5] }] };
  log.length = 0;
  click(direct);
  !byId('ask-direction').hidden && byId('ask-revise').hidden && byId('ask-rework').hidden
    && /propose it/.test(byId('note-send').textContent) && !byId('note-send').disabled
    && /direction marks on 2 pages/.test(byId('note-marks').textContent)
    ? ok('kinds: send directions opens the direction panel, live on the direction ink alone')
    : fail('kinds: the direction panel: ' + byId('note-marks').textContent + ' / '
           + byId('note-send').textContent);
  click(byId('note-send'));
  await sleep(60);
  const dirPics = pics('dir');
  const dp1 = dirPics.filter((b) => b.card === P1)[0];
  dirPics.map((b) => b.card).sort().join('|') === [P1, P3].join('|') && !pics('fix').length
    ? ok('kinds: the directions\' pictures are saved as directions, for the pages carrying them')
    : fail('kinds: the direction send saved pictures for '
           + dirPics.map((b) => b.card).join(', ') + ' and ' + pics('fix').length + ' fix ones');
  dp1 && JSON.stringify(colours(dp1.png)) === JSON.stringify([DIR_C])
    ? ok('kinds: and a page carrying both shows the directions alone')
    : fail('kinds: page 1\'s direction picture painted ' + JSON.stringify(dp1 && colours(dp1.png)));
  const dpost = log.filter((r) => /library\/direction/.test(r.url))[0];
  dpost && JSON.parse(dpost.opts.body).page === 0
    && !log.some((r) => /library\/feedback/.test(r.url))
    ? ok('kinds: the directions go to /library/direction, every page of them, and no revision')
    : fail('kinds: the direction send asked ' + log.map((r) => r.url).join(' '));
  kinds(P1) === '{"fix":1,"dir":0}' && A.marked().indexOf(P3) < 0
    && kinds(P2) === '{"fix":1,"dir":0}'
    ? ok('kinds: sent directions leave the glass, and the edits beside them stay')
    : fail('kinds: after the send: page 1 ' + kinds(P1) + ', page 2 ' + kinds(P2)
           + ', marked ' + A.marked().join(','));
  direct.textContent === 'send directions'
    ? ok('kinds: and the send says nothing is left to send')
    : fail('kinds: after the send it reads ' + direct.textContent);
  D.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape' }));

  // ---- WHAT THE SERVER HANDS BACK ---------------------------------------
  // Page 2 drawn on again while the board is down: still owed, so a reply
  // naming it stripped leaves it alone. Page 1 is saved and named, so the
  // reply's two strokes replace its one.
  net.save = 'down';
  await drawOn(2, line(0.7));
  net.ink = { [P1]: [OLD, { c: FIX_C, w: 2, pg: 1, p: [0.1, 0.8, 0.3, 0.8] }],
              [P2]: [{ c: FIX_C, w: 2, pg: 1, p: [0.2, 0.5, 0.6, 0.5] }] };
  net.stripped = [P1, P2];
  click(direct);
  click(byId('note-send'));
  await sleep(80);
  kinds(P1) === '{"fix":2,"dir":0}' && kinds(P2) === '{"fix":1,"dir":1}'
    ? ok('kinds: a reply replaces the saved pages it names stripped and leaves an owed one alone')
    : fail('kinds: after the reply page 1 is ' + kinds(P1) + ', page 2 ' + kinds(P2));
  net.save = 'ok';
  net.stripped = null;
  D.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape' }));

  click(mode);
  A.undo();
  A.kind() === null && direct.hidden
    ? ok('kinds: back on edits with no directions on the glass, there is no directions\' send')
    : fail('kinds: on edits with nothing to send, it is ' + (direct.hidden ? 'hidden' : 'shown')
           + ' and the kind is ' + A.kind());

  // ---- ONE DRAFT PER SEND ------------------------------------------------
  click(mode);
  click(direct);
  byId('note-text').value = 'Dr. Paulus: try the MDD-only cohort.';
  byId('note-text').dispatchEvent(new w.Event('input', { bubbles: true }));
  D.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape' }));
  click(byId('reader-say'));
  byId('note-text').value === ''
    ? ok('kinds: words typed for a direction never come back in the fix panel')
    : fail('kinds: the fix panel opened with ' + JSON.stringify(byId('note-text').value));
  byId('note-text').value = 'Slide 4 has the old n.';
  byId('note-text').dispatchEvent(new w.Event('input', { bubbles: true }));
  D.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape' }));
  click(direct);
  /Paulus/.test(byId('note-text').value)
    ? ok('kinds: and the direction panel has its own')
    : fail('kinds: the direction panel opened with ' + JSON.stringify(byId('note-text').value));
  click(byId('note-send'));
  await sleep(60);
  D.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape' }));
  click(byId('reader-say'));
  byId('note-text').value === 'Slide 4 has the old n.'
    && !w.localStorage.getItem('library.draft-dir:' + ID)
    ? ok('kinds: a direction sent drops its own draft and leaves the fix draft')
    : fail('kinds: after the direction went the fix panel reads '
           + JSON.stringify(byId('note-text').value));
  D.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape' }));

  click(byId('reader-close'));
  A.kind() === null
    ? ok('kinds: closing the reader puts the pen back to edits')
    : fail('kinds: the pen still draws ' + A.kind() + ' after the reader closed');
}

/* ==========================================================================
   A ROUND AS PAIRS: what was written, and what was done -- with a pip on the
   page for each.

   Asked as: "I need some nifty way to keep track of what each edit request
   was, and what was done to address it", and then, once a round was answered
   and its ink was still drawn over the revision: "Think of a slicker feature
   to show the most recent round of feedback and corresponding revision, where
   when I tap on each such pair ... it'll take me to that part of the paper."
   So an answered round's ink leaves the page for a panel, a pair to a row; a
   numbered pip marks each on the page; a row tap zooms and scrolls to its
   place, flashes the revision and lays a ghost of the ink over it; and each
   pair is fine or not fixed. On a DOM of its own, so what it asks for is the
   only thing in its list.
   ========================================================================== */
async function changesArePins() {
  const ID = 'writeups-led-led';
  const LIB = { workspace: 'research/TRD-EHR', writeups: 'writeups', documents: [{
    id: ID, dir: 'writeups/led', stem: 'led', title: 'A paper with requests',
    kind: 'paper', formats: ['pdf', 'tex'], rel: 'writeups/led/led.pdf',
    pages: 2, pdf: true, stale: false, iso: '2026-09-29', made: 'board',
    notes: [{ name: '2026-09-29-v1.md', day: '2026-09-29', v: 1 },
            { name: '2026-09-30-v1.md', day: '2026-09-30', v: 1 }],
    marks: { pages: 1, strokes: 3, waiting: 1 },
    ledger: { rounds: 2, items: 6, open: 4, reopened: 0 },
  }] };
  const ans = (d, did, oldw, neww) => ({ disposition: d, did: did, old: oldw || '',
                                         new: neww || '', old_from: 'before', by: 'turn' });
  const S = { c: '#e8746c', w: 3, pg: 1, p: [0.1, 0.3, 0.3, 0.32] };
  const row = (o) => Object.assign({ kind: 'ink', text: '', why: '', previous: '', count: 1,
    crop: '', marked: '', status: 'answered', problems: [], state: 'open', state_why: '',
    carried: '', ink: null, ink_at: null, at: null, diff: null, reply: '', gone: false }, o);
  const LEDGER = { ok: true, document: ID, digest: 'd1',
    summary: { rounds: 2, items: 6, open: 4, reopened: 0 },
    rounds: [{ note: '2026-09-30-v1.md', round: 2, filed: '2026-09-30 17:00',
      ask: 'revise', landed: true, answered: 3, open: 3, judged: 1, done: false,
      extra: [], unknown: [], items: [
        row({ id: 'R2.1', n: 2, page: 2, count: 2,
          crop: '/library/evidence/' + ID + '/2026-09-30-v1.md/R2.1.svg',
          answer: ans('done', 'Said considered.', 'was significant', 'was considered significant'),
          placed: { page: 2, box: [0.12, 0.30, 0.60, 0.34], by: 'text', score: 1 },
          at: { page: 2, y: 0.30, box: [0.12, 0.30, 0.60, 0.34], by: 'answer' },
          ink: { page: 2, box: [0.1, 0.3, 0.3, 0.32], strokes: [S], drawn_on: 'd0' },
          ink_at: { by: 'text', page: 2, box: [0.1, 0.31, 0.3, 0.33], dx: 0.02, dy: 0.01 },
          diff: [['=', 'the model was'], ['+', 'considered'], ['=', 'significant']] }),
        row({ id: 'R2.2', n: 1, kind: 'text', page: 1, count: 0, text: 'The abstract overclaims.',
          answer: ans('pushed back', 'The claim is the paper’s result, so it stays.'),
          reply: 'The claim is the paper’s result, so it stays.',
          placed: { page: 1, box: [0.1, 0.5, 0.5, 0.53], by: 'text', score: 0.8 },
          at: { page: 1, y: 0.5, box: [0.1, 0.5, 0.5, 0.53], by: 'answer' } }),
        row({ id: 'R2.3', n: 3, page: 2, state: 'accepted',
          answer: ans('done', 'Cut it.', 'An old line.', ''),
          at: { page: 2, y: 0.7, box: [0.1, 0.7, 0.5, 0.72], by: 'answer' },
          diff: [['-', 'An old line.']] }),
        row({ id: 'R2.4', n: 4, page: 2, status: 'not answered', answer: null,
          ink: { page: 2, box: [0.6, 0.8, 0.8, 0.85], strokes: [S], drawn_on: 'd1' },
          ink_at: { by: 'same', page: 2, box: [0.6, 0.8, 0.8, 0.85], dx: 0, dy: 0 },
          at: { page: 2, y: 0.8, box: [0.6, 0.8, 0.8, 0.85], by: 'ink' } }),
        row({ id: 'R2.5', n: 5, page: 1, answer: ans('done', 'Rewrote it.', 'a', 'b'),
          ink: { page: 1, box: [0.1, 0.1, 0.2, 0.2], strokes: [S], drawn_on: 'd0' },
          ink_at: { by: 'gone' }, gone: true, diff: [['-', 'a'], ['+', 'b']] }),
      ] },
      { note: '2026-09-29-v1.md', round: 1, filed: '2026-09-29 17:00', ask: 'revise',
        landed: true, answered: 1, open: 0, judged: 1, done: true, extra: [], unknown: [],
        items: [row({ id: 'R1.1', n: 1, page: 1, state: 'accepted',
          answer: ans('done', 'Fixed.', 'x', 'y'), diff: [['-', 'x'], ['+', 'y']],
          at: { page: 1, y: 0.2, box: [0.1, 0.2, 0.3, 0.22], by: 'answer' } })] }] };
  const asked = [];
  const d = new JSDOM(LIB_HTML, { runScripts: 'outside-only', pretendToBeVisual: true,
                                 url: 'https://board.test/library' });
  const w = d.window;
  const D = w.document;
  w.HTMLCanvasElement.prototype.getContext = () =>
    new Proxy({}, { get: () => () => {}, set: () => true });
  w.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
  w.Element.prototype.setPointerCapture = function () {};
  w.Element.prototype.releasePointerCapture = function () {};
  w.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  // THE GEOMETRY OF THE GLASS, so a jump can be measured: the scroller's
  // window, each page a 800 x 1000 box stacked under the last, and the panel
  // as a sheet whose top edge is at 500.
  const rect = (l, t, wd, h) => ({ left: l, top: t, width: wd, height: h, right: l + wd,
                                   bottom: t + h, x: l, y: t });
  w.HTMLElement.prototype.getBoundingClientRect = function () {
    if (this.id === 'reader-pages') return rect(0, 100, 800, 600);
    if (this.id === 'lg-panel') return rect(0, 500, 800, 300);
    if (this.classList && this.classList.contains('lib-page')) {
      const top = 100 + (+this.dataset.page - 1) * 1000 - (scrolled.top || 0);
      return rect(0, top, 800, 1000);
    }
    return rect(0, 0, 0, 0);
  };
  const scrolled = { top: 0, left: 0 };
  w.HTMLImageElement.prototype.__defineGetter__('naturalWidth', () => 1240);
  w.HTMLImageElement.prototype.__defineGetter__('naturalHeight', () => 1754);
  const json = (o) => Promise.resolve({ ok: true, json: () => Promise.resolve(o) });
  w.fetch = (u, opts) => {
    const url = String(u);
    asked.push({ url: url, body: (opts && opts.body) || '' });
    if (/library\.json/.test(url)) return json(LIB);
    if (/library\/stamp/.test(url)) return json({ ok: true, stamp: 's', documents: { [ID]: 'x' } });
    if (/library\/view\//.test(url)) {
      return json({ ok: true, n: 2, truncated: false, digest: 'd1',
                    pages: ['/paper/d1-1.png', '/paper/d1-2.png'], ink: {},
                    build: { digest: 'd1', at: 1790000000, pages: 2 }, rebuilt: null });
    }
    if (/library\/ledger\/preview/.test(url)) {
      const body = JSON.parse(opts.body || '{}');
      const one = (body.merge || []).indexOf(2) >= 0;
      return json({ ok: true, items: (one
        ? [{ id: 'R3.1', kind: 'ink', page: 2, count: 3, text: '', together: 1, merged: true }]
        : [{ id: 'R3.1', kind: 'ink', page: 2, count: 2, text: '', together: 2, merged: false },
           { id: 'R3.2', kind: 'ink', page: 2, count: 1, text: '', together: 2, merged: false }])
        .concat(body.text ? [{ id: 'R3.' + (one ? 2 : 3), kind: 'text', page: 0, count: 0,
                               text: body.text, together: 0, merged: false }] : []) });
    }
    if (/library\/ledger\/state/.test(url)) {
      const body = JSON.parse(opts.body || '{}');
      return json({ ok: true, id: body.id, state: body.state, why: body.why });
    }
    if (/library\/ledger\//.test(url)) return json(LEDGER);
    if (/library\/feedback/.test(url)) {
      return json({ ok: true, rel: 'writeups/led/feedback/2026-09-30-v2.md', revise: 'board',
                    asked: true, items: 2, ids: ['R3.1', 'R3.2'], detail: 'Asked.' });
    }
    if (/annotate\/save/.test(url)) return json({ ok: true });
    return new Promise(() => {});
  };
  w.addEventListener('error', (e) => fail('uncaught (ledger page): ' + e.message));
  for (const f of LIB_SCRIPTS) {
    try { w.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
    catch (e) { fail(f + ': ' + e.message); }
  }
  w.STAMP_EVERY = 100000;
  w.PICTURE_WAIT_MS = 20;
  w.SPLIT_WAIT = 5;
  try { w.eval(fs.readFileSync(path.join(WEB, 'library.js'), 'utf8')); }
  catch (e) { fail('library.js (ledger page): ' + e.message); }
  const pagesEl = D.getElementById('reader-pages');
  Object.defineProperty(pagesEl, 'scrollTop', { get: () => scrolled.top,
                                                set: (v) => { scrolled.top = v; } });
  Object.defineProperty(pagesEl, 'scrollLeft', { get: () => scrolled.left,
                                                 set: (v) => { scrolled.left = v; } });
  await sleep(20);
  const click = (el) => el.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));

  LIB_SCRIPTS.includes('ledger.js')
    && /src="\/static\/ledger\.js"/.test(fs.readFileSync(path.join(WEB, 'meeting.html'), 'utf8'))
    ? ok('ledger: the library reader and the meeting deck both load ledger.js')
    : fail('ledger.js is not loaded by both readers');
  const sw = fs.readFileSync(path.join(WEB, 'sw.js'), 'utf8');
  /"\/static\/ledger\.js"/.test(sw) && /"\/static\/ledger\.css"/.test(sw)
    && /href="\/static\/ledger\.css"/.test(LIB_HTML)
    ? ok('ledger: the library loads ledger.css, and the offline shell carries both')
    : fail('ledger.css is not loaded, or sw.js does not precache ledger.js and ledger.css');

  const rowBtn = D.querySelector('.lib-ledger');
  rowBtn && /4 of 6 requests open/.test(rowBtn.textContent)
    ? ok('ledger: a document’s row says how many requests are still open')
    : fail('the row does not count open requests: ' + (rowBtn && rowBtn.textContent));

  click(rowBtn);
  await sleep(40);
  asked.some((r) => r.url === '/library/ledger/' + ID)
    ? ok('ledger: the round is asked for by the document id')
    : fail('the ledger was never asked for: ' + asked.map((r) => r.url).join(' '));
  const chip = D.getElementById('reader-changes');
  const panel = D.getElementById('lg-panel');
  /Round 2 · 1 open|Round 2 · 3 open/.test(chip.textContent) && !chip.hidden
    ? ok('ledger: the chip names the round and how many of its pairs are open')
    : fail('the chip says ' + chip.textContent);
  !panel.hidden
    ? ok('ledger: “see the changes” opens the panel')
    : fail('the panel did not open from the row');

  // THE PIPS.
  const pip = (id) => D.querySelector('.lg-pip[data-id="' + id + '"]');
  const pips = Array.prototype.slice.call(D.querySelectorAll('#reader-pages .lg-pip'));
  pips.length === 3 && pips.every((p) => p.parentNode.classList.contains('lib-page'))
    ? ok('ledger: one pip per open placed pair, inside its page box')
    : fail(pips.length + ' pips: ' + pips.map((p) => p.dataset.id).join(','));
  pip('R2.1') && pip('R2.1').parentNode.dataset.page === '2' && parseFloat(pip('R2.1').style.top) === 30
    && pip('R2.2').parentNode.dataset.page === '1' && pip('R2.2').textContent === '1'
    && pip('R2.1').textContent === '2' && pip('R2.4').textContent === '4'
    ? ok('ledger: each pip is at its pair’s height in % of the page, numbered in document order')
    : fail('the pips are in the wrong places or numbered wrong');
  !pip('R2.3') && !pip('R2.5')
    ? ok('ledger: a pair said fine has no pip, and nor does one with nowhere to be')
    : fail('an accepted or unplaced pair has a pip');
  D.querySelectorAll('#reader-pages .lg-mark').length === 0
    ? ok('ledger: the revised passages are not boxed until a pair is selected')
    : fail('boxes are drawn with nothing selected');
  const fulls = D.querySelectorAll('#reader-pages .lg-ghost.lg-full');
  fulls.length === 1 && fulls[0].dataset.id === 'R2.4'
    ? ok('ledger: ink nothing answered stays on the page at full strength, from the archive')
    : fail(fulls.length + ' full-strength ghosts');

  // THE ROWS.
  const ids = Array.prototype.map.call(D.querySelectorAll('#lg-panel .lg-row'),
                                       (r) => r.dataset.id).join(',');
  ids === 'R2.2,R2.1,R2.3,R2.4,R2.5'
    ? ok('ledger: the panel lists the pairs in document order, the numbers the pips carry')
    : fail('the rows are ' + ids);
  const r21 = D.querySelector('.lg-row[data-id="R2.1"]');
  r21.querySelector('img.lg-crop') && r21.querySelector('img.lg-crop').loading === 'lazy'
    && r21.querySelector('.lg-diff ins') && r21.querySelector('.lg-diff ins').textContent === 'considered'
    ? ok('ledger: a row is the ink as drawn over the revision, insertions marked')
    : fail('the R2.1 row lacks its crop or its diff');
  /Pushed back/.test(D.querySelector('.lg-row[data-id="R2.2"] .lg-reply').textContent)
    && D.querySelector('.lg-row[data-id="R2.2"] .lg-quote').textContent === 'The abstract overclaims.'
    ? ok('ledger: a typed request shows its words, and a reply rather than an edit says so')
    : fail('the R2.2 row does not show its reply');
  /no longer in the document/.test(D.querySelector('.lg-row[data-id="R2.5"]').textContent)
    ? ok('ledger: a pair whose words vanished says so plainly')
    : fail('the vanished pair says nothing');
  /Round 1 done · 1 note/.test(D.querySelector('#lg-panel .lg-rounds').textContent)
    ? ok('ledger: an earlier finished round is one line, still browsable')
    : fail('the other rounds read: ' + D.querySelector('#lg-panel .lg-rounds').textContent);

  // A PIP OPENS ITS ROW; A ROW BRINGS ITS PLACE ONTO THE GLASS.
  click(D.querySelector('#lg-panel .lg-x'));
  panel.hidden
    ? ok('ledger: the panel closes')
    : fail('the panel did not close');
  w.Annotate.isOn = () => true;
  click(pip('R2.2'));
  panel.hidden
    ? ok('ledger: with the pen out a pip is not a button under the nib')
    : fail('a pip opened the panel with the pen on');
  w.Annotate.isOn = () => false;
  scrolled.top = 0;
  click(pip('R2.2'));
  !panel.hidden && D.querySelector('.lg-row.lg-sel').dataset.id === 'R2.2' && scrolled.top === 0
    ? ok('ledger: a pip opens the panel at its row and leaves the page where it is')
    : fail('the pip opened ' + (D.querySelector('.lg-row.lg-sel') || {}).dataset);
  click(D.querySelector('.lg-row[data-id="R2.1"] .lg-hit'));
  const zoomNow = parseFloat(pagesEl.style.getPropertyValue('--zoom'));
  zoomNow === 1.25
    ? ok('ledger: a row tap brings the zoom up to 125%')
    : fail('the zoom after a jump is ' + zoomNow);
  // page 2's box from y 0.30 to 0.34 of a page whose top is at 1100: its
  // middle at 1420, put in the middle of 100..500, what the sheet leaves.
  scrolled.top === 1420 - 300
    ? ok('ledger: and scrolls the pair to the middle of what the panel leaves of the glass')
    : fail('the jump scrolled to ' + scrolled.top);
  const marks = D.querySelectorAll('#reader-pages .lg-mark');
  marks.length === 1 && marks[0].classList.contains('lg-flash')
    && marks[0].parentNode.dataset.page === '2' && parseFloat(marks[0].style.top) === 30
    ? ok('ledger: the revised passage is boxed and flashed')
    : fail(marks.length + ' marks after a jump');
  const faint = D.querySelectorAll('#reader-pages .lg-ghost.lg-faint');
  const g = faint[0];
  faint.length === 1 && g.getAttribute('viewBox') === '0 0 1240 1754.0'
    && g.parentNode.dataset.page === '2'
    && g.querySelector('g').getAttribute('transform') === 'translate(24.8 17.5)'
    && g.querySelector('polyline').getAttribute('stroke-width') === '3'
    ? ok('ledger: and exactly one ghost of the ink, in page units, shifted as its words moved')
    : fail('the ghost: ' + (g ? g.outerHTML.slice(0, 200) : 'none'));
  const before = [pip('R2.1').style.top, g.getAttribute('viewBox'),
                  g.querySelector('g').getAttribute('transform')].join('|');
  w.zoomer.set(2);
  w.ledger.redraw();
  const g2 = D.querySelector('#reader-pages .lg-ghost.lg-faint');
  [pip('R2.1').style.top, g2.getAttribute('viewBox'),
   g2.querySelector('g').getAttribute('transform')].join('|') === before
    ? ok('ledger: at 200% the pip’s top and the ghost’s frame are the same fractions: no pixels')
    : fail('the zoom moved the pip or the ghost');
  click(D.querySelector('.lg-row[data-id="R2.1"] .lg-hit'));
  !D.querySelector('#reader-pages .lg-ghost.lg-faint') && !D.querySelector('#reader-pages .lg-mark')
    ? ok('ledger: deselecting the pair takes its ghost and its box away')
    : fail('the ghost outlived its pair');

  // FINE, AND NOT FIXED.
  click(D.querySelector('.lg-row[data-id="R2.4"] .lg-hit'));
  asked.length = 0;
  const backBtn = () => D.querySelector('.lg-row.lg-sel .lg-back-btn');
  click(backBtn());
  click(backBtn());
  !asked.filter((r) => /ledger\/state/.test(r.url)).length
    && /what is still wrong/i.test(D.querySelector('.lg-row.lg-sel .lg-msg').textContent)
    ? ok('ledger: not fixed refuses without a line of why')
    : fail('not fixed was sent with no reason');
  D.querySelector('.lg-row.lg-sel .lg-reason').value = 'the ring is round the wrong word';
  click(backBtn());
  await sleep(20);
  const st = asked.filter((r) => /ledger\/state/.test(r.url))[0];
  st && JSON.parse(st.body).id === 'R2.4' && JSON.parse(st.body).state === 'reopened'
    && JSON.parse(st.body).note === '2026-09-30-v1.md' && /wrong word/.test(JSON.parse(st.body).why)
    ? ok('ledger: not fixed goes with its round, its id and its why')
    : fail('not fixed was sent as ' + (st && st.body));
  D.querySelector('#reader-pages .lg-ghost.lg-full[data-id="R2.4"]')
    && /lg-back/.test(pip('R2.4').className)
    ? ok('ledger: and its ink stays at full strength, its pip marked as sent back')
    : fail('a pair not fixed lost its ink');
  const send = D.querySelector('#lg-panel .lg-send');
  send && /1 not fixed — send them/.test(send.textContent)
    ? ok('ledger: the panel offers to send what is not fixed')
    : fail('no send offer: ' + D.querySelector('#lg-panel .lg-foot').textContent);
  click(send);
  !D.getElementById('note').hidden
    ? ok('ledger: and sending them opens the filing panel, which carries every reopened pair')
    : fail('send them opened nothing');
  for (const id of ['R2.1', 'R2.2', 'R2.4', 'R2.5']) {
    if (!D.querySelector('.lg-row.lg-sel[data-id="' + id + '"]')) {
      click(D.querySelector('.lg-row[data-id="' + id + '"] .lg-hit'));
    }
    click(D.querySelector('.lg-row.lg-sel .lg-fine-btn'));
    await sleep(15);
  }
  !pip('R2.1') && !pip('R2.2')
    ? ok('ledger: a pair said fine loses its pip')
    : fail('fine pairs keep their pips');
  /Round 2 done/.test(chip.textContent)
    && /show the 5 notes/.test(D.querySelector('#lg-panel .lg-scroll').textContent)
    && !D.querySelectorAll('#reader-pages .lg-pip').length
    ? ok('ledger: a round with every pair fine collapses to “Round 2 done”')
    : fail('the finished round: chip ' + chip.textContent);
  click(D.querySelector('#lg-panel .lg-round'));
  D.querySelector('#lg-panel .lg-title').textContent === 'Round 1 done · 1 note'
    ? ok('ledger: and the earlier round opens from its line')
    : fail('the earlier round: ' + D.querySelector('#lg-panel .lg-title').textContent);
  click(D.querySelector('#lg-panel .lg-x'));

  // THE SPLIT, BEFORE IT GOES.
  asked.length = 0;
  click(D.getElementById('reader-say'));
  await sleep(20);
  const items = () => Array.prototype.map.call(
    D.querySelectorAll('#note-items .lg-pre'), (r) => r.dataset.id).join(',');
  asked.some((r) => /ledger\/preview/.test(r.url)) && items() === 'R3.1,R3.2'
    ? ok('ledger: the filing panel shows the split before anything is sent')
    : fail('the panel shows ' + items());
  const txt = D.getElementById('note-text');
  txt.value = 'And the title is long.';
  txt.dispatchEvent(new w.Event('input', { bubbles: true }));
  await sleep(40);
  items() === 'R3.1,R3.2,R3.3'
    ? ok('ledger: and again once the typing pauses, a paragraph a request')
    : fail('typing did not re-split: ' + items());
  click(D.querySelector('#note-items .lg-merge'));
  await sleep(20);
  items() === 'R3.1,R3.2' && /all of it, as one/.test(D.getElementById('note-items').textContent)
    ? ok('ledger: "these are one request" is one tap, and the split says so')
    : fail('merging did not take: ' + items());
  asked.length = 0;
  click(D.getElementById('note-send'));
  await sleep(40);
  const filed = asked.filter((r) => /library\/feedback/.test(r.url))[0];
  filed && JSON.stringify(JSON.parse(filed.body).merge) === '[2]'
    ? ok('ledger: and the round is filed with that page as one request')
    : fail('the send carried merge ' + (filed && filed.body));
  /2 requests, R3\.1, R3\.2/.test(D.getElementById('note-said').textContent)
    ? ok('ledger: the reply names the ids the revision will answer')
    : fail('the reply says: ' + D.getElementById('note-said').textContent);
}

/* THE PIPS KEEP APART, AND OWED INK IS DRAWN FROM EVERY ROUND. Two pairs a
   line apart must not put one disc over the other; ink still owed in a round
   the panel is not showing is still on the page; and a not-fixed pair riding
   a round still being revised keeps its ink at full strength. */
async function pipsAndOwedInk() {
  const S = { c: '#e8746c', w: 3, pg: 1, p: [0.1, 0.3, 0.3, 0.32] };
  const ink = (page) => ({ page: page, box: [0.1, 0.3, 0.3, 0.32], strokes: [S], drawn_on: 'd0' });
  const row = (o) => Object.assign({ kind: 'text', text: '', why: '', previous: '', count: 0,
    crop: '', marked: '', status: 'answered', problems: [], state: 'open', state_why: '',
    carried: '', ink: null, ink_at: null, at: null, diff: null, reply: '', gone: false,
    answer: { disposition: 'done', did: 'Done.', old: 'a', new: 'b', old_from: 'before' } }, o);
  const at = (page, y) => ({ page: page, y: y, box: [0.1, y, 0.5, y + 0.01], by: 'answer' });
  const LED = { ok: true, document: 'x', digest: 'd1', rounds: [
    { note: 'b.md', round: 3, landed: false, open: 1, judged: 0, done: false, items: [
      row({ id: 'R2.2', n: 1, kind: 'reopened', page: 1, status: 'waiting', answer: null,
            ink: ink(1), ink_at: { by: 'text', page: 1, box: [0.1, 0.3, 0.3, 0.32], dx: 0, dy: 0.01 } })] },
    { note: 'a.md', round: 2, landed: true, open: 3, judged: 1, done: false, items: [
      row({ id: 'R2.1', n: 1, page: 1, at: at(1, 0.300) }),
      row({ id: 'R2.2', n: 2, page: 1, at: at(1, 0.305), state: 'reopened', carried: 'b.md',
            ink: ink(1), ink_at: { by: 'same', page: 1, box: [0.1, 0.3, 0.3, 0.32], dx: 0, dy: 0 } }),
      row({ id: 'R2.3', n: 3, page: 1, at: at(1, 0.310) }),
      row({ id: 'R2.4', n: 4, page: 2, at: at(2, 0.5), status: 'not answered', answer: null,
            ink: ink(2), ink_at: { by: 'same', page: 2, box: [0.1, 0.3, 0.3, 0.32], dx: 0, dy: 0 } })] },
    { note: '0.md', round: 1, landed: true, open: 0, judged: 1, done: true, items: [
      row({ id: 'R1.1', n: 1, page: 2, at: at(2, 0.1), state: 'accepted' })] }] };
  const d = new JSDOM('<!doctype html><div id="reader"><div id="reader-pages">'
    + '<figure class="lib-page" data-page="1"><img></figure>'
    + '<figure class="lib-page" data-page="2"><img></figure></div></div>'
    + '<button id="chip"></button>', { runScripts: 'outside-only', pretendToBeVisual: true });
  const w = d.window;
  const D = w.document;
  w.HTMLImageElement.prototype.__defineGetter__('naturalWidth', () => 1240);
  w.HTMLImageElement.prototype.__defineGetter__('naturalHeight', () => 1754);
  w.fetch = () => Promise.resolve({ ok: true, json: () => Promise.resolve(LED) });
  w.eval(fs.readFileSync(path.join(WEB, 'ledger.js'), 'utf8'));
  const L = w.Ledger.make({ pages: D.getElementById('reader-pages'), button: D.getElementById('chip') });
  L.open({ id: 'x', ledger: { rounds: 3 } });
  await sleep(20);
  const tops = Array.prototype.map.call(D.querySelectorAll('.lib-page[data-page="1"] .lg-pip'),
                                        (p) => parseFloat(p.style.top));
  const gap = 100 * 0.036 * 1240 / 1754;
  tops.length === 2 && Math.abs(tops[0] - 30) < 1e-6 && Math.abs(tops[1] - tops[0] - gap) < 0.01
    ? ok('ledger: two pairs a line apart get pips a disc apart, in % of the page')
    : fail('pips on page 1 at ' + tops.join(', ') + '%');
  const fulls = Array.prototype.map.call(D.querySelectorAll('.lg-ghost.lg-full'),
    (g) => g.dataset.id + '@' + g.closest('.lib-page').dataset.page).sort().join(' ');
  fulls === 'R2.2@1 R2.4@2'
    ? ok('ledger: a not-fixed pair riding a round still being revised keeps its ink at full strength, once')
    : fail('full-strength ghosts: ' + fulls);
  L.toggle();
  const other = Array.prototype.filter.call(D.querySelectorAll('.lg-round'),
                                            (b) => b.dataset.note === '0.md')[0];
  if (other) other.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  await sleep(5);
  D.querySelectorAll('.lg-ghost.lg-full[data-id="R2.4"]').length === 1
    ? ok('ledger: ink still owed stays on the page while the panel shows another round')
    : fail('owed ink went when another round was shown');
}
