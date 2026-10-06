---
kind: lesson
title: check 9c-sqrt2-in-K
---
All three factorisations in 9(b) are right now, including $\mathbb{Q}(\sqrt{-2})$: $(x^2-1+\sqrt{-2}\,x)(x^2-1-\sqrt{-2}\,x) = (x^2-1)^2 + 2x^2 = x^4+1$. 9(b) is in the write-up with your three lines, and the PDF builds.

Next is 9(c). It has two halves: $\mathbb{Q}(i,\sqrt2) \subseteq K$ needs $i$ and $\sqrt2$ written in terms of $\zeta$, and $K \subseteq \mathbb{Q}(i,\sqrt2)$ needs $\zeta$ written in terms of $i$ and $\sqrt2$. The hard half is getting $\sqrt2$ out of $\zeta$, so do that one first.

**Problem 9(c).** With $\zeta = \zeta_8$ and $K = \mathbb{Q}(\zeta)$, show that $K = \mathbb{Q}(i,\sqrt2)$.

What you need:
- $\zeta = \zeta_8 = e^{2\pi i/8}$, so $\zeta^8 = 1$ and $\zeta^4 = -1$.
- $K = \mathbb{Q}(\zeta)$ is every polynomial in $\zeta$ with rational coefficients.
- $\mathbb{Q}(i,\sqrt2)$ is the smallest field containing $\mathbb{Q}$, $i$ and $\sqrt2$.
- Two fields are equal when each contains the other's generators.
- Euler: $e^{i\theta} = \cos\theta + i\sin\theta$, and $\cos\frac{\pi}{4} = \sin\frac{\pi}{4} = \frac{\sqrt2}{2}$.

Write $\sqrt2$ as a polynomial in $\zeta$ with rational coefficients.
