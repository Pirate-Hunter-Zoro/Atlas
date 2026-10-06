---
kind: lesson
title: check 12b-aim-at-a-q-equals-a
---
You are stuck because you aimed at the wrong equation. Show $(a+b)^q = a+b$, not $(a+b)^{q-1} = 1$. Then no inverse is needed.

Two things on your page go wrong.

- $a^q = a \iff a^{q-1} = 1$ holds only for $a \neq 0$. At $a = 0$: $0^q = 0$, but $0^{q-1} = 0 \neq 1$. The same trap catches $b = -a$: then $a + b = 0$ and $(a+b)^{-1}$ does not exist.
- $((a+b)^p)^k = (a+b)^{pk}$, not $(a+b)^{p^k}$. The exponent $p^n$ means raising to the $p$-th power $n$ times in a row.

The recipe for closure under $+$: apply the freshman's dream to $(a+b)^p$. Then apply it again to the result, raised to the $p$-th power. After $n$ rounds you have $(a+b)^{p^n}$ written in terms of $a^{p^n}$ and $b^{p^n}$. Make that an induction on $n$. The other closures are shorter.

**Problem 12(b).** Let $p$ be prime, $q = p^n$, and let $E$ be a splitting field of $f(x) = x^q - x$ over $\mathbb{F}_p$. Show that the roots of $f$ form a subfield of $E$. Conclude that this subfield is all of $E$, so $|E| = q$ and $E$ consists of $0$ together with the $(q-1)$-th roots of unity.

What it uses:

- $\mathbb{F}_p$: the field $\mathbb{Z}/p\mathbb{Z}$; $E$ has characteristic $p$.
- Subfield: a subset containing $0$ and $1$, closed under $+$, $-$, $\times$, and inverses of nonzero elements.
- Splitting field: $E$ is generated over $\mathbb{F}_p$ by the roots of $f$, so the only subfield of $E$ containing $\mathbb{F}_p$ and every root of $f$ is $E$ itself.
- Freshman's dream: in characteristic $p$, $(a + b)^p = a^p + b^p$.
- Fermat's little theorem: $a^p = a$ for every $a \in \mathbb{F}_p$.
- 12(a): $f$ has exactly $q$ distinct roots in $E$.
- $(q-1)$-th root of unity: a nonzero $a$ with $a^{q-1} = 1$.

Let $R = \{a \in E : a^q = a\}$. Show that $R$ is a subfield of $E$ containing $\mathbb{F}_p$, working with $a^q = a$ throughout. Then conclude $R = E$, $|E| = q$, and $E = \{0\} \cup \{a : a^{q-1} = 1\}$.
