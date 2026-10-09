// THE BOARD OPENS ON FORTY CARDS AND THEN TAKES DELTAS, AND STAYS QUICK.
//
// The frames here are the server's own: a 500-card session is built in a temp
// Atlas and its Hub ticked, so the whole payload and every delta below are
// what `server/hub.py` really sends. Each is fed to the page's stream and
// timed in a real DOM.
//
//   * A 500-card session paints each push in under PUSH_MS, and the whole
//     payload stays under SIZE_CAP however long the session is.
//   * The whole payload paints the newest 40 cards and offers the rest; a
//     delta adds a card, rewrites one and removes one, and a card that slid
//     out of the server's window stays on the page.
//   * Older cards come on a tap from `/cards?before=`, below what is held.
//   * A payload whose map, plan, reading and direction are
//     null, with no sets, results, jobs or Colibri on it, paints without a
//     throw; the subject's sets and counts come from `/subject.json`.
//
// jsdom is a development-only dependency; without it this skips.

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

let JSDOM;
try { ({ JSDOM } = require('jsdom')); }
catch (e) {
  console.log('skip  jsdom is not installed — `npm install jsdom` to run this test');
  process.exit(0);
}

const BOARD = path.join(__dirname, '..');
const WEB = path.join(BOARD, 'web');
const PUSH_MS = 300;
const SIZE_CAP = 48 * 1024;
const errors = [];
const ok = (m) => console.log('ok   ' + m);
const fail = (m) => { errors.push(m); console.log('FAIL ' + m); };
const check = (m, cond) => (cond ? ok(m) : fail(m));

// ---- the server's frames, from a real Hub --------------------------------
const MAKE = String.raw`
import json, os, sys, tempfile, time, shutil
sys.path.insert(0, os.getcwd())
base = os.path.realpath(tempfile.mkdtemp(prefix="tutor-tickjs-"))
os.environ["TUTORBOARD_COURSES"] = base
os.environ["TUTORBOARD_TRASH"] = tempfile.mkdtemp(prefix="tutor-tickjs-trash-")
os.environ.pop("TUTORBOARD_SESSION", None)
from tutorboard import sessions
from tutorboard.server import hub
from tutorboard.server.tikz import TikzWorker
def write(p, t):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(t)
course = os.path.join(base, "courses", "Topology")
write(os.path.join(course, "tutorboard.json"), json.dumps({"name": "Topology"}))
write(os.path.join(course, "homework", "hw01", "hw01.tex"), "\\begin{problem}{1.1}x\\end{problem}\n")
rec = sessions.new("Topology", base=base)
repo = sessions.repo(rec["id"], base, create=True)
repo.set_state(subject="courses/Topology")
repo = sessions.repo(rec["id"], base, create=True)
repo.ensure_dirs()
def card(i, body=None):
    write(os.path.join(repo.cards, "%04d-card.md" % i),
          "---\nkind: %s\ntitle: Card %d\n---\n\n%s\n" % (
              "question" if i % 5 == 0 else "lesson", i,
              body or ("Card %d: an open set, a closed one, and **why** the "
                       "difference matters, in a paragraph of ordinary length "
                       "with a list:\n\n- one\n- two\n" % i)))
for i in range(1, 501):
    card(i)
board = hub.Hub(repo, TikzWorker(repo))
q, cv = board.subscribe()
board.tick()
frames = [json.loads(board.payload)]
del q[:]
card(501)
board.tick()
card(495, "Rewritten in place.")
st = os.stat(os.path.join(repo.cards, "0495-card.md"))
os.utime(os.path.join(repo.cards, "0495-card.md"), (st.st_atime, st.st_mtime + 5))
board.tick()
os.remove(os.path.join(repo.cards, "0490-card.md"))
board.tick()
for i in range(502, 512):
    card(i)
    board.tick()
frames += [json.loads(x) for x in q]
out = {"frames": frames, "sizes": [len(board.payload.encode("utf-8"))],
       "older": hub.older_cards(repo, None, 461),
       "subject": hub.subject_info(repo)}
shutil.rmtree(base, ignore_errors=True)
print(json.dumps(out))
`;

let made;
try {
  made = JSON.parse(execFileSync('python3', ['-c', MAKE], {
    cwd: BOARD, maxBuffer: 64 * 1024 * 1024, encoding: 'utf8',
  }));
} catch (e) {
  fail('the server could not make the frames: ' + e.message);
  process.exit(1);
}
const frames = made.frames;
const whole = frames[0];
const wholeSize = Buffer.byteLength(JSON.stringify(whole));
check('the whole payload of a 500-card session stays under ' + SIZE_CAP
      + ' bytes (' + wholeSize + ', and ' + made.sizes[0] + ' at 511 cards)',
      wholeSize < SIZE_CAP && made.sizes[0] < SIZE_CAP);
check('it carries the newest 40 cards and says 460 are older',
      whole.cards.length === 40 && whole.cards_older === 460
      && whole.cards[0].id === '0461');
check('and every push after it is a delta', frames.slice(1).every((f) => f.delta === true)
      && frames.length === 1 + 3 + 10);

// ---- the page --------------------------------------------------------------
const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
  runScripts: 'outside-only', pretendToBeVisual: true, url: 'https://board.test/board',
});
const { window } = dom;
const doc = window.document;
window.HTMLCanvasElement.prototype.getContext = () =>
  new Proxy({}, { get: () => () => {}, set: () => true });
window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => 900 });
Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 500 });
window.HTMLElement.prototype.getBoundingClientRect = function () {
  return { left: 0, top: 0, width: 900, height: 500, right: 900, bottom: 500, x: 0, y: 0 };
};
window.Element.prototype.scrollIntoView = function () {};
window.renderMathInElement = () => {};
window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
window.scrollTo = () => {};
window.addEventListener('error', (e) => fail('uncaught: ' + e.message));

const asked = [];
const answer = (body) => Promise.resolve({ json: () => Promise.resolve(body) });
window.fetch = (u) => {
  u = String(u);
  asked.push(u);
  if (/slate\/state/.test(u)) return answer({ pages: [] });
  if (/^\/cards\?before=/.test(u)) return answer(made.older);
  if (u === '/subject.json') return answer(made.subject);
  return new Promise(() => {});
};
let stream = null;
window.EventSource = function (url) {
  stream = { url: url, close() {}, readyState: 1, addEventListener() {} };
  return stream;
};

for (const f of ['typeface.js', 'macros.js', 'plane-core.js', 'ink-core.js', 'slate-core.js',
                 'annotate.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
try {
  let src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
  src = src.replace(/\}\)\(\);\s*$/, 'window.__render = render;\n'
                    + 'window.__absorb = absorb;\nwindow.__frame = frame;\n})();');
  window.eval(src);
  ok('loaded the board');
} catch (e) { fail('board.js: ' + e.message); }

check('the board listens on the stream', stream && stream.url === '/events');

const shown = () => Array.prototype.map.call(
  doc.querySelectorAll('#cards .card[data-card]'), (n) => n.dataset.card);

// Straight through `render`, so a throw is seen rather than swallowed as a
// torn frame, then timed through the stream the way the page takes it.
function push(msg) {
  const data = window.__absorb(JSON.parse(JSON.stringify(msg)));
  if (!data) return 0;
  const t0 = process.hrtime.bigint();
  try { window.__render(window.__frame()); }
  catch (e) { fail('a push threw: ' + e.message); }
  return Number(process.hrtime.bigint() - t0) / 1e6;
}

const times = [];
times.push(push(whole));
check('the whole payload paints the newest 40 cards',
      shown().length === 40 && shown()[0] === '0461' && shown()[39] === '0500');
const older = doc.getElementById('older');
check('and offers the 460 before them', older && !older.hidden
      && /460 earlier cards/.test(older.textContent));

times.push(push(frames[1]));
check('a delta adds the new card', shown().length === 41 && shown()[40] === '0501');
times.push(push(frames[2]));
check('a delta rewrites a card in place',
      /Rewritten in place/.test(doc.querySelector('.card[data-card="0495"]').textContent)
      && shown().length === 41);
times.push(push(frames[3]));
check('a delta removes a deleted card', shown().indexOf('0490') < 0 && shown().length === 40);
for (const f of frames.slice(4)) times.push(push(f));
check('a card that slid out of the server\'s window stays on the page',
      shown()[0] === '0461' && shown().length === 50);
check('and a delta it already holds changes nothing',
      push(frames[frames.length - 1]) === 0 && shown().length === 50);
times.sort((a, b) => a - b);
check('each of ' + times.length + ' pushes paints in under ' + PUSH_MS + ' ms (slowest '
      + times[times.length - 1].toFixed(1) + ' ms, median '
      + times[Math.floor(times.length / 2)].toFixed(1) + ' ms)',
      times[times.length - 1] < PUSH_MS);

// ---- null-safe ----------------------------------------------------------------
check('null map, plan, reading and direction paint without a throw',
      ['map', 'plan', 'reading', 'direction']
        .every((k) => k in whole && whole[k] === null) && errors.length === 0);
check('and the payload carries no news or missions',
      !('news' in whole) && !('missions' in whole));

// ---- older cards, and the subject, on demand -----------------------------------
setTimeout(() => {
  older.onclick();
  check('the earlier cards are asked for below the oldest one held',
        asked.indexOf('/cards?before=461') >= 0);
  setTimeout(() => {
    check('and painted above it', shown().length === 90 && shown()[0] === '0421');
    check('with the count of what is left', !older.hidden
          && /420 earlier cards/.test(older.textContent));

    // The subject is asked for on a push, not carried on it.
    asked.length = 0;
    stream.onmessage({ data: JSON.stringify(whole) });
    check('a push asks for the subject on its own route, /subject.json',
          asked.indexOf('/subject.json') >= 0);
    refusingStore();
    console.log(errors.length ? '\n' + errors.length + ' FAILURES'
      : '\nthe board opens on forty cards, takes deltas, and stays quick');
    process.exit(errors.length ? 1 : 0);
  }, 20);
}, 20);

// ---- a browser that refuses site data ------------------------------------------
// A private window, or site data turned off: every touch of `localStorage`
// throws. The board keeps per-device conveniences there and none of them may
// cost the lesson.
function refusingStore() {
  const d = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
    runScripts: 'outside-only', pretendToBeVisual: true, url: 'https://board.test/board',
  });
  const w = d.window;
  let threw = null;
  w.addEventListener('error', (e) => { threw = e.message; });
  Object.defineProperty(w, 'localStorage', {
    get() { throw new w.DOMException('refused', 'SecurityError'); },
  });
  w.HTMLCanvasElement.prototype.getContext = () =>
    new Proxy({}, { get: () => () => {}, set: () => true });
  w.Element.prototype.scrollIntoView = function () {};
  w.renderMathInElement = () => {};
  w.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  w.scrollTo = () => {};
  w.fetch = () => new Promise(() => {});
  w.EventSource = function () { return { close() {}, readyState: 1, addEventListener() {} }; };
  try {
    for (const f of ['typeface.js', 'macros.js', 'plane-core.js', 'ink-core.js',
                     'slate-core.js', 'annotate.js']) {
      w.eval(fs.readFileSync(path.join(WEB, f), 'utf8'));
    }
    let src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
    src = src.replace(/\}\)\(\);\s*$/, 'window.__render = render;\n'
                      + 'window.__absorb = absorb;\nwindow.__frame = frame;\n})();');
    w.eval(src);
    w.__absorb(JSON.parse(JSON.stringify(whole)));
    w.__render(w.__frame());
  } catch (e) { threw = e.message; }
  check('a browser that refuses site data still paints the lesson'
        + (threw ? ' (threw: ' + threw + ')' : ''),
        !threw && d.window.document.querySelectorAll('#cards .card[data-card]').length === 40);
  w.close();
}
