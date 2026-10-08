// The library page over artifacts: three groups, a status, and a delete that
// takes a second tap.
//
//   * Groups in the server's order -- made here, already here, materials --
//     each headed, once there is more than one.
//   * An artifact being written says so on its row.
//   * Only an artifact offers delete. The first tap arms it and sends nothing;
//     the second sends `POST /doc/delete {subject, id}`, an id and never a path.
//   * A material is read, not corrected: no "say what is wrong".

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

const LIBRARY = {
  workspace: 'courses/Topo', subject: 'courses/Topo', writeups: 'writeups',
  documents: [
    { id: 'compactness', group: 'artifact', dir: 'docs/compactness', stem: 'compactness',
      title: 'Compactness, explained', kind: 'paper', type: 'paper', formats: ['md'],
      rel: 'docs/compactness/compactness.md', pages: 0, pdf: false, stale: false,
      iso: '', notes: [], artifact: 'docs/compactness', status: 'writing', own: true },
    { id: 'notes-intro', group: 'legacy', dir: 'notes', stem: 'intro',
      title: 'An introduction', kind: 'paper', formats: ['md', 'pdf'],
      rel: 'notes/intro.pdf', pages: 2, pdf: true, stale: false, iso: '2026-10-01',
      notes: [] },
    { id: 'materials-reading', group: 'material', dir: 'materials', stem: 'reading',
      title: 'reading', kind: 'paper', formats: ['pdf'], rel: 'materials/reading.pdf',
      pages: 9, pdf: true, stale: false, iso: '2026-10-01', notes: [] },
  ],
};

const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'library.html'), 'utf8'), {
  runScripts: 'outside-only', pretendToBeVisual: true,
  url: 'https://board.test/library',
});
const { window } = dom;
const doc = window.document;
const sent = [];
window.fetch = (u, opts) => {
  const url = String(u);
  sent.push({ url: url, opts: opts || {} });
  if (/library\.json/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve(LIBRARY) });
  }
  if (/doc\/delete/.test(url)) {
    return Promise.resolve({ json: () => Promise.resolve({ ok: true }) });
  }
  return new Promise(() => {});
};
window.addEventListener('error', (e) => fail('uncaught: ' + e.message));
window.HTMLCanvasElement.prototype.getContext = () =>
  new Proxy({}, { get: () => () => {}, set: () => true });
window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
window.ResizeObserver = function () { this.observe = () => {}; this.disconnect = () => {}; };
try { window.localStorage.removeItem('library.flight'); } catch (e) {}

const HTML = fs.readFileSync(path.join(WEB, 'library.html'), 'utf8');
const SCRIPTS = (HTML.match(/src="\/static\/[\w.-]+"/g) || [])
  .map((m) => /static\/([\w.-]+)/.exec(m)[1])
  .filter((f) => f !== 'library.js' && f !== 'typeface.js');
for (const f of SCRIPTS) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
try { window.eval(fs.readFileSync(path.join(WEB, 'library.js'), 'utf8')); }
catch (e) { fail('library.js: ' + e.message); }

const tap = (el) => el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
const rowOf = (title) => Array.prototype.slice.call(doc.querySelectorAll('.lib-row'))
  .filter((r) => r.querySelector('.lib-name').textContent === title)[0];
const buttons = (row) => Array.prototype.map.call(
  row.querySelectorAll('.lib-acts button'), (b) => b.textContent);

(async function () {
  await sleep(30);
  const heads = Array.prototype.map.call(doc.querySelectorAll('.lib-group'),
                                         (h) => h.textContent).join('|');
  heads === 'Made here|Already here|Materials'
    ? ok('three groups, headed, in the server\'s order')
    : fail('group headings: ' + heads);

  const made = rowOf('Compactness, explained');
  const st = made && made.querySelector('.lib-status');
  st && st.textContent === 'being written'
    ? ok('an artifact being written says so on its row')
    : fail('no status on the artifact row');

  buttons(rowOf('An introduction')).indexOf('delete') < 0
    ? ok('a legacy document offers no delete')
    : fail('a legacy document offers delete');
  buttons(rowOf('reading')).indexOf('say what is wrong') < 0
    ? ok('a material is read, not corrected')
    : fail('a material offers "say what is wrong"');

  const del = made.querySelector('.lib-delete');
  if (!del) { fail('the artifact has no delete'); }
  else {
    sent.length = 0;
    tap(del);
    await sleep(5);
    !sent.some((r) => /doc\/delete/.test(r.url)) && /again/.test(del.textContent)
      ? ok('the first tap arms delete and sends nothing')
      : fail('the first tap sent: ' + sent.map((r) => r.url).join(' '));
    tap(del);
    await sleep(10);
    const post = sent.filter((r) => /doc\/delete/.test(r.url))[0];
    const body = post ? JSON.parse(post.opts.body) : {};
    post && post.opts.method === 'POST' && body.id === 'compactness'
      && body.subject === 'courses/Topo' && Object.keys(body).length === 2
      ? ok('the second tap posts /doc/delete with the subject and the id, no path')
      : fail('delete sent: ' + JSON.stringify(post));
    sent.some((r) => /library\.json/.test(r.url))
      ? ok('and the list is asked for again')
      : fail('the list was not reloaded after a delete');
  }

  if (errors.length) {
    console.log('\n' + errors.length + ' FAILED');
    process.exit(1);
  }
  console.log('\nall artifact page checks passed');
  process.exit(0);
})();
