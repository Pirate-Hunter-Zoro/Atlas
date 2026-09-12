---
kind: correct
title: The sum is in $R$, and you checked the right thing. One pair is not closure.
---

The verdict is right: the sum lies in $R$, because its denominator is not
divisible by $3$. And you checked the denominator, which is the whole of what
membership asks.

Two notes before the next step.

One is pen, not thought: $4/7 = 20/35$, not $28/35$, so the sum is $34/35$. The
denominator is still $35$ and $3 \nmid 35$, so nothing you concluded changes. I
will carry $34/35$ into the write-up.

The other is the real one. "Looks like we're closed under addition" is the
thing to be proved, and one pair of numbers cannot prove it. You have shown
$2/5 + 4/7 \in R$. Closure says **every** pair. The general statement is short:
if $a/s$ and $b/t$ are in $R$, their sum is $(at + bs)/(st)$, and that is a good
representation exactly when $p \nmid st$.

So the whole of closure under addition sits on one question: given $p \nmid s$
and $p \nmid t$, why must $p \nmid st$? Before you answer it for $p$, look at
what happens when the divisor is not prime.

---

**Exercise 3.17, part one.** With $p$ a fixed prime, show that

$$R = \left\{ x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z} \text{ with } s \neq 0 \text{ and } p \nmid s \right\}$$

is a **subring** of $\mathbb{Q}$.

**Recall.**

- *Subring:* a subset $S \subseteq \mathbb{Q}$ containing $1$, closed under
  addition, closed under negation, and closed under multiplication.
- *$n \mid m$:* $m = nk$ for some integer $k$. *$n \nmid m$:* no such $k$.
- *Membership in $R$:* $x \in R$ iff **at least one** representation $r/s$ of
  $x$ has $p \nmid s$.
- *Adding fractions:* $a/s + b/t = (at + bs)/(st)$.
- *$p$ prime:* $p > 1$, and its only positive divisors are $1$ and $p$.

---

**Your move.** Forget primes for one line. Take the divisor to be $6$, and take

$$s = 2, \qquad t = 3.$$

Answer three yes/no questions about those numbers:

1. Does $6$ divide $s$?
2. Does $6$ divide $t$?
3. Does $6$ divide $st$?
