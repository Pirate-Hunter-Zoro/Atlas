---
kind: lesson
title: irreducible-done-now-invert-alpha
---
Correct, and the first half of 4.4 is done. The constant term is $1$, so the
rational root test leaves only $1$ and $-1$; you evaluated both and got $5$
and $-3$. Neither is zero, so there is no rational root. A cubic with no
rational root cannot factor in $\mathbb{Q}[x]$, because any factorisation of a
degree-$3$ polynomial has a factor of degree $1$, and a degree-$1$ factor over
$\mathbb{Q}$ gives a rational root.

That also fixes the shape of the answer to the rest. $x^3 + 3x + 1$ is monic,
irreducible, and has $\alpha$ as a root, so it is the minimal polynomial of
$\alpha$ and $[\mathbb{Q}(\alpha) : \mathbb{Q}] = 3$. Every element of
$\mathbb{Q}(\alpha)$ is therefore $a + b\alpha + c\alpha^2$ with $a$, $b$, $c$
rational, which is exactly the form the exercise demands.

**Exercise 4.4, the part still open.** *Suppose that $\alpha$ is a root of
$x^3 + 3x + 1$ in $\mathbb{C}$. Express $\alpha^{-1}$ and $(1 + \alpha)^{-1}$
as linear combinations, with rational coefficients, of $1$, $\alpha$ and
$\alpha^2$.*

Everything it uses:

- **$\alpha$ is a root** — it means $\alpha^3 + 3\alpha + 1 = 0$. This is the only fact about $\alpha$ you have, and every step comes out of it.
- **$\mathbb{Q}(\alpha)$** — the smallest subfield of $\mathbb{C}$ containing $\mathbb{Q}$ and $\alpha$; here every element of it is $a + b\alpha + c\alpha^2$ with $a$, $b$, $c$ rational.
- **$\alpha^{-1}$** — the element of $\mathbb{Q}(\alpha)$ with $\alpha \cdot \alpha^{-1} = 1$. It exists because $\alpha \neq 0$: putting $0$ into $x^3 + 3x + 1$ gives $1$, not $0$.
- **Linear combination of $1$, $\alpha$, $\alpha^2$ with rational coefficients** — a sum $a \cdot 1 + b\alpha + c\alpha^2$, nothing else allowed, no division by $\alpha$ left in it.

**Your move.** $\alpha^{-1}$ only this turn; leave $(1 + \alpha)^{-1}$ alone, it
is the harder half. Take $\alpha^3 + 3\alpha + 1 = 0$ and move the $1$ by
itself to the other side. What is left on the first side has $\alpha$ as a
common factor of both terms. Pull it out, and you have $\alpha$ times something
equal to $-1$. Write down what that makes $\alpha^{-1}$.
