// The ink clipboard across pages.
//
// board.html, library.html (annotate) and slate.html are separate documents.
// They share one clipboard through localStorage `tutor-board.clip`, and the
// newest copy has to win wherever it was made. Copying on the board, then in
// annotate, then pasting on the board must paste the annotate ink -- and a copy
// too big for the disk must not let another page paste the older clip it
// replaced.
//
// Several JSDOMs, one Map-backed localStorage, with the storage event a real
// browser sends the OTHER documents on every write.
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
const KEY = 'tutor-board.clip';
const errors = [];
const ok = (m) => console.log('ok   ' + m);
const fail = (m) => { errors.push(m); console.log('FAIL ' + m); };
const check = (cond, good, bad) => (cond ? ok(good) : fail(bad));

const disk = new Map();
const pages = [];
// Set to a function of the value to make setItem throw, as a full quota does.
let refuse = null;

function storageFor(page) {
  const tell = (key, value) => {
    for (const other of pages) {
      if (other === page) continue;
      const ev = new other.window.Event('storage');
      ev.key = key;
      ev.newValue = value;
      other.window.dispatchEvent(ev);
    }
  };
  return {
    getItem: (k) => (disk.has(k) ? disk.get(k) : null),
    setItem: (k, v) => {
      v = String(v);
      if (refuse && refuse(v)) {
        const e = new Error('QuotaExceededError');
        e.name = 'QuotaExceededError';
        throw e;
      }
      disk.set(k, v);
      tell(k, v);
    },
    removeItem: (k) => { disk.delete(k); tell(k, null); },
    clear: () => { disk.clear(); tell(null, null); },
    key: (i) => Array.from(disk.keys())[i] || null,
    get length() { return disk.size; },
  };
}

let clock = 1700000000000;
function page(file, name) {
  const dom = new JSDOM(fs.readFileSync(path.join(WEB, file), 'utf8'), {
    runScripts: 'outside-only', url: 'https://board.test/' + name,
  });
  const p = { name, window: dom.window, changes: 0 };
  Object.defineProperty(dom.window, 'localStorage',
                        { value: storageFor(p), configurable: true });
  dom.window.Date.now = () => clock;
  dom.window.addEventListener('error', (e) => fail(name + ' uncaught: ' + e.message));
  dom.window.eval(fs.readFileSync(path.join(WEB, 'ink-clip.js'), 'utf8'));
  dom.window.InkClip.onChange(() => { p.changes++; });
  pages.push(p);
  return p;
}

// A clip whose first stroke starts at a marker x, so which one pasted is plain.
const ink = (mark, n = 2) => [
  { c: '#eee', w: 3, pts: [[mark, 0, 0.5], [mark + 1, 2, 0.6]] },
  { c: '#c33', w: 2, pts: Array.from({ length: n }, (_, i) => [mark + i, 40 + i, 0.5]) },
];
const which = (p) => {
  const c = p.window.InkClip.get();
  return c ? c.strokes.length + ':' + c.w : null;
};
// What a page pastes, by the width of the clip: `ink(mark, n)` is n-1 wide, so
// the width names the clip.
const width = (p) => { const c = p.window.InkClip.get(); return c ? Math.round(c.w) : null; };

const board = page('board.html', 'board');
const annotate = page('library.html', 'library');
const slate = page('slate.html', 'slate');

// ------------------------------------------------------------- newest wins
{
  board.window.InkClip.put(ink(0, 31), { kind: 'slate', src: 'b' });     // 30 wide
  clock += 5;
  annotate.window.InkClip.put(ink(0, 51), { kind: 'annotation', src: 'c1' }); // 50 wide
  check(width(board) === 50,
        'copied on the board, then in annotate: the board pastes the annotate ink',
        'the board pasted a clip ' + width(board) + ' wide, not the annotate one (50)');
  clock += 5;
  board.window.InkClip.put(ink(0, 71), { kind: 'slate', src: 'b' });     // 70 wide
  check(width(annotate) === 70,
        'and the reverse: annotate pastes the board\'s newer ink',
        'annotate pasted a clip ' + width(annotate) + ' wide, not the board\'s (70)');
  check(width(slate) === 70, 'a third page that copied nothing pastes the newest too',
        'the slate pasted ' + width(slate));
  check(annotate.changes > 0 && slate.changes > 0,
        'and the other pages heard about it, so their bars can offer Paste',
        'no change reached the other pages');
}

// ---------------------------------------------------- the same millisecond
{
  const a = board.window.InkClip.put(ink(0, 11), { src: 'b' }).seq;       // 10 wide
  const b = annotate.window.InkClip.put(ink(0, 21),
                                        { kind: 'annotation', src: 'c1' }).seq; // 20 wide
  check(b > a, 'two copies in one millisecond still have an order (' + a + ' < ' + b + ')',
        'the second copy in the same millisecond stamped ' + b + ', not past ' + a);
  check(width(board) === 20 && width(annotate) === 20,
        'and both pages paste the second',
        'the pages paste ' + width(board) + ' and ' + width(annotate) + ', not 20 and 20');
  board.window.InkClip.put(ink(0, 41), { src: 'b' });       // 40 wide, same ms again
  check(width(board) === 40 && width(annotate) === 40,
        'and the reverse in that same millisecond',
        'after the board copied back, the pages paste ' + width(board) + ' and '
        + width(annotate));
}

// --------------------------------------------------- an oversize copy
{
  clock += 1000;
  annotate.window.InkClip.put(ink(0, 6), { kind: 'annotation', src: 'c1' }); // 5 wide, small
  const before = annotate.window.InkClip.get();
  check(before && Math.round(before.w) === 5, 'annotate holds a small clip of its own',
        'annotate could not paste its own small clip');
  // Ink that zigzags the width of a page, so every difference is a long number:
  // about 40000 points is over 300000 characters even in v2.
  const big = [{ c: '#eee', w: 3, pts: Array.from({ length: 40000 },
                (_, i) => [(i % 2) * 900 + (i % 7), (i % 3) * 700 + (i % 11), (i % 5) / 5]) }];
  clock += 1;
  const got = board.window.InkClip.put(big, { src: 'b' });
  const raw = JSON.parse(disk.get(KEY));
  check(got && raw.big === true && raw.strokes.length === 0 && raw.n === 1,
        'a copy too big for the disk leaves a stub there',
        'the disk holds ' + JSON.stringify(raw).slice(0, 120));
  check(board.window.InkClip.local() && board.window.InkClip.get()
        && board.window.InkClip.get().strokes[0].pts.length === 40000,
        'and the page that copied it still pastes the whole of it, saying so',
        'the copying page lost its own big clip');
  check(annotate.window.InkClip.get() === null && annotate.window.InkClip.why() === 'big',
        'annotate pastes nothing rather than its own older clip, and says why',
        'annotate pastes ' + which(annotate) + ' and says "' + annotate.window.InkClip.why() + '"');
  check(annotate.window.InkClip.has(),
        'it still offers Paste, which answers "copy it again here"',
        'annotate hides Paste, so the person never learns why');
  const fresh = page('slate.html', 'slate2');
  check(fresh.window.InkClip.get() === null && fresh.window.InkClip.why() === 'big',
        'a page opened afterwards does not paste the older clip either',
        'a fresh page pastes ' + which(fresh));
  clock += 1;
  annotate.window.InkClip.put(ink(0, 9), { kind: 'annotation', src: 'c1' }); // 8 wide
  check(width(board) === 8 && !board.window.InkClip.local(),
        'and a newer small copy elsewhere wins over the big one',
        'the board pastes ' + width(board) + ' after annotate copied again');
}

// --------------------------------------------- a setItem that throws
{
  clock += 1000;
  slate.window.InkClip.put(ink(0, 13), { src: 's' });   // 12 wide, on disk
  // The quota is full for anything but a small write: the clip throws, the stub fits.
  refuse = (v) => v.length > 400;
  clock += 1;
  board.window.InkClip.put(ink(0, 60), { src: 'b' });   // 59 wide, refused
  check(board.window.InkClip.local() && width(board) === 59,
        'a refused write keeps the clip on its own page',
        'the board pastes ' + width(board) + ' after its write was refused');
  check(slate.window.InkClip.get() === null && slate.window.InkClip.why() === 'big',
        'and the slate pastes nothing rather than its own older clip',
        'the slate pastes ' + which(slate) + ' after a refused copy elsewhere');
  // Nothing at all can be written: the old clip is still taken off the disk.
  refuse = () => true;
  clock += 1;
  slate.window.InkClip.put(ink(0, 3), { src: 's' });
  board.window.InkClip.put(ink(0, 25), { src: 'b' });
  check(!disk.has(KEY) && slate.window.InkClip.get() === null,
        'with no room even for the stub, the key is gone and the slate pastes nothing',
        'the slate pastes ' + which(slate) + ' with the disk refusing everything');
  refuse = null;
}

// ----------------------------------------------------------- a v1 clip
{
  clock += 1000;
  disk.set(KEY, JSON.stringify({
    v: 1, at: clock, kind: 'slate', src: 'old', ox: 0, oy: 0, w: 17, h: 3,
    strokes: [{ c: '#eee', w: 3, hl: false, pts: [[0, 0, 0.5], [17, 3, 0.5]] }],
  }));
  const fresh = page('board.html', 'board2');
  check(width(fresh) === 17, 'a clip left on disk by the old code still pastes',
        'a v1 clip pastes as ' + width(fresh));
  clock += 1;
  annotate.window.InkClip.put(ink(0, 4), { kind: 'annotation', src: 'c1' });
  check(width(fresh) === 3 && JSON.parse(disk.get(KEY)).v === 2,
        'and a later copy outranks it by its stamp, written as v2',
        'after a v2 copy over a v1 clip, the page pastes ' + width(fresh));
}

// ---------------------------------------------------- the v2 round trip
{
  clock += 1000;
  const src = [{ c: '#123', w: 2.5, hl: true,
                 pts: [[3.14, 2.71, 0.37], [-5.5, 100.1, 1], [1000.2, -0.3, 0]] }];
  board.window.InkClip.put(src, { src: 'b' });
  const back = annotate.window.InkClip.get();
  const want = [[8.6, 3, 0.37], [0, 100.4, 1], [1005.7, 0, 0]];
  const same = back && back.strokes[0].hl === true && back.strokes[0].c === '#123'
    && back.strokes[0].pts.every((q, i) => q.every((v, j) => Math.abs(v - want[i][j]) < 1e-9));
  check(same, 'v2 carries colour, width, highlighter and every point to a tenth',
        'v2 came back as ' + JSON.stringify(back && back.strokes));
  // A line of handwriting: fractional coordinates, small steps, varying pressure.
  const hand = [{ c: '#eee', w: 3, pts: Array.from({ length: 3000 }, (_, i) =>
    [100 + i * 0.7 + 3 * Math.sin(i / 3), 300 + 40 * Math.sin(i / 9),
     0.4 + 0.2 * Math.sin(i / 13)]) }];
  board.window.InkClip.put(hand, { src: 'b' });
  const v2 = disk.get(KEY).length;
  const v1 = JSON.stringify(Object.assign(board.window.InkClip.get(), { v: 1 })).length;
  check(v2 * 2 < v1, 'and handwriting in v2 is under half its v1 size ('
        + v2 + ' against ' + v1 + ' characters)',
        'v2 is ' + v2 + ' characters against ' + v1 + ' in v1');
}

// ------------------------------------------------------ back from bfcache
{
  const before = board.changes;
  const ev = new board.window.Event('pageshow');
  ev.persisted = true;
  board.window.dispatchEvent(ev);
  check(board.changes > before, 'a page back from the bfcache repaints its bars',
        'pageshow with persisted set told nobody');
}

console.log(errors.length ? errors.length + ' failed' : 'the clipboard crosses pages');
process.exit(errors.length ? 1 : 0);
