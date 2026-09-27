---
kind: lesson
title: edition-check
---
Yes: all eight Homework 3 problems are the same in the 11th edition. Nothing you have done needs redoing.

I checked each one (1, 7, 9, 10, 12, 22, 31, 37, 40) against the Chapter 3 exercises of the new book. The number and the wording match, down to the Poisson means $2.6$, $3$, $3.4$ in Problem 37.

Homework 2 is different, and it already has a fix. Its problems 61 and 76 were worked from the 10th edition and are different exercises in the 11th. Your 10th-edition work is kept in `homework/hw02/superseded-edition-10.tex` (the old write-up, set aside). The main `hw02.tex` now holds the 11th-edition statements, still unsolved.

Back to Problem 31, where we were.

**Problem 31.** Each element in a sequence of binary data is $1$ with probability $p$ or $0$ with probability $1-p$, independently. A *run* is a maximal stretch of consecutive equal values. In $1,1,0,1,1,1,0$ the runs have lengths $2$, $1$, $3$.
(a) Find the expected length of the first run.
(b) Find the expected length of the second run.

The warm-up: $p = 1/3$, and the sequence opens with a $1$.

- $L_1$ = the length of the first run.
- Opening with a $1$ means the first run is made of $1$s, so it ends at the first $0$.
- Each later element is $1$ with probability $1/3$ and $0$ with probability $2/3$, independent of the rest.

With $p = 1/3$, and given the sequence opens with a $1$: what is $P(L_1 = 3)$, and what is $E[L_1]$?
