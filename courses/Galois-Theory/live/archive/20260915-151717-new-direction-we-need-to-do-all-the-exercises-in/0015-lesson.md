---
kind: lesson
title: that-is-the-polynomial-over-Q-not-over-L
---
$x^6 - 2$ is the minimal polynomial of $\alpha$ over $K = \mathbb{Q}$, not over
$L$. Both exist, they are different polynomials, and the exercise is about the
second one. Everything above that last cloud is right: $[L:K] = 3$ by Eisenstein
on $x^3 - 2$, and $[L(\alpha):L] = 6/3 = 2$ by the tower law. You then wrote down
a degree-$6$ polynomial, which contradicts the $2$ you had just computed.

Here is the test that separates them. $m_L$ may use every element of
$L = \mathbb{Q}(2^{1/3})$ in its coefficients, so $2^{1/3}$ itself is a legal
coefficient; $m_K$ may use only rationals. More coefficients available means a
shorter polynomial can reach $\alpha$, and Theorem 4.4 pins how short: degree
exactly $[L(\alpha):L] = 2$.

So you are looking for a monic quadratic, coefficients in $L$, killing
$\alpha = 2^{1/6}$. There is only one lever: compute $\alpha^2$ and notice which
field it lands in.

What you need:

- $K = \mathbb{Q}$, $L = \mathbb{Q}(2^{1/3})$, $\alpha = 2^{1/6}$ — the positive real sixth root of $2$.
- $m_L$ — the monic polynomial of least degree with all coefficients in $L$ and $\alpha$ as a root.
- $m_K$ — the same thing with coefficients in $K$. For this $\alpha$ that is $x^6 - 2$, which you found.
- $L = \{a + b\,2^{1/3} + c\,2^{2/3} : a,b,c \in \mathbb{Q}\}$ — so $2^{1/3}$ and $2^{2/3}$ are in $L$, and $2^{1/6}$ is not.
- **Monic** — leading coefficient $1$.
- **Theorem 4.4** — $[L(\alpha):L]$ equals the degree of $m_L$.

**Your move.** Work out $\alpha^2$ as a power of $2$, then write the monic
degree-$2$ polynomial with coefficients in $L$ that has $\alpha$ as a root. Then
answer one thing about it: is its constant coefficient a rational number?
