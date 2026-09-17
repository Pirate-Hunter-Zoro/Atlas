---
kind: lesson
title: finite-degree-means-a-finite-basis-nothing-more
---
Finite degree means the big field is a finite-dimensional vector space over the
small one. That is the whole content of the phrase.

Take $L \subseteq M$. Throw away the fact that elements of $M$ multiply each
other, and keep two operations: adding two elements of $M$, and multiplying an
element of $M$ by a scalar from $L$. Those axioms are satisfied, so $M$ is a
vector space over $L$. Then $[M:L]$ is its dimension. Finite degree means some
finite list of elements of $M$ spans every element of $M$ using coefficients
from $L$.

Two examples to fix it. $[\mathbb{Q}(\sqrt2):\mathbb{Q}] = 2$: every element is
$a + b\sqrt2$, and $\{1, \sqrt2\}$ is a basis. Against that, $\mathbb{Q}(t):\mathbb{Q}$
with $t$ transcendental is infinite, because $1, t, t^2, t^3, \dots$ are linearly
independent over $\mathbb{Q}$ forever, so no finite list spans.

Why you want it. A finite degree over $K$ forces every element of the field to be
algebraic over $K$ — the powers $1, x, x^2, \dots$ cannot all be independent, so
some finite $K$-combination of them is $0$, and that combination is a polynomial
over $K$ killing $x$. That is the contradiction you are walking toward.

What it uses:

- $[M:L]$ — the dimension of $M$ as a vector space over $L$.
- Basis — a linearly independent spanning list; its length is the dimension.
- Algebraic over $K$ — some non-zero polynomial in $K[x]$ has it as a root.
- Minimal polynomial — the monic polynomial over $K$ of least degree killing it.
- $\alpha$ algebraic over $K$ with minimal polynomial of degree $n$ gives
  $[K(\alpha):K] = n$, with basis $1, \alpha, \dots, \alpha^{n-1}$.

**Your move.** One concrete case, to make that last fact yours before you use it
on $\alpha$. Let $\beta$ be a root of $x^3 - 2$ over $\mathbb{Q}$. What is
$[\mathbb{Q}(\beta):\mathbb{Q}]$, and what is the basis?
