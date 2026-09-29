---
kind: lesson
title: check 8a-what-the-quotient-is
---
$\mathbb{Q}[x]/(p)$ is just polynomials in $x$ with one extra rule: $x^2 = 2$. That is the whole creature.

Its elements are remainders on division by $x^2-2$, so every one looks like $a+bx$ with $a,b\in\mathbb{Q}$. You add them as usual. You multiply them as usual, then replace every $x^2$ by $2$. For example $x\cdot x = x^2 = 2$.

So it looks exactly like $\mathbb{Q}(\sqrt2)$, with $x$ playing the part of a square root of $2$. The key point: $x$ never says *which* square root. It is only "a thing whose square is $2$". That is why the same quotient maps onto $\mathbb{Q}(\sqrt2)$ by $x\mapsto\sqrt2$ and also by $x\mapsto-\sqrt2$. The quotient is the neutral middle of the chain, and $\sigma$ is "go in by $\alpha$, come out by $\beta$".

(One slip on your page: not *all* $f\in\mathbb{Q}[x]$ have $p$ as a factor, only the ones with $f(-\sqrt2)=0$. Your reason, $p$ irreducible so nothing smaller works, is the right one.)

**Your move.** In $\mathbb{Q}[x]/(x^2-2)$, compute $(1+x)(3-2x)$ and write it as $a+bx$. Then put $x=-\sqrt2$ into your answer and into $(1-\sqrt2)(3+2\sqrt2)$. Do they agree?

**Problem 8(a).** Let $p\in F[x]$ be irreducible, with roots $\alpha$ and $\beta$ in (possibly different) extensions of $F$. Show there is a unique isomorphism $F(\alpha)\to F(\beta)$ fixing $F$ and sending $\alpha\mapsto\beta$.

What it uses:

- $F[x]/(p)$: polynomials over $F$, where two are equal if their difference is a multiple of $p$; in effect, "$p(x)=0$" is imposed.
- $(p)$: the ideal of all multiples of $p$ in $F[x]$.
- Evaluation at $\beta$: the ring homomorphism $F[x]\to F(\beta)$, $f\mapsto f(\beta)$. It fixes $F$ and is onto.
- First isomorphism theorem: a surjective ring homomorphism $\phi:R\to S$ gives $R/\ker\phi\cong S$.
- The chain: $F(\alpha)\cong F[x]/(p)\cong F(\beta)$, with $\alpha\leftrightarrow x\leftrightarrow\beta$.

Compute $(1+x)(3-2x)$ in $\mathbb{Q}[x]/(x^2-2)$ as $a+bx$, then check that $x\mapsto-\sqrt2$ turns it into $(1-\sqrt2)(3+2\sqrt2)$.
