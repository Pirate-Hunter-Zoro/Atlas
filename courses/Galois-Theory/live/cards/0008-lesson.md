---
kind: lesson
title: algebraic-closure-is-the-wrong-object-the-fact-you-want-is-the-degree
---
The skeleton is right, the contradiction lands, and one phrase names the wrong
object. You justified "$f(\beta)$ is algebraic" by *algebraic closure of
$K(\beta)$*. The algebraic closure of $K(\beta)$ is a specific and much larger
field — one containing a root of every non-constant polynomial over $K(\beta)$ —
and $K(\beta)$ itself is almost never that. $\mathbb{Q}(\sqrt{2})$ contains no
root of $x^2 + 1$.

The sentence you want instead: every element of $K(\beta)$ is algebraic **over
$K$**. That is true here, and the reason is the one your proof skips. $\beta$
algebraic makes $[K(\beta):K]$ finite, and finiteness is the whole engine.

So prove the engine on the smallest case there is.

**Your move.** Take $K = \mathbb{Q}$ and $\beta = \sqrt{2}$, so
$[\mathbb{Q}(\sqrt{2}):\mathbb{Q}] = 2$ with basis $1, \sqrt{2}$. Let $\gamma = 1
+ \sqrt{2}$, an element of that field which is not $\beta$ and not in
$\mathbb{Q}$. Write each of $1$, $\gamma$, $\gamma^2$ in terms of the basis $1,
\sqrt{2}$. Three vectors in a $2$-dimensional $\mathbb{Q}$-vector space cannot be
linearly independent, so find the dependence between those three and read off
from it a non-zero polynomial in $\mathbb{Q}[x]$ having $\gamma$ as a root.

What it uses:

- $\mathbb{Q}(\sqrt{2})$ — the smallest subfield of $\mathbb{R}$ containing $\mathbb{Q}$ and $\sqrt{2}$; every element is $a + b\sqrt{2}$ with $a, b \in \mathbb{Q}$.
- $[K(\beta):K]$ — the dimension of $K(\beta)$ as a vector space over $K$.
- Basis — a list of elements such that every element of the space is a $K$-combination of them, in exactly one way.
- Linearly dependent over $\mathbb{Q}$ — some $\mathbb{Q}$-combination of them equals $0$ with the coefficients not all $0$.
- Algebraic over $K$ — a root of some non-zero polynomial in $K[x]$.
- Algebraically closed — every non-constant polynomial with coefficients in the field has a root in that same field.
- $\gamma^2 = (1 + \sqrt{2})^2$, expanded and collected as $a + b\sqrt{2}$.

Two ordinary rational numbers as the coefficients, and a degree-$2$ polynomial at
the end.
