---
kind: correct
title: $c$ can't be a unit. Correct — 3.14 is closed. Now 3.15.
---

One letter, and it is the right one. $(c) \neq R$ and the 3.11 biconditional
read backwards gives *$c$ is not a unit*, which is the clause the definition of
a prime element wanted.

**3.14 is done.** Both directions, properness and non-unit at both ends.
Transcribing it now — I have the reverse direction from the page before last, so
nothing is lost by this revision having written over it.

---

## 3.15

Suppose that $f = k_{0} + k_{1}x + \cdots + k_{n}x^{n}$ is a non-zero element of
$K[x]$, where $K$ is a field. An element $a$ of $K$ is a **root** of $f$ if
$f(a) = k_{0} + k_{1}a + \cdots + k_{n}a^{n} = 0$. Show that $a$ is a root of
$f$ if and only if $f \in (x - a)$, and show that $f$ has at most $n$ distinct
roots.

What the statement uses:

- *$K[x]$:* polynomials in $x$ with coefficients in the field $K$.
- *$(x-a)$:* the principal ideal of $K[x]$ — all multiples $g \cdot (x-a)$ for
  $g \in K[x]$.
- *$f \in (x-a) \iff (x-a) \mid f$* — yours, from 3.11.
- *Theorem 3.7 (division in $K[x]$):* for $f \neq 0$ and any $g$ in $K[x]$ there
  exist $q, r$ with $g = qf + r$ and either $r = 0$ or $\deg r < \deg f$.
- *$\deg(gh) = \deg g + \deg h$ over a domain* — yours, from 3.10.

---

**Your move.** The first half only: $a$ is a root of $f$ if and only if
$f \in (x-a)$.

Leave the at-most-$n$ count alone; it comes after.
