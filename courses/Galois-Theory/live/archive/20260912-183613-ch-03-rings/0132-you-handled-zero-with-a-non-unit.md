---
kind: wrong
title: You patched the hole. The patch uses a $u$ that is not a unit.
---

You added, in the margin:

> If $r/s = 0$, done b/c pick $u = 0$, $k$ any.

So you found the missing case yourself and you put it where it belongs — before
the unit / non-unit split. That is the right instinct and the right place.

**But the lemma does not say "there is $u \in R$".** It says there is a *unit*
$u$ of $R$. Your own criterion, two cards ago, is that $n/q \in R$ is a unit iff
$p \nmid n$. Write $0$ as $0/1$: the numerator is $0$, and $p \mid 0$. So $u = 0$
is not admissible, and the case is not handled — it is still open.

---

**Exercise 3.17, part three.** With $p$ a fixed prime and

$$R = \left\{ x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z},\ s \neq 0,\ p \nmid s \right\},$$

**show that $R$ is a principal ideal domain.**

**Recall.**

- *Integral domain:* commutative ring with $1$, no zero divisors. $R \subseteq \mathbb{Q}$, so that half is free.
- *Unit:* $u \in R$ is a unit if $uv = 1$ for some $v \in R$.
- *Units of $R$ (yours):* $n/q \in R$ is a unit iff $p \nmid n$.
- *Ideal $I$ of $R$:* nonempty, closed under addition, and $rx \in I$ for every $r \in R$, $x \in I$.
- *Principal ideal:* $(c) = \{rc : r \in R\}$. *PID:* every ideal is some $(c)$.
- *Membership in $R$:* $x \in R$ iff **at least one** representation $r/s$ of $x$ has $p \nmid s$.
- *$a \mid b$:* there is an integer $k$ with $b = ak$.
- *The lemma in progress:* for every $x \in R$ with \_\_\_\_\_, there are a unit
  $u$ of $R$ and an integer $k \geq 0$ with $x = u\,p^{k}$.

---

**Your move.** One line.

Suppose $u$ is a unit of $R$ and $k \geq 0$, and $u\,p^{k} = 0$. Derive a
contradiction — you have exactly one fact about $R$ that kills a product being
zero.

Then fill the blank.
