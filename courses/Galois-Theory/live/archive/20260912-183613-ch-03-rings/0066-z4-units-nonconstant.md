---
kind: correct
title: $1$ and $3$. Correct — and now the ones that are not constants
---

Correct: the units of $\mathbb{Z}_{4}$ are $1$ and $3$, each its own inverse,
$3 \cdot 3 = 9 \equiv 1$. And $2$ is out for the reason you named.

So the constants are settled. But the question was about $\mathbb{Z}_{4}[x]$,
and in $R[x]$ the reason units *had* to be constants was $\deg(fg) = \deg f +
\deg g$ — which needs $R$ to be an integral domain. $\mathbb{Z}_{4}$ is not
one. Nothing rules out a unit of positive degree here, and in fact nothing
does.

---

**Your move.** Find $f, g \in \mathbb{Z}_{4}[x]$ with
$$\deg f \geq 1 \quad\text{and}\quad fg = 1.$$

Degree $1$ is enough. Write down $f$, write down $g$, and multiply them out to
show the product is $1$.

What to lean on: you saw in $\mathbb{Z}_{6}$ that a top coefficient can die
when two non-zero coefficients multiply to $0$. For a product to come out as
$1$, *every* coefficient above the constant one has to die like that. In
$\mathbb{Z}_{4}$ you have already put your finger on the element that does it.

---

- $\mathbb{Z}_{4} = \{0,1,2,3\}$, arithmetic mod $4$.
- $\mathbb{Z}_{4}[x]$: polynomials with coefficients in $\mathbb{Z}_{4}$.
- *Unit:* $f$ with $fg = 1$ for some $g$ in the same ring, $1$ the constant
  polynomial $1$.
