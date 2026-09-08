---
kind: question
title: 3.3 — a finite integral domain is a field
---

Show that an integral domain with a finite number of elements is always a
field.

What the statement uses:

- *Integral domain:* a ring $R$ — commutative, with identity $e$ — in which
  $rs = 0$ forces $r = 0$ or $s = 0$.
- *$R^{*}$:* the non-zero elements of $R$.
- *Unit:* an $a \in R$ for which $ab = e$ for some $b \in R$.
- *Field:* a commutative ring with $e \neq 0$ in which **every** element of
  $R^{*}$ is a unit.
- *Cancellation:* in an integral domain, if $a \neq 0$ and $ax = ay$ then
  $x = y$. (This is what "no zero divisors" buys you, and you may use it.)
- *Finite:* $R$ has finitely many elements, so $R^{*}$ does too.

---

**Your move.** Prove it.

So: fix a non-zero $a \in R$ and produce a $b$ with $ab = e$.
