// Every session speaks, listens and shows what it heard.
//
// The real board in a real DOM, with the microphone, MediaRecorder,
// AudioContext and the audio element stubbed: the third answer tab and its
// box; getUserMedia asked for only on the record tap, and every track stopped
// when the take ends; audio/mp4 chosen where it can be made, else WebM/Opus;
// the take posted to /speech/say with the phrase it aims at, and the heard
// block with a tone chip per syllable; a card's speak button posting
// /speech/card and playing what it answers, fetched whole into a Blob; a
// `say` phrase drawn and played; and auto-speak, which plays a new card's
// phrases and never its prose, a per-subject choice that takes the subject's
// `speech.auto` until one is made, and whose tap unlocks iOS audio.
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
                   body: 'Say this:\n\n@@SAY:' + SHA + ':ready:zh-CN@@ 你好 (ni3 hao3)\n\nThen stop.',
                   mtime: now };
const lesson = { id: '0002', kind: 'lesson', title: '', body: 'A card with no head.',
                 mtime: now - 10 };

function paint(extra) {
  window.__render(Object.assign({
    state: { course: 'Mandarin', subject: 'courses/Mandarin' },
    cards: [lesson, question], turns: [], messages: [], uploads: [], slate: [],
    speech: { lang: 'zh-CN', native: 'en-US', voice: null, auto: true },
  }, extra || {}));
}

(async () => {
  // Auto-speak is on for this subject: the first frame only learns what is
  // there, and speaks nothing.
  paint();
  await sleep(20);
  check(!posts(/\/speech\/card$/).length,
        'the first frame speaks nothing, even with auto-speak on',
        'opening the board read out every card already on it');

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
  check(/你好/.test(doc.getElementById('speak-target').textContent)
        && /ni3 hao3/.test(doc.getElementById('speak-target').textContent),
        'the take is aimed at the question\'s say phrase',
        'the box does not show the phrase a take aims at: '
        + doc.getElementById('speak-target').textContent);

  // ---- the MIME choice -----------------------------------------------------
  check(window.Speak.mime() === 'audio/mp4', 'audio/mp4 where the browser can make it',
        'mp4 was not preferred: ' + window.Speak.mime());
  supported = ['audio/webm;codecs=opus'];
  check(window.Speak.mime() === 'audio/webm;codecs=opus', 'else audio/webm;codecs=opus',
        'WebM/Opus was not the fallback: ' + window.Speak.mime());
  supported = ['audio/mp4', 'audio/webm;codecs=opus'];

  // ---- a take --------------------------------------------------------------
  heardReply = {
    ok: true, turn: '0003', rev: 1,
    heard: { heard: '你好', target: '你好', pinyin: 'ni3 hao3', verdict: 'one tone off',
             assess: { prototype: true, syllables: [
               { syllable: '你', expect: 'T2', heard: 'T2', confidence: 0.9 },
               { syllable: '好', expect: 'T3', heard: 'T1', confidence: 0.7 },
               { syllable: '吗', expect: 'T0', heard: 'unknown', confidence: 0.1 }] } },
  };
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
  check(form && form.get('answers') === '0001' && form.get('lang') === 'zh-CN'
        && form.get('ref') === '你好' && form.get('pinyin') === 'ni3 hao3',
        'with the question it answers, the language, the target and its pinyin',
        'the take\'s fields are wrong: ' + (form ? JSON.stringify([...form.entries()]
          .filter(([k]) => k !== 'audio')) : 'none'));
  await sleep(10);
  const heard = doc.getElementById('heard');
  check(!heard.hidden && /heard: 你好/.test(heard.textContent),
        'the heard block says "heard: 你好"', 'no heard block: ' + heard.textContent);
  const chips = heard.querySelectorAll('.tone');
  check(chips.length === 3, 'with a chip per syllable', 'tone chips: ' + chips.length);
  check(chips.length === 3 && chips[0].classList.contains('ok') && chips[1].classList.contains('off')
        && chips[2].classList.contains('unknown'),
        'right, wrong and unsure each marked', 'the chips are not marked by verdict');
  check(chips.length === 3 && /T1/.test(chips[1].textContent) && /\?/.test(chips[2].textContent),
        'and each says the tone it heard, in text, not colour alone',
        'a chip does not say what it heard');
  check(/one tone off/.test(heard.textContent), 'with the verdict under them', 'no verdict');
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
                    t: now + 5, text: '你号', target: '你好', pinyin: 'ni3 hao3',
                    verdict: 'heard 号 for 好',
                    tones: [{ syllable: '你', expect: 'T2', heard: 'T2', confidence: 0.8 }] }] });
  await sleep(10);
  check(/heard: 你号/.test(heard.textContent) && heard.querySelectorAll('.tone').length === 1,
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
        && phrase.dataset.text === '你好' && phrase.dataset.pinyin === 'ni3 hao3',
        'a say fence is drawn as a phrase with its words and pinyin',
        'the say phrase was not drawn: ' + (phrase ? phrase.outerHTML : 'none'));
  check(phrase && /Say this/.test(doc.querySelector('.card[data-card="0001"] .body').textContent)
        && /Then stop/.test(doc.querySelector('.card[data-card="0001"] .body').textContent),
        'between the prose around it', 'the prose around the phrase was lost');
  plays.length = 0;
  phrase.querySelector('.say-play').click();
  await sleep(20);
  check(gets(new RegExp('/speech/' + SHA + '\\.m4a$')).length === 1 && plays.length === 1,
        'its play button fetches /speech/<sha>.m4a and plays it',
        'the phrase did not play');

  // ---- auto-speak ----------------------------------------------------------
  const auto = doc.getElementById('speak-auto');
  check(auto && auto.getAttribute('aria-pressed') === 'true',
        'auto-speak starts as the subject\'s speech.auto says', 'auto-speak is not on by default');
  const SHA2 = 'b'.repeat(32);
  const cardPosts = posts(/\/speech\/card$/).length;
  paint({ cards: [lesson, question, { id: '0004', kind: 'lesson', title: 'Next',
                                      body: 'A new card.\n\n@@SAY:' + SHA2 + ':ready:zh-CN@@ 谢谢',
                                      mtime: now + 20 }] });
  await sleep(30);
  check(gets(new RegExp('/speech/' + SHA2 + '\\.m4a$')).length === 1,
        'a new card\'s say phrase plays unasked while it is on',
        'the new card\'s phrase was not played');
  check(posts(/\/speech\/card$/).length === cardPosts,
        'and its prose is not read: target phrases only',
        'auto-speak read the whole card aloud');
  await sleep(30);
  plays.length = 0;
  auto.click();
  check(plays.length === 1 && /^data:audio/.test(plays[0]),
        'the toggle\'s own tap plays a silent clip: the iOS unlock',
        'the toggle tap played nothing, so iOS would stay locked');
  check(window.localStorage.getItem('speak-auto:courses/Mandarin') === '0'
        && auto.getAttribute('aria-pressed') === 'false',
        'turned off, and stored for this subject', 'the choice was not stored per subject');
  const SHA3 = 'd'.repeat(32);
  paint({ cards: [lesson, question, { id: '0005', kind: 'lesson', title: 'Later',
                                      body: '@@SAY:' + SHA3 + ':ready:zh-CN@@ 再见', mtime: now + 30 }] });
  await sleep(30);
  check(!gets(new RegExp('/speech/' + SHA3 + '\\.m4a$')).length
        && auto.getAttribute('aria-pressed') === 'false',
        'and a stored off outranks the subject\'s default', 'auto-speak came back on');

  // Another subject has its own choice, and its own default.
  paint({ state: { course: 'Topology', subject: 'courses/Topology' }, speech: null });
  check(auto.getAttribute('aria-pressed') === 'false',
        'a subject with no speech block defaults to off', 'auto-speak is on for a maths subject');
  auto.click();
  check(window.localStorage.getItem('speak-auto:courses/Topology') === '1'
        && window.localStorage.getItem('speak-auto:courses/Mandarin') === '0',
        'and its choice is kept apart from the other subject\'s', 'auto-speak leaked between subjects');

  console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                            : '\nevery session speaks, listens and shows what it heard');
  process.exit(errors.length ? 1 : 0);
})();
