---
kind: lesson
title: p37-agreed-p40-first-door
---
**$\mathrm{Var}(X) = 233/75 \approx 3.107$. Problem 37 is done.** Your brackets now use $2.6$ and $3.4$, $E[X^2] = 908/75$, and subtracting $9$ gives the right answer. One stray symbol is left: the side line still reads $2.4 = E[X^2] - (2.4)^2$. The typeset solution says $2.6$ there. Seven of eight are now in the file.

**Problem 40.** A prisoner is in a cell with three doors. Door 1 leads to a tunnel that returns him to the cell after 2 days. Door 2 returns him after 3 days. Door 3 leads straight to freedom.
(a) He picks doors 1, 2, 3 with probabilities $0.5, 0.3, 0.2$ every time. What is the expected number of days until he is free?
(b) He picks uniformly among the doors he has not yet used. Same question.
(c) Find the variance of the number of days for (a) and for (b).

The first piece of (a) is one conditional expectation.

- $X$ = the number of days until he reaches freedom.
- $D$ = the door he picks first, with $P(D=1)=0.5$, $P(D=2)=0.3$, $P(D=3)=0.2$.
- In (a) he has no memory: after a tunnel returns him, he faces exactly the same choice as at the start.
- Conditioning on $D$: $E[X] = \sum_d E[X \mid D=d]\,P(D=d)$.

Write $E[X \mid D=1]$ in terms of $E[X]$.
