# Galois Theory

## Where things are

- The book is A Course in Galois Theory; chapters.tsv lists its chapters. Each is chapters/chNN-slug/ with notes/, homework/ and handwritten/; reading/ (the excerpt) and textbook/ stay out of git.
- latex/coursemacros.sty is the shared preamble.
- Worksheets live in homework/<sheet>/ with the typeset .tex and handwritten/ beside it.

## Now

Chapter 7, Splitting fields. Problem 13. Parts (a) and (b) are written up. 13(c) -- list the subgroups of $(\ZZ/13\ZZ)^\times$ with their fixed-field degrees -- was SKIPPED at t0136 (card 0035 held the full restatement), after the hand-check in 0034 was also skipped; per the skip rule it is not re-asked and stays unwritten.

13(d): with $H\le G$ of index $d$ and $\eta_H=\sum_{a\in H}\zeta^a$, show $K_d=\QQ(\eta_H)$. At t0137 they did not compute the period; instead they sketched the plan and asked on the page "Is this plan a good direction?" Card 0037 answers yes -- the plan is $\eta_H\in K_d$ (H fixes the period) then a degree comparison, keeping the nested-over-$\QQ$ diagram -- and re-poses the one concrete step: for $p=13$, $H=\{1,3,4,9,10,12\}$, compute $\sigma_3(\eta_H)$ and say in one line why it returns $\eta_H$. Awaiting their reply. Arc to hold: $\eta_H\in K_d$, then $[\QQ(\eta_H):\QQ]=d$ via the $d$ distinct coset periods as conjugates, forcing equality.

## Open decisions

## Done recently

- The automorphisms and splitting-fields worksheet, problems 7-12: Aut(ℚ(ζₙ)/ℚ) inside (ℤ/nℤ)ˣ, Φₚ irreducible, the whole machine on x⁴+1, the splitting field of x³−2, and the finite-field pair.
- Problem 13(a) and 13(b) transcribed into ch07-homework.tex (SOLUTION 13 region); pages ch07-13a.png, ch07-13b.png.
