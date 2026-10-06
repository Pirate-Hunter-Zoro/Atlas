---
kind: lesson
title: p31-warmup-again
---
Problem 31 is up: five of the eight on Homework 3 are done and typeset, and this is the sixth.

**Problem 31.** Each element in a sequence of binary data is $1$ with probability $p$ or $0$ with probability $1-p$, independently. A *run* is a maximal stretch of consecutive equal values. In $1,1,0,1,1,1,0$ the runs have lengths $2$, $1$, $3$.
(a) Find the expected length of the first run.
(b) Find the expected length of the second run.

One small case first, with numbers: $p = 1/3$, and the sequence opens with a $1$.

- $L_1$ = the length of the first run.
- Opening with a $1$ means the first run is made of $1$s, so it ends at the first $0$.
- Each later element is $1$ with probability $1/3$ and $0$ with probability $2/3$, independent of the rest.

With $p = 1/3$, and given the sequence opens with a $1$: what is $P(L_1 = 3)$, and what is $E[L_1]$?
