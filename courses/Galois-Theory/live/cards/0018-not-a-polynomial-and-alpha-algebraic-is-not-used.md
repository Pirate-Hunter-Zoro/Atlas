---
kind: lesson
title: not-a-polynomial-and-alpha-algebraic-is-not-used-yet
---
No, it is not in $K[x]$, and your suspicion is right. Substitute a quotient
into a polynomial and you get a quotient back: $h(f(x)/g(x))$ is a rational
function, an element of $K(x)$. That is the creature. It is a perfectly good
object; it is just not a polynomial, so it cannot be the non-zero polynomial
you are hunting for.

Your other question is the better one. $\alpha$ algebraic is **not** used at
this step at all — only $\alpha \notin K$ is. That is why reaching for $h$ here
feels unmotivated: it is unmotivated. $h$ is used later, once $\gamma$ has been
caught, to finish the contradiction. Leave it alone for now.

So do not substitute into anything. Use the equation you already wrote. You
have $\alpha = f(\gamma)/g(\gamma)$ with $g(\gamma) \ne 0$. Multiply both sides
by $g(\gamma)$ and put everything on one side. What you are left with is a
number that equals zero — and that number is some polynomial evaluated at
$\gamma$.

**Your move.** Do that multiplication and name the polynomial it produces:
write out its coefficients in terms of the coefficients of $f$ and $g$, and say
which field those coefficients lie in. Only that. Why it is non-zero is the
next step, not this one.

What it uses:

- $L : K$ an extension — $K$ is a subfield of the field $L$.
- $K(\alpha,\beta)$ — the smallest subfield of $L$ containing $K$, $\alpha$ and $\beta$.
- Simple extension — $L : K$ is simple when $L = K(\gamma)$ for one $\gamma \in L$.
- Algebraic over $K$ — a root of some non-zero polynomial in $K[x]$.
- Transcendental over $K$ — no non-zero polynomial in $K[x]$ has it as a root.
- $K[x]$ — polynomials in $x$ with coefficients in $K$; $K(\alpha)[x]$ allows coefficients from the larger field $K(\alpha)$.
- $K(x)$ — quotients of polynomials; a field, and bigger than $K[x]$.
- Shape of $K(\gamma)$ — every element is $f(\gamma)/g(\gamma)$ for some $f, g \in K[x]$ with $g(\gamma) \ne 0$.

**Exercise 4.10.** $K(\alpha,\beta) : K$ an extension, $\alpha$ algebraic over
$K$ but not in $K$, $\beta$ transcendental over $K$; show $K(\alpha,\beta) : K$
is not simple.

**Again.** Multiply $\alpha = f(\gamma)/g(\gamma)$ through by $g(\gamma)$,
collect on one side, and name the polynomial having $\gamma$ as a root: its
coefficients, and which field they live in.
