---
kind: wrong
title: The $\Leftarrow$ direction is right. In the $\Rightarrow$ direction, $(x-a)^{-1}$ does not exist.
---

**$\Leftarrow$ is done.** You took $g$ with $g\cdot(x-a) = f$, evaluated at $a$,
and got $f(a) = g(a)\cdot 0 = 0$. That is the whole direction and it is correct.
The bracketing on that line is loose but the intent is unambiguous: evaluation
respects products and sums, so evaluating $g \cdot (x-a)$ at $a$ gives
$g(a)\cdot(a-a)$. Nothing to fix.

**$\Rightarrow$ is not.** Your line is:

> $K$ is a field, so $(x-a)^{-1}$ exists. Take $g = f(x-a)^{-1} \in K[x]$.

$K$ being a field says every non-zero element **of $K$** is a unit. It says
nothing about $K[x]$, which is a different ring — and it is not a field. Your
$g$ has to be an element of $K[x]$, so $(x-a)^{-1}$ has to be one too.

There is a second tell, and it is the louder one. Your argument never uses
$f(a) = 0$. Delete that hypothesis and every line still stands — so if the
argument worked, **every** $f \in K[x]$ would lie in $(x-a)$. A proof that
proves too much has a false step in it.

---

What you have available, all of it yours already:

- *$K[x]$:* polynomials in the indeterminate $x$ with coefficients in $K$. A
  domain, since $K$ is.
- *unit:* $u$ with $uv = 1$ for some $v$ in the **same** ring.
- *$\deg(gh) = \deg g + \deg h$ over a domain* — 3.10.
- *$\deg$ of a non-zero constant is $0$;* the zero polynomial has no degree.
- *$x - a$ has degree $1$:* coefficients $-a$ and $1$.

---

**Your move.** Suppose, for contradiction, that $(x-a)^{-1}$ does exist in
$K[x]$ — that is, there is some $g \in K[x]$ with $g\cdot(x-a) = 1$.

Apply $\deg(gh) = \deg g + \deg h$ to that equation. What would $\deg g$ have to
be, and why is that impossible?

One number, one line.
