---
kind: lesson
title: check 12b-prime-field-inside-r
---
**One gap left: you never show $\mathbb{F}_p \subseteq R$.** The minimality step needs it. $E$ is the smallest subfield containing $\mathbb{F}_p$ *and* the roots, so $R$ must contain both before you can conclude $R = E$.

Everything else on the page is right.

- $-a \in R$: correct, both cases.
- $a^{-1} \in R$: correct.
- Minimality giving $R = E$, then $|E| = q$ from 12(a): correct, once the gap is filled.

One slip in the last line. You wrote $a^q = a \iff a^{q-1} = a$. For $a \neq 0$ it is $a^{q-1} = 1$: cancel one $a$.

Also, your page says $R$ contains $0$ but never says it contains $1$. That is the piece the gap needs.

**Problem 12(b).** Let $p$ be prime, $q = p^n$, and let $E$ be a splitting field of $f(x) = x^q - x$ over $\mathbb{F}_p$. Show that the roots of $f$ form a subfield of $E$. Conclude that this subfield is all of $E$, so $|E| = q$ and $E$ consists of $0$ together with the $(q-1)$-th roots of unity.

What it uses:

- $\mathbb{F}_p$: the field $\mathbb{Z}/p\mathbb{Z} = \{0, 1, 2, \dots, p-1\}$, sitting inside $E$ as the multiples of $1$.
- $R = \{a \in E : a^q = a\}$, the set of roots of $f$ in $E$.
- Subfield: a subset containing $0$ and $1$, closed under $+$, $-$, $\times$, and inverses of nonzero elements.
- Splitting field: the only subfield of $E$ containing $\mathbb{F}_p$ and every root of $f$ is $E$ itself.
- Your closure under $+$: if $a, b \in R$ then $a + b \in R$.
- Fermat's little theorem: $a^p = a$ for every $a \in \mathbb{F}_p$.

Show that $\mathbb{F}_p \subseteq R$. Either route works: show $1 \in R$ and use your closure under $+$, or iterate Fermat $n$ times to get $a^{p^n} = a$.
