---
kind: correct
title: All three land, and $7/4$ is the $k = 0$ one. Now say it for every $x$.
---

$$\frac{45}{7} = \frac{5}{7}\cdot 3^{2}, \qquad \frac{7}{4} = \frac{7}{4}\cdot 3^{0},
\qquad \frac{6}{25} = \frac{2}{25}\cdot 3^{1}.$$

Correct, all three, and each $u$ really is a unit: $3 \nmid 5$, $3 \nmid 7$,
$3 \nmid 2$. You pulled every factor of $3$ out of the numerator and what was
left was a unit. That is the whole engine of part three.

---

**Exercise 3.17, part three.** With $p$ a fixed prime and

$$R = \left\{ x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z},\ s \neq 0,\ p \nmid s \right\},$$

**show that $R$ is a principal ideal domain.**

**Recall.**

- *Integral domain:* a commutative ring with $1$ and no zero divisors.
  $R \subseteq \mathbb{Q}$, so this half is free.
- *Ideal $I$ of $R$:* nonempty, closed under addition, and $rx \in I$ for
  every $r \in R$, $x \in I$.
- *Principal ideal:* $(c) = \{ rc : r \in R\}$.
- *Principal ideal domain:* an integral domain in which **every** ideal is
  $(c)$ for some $c$.
- *Membership in $R$:* $x \in R$ iff **at least one** representation $r/s$
  of $x$ has $p \nmid s$.
- *Units of $R$ (yours):* $n/q \in R$ is a unit iff $p \nmid n$.
- *$a \mid b$:* there is an integer $k$ with $b = ak$.

---

**Your move.** One statement, in general, no ideals yet.

Let $x \in R$ with $x \neq 0$. Show that

$$x = u \cdot p^{k}$$

for some unit $u$ of $R$ and some integer $k \geq 0$.

Start from a representation $x = r/s$ with $p \nmid s$, and do to $r$ what you
just did to $45$, $7$ and $6$. Say what $u$ is, say what $k$ is, and say why
your $u$ is a unit.
