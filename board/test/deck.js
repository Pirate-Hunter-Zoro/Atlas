// The meeting deck, read in the Meetings library's one reader and marked up
// there.
//
// Driven in a real DOM, because everything worth checking here is what the
// page SENDS and DRAWS.
//
//   * FROM THE FRONT DOOR. "Read the deck" is the Meetings library with the
//     deck asked for (`?subject=projects/Meetings&doc=meeting&from=home`), and
//     the library opens it with `Reader.open`: the same pages, pen, pinch and
//     save as every other PDF on the glass.
//   * WHAT NO SOURCE SUPPORTS is listed in the reader, with the slide.
//   * INK IS STAMPED WITH ITS DECK, so a reader left open over a deck asked
//     for again lets the old deck's marks go instead of writing them on the
//     new deck's slides.
//   * A MARK PLUS "SAY WHAT IS WRONG" is one round on the deck, filed through
//     `/library/feedback` in Meetings, page pictures first.

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
const Q = 'subject=projects%2FMeetings';

/* THE DECK'S RECORD, as `/library.json?subject=projects/Meetings` carries it
   (`with_deck` on the server). */
const MEETING = {
  state: 'ready', why: '', ready: true, deck: '2026-10-09T10:00:00',
  since: 'the last week', period: '2 Oct – 9 Oct', subjects: ['PSYCH-ASR', 'TRD-EHR'],
  pages: 3,
  check: {
    numbers: [{ value: '0.713', frame: 3, title: 'Two arms',
                context: 'the weighted arm reaches 0.713 in a subgroup' }],
    figures: [], internal: [],
  },
};
const ROW = {
  id: 'meeting', group: 'artifact', dir: 'docs/meeting', stem: 'meeting',
  title: 'Meeting deck: the last week', kind: 'deck', formats: ['pdf', 'tex'],
  rel: 'docs/meeting/meeting.pdf', source: 'docs/meeting/meeting.tex', pages: 3,
  pdf: true, stale: false, iso: '2026-10-09', notes: [], own: true,
  artifact: 'docs/meeting', type: 'deck', status: 'done',
  marks: { pages: 0, strokes: 0, waiting: 0 }, meeting: MEETING,
};
const LIBRARY = { workspace: 'Meetings', subject: 'projects/Meetings',
                  writeups: 'writeups', documents: [ROW], meeting: MEETING };
const BUILD = { digest: 'abc123def4567890', at: 1790000000, pages: 3 };
const VIEW = {
  ok: true, n: 3, truncated: false, digest: BUILD.digest, build: BUILD, rebuilt: null,
  pages: ['/paper/deck-1.png', '/paper/deck-2.png', '/paper/deck-3.png'],
  ink: {}, wiped: {},
};

const HTML = fs.readFileSync(path.join(WEB, 'library.html'), 'utf8');
const dom = new JSDOM(HTML, {
  runScripts: 'outside-only', pretendToBeVisual: true,
  url: 'https://board.test/library?' + Q + '&doc=meeting&from=home',
});
const { window } = dom;
const doc = window.document;

const sent = [];
const net = { save: 'ok' };
window.fetch = (u, opts) => {
  const url = String(u);
  sent.push({ url: url, opts: opts || {} });
  if (/library\.json/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve(LIBRARY) });
  }
  if (/library\/view\//.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve(VIEW) });
  }
  if (/annotate\/save/.test(url)) {
    if (net.save === 'gone') {
      return Promise.resolve({ ok: false, status: 409,
                               json: () => Promise.resolve({ ok: false, gone: true }) });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) });
  }
  if (/library\/feedback/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve({
      ok: true, rel: 'docs/meeting/feedback/2026-10-09-v1.md', marks: 1,
      revise: 'board', asked: true, session: '20261009-100000',
      detail: 'The tutor has been asked to revise it, in the newest session on this subject.',
    }) });
  }
  return new Promise(() => {});
};
window.addEventListener('error', (e) => fail('uncaught: ' + e.message));

// The pen is the board's own, unchanged, so it is loaded the way the page
// loads it. jsdom has no canvas, and everything `annotate.js` does with one is
// drawing -- which is not what is being asserted here.
window.HTMLCanvasElement.prototype.getContext = () =>
  new Proxy({}, { get: () => () => {}, set: () => true });
window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
window.Element.prototype.setPointerCapture = function () {};
window.Element.prototype.releasePointerCapture = function () {};
window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
window.ResizeObserver = function () { this.observe = () => {}; this.disconnect = () => {}; };
try { window.localStorage.clear(); } catch (e) { /* none */ }

/* THE SCRIPTS THE PAGE ITSELF LOADS, in its order, read out of its markup: a
   hand-kept list is how a suite goes green against a page missing a file. */
const SCRIPTS = (HTML.match(/src="\/static\/[\w.-]+"/g) || [])
  .map((m) => /static\/([\w.-]+)/.exec(m)[1])
  .filter((f) => f !== 'typeface.js');
for (const f of SCRIPTS) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}

const tap = (n) => n.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
const byId = (id) => doc.getElementById(id);
const S = { c: '#e8746c', w: 2, p: [0.1, 0.1, 0.3, 0.4], pr: [0.5, 0.5] };
/* A stroke on a slide, the way the pen leaves one: on the page, and owed. */
const draw = (key) => {
  window.Annotate.load({ [key]: [S] }); window.Annotate.clear(key); window.Annotate.undo();
};

(async function () {
  await sleep(40);

  // 1. The deck the front door asked for is open, in the one reader.
  const r = window.Reader && window.Reader.current();
  r && r.id === 'meeting' && !byId('reader').hidden
    ? ok('the deck opens in the one reader (`Reader.open`), straight from the link')
    : fail('the deck is not open in reader.js: ' + JSON.stringify(r));
  const views = sent.filter((x) => /library\/view\//.test(x.url));
  views.length === 1 && views[0].url === '/library/view/meeting?' + Q
    ? ok('its pages are the Meetings library\'s, asked for by id')
    : fail('the view was asked for as: ' + views.map((x) => x.url).join('|'));
  !sent.some((x) => /^\/meeting(\/|\?|$)/.test(x.url))
    ? ok('and no meeting route is asked')
    : fail('a meeting route was asked: ' + sent.map((x) => x.url).join('|'));

  // 2. Every slide is an anchor.
  const pages = Array.prototype.slice.call(doc.querySelectorAll('.lib-page'));
  pages.map((p) => p.dataset.ann).join('|')
    === 'doc/meeting/p1|doc/meeting/p2|doc/meeting/p3'
    ? ok('every slide is drawn, carrying the address the pen anchors to')
    : fail('anchors: ' + pages.map((p) => p.dataset.ann).join('|'));

  // 3. What no source supports is on the reader, with the slide it is on.
  {
    const box = byId('reader-check');
    const said = box ? box.textContent : '';
    box && !box.hidden && /0\.713/.test(said) && /slide 3/.test(said)
      && /not in any source/.test(said)
      ? ok('a number no source gives is listed in the reader, with its slide')
      : fail('the check in the reader: ' + (box ? (box.hidden ? 'hidden' : said) : 'missing'));
  }

  // 4. The way back is the front door.
  /Everything/.test(byId('lib-back').textContent)
    && byId('lib-back').getAttribute('href') === '/'
    ? ok('the way back says Everything and goes to the front door')
    : fail('the way back: ' + byId('lib-back').getAttribute('href'));

  // 5. Ink on a slide is kept in Meetings, stamped with its build and deck.
  sent.length = 0;
  draw('doc/meeting/p2');
  await sleep(1000);
  const save = sent.filter((x) => /annotate\/save/.test(x.url)).pop();
  const body = save ? JSON.parse(save.opts.body) : {};
  save && save.url === '/annotate/save?' + Q && body.card === 'doc/meeting/p2'
    && body.deck === MEETING.deck && (body.build || {}).digest === BUILD.digest && !body.send
    ? ok('a mark on a slide is saved into Meetings, stamped with its build and its deck')
    : fail('the save was: ' + (save && save.url + ' ' + save.opts.body));

  // 6. A deck replaced under the reader: its old ink is let go, not retried.
  net.save = 'gone';
  sent.length = 0;
  draw('doc/meeting/p3');
  await sleep(1000);
  window.Annotate.unsaved().indexOf('doc/meeting/p3') < 0
    && sent.some((x) => /library\.json/.test(x.url))
    && !/not saved/.test(byId('reader-kept').textContent)
    ? ok('a save the board says is for another deck is let go, and the list asked again')
    : fail('a gone save: unsaved ' + window.Annotate.unsaved().join(','));
  net.save = 'ok';
  window.Annotate.drop('doc/meeting/p3');

  // 7. Say what is wrong: page pictures, then one round in Meetings.
  ROW.marks = { pages: 1, strokes: 1, waiting: 1 };
  tap(byId('reader-say'));
  await sleep(10);
  !byId('note').hidden
    ? ok('say what is wrong opens the library\'s panel over the deck')
    : fail('the panel did not open');
  sent.length = 0;
  byId('note-text').value = 'Slide 2 needs the ROC curve.';
  byId('note-text').dispatchEvent(new window.Event('input', { bubbles: true }));
  const img2 = doc.querySelector('.lib-page[data-page="2"] img');
  if (img2) {
    Object.defineProperty(img2, 'naturalWidth', { value: 1600 });
    img2.getBoundingClientRect = () => ({ left: 0, top: 0, width: 800, height: 450,
                                          right: 800, bottom: 450 });
  }
  tap(byId('note-send'));
  await sleep(80);
  const pic = sent.findIndex((x) => /annotate\/save/.test(x.url)
    && JSON.parse(x.opts.body || '{}').card === 'doc/meeting/p2'
    && /^data:image\/png/.test(JSON.parse(x.opts.body || '{}').png || ''));
  const filed = sent.findIndex((x) => /library\/feedback/.test(x.url));
  const fbody = filed >= 0 ? JSON.parse(sent[filed].opts.body) : {};
  filed >= 0 && sent[filed].url === '/library/feedback?' + Q
    && fbody.document === 'meeting' && /ROC/.test(fbody.text)
    ? ok('the marks and the words go as one round on the deck, to Meetings')
    : fail('nothing was filed: ' + sent.map((x) => x.url).join('|'));
  pic >= 0 && filed > pic
    ? ok('and the marked slide\'s picture is saved before the round is filed')
    : fail('no slide picture went ahead of the round: ' + sent.map((x) => x.url).join(' '));
  /Filed at docs\/meeting\/feedback/.test(byId('note-said').textContent)
    ? ok('and the reply says where the round was filed')
    : fail('the reply: ' + byId('note-said').textContent);

  // 8. The meeting page is gone from the web tree and nothing points at it.
  const left = fs.readdirSync(WEB).filter((f) => /\.(js|html)$/.test(f))
    .filter((f) => /\/meeting\/(view|pdf|deck\.json)|meeting\.(html|js)\b|href="\/meeting"/
      .test(fs.readFileSync(path.join(WEB, f), 'utf8')));
  !fs.existsSync(path.join(WEB, 'meeting.html')) && !fs.existsSync(path.join(WEB, 'meeting.js'))
    && !left.length
    ? ok('meeting.html and meeting.js are gone, and no page names them or their routes')
    : fail('still there or named: ' + left.join(', '));

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\nthe meeting deck is read and marked in the one reader');
  process.exit(errors.length ? 1 : 0);
})();
