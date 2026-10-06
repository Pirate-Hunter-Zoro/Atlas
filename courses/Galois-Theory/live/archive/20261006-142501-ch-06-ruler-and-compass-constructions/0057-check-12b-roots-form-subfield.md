---
kind: lesson
title: check 12b-roots-form-subfield
---
12(a) is right, and it is now written up. You showed $h(x) = x^{q-1} - 1$ has no repeated root: $h'(\alpha) = 0$ forces $\alpha^{q-2} = 0$, and then $h(\alpha) = -1$. Your reason $q - 1 \equiv -1 \not\equiv 0 \pmod p$ is the right one.

One thing was left unsaid, and the file now says it. The extra root $0$ from the factor $x$ is not among the roots of $h$, because $h(0) = -1$. Without that line, $0$ could in principle be counted twice.

**Problem 12(b).** Let $p$ be prime, $q = p^n$, and let $E$ be a splitting field of $f(x) = x^q - x$ over $\mathbb{F}_p$. Show that the roots of $f$ form a subfield of $E$. Conclude that this subfield is all of $E$, so $|E| = q$ and $E$ consists of $0$ together with the $(q-1)$-th roots of unity.

What it uses:

- $\mathbb{F}_p$: the field $\mathbb{Z}/p\mathbb{Z}$; $E$ has characteristic $p$.
- Subfield: a subset containing $0$ and $1$, closed under $+$, $-$, $\times$, and inverses of nonzero elements.
- Splitting field: $E$ is generated over $\mathbb{F}_p$ by the roots of $f$, so the only subfield of $E$ containing $\mathbb{F}_p$ and every root of $f$ is $E$ itself.
- Freshman's dream: in characteristic $p$, $(a + b)^p = a^p + b^p$, because $p$ divides $\binom{p}{k}$ for $0 < k < p$.
- Fermat's little theorem: $a^p = a$ for every $a \in \mathbb{F}_p$.
- 12(a): $f$ has exactly $q$ distinct roots in $E$.
- $(q-1)$-th root of unity: a nonzero $a$ with $a^{q-1} = 1$.

Let $R = \{a \in E : a^q = a\}$. Show that $R$ is a subfield of $E$ containing $\mathbb{F}_p$, then conclude $R = E$, $|E| = q$, and $E = \{0\} \cup \{a : a^{q-1} = 1\}$.
