// AN ANSWER THAT LANDED SOMEWHERE NOBODY WAS LOOKING.
//
// Asked for in these words:
//
//   "maybe something I give the agent to do or think about is going to take a
//    while. I want to be able to go into a different section of a project, or a
//    different fucking project completely, and put other agents to work on other
//    things while the first one is working. We should set up a notification
//    system where if a response that takes a while comes back in a session, I'll
//    get notified somewhere in the app and can click that notification to take me
//    back to that tutoring session."
//
// Three things have to be true for that to be worth having, and two of them are
// about restraint:
//
//   * IT HAS TO SAY SO. A turn that finishes in an empty room has to leave
//     something on the surface the person IS looking at.
//   * IT MUST NOT INTERRUPT. It is news about somewhere else. It goes in the
//     chrome, with everything else that is true and is not what they are doing --
//     never over the lesson, and never over the board they are writing on.
//   * THE ROW IS THE WAY BACK. "click that notification to take me back to that
//     tutoring session" -- so the row carries the workspace's address, and it
//     goes through the front door, which is the only thing that can move the one
//     https name from one board to another.
//
// Both surfaces carry it, and both are driven here: the board (the strip) and the
// front door (the row under the hero, and the badge on the card).

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

/* WHAT `/mission` COMES BACK WITH. A mission that has reported nothing is the
   case the panel exists for -- one had run five hours with no card, no file and
   no progress anywhere -- so this default says exactly that: no steps, no
   cards, no commits, and every fact the record holds on its own. */
let missionAnswer = {
  ok: true, id: 't0007', ws: 'research/PSYCH-ASR', repo: 'PSYCH-ASR',
  course: 'PSYCH-ASR', agent: 'colibri', state: 'running',
  task: 'grade the four typists', at: 0, elapsed: 5 * 3600 + 29 * 60,
  turns: 2, carries: 1, stalls: 0, working: true, host: 'compute301',
  left: 4 * 3600, budget: 12 * 3600, session: 'fc26', ship: true, shipped: 0,
  steps: [], cards: [], card_count: 0, commits: [], files: [], dirty: 0,
  withheld: 0, fenced: ['phi'],
};

/* ABOUT THE MISSION THAT WAS ASKED FOR. The panel is keyed on the id the tap
   named, so a stub answering about a different one would let a panel that
   re-keys itself off the payload pass -- which is exactly the fault that
   stopped a second tap closing it. */
function answerFor(u) {
  const m = /[?&]id=([^&]*)/.exec(String(u));
  const w = /[?&]ws=([^&]*)/.exec(String(u));
  return Object.assign({}, missionAnswer, {
    id: m ? decodeURIComponent(m[1]) : missionAnswer.id,
    ws: w ? decodeURIComponent(w[1]) : missionAnswer.ws,
  });
}

const t0 = Date.now() / 1000;

/* ------------------------------------------------------------- the board */
function boardDom() {
  const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'board.html'), 'utf8'), {
    runScripts: 'outside-only', pretendToBeVisual: true,
    url: 'https://board.test/board',
  });
  const { window } = dom;
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
  window.asked = [];
  window.fetch = (u, opts) => {
    window.asked.push({ url: String(u), how: (opts && opts.method) || 'GET' });
    if (/slate\/state/.test(String(u))) {
      return Promise.resolve({ json: () => Promise.resolve({ pages: [] }) });
    }
    /* The progress panel is a TAP, so the answer comes from here rather than
       from the payload. `missionAnswer` is what the server would say. */
    if (/^\/mission\?/.test(String(u))) {
      return Promise.resolve({ json: () => Promise.resolve(answerFor(u)) });
    }
    return new Promise(() => {});
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
                   'slate-core.js', 'annotate.js', 'address.js',
                   'mission.js', 'board.js']) {
    try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
    catch (e) { fail(f + ': ' + e.message); }
  }
  return window;
}

(async () => {

const window = boardDom();
const doc = window.document;
const es = window.__es;
if (!es) { console.log('FAIL board.js never opened a stream'); process.exit(1); }

const bar = () => doc.getElementById('newsbar');
/* Scoped to the list they are in, both of them: the strip carries two lists now
   -- answers that landed and missions still running -- and a mission row wears
   the answer row's own classes because it is the same row with a state on it. */
const rows = () => Array.from(doc.querySelectorAll('#news-list .news-row'));

const frame = (news, missions, papers) => JSON.stringify({
  state: { course: 'Galois Theory', session: 'lecture' },
  cards: [{ id: '0001', kind: 'lesson', title: '', body: 'A field is a ring.',
            mtime: t0 - 600 }],
  turns: [], agent: { agent: 'claude', state: 'listening', turns: 2 },
  waiting: null, history: 0, news: news || [], missions: missions || [],
  writeups: papers || null,
});

// Nothing elsewhere: nothing to say, and saying something anyway is furniture.
es.onmessage({ data: frame([]) });
await sleep(60);
bar().hidden
  ? ok('with nothing waiting anywhere else, there is no strip')
  : fail('the notification strip is up over no notifications');

// The lesson being read is marked as read, which is what keeps a workspace from
// notifying about its own cards the moment somebody switches away from it.
window.asked.some((r) => r.url === '/seen' && r.how === 'POST')
  ? ok('opening a board says, on the server, that somebody is looking at it')
  : fail('nothing told the server this workspace is being read');

// ...AND ONLY WHILE IT IS IN FRONT OF SOMEBODY. A board left open in a
// background tab that went on marking itself read would cancel its own
// notification, which is the one case this whole thing exists for.
{
  const src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
  /function markSeen\(force\) \{[\s\S]{0,600}?document\.hidden/.test(src)
    ? ok('and stops saying so the moment the tab goes behind something')
    : fail('a board in a background tab goes on marking itself read');
}

// --------------------------------------------- and then one comes back
const psych = { id: 'research/PSYCH-ASR', repo: 'PSYCH-ASR', family: 'research',
                course: 'PSYCH-ASR', chapter: 'cli', card: '0014',
                title: 'the four typists agree', when: t0 - 240 };
const trd = { id: 'research/TRD-EHR', repo: 'TRD-EHR', family: 'research',
              course: 'TRD-EHR', chapter: '', card: '0008',
              title: '', when: t0 - 30 };

es.onmessage({ data: frame([trd, psych]) });
await sleep(60);

!bar().hidden && rows().length === 2
  ? ok('two turns that finished elsewhere are two rows')
  : fail('the strip shows ' + rows().length + ' of 2 answers');
/PSYCH-ASR/.test(rows()[1].textContent)
  ? ok('each says which workspace answered')
  : fail('a row does not name its workspace: "' + rows()[1].textContent + '"');
/the four typists agree/.test(rows()[1].textContent)
  ? ok('and what the card is, when the card said')
  : fail('the row says nothing about the answer: "' + rows()[1].textContent + '"');
/wrote a card|TRD-EHR/.test(rows()[0].textContent)
  ? ok('and claims nothing when it did not')
  : fail('an untitled card invented a title: "' + rows()[0].textContent + '"');

// IT IS NOT OVER THE LESSON. Everything on this page that interrupts lives
// outside `#chrome`; this is inside it, which is where the things that are true
// and are not what you are doing belong.
{
  const html = fs.readFileSync(path.join(WEB, 'board.html'), 'utf8');
  /<div id="chrome">[\s\S]*id="newsbar"[\s\S]*<\/div><!-- \/#chrome -->/.test(html)
    ? ok('and it is in the chrome, under the bar, not over the lesson')
    : fail('the notification strip is somewhere it can cover the board');
}

// ------------------------------------------- and the row is the way back
//
// A LINK, spelled with the address grammar. "click that notification to take me
// back to that tutoring session" -- so the row goes to the front door carrying
// the workspace's address, which is the one thing that can move the single https
// name from this board to that one. Being a link rather than a handler is what
// makes it hold-to-open, readable, and testable as what it is.
{
  const at = rows()[1].getAttribute('href');
  at === '/#/w/research/PSYCH-ASR'
    ? ok('and the row IS the way back — the front door, carrying that '
         + "workspace's address")
    : fail('the row points at "' + at + '"');
  rows()[1].tagName === 'A'
    ? ok('and it is a link, so it can be held down, read and opened like one')
    : fail('the row is a ' + rows()[1].tagName + ', not a link');
}

// ------------------------------------------------- and it can be waved away
{
  doc.getElementById('news-hide').dispatchEvent(new window.Event('click'));
  bar().hidden
    ? ok('and it can be put away')
    : fail('the strip cannot be dismissed');
  es.onmessage({ data: frame([trd, psych]) });
  await sleep(60);
  bar().hidden
    ? ok('and stays away for the answers it was dismissed over')
    : fail('a dismissed notification came straight back');

  // But the NEXT answer in that workspace is a different answer.
  es.onmessage({ data: frame([Object.assign({}, psych, { when: t0 - 5,
                                                         title: 'and here is why' })]) });
  await sleep(60);
  !bar().hidden && /and here is why/.test((rows()[0] || {}).textContent || '')
    ? ok('and comes back for the next one, which is a different fact')
    : fail('dismissing one answer silenced the workspace');
}

/* ---------------------------------------- AND WHAT HAS NOT FINISHED YET
//
// "when I put colibri or anything on a mission, just because I close the iPad
//  doesn't mean that should end. Next time I open the iPad and access the board,
//  that mission should still be going or notify me somewhere if it's done."
//
// The rows above are turns that finished. A mission is one that has not, and the
// difference is what somebody does next: still going means leave it, done means
// go and read it, failed means send it again. So the row says which, and a
// failure says WHY -- "nothing is attached to that workspace any more" and "the
// allocation ended" are the same state word and two different next moves. */
{
  const jobs = () => Array.from(doc.querySelectorAll('.mission-row'));
  const mission = (over) => Object.assign({
    id: 't0007', ws: 'research/PSYCH-ASR', repo: 'PSYCH-ASR',
    course: 'PSYCH-ASR', agent: 'colibri', at: t0 - 7200, state: 'running',
    ship: true, reason: '', here: false, task: 'grade the four typists',
  }, over || {});

  es.onmessage({ data: frame([], [mission()]) });
  await sleep(60);
  !bar().hidden && jobs().length === 1
    ? ok('a mission set going before the lid closed is still on the strip')
    : fail('nothing says the mission is still running');
  /still going/.test(jobs()[0].textContent)
    ? ok('and says it has not finished, which is the state to leave alone')
    : fail('the row does not say what state it is in: "' + jobs()[0].textContent + '"');
  /grade the four typists/.test(jobs()[0].textContent)
    ? ok('and what it was put on, in the words it was asked in')
    : fail('the row does not say what the mission is');
  jobs()[0].getAttribute('href') === '/#/w/research/PSYCH-ASR'
    ? ok('and the row is the way back to it, like every other row here')
    : fail('the row points at "' + jobs()[0].getAttribute('href') + '"');
  /still going/.test(doc.getElementById('news-lead').textContent)
    ? ok('and the lead over the strip is about what is in it')
    : fail('the lead says "' + doc.getElementById('news-lead').textContent + '"');

  /* ------------------------------ AND WHAT IT HAS BEEN DOING
  //
  // "Whenever an agent is dispatched in some way, make it so that if I click on
  //  that box that says 'A Mission is still going' I can see what has been
  //  going on and been accomplished thus far."
  //
  // Three words are what somebody DOES about a mission; after the first hour
  // they are not what somebody wants to know. One had run five hours, taken a
  // pick-up, and put nothing anywhere -- because a doing turn's report lands at
  // the end and this model prefills for hours. So the row carries the last
  // thing the turn said it finished, and the whole of it is one tap further. */
  es.onmessage({ data: frame([], [mission({
    steps: 3, step: 'rebuilt the reference: 74 rows, 6 disagree' })]) });
  await sleep(60);
  /rebuilt the reference/.test(jobs()[0].textContent)
    ? ok('the row says the last thing the turn reported finishing, which is the '
         + 'one line that says the work is moving')
    : fail('the row gives a state and no progress: "' + jobs()[0].textContent + '"');
  /3 steps/.test(jobs()[0].textContent)
    ? ok('and offers the rest of the trail, saying how much of it there is')
    : fail('nothing on the row offers what else it has done');

  // A NEW STEP IS A NEW ROW. The list is rebuilt only when it has changed, and
  // keying that on the STATE alone would hold the first progress line for the
  // whole of a five-hour mission.
  es.onmessage({ data: frame([], [mission({
    steps: 4, step: 'scored it: 71 of 74 within 2s' })]) });
  await sleep(60);
  /71 of 74/.test(jobs()[0].textContent)
    ? ok('and the next step replaces it, because a row rebuilt only on a change '
         + 'of state would freeze the first line for five hours')
    : fail('the row still shows the previous step');

  // AND THE PANEL, WHICH IS THE OTHER HALF: everything the record knows about a
  // mission that has reported nothing at all.
  {
    const panel = () => doc.getElementById('mission-progress');
    const more = jobs()[0].querySelector('.mprog-more')
      || jobs()[0].appendChild(doc.createElement('span'));
    jobs()[0].querySelector('.mprog-more')
      ? ok('the tap that opens it is a control of its own, so the row itself is '
           + 'still the way back into that workspace')
      : fail('nothing on the row opens what it has done');
    more.dispatchEvent(new window.Event('click'));
    await sleep(60);
    window.asked.some((r) => /^\/mission\?ws=research%2FPSYCH-ASR&id=t0007$/.test(r.url))
      ? ok('and it asks the server for that one mission, by workspace and by id')
      : fail('nothing asked the server what the mission has done');
    const said = panel().textContent;
    !panel().hidden && /5h 29m in/.test(said)
      ? ok('and the panel says how long it has been going, which is true of a '
           + 'mission that has written nothing')
      : fail('the panel does not say how long: "' + said + '"');
    /turn 2 of it/.test(said) && /picked up once/.test(said)
      ? ok('and which turn it is on, and that a node went away under it')
      : fail('the panel says nothing about the turns: "' + said + '"');
    /a turn is running right now/.test(said) && /compute301/.test(said)
      ? ok('and whether a client is running right now, and on which node -- the '
           + 'two facts no card can answer')
      : fail('the panel cannot say whether anything is running');
    /4h left on that allocation/.test(said) && /12h of budget left/.test(said)
      ? ok('and how long that node has, against how much of the mission budget '
           + 'is left, which are two different clocks')
      : fail('the panel says nothing about either ceiling: "' + said + '"');
    /Nothing reported yet/.test(said)
      ? ok('and where the assistant has reported nothing it SAYS so, rather '
           + 'than showing a blank that reads as broken')
      : fail('a mission that has reported nothing draws an empty panel');

    // AND WHEN IT HAS REPORTED, the trail is there -- with the board's own
    // lines marked as the board's, because the machinery working must not read
    // as the assistant's report.
    missionAnswer = Object.assign({}, missionAnswer, {
      steps: [
        { at: t0 - 19000, who: 'board', said: 'dispatched to colibri from courses/Probability' },
        { at: t0 - 18000, who: 'board', said: 'a turn started on compute300' },
        { at: t0 - 9000, who: 'agent', said: 'rebuilt the reference: 74 rows, 6 disagree' },
        { at: t0 - 400, who: 'board', said: 'picked up where it stopped -- the node it was on went away (pick-up 1 of 6)' },
      ],
      cards: [{ id: '0057', at: t0 - 8000, title: 'the reference is rebuilt' }],
      card_count: 1,
      commits: [{ at: t0 - 7000, subject: 'Rebuild the reference transcript' }],
      files: ['psych_asr/repair.py'], dirty: 1, withheld: 2,
    });
    more.dispatchEvent(new window.Event('click'));   // shut it
    more.dispatchEvent(new window.Event('click'));   // and ask again
    await sleep(60);
    const told = panel().textContent;
    /rebuilt the reference: 74 rows/.test(told) && /picked up where it stopped/.test(told)
      ? ok('a mission that has reported shows what it reported, and the hop it '
           + 'crossed, in the order they happened')
      : fail('the trail is not on the panel: "' + told + '"');
    Array.from(panel().querySelectorAll('.mprog-step.machine')).length === 3
      ? ok("and the board's own lines are marked as the board's, because the "
           + "machinery working is not the assistant's report")
      : fail('nothing separates what the board wrote from what the turn said');
    /1 card/.test(told) && /1 commit/.test(told) && /1 file/.test(told)
      ? ok('and what it has MADE, which is the half of "accomplished" that no '
           + 'prompt can lie about')
      : fail('the panel does not say what landed: "' + told + '"');
    /the reference is rebuilt/.test(told) && /Rebuild the reference transcript/.test(told)
      ? ok('by name, so there is something to go and read')
      : fail('the panel counts without naming');
    /2 more under phi, not named here/.test(told)
      ? ok('and a path under the fence is COUNTED and never named, said out '
           + 'loud -- a name silently missing is one somebody scrolls for')
      : fail('the fence is either leaking names or hiding the count: "' + told + '"');

    // THE LEAD IS A TAP TOO, because that is the sentence the ask points at and
    // it is on this strip as well as on the front door.
    const lead = doc.getElementById('news-lead');
    window.MissionPanel.hide(panel());
    lead.classList.contains('mprog-lead') && typeof lead.onclick === 'function'
      ? ok('and the line that says a mission is still going is itself the tap, '
           + 'which is the sentence the ask names')
      : fail('"a mission is still going" cannot be tapped');
    lead.dispatchEvent(new window.Event('click'));
    await sleep(60);
    !panel().hidden && /rebuilt the reference/.test(panel().textContent)
      ? ok('and it opens the newest one')
      : fail('tapping the lead showed nothing');
    const shut = panel().querySelector('.mprog-close');
    if (shut) shut.dispatchEvent(new window.Event('click'));
    shut && panel().hidden
      ? ok('and it can be shut again without leaving the lesson')
      : fail('the panel cannot be closed');
    missionAnswer = Object.assign({}, missionAnswer, { steps: [] });
  }

  // A FAILURE IS A DIFFERENT NEXT MOVE, so it says which one.
  es.onmessage({ data: frame([], [mission({
    state: 'failed',
    reason: 'the allocation colibri runs in ended before the mission did' })]) });
  await sleep(60);
  jobs().length && /failed/.test(jobs()[0].textContent)
    ? ok('a mission that stopped without finishing says so')
    : fail('a failed mission reads as running');
  /allocation/.test(jobs()[0].textContent)
    ? ok('and says why, because two failures have two different answers')
    : fail('the row gives a state word and no reason');

  // A mission in the workspace already open is not a place to go.
  es.onmessage({ data: frame([], [mission({ here: true })]) });
  await sleep(60);
  jobs().length && jobs()[0].tagName !== 'A'
    ? ok('and one in the workspace already open does not pretend to be a link')
    : fail('a mission here offers a way to where somebody already is');

  // AND IT CAN BE PUT AWAY, but a state change is a new fact.
  es.onmessage({ data: frame([], [mission()]) });
  await sleep(60);
  doc.getElementById('news-hide').dispatchEvent(new window.Event('click'));
  es.onmessage({ data: frame([], [mission()]) });
  await sleep(60);
  bar().hidden
    ? ok('a mission can be waved away for as long as it stays as it was')
    : fail('a dismissed mission came straight back');
  es.onmessage({ data: frame([], [mission({ state: 'failed',
                                            reason: 'nothing is attached' })]) });
  await sleep(60);
  !bar().hidden && /failed/.test((jobs()[0] || {}).textContent || '')
    ? ok('and comes back the moment it ends, which is a different fact')
    : fail('waving away a running mission silenced its failure');
  doc.getElementById('news-hide').dispatchEvent(new window.Event('click'));
  await sleep(10);
}

/* ----------------------------------- a document asked for from THIS sitting

   The only row in this strip that is about the board in front of you. It is in
   the chrome for the same reason the rest of it is: the turn writing a deck must
   not push a proof off the glass, which is the whole design of `POST /writeup`.

   IT EXISTS BECAUSE THAT TURN IS TOLD TO WRITE NO CARD, so nothing about it can
   appear on the board itself and "I asked for a deck and nothing happened" had
   nowhere at all to be answered. */
{
  const papers = () => Array.from(doc.querySelectorAll('#writeup-list .mission-row'));
  const paper = (over) => Object.assign({
    id: 't0021', makes: 'slides', about: '', at: t0 - 90,
    agent: 'claude', state: 'writing', doc: '',
  }, over || {});

  es.onmessage({ data: frame([], [], [paper()]) });
  await sleep(60);
  !bar().hidden && papers().length === 1
    ? ok('a deck asked for mid-sitting says on the board that it is being written')
    : fail('nothing says the document is being written');
  /being written/.test((papers()[0] || {}).textContent || '')
    ? ok('and which of the three states it is in')
    : fail('the row does not say the document is in progress');
  /what this sitting has covered/.test((papers()[0] || {}).textContent || '')
    ? ok('and what it is about, which with nobody naming one is the evening')
    : fail('the row claims nothing about the scope: "'
           + (papers()[0] || {}).textContent + '"');
  papers()[0].tagName !== 'A'
    ? ok('and offers no way to read a document that is not written yet')
    : fail('a document being written pretends to be somewhere to go');

  // AND WHEN IT IS THERE. The library is where it went, so that is where the
  // row goes -- and going there is what retires it, which the SERVER remembers
  // because the fact is about the document rather than about this page.
  es.onmessage({ data: frame([], [], [paper({ state: 'done',
                                              doc: 'writeups-harness' })]) });
  await sleep(60);
  /in the library/.test((papers()[0] || {}).textContent || '')
    ? ok('and says when it is in the library')
    : fail('a finished document reads as still being written');
  papers()[0].tagName === 'A' && /\/library$/.test(papers()[0].getAttribute('href'))
    ? ok('and the row is the way to it')
    : fail('the finished row is not a link to the library');
  papers()[0].dispatchEvent(new window.Event('click'));
  await sleep(30);
  window.asked.some((r) => r.url === '/writeup/seen' && r.how === 'POST')
    ? ok('reading it tells the server, so a second device does not offer it again')
    : fail('nothing told the server the document had been looked at');

  // IT IS NOT WAVED AWAY WHILE IT IS STILL BEING WRITTEN. `✕` is a gesture
  // about news from elsewhere; this is work happening here, and it comes back.
  es.onmessage({ data: frame([], [], [paper()]) });
  await sleep(60);
  doc.getElementById('news-hide').dispatchEvent(new window.Event('click'));
  es.onmessage({ data: frame([], [], [paper()]) });
  await sleep(60);
  !bar().hidden && papers().length === 1
    ? ok('and a document still being written cannot be dismissed, because it is '
         + 'still being written')
    : fail('waving away news from elsewhere silenced work happening here');
}

/* --------------------------------------------------------- the front door */
{
  const dom = new JSDOM(fs.readFileSync(path.join(WEB, 'home.html'), 'utf8'), {
    runScripts: 'outside-only', pretendToBeVisual: true, url: 'https://board.test/',
  });
  const w = dom.window;
  const d = w.document;
  w.HTMLCanvasElement.prototype.getContext = () =>
    new Proxy({}, { get: () => () => {}, set: () => true });
  Object.defineProperty(w.HTMLElement.prototype, 'clientWidth', { get: () => 900 });
  Object.defineProperty(w.HTMLElement.prototype, 'clientHeight', { get: () => 600 });
  w.HTMLElement.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: 900, height: 600, right: 900, bottom: 600, x: 0, y: 0 };
  };
  w.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  w.scrollTo = function () {};
  w.asked = [];
  w.fetch = (u) => {
    w.asked.push(String(u));
    return /^\/mission\?/.test(String(u))
      ? Promise.resolve({ json: () => Promise.resolve(answerFor(u)) })
      : new Promise(() => {});
  };
  w.addEventListener('error', (e) => fail('home: uncaught: ' + e.message));
  // The front door draws no plane and measures no text any more -- six
  // families is a list of six -- so neither `gauge.js` nor `plane-core.js` is
  // loaded by it or by this.
  for (const f of ['typeface.js', 'address.js', 'recentre.js', 'mission.js',
                   'home.js']) {
    let src = fs.readFileSync(path.join(WEB, f), 'utf8');
    if (f === 'home.js') src = src.replace('})();', 'window.__atlas = paintAtlas;\n})();');
    try { w.eval(src); } catch (e) { fail('home: ' + f + ': ' + e.message); }
  }

  const payload = {
    families: [{ id: 'research', name: 'Research' }],
    workspaces: [
      { id: 'research/PSYCH-ASR', repo: 'PSYCH-ASR', family: 'research',
        family_name: 'Research', course: 'PSYCH-ASR', chapter: 'cli',
        root: '/x/research/PSYCH-ASR', current: false, cards: 14, open: 3,
        next: 'grade the pilot', kind: 'project', touched: t0 - 900,
        news: true, news_at: t0 - 240, news_title: 'the four typists agree' },
      { id: 'research/TRD-EHR', repo: 'TRD-EHR', family: 'research',
        family_name: 'Research', course: 'TRD-EHR', chapter: '',
        root: '/x/research/TRD-EHR', current: true, cards: 2, open: 1,
        next: 'the packet', kind: 'project', touched: t0 - 60,
        news: false, news_at: 0, news_title: '',
        // A MISSION IN THE WORKSPACE SOMEBODY IS IN IS STILL A MISSION. It was
        // set going hours ago and the board does not open by itself, so "still
        // going" about the box you are about to enter is the thing to know
        // before entering it -- which is where this panel parts company with
        // the answers above it.
        mission: { id: 't0009', state: 'running', agent: 'colibri',
                   task: 'decode the pilot session', at: t0 - 7200,
                   ship: true, reason: '',
                   // AND WHAT IT HAS DONE, on the card. "Still going" is the
                   // state to leave alone; this is the line that says the work
                   // is moving, and it is on the surface somebody comes back to.
                   steps: 3, step: 'rebuilt the reference: 74 rows' } },
    ],
  };
  w.__atlas(payload);
  await sleep(40);

  const mpanel = d.getElementById('missions');
  const mrows = Array.from(d.querySelectorAll('#missions-list .mission-row'));
  mpanel && !mpanel.hidden && mrows.length === 1
    ? ok('the front door says a mission is still going, which is what somebody '
         + 'coming back to the app is asking')
    : fail('the front door is silent about a mission in flight');
  mrows.length && /still going/.test(mrows[0].textContent)
               && /decode the pilot/.test(mrows[0].textContent)
    ? ok('and what it is, and that it has not finished')
    : fail('the mission row says nothing useful');
  mrows.length && /rebuilt the reference/.test(mrows[0].textContent)
    ? ok('and the last thing it reported finishing, because after the first '
         + 'hour "still going" is not something anybody can act on')
    : fail('the front-door row says nothing about progress');

  /* AND THE BOX ITSELF IS THE TAP, which is the ask in the owner's own words:
     "if I click on that box that says 'A Mission is still going' I can see what
      has been going on and been accomplished thus far."

     The rows under it stay the way BACK into the workspace -- one surface per
     next move -- so the disclosure is the lead and a control on each row. */
  {
    /* A control that is not there would take the rest of this block down with
       it, and a crash is a worse report than a failure: the point of these is
       to say WHICH of them broke. */
    const open = d.getElementById('missions-open')
      || d.body.appendChild(d.createElement('span'));
    const panel = d.getElementById('mission-progress')
      || d.body.appendChild(d.createElement('div'));
    open.tagName === 'BUTTON'
      ? ok('the line that says a mission is still going is a button, which is '
           + 'the thing the ask points at')
      : fail('"A mission is still going" cannot be clicked');
    /a mission is still going/i.test(open.textContent)
      ? ok('and it still says that, so the tap is on the sentence rather than '
           + 'beside it')
      : fail('the lead no longer says what it said: "' + open.textContent + '"');
    open.dispatchEvent(new w.Event('click'));
    await sleep(60);
    w.asked.some((u) => /^\/mission\?ws=research%2FTRD-EHR&id=t0009$/.test(u))
      ? ok('and it asks the server for that one mission, by workspace and by id')
      : fail('tapping the box asked the server nothing');
    !panel.hidden && /5h 29m in/.test(panel.textContent)
      ? ok('and what comes back is how long it has been going, which is true '
           + 'even of a mission that has written nothing at all')
      : fail('the panel says nothing: "' + panel.textContent + '"');
    /Nothing reported yet/.test(panel.textContent)
      ? ok('and says plainly that the assistant has reported nothing, rather '
           + 'than drawing a blank that reads as broken')
      : fail('a mission with no report draws an empty panel');
    // A SECOND TAP SHUTS IT. It is a disclosure on the front door, and the
    // front door is a page somebody is passing through.
    open.dispatchEvent(new w.Event('click'));
    await sleep(20);
    panel.hidden
      ? ok('and a second tap puts it away')
      : fail('the panel cannot be closed from the same control');
    // AND THE ROW ITSELF STILL OPENS THE WORKSPACE, which is what it was for.
    const chip = mrows[0].querySelector('.mprog-more');
    chip
      ? ok('while each row carries its own control, so a second mission is not '
           + 'behind the first')
      : fail('a row cannot open its own progress');
  }
  // ON THE CARD, WHICH IS ONE LEVEL DOWN. The front door is the FAMILIES now,
  // and the workspaces are behind whichever one you tap -- so the mark lives on
  // the card, and the count of what is waiting lives on the door above it. Both
  // halves matter: the door is what somebody coming back to the app sees first.
  const door = Array.from(d.querySelectorAll('#doors .door'))[0];
  door && /an answer waiting/.test(door.textContent)
       && /one still going/.test(door.textContent)
    ? ok('the door into the family says an answer is waiting and something is '
         + 'still going, before any of it is tapped')
    : fail('the door says nothing about what is waiting inside it');
  if (door) door.dispatchEvent(new w.Event('click'));
  await sleep(10);

  d.querySelector('.ws-dot.mission')
    ? ok('and the box it is running in is marked on the map of everything')
    : fail('nothing on the atlas marks the workspace with work in it');

  const panel = d.getElementById('answers');
  const list = Array.from(d.querySelectorAll('#answers-list .answer-row'));
  panel && !panel.hidden && list.length === 1
    ? ok('the front door says an answer came back while you were away')
    : fail('the front door is silent about a finished turn');
  list.length && /PSYCH-ASR/.test(list[0].textContent)
    ? ok('and which workspace it is in')
    : fail('the row does not name the workspace');
  list.length && /the four typists agree/.test(list[0].textContent)
    ? ok('and what it says')
    : fail('the row says nothing about the card');

  // And on the picture itself, because the atlas is what the front door IS.
  d.querySelector('.ws-dot.news')
    ? ok('and the workspace is badged on the map of everything')
    : fail('nothing on the atlas marks the workspace that answered');

  // NEVER ABOUT THE ONE YOU ARE IN. A badge on the card you are standing in is
  // furniture: the lesson is one tap away and you are about to read it anyway.
  d.querySelectorAll('.ws-dot.news').length === 1
    ? ok('and only that one — the workspace you are in is never badged')
    : fail('the current workspace was badged as unread');
}

console.log(errors.length ? '\n' + errors.length + ' FAILURES'
  : '\nwork that came back while you were elsewhere says so, and is one tap away');
process.exit(errors.length ? 1 : 0);

})();
