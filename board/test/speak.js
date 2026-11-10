// Every session speaks, listens and shows what it heard.
//
// The real board in a real DOM, with the microphone, MediaRecorder,
// AudioContext and the audio element stubbed: the third answer tab and its
// box; getUserMedia asked for only on the record tap, and every track stopped
// when the take ends; audio/mp4 chosen where it can be made, else WebM/Opus;
// the take posted to /speech/say with the question it answers, and the heard
// block; a card's speak button posting /speech/card and playing what it
// answers, fetched whole into a Blob; and a `say` phrase drawn and played.
// Nothing plays unasked.
//
// jsdom is a development-only dependency; without it this test skips.

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
const check = (cond, good, bad) => (cond ? ok(good) : fail(bad));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const HTML = fs.readFileSync(path.join(WEB, 'board.html'), 'utf8');
const SW = fs.readFileSync(path.join(WEB, 'sw.js'), 'utf8');

// ---- the page's own wiring ------------------------------------------------
const at = (s) => HTML.indexOf(s);
check(at('src="/static/speak.js"') > 0 && at('src="/static/speak.js"') < at('src="/static/board.js"'),
      'speak.js loads before board.js', 'speak.js does not load before board.js');
check(/"\/static\/speak\.js"/.test(SW), 'and it is in the service worker\'s shell',
      'speak.js is not in sw.js SHELL');
check(at('id="speak-auto"') < 0 && at('id="speak-target"') < 0,
      'there is no auto-speak toggle and no target phrase box',
      'the removed language-drill controls are still in the page');

// ---- the page, with every audio API stubbed --------------------------------
const dom = new JSDOM(HTML, {
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
  return { left: 0, top: 0, width: 900, height: 500, right: 900, bottom: 500, x: 0, y: 0 };
};
window.Element.prototype.scrollIntoView = function () {};
window.EventSource = function () { return { close() {}, readyState: 1, addEventListener() {} }; };
window.renderMathInElement = () => {};
window.requestAnimationFrame = (fn) => setTimeout(fn, 5);
window.cancelAnimationFrame = (id) => clearTimeout(id);
window.scrollTo = () => {};
window.addEventListener('error', (e) => fail('uncaught: ' + e.message));

// What was fetched, and what the server says.
const fetched = [];
let heardReply = null;
window.fetch = (u, init) => {
  const url = String(u);
  fetched.push({ url, init: init || {} });
  if (/slate\/state/.test(url)) {
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ pages: [] }) });
  }
  if (/\/speech\/card$/.test(url)) {
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(
      { ok: true, sha: 'c'.repeat(32), url: '/speech/' + 'c'.repeat(32) + '.m4a' }) });
  }
  if (/\/speech\/say$/.test(url)) {
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(heardReply) });
  }
  if (/\/speech\/[0-9a-f]{32}\.m4a$/.test(url)) {
    return Promise.resolve({ ok: true, status: 200,
                             blob: () => Promise.resolve(new window.Blob(['m4a'], { type: 'audio/mp4' })) });
  }
  return new Promise(() => {});
};
const posts = (re) => fetched.filter((f) => re.test(f.url) && f.init.method === 'POST');
const gets = (re) => fetched.filter((f) => re.test(f.url) && !f.init.method);

// The audio element: what it was asked to play.
const plays = [];
window.HTMLMediaElement.prototype.play = function () {
  plays.push(this.src);
  setTimeout(() => this.dispatchEvent(new window.Event('ended')), 2);
  return Promise.resolve();
};
window.HTMLMediaElement.prototype.pause = function () {};
let blobs = 0;
window.URL.createObjectURL = () => 'blob:board.test/' + (++blobs);
window.URL.revokeObjectURL = () => {};

// The microphone.
let gum = [];
let tracks = [];
window.navigator.mediaDevices = {
  getUserMedia(constraints) {
    gum.push(constraints);
    const track = { stopped: false, stop() { this.stopped = true; } };
    tracks.push(track);
    return Promise.resolve({ getTracks: () => [track] });
  },
};
let supported = ['audio/mp4', 'audio/webm;codecs=opus'];
const recorders = [];
window.MediaRecorder = class {
  static isTypeSupported(t) { return supported.indexOf(t) !== -1; }
  constructor(stream, opts) {
    this.stream = stream;
    this.mimeType = (opts && opts.mimeType) || '';
    this.state = 'inactive';
    recorders.push(this);
  }
  start() { this.state = 'recording'; }
  stop() {
    this.state = 'inactive';
    setTimeout(() => {
      this.ondataavailable({ data: new window.Blob(['take'], { type: this.mimeType }) });
      this.onstop();
    }, 0);
  }
};
let contexts = 0;
window.AudioContext = class {
  constructor() { contexts += 1; this.closed = false; }
  createMediaStreamSource() { return { connect() {}, disconnect() {} }; }
  createAnalyser() {
    return { fftSize: 512, getByteTimeDomainData(buf) { buf.fill(170); } };
  }
  close() { this.closed = true; return Promise.resolve(); }
};

for (const f of ['typeface.js', 'macros.js', 'plane-core.js', 'ink-core.js', 'slate-core.js',
                 'annotate.js', 'speak.js']) {
  try { window.eval(fs.readFileSync(path.join(WEB, f), 'utf8')); }
  catch (e) { fail(f + ': ' + e.message); }
}
try {
  let src = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
  src = src.replace('})();', 'window.__render = render;\n})();');
  window.eval(src);
  ok('loaded the board');
} catch (e) { fail('board.js: ' + e.message); }

const now = Date.now() / 1000;
const SHA = 'a'.repeat(32);
const question = { id: '0001', kind: 'question', title: 'Say hello',
                   body: 'Say this:\n\n@@SAY:' + SHA + ':ready:zh-CN@@ 你好\n\nThen stop.',
                   mtime: now };
const lesson = { id: '0002', kind: 'lesson', title: '', body: 'A card with no head.',
                 mtime: now - 10 };

function paint(extra) {
  window.__render(Object.assign({
    state: { course: 'Mandarin', subject: 'courses/Mandarin' },
    cards: [lesson, question], turns: [], messages: [], uploads: [], slate: [],
    speech: { lang: 'zh-CN', native: 'en-US', voice: null },
  }, extra || {}));
}

(async () => {
  // Opening the board reads nothing out and plays nothing.
  paint();
  await sleep(20);
  check(!posts(/\/speech\/card$/).length && plays.length === 0,
        'the first frame speaks nothing: no card is read, no phrase played',
        'opening the board started audio');
  doc.body.click();
  await sleep(10);
  check(plays.length === 0, 'and a tap anywhere plays nothing unasked',
        'a tap made the board play audio');

  // ---- the tab ------------------------------------------------------------
  const tab = doc.getElementById('tab-speak');
  check(tab && tab.closest('#writer-head .tabs'),
        'a third answer tab, beside write and type', 'there is no #tab-speak in the answer tabs');
  const box = doc.getElementById('speakbox');
  check(box && box.hidden, 'its box is shut until the tab is pressed',
        '#speakbox is missing or open before anyone asked');
  tab.onclick();
  check(!box.hidden && doc.getElementById('typebox').hidden && doc.getElementById('slate').hidden,
        'the tab opens #speakbox, and the slate and the typed box close',
        'the speak tab did not open its box alone');
  check(tab.classList.contains('on') && !doc.getElementById('tab-write').classList.contains('on'),
        'and the tab reads as the one in use', 'the tab state does not follow the speak tab');
  check(gum.length === 0, 'opening the tab does not ask for the microphone',
        'getUserMedia ran before any record tap');

  // ---- the MIME choice -----------------------------------------------------
  check(window.Speak.mime() === 'audio/mp4', 'audio/mp4 where the browser can make it',
        'mp4 was not preferred: ' + window.Speak.mime());
  supported = ['audio/webm;codecs=opus'];
  check(window.Speak.mime() === 'audio/webm;codecs=opus', 'else audio/webm;codecs=opus',
        'WebM/Opus was not the fallback: ' + window.Speak.mime());
  supported = ['audio/mp4', 'audio/webm;codecs=opus'];

  // ---- a take --------------------------------------------------------------
  heardReply = { ok: true, turn: '0003', rev: 1, heard: { heard: '你好' } };
  const rec = doc.getElementById('speak-rec');
  rec.click();
  await sleep(20);
  check(gum.length === 1 && gum[0].audio === true, 'the record tap asks for the microphone, once',
        'getUserMedia calls after one tap: ' + gum.length);
  check(recorders.length === 1 && recorders[0].mimeType === 'audio/mp4' && recorders[0].state === 'recording',
        'and records audio/mp4', 'the recorder did not start as audio/mp4');
  check(contexts === 1 && doc.getElementById('speak-meter').classList.contains('on'),
        'with a level meter running', 'no level meter while recording');
  await sleep(20);
  check(parseInt(doc.getElementById('speak-level').style.width, 10) > 0,
        'and the meter moves with the voice', 'the level meter stays at nothing');
  check(/stop/.test(rec.textContent) && !tracks[0].stopped,
        'the button is now stop, and the microphone is held', 'recording state is wrong');
  rec.click();
  await sleep(30);
  check(tracks[0].stopped, 'stop lets the microphone go: every track is stopped',
        'the tracks were left running after the take');
  const sent = posts(/\/speech\/say$/);
  check(sent.length === 1, 'the take is posted to /speech/say', 'posts to /speech/say: ' + sent.length);
  const form = sent.length ? sent[0].init.body : null;
  check(form && form.get('audio') && form.get('audio').name === 'take.m4a'
        && form.get('audio').type === 'audio/mp4',
        'as multipart, the audio a take.m4a', 'the audio part is wrong');
  check(form && form.get('answers') === '0001' && form.get('lang') === 'zh-CN',
        'with the question it answers and the language',
        'the take\'s fields are wrong: ' + (form ? JSON.stringify([...form.entries()]
          .filter(([k]) => k !== 'audio')) : 'none'));
  check(form && !form.get('ref') && !form.get('pinyin'),
        'and no target phrase or pinyin: nothing is graded',
        'the take still carries a target: ' + JSON.stringify([...form.keys()]));
  await sleep(10);
  const heard = doc.getElementById('heard');
  check(!heard.hidden && /heard: 你好/.test(heard.textContent),
        'the heard block says "heard: 你好"', 'no heard block: ' + heard.textContent);
  check(!heard.querySelector('.tone') && !heard.querySelector('.syl'),
        'and shows no tone chips', 'the heard block still draws tone chips');
  check(!/stop/.test(rec.textContent) && !doc.getElementById('speak-meter').classList.contains('on'),
        'and the button is back to record', 'the box still looks like it is recording');

  // A second take asks again: the microphone is never kept between takes.
  rec.click();
  await sleep(20);
  check(gum.length === 2, 'the next take asks for the microphone again',
        'a stream was reused across takes');
  rec.click();
  await sleep(30);
  check(tracks[1].stopped, 'and lets it go again', 'the second take left its tracks running');

  // WebM where mp4 cannot be made.
  supported = ['audio/webm;codecs=opus'];
  rec.click();
  await sleep(20);
  rec.click();
  await sleep(30);
  const webm = posts(/\/speech\/say$/).pop().init.body.get('audio');
  check(recorders[recorders.length - 1].mimeType === 'audio/webm;codecs=opus' && webm.name === 'take.webm',
        'a WebM take is sent as take.webm', 'the WebM take was named ' + webm.name);
  supported = ['audio/mp4', 'audio/webm;codecs=opus'];

  // The heard block comes back from a speech turn after a reload.
  paint({ turns: [{ id: '0003', rev: 1, kind: 'speech', answers: '0001', from: 'student',
                    t: now + 5, text: '你号' }] });
  await sleep(10);
  check(/heard: 你号/.test(heard.textContent),
        'a speech turn repaints the heard block', 'the turn did not repaint the heard block');
  check(/heard: 你号/.test((doc.querySelector('.mine[data-turn="0003"]') || {}).textContent || ''),
        'and the transcript shows what was heard', 'the speech turn is not in the transcript');

  // ---- speaking ------------------------------------------------------------
  const qSpeak = doc.querySelector('.card[data-card="0001"] .card-head .card-speak');
  const bare = doc.querySelector('.card[data-card="0002"] > .card-speak.bare');
  check(qSpeak, 'a card head has a speak button', 'no speak button in the card head');
  check(bare, 'and a card with no head gets one too', 'a headless card has no speak button');
  check(doc.querySelectorAll('.card[data-card="0001"] .card-speak').length === 1,
        'one each, however often the board repaints', 'speak buttons pile up on repaint');
  plays.length = 0;
  qSpeak.click();
  await sleep(20);
  const asked = posts(/\/speech\/card$/);
  check(asked.length === 1 && JSON.parse(asked[0].init.body).card === '0001',
        'the speak button posts /speech/card {card}', 'speak posted: '
        + JSON.stringify(asked.map((a) => a.init.body)));
  check(gets(/\/speech\/c{32}\.m4a$/).length === 1,
        'and fetches the phrase it answers with', 'the card\'s audio was not fetched');
  check(plays.length === 1 && /^blob:/.test(plays[0]),
        'and plays it from a Blob, not a Range-hungry src', 'played: ' + JSON.stringify(plays));

  const phrase = doc.querySelector('.card[data-card="0001"] .say-phrase');
  check(phrase && phrase.dataset.sha === SHA && phrase.dataset.lang === 'zh-CN'
        && phrase.dataset.text === '你好' && !phrase.dataset.pinyin,
        'a say fence is drawn as a phrase with its words, and no pinyin field',
        'the say phrase was not drawn: ' + (phrase ? phrase.outerHTML : 'none'));
  check(phrase && /Say this/.test(doc.querySelector('.card[data-card="0001"] .body').textContent)
        && /Then stop/.test(doc.querySelector('.card[data-card="0001"] .body').textContent),
        'between the prose around it', 'the prose around the phrase was lost');
  window.__render({ state: { course: 'Mandarin', subject: 'courses/Mandarin' },
                    cards: [{ id: '0009', kind: 'lesson', title: 'Thanks', mtime: now,
                              body: '@@SAY:' + 'e'.repeat(32) + ':ready:zh-CN@@ 谢谢 (thank you)' }],
                    turns: [], messages: [], uploads: [], slate: [], speech: null });
  const bare2 = doc.querySelector('.card[data-card="0009"] .say-phrase');
  check(bare2 && bare2.dataset.text === '谢谢 (thank you)',
        'a phrase keeps its own parentheses as words',
        'the phrase\'s words were cut: ' + (bare2 ? JSON.stringify(bare2.dataset) : 'none'));
  paint();
  await sleep(10);
  plays.length = 0;
  doc.querySelector('.card[data-card="0001"] .say-phrase .say-play').click();
  await sleep(20);
  check(gets(new RegExp('/speech/' + SHA + '\\.m4a$')).length === 1 && plays.length === 1,
        'its play button fetches /speech/<sha>.m4a and plays it',
        'the phrase did not play');

  // ---- nothing plays unasked ----------------------------------------------
  const SHA2 = 'b'.repeat(32);
  plays.length = 0;
  paint({ cards: [lesson, question, { id: '0004', kind: 'lesson', title: 'Next',
                                      body: 'A new card.\n\n@@SAY:' + SHA2 + ':ready:zh-CN@@ 谢谢',
                                      mtime: now + 20 }] });
  await sleep(30);
  check(!gets(new RegExp('/speech/' + SHA2 + '\\.m4a$')).length && plays.length === 0,
        'a new card\'s phrase does not play unasked',
        'a fresh card started audio by itself');
  check(posts(/\/speech\/card$/).length === asked.length,
        'and a new card is never read aloud by itself',
        'a fresh card was read aloud');
  check(!doc.getElementById('speak-auto'), 'and there is no auto-speak toggle',
        'the auto-speak toggle is still in the menu');

  const figured = (status) => ({ id: '0007', kind: 'lesson', title: 'Figure', mtime: now + 26,
                                 body: '@@FIGURE:' + 'ab'.repeat(8) + ':' + status + '@@' });
  paint({ cards: [lesson, question, figured('pending')] });
  paint({ cards: [lesson, question, figured('ready')] });
  check(doc.querySelector('.card[data-card="0007"] .figure img')
        && !doc.querySelector('.card[data-card="0007"] .figure.pending'),
        'a figure compiled after its card landed is drawn',
        'a figure made after its card landed still says compiling');

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\nevery session speaks, listens and shows what it heard');
  process.exit(errors.length ? 1 : 0);
})();
