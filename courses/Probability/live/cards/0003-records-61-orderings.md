---
kind: question
title: records-61-orderings
---
$1/2$. It is already on your page --- you stopped one line early.

You went by parts rather than by substitution, which is fine, and it closed. With $u = F(x_2)$ and $dv = f(x_2)\,dx_2$ you get $v = F(x_2)$, so
$$I = \Big[F(x_2)^2\Big]_{-\infty}^{\infty} - I .$$
That bracket is not an unknown. It is $F(\infty)^2 - F(-\infty)^2 = 1 - 0 = 1$. So $2I = 1$ and $I = 1/2$. The density $f$ never had to be known; only the two endpoint values of $F$ were needed. Your $F(x_2)^2/2$ is the antiderivative with the limits not yet put in.

Base case done: for $n = 2$, $P\{X_2 > X_1\} = 1/2 = 1/2$. Now abandon the induction. There is a route to all of (a) that never integrates.

**Problem 61(a), in full.** $X_1, X_2, \ldots, X_n$ are independent and identically distributed continuous random variables. Show that
$$P\{X_n > \max(X_1, \ldots, X_{n-1})\} = \frac{1}{n}.$$

Everything the new route uses:

- Continuous means $P\{X_i = X_j\} = 0$, so with probability $1$ the $n$ values are all distinct and can be ranked.
- An *ordering* is one arrangement of $X_1, \ldots, X_n$ from smallest to largest, e.g. $X_2 < X_1 < X_3$. There are $n!$ of them.
- Identically distributed and independent means the $X_i$ are *exchangeable*: relabelling them does not change the joint distribution, so all $n!$ orderings have the same probability.
- $X_n > \max(X_1, \ldots, X_{n-1})$ says exactly one thing about an ordering: $X_n$ sits last.

Take $n = 3$. Write out all $6$ orderings of $X_1, X_2, X_3$ from smallest to largest. How many of them have $X_3$ last, and so what is $P\{X_3 > \max(X_1, X_2)\}$?
