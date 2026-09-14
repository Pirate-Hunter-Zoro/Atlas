---
kind: note
title: Subtraction is not a third operation. It is $+$ with the additive inverse.
---

Right to ask, and you are right that the operations are only $+$ and the
product. Subtraction is notation, not a new operation:

- A ring's axioms make $(R, +)$ an **abelian group**. So every $a \in R$ has an
  additive inverse $-a$, the unique element with $a + (-a) = 0$.
- $a - b$ is *defined* to mean $a + (-b)$. Nothing is being assumed beyond the
  additive group you already have.

So in $\Fq{3}$, where $1 + 2 = 0$, the inverse of $1$ is $2$ and the inverse of
$2$ is $1$. Your $p$ has no minus signs in it at all:
$$p(x) = (x-1)(x-2) = (x+2)(x+1) \in \Fq{3}[x].$$

And your three values are correct: $p(0) = 2\cdot 1 = 2$, $p(1) = 0 \cdot 2 = 0$,
$p(2) = 1 \cdot 0 = 0$. One point where it is nonzero, zero at the other two —
which is the whole reason that product was written down.

---

**Your move.** It is not yet an indicator, because $p(0) = 2$ and you want $1$.
Fix that by scaling.

Find the $c \in \Fq{3}$ with $c \cdot 2 = 1$, set
$$\delta(x) = c \cdot p(x) \in \Fq{3}[x],$$
and give the three values $\delta(0)$, $\delta(1)$, $\delta(2)$.

Recall that in $\Fq{3}$: $2 \cdot 2 = 4 = 1$.
