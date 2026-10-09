// Harness: run board.js in a stub DOM and exercise renderMarkdown.
const fs = require('fs');
const path = require('path').join(__dirname, '..', 'web', 'board.js');

function stubEl() {
  const el = {
    style: {}, dataset: {}, classList: { add(){}, remove(){}, toggle(){} },
    hidden: false, value: '', textContent: '', innerHTML: '', files: [],
    addEventListener(){}, appendChild(){}, querySelector(){ return stubEl(); },
    querySelectorAll(){ return []; }, after(){},
    scrollHeight: 0,
  };
  Object.defineProperty(el, 'onclick', { set(){}, get(){ return null; } });
  return el;
}
global.document = {
  getElementById: () => stubEl(),
  querySelectorAll: () => [],
  createElement: () => stubEl(),
  createDocumentFragment: () => stubEl(),
  addEventListener(){}, body: { scrollHeight: 0, dataset: {}, classList: { toggle(){} } },
  documentElement: { style: { setProperty(){} } },
  title: '', hidden: false,
};
global.window = global;
global.localStorage = { getItem(){ return null; }, setItem(){} };
global.EventSource = function(){ return { close(){}, readyState: 1 }; };
global.getComputedStyle = () => ({ getPropertyValue: () => '18px' });
global.matchMedia = () => ({ matches: false, addEventListener(){} });
global.addEventListener = () => {};
global.scrollTo = () => {};
global.fetch = () => Promise.resolve({});
global.renderMathInElement = () => {};
global.innerHeight = 800; global.scrollY = 0;
global.FormData = function(){ this.append = () => {}; };
global.setTimeout = setTimeout;

// The board reads the shared plane -- what the hand is doing on a surface that
// pans and pinches. See web/plane-core.js.
eval(fs.readFileSync(path.replace('board.js', 'plane-core.js'), 'utf8'));

// Code fences are highlighted by the vendored highlight.js through codeview.js,
// both loaded by board.html before board.js. Indirect eval: each defines a global.
(0, eval)(fs.readFileSync(path.replace('board.js', 'vendor/highlight/highlight.min.js'), 'utf8'));
(0, eval)(fs.readFileSync(path.replace('board.js', 'codeview.js'), 'utf8'));

let src = fs.readFileSync(path, 'utf8');
// expose the internals for testing
src = src.replace('})();', 'window.__test = { renderMarkdown, inline, protect, restore, typeset, katexTrust };\n})();');
eval(src);

const R = window.__test.renderMarkdown;
let fails = 0;
function check(name, md, mustContain, mustNotContain) {
  const out = R(md);
  const bad = [];
  (mustContain || []).forEach(s => { if (out.indexOf(s) === -1) bad.push('missing: ' + s); });
  (mustNotContain || []).forEach(s => { if (out.indexOf(s) !== -1) bad.push('present: ' + s); });
  if (bad.length) { fails++; console.log('FAIL ' + name); bad.forEach(b => console.log('   ' + b)); console.log('   got: ' + out.replace(/\n/g,' ').slice(0,300)); }
  else console.log('ok   ' + name);
}

check('heading', '## Splitting fields', ['<h2>Splitting fields</h2>']);
check('paragraph', 'Plain text here.', ['<p>Plain text here.</p>']);
check('inline math untouched by emphasis',
  'Let $a_1 * a_2$ and $x_i$ be given.',
  ['$a_1 * a_2$', '$x_i$'], ['<em>']);
check('display math',
  'Then\n\n$$\n\\degree{L}{\\QQ} = 6\n$$\n\ndone.',
  ['\\degree{L}{\\QQ} = 6', '<p>done.</p>']);
check('bracket display math', 'text\n\n\\[ x^2 \\]\n\nmore', ['x^2']);
check('bold and italic', 'This is **bold** and *slanted*.', ['<strong>bold</strong>', '<em>slanted</em>']);
check('underscore in math not escaped',
  '$\\alpha_1$ and _real_ emphasis',
  ['$\\alpha_1$', '<em>real</em>']);
check('inline code', 'run `make split` now', ['<code>make split</code>']);
check('fenced code', 'a\n\n```\nx = 1\n```\n\nb', ['<pre><code>x = 1</code></pre>']);
// A FENCE KEEPS ITS INFO STRING. A language highlights; `path#Lx-y` numbers
// from x and adds a caption linking the source viewer; math stays plain.
{
  const holds = fs.readFileSync(path.replace('web/board.js', 'tutorboard/holds.py'), 'utf8')
    .split('\n').slice(39, 58).join('\n');
  const out = R('See\n\n```py board/tutorboard/holds.py#L40-58\n' + holds + '\n```\n\ndone.');
  const nums = (out.match(/<span class="line" data-n="(\d+)">/g) || [])
    .map(s => +/data-n="(\d+)"/.exec(s)[1]);
  const ok = out.indexOf('<figure class="code-fence">') !== -1
    && out.indexOf('<a class="code-ref" href="/source/board/tutorboard/holds.py?from=40&amp;to=58"') !== -1
    && out.indexOf('<code>board/tutorboard/holds.py#L40-58</code>') !== -1
    && out.indexOf('class="hljs language-py"') !== -1
    && /<span class="hljs-(keyword|string|comment|title)/.test(out)
    && JSON.stringify(nums) === JSON.stringify(Array.from({ length: 19 }, (_, i) => 40 + i))
    && out.indexOf('<p>done.</p>') !== -1;
  ok ? console.log('ok   a py fence over holds.py#L40-58 is highlighted, numbered 40 to 58, with a caption link')
     : (fails++, console.log('FAIL holds.py fence\n   got: ' + out.slice(0, 600)));
}
{
  const code = fs.readFileSync(path.replace('web/board.js', 'tutorboard/code.py'), 'utf8')
    .split('\n').slice(9, 12).join('\n');
  const out = R('```board/tutorboard/code.py#L10-12\n' + code + '\n```');
  /href="\/source\/board\/tutorboard\/code\.py\?from=10&amp;to=12"/.test(out)
    && /language-python/.test(out) && /data-n="10"/.test(out) && /data-n="12"/.test(out)
    && !/data-n="13"/.test(out)
    ? console.log('ok   a path with no language takes python from .py')
    : (fails++, console.log('FAIL code.py fence\n   got: ' + out.slice(0, 400)));
}
check('a language alone highlights without numbers or a caption',
  '```bash\necho "hi" # done\n```',
  ['<pre class="code"><code class="hljs language-bash">', 'hljs-'], ['data-n=', 'figcaption']);
['go', 'lean', 'r', 'sql', 'python'].forEach(l => {
  const known = window.CodeView.language(l);
  known ? console.log('ok   highlight.js has ' + l)
        : (fails++, console.log('FAIL highlight.js lacks ' + l));
});
check('a math fence is untouched', '```math\nx^2 < y\n```',
  ['<pre><code>x^2 &lt; y</code></pre>'], ['hljs', 'data-n=']);
check('a caption path is escaped, and html in code is text',
  '```py a/"b<x>.py#L1\nprint("<script>")\n```',
  [], ['<script>', '"b<x>']);
check('bullet list', '- alpha\n- beta\n', ['<ul>', '<li>alpha</li>', '<li>beta</li>', '</ul>']);
check('ordered list', '1. first\n2. second\n', ['<ol>', '<li>first</li>']);
check('nested list', '- outer\n  - inner\n', ['<ul>', '<li>outer<ul><li>inner</li></ul></li>']);
check('list with math', '- $x$ has degree $2$\n', ['<li>', 'math-raw']);
check('table', '| a | b |\n|---|---|\n| 1 | 2 |\n', ['<table>', '<th', '>a</th>', '<td', '>1</td>']);
check('table with math cells', '| root | value |\n|---|---|\n| $\\alpha$ | $\\omega\\sqrt[3]{2}$ |\n',
  ['$\\alpha$', '$\\omega\\sqrt[3]{2}$']);
check('hr', 'a\n\n---\n\nb', ['<hr>']);
check('blockquote', '> quoted line', ['<blockquote>', 'quoted line']);
check('a markdown image is fitted to the card',
  '![the sweep](/result/abc123)',
  ['<img class="card-img" alt="the sweep" src="/result/abc123">']);
{
  const css = fs.readFileSync(path.replace('board.js', 'board.css'), 'utf8');
  const rule = /\.card-img\s*{([^}]*)}/.exec(css);
  rule && /max-width:\s*100%/.test(rule[1]) && /max-height:/.test(rule[1])
    ? console.log('ok   .card-img caps width and height, so a 2100-px figure fits the glass')
    : (fails++, console.log('FAIL board.css has no .card-img rule capping both dimensions'));
}
check('figure ready', '@@FIGURE:abc123:ready@@', ['<img alt="figure" src="/figure/abc123.svg">']);
check('figure pending', '@@FIGURE:abc123:pending@@', ['compiling figure']);
// `>` is left unescaped on purpose so blockquote lines still match; `&lt;script>`
// is inert text, which is what matters.
check('html escaped in prose', 'if a < b then <script>alert(1)</script>',
  ['&lt;', '&lt;script&gt;alert(1)&lt;/script&gt;'.replace(/&gt;/g, '>')], ['<script>']);
check('math with less-than survives', '$a < b$', ['$a &lt; b$']);
check('escaped dollar', 'costs \\$5 today', ['$5']);
check('link', '[Garling](https://example.com)', ['<a href="https://example.com"']);
check('multiline paragraph joins', 'one\ntwo', ['<p>one two</p>']);
check('adjacent inline math', '$a$ and $b$', ['$a$', '$b$']);
check('starred command not italic', 'use $x^*y^*z$ here', ['$x^*y^*z$'], ['<em>']);

// AND WHAT THE FIRST PASS PARKS, because the answer panel's hint rests on it.
// `bareCommand` in board.js complains about a backslash command that will render
// as nothing, and the only thing it is allowed to complain about is what
// `protect` hands BACK -- so a command inside `$...$` or inside backticks has to
// be gone from that, or a regex in a code workspace gets called broken
// mathematics every time somebody types one.
{
  const store = [];
  const left = window.__test.protect(
    'so $\\gamma^2 = 2$ and the pattern `\\d+` but \\omega on its own', store);
  const bare = /\\([A-Za-z]+)/.exec(left);
  bare && bare[1] === 'omega'
    ? console.log('ok   protect parks math and code, so only a bare command is '
                  + 'left to complain about')
    : (fails++, console.log('FAIL the first pass left ' + JSON.stringify(left)));
}

// KATEX TRUSTS ONLY SAFE COMMANDS. A card is model-written text rendered as
// HTML, so `\href{javascript:...}` must not become a live anchor, an image must
// not load from another host, and `\htmlClass` and friends must not reach the
// DOM. Run with the real KaTeX and auto-render in jsdom, through `typeset`.
{
  let JSDOM = null;
  try { ({ JSDOM } = require('jsdom')); } catch (e) { JSDOM = null; }
  if (!JSDOM) {
    fails++;
    console.log('FAIL jsdom is not installed; run.py installs it');
  } else {
    const web = require('path').join(__dirname, '..', 'web', 'katex');
    const dom = new JSDOM('<!doctype html><html><body></body></html>',
      { url: 'https://board.test/s/1/board', runScripts: 'outside-only' });
    dom.window.eval(fs.readFileSync(web + '/katex.min.js', 'utf8'));
    dom.window.eval(fs.readFileSync(web + '/auto-render.min.js', 'utf8'));
    global.renderMathInElement = dom.window.renderMathInElement;
    global.location = dom.window.location;
    global.URL = dom.window.URL;

    const card = (md) => {
      const el = dom.window.document.createElement('div');
      el.innerHTML = R(md);
      window.__test.typeset(el);
      return el;
    };
    const verdict = (name, ok, el) => {
      if (ok) { console.log('ok   ' + name); return; }
      fails++;
      console.log('FAIL ' + name + '\n   got: ' + el.innerHTML.slice(0, 300));
    };
    const anchors = (el) => Array.from(el.querySelectorAll('a')).map(a => a.getAttribute('href'));
    const images = (el) => Array.from(el.querySelectorAll('img')).map(i => i.getAttribute('src'));

    let el = card('Click $\\href{javascript:alert(1)}{x}$ now.');
    verdict('a card whose math is \\href{javascript:alert(1)}{x} renders no javascript: anchor',
      el.querySelector('.katex') && anchors(el).length === 0
      && !/javascript:/i.test(el.innerHTML.replace(/<annotation[\s\S]*?<\/annotation>/g, '')), el);
    ['JaVaScRiPt:alert(1)', 'javascript&colon;alert(1)', ' javascript:alert(1)',
     'data:text/html,<b>x</b>', 'vbscript:x'].forEach(u => {
      el = card('$\\href{' + u + '}{x}$ and $\\url{' + u + '}$');
      verdict('no anchor for ' + u, anchors(el).length === 0, el);
    });
    el = card('$\\href{https://example.org/a}{x}$, $\\url{http://example.org}$, $\\href{notes/a.pdf}{y}$');
    verdict('http, https and relative links still render as anchors',
      JSON.stringify(anchors(el)) === JSON.stringify(
        ['https://example.org/a', 'http://example.org', 'notes/a.pdf']), el);
    el = card('$\\includegraphics{/static/a.png}$ $\\includegraphics{https://board.test/b.png}$');
    verdict('a same-origin image loads',
      JSON.stringify(images(el)) === JSON.stringify(['/static/a.png', 'https://board.test/b.png']), el);
    el = card('$\\includegraphics{https://evil.test/x.png}$ $\\includegraphics{//evil.test/y.png}$');
    verdict('an image from another origin does not', images(el).length === 0, el);
    el = card('$\\htmlId{pwn}{a}$ $\\htmlClass{pwn}{b}$ $\\htmlStyle{color:red}{c}$ $\\htmlData{pwn=1}{d}$');
    verdict('\\htmlId, \\htmlClass, \\htmlStyle and \\htmlData are refused',
      !el.querySelector('#pwn') && !el.querySelector('.pwn')
      && !el.querySelector('[style*="red"]') && !el.querySelector('[data-pwn]'), el);
    // The source page: the server's numbered, marked lines, coloured in place.
    {
      const d = new JSDOM('<!doctype html><body class="source-page"><pre class="code numbered">'
        + '<code data-source="1" data-lang="python" data-from="2" data-to="3">'
        + '<span class="line" data-n="1" id="L1">s = """a\n</span>'
        + '<span class="line mark" data-n="2" id="L2">b"""\n</span>'
        + '<span class="line mark" data-n="3" id="L3">def f(x):\n</span>'
        + '<span class="line" data-n="4" id="L4">    return x &lt; 1</span></code></pre></body>').window.document;
      const before = d.querySelector('code').textContent;
      window.CodeView.upgrade(d);
      const code = d.querySelector('code');
      const lines = Array.from(code.querySelectorAll('.line'));
      verdict('the source page keeps its numbers and marks once highlighted, a string across lines included',
        code.textContent === before && lines.length === 4
        && lines.map(l => l.getAttribute('data-n')).join() === '1,2,3,4'
        && lines.filter(l => l.classList.contains('mark')).map(l => l.getAttribute('data-n')).join() === '2,3'
        && !!lines[1].querySelector('.hljs-string') && !!lines[2].querySelector('.hljs-keyword'), code);
    }
    const t = window.__test.katexTrust;
    verdict('the trust function refuses a command it does not know',
      t({ command: '\\htmlClass', class: 'x' }) === false
      && t({ command: '\\somethingNew', url: 'https://x' }) === false
      && t({ command: '\\href', url: 'https://x', protocol: 'https' }) === true, el);
  }
}


console.log(fails ? '\n' + fails + ' FAILURES' : '\nall markdown checks passed');
process.exit(fails ? 1 : 0);
