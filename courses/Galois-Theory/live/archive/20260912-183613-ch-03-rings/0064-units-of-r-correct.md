---
kind: correct
title: $\{a : a^{-1}$ exists$\}$. Correct — now the line that rules out degree $\geq 1$
---

Correct. The units of $R[x]$ are the constants $a \in R$ that are invertible
**in $R$** — the units of $R$, sitting inside $R[x]$. And your annotation is
the point of the whole exercise: an integral domain does not guarantee
inverses, which is why the answer is *the units of $R$* and not some list of
elements. $\mathbb{Z}$ gives $\pm 1$; $\mathbb{Q}$ gives every non-zero
constant, so yes, $2$ is a unit there with inverse $1/2$. Both are instances of
your one sentence.

That is the answer. It is not yet the argument, and the missing piece is
exactly the line you got wrong two pages ago.

---

**Your move.** Suppose $f \in R[x]$ is a unit, $R$ an integral domain: there is
$g \in R[x]$ with $fg = 1$.

Show $\deg f = 0$.

You have what it takes: $\deg(fg) = \deg f + \deg g$ over an integral domain
(you proved the top coefficient is $a_{n}b_{m} \neq 0$), and $\deg 1 = 0$. Two
or three lines.
