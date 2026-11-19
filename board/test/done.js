// THE DONE TAB: one tap says the step the tutor set is finished.
//
// A course whose work is code ("add the method, run the test, push it") asks for
// an answer that is not a sentence and is not ink. The composer had write, type
// and speak, and none of them is "I did it", so saying so meant typing the word
// "Done" -- which is what the Go-Algorithms session did three times, and which
// the tutor cannot tell apart from an answer that happens to be that word.
//
// So the fourth choice is a signal, not a surface: it sends the fixed completion
// payload the server and the tutor already share, it never picks up an unsent
// draft, and it leaves the box alone. jsdom, because every assertion here is
// about what is on the glass and what went out on the wire.

const fs = require('fs');
const path = require('path');

let JSDOM;
try { ({ JSDOM } = require('jsdom')); }
catch (e) {
  console.log('skip  jsdom is not installed — `npm install jsdom` to run this test');
  process.exit(0);
}

const WEB = path.join(__dirname, '..', 'web');
const errors = [];
const ok = (m) => console.log('ok   ' + m);
const fail = (m) => { errors.push(m); console.log('FAIL ' + m); };
const check = (cond, good, bad) => cond ? ok(good) : fail(bad);

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

// Every request the page makes, so the send can be read back out of it.
const posted = [];
window.fetch = (u, opt) => {
  posted.push({ url: String(u), body: opt && opt.body ? JSON.parse(opt.body) : null });
  if (/slate\/state/.test(String(u))) {
    return Promise.resolve({ json: () => Promise.resolve({ pages: [] }) });
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

for (const f of ['typeface.js', 'macros.js', 'plane-core.js',
                 'ink-core.js', 'slate-core.js', 'annotate.js', 'board.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
const es = window.__es;
if (!es) { console.log('FAIL board.js never opened a stream'); process.exit(1); }

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const t0 = Date.now() / 1000 - 3600;

const question = { id: '0001', kind: 'question', title: 'Dynamic array append',
                   body: 'Make append amortised constant time, then run the test',
                   mtime: t0 };

const frame = (cards, turns) => JSON.stringify({
  state: { course: 'Go Algorithms', session: 'lecture' },
  cards: cards, turns: turns || [],
  agent: { agent: 'deepseek', state: 'listening' },
});

const lastSay = () => {
  for (let i = posted.length - 1; i >= 0; i--) {
    if (/\/say$/.test(posted[i].url)) return posted[i].body;
  }
  return null;
};
const sayCount = () => posted.filter((p) => /\/say$/.test(p.url)).length;

(async () => {

// ------------------------------------------------------- the fourth choice
es.onmessage({ data: frame([question]) });
for (let i = 0; i < 80 && doc.getElementById('writer').hidden; i++) await sleep(50);

const tabs = doc.querySelector('#writer-head .tabs');
const ids = ['tab-write', 'tab-type', 'tab-speak', 'tab-done'];
const present = ids.every((id) => {
  const el = doc.getElementById(id);
  return el && tabs && el.closest('#writer-head .tabs') === tabs;
});
check(present,
      'the composer offers four choices in one row: write, type, speak and done',
      'the done tab is missing from #writer-head .tabs: '
      + ids.map((id) => id + '=' + !!doc.getElementById(id)).join(' '));

const done = doc.getElementById('tab-done');
const slate = doc.getElementById('slate');
const typebox = doc.getElementById('typebox');
check(done && /done/i.test(done.textContent),
      'and it is labelled done, so a tap needs no explanation',
      'the done tab is not labelled done: ' + (done && done.textContent));

// It is an action, not a surface: pressing it must not swap the half of the
// panel that is showing, or it would send and then hide what it sent from.
const beforeSlate = slate.hidden, beforeType = typebox.hidden;
done.click();
await sleep(60);
check(slate.hidden === beforeSlate && typebox.hidden === beforeType && !done.classList.contains('on'),
      'and pressing it is not a tab: the half that was showing stays showing',
      'pressing done switched the panel like a tab');

// ------------------------------------------------- what actually went out
const sentDone = lastSay();
check(sentDone && sentDone.signal === 'done',
      'one tap sends the completion signal the server already accepts',
      'the tap sent no done signal: ' + JSON.stringify(sentDone));
check(sentDone && sentDone.text === '',
      'with a fixed, empty text -- the signal is the whole message',
      'the done tap carried text: ' + JSON.stringify(sentDone && sentDone.text));
check(sentDone && sentDone.answers === '0001',
      'and it answers the question that is open',
      'the done tap did not name the open question: ' + JSON.stringify(sentDone));
check(sentDone && sentDone.turn === null,
      'as a new turn, not a revision of the last typed answer',
      'the done tap revised an earlier answer: ' + JSON.stringify(sentDone));
check(sentDone && Object.keys(sentDone).sort().join(',') === 'answers,signal,text,turn',
      'nothing else rides along on it',
      'the done payload has fields the route does not expect: ' + JSON.stringify(sentDone));

// An unsent sentence in the box is not the message. It is also not thrown away:
// Done answers the question, it does not discard a draft the person was writing.
const saybox = doc.getElementById('saybox');
saybox.value = 'wait, the capacity is still wrong';
saybox.dispatchEvent(new window.Event('input'));
const beforeDraft = sayCount();
done.click();
await sleep(60);
const sentWithDraft = lastSay();
check(sayCount() === beforeDraft + 1,
      'a tap sends exactly one turn',
      'a tap sent ' + (sayCount() - beforeDraft) + ' turns');
check(sentWithDraft && sentWithDraft.text === '',
      'and still sends no text, so an unsent answer is never filed as done',
      'the draft rode along with the done tap: ' + JSON.stringify(sentWithDraft));
check(saybox.value === 'wait, the capacity is still wrong',
      'while the draft stays in the box for the person to keep writing',
      'the done tap emptied or changed the typed draft: "' + saybox.value + '"');
check(!done.disabled,
      'and the button is usable again once the send is away',
      'the done button stayed disabled after its send');

// ------------------------------------------- the three surfaces still work
doc.getElementById('tab-type').click();
check(!typebox.hidden && slate.hidden,
      'type still opens the typed half alone',
      'the type tab no longer opens the typed half');
saybox.value = 'append is amortised constant time now';
saybox.dispatchEvent(new window.Event('input'));
doc.getElementById('send-type').click();
await sleep(60);
const sentType = lastSay();
check(sentType && sentType.text === 'append is amortised constant time now'
      && sentType.signal === null && sentType.answers === '0001',
      'and send still posts the typed answer with no signal, as before',
      'the typed send changed shape: ' + JSON.stringify(sentType));

doc.getElementById('tab-write').click();
check(!slate.hidden && typebox.hidden,
      'write still opens the slate and shuts the typed half',
      'the write tab no longer opens the slate alone');
doc.getElementById('tab-speak').click();
check(doc.getElementById('tab-speak').classList.contains('on')
      && !doc.getElementById('tab-write').classList.contains('on'),
      'and speak is still the third surface, reading as the tab in use',
      'the speak tab no longer takes the panel\'s state');
doc.getElementById('tab-type').click();

// ------------------------------------ and with nothing owed, a tap says nothing
// A correct card arrives after the question, so the panel retires. The button
// is off the glass, but the handler checks too: a signal is a turn, and a turn
// must answer something.
es.onmessage({ data: frame([question,
  { id: '0002', kind: 'correct', body: 'that is the whole of it', mtime: t0 + 100 }]) });
for (let i = 0; i < 80 && !doc.getElementById('writer').hidden; i++) await sleep(50);
const quiet = sayCount();
done.click();
await sleep(60);
check(doc.getElementById('writer').hidden,
      'a correct reply retires the whole composer, done included',
      'the composer stayed open after the question was marked right');
check(sayCount() === quiet,
      'and nothing is sent when no question is open',
      'a done tap sent a turn with no question to answer');

console.log(errors.length
  ? errors.length + ' FAILURES'
  : 'done is one tap, and the other three still send what they always did');
process.exit(errors.length ? 1 : 0);
})();
