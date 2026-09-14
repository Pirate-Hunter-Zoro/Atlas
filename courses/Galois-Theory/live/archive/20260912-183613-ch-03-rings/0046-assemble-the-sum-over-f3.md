---
kind: correct
title: $c = 2$, and $\delta$ is $1,0,0$. Now put three of them together.
---

Correct. $\delta(x) = 2(x-1)(x-2)$ takes the values $\delta(0) = 1$,
$\delta(1) = 0$, $\delta(2) = 0$ — an indicator at $0$.

The same recipe at the other two points, which is your operation run twice more,
so I am not making you do it:

| | polynomial | at $0$ | at $1$ | at $2$ |
|---|---|---|---|---|
| $\delta_{0}$ | $2(x-1)(x-2)$ | $1$ | $0$ | $0$ |
| $\delta_{1}$ | $2x(x-2)$ | $0$ | $1$ | $0$ |
| $\delta_{2}$ | $2x(x-1)$ | $0$ | $0$ | $1$ |

Each one is built the same way: multiply the two factors that kill the *other*
two points, then scale so the surviving value is $1$.

---

**Your move.** Let $h \in \Fq{3}^{\Fq{3}}$ be the mapping
$$h(0) = 2, \qquad h(1) = 0, \qquad h(2) = 1.$$

Using only $\delta_{0}$, $\delta_{1}$, $\delta_{2}$ from the table and elements
of $\Fq{3}$, write down a polynomial $f \in \Fq{3}[x]$ with $\Phi(f) = h$ — and
then compute $f(0)$, $f(1)$, $f(2)$ from the table's rows to check that it is.
