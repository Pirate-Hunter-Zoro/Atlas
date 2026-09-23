<!-- chapter: hw03 -->
Homework 3 (Ross ch. 3): problems 1, 7, 9-or-10, 12, 22, 31, 37, 40. All eight statements are transcribed in `homework/hw03/hw03.tex`.

**Done, correct, typeset — do not re-teach.** Problems 1, 7, 9-or-10, 12 and 22. Five of eight, each with their own argument in its SOLUTION region and their page in `handwritten/`. Last build: 4 pages, 0 warnings. (`board hw` misreads the label "9 or 10" as an empty region and reports 3 of 8. It is wrong; the solution is there.)

Between them they own: the chain rule for a joint pmf; marginalising to rebuild p_Y(y); conditioning on two variables at once; the continuous case end to end (marginal by integration, conditional as a quotient, expectation against the conditional, integration by parts, L'Hôpital on the boundary term); and now induction with a recursion solved for its own unknown.

**Problem 22, two errors, both fixed.** First the miss branch: the run restarted at 0 rather than at 1, so a failed extension cost nothing. Second, pure algebra — clearing to m(m-1) they wrote m(mⁿ-1) where the cancelling (m-1) belongs, which propagated to a final line holding only at m=2. Each named once; their redo is clean and I checked the recursion independently.

**The error pattern.** Every mistake is one defective symbol, not confusion: a missing conditioning denominator on Problems 1 and 12, a missing factor here. Name the symbol and stop.

**Next: Problem 31**, posed on card 0014, unanswered. Expected length of the first and second runs in a Bernoulli(p) sequence. Open ask is a p=1/3 warm-up: P(L₁=3) and E[L₁] given a leading 1. It targets the two ideas the problem needs — a run's length given its symbol is geometric, and the second run's symbol is forced opposite, which is why E[L₂]=2 with no p in it.

**How this student works.** They skip the warm-up and send a full proof instead, five times now. Do not chase the skipped sub-question; mark what arrived. They sometimes write "where did I mess up?" when nothing is wrong; answer that first and say plainly when the answer is nowhere.

## The textbook changed under the course, on 22 September 2026

`textbook/ProbTextbook.pdf` is Ross, eleventh edition, 769 pages, and it replaced the
tenth. `chapters.tsv` is re-indexed against it — offset 8, so printed page 1 is PDF page
9 — and all eleven `chapters/chNN-*/reading/chNN.pdf` excerpts are re-cut from it.

**What this costs, and it has already cost it once.** Exercise numbers differ between the
editions. Homework 2's 61 and 76 were transcribed from the tenth and worked in full before
anyone noticed; the eleventh's 61 is about records in a sequence of iid continuous
variables and its 76 is Chebyshev to the weak law. The tenth-edition work is complete and
kept in `homework/hw02/superseded-edition-10.tex`, with its scans under
`homework/hw02/handwritten/superseded-edition-10/`. `hw02.tex` now carries the eleventh's
statements with empty solution regions.

Check any exercise number against `textbook/ProbTextbook.pdf` before teaching it. The
assignment sheet in each set's `assignment/` directory is the authority over any number
written down anywhere else.
