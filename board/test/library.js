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
  if (/library\/view\//.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve({
      ok: true, n: 2, truncated: false,
      pages: ['/paper/abc123-1.png', '/paper/abc123-2.png'],
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

try { window.eval(fs.readFileSync(path.join(WEB, 'library.js'), 'utf8')); }
catch (e) { fail('library.js: ' + e.message); }

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

  doc.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape' }));
  doc.getElementById('note').hidden
    ? ok('escape closes the note without sending it')
    : fail('escape left the panel open');

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\nthe library draws what a workspace wrote, and takes a word about one');
  process.exit(errors.length ? 1 : 0);
})();
