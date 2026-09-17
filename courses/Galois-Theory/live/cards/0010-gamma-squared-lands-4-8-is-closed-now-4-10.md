---
kind: lesson
title: gamma-squared-lands-4-8-is-closed-now-4-10
---
All correct, and 4.8 is closed. $\gamma^2 = 3 + 2\sqrt2$ is right, $c_0 = 1$,
$c_1 = 2$, $c_2 = -1$ satisfy $1 + 2\gamma - \gamma^2 = 0$, and $h(x) = 1 + 2x -
x^2$ has $\gamma$ as a root. I checked it: $1 + 2(1+\sqrt2) - (3+2\sqrt2) = 0$.
One word only — say algebraic **over** $\mathbb{Q}$, not *in* $\mathbb{Q}$;
$\gamma$ is not in $\mathbb{Q}$, it is a root of a polynomial with coefficients
there.

**Exercise 4.10.** Suppose $K(\alpha, \beta) : K$ is an extension, that $\alpha$
is algebraic over $K$ but not in $K$, and that $\beta$ is transcendental over
$K$. Show that $K(\alpha, \beta) : K$ is not simple.

**Your move**, one piece of it. Suppose someone hands you a $\gamma \in
K(\alpha, \beta)$ with $K(\gamma) = K(\alpha, \beta)$, and suppose that
$\gamma$ is algebraic over $K$. Something in the hypotheses of 4.10 breaks.
Name which one, and give the chain of two facts that breaks it. You proved both
facts in the last two cards.

What it uses:

- $L : K$ an extension — $K$ is a subfield of the field $L$.
- $K(\alpha, \beta)$ — the smallest subfield of $L$ containing $K$, $\alpha$ and $\beta$.
- Simple extension — $L : K$ is simple when $L = K(\gamma)$ for some single $\gamma \in L$.
- Algebraic over $K$ — a root of some non-zero polynomial in $K[x]$.
- Transcendental over $K$ — not algebraic over $K$: no non-zero polynomial in $K[x]$ has it as a root.
- $[L:K]$ — the dimension of $L$ as a vector space over $K$.
- The degree fact — if $\gamma$ is algebraic over $K$ then $[K(\gamma):K]$ is finite, with basis $1, \gamma, \dots, \gamma^{n-1}$ for $n$ the least degree of a non-zero polynomial in $K[x]$ killing $\gamma$.
- The membership fact — every element of a finite extension of $K$ is algebraic over $K$.

Two sentences is enough.
