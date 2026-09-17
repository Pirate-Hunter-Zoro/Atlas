---
kind: lesson
title: the-aside-lands-now-replace-x-squared-by-any-f
---
The Aside is right, and the reason you gave for $q \neq 0$ is the reason that
works. $q(x) = h(x^2)$ carries each coefficient of $h$ from degree $i$ to
degree $2i$; the exponents stay distinct, so nothing cancels, so a non-zero
$h$ gives a non-zero $q$. And $q(\gamma) = h(\gamma^2) = 0$ makes $\gamma$ a
root of a non-zero polynomial over $K$, contradicting transcendence. So
$\gamma^2$ is transcendental over $K$.

Now the same move with $x^2$ replaced by anything.

**The step.** Let $\gamma$ be transcendental over $K$, and let $f \in K[x]$
have degree at least $1$. Show that $f(\gamma)$ is transcendental over $K$.
Same shape as the warm-up: suppose some non-zero $h \in K[x]$ has
$h\bigl(f(\gamma)\bigr) = 0$, and set $q(x) = h\bigl(f(x)\bigr)$.

**Your move.** Two lines. First, why $q(\gamma) = 0$. Second, why $q$ is not
the zero polynomial — "the powers doubled" does not transfer here, so name
the property of $q$ that forces it. You may use that $h$ has degree at least
$1$; say in half a line why that is free.

What it uses:

- $K[x]$ — polynomials in $x$ with coefficients in $K$.
- Algebraic over $K$ — a root of some non-zero polynomial in $K[x]$.
- Transcendental over $K$ — not algebraic over $K$.
- The zero polynomial — every coefficient is $0$.
- $h(f(x))$ — substitute $f(x)$ for $x$ throughout $h$; the result is again in $K[x]$.
- $\deg$ of a composite — $\deg h(f(x)) = \deg h \cdot \deg f$ over a field.
- Where this goes — in **4.10** you need $\alpha = f(\gamma)/g(\gamma)$, a quotient, not a polynomial. Polynomials first.

**Again.** $\gamma$ transcendental over $K$, $f \in K[x]$ of degree at least
$1$, $h \in K[x]$ non-zero with $h(f(\gamma)) = 0$, and $q(x) = h(f(x))$. Why
is $q(\gamma) = 0$, and why is $q$ not the zero polynomial?
