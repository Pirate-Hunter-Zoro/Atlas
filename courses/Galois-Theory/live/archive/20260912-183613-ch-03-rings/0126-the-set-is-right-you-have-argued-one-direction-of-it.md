---
kind: correct
title: The set is right. You have argued one direction of it.
---

You skipped the three instances again and went straight to the general
claim, and the claim is right:

$$R^{\times} = \left\{ \tfrac{n}{q} \in R \; : \; p \nmid n \right\}.$$

That is the correct set. Two things worth knowing about it, both free:
$n \neq 0$ comes for nothing, since $p \mid 0$, so the condition
$p \nmid n$ already throws $0$ out. And the condition does not depend on
which representation you picked — if $n/q = n'/q'$ with $p \nmid q$ and
$p \nmid q'$, then $p \mid n$ forces $p \mid n'$.

**What "so that inverse exists" has earned.** One direction. If
$p \nmid n$, then $(n/q)^{-1} = q/n$ is a fraction whose denominator $n$
is not divisible by $p$, so it lies in $R$, so $n/q$ is a unit. That half
is done.

**What it has not.** The other half — that nothing else is a unit. Your
line is an equality of sets, and an equality of sets is two inclusions.
Nothing on the page yet says why $p \mid n$ *stops* $n/q$ from being a
unit.

---

**Exercise 3.17, part two.** With $p$ a fixed prime and

$$R = \left\{ x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z} \text{ with } s \neq 0 \text{ and } p \nmid s \right\},$$

**determine the units of $R$.**

**Recall.**

- *Unit of $R$:* $x \in R$ such that some $y \in R$ has $xy = 1$. The
  inverse must itself lie in $R$.
- *Membership in $R$:* $x \in R$ iff **at least one** representation
  $r/s$ of $x$ has $p \nmid s$.
- *Therefore non-membership:* $x \notin R$ iff **every** representation
  $r/s$ of $x$ has $p \mid s$. Not one — all of them.
- *The representations of a rational $a/b$:* exactly the fractions
  $ak/bk$ for nonzero integers $k$, together with the sign-flips, all of
  which are of that form.
- *$p \nmid m$:* there is no integer $k$ with $m = pk$.
- *Euclid:* $p$ prime and $p \mid uv$ implies $p \mid u$ or $p \mid v$.
- *Already yours:* $R$ is a subring of $\mathbb{Q}$ containing $1$; and
  every $n/q \in R$ with $p \nmid n$ is a unit.

---

**Your move.** Take $p = 3$ and take the element $9/4$, which is in $R$.
Its only candidate inverse in $\mathbb{Q}$ is $4/9$.

Show that $4/9 \notin R$: not that the denominator $9$ is divisible by
$3$, but that **no** way of writing $4/9$ as a fraction escapes it. Two
or three lines. Nothing general yet.
