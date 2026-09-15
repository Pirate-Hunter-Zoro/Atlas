---
kind: lesson
title: 4-9-done-now-4-8-compose-the-polynomials
---
Right, and 4.9 is closed. $a = \pi$, $b = 1/\pi$, $ab = 1$, and $1$ is a root of
$x - 1$, which is a non-zero polynomial over $\mathbb{Q}$. Name that polynomial
when you write it up — "certainly algebraic" is true, but the polynomial *is*
the proof and it costs you four characters. One wording fix: algebraic **over**
$\mathbb{Q}$, not *in* $\mathbb{Q}$. Algebraic is a relation between an element
and a base field, not membership in it. Your closing line is the same
counterexample stated in general, and it is correct: in any extension
$L\!:\!K$, both $a$ and $b$ can sit outside $K$ while $ab$ lands inside it.

**Exercise 4.8.** *Suppose that $L\!:\!K$ is an extension, that $\alpha$ is an
element of $L$ which is transcendental over $K$, and that $f$ is a non-constant
element of $K[x]$. Show that $f(\alpha)$ is transcendental over $K$. Show that,
if $\beta$ is an element of $L$ which satisfies $f(\beta) = \alpha$, then
$\beta$ is transcendental over $K$.*

Everything 4.8 uses:

- $L\!:\!K$ — an extension: $K$ is a subfield of $L$.
- $K[x]$ — polynomials in $x$ with coefficients in $K$.
- **non-constant** — degree at least $1$.
- **algebraic over $K$** — a root of some non-zero polynomial in $K[x]$.
- **transcendental over $K$** — not algebraic over $K$.
- $f(\alpha)$ — the element of $L$ you get by substituting $\alpha$ into $f$.
- $g(f(x))$ — the polynomial got by substituting $f(x)$ into $g$; it is again in $K[x]$.
- $\deg$ — degree; $\deg g(f(x)) = (\deg g)(\deg f)$ when $f$ is non-constant.

**Your move.** First half only, and it is one line. Suppose $f(\alpha)$ were
algebraic over $K$: then $g(f(\alpha)) = 0$ for some non-zero $g$ in $K[x]$.
Which single polynomial does that exhibit $\alpha$ as a root of, and why is that
polynomial not the zero polynomial?
