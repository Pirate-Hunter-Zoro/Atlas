// The answer box docks on the iPad keyboard.
//
// With the full keyboard up, the typed answer box was under the keys or
// scrolled away from them. While `#saybox` has the focus and the keys take more
// than 120px of the window, `#typebox` is fixed to the top of the keys and the
// lesson scrolls behind it; it can be made tall; and the textarea is never
// moved, because moving a focused element closes the keyboard.
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
  this.readyState = 1; this.close = function () {}; this.addEventListener = function () {};
};
window.addEventListener('error', (e) => fail('uncaught: ' + e.message));

// An iPad in portrait: the window is 1366 tall, and the keyboard is the visual
// viewport getting shorter than it.
const H = 1366;
Object.defineProperty(window, 'innerHeight', { value: H, configurable: true });
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
  window.dispatchEvent(new window.Event('orientationchange'));
  await sleep(10);
  check(typebox.style.width === '1366px' && typebox.style.top === '624px',
        'turning the iPad re-docks it on the new keys',
        'after turning the dock is ' + typebox.style.cssText);
  Object.defineProperty(window, 'innerHeight', { value: H, configurable: true });
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
          'and it is the system keyboard\'s textarea, with dictation and Scribble',
          'the answer box asks for a keyboard of its own');
  }

  console.log(errors.length ? errors.length + ' failed' : 'the answer box docks on the keys');
  process.exit(errors.length ? 1 : 0);
})();
