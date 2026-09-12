---
kind: question
title: Fair question. $x$ is not an element of $K$, and $(x-a)$ is an ideal of $K[x]$.
---

Your objection is exactly right *given* what you assumed, and what you assumed
is the one thing that is false. $(x-a)$ is **not** a subset of $K$. It is an
ideal of $K[x]$, so both sides of $f \in (x-a)$ live in the same ring and the
question is fine.

**$x$ is an indeterminate.** It is not an element of $K$ and it is never
assigned a value. A polynomial in $K[x]$ *is* its list of coefficients
$k_0, k_1, \ldots, k_n$ from $K$; the symbol $x$ is bookkeeping that tells you
which coefficient is which. Nothing in $K$ is called $x$, and no element of $K$
is ever substituted for it — that is what makes $K[x]$ a bigger ring than $K$
rather than a set of values.

**So which ring is $(x-a)$ an ideal of?** $K[x]$. The generator $x - a$ is a
degree-1 *polynomial*: coefficients $-a$ and $1$, both in $K$. Its ideal is
every multiple of it,
$$(x-a) = \{\, g \cdot (x-a) : g \in K[x] \,\},$$
and every one of those is a polynomial. With $K = \mathbb{Q}$ and $a = 2$, the
ideal $(x-2)$ contains $x-2$, and $7x-14$, and $(x+5)(x-2) = x^2+3x-10$. It
contains no bare rational number except $0$.

It could not be an ideal of $K$ anyway: $K$ is a field, so by your own 3.11 work
its only ideals are $\{0\}$ and $K$ itself. Ideals only get interesting one ring
up.

**Where $a$ does live.** $a \in K$, and $K$ sits inside $K[x]$ as the constant
polynomials. That is why $f(a)$ makes sense: *evaluation at $a$* is a separate
operation that takes a polynomial and returns the element
$k_0 + k_1a + \cdots + k_na^n$ of $K$. Evaluating is a thing you do to a
polynomial; it is not what the polynomial is.

---

## 3.15, again — first half only

Suppose that $f = k_{0} + k_{1}x + \cdots + k_{n}x^{n}$ is a non-zero element of
$K[x]$, where $K$ is a field. An element $a$ of $K$ is a **root** of $f$ if
$f(a) = k_{0} + k_{1}a + \cdots + k_{n}a^{n} = 0$. Show that $a$ is a root of
$f$ if and only if $f \in (x - a)$.

What the statement uses:

- *$K$ a field:* commutative ring, $1 \neq 0$, every non-zero element a unit.
- *$K[x]$:* polynomials in the indeterminate $x$ with coefficients in $K$. A
  domain, since $K$ is.
- *$(x-a)$:* the principal ideal **of $K[x]$** — all $g \cdot (x-a)$ with
  $g \in K[x]$.
- *$f \in (x-a) \iff (x-a) \mid f$* — yours, from 3.11.
- *Theorem 3.7 (division in $K[x]$):* for $f \neq 0$ and any $g$ in $K[x]$ there
  exist $q, r$ with $g = qf + r$ and either $r = 0$ or $\deg r < \deg f$.
- *$\deg(gh) = \deg g + \deg h$ over a domain* — yours, from 3.10.
- *$\deg$ of a non-zero constant is $0$; the zero polynomial has no degree.*

---

**Your move.** Prove it: $a$ is a root of $f$ if and only if $f \in (x-a)$.

The at-most-$n$ count stays off the table until this half is closed.
