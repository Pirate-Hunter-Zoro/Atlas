// THE START SCREEN (T23).
//
//   1. With a stubbed server: the sections in order, a Continue row with its
//      subject, last card and new count, notices that dismiss, + new project
//      made from its name, and the address grammar -- `#/s/` carried to
//      the session's board, and an old `#/w/` link followed nowhere. The
//      re-centre pill placed off the bar; the boot check's Retry line and
//      the beacon to /client-error; a failed refresh tried again; the Tutor
//      chooser under New session saying who takes the next turn; the search,
//      the most-recently-used order and the newest ten past sessions; a
//      subject deleted from its row (and the ones that cannot be, saying
//      why); and an unbound past session sent to a course or project.
//   2. Against a real server on a temp Atlas holding a Galois session with
//      45 cards, so card 0003 is older than the board's window of 40: `/`
//      asks nothing of the old switch route or /atlas.json, New session opens an unbound
//      session in teach, "Linear Algebra" made as a course is listed and
//      committed, no visible control gets a 404, and `#/s/<id>/card/0003`
//      from the start screen lands on that card in the Galois session's
//      board.
//
// jsdom is a development-only dependency; without it this skips.

const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const { spawn, execFileSync } = require('child_process');

let JSDOM;
try {
  ({ JSDOM } = require('jsdom'));
} catch (e) {
  console.log('skip  jsdom is not installed — `npm install jsdom` to run this test');
  process.exit(0);
}

const BOARD = path.join(__dirname, '..');
const WEB = path.join(BOARD, 'web');
const errors = [];
const ok = (m) => console.log('ok   ' + m);
const fail = (m) => { errors.push(m); console.log('FAIL ' + m); };
const check = (m, cond) => (cond ? ok(m) : fail(m));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function until(test, ms) {
  for (let t = 0; t < ms; t += 50) {
    if (test()) return true;
    await sleep(50);
  }
  return !!test();
}

// The page's one navigation, recorded instead of followed.
function patched(src) {
  const from = 'function go(url) { window.location.href = url; }';
  if (src.indexOf(from) < 0) fail('home.js has no go(url) to record');
  return src.replace(from, 'function go(url) { window.__went.push(url); }');
}

function quiet(window) {
  window.HTMLCanvasElement.prototype.getContext = () =>
    new Proxy({}, { get: () => () => {}, set: () => true });
  window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
  Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => 900 });
  Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 600 });
  window.HTMLElement.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: 900, height: 600, right: 900, bottom: 600, x: 0, y: 0 };
  };
  window.Element.prototype.setPointerCapture = function () {};
  window.Element.prototype.releasePointerCapture = function () {};
  window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  window.scrollTo = function () {};
  window.renderMathInElement = () => {};
  window.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {},
                               addEventListener() {}, removeEventListener() {} });
  window.caches = { keys: () => Promise.resolve([]) };
}

/* ======================================================= 1. a stubbed server */
async function stubbed() {
  const SID = '20261008-201500';
  const GAL = '20261001-090000';
  const LECT = '20260830-090000';
  const now = Date.now() / 1000;
  // Ten more ended sessions on Galois, so Past sessions has twelve.
  const older = [];
  for (let dd = 20; dd > 10; dd--) {
    older.push({ id: '202608' + dd + '-090000', title: 'Past ' + dd,
                 subject: 'courses/Galois-Theory', subject_name: 'Galois Theory',
                 mode: 'teach', opened: '2026-08-' + dd + ' 09:00:00',
                 ended: '2026-08-' + dd + ' 10:00:00', url: '/s/202608' + dd + '-090000/board' });
  }
  const SUBJECTS = [
    { id: 'courses/Galois-Theory', kind: 'course', slug: 'Galois-Theory', name: 'Galois Theory' },
    { id: 'courses/Probability', kind: 'course', slug: 'Probability', name: 'Probability' },
    { id: 'projects/Mosaic', kind: 'project', slug: 'Mosaic', name: 'Mosaic' },
    { id: 'projects/Cohort-Study', kind: 'project', slug: 'Cohort-Study', name: 'Cohort-Study' },
    { id: 'projects/local-models', kind: 'project', slug: 'local-models', name: 'Local LLM' }];
  const AGENTS = [
    { name: 'claude', label: 'Claude', headless: true, cmd: 'claude' },
    { name: 'codex', label: 'Codex', headless: true, cmd: 'codex' }];
  // GET /subject/delete?subject=, by subject: what the check says.
  const CHECKS = {
    'courses/Probability': { why: '', blocker: '', sessions: [] },
    'courses/Galois-Theory': { why: 'open-session', sessions: [SID, GAL],
      blocker: 'sessions ' + SID + ' and ' + GAL + ' are open on it; end them first; '
        + 'request 2026-10-09-gal has no terminal report yet' },
    'projects/Cohort-Study': { why: 'request', sessions: [],
      blocker: 'request 2026-10-09-knn is outstanding on it; wait for its report' },
  };
  const answers = {
    '/sessions.json': {
      ok: true,
      sessions: [
        { id: SID, title: 'Rings', subject: 'courses/Galois-Theory',
          subject_name: 'Galois Theory', mode: 'teach', ended: null,
          opened: '2026-10-08 20:15:00',
          url: '/s/' + SID + '/board', new_cards: 3,
          last_card: { id: '0012', title: 'Eisenstein, again' } },
        { id: '20261008-180000', title: null, subject: null, subject_name: null,
          mode: 'teach', ended: null, url: '/s/20261008-180000/board',
          opened: '2026-10-08 18:00:00', new_cards: 0, last_card: null },
        { id: GAL, title: 'Galois Theory: ch07', subject: 'courses/Galois-Theory',
          subject_name: 'Galois Theory', mode: 'teach', ended: null,
          opened: '2026-10-01 09:00:00',
          url: '/s/' + GAL + '/board', new_cards: 0,
          last_card: { id: '0018', title: '' } },
        { id: '20260901-100000', title: 'Old one', subject: 'projects/Cohort-Study',
          subject_name: 'Cohort-Study', mode: 'do', opened: '2026-09-01 10:00:00',
          ended: '2026-09-02 11:00:00', url: '/s/20260901-100000/board' },
        { id: LECT, title: 'Lecture 4', subject: null, subject_name: null, mode: 'teach',
          opened: '2026-08-30 09:00:00', ended: '2026-08-30 10:00:00',
          url: '/s/' + LECT + '/board' }].concat(older) },
    '/subjects.json': { ok: true, subjects: SUBJECTS },
    '/notices.json': { ok: true, notices: [
      { t: now - 60, text: 'report t0031 landed', subject: 'projects/Cohort-Study' },
      { t: now - 30, text: 'report t0032 landed', subject: 'projects/Cohort-Study' }] },
    // The sync health (`sync.health`).
    '/sync.json': { ok: true, synced: false, down: true,
      lines: ['not synced: fatal: Not possible to fast-forward, aborting.',
              'brew: node did not upgrade: it is pinned'] },
    '/assistants.json': { ok: true, assistants: { default: 'claude', machine: 'claude',
                                                  why: null, agents: AGENTS } },
  };

  // opts: `over` replaces answers by path; `fail` answers a path 502 with an
  // empty body for its first n asks; `skip` leaves scripts out; `errorsOk`
  // drops the guard that fails the run on an uncaught error; `hold` never
  // answers a path while `w.held[path]` is true; `kept` is this device's
  // `board.subjects`; `wait` shortens WAIT_MS.
  function load(hash, opts) {
    opts = opts || {};
    const html = fs.readFileSync(path.join(WEB, 'home.html'), 'utf8');
    const dom = new JSDOM(html, {
      runScripts: 'outside-only', pretendToBeVisual: true,
      url: 'https://board.test/' + (hash || ''),
    });
    const w = dom.window;
    quiet(w);
    w.__went = [];
    w.asked = [];
    const fails = Object.assign({}, opts.fail || {});
    const over = opts.over || {};
    w.held = Object.assign({}, opts.hold || {});
    if (opts.kept) w.localStorage.setItem('board.subjects', JSON.stringify(opts.kept));
    w.fetch = (u, init) => {
      const url = String(u);
      const method = (init && init.method) || 'GET';
      const body = init && init.body ? JSON.parse(init.body) : null;
      w.asked.push({ url, method, body, keepalive: !!(init && init.keepalive) });
      const where = url.split('?')[0];
      if (w.held[where] && typeof w.held[where].then === 'function') {
        return w.held[where].then((v) => ({ status: 200, json: () => Promise.resolve(v) }));
      }
      if (w.held[where]) return new Promise(() => {});
      if (fails[where]) {
        fails[where] -= 1;
        return Promise.resolve({ status: 502,
                                 json: () => Promise.reject(new SyntaxError('Unexpected end of JSON')) });
      }
      let got = where in over ? over[where] : answers[where];
      if (method === 'GET' && where === '/subject/delete') {
        const id = new URL(url, 'https://board.test/').searchParams.get('subject');
        const s = SUBJECTS.filter((x) => x.id === id)[0];
        got = s && CHECKS[id] ? Object.assign({ ok: true, subject: id, slug: s.slug,
                                                kind: s.kind, name: s.name }, CHECKS[id]) : null;
      }
      if (method === 'POST' && url === '/subject/delete') {
        got = w.dropReply || { ok: true, subject: body.subject, trash: '/t/x/courses-Probability' };
      }
      if (method === 'POST' && /^\/s\/[^/]+\/send$/.test(url)) {
        const s = SUBJECTS.filter((x) => x.id === body.subject)[0];
        got = w.sendReply || { ok: true, sent: { id: body.subject, kind: s ? s.kind : 'project',
                                                 name: s ? s.name : body.subject.split('/')[1] },
                               filed: ['slides.pdf'], refused: [] };
      }
      if (method === 'POST' && url === '/client-error') got = { ok: true };
      if (method === 'POST' && url === '/default-agent') {
        got = { ok: true, default: body.agent, machine: body.agent, why: null,
                assistants: { default: body.agent, machine: body.agent, why: null, agents: AGENTS } };
      }
      if (method === 'POST' && url.split('?')[0] === '/artifact') {
        got = { ok: true, id: 't0003', make: body.make, session: SID,
                source: 'courses/Galois-Theory/docs/x/x.' + (body.make === 'deck' ? 'tex' : 'md') };
      }
      if (method === 'POST' && url === '/session/delete') got = { ok: true, id: body.id };
      if (method === 'POST' && url === '/subjects/new') {
        got = { ok: true, subject: { id: 'projects/' + body.name, kind: 'project',
                                     slug: body.name, name: body.name } };
      }
      if (!got) return Promise.resolve({ status: 404, json: () => Promise.resolve({ ok: false }) });
      return Promise.resolve({ status: 200,
                               json: () => Promise.resolve(JSON.parse(JSON.stringify(got))) });
    };
    if (!opts.errorsOk) w.addEventListener('error', (e) => fail('home: uncaught: ' + e.message));
    for (const f of ['typeface.js', 'keyguard.js', 'address.js', 'recentre.js', 'who.js', 'home.js']) {
      if ((opts.skip || []).indexOf(f) >= 0) continue;
      let src = fs.readFileSync(path.join(WEB, f), 'utf8');
      if (f === 'home.js') src = patched(src);
      if (f === 'home.js' && opts.wait) {
        src = src.replace('var WAIT_MS = 10000;', 'var WAIT_MS = ' + opts.wait + ';');
      }
      try { w.eval(src); } catch (e) { fail('home: ' + f + ': ' + e.message); }
      if (f === 'recentre.js' && w.Recentre) {
        const mount = w.Recentre.mount;
        w.Recentre.mount = (spec) => { w.__mounted = spec; return mount(spec); };
      }
    }
    // The boot check, the inline script at the end of the page, as the
    // browser would run it after the others.
    if (opts.boot) {
      if (opts.missed) w.bootMissed = opts.missed.slice();
      const inline = /<script>([\s\S]*?)<\/script>/.exec(html);
      try { w.eval(inline ? inline[1] : ''); } catch (e) { fail('home: the boot check: ' + e.message); }
    }
    return w;
  }
  const beacons = (page) => page.asked.filter((r) => r.url === '/client-error');

  let w = load();
  const d = w.document;
  await sleep(80);

  const order = ['continue', 'new-session', 'who', 'notices', 'find', 'courses', 'projects',
                 'past', 'make', 'settings'];
  const at = order.map((id) => {
    const e = d.getElementById(id);
    return e ? Array.prototype.indexOf.call(d.querySelectorAll('main *'), e) : -1;
  });
  check('top to bottom: Continue, New session, Tutor, notices, the search, Courses, '
        + 'Projects, Past sessions, the three actions, Settings',
        at.every((n, i) => n >= 0 && (i === 0 || n > at[i - 1])));

  // THE RE-CENTRE PILL is mounted as on the board, under the home key, and
  // placed below the bar rather than over the dot and the wordmark.
  const panicAt = /translate\(([-\d.]+)px,\s*([-\d.]+)px\)/.exec(d.getElementById('panic').style.transform || '');
  check('the re-centre pill is mounted by recentre.js under its own home key',
        w.__mounted && w.__mounted.key === 'home.panic'
        && w.__mounted.buttons[0].el === d.getElementById('panic'));
  check('and placed down the right edge below the bar, off the dot and the wordmark',
        panicAt && parseFloat(panicAt[2]) >= 60 && parseFloat(panicAt[1]) > 500);
  check('and shown, once mounted', !d.getElementById('panic').hidden);
  {
    const bare = load('', { skip: ['recentre.js'] });
    const broke = load('', { skip: ['home.js'] });
    await sleep(60);
    check('without recentre.js or home.js the pill stays hidden, not unplaced over the bar',
          bare.document.getElementById('panic').hidden
          && !bare.document.getElementById('panic').style.transform
          && broke.document.getElementById('panic').hidden);
    bare.close();
    broke.close();
  }
  check('the page told the boot check it is running, and nothing was beaconed',
        w.HomeBooted === true && beacons(w).length === 0);

  const open = Array.from(d.querySelectorAll('#open-list .row'));
  check('Continue lists the three open sessions', open.length === 3);
  const rings = open[0] || d.body;
  check('a Continue row names its subject, its last card and the new cards since seen',
        /Galois Theory/.test(rings.textContent) && /Eisenstein, again/.test(rings.textContent)
        && /3 new/.test(rings.textContent));
  check('and opens that session\'s board',
        rings.getAttribute('href') === '/s/20261008-201500/board');
  check('an unbound session says so', open[1] && /unbound/.test(open[1].textContent));
  const past = Array.from(d.querySelectorAll('#past-list .row'));
  check('Past sessions lists the newest ten ended ones, read only, and nothing open',
        past.length === 10 && /Old one/.test(past[0].textContent)
        && past[0].title === 'read only'
        && past.every((a) => !/Rings|ch07/.test(a.textContent)));
  // An ended session is read on its own board, which is read only once it has
  // ended. The board keeps no second reader of past sittings behind a menu.
  const boardHtml = fs.readFileSync(path.join(WEB, 'board.html'), 'utf8');
  const boardJs = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
  check('a past row opens that session\'s own board, the one way to read it',
        past[0] && past[0].getAttribute('href') === '/s/20260901-100000/board'
        && !/id="(history|btn-history|reading)"/.test(boardHtml)
        && !/["']\/archive\b/.test(boardJs));
  check('with "show all (12)" under them',
        !d.getElementById('past-more').hidden
        && d.getElementById('past-more').textContent === 'show all (12)');

  // A session is deleted from its row, on the second tap.
  const pastDel = d.querySelector('#past-list .row-delete');
  const deletes = () => w.asked.filter((r) => r.url === '/session/delete');
  check('every session row, open or past, offers delete',
        d.querySelectorAll('#open-list .row-delete').length === 3 && pastDel);
  pastDel.click();
  await sleep(10);
  check('one tap only arms it', deletes().length === 0 && /again/.test(pastDel.textContent));
  pastDel.click();
  await sleep(30);
  check('the second posts /session/delete with the id',
        deletes().length === 1 && deletes()[0].body.id === '20260901-100000');
  check('and the screen asks for the sessions again',
        w.asked.filter((r) => r.url === '/sessions.json').length >= 2);

  const courses = Array.from(d.querySelectorAll('#course-list .row'));
  const projects = Array.from(d.querySelectorAll('#project-list .row'));
  check('Courses and Projects each list their own subjects',
        courses.length === 2 && projects.length === 3
        && /Galois Theory/.test(courses[0].textContent));
  const names = (list) => Array.from(d.querySelectorAll(list + ' .row-name')).map((e) => e.textContent);
  check('the most recently used first, then the untouched ones by name',
        names('#project-list').join('|') === 'Cohort-Study|Local LLM|Mosaic'
        && names('#course-list').join('|') === 'Galois Theory|Probability');
  const sub = (id) => (d.querySelector('[data-subject="' + id + '"] .row-sub') || {}).textContent;
  check('a row says when it was last used, when it has been',
        sub('projects/Cohort-Study') === 'last: 2026-09-02'
        && sub('courses/Galois-Theory') === '2 open sessions  ·  last: 2026-10-08'
        && sub('courses/Probability') === 'courses/Probability');
  check('a subject row opens its page, the library for that subject',
        courses[0].getAttribute('href')
        === '/library?subject=courses%2FGalois-Theory&from=home');

  // A deck or a paper from a subject's row: the sheet asks what it is about,
  // then posts /artifact naming the subject, and offers the session writing it.
  const makeBtn = d.querySelector('#course-list [data-make-for="courses/Galois-Theory"]');
  if (makeBtn) makeBtn.click();
  const art = d.getElementById('artmaker');
  check('a subject row has a Make button that opens the deck-or-paper sheet',
        makeBtn && !art.hidden && /Galois Theory/.test(d.getElementById('artmaker-where').textContent));
  check('and it will not ask before it is told what the document is about',
        d.getElementById('artmaker-go').disabled);
  d.querySelector('#artmaker-make button[data-make="paper"]').click();
  const artAbout = d.getElementById('artmaker-about');
  artAbout.value = 'Galois groups of cubics';
  artAbout.dispatchEvent(new w.Event('input'));
  d.getElementById('artmaker-go').click();
  await sleep(40);
  const artAsk = w.asked.filter((r) => r.url.split('?')[0] === '/artifact');
  check('it posts /artifact for that subject with the product and the line',
        artAsk.length === 1
        && artAsk[0].url === '/artifact?subject=courses%2FGalois-Theory'
        && artAsk[0].body.make === 'paper' && artAsk[0].body.about === 'Galois groups of cubics');
  const artOpen = d.getElementById('artmaker-open');
  check('and offers the session the router chose, where it is being written',
        !artOpen.hidden && artOpen.getAttribute('href') === '/s/' + SID + '/board'
        && /docs\/x\/x\.md/.test(d.getElementById('artmaker-said').textContent));
  d.getElementById('artmaker-close').click();

  const urls = () => w.asked.map((r) => r.url);
  check('the start screen asks nothing of the old switch route or /atlas.json',
        !urls().some((u) => /^\/(switch|atlas\.json)/.test(u)));
  check('and reads the sessions, subjects, notices and assistants it draws',
        ['/sessions.json', '/subjects.json', '/notices.json', '/assistants.json']
          .every((u) => urls().indexOf(u) >= 0));

  // Notices: each dismissible, and a dismissed one stays gone.
  let notes = Array.from(d.querySelectorAll('#notice-list .notice'));
  check('notices from /notices.json are listed', !d.getElementById('notices').hidden
        && notes.length === 2 && /t0031/.test(notes[0].textContent));
  notes[0].querySelector('.dismiss').click();
  notes = Array.from(d.querySelectorAll('#notice-list .notice'));
  check('a dismissed notice goes', notes.length === 1 && /t0032/.test(notes[0].textContent));
  d.dispatchEvent(new w.Event('visibilitychange'));
  await sleep(60);
  check('and stays gone when the list is read again',
        d.querySelectorAll('#notice-list .notice').length === 1);
  d.querySelector('#notice-list .dismiss').click();
  check('with none left, the section hides', d.getElementById('notices').hidden);

  // The sync health, from /sync.json.
  const health = d.getElementById('health');
  check('the health lines from /sync.json are drawn, not synced first',
        !health.hidden && health.children.length === 2
        && /not synced/.test(health.children[0].textContent)
        && /brew/.test(health.children[1].textContent));
  check('and home.html has no Colibri panel',
        !d.getElementById('colibri')
        && !/colibri/i.test(fs.readFileSync(path.join(WEB, 'home.html'), 'utf8')));

  // + new project: a name, and nothing else, before it can be made.
  d.getElementById('new-project').click();
  check('+ new project opens the sheet',
        !d.getElementById('maker').hidden);
  check('an unnamed project cannot be made yet',
        d.getElementById('maker-go').disabled);
  const name = d.getElementById('maker-name');
  name.value = 'Diarization';
  name.dispatchEvent(new w.Event('input'));
  check('named, it can', !d.getElementById('maker-go').disabled);
  d.getElementById('maker-go').click();
  await sleep(60);
  const made = w.asked.filter((r) => r.url === '/subjects/new');
  check('it posts the kind and the name, and nothing else',
        made.length === 1 && made[0].body.kind === 'project'
        && made[0].body.name === 'Diarization'
        && Object.keys(made[0].body).sort().join(',') === 'kind,name');
  check('and the sheet closes', d.getElementById('maker').hidden);

  check('Notes and Annotate a PDF are live',
        !d.getElementById('act-notes').disabled && !d.getElementById('act-annotate').disabled);

  // Settings: theme cycles; the default assistant is drawn.
  const theme = d.body.dataset.mode;
  d.getElementById('btn-theme').click();
  check('the theme setting cycles and says where it is',
        d.body.dataset.mode !== theme
        && d.getElementById('theme-now').textContent === d.body.dataset.mode);
  check('the face setting is wired by typeface.js',
        typeof d.getElementById('btn-face').onclick === 'function');
  // THE TUTOR: right under New session, its buttons reading the recipes'
  // labels, and its note saying who takes the next turn before any tap.
  const who = d.getElementById('who');
  const whoNote = () => d.getElementById('who-note').textContent;
  check('the Tutor chooser sits directly under New session and New canvas, out of Settings',
        d.getElementById('starts').nextElementSibling === who
        && d.getElementById('new-session').parentElement === d.getElementById('starts')
        && !d.getElementById('settings').contains(who)
        && /^Tutor$/.test(who.querySelector('.who-lead').textContent));
  check('it is drawn with both choices, each reading its label',
        !who.hidden && Array.from(d.querySelectorAll('#who-ways button'))
          .map((b) => b.textContent + '=' + b.getAttribute('data-name')).join('|')
          === 'Claude=claude|Codex=codex');
  check('and says who takes the next turn without a tap',
        whoNote() === 'Claude takes the next turn in every session.');
  answers['/assistants.json'] = { ok: true, assistants: { default: 'claude', machine: 'codex',
    why: 'claude has run out of its allowance until 14:00, so codex takes the next turn',
    agents: AGENTS } };
  d.dispatchEvent(new w.Event('visibilitychange'));
  await sleep(60);
  check('the listing is read again on coming back, and a fallback says why',
        whoNote() === 'claude has run out of its allowance until 14:00, so codex takes the next turn.');
  d.querySelector('#who-ways button[data-name="codex"]').click();
  await sleep(40);
  const picked = w.asked.filter((r) => r.url === '/default-agent');
  check('a tap posts the recipe\'s name, not its label, and the note follows the reply',
        picked.length === 1 && picked[0].body.agent === 'codex'
        && whoNote() === 'Codex takes the next turn in every session.'
        && d.querySelector('#who-ways button.on').getAttribute('data-name') === 'codex');
  answers['/assistants.json'] = { ok: true, assistants: { default: 'claude', machine: 'claude',
                                                          why: null, agents: AGENTS } };
  {
    const one = load('', { over: { '/assistants.json': { ok: true, assistants: {
      default: 'claude', machine: 'claude', why: null, agents: [AGENTS[0]] } } } });
    await sleep(60);
    check('with fewer than two to choose between, there is no chooser',
          one.document.getElementById('who').hidden);
  }

  // THE SEARCH narrows the subjects and the past sessions, here on the page,
  // and holds across a refresh.
  const find = d.getElementById('find');
  const typeIn = (input, text) => { input.value = text; input.dispatchEvent(new w.Event('input')); };
  typeIn(find, 'cohort');
  check('the search narrows the courses, the projects and the past sessions by name or id',
        d.querySelectorAll('#course-list .row').length === 0
        && !d.getElementById('course-none').hidden
        && d.getElementById('course-none').textContent === 'No course matches.'
        && names('#project-list').join('|') === 'Cohort-Study'
        && d.querySelectorAll('#past-list .row').length === 1
        && /Old one/.test(d.querySelector('#past-list .row').textContent)
        && d.getElementById('past-more').hidden);
  d.dispatchEvent(new w.Event('visibilitychange'));
  await sleep(60);
  check('and still narrows them after the lists are read again',
        names('#project-list').join('|') === 'Cohort-Study'
        && d.querySelectorAll('#past-list .row').length === 1);
  typeIn(find, '20260830');
  check('a past session is found by its id too',
        d.querySelectorAll('#past-list .row').length === 1
        && /Lecture 4/.test(d.querySelector('#past-list .row').textContent));
  typeIn(find, '');
  check('cleared, everything is back',
        d.querySelectorAll('#course-list .row').length === 2
        && d.querySelectorAll('#past-list .row').length === 10);
  d.getElementById('past-more').click();
  check('"show all" shows every past session, and goes',
        d.querySelectorAll('#past-list .row').length === 12
        && d.getElementById('past-more').hidden);

  // DELETING A SUBJECT from its row: the sheet asks the server first.
  check('every course and project row offers delete, styled as a session\'s is',
        d.querySelectorAll('#course-list .subj, #project-list .subj').length === 5
        && Array.from(d.querySelectorAll('#course-list .subj, #project-list .subj'))
          .every((b) => b.querySelector('button.row-delete[data-drop-for]')));
  const dropper = d.getElementById('dropper');
  const dropGo = d.getElementById('dropper-go');
  const dropName = d.getElementById('dropper-name');
  const dropWhy = () => d.getElementById('dropper-why');
  const openDrop = async (id) => {
    d.querySelector('[data-drop-for="' + id + '"]').click();
    await sleep(30);
  };
  await openDrop('courses/Probability');
  check('a subject\'s delete opens the sheet, named, and asks the server whether it can go',
        !dropper.hidden && d.getElementById('dropper-title').textContent === 'Probability'
        && d.getElementById('dropper-kind').textContent === 'delete course'
        && w.asked.some((r) => r.method === 'GET'
                        && r.url === '/subject/delete?subject=courses%2FProbability'));
  check('nothing in the way: its slug is asked for, and Go waits for it',
        !d.getElementById('dropper-ask').hidden
        && d.getElementById('dropper-slug').textContent === 'Probability' && dropGo.disabled);
  typeIn(dropName, 'probability');
  check('the slug typed in the wrong case leaves Go asleep', dropGo.disabled);
  typeIn(dropName, 'Probability');
  check('typed exactly, Go wakes', !dropGo.disabled);
  w.dropReply = { ok: false, error: 'not committed, so nothing moved: index.lock' };
  dropGo.click();
  await sleep(30);
  check('a refusal keeps the sheet open, with the board\'s words',
        !dropper.hidden && /index\.lock/.test(d.getElementById('dropper-said').textContent)
        && /bad/.test(d.getElementById('dropper-said').className) && !dropGo.disabled);
  w.dropReply = null;
  const askedSubjects = w.asked.filter((r) => r.url === '/subjects.json').length;
  dropGo.click();
  await sleep(40);
  const dropped = w.asked.filter((r) => r.method === 'POST' && r.url === '/subject/delete');
  check('Go posts the subject and the slug as typed',
        dropped.length === 2 && dropped[1].body.subject === 'courses/Probability'
        && dropped[1].body.typed === 'Probability');
  check('and on ok the sheet closes, says where it went, and the lists are read again',
        dropper.hidden
        && d.getElementById('said').textContent === 'Probability is in the trash (/t/x/courses-Probability).'
        && w.asked.filter((r) => r.url === '/subjects.json').length > askedSubjects);
  await openDrop('courses/Galois-Theory');
  const held = Array.from(dropWhy().querySelectorAll('a')).map((a) => a.getAttribute('href'));
  check('a subject with open sessions links each to its board, and says to end or delete them',
        d.getElementById('dropper-ask').hidden
        && held.join('|') === '/s/' + SID + '/board|/s/' + GAL + '/board'
        && /Rings/.test(dropWhy().textContent)
        && /End or delete them first/.test(dropWhy().textContent));
  check('and the board\'s sentence follows, naming what else is in the way',
        /request 2026-10-09-gal has no terminal report yet/.test(dropWhy().textContent));
  dropper.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  check('a tap on the backdrop closes it', dropper.hidden);
  await openDrop('projects/Cohort-Study');
  check('any other blocker is shown in the board\'s own words',
        d.getElementById('dropper-ask').hidden
        && dropWhy().textContent === 'request 2026-10-09-knn is outstanding on it; wait for its report');
  d.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape' }));
  check('Escape closes it', dropper.hidden);
  await openDrop('projects/local-models');
  check('a check the board could not answer asks for nothing',
        d.getElementById('dropper-ask').hidden && dropGo.hidden && !dropper.hidden);
  d.getElementById('dropper-close').click();

  // SEND TO…: an unbound past session, to a course or a project.
  const sender = d.getElementById('sender');
  check('only a past session bound to nothing offers "send to…"',
        d.querySelectorAll('[data-send-for]').length === 1
        && d.querySelector('[data-send-for]').getAttribute('data-send-for') === LECT);
  const openSend = () => d.querySelector('[data-send-for="' + LECT + '"]').click();
  openSend();
  const sendIds = () => Array.from(d.querySelectorAll('#sender-list button'))
    .map((b) => b.getAttribute('data-id'));
  check('it opens a sheet over every course and project in the one picker order: '
        + 'Recent, then Courses, then Projects',
        !sender.hidden && d.getElementById('sender-title').textContent === 'Lecture 4'
        && sendIds().join('|') === ['courses/Galois-Theory', 'projects/Cohort-Study',
          'courses/Probability', 'projects/local-models', 'projects/Mosaic'].join('|')
        && Array.from(d.querySelectorAll('#sender-list .sender-group'))
          .map((e) => e.textContent).join('|') === 'Recent|Courses|Projects');
  typeIn(d.getElementById('sender-find'), 'prob');
  check('its search narrows them', sendIds().join('|') === 'courses/Probability');
  const sendsBefore = w.asked.filter((r) => r.url === '/sessions.json').length;
  d.querySelector('#sender-list button').click();
  await sleep(40);
  const sends = () => w.asked.filter((r) => r.method === 'POST' && /\/send$/.test(r.url));
  check('a tap posts /s/<id>/send with that subject',
        sends().length === 1 && sends()[0].url === '/s/' + LECT + '/send'
        && sends()[0].body.subject === 'courses/Probability');
  check('and the sheet closes, says where it went, and the lists are read again',
        sender.hidden
        && d.getElementById('said').textContent === 'Lecture 4 went to Probability, with 1 upload filed.'
        && w.asked.filter((r) => r.url === '/sessions.json').length > sendsBefore);
  w.sendReply = { ok: false, error: 'that session is bound elsewhere already' };
  openSend();
  d.querySelector('#sender-list button[data-id="courses/Galois-Theory"]').click();
  await sleep(40);
  check('a refusal keeps the sheet open, with the board\'s words',
        !sender.hidden && /bound elsewhere/.test(d.getElementById('sender-said').textContent));
  w.sendReply = null;
  d.getElementById('sender-new-project').click();
  check('+ new project from it opens the maker',
        sender.hidden && !d.getElementById('maker').hidden
        && /sent to it/.test(d.getElementById('maker-kind').textContent));
  typeIn(d.getElementById('maker-name'), 'Lectures');
  d.getElementById('maker-go').click();
  await sleep(60);
  const madeThen = w.asked.filter((r) => r.url === '/subjects/new').pop();
  check('and the session is sent to what it made',
        madeThen && madeThen.body.name === 'Lectures'
        && sends().length === 3 && sends()[2].body.subject === 'projects/Lectures'
        && sender.hidden && d.getElementById('maker').hidden);
  openSend();
  d.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape' }));
  check('Escape closes the send sheet', sender.hidden);
  {
    const listing = JSON.parse(JSON.stringify(answers['/sessions.json']));
    listing.sessions.forEach((r) => { if (r.id === LECT) r.wrapping = true; });
    const ww = load('', { over: { '/sessions.json': listing } });
    await sleep(80);
    const b = ww.document.querySelector('[data-send-for="' + LECT + '"]');
    check('a past session whose wrap-up is running has "send to…" disabled, saying why',
          b && b.disabled && /wrap-up is running/.test(b.title));
    ww.close();
  }
  openSend();
  sender.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  check('and so does its backdrop', sender.hidden);
  w.sendReply = { ok: true, sent: { id: 'courses/Probability', kind: 'course', name: 'Probability' },
                  filed: [], refused: [{ upload: 'uploads/notes.pdf', error: 'taken' }] };
  openSend();
  d.querySelector('#sender-list button[data-id="courses/Probability"]').click();
  await sleep(40);
  check('an upload the board could not file is named where it went',
        d.getElementById('said').textContent === 'Lecture 4 went to Probability. uploads/notes.pdf '
        + 'stayed in the session: a file of that name is already in its materials.');
  w.sendReply = null;

  // THE BOOT CHECK, at the end of home.html.
  {
    const html = fs.readFileSync(path.join(WEB, 'home.html'), 'utf8');
    const tags = html.match(/<script src="\/static\/[^"]+"[^>]*>/g) || [];
    check('every script the page loads records itself when it does not arrive',
          tags.length === 6 && tags.every((t) => /onerror="\(window\.bootMissed/.test(t)));
    check('and the check comes after them all',
          html.lastIndexOf('<script>') > html.indexOf('<script src="/static/home.js"'));
    const fine = load('', { boot: true });
    await sleep(60);
    check('with home.js running there is no Retry line',
          fine.document.getElementById('boot').hidden && beacons(fine).length === 0);
    const gone = load('', { boot: true, skip: ['home.js'], missed: ['https://board.test/static/home.js'] });
    await sleep(20);
    const boot = gone.document.getElementById('boot');
    check('with home.js missing the page says it did not finish loading, with a Retry',
          !boot.hidden && /did not finish loading/.test(boot.textContent)
          && /did not arrive/.test(boot.textContent)
          && typeof gone.document.getElementById('boot-retry').onclick === 'function');
    const told = beacons(gone);
    check('and tells the board which script it was',
          told.length === 1 && told[0].body.page === 'home' && told[0].body.what === 'boot'
          && told[0].body.src === 'https://board.test/static/home.js' && told[0].keepalive);
    const ran = load('', { boot: true, skip: ['home.js'] });
    await sleep(20);
    check('home.js that arrived but never ran says so too',
          !ran.document.getElementById('boot').hidden
          && beacons(ran).some((r) => /did not run/.test(r.body.msg)));
  }

  // THE BEACON: what broke, told to /client-error, rate-limited, never throwing.
  {
    const bw = load('', { errorsOk: true });
    await sleep(60);
    const bd = bw.document;
    bw.dispatchEvent(new bw.ErrorEvent('error', { message: 'boom', filename: 'https://board.test/static/x.js',
                                                  lineno: 3, error: new bw.Error('boom') }));
    bw.dispatchEvent(new bw.ErrorEvent('error', { message: 'boom', filename: 'https://board.test/static/x.js',
                                                  lineno: 3 }));
    let got = beacons(bw);
    check('an uncaught error is posted to /client-error once, with where it was',
          got.length === 1 && got[0].body.page === 'home' && got[0].body.what === 'error'
          && got[0].body.msg === 'boom' && got[0].body.src === 'https://board.test/static/x.js:3'
          && typeof got[0].body.ua === 'string' && got[0].keepalive);
    const img = bd.createElement('img');
    img.setAttribute('src', '/static/gone.png');
    bd.body.appendChild(img);
    img.dispatchEvent(new bw.Event('error'));
    got = beacons(bw);
    check('a resource that did not load is caught on its way down, by its URL',
          got.length === 2 && got[1].body.what === 'load' && /\/static\/gone\.png$/.test(got[1].body.src));
    const rej = new bw.Event('unhandledrejection');
    rej.reason = new bw.Error('nope');
    bw.dispatchEvent(rej);
    got = beacons(bw);
    check('an unhandled rejection is told too',
          got.length === 3 && got[2].body.what === 'rejection' && got[2].body.msg === 'nope');
    for (let i = 0; i < 20; i++) {
      bw.dispatchEvent(new bw.ErrorEvent('error', { message: 'storm ' + i, filename: 'y.js', lineno: i }));
    }
    check('and a storm is cut short: a handful a minute, not twenty',
          beacons(bw).length === 6);
    bw.fetch = () => { throw new Error('no fetch here'); };
    let threw = null;
    try {
      bw.dispatchEvent(new bw.ErrorEvent('error', { message: 'later', filename: 'z.js', lineno: 1 }));
    } catch (e) { threw = e; }
    check('telling never throws, even with no fetch', !threw);
  }

  // A REFRESH THAT FAILED: told, the dot dead, and tried again.
  {
    const fw = load('', { fail: { '/sessions.json': 1 } });
    await sleep(60);
    const fd = fw.document;
    check('a list answered 502 leaves the dot dead and is told to the board',
          fd.getElementById('dot').className === 'dot dead'
          && beacons(fw).some((r) => r.body.what === 'fetch' && r.body.src === '/sessions.json'
                              && /502/.test(r.body.msg)));
    await until(() => fd.getElementById('dot').className === 'dot live', 3500);
    check('and the refresh is tried again a moment later, and lands',
          fd.getElementById('dot').className === 'dot live'
          && fw.asked.filter((r) => r.url === '/sessions.json').length === 2
          && fd.querySelectorAll('#open-list .row').length === 3);
  }

  // New session goes to the board it was given.
  w.fetch = ((orig) => (u, init) => (String(u) === '/sessions/new'
    ? Promise.resolve({ status: 200, json: () => Promise.resolve({
      ok: true, id: '20261009-120000', url: '/s/20261009-120000/board' }) })
    : orig(u, init)))(w.fetch);
  d.getElementById('new-session').click();
  await sleep(30);
  check('New session opens the new session\'s board',
        w.__went.indexOf('/s/20261009-120000/board') >= 0);

  // NOTES: a session in full-slate view, titled by the day, opened at its slate.
  {
    const nw = load();
    await sleep(60);
    const NEW = '20261009-130000';
    nw.fetch = ((orig) => (u, init) => (String(u) === '/sessions/new'
      ? (nw.asked.push({ url: '/sessions/new', method: 'POST', body: JSON.parse(init.body) }),
         Promise.resolve({ status: 200, json: () => Promise.resolve({
           ok: true, id: NEW, url: '/s/' + NEW + '/slate' }) }))
      : orig(u, init)))(nw.fetch);
    const said = nw.document.getElementById('act-notes-sub').textContent;
    nw.document.getElementById('act-notes').click();
    await sleep(30);
    const asked = nw.asked.filter((r) => r.url === '/sessions/new')[0];
    check('New canvas, beside New session, posts /sessions/new with view slate and a '
          + 'title of the day',
          asked && asked.body.view === 'slate'
          && /^Canvas \d{4}-\d\d-\d\d$/.test(asked.body.title)
          && nw.document.getElementById('act-notes').parentElement.id === 'starts'
          && /New canvas/.test(nw.document.getElementById('act-notes').textContent)
          && said === 'write now; file it or give it to a tutor later');
    check('and opens the new session at its slate',
          nw.__went.indexOf('/s/' + NEW + '/slate') >= 0);
  }

  // ANNOTATE A PDF: a new session, the upload, filed when a subject is
  // picked, and the session's board opened on the document.
  async function annotated(subject, address) {
    const aw = load();
    await sleep(60);
    const ad = aw.document;
    const NEW = '20261009-140000';
    const xhrs = [];
    aw.XMLHttpRequest = function () {
      const x = this;
      x.upload = {};
      x.open = (m, u) => { x.method = m; x.url = u; };
      x.send = (form) => {
        xhrs.push({ url: x.url, file: form.get('f0') });
        x.status = 200;
        x.responseText = JSON.stringify({ ok: true, saved: ['slides.pdf'],
          files: [{ name: 'slides.pdf', size: 4, doc: 'uploads-slides' }] });
        setTimeout(() => x.onload(), 5);
      };
    };
    aw.fetch = ((orig) => (u, init) => {
      const url = String(u);
      const body = init && init.body ? JSON.parse(init.body) : null;
      let got = null;
      if (url === '/sessions/new') got = { ok: true, id: NEW, url: '/s/' + NEW + '/board' };
      if (url === '/s/' + NEW + '/bind') got = { ok: true };
      if (url === '/s/' + NEW + '/file') got = { ok: true, doc: 'materials-slides' };
      if (url === '/s/' + NEW + '/fetch') {
        got = { ok: true, saved: ['slides.pdf'],
                files: [{ name: 'slides.pdf', size: 4, doc: 'uploads-slides' }] };
      }
      if (!got) return orig(u, init);
      aw.asked.push({ url, method: 'POST', body });
      return Promise.resolve({ status: 200, json: () => Promise.resolve(got) });
    })(aw.fetch);
    ad.getElementById('act-annotate').click();
    const sheet = ad.getElementById('annot');
    const opts = Array.from(ad.querySelectorAll('#annot-subject option')).map((o) => o.value);
    const input = ad.getElementById('annot-file');
    if (address) {
      const box = ad.getElementById('annot-url');
      box.value = address;
      box.dispatchEvent(new aw.Event('input'));
    } else {
      Object.defineProperty(input, 'files', {
        value: [new aw.File(['%PDF-1.4'], 'slides.pdf', { type: 'application/pdf' })] });
      input.dispatchEvent(new aw.Event('change'));
    }
    ad.getElementById('annot-subject').value = subject;
    ad.getElementById('annot-subject').dispatchEvent(new aw.Event('change'));
    const ready = !ad.getElementById('annot-go').disabled;
    ad.getElementById('annot-go').click();
    await sleep(80);
    return { aw, sheet, opts, ready, xhrs, NEW };
  }
  {
    const r1 = await annotated('');
    check('Annotate a PDF opens its sheet, offering every subject, and "not yet" last',
          !r1.sheet.hidden && r1.opts[r1.opts.length - 1] === '' && r1.opts.length === 6
          && r1.opts.slice(0, 2).join('|') === 'courses/Galois-Theory|projects/Cohort-Study');
    check('a chosen PDF can be sent', r1.ready);
    const made = r1.aw.asked.filter((r) => r.url === '/sessions/new')[0];
    check('it makes a session titled for the file, and uploads into that session',
          made && made.body.title === 'Annotate slides.pdf'
          && r1.xhrs.length === 1 && r1.xhrs[0].url === '/s/' + r1.NEW + '/upload'
          && r1.xhrs[0].file && r1.xhrs[0].file.name === 'slides.pdf');
    check('with no subject nothing is bound or filed, and the reader opens the upload',
          !r1.aw.asked.some((r) => /\/(bind|file)$/.test(r.url))
          && r1.aw.__went[0] === '/s/' + r1.NEW + '/board#/s/' + r1.NEW + '/doc/uploads-slides');
    const r2 = await annotated('courses/Galois-Theory');
    const bind = r2.aw.asked.filter((r) => /\/bind$/.test(r.url))[0];
    const filed = r2.aw.asked.filter((r) => /\/file$/.test(r.url))[0];
    check('with a subject the session is bound to it and the upload filed into '
          + 'its materials',
          bind && bind.body.subject === 'courses/Galois-Theory'
          && filed && filed.body.upload === 'slides.pdf');
    check('and the reader opens the material, by the id it was filed under',
          r2.aw.__went[0] === '/s/' + r2.NEW + '/board#/s/' + r2.NEW + '/doc/materials-slides');
    const r3 = await annotated('courses/Probability', 'https://example.org/papers/slides.pdf?dl=1');
    const fetched = r3.aw.asked.filter((r) => /\/fetch$/.test(r.url))[0];
    const made3 = r3.aw.asked.filter((r) => r.url === '/sessions/new')[0];
    check('an address in #annot-url is fetched by the board into the new session, '
          + 'then bound and filed like a file',
          r3.ready && fetched && fetched.body.url === 'https://example.org/papers/slides.pdf?dl=1'
          && made3 && made3.body.title === 'Annotate slides.pdf' && !r3.xhrs.length
          && r3.aw.asked.some((r) => /\/file$/.test(r.url) && r.body.upload === 'slides.pdf')
          && r3.aw.__went[0] === '/s/' + r3.NEW + '/board#/s/' + r3.NEW + '/doc/materials-slides');
  }

  // RANDOM LESSONS FIRST: with the catch-all on the tree (/subjects.json
  // `scratch`), the send sheet offers it first, under no heading, and Annotate
  // preselects it.
  {
    const withRandom = { ok: true, scratch: 'courses/Random',
      subjects: SUBJECTS.concat([{ id: 'courses/Random', kind: 'course', slug: 'Random',
                                   name: 'Random lessons' }]) };
    const rw = load('', { over: { '/subjects.json': withRandom } });
    await sleep(80);
    const rd = rw.document;
    rd.querySelector('[data-send-for="' + LECT + '"]').click();
    const ids = Array.from(rd.querySelectorAll('#sender-list button')).map((b) => b.getAttribute('data-id'));
    const first = rd.getElementById('sender-list').firstElementChild;
    check('the send sheet offers Random lessons first, then Recent, Courses, Projects',
          ids.join('|') === ['courses/Random', 'courses/Galois-Theory', 'projects/Cohort-Study',
            'courses/Probability', 'projects/local-models', 'projects/Mosaic'].join('|')
          && first && first.getAttribute('data-id') === 'courses/Random'
          && /Random lessons/.test(first.textContent));
    rd.getElementById('sender-close').click();
    rd.getElementById('act-annotate').click();
    const sel = rd.getElementById('annot-subject');
    const vals = Array.from(sel.querySelectorAll('option')).map((o) => o.value);
    check('Annotate a PDF preselects Random lessons, first, with "not yet" still last',
          sel.value === 'courses/Random' && vals[0] === 'courses/Random'
          && vals[vals.length - 1] === ''
          && Array.from(sel.querySelectorAll('optgroup')).map((g) => g.label).join('|')
            === 'Recent|Courses|Projects');
    rw.close();
  }

  // A LIST THE LINK HOLDS: the iPad's link once held every request for
  // minutes. Annotate, which opens before the first refresh lands, offers the
  // subjects kept from last time, Random lessons preselected; with none kept
  // it says it is asking, then that the list did not come, and reopening
  // asks again. A /send not answered is held, never let go of.
  {
    const withRandom = { ok: true, scratch: 'courses/Random',
      subjects: SUBJECTS.concat([{ id: 'courses/Random', kind: 'course', slug: 'Random',
                                   name: 'Random lessons' }]) };
    const kw = load('', { over: { '/subjects.json': withRandom }, kept: withRandom,
                          hold: { '/subjects.json': true }, wait: 150 });
    await sleep(40);
    kw.document.getElementById('act-annotate').click();
    const ksel = kw.document.getElementById('annot-subject');
    check('with /subjects.json held, Annotate offers the kept list, Random lessons preselected',
          ksel.value === 'courses/Random'
          && ksel.querySelector('option').value === 'courses/Random'
          && !ksel.querySelector('option[disabled]'));
    kw.close();

    const nw = load('', { over: { '/subjects.json': withRandom },
                          hold: { '/subjects.json': true }, wait: 150 });
    await sleep(40);
    const nd = nw.document;
    nd.getElementById('act-annotate').click();
    const nsel = nd.getElementById('annot-subject');
    const waitOpt = () => nsel.querySelector('option[disabled]');
    check('with nothing kept, Annotate says it is asking, not nothing',
          waitOpt() && /Getting the courses and projects/.test(waitOpt().textContent)
          && nsel.value === '', waitOpt() && waitOpt().textContent);
    await sleep(220);
    check('and, not answered in WAIT_MS, that the list did not come',
          waitOpt() && /did not come/.test(waitOpt().textContent),
          waitOpt() && waitOpt().textContent);
    nw.held['/subjects.json'] = false;
    nd.getElementById('annot-close').click();
    nd.getElementById('act-annotate').click();
    await sleep(60);
    check('reopened, it asks again and fills it in, Random lessons preselected',
          !waitOpt() && nsel.value === 'courses/Random', nsel.value);
    check('and the list that came is kept for next time',
          JSON.parse(nw.localStorage.getItem('board.subjects')).scratch === 'courses/Random');
    let sent;
    nw.held['/s/' + LECT + '/send'] = new Promise((r) => { sent = r; });
    nd.getElementById('annot-close').click();
    nd.querySelector('[data-send-for="' + LECT + '"]').click();
    nd.querySelector('#sender-list button[data-id="courses/Random"]').click();
    const senderSaid = () => nd.getElementById('sender-said').textContent;
    check('a send says it is sending, rows held',
          /sending it to Random lessons/.test(senderSaid())
          && nd.querySelector('#sender-list button').disabled);
    await sleep(220);
    check('not answered in WAIT_MS, a send is not let go of: it says the board has not '
          + 'answered yet, rows still held, so it is never tapped twice',
          /has not answered yet/.test(senderSaid()) && !/Tap it again/.test(senderSaid())
          && nd.querySelector('#sender-list button').disabled
          && nw.asked.filter((r) => r.method === 'POST' && /\/send$/.test(r.url)).length === 1,
          senderSaid());
    sent({ ok: true, sent: { id: 'courses/Random', kind: 'course', name: 'Random lessons' },
           filed: [], refused: [] });
    await sleep(40);
    check('and the answer, when it comes, is the one the page shows',
          nd.getElementById('sender').hidden
          && /went to Random lessons/.test(nd.body.textContent), senderSaid());
    nw.close();
  }

  // A CANVAS'S ROW, open or past, offers "give to the tutor": a second tap
  // posts /s/<id>/give and opens the board it answers with.
  {
    const CAN = '20261009-170000';
    const listing = JSON.parse(JSON.stringify(answers['/sessions.json']));
    listing.sessions.unshift({ id: CAN, title: 'Canvas 2026-10-09', subject: null,
                               view: 'slate', mode: 'teach', opened: '2026-10-09 17:00:00',
                               ended: null, url: '/s/' + CAN + '/slate', new_cards: 0,
                               last_card: null });
    const cw = load('', { over: { '/sessions.json': listing } });
    await sleep(80);
    const gave = [];
    cw.fetch = ((orig) => (u, init) => {
      if (String(u) === '/s/' + CAN + '/give') {
        gave.push(init && init.method);
        return Promise.resolve({ status: 200, json: () => Promise.resolve({
          ok: true, pages: 3, url: '/s/' + CAN + '/board' }) });
      }
      return orig(u, init);
    })(cw.fetch);
    const cd = cw.document;
    const b = cd.querySelector('[data-give-for="' + CAN + '"]');
    check('only a canvas\'s row offers "give to the tutor", and it opens at its slate',
          b && cd.querySelectorAll('[data-give-for]').length === 1
          && cd.querySelector('a[data-session="' + CAN + '"]').getAttribute('href')
            === '/s/' + CAN + '/slate');
    b.click();
    await sleep(20);
    check('the first tap posts nothing', !gave.length && /again/.test(b.textContent));
    b.click();
    await sleep(40);
    check('the second posts /give and opens the canvas\'s board',
          gave.length === 1 && gave[0] === 'POST'
          && cw.__went.indexOf('/s/' + CAN + '/board') >= 0);
    cw.close();
  }

  // + NEW COURSE WITH ITS TEXTBOOK: the course made, then a session bound to
  // it, the PDF uploaded there, /textbook asked, and that session's board.
  {
    const bw = load();
    await sleep(60);
    const bd = bw.document;
    const NEW = '20261009-150000';
    const xhrs = [];
    bw.XMLHttpRequest = function () {
      const x = this;
      x.upload = {};
      x.open = (m, u) => { x.method = m; x.url = u; };
      x.send = (form) => {
        xhrs.push({ url: x.url, file: form.get('f0') });
        x.status = 200;
        x.responseText = JSON.stringify({ ok: true, saved: ['Book.pdf'],
          files: [{ name: 'Book.pdf', size: 4 }] });
        setTimeout(() => x.onload(), 5);
      };
    };
    bw.fetch = ((orig) => (u, init) => {
      const url = String(u);
      const body = init && init.body ? JSON.parse(init.body) : null;
      let got = null;
      if (url === '/subjects/new') {
        got = { ok: true, subject: { id: 'courses/' + body.name, kind: 'course',
                                     slug: body.name, name: body.name } };
      }
      if (url === '/sessions/new') got = { ok: true, id: NEW, url: '/s/' + NEW + '/board' };
      if (url === '/s/' + NEW + '/bind') got = { ok: true };
      if (url === '/s/' + NEW + '/textbook') got = { ok: true, started: true };
      if (!got) return orig(u, init);
      bw.asked.push({ url, method: 'POST', body });
      return Promise.resolve({ status: 200, json: () => Promise.resolve(got) });
    })(bw.fetch);
    bd.getElementById('new-course').click();
    check('+ new course offers a textbook PDF field',
          !bd.getElementById('maker-book').hidden);
    const bname = bd.getElementById('maker-name');
    bname.value = 'Topology';
    bname.dispatchEvent(new bw.Event('input'));
    const bfile = bd.getElementById('maker-book-file');
    Object.defineProperty(bfile, 'files', {
      value: [new bw.File(['%PDF-1.4'], 'Book.pdf', { type: 'application/pdf' })] });
    bfile.dispatchEvent(new bw.Event('change'));
    check('and says the book is indexed once it is made',
          /textbook is indexed/.test(bd.getElementById('maker-go-sub').textContent));
    bd.getElementById('maker-go').click();
    await sleep(120);
    const order = bw.asked.map((r) => r.url).filter((u) => /subjects\/new|sessions\/new|\/bind$|\/textbook$/.test(u));
    const bound = bw.asked.filter((r) => /\/bind$/.test(r.url))[0];
    const took = bw.asked.filter((r) => /\/textbook$/.test(r.url))[0];
    check('it makes the course, a session bound to it, uploads the PDF there and '
          + 'asks /textbook for it',
          order.join(' ') === '/subjects/new /sessions/new /s/' + NEW + '/bind /s/'
            + NEW + '/textbook'
          && bound.body.subject === 'courses/Topology'
          && xhrs.length === 1 && xhrs[0].url === '/s/' + NEW + '/upload'
          && took.body.upload === 'Book.pdf');
    check('and opens that session\'s board', bw.__went[0] === '/s/' + NEW + '/board');
    bd.getElementById('new-project').click();
    check('a project has no textbook field', bd.getElementById('maker-book').hidden);
    bd.getElementById('maker-close').click();
  }

  // Addresses.
  async function routed(hash) {
    const page = load(hash);
    await sleep(80);
    return { went: page.__went.slice(), said: page.document.getElementById('said') };
  }
  let r = await routed('#/s/20261008-201500/card/0007');
  check('#/s/<id>/card/NNNN goes to that session\'s board with the address whole',
        r.went[0] === '/s/20261008-201500/board#/s/20261008-201500/card/0007');
  r = await routed('#/w/Courses/Galois-Theory/card/0003');
  check('an old #/w/ link is no address: the start screen goes nowhere',
        !r.went.length);
  r = await routed('#/s/../card/0001');
  check('a malformed address is not followed', !r.went.length);
}

/* ======================================================== 2. a real server */
const SERVE = String.raw`
import json, os, shutil, signal, subprocess, sys, tempfile
board = sys.argv[1]
signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
sys.path.insert(0, board)
tmp = os.path.realpath(tempfile.mkdtemp(prefix="tutor-home-"))
atlas = os.path.join(tmp, "atlas")
os.environ["TUTORBOARD_COURSES"] = atlas
os.environ["TUTORBOARD_TRASH"] = os.path.join(tmp, "trash")
os.environ.pop("TUTORBOARD_SESSION", None)

def write(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)

def git(*a):
    subprocess.run(["git", "-C", atlas] + list(a), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

os.makedirs(atlas)
git("init", "-q")
git("config", "user.name", "Fixture")
git("config", "user.email", "fixture@example.invalid")
git("config", "commit.gpgsign", "false")
gal = os.path.join(atlas, "courses", "Galois-Theory")
write(os.path.join(gal, "tutorboard.json"), json.dumps({"name": "Galois Theory"}))
write(os.path.join(atlas, "projects", "Mosaic", "tutorboard.json"),
      json.dumps({"name": "Mosaic"}))
write(os.path.join(atlas, ".gitignore"), "/sessions/\n*/*/live/\n")
git("add", "-A")
git("commit", "-q", "-m", "fixture")
from tutorboard import sessions
from tutorboard.server import app
sid = sessions.new(title="Galois Theory: ch07", base=atlas)["id"]
sessions.bind(sid, "courses/Galois-Theory", base=atlas)
for n in range(1, 46):
    write(os.path.join(sessions.path(sid, atlas), "cards", "%04d-card.md" % n),
          "---\nkind: note\ntitle: Card %d\n---\nthe body of card-%04d\n" % (n, n))
httpd = app.make_server(atlas, 0)
print(json.dumps({"port": httpd.server_port, "atlas": atlas, "tmp": tmp,
                  "sid": sid}), flush=True)
try:
    httpd.serve_forever()
finally:
    shutil.rmtree(tmp, ignore_errors=True)
`;

// The server runs under a home of its own: a route like POST /default-agent
// writes ~/.config/tutor-board/config.json, and a test must never write the
// machine's real one.
function serve() {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'tutor-home-user-'));
  const env = Object.assign({}, process.env, {
    HOME: home,
    XDG_CONFIG_HOME: path.join(home, '.config'),
    XDG_CACHE_HOME: path.join(home, '.cache'),
    XDG_STATE_HOME: path.join(home, '.local', 'state'),
    GIT_CONFIG_NOSYSTEM: '1',
  });
  return new Promise((resolve, reject) => {
    const child = spawn('python3', ['-c', SERVE, BOARD],
                        { stdio: ['ignore', 'pipe', 'pipe'], env });
    child.on('exit', () => fs.rmSync(home, { recursive: true, force: true }));
    let buf = '';
    let err = '';
    child.stderr.on('data', (c) => { err += c; });
    child.stdout.on('data', (c) => {
      buf += c;
      const cut = buf.indexOf('\n');
      if (cut >= 0) {
        try { resolve(Object.assign({ child }, JSON.parse(buf.slice(0, cut)))); }
        catch (e) { reject(e); }
      }
    });
    child.on('exit', (code) => reject(new Error('server exited ' + code + ': '
                                                + err.slice(-1500))));
  });
}

// A page off the server, every script off the server, fetch over the wire.
async function page(url, opts) {
  opts = opts || {};
  const res = await fetch(url);
  const html = await res.text();
  const dom = new JSDOM(html, { runScripts: 'outside-only', pretendToBeVisual: true, url });
  const w = dom.window;
  quiet(w);
  w.__went = [];
  w.__requests = [];
  w.__scrolled = [];
  w.Element.prototype.scrollIntoView = function () {
    w.__scrolled.push(this.getAttribute && this.getAttribute('data-card'));
  };
  w.addEventListener('error', (e) => w.__requests.push({ url: 'uncaught ' + e.message }));
  w.fetch = (u, init) => {
    const target = new URL(String(u), url);
    const o = Object.assign({}, init || {});
    // The page's signal is jsdom's, which Node's fetch refuses; the wait it
    // carries is the page's own timer, which still runs.
    delete o.keepalive; delete o.cache; delete o.credentials; delete o.signal;
    const rec = { url: target.pathname + target.search, method: o.method || 'GET' };
    w.__requests.push(rec);
    return fetch(target, o).then((r) => { rec.status = r.status; return r; },
                                 (e) => { rec.status = 'error'; throw e; });
  };
  w.EventSource = function (u) {
    const target = new URL(String(u), url);
    const self = this;
    const rec = { url: target.pathname, method: 'STREAM' };
    w.__requests.push(rec);
    this.readyState = 0;
    this.close = function () { self.readyState = 2; if (self.req) self.req.destroy(); };
    this.addEventListener = function () {};
    this.req = http.get(target, (r) => {
      rec.status = r.statusCode;
      self.readyState = 1;
      if (self.onopen) self.onopen();
      let buf = '';
      r.setEncoding('utf8');
      r.on('data', (chunk) => {
        buf += chunk;
        let cut;
        while ((cut = buf.indexOf('\n\n')) !== -1) {
          const block = buf.slice(0, cut);
          buf = buf.slice(cut + 2);
          const data = block.split('\n').filter((l) => l.indexOf('data: ') === 0)
            .map((l) => l.slice(6)).join('\n');
          if (data && self.onmessage) {
            try { self.onmessage({ data }); } catch (e) { /* the page's to say */ }
          }
        }
      });
    });
    this.req.on('error', () => {});
  };
  w.__pages = [];
  const re = /<script src="(\/static\/[^"]+)"/g;
  let m;
  while ((m = re.exec(html))) {
    if (m[1].indexOf('/static/katex/') === 0) continue;
    let body = await (await fetch(new URL(m[1], url))).text();
    if (m[1] === '/static/home.js') body = patched(body);
    try { w.eval(body); } catch (e) { w.__requests.push({ url: 'eval ' + m[1] + ': ' + e.message }); }
  }
  if (opts.hash) {
    w.location.hash = opts.hash;
  }
  return w;
}

function visible(d, e) {
  for (let n = e; n && n !== d.body; n = n.parentElement) {
    if (n.hidden) return false;
  }
  return true;
}

async function real() {
  let srv;
  try { srv = await serve(); } catch (e) { fail('the fixture server: ' + e.message); return; }
  const base = 'http://127.0.0.1:' + srv.port;
  try {
    const w = await page(base + '/');
    const d = w.document;
    await until(() => d.querySelectorAll('#course-list .row').length > 0, 8000);
    await until(() => w.__requests.some((r) => r.url === '/assistants.json' && r.status), 8000);

    const asked = () => w.__requests.map((r) => r.url);
    check('/ makes no request to the old switch route or /atlas.json',
          !asked().some((u) => /^\/(switch|atlas\.json)/.test(u)));
    check('every request / makes is answered, none 404',
          w.__requests.every((r) => r.status && r.status !== 404));
    const cont = d.querySelector('#open-list .row');
    check('the Galois session is under Continue with its last card',
          cont && /Galois Theory/.test(cont.textContent) && /Card 45/.test(cont.textContent));

    // New session.
    d.getElementById('new-session').click();
    await until(() => w.__went.length > 0, 5000);
    const to = w.__went[0] || '';
    const sid = (/^\/s\/([^/]+)\/board$/.exec(to) || [])[1];
    const listed = await (await fetch(base + '/sessions.json')).json();
    const rec = (listed.sessions || []).filter((s) => s.id === sid)[0] || {};
    check('New session opens a new session\'s board', !!sid);
    check('and the session is unbound, in teach', rec.subject === null && rec.mode === 'teach');
    const board = await fetch(base + to);
    check('its board answers', board.status === 200);

    // + new course: Linear Algebra.
    d.getElementById('new-course').click();
    const name = d.getElementById('maker-name');
    name.value = 'Linear Algebra';
    name.dispatchEvent(new w.Event('input'));
    d.getElementById('maker-go').click();
    const listedNow = await until(() => Array.from(d.querySelectorAll('#course-list .row'))
      .some((a) => /Linear Algebra/.test(a.textContent)), 8000);
    check('creating "Linear Algebra" as a course adds it to the Courses list', listedNow);
    let log = '';
    try {
      log = execFileSync('git', ['-C', srv.atlas, 'log', '-1', '--name-only',
                                 '--format=%s'], { encoding: 'utf8' });
    } catch (e) { log = e.message; }
    check('and commits it: tutorboard.json and TUTOR.md in one commit',
          /courses\/Linear-Algebra: a new course/.test(log)
          && /courses\/Linear-Algebra\/tutorboard\.json/.test(log)
          && /courses\/Linear-Algebra\/TUTOR\.md/.test(log));
    const post = async (body) => {
      const r = await fetch(base + '/subjects/new', { method: 'POST', body: JSON.stringify(body),
                                                      headers: { 'Content-Type': 'application/json' } });
      return { status: r.status, body: await r.json() };
    };
    let refused = await post({ kind: 'course', name: 'Linear Algebra' });
    check('and a name some subject already has',
          refused.status === 400 && /already exists/.test(refused.body.error || ''));
    refused = await post({ kind: 'course', name: '../x' });
    check('and a name with a slash in it', refused.status === 400);
    refused = await post({ kind: 'family', name: 'X' });
    check('and a kind that is neither course nor project', refused.status === 400);
    const row = Array.from(d.querySelectorAll('#course-list .row'))
      .filter((a) => /Linear Algebra/.test(a.textContent))[0];
    const lib = row && await fetch(base + row.getAttribute('href'));
    check('its row opens its subject page', lib && lib.status === 200);

    // No visible control calls a route that 404s.
    const seen = new Set();
    const links = Array.from(d.querySelectorAll('a[href]')).filter((a) => visible(d, a));
    let bad = [];
    for (const a of links) {
      const href = a.getAttribute('href');
      if (seen.has(href)) continue;
      seen.add(href);
      const r = await fetch(new URL(href, base));
      if (r.status === 404) bad.push('link ' + href);
    }
    // The route this page reads that the server may not serve yet: the
    // delete check. Where it has it, it is pressed like everything else; where
    // it does not, its controls are left alone.
    const probe = await fetch(base + '/subject/delete?subject=courses%2FGalois-Theory');
    const checks = probe.status !== 404;
    if (!checks) console.log('skip  this server has no GET /subject/delete, so no row\'s delete is pressed');
    const before = w.__requests.length;
    const buttons = Array.from(d.querySelectorAll('button'))
      .filter((b) => visible(d, b) && !b.disabled);
    for (const b of buttons) {
      if (b.id === 'btn-reload' || b.id === 'panic') continue;
      if (!checks && b.hasAttribute('data-drop-for')) continue;
      b.click();
      await sleep(40);
      // Inside a sheet the buttons are visible now: press those too, once.
      ['maker', 'dropper'].forEach((id) => {
        const sheet = d.getElementById(id);
        if (sheet.hidden || sheet.__pressed) return;
        sheet.__pressed = true;
        if (id === 'maker') d.getElementById('maker-close').click();
      });
      if (!d.getElementById('dropper').hidden) {
        await sleep(200);
        d.getElementById('dropper-close').click();
      }
    }
    await sleep(1500);
    bad = bad.concat(w.__requests.slice(before)
      .filter((r) => r.status === 404 || /^(uncaught|eval)/.test(r.url))
      .map((r) => r.method + ' ' + r.url));
    check('no visible control calls a route that 404s'
          + (bad.length ? ': ' + bad.join(', ') : ''), bad.length === 0);
    if (checks) {
      check('a row\'s delete asked the server whether that subject can go',
            w.__requests.some((r) => /^\/subject\/delete\?subject=/.test(r.url) && r.status === 200));
    }

    await sessionLink(base, srv.sid, 'the fixture', true);
  } finally {
    srv.child.kill();
  }
}

// `#/s/<id>/card/0003` from the start screen, then the board it went to, on
// that card.
async function sessionLink(base, sid, where, older) {
  const w = await page(base + '/', { hash: '#/s/' + sid + '/card/0003' });
  await until(() => w.__went.length > 0, 8000);
  const want = '/s/' + sid + '/board#/s/' + sid + '/card/0003';
  check(where + ': #/s/<id>/card/0003 goes to card 0003 of the Galois session',
        w.__went[0] === want);
  const b = await page(base + want);
  const card = () => b.document.querySelector('[data-card="0003"]');
  const landed = await until(() => card() && b.__scrolled.indexOf('0003') >= 0, 15000);
  check(where + ': the board lands on that card', landed);
  if (older) {
    check(where + ': older than the window of 40, it was fetched with /cards?before=',
          b.__requests.some((r) => /^\/s\/[^/]+\/cards\?before=/.test(r.url)));
  }
  await sleep(300);
  check(where + ': and the bar keeps the session address',
        b.location.hash === '#/s/' + sid + '/card/0003');
  const said = b.document.getElementById('pushed');
  check(where + ': and calls nothing gone',
        !said || said.hidden || !/not in this session/.test(said.textContent));
  const errs = b.__requests.filter((r) => r.status === 404 || /^(uncaught|eval)/.test(r.url));
  check(where + ': the board asks nothing that 404s'
        + (errs.length ? ': ' + errs.map((r) => r.url).join(', ') : ''), !errs.length);
  if (b.EventSource) b.document.defaultView.close();
}

(async () => {
  await stubbed();
  await real();
  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
    : '\nthe start screen opens every session, and every session link lands');
  process.exit(errors.length ? 1 : 0);
})().catch((e) => {
  console.log('FAIL driver: ' + e.stack);
  process.exit(1);
});
