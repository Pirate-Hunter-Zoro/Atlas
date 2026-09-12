---
kind: correct
title: $u \in I$ and $I \subseteq I'$. Both facts named, so $u \in I'$ — 3.25 is closed. Now the last one.
---

Those are the two. $u \in I$ from your own construction, $I \subseteq I'$ from
the part of Theorem 3.14 you had not spent yet, and $u \in I'$ is what you get
by putting them next to each other. Nothing is computed, which was the point.

Your contrapositive line at the top is stated correctly too, and citing Zorn's
lemma directly instead of Theorem 3.14 is fine — Zorn is what proves it.

**3.25 is closed. I am writing it up.** One statement left on the sheet.

---

## Exercise 3.26

Suppose $J$ is a proper prime ideal in an **integral domain** $R$.

1. Show that $J[x]$ is prime in $R[x]$.
2. Show that $J[x]$ is **not** a maximal proper ideal in $R[x]$.

### Everything the statement uses

- $R$: a commutative ring with identity $1$. An **integral domain**: $R$ has no zero divisors — $ab = 0$ forces $a = 0$ or $b = 0$.
- $R[x]$: polynomials in $x$ with coefficients in $R$.
- *Ideal* $I$: closed under addition, and **absorbing** — $a \in I$, $r \in R$ $\Rightarrow$ $ra \in I$.
- *Proper*: $I \neq R$. Equivalently (your card 0112 territory) $1 \notin I$.
- *Prime ideal* $J$: proper, and $ab \in J$ $\Rightarrow$ $a \in J$ or $b \in J$.
- *Maximal proper ideal* $M$: proper, and no ideal sits strictly between $M$ and $R$.
- $J[x]$: the polynomials **every one of whose coefficients lies in $J$**. That this is an ideal of $R[x]$ is one line of absorption, and I am granting it to you — the exercise is the two properties above.
- **Your card 0130-ish machinery:** $\deg(fg) = \deg f + \deg g$ in a domain.

Note what part 2 is really saying: prime does not imply maximal. It is the
counterexample I mentioned in the last card, in its polynomial form.

---

**Your move — one thing only, and it is a membership check.** Take $R =
\mathbb{Z}$ and $J = (3)$, which is a proper prime ideal of $\mathbb{Z}$.

Which of these four lie in $J[x]$?

| | polynomial |
|---|---|
| (a) | $3x^{2} + 6x - 9$ |
| (b) | $x^{2} + 3x + 6$ |
| (c) | $6x^{5} + 12$ |
| (d) | $x$ |

Just the letters that are in. No proof.
