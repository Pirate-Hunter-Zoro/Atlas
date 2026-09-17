---
kind: lesson
title: integral-domain-is-the-right-engine-but-a-constant-f-breaks-it
---
Your second reason is the right engine with one hypothesis left off. As stated,
"composition of non-zero polynomials is non-zero" is false. The integral domain
is what rescues the true version: over one, the leading coefficient of
$h(f(x))$ is $a_n b_m^{\,n}$, where $a_n$ leads $h$ and $b_m$ leads $f$. That
is a product of non-zero elements, so it is non-zero, so
$\deg q = \deg h \cdot \deg f$. Now read that formula when $\deg f = 0$.

The first line is right and needs nothing: $q(\gamma) = h(f(\gamma)) = 0$,
because $f(\gamma)$ is exactly the element $h$ was assumed to kill.

**Your move.** Over $K = \mathbb{Q}$, take $h(x) = x - 1$ and $f(x) = 1$. Both
are non-zero polynomials. Write down $q(x) = h(f(x))$, and then name the
hypothesis of the step that rules this $f$ out.

What it uses:

- $K[x]$ — polynomials in $x$ with coefficients in $K$.
- The zero polynomial — every coefficient is $0$; it has no degree.
- A constant polynomial — degree $0$ if non-zero, e.g. $f(x) = 1$.
- Integral domain — a commutative ring with no zero divisors; $K[x]$ over a
  field is one.
- $h(f(x))$ — substitute $f(x)$ for $x$ throughout $h$; the result is in $K[x]$.
- $\deg$ of a composite — $\deg h(f(x)) = \deg h \cdot \deg f$, by the leading
  coefficient argument above.
- The step you are proving — $\gamma$ transcendental over $K$, $f \in K[x]$ of
  degree at least $1$, $h \in K[x]$ non-zero with $h(f(\gamma)) = 0$, and
  $q(x) = h(f(x))$; the contradiction is $q$ non-zero with $q(\gamma) = 0$.

**Again.** With $K = \mathbb{Q}$, $h(x) = x - 1$ and $f(x) = 1$: what is
$q(x) = h(f(x))$, and which hypothesis of the step forbids this $f$?
