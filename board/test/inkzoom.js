// INK FOLLOWS THE READER'S ZOOM -- one case, run against every reader that
// zooms (`test/library.js` and `test/deck.js` each call it in one line).
//
// Asked as: *"my annotations do NOT scale with said paper/presentation --
// they're getting all out of wack and misplaced."*
//
// jsdom lays nothing out, so the reader's layout is stood in for here, from
// the same numbers `library.css` uses: a page `min(100%, 54rem) × zoom` wide,
// a picture as tall as its own aspect makes it, and a caption that is part of
// the page's box only if the stylesheet leaves it in flow -- read off the real
// stylesheet, so the model moves when the CSS does. The canvas is a recorder:
// what is asserted is where the ink is PAINTED, against the page picture's own
// box, at every zoom.
//
//   * A RING DRAWN AT 100% sits on the same place of the picture at 250%, 50%
//     and 100% again, at the same width relative to the page.
//   * INK DRAWN AT 250%, on a page wider than the glass and scrolled sideways,
//     paints where it was drawn at 100%, and after a reload.
//   * THE COMMIT REPAINTS. No resize observer is fired here: the zoom's own
//     commit lays every layer out again.
//   * INK SAVED AGAINST THE OLD BOX -- the figure, caption and all, and a pen
//     width in the pixels of whatever width the page had -- comes back on the
//     same words at the same weight.
//   * A BOARD CARD, which does not zoom, paints its ink exactly as it did.

const fs = require('fs');
const path = require('path');

const WEB = path.join(__dirname, '..', 'web');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const GLASS = 1024;          /* the window */
const PADDING = 16;          /* #reader-pages padding, 1rem */
const FIT = 864;             /* 54rem */
const CAPTION = 26;          /* a caption's height in flow, measured on the iPad */
const GAP = 16;              /* .lib-page margin-bottom */

module.exports = async function inkFollowsZoom(w, t) {
  const ok = t.ok, fail = t.fail;
  const doc = w.document;
  const scroller = doc.getElementById('reader-pages');
  const figs = Array.prototype.slice.call(scroller.querySelectorAll('.lib-page'));
  if (figs.length < 2) { fail('ink/zoom: the reader has fewer than two pages'); return; }
  const tag = t.name || 'reader';
  const say = (m) => tag + ': ' + m;

  /* ---- the stylesheet, the window, the scroll -------------------------- */
  const style = doc.createElement('style');
  style.textContent = fs.readFileSync(path.join(WEB, 'library.css'), 'utf8');
  doc.head.appendChild(style);
  const de = doc.documentElement;
  Object.defineProperty(de, 'clientWidth', { configurable: true, get: () => GLASS });
  const scroll = { left: 0, top: 0 };
  Object.defineProperty(scroller, 'scrollLeft', { configurable: true,
    get: () => scroll.left, set: (v) => { scroll.left = Math.max(0, v); } });
  Object.defineProperty(scroller, 'scrollTop', { configurable: true,
    get: () => scroll.top, set: (v) => { scroll.top = Math.max(0, v); } });
  scroller.getBoundingClientRect = () => rect(0, 60, GLASS, 700);

  figs.forEach((f) => {
    const img = f.querySelector('img');
    Object.defineProperty(img, 'naturalWidth', { configurable: true, value: 1240 });
    Object.defineProperty(img, 'naturalHeight', { configurable: true,
                                                  value: t.naturalHeight || 698 });
    Object.defineProperty(img, 'complete', { configurable: true, value: true });
    f.getBoundingClientRect = () => layout().get(f).r;
    img.getBoundingClientRect = () => layout().get(f).ir;
  });

  function rect(left, top, width, height) {
    return { left, top, width, height, right: left + width, bottom: top + height,
             x: left, y: top };
  }
  function zoom() { return parseFloat(scroller.style.getPropertyValue('--zoom')) || 1; }
  function layout() {
    const content = GLASS - 2 * PADDING;
    const W = Math.min(content, FIT) * zoom();
    const left = PADDING + Math.max(0, (content - W) / 2) - scroll.left;
    let top = 60 + PADDING - scroll.top;
    const out = new Map();
    figs.forEach((f) => {
      /* The picture's laid-out aspect, which a page still decoding has too
         (the stylesheet gives it one), so it is not read off the image. */
      const ih = W * (t.naturalHeight || 698) / 1240;
      const cap = f.querySelector('figcaption');
      const pos = cap ? w.getComputedStyle(cap).position : 'absolute';
      const inFlow = !(pos === 'absolute' || pos === 'fixed');
      const h = ih + (inFlow ? CAPTION : 0);
      out.set(f, { r: rect(left, top, W, h), ir: rect(left, top, W, ih) });
      top += h + GAP + (inFlow ? 0 : CAPTION);
    });
    return out;
  }

  /* ---- a canvas that remembers what was painted on it, and where --------- */
  const proto = w.HTMLCanvasElement.prototype;
  const oldGet = proto.getContext;
  const widthDesc = Object.getOwnPropertyDescriptor(proto, 'width');
  const heightDesc = Object.getOwnPropertyDescriptor(proto, 'height');
  const inkOf = (cv) => (cv._ink || (cv._ink = []));
  /* Setting a canvas's size clears it, in a browser. */
  Object.defineProperty(proto, 'width', { configurable: true,
    get() { return widthDesc.get.call(this); },
    set(v) { this._ink = []; widthDesc.set.call(this, v); } });
  Object.defineProperty(proto, 'height', { configurable: true,
    get() { return heightDesc.get.call(this); },
    set(v) { this._ink = []; heightDesc.set.call(this, v); } });
  proto.getContext = function () {
    const cv = this;
    const st = { lineWidth: 1, strokeStyle: '' };
    const ctx = {
      clearRect(x, y, ww, hh) {
        cv._ink = inkOf(cv).filter((q) => !(q.x >= x && q.x <= x + ww
                                            && q.y >= y && q.y <= y + hh));
      },
      moveTo(x, y) { inkOf(cv).push({ x, y, lw: st.lineWidth, c: st.strokeStyle }); },
      lineTo(x, y) { inkOf(cv).push({ x, y, lw: st.lineWidth, c: st.strokeStyle }); },
      arc(x, y, r) { inkOf(cv).push({ x, y, lw: 2 * r, c: st.strokeStyle }); },
    };
    return new Proxy(ctx, {
      get: (o, k) => (k in o ? o[k] : (k in st ? st[k] : () => {})),
      set: (o, k, v) => { st[k] = v; return true; },
    });
  };

  /* Painted ink of one colour on one page, in fractions of the PAGE PICTURE,
     and its mean width as a fraction of the picture's width. */
  function seen(f, colour) {
    const cv = f.querySelector('canvas.ann-layer');
    const g = layout().get(f);
    const ox = g.r.left + parseFloat(cv.style.left || '0');
    const oy = g.r.top + parseFloat(cv.style.top || '0');
    const pts = inkOf(cv).filter((q) => q.c === colour);
    if (!pts.length) return null;
    const fx = pts.map((q) => (ox + q.x - g.ir.left) / g.ir.width);
    const fy = pts.map((q) => (oy + q.y - g.ir.top) / g.ir.height);
    const lw = pts.reduce((a, q) => a + q.lw, 0) / pts.length;
    return { x0: Math.min(...fx), x1: Math.max(...fx), y0: Math.min(...fy),
             y1: Math.max(...fy), lw: lw, rel: lw / g.ir.width, W: g.ir.width };
  }
  const near = (a, b, tol) => Math.abs(a - b) <= tol;
  function same(a, b) {
    if (!a || !b) return false;
    /* A pixel at the narrowest zoom, and the line's own rounding to a quarter
       pixel, is the whole of the slack. */
    const tol = 1.5 / Math.min(a.W, b.W);
    const wtol = 0.2 / Math.min(a.W, b.W);
    return near(a.x0, b.x0, tol) && near(a.x1, b.x1, tol)
      && near(a.y0, b.y0, tol * 1.8) && near(a.y1, b.y1, tol * 1.8)
      && near(a.rel, b.rel, wtol);
  }
  const show = (s) => (s ? '[' + [s.x0, s.x1, s.y0, s.y1].map((v) => v.toFixed(4)).join(',')
                            + '] w/W=' + s.rel.toFixed(5) : 'nothing painted');

  /* ---- the hands -------------------------------------------------------- */
  function pointer(type, target, x, y) {
    const e = new w.Event(type, { bubbles: true, cancelable: true });
    Object.defineProperties(e, {
      clientX: { value: x }, clientY: { value: y }, pointerType: { value: 'pen' },
      pointerId: { value: 7 }, pressure: { value: 0.5 },
    });
    target.dispatchEvent(e);
  }
  /* A stroke through picture fractions, at whatever the layout is now. */
  async function drawOn(f, fracs) {
    const g = layout().get(f);
    const at = fracs.map(([fx, fy]) => [g.ir.left + fx * g.ir.width, g.ir.top + fy * g.ir.height]);
    const cv = f.querySelector('canvas.ann-layer');
    pointer('pointerdown', cv, at[0][0], at[0][1]);
    for (let i = 1; i < at.length; i++) {
      pointer('pointermove', cv, at[i][0], at[i][1]);
      if (i % 4 === 0) await sleep(1);
    }
    pointer('pointerup', w, at[at.length - 1][0], at[at.length - 1][1]);
    await sleep(10);
  }
  function touch(name, pts) {
    const ev = new w.Event(name, { bubbles: true, cancelable: true });
    Object.defineProperty(ev, 'touches', { value: pts.map(([x, y]) => (
      { clientX: x, clientY: y, touchType: 'direct', radiusX: 10 })) });
    scroller.dispatchEvent(ev);
  }
  /* A pinch to `z`, the way two fingers make one. Nothing else is fired: no
     resize observer, no image load. */
  async function pinchTo(z) {
    doc.body.classList.remove('pen-writing');
    const d = 100 * z / zoom();
    touch('touchstart', [[450, 300], [550, 300]]);
    touch('touchmove', [[500 - d / 2, 300], [500 + d / 2, 300]]);
    touch('touchend', [[500 + d / 2, 300]]);
    await sleep(5);
    if (!near(zoom(), z, 1e-6)) fail(say('the pinch landed at ' + zoom() + ', not ' + z));
  }

  const A = w.Annotate;
  const f1 = figs[0], f2 = figs[1];
  const K1 = f1.dataset.ann, K2 = f2.dataset.ann;
  const RING = '#e8746c', LINE = '#7fb07f';
  const wasOn = A.isOn();
  A.drop(K1); A.drop(K2);
  A.setOn(true);
  A.setTool('pen');
  if (zoom() !== 1) await pinchTo(1);

  try {
    // 1. A ring round the caption of a figure, low on the page, at 100%.
    const ring = [];
    for (let i = 0; i <= 60; i++) {
      const a = (i / 60) * 2 * Math.PI;
      ring.push([0.5 + 0.18 * Math.cos(a), 0.86 + 0.05 * Math.sin(a)]);
    }
    A.setPen(RING, 2.2);
    await drawOn(f1, ring);
    const at1 = seen(f1, RING);
    at1 && near((at1.y0 + at1.y1) / 2, 0.86, 0.015) && near((at1.x0 + at1.x1) / 2, 0.5, 0.015)
      ? ok(say('a ring drawn at 100% is painted where it was drawn on the page picture'))
      : fail(say('the ring is not where it was drawn: ' + show(at1)));

    for (const z of [2.5, 0.5, 1]) {
      await pinchTo(z);
      const got = seen(f1, RING);
      same(got, at1)
        ? ok(say('at ' + Math.round(z * 100) + '% the ring sits on the same place of the '
                 + 'page, at the same width against it'))
        : fail(say('at ' + Math.round(z * 100) + '% the ring moved: ' + show(got)
                   + ' against ' + show(at1)));
    }

    // 2. Ink drawn at 250%, on a page wider than the glass and scrolled
    //    sideways, lands where it was drawn at every other zoom.
    await pinchTo(2.5);
    scroll.left = 600;
    A.setPen(LINE, 2.2);
    const line = [];
    for (let i = 0; i <= 12; i++) line.push([0.3 + 0.1 * i / 12, 0.8]);
    await drawOn(f1, line);
    const at25 = seen(f1, LINE);
    at25 && near(at25.x0, 0.3, 0.004) && near(at25.x1, 0.4, 0.004) && near(at25.y0, 0.8, 0.004)
      ? ok(say('a line drawn at 250%, scrolled sideways, is painted under the nib'))
      : fail(say('the line drawn at 250% is not under the nib: ' + show(at25)));
    scroll.left = 0;
    await pinchTo(1);
    const back = seen(f1, LINE);
    same(back, at25)
      ? ok(say('and at 100% it is in the same place, at the same weight against the page'))
      : fail(say('ink drawn at 250% moved at 100%: ' + show(back) + ' against ' + show(at25)));

    // 3. And after a reload: what would be saved, loaded into a fresh store.
    const saved = JSON.parse(JSON.stringify(A.payload(K1, false).strokes));
    saved.every((s) => !('_d' in s) && !('_bb' in s))
      ? ok(say('a saved stroke carries no painted path, only its points'))
      : fail(say('the painted-path cache went to disk: ' + Object.keys(saved[0]).join(',')));
    A.drop(K1);
    A.load({ [K1]: saved });
    A.redrawAll();
    same(seen(f1, RING), at1) && same(seen(f1, LINE), at25)
      ? ok(say('and after a reload, both marks come back where they were drawn'))
      : fail(say('a reload moved the ink: ' + show(seen(f1, RING)) + ' / '
                 + show(seen(f1, LINE))));

    // 4. INK ALREADY ON DISK, saved against the figure -- picture and caption
    //    -- and in the pen's own pixels at the width the page then had.
    //    `_k` is the geometry it was last painted at, which the old viewer
    //    wrote beside every stroke.
    const WAS = 972, picWas = WAS * f2.querySelector('img').naturalHeight / 1240;
    const HWAS = Math.round(picWas + CAPTION);
    const oldRing = [];
    for (let i = 0; i <= 20; i++) {
      const a = (i / 20) * 2 * Math.PI;
      /* A ring round picture-fraction (0.4, 0.9), stored the old way. */
      oldRing.push(0.4 + 0.1 * Math.cos(a), (0.9 + 0.03 * Math.sin(a)) * picWas / HWAS);
    }
    const oldRec = [{ c: RING, w: 2.2, p: oldRing, pr: oldRing.map(() => 0.5).slice(0, 21),
                      _k: WAS + 'x' + HWAS + '@104,18', _d: [[1, 2, 0.5]] }];
    const onDisk = JSON.stringify(oldRec);
    A.load({ [K2]: JSON.parse(onDisk) });
    A.redrawAll();
    /* The server keeps a page's build stamp and its `sent` only for the very
       strokes on disk, and the library re-saves every marked page to attach
       its picture. So until it is changed, old ink goes back as it came. */
    JSON.stringify(A.payload(K2, false).strokes) === onDisk
      ? ok(say('old ink nobody has changed is saved back exactly as it is on disk'))
      : fail(say('old ink is rewritten by a save that changed nothing: '
                 + JSON.stringify(A.payload(K2, false).strokes).slice(0, 160)));
    const old = seen(f2, RING);
    old && near((old.y0 + old.y1) / 2, 0.9, 0.004) && near((old.x0 + old.x1) / 2, 0.4, 0.004)
      ? ok(say('ink saved against the figure box comes back on the same words of the picture'))
      : fail(say('old ink moved: ' + show(old)));
    old && near(old.rel, 2.2 / WAS, 0.25 / old.W)
      ? ok(say('and at the weight it had against the page when it was drawn'))
      : fail(say('old ink changed weight: ' + old.rel + ' against ' + 2.2 / WAS));
    await pinchTo(2.5);
    same(seen(f2, RING), old)
      ? ok(say('and it follows the zoom like new ink'))
      : fail(say('old ink does not follow the zoom: ' + show(seen(f2, RING))));
    await pinchTo(1);

    // 4b. OLD INK ERASED IN PART BEFORE ITS PICTURE HAS DECODED. The pieces
    //     keep the box they were drawn against, so once the picture is there
    //     they are brought onto it with the rest, not left where they fell.
    A.drop(K2);
    const img2 = f2.querySelector('img');
    Object.defineProperty(img2, 'naturalWidth', { configurable: true, value: 0 });
    A.load({ [K2]: JSON.parse(onDisk) });
    A.redrawAll();
    A.setTool('erase');
    {
      const g = layout().get(f2);
      const yy = 0.9 * picWas / HWAS;
      const cv2 = f2.querySelector('canvas.ann-layer');
      const X = g.ir.left + 0.3 * g.ir.width;
      pointer('pointerdown', cv2, X, g.ir.top + (yy - 0.04) * g.ir.height);
      for (let i = 1; i <= 8; i++) {
        pointer('pointermove', cv2, X, g.ir.top + (yy - 0.04 + 0.01 * i) * g.ir.height);
        await sleep(1);
      }
      pointer('pointerup', w, X, g.ir.top + (yy + 0.04) * g.ir.height);
      await sleep(10);
    }
    A.setTool('pen');
    Object.defineProperty(img2, 'naturalWidth', { configurable: true, value: 1240 });
    A.redrawAll();
    const pieces = A.payload(K2, false).strokes;
    const cut = seen(f2, RING);
    JSON.stringify(pieces) !== onDisk && pieces.every((s) => s.pg)
      && cut && near(cut.y0, 0.87, 0.006) && near(cut.y1, 0.93, 0.006)
      && near(cut.rel, 2.2 / WAS, 0.25 / cut.W)
      ? ok(say('old ink erased in part before its picture loaded lands on the picture with the rest'))
      : fail(say('the pieces of an erased old ring moved or changed weight: ' + show(cut)
                 + ' against w/W=' + (2.2 / WAS).toFixed(5)));

    // 5. A BOARD CARD does not zoom, and its saved ink paints exactly as it
    //    did: fractions of the card, and the pen's width in pixels whatever
    //    width the card has.
    const card = doc.createElement('div');
    card.dataset.card = 'c-zoom-test';
    doc.body.appendChild(card);
    let cw = 600;
    card.getBoundingClientRect = () => rect(100, 900, cw, 200);
    A.attach(card);
    A.load({ 'c-zoom-test': [{ c: RING, w: 2, p: [0.1, 0.5, 0.5, 0.5], pr: [0.5, 0.5] }] });
    A.redrawAll();
    const cv = card.querySelector('canvas.ann-layer');
    const ws = () => inkOf(cv).filter((q) => q.c === RING).map((q) => q.lw);
    const narrow = (cw = 300, A.redrawAll(), ws());
    const wide = (cw = 900, A.redrawAll(), ws());
    narrow.length && narrow.concat(wide).every((v) => v === 2)
      && !('pg' in A.payload('c-zoom-test', false).strokes[0])
      ? ok(say('a board card paints its ink at the width it always has, at any card width'))
      : fail(say('a board card\'s ink changed: ' + narrow.join(',') + ' / ' + wide.join(',')));
    A.drop('c-zoom-test');
    card.remove();
  } finally {
    [K1, K2].forEach((k) => { A.drop(k); });
    A.setOn(wasOn);
    style.remove();
    delete de.clientWidth;
    delete scroller.scrollLeft;
    delete scroller.scrollTop;
    delete scroller.getBoundingClientRect;
    figs.forEach((f) => { delete f.getBoundingClientRect;
                          delete f.querySelector('img').getBoundingClientRect; });
    proto.getContext = oldGet;
    Object.defineProperty(proto, 'width', widthDesc);
    Object.defineProperty(proto, 'height', heightDesc);
  }
};
