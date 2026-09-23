---
kind: question
title: records-61-open
---
Homework 2 is not finished: problems 61 and 76 still have empty solution regions and no filed page, so this sitting starts at 61. The other seven are typeset.

**Problem 61** (Edition 11, Chapter 2). Let $X_1, X_2, \ldots$ be independent, identically distributed continuous random variables. A *record* occurs at time $n$ if $X_n > \max(X_1, \ldots, X_{n-1})$. Show that

(a) $P\{\text{a record occurs at time } n\} = 1/n$;

(b) $\E[\text{number of records by time } n] = \sum_{i=1}^{n} 1/i$;

(c) $\Var(\text{number of records by time } n) = \sum_{i=1}^{n} (i-1)/i^{2}$;

(d) with $N = \min\{n : n > 1 \text{ and a record occurs at time } n\}$, $\E[N] = \infty$.

The book's hint for (b) and (c): write the number of records as a sum of indicator variables.

Everything the problem uses:

- i.i.d.: every $X_i$ has the same distribution, and any collection of them is independent.
- Continuous random variable: it has a density, so $P\{X_i = X_j\} = 0$ when $i \neq j$ --- no two of the values are ever equal.
- A record at time $n$: $X_n$ is strictly bigger than every one of $X_1, \ldots, X_{n-1}$.
- $\max(X_1, \ldots, X_{n-1})$: the largest of the first $n-1$ values.
- Indicator variable $I_A$: it equals $1$ when the event $A$ happens and $0$ when it does not.
- $\E[I_A] = P(A)$, because the mean of a $0/1$ variable is the probability of the $1$.
- $\Var(Y) = \E[Y^{2}] - (\E[Y])^{2}$.

One small step first, and it is only about part (a). Take $n = 3$. The three values are all different, so you can rank them smallest to largest, and each ranking is one ordering of the subscripts $1, 2, 3$. There are $6$ such orderings.

Write out those $6$ orderings, and tell me in how many of them $X_3$ is the largest.
