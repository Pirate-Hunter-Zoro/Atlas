// The way back, from anywhere.
//
// The writing surface is capped so that pinch-zooming the page cannot make it
// swallow the glass. A cap is a guess at a number, though, and being wrong
// about it strands somebody mid-proof with nothing to pinch on and no way out
// but quitting the app. The button is the part that does not depend on the
// guess being right, which is why it is worth a file of its own.
//
// Two things here are easy to get wrong and impossible to see in a screenshot:
//
//   1. `position: fixed` is fixed to the LAYOUT viewport. Pinching moves the
//      VISUAL one. A control placed by CSS alone therefore slides off the glass
//      at exactly the moment it is needed, and looks perfect in every test that
//      never zooms.
//   2. A tap on a tablet always travels a few pixels. Telling a tap from a drag
//      by distance means the button sometimes moves when it was meant to act,
//      and sometimes acts when it was meant to move. It is told by time.

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

const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
  runScripts: 'outside-only', pretendToBeVisual: true, url: 'https://board.test/board',
});
const { window } = dom;

window.HTMLCanvasElement.prototype.getContext = () =>
  new Proxy({}, { get: () => () => {}, set: () => true });
window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => 800 });
Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 600 });
window.HTMLElement.prototype.getBoundingClientRect = function () {
  return { left: 0, top: 0, width: 800, height: 40, right: 800, bottom: 40, x: 0, y: 0 };
};
window.Element.prototype.scrollIntoView = function () {};
// The slate asks for its saved pages before it can say how many it has,
// and the board now waits for that answer rather than acting on the one
// blank sheet that stands in until it comes. A promise that never settles
// models a board that never finds out; these tests mean a board with
// nothing saved, which is a different thing and has to say so.
window.fetch = (u) => (/slate\/state/.test(String(u))
  ? Promise.resolve({ json: () => Promise.resolve({ pages: [] }) })
  : new Promise(() => {}));
window.renderMathInElement = () => {};
window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
window.EventSource = function () {
  this.readyState = 1; this.close = function () {}; this.addEventListener = function () {};
};

const scrolls = [];
window.scrollTo = function (a, b) {
  scrolls.push(typeof a === 'object' && a ? a.top : b);
};

// jsdom has no visual viewport, which is the whole subject here, so stand one
// up that can be zoomed and panned on demand.
const vv = new window.EventTarget();
vv.width = 800; vv.height = 600; vv.offsetLeft = 0; vv.offsetTop = 0; vv.scale = 1;
Object.defineProperty(window, 'visualViewport', { value: vv, configurable: true });
// Placement is coalesced to one per animation frame — this fires on every scroll
// event, and a forced layout per scroll frame is how a page that is merely
// scrolling starts to stutter. So a zoom has to be given a frame to land in.
const zoomTo = async (scale, offsetLeft, offsetTop) => {
  vv.scale = scale;
  vv.width = 800 / scale;
  vv.height = 600 / scale;
  vv.offsetLeft = offsetLeft;
  vv.offsetTop = offsetTop;
  vv.dispatchEvent(new window.Event('resize'));
  await sleep(10);
};

window.addEventListener('error', (e) => fail('uncaught: ' + e.message));

for (const f of ['typeface.js', 'macros.js', 'gauge.js', 'recentre.js', 'plane-core.js', 'ink-core.js', 'slate-core.js', 'annotate.js', 'reader.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
try { window.eval(fs.readFileSync(path.join(WEB, 'board.js'), 'utf8')); }
catch (e) { fail('board.js: ' + e.message); }

const doc = window.document;
const btn = doc.getElementById('panic');
const meta = doc.querySelector('meta[name="viewport"]');
const metaWas = meta && meta.getAttribute('content');

const at = () => {
  const m = /translate\(([-\d.]+)px,\s*([-\d.]+)px\)\s*scale\(([\d.]+)\)/
    .exec(btn.style.transform || '');
  return m ? { x: +m[1], y: +m[2], k: +m[3] } : null;
};
const press = (type, x, y) => btn.dispatchEvent(
  new window.MouseEvent(type, { bubbles: true, clientX: x || 0, clientY: y || 0 }));

(async function () {
  if (!btn) {
    fail('there is no way back: the board has no re-centre button at all');
    console.log('\n' + errors.length + ' FAILURES');
    process.exit(1);
  }
  ok('the board carries a re-centre button');

  // 1. Always there. Not conditional on a mode, a card, or an answer being owed
  //    — the state it exists to rescue you from is one you can reach at any
  //    moment, including one where nothing else on the page can be reached.
  !btn.hidden ? ok('and it is present without being asked for')
              : fail('the button starts hidden, so it is not there when it is needed');
  {
    const js = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
    !/els\.panic\.hidden\s*=/.test(js)
      ? ok('and nothing in the board ever takes it away')
      : fail('something hides the button; the one guarantee is then conditional');
  }

  // 2. It is placed against the visual viewport, not by CSS.
  const first = at();
  first ? ok('it is placed from JavaScript: ' + btn.style.transform)
        : fail('nothing positioned the button — CSS alone cannot follow a pinch');

  // 3. Zoom the page in and pan to the far corner. This is the state that
  //    stranded a person: everything fixed by CSS is now off the glass.
  await zoomTo(2, 300, 200);
  const zoomed = at();
  if (!zoomed) {
    fail('the button lost its position when the page was zoomed');
  } else {
    Math.abs(zoomed.k - 0.5) < 0.001
      ? ok('zoomed to 2×, it counter-scales to 0.5 and stays a thumb wide')
      : fail('the button scales with the page: at 2× it is drawn at ' + zoomed.k);
    zoomed.x >= vv.offsetLeft && zoomed.x <= vv.offsetLeft + vv.width &&
    zoomed.y >= vv.offsetTop && zoomed.y <= vv.offsetTop + vv.height
      ? ok('and it followed the visible window into the corner it was panned to')
      : fail('the button sits at ' + zoomed.x + ',' + zoomed.y + ' — outside the '
             + 'visible window at ' + vv.offsetLeft + ',' + vv.offsetTop);
    zoomed.x !== first.x || zoomed.y !== first.y
      ? ok('which is to say it moved when the page did')
      : fail('the button did not move at all; it is pinned to the layout');
  }

  // 4. A tap. It travels a couple of pixels, as every tap on a tablet does,
  //    and it must still be a tap.
  scrolls.length = 0;
  press('pointerdown', 400, 300);
  press('pointermove', 402, 303);
  press('pointerup', 402, 303);

  // It is a zoom control and nothing else. Being zoomed too far into the writing
  // is not the same as being in the wrong part of the transcript, and answering
  // the first with the second takes the page away from somebody who was looking
  // at exactly the right thing.
  !scrolls.length
    ? ok('a tap leaves the lesson exactly where it was')
    : fail('the button scrolled the page; it is a zoom control, not a jump');
  btn.classList.contains('hit')
    ? ok('and says out loud that it did something, since a change of scale is '
         + 'easy to miss')
    : fail('a tap gave no sign at all that it had been received');
  !btn.classList.contains('holding')
    ? ok('and a tap that travelled three pixels was not mistaken for a drag')
    : fail('the button was picked up by a tap; distance is being used to decide');

  const during = meta && meta.getAttribute('content');
  /maximum-scale=1/.test(during || '')
    ? ok('and it asks the browser to drop the magnification')
    : fail('nothing attempts to undo the page zoom: ' + during);

  // The clamp must be temporary. A board that can never be zoomed in again is a
  // worse outcome than the one this fixes.
  await sleep(650);
  meta.getAttribute('content') === metaWas
    ? ok('and lifts the clamp again, so the page can still be zoomed by hand')
    : fail('the viewport was left clamped: ' + meta.getAttribute('content'));

  // Safari on an iPad ignores the clamp, and jsdom's zoom did not drop either.
  // A kept zoom is the one case the content is moved, since nothing else can be.
  await sleep(100);
  scrolls.length
    ? ok('when the browser keeps its zoom, the newest card is brought under the glass')
    : fail('the zoom stayed and the tap did nothing a reader could see');

  // And a zoom that DID drop leaves the lesson where it was.
  scrolls.length = 0;
  press('pointerdown', 400, 300);
  press('pointerup', 400, 300);
  await zoomTo(1, 0, 0);
  await sleep(750);
  !scrolls.length
    ? ok('and when the zoom does drop, nothing is scrolled')
    : fail('the zoom dropped and the page was scrolled anyway');
  await zoomTo(2, 300, 200);

  // The page itself is never pinched: Safari gives a page no way to undo that.
  {
    const css = fs.readFileSync(path.join(WEB, 'board.css'), 'utf8');
    /(^|\n)html\s*\{\s*touch-action:\s*pan-x pan-y;\s*\}/.test(css)
      && !/touch-action:[^;]*pinch-zoom/.test(css)
      ? ok('the page cannot be pinched, anywhere on it')
      : fail('something on the page still lets the browser pinch it');
    const g = new window.Event('gesturestart', { cancelable: true });
    doc.dispatchEvent(g);
    g.defaultPrevented
      ? ok('and Safari\'s own pinch gesture is refused too')
      : fail('gesturestart reaches Safari, which pinches the page from it');
  }

  // 5. Findable. It is a rescue, and the state it rescues you from is one where
  //    the screen is already full of something else — so it carries its own name
  //    and the board's accent rather than being a dim circle in a corner.
  {
    /re-cent/i.test(btn.textContent)
      ? ok('the button says what it does')
      : fail('the button is unlabelled: ' + JSON.stringify(btn.textContent));
    const css = fs.readFileSync(path.join(WEB, 'board.css'), 'utf8');
    // The rule is shared with the re-centres for the other two zooms on this
    // page -- the writing surface's, and the map's. One shape, one corner.
    const rule = (css.match(/#panic(?:,\s*#(?:findink|mapback))*\s*\{[^}]*\}/) || [''])[0];
    /background:\s*var\(--accent\)/.test(rule)
      ? ok('and is painted in the accent, not in the page it sits on')
      : fail('the button has no contrasting fill; it reads as a smudge');

    // 5b. There are two zooms on this page and only one of them had a way back.
    //     `#panic` puts the PAGE's magnification back; the writing surface has a
    //     zoom of its own that it knows nothing about, and getting lost in that
    //     one left the toolbar's ⤢ as the only way out — in the page chrome,
    //     which is exactly what pinching pans off the glass.
    const find = doc.getElementById('findink');
    find
      ? ok('the writing surface has a re-centre of its own')
      : fail('there is no way back from a zoom into the writing');
    const said = (n) => (n ? (n.textContent || '').trim().toLowerCase() : '');
    find && said(find) && said(find) !== said(btn)
      ? ok('and it says which of the two it is')
      : fail('the two re-centres are not tellable apart: both say "'
             + said(btn) + '"');
    /ink|writ/.test(said(find))
      ? ok('and what it says is about the writing, not about the page')
      : fail('the writing re-centre is labelled "' + said(find)
             + '", which names neither the writing nor whose it is');
    find && find.hidden
      ? ok('and is absent while there is no surface to be lost on')
      : fail('a button offering to find writing on a board that is not there');
    /#panic,\s*#findink[^{]*\{[^}]*position:\s*fixed/.test(css)
      ? ok('and is placed by script against the visible window, as the other is')
      : fail('the second button is laid out by CSS alone, so a pinch takes it '
             + 'off the glass at the moment it is wanted');
    // Asked of the RUNNING page rather than of the source: where the placement
    // lives moved once already, when the front door needed the same stack and
    // the machinery came out into `recentre.js`. What must be true is that the
    // button ends up carrying a transform, wherever the code for it sits.
    if (find) {
      find.hidden = false;
      window.Recentre.remeasure();
      window.Recentre.place();
      /translate/.test(find.style.transform || '')
        ? ok('and rides under the first, so there is one thing to move')
        : fail('nothing ever positions it');
      find.hidden = true;
      window.Recentre.place();
    }
    !/opacity:\s*0?\.[0-8]/.test(rule)
      ? ok('and is not dimmed away')
      : fail('the button is still faded out at rest');
  }

  // 6. A press and hold picks it up, and where it is put is where it stays.
  await zoomTo(1, 0, 0);
  const before = at();
  scrolls.length = 0;
  try { window.localStorage.removeItem('board.panic'); } catch (e) {}

  press('pointerdown', 600, 200);
  await sleep(500);
  btn.classList.contains('holding')
    ? ok('a press and hold picks the button up, and says so before it moves')
    : fail('holding the button does nothing; there is no way to get it out of the way');

  press('pointermove', 120, 480);
  const moved = at();
  moved && (moved.x !== before.x || moved.y !== before.y)
    ? ok('and it follows the finger across the screen')
    : fail('the button was held but would not move');

  press('pointerup', 120, 480);
  !btn.classList.contains('holding')
    ? ok('letting go puts it down')
    : fail('the button is still being held after the finger left');
  !scrolls.length
    ? ok('and moving it is not also a tap, so nothing jumped underneath it')
    : fail('the drag re-centred the board as well — every move is now a surprise');

  let stored = null;
  // Each button is remembered under its own key: they are separate widgets and
  // a shared anchor is what made them one.
  try { stored = JSON.parse(window.localStorage.getItem('board.panic.panic') || 'null'); }
  catch (e) { /* reported below */ }
  stored && typeof stored.x === 'number'
    ? ok('where it was put is remembered, so it is not re-placed every session')
    : fail('the position is not saved; the button walks home on every reload');
  stored && stored.x >= 0 && stored.x <= 1 && stored.y >= 0 && stored.y <= 1
    ? ok('and remembered as a fraction of the window, so a rotation keeps it on screen')
    : fail('the position was saved in pixels: ' + JSON.stringify(stored));

  // 7. Wherever it is put, it stays on the glass. A control dragged to the very
  //    edge and then met with a rotation or a zoom must not end up half off it.
  window.localStorage.setItem('board.panic', JSON.stringify({ x: 1, y: 1 }));
  await zoomTo(3, 500, 400);
  const corner = at();
  const bw = (btn.offsetWidth || 108) / 3, bh = (btn.offsetHeight || 32) / 3;
  corner && corner.x + bw <= vv.offsetLeft + vv.width + 1 &&
            corner.y + bh <= vv.offsetTop + vv.height + 1
    ? ok('pushed into the corner it is still wholly on the glass')
    : fail('the button can be pushed past the edge of the visible window');

  // 8. AND THE SAME LESSON, IN THE OVERFLOW MENU.
  //
  // The button above is placed from the visual viewport because `position:
  // fixed` is fixed to the LAYOUT one, and the two part company the moment
  // anybody pinches or the keyboard comes up. The ⋯ menu had the identical
  // defect in the identical place -- `placeMenu` capped its height against
  // `window.innerHeight` -- and it produced both halves of one report:
  //
  //   "There are three dots I can tap to get a menu of other things I can do,
  //    like refresh the app, etc. That isn't scrollable - or at least when I
  //    try to scroll it, the main session page behind it is what scrolls
  //    instead."
  //
  // A cap bigger than the glass puts the last entries off the bottom AND stops
  // the menu overflowing its own box -- and a box that does not overflow is not
  // a scroller, so iOS gives the drag to the page. One wrong number, both
  // complaints.
  {
    await zoomTo(1, 0, 0);
    const more = doc.getElementById('btn-more');
    const menu = doc.getElementById('barmenu');
    more && menu
      ? ok('the board has an overflow menu and a control to open it')
      : fail('no overflow menu to measure');

    if (more && menu) {
      // The keyboard up under a typed answer: half the glass gone, and
      // `window.innerHeight` has not moved a pixel.
      vv.height = 260;
      vv.width = 800;
      vv.offsetTop = 0;
      vv.offsetLeft = 0;
      vv.dispatchEvent(new window.Event('resize'));
      await sleep(10);

      more.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
      await sleep(10);
      !menu.hidden ? ok('and it opens') : fail('the menu did not open');

      const cap = parseFloat(menu.style.maxHeight || '0');
      cap > 0 && cap <= 260
        ? ok('and is capped to what can actually be seen (' + cap + 'px of a '
             + '260px visible viewport)')
        : fail('the menu is capped at ' + cap + 'px against a visible viewport '
               + 'of 260px: its last entries are off the glass and it does not '
               + 'overflow, so the drag goes to the lesson');
      /px$/.test(menu.style.top || '')
        ? ok('and hung from a measured top rather than an ancestor\'s edge')
        : fail('nothing placed the menu; CSS alone cannot follow a keyboard');

      // And it follows the glass while it is open, rather than being measured
      // once and left behind.
      const was = parseFloat(menu.style.maxHeight);
      vv.height = 520;
      vv.dispatchEvent(new window.Event('resize'));
      await sleep(30);
      const roomy = parseFloat(menu.style.maxHeight);
      roomy > was
        ? ok('and is measured again when the keyboard goes away')
        : fail('the menu keeps the cap it was opened with, so it stays wrong '
               + 'for as long as it is up');

      // 9. AND IT STOPS ABOVE THE WRITING TOOLBAR.
      //
      // `#drawbar` is fixed to the bottom and grows UPWARD -- it is
      // `column-reverse`, so the slate's own menu and selection bar open above
      // the tool row -- and on a board with the pen out it reaches well into
      // the lower half of this menu. Being painted on top of it is not the
      // same as not overlapping it: an entry drawn over a black tool bar is
      // still an entry nobody can read.
      const drawbar = doc.getElementById('drawbar');
      drawbar.hidden = false;
      drawbar.getBoundingClientRect = () => ({
        left: 0, right: 800, width: 800, top: 380, bottom: 520, height: 140,
        x: 0, y: 380,
      });
      vv.dispatchEvent(new window.Event('resize'));
      await sleep(30);
      const capped = parseFloat(menu.style.maxHeight);
      const top = parseFloat(menu.style.top);
      capped <= 380 - top + 1
        ? ok('and stops above the writing toolbar (' + capped + 'px, toolbar at '
             + '380 with the menu opening at ' + top + ')')
        : fail('the menu runs down behind the writing toolbar: ' + capped
               + 'px from ' + top + ' reaches ' + (top + capped)
               + ', and the toolbar starts at 380');
      capped < roomy
        ? ok('so the toolbar coming out actually costs it room')
        : fail('the toolbar was ignored entirely');
      drawbar.hidden = true;
      delete drawbar.getBoundingClientRect;
    }
  }

  // --- THE MAP IS RETIRED, AND EVERY WAY TO IT WITH IT ----------------------
  //
  // A session starts generic and names its subject from the header's chip;
  // there is no map to go back to. Every control that opened it is drawn
  // nowhere -- the bar's, each drawer's, the reader's and the slate's -- until
  // T51 deletes the map's code.
  {
    const css = fs.readFileSync(path.join(WEB, 'board.css'), 'utf8');
    /\[data-retired\][^{]*\.to-map\s*{\s*display:\s*none\s*!important/.test(css)
      ? ok('every .to-map control is drawn nowhere')
      : fail('a way to the retired map is still drawn');
    const bar = doc.getElementById('btn-map');
    !bar || bar.hasAttribute('data-retired')
      ? ok('the title bar carries no way to the map')
      : fail('the title bar still opens the map');
    const slate = fs.readFileSync(path.join(WEB, 'slate.html'), 'utf8');
    /<a id="tomap" hidden/.test(slate)
      ? ok('nor does the writing surface')
      : fail('/slate still links to the map');
  }

  // 8. THE MAP IS A PLANE, AND A PLANE CAN BE PANNED INTO NOTHING.
  //    The map covers the whole glass and has a pan and a zoom the page knows
  //    nothing about; its own ⤢ is page chrome, which a pinch takes away. So it
  //    gets the same treatment the writing surface already had -- and the stack
  //    has to be ABOVE the map while one is open, which is the one thing the
  //    z-index order got wrong for as long as the map has existed.
  {
    const back = doc.getElementById('mapback');
    back ? ok('the map has a re-centre of its own')
         : fail('a map panned into empty space has no way back');
    back && back.hidden
      ? ok('and is absent while there is no map to be lost on')
      : fail('the map re-centre is offered with no map on the glass');
    back && /map/i.test(back.textContent)
      ? ok('and says which of the three it is')
      : fail('the three re-centres are not tellable apart');
    const css = fs.readFileSync(path.join(WEB, 'board.css'), 'utf8');
    const mapZ = (css.match(/#map\s*\{[^}]*z-index:\s*(\d+)/) || [])[1];
    const upZ = (css.match(/body\.mapping\s+#panic[^{]*\{[^}]*z-index:\s*(\d+)/) || [])[1];
    (mapZ && upZ && Number(upZ) > Number(mapZ))
      ? ok('and the stack rises over the map, which used to paint over it')
      : fail('the way back is underneath the thing it is a way back from');
    // And only there: everywhere else the stack's ordinary place in the order is
    // the right one -- over the lesson, under the menu.
    /body\.mapping\s+#panic/.test(css)
      ? ok('and only while the map is open')
      : fail('the stack was raised everywhere, so it now sits over the menu');
  }

  // 8b. AND EACH OF THEM MOVES ITSELF, AND NOTHING ELSE.
  //
  //     They were one stack with one anchor: a press on any of them moved all
  //     three, because all three were one object. They are three now -- putting
  //     the zoom back, finding your own writing, and abandoning the plan have
  //     nothing to do with each other -- and a control that moves something other
  //     than itself is a control nobody can aim. Asked for as: "make the
  //     re-centre, the writing re-centre, and the change direction buttons
  //     independent of each other - three separate widgets not stuck to each
  //     other."
  {
    const turn = doc.getElementById('redirect');
    const spot = (el) => {
      const m = /translate\(([-\d.]+)px,\s*([-\d.]+)px\)/.exec(el.style.transform || '');
      return m ? { x: +m[1], y: +m[2] } : null;
    };
    const wasPanic = at();
    const wasTurn = spot(turn);
    const press2 = (type, x, y) => turn.dispatchEvent(
      new window.MouseEvent(type, { bubbles: true, clientX: x || 0, clientY: y || 0,
                                    pointerId: 9 }));
    press2('pointerdown', 600, 300);
    await sleep(500);
    turn.classList.contains('holding')
      ? ok('a press and hold picks up whichever button is under the thumb')
      : fail('only one of them can be moved, which nobody was told');
    press2('pointermove', 200, 520);
    const nowTurn = spot(turn);
    nowTurn && wasTurn && (nowTurn.x !== wasTurn.x || nowTurn.y !== wasTurn.y)
      ? ok('and that one follows the finger')
      : fail('the button was held but would not move');
    const nowPanic = at();
    nowPanic && wasPanic
      && nowPanic.x === wasPanic.x && nowPanic.y === wasPanic.y
      ? ok('while the others stay exactly where they were put')
      : fail('moving one dragged the rest along behind it — they are still one '
             + 'object wearing three coats');

    press2('pointerup', 200, 520);
    !turn.classList.contains('holding')
      ? ok('and it is put down where it was left')
      : fail('the button is still held after the finger lifted');
    let mine = null;
    try { mine = JSON.parse(window.localStorage.getItem('board.panic.redirect') || 'null'); }
    catch (e) { /* reported below */ }
    mine && typeof mine.x === 'number'
      ? ok('and remembered under its own name, not the group\'s')
      : fail('where this one was put was not saved separately, so the next '
             + 'session puts it back with the others');
  }

  // 8c. SEND MY ANNOTATIONS IS ONE OF THEM TOO.
  //
  //     It sat pinned to the bottom centre of the glass, which is where the ink
  //     is. Asked for as: "I want it to be a movable widget like the re-center,
  //     my ink, and rethink buttons."
  {
    const send = doc.getElementById('notesend');
    const press3 = (type, x, y) => send.dispatchEvent(
      new window.MouseEvent(type, { bubbles: true, clientX: x || 0, clientY: y || 0,
                                    pointerId: 11 }));
    // Always on the glass, marks or none, and a tap opens the picker.
    !send.hidden && !window.Annotate.marked().length
      ? ok('send my annotations is on the glass with nothing marked')
      : fail('send my annotations hides while nothing is marked');
    const pick = doc.getElementById('notepick');
    press3('pointerdown', 400, 560);
    press3('pointerup', 400, 560);
    await sleep(20);
    pick && !pick.hidden
      ? ok('a tap on it opens the picker')
      : fail('a tap on send my annotations did not open the picker');
    pick && pick.querySelector('#notepick-send').disabled
      && !pick.querySelector('.notepick-row')
      ? ok('which, with nothing marked, lists nothing and will not send')
      : fail('the picker offers something to send with nothing marked');
    doc.body.dispatchEvent(new window.MouseEvent('pointerdown', { bubbles: true }));
    pick && pick.hidden
      ? ok('and a tap outside closes it')
      : fail('the picker stays open after a tap outside it');
    {
      const pcss = fs.readFileSync(path.join(WEB, 'board.css'), 'utf8');
      /body\.mapping #notesend[^{]*\{[^}]*z-index:\s*97/.test(pcss)
        || /body\.mapping #notesend\s*\{[^}]*z-index:\s*97/.test(pcss)
        || /body\.mapping #mapback,\s*body\.mapping #notesend\s*\{\s*z-index:\s*97/.test(pcss)
        ? ok('and it is raised over the map with the rest of the stack')
        : fail('send my annotations is painted under the map');
      const z = /#notepick\s*\{[^}]*z-index:\s*(\d+)/.exec(pcss);
      z && +z[1] > 96 && +z[1] < 99
        ? ok('the picker sits over the map and under the menu')
        : fail('the picker is under the map or over the menu');
    }
    press3('pointerdown', 400, 560);
    await sleep(500);
    send.classList.contains('holding')
      ? ok('send my annotations can be pressed and held to move it')
      : fail('send my annotations is still pinned where the stack cannot move it');
    press3('pointermove', 120, 200);
    press3('pointerup', 120, 200);
    let put = null;
    try { put = JSON.parse(window.localStorage.getItem('board.panic.notesend') || 'null'); }
    catch (e) { /* reported below */ }
    put && typeof put.x === 'number'
      ? ok('and where it is put is remembered under its own name')
      : fail('send my annotations was moved and forgotten');
    const ncss = fs.readFileSync(path.join(WEB, 'board.css'), 'utf8');
    /\.notesend\s*\{[^}]*left:\s*0;\s*top:\s*0/.test(ncss)
      && !/\.notesend\s*\{[^}]*bottom:/.test(ncss)
      ? ok('and it is placed from JavaScript, not docked by CSS')
      : fail('send my annotations is still docked to the bottom by CSS');
  }

  // 9. THE FRONT DOOR HAS ONE WAY TO BE LOST, and it needs the one button.
  //    There were two: the page's own magnification, and an atlas that was a
  //    plane with a pan of its own. The atlas is two levels of HTML now -- six
  //    families is a list of six and a list is not a diagram -- so the plane is
  //    gone and so is the button that put it back. The page still pinches like
  //    any other, which is what this half is for.
  {
    const home = fs.readFileSync(path.join(WEB, 'home.html'), 'utf8');
    /id="panic"/.test(home)
      ? ok('the front door has the page re-centre too')
      : fail('a pinched front door has no way back');
    !/id="atlasback"/.test(home)
      ? ok('and no second one, because there is no plane on it to pan')
      : fail('the front door still carries a way back to a plane it does not '
             + 'have');
    /static\/recentre\.js/.test(home)
      ? ok('and it is the same machinery, not a second copy of it')
      : fail('the front door spells the stack its own way');
    const hcss = fs.readFileSync(path.join(WEB, 'home.css'), 'utf8');
    /#panic\s*\{[^}]*position:\s*fixed/.test(hcss)
      ? ok('and it is placed against the visible window, as on the board')
      : fail('the front door lays it out by CSS alone, so a pinch takes it '
             + 'off the glass at the moment it is wanted');
  }

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\nthere is always a way back');
  process.exit(errors.length ? 1 : 0);
})();
