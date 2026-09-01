# HANDOFF

**Homework 1 is done, compiled and pushed.** Ross 1, 8, 10, 12, 39, 41 in
`homework/hw01/hw01.tex`; PDF 4 pages, 0 warnings; handwriting filed. Answers:
12 → P(E)/(P(E)+P(F)); 39 → 1/2; 41 → 1/3 and 16/17. Nothing outstanding.

## What he owns — do not re-teach

Inclusion–exclusion, Bonferroni, Boole via the disjointification
F_i = E_i E_1^c⋯E_{i-1}^c, monotonicity, countable additivity with a geometric
sum, the sample space of a *repeat until* experiment. On 39 he produced Bayes
**and** the law of total probability before either was named to him; on 41 he
conditioned twice and used (a)'s posterior as (b)'s prior himself.

## The one real error

On 41(a) he wrote P(BB | bb sibling, parents Bb,Bb) and answered 1/4, never
putting *the rat is black* behind the bar. The misunderstanding: he keeps
hypotheses that do arithmetic work and drops ones that merely restrict the
sample space. Reading his own conditioning bar back to him fixed it in one card.
Everything else that went wrong was arithmetic or copying — do not mistake five
revisions of 39 for shaky understanding.

## Next: conditional probability, properly

Independence, the multiplication rule for several events, and the law of total
probability as a statement rather than a move. It is the only machinery he used
this session without ever being taught it, and he has half-derived it already,
so it is cheap. Card 0033 asked whether to start; he left before answering.

## Tooling — settled, do not re-diagnose

`scripts/save-and-push.sh` pushed without ever fetching, so one commit from
another machine made every push permanently non-fast-forward. It now merges
first and auto-resolves collisions only under `build/`. Pushed at `7f2a1ed`.
He chose to keep build output tracked. `.claude/settings.local.json` is
untracked and per-machine: check it for `pdflatex`, never assume.

## How he works

Skips checks he genuinely has. Says "I am stuck" plainly — go back a step, never
mark it wrong. Does exactly the one thing named and leaves the rest, so state
every missing half. When a hint fails, change mode entirely. He diagnoses tooling
himself and is worth listening to — but check his stated mechanism, which was
wrong twice while his instinct was right.
