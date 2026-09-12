---
kind: note
title: Lowest terms is the right move. "No safe representation" is the thing to prove.
---

You skipped the instance again and wrote the general converse. The
skeleton is the correct one:

> WLOG $n/q$ in lowest terms. If $p \mid n$ then $q/n$ has no safe
> representation, so $q/n \notin R$, and $n/q$ is not a unit.

Every arrow in that points the right way. Three remarks, two of them
free.

**The WLOG is legitimate, and I am giving it to you rather than asking
for it.** Reducing $n/q$ to lowest terms $n'/q'$ keeps both hypotheses:
$q'$ divides $q$, so $p \nmid q'$ survives; and from $nq' = n'q$ with
$p \mid n$ and $p \nmid q$, Euclid gives $p \mid n'$. So the reduced
fraction still has $p$ dividing its numerator. Fine.

**The last step is fine too.** An inverse in $\mathbb{Q}$ is unique, so
$q/n$ is the only candidate; if it is not in $R$, nothing in $R$
multiplies $n/q$ to $1$.

**The middle clause is asserted, not argued.** "$q/n$ has no safe
representation" is the entire content of the converse, and it is the
one sentence you did not write. It is a claim about *all* fractions
equal to $q/n$, and you have not said what those fractions are. This is
the $\exists$-not-$\forall$ point from the other side: to put something
*out* of $R$ you must knock down every representation, not the one in
front of you.

---

**Exercise 3.17, part two.** With $p$ a fixed prime and

$$R = \left\{ x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z} \text{ with } s \neq 0 \text{ and } p \nmid s \right\},$$

**determine the units of $R$.** You have the set,
$R^{\times} = \{\, n/q \in R : p \nmid n \,\}$, and you have the
inclusion $\supseteq$: if $p \nmid n$ then $q/n \in R$ inverts it. What
is left is $\subseteq$ — that $p \mid n$ forces $n/q$ to be a non-unit.

**Recall.**

- *Membership in $R$:* $x \in R$ iff **at least one** representation
  $r/s$ of $x$ has $p \nmid s$.
- *Non-membership:* $x \notin R$ iff **every** representation $r/s$ of
  $x$ has $p \mid s$.
- *Lowest terms:* $a/b$ is in lowest terms when $\gcd(a,b) = 1$.
- *Representations of a lowest-terms fraction:* if $\gcd(a,b) = 1$,
  then the integer fractions equal to $a/b$ are exactly the $ak/bk$ for
  nonzero integers $k$. (True only in lowest terms — this is why the
  WLOG earns its keep.)
- *$p \nmid m$:* there is no integer $k$ with $m = pk$.
- *Euclid:* $p$ prime and $p \mid uv$ implies $p \mid u$ or $p \mid v$.
- *Already yours:* $R$ is a subring of $\mathbb{Q}$ containing $1$; the
  set above is correct; the $\supseteq$ inclusion is proved.

---

**Your move.** Take $n/q \in R$ in lowest terms with $p \mid n$, so
$q/n$ is also in lowest terms.

Write down what an arbitrary fraction equal to $q/n$ looks like, and
say in one line why $p$ divides its denominator. That is the missing
clause. Two lines, no more.
