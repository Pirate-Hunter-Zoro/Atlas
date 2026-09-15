---
kind: lesson
title: alpha-inverse-correct-now-shift-to-one-plus-alpha
---
$\alpha^{-1} = -1 \cdot \alpha^2 - 3 \cdot 1$ is right, and the factorisation is
fixed: $\alpha(\alpha^2 + 3)$ with the power back. I ran the check for you.
Multiplying gives $\alpha \cdot (-\alpha^2 - 3) = -\alpha^3 - 3\alpha$, and
replacing $\alpha^3$ with $-3\alpha - 1$ turns that into
$3\alpha + 1 - 3\alpha = 1$. The two underlined coefficients are rational, so
that half of 4.4 is closed.

**Exercise 4.4, the other half.** *Suppose that $\alpha$ is a root of
$x^3 + 3x + 1$ in $\mathbb{C}$. Express $(1 + \alpha)^{-1}$ as a linear
combination, with rational coefficients, of $1$, $\alpha$ and $\alpha^2$.*

Everything it uses:

- **$\alpha$ is a root** — it means $\alpha^3 + 3\alpha + 1 = 0$, and this is the only fact about $\alpha$ you have.
- **$\mathbb{Q}(\alpha)$** — the smallest subfield of $\mathbb{C}$ containing $\mathbb{Q}$ and $\alpha$; every element of it is $a + b\alpha + c\alpha^2$ with $a$, $b$, $c$ rational.
- **$(1 + \alpha)^{-1}$** — the element whose product with $1 + \alpha$ is $1$. It exists because $1 + \alpha \neq 0$: putting $-1$ into $x^3 + 3x + 1$ gives $-3$, so $\alpha \neq -1$.
- **Linear combination of $1$, $\alpha$, $\alpha^2$ over $\mathbb{Q}$** — a sum $a \cdot 1 + b\alpha + c\alpha^2$, with nothing left in a denominator except plain rational numbers.
- **Reducing with the cubic** — $\alpha^3 = -3\alpha - 1$, used to collapse any cubic or higher power back to the three-term form.

Why the first half will not just repeat. It worked because the cubic has a
nonzero constant term, which let you pull $\alpha$ out of everything else and
divide. To invert $1 + \alpha$ you need a polynomial relation in which
$1 + \alpha$ is the thing you can pull out. Get one by giving it a name:
set $\beta = 1 + \alpha$, so $\alpha = \beta - 1$, and put that into the cubic.

**Your move.** Expand and collect $(\beta - 1)^3 + 3(\beta - 1) + 1$ into a
cubic in $\beta$ with integer coefficients. One expansion, nothing clever.
Report all four coefficients. The constant term is the one to watch: if it
comes out nonzero, the same pull-out-and-divide move is available to you again.
