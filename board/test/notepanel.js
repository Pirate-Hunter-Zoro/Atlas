// The library's "say what is wrong" panel has to fit on the glass.
//
// Reported as: the markups on a deck were never sent, and "the
// WINDOW that shows up for me to send my markups of the presentation was not
// scrollable or workable". Eleven pages of ink made twenty-three requests, and
// the panel listing them was 1020px tall on an iPad whose landscape glass is
// 733: centred and fixed, it spilled off the top and the bottom alike, nothing
// scrolled to either end, the page under it was locked and the pinch is the
// board's. "send it" was below the screen, so nothing was ever sent.
//
// jsdom does no layout -- every element there is 0x0 -- which is how the
// library suite stayed green over a panel nobody could use. So this reads the
// sheet for the rules that keep the panel on the glass, and then, where a
// Chrome is installed, renders the real markup with the real sheets at iPad
// sizes and measures it. No Chrome, and that half says SKIP.

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const WEB = path.join(__dirname, '..', 'web');
const CSS = fs.readFileSync(path.join(WEB, 'library.css'), 'utf8');
const HTML = fs.readFileSync(path.join(WEB, 'library.html'), 'utf8');
const errors = [];
const ok = (m) => console.log('ok   ' + m);
const fail = (m) => { errors.push(m); console.log('FAIL ' + m); };

// The declarations of every top-level rule for one selector, comments and
// @media blocks left out (the same reading as `chrome.js`).
function block(selector) {
  const screen = CSS.replace(/\/\*[\s\S]*?\*\//g, '')
                    .replace(/@media[^{]*\{(?:[^{}]*\{[^{}]*\}\s*)*\}/g, '');
  const re = new RegExp('(^|[},])\\s*' + selector.replace(/[#.]/g, '\\$&')
                        + '\\s*\\{([^}]*)\\}', 'mg');
  let m, body = '';
  while ((m = re.exec(screen)) !== null) body += ';' + m[2];
  return body || null;
}

function decl(body, prop) {
  if (!body) return null;
  const m = new RegExp('(?:^|;|\\n)\\s*' + prop + '\\s*:\\s*([^;]+)', 'm').exec(body);
  return m ? m[1].trim() : null;
}

// ---- 1. THE SHEET ---------------------------------------------------------
const note = block('#note');
const box = block('#note-box');
const body = block('#note-body');

/auto|scroll/.test(decl(note, 'overflow-y') || '')
  ? ok('the panel itself scrolls, as the last resort on a glass smaller than its frame')
  : fail('#note has no overflow-y: content past the glass is unreachable');
decl(note, 'align-items') === null || /safe|start/.test(decl(note, 'align-items'))
  ? ok('a box taller than the panel is not centred off the top of it')
  : fail('#note centres its box (' + decl(note, 'align-items') + '): the top spills '
         + 'above the glass, where a fixed panel cannot scroll to');
/100%|vh|dvh|svh/.test(decl(box, 'max-height') || '')
  ? ok('the box is capped at the height of the panel')
  : fail('#note-box has no max-height: it grows with every request in the split');
decl(box, 'margin') === 'auto'
  ? ok('and centred by auto margins, which start a box that does not fit at the top')
  : fail('#note-box is not centred by margin: auto');
/auto|scroll/.test(decl(body, 'overflow-y') || '') && decl(body, 'min-height') === '0'
  ? ok('the middle of the panel scrolls, and is allowed to shrink to do it')
  : fail('#note-body does not scroll or cannot shrink: overflow-y '
         + decl(body, 'overflow-y') + ', min-height ' + decl(body, 'min-height'));

// ---- 2. THE MARKUP --------------------------------------------------------
// The answer and the buttons are OUTSIDE the scroller, after it: they never
// scroll away, and a refusal in red is on the glass when it arrives.
const panel = /<div id="note" hidden data-no-ink>[\s\S]*?\n<\/div>\n/.exec(HTML);
const P = panel ? panel[0] : '';
const bodyAt = P.indexOf('<div id="note-body">');
const items = P.indexOf('id="note-items"');
const said = P.indexOf('id="note-said"');
const acts = P.indexOf('id="note-acts"');
// The scroller's own closing tag: the first `</div>` at its indentation.
const bodyEnd = bodyAt >= 0 ? P.indexOf('\n    </div>', bodyAt) : -1;
bodyAt >= 0 && items > bodyAt && items < bodyEnd
  ? ok('the list of requests is inside the part that scrolls')
  : fail('#note-items is not inside #note-body');
said > bodyEnd && acts > said && bodyEnd > 0
  ? ok('the answer and the buttons follow it, outside it, so they never scroll away')
  : fail('#note-said / #note-acts are inside the scroller or above it');

// ---- 3. THE GLASS ---------------------------------------------------------
function findChrome() {
  const named = [process.env.CHROME,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium'];
  for (const c of named) if (c && fs.existsSync(c)) return c;
  for (const c of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
    const r = spawnSync('which', [c], { encoding: 'utf8' });
    if (r.status === 0 && r.stdout.trim()) return r.stdout.trim();
  }
  return null;
}

/* The page under test: the real sheets, in the order library.html loads them,
   the real panel markup, and twenty-five requests drawn by the real
   `Ledger.preview` -- eleven pages of ink, three of them offering a merge.
   What the measurement finds is written into the page and read back off
   Chrome's dump of the DOM. */
function page() {
  const href = (f) => 'file://' + path.join(WEB, f);
  const sheets = (HTML.match(/href="\/static\/[\w.-]+\.css"/g) || [])
    .map((m) => /static\/([\w.-]+)/.exec(m)[1])
    .map((f) => '<link rel="stylesheet" href="' + href(f) + '">').join('\n');
  const reqs = [];
  for (let i = 1; i <= 25; i++) {
    const pg = Math.ceil(i / 2.3);
    reqs.push({ id: 'R1.' + i, kind: 'ink', page: pg, together: pg % 3 === 0 ? 4 : 1 });
  }
  return '<!doctype html><html><head><meta charset="utf-8">'
    + '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
    + sheets + '</head><body class="reading">'
    + P.replace('<div id="note" hidden data-no-ink>', '<div id="note" data-no-ink>')
    + '<pre id="out"></pre>'
    + '<script src="' + href('ledger.js') + '"></script>'
    + '<script>(function () {\n'
    + 'var $ = function (id) { return document.getElementById(id); };\n'
    + '$("note-title").textContent = "Kestrel: a model that never leaves the building";\n'
    + '$("note-where").textContent = "docs/kestrel-pitch/kestrel-pitch.pdf";\n'
    + '$("note-page").hidden = false; $("note-page").textContent = "about page 11";\n'
    + 'window.Ledger.preview($("note-items"), ' + JSON.stringify(reqs) + ', [], function () {});\n'
    + '$("note-marks").hidden = false;\n'
    + '$("note-marks").textContent = "Your marks on 11 pages go with this. Send it with '
    + 'nothing typed and the ink is the feedback.";\n'
    + '$("note-said").hidden = false; $("note-said").className = "note-said bad";\n'
    + '$("note-said").textContent = "Not sent: the note is written but nothing could be '
    + 'asked. Your marks are still waiting; send it again.";\n'
    + '$("note-send").disabled = false;\n'
    + 'var r = function (id) { var b = $(id).getBoundingClientRect();\n'
    + '  return { top: b.top, bottom: b.bottom, left: b.left, right: b.right }; };\n'
    + 'var b = $("note-body");\n'
    + 'var out = { h: window.innerHeight, w: window.innerWidth,\n'
    + '  send: r("note-send"), cancel: r("note-cancel"), title: r("note-title"),\n'
    + '  said: r("note-said"), box: r("note-box"),\n'
    + '  scrollH: b.scrollHeight, clientH: b.clientHeight,\n'
    + '  overflowY: getComputedStyle(b).overflowY, lines: $("note-items").children.length };\n'
    + 'b.scrollTop = b.scrollHeight;\n'
    + 'var pre = $("note-items").querySelectorAll(".lg-pre");\n'
    + 'var last = pre[pre.length - 1].getBoundingClientRect();\n'
    + 'out.lastBottom = last.bottom; out.bodyBottom = b.getBoundingClientRect().bottom;\n'
    + 'out.sendAfter = r("note-send");\n'
    + '$("out").textContent = JSON.stringify(out);\n'
    + '})();</script></body></html>';
}

function measure(chrome, file, w, h) {
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'notepanel-chrome-'));
  try {
    const r = spawnSync(chrome, ['--headless=new', '--disable-gpu', '--no-first-run',
      '--no-default-browser-check', '--allow-file-access-from-files',
      '--hide-scrollbars', '--user-data-dir=' + prof, '--window-size=' + w + ',' + h,
      '--virtual-time-budget=3000', '--dump-dom', 'file://' + file],
      { encoding: 'utf8', timeout: 60000 });
    const m = /<pre id="out">([^<]*)<\/pre>/.exec(r.stdout || '');
    if (!m || !m[1]) return { error: (r.error && r.error.message) || (r.stderr || '').slice(-400) };
    return JSON.parse(m[1].replace(/&quot;/g, '"').replace(/&amp;/g, '&'));
  } finally {
    fs.rmSync(prof, { recursive: true, force: true });
  }
}

const chrome = findChrome();
if (!chrome) {
  console.log('skip  no Chrome here -- the panel is not measured on a rendered page');
} else if (!P) {
  fail('the #note panel could not be read out of library.html');
} else {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'notepanel-'));
  const file = path.join(dir, 'note.html');
  fs.writeFileSync(file, page());
  /* An iPad Air in landscape and portrait, and landscape with the keyboard up
     (the glass that is left above it). */
  const glasses = [['landscape', 1180, 820], ['portrait', 820, 1180],
                   ['landscape with the keyboard up', 1180, 430]];
  try {
    for (const [name, w, h] of glasses) {
      const m = measure(chrome, file, w, h);
      if (m.error) { fail(name + ': Chrome did not render the panel: ' + m.error); continue; }
      const on = (b) => b.top >= 0 && b.bottom <= m.h + 0.5 && b.left >= 0 && b.right <= m.w + 0.5;
      m.lines === 26
        ? ok(name + ': the panel carries the 25 requests it is measured with')
        : fail(name + ': ' + m.lines + ' lines in the split');
      on(m.send) && on(m.cancel)
        ? ok(name + ': "send it" and "cancel" are on the glass ('
             + Math.round(m.send.bottom) + ' of ' + m.h + 'px)')
        : fail(name + ': "send it" is at ' + JSON.stringify(m.send) + ' on a glass '
               + m.w + 'x' + m.h + ', the box at ' + JSON.stringify(m.box));
      on(m.title) && on(m.said)
        ? ok(name + ': and so are the title and the answer under the list')
        : fail(name + ': title at ' + JSON.stringify(m.title) + ', answer at '
               + JSON.stringify(m.said));
      m.overflowY === 'auto' && m.scrollH > m.clientH
        ? ok(name + ': the list scrolls (' + m.scrollH + 'px in ' + m.clientH + ')')
        : (m.scrollH <= m.clientH
          ? ok(name + ': the whole list fits without scrolling')
          : fail(name + ': the list overflows and does not scroll: ' + m.overflowY));
      m.lastBottom <= m.bodyBottom + 1
        && Math.abs(m.sendAfter.top - m.send.top) < 0.5
        ? ok(name + ': scrolled to the end, the last request is in view and the buttons '
             + 'have not moved')
        : fail(name + ': the last request ends at ' + m.lastBottom + ' below the list\'s '
               + m.bodyBottom + ', send moved ' + m.send.top + ' -> ' + m.sendAfter.top);
    }
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                          : '\nthe note panel fits the glass, and its buttons stay on it');
process.exit(errors.length ? 1 : 0);
