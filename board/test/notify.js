// AN ANSWER THAT LANDED SOMEWHERE NOBODY WAS LOOKING.
//
// Asked for in these words:
//
//   "maybe something I give the agent to do or think about is going to take a
//    while. I want to be able to go into a different section of a project, or a
//    different fucking project completely, and put other agents to work on other
//    things while the first one is working. We should set up a notification
//    system where if a response that takes a while comes back in a session, I'll
//    get notified somewhere in the app and can click that notification to take me
//    back to that tutoring session."
//
// Three things have to be true for that to be worth having, and two of them are
// about restraint:
//
//   * IT HAS TO SAY SO. A turn that finishes in an empty room has to leave
//     something on the surface the person IS looking at.
//   * IT MUST NOT INTERRUPT. It is news about somewhere else. It goes in the
//     chrome, with everything else that is true and is not what they are doing --
//     never over the lesson, and never over the board they are writing on.
//   * THE ROW IS THE WAY BACK. "click that notification to take me back to that
//     tutoring session" -- so the row carries the workspace's address, and it
//     goes through the front door, which is the only thing that can move the one
//     https name from one board to another.
//
// Both surfaces carry it, and both are driven here: the board (the strip) and the
// front door (the row under the hero, and the badge on the card).

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
    return /slate\/state/.test(String(u))
      ? Promise.resolve({ json: () => Promise.resolve({ pages: [] }) })
      : new Promise(() => {});
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
  for (const f of ['typeface.js', 'macros.js', 'gauge.js', 'plane-core.js',
                   'slate-core.js', 'annotate.js', 'address.js', 'board.js']) {
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
const rows = () => Array.from(doc.querySelectorAll('.news-row'));

const frame = (news) => JSON.stringify({
  state: { course: 'Galois Theory', session: 'lecture' },
  cards: [{ id: '0001', kind: 'lesson', title: '', body: 'A field is a ring.',
            mtime: t0 - 600 }],
  turns: [], agent: { agent: 'claude', state: 'listening', turns: 2 },
  waiting: null, history: 0, news: news || [],
});

// Nothing elsewhere: nothing to say, and saying something anyway is furniture.
es.onmessage({ data: frame([]) });
await sleep(60);
bar().hidden
  ? ok('with nothing waiting anywhere else, there is no strip')
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

// --------------------------------------------- and then one comes back
const psych = { id: 'research/PSYCH-ASR', repo: 'PSYCH-ASR', family: 'research',
                course: 'PSYCH-ASR', chapter: 'cli', card: '0014',
                title: 'the four typists agree', when: t0 - 240 };
const trd = { id: 'research/TRD-EHR', repo: 'TRD-EHR', family: 'research',
              course: 'TRD-EHR', chapter: '', card: '0008',
              title: '', when: t0 - 30 };

es.onmessage({ data: frame([trd, psych]) });
await sleep(60);

!bar().hidden && rows().length === 2
  ? ok('two turns that finished elsewhere are two rows')
  : fail('the strip shows ' + rows().length + ' of 2 answers');
/PSYCH-ASR/.test(rows()[1].textContent)
  ? ok('each says which workspace answered')
  : fail('a row does not name its workspace: "' + rows()[1].textContent + '"');
/the four typists agree/.test(rows()[1].textContent)
  ? ok('and what the card is, when the card said')
  : fail('the row says nothing about the answer: "' + rows()[1].textContent + '"');
/wrote a card|TRD-EHR/.test(rows()[0].textContent)
  ? ok('and claims nothing when it did not')
  : fail('an untitled card invented a title: "' + rows()[0].textContent + '"');

// IT IS NOT OVER THE LESSON. Everything on this page that interrupts lives
// outside `#chrome`; this is inside it, which is where the things that are true
// and are not what you are doing belong.
{
  const html = fs.readFileSync(path.join(WEB, 'board.html'), 'utf8');
  /<div id="chrome">[\s\S]*id="newsbar"[\s\S]*<\/div><!-- \/#chrome -->/.test(html)
    ? ok('and it is in the chrome, under the bar, not over the lesson')
    : fail('the notification strip is somewhere it can cover the board');
}

// ------------------------------------------- and the row is the way back
//
// A LINK, spelled with the address grammar. "click that notification to take me
// back to that tutoring session" -- so the row goes to the front door carrying
// the workspace's address, which is the one thing that can move the single https
// name from this board to that one. Being a link rather than a handler is what
// makes it hold-to-open, readable, and testable as what it is.
{
  const at = rows()[1].getAttribute('href');
  at === '/#/w/research/PSYCH-ASR'
    ? ok('and the row IS the way back — the front door, carrying that '
         + "workspace's address")
    : fail('the row points at "' + at + '"');
  rows()[1].tagName === 'A'
    ? ok('and it is a link, so it can be held down, read and opened like one')
    : fail('the row is a ' + rows()[1].tagName + ', not a link');
}

// ------------------------------------------------- and it can be waved away
{
  doc.getElementById('news-hide').dispatchEvent(new window.Event('click'));
  bar().hidden
    ? ok('and it can be put away')
    : fail('the strip cannot be dismissed');
  es.onmessage({ data: frame([trd, psych]) });
  await sleep(60);
  bar().hidden
    ? ok('and stays away for the answers it was dismissed over')
    : fail('a dismissed notification came straight back');

  // But the NEXT answer in that workspace is a different answer.
  es.onmessage({ data: frame([Object.assign({}, psych, { when: t0 - 5,
                                                         title: 'and here is why' })]) });
  await sleep(60);
  !bar().hidden && /and here is why/.test((rows()[0] || {}).textContent || '')
    ? ok('and comes back for the next one, which is a different fact')
    : fail('dismissing one answer silenced the workspace');
}

/* --------------------------------------------------------- the front door */
{
  const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'home.html'), 'utf8'), {
    runScripts: 'outside-only', pretendToBeVisual: true, url: 'https://board.test/',
  });
  const w = dom.window;
  const d = w.document;
  w.HTMLCanvasElement.prototype.getContext = () =>
    new Proxy({}, { get: () => () => {}, set: () => true });
  Object.defineProperty(w.HTMLElement.prototype, 'clientWidth', { get: () => 900 });
  Object.defineProperty(w.HTMLElement.prototype, 'clientHeight', { get: () => 600 });
  w.HTMLElement.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: 900, height: 600, right: 900, bottom: 600, x: 0, y: 0 };
  };
  w.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  w.scrollTo = function () {};
  w.fetch = () => new Promise(() => {});
  w.addEventListener('error', (e) => fail('home: uncaught: ' + e.message));
  for (const f of ['typeface.js', 'address.js', 'gauge.js', 'recentre.js',
                   'plane-core.js', 'home.js']) {
    let src = fs.readFileSync(path.join(WEB, f), 'utf8');
    if (f === 'home.js') src = src.replace('})();', 'window.__atlas = paintAtlas;\n})();');
    try { w.eval(src); } catch (e) { fail('home: ' + f + ': ' + e.message); }
  }

  const payload = {
    families: [{ id: 'research', name: 'Research' }],
    workspaces: [
      { id: 'research/PSYCH-ASR', repo: 'PSYCH-ASR', family: 'research',
        family_name: 'Research', course: 'PSYCH-ASR', chapter: 'cli',
        root: '/x/research/PSYCH-ASR', current: false, cards: 14, open: 3,
        next: 'grade the pilot', kind: 'project', touched: t0 - 900,
        news: true, news_at: t0 - 240, news_title: 'the four typists agree' },
      { id: 'research/TRD-EHR', repo: 'TRD-EHR', family: 'research',
        family_name: 'Research', course: 'TRD-EHR', chapter: '',
        root: '/x/research/TRD-EHR', current: true, cards: 2, open: 1,
        next: 'the packet', kind: 'project', touched: t0 - 60,
        news: false, news_at: 0, news_title: '' },
    ],
  };
  w.__atlas(payload);
  await sleep(40);

  const panel = d.getElementById('answers');
  const list = Array.from(d.querySelectorAll('.answer-row'));
  panel && !panel.hidden && list.length === 1
    ? ok('the front door says an answer came back while you were away')
    : fail('the front door is silent about a finished turn');
  list.length && /PSYCH-ASR/.test(list[0].textContent)
    ? ok('and which workspace it is in')
    : fail('the row does not name the workspace');
  list.length && /the four typists agree/.test(list[0].textContent)
    ? ok('and what it says')
    : fail('the row says nothing about the card');

  // And on the picture itself, because the atlas is what the front door IS.
  d.querySelector('.card-news')
    ? ok('and the workspace is badged on the map of everything')
    : fail('nothing on the atlas marks the workspace that answered');

  // NEVER ABOUT THE ONE YOU ARE IN. A badge on the card you are standing in is
  // furniture: the lesson is one tap away and you are about to read it anyway.
  d.querySelectorAll('.card-news').length === 1
    ? ok('and only that one — the workspace you are in is never badged')
    : fail('the current workspace was badged as unread');
}

console.log(errors.length ? '\n' + errors.length + ' FAILURES'
  : '\nwork that came back while you were elsewhere says so, and is one tap away');
process.exit(errors.length ? 1 : 0);

})();
