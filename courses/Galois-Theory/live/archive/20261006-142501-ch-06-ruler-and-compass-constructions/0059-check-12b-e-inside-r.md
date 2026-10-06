---
kind: lesson
title: check 12b-e-inside-r
---
**Your question: how to show $E \subseteq R$.** Use the splitting field, not elements. $R$ is exactly the set of roots of $f$. So once $R$ is a subfield containing $\mathbb{F}_p$, it is a subfield of $E$ containing $\mathbb{F}_p$ and every root of $f$. $E$ is generated over $\mathbb{F}_p$ by those roots, so nothing smaller than $E$ can hold them all. Hence $R = E$. Then 12(a) gives $|E| = |R| = q$.

That argument needs $R$ to be a genuine subfield containing $\mathbb{F}_p$. Your page does not show that yet.

- Closure under $+$: correct. The induction $(a+b)^{p^k} = a^{p^k} + b^{p^k}$ is right; take $k = n$ to get $(a+b)^q = a+b$.
- Closure under $\times$: correct.
- Still missing: $-a \in R$, $a^{-1} \in R$ for $a \neq 0$, and $\mathbb{F}_p \subseteq R$.

The sign needs one case split on $p$. Inverses take a line.

**Problem 12(b).** Let $p$ be prime, $q = p^n$, and let $E$ be a splitting field of $f(x) = x^q - x$ over $\mathbb{F}_p$. Show that the roots of $f$ form a subfield of $E$. Conclude that this subfield is all of $E$, so $|E| = q$ and $E$ consists of $0$ together with the $(q-1)$-th roots of unity.

What it uses:

- $\mathbb{F}_p$: the field $\mathbb{Z}/p\mathbb{Z}$; $E$ has characteristic $p$, so $p \cdot 1 = 0$ in $E$.
- $R = \{a \in E : a^q = a\}$, the set of roots of $f$ in $E$.
- Subfield: a subset containing $0$ and $1$, closed under $+$, $-$, $\times$, and inverses of nonzero elements.
- Splitting field: $E$ is generated over $\mathbb{F}_p$ by the roots of $f$, so the only subfield of $E$ containing $\mathbb{F}_p$ and every root of $f$ is $E$ itself.
- Fermat's little theorem: $a^p = a$ for every $a \in \mathbb{F}_p$.
- 12(a): $f$ has exactly $q$ distinct roots in $E$.
- $(q-1)$-th root of unity: a nonzero $a$ with $a^{q-1} = 1$.

Show that $-a \in R$ (treat $p$ odd and $p = 2$ separately), that $a^{-1} \in R$ for nonzero $a \in R$, and that $\mathbb{F}_p \subseteq R$. Then conclude $R = E$, $|E| = q$, and $E = \{0\} \cup \{a : a^{q-1} = 1\}$.
