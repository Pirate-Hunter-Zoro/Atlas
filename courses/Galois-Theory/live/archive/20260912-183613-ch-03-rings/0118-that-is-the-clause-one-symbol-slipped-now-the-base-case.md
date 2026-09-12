---
kind: correct
title: That is the clause — $(b-a) \neq 0$ and no zero divisors. One symbol slipped. Now the base case.
---

That is the missing clause, earned. Evaluate $f = (x-a)g$ at $b$, note
$b - a \neq 0$ because $b \neq a$, and since $K$ has no zero divisors the
other factor must vanish. Your sentence at the bottom says exactly the right
thing: a root of $f$ other than $a$ is a root of $g$.

One symbol slipped, in both places. Evaluating at $b$ gives
$f(b) = (b-a)\,g(b)$, so what you conclude is $g(b) = 0$ — not $g(a)$. You
wrote $g(a)$ twice while your words said $b$; I am correcting it in the
write-up, not asking you to redo the line.

So the step is complete: $f$ of degree $n$ with a root $a$ factors as
$(x-a)g$ with $\deg g = n-1$, every root of $f$ is $a$ or a root of $g$, and
if $g$ has at most $n-1$ distinct roots then $f$ has at most $n$. (If $f$ has
no root at all, it has $0 \leq n$ roots and there is nothing to prove.)

An induction with no base case proves nothing. That is the last piece.

---

## Where you are, in full

**3.15 (second half).** $K$ a field, $f \in K[x]$ **non-zero** of degree $n$.
Show $f$ has **at most $n$ distinct roots** in $K$. You are proving it by
induction on $n = \deg f$, and the step is now done.

Available:

- *Degree:* if $f = k_{0} + k_{1}x + \cdots + k_{n}x^{n}$ with $k_{n} \neq 0$
  then $\deg f = n$. The non-zero constants are exactly the polynomials of
  degree $0$.
- *Root:* $a \in K$ is a root of $f$ if $f(a) = 0$.
- *Evaluation:* $f(a) = k_{0} + k_{1}a + \cdots + k_{n}a^{n}$, computed in $K$.
- *"At most $n$ distinct roots"* means: no list of $n+1$ pairwise distinct
  elements of $K$ are all roots of $f$.
- *Roots and factors (yours):* $a$ is a root of $f$ $\iff$ $f = (x-a)g$ for
  some $g \in K[x]$.
- *$\deg(gh) = \deg g + \deg h$* for non-zero $g,h$ over an integral domain
  (yours, 3.10).

---

**Your move.** The base case. One line.

Let $f \in K[x]$ be non-zero of degree $0$, so $f = k_{0}$ with
$k_{0} \in K$, $k_{0} \neq 0$.

How many roots does $f$ have, and why? Say which $b \in K$ could be one.
