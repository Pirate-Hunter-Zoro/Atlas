// THE STRIP IN THE CHROME: documents asked for from this session.
//
// A deck or paper turn writes no card, so this strip is the only place that
// says it is being written and that it is there. It sits in the chrome, never
// over the lesson. The board also tells the server somebody is looking, which
// is what the start screen's new-card count reads.
//
// Cross-board missions and answers from other workspaces are gone (T52): the
// payload carries no `news` or `missions`, and their rows are not drawn.

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

const t0 = Date.now() / 1000;

/* ------------------------------------------------------------- the board */
function boardDom() {
  const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
    runScripts: 'outside-only', pretendToBeVisual: true,
    url: 'https://board.test/board',
  });
  const { window } = dom;
  window.HTMLCanvasElement.prototype.getContext = () =>
    new Proxy({}, { get: () => () => {}, set: () => true });
  window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
  Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => 900 });
  Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 500 });
  window.HTMLElement.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: 900, height: 120, right: 900, bottom: 120, x: 0, y: 0 };
  };
  window.Element.prototype.scrollIntoView = function () {};
  window.Element.prototype.setPointerCapture = function () {};
  window.Element.prototype.releasePointerCapture = function () {};
  window.asked = [];
  window.fetch = (u, opts) => {
    window.asked.push({ url: String(u), how: (opts && opts.method) || 'GET' });
    if (/slate\/state/.test(String(u))) {
      return Promise.resolve({ json: () => Promise.resolve({ pages: [] }) });
    }
    return new Promise(() => {});
  };
  window.renderMathInElement = () => {};
  window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  window.scrollTo = function () {};
  window.addEventListener('error', (e) => fail('uncaught: ' + e.message));
  window.EventSource = function () {
    window.__es = this;
    this.readyState = 1;
    this.close = function () {};
    this.addEventListener = function () {};
  };
  for (const f of ['typeface.js', 'macros.js', 'plane-core.js',
                   'ink-core.js', 'slate-core.js', 'annotate.js', 'address.js',
                   'board.js']) {
    try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
    catch (e) { fail(f + ': ' + e.message); }
  }
  return window;
}

(async () => {

const window = boardDom();
const doc = window.document;
const es = window.__es;
if (!es) { console.log('FAIL board.js never opened a stream'); process.exit(1); }

const bar = () => doc.getElementById('newsbar');

const frame = (papers, extra) => JSON.stringify(Object.assign({
  state: { course: 'Galois Theory', session: 'lecture' },
  cards: [{ id: '0001', kind: 'lesson', title: '', body: 'A field is a ring.',
            mtime: t0 - 600 }],
  turns: [], agent: { agent: 'claude', state: 'listening', turns: 2 },
  waiting: null, history: 0, writeups: papers || null,
}, extra || {}));

// Nothing asked for: nothing to say, and saying something anyway is furniture.
es.onmessage({ data: frame([]) });
await sleep(60);
bar().hidden
  ? ok('with no document asked for, there is no strip')
  : fail('the notification strip is up over no notifications');

// The lesson being read is marked as read, which is what keeps a workspace from
// notifying about its own cards the moment somebody switches away from it.
window.asked.some((r) => r.url === '/seen' && r.how === 'POST')
  ? ok('opening a board says, on the server, that somebody is looking at it')
  : fail('nothing told the server this workspace is being read');

// ...AND ONLY WHILE IT IS IN FRONT OF SOMEBODY. A board left open in a
// background tab that went on marking itself read would cancel its own
// notification, which is the one case this whole thing exists for.
{
  const src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
  /function markSeen\(force\) \{[\s\S]{0,600}?document\.hidden/.test(src)
    ? ok('and stops saying so the moment the tab goes behind something')
    : fail('a board in a background tab goes on marking itself read');
}

// IT IS NOT OVER THE LESSON. Everything on this page that interrupts lives
// outside `#chrome`; this is inside it, which is where the things that are true
// and are not what you are doing belong.
{
  const html = fs.readFileSync(path.join(WEB, 'board.html'), 'utf8');
  /<div id="chrome">[\s\S]*id="newsbar"[\s\S]*<\/div><!-- \/#chrome -->/.test(html)
    ? ok('and it is in the chrome, under the bar, not over the lesson')
    : fail('the notification strip is somewhere it can cover the board');
}

// A payload from before T52 that still carries answers and missions draws no
// row for either: there is no list for them on the page any more.
{
  const psych = { id: 'research/PSYCH-ASR', repo: 'PSYCH-ASR', course: 'PSYCH-ASR',
                  card: '0014', title: 'the four typists agree', when: t0 - 240 };
  const mission = { id: 't0007', ws: 'research/PSYCH-ASR', state: 'running',
                    task: 'grade the four typists', at: t0 - 7200 };
  es.onmessage({ data: frame([], { news: [psych], missions: [mission] }) });
  await sleep(60);
  bar().hidden && !doc.getElementById('news-list')
    && !doc.getElementById('mission-list') && !doc.getElementById('mission-progress')
    ? ok('answers from elsewhere and missions are gone: no strip, no list, no panel')
    : fail('the board still draws news or missions');
  typeof window.MissionPanel === 'undefined'
    ? ok('and mission.js is not loaded')
    : fail('the mission panel is still on the page');
}

/* ----------------------------------- a document asked for from THIS sitting

   The only row in this strip that is about the board in front of you. It is in
   the chrome for the same reason the rest of it is: the turn writing a deck must
   not push a proof off the glass, which is the whole design of `POST /artifact`.

   IT EXISTS BECAUSE THAT TURN IS TOLD TO WRITE NO CARD, so nothing about it can
   appear on the board itself and "I asked for a deck and nothing happened" had
   nowhere at all to be answered. */
{
  const papers = () => Array.from(doc.querySelectorAll('#writeup-list .writeup-row'));
  const paper = (over) => Object.assign({
    id: 't0021', makes: 'slides', about: '', at: t0 - 90,
    agent: 'claude', state: 'writing', doc: '',
  }, over || {});

  es.onmessage({ data: frame([paper()]) });
  await sleep(60);
  !bar().hidden && papers().length === 1
    ? ok('a deck asked for mid-sitting says on the board that it is being written')
    : fail('nothing says the document is being written');
  /being written/.test((papers()[0] || {}).textContent || '')
    ? ok('and which of the three states it is in')
    : fail('the row does not say the document is in progress');
  /what this sitting has covered/.test((papers()[0] || {}).textContent || '')
    ? ok('and what it is about, which with nobody naming one is the evening')
    : fail('the row claims nothing about the scope: "'
           + (papers()[0] || {}).textContent + '"');
  papers()[0].tagName !== 'A'
    ? ok('and offers no way to read a document that is not written yet')
    : fail('a document being written pretends to be somewhere to go');

  // AND WHEN IT IS THERE. The library is where it went, so that is where the
  // row goes -- and going there is what retires it, which the SERVER remembers
  // because the fact is about the document rather than about this page.
  es.onmessage({ data: frame([paper({ state: 'done',
                                              doc: 'writeups-harness' })]) });
  await sleep(60);
  /in the library/.test((papers()[0] || {}).textContent || '')
    ? ok('and says when it is in the library')
    : fail('a finished document reads as still being written');
  papers()[0].tagName === 'A'
    && /\/library\?doc=writeups-harness$/.test(papers()[0].getAttribute('href'))
    ? ok('and the row is the way to it, opened on that document')
    : fail('the finished row is not a link to the library');
  papers()[0].dispatchEvent(new window.Event('click'));
  await sleep(30);
  window.asked.some((r) => r.url === '/writeup/seen' && r.how === 'POST')
    ? ok('reading it tells the server, so a second device does not offer it again')
    : fail('nothing told the server the document had been looked at');

  // IT IS NOT WAVED AWAY WHILE IT IS STILL BEING WRITTEN: this is work
  // happening here, and it comes back.
  es.onmessage({ data: frame([paper()]) });
  await sleep(60);
  doc.getElementById('news-hide').dispatchEvent(new window.Event('click'));
  es.onmessage({ data: frame([paper()]) });
  await sleep(60);
  !bar().hidden && papers().length === 1
    ? ok('and a document still being written cannot be dismissed, because it is '
         + 'still being written')
    : fail('waving the strip away silenced work happening here');

  // BUT A FINISHED ONE IS. `✕` on a landed document retires it on the server,
  // and the payloads that still carry it before the record changes do not
  // paint the strip back up.
  window.asked.length = 0;
  const landed = paper({ id: 't0022', state: 'done', doc: 'writeups-harness' });
  es.onmessage({ data: frame([landed]) });
  await sleep(60);
  doc.getElementById('news-hide').dispatchEvent(new window.Event('click'));
  await sleep(30);
  window.asked.some((r) => r.url === '/writeup/seen' && r.how === 'POST')
    ? ok('waving off a finished document tells the server it has been seen')
    : fail('the cross on a finished document told the server nothing');
  es.onmessage({ data: frame([landed]) });
  await sleep(60);
  bar().hidden
    ? ok('and it does not come back on the next payload')
    : fail('a finished document waved off came straight back');
}

console.log(errors.length ? '\n' + errors.length + ' FAILURES'
  : '\na document asked for here says it is being written, and where it landed');
process.exit(errors.length ? 1 : 0);

})();
