---
kind: correct
title: problem-12-done-now-problem-22
---
Nowhere. This page is correct from the first line to the last, and the division you dropped last time is now in line 2: $x f(x,y)/f_Y(y)$ under the integral, then $\frac{e^{-y}}{y}\cdot\frac{1}{e^{-y}}$ pulled out, leaving $\frac{1}{y}\int_0^{\infty} x e^{-x/y}\,dx$.

The right column gets $f_Y(y) = e^{-y}$ correctly. Parts is correct. The boundary term $[-y^2 e^{-x/y}]_0^{\infty}$ gives $y^2$. Your L'H\^opital step is right: $-xy$ differentiates to $-y$, $e^{x/y}$ to $\frac{1}{y}e^{x/y}$, and that limit is $0$. So $\frac{1}{y}(y^2) = y$.

Problem 12 is done. It is typeset in SOLUTION 12 with your page beside it.

---

**Exercise (Homework 3, Problem 22).**
Independent trials, each equally likely to have any of $m$ possible outcomes, are performed until the same outcome occurs $k$ consecutive times. If $N$ is the number of trials, show that
$$
E[N] = \frac{m^{k}-1}{m-1}.
$$

*Definitions / symbols used*
- Each trial takes one of $m$ values, each with probability $1/m$, independently of all other trials.
- A **run** at trial $n$ is the number of trials ending at $n$ that all show the same outcome.
- $N$ = the first trial at which the run reaches $k$.
- $N_j$ = the first trial at which the run reaches $j$, so $N_1 = 1$ and $N = N_k$.
- **Law of total expectation**: $E[X] = \sum_i E[X \mid A_i]P(A_i)$ for events $A_i$ partitioning the space.

**One thing first.** Roll a fair die, so $m = 6$. Trials $4$ and $5$ both came up $3$, so the run at trial $5$ is $2$. Now trial $6$ is rolled. After trial $6$, what values can the run take, and with what probabilities?

**Then the exercise.** Independent trials, each equally likely to give any of $m$ outcomes, run until the same outcome occurs $k$ times in a row; $N$ is the number of trials. Show $E[N] = (m^k-1)/(m-1)$.
