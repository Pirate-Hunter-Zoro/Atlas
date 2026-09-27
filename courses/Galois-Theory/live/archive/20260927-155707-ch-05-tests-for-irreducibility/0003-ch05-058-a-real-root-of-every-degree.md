---
kind: lesson
title: ch05-058-a-real-root-of-every-degree
---
05.7 is agreed correct. Every $a_i$ with $1 \le i \le n-1$ is $0 = p \cdot 0$, so all four Eisenstein conditions hold. Your argument is now in the 05.7 solution region of the ch05 homework, with your finished page filed beside it, and it compiles cleanly.

05.8 comes next rather than 05.4, because 05.8 runs straight off what you just proved.

**The exercise (05.8).** Let $A$ denote the field of real numbers which are algebraic over $\mathbb{Q}$. Show that $[A : \mathbb{Q}] = \infty$.

What you need:
- Algebraic over $\mathbb{Q}$: a root of some nonzero polynomial in $\mathbb{Q}[x]$.
- $[L : K]$: the dimension of $L$ as a vector space over $K$.
- Tower law: if $K \subseteq M \subseteq L$ are fields, then $[L : K] = [L : M]\,[M : K]$.
- Simple extensions: if $\alpha$ is algebraic over $\mathbb{Q}$ with minimal polynomial $m$, then $[\mathbb{Q}(\alpha) : \mathbb{Q}] = \deg m$.
- Minimal polynomial: a monic irreducible polynomial in $\mathbb{Q}[x]$ with $\alpha$ as a root is the minimal polynomial of $\alpha$.
- 05.7: $x^n - p$ is irreducible in $\mathbb{Q}[x]$ for every prime $p$ and every $n \ge 1$.

**The check.** Take $\alpha = \sqrt[n]{2}$, the positive real $n$-th root of $2$. Is $\alpha$ in $A$? What is $[\mathbb{Q}(\alpha) : \mathbb{Q}]$, and which fact above gives it?
