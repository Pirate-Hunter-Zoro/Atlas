// WHO WRITES IT, THIS SITTING — and what the local model's server is doing.
//
// The ask, in the owner's words: "start colibri on a specified project from the
// iPad, in any old tutoring session or any old project or course map, at any
// time."
//
// Four layers resolved which assistant tutors a course and a tablet could reach
// none of them: a flag on a command line, a line in the workspace's own
// `tutorboard.json` that is a statement about it for ever, a hostname, and a
// machine default. The sitting is the fifth, and this is the control for it.
//
// It is held rather than sent, which is the decision rather than the shortcut.
// The aim beside it changes in place because it changes what the next card is;
// an assistant changes WHO WRITES IT, and the conversation the outgoing one was
// holding does not transfer — on the local model that is a 15,900-token preamble
// re-paid at a few tokens a second, in hours. So it travels with the next
// sitting.
//
// And the server it needs has four states that no button can express: nothing
// submitted, queued behind an allocation, loading 429 GB off the filer, warm.
//
// jsdom, because every assertion is what a person can read and tap.

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
  return { left: 0, top: 0, width: 900, height: 120, right: 900, bottom: 120, x: 0, y: 0 };
};
window.Element.prototype.scrollIntoView = function () {};
window.Element.prototype.setPointerCapture = function () {};
window.Element.prototype.releasePointerCapture = function () {};

const posted = [];
let elsewhereAnswer = null;
window.fetch = (u, opt) => {
  posted.push({ url: String(u), body: opt && opt.body ? JSON.parse(opt.body) : null });
  if (/slate\/state/.test(String(u))) {
    return Promise.resolve({ json: () => Promise.resolve({ pages: [] }) });
  }
  if (/\/atlas\.json$/.test(String(u))) {
    return Promise.resolve({ json: () => Promise.resolve({ workspaces: [
      { repo: 'PSYCH-ASR', id: 'research/PSYCH-ASR', family_name: 'Research',
        course: 'PSYCH-ASR', chapter: 'cli', current: true },
      { repo: 'TRD-EHR', id: 'research/TRD-EHR', family_name: 'Research',
        course: 'TRD-EHR', chapter: 'the grid', current: false,
        fenced: ['phi'] },
      { repo: 'Galois-Theory', id: 'courses/Galois-Theory', family_name: 'Courses',
        course: 'Galois Theory', chapter: 'Ch 04', current: false, fenced: [] },
    ] }) });
  }
  if (/\/elsewhere$/.test(String(u))) {
    return Promise.resolve({ json: () => Promise.resolve(
      elsewhereAnswer || { ok: true, repo: 'TRD-EHR', turn: 't0007' }) });
  }
  if (/\/colibri$/.test(String(u))) {
    return Promise.resolve({ json: () => Promise.resolve({
      ok: true, started: true,
      detail: 'starting the server — seven or eight minutes',
      colibri: { state: 'queued', job: '4231', node: '', detail: 'Resources' },
    }) });
  }
  return Promise.resolve({ json: () => Promise.resolve({ ok: true }) });
};
window.renderMathInElement = () => {};
window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
window.scrollTo = function () {};
window.addEventListener('error', (e) => fail('uncaught: ' + e.message));
window.EventSource = function () {
  window.__es = this;
  this.readyState = 1;
  this.close = function () {};
  this.addEventListener = function () {};
};

for (const f of ['typeface.js', 'macros.js', 'gauge.js', 'plane-core.js',
                 'slate-core.js', 'annotate.js', 'board.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
const es = window.__es;
if (!es) { console.log('FAIL board.js never opened a stream'); process.exit(1); }

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const t0 = Date.now() / 1000 - 600;

const HOSTED = { name: 'claude', cmd: 'claude', missing: null, headless: true,
                 exclusive: null, private: null };
const LOCAL = { name: 'colibri', cmd: 'coli-code', missing: null, headless: true,
                exclusive: 'the server runs one KV slot, so a second sitting '
                         + 'evicts the first one\'s prefix',
                private: 'it is the only assistant allowed to read `phi`' };
const ABSENT = { name: 'cursor', cmd: 'cursor-agent', missing: 'cursor-agent',
                 headless: false, exclusive: null, private: null };

const frame = (extra) => JSON.stringify(Object.assign({
  state: { course: 'PSYCH-ASR', session: 'lecture', chapter: 'cli',
           aim: 'build', declared_stance: 'teach' },
  cards: [{ id: '0001', kind: 'lesson', title: 'opening',
            html: '<p>Here.</p>', mtime: t0 }],
  turns: [], history: 0,
  agent: { agent: 'claude', state: 'listening' },
}, extra || {}));

const row = () => doc.getElementById('kind-who');
const ways = () => Array.prototype.map.call(
  doc.getElementById('kind-who-ways').querySelectorAll('button'),
  (b) => b.textContent);
const chosen = () => {
  const b = doc.getElementById('kind-who-ways').querySelector('button.on');
  return b ? b.textContent : '';
};
const note = () => doc.getElementById('kind-who-note').textContent;
const fence = () => doc.getElementById('kind-who-fence').textContent;
const start = () => doc.getElementById('kind-who-up');
const open = () => { doc.getElementById('session').click(); };
const sessionOf = () => {
  for (let i = posted.length - 1; i >= 0; i--) {
    if (/\/session$/.test(posted[i].url)) return posted[i].body;
  }
  return null;
};

(async () => {

// ------------------------------------------- nothing to choose is no chooser
es.onmessage({ data: frame({ assistants: { default: 'claude', agents: [HOSTED, ABSENT] },
                             colibri: { state: 'off', detail: 'no server is running' } }) });
await sleep(60);
open();
await sleep(40);
row().hidden
  ? ok('one assistant is not a choice, so the row is not drawn')
  : fail('a chooser offering one name is furniture');

// A machine that could not say is not a machine with nothing: `assistants` is
// null there, and the two must not be confused.
es.onmessage({ data: frame({ assistants: null, colibri: null }) });
await sleep(60);
open();
await sleep(40);
row().hidden
  ? ok('and a machine that could not say what it has draws nothing either')
  : fail('the chooser is drawn over an answer nobody gave');

// ------------------------------------------------------- two, and a default
es.onmessage({ data: frame({
  assistants: { default: 'claude', agents: [HOSTED, LOCAL, ABSENT] },
  colibri: { state: 'off', detail: 'no server is running' } }) });
await sleep(60);
open();
await sleep(40);
!row().hidden
  ? ok('two of them is a choice, and it is on the glass')
  : fail('the chooser is hidden with two assistants installed');
ways().join(',') === 'claude,colibri'
  ? ok('an assistant this machine has not got is not offered: ' + ways().join(','))
  : fail('the row offers: ' + ways().join(','));
chosen() === 'claude'
  ? ok('and it opens showing the one actually in force')
  : fail('the chooser shows "' + chosen() + '" over a sitting running claude');

// The sitting's own answer, which is the fifth layer and the whole point.
es.onmessage({ data: frame({
  state: { course: 'PSYCH-ASR', session: 'lecture', aim: 'build',
           declared_stance: 'teach', agent: 'colibri' },
  assistants: { default: 'claude', agents: [HOSTED, LOCAL] },
  colibri: { state: 'warm', job: '4231', node: 'compute304',
             detail: 'warm on compute304' } }) });
await sleep(60);
open();
await sleep(40);
chosen() === 'colibri'
  ? ok('a sitting that named one shows it, rather than the machine default')
  : fail('the sitting\'s own assistant is not shown: "' + chosen() + '"');
/warm on compute304/.test(note())
  ? ok('and the local model says where its server is: "' + note() + '"')
  : fail('nothing says what the server is doing: "' + note() + '"');
start().hidden
  ? ok('with a warm server there is nothing to start')
  : fail('a warm server is still offering to be started');

// ------------------------------------------------ the four states, in words
const withServer = async (colibri) => {
  es.onmessage({ data: frame({
    state: { course: 'PSYCH-ASR', session: 'lecture', agent: 'colibri' },
    assistants: { default: 'claude', agents: [HOSTED, LOCAL] },
    colibri: colibri }) });
  await sleep(60);
  open();
  await sleep(40);
};

await withServer({ state: 'off', detail: 'no server is running' });
/no server is running/.test(note()) && !start().hidden
  ? ok('nothing running says so, and offers to start one')
  : fail('"' + note() + '" / start hidden: ' + start().hidden);
/seven or eight minutes/.test(note())
  ? ok('and says what starting one costs before the tap, not after')
  : fail('the cost of a start is not stated: "' + note() + '"');
/before you stop for the day/.test(note())
  ? ok('and says the one thing that makes it worth doing now')
  : fail('"' + note() + '"');

await withServer({ state: 'queued', job: '4231', detail: 'Resources' });
/queued/.test(note()) && /Resources/.test(note())
  ? ok('a queued job says so, in Slurm\'s own reason: "' + note() + '"')
  : fail('"' + note() + '"');
start().hidden
  ? ok('and the control does not offer to submit a second')
  : fail('a queued job is being offered a second submission');

await withServer({ state: 'loading', job: '4231', node: 'compute304',
                   detail: 'reading 429 GB off the filer' });
/coming up/.test(note()) && /429 GB/.test(note())
  ? ok('a job that is running but not ready is loading, not warm')
  : fail('"' + note() + '"');
start().hidden
  ? ok('and is not offered a start either')
  : fail('a loading server is being offered a start');

// And the tap returns at once with the state, because an allocation, a 429 GB
// load and a warm-up generation cannot be reported by the request that asked.
await withServer({ state: 'off', detail: 'no server is running' });
start().click();
await sleep(60);
posted.some((p) => /\/colibri$/.test(p.url))
  ? ok('the tap asks the board to start one')
  : fail('nothing was sent');
// The state that comes back with the receipt is strictly better than the
// receipt: a job number and Slurm's own reason beat "submitting".
/queued/.test(note()) && /Resources/.test(note()) && start().hidden
  ? ok('and what comes straight back is the state, not a promise: "' + note() + '"')
  : fail('"' + note() + '" / start hidden: ' + start().hidden);

// ----------------------------------------- held, and sent with the sitting
es.onmessage({ data: frame({
  assistants: { default: 'claude', agents: [HOSTED, LOCAL] },
  colibri: { state: 'warm', detail: 'warm on compute304' } }) });
await sleep(60);
open();
await sleep(40);
doc.getElementById('kind-who-ways').querySelectorAll('button')[1].click();
await sleep(40);
chosen() === 'colibri'
  ? ok('a tap is shown at once, before anything is sent')
  : fail('the tap did not land: "' + chosen() + '"');
posted.filter((p) => /\/session$/.test(p.url)).length === 0
  ? ok('and NOTHING is sent, because an assistant is chosen as a sitting OPENS '
       + '— the conversation the old one held does not transfer')
  : fail('the tap changed the sitting that is open');

doc.getElementById('kind-lecture').click();
await sleep(40);
(sessionOf() || {}).agent === 'colibri'
  ? ok('opening the sitting is what carries it')
  : fail('the sitting was opened without it: ' + JSON.stringify(sessionOf()));

// And it does not survive the sitting it was chosen for: leaving it set would
// make the next tap on `lecture` silently carry a choice made an hour ago for
// something else. Same rule as a stance.
doc.getElementById('session').click();
await sleep(40);
doc.getElementById('kind-lecture').click();
await sleep(40);
(sessionOf() || {}).agent === null
  ? ok('and the next sitting starts from the repository again')
  : fail('the pick outlived its sitting: ' + JSON.stringify(sessionOf()));

// ------------------------------ and whether this box holds something fenced
//
// "if I'm in PSYCH-ASR on the iPad, we should know that there is a phi folder
// that I can't let claude or any outsourced AI model see."
//
// The fence was real and per-PATH: every walk refused a fenced directory, and
// nothing anywhere said that a WORKSPACE had one. So this row offered `claude`
// beside `colibri` in a box holding session content exactly as it does in a box
// holding a textbook, and the only thing between the tap and a hosted model
// reaching for that content was a hook the person cannot see.
//
// Visibility and a default, NOT a refusal. The fence stops a hosted assistant
// READING `phi` rather than stops it existing — the teaching thread on this very
// code is a hosted conversation and works.
es.onmessage({ data: frame({
  assistants: { default: 'claude', agents: [HOSTED, LOCAL] },
  colibri: { state: 'warm', detail: 'warm on compute304' },
  fenced: ['phi'] }) });
await sleep(60);
open();
await sleep(40);
/phi\//.test(fence())
  ? ok('a fenced workspace says so, and names the directory rather than a flag: "'
       + fence() + '"')
  : fail('nothing on the row says this box holds a fence: "' + fence() + '"');
/only by colibri/.test(fence())
  ? ok('and names the one assistant that may read it, out of the registry')
  : fail('"' + fence() + '"');
/claude will not be able to open phi\//.test(fence())
  ? ok('and the hosted pick in force carries what it will not be able to open')
  : fail('a hosted pick says nothing about the fence: "' + fence() + '"');
ways().join(',') === 'claude,colibri'
  ? ok('while both are still offered — the fence stops a hosted assistant '
       + 'READING phi, not existing')
  : fail('a fence removed a choice: ' + ways().join(','));

doc.getElementById('kind-who-ways').querySelectorAll('button')[1].click();
await sleep(40);
!/will not be able to open/.test(fence()) && /only by colibri/.test(fence())
  ? ok('and picking the one that may read it drops the warning, keeping the fence')
  : fail('"' + fence() + '"');

// A machine that has not GOT the one that may read it is the honest half of the
// same sentence: there is nothing to choose, and the row is drawn anyway to say
// why. A chooser that vanishes here would be a fence nobody is told about.
const ABSENT_LOCAL = Object.assign({}, LOCAL, { missing: 'coli-code' });
es.onmessage({ data: frame({
  assistants: { default: 'claude', agents: [HOSTED, ABSENT_LOCAL] },
  colibri: null, fenced: ['phi'] }) });
await sleep(60);
open();
await sleep(40);
!row().hidden && /colibri, which is not installed here/.test(fence())
  ? ok('with the reader not installed the row is still drawn, because the '
       + 'absence of a choice is the thing worth saying: "' + fence() + '"')
  : fail('row hidden: ' + row().hidden + ' / "' + fence() + '"');
ways().length === 0
  ? ok('and one name is still not a choice, so no buttons are drawn under it')
  : fail('a chooser offering one name is furniture: ' + ways().join(','));

// And a box with no fence says nothing at all. A warning on every workspace is
// a warning nobody reads.
es.onmessage({ data: frame({
  assistants: { default: 'claude', agents: [HOSTED, LOCAL] },
  colibri: { state: 'warm', detail: 'warm on compute304' }, fenced: [] }) });
await sleep(60);
open();
await sleep(40);
doc.getElementById('kind-who-fence').hidden && fence() === ''
  ? ok('and a workspace holding no fence is not warned about one')
  : fail('an unfenced workspace carries a fence line: "' + fence() + '"');

// ------------------------------------- not in the two sittings that only read
es.onmessage({ data: frame({
  state: { course: 'PSYCH-ASR', session: 'walk' },
  walk: { units: [{ name: 'a.py', label: 'a.py' }], scope: ['a.py'] },
  assistants: { default: 'claude', agents: [HOSTED, LOCAL] },
  colibri: { state: 'warm', detail: 'warm on compute304' } }) });
await sleep(60);
open();
await sleep(40);
row().hidden
  ? ok('a walkthrough is not offered one, the same as it is offered no stance')
  : fail('the chooser is up over a sitting that only reads');

// ------------------------- and the same choice, aimed at another workspace
//
// "I want to be able to go into a different section of a project, or a different
// fucking project completely, and put other agents to work on other things
// while the first one is working."
es.onmessage({ data: frame({
  assistants: { default: 'claude', agents: [HOSTED, LOCAL] },
  colibri: { state: 'warm', detail: 'warm on compute304' } }) });
await sleep(60);
doc.getElementById('btn-work-elsewhere').click();
await sleep(80);

const panel = doc.getElementById('elsewhere');
const rows = () => Array.prototype.map.call(
  doc.getElementById('elsewhere-list').querySelectorAll('button'),
  (b) => b.textContent);
const go = () => doc.getElementById('elsewhere-go');
const said = () => doc.getElementById('elsewhere-said').textContent;
const elsewhereOf = () => {
  for (let i = posted.length - 1; i >= 0; i--) {
    if (/\/elsewhere$/.test(posted[i].url)) return posted[i].body;
  }
  return null;
};

!panel.hidden
  ? ok('the control opens without leaving the lesson')
  : fail('the panel did not open');
rows().length === 2
  ? ok('it lists every workspace this machine has, found by walking rather '
       + 'than by a registry: ' + rows().join(' / '))
  : fail('the list is: ' + rows().join(' / '));
rows().join(' ').indexOf('PSYCH-ASR') === -1
  ? ok('and not the one you are already looking at')
  : fail('the board you are on is offered as somewhere else');
go().disabled
  ? ok('with nothing picked and nothing to do, there is nothing to start')
  : fail('the control is live with no workspace and no task');

doc.getElementById('elsewhere-list').querySelectorAll('button')[0].click();
await sleep(40);
go().disabled
  ? ok('a workspace on its own is not a job')
  : fail('a workspace with no task is being offered a start');

const task = doc.getElementById('elsewhere-task');
task.value = 'reproduce the corrected transcript';
task.dispatchEvent(new window.Event('input'));
await sleep(40);
!go().disabled
  ? ok('a workspace and a task is a job')
  : fail('the control is still dead with both');

// And who, which is the same registry the sitting chooser reads.
const whoBtns = () => Array.prototype.map.call(
  doc.getElementById('elsewhere-who').querySelectorAll('button'),
  (b) => b.textContent);
const whoOn = () => {
  const b = doc.getElementById('elsewhere-who').querySelector('button.on');
  return b ? b.textContent : '';
};
const elsewhereFence = () =>
  doc.getElementById('elsewhere-fence').textContent;
whoBtns().join(',') === 'whatever is there,claude,colibri'
  ? ok('who is offered, with the honest default first: ' + whoBtns().join(','))
  : fail('the who row offers: ' + whoBtns().join(','));

// A MISSION GOES INTO A BOX NOBODY IS LOOKING AT, so there is no second chance
// to notice what is in it. TRD-EHR holds a fence here, and that changes which
// assistant is already chosen when nobody says otherwise.
rows()[0].indexOf('fenced') !== -1
  ? ok('a workspace holding a fence is marked on the row you pick it from')
  : fail('the list says nothing: ' + rows()[0]);
whoOn() === 'colibri'
  ? ok('and aiming at it defaults to the one assistant that may read it, '
       + 'rather than to whatever is listening')
  : fail('the default over a fenced workspace is "' + whoOn() + '"');
/only by colibri/.test(elsewhereFence())
  ? ok('with the reason under it: "' + elsewhereFence() + '"')
  : fail('the panel says nothing about the fence: "' + elsewhereFence() + '"');

// Still a default and not a refusal: the others are on the row, a tap is
// remembered as a tap, and it carries what that pick will not be able to open.
doc.getElementById('elsewhere-who').querySelectorAll('button')[1].click();
await sleep(40);
whoOn() === 'claude' && /claude will not be able to open phi\//.test(elsewhereFence())
  ? ok('a hosted pick is honoured and says what it will not open: "'
       + elsewhereFence() + '"')
  : fail('"' + whoOn() + '" / "' + elsewhereFence() + '"');

// And an unfenced workspace is not warned about somebody else's fence.
doc.getElementById('elsewhere-list').querySelectorAll('button')[1].click();
await sleep(40);
doc.getElementById('elsewhere-fence').hidden
  ? ok('while the box next to it, holding none, is told nothing')
  : fail('an unfenced workspace carries a fence line: "' + elsewhereFence() + '"');

doc.getElementById('elsewhere-list').querySelectorAll('button')[0].click();
await sleep(40);
doc.getElementById('elsewhere-who').querySelectorAll('button')[2].click();
await sleep(40);
go().click();
await sleep(60);
JSON.stringify(elsewhereOf()) === JSON.stringify({ repo: 'TRD-EHR',
    agent: 'colibri', ship: false, task: 'reproduce the corrected transcript' })
  ? ok('and the job goes out naming the workspace, the assistant and the task')
  : fail('what went out was ' + JSON.stringify(elsewhereOf()));
panel.hidden && task.value === ''
  ? ok('then it closes, and you are back where you were')
  : fail('the panel stayed open over a job that went');

/* ---------------------------------------- and whether it ships itself
//
// "when I put anything on a mission, I should have the option to tell it to
//  ship its changes once it is done - I don't know if colibri is capable of
//  doing that, but the tutor certainly should be once colibri is done."
//
// One switch, and a sentence under it saying who actually pushes: never the
// assistant that did the work. "Ship it" otherwise reads as "and nobody looks
// at it", and the opposite is the whole design. */
{
  const ship = () => doc.getElementById('elsewhere-ship');
  const shipNote = () => doc.getElementById('elsewhere-ship-note');
  doc.getElementById('btn-work-elsewhere').click();
  await sleep(80);
  !ship().checked
    ? ok('the panel opens with the ship switch off, every time')
    : fail('a mission was about to be pushed because a box was still ticked');
  shipNote().hidden
    ? ok('and says nothing about pushing until it is asked to')
    : fail('the ship note is up over a switch nobody set');

  doc.getElementById('elsewhere-list').querySelectorAll('button')[0].click();
  await sleep(40);
  ship().checked = true;
  ship().dispatchEvent(new window.Event('change'));
  await sleep(40);
  !shipNote().hidden && /ordinary tutor/.test(shipNote().textContent)
    ? ok('ticked, it says who pushes — the workspace\'s own tutor')
    : fail('the switch says nothing about who pushes: "' + shipNote().textContent + '"');
  /not colibri|could not read/.test(shipNote().textContent)
    ? ok('and that it is not the assistant that did the work: "'
         + shipNote().textContent + '"')
    : fail('the note does not say whose work is being checked: "'
           + shipNote().textContent + '"');

  task.value = 'repair the diarization on the pilot';
  task.dispatchEvent(new window.Event('input'));
  await sleep(40);
  go().click();
  await sleep(60);
  (elsewhereOf() || {}).ship === true
    ? ok('and the switch goes out with the mission, because the record is '
         + 'written once and read when it finishes')
    : fail('the ship switch never reached the server: '
           + JSON.stringify(elsewhereOf()));

  // A DECISION ABOUT THIS MISSION, not a setting. The next one starts off.
  doc.getElementById('btn-work-elsewhere').click();
  await sleep(80);
  !ship().checked
    ? ok('and the next mission starts with it off again')
    : fail('the ship switch was still ticked for the next mission');
  doc.getElementById('elsewhere-close').click();
  await sleep(20);
}

// A REFUSAL IS AN ANSWER AND IT GOES ON THE GLASS. One colibri sitting at a
// time, machine-wide: a second tap would evict the first one's KV prefix and
// cost it its whole preamble again, in hours.
elsewhereAnswer = { ok: false,
  error: "'colibri' is already working in PSYCH-ASR, and it runs one sitting "
       + 'at a time on this machine' };
doc.getElementById('btn-work-elsewhere').click();
await sleep(80);
doc.getElementById('elsewhere-list').querySelectorAll('button')[0].click();
task.value = 'and another one';
task.dispatchEvent(new window.Event('input'));
await sleep(40);
go().click();
await sleep(60);
/already working in PSYCH-ASR/.test(said())
  ? ok('a refusal is read on the glass, naming the workspace holding it')
  : fail('the refusal went nowhere: "' + said() + '"');
doc.getElementById('elsewhere-said').classList.contains('bad') && !panel.hidden
  ? ok('and it is painted as a refusal, with the panel still open to act on it')
  : fail('a refusal was painted as a success');

console.log(errors.length ? '\n' + errors.length + ' FAILURES'
  : '\nwho writes this sitting is a choice, and the server says which of four states it is in');
process.exit(errors.length ? 1 : 0);

})();
