// The meeting deck, read on the glass and marked up on it.
//
// Driven in a real DOM, because everything worth checking here is what the
// page SENDS and DRAWS, and one of those things is a route it must never send
// to.
//
//   * A MARK IS DIRECTION, NOT FEEDBACK. Every line of this page makes
//     `/library/feedback` the obvious next call, and it is the wrong one: that
//     route files a complaint about the document and wakes a turn to fix the
//     slides. The deck is a throwaway communication tool; what a mentor draws
//     on a frame is a suggested new direction for the project that frame is
//     about. `/meeting/direction` is the only route the marks go to.
//   * THE PAGE IS HOW A MARK FINDS ITS PROJECT. One frame per workspace, and
//     the caption under each page names it BEFORE anybody draws, so marking
//     the wrong slide is visibly the wrong slide.
//   * A MARK ON THE TITLE SLIDE BELONGS TO NOBODY, and the page says so rather
//     than letting somebody believe it went somewhere.
//   * NOTHING IS APPLIED. The panel says, before it sends, that each workspace
//     writes a card PROPOSING a direction and stops -- because the route it
//     would be easy to build instead archives a lesson and replaces an
//     assistant, unattended, in as many workspaces as there are marked slides.
//   * NO NAME GOES OVER THE WIRE. There is one deck, so `/meeting/view` takes
//     no argument at all.

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

/* What `/meeting/view` serves: the pages, the page map, the names those
   workspaces are drawn under, and whatever ink is already on them. */
const VIEW = {
  ok: true, n: 3, truncated: false,
  pages: ['/paper/deck-1.png', '/paper/deck-2.png', '/paper/deck-3.png'],
  pages_of: { 2: 'research/PSYCH-ASR', 3: 'research/TRD-EHR' },
  names: { 'research/PSYCH-ASR': 'PSYCH-ASR', 'research/TRD-EHR': 'TRD-EHR' },
  since: 'last week',
  ink: {},
};

const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'meeting.html'), 'utf8'), {
  runScripts: 'outside-only', pretendToBeVisual: true,
  url: 'https://board.test/meeting',
});
const { window } = dom;
const doc = window.document;

const sent = [];
window.fetch = (u, opts) => {
  const url = String(u);
  sent.push({ url: url, opts: opts || {} });
  if (/meeting\/view/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve(VIEW) });
  }
  if (/annotate\/save/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve({ ok: true }) });
  }
  if (/meeting\/direction/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve({
      ok: true, sent: [{ workspace: 'research/PSYCH-ASR', name: 'PSYCH-ASR',
                         pages: [2], turn: '0007' }],
      skipped: [],
      detail: '1 workspace has been asked to propose a new direction.',
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

for (const f of ['ink-clip.js', 'annotate.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
try { window.eval(fs.readFileSync(path.join(WEB, 'meeting.js'), 'utf8')); }
catch (e) { fail('meeting.js: ' + e.message); }

(async function () {
  await sleep(20);

  // 1. One deck, so nothing is named.
  const asked = sent.filter((r) => /meeting\/view/.test(r.url));
  asked.length === 1 && asked[0].url === '/meeting/view'
    ? ok('the page asks for the one deck, and names nothing')
    : fail('the view was asked for as: ' + asked.map((a) => a.url).join('|'));

  // 2. Every slide is an anchor, and every slide says whose it is.
  const pages = Array.prototype.slice.call(doc.querySelectorAll('.lib-page'));
  pages.length === 3
    ? ok('every slide is drawn')
    : fail('slides drawn: ' + pages.length);
  pages.map((p) => p.dataset.ann).join('|')
    === 'doc/meeting/p1|doc/meeting/p2|doc/meeting/p3'
    ? ok('and each one carries the page address the pen anchors to')
    : fail('anchors: ' + pages.map((p) => p.dataset.ann).join('|'));
  /PSYCH-ASR/.test(pages[1].querySelector('figcaption').textContent)
    && /whole repository/.test(pages[0].querySelector('figcaption').textContent)
    ? ok('and says which project it is about before anybody draws on it, '
         + 'because the page is how a mark finds its project')
    : fail('captions: ' + pages.map(
        (p) => p.querySelector('figcaption').textContent).join(' | '));

  // 3. Nothing to send until something is marked.
  const send = doc.getElementById('deck-send');
  send.disabled
    ? ok('there is nothing to send until something is marked')
    : fail('the send button was live with no marks');

  // 4. A mark on the title slide belongs to nobody, and it is SAID.
  //
  // `load` restores ink without firing the page's own change callback -- which
  // is right, because that is what a reload does. `clear` on a key nothing is
  // drawn on fires it and changes nothing else, which is the cheapest way to
  // reach the repaint a stroke would have caused without a canvas to stroke on.
  window.Annotate.load({ 'doc/meeting/p1': [[[0.1, 0.1], [0.4, 0.2]]] });
  window.Annotate.clear('doc/meeting/p9');
  await sleep(10);
  const said = doc.getElementById('reader-said').textContent;
  /go nowhere/.test(said) && doc.getElementById('deck-send').disabled
    ? ok('a mark on the title slide is said to go nowhere rather than '
         + 'silently dropped')
    : fail('the title-slide mark was not reported: ' + said);

  // 5. A mark on a project's slide is that project's direction.
  window.Annotate.load({ 'doc/meeting/p2': [[[0.2, 0.2], [0.5, 0.3]]] });
  window.Annotate.clear('doc/meeting/p9');
  await sleep(10);
  !doc.getElementById('deck-send').disabled
    && /PSYCH-ASR/.test(doc.getElementById('reader-said').textContent)
    ? ok('a mark on a project slide names that project, and the send is live')
    : fail('the marked project was not picked up: '
           + doc.getElementById('reader-said').textContent);

  // 6. IT SAYS WHAT IS ABOUT TO HAPPEN BEFORE IT HAPPENS, and the thing it
  //    says is the thing that makes it safe.
  doc.getElementById('deck-send').dispatchEvent(
    new window.MouseEvent('click', { bubbles: true }));
  await sleep(10);
  const panel = doc.getElementById('note');
  !panel.hidden && /PSYCH-ASR/.test(doc.getElementById('deck-ask-list').textContent)
    ? ok('sending asks first, and names which projects it would wake')
    : fail('the confirmation did not open');
  /proposing/i.test(panel.textContent) && /Nothing is applied/.test(panel.textContent)
    ? ok('and says plainly that nothing is applied: each one writes a card')
    : fail('the panel does not say what it will not do');

  // 7. The marks go to `/meeting/direction` and nowhere else.
  sent.length = 0;
  doc.getElementById('deck-ask-go').dispatchEvent(
    new window.MouseEvent('click', { bubbles: true }));
  await sleep(30);
  const where = sent.map((r) => r.url);
  where.indexOf('/meeting/direction') !== -1
    ? ok('the marks are sent as direction')
    : fail('nothing was sent: ' + where.join('|'));
  !where.some((u) => /library\/feedback/.test(u))
    ? ok('and never as feedback on the deck, which would spend a turn fixing '
         + 'the slides and throw away what the marks said')
    : fail('the page filed feedback on the deck');
  /propose a new direction/.test(doc.getElementById('deck-ask-said').textContent)
    ? ok('and the reply says what was asked of them')
    : fail('the reply was not painted');

  // 8. Nothing on this page knows how to touch a lesson.
  //
  // The COMMENTS are stripped first. This file's own header names
  // `/library/feedback` as the route it must not use, and a guard that cannot
  // tell a warning from a call is a guard that fails on the sentence
  // explaining it.
  const js = fs.readFileSync(path.join(WEB, 'meeting.js'), 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
  !/library\/feedback|"\/say"|\/session|"\/direction"|live\/cards/.test(js)
    ? ok('nothing in it knows how to write a card, file feedback, or apply a '
         + 'direction')
    : fail('meeting.js reaches somewhere it must not');

  // 9. The way back, because this is a full-screen surface.
  doc.getElementById('deck-back').getAttribute('href') === '/'
    ? ok('the front door is one tap away')
    : fail('there is no way back');

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\na mark on a meeting slide is that project\'s '
                              + 'direction, and nothing about the slide');
  process.exit(errors.length ? 1 : 0);
})();
