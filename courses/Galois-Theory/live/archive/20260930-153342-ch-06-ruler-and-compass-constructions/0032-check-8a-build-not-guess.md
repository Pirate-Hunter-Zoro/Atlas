---
kind: lesson
title: check 8a-build-not-guess
---
You do not have to invent the map. You build it by chaining two isomorphisms you already know:
$$F(\alpha)\;\cong\;F[x]/(p)\;\cong\;F(\beta).$$
Going left to right, $\alpha$ goes to the class of $x$, and the class of $x$ goes to $\beta$. Compose them and you have your $\sigma$. So the existence proof is not "find an example" — it is "show each link in the chain is an isomorphism". The link you already did in 7(b) is the left one. The right one is the same argument with $\beta$ in place of $\alpha$.

(One slip on your page: in the toy case the map is $a+b\sqrt2\mapsto a-b\sqrt2$, not $a+bi\mapsto a-bi$. Same idea, different number.)

The one thing a link needs is this. Evaluation at $\beta$, $f\mapsto f(\beta)$, has kernel exactly $(p)$. Then the first isomorphism theorem gives $F[x]/(p)\cong F(\beta)$. Try it on the toy case.

**Your move.** Take $F=\mathbb{Q}$, $p=x^2-2$, $\beta=-\sqrt2$. Which polynomials $f\in\mathbb{Q}[x]$ have $f(-\sqrt2)=0$? Say why they are all multiples of $x^2-2$, and not something smaller.

**Problem 8(a).** Let $p\in F[x]$ be irreducible, with roots $\alpha$ and $\beta$ in (possibly different) extensions of $F$. Show there is a unique isomorphism $F(\alpha)\to F(\beta)$ fixing $F$ and sending $\alpha\mapsto\beta$.

What it uses:

- $F(\beta)$ is the smallest field containing $F$ and $\beta$; for $\beta$ algebraic, every element is a polynomial in $\beta$ with coefficients in $F$.
- $(p)$ is the ideal of all multiples of $p$ in $F[x]$.
- Evaluation at $\beta$: the ring homomorphism $F[x]\to F(\beta)$, $f\mapsto f(\beta)$. It fixes $F$ and is onto.
- Kernel: the set of $f$ that evaluation sends to $0$.
- First isomorphism theorem: a surjective ring homomorphism $\phi:R\to S$ gives $R/\ker\phi\cong S$.
- $F[x]$ is a principal ideal domain: every ideal is the set of multiples of one polynomial.
- Uniqueness is already yours: an $F$-map out of $F(\alpha)$ is fixed by where it sends $\alpha$.

For $\beta=-\sqrt2$ over $\mathbb{Q}$: which polynomials vanish at $-\sqrt2$, and why is every one of them a multiple of $x^2-2$?
