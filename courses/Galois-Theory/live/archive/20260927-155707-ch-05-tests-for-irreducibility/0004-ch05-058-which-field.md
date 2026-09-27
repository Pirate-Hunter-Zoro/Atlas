---
kind: lesson
title: ch05-058-which-field
---
Almost. Your argument proves the result for $\overline{\mathbb{Q}}$, all algebraic numbers, but 05.8 is about $A$, the real ones only. Those are different fields: $i$ is in $\overline{\mathbb{Q}}$ and not in $A$.

The rest is right. $x^n - 2$ is irreducible by 05.7 with $p = 2$, so $[\mathbb{Q}(\sqrt[n]{2}) : \mathbb{Q}] = n$. A subfield of degree $n$ forces $[A : \mathbb{Q}] \ge n$, and $n$ was arbitrary. Proving it for $\overline{\mathbb{Q}}$ does not give it for the smaller field $A$. The implication runs the other way.

So the one missing line is why $\mathbb{Q}(\sqrt[n]{2})$ sits inside $A$ at all.

**The exercise (05.8).** Let $A$ denote the field of real numbers which are algebraic over $\mathbb{Q}$. Show that $[A : \mathbb{Q}] = \infty$.

What you need:
- Algebraic over $\mathbb{Q}$: a root of some nonzero polynomial in $\mathbb{Q}[x]$.
- $A$: the real numbers algebraic over $\mathbb{Q}$. It is a field.
- $\overline{\mathbb{Q}}$: all complex numbers algebraic over $\mathbb{Q}$. It contains $A$.
- $\mathbb{Q}(\alpha)$: the smallest field containing $\mathbb{Q}$ and $\alpha$.
- $[L : K]$: the dimension of $L$ as a vector space over $K$.
- 05.7: $x^n - p$ is irreducible in $\mathbb{Q}[x]$ for every prime $p$ and every $n \ge 1$.

**The check.** Why is $\mathbb{Q}(\sqrt[n]{2}) \subseteq A$? Name the two properties of $\sqrt[n]{2}$ that put it in $A$. Then say why the whole field $\mathbb{Q}(\sqrt[n]{2})$ lands in $A$ too.
