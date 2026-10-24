// A given, typeset, on the writing surface: placed, moved, rubbed out, undone, sent.
//
// A page carries `objects`, each a given from the problem bar typeset by the
// server as /figure/<digest>.svg (`server/tikz.py`, kind `latex`). Checked
// here, on slate-core.js in a real DOM:
//
//   1. `placeTex` lands it in the middle of the view, looped, with the lasso
//      in hand; the plane and the picture's crop cover it;
//   2. the lasso moves it, the eraser takes it whole, and undo brings it back;
//   3. a save carries it, and the picture a send carries draws it under the
//      ink;
//   4. where drawing an SVG taints the canvas (some iPad Safari builds), the
//      first figure is caught doing it, every figure comes from the server's
//      PNG instead, and the picture is still made.
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
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const FIG = 'de62f3b1439edd70';

// A page whose canvases remember what was drawn on them, in order, and which
// of them an SVG has tainted when `taints` is set.
function world(taints) {
  const dom = new JSDOM('<!doctype html><body><div id="slate"></div></body>', {
    runScripts: 'outside-only', pretendToBeVisual: true, url: 'https://board.test/s/20261023-1/board',
  });
  const { window } = dom;
  const log = [];
  const loaded = [];
  window.HTMLCanvasElement.prototype.getContext = function () {
    const canvas = this;
    if (!canvas.__ctx) {
      canvas.__ctx = new Proxy({}, {
        get: (t, k) => (k in t ? t[k] : function () {
          log.push({ k, canvas, args: Array.from(arguments) });
          if (k === 'drawImage') {
            const src = arguments[0];
            if (src && (src.__tainted || (taints && /\.svg$/.test(src.src || '')))) {
              canvas.__tainted = true;
            }
          }
        }),
        set: (t, k, v) => { t[k] = v; return true; },
      });
    }
    return canvas.__ctx;
  };
  window.HTMLCanvasElement.prototype.toDataURL = function () {
    if (this.__tainted) {
      const e = new Error('The operation is insecure.');
      e.name = 'SecurityError';
      throw e;
    }
    return 'data:image/png;base64,UE5H';
  };
  // Figures: an SVG of 134 by 75 CSS pixels, its PNG twice that; anything
  // else is a figure the server has not got.
  window.Image = function () {
    const img = { naturalWidth: 0, naturalHeight: 0 };
    Object.defineProperty(img, 'src', {
      get: () => img.__src,
      set: (u) => {
        img.__src = u;
        loaded.push(u);
        setTimeout(() => {
          if (u.indexOf(FIG) < 0) return img.onerror && img.onerror();
          const png = /\.png$/.test(u);
          img.naturalWidth = png ? 268 : 134;
          img.naturalHeight = png ? 150 : 75;
          img.onload && img.onload();
        }, 1);
      },
    });
    return img;
  };
  Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => 900 });
  Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 500 });
  window.HTMLElement.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: 900, height: 500, right: 900, bottom: 500, x: 0, y: 0 };
  };
  window.Element.prototype.setPointerCapture = function () {};
  window.Element.prototype.releasePointerCapture = function () {};
  const saves = [];
  window.fetch = (u, init) => {
    if (/slate\/state/.test(String(u))) {
      return Promise.resolve({ json: () => Promise.resolve({ pages: [] }) });
    }
    if (init && init.method === 'POST') {
      saves.push({ url: String(u), body: JSON.parse(init.body) });
      return Promise.resolve({ json: () => Promise.resolve({ ok: true, rev: 1 }) });
    }
    return new Promise(() => {});
  };
  window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  window.addEventListener('error', (e) => fail('uncaught: ' + e.message));
  for (const f of ['ink-clip.js', 'plane-core.js', 'ink-core.js', 'slate-core.js']) {
    try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); } catch (e) { fail(f + ': ' + e.message); }
  }
  const slate = window.Slate.create({
    root: window.document.getElementById('slate'), compact: false,
    stateUrl: '/s/20261023-1/slate/state', saveUrl: '/s/20261023-1/slate/save',
  });
  return { window, slate, log, loaded, saves };
}

function pointer(w, slate, type, lx, ly, id) {
  const sheet = slate.root.querySelector('canvas.sl-sheet');
  const v = slate.view();
  const ev = new w.window.Event(type, { bubbles: true, cancelable: true });
  Object.assign(ev, { pointerId: id || 7, pointerType: 'pen', pressure: 0.6,
                      clientX: lx * v.k + v.ox, clientY: ly * v.k + v.oy, isPrimary: true });
  ev.getCoalescedEvents = () => [ev];
  sheet.dispatchEvent(ev);
}

const P = { id: 'P', tex: 'P=\\begin{pmatrix} \\tfrac12 & 0 \\end{pmatrix}', fig: FIG };

(async () => {
  // ------------------------------------------------------------- placing
  const A = world(false);
  const S = A.slate;
  await sleep(20);
  const placed = await S.placeTex(P);
  const objs = S.objects();
  placed && objs.length === 1 && objs[0].id === 'P' && objs[0].fig === FIG && objs[0].kind === 'tex'
    ? ok('placeTex puts the given on the page as an object')
    : fail('placed: ' + placed + ' ' + JSON.stringify(objs));
  A.loaded.some((u) => u === '/s/20261023-1/figure/' + FIG + '.svg')
    ? ok('its figure comes from the session\'s /figure/<digest>.svg')
    : fail('figure urls: ' + A.loaded.join(', '));
  const o = objs[0] || {};
  const v = S.view();
  const cx = (-v.ox + 450) / v.k, cy = (-v.oy + 250) / v.k;
  Math.abs(o.w - 134) < 0.01 && Math.abs(o.h - 75) < 0.01
    && Math.abs(o.x + o.w / 2 - cx) < 1 && Math.abs(o.y + o.h / 2 - cy) < 1
    ? ok('at its typeset size, in the middle of the view')
    : fail('placed at ' + JSON.stringify(o) + ' view ' + JSON.stringify(v));
  S.picked() === 1 && S.tool() === 'lasso'
    ? ok('looped, with the lasso in hand to move it') : fail('picked ' + S.picked() + ' tool ' + S.tool());
  const box = S.pngBox();
  box.x0 <= o.x && box.y0 <= o.y && box.x0 + box.w >= o.x + o.w && box.y0 + box.h >= o.y + o.h
    ? ok('the picture\'s crop covers it') : fail('pngBox ' + JSON.stringify(box));
  const ib = S.inkBox();
  ib && ib.x0 <= o.x && ib.x1 >= o.x + o.w ? ok('and so does the plane') : fail('inkBox ' + JSON.stringify(ib));
  (await S.placeTex({ id: 'Q', tex: 'Q', fig: 'abcdef0123456789' })) === false
    && S.objects().length === 1
    ? ok('a figure the server has not got places nothing, and says so')
    : fail('a missing figure was placed');

  // ------------------------------------------------- lasso, eraser, undo
  pointer(A, S, 'pointerdown', o.x + o.w / 2, o.y + o.h / 2);
  pointer(A, S, 'pointermove', o.x + o.w / 2 + 50, o.y + o.h / 2 + 30);
  pointer(A, S, 'pointerup', o.x + o.w / 2 + 50, o.y + o.h / 2 + 30);
  let moved = S.objects()[0];
  Math.abs(moved.x - (o.x + 50)) < 0.01 && Math.abs(moved.y - (o.y + 30)) < 0.01
    ? ok('the lasso moves it') : fail('after the drag: ' + JSON.stringify(moved));
  S.tool('pen');
  S.load({ w: 900, h: 500, strokes: [], objects: [moved] });
  S.tool('lasso');
  pointer(A, S, 'pointerdown', moved.x - 20, moved.y - 20, 9);
  [[moved.x + moved.w + 20, moved.y - 20], [moved.x + moved.w + 20, moved.y + moved.h + 20],
   [moved.x - 20, moved.y + moved.h + 20], [moved.x - 20, moved.y - 20]]
    .forEach(([x, y]) => pointer(A, S, 'pointermove', x, y, 9));
  pointer(A, S, 'pointerup', moved.x - 20, moved.y - 20, 9);
  S.picked() === 1 ? ok('a loop around it catches it') : fail('the loop caught ' + S.picked());
  S.tool('erase');
  pointer(A, S, 'pointerdown', moved.x + 5, moved.y + 5, 10);
  pointer(A, S, 'pointerup', moved.x + 5, moved.y + 5, 10);
  S.objects().length === 0 ? ok('the eraser takes it whole') : fail('the eraser left ' + S.objects().length);
  const undo = S.bar.querySelector('button[title="undo"]') || S.root.querySelector('button[title="undo"]');
  undo.onclick();
  S.objects().length === 1 && S.objects()[0].x === moved.x
    ? ok('and undo brings it back where it was') : fail('undo gave ' + JSON.stringify(S.objects()));

  // ---------------------------------------------------------- the send
  S.tool('pen');
  pointer(A, S, 'pointerdown', 40, 40, 11);
  pointer(A, S, 'pointermove', 80, 60, 11);
  pointer(A, S, 'pointermove', 120, 90, 11);
  pointer(A, S, 'pointerup', 120, 90, 11);
  await sleep(20);
  A.log.length = 0;
  A.saves.length = 0;
  S.save(true);
  // The tinted figure, a canvas of its own, drawn onto the picture's canvas
  // before any line of ink is.
  const objDraw = A.log.findIndex((c) => c.k === 'drawImage' && c.args.length === 5
                                         && c.args[0] && c.args[0].tagName === 'CANVAS');
  const onto = objDraw >= 0 ? A.log[objDraw].canvas : null;
  const firstStroke = A.log.findIndex((c) => c.canvas === onto && (c.k === 'stroke' || c.k === 'lineTo'));
  objDraw >= 0 && firstStroke > objDraw
    ? ok('the picture a send carries draws the given under the ink')
    : fail('draw order: image ' + objDraw + ' stroke ' + firstStroke);
  await sleep(20);
  const sent = A.saves.filter((s) => s.body.send)[0];
  sent && sent.body.objects && sent.body.objects.length === 1
    && sent.body.objects[0].fig === FIG && sent.body.objects[0].tex === P.tex
    && Object.keys(sent.body.objects[0]).sort().join() === 'fig,h,id,kind,tex,w,x,y'
    && /data:image\/png/.test(sent.body.png)
    ? ok('and the save carries it, {id, kind, tex, fig, x, y, w, h}')
    : fail('sent: ' + JSON.stringify(sent && sent.body.objects));

  // ------------------------------------------------- a tainting browser
  const B = world(true);
  await sleep(20);
  const placedB = await B.slate.placeTex(P);
  B.loaded.some((u) => /\.png$/.test(u) && u.indexOf(FIG) >= 0)
    ? ok('where an SVG taints the canvas, the figure comes from the server\'s PNG')
    : fail('loaded: ' + B.loaded.join(', '));
  const ob = B.slate.objects()[0] || {};
  placedB && Math.abs(ob.w - 134) < 0.01 && Math.abs(ob.h - 75) < 0.01
    ? ok('at the same size the SVG would have had')
    : fail('placed from the PNG at ' + JSON.stringify(ob));
  B.saves.length = 0;
  let threw = null;
  try { B.slate.save(true); } catch (e) { threw = e; }
  await sleep(20);
  const sentB = B.saves.filter((s) => s.body.send)[0];
  !threw && sentB && /data:image\/png/.test(sentB.body.png)
    ? ok('and the picture is still made') : fail('the tainted send: ' + (threw && threw.message));

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\na given goes onto the page, moves, rubs out, undoes and is sent');
  process.exit(errors.length ? 1 : 0);
})().catch((e) => { fail(e.stack || e.message); process.exit(1); });
