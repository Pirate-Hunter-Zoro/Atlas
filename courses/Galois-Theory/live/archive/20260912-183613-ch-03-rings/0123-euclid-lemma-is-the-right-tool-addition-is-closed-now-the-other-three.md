---
kind: correct
title: You skipped the warm-up and proved it in general. Addition is closed.
---

That is the argument, and it is general: arbitrary $a/b$ and $c/d$ in $R$, sum
$(ad+bc)/(bd)$, and membership decided by the one thing membership depends on,
whether $p$ divides the denominator.

The step you leaned on has a name. **Euclid's lemma:** if $p$ is prime and
$p \mid bd$, then $p \mid b$ or $p \mid d$. That is the only place primality
enters this whole exercise. Your $\Longleftrightarrow$ line is its
contrapositive, and you formed it correctly — negating a disjunction gives a
conjunction, so $p \nmid b$ **and** $p \nmid d$ is what you get, which is
exactly what you had.

The composite case I asked for was going to show you why the word *prime* is
load-bearing: $6 \nmid 2$ and $6 \nmid 3$, but $6 \mid 6$. Non-primes divide
products they divide neither factor of. You did not need it.

One thing you did not write and did not have to: $b \neq 0$. It comes free
here, because $p \mid 0$ for every $p$, so $p \nmid b$ already forbids $b = 0$.
Worth knowing where the side condition went rather than assuming it was
dropped.

Addition is one of four. Here is the whole of part one again.

---

**Exercise 3.17, part one.** With $p$ a fixed prime, show that

$$R = \left\{ x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z} \text{ with } s \neq 0 \text{ and } p \nmid s \right\}$$

is a **subring** of $\mathbb{Q}$.

**Recall.**

- *Subring:* a subset $S \subseteq \mathbb{Q}$ that contains $1$, is closed
  under addition, is closed under negation, and is closed under
  multiplication.
- *Membership in $R$:* $x \in R$ iff **at least one** representation $r/s$ of
  $x$ has $p \nmid s$.
- *$n \mid m$:* $m = nk$ for some integer $k$. *$n \nmid m$:* no such $k$.
- *$p$ prime:* $p > 1$, and its only positive divisors are $1$ and $p$.
- *Euclid's lemma:* $p$ prime and $p \mid bd$ $\Rightarrow$ $p \mid b$ or
  $p \mid d$. Contrapositive: $p \nmid b$ and $p \nmid d$ $\Rightarrow$
  $p \nmid bd$.
- *Arithmetic in $\mathbb{Q}$:* $a/b + c/d = (ad+bc)/(bd)$;
  $-(a/b) = (-a)/b$; $(a/b)(c/d) = ac/(bd)$.
- *Done already:* closure under addition, on the page in front of you.

---

**Your move.** Write the other three conditions: $1 \in R$, closed under
negation, closed under multiplication. Each is one line, and for each one the
only thing to say is what the denominator is and why $p$ does not divide it.
None of the three needs an idea you do not already have on the page.
