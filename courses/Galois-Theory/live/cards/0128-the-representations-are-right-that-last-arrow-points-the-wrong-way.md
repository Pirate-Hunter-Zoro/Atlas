---
kind: wrong
title: The representations are right. That last arrow points the wrong way.
---

The margin is where the work is, and the first half of it is exactly
what I asked for:

> $q/n$ is in lowest terms, so all other representations are of the
> form $\dfrac{r \cdot q}{r \cdot n}$

Correct, and that is the sentence that was missing yesterday. You are
now quantifying over *every* fraction equal to $q/n$, which is what
non-membership needs.

**The last line is backwards.** You wrote

> and if $p \mid r \cdot n$, then $p \mid n$

That implication is not one you have, and it is not true as stated:
take $p = 3$, $r = 3$, $n = 1$. Then $p \mid r \cdot n = 3$ while
$p \nmid n$. What you were reaching for is the *other* direction, and
that one is free — you do not need Euclid for it, you need the
definition of divides, once.

You have $p \mid n$ **as the hypothesis**. The denominators are
$r \cdot n$. Go that way.

---

**Exercise 3.17, part two.** With $p$ a fixed prime and

$$R = \left\{ x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z} \text{ with } s \neq 0 \text{ and } p \nmid s \right\},$$

**determine the units of $R$.** The set is
$R^{\times} = \{\, n/q \in R : p \nmid n \,\}$. The $\supseteq$
inclusion is done. For $\subseteq$ you are proving: if $n/q \in R$ is
in lowest terms with $p \mid n$, then $n/q$ is not a unit.

**Recall.**

- *Membership in $R$:* $x \in R$ iff **at least one** representation
  $r/s$ of $x$ has $p \nmid s$.
- *Non-membership:* $x \notin R$ iff **every** representation $r/s$ of
  $x$ has $p \mid s$.
- *Representations:* if $\gcd(q,n) = 1$, the integer fractions equal to
  $q/n$ are exactly the $rq/rn$ for nonzero integers $r$ — your margin
  line.
- *$a \mid b$:* there is an integer $k$ with $b = ak$.
- *Yours already:* the WLOG to lowest terms is legitimate (card 0127);
  the inverse of $n/q$ in $\mathbb{Q}$ is unique, so if $q/n \notin R$
  then $n/q$ has no inverse in $R$; $R$ is a subring of $\mathbb{Q}$
  containing $1$.

---

**Your move.** One line, in the correct direction: from $p \mid n$,
conclude that $p$ divides $r \cdot n$ for every nonzero integer $r$.
Write the integer that witnesses it.

That closes the units, and 3.17 has one part left.
