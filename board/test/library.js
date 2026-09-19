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
window.fetch = (u, opts) => {
  const url = String(u);
  sent.push({ url: url, opts: opts || {} });
  if (/library\.json/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve(LIBRARY) });
  }
  if (/library\/stamp/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve(STAMP) });
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
      ink: { 'doc/docs-stage1-pipeline-walkthrough/p2': [[[0.1, 0.1], [0.3, 0.4]]] },
    }) });
  }
  if (/annotate\/save/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve({ ok: true }) });
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

for (const f of ['ink-clip.js', 'annotate.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}

/* A tablet picked up again would arrive with a turn already recorded as in
   flight -- the page keeps that where a reload finds it. Nothing is, here. */
try { window.localStorage.removeItem('library.flight'); } catch (e) {}

try { window.eval(fs.readFileSync(path.join(WEB, 'library.js'), 'utf8')); }
catch (e) { fail('library.js: ' + e.message); }

/* The poll's own interval, turned down so a test can watch two passes of it
   rather than sitting out eight seconds. The page reads the global on every
   pass, so this is the same code path at a different cadence. */
window.STAMP_EVERY = 60;

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
  tap(doc.getElementById('note-send'));
  await sleep(20);
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

  const home = fs.readFileSync(path.join(WEB, 'home.js'), 'utf8');
  /\/library\?from=home/.test(home)
    ? ok('and the front door is what says so, on both routes in -- the one it '
         + 'is already serving and the one it has to switch to')
    : fail('home.js opens the library without saying where from');

  doc.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape' }));
  doc.getElementById('note').hidden
    ? ok('escape closes the note without sending it')
    : fail('escape left the panel open');

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\nthe library draws what a workspace wrote, and takes a word about one');
  process.exit(errors.length ? 1 : 0);
})();
