---
kind: lesson
title: check 8a-pose
---
Correct. Two distinct automorphisms sharing one $k$ is exactly the pigeonhole contradiction: injectivity of $\sigma\mapsto k$ forces $\sigma_1=\sigma_2$. 7(c) is finished, and the write-up now carries your bound in place of the TODO.

Next is 8(a).

**Problem 8(a).** Let $p\in F[x]$ be irreducible, with roots $\alpha$ and $\beta$ in (possibly different) extensions of $F$. Show there is a unique isomorphism $F(\alpha)\to F(\beta)$ fixing $F$ and sending $\alpha\mapsto\beta$.

The smallest case: $F=\mathbb{Q}$, $p=x^2-2$, $\alpha=\sqrt2$, $\beta=-\sqrt2$. The isomorphism is $a+b\sqrt2\mapsto a-b\sqrt2$. The problem asks why such a map always exists, and why there is only one.

What it uses:

- $F(\alpha)$ is the smallest field containing $F$ and $\alpha$.
- For $\alpha$ algebraic, $F(\alpha)=F[\alpha]$: every element is a polynomial in $\alpha$ with coefficients in $F$.
- $(p)$ is the ideal of multiples of $p$ in $F[x]$. It is maximal because $p$ is irreducible, so $F[x]/(p)$ is a field.
- The evaluation map $F[x]\to F(\alpha)$, $f\mapsto f(\alpha)$, is a ring homomorphism fixing $F$.
- First isomorphism theorem: a surjective ring homomorphism $\phi:R\to S$ gives $R/\ker\phi\cong S$.
- You used the quotient route in 7(b): $F[x]/(p)\cong F(\alpha)$ when $p$ is the minimal polynomial of $\alpha$.

Show there is a unique isomorphism $F(\alpha)\to F(\beta)$ that fixes $F$ and sends $\alpha$ to $\beta$.
