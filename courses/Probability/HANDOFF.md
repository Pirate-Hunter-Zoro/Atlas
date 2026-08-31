# HANDOFF

**Homework 1**, `homework/hw01/hw01.tex`, due 2 September 2026.
Assigned: instructor's own, then Ross ch.1 ex. 8, 10, 12, 39, 41.

## The sheet is finished — 6 of 6 written up

Every solution region is filled with his own argument, transcribed unimproved,
in the sheet's order. Handwriting is filed alongside in
`homework/hw01/handwritten/`. **Nothing on this sheet is owed.**

| problem | answer | what he owns and must not be re-taught |
|---|---|---|
| instructor's | — | inclusion–exclusion from the axioms; taking $P$ of a set identity |
| Ross 8 | — | Bonferroni; $P(A)\le 1$ |
| Ross 10 | — | Boole; the disjointification $F_i=E_iE_1^c\cdots E_{i-1}^c$, $\bigcup E_i\subseteq\bigcup F_i$ by induction, monotonicity |
| Ross 12 | $\dfrac{P(E)}{P(E)+P(F)}$ | countable additivity with a geometric sum; the sample space of a *repeat until* experiment as finite sequences |
| Ross 39 | $1/2$ | Bayes **and** the law of total probability, produced unprompted |
| Ross 41 | (a) $1/3$, (b) $16/17$ | conditioning twice; using (a)'s posterior as (b)'s prior |

## The one thing still outstanding — the build

The repository is **committed and pushed**; the working tree is clean. Only the
PDF is behind.

`pdflatex` is present and found by `board doctor` at `/Library/TeX/texbin/`, and
the last real LaTeX error in this document was zero. What blocks the build is
the harness, not LaTeX and not Tutor-Board: **a headless session is not
permitted to execute the binary**, and it is equally not permitted to edit
`.claude/settings.local.json` to allow it, so both routes need a human approval
that nobody is present to give. `board hw build` therefore fails writing no log,
and `board push` pushes the source with the PDF behind it. The PDF in
`homework/hw01/build/` is from 12:11 and predates Solutions 8, 10, 12, 39 and 41.

**First action of the next session: build it.** Interactively this is one
approval prompt, tapped once. Failing that, `pdflatex` wants an entry in the
permissions allow list in `.claude/settings.local.json`, beside the `pdftotext`
entries already there. He was told all of this on card 0030 rather than left to
find it.

## Tutor-Board — asked for, not done

He asked (18:32) for Tutor-Board to be changed so a tutor can compile once a set
is finished, and for both repositories to be shipped. Probability shipped.
**Tutor-Board was not touched**: it lives at `/Users/mikeyferguson/Learning/
Tutor-Board`, outside this session's working directory, so it could not be read,
edited or pushed. It needs a session opened with that directory in scope.

Two things to carry into that session. No Tutor-Board change can grant a
sandboxed process a permission the harness withheld — it already detects the
compiler correctly and correctly refuses to fake a PDF, so the request as stated
does not fix the symptom. What *is* worth doing there, and was promised on card
0030, is making `board hw build` report the reason for a failure instead of
printing the single word `FAILED`, which is what cost this session an afternoon
of guessing.

## What actually went wrong, and what did not

**Conditioning was never the problem.** It was taught once on card 0017 —
restrict to $B$, renormalise — with one die roll as the example. He skipped the
hand-check, and was right to: rev 1 of Ross 39 produced Bayes with total
probability underneath it before either had been named to him.

**One genuine probability error all session,** on 41(a): he wrote $P(BB\mid bb$
sibling, parents $Bb,Bb)$ and answered $1/4$, because *the rat is black* never
reached his conditioning bar. He uses the hypotheses that do work inside a
calculation and drops the one that merely restricts the sample space. Reading
his own conditioning bar back to him fixed it in one card, in two minutes.

**Everything else was arithmetic or copying** — $215$ for $225$; $0.75$ against
$0.7$; a stale line left above one he had just fixed; $0.7\cdot\frac49$ written
as $\frac{28}{45}$, i.e. $\frac{28}{90}$ with only the denominator halved. Five
revisions of Ross 39 were spent on these and none on the probability. Do not
mistake that history for shaky understanding.

## How he works

- **Skips checks he has**, and the skips have been accurate. Take them at face
  value.
- **Says "I am stuck" plainly.** Go back a step and teach it; never mark it
  wrong.
- **Invents his own notation and route.** Check it on its terms and transcribe
  it unimproved.
- **Does exactly the one thing named and leaves the rest**, so state every
  missing half explicitly and re-read the whole page each revision rather than
  only the break.
- **When a hint fails, change mode rather than rephrase.** Two arithmetic hints
  on $0.7\cdot\frac49$ went nowhere; *"$28/45>4/9$, yet multiplying by $0.7$
  must shrink"* fixed it immediately. Locating by size, or by pointing at a line
  he had already written, has worked every time an algebraic hint has not.

## Where to go next

The sheet is done, so the next sitting is not homework. Ross ch.1 is spent as
far as this assignment goes; conditional probability got one card and two
problems and has never been taught properly — independence, the multiplication
rule for several events, and the law of total probability as a statement rather
than a move he improvised. That is the natural next lecture, and he has already
half-derived it, which makes it cheap.
