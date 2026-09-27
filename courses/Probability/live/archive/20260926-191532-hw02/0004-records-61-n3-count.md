---
kind: question
title: records-61-n3-count
---
The route to 61(a) is counting, not integration. Your $n = 2$ page closed at $1/2$ by parts, and that is right. The general case needs no integral at all --- only that all $n!$ orderings of the $n$ values are equally likely.

**Problem 61(a), in full.** Let $X_1, X_2, \ldots, X_n$ be independent and identically distributed continuous random variables. Show that
$$P\{X_n > \max(X_1, \ldots, X_{n-1})\} = \frac{1}{n}.$$

Everything the problem uses:

- Continuous: $P\{X_i = X_j\} = 0$ for $i \neq j$, so with probability $1$ the $n$ values are all distinct and can be ranked.
- Ordering: one arrangement of $X_1, \ldots, X_n$ from smallest to largest, written like $X_2 < X_1 < X_3$. There are $n!$ of them.
- Exchangeable: independent and identically distributed means relabelling the $X_i$ leaves the joint distribution unchanged, so every one of the $n!$ orderings carries the same probability.
- $\max(X_1, \ldots, X_{n-1})$: the largest of the first $n-1$ values.
- The event $X_n > \max(X_1, \ldots, X_{n-1})$ says exactly one thing about an ordering --- that $X_n$ sits last in it.

Take $n = 3$. Write out all six orderings of $X_1, X_2, X_3$ from smallest to largest, count how many of them have $X_3$ last, and say what $P\{X_3 > \max(X_1, X_2)\}$ is.
