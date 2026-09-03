---
kind: correct
title: $f = 1+x$. Correct, both evaluations shown.
---

Right. $(\Phi(f))(0) = 1+0 = 1$ and $(\Phi(f))(1) = 1+1 = 0$, so $\Phi(1+x) = h$.
($x^2+1$ would have done it too.)

What you just built is the whole finite-$K$ proof in miniature: a polynomial
whose *values* were prescribed at every point of $K$. Over $\Fq{2}$ you could
find it by staring. Over a bigger $K$ you need a recipe, and the recipe is built
out of polynomials that hit one point and kill all the others.

One rung toward that, so the mechanics are fluent before the proof.

- *$K$ finite:* write its elements as $c_1,\ldots,c_q$, all distinct.
- Recall that in $K[x]$ a product is zero at $k$ exactly when one of its factors
  is zero at $k$ — evaluation is a homomorphism, which is the clause you just
  finished proving.

---

**Your move.** Take $K = \Fq{3} = \{0,1,2\}$, so $1+1 = 2$, $1+1+1 = 0$, and
$2 \cdot 2 = 1$.

Let
$$p(x) = (x-1)(x-2) \in \Fq{3}[x].$$

Compute all three values $p(0)$, $p(1)$, $p(2)$ in $\Fq{3}$. Show the arithmetic
— note that $-1 = 2$ and $-2 = 1$ here.
