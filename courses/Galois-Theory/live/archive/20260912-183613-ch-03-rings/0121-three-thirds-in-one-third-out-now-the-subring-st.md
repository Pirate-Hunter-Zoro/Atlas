---
kind: correct
title: three-thirds-in-one-third-out-now-the-subring-starting-with-sums
---
---
kind: correct
title: $3/3 \in R$, $1/3 \notin R$. Correct — now the subring, starting with sums.
---

Both right, and the reading has landed. $3/3 = 1/1$ and $3 \nmid 1$, so it is
in, even though the printed denominator is $3$. $1/3$ is out.

Your reason — "all representations of $1/3$ fail" — is the right statement, but
it is the thing to be shown, not the showing of it. Here is the half-line that
earns it: $1/3$ is in lowest terms, so every representation of it is $k/3k$ for
some non-zero integer $k$, and $3 \mid 3k$ always. That is what rules out
**every** representation rather than the one in front of you.

So membership is settled. On to the first of the three tasks.

---

**Exercise 3.17, part one.** With $p$ a fixed prime, show that

$$R = \left\{ x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z} \text{ with } s \neq 0 \text{ and } p \nmid s \right\}$$

is a **subring** of $\mathbb{Q}$.

**Recall.**

- *Subring:* a subset $S \subseteq \mathbb{Q}$ containing $1$, closed under
  addition, closed under negation, and closed under multiplication. (Then $S$
  is a ring under the operations it inherits.)
- *$p \nmid s$:* $p$ does not divide $s$ in $\mathbb{Z}$.
- *Membership in $R$:* $x \in R$ iff **at least one** representation $r/s$ of
  $x$ has $p \nmid s$.
- *$p$ prime:* $p > 1$, and its only positive divisors are $1$ and $p$.
- *Adding fractions:* $a/s + b/t = (at + bs)/(st)$.

---

**Your move.** Take $p = 3$, and take these two members of $R$:

$$\frac{2}{5}, \qquad \frac{4}{7}.$$

Write their sum as a single fraction, and say whether that fraction is a
**good** representation — that is, whether $3$ divides the denominator you got.
