---
kind: correct
title: $x^{\ell-k} = e$. Correct — that was the cancellation, and 3.3 is done.
---

$x^{k} = x^{\ell}$ with $\ell > k$; rewrite the right side as
$x^{k}x^{\ell-k}$; cancel $x^{k}$, which is legitimate because it is nonzero and
$R$ is a domain; so $x^{\ell-k} = e$. Then $x \cdot x^{\ell-k} = x$, and the
sequence does loop back to $x$.

Correct — and you did it at general exponents rather than on the instance I
gave you, which is the better answer.

It also closes a loose end I had not raised: $\ell > k$ makes
$n = \ell - k + 1 \geq 2$, so the $x^{n-2}$ in your original line is always a
genuine power. Nothing is owed on 3.3. Transcribing it now.

---

## 3.14

A proper ideal $I$ of a ring $R$ is said to be **prime** if whenever
$ab \in I$ then either $a \in I$ or $b \in I$. Show that a non-zero element $c$
of $R$ is prime if and only if $(c)$ is a prime ideal.

What the statement uses:

- *Ideal:* an additive subgroup $I \subseteq R$ with $rc \in I$ for every
  $r \in R$ and $c \in I$.
- *$(c)$:* the principal ideal — all multiples $rc$, $r \in R$.
- *Proper:* $I \neq R$.
- *Prime element* (Garling, p. 362; $c$ non-zero and not a unit):
  $c \mid ab$ implies $c \mid a$ or $c \mid b$.
- *$a \in (c) \iff c \mid a$* — you proved this in 3.11.
- *$(c) = R \iff c$ is a unit* — you proved both directions of this in 3.11.

---

**Your move.** Prove it.
