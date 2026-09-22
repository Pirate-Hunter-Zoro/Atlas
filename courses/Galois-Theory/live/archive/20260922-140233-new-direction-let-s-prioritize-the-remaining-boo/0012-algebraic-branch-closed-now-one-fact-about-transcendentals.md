---
kind: lesson
title: algebraic-branch-closed-now-one-fact-about-transcendentals
---
Right, and that closes the algebraic branch. The hypothesis that breaks is
*$\beta$ transcendental over $K$*, and your chain is the one that breaks it:
$\gamma$ algebraic over $K$ makes $[K(\gamma):K]$ finite, every element of a
finite extension of $K$ is algebraic over $K$, and $\beta$ lies in $K(\gamma)$
because $K(\gamma) = K(\alpha,\beta)$. So $\beta$ would be algebraic, and it is
not. You copied *algebraic in $K$* again in the statement; the word is *over*.

Now the transcendental branch, which is the real half. Suppose $\gamma$ is
transcendental over $K$. The target is $\alpha \in K$, which kills the other
hypothesis. Reaching it needs one fact about transcendental elements, and that
fact is your move.

**Exercise 4.10.** Suppose $K(\alpha, \beta) : K$ is an extension, that
$\alpha$ is algebraic over $K$ but not in $K$, and that $\beta$ is
transcendental over $K$. Show that $K(\alpha, \beta) : K$ is not simple.

**Your move**, a warm-up for that branch and nothing to do with $\alpha$ or
$\beta$. Let $\gamma$ be transcendental over $K$. Show that $\gamma^2$ is
transcendental over $K$. Do it by contradiction: assume some non-zero
$p \in K[x]$ has $p(\gamma^2) = 0$, then build from $p$ a non-zero polynomial
in $K[x]$ that has $\gamma$ as a root. Name that polynomial and say why it is
not the zero polynomial. Two lines.

What it uses:

- $L : K$ an extension — $K$ is a subfield of the field $L$.
- $K(\alpha, \beta)$ — the smallest subfield of $L$ containing $K$, $\alpha$ and $\beta$.
- Simple extension — $L : K$ is simple when $L = K(\gamma)$ for some single $\gamma \in L$.
- Algebraic over $K$ — a root of some non-zero polynomial in $K[x]$.
- Transcendental over $K$ — not algebraic over $K$: no non-zero polynomial in $K[x]$ has it as a root.
- $K[x]$ — polynomials in $x$ with coefficients in $K$.
- $[L:K]$ — the dimension of $L$ as a vector space over $K$.
- The degree fact — if $\gamma$ is algebraic over $K$ then $[K(\gamma):K]$ is finite.
- The membership fact — every element of a finite extension of $K$ is algebraic over $K$.
