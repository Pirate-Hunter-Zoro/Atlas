// THE MATERIALS DRAWER (T25): uploads with progress and visible errors, and a
// material deleted after a second tap.
//
//   1. With a stubbed XHR: a 150 MB file shows its progress as it goes, a
//      forced 500 leaves an error line that stays, a file over 1 GB is
//      refused before anything is sent, and the drawer lists the subject's
//      materials, deleting one only on the second tap.
//   2. Against a real server on a temp Atlas: the board's own XHR, through
//      jsdom, puts a file in the session's uploads/ with a line that wakes
//      nothing. The 150 MB body and the server's memory are test/uploads.py's.
//
// jsdom is a development-only dependency; without it this skips.

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');

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
const MB = 1024 * 1024;

async function until(test, ms) {
  for (let t = 0; t < ms; t += 50) {
    if (test()) return true;
    await sleep(50);
  }
  return !!test();
}

function quiet(window) {
  window.HTMLCanvasElement.prototype.getContext = () =>
    new Proxy({}, { get: () => () => {}, set: () => true });
  window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
  Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => 900 });
  Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 500 });
  window.HTMLElement.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: 900, height: 500, right: 900, bottom: 500, x: 0, y: 0 };
  };
  window.Element.prototype.scrollIntoView = function () {};
  window.Element.prototype.setPointerCapture = function () {};
  window.Element.prototype.releasePointerCapture = function () {};
  window.renderMathInElement = () => {};
  window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  window.scrollTo = () => {};
  window.matchMedia = (q) => ({ matches: false, media: String(q), addListener() {},
                                removeListener() {}, addEventListener() {},
                                removeEventListener() {} });
}

const SCRIPTS = ['typeface.js', 'macros.js', 'plane-core.js', 'ink-core.js',
                 'slate-core.js', 'annotate.js', 'annbar.js', 'who.js', 'board.js'];

// The scripts, with board.js's uploader handed out of its closure.
function load(w, where) {
  for (const f of SCRIPTS) {
    let src = fs.readFileSync(path.join(WEB, f), 'utf8');
    if (f === 'board.js') {
      if (src.indexOf('})();') < 0) fail('board.js has no closure to reach into');
      src = src.replace('})();', 'window.__upload = upload;\n})();');
    }
    try { w.eval(src); } catch (e) { fail(where + f + ': ' + e.message); }
  }
}

/* ======================================================= 1. a stubbed XHR */
function stubbed() {
  const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
    runScripts: 'outside-only', pretendToBeVisual: true,
    url: 'https://board.test/s/20261009-210000/board',
  });
  const w = dom.window;
  quiet(w);
  w.addEventListener('error', (e) => fail('uncaught: ' + e.message));
  const asked = [];
  let materials = [{ name: 'book.pdf', size: 3 * MB, at: 2 },
                   { name: 'notes/week1.pdf', size: 2048, at: 1 }];
  const reply = (o, status) => Promise.resolve({ status: status || 200, ok: true,
                                                 json: () => Promise.resolve(o) });
  w.fetch = (u, init) => {
    const url = String(u);
    const method = (init && init.method) || 'GET';
    const body = init && typeof init.body === 'string' ? JSON.parse(init.body) : null;
    asked.push({ url, method, body });
    if (/\/slate\/state$/.test(url)) return reply({ pages: [] });
    if (/\/materials\.json$/.test(url)) {
      return reply({ ok: true, subject: 'courses/Galois-Theory', materials: materials });
    }
    if (/\/material\/delete$/.test(url)) {
      materials = materials.filter((m) => m.name !== body.name);
      return reply({ ok: true, name: body.name });
    }
    return new Promise(() => {});
  };
  w.EventSource = function () {
    this.readyState = 0;
    this.close = function () {};
    this.addEventListener = function () {};
  };
  // Every XHR the page opens, held so the test can play the network.
  const xhrs = [];
  w.XMLHttpRequest = function () {
    this.upload = {};
    this.status = 0;
    this.responseText = '';
    xhrs.push(this);
  };
  w.XMLHttpRequest.prototype.open = function (method, url) {
    this.method = method;
    this.url = url;
  };
  w.XMLHttpRequest.prototype.send = function (body) { this.body = body; };
  w.FormData = function () { this.parts = []; };
  w.FormData.prototype.append = function (k, v, name) { this.parts.push([k, v, name]); };
  load(w, '');
  return { w, asked, xhrs, d: w.document };
}

async function stubbedFlow() {
  const { w, asked, xhrs, d } = stubbed();
  const drawer = d.getElementById('scratch');
  const state = d.getElementById('upload-state');
  const add = d.getElementById('btn-add-file');
  check('the drawer is Materials, with one button to add a file',
        /Materials/.test(drawer.textContent) && add && /add a file/.test(add.textContent));
  check('and the picker takes any file, not only photos and PDFs',
        !d.getElementById('file').hasAttribute('accept'));

  // 150 MB, as the iPad hands it over.
  const big = { name: 'Lecture Notes.pdf', size: 150 * MB };
  w.__upload([big]);
  const x = xhrs[0];
  check('an upload is one XHR to the session\'s /upload',
        x && x.method === 'POST' && x.url === '/s/20261009-210000/upload'
        && x.body && x.body.parts.length === 1 && x.body.parts[0][1] === big);
  check('and the drawer opens to show it', !drawer.hidden);
  const bar = state.querySelector('progress');
  check('a progress bar starts at 0', bar && bar.value === 0
        && /uploading Lecture Notes\.pdf \(150 MB\)/.test(state.textContent));
  x.upload.onprogress({ lengthComputable: true, loaded: 75 * MB, total: 150 * MB });
  check('and moves as the body goes: 50% of 150 MB',
        bar.value === 50 && /50% of 150 MB/.test(state.textContent));
  x.upload.onprogress({ lengthComputable: true, loaded: 150 * MB, total: 150 * MB });
  check('to 100%', bar.value === 100);
  x.status = 200;
  x.responseText = JSON.stringify({ ok: true, saved: ['Lecture-Notes.pdf'] });
  x.onload();
  check('a landed upload says so, and that the tutor reads it with what you say next',
        /uploaded Lecture-Notes\.pdf/.test(state.textContent)
        && /with what you say next/.test(state.textContent)
        && !state.querySelector('.upload-line.bad'));

  // A forced 500.
  w.__upload([{ name: 'scan.png', size: 2 * MB }]);
  const y = xhrs[1];
  y.status = 500;
  y.responseText = JSON.stringify({ ok: false, error: 'the upload could not be written: disk full' });
  y.onload();
  let bad = state.querySelector('.upload-line.bad');
  check('a forced 500 shows an error line, with the reason',
        bad && /upload failed \(500\)/.test(bad.textContent) && /disk full/.test(bad.textContent));
  check('which has no progress bar left on it', bad && !bad.querySelector('progress'));
  await sleep(10);
  check('and stays until dismissed', state.contains(bad));
  bad.querySelector('.upload-dismiss').click();
  check('the ✕ dismisses it', !state.contains(bad));

  // The link drops mid-upload.
  w.__upload([{ name: 'a.pdf', size: 10 }]);
  xhrs[2].onerror();
  bad = state.querySelector('.upload-line.bad');
  check('a dropped link is an error line too',
        bad && /did not answer/.test(bad.textContent));

  // Over 1 GB: nothing is sent.
  const before = xhrs.length;
  w.__upload([{ name: 'huge.mov', size: 1100 * MB }]);
  check('over 1 GB is refused on the page, before anything is sent',
        xhrs.length === before && /at most 1 GB/.test(state.textContent));

  // The subject's materials, and a delete on the second tap.
  drawer.hidden = true;
  d.getElementById('btn-scratch').click();
  await until(() => d.querySelectorAll('#materials-list .mat-row').length === 2, 2000);
  const rows = d.querySelectorAll('#materials-list .mat-row');
  check('opening the drawer lists the subject\'s materials',
        rows.length === 2 && !d.getElementById('materials').hidden
        && /book\.pdf/.test(rows[0].textContent) && /3 MB/.test(rows[0].textContent));
  const del = rows[0].querySelector('.mat-delete');
  del.click();
  await sleep(20);
  const posts = () => asked.filter((a) => /\/material\/delete$/.test(a.url));
  check('one tap on delete only arms it',
        posts().length === 0 && del.classList.contains('armed')
        && /tap again/.test(del.textContent));
  del.click();
  await until(() => d.querySelectorAll('#materials-list .mat-row').length === 1, 2000);
  check('the second tap posts /material/delete with the name, under the session',
        posts().length === 1 && posts()[0].body.name === 'book.pdf'
        && posts()[0].url === '/s/20261009-210000/material/delete');
  check('and the list no longer has it',
        d.querySelectorAll('#materials-list .mat-row').length === 1);
  w.close();
}

/* ======================================================= 2. a real server */
const SERVE = `
import json, os, subprocess, sys
board, tmp = sys.argv[1], sys.argv[2]
sys.path.insert(0, board)
atlas = os.path.join(tmp, "Atlas")
os.environ.update({"TUTORBOARD_COURSES": atlas,
                   "BOARD_STATE_DIR": os.path.join(tmp, ".state"),
                   "TUTORBOARD_TRASH": os.path.join(tmp, ".trash"),
                   "XDG_CONFIG_HOME": os.path.join(tmp, ".config"),
                   "TUTORBOARD_PAGES": os.path.join(tmp, ".pages")})
os.makedirs(os.path.join(atlas, "courses", "Alpha", "materials"))
open(os.path.join(atlas, "courses", "Alpha", "materials", "old.pdf"), "w").write("%PDF")
subprocess.run(["git", "init", "-q", atlas], check=True)
from tutorboard import sessions
from tutorboard.server import app
sid = sessions.new("uploads", base=atlas)["id"]
sessions.bind(sid, "courses/Alpha", base=atlas)
httpd = app.make_server(atlas, 0)
print(json.dumps({"port": httpd.server_port, "sid": sid, "atlas": atlas}), flush=True)
httpd.serve_forever()
`;

function serve() {
  const tmp = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'tutor-uploadsjs-')));
  const child = spawn('python3', ['-c', SERVE, BOARD, tmp],
                      { stdio: ['ignore', 'pipe', 'ignore'] });
  return new Promise((resolve, reject) => {
    let buf = '';
    child.stdout.on('data', (b) => {
      buf += b;
      const nl = buf.indexOf('\n');
      if (nl >= 0) resolve(Object.assign({ child }, JSON.parse(buf.slice(0, nl))));
    });
    child.on('exit', (code) => reject(new Error('server exited ' + code)));
    setTimeout(() => reject(new Error('server did not start')), 20000);
  });
}

async function realFlow() {
  let srv;
  try { srv = await serve(); } catch (e) { fail('the fixture server: ' + e.message); return; }
  const base = 'http://127.0.0.1:' + srv.port;
  try {
    const page = base + '/s/' + srv.sid + '/board';
    const html = await (await fetch(page)).text();
    const dom = new JSDOM(html, { runScripts: 'outside-only', pretendToBeVisual: true,
                                  url: page });
    const w = dom.window;
    quiet(w);
    w.EventSource = function () { this.close = function () {}; this.addEventListener = function () {}; };
    w.fetch = (u, init) => fetch(new URL(String(u), page), init);
    load(w, 'real: ');
    const d = w.document;
    const file = new w.File(['%PDF-1.4 handed over\n'], 'Problem Set 3.pdf',
                            { type: 'application/pdf' });
    w.__upload([file]);
    const state = d.getElementById('upload-state');
    await until(() => /uploaded|failed/.test(state.textContent), 10000);
    check('the board\'s own XHR uploads a file to the real server',
          /uploaded Problem-Set-3\.pdf/.test(state.textContent));
    const up = path.join(srv.atlas, 'sessions', srv.sid, 'uploads', 'Problem-Set-3.pdf');
    check('into the session\'s uploads/, whole',
          fs.existsSync(up) && fs.readFileSync(up, 'utf8') === '%PDF-1.4 handed over\n');
    const inbox = path.join(srv.atlas, 'sessions', srv.sid, 'inbox', 'messages.jsonl');
    const lines = fs.readFileSync(inbox, 'utf8').split('\n').filter(Boolean)
      .map((l) => JSON.parse(l)).filter((m) => m.signal === 'uploaded');
    check('with one [uploaded] <name> (<size>) line that wakes nothing',
          lines.length === 1 && lines[0].text === '[uploaded] Problem-Set-3.pdf (21 B)'
          && lines[0].wake === false);
    // The upload opened the drawer, and the drawer asked for the materials.
    await until(() => d.querySelectorAll('#materials-list .mat-row').length > 0, 5000);
    check('the drawer lists the bound subject\'s materials from the server',
          /old\.pdf/.test(d.getElementById('materials-list').textContent)
          && /courses\/Alpha/.test(d.getElementById('materials-head').textContent));
    w.close();
  } finally {
    srv.child.kill();
  }
}

(async () => {
  await stubbedFlow();
  await realFlow();
  if (errors.length) {
    console.log('\n' + errors.length + ' failed');
    process.exit(1);
  }
  console.log('\nall passed');
  process.exit(0);
})();
