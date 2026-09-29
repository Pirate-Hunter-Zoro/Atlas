---
kind: lesson
title: check 8a-full
---
Correct: $(1+x)(3-2x) = -1+x$, and both routes give $-1-\sqrt2$ under $x\mapsto-\sqrt2$.

That is the whole mechanism of 8(a). The quotient computes without knowing which root $x$ is. Evaluation at a root then turns the quotient's answer into that root's answer. Nothing about $\sqrt2$ was special, so now do it in general.

**Problem 8(a).** Let $p\in F[x]$ be irreducible, with roots $\alpha$ and $\beta$ in (possibly different) extensions of $F$. Show there is a unique isomorphism $\sigma: F(\alpha)\to F(\beta)$ fixing $F$ and sending $\alpha\mapsto\beta$.

What it uses:

- $(p)$: the ideal of all multiples of $p$ in $F[x]$.
- $F[x]/(p)$: polynomials over $F$ with "$p(x)=0$" imposed; two are equal if they differ by a multiple of $p$.
- $\mathrm{ev}_\beta: F[x]\to F(\beta)$, $f\mapsto f(\beta)$: a ring homomorphism that fixes $F$ and is onto.
- $\ker \mathrm{ev}_\beta = (p)$: $p(\beta)=0$, and $p$ irreducible means no smaller-degree polynomial vanishes at $\beta$. The same holds for $\alpha$.
- First isomorphism theorem: a surjective ring homomorphism $\phi:R\to S$ gives $R/\ker\phi\cong S$, via $r+\ker\phi\mapsto\phi(r)$.
- An automorphism, or isomorphism, fixing $F$ is determined by where it sends a generator (you proved this in 7).

Prove 8(a): build $\sigma: F(\alpha)\to F(\beta)$ from the chain $F(\alpha)\cong F[x]/(p)\cong F(\beta)$, check it fixes $F$ and sends $\alpha\mapsto\beta$, and show it is the only such map.
