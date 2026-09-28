---
kind: lesson
title: check minus-two-term
---
Your chain lands on the right equation, but the first step does three jobs at once and only one of them is labelled. You went from $\sigma(\alpha^2-2\alpha+5)$ straight to $\sigma(\alpha^2)-2\sigma(\alpha)+\sigma(5)$, and marked only $\sigma(5)=5$ as "fixes $\mathbb{Q}$".

That first equality is really "adds": $\sigma(\alpha^2-2\alpha+5)=\sigma(\alpha^2)+\sigma(-2\alpha)+\sigma(5)$. Then $\sigma(-2\alpha)$ became $-2\sigma(\alpha)$ with no label. That hidden step is the one to pin down.

The setting, for reference:

- $K=\mathbb{C}$, $F=\mathbb{Q}$, $\sigma(z)=\bar z$ (complex conjugation), $\alpha=1+2i$, a root of $f(x)=x^2-2x+5$.
- "Adds": $\sigma(a+b)=\sigma(a)+\sigma(b)$.
- "Multiplies": $\sigma(ab)=\sigma(a)\sigma(b)$.
- "Fixes $\mathbb{Q}$": $\sigma(c)=c$ for every rational $c$.

Two lines are still owed after this one: $\sigma(\alpha^2)$ becoming $\sigma(\alpha)^2$, and why $\sigma(0)=0$. They come next.

Your move: write $\sigma(-2\alpha)=-2\sigma(\alpha)$ as two equalities, and label each one "adds", "multiplies" or "fixes $\mathbb{Q}$".
