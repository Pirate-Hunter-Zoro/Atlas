---
kind: correct
title: Both lines land. Part one of 3.17 is closed. Now the units.
---

**Negation.** Correct, and "literally" is the right word for it: $-(p/q)$ has
the same denominator as $p/q$, so the one condition membership looks at is
untouched. Nothing else needed saying.

**$1 \in R$.** Also correct. $1 = (p-1)/(p-1)$ is a legitimate representation
— $p - 1 \neq 0$ because $p > 1$ — and $p \nmid p-1$ because the smallest
positive multiple of $p$ is $p$ itself, which is already bigger than $p-1$.
So the witness works. It is a longer road than $1 = 1/1$ needs, but it is not
a wrong one.

One symbol note, pen only, nothing to redo: you wrote the element as $p/q$,
and $p$ is already the fixed prime in this exercise. In the write-up it
becomes $r/s$.

Four conditions, four lines, all four on your page. **Part one is closed** —
$R$ is a subring of $\mathbb{Q}$. I am writing it up.

---

**Exercise 3.17, part two.** With $p$ a fixed prime and

$$R = \left\{ x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z} \text{ with } s \neq 0 \text{ and } p \nmid s \right\},$$

**determine the units of $R$.**

**Recall.**

- *Unit of a ring $S$:* an element $x \in S$ for which there exists
  $y \in S$ with $xy = 1$. That $y$ is $x^{-1}$, and it must itself lie in
  $S$.
- *The catch:* every nonzero $x \in R$ has an inverse in $\mathbb{Q}$. The
  question is only whether that inverse is in $R$.
- *Membership in $R$:* $x \in R$ iff **at least one** representation $r/s$ of
  $x$ has $p \nmid s$. Equivalently, in lowest terms, $p \nmid s$.
- *Inverse in $\mathbb{Q}$:* $(r/s)^{-1} = s/r$, for $r \neq 0$.
- *$p \nmid m$:* there is no integer $k$ with $m = pk$.
- *Already yours:* $R$ is a subring of $\mathbb{Q}$, with $1 \in R$.

---

**Your move.** Take $p = 3$. These three all lie in $R$:

$$\frac{2}{5}, \qquad \frac{3}{7}, \qquad \frac{9}{4}.$$

Which of them are units of $R$? For each one, write down the inverse and say
whether that inverse is in $R$. One line each — no general claim yet.
