---
kind: lesson
title: check-quotients
---
Your coefficients are now in $F$, so that fault is fixed and card 0010 is settled. One gap is left: not every $x\in K$ is a polynomial in the $\alpha_i$. No question on the page, so this is grading only.

In $\mathbb{Q}(\sqrt2)$ you get lucky. There $1/(1+\sqrt2)=\sqrt2-1$, a polynomial in $\sqrt2$. That luck comes from $\sqrt2$ being algebraic. Problem 7(b) says nothing about the $\alpha_i$ being algebraic, so your proof may not assume it.

One check, with a transcendental element.

- $F=\mathbb{Q}$, and $t$ is transcendental over $\mathbb{Q}$: no nonzero polynomial over $\mathbb{Q}$ has $t$ as a root.
- $K=\mathbb{Q}(t)$, the smallest field containing $\mathbb{Q}$ and $t$. It contains $1/t$.
- Your line claims $1/t=f(t)$ for some polynomial $f\in\mathbb{Q}[x]$.

Your move: suppose $1/t=f(t)$ for a polynomial $f$ over $\mathbb{Q}$. Multiply through by $t$ and say why that contradicts $t$ being transcendental.
