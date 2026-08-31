# HANDOFF

**Homework 1 is finished and compiled.** All six problems written up in
`homework/hw01/hw01.tex`, handwriting filed, PDF built at
`homework/hw01/build/hw01.pdf` — 4 pages, 0 warnings, 0 errors, no placeholder
regions left. Problems: Ross 1, 8, 10, 12, 39, 41.

Answers: Ross 12 → P(E)/(P(E)+P(F)); Ross 39 → 1/2; Ross 41 → 1/3 and 16/17.

## What he owns — do not re-teach

Inclusion–exclusion, Bonferroni, Boole with the disjointification
F_i = E_i E_1^c⋯E_{i-1}^c, monotonicity, countable additivity with a geometric
sum, the sample space of a *repeat until* experiment as finite sequences. On 39
he produced Bayes **and** the law of total probability unprompted, before either
was named to him. On 41 he conditioned twice and used (a)'s posterior as (b)'s
prior himself.

## What he got wrong

One probability error all session, on 41(a): he wrote P(BB | bb sibling, parents
Bb,Bb), answered 1/4, and never put *the rat is black* behind the bar. He uses
hypotheses that do work inside a calculation and drops the one that merely
restricts the sample space. Reading his own conditioning bar back to him fixed
it in one card.

Everything else was arithmetic or copying — 215 for 225, 0.75 against 0.7, a
stale line left above one he had just fixed, 0.7·(4/9) as 28/45. Five revisions
of 39 went on these and none on the probability. Do not mistake that for shaky
understanding.

## Next: conditional probability, properly

It got one card and two problems and he improvised the rest. Teach independence,
the multiplication rule for several events, and the law of total probability as
a statement rather than a move — he has half-derived it, so it is cheap.

## How he works

Skips checks he has, accurately. Says "I am stuck" plainly — go back a step,
never mark it wrong. Does exactly the one thing named and leaves the rest, so
state every missing half and re-read the whole page each revision. When a hint
fails, change mode: *28/45 > 4/9, yet ×0.7 must shrink* landed where two
algebraic hints had not.

He also diagnoses tooling accurately and acts on it — he read the sandbox
refusal correctly and shipped the permissions edit himself.

## Build permissions — resolved, do not re-report as blocked

`.claude/settings.local.json` now allows `pdflatex` and the rest of the TeX
binaries alongside `board` and `scripts/build.sh`. `board hw build` runs headless
with no approval prompt. The previous handoff's "cannot compile" note is stale.

## Still open

Tutor-Board (`~/Learning/Tutor-Board`) is outside this repository's scope and was
never touched. `board hw build` prints the bare word `FAILED` on error while
knowing the reason; he asked for it to say why. That needs a session opened with
that directory in scope.

Earlier pushes were rejected once (remote ahead); the tree is at `8771c6b` plus
this session's card, turns and PDF. If a push is refused, integrate the remote
first — do not force it.
