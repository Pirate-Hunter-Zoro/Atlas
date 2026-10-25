// The answer box docks on the iPad keyboard.
//
// With the full keyboard up, the typed answer box was under the keys or
// scrolled away from them. While `#saybox` has the focus and the keys take more
// than 120px of the window, `#typebox` is fixed to the top of the keys and the
// lesson scrolls behind it; it can be made tall; and the textarea is never
// moved, because moving a focused element closes the keyboard. A pinch-zoom
// shortens the visual viewport too, and that is no keyboard. Nor does the
// surface move under a card while the box has the focus: the move waits for
// the blur.
//
// jsdom has no visual viewport and no keyboard, so both are faked: the
// keyboard is the visual viewport getting shorter than the window.
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
const check = (cond, good, bad) => (cond ? ok(good) : fail(bad));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
  runScripts: 'outside-only', pretendToBeVisual: true, url: 'https://board.test/board',
});
const { window } = dom;
const doc = window.document;

window.HTMLCanvasElement.prototype.getContext = () =>
  new Proxy({}, { get: () => () => {}, set: () => true });
window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => 1024 });
Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 600 });
Object.defineProperty(window.HTMLElement.prototype, 'offsetHeight', {
  get() { return this.id === 'typebox' ? 180 : 40; },
});
window.HTMLElement.prototype.getBoundingClientRect = function () {
  return { left: 0, top: 0, width: 1024, height: 40, right: 1024, bottom: 40, x: 0, y: 0 };
};
window.Element.prototype.scrollIntoView = function () {};
window.fetch = (u) => (/slate\/state/.test(String(u))
  ? Promise.resolve({ json: () => Promise.resolve({ pages: [] }) })
  : new Promise(() => {}));
window.renderMathInElement = () => {};
window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
window.EventSource = function () {
  window.__es = this;
  this.readyState = 1; this.close = function () {}; this.addEventListener = function () {};
};
window.addEventListener('error', (e) => fail('uncaught: ' + e.message));

// An iPad in portrait: the window is 1366 tall, and the keyboard is the visual
// viewport getting shorter than it.
const H = 1366;
Object.defineProperty(window, 'innerHeight', { value: H, configurable: true, writable: true });
// The layout viewport, which moves with neither the pinch nor the keys.
let layoutH = H;
Object.defineProperty(doc.documentElement, 'clientHeight', { get: () => layoutH });
const vv = new window.EventTarget();
vv.width = 1024; vv.height = H; vv.offsetLeft = 0; vv.offsetTop = 0; vv.scale = 1;
Object.defineProperty(window, 'visualViewport', { value: vv, configurable: true });
const keys = async (height, offsetTop = 0, type = 'resize') => {
  vv.height = H - height;
  vv.offsetTop = offsetTop;
  vv.dispatchEvent(new window.Event(type));
  await sleep(10);
};

for (const f of ['typeface.js', 'macros.js', 'recentre.js', 'plane-core.js', 'ink-core.js',
                 'slate-core.js', 'annotate.js', 'reader.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
try { window.eval(fs.readFileSync(path.join(WEB, 'board.js'), 'utf8')); }
catch (e) { fail('board.js: ' + e.message); }

const writer = doc.getElementById('writer');
const typebox = doc.getElementById('typebox');
const saybox = doc.getElementById('saybox');
const sayrow = doc.getElementById('sayrow');
const said = doc.getElementById('said');
const grow = doc.getElementById('say-grow');
// A long answer, so the box's own height is what the cap decides.
Object.defineProperty(saybox, 'scrollHeight', { get: () => 2000, configurable: true });

const docked = () => typebox.classList.contains('say-docked');
const px = (v) => parseFloat(v || '0');

(async () => {
  await sleep(20);
  writer.hidden = false;
  typebox.hidden = false;

  // ----------------------------------------------------- no keyboard, no dock
  saybox.focus();
  await sleep(10);
  check(doc.activeElement === saybox && !docked(),
        'focused with no keyboard up, the box stays in the lesson',
        'the box docked with no keyboard (' + docked() + ')');

  // ------------------------------------- the floating keyboard leaves it be
  await keys(100);
  check(!docked(), 'a keyboard taking 100px (the floating one) does not dock it',
        'the box docked over a 100px keyboard');

  // ------------------------------------------- the full keyboard docks it
  await keys(400);
  check(docked(), 'the full keyboard up docks the box on the keys',
        'with a 400px keyboard the box did not dock');
  check(typebox.style.top === (H - 400) + 'px' && typebox.style.width === '1024px'
        && typebox.style.left === '0px',
        'at the top of the keys, across the visible width (' + typebox.style.top + ')',
        'the dock is at ' + typebox.style.cssText);
  const hold = doc.getElementById('say-hold');
  check(hold && hold.nextElementSibling === typebox && hold.style.height === '180px',
        'a placeholder holds its 180px in the lesson',
        'the placeholder is ' + (hold ? hold.outerHTML : 'missing'));
  check(px(doc.body.style.paddingBottom) === 180 + 400,
        'and the body is padded so every card scrolls above the dock ('
        + doc.body.style.paddingBottom + ')',
        'the body padding is "' + doc.body.style.paddingBottom + '"');
  check(saybox.parentNode === sayrow && typebox.parentNode === writer
        && doc.activeElement === saybox,
        'the textarea never moved, and still has the focus',
        'the textarea was moved, or lost the focus');

  // ------------------------------------------------- the box, while docked
  check(px(saybox.style.height) === Math.round((H - 400) * 0.4),
        'a long answer grows the box to 40% of what can be seen (' + saybox.style.height + ')',
        'docked, the box is ' + saybox.style.height + ', not 40% of ' + (H - 400));
  check(px(said.style.maxHeight) === Math.round((H - 400) * 0.25),
        'and the rendered block above it to 25%',
        'the block above the box is capped at "' + said.style.maxHeight + '"');
  grow.dispatchEvent(new window.MouseEvent('mousedown', { bubbles: true, cancelable: true }));
  grow.click();
  await sleep(5);
  check(typebox.classList.contains('say-tall')
        && px(saybox.style.height) === Math.round((H - 400) * 0.6)
        && doc.activeElement === saybox,
        'the grow key makes it tall, about 60%, and the keyboard stays up',
        'after the grow key the box is ' + saybox.style.height + ', tall '
        + typebox.classList.contains('say-tall') + ', focus on ' + doc.activeElement.id);
  grow.click();
  await sleep(5);
  check(!typebox.classList.contains('say-tall')
        && px(saybox.style.height) === Math.round((H - 400) * 0.4),
        'and pressed again, back to 40%', 'the grow key does not toggle back');

  // ------------------------------------------- the lesson scrolls behind it
  await keys(400, 250, 'scroll');
  check(typebox.style.top === (250 + H - 400) + 'px',
        'when the visible part scrolls, the dock follows the keys',
        'after a scroll the dock is at ' + typebox.style.top);
  vv.width = 1366;
  vv.height = 1024 - 400;
  vv.offsetTop = 0;
  Object.defineProperty(window, 'innerHeight', { value: 1024, configurable: true });
  layoutH = 1024;
  window.dispatchEvent(new window.Event('orientationchange'));
  await sleep(10);
  check(typebox.style.width === '1366px' && typebox.style.top === '624px',
        'turning the iPad re-docks it on the new keys',
        'after turning the dock is ' + typebox.style.cssText);
  Object.defineProperty(window, 'innerHeight', { value: H, configurable: true, writable: true });
  layoutH = H;
  vv.width = 1024;
  await keys(400);

  // ----------------------------------------------------- blur undocks it
  saybox.blur();
  await sleep(10);
  check(!docked() && !doc.getElementById('say-hold') && doc.body.style.paddingBottom === ''
        && typebox.style.top === '' && said.style.maxHeight === '',
        'losing the focus undocks it and clears the placeholder, padding and position',
        'after a blur: docked ' + docked() + ', ' + typebox.style.cssText
        + ', body "' + doc.body.style.paddingBottom + '"');
  check(px(saybox.style.height) === 144,
        'and the box is capped at 144px again', 'undocked, the box is ' + saybox.style.height);

  // ------------------------------------- a hidden typebox never docks
  typebox.hidden = true;
  saybox.focus();
  await keys(400);
  check(!docked(), 'the write half showing, the box does not dock', 'a hidden typebox docked');
  typebox.hidden = false;
  saybox.blur();

  // ------------------------------------------- a pinch-zoom is not a keyboard
  // Zoomed to 1.5, the visible part is two thirds of the window by the zoom
  // alone; scaled back up it is the whole window, and nothing docks.
  vv.scale = 1.5;
  saybox.focus();
  vv.height = H / 1.5;
  vv.dispatchEvent(new window.Event('resize'));
  await sleep(10);
  check(!docked() && doc.body.style.paddingBottom === '',
        'zoomed to 1.5 with no keyboard, the box does not dock and the body is not padded',
        'a pinch-zoom docked the box (' + docked() + ') or padded the body "'
        + doc.body.style.paddingBottom + '"');
  vv.height = (H - 400) / 1.5;
  vv.dispatchEvent(new window.Event('resize'));
  await sleep(10);
  check(docked() && px(doc.body.style.paddingBottom) === 180 + 400,
        'zoomed with the full keyboard up, it docks and pads by the keys alone',
        'zoomed with a 400px keyboard: docked ' + docked() + ', body "'
        + doc.body.style.paddingBottom + '"');
  // Safari on the iPad shrinks innerHeight with the pinch as well; Chrome, as
  // above, does not. Both have to read the same keys.
  window.innerHeight = H / 1.5;
  vv.height = H / 1.5;
  vv.dispatchEvent(new window.Event('resize'));
  await sleep(10);
  check(!docked() && doc.body.style.paddingBottom === '',
        'with Safari\'s innerHeight shrunk by the zoom too, no keyboard still docks nothing',
        'Safari\'s zoom docked the box (' + docked() + ') or padded the body "'
        + doc.body.style.paddingBottom + '"');
  vv.height = (H - 400) / 1.5;
  vv.dispatchEvent(new window.Event('resize'));
  await sleep(10);
  check(docked() && px(doc.body.style.paddingBottom) === 180 + 400,
        'and the full keyboard docks it there, padded by the keys alone',
        'Safari zoomed with a 400px keyboard: docked ' + docked() + ', body "'
        + doc.body.style.paddingBottom + '"');
  saybox.blur();
  window.innerHeight = H;
  vv.scale = 1;
  await keys(0);

  // --------------------------------------------------------- the CSS
  {
    const css = fs.readFileSync(path.join(WEB, 'board.css'), 'utf8');
    const rule = /#typebox\.say-docked\s*\{([^}]*)\}/.exec(css);
    check(rule && /position:\s*fixed/.test(rule[1]) && /z-index:\s*45/.test(rule[1])
          && /background:\s*#15161a/.test(rule[1]),
          'the dock is fixed, at z-index 45, on the writer\'s paper',
          'the .say-docked rule is ' + (rule ? rule[1].trim() : 'missing'));
    const ta = /#typebox textarea\s*\{([^}]*)\}/.exec(css);
    const size = ta && /font-size:\s*([^;]+);/.exec(ta[1]);
    check(size && /max\(16px/.test(size[1]),
          'the textarea\'s font is at least 16px, so iOS does not zoom on focus',
          'the textarea\'s font-size is ' + (size ? size[1] : 'unset'));
    check(saybox.tagName === 'TEXTAREA' && !saybox.hasAttribute('inputmode'),
          'and it is the system keyboard\'s textarea, with dictation',
          'the answer box asks for a keyboard of its own');
  }

  // ------------------------------- the surface does not move under the box
  // A typed answer and the reply to it each move the surface down the lesson,
  // and a move would take the focus off the box and the keyboard down
  // mid-word. Focused, the surface stays put and the new cards land above it,
  // which is where it would have gone anyway. A sitting doing the work opens
  // on the box.
  {
    const t0 = Date.now() / 1000 - 3600;
    const q = (id, at) => ({ id: id, kind: 'question', title: 'Exercise ' + id,
                             body: 'and the tower law', mtime: at });
    const note = (id, at) => ({ id: id, kind: 'note', title: 'N' + id, body: 'aside',
                                mtime: at });
    const typed = (id, at, text) => ({ id: id, rev: 1, kind: 'text', answers: '0002',
                                       t: at, text: text });
    const frame = (cards, turns) => ({ data: JSON.stringify({
      state: { course: 'Speech-Lab', opened: '2026-09-17 19:55', session: 'lecture',
               aim: 'build', stance: 'do', stance_now: 'do', declared_stance: 'do' },
      cards: cards, turns: turns || [], messages: [], uploads: [], slate: [],
      agent: { agent: 'claude', state: 'listening' } }) });
    const under = () => {
      const p = writer.previousElementSibling;
      return (p && p.dataset && p.dataset.card) || '-';
    };
    let moves = 0;
    new window.MutationObserver((records) => {
      records.forEach((r) => {
        if (Array.prototype.indexOf.call(r.addedNodes, writer) !== -1) moves++;
      });
    }).observe(doc.getElementById('cards'), { childList: true });
    // Long enough for a card to type out and the surface to come down after it.
    const settle = () => sleep(3000);
    const es = window.__es;
    const Q = [q('0001', t0), q('0002', t0 + 60)];
    const one = [typed('t0010', t0 + 90, 'x')];
    const two = one.concat([typed('t0011', t0 + 130, 'y')]);

    es.onmessage(frame(Q));
    await settle();
    moves = 0;
    es.onmessage(frame(Q, one));
    await settle();
    es.onmessage(frame(Q.concat([note('0003', t0 + 120)]), one));
    await settle();
    check(moves > 0 && under() === '0003',
          'unfocused, an answer and its reply move the surface (' + moves
          + ' moves) to under the reply',
          'unfocused: ' + moves + ' moves, under ' + under());

    saybox.focus();
    moves = 0;
    es.onmessage(frame(Q.concat([note('0003', t0 + 120)]), two));
    await settle();
    es.onmessage(frame(Q.concat([note('0003', t0 + 120), note('0004', t0 + 140)]), two));
    await settle();
    check(moves === 0 && under() === '0004' && doc.activeElement === saybox
          && saybox.parentNode === sayrow,
          'focused, the same never moves the surface: the cards land above it, and the '
          + 'box keeps the focus',
          'focused: the surface moved ' + moves + ' times, is under ' + under()
          + ', focus on ' + doc.activeElement.id);
    // The move a blur makes, and a touch on a board moving it at once, are in
    // chain.js, which has earlier boards to go back to.
    saybox.blur();
  }

  console.log(errors.length ? errors.length + ' failed' : 'the answer box docks on the keys');
  process.exit(errors.length ? 1 : 0);
})();
