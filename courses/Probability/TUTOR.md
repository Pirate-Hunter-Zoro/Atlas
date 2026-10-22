# Probability

## Where things are

- The book is Ross; chapters.tsv lists its chapters. Each is chapters/chNN-slug/: reading/ holds the excerpt and lectures/ the professor's module slides, both out of git, and notes/ the tracked write-up.
- homework/hwNN/ is one assignment, numbered by assignment rather than chapter, since assignments cut across chapters. assignment/ holds the sheet as distributed, out of git, so read it off disk; hwNN.tex holds the typeset solutions.
- exams/exam1-practice/ holds the practice exam, its key and the cheat sheet; homework/exam1-practice/ holds the owner's worked answers.
- Every unit has handwritten/ for the owner's pages. latex/ holds the shared macros.

## Now

Working hw04 (Chapter 4, Markov Chains), nine problems: 2, 3, 5, 14, 34, 40, 52, 60, 76. Problems 2, 3 and 5 are written up and the PDF builds: hw04-2.png needs $2^3=8$ states, hw04-3.png has the correct eight-row matrix, hw04-5.png has the setup.

Problem 5 is closed. They switched the session to do mode and asked for the triple product, so SOLUTION 5 was filled: $P^2$ rows $(\tfrac13,\tfrac5{18},\tfrac7{18})$, $(\tfrac13,\tfrac19,\tfrac59)$, $(\tfrac12,\tfrac16,\tfrac13)$; $pP^3=(59/144,\ 43/216,\ 169/432)$; $E[X_3]=53/54$. Card 0004 reports it and says the $(1,3)$ entry is $169/432$. They said they would switch back to teach mode.

Next: problem 14, the classes of states. Then 34, 40, 52 (long-run proportions), then 60, 76 (hitting probability and mean hitting time).

## Open decisions

## Done recently

Problem 5 of hw04 written into homework/hw04/hw04.tex in do mode, the page filed as handwritten/hw04-5.png, PDF built. Committed as 15d1b202.
