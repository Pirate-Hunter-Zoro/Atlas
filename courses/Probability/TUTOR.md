# Probability

## Where things are

- The book is Ross; chapters.tsv lists its chapters. Each is chapters/chNN-slug/: reading/ holds the excerpt and lectures/ the professor's module slides, both out of git, and notes/ the tracked write-up.
- homework/hwNN/ is one assignment, numbered by assignment rather than chapter, since assignments cut across chapters. assignment/ holds the sheet as distributed, out of git, so read it off disk; hwNN.tex holds the typeset solutions.
- exams/exam1-practice/ holds the practice exam, its key and the cheat sheet; homework/exam1-practice/ holds the owner's worked answers.
- Every unit has handwritten/ for the owner's pages. latex/ holds the shared macros.

## Now

hw04, nine problems: 2, 3, 5, 14, 34, 40 and 52 are closed and written up; 60 and 76 remain. Problem 14's region carries the four transition diagrams (TikZ, credited to DeepSeek) beside its classifications. The PDF builds, 3 pdflatex runs.

Standing instruction (2026-10-24): they will not do algebra. Give every arithmetic step, simplification, matrix product or numeric value exactly and directly, in the card, without asking them for it. Ask only for reasoning: which object, which argument, which symmetry.

Problem 52 closed (card 0021; page t0002-r15 filed as handwritten/hw04-52.png). Their page: states are the pickup zone, $P=\begin{pmatrix}.6&.4\\.3&.7\end{pmatrix}$; profit table $AA\to6$, $BB\to8$, $AB\to12$, $BA\to12$; stationarity $[p_A\ p_B]P=[p_A\ p_B]$; $E=6p(AA)+8p(BB)+12p(AB)+12p(BA)$, written out as $6p_A(0.6)+8p_B(0.7)+12p_A(0.4)+12p_B(0.3)$. They asked me to solve it and then move on. $\pi=(3/7,4/7)$, $E=62/7\approx8.857$, both in region 52.

Problem 60 posed (card 0021), region 60 in hw04.tex. $P$ rows $.4\ .3\ .2\ .1$ / $.2\ .2\ .2\ .4$ / $.25\ .25\ .5\ 0$ / $.2\ .1\ .4\ .3$; $X_0=1$. Card 0021 introduced $u_i$, the chance 3 is entered before 4 starting at $i$, and asks for the equation row 1 gives for $u_1$ once $u_3,u_4$ are set. Answer: $u_3=1$, $u_4=0$, then $u_1=.4u_1+.3u_2+.2$ and $u_2=.2u_1+.2u_2+.2$; solution $u_1=3/5$. Part (b) is $g_i=1+\sum_jP_{ij}g_j$ with $g_3=g_4=0$. Those values are mine when they ask.

Then 76, statement from `board textbook find "Ch 4 #76"`; pose with `board writeup pose 76` first.

Do not reopen 5, 14, 34, 40.

## Open decisions

## Done recently

Problem 52 transcribed into homework/hw04/hw04.tex with their profit table, stationarity equation and expectation sum, plus the computed $\pi=(3/7,4/7)$ and $E=62/7$; page t0002-r15 filed as handwritten/hw04-52.png; PDF rebuilt twice at card 0021. Problem 60 posed with `board writeup pose 60`, statement written and empty region added. Exercise 34 transcribed in full earlier at card 0017; exercise 14 from t0002-r5.
