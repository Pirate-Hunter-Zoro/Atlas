---
kind: lesson
title: p31-closed-forms
---
Both probabilities are now right. There is no question on the page, so straight to the working.

$$P(L_1 = i) = (1-p)^i\,p + p^i(1-p), \qquad P(L_2 = i) = p^2(1-p)^{i-1} + (1-p)^2 p^{i-1}.$$

I checked the second one independently. Summing $p^j(1-p)^i p$ over every length $j \ge 1$ of a first run of $1$s gives exactly your $p^2(1-p)^{i-1}$. Both lines sum to $1$ over $i$, as a distribution must.

One stale symbol: your boxed sum for the first run still reads $\sum i\big((1-p)^i + p^i\big)$. The line beneath it is the corrected one. Use that.

What remains is turning the two sums into closed forms. The problem asks for an expected length, and an infinite sum is not yet an answer.

**Problem 31.** Each element in a sequence of binary data is $1$ with probability $p$ or $0$ with probability $1-p$, independently. A *run* is a maximal stretch of consecutive equal values. In $1,1,0,1,1,1,0$ the runs have lengths $2$, $1$, $3$.
(a) Find the expected length of the first run.
(b) Find the expected length of the second run.

- $L_1$, $L_2$ = the lengths of the first and second runs.
- Your distributions: $P(L_1 = i) = (1-p)^i p + p^i(1-p)$ and $P(L_2 = i) = p^2(1-p)^{i-1} + (1-p)^2 p^{i-1}$, for $i \ge 1$.
- Geometric mean: for $0 < q < 1$, $\displaystyle\sum_{i=1}^{\infty} i\,q^{i-1}(1-q) = \frac{1}{1-q}$.
- The trick: pull constants out of each sum until what is left is exactly that geometric sum.

Evaluate both sums in closed form: what are $E[L_1]$ and $E[L_2]$ as functions of $p$?
