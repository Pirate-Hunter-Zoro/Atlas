---
kind: question
title: 3.10 — units in $R[x]$. First, one product over $\mathbb{Z}_{6}$.
---

**3.10 (Garling).** What are the units in $R[x]$, where $R$ is an integral
domain? What are the units in $\mathbb{Z}_{4}[x]$?

You are not answering that yet. What it uses:

- *Unit:* $u$ in a ring $S$ is a unit if there is $v \in S$ with $uv = 1_{S}$.
- *Integral domain:* commutative, $1 \neq 0$, and no zero divisors — $ab = 0$
  forces $a = 0$ or $b = 0$.
- $R[x]$: polynomials $\sum_{i} a_{i}x^{i}$, $a_{i} \in R$, finitely many
  non-zero.
- $\deg f$: the largest $i$ with $a_{i} \neq 0$.
- $\mathbb{Z}_{4}$, $\mathbb{Z}_{6}$: the integers mod $4$, mod $6$. Neither is
  an integral domain — in $\mathbb{Z}_{6}$, $2 \cdot 3 = 0$.

Two questions, and the second one is not there for variety. The hypothesis
*integral domain* is doing work, and dropping it changes the answer.

---

**Your move.** Before the exercise, one product, so the mechanism is in front of
you rather than in a sentence. Work in $\mathbb{Z}_{6}[x]$ — coefficients
reduced mod $6$ — and multiply
$$(2x + 1)(3x + 1).$$
Give the product in lowest terms and state its degree.
