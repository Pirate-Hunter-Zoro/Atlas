---
kind: lesson
title: ch05-058-why-inside-A
---
Not yet. You now write $\mathbb{Q}(\sqrt[n]{2}) \subset A$, but you assert it rather than prove it. That containment is the one line 05.8 is testing.

Your new strict step is fine but unnecessary. $[A : \mathbb{Q}] \ge n$ for every $n$ already gives $\infty$. The $\sqrt[n+1]{2}$ detour also needs its own reason why $\sqrt[n+1]{2} \notin \mathbb{Q}(\sqrt[n]{2})$, so dropping it is shorter.

**The exercise (05.8).** Let $A$ denote the field of real numbers which are algebraic over $\mathbb{Q}$. Show that $[A : \mathbb{Q}] = \infty$.

What you need:
- Algebraic over $\mathbb{Q}$: a root of some nonzero polynomial in $\mathbb{Q}[x]$.
- $A$: the real numbers algebraic over $\mathbb{Q}$. It is a field, and it contains $\mathbb{Q}$.
- $\mathbb{Q}(\alpha)$: the smallest subfield of $\mathbb{C}$ containing $\mathbb{Q}$ and $\alpha$.
- $[L : K]$: the dimension of $L$ as a vector space over $K$.
- 05.7: $x^n - p$ is irreducible in $\mathbb{Q}[x]$ for every prime $p$ and every $n \ge 1$.

**The check.** Why is $\mathbb{Q}(\sqrt[n]{2}) \subseteq A$? First: why is $\sqrt[n]{2}$ real, and which polynomial makes it algebraic? Then: $A$ is a field containing $\mathbb{Q}$ and $\sqrt[n]{2}$. What does "smallest" in the definition of $\mathbb{Q}(\sqrt[n]{2})$ then give you?
