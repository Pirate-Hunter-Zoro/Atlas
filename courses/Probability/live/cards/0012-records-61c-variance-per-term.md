---
kind: question
title: records-61c-variance-per-term
---
You don't simplify it, and you don't have to. Squaring the sum is the expensive road, and there is a free one sitting in the list on the last card.

Expanding $\left(\sum_{i=1}^n I_i\right)^2$ gives the double sum $\sum_{i=1}^n \sum_{j=1}^n I_i I_j$ -- $n^2$ terms, and you would need $\mathbb{E}[I_i I_j]$ for every pair $i \neq j$. That is a real calculation, and it only collapses once you use independence.

So use independence at the start instead. For independent random variables, the variance of the sum IS the sum of the variances. No squaring, no cross terms:
$$\operatorname{Var}(N) = \sum_{i=1}^{n} \operatorname{Var}(I_i).$$

Your two lines are right, and they still matter. $\mathbb{E}[X^2] - (\mathbb{E}[X])^2$ is the definition you need -- you just apply it to one $I_i$ at a time, not to $N$ as a whole. And $\mathbb{E}[N] = \sum 1/i$ is correct; it is simply not needed on this route.

**Problem 61(c).** $X_1, X_2, \ldots$ are independent, identically distributed, continuous. A record occurs at time $n$ if $X_n > \max(X_1,\ldots,X_{n-1})$. Let $N$ be the number of records by time $n$. Show that
$$\operatorname{Var}(N) = \sum_{i=1}^{n} \frac{i-1}{i^{2}}.$$

Everything this uses:

- $I_i$: equals $1$ if a record occurs at time $i$, else $0$. So $N = \sum_{i=1}^n I_i$.
- $P\{\text{record at time } i\} = 1/i$, proved in part (a).
- $\mathbb{E}[I_i] = 1/i$, proved in part (b).
- $\operatorname{Var}(Y) = \mathbb{E}[Y^2] - (\mathbb{E}[Y])^2$.
- Independent summands: $\operatorname{Var}\left(\sum_i I_i\right) = \sum_i \operatorname{Var}(I_i)$. The $I_i$ are independent; take that as given.
- $I_i$ takes only the values $0$ and $1$. Note what squaring does to each of those two numbers.

One term, one $i$, fixed.

What is $\mathbb{E}[I_i^{2}]$, and hence what is $\operatorname{Var}(I_i)$?
