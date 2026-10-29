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

// The board's macro table, which board.html loads before board.js.
eval(fs.readFileSync(path.replace('board.js', 'macros.js'), 'utf8'));

let src = fs.readFileSync(path, 'utf8');
// expose the internals for testing
src = src.replace('})();', 'window.__test = { renderMarkdown, inline, protect, restore, typeset, katexTrust, bareCommand };\n})();');
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
check('bracket display math', 'text\n\n\\[ x^2 \\]\n\nmore', ['<div class="math-raw">\\[ x^2 \\]</div>']);
// \( and \[ ARE PARKED LIKE $. Their closes start with a backslash, and a scan
// that stepped over every escape first walked past them: the math stayed in the
// prose, and markdown cut it into pieces auto-render cannot put back together.
check('\\(...\\) is parked, so its asterisks are not emphasis',
  'so \\(a * b * c\\) here', ['<span class="math-raw">\\(a * b * c\\)</span>'], ['<em>']);
check('a line of \\[...\\] that starts with a dash is not a list item',
  'We get \\[ f(x) = x^2\n- 3x + 2 \\] done', ['math-raw', '- 3x + 2 \\]'], ['<ul>', '<li>']);
check('an underscore pair inside \\(...\\) is not emphasis',
  'take \\( _1 x_ \\) now', ['\\( _1 x_ \\)'], ['<em>']);

// TEXT-MODE TeX IN PROSE IS SET, NOT SHOWN. The card the iPad showed as
// `\texttt{ch07-homework.tex}` and `\textbf{Problem 16(d), whole.}`, verbatim.
check('the 0122 card: \\texttt and \\textbf are set, the math is parked',
  '14(d) is done. Both lattices sit in \\texttt{ch07-homework.tex} and '
  + '\\texttt{ch07-14d.png}.\n\n\\textbf{Problem 16(d), whole.} Let '
  + '$\\alpha=\\sqrt[4]{2}\\in\\mathbb{R}$ and $\\langle\\sigma_1\\rangle$.',
  ['<code>ch07-homework.tex</code>', '<code>ch07-14d.png</code>',
   '<strong>Problem 16(d), whole.</strong>',
   '<span class="math-raw">$\\alpha=\\sqrt[4]{2}\\in\\mathbb{R}$</span>'],
  ['\\texttt', '\\textbf']);
check('math inside \\textbf is still math',
  '\\noindent\\textbf{The case $p_1=13$.} done',
  ['<strong>The case <span class="math-raw">$p_1=13$</span>.</strong> done'], ['noindent']);
check('\\emph, \\textit and nesting',
  '\\emph{one} and \\textit{two \\textbf{three}}',
  ['<em>one</em>', '<em>two <strong>three</strong></em>']);
check('\\texttt unescapes its own escapes and escapes html',
  'see \\texttt{a\\_b\\%<script>}', ['<code>a_b%&lt;script&gt;</code>'], ['<script>']);
check('an unknown command, or one with no group, is left as written',
  '\\foo{x} and \\textbf alone', ['\\foo{x}', '\\textbf alone']);
check('a group never crosses a blank line', '\\textbf{open\n\nclosed}', ['\\textbf{open']);
check('control symbols, words, a line break and quotes',
  "50\\% \\& \\_x\\_ \\LaTeX\\ is \\ldots{} fine\\\\\nnext ``quoted'' \\S 3",
  ['50% &amp; _x_ LaTeX is … fine<br>', '“quoted”', '§ 3'], ['<em>', '\\']);
check("a TeX quote is not an empty code span", "``quoted'' and $a$ here",
  ['“quoted” and <span class="math-raw">$a$</span>'], ['<code>']);
check('ties and dashes, where they cannot be anything else',
  'Problem~16, pages 3--5, a --- b, ~5 min, ~~gone~~ and a-->b',
  ['Problem\u00a016', '3\u20135', 'a \u2014 b', '~5 min', '<del>gone</del>', 'a-->b']);
check('a tilde in a link or a path is a tilde',
  '[home](https://x.org/a~b) and docs/v~2', ['href="https://x.org/a~b"', 'docs/v~2']);
check('a tilde that means "distributed as" or a git ancestor stays a tilde',
  'X~N(0,1), Y~Bernoulli(p), x~y and HEAD~1; Fig.~2', ['X~N(0,1)', 'Y~Bernoulli(p)', 'x~y', 'HEAD~1', 'Fig.\u00a02']);
check('a URL keeps its dashes',
  '[doc](http://x.com/a---b) and https://x.com/1--2 but 1--2',
  ['href="http://x.com/a---b"', 'https://x.com/1--2', 'but 1\u20132']);
// A MATH SPAN CLOSES WHERE AUTO-RENDER CLOSES IT: a `$` inside braces does not
// end it. The Probability write-up's `P(\text{$E$ before $F$ on trial $n$})`,
// carried into a card, was parked as `$P(\text{$` and the rest left raw.
check('a $ inside \\text{...} does not close the span (hw01:205)',
  'so $P(\\text{$E$ before $F$ on trial $n$})$ holds',
  ['<span class="math-raw">$P(\\text{$E$ before $F$ on trial $n$})$</span> holds']);
check('an inline $ never pairs across a blank line, and stays a dollar',
  'It costs $5 per unit.\n\nLater we set $x = 1$ here.',
  ['It costs <span class="tex-dollar">$</span>5 per unit.', '<span class="math-raw">$x = 1$</span> here'],
  ['$5 per unit.\n']);
// DISPLAY ENVIRONMENTS ARE MATH. An `align*` the tutor transcribes is parked
// whole: its `\\` rows are not <br> and its `&` reaches KaTeX as written.
check('align* is parked whole, rows and ampersands intact',
  'Expanding gives \\begin{align*} x_1 &= a_1 + b \\\\ y_1 &= 2 \\end{align*} holds.',
  ['<div class="math-raw">\\begin{align*} x_1 &amp;= a_1 + b \\\\ y_1 &amp;= 2 \\end{align*}</div>'],
  ['<br>']);
check('an environment KaTeX lacks is handed over as one it has',
  '\\begin{multline*} a \\\\ b \\end{multline*} and \\begin{displaymath} c \\end{displaymath}',
  ['\\begin{gather*} a \\\\ b \\end{gather*}', '\\[ c \\]'], ['multline', 'displaymath']);
// FONT DECLARATIONS SAY NOTHING; A GROUP THEY SCOPE IS SET. hw01's hints open
// `\upshape\emph{Hint:}`, and the problem view showed `\upshape*Hint:*`.
check('\\upshape and its kin are dropped; {\\bf X} and {\\itshape X} are set',
  '\\upshape\\emph{Hint:} {\\bf bold} {\\itshape it} {\\small s} \\normalfont end',
  ['<em>Hint:</em> <strong>bold</strong> <em>it</em> s end'], ['\\', '{', '}']);
// ACCENTS, AND A QUOTE LEFT ESCAPED. Card 0048 read `\"how does this help.\"`.
check('an escaped quote is a quote, an accent between letters is the letter',
  'content of \\"how does this help.\\" and L\'H\\^opital, G\\"odel, \\\'{e}t\\\'e, it\\\'s',
  ['content of "how does this help." and', "L'Hôpital", 'Gödel', 'été', "it's"], ['\\', 'ḧ']);
// LISTS, PROOFS AND RUN-IN HEADINGS, as a tutor transcribes them from a write-up.
check('enumerate[label=(\\alph*)] is bold-labelled paragraphs, with nesting',
  'Show:\n\\begin{enumerate}[label=(\\alph*)]\n  \\item $G$ is \\emph{cyclic}.\n'
  + '  \\item Find $x$ with\n    \\begin{itemize}\n      \\item one\n      \\item two\n    \\end{itemize}\n'
  + '  \\item[(z)] its own label\n\\end{enumerate}\nAfter.',
  ['<p>Show:</p>', '<p><strong>(a)</strong> <span class="math-raw">$G$</span> is <em>cyclic</em>.</p>',
   '<p><strong>(b)</strong> Find', '<ul><li>one</li><li>two</li></ul>',
   '<p><strong>(z)</strong> its own label</p>', '<p>After.</p>'], ['\\item', '\\begin', '\\end']);
check('a plain enumerate is an ordered list, and a stray \\item[x] is bold',
  '\\begin{enumerate}\\item one\\item two\\end{enumerate}\n\nThen \\item[(c)] more.',
  ['<ol><li>one</li><li>two</li></ol>', 'Then <strong>(c)</strong> more.'], ['\\item']);
check('a proof is its run-in head and one box; a theorem is bold with its note',
  '\\begin{proof}[Proof that {$[L:K]=2$}]\nSince $G$ is cyclic, done. \\qed\n\\end{proof}\n'
  + '\\begin{lemma}[Tower] $[L:K]$ is finite. \\end{lemma}',
  ['<em>Proof that <span class="math-raw">$[L:K]=2$</span>.</em> Since', 'cyclic, done.', '∎</p>',
   '<strong>Lemma (Tower).</strong> <span class="math-raw">$[L:K]$</span> is finite.'],
  ['\\begin', '\\end', '∎ ∎', '{<span']);
check('\\paragraph and \\section are run-in bold',
  '\\paragraph{(a) The tower.} $[K:\\QQ]=4$. \\subsection*{Part (b)} next',
  ['<strong>(a) The tower.</strong> <span class="math-raw">', '<strong>Part (b)</strong> next'],
  ['\\paragraph', '\\subsection']);
check("a TeX single quote is a pair of quotes; code with an apostrophe is code",
  "of `duplicating the cube') and the `fixed' field, but `don't` and `f'(x)` and `--format='%h'`",
  ["of ‘duplicating the cube’)", "the ‘fixed’ field", '<code>don\'t</code>', "<code>f'(x)</code>",
   "<code>--format='%h'</code>"]);
check('a bracket after \\\\ is kept unless it is a length',
  'one\\\\[2pt]\ntwo\\\\\n[note] three', ['<br>', '[note] three'], ['[2pt]']);
check('a table separator and a rule keep their dashes',
  '| a | b |\n| --- | --- |\n| 1 | 2 |\n\n---\n\nend', ['<table>', '<hr>'], ['\u2014']);
check('a lone backtick does not swallow the next paragraph',
  'a `b\n\nc $x$ d', ['a `b', '<span class="math-raw">$x$</span>'], ['<code>']);
// A LABEL IS READ AS TeX READS IT: a `]` inside `{...}` or `$...$` does not
// close it, and `[L:K]` is everyday Galois notation.
check('an \\item label holding $[L:K]$ is one label, in a list or stray',
  '\\begin{itemize}\\item[{$[L:K]=2$}] degree two \\item[$[M:K]=3$] three\\end{itemize}\n\n'
  + 'And \\item[{$[E:F]$}] stray.',
  ['<strong><span class="math-raw">$[L:K]=2$</span></strong> degree two',
   '<strong><span class="math-raw">$[M:K]=3$</span></strong> three',
   '<strong><span class="math-raw">$[E:F]$</span></strong> stray.'], ['{$', '$}', '<strong>{']);
check('a proof note holding unbraced $[L:K]$ is one note',
  '\\begin{proof}[Proof that $[L:K]=2$] Done.\\qedhere\\end{proof}',
  ['<em>Proof that <span class="math-raw">$[L:K]=2$</span>.</em> Done. ∎'], ['qedhere', '=2$]']);
check('a description is bold-labelled paragraphs; center and quote are their words',
  '\\begin{description}\\item[Case 1] foo \\item[Case $[a,b]$] bar\\end{description}\n'
  + '\\begin{center}$x$\\end{center} \\begin{quote}q\\end{quote}',
  ['<p><strong>Case 1</strong> foo</p>', '<strong>Case <span class="math-raw">$[a,b]$</span></strong> bar',
   '<p><span class="math-raw">$x$</span></p>', '<p>q</p>'], ['\\begin', '\\end', '\\item']);
// A CODE SPAN ENDING IN A PRIME IS CODE, not a TeX quote.
check("`foldl'`, `A'*B` and `f'` are code spans",
  "Use `foldl'` instead of `foldl` here. MATLAB's `A'*B` and `x`. Call `f'` the derivative and `g` too.",
  ["<code>foldl'</code> instead of <code>foldl</code> here", "<code>A'*B</code> and <code>x</code>",
   "<code>f'</code> the derivative and <code>g</code> too"], ['‘', '’']);
// AN ATTRIBUTE IS NEVER CLOSED BY A CARD'S WORDS, AND A LINK IS NEVER SCRIPT.
check('alt text and an address cannot open an attribute; javascript: is no link',
  '![x" onerror="alert(1)](a.png) ![costs \\$5](b.png) [tap](javascript:alert%281%29) '
  + '[ok](https://a.org/?a=1&b=2) ![i](c"onerror="alert(1))',
  ['alt="x&quot; onerror=&quot;alert(1)"', 'alt="costs $5" src="b.png"', ' tap ',
   '<a href="https://a.org/?a=1&amp;b=2"'], ['" onerror="', 'href="javascript', '"onerror="', 'tex-dollar']);
check("TeX's spacing symbols in prose are space or nothing",
  '{\\it word\\/} and 10\\,000 and e.g.\\@ here and a\\;b and a\\!b',
  ['<em>word</em> and 10 000 and e.g. here and a b and ab'], ['\\']);
check('a star after a command with no starred form is the text\'s own',
  '\\upshape*Hint:* go, \\section*{Part} and \\vspace*{2pt}x',
  ['<em>Hint:</em> go', '<strong>Part</strong>'], ['2pt', '\\']);
check("Markdown's escapes are the character; \\S before a non-number is not §",
  'example\\.com, \\*lit\\*, x\\~y, hy\\-phen, \\S 3, \\S+ and \\~{n}',
  ['example.com, *lit*, x~y, hyphen, § 3, \\S+ and ñ'], ['ċ', 'ỹ', '<em>lit']);
// Accepted: a hyphen pair between two numbers is a range, and a tie from a
// lowercase word to a number a space, as in TeX -- `3--2` and `main~1` too.
check('a range and a tie, as TeX sets them', 'pages 3--5, Problem~16', ['pages 3\u20135, Problem\u00a016']);
check('text commands: links, small caps, colour, verb, scripts, ensuremath, backslash',
  '\\url{https://x.org/a\\_b} \\href{https://y.org}{the \\textbf{site}} \\href{javascript:x}{bad} '
  + '\\textsc{Sc} \\textcolor{red}{red} {\\color{red} x} \\color{blue}y \\verb|x_1| '
  + '\\textsuperscript{th} \\textsubscript{2} \\ensuremath{\\sigma} \\textbackslash{} \\textbf\n{c}',
  ['<a href="https://x.org/a_b" target="_blank" rel="noopener">https://x.org/a_b</a>',
   '<a href="https://y.org" target="_blank" rel="noopener">the <strong>site</strong></a> bad Sc red  x y',
   '<code>x_1</code> <sup>th</sup> <sub>2</sub> <span class="math-raw">\\(\\sigma\\)</span> \\ <strong>c</strong>'],
  ['javascript', '{', '}']);
{
  const bare = window.__test.bareCommand('\\textbf{say} \\(\\alpha\\) and \\emph{\\omega}');
  bare === '\\omega'
    ? console.log('ok   the hint looks inside \\emph{...}, and not inside \\(...\\)')
    : (fails++, console.log('FAIL bareCommand said ' + JSON.stringify(bare)));
}
check('bold and italic', 'This is **bold** and *slanted*.', ['<strong>bold</strong>', '<em>slanted</em>']);
check('underscore in math not escaped',
  '$\\alpha_1$ and _real_ emphasis',
  ['$\\alpha_1$', '<em>real</em>']);
check('inline code', 'run `make split` now', ['<code>make split</code>']);
check('fenced code', 'a\n\n```\nx = 1\n```\n\nb', ['<pre><code>x = 1</code></pre>']);
// A FENCE KEEPS ITS INFO STRING. A language highlights; `path#Lx-y` numbers
// from x and adds a caption linking the source viewer; math stays plain.
{
  const src = fs.readFileSync(path.replace('web/board.js', 'tutorboard/code.py'), 'utf8')
    .split('\n').slice(39, 58).join('\n');
  const out = R('See\n\n```py board/tutorboard/code.py#L40-58\n' + src + '\n```\n\ndone.');
  const nums = (out.match(/<span class="line" data-n="(\d+)">/g) || [])
    .map(s => +/data-n="(\d+)"/.exec(s)[1]);
  const ok = out.indexOf('<figure class="code-fence">') !== -1
    && out.indexOf('<a class="code-ref" href="/source/board/tutorboard/code.py?from=40&amp;to=58"') !== -1
    && out.indexOf('<code>board/tutorboard/code.py#L40-58</code>') !== -1
    && out.indexOf('class="hljs language-py"') !== -1
    && /<span class="hljs-(keyword|string|comment|title)/.test(out)
    && JSON.stringify(nums) === JSON.stringify(Array.from({ length: 19 }, (_, i) => 40 + i))
    && out.indexOf('<p>done.</p>') !== -1;
  ok ? console.log('ok   a py fence over code.py#L40-58 is highlighted, numbered 40 to 58, with a caption link')
     : (fails++, console.log('FAIL code.py fence\n   got: ' + out.slice(0, 600)));
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
check('escaped dollar is a dollar, in an element of its own',
  'costs \\$5 today', ['<span class="tex-dollar">$</span>5'], ['\\$']);
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
    // Through the real auto-render: an escaped dollar never opens a formula,
    // and \( and \[ come out typeset, a dash-led line and all.
    el = card('costs \\$5 and \\$6 today');
    verdict('two escaped dollars are two dollars, and no formula',
      !el.querySelector('.katex') && el.textContent === 'costs $5 and $6 today', el);
    el = card('so \\(a * b * c\\) and\n\n\\[ f(x) = x^2\n- 3x + 2 \\]\n\nand \\textbf{$x_1$ bold}');
    verdict('\\(...\\), a multi-line \\[...\\] and math in \\textbf are all typeset',
      el.querySelectorAll('.katex').length === 3 && !el.querySelector('ul, em')
      && el.querySelector('strong .katex') && !/\\[(\[]/.test(el.textContent.replace(/f\(x\)/, '')), el);
    // An environment and a write-up's furniture, through the real auto-render.
    el = card('So \\begin{align*} a &= b \\label{eq:x} \\\\ &= c \\qedhere \\end{align*} and $\\lcm(a,b)$, '
              + 'and $P(\\text{$E$ before $F$})$.');
    verdict('align*, \\label, \\qedhere, \\lcm and a $ inside \\text are typeset without an error',
      el.querySelectorAll('.katex').length === 3 && !el.querySelector('.katex-error')
      && !/eq:x|\\(begin|label|qedhere|lcm)/.test(
        Array.from(el.querySelectorAll('.katex-html')).map(n => n.textContent).join(' ')), el);
    // ONE CARD'S \gdef IS ITS OWN: KaTeX writes it into the table it is
    // handed, and the board's cached table was every later card's.
    card('Define $\\gdef\\QQ{\\mathbf{Z}}$ and $\\global\\def\\sigma{s}\\sigma$.');
    el = card('Field $\\QQ$ and map $\\sigma$.');
    verdict('a card\'s \\gdef does not change a later card',
      !/Z|s/.test(Array.from(el.querySelectorAll('.katex-html')).map(n => n.textContent).join('')), el);
    el = card('$$a = b \\qed$$ and $\\eqref{eq:1}$ and $\\ref{x}$');
    verdict('\\qed, \\ref and \\eqref in math are set, not red',
      el.querySelectorAll('.katex').length === 3 && !el.querySelector('.katex-error'), el);
    {
      // A typeset with no KaTeX on the page asks for it rather than leaving the
      // card raw for good (`loadKatex`).
      const had = global.renderMathInElement, asked = [];
      const doc = global.document;
      global.renderMathInElement = undefined;
      global.document = Object.assign({}, doc, {
        head: { appendChild(tag) { asked.push(tag.src); } },
        createElement: () => ({}) });
      window.__test.typeset(dom.window.document.createElement('div'));
      window.__test.typeset(dom.window.document.createElement('div'));
      global.document = doc;
      global.renderMathInElement = had;
      asked.length === 1 && /katex/.test(asked[0])
        ? console.log('ok   typeset with KaTeX missing loads it, once')
        : (fails++, console.log('FAIL typeset with KaTeX missing asked for ' + JSON.stringify(asked)));
    }
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

// THE COURSE'S MACROS ARE IN PLACE BEFORE A CARD IS TYPESET, and a card is
// keyed by the table it was typeset against. Installed after, the first payload
// after every load set every card with the board's table alone, and the key
// kept those cards so for good.
{
  const board = fs.readFileSync(path, 'utf8');
  const body = board.slice(board.indexOf('function render(data) {'));
  const set = body.indexOf('setCourseMacros(data.macros)');
  const build = body.indexOf('items.forEach(function (item) {');
  const typed = body.indexOf('freshNodes.forEach(typeset)');
  set !== -1 && set < build && build < typed && /\+ ":x" \+ macrosGen;/.test(body)
    ? console.log('ok   render installs the course macros before it builds or typesets a card, '
                  + 'and keys each card by them')
    : (fails++, console.log('FAIL render typesets cards before the course macros are installed'));
}

// AND EVERYTHING ELSE THAT WOULD LEAVE A CARD RAW: a throw between reconcile
// and typeset (now a `finally`), a problem panel kept against an old macro table
// (its repaint key carries the table's generation), a card rewritten twice in
// one second (keyed on the exact mtime), and a board left open in the foreground
// that never asked for a new version (it asks every few minutes).
{
  const board = fs.readFileSync(path, 'utf8');
  const prob = fs.readFileSync(path.replace('board.js', 'problem.js'), 'utf8');
  const body = board.slice(board.indexOf('function render(data) {'));
  const wired = [
    ['the fresh cards are typeset in a finally after reconcile',
     /reconcile\(els\.cards, wanted\);\s*try \{[\s\S]{0,200}\} finally \{[\s\S]{0,600}freshNodes\.forEach\(typeset\)/.test(body)],
    ['the problem panel repaints on a new macro table',
     /macrosGen: function \(\) \{ return macrosGen; \}/.test(board)
     && /var blob = JSON\.stringify\(p \|\| null\) \+ "\|" \+ \(hooks\.macrosGen/.test(prob)],
    ['a card is keyed by its exact mtime', /":m" \+ item\.card\.mtime\)/.test(body)],
    ['an open board asks for a new version on a timer', /setInterval\(check, 5 \* 60 \* 1000\)/.test(board)],
  ];
  wired.forEach(([name, ok]) => ok ? console.log('ok   ' + name) : (fails++, console.log('FAIL ' + name)));
}

console.log(fails ? '\n' + fails + ' FAILURES' : '\nall markdown checks passed');
process.exit(fails ? 1 : 0);
