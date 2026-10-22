# Probability

## Where things are

- The book is Ross; chapters.tsv lists its chapters. Each is chapters/chNN-slug/: reading/ holds the excerpt and lectures/ the professor's module slides, both out of git, and notes/ the tracked write-up.
- homework/hwNN/ is one assignment, numbered by assignment rather than chapter, since assignments cut across chapters. assignment/ holds the sheet as distributed, out of git, so read it off disk; hwNN.tex holds the typeset solutions.
- exams/exam1-practice/ holds the practice exam, its key and the cheat sheet; homework/exam1-practice/ holds the owner's worked answers.
- Every unit has handwritten/ for the owner's pages. latex/ holds the shared macros.

## Now

Working hw04 (Chapter 4, Markov Chains), nine problems: 2, 3, 5, 14, 34, 40, 52, 60, 76. Exercises 2 and 3 are written up (hw04-2.png needs $2^3=8$ states; hw04-3.png has the correct eight-row matrix). The set builds.

The live problem is 5. t0002 has the right setup: $P$ with rows $(\tfrac12,\tfrac13,\tfrac16)$, $(0,\tfrac13,\tfrac23)$, $(\tfrac12,0,\tfrac12)$ -- every row sums to 1 -- plus $p=(\tfrac14,\tfrac14,\tfrac12)$, the route $pP^3$, the dimension check, and $E[X_3]=P\{X_3=1\}+2P\{X_3=2\}$. No entries computed yet.

They asked the board to do the triple product and hand them the $(1,3)$ entry ("just do this for me"). Card 0003 declined and read it as a request to shrink the step, not a mode switch. If they repeat the demand plainly, treat it as a do-mode request.

The rung still open: $P\{X_1=0\}$ as one fraction; correct value $3/8$, the row is $(3/8,\ 1/6,\ 11/24)$. Then $P^2$, then $P^3$, then $E[X_3]$.

Checked for grading: $P^2$ rows $(\tfrac13,\tfrac5{18},\tfrac7{18})$, $(\tfrac13,\tfrac19,\tfrac59)$, $(\tfrac12,\tfrac16,\tfrac13)$; then $pP^3=(59/144,\ 43/216,\ 169/432)$ and $E[X_3]=53/54$.

Groups still ahead: 14 (classes of states), 34/40/52 (long-run proportions), 60/76 (hitting probability and mean hitting time).

## Open decisions

## Done recently
