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
  unsupported: {
    numbers: [{ value: '0.713', frame: 3, title: 'Two arms',
                context: 'the weighted arm reaches 0.713 in a subgroup' }],
    figures: [], internal: [],
  },
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

/* THE SCRIPTS THE PAGE ITSELF LOADS, in its order, read out of its markup: a
   hand-kept list is how a suite goes green against a page missing a file. */
const MEETING_HTML = fs.readFileSync(path.join(WEB, 'meeting.html'), 'utf8');
const MEETING_SCRIPTS = (MEETING_HTML.match(/src="\/static\/[\w.-]+"/g) || [])
  .map((m) => /static\/([\w.-]+)/.exec(m)[1])
  .filter((f) => f !== 'meeting.js' && f !== 'typeface.js');
MEETING_SCRIPTS.includes('inkkeep.js')
  ? ok('the page loads the save path the library reader uses, not a copy of it')
  : fail('meeting.html does not load inkkeep.js: ' + MEETING_SCRIPTS.join(', '));
for (const f of MEETING_SCRIPTS) {
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
    && /every project/.test(pages[0].querySelector('figcaption').textContent)
    ? ok('and says which project it is about before anybody draws on it, '
         + 'because the page is how a mark finds its project')
    : fail('captions: ' + pages.map(
        (p) => p.querySelector('figcaption').textContent).join(' | '));

  // 2a. What no source supports is on the page, with the slide it is on.
  {
    const box = doc.getElementById('deck-check');
    const said = box ? box.textContent : '';
    box && !box.hidden && /0\.713/.test(said) && /slide 3/.test(said)
      && /not in any source/.test(said)
      ? ok('a number no source gives is listed beside the deck, with its slide')
      : fail('the sidecar on the page: ' + (box ? (box.hidden ? 'hidden' : said) : 'missing'));
  }

  // 2b. The pen brings the board's own tools, and "done" puts them away.
  {
    const click = (n) => n.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    const pen = doc.getElementById('reader-pen');
    const bar = doc.querySelector('.annbar-doc');
    bar && bar.hidden
      ? ok('the tool bar is away until the pen is asked for')
      : fail('the tool bar is missing or showing with the pen off');
    click(pen);
    const names = bar ? Array.prototype.map.call(bar.querySelectorAll('button'),
      (b) => b.textContent) : [];
    !bar.hidden && ['Pen', 'Erase', 'Select', 'Copy', 'Paste', '↶', 'done']
      .every((t) => names.includes(t))
      ? ok('a slide gets the board\'s pen, eraser, loop, clipboard and undo')
      : fail('the slide\'s tool bar: ' + names.join(','));
    click(bar.querySelector('.ann-ink[data-ink="#6fc3f7"]'));
    window.Annotate.colour() === '#6fc3f7'
      ? ok('and its colours')
      : fail('blue did not take: ' + window.Annotate.colour());
    click(Array.prototype.find.call(bar.querySelectorAll('button'),
      (b) => b.textContent === 'done'));
    !window.Annotate.isOn() && bar.hidden && /mark it up/.test(pen.textContent)
      ? ok('done on the bar is the pen switched off')
      : fail('done left the pen on, or the bar up');
  }

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

  // 9. The way back, because this is a full-screen surface -- and it is named
  // after where it goes. Every way back to the front door in this app says the
  // same word, and the word is the one on the heading it lands on.
  const back = doc.getElementById('deck-back');
  back.getAttribute('href') === '/' && /Everything/.test(back.textContent)
    ? ok('the front door is one tap away, and the tap says Everything, which '
         + 'is the heading it lands on')
    : fail('there is no way back, or it is named after something else: '
           + back.getAttribute('href') + ' / ' + back.textContent);

  await inkIsKept();

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\na mark on a meeting slide is that project\'s '
                              + 'direction, and nothing about the slide');
  process.exit(errors.length ? 1 : 0);
})();

/* ==========================================================================
   THE INK SAYS IT IS KEPT, on this reader as on the library's.

   Ink drawn on a slide has to say it is on disk, survive the lid shutting,
   and know which build it was drawn on. A page of its own, on a DOM of its
   own, because what is asserted is what a network that says no does to it.
   ========================================================================== */
async function inkIsKept() {
  const BUILD = { digest: 'abc123def4567890', at: 1790000000, pages: 3 };
  const S = { c: '#e8746c', w: 2, p: [0.1, 0.1, 0.3, 0.4], pr: [0.5, 0.5] };
  const P2 = 'doc/meeting/p2';
  const P3 = 'doc/meeting/p3';
  const net = { save: 'ok', rebuilt: null, deck: '1790000000.5' };
  const d = new JSDOM(MEETING_HTML, { runScripts: 'outside-only', pretendToBeVisual: true,
                                      url: 'https://board.test/meeting' });
  const w = d.window;
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
  w.fetch = (u, o) => {
    const url = String(u);
    log.push({ url: url, opts: o || {} });
    if (/meeting\/view/.test(url)) {
      return Promise.resolve({ json: () => Promise.resolve(Object.assign(
        {}, VIEW, { digest: BUILD.digest, build: BUILD, rebuilt: net.rebuilt,
                    deck: net.deck })) });
    }
    if (/annotate\/save/.test(url)) {
      if (net.save === 'down') return Promise.reject(new TypeError('Failed to fetch'));
      if (net.save === 'gone') {
        return Promise.resolve({ ok: false, status: 409,
                                 json: () => Promise.resolve({ ok: false, gone: true }) });
      }
      if (net.save === 'refused') {
        return Promise.resolve({ ok: false, status: 500,
                                 json: () => Promise.resolve({ ok: false }) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) });
    }
    return new Promise(() => {});
  };
  w.addEventListener('error', (e) => fail('uncaught (ink page): ' + e.message));
  for (const f of MEETING_SCRIPTS) {
    try { w.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
    catch (e) { fail(f + ' (ink page): ' + e.message); }
  }
  w.INK_RETRY_MS = 100000;
  try { w.eval(fs.readFileSync(path.join(WEB, 'meeting.js'), 'utf8')); }
  catch (e) { fail('meeting.js (ink page): ' + e.message); }
  await sleep(30);

  const byId = (id) => w.document.getElementById(id);
  const saves = () => log.filter((r) => /annotate\/save/.test(r.url));
  const kept = () => { const k = byId('reader-kept'); return k.hidden ? '' : k.textContent; };
  const hide = (v) => { hidden = v; w.document.dispatchEvent(new w.Event('visibilitychange')); };
  /* A stroke on a slide, the way the pen leaves one: on the page, and owed. */
  const draw = (key) => { w.Annotate.load({ [key]: [S] }); w.Annotate.clear(key); w.Annotate.undo(); };

  kept() === ''
    ? ok('ink: a deck with no ink on it says nothing about ink')
    : fail('ink: a clean deck says: ' + kept());

  // ---- a good save, stamped, and said ---------------------------------
  draw(P2);
  /saving/.test(kept())
    ? ok('ink: a stroke not yet on disk reads “saving…”')
    : fail('ink: a fresh stroke reads: ' + kept());
  await sleep(1000);
  const first = saves().pop();
  const body = first ? JSON.parse(first.opts.body) : {};
  (body.build || {}).digest === BUILD.digest && body.card === P2 && !body.send
    && body.deck === net.deck
    ? ok('ink: a saved slide carries the build and the deck it was drawn on, and is not a send')
    : fail('ink: the save was: ' + (first && first.opts.body));
  kept() === 'saved · 1 page marked'
    ? ok('ink: once it lands the bar says “saved · 1 page marked”')
    : fail('ink: a landed save reads: ' + kept());

  // ---- a 500 stays unsaved, is shown, and is retried on `online` ------
  net.save = 'refused';
  draw(P3);
  await sleep(1000);
  kept() === 'not saved — retrying' && byId('reader-kept').classList.contains('bad')
    ? ok('ink: a save the board answers 500 is shown: “not saved — retrying”')
    : fail('ink: a 500 reads: ' + kept());
  w.Annotate.unsaved().indexOf(P3) >= 0
    ? ok('ink: and the slide stays unsaved rather than being cleaned on any reply')
    : fail('ink: a 500 cleaned the slide');
  let before = saves().length;
  hide(false);
  await sleep(30);
  saves().length > before && w.Annotate.unsaved().indexOf(P3) >= 0
    ? ok('ink: back to visible is a retry, and a second 500 is still not a save')
    : fail('ink: visible retry: ' + (saves().length - before) + ' saves');
  net.save = 'ok';
  before = saves().length;
  w.dispatchEvent(new w.Event('online'));
  await sleep(30);
  saves().length > before && w.Annotate.unsaved().indexOf(P3) < 0
    && kept() === 'saved · 2 pages marked'
    ? ok('ink: the network coming back is a retry, and only its success is kept')
    : fail('ink: after online: ' + (saves().length - before) + ' saves, bar '
           + kept() + ', unsaved ' + w.Annotate.unsaved().join(','));

  // ---- the lid shutting ------------------------------------------------
  draw(P2);
  before = saves().length;
  hide(true);
  await sleep(10);
  const flushed = saves().slice(before);
  flushed.length && flushed.every((r) => r.opts.keepalive === true)
    && JSON.parse(flushed[0].opts.body).card === P2
    ? ok('ink: a page going hidden flushes what is owed at once, with keepalive')
    : fail('ink: the hidden flush: ' + JSON.stringify(flushed.map((r) => r.opts.keepalive)));
  hide(false);
  await sleep(30);

  // ---- sending waits for the ink, and will not go without it -----------
  net.save = 'down';
  draw(P2);
  byId('deck-send').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  byId('deck-ask-go').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  await sleep(40);
  !log.some((r) => /meeting\/direction/.test(r.url))
    && /not saved yet/.test(byId('deck-ask-said').textContent)
    ? ok('ink: marks the board has not got are not sent as direction, and it says so')
    : fail('ink: direction went with unsaved ink: ' + byId('deck-ask-said').textContent);
  // ---- close waits for the ink, and says when it will not save ---------
  byId('reader-close').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  await sleep(40);
  /close again to leave without it/.test(kept()) && w.Annotate.unsaved().indexOf(P2) >= 0
    ? ok('ink: close waits on the save, and ink that will not save stops it once, saying so')
    : fail('ink: close with unsaved ink: ' + kept());
  net.save = 'ok';
  w.dispatchEvent(new w.Event('online'));
  await sleep(30);

  // ---- a deck replaced under the page lets its old ink go --------------
  net.save = 'gone';
  draw(P3);
  const views = () => log.filter((r) => /meeting\/view/.test(r.url)).length;
  const viewsBefore = views();
  await sleep(1000);
  w.Annotate.unsaved().indexOf(P3) < 0 && views() > viewsBefore
    && !/not saved/.test(kept())
    ? ok('ink: a save the board says is for another deck is let go, not retried, '
         + 'and the page draws the deck again')
    : fail('ink: a gone save: unsaved ' + w.Annotate.unsaved().join(',')
           + ', bar ' + kept());
  net.save = 'ok';
  await sleep(30);

  // ---- rebuilt since ---------------------------------------------------
  net.rebuilt = { at: 1789990000, when: '28 Sep 21:40', pages: [2], copy: true, detail: '' };
  // The deck opened again, after a recompile in place.
  const again = new JSDOM(MEETING_HTML, { runScripts: 'outside-only', pretendToBeVisual: true,
                                          url: 'https://board.test/meeting' });
  const w2 = again.window;
  w2.HTMLCanvasElement.prototype.getContext = w.HTMLCanvasElement.prototype.getContext;
  w2.HTMLCanvasElement.prototype.toDataURL = w.HTMLCanvasElement.prototype.toDataURL;
  w2.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  w2.fetch = w.fetch;
  for (const f of MEETING_SCRIPTS) {
    try { w2.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
    catch (e) { fail(f + ' (rebuilt page): ' + e.message); }
  }
  try { w2.eval(fs.readFileSync(path.join(WEB, 'meeting.js'), 'utf8')); }
  catch (e) { fail('meeting.js (rebuilt page): ' + e.message); }
  await sleep(30);
  const flag = w2.document.getElementById('reader-rebuilt');
  flag && !flag.hidden && /28 Sep 21:40 build/.test(flag.textContent)
    && /rebuilt since/.test(flag.textContent)
    ? ok('ink: marks drawn on an earlier build of the deck are flagged “rebuilt since”')
    : fail('ink: the rebuilt flag: ' + (flag ? (flag.hidden ? 'hidden' : flag.textContent) : 'missing'));

  // Re-drawing the flagged slide on this build clears the flag on the board,
  // and the page asks again rather than going on saying it.
  net.rebuilt = null;
  w2.Annotate.load({ [P2]: [S] }); w2.Annotate.clear(P2); w2.Annotate.undo();
  await sleep(1100);
  flag && flag.hidden
    ? ok('ink: a flag re-drawing has cleared goes from the page after the save')
    : fail('ink: the rebuilt flag stayed up after the marks were re-drawn');
}
