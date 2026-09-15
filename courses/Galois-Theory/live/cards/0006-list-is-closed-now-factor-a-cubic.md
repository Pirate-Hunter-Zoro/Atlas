---
kind: lesson
title: list-is-closed-now-factor-a-cubic
---
Exactly two: $K$ and $L$. "Just $L$ and $K$" is the answer 4.1 wanted, and
your page now has it. The one line it still owes is why the list has two
entries rather than one: if $K = L$ then $[L:K] = 1$, but $[L:K] = p \ge 2$.
So $K \neq L$, and the tower-law work above it rules out any third field.
4.1 is closed.

Next, and it is a different kind of work — arithmetic with an actual
polynomial, not a degree argument.

**Exercise 4.4.** *Show that $x^3 + 3x + 1$ is irreducible in
$\mathbb{Q}[x]$. Suppose that $\alpha$ is a root of $x^3 + 3x + 1$ in
$\mathbb{C}$. Express $\alpha^{-1}$ and $(1 + \alpha)^{-1}$ as linear
combinations, with rational coefficients, of $1$, $\alpha$ and
$\alpha^2$.*

Everything it uses:

- **Irreducible in $\mathbb{Q}[x]$** — not a product of two polynomials in $\mathbb{Q}[x]$ of smaller degree.
- **The cubic fact** — degree $3$ splits only as $1 + 2$, so a cubic is irreducible over $\mathbb{Q}$ exactly when it has no root in $\mathbb{Q}$.
- **Rational root test** — if a monic polynomial with integer coefficients has a rational root, that root is an integer dividing the constant term.
- **Minimal polynomial $m_\alpha$** — the monic polynomial of least degree in $K[x]$ with $\alpha$ as a root; it is irreducible.
- **$\mathbb{Q}(\alpha)$** — the smallest subfield of $\mathbb{C}$ containing $\mathbb{Q}$ and $\alpha$. When $m_\alpha$ has degree $3$, every element of it is $a + b\alpha + c\alpha^2$ with $a, b, c$ rational, and that is why the exercise asks for that shape.

**Your move.** The constant term is $1$, so the rational root test leaves
exactly two candidates. Name them, evaluate $x^3 + 3x + 1$ at each, and
say what the two numbers you get prove.
