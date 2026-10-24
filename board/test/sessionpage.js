// THE BOARD, LOADED FROM A REAL SERVER AT /s/<id>/board. A helper, not a
// suite: `onesession.py` starts the server and runs this against it.
//
//     node sessionpage.js <board url> <marker on the card>
//
// The page and every script come off the server, as the iPad gets them; jsdom
// runs them with a fetch and an EventSource that go over the wire. Then it
// writes the three kinds of answer -- ink on the card, a page of the slate, and
// a typed answer -- and prints one JSON line: every request it made, with the
// status each got, and what it saw.

const http = require('http');

let JSDOM;
try {
  ({ JSDOM } = require('jsdom'));
} catch (e) {
  console.log(JSON.stringify({ skip: 'jsdom is not installed' }));
  process.exit(0);
}

const PAGE = process.argv[2];
const MARK = process.argv[3] || '';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const out = { requests: [], rendered: false, errors: [], saved: {} };

async function text(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(url + ' answered ' + r.status);
  return r.text();
}

async function until(test, ms) {
  for (let t = 0; t < ms; t += 50) {
    if (test()) return true;
    await sleep(50);
  }
  return !!test();
}

(async () => {
  const html = await text(PAGE);
  const dom = new JSDOM(html, { runScripts: 'outside-only', pretendToBeVisual: true,
                                url: PAGE });
  const { window } = dom;
  const doc = window.document;
  window.HTMLCanvasElement.prototype.getContext = () =>
    new Proxy({}, { get: () => () => {}, set: () => true });
  window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
  Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get: () => 900 });
  Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', { get: () => 500 });
  window.HTMLElement.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: 900, height: 400, right: 900, bottom: 400, x: 0, y: 0 };
  };
  window.Element.prototype.scrollIntoView = function () {};
  window.Element.prototype.setPointerCapture = function () {};
  window.Element.prototype.releasePointerCapture = function () {};
  window.renderMathInElement = () => {};
  window.requestAnimationFrame = (fn) => setTimeout(fn, 0);
  window.scrollTo = function () {};
  window.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {},
                               addEventListener() {}, removeEventListener() {} });
  window.caches = { keys: () => Promise.resolve([]) };
  window.addEventListener('error', (e) => out.errors.push('uncaught: ' + e.message));

  // Over the wire, resolved against the page as a browser would.
  window.fetch = (u, init) => {
    const url = new URL(String(u), PAGE);
    const opts = Object.assign({}, init || {});
    delete opts.keepalive;
    delete opts.cache;
    delete opts.credentials;
    const rec = { url: url.pathname + url.search, method: opts.method || 'GET' };
    out.requests.push(rec);
    return fetch(url, opts).then((r) => { rec.status = r.status; return r; },
                                 (e) => { rec.status = 'error ' + e.message; throw e; });
  };
  window.EventSource = function (u) {
    const url = new URL(String(u), PAGE);
    const self = this;
    const rec = { url: url.pathname, method: 'STREAM' };
    out.requests.push(rec);
    this.readyState = 0;
    this.close = function () { self.readyState = 2; if (self.req) self.req.destroy(); };
    this.addEventListener = function () {};
    this.req = http.get(url, (res) => {
      rec.status = res.statusCode;
      self.readyState = 1;
      if (self.onopen) self.onopen();
      let buf = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => {
        buf += chunk;
        let cut;
        while ((cut = buf.indexOf('\n\n')) !== -1) {
          const block = buf.slice(0, cut);
          buf = buf.slice(cut + 2);
          const data = block.split('\n').filter((l) => l.indexOf('data: ') === 0)
            .map((l) => l.slice(6)).join('\n');
          if (data && self.onmessage) {
            try { self.onmessage({ data }); }
            catch (e) { out.errors.push('onmessage: ' + e.message); }
          }
        }
      });
    });
    this.req.on('error', () => {});
  };

  // Every script the page names, off the server. KaTeX is stubbed above.
  const re = /<script src="(\/static\/[^"]+)"/g;
  let m;
  const scripts = [];
  while ((m = re.exec(html))) if (m[1].indexOf('/static/katex/') !== 0) scripts.push(m[1]);
  for (const src of scripts) {
    out.requests.push({ url: src, method: 'GET', status: 200, script: true });
    const body = await text(new URL(src, PAGE));
    if (src === '/static/board.js' && window.Slate) {
      const real = window.Slate.create;
      window.Slate.create = function (opts) {
        const api = real(opts);
        window.__slate = api;
        return api;
      };
    }
    try { window.eval(body); } catch (e) { out.errors.push(src + ': ' + e.message); }
  }

  // 1. The card renders.
  const card = () => doc.querySelector('[data-card="0001"]');
  out.rendered = await until(() => card() && card().textContent.indexOf(MARK) !== -1, 15000);

  // 2. Ink on the card: the pen on, one stroke, and the page put away.
  await until(() => !doc.getElementById('writer').hidden, 8000);
  if (window.Annotate && card()) {
    window.Annotate.setOn(true);
    window.Annotate.attach(card());
    const layer = card().querySelector('canvas.' + 'ann-layer') || card().querySelector('canvas');
    const ev = (type, x, y) => {
      const e = new window.Event(type, { bubbles: true, cancelable: true });
      Object.assign(e, { pointerId: 7, pointerType: 'pen', pressure: 0.5,
                         clientX: x, clientY: y, isPrimary: true, buttons: 1 });
      return e;
    };
    if (layer) {
      layer.dispatchEvent(ev('pointerdown', 40, 40));
      for (let i = 1; i <= 6; i++) layer.dispatchEvent(ev('pointermove', 40 + 20 * i, 40 + 8 * i));
      layer.dispatchEvent(ev('pointerup', 160, 88));
    }
    out.saved.inkOwed = window.Annotate.unsaved();
    window.dispatchEvent(new window.Event('pagehide'));
  }
  await sleep(300);

  // 3. A page of the slate.
  const slate = window.__slate;
  if (slate) {
    slate.load({ w: 1130, h: 1514, strokes: [
      { c: '#1a1a1a', w: 3, pts: [[100, 100], [220, 180], [340, 140]] }] });
    try { await slate.save(); } catch (e) { out.errors.push('slate save: ' + e.message); }
  } else {
    out.errors.push('no slate on the board');
  }

  // 4. A typed answer: a draft, kept, then sent.
  const say = doc.getElementById('saybox');
  say.value = 'typed ' + MARK;
  say.dispatchEvent(new window.Event('input'));
  await sleep(1200);
  doc.getElementById('send-type').click();
  await sleep(600);

  console.log(JSON.stringify(out));
  process.exit(0);
})().catch((e) => {
  out.errors.push('driver: ' + e.message + ' ' + (e.stack || '').split('\n').slice(1, 4).join(' | '));
  console.log(JSON.stringify(out));
  process.exit(0);
});
