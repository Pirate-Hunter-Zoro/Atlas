// A canvas's "Save to…" picker on a link that holds its requests.
//
// The iPad's link once held every request for twelve minutes and then
// delivered them all at once. The picker had asked for /subjects.json with
// nothing kept and no wait on it, so it opened on "+ new course", "+ new
// project" and "not yet" and nothing else: no Random lessons, no course, no
// word that it was asking. Checked here, against a fetch that answers only
// when told to:
//
//   1. the last list that came is kept and painted the instant the panel
//      opens, Random lessons first, and the fresh one repaints it;
//   2. with nothing kept the panel says it is asking, then (WAIT_MS later)
//      that the list did not come, with "try again", which works;
//   3. a list that fails says so;
//   4. Save, End, Give and a new course, not answered, say they are still
//      waiting, are never asked twice, and act on the answer when it comes;
//      End goes ahead over a Save not yet answered on a canvas bound to
//      nothing, naming its subject, and waits for a held move; Give waits for
//      a held Save or End, End for a held Give; a subject tapped or made
//      while a Save is held is refused by name; a refused End repaints the
//      list it held;
//   5. a save still on its way does not hold Save for ever, and End waits
//      for it rather than ending over it;
//   6. nor do End and Give go over a refused save waiting to be tried again.
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
const check = (m, c, why) => (c ? ok(m) : fail(m + (why ? ' — ' + why : '')));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const W = 900, H = 500;
const SID = '20261029-190000';
const B = '/s/' + SID;
const WAIT = 150;          // WAIT_MS, shortened: the page's own is ten seconds
const KEY = 'board.subjects';
const LIST = { ok: true, scratch: 'courses/Random', subjects: [
  { id: 'courses/Galois-Theory', kind: 'course', slug: 'Galois-Theory', name: 'Galois Theory' },
  { id: 'courses/Random', kind: 'course', slug: 'Random', name: 'Random lessons' },
  { id: 'projects/Mosaic', kind: 'project', slug: 'Mosaic', name: 'Mosaic' }] };

// A canvas, bound to nothing unless `state` says so. `net` answers a request
// with a value, or returns undefined to hold it for ever; `kept` is what this
// device already has under `board.subjects`.
function mount(net, opts) {
  opts = opts || {};
  const d = new JSDOM(fs.readFileSync(path.join(WEB, 'slate.html'), 'utf8'), {
    runScripts: 'outside-only', pretendToBeVisual: true,
    url: 'https://board.test' + B + '/slate',
  });
  const w = d.window;
  w.HTMLCanvasElement.prototype.getContext = () =>
    new Proxy({}, { get: () => () => {}, set: () => true });
  w.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,AAAA';
  Object.defineProperty(w.HTMLElement.prototype, 'clientWidth', { get: () => W });
  Object.defineProperty(w.HTMLElement.prototype, 'clientHeight', { get: () => H });
  w.HTMLElement.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: W, height: H, right: W, bottom: H, x: 0, y: 0 };
  };
  w.Element.prototype.scrollIntoView = function () {};
  w.Element.prototype.setPointerCapture = function () {};
  w.Element.prototype.releasePointerCapture = function () {};
  w.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  if (opts.kept) w.localStorage.setItem(KEY, JSON.stringify(opts.kept));
  w.asked = [];
  w.fetch = (u, init) => {
    const url = String(u);
    const body = init && init.body ? JSON.parse(init.body) : null;
    w.asked.push({ url, method: (init && init.method) || 'GET', body,
                   signal: !!(init && init.signal) });
    let got;
    if (url === B + '/slate/state') got = { pages: [] };
    else if (url === B + '/board.json' && !net.hasOwnProperty(url)) {
      got = { state: Object.assign({ id: SID, view: 'slate', title: 'Canvas', ended: null },
                                   opts.state || {}), cards: [] };
    } else {
      const h = net[url];
      got = typeof h === 'function' ? h(body, w) : h;
    }
    if (got === undefined) return new Promise(() => {});
    if (got instanceof Error) return Promise.reject(got);
    if (got && typeof got.then === 'function') {
      return got.then((v) => ({ ok: true, json: () => Promise.resolve(v) }));
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve(got) });
  };
  w.addEventListener('error', (e) => fail('uncaught: ' + e.message));
  w.__went = [];
  for (const f of ['typeface.js', 'ink-clip.js', 'plane-core.js', 'ink-core.js',
                   'slate-core.js', 'slate.js']) {
    let src = fs.readFileSync(path.join(WEB, f), 'utf8');
    if (f === 'slate.js') {
      src = src.replace('var WAIT_MS = 10000;', 'var WAIT_MS = ' + WAIT + ';')
        .replace('function go(url) { window.location.href = url; }',
                 'function go(url) { window.__went.push(url); }');
    }
    try { w.eval(src); } catch (e) { fail(f + ': ' + e.message); }
  }
  return w;
}

const rows = (w) => Array.from(w.document.querySelectorAll('#notes-send-list button[data-subject]'))
  .map((b) => b.textContent);
const waitLine = (w) => {
  const p = w.document.querySelector('#notes-send-list .notes-send-wait');
  return p ? p.textContent : '';
};
const again = (w) => w.document.querySelector('#notes-send-list .notes-send-again');
const said = (w) => w.document.getElementById('notes-send-said').textContent;
const asks = (w, url) => w.asked.filter((a) => a.url === url).length;

(async () => {
  // 1. Kept: painted at once, Random lessons first, and the fresh one repaints.
  {
    let answer;
    const fresh = new Promise((r) => { answer = r; });
    const kept = { scratch: 'courses/Random', subjects: [
      { id: 'courses/Random', kind: 'course', slug: 'Random', name: 'Random lessons' },
      { id: 'courses/Old', kind: 'course', slug: 'Old', name: 'Old course' }] };
    const w = mount({ '/subjects.json': () => fresh, '/sessions.json': { sessions: [] } },
                    { kept });
    await sleep(40);
    check('the canvas asks for /subjects.json as it opens, before any tap',
          asks(w, '/subjects.json') === 1 && w.document.getElementById('notes-send').hidden);
    w.document.getElementById('canvas-save').click();
    check('"Save to…" paints the kept list at once, Random lessons first, '
          + 'while the fresh one is still on its way',
          rows(w).join(',') === 'Random lessons,Old course' && !waitLine(w),
          rows(w).join(',') + ' / ' + waitLine(w));
    answer(LIST);
    await sleep(20);
    check('and the fresh one repaints it, and is kept for next time',
          rows(w).join(',') === 'Random lessons,Galois Theory,Mosaic'
          && JSON.parse(w.localStorage.getItem(KEY)).subjects.length === 3,
          rows(w).join(','));
    w.close();
  }

  // 2. Nothing kept, nothing answered: asking, then not come, then try again.
  {
    const net = { '/sessions.json': { sessions: [] } };
    const w = mount(net);
    await sleep(20);
    w.document.getElementById('canvas-save').click();
    check('with nothing kept the panel says it is asking, not nothing',
          !w.document.getElementById('notes-send').hidden && rows(w).length === 0
          && /Getting the courses and projects/.test(waitLine(w)) && !again(w),
          waitLine(w));
    check('and the request carries a signal, so it can be abandoned',
          w.asked.some((a) => a.url === '/subjects.json' && a.signal));
    await sleep(WAIT + 60);
    check('not answered in WAIT_MS, it says the list did not come in time, with "try again"',
          /did not come in time/.test(waitLine(w)) && !!again(w), waitLine(w));
    net['/subjects.json'] = LIST;
    const before = asks(w, '/subjects.json');
    again(w).click();
    await sleep(20);
    check('"try again" asks again and paints it, Random lessons first',
          asks(w, '/subjects.json') === before + 1
          && rows(w)[0] === 'Random lessons' && !waitLine(w) && !again(w),
          rows(w).join(',') + ' / ' + waitLine(w));
    w.close();
  }

  // 3. A list that fails says so, and the kept rows stay.
  {
    const w = mount({ '/subjects.json': () => new Error('Load failed'),
                      '/sessions.json': { sessions: [] } });
    await sleep(20);
    w.document.getElementById('canvas-save').click();
    await sleep(20);
    check('a list that fails says it did not come, with "try again"',
          /did not come\./.test(waitLine(w)) && !!again(w) && rows(w).length === 0,
          waitLine(w));
    w.close();
    const k = mount({ '/subjects.json': () => new Error('Load failed'),
                      '/sessions.json': { sessions: [] } }, { kept: LIST });
    await sleep(20);
    k.document.getElementById('canvas-save').click();
    await sleep(20);
    check('and with a list kept, those rows stay, said to be last time\'s',
          rows(k)[0] === 'Random lessons' && /last time/.test(waitLine(k)), waitLine(k));
    k.close();
  }

  // A request held until `.go(value)` lets it answer.
  const held = () => {
    let go;
    const p = new Promise((r) => { go = r; });
    p.go = go;
    return p;
  };

  // 4a. Save not answered: held, said to be waiting, and its answer, when it
  //     comes, is the one the page shows; End waits for it.
  {
    const bind = held();
    const net = { '/subjects.json': LIST, '/sessions.json': { sessions: [] },
                  [B + '/bind']: () => bind };
    const w = mount(net);
    await sleep(20);
    w.document.getElementById('canvas-save').click();
    await sleep(20);
    const random = () => w.document.querySelector(
      '#notes-send-list button[data-subject="courses/Random"]');
    random().click();
    await sleep(10);
    check('a tap on Random lessons says "saving…"', said(w) === 'saving…', said(w));
    await sleep(WAIT + 60);
    check('not answered in WAIT_MS, it says the board has not answered yet, not "Not saved"',
          /has not answered yet/.test(said(w)) && !/Not saved/.test(said(w)), said(w));
    random().click();
    await sleep(10);
    check('and a tap again does not ask a second time',
          asks(w, B + '/bind') === 1 && /has not answered yet/.test(said(w)), said(w));
    w.document.querySelector('#notes-send-list button[data-subject="courses/Galois-Theory"]').click();
    await sleep(10);
    check('a tap on another subject while it is held is refused, saying so by name, '
          + 'not answered with "it is saved when it does"',
          asks(w, B + '/bind') === 1 && /Not saved in Galois Theory/.test(said(w))
          && /save in Random lessons/.test(said(w)) && !/saved when it does/.test(said(w)),
          said(w));
    w.document.getElementById('notes-send-back').click();
    const give = w.document.getElementById('canvas-give');
    give.click();
    give.click();
    await sleep(10);
    check('Give waits for it, saying so, and is not asked',
          asks(w, B + '/give') === 0 && /wait: Save to/.test(give.textContent), give.textContent);
    const end = w.document.getElementById('notes-end');
    end.click();
    check('End, bound to nothing, does not wait for it: it opens, with no "Keep it unfiled"',
          !w.document.getElementById('canvas-end').hidden
          && w.document.getElementById('canvas-end-unfiled').hidden, end.textContent);
    w.document.getElementById('canvas-end-back').click();
    bind.go({ ok: true, changed: true, subject: { id: 'courses/Random', name: 'Random lessons' } });
    await sleep(20);
    check('the answer, when it comes, binds it on the page',
          /in Random lessons/.test(w.document.getElementById('canvas-save').textContent));
    check('and Give says its own name again', give.textContent === 'Give to the tutor',
          give.textContent);
    end.click();
    check('and End then offers no "Keep it unfiled"',
          !w.document.getElementById('canvas-end').hidden
          && w.document.getElementById('canvas-end-unfiled').hidden);
    w.close();

    const n = mount({ '/subjects.json': LIST, '/sessions.json': { sessions: [] },
                      [B + '/bind']: () => new Error('Load failed') });
    await sleep(20);
    n.document.getElementById('canvas-save').click();
    await sleep(20);
    n.document.querySelector('#notes-send-list button[data-subject="courses/Random"]').click();
    await sleep(20);
    check('a bind that fails says it may not be saved, and to tap again to make sure',
          /may not be saved/.test(said(n)) && /Tap it again/.test(said(n)), said(n));
    n.close();
  }

  // 4f. A bind that never answers does not hold End: End names its subject.
  {
    const net = { '/subjects.json': LIST, '/sessions.json': { sessions: [] },
                  [B + '/bind']: () => undefined,
                  [B + '/end']: (body) => ({ ok: true, session: {},
                    sent: { id: body.subject, name: 'Random lessons' } }) };
    const w = mount(net);
    await sleep(20);
    w.document.getElementById('canvas-save').click();
    await sleep(10);
    w.document.querySelector('#notes-send-list button[data-subject="courses/Random"]').click();
    await sleep(WAIT * 3);
    w.document.getElementById('notes-send-back').click();
    const end = w.document.getElementById('notes-end');
    end.click();
    w.document.querySelector('#canvas-end [data-end="keep"]').click();
    await sleep(30);
    const asked = w.asked.filter((a) => a.url === B + '/end');
    check('with a /bind that never answers, End still ends, naming the subject the bind names',
          asked.length === 1 && asked[0].body.subject === 'courses/Random'
          && /ended: the pages are in Random lessons/.test(end.textContent), end.textContent);
    w.close();
  }

  // 4g. A held move off the subject it is bound to is waited for, and End
  //     says its own name again once it answers.
  {
    const bind = held();
    const w = mount({ '/subjects.json': LIST, '/sessions.json': { sessions: [] },
                      [B + '/bind']: () => bind },
                    { state: { subject: 'courses/Galois-Theory', course: 'Galois Theory' } });
    await sleep(20);
    w.document.getElementById('canvas-save').click();
    await sleep(10);
    w.document.querySelector('#notes-send-list button[data-subject="courses/Random"]').click();
    await sleep(10);
    w.document.getElementById('notes-send-back').click();
    const end = w.document.getElementById('notes-end');
    end.click();
    check('End waits for a held move, saying so',
          w.document.getElementById('canvas-end').hidden && /wait: Save to/.test(end.textContent),
          end.textContent);
    bind.go({ ok: true, changed: true, subject: { id: 'courses/Random', name: 'Random lessons' } });
    await sleep(20);
    check('and once it answers, End says "End" again, not "wait"', end.textContent === 'End',
          end.textContent);
    w.close();
  }

  // 4h. A course made while a bind is held is offered, not silently dropped.
  {
    const bind = held();
    const w = mount({ '/subjects.json': LIST, '/sessions.json': { sessions: [] },
                      [B + '/bind']: (body) => (body.subject === 'courses/Random' ? bind
                        : { ok: true, changed: true, subject: { id: body.subject, name: 'Topology' } }),
                      '/subjects/new': (body) => ({ ok: true, subject:
                        { id: 'courses/' + body.name, kind: 'course', slug: body.name, name: body.name } }) });
    await sleep(20);
    w.document.getElementById('canvas-save').click();
    await sleep(10);
    w.document.querySelector('#notes-send-list button[data-subject="courses/Random"]').click();
    await sleep(10);
    w.document.getElementById('notes-new-course').click();
    w.document.getElementById('notes-send-name').value = 'Topology';
    w.document.getElementById('notes-send-go').click();
    await sleep(20);
    check('a course made while a Save to… is held says it is made but not saved in yet, '
          + 'and is in the list',
          asks(w, B + '/bind') === 1 && /Topology is made/.test(said(w))
          && /save in Random lessons/.test(said(w)) && rows(w).indexOf('Topology') >= 0,
          said(w) + ' / ' + rows(w).join(','));
    bind.go({ ok: true, changed: true, subject: { id: 'courses/Random', name: 'Random lessons' } });
    await sleep(20);
    w.document.getElementById('canvas-save').click();
    await sleep(10);
    w.document.querySelector('#notes-send-list button[data-subject="courses/Topology"]').click();
    await sleep(20);
    check('and a tap on it once that answers saves it there',
          w.asked.some((a) => a.url === B + '/bind' && a.body.subject === 'courses/Topology')
          && /in Topology/.test(w.document.getElementById('canvas-save').textContent));
    w.close();
  }

  // 4b. End not answered: held, never asked twice, ended when it answers.
  {
    const answer = held();
    const net = { '/subjects.json': LIST, '/sessions.json': { sessions: [] },
                  [B + '/end']: () => answer };
    const w = mount(net, { state: { subject: 'courses/Random', course: 'Random lessons' } });
    await sleep(20);
    const end = w.document.getElementById('notes-end');
    end.click();
    w.document.querySelector('#canvas-end [data-end="keep"]').click();
    await sleep(10);
    check('End says "ending…" while it is asked', end.textContent === 'ending…');
    await sleep(WAIT + 60);
    check('not answered in WAIT_MS, it says so and stays held',
          /has not answered yet/.test(end.textContent) && end.disabled, end.textContent);
    end.click();
    await sleep(10);
    check('and is not asked a second time',
          asks(w, B + '/end') === 1 && w.document.getElementById('canvas-end').hidden);
    const give = w.document.getElementById('canvas-give');
    give.click();
    give.click();
    await sleep(10);
    check('Give waits for a held End, saying so, and is not asked',
          asks(w, B + '/give') === 0 && /wait: End/.test(give.textContent), give.textContent);
    answer.go({ ok: true, session: {} });
    await sleep(20);
    check('and says its own name again once End answers', give.textContent === 'Give to the tutor',
          give.textContent);
    check('the answer, when it comes, ends it',
          /ended: the pages are in Random lessons/.test(end.textContent), end.textContent);
    w.close();
  }

  // 4c. A refused End repaints the list it held, kept-for-nothing or not.
  {
    const list = held();
    const end = held();
    const w = mount({ '/subjects.json': () => list, '/sessions.json': { sessions: [] },
                      [B + '/end']: () => end });
    await sleep(20);
    w.document.getElementById('notes-end').click();
    w.document.querySelector('#canvas-end [data-end="keep"]').click();
    await sleep(10);
    check('End, keep, bound to nothing opens the picker, asking',
          /Getting the courses/.test(waitLine(w)), waitLine(w));
    w.document.getElementById('notes-send-skip').click();
    await sleep(10);
    list.go(LIST);
    await sleep(10);
    end.go({ ok: false, error: 'refused' });
    await sleep(20);
    check('the list that came while it was ending is painted once the End is refused',
          rows(w)[0] === 'Random lessons' && !waitLine(w) && /Not ended: refused/.test(said(w)),
          rows(w).join(',') + ' / ' + waitLine(w) + ' / ' + said(w));
    w.close();

    const end2 = held();
    const n = mount({ '/subjects.json': () => undefined, '/sessions.json': { sessions: [] },
                      [B + '/end']: () => end2 });
    await sleep(20);
    n.document.getElementById('notes-end').click();
    n.document.querySelector('#canvas-end [data-end="keep"]').click();
    await sleep(10);
    n.document.getElementById('notes-send-skip').click();
    await sleep(WAIT + 60);
    end2.go({ ok: false, error: 'refused' });
    await sleep(20);
    check('and one that did not come in time says so, with "try again"',
          /did not come in time/.test(waitLine(n)) && !!again(n), waitLine(n));
    n.close();
  }

  // 4d. Give not answered: held, never given twice, opens the board when it answers.
  {
    const answer = held();
    const w = mount({ '/subjects.json': LIST, '/sessions.json': { sessions: [] },
                      [B + '/give']: () => answer });
    await sleep(20);
    const give = w.document.getElementById('canvas-give');
    give.click();
    give.click();
    await sleep(10);
    check('Give says "giving…" while it is asked', give.textContent === 'giving…');
    await sleep(WAIT + 60);
    check('not answered in WAIT_MS, it says so and stays held',
          /has not answered yet/.test(give.textContent) && give.disabled, give.textContent);
    give.click();
    give.click();
    await sleep(10);
    check('and is not given a second time', asks(w, B + '/give') === 1);
    const end = w.document.getElementById('notes-end');
    end.click();
    check('End waits for a held Give, saying so',
          w.document.getElementById('canvas-end').hidden && /wait: Give/.test(end.textContent),
          end.textContent);
    answer.go({ ok: true, url: B + '/board' });
    await sleep(20);
    check('the answer, when it comes, opens the board', w.__went.indexOf(B + '/board') >= 0);
    w.close();
  }

  // 4e. A course made on a held link is made once, and filed into when it answers.
  {
    const made = held();
    const net = { '/subjects.json': LIST, '/sessions.json': { sessions: [] },
                  '/subjects/new': () => made,
                  [B + '/bind']: (body) => ({ ok: true, changed: true,
                    subject: { id: body.subject, name: 'Topology' } }) };
    const w = mount(net);
    await sleep(20);
    w.document.getElementById('canvas-save').click();
    await sleep(10);
    w.document.getElementById('notes-new-course').click();
    w.document.getElementById('notes-send-name').value = 'Topology';
    const go = w.document.getElementById('notes-send-go');
    go.click();
    await sleep(WAIT + 60);
    check('a course not made in WAIT_MS is said to be waiting, not "Not made"',
          /has not answered yet/.test(said(w)) && !/Not made/.test(said(w)), said(w));
    go.click();
    await sleep(10);
    check('and a tap again does not ask to make it twice', asks(w, '/subjects/new') === 1);
    made.go({ ok: true, subject: { id: 'courses/Topology', name: 'Topology' } });
    await sleep(30);
    check('the answer, when it comes, saves the canvas there',
          w.asked.some((a) => a.url === B + '/bind' && a.body.subject === 'courses/Topology')
          && /in Topology/.test(w.document.getElementById('canvas-save').textContent));
    w.close();
  }
  // 5. A save still on its way: Save goes ahead after WAIT_MS, End waits for it.
  {
    const net = { '/subjects.json': LIST, '/sessions.json': { sessions: [] },
                  [B + '/slate/save']: () => undefined,
                  [B + '/bind']: (body) => ({ ok: true, changed: true,
                    subject: { id: body.subject, name: 'Random lessons' } }) };
    const w = mount(net);
    await sleep(30);
    const sheet = w.document.querySelector('canvas.sl-sheet');
    const pen = (type, x, y) => {
      const ev = new w.Event(type, { bubbles: true, cancelable: true });
      Object.assign(ev, { pointerId: 7, pointerType: 'pen', pressure: 0.6,
                          clientX: x, clientY: y, isPrimary: true });
      ev.getCoalescedEvents = () => [ev];
      sheet.dispatchEvent(ev);
    };
    pen('pointerdown', 100, 100);
    for (let i = 0; i < 12; i++) pen('pointermove', 100 + i * 10, 100 + i);
    pen('pointerup', 220, 112);
    w.document.getElementById('canvas-save').click();
    await sleep(20);
    w.document.querySelector('#notes-send-list button[data-subject="courses/Random"]').click();
    await sleep(WAIT * 2 + 80);
    check('with a save held on the wire, Save to… still files it once WAIT_MS has passed',
          w.asked.some((a) => a.url === B + '/slate/save')
          && w.asked.filter((a) => a.url === B + '/bind').length === 1
          && /in Random lessons/.test(w.document.getElementById('canvas-save').textContent),
          said(w));
    const end = w.document.getElementById('notes-end');
    end.click();
    w.document.querySelector('#canvas-end [data-end="keep"]').click();
    await sleep(WAIT + 60);
    check('but End will not end over a save still on its way, and says why',
          !w.asked.some((a) => a.url === B + '/end') && !end.disabled
          && /still on their way/.test(end.textContent), end.textContent);
    w.close();
  }

  // 6. A save the board refused, waiting to be tried again: End and Give
  //    will not end or give over it either.
  {
    const net = { '/subjects.json': LIST, '/sessions.json': { sessions: [] },
                  [B + '/slate/save']: () => new Error('Load failed'),
                  [B + '/end']: { ok: true, session: {} }, [B + '/give']: { ok: true } };
    const w = mount(net, { state: { subject: 'courses/Random', course: 'Random lessons' } });
    await sleep(30);
    const sheet = w.document.querySelector('canvas.sl-sheet');
    const pen = (type, x, y) => {
      const ev = new w.Event(type, { bubbles: true, cancelable: true });
      Object.assign(ev, { pointerId: 7, pointerType: 'pen', pressure: 0.6,
                          clientX: x, clientY: y, isPrimary: true });
      ev.getCoalescedEvents = () => [ev];
      sheet.dispatchEvent(ev);
    };
    pen('pointerdown', 100, 100);
    for (let i = 0; i < 12; i++) pen('pointermove', 100 + i * 10, 100 + i);
    pen('pointerup', 220, 112);
    const end = w.document.getElementById('notes-end');
    end.click();
    w.document.querySelector('#canvas-end [data-end="keep"]').click();
    await sleep(60);
    check('End will not end over a refused save waiting to be tried again',
          w.asked.some((a) => a.url === B + '/slate/save') && asks(w, B + '/end') === 0
          && !end.disabled && /still on their way/.test(end.textContent), end.textContent);
    const give = w.document.getElementById('canvas-give');
    give.click();
    give.click();
    await sleep(60);
    check('and nor will Give', asks(w, B + '/give') === 0
          && /still on their way/.test(give.textContent), give.textContent);
    w.close();
  }

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\nthe picker is never blank while it waits, and nothing is asked twice');
  process.exit(errors.length ? 1 : 0);
})();
