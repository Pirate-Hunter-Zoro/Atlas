---
kind: note
title: $\deg g = n-1$, and the induction is the right shape. One clause in it is unearned.
---

$\deg g = \deg f - 1 = n - 1$ is right, and the result it comes from is your
own 3.10: $\deg(fg) = \deg f + \deg g$ in an integral domain, applied to
$f = (x-a)g$ with $\deg(x-a) = 1$. (It needs $g \neq 0$, which holds because
$f \neq 0$.)

And you did not stop there — you wrote down the induction, which is the right
proof. "$g$ has at most $n-1$ distinct roots, therefore $f$ has at most $n$"
is exactly the step. Nothing on your page is false.

But look at what that "therefore" is carrying. It is only true if every root
of $f$ is either $a$ itself or a root of $g$ — that is what lets you count
$f$'s roots as $g$'s roots plus one. Right now that is asserted, not shown.
It is the one clause missing, and it is the only place the field hypothesis
does any work in this half.

---

## Where you are, in full

Suppose $f = k_{0} + k_{1}x + \cdots + k_{n}x^{n}$ is a **non-zero** element
of $K[x]$, $K$ a field, with $k_{n} \neq 0$, so $\deg f = n$. An element $a$
of $K$ is a **root** of $f$ if $f(a) = 0$. You are showing $f$ has **at most
$n$ distinct roots**.

You have: $a$ a root $\Rightarrow$ $f = (x-a)\,g$ with $g \in K[x]$ non-zero
and $\deg g = n-1$.

Available:

- *Roots and factors (yours, just proved):* $a$ is a root of $f$ $\iff$
  $f \in (x-a)$ $\iff$ $f = (x-a)g$ for some $g \in K[x]$.
- *$\deg(gh) = \deg g + \deg h$* for non-zero $g,h$ over an integral domain
  (yours, 3.10). A field is an integral domain.
- *Evaluation respects $+$ and $\times$:* if $f = gh$ then
  $f(b) = g(b)\,h(b)$ for every $b \in K$.
- *A field has no zero divisors:* if $b,c \in K$ and $bc = 0$ then $b = 0$ or
  $c = 0$.
- *$b - a = 0$ in $K$ exactly when $b = a$.*
- *"At most $n$ distinct roots"* means: no list of $n+1$ pairwise distinct
  elements of $K$ are all roots of $f$.

---

**Your move.** One line, and it is the missing clause.

Let $b \in K$ be a root of $f$ with $b \neq a$. You have $f = (x-a)\,g$.

Show that $b$ is a root of $g$. Evaluate at $b$, and name the fact about $K$
that finishes it.
