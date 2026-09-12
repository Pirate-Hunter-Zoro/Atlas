---
kind: wrong
title: $5/2$ and $2/9$ are right. $6/3$ is the one that goes the other way.
---

Two of the three are right. $5/2 \in R$: denominator $2$, and $3 \nmid 2$.
$2/9 \notin R$: in lowest terms it is $2/9$, and every way of writing it is
$2k/9k$, so the denominator always carries a factor of $3$.

$6/3$ is the miniature, and it lies **in** $R$. You read the denominator that
happens to be printed. The condition is not "the $s$ in front of me is not
divisible by $p$" — it is that **there exists** a representation $r/s$ with
$p \nmid s$. And $6/3$ has one:

$$\frac{6}{3} = \frac{2}{1}, \qquad 3 \nmid 1 .$$

So $6/3 = 2 \in R$. This is the same quantifier as card 0086: membership is
$\exists$, not $\forall$. One good representation is enough; a bad one proves
nothing.

Worth seeing what that buys you: every integer is $n/1$, so $\mathbb{Z}
\subseteq R$, and $R$ sits strictly between $\mathbb{Z}$ and $\mathbb{Q}$.

---

**Recall.** For the question below, $p = 3$ and

$$R = \left\{\, x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z} \text{ with } p \nmid s \,\right\}.$$

- *$p \nmid s$:* $p$ does not divide $s$ in $\mathbb{Z}$.
- *Membership in $R$:* $x \in R$ iff **at least one** representation $r/s$ of
  $x$ has $p \nmid s$. Other representations of the same $x$ may fail it.
- *Equal fractions:* $r/s = rk/sk$ for any non-zero integer $k$, and every
  rational has exactly one lowest-terms form up to sign.

---

**Your move.** Same $p = 3$. These two are both written with denominator $3$:

$$\frac{3}{3}, \qquad \frac{1}{3}.$$

Say for each whether it lies in $R$, and in the one case where it does not,
say what stops you finding a good representation.
