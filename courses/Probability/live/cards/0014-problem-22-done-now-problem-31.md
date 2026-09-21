---
kind: correct
title: problem-22-done-now-problem-31
---
Correct, end to end — Problem 22 is done. The factor of $m-1$ is back where it belongs, and now the chain closes with nothing left over.

Two lines of yours are worth naming. First, $1-\frac{m-1}{m}=\frac{1}{m}$, which clears the denominator instead of making a new one. Second, the grouping $(m^n-1)+(m-1)(m^n-1)=m(m^n-1)$, so the numerator is $m^{n+1}-m+(m-1)=m^{n+1}-1$. That is the $k=n+1$ statement, and your base case $k=1$ giving one trial is right. I solved your recursion independently and it agrees for every $m$ and $n$ I checked.

**Exercise (Homework 3, Problem 31).**
Each element in a sequence of binary data is either $1$ with probability $p$ or $0$ with probability $1-p$. A maximal subsequence of consecutive values having identical outcomes is called a **run**. For instance, if the outcome sequence is $1,1,0,1,1,1,0$, the first run is of length $2$, the second is of length $1$, and the third is of length $3$.

(a) Find the expected length of the first run.
(b) Find the expected length of the second run.

*Definitions / symbols used*
- The elements are independent, and every element is $1$ with probability $p$.
- A **run** is maximal: it ends at the first element that differs from the one before it.
- The first run starts at element $1$, so its symbol is whatever element $1$ is.
- The second run starts at the first element that differs from element $1$.
- $L_1$, $L_2$ = the lengths of the first and second runs.
- **Geometric**: if each independent attempt succeeds with probability $q$, the number of attempts up to and including the first success has expectation $1/q$.
- **Law of total expectation**: $E[X]=\sum_i E[X\mid A_i]P(A_i)$ over a partition $\{A_i\}$.

**The one thing.** Take $p=\frac{1}{3}$, and condition on element $1$ being a $1$. Give me two numbers: $P(L_1=3)$ under that conditioning, and $E[L_1]$ under that conditioning.

**Then the exercise.** Elements independent, each $1$ with probability $p$ and $0$ with probability $1-p$; a run is a maximal block of identical consecutive values. Find $E[L_1]$, the expected length of the first run, and $E[L_2]$, the expected length of the second run.
