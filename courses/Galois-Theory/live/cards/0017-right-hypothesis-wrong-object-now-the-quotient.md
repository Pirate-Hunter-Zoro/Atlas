---
kind: lesson
title: right-hypothesis-wrong-object-now-the-quotient
---
Right hypothesis. $\deg f \ge 1$ — $f$ non-constant — is exactly what forbids
that $f$, and it is the hypothesis you were handed and had not used.

Your sentence describes the wrong object, though. Nothing is wrong with
$f(x) = 1$; it is a perfectly good non-zero polynomial. What breaks is
$q(x) = h(f(x)) = 1 - 1 = 0$, the zero polynomial. The zero polynomial vanishes
at $\gamma$ and at everything else, so it contradicts nothing, and the proof
dies there. With $\deg f \ge 1$ you get $\deg q = \deg h \cdot \deg f \ge 1$,
so $q$ is non-zero, and the contradiction with $\gamma$ transcendental lands.

So the polynomial fact is closed: if $\gamma$ is transcendental over $K$ and
$\deg f \ge 1$, then $f(\gamma)$ is transcendental over $K$.

Now the element 4.10 actually gives you. A general element of $K(\gamma)$ is
not $f(\gamma)$ but a quotient $f(\gamma)/g(\gamma)$, with $f, g \in K[x]$ and
$g(\gamma) \ne 0$. Suppose $K(\alpha,\beta) = K(\gamma)$ with $\gamma$
transcendental over $K$, and write $\alpha = f(\gamma)/g(\gamma)$. Recall
$\alpha \notin K$.

**Your move.** Clear that denominator. Write down one non-zero polynomial,
with coefficients in $K(\alpha)$, that has $\gamma$ as a root — and say why it
is not the zero polynomial. The reason uses $\alpha \notin K$.

What it uses:

- $L : K$ an extension — $K$ is a subfield of the field $L$.
- $K(\alpha,\beta)$ — the smallest subfield of $L$ containing $K$, $\alpha$ and $\beta$.
- Simple extension — $L : K$ is simple when $L = K(\gamma)$ for a single $\gamma \in L$.
- Algebraic over $K$ — a root of some non-zero polynomial in $K[x]$.
- Transcendental over $K$ — no non-zero polynomial in $K[x]$ has it as a root.
- $K[x]$ — polynomials in $x$ with coefficients in $K$; $K(\alpha)[x]$ allows coefficients from the larger field $K(\alpha)$.
- Shape of $K(\gamma)$ — every element is $f(\gamma)/g(\gamma)$ for some $f, g \in K[x]$ with $g(\gamma) \ne 0$.
- The zero polynomial — every coefficient $0$; two polynomials are equal exactly when every coefficient matches.

**Exercise 4.10.** $K(\alpha,\beta) : K$ an extension, $\alpha$ algebraic over
$K$ but not in $K$, $\beta$ transcendental over $K$; show $K(\alpha,\beta) : K$
is not simple.

**Again.** With $\alpha = f(\gamma)/g(\gamma)$ and $\alpha \notin K$: name a
non-zero polynomial in $K(\alpha)[x]$ having $\gamma$ as a root, and say why it
is not the zero polynomial.
