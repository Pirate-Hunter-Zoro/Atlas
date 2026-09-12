---
kind: correct
title: "\"not a unit\" — correct. The forward direction is done. Now the converse."
---

Correct. $a \nmid 1$ because $a$ is not a unit: $a \mid 1$ would mean $1 = ra$,
which is what being a unit says. That is the clause earning its keep, and the
$\Rightarrow$ direction of 3.11 is finished — no zero divisors, and
$1 + (a) \neq 0 + (a)$. Typesetting it now.

---

**Your move.** The converse, which is the other half of 3.11:

> Suppose $R/(a)$ is an integral domain, where $a \neq 0$ is an element of the
> integral domain $R$. Show that $a$ is prime.

There are two things to establish, matching the two you just used, and they run
in the opposite direction.

- *Prime* (Garling): $a \neq 0$, $a$ not a unit, and $a \mid bc$ implies
  $a \mid b$ or $a \mid c$.
- *Integral domain:* commutative, $1 \neq 0$, no zero divisors — $uv = 0$
  forces $u = 0$ or $v = 0$.
- $R/(a)$: classes $b + (a)$, product $(b+(a))(c+(a)) = bc + (a)$, zero
  $0 + (a)$, one $1 + (a)$.
- $a \mid b$ means $b = ra$ for some $r \in R$.
- *Yours, from rung one:* $b + (a) = 0 + (a)$ if and only if $a \mid b$.

$a \neq 0$ is given, so it is the other two you owe.
