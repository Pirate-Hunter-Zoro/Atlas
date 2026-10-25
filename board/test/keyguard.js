// Fingers type, the Pencil draws.
//
// On the iPad a text field the Apple Pencil touches belongs to Scribble, whose
// palette opens the small floating keyboard; once it has, every later tap gets
// it too. keyguard.js keeps every text field readonly while it does not have
// the focus, so Scribble never sees one, and a finger takes the lock off as it
// lands so the tap gets the full keyboard. The Pencil on a field is refused, and
// the Pencil anywhere takes the focus off a field that has it.
//
// jsdom has no touch hardware: a touch device is `maxTouchPoints` faked to 5,
// and a touch is an event carrying the `changedTouches` Safari would send, the
// Pencil's with `touchType: 'stylus'`. The real board page is loaded for its
// fields, `#saybox` to guard and `#code-cmd` to leave alone.
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
const SRC = fs.readFileSync(path.join(WEB, 'keyguard.js'), 'utf8');
const errors = [];
const ok = (m) => console.log('ok   ' + m);
const fail = (m) => { errors.push(m); console.log('FAIL ' + m); };
const check = (cond, good, bad) => (cond ? ok(good) : fail(bad));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const EXTRA = '<div id="ink" style="height:200px"></div>'
  + '<label id="lab" for="name">name</label><input id="name">'
  + '<input id="find" type="search"><input id="tick" type="checkbox">'
  + '<input id="mine" type="text" readonly>';

function page(touchPoints) {
  const html = fs.readFileSync(path.join(WEB, 'board.html'), 'utf8')
    .replace(/<script[\s\S]*?<\/script>/g, '')
    .replace('</body>', EXTRA + '</body>');
  const dom = new JSDOM(html, { runScripts: 'outside-only', url: 'https://board.test/board' });
  const { window } = dom;
  if (touchPoints) {
    Object.defineProperty(window.navigator, 'maxTouchPoints', { value: touchPoints });
  }
  window.addEventListener('error', (e) => fail('uncaught: ' + e.message));
  // What the document-level listeners were registered as: a non-passive one
  // there makes every finger on the page wait for the page before it scrolls.
  const docListeners = [];
  const add = window.document.addEventListener;
  window.document.addEventListener = function (type, fn, opts) {
    docListeners.push({ type: type, opts: opts });
    return add.call(this, type, fn, opts);
  };
  window.__docListeners = docListeners;
  try { window.eval(SRC); } catch (e) { fail('keyguard.js: ' + e.message); }
  return { window, doc: window.document };
}

// A touch as Safari sends it: `changedTouches` with the Pencil's `touchType`,
// and `touches` emptied on the way up.
// `at` places it, and `also` is touches already on the glass (the nib, for a
// palm).
function touch(w, el, type, kind, at, also) {
  const ev = new w.Event(type, { bubbles: true, cancelable: true });
  const t = { touchType: kind === 'pen' ? 'stylus' : 'direct', target: el,
              clientX: at ? at[0] : undefined, clientY: at ? at[1] : undefined };
  Object.defineProperty(ev, 'changedTouches', { value: [t] });
  Object.defineProperty(ev, 'touches',
                        { value: type === 'touchstart' ? [t].concat(also || []) : (also || []) });
  el.dispatchEvent(ev);
  return ev;
}

function pointer(w, el, type, pointerType, id) {
  const ev = new w.Event(type, { bubbles: true, cancelable: true });
  Object.defineProperty(ev, 'pointerType', { value: pointerType });
  Object.defineProperty(ev, 'pointerId', { value: id || 1 });
  el.dispatchEvent(ev);
  return ev;
}

const locked = (el) => el.hasAttribute('readonly');

(async () => {
  // ------------------------------------------------- a touch device, at load
  const { window: w, doc } = page(5);
  const say = doc.getElementById('saybox');
  const name = doc.getElementById('name');
  const ink = doc.getElementById('ink');
  const KG = w.KeyGuard;

  check(KG && KG.on === true, 'on a touch device KeyGuard is on',
        'KeyGuard is ' + (KG ? 'off' : 'missing') + ' on a touch device');
  check(locked(say) && say.hasAttribute('data-keyguard')
        && locked(doc.getElementById('find')) && locked(name),
        'every text field is readonly while it does not have the focus, #saybox included',
        'a text field was left open: saybox ' + locked(say) + ', name ' + locked(name));
  const cmd = doc.getElementById('code-cmd');
  const mine = doc.getElementById('mine');
  check(locked(cmd) && !cmd.hasAttribute('data-keyguard')
        && locked(mine) && !mine.hasAttribute('data-keyguard'),
        'a field readonly in its markup (#code-cmd) is not taken over',
        '#code-cmd or a readonly field was taken over');
  check(!locked(doc.getElementById('tick')) && !locked(doc.getElementById('file')),
        'a checkbox and a file picker are not text fields, and are left alone',
        'a checkbox or a file picker was locked');

  // ------------------------------------------- a finger tap gets the keyboard
  touch(w, say, 'touchstart', 'finger');
  check(!locked(say), 'a finger landing on the box unlocks it before the tap focuses it',
        'after a finger touchstart the box is still readonly');
  say.focus();
  touch(w, say, 'touchend', 'finger');
  check(doc.activeElement === say && !locked(say),
        'the tap focuses it unlocked: the full keyboard, not none',
        'after the tap: focus on ' + doc.activeElement.id + ', locked ' + locked(say));
  await sleep(700);
  check(!locked(say), 'and it stays unlocked while it has the focus',
        'the focused box was locked again after the finger lifted');

  // ---------------------------------------------------- focusout re-locks it
  say.blur();
  check(locked(say), 'losing the focus locks it again', 'a blurred box stayed open');

  // ------------------------------------------- a finger scroll locks it again
  touch(w, name, 'touchstart', 'finger');
  check(!locked(name), 'a finger starting a scroll on a field unlocks it too',
        'the finger did not unlock the field');
  touch(w, name, 'touchend', 'finger');
  await sleep(700);
  check(locked(name) && doc.activeElement !== name,
        'and with no focus once it lifted, it is locked again shortly after',
        'a field scrolled over was left open');

  // ------------------------------------------- the Pencil on a field: nothing
  {
    const ev = touch(w, say, 'touchstart', 'pen');
    check(ev.defaultPrevented && locked(say) && doc.activeElement !== say,
          'the Pencil on the box is refused: default prevented, locked, not focused',
          'the Pencil on the box: prevented ' + ev.defaultPrevented + ', locked '
          + locked(say) + ', focus on ' + doc.activeElement.id);
    touch(w, say, 'touchend', 'pen');
    const lab = touch(w, doc.getElementById('lab'), 'touchstart', 'pen');
    check(lab.defaultPrevented && locked(name),
          'and on a label for a field, the same', 'the Pencil on a label was let through');
    const p = pointer(w, say, 'pointerdown', 'pen');
    check(p.defaultPrevented && locked(say),
          'a pen pointerdown on the box is refused the same way',
          'a pen pointerdown on the box was let through');
    pointer(w, say, 'pointerup', 'pen');
  }

  // ------------------------- the document never holds a finger's scroll up
  check(w.__docListeners.filter((l) => /^(touchstart|pointerdown)$/.test(l.type))
          .every((l) => l.opts && l.opts.passive === true),
        'the document\'s own touchstart and pointerdown are passive: only a field\'s '
        + 'rectangle waits on the page',
        'a document-level touchstart or pointerdown is not passive');

  // ------------------------------- the helper refuses after a Pencil contact
  check(KG.contact() === 'pen' && KG.focus(say) === false
        && doc.activeElement !== say && locked(say),
        'after the Pencil, KeyGuard.focus does not focus the box (no Scribble keyboard)',
        'after the Pencil the helper focused the box: ' + doc.activeElement.id);

  // ----------------------- a focus that arrives locked after the Pencil goes
  say.focus();
  check(doc.activeElement !== say && locked(say),
        'a page path focusing the box straight after the Pencil is turned away',
        'a plain focus() after the Pencil kept the box focused');

  // --------------------------------------- the helper focuses after a finger
  touch(w, ink, 'touchstart', 'finger');
  touch(w, ink, 'touchend', 'finger');
  check(KG.contact() === 'touch' && KG.focus(say) === true
        && doc.activeElement === say && !locked(say),
        'after a finger, KeyGuard.focus unlocks the box and focuses it',
        'after a finger the helper left focus on ' + doc.activeElement.id
        + ', locked ' + locked(say));

  // ------------------- the Pencil anywhere takes the focus off the box
  {
    const ev = touch(w, ink, 'touchstart', 'pen');
    check(!ev.defaultPrevented && doc.activeElement !== say && locked(say),
          'the Pencil down off the box while it is focused blurs and locks it, and '
          + 'the stroke itself is left to the ink',
          'the Pencil off the box: prevented ' + ev.defaultPrevented + ', focus on '
          + doc.activeElement.id + ', locked ' + locked(say));
    touch(w, ink, 'touchend', 'pen');
  }
  KG.focus(say);   // refused: the Pencil was last
  pointer(w, ink, 'pointerdown', 'touch');
  KG.focus(say);
  check(doc.activeElement === say, 'a finger pointerdown lets the helper focus again',
        'after a finger pointerdown the helper left focus on ' + doc.activeElement.id);
  const pen = pointer(w, ink, 'pointerdown', 'pen');
  check(!pen.defaultPrevented && doc.activeElement !== say && locked(say),
        'and a pen pointerdown off the box does the same',
        'a pen pointerdown off the box left focus on ' + doc.activeElement.id);
  pointer(w, ink, 'pointerup', 'pen');

  // ---------------------------------------------- a palm is not a finger
  {
    const nib = { touchType: 'stylus', target: ink };
    touch(w, name, 'touchstart', 'finger', null, [nib]);
    check(locked(name) && KG.contact() === 'pen',
          'a palm landing on a field while the nib is down leaves it locked',
          'a palm unlocked the field under it (locked ' + locked(name) + ', contact '
          + KG.contact() + ')');
    touch(w, name, 'touchend', 'finger', null, [nib]);
    pointer(w, ink, 'pointerdown', 'pen', 7);
    pointer(w, name, 'pointerdown', 'touch', 8);
    check(locked(name) && KG.contact() === 'pen' && KG.focus(say) === false,
          'and so does a touch pointer while a pen pointer is down, and the helper '
          + 'still refuses',
          'a touch pointer under a down pen counted as a finger');
    pointer(w, ink, 'pointerup', 'pen', 7);
    pointer(w, ink, 'pointerdown', 'touch', 9);
    check(KG.contact() === 'touch', 'once the pen lifts, a touch is a finger again',
          'after the pen lifted, a touch still counted as the pen');
  }

  // ------------------------------------- a near miss is aimed at the field
  {
    name.getBoundingClientRect = () => ({ left: 100, top: 100, right: 300, bottom: 130,
                                          width: 200, height: 30 });
    touch(w, ink, 'touchstart', 'finger', [150, 400]);
    check(locked(name), 'a finger far from a field leaves it locked',
          'a finger 270px away unlocked the field');
    touch(w, ink, 'touchend', 'finger');
    touch(w, ink, 'touchstart', 'finger', [150, 155]);
    check(!locked(name),
          'a finger just outside a field unlocks it, since WebKit gives the tap to it',
          'a near miss left the field locked, so the tap would focus it with no keyboard');
    touch(w, ink, 'touchend', 'finger');
    await sleep(700);
    check(locked(name), 'and locks it again when nothing took the focus',
          'the near field stayed open after the finger lifted');
  }

  // --------------------- the keyboard's arrows move between open fields
  {
    touch(w, say, 'touchstart', 'finger');
    say.focus();
    touch(w, say, 'touchend', 'finger');
    let lockedAsFocused = null;
    name.addEventListener('focus', () => { lockedAsFocused = locked(name); }, { once: true });
    name.focus();
    check(lockedAsFocused === false && doc.activeElement === name,
          'with one field focused the others are open, so the next arrow lands on one '
          + 'unlocked',
          'the next field was locked (' + lockedAsFocused + ') as the focus landed');
    await sleep(700);
    check(!locked(say) && !locked(name), 'and they stay open while one has the focus',
          'the settle locked a field while another had the focus');
    name.blur();
    check(locked(say) && locked(name), 'and the focus leaving them all locks them all',
          'a field stayed open after the focus left');
  }

  // ------------------------------- a hardware keyboard's Tab gets in
  doc.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Tab', bubbles: true }));
  say.focus();
  check(doc.activeElement === say && !locked(say),
        'a focus that lands locked from a Tab unlocks it, so a hardware keyboard types',
        'after a Tab: focus on ' + doc.activeElement.id + ', locked ' + locked(say));
  say.blur();

  // ------------------------------ a trackpad on the iPad is a finger
  pointer(w, name, 'pointerdown', 'mouse');
  check(!locked(name) && KG.contact() === 'mouse',
        'a trackpad press on a field unlocks it like a finger',
        'a trackpad press left the field locked');
  pointer(w, name, 'pointerup', 'mouse');
  await sleep(700);
  check(locked(name), 'and with no focus after it, locks it again',
        'the field stayed open after a trackpad press that focused nothing');

  // ---------------------------------------------- fields that arrive later
  {
    const later = doc.createElement('textarea');
    doc.body.appendChild(later);
    const wrap = doc.createElement('div');
    wrap.innerHTML = '<input class="lg-reason" type="text">';
    doc.body.appendChild(wrap);
    // problem.js's copy box: readonly before it reaches the page.
    const copy = doc.createElement('textarea');
    copy.setAttribute('readonly', '');
    doc.body.appendChild(copy);
    await sleep(0);
    const inner = wrap.querySelector('input');
    check(locked(later) && later.hasAttribute('data-keyguard')
          && locked(inner) && inner.hasAttribute('data-keyguard'),
          'a field added later, alone or inside new markup, is guarded too',
          'a later field was left open: ' + locked(later) + ', ' + locked(inner));
    touch(w, copy, 'touchstart', 'finger');
    check(locked(copy) && !copy.hasAttribute('data-keyguard'),
          'and one readonly before it arrived stays readonly under a finger',
          'problem.js\'s readonly copy box was unlocked');
    touch(w, copy, 'touchend', 'finger');
  }
  w.close();

  // --------------------------------------------------- no touch: untouched
  {
    const { window: m, doc: md } = page(0);
    const box = md.getElementById('saybox');
    check(m.KeyGuard && m.KeyGuard.on === false && !locked(box)
          && !box.hasAttribute('data-keyguard') && !locked(md.getElementById('name')),
          'with no touch (a Mac) no field is locked',
          'on a device with no touch a field was locked');
    touch(m, box, 'touchstart', 'pen');
    check(m.KeyGuard.focus(box) === true && md.activeElement === box,
          'and KeyGuard.focus is a plain focus there',
          'with no touch the helper did not focus');
    m.close();
  }

  // --------------------------------------------------- loaded on every page
  for (const f of ['board.html', 'home.html', 'library.html', 'slate.html']) {
    const html = fs.readFileSync(path.join(WEB, f), 'utf8');
    const srcs = [];
    html.replace(/<script src="\/static\/([^"]+)"/g, (_, s) => srcs.push(s));
    const at = srcs.indexOf('keyguard.js');
    const firstPage = srcs.findIndex((s) => /^(board|home|library|ledger|slate|annotate|slate-core)\.js$/.test(s));
    check(at >= 0 && at < firstPage, f + ' loads keyguard.js before its page scripts',
          f + ' does not load keyguard.js before its page scripts');
  }
  check(/"\/static\/keyguard\.js"/.test(fs.readFileSync(path.join(WEB, 'sw.js'), 'utf8')),
        'and the service worker caches it with the shell',
        'keyguard.js is not in sw.js SHELL');

  // ------------------------------- every page focus goes through the helper
  // A plain focus() on the iPad lands on a field that is still locked, and a
  // field locked as the focus lands gets no keyboard. The one plain focus left
  // in each page is its helper's fallback for when keyguard.js did not load,
  // and the viewer's close button is not a text field.
  {
    const stray = [];
    for (const f of fs.readdirSync(WEB).filter((n) => /\.js$/.test(n) && n !== 'keyguard.js'
                                                  && n !== 'sw.js')) {
      const lines = fs.readFileSync(path.join(WEB, f), 'utf8').split('\n');
      lines.forEach((line, i) => {
        if (!/\.focus\(/.test(line) || /KeyGuard\.focus\(/.test(line)) return;
        const fallback = /^\s*el\.focus\(\);\s*$/.test(line)
          && /window\.KeyGuard\.focus\(el\)/.test(lines[i - 1] || '');
        if (!fallback && !/#viewer-close/.test(line)) stray.push(f + ':' + (i + 1));
      });
    }
    check(stray.length === 0, 'no page script focuses a field except through KeyGuard',
          'a plain focus() outside the helper: ' + stray.join(', '));
  }

  console.log(errors.length ? errors.length + ' failed' : 'fingers type, the Pencil draws');
  process.exit(errors.length ? 1 : 0);
})();
