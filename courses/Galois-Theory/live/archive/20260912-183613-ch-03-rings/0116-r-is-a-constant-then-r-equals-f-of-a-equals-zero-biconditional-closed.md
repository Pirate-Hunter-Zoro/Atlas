---
kind: correct
title: A constant, then $r = f(a) = 0$. Correct — the biconditional is closed. Now the root count.
---

That is the construction, and you went a step past what I asked for. $r = 0$ or
$\deg r < 1$ leaves $r$ a constant; substituting $a$ kills the $(x-a)$ factor
and strands $r$ alone on the right; so $r = f(a) = 0$ and $f = (x-a)q$. The $g$
is produced, not merely asserted to exist. Your contradiction framing works
this time, and for the reason it failed last time: there is now an equation on
the page for it to bite on.

**One notation fix, which I am making in the write-up.** Your line reads
$f(a) = 0 = (x-a)q + r$. The left side is a number in $K$; the right side is
still a polynomial, with an $x$ in it. Once you evaluate, $x$ becomes $a$
*everywhere*:

$$f(a) = (a-a)\,q(a) + r = 0 \cdot q(a) + r = r.$$

Same three steps you wrote, with $q$ evaluated too and no surviving $x$.

**Both directions of the biconditional are done.** Transcribing it now.

---

## 3.15, second half — in full

Suppose $f = k_{0} + k_{1}x + \cdots + k_{n}x^{n}$ is a **non-zero** element of
$K[x]$, $K$ a field, with $k_{n} \neq 0$ — so $\deg f = n$. An element $a$ of
$K$ is a **root** of $f$ if $f(a) = 0$.

Show that $f$ has **at most $n$ distinct roots**.

What you have available:

- *The half you just proved:* $a$ is a root of $f$ $\iff$ $f \in (x-a)$ $\iff$
  $f = (x-a)\,g$ for some $g \in K[x]$.
- *$\deg(gh) = \deg g + \deg h$* whenever $g, h$ are non-zero in $R[x]$ and $R$
  is an integral domain — yours, from 3.10. A field is an integral domain, so
  this holds in $K[x]$.
- *$\deg(x-a) = 1$;* a non-zero constant has degree $0$; the zero polynomial
  has no degree.
- *$K$ has no zero divisors:* if $b, c \in K$ and $bc = 0$ then $b = 0$ or
  $c = 0$. In particular $b - a \neq 0$ whenever $b \neq a$ in $K$.
- *Evaluation at a point respects $+$ and $\times$:* if $f = gh$ then
  $f(b) = g(b)\,h(b)$, and if $f = g + h$ then $f(b) = g(b) + h(b)$.
- *"At most $n$ distinct roots"* means: there is no list of $n+1$ pairwise
  distinct elements of $K$ all of which are roots of $f$.

---

**Your move.** One line, and it is the whole engine of this half.

$f$ is non-zero of degree $n$, and $a$ is a root, so by the half you just
proved $f = (x-a)\,g$ for some $g \in K[x]$.

What is $\deg g$? Name the number and name the result you got it from.
