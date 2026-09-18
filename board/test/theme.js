// The dark theme has to reach the whole window, not just the part with content.
//
// This is here because of a screenshot. An iPad showed the board in dark mode
// with a cream panel filling the bottom 40% of the screen, and it looked for all
// the world like a broken writing surface. It was the page itself:
//
//   :root                    { --paper: #fbfaf7 }      <- light
//   body[data-mode="dark"]   { --paper: #16171a }      <- dark, scoped to BODY
//   html, body               { background: var(--paper) }
//
// The viewport's background is taken from <html>, and only falls through to
// <body> when <html> paints none of its own. So <html> painted `var(--paper)`
// resolved against `:root` -- always the light cream, whatever theme was on --
// and <body>'s dark box stopped wherever the content did. An empty board is
// almost all "wherever the content did".
//
// The rule this guards: if a sheet defines its dark palette on a `body` selector,
// then `html` must not paint a background of its own.

const fs = require('fs');
const path = require('path');

const WEB = path.join(__dirname, '..', 'web');
const errors = [];
const ok = (m) => console.log('ok   ' + m);
const fail = (m) => { errors.push(m); console.log('FAIL ' + m); };

// Every top-level rule as [selector, declarations], @media blocks removed.
function rules(css) {
  const flat = css.replace(/@media[^{]*\{(?:[^{}]*\{[^{}]*\}\s*)*\}/g, '')
                  .replace(/\/\*[\s\S]*?\*\//g, '');
  const out = [];
  const re = /([^{}]+)\{([^{}]*)\}/g;
  let m;
  while ((m = re.exec(flat)) !== null) out.push([m[1].trim(), m[2]]);
  return out;
}

function paintsBackground(body) {
  // `background: none` and `background-color: transparent` paint nothing, which
  // is the whole point of the fix; anything else is a real paint.
  const m = /(?:^|;)\s*background(?:-color)?\s*:\s*([^;]+)/.exec(body);
  if (!m) return false;
  return !/^\s*(none|transparent|initial|unset)\s*$/i.test(m[1]);
}

for (const sheet of ['board.css', 'home.css', 'slate.css']) {
  const css = fs.readFileSync(path.join(WEB, sheet), 'utf8');
  const all = rules(css);

  const darkOnBody = all.some(([sel]) => /body\s*\[data-mode/.test(sel));
  if (!darkOnBody) {
    ok(sheet + ': one palette, no theme switch to get wrong');
    continue;
  }
  ok(sheet + ': the dark palette is scoped to the body');

  const htmlPaints = all.filter(([sel, body]) =>
    sel.split(',').some((s) => /(^|\s)html\b/.test(s.trim()) && !/:has|\bbody\b/.test(s))
    && paintsBackground(body));

  if (htmlPaints.length === 0) {
    ok(sheet + ': html paints nothing, so the body colour reaches the viewport');
  } else {
    fail(sheet + ': html paints a background (' + htmlPaints[0][0] + ') while the'
         + ' dark tokens are body-scoped — the bottom of a short page goes light');
  }

  const bodyPaints = all.some(([sel, body]) =>
    sel.split(',').some((s) => /^body$/.test(s.trim())) && paintsBackground(body));
  bodyPaints
    ? ok(sheet + ': the body paints one, so there is something to propagate')
    : fail(sheet + ': nothing paints a background at all');

  // A body only as tall as its content leaves the rest of the viewport to the
  // canvas. Propagation covers it, but the body must still have a colour to give.
  const tall = all.some(([sel, body]) =>
    sel.split(',').some((s) => /^body$/.test(s.trim())) && /min-height/.test(body));
  tall
    ? ok(sheet + ': and the body is at least a screen tall')
    : fail(sheet + ': the body can be shorter than the screen with nothing behind it');
}

// The board is the page this actually happened on, so pin the specific shape.
const board = fs.readFileSync(path.join(WEB, 'board.css'), 'utf8');
/--paper\s*:/.test(board) && /body\[data-mode="dark"\][^{]*\{[^}]*--paper/.test(board)
  ? ok('board.css still switches --paper by theme')
  : fail('board.css no longer defines a dark --paper — this test is now lying');

// A VERDICT HAS A COLOUR, AND THE COLOUR COSTS NO HEIGHT.
//
// Green for right, red for not, amber for a question put back — asked for as
// "a little more fun/interactive/dopamine reward-esque", and true of a sitting
// over a repository as much as one over a proof.
//
// The constraint that is easy to break later: annotations are anchored as
// fractions of the card they were drawn on, so a panel that pads a card moves
// ink that was put down weeks ago. The tint is a background and a spread
// shadow, and neither is allowed to grow into vertical geometry.
{
  const all = rules(board);
  const decl = (sel) => (all.find(([s]) =>
    s.split(',').some((one) => one.trim() === sel)) || [null, ''])[1];

  const wants = { correct: '--good', wrong: '--bad', question: '--ask' };
  for (const kind of Object.keys(wants)) {
    const d = decl('.card[data-kind="' + kind + '"]');
    d.includes('--accent') && d.includes(wants[kind])
      ? ok('a ' + kind + ' card carries ' + wants[kind])
      : fail('a ' + kind + ' card no longer carries its own colour');
  }

  const panel = all.find(([sel, body]) =>
    /\.card\[data-kind="correct"\]\s+\.body/.test(sel) && paintsBackground(body));
  if (!panel) {
    fail('a verdict card is no longer washed in its own colour — the board is '
         + 'back to reading the same whatever it says');
  } else {
    ok('and the card is washed in it, not merely ruled down one side');
    ['wrong', 'question'].forEach((kind) => {
      new RegExp('\\.card\\[data-kind="' + kind + '"\\]\\s+\\.body').test(panel[0])
        ? ok('and a ' + kind + ' card is washed in the same way')
        : fail('only some kinds are washed, which reads as a bug rather than a '
               + 'verdict');
    });
    /(^|;)\s*(padding|margin)(-top|-bottom)?\s*:[^;]*(rem|px|em)\s+/.test(panel[1])
    || /(^|;)\s*(padding|margin)-(top|bottom)\s*:/.test(panel[1])
      ? fail('the wash pads the card vertically, which moves every annotation '
             + 'ever drawn on one: the tint must be paint, not layout')
      : ok('and it costs no height, so ink stays on the words it was drawn over');
  }

  // KEYED ON THE VERDICT, NOT ON THE KIND -- which is the half the card used to
  // get wrong. The kind is what the tutor called the card; the verdict is what
  // it says about work that was handed in, and those agree only for `correct`
  // and `wrong`. `question` keeps its own mark because being asked something is
  // a property of the card rather than a verdict on anything.
  const marks = ['correct', 'wrong', 'open'].every((v) =>
    decl('.card[data-verdict="' + v + '"] .kind::before').includes('content'))
    && decl('.card[data-kind="question"] .kind::before').includes('content');
  marks
    ? ok('and each verdict chip carries its own mark')
    : fail('a verdict is colour alone, which is nothing to somebody who cannot '
           + 'tell the two of them apart');

  // AND THE AMBER CASE IS PAINTED FROM THE VERDICT, so the card and the answer
  // a finger's width below it say the same thing. Asked for as "if the user asks
  // a question, or we're not really in a 'right or wrong' scenario, then the
  // response should be highlighted with a yellow kind of band" -- and the card
  // took its band from its kind, so a reply that was neither right nor wrong
  // went grey while the answer went amber.
  const verdicts = { correct: '--good', wrong: '--bad', open: '--ask' };
  for (const v of Object.keys(verdicts)) {
    const d = decl('.card[data-verdict="' + v + '"]');
    d.includes('--accent') && d.includes(verdicts[v])
      ? ok('a card the transcript says is ' + v + ' carries ' + verdicts[v])
      : fail('a ' + v + ' verdict no longer paints the card');
  }
  const washed = all.find(([sel, body]) =>
    /\.card\[data-verdict\]\s+\.body/.test(sel) && paintsBackground(body));
  washed
    ? ok('and a card carrying any verdict is washed in it, which is what makes '
         + 'the amber case exist at all')
    : fail('only the named kinds are washed, so a lesson card replying to work '
           + 'that was handed in still has no band');

  // HOW MANY RIGHT IN A ROW, AS TEXT. The run is the reward; an entrance is not.
  const streak = decl('.card[data-streak] .streak');
  streak && streak.includes('--good')
    ? ok('and a run of right answers is a chip in the same green, which survives '
         + 'everything an animation does not')
    : fail('nothing marks a streak, so a correct answer is one tick and no more');

  // `.card` is declared in several places; the wash may live in any of them.
  const light = all.some(([sel, body]) =>
    sel.split(',').some((one) => one.trim() === '.card') && body.includes('--wash'));
  const dark = all.find(([sel, body]) =>
    /body\[data-mode="dark"\]\s*\.card/.test(sel) && body.includes('--wash'));
  light && dark
    ? ok('and the wash is mixed for both themes, not just the light one')
    : fail('the wash is defined once, so one theme gets a tint nobody can see');
}

console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                          : '\nthe theme reaches the whole window');
process.exit(errors.length ? 1 : 0);
