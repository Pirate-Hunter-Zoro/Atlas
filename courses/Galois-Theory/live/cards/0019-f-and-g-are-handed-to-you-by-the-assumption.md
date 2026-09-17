---
kind: lesson
title: f-and-g-are-handed-to-you-by-the-assumption
---
$f$ and $g$ are not chosen by us. They are handed over by the assumption. We
supposed $K(\gamma) = K(\alpha,\beta)$. Now $\alpha$ lives in $K(\alpha,\beta)$,
so $\alpha$ lives in $K(\gamma)$. And every single element of $K(\gamma)$ is a
quotient of two polynomials in $\gamma$ with coefficients in $K$. That is what
$K(\gamma)$ *is*. So the moment you write $\alpha \in K(\gamma)$, some $f$ and
some $g$ in $K[x]$ exist with $\alpha = f(\gamma)/g(\gamma)$ and $g(\gamma) \ne 0$.
You do not know which ones. You do not need to.

Why start there. We want to trap $\gamma$ into being algebraic over $K(\alpha)$,
so we need a non-zero polynomial with coefficients in $K(\alpha)$ that kills
$\gamma$. The only relation we possess between $\alpha$ and $\gamma$ is that
quotient. It is the only raw material in the room.

And what has $\gamma$ as a root is not a new object. It is the line you just
wrote. You have $f(\gamma) = \alpha g(\gamma)$, so $\alpha g(\gamma) - f(\gamma) = 0$.
Read the left side as some polynomial in $x$, with $\gamma$ substituted in.
Write that polynomial down.

What it uses:

- $K(\gamma)$ — the smallest subfield containing $K$ and $\gamma$.
- Shape of $K(\gamma)$ — every element is $f(\gamma)/g(\gamma)$, $f,g \in K[x]$, $g(\gamma) \ne 0$.
- $K[x]$ — polynomials with coefficients in $K$. $K(\alpha)[x]$ — coefficients allowed from $K(\alpha)$.
- $K(\alpha)$ — the smallest subfield containing $K$ and $\alpha$; bigger than $K$ here, since $\alpha \notin K$.
- Algebraic over a field — a root of some non-zero polynomial with coefficients in that field.
- Transcendental over $K$ — no non-zero polynomial in $K[x]$ has it as a root.
- Simple extension — $L : K$ is simple when $L = K(\gamma)$ for a single $\gamma$.

**Exercise 4.10.** $K(\alpha,\beta) : K$ an extension, $\alpha$ algebraic over
$K$ but not in $K$, $\beta$ transcendental over $K$. Show $K(\alpha,\beta) : K$
is not simple.

**Again.** Take $\alpha g(\gamma) - f(\gamma) = 0$ and name the polynomial in
$x$ it comes from: write its coefficients in terms of the coefficients of $f$
and $g$, and say which field those coefficients lie in. Only that.
