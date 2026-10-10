// THE START SCREEN (T23).
//
//   1. With a stubbed server: the sections in order, a Continue row with its
//      subject, last card and new count, notices that dismiss, + new project
//      asking "patient data?", and the address grammar -- `#/s/` carried to
//      the session's board, and an old `#/w/` link followed nowhere.
//   2. Against a real server on a temp Atlas whose Galois live/ was imported
//      (45 cards, so card 0003 is older than the board's window of 40): `/`
//      asks nothing of the old switch route or /atlas.json, New session opens an unbound
//      session in teach, "Linear Algebra" made as a course is listed and
//      committed, no visible control gets a 404, and `#/s/<id>/card/0003`
//      from the start screen lands on that card in the imported session's
//      board.
//   3. Where ~/Archive/atlas-migration/2026-10-07/live-dirs.tgz exists, the
//      same link on a copy of the real Galois live/.
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
const TGZ = path.join(os.homedir(), 'Archive', 'atlas-migration', '2026-10-07',
                      'live-dirs.tgz');
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
  const now = Date.now() / 1000;
  const answers = {
    '/sessions.json': {
      ok: true,
      sessions: [
        { id: SID, title: 'Rings', subject: 'courses/Galois-Theory',
          subject_name: 'Galois Theory', mode: 'teach', ended: null,
          url: '/s/' + SID + '/board', new_cards: 3,
          last_card: { id: '0012', title: 'Eisenstein, again' } },
        { id: '20261008-180000', title: null, subject: null, subject_name: null,
          mode: 'teach', ended: null, url: '/s/20261008-180000/board',
          new_cards: 0, last_card: null },
        { id: GAL, title: 'Galois Theory: ch07', subject: 'courses/Galois-Theory',
          subject_name: 'Galois Theory', mode: 'teach', ended: null,
          url: '/s/' + GAL + '/board', new_cards: 0,
          last_card: { id: '0018', title: '' } },
        { id: '20260901-100000', title: 'Old one', subject: 'projects/TRD-EHR',
          subject_name: 'TRD-EHR', mode: 'do', opened: '2026-09-01 10:00:00',
          ended: '2026-09-02 11:00:00', url: '/s/20260901-100000/board' }] },
    '/subjects.json': { ok: true, subjects: [
      { id: 'courses/Galois-Theory', kind: 'course', slug: 'Galois-Theory', name: 'Galois Theory' },
      { id: 'courses/Probability', kind: 'course', slug: 'Probability', name: 'Probability' },
      { id: 'projects/TRD-EHR', kind: 'project', slug: 'TRD-EHR', name: 'TRD-EHR' },
      { id: 'projects/Meetings', kind: 'project', slug: 'Meetings', name: 'Meetings' }] },
    '/notices.json': { ok: true, notices: [
      { t: now - 60, text: 'report t0031 landed', subject: 'projects/TRD-EHR' },
      { t: now - 30, text: 'report t0032 landed', subject: 'projects/TRD-EHR' }] },
    // The Meetings library, carrying the deck's record (`with_deck`).
    '/library.json': { subject: 'projects/Meetings', documents: [
      { id: 'meeting', artifact: 'docs/meeting', pdf: true, pages: 4, marks: { pages: 1 },
        meeting: { state: 'ready', ready: true, deck: '2026-10-08T09:00:00' } }],
      meeting: { state: 'ready', ready: true, deck: '2026-10-08T09:00:00', pages: 4,
                 period: 'the last week', subjects: ['TRD-EHR'],
                 check: { numbers: [{ value: '0.7', frame: 2 }], figures: [], internal: [] } } },
    // The cluster's health and Colibri (`relay.panel`).
    '/relay.json': { ok: true, down: true,
      lines: ['relay looks down: projects/TRD-EHR 2026-10-09-knn had no report 15 minutes after its commit',
              'not synced: fatal: Not possible to fast-forward, aborting.'],
      colibri: { state: 'loading', left: 7000, queue: 1, task: 'coli-20261009-120000-abcd',
                 load_s: 4080, detail: 'loading, a cold load takes about 68 min' },
      colibri_subject: 'projects/libr-local-llm',
      colibri_tasks: [
        { id: '2026-10-09-rows-colibri', label: 'rows', brief: 'count rows', state: 'submitted',
          phase: 'working', task: 'coli-20261009-120000-abcd', attempts: 1, deaths: 0,
          note: '', relay: [] },
        { id: '2026-10-08-colibri', label: '', brief: 'smoke test', state: 'completed',
          phase: 'done', task: 'coli-x', attempts: 1, deaths: 0, note: 'Colibri finished.',
          relay: ['python 3.12.3'] },
        { id: '2026-10-09-sites-colibri', label: 'sites', brief: 'count sites', state: 'submitted',
          phase: 'queued', task: 'coli-y', attempts: 0, deaths: 0, note: '', relay: [] }],
      estimate: 'a generation is coming up: the relay\'s next pass (every 5 min) queues it' },
    '/assistants.json': { ok: true, assistants: { default: 'claude', agents: [
      { name: 'claude', headless: true, cmd: 'claude' },
      { name: 'codex', headless: true, cmd: 'codex' }] } },
  };

  function load(hash) {
    const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'home.html'), 'utf8'), {
      runScripts: 'outside-only', pretendToBeVisual: true,
      url: 'https://board.test/' + (hash || ''),
    });
    const w = dom.window;
    quiet(w);
    w.__went = [];
    w.asked = [];
    w.fetch = (u, init) => {
      const url = String(u);
      const method = (init && init.method) || 'GET';
      const body = init && init.body ? JSON.parse(init.body) : null;
      w.asked.push({ url, method, body });
      let got = answers[url.split('?')[0]];
      if (method === 'POST' && url.split('?')[0] === '/artifact') {
        got = { ok: true, id: 't0003', make: body.make, session: SID,
                source: 'courses/Galois-Theory/docs/x/x.' + (body.make === 'deck' ? 'tex' : 'md') };
      }
      if (method === 'POST' && url === '/session/delete') got = { ok: true, id: body.id };
      if (method === 'POST' && url === '/colibri') {
        got = { ok: true, id: '2026-10-09-colibri', detail: 'request 2026-10-09-colibri filed and pushed',
                estimate: 'a cold start: about 68 min' };
      }
      if (method === 'POST' && url === '/subjects/new') {
        got = { ok: true, subject: { id: 'projects/' + body.name, kind: 'project',
                                     slug: body.name, name: body.name } };
      }
      if (!got) return Promise.resolve({ status: 404, json: () => Promise.resolve({ ok: false }) });
      return Promise.resolve({ status: 200,
                               json: () => Promise.resolve(JSON.parse(JSON.stringify(got))) });
    };
    w.addEventListener('error', (e) => fail('home: uncaught: ' + e.message));
    for (const f of ['typeface.js', 'address.js', 'recentre.js', 'who.js', 'home.js']) {
      let src = fs.readFileSync(path.join(WEB, f), 'utf8');
      if (f === 'home.js') src = patched(src);
      try { w.eval(src); } catch (e) { fail('home: ' + f + ': ' + e.message); }
    }
    return w;
  }

  let w = load();
  const d = w.document;
  await sleep(80);

  const order = ['continue', 'new-session', 'notices', 'courses', 'projects', 'past',
                 'make', 'settings'];
  const at = order.map((id) => {
    const e = d.getElementById(id);
    return e ? Array.prototype.indexOf.call(d.querySelectorAll('main *'), e) : -1;
  });
  check('top to bottom: Continue, New session, notices, Courses, Projects, Past '
        + 'sessions, the three actions, Settings',
        at.every((n, i) => n >= 0 && (i === 0 || n > at[i - 1])));

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
  check('Past sessions lists the ended one, read only, and nothing open',
        past.length === 1 && /Old one/.test(past[0].textContent)
        && past[0].title === 'read only');

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
        courses.length === 2 && projects.length === 2
        && /Galois Theory/.test(courses[0].textContent));
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

  // The cluster's health and the Colibri panel, both from /relay.json.
  const health = d.getElementById('health');
  check('the health lines from /relay.json are drawn, relay down first',
        !health.hidden && health.children.length === 2
        && /relay looks down/.test(health.children[0].textContent)
        && /not synced/.test(health.children[1].textContent));
  const coli = d.getElementById('colibri');
  check('libr-local-llm\'s Colibri panel shows its state, queue and tasks',
        !coli.hidden && /loading/.test(d.getElementById('colibri-state').textContent)
        && /1 task waiting/.test(d.getElementById('colibri-state').textContent)
        && d.querySelectorAll('#colibri-tasks .row').length === 3
        && /working/.test(d.querySelectorAll('#colibri-tasks .row')[0].textContent)
        && /done/.test(d.querySelectorAll('#colibri-tasks .row')[1].textContent)
        && /RELAY: python 3.12.3/.test(d.querySelectorAll('#colibri-tasks .row')[1].textContent)
        && /queued/.test(d.querySelectorAll('#colibri-tasks .row')[2].textContent));
  const brief = d.getElementById('colibri-brief');
  const fileBtn = d.getElementById('colibri-file');
  check('filing waits for a brief', fileBtn.disabled);
  brief.value = 'grade the diarization';
  brief.dispatchEvent(new w.Event('input'));
  check('and shows what the wait will be before the tap',
        !fileBtn.disabled && /coming up/.test(d.getElementById('colibri-file-sub').textContent));
  fileBtn.click();
  await sleep(60);
  const coliAsk = w.asked.filter((r) => r.url === '/colibri' && r.method === 'POST');
  check('a task is filed with POST /colibri and its brief, and the reply\'s '
        + 'cold-start estimate is shown',
        coliAsk.length === 1 && coliAsk[0].body.brief === 'grade the diarization'
        && /68 min/.test(d.getElementById('colibri-said').textContent)
        && brief.value === '');

  // + new project: it asks "patient data?" before it can be made.
  d.getElementById('new-project').click();
  check('+ new project opens the sheet and asks "patient data?"',
        !d.getElementById('maker').hidden && !d.getElementById('maker-phi').hidden
        && /Patient data\?/.test(d.getElementById('maker-phi').textContent));
  const name = d.getElementById('maker-name');
  name.value = 'Diarization';
  name.dispatchEvent(new w.Event('input'));
  check('a named project with no answer cannot be made yet',
        d.getElementById('maker-go').disabled);
  d.querySelector('#maker-phi button[data-phi="yes"]').click();
  check('answered, it can', !d.getElementById('maker-go').disabled);
  d.getElementById('maker-go').click();
  await sleep(60);
  const made = w.asked.filter((r) => r.url === '/subjects/new');
  check('it posts the kind, the name and the answer',
        made.length === 1 && made[0].body.kind === 'project'
        && made[0].body.name === 'Diarization' && made[0].body.phi === true);
  check('and the sheet closes', d.getElementById('maker').hidden);
  d.getElementById('new-course').click();
  check('+ new course asks nothing about patient data',
        d.getElementById('maker-phi').hidden);
  d.getElementById('maker-close').click();

  // The meeting deck lists the subjects, Meetings itself left out.
  d.getElementById('act-meeting').click();
  const which = Array.from(d.querySelectorAll('#notes-list button')).map((b) => b.getAttribute('data-id'));
  check('Meeting deck opens its sheet over every subject but Meetings',
        !d.getElementById('notes').hidden && which.length === 3
        && which.indexOf('projects/Meetings') < 0);
  await sleep(30);
  const read = d.getElementById('notes-read');
  check('a ready deck is offered as the Meetings library opened on it, the one reader',
        !read.hidden && read.getAttribute('href')
          === '/library?subject=projects%2FMeetings&doc=meeting&from=home'
        && /1 to check/.test(d.getElementById('notes-read-sub').textContent)
        && w.asked.some((r) => r.url === '/library.json?subject=projects%2FMeetings')
        && !w.asked.some((r) => /^\/meeting\//.test(r.url)));
  d.getElementById('notes-close').click();
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
  check('the default assistant is drawn with both choices',
        !d.getElementById('who').hidden
        && d.querySelectorAll('#who-ways button').length === 2);

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
    nw.document.getElementById('act-notes').click();
    await sleep(30);
    const asked = nw.asked.filter((r) => r.url === '/sessions/new')[0];
    check('Notes posts /sessions/new with view slate and a title of the day',
          asked && asked.body.view === 'slate'
          && /^Notes \d{4}-\d\d-\d\d$/.test(asked.body.title));
    check('and opens the new session at its slate',
          nw.__went.indexOf('/s/' + NEW + '/slate') >= 0);
  }

  // ANNOTATE A PDF: a new session, the upload, filed when a subject is
  // picked, and the session's board opened on the document.
  async function annotated(subject) {
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
      if (!got) return orig(u, init);
      aw.asked.push({ url, method: 'POST', body });
      return Promise.resolve({ status: 200, json: () => Promise.resolve(got) });
    })(aw.fetch);
    ad.getElementById('act-annotate').click();
    const sheet = ad.getElementById('annot');
    const opts = Array.from(ad.querySelectorAll('#annot-subject option')).map((o) => o.value);
    const input = ad.getElementById('annot-file');
    Object.defineProperty(input, 'files', {
      value: [new aw.File(['%PDF-1.4'], 'slides.pdf', { type: 'application/pdf' })] });
    input.dispatchEvent(new aw.Event('change'));
    ad.getElementById('annot-subject').value = subject;
    ad.getElementById('annot-subject').dispatchEvent(new aw.Event('change'));
    const ready = !ad.getElementById('annot-go').disabled;
    ad.getElementById('annot-go').click();
    await sleep(80);
    return { aw, sheet, opts, ready, xhrs, NEW };
  }
  {
    const r1 = await annotated('');
    check('Annotate a PDF opens its sheet, offering every subject or none',
          !r1.sheet.hidden && r1.opts[0] === '' && r1.opts.length === 5);
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
import json, os, shutil, signal, subprocess, sys, tarfile, tempfile
board, mode, tgz = sys.argv[1], sys.argv[2], sys.argv[3]
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
write(os.path.join(gal, "tutorboard.json"), json.dumps({"name": "Galois Theory", "phi": False}))
write(os.path.join(atlas, "projects", "Meetings", "tutorboard.json"),
      json.dumps({"name": "Meetings", "phi": True}))
write(os.path.join(atlas, ".gitignore"), "/sessions/\n*/*/live/\n")
git("add", "-A")
git("commit", "-q", "-m", "fixture")
live = os.path.join(gal, "live")
if mode == "galois":
    with tarfile.open(tgz, "r:gz") as tf:
        members = [m for m in tf.getmembers()
                   if m.name.startswith("courses/Galois-Theory/live/")
                   and "/live/archive/" not in m.name and (m.isfile() or m.isdir())]
        if hasattr(tarfile, "data_filter"):
            tf.extractall(atlas, members, filter="data")
        else:
            tf.extractall(atlas, members)
else:
    write(os.path.join(live, "state.json"), json.dumps({"course": "Galois Theory",
                                                         "chapter": "ch07"}))
    for n in range(1, 46):
        write(os.path.join(live, "cards", "%04d-card.md" % n),
              "---\nkind: note\ntitle: Card %d\n---\nthe body of card-%04d\n" % (n, n))

from tutorboard import sessions
from tutorboard.server import app
got = sessions.import_live(atlas, gal, "courses/Galois-Theory",
                           manifest=os.path.join(tmp, "import.jsonl"))
httpd = app.make_server(atlas, 0)
print(json.dumps({"port": httpd.server_port, "atlas": atlas, "tmp": tmp,
                  "sid": got["session"]}), flush=True)
try:
    httpd.serve_forever()
finally:
    shutil.rmtree(tmp, ignore_errors=True)
`;

// The server runs under a home of its own: a route like POST /default-agent
// writes ~/.config/tutor-board/config.json, and a test must never write the
// machine's real one.
function serve(mode) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'tutor-home-user-'));
  const env = Object.assign({}, process.env, {
    HOME: home,
    XDG_CONFIG_HOME: path.join(home, '.config'),
    XDG_CACHE_HOME: path.join(home, '.cache'),
    XDG_STATE_HOME: path.join(home, '.local', 'state'),
    GIT_CONFIG_NOSYSTEM: '1',
  });
  return new Promise((resolve, reject) => {
    const child = spawn('python3', ['-c', SERVE, BOARD, mode, TGZ],
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
    delete o.keepalive; delete o.cache; delete o.credentials;
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
  try { srv = await serve('fixture'); } catch (e) { fail('the fixture server: ' + e.message); return; }
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
    check('the imported Galois session is under Continue with its last card',
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
    let refused = await post({ kind: 'project', name: 'Unanswered' });
    check('POST /subjects/new refuses a project with no answer about patient data',
          refused.status === 400 && /patient data/.test(refused.body.error || ''));
    refused = await post({ kind: 'course', name: 'Linear Algebra' });
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
    const before = w.__requests.length;
    const buttons = Array.from(d.querySelectorAll('button'))
      .filter((b) => visible(d, b) && !b.disabled);
    for (const b of buttons) {
      if (b.id === 'btn-reload' || b.id === 'panic') continue;
      b.click();
      await sleep(40);
      // Inside a sheet the buttons are visible now: press those too, once.
      ['notes', 'maker'].forEach((id) => {
        const sheet = d.getElementById(id);
        if (sheet.hidden || sheet.__pressed) return;
        sheet.__pressed = true;
        if (id === 'notes') {
          d.querySelector('#notes-since button[data-since="7d"]').click();
          d.getElementById('notes-make').click();
          d.getElementById('notes-close').click();
        } else {
          d.querySelector('#maker-phi button[data-phi="no"]').click();
          d.getElementById('maker-close').click();
        }
      });
    }
    await sleep(1500);
    bad = bad.concat(w.__requests.slice(before)
      .filter((r) => r.status === 404 || /^(uncaught|eval)/.test(r.url))
      .map((r) => r.method + ' ' + r.url));
    check('no visible control calls a route that 404s'
          + (bad.length ? ': ' + bad.join(', ') : ''), bad.length === 0);
    check('the controls pressed reached the meeting deck',
          w.__requests.some((r) => r.url === '/meeting' && r.method === 'POST')
          && w.__requests.some((r) => r.url === '/library.json?subject=projects%2FMeetings'));

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
  check(where + ': #/s/<id>/card/0003 goes to card 0003 of the imported Galois '
        + 'session', w.__went[0] === want);
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

async function rehearsal() {
  if (!fs.existsSync(TGZ)) {
    console.log('SKIPPED the Galois rehearsal: ' + TGZ + ' is not here');
    return;
  }
  let srv;
  try { srv = await serve('galois'); } catch (e) { fail('the Galois copy: ' + e.message); return; }
  try {
    await sessionLink('http://127.0.0.1:' + srv.port, srv.sid, 'a copy of the real Galois live/');
  } finally {
    srv.child.kill();
  }
}

(async () => {
  await stubbed();
  await real();
  await rehearsal();
  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
    : '\nthe start screen opens every session, and every session link lands');
  process.exit(errors.length ? 1 : 0);
})().catch((e) => {
  console.log('FAIL driver: ' + e.stack);
  process.exit(1);
});
