---
kind: lesson
title: check 11a-root-bound
---
The first half is right. You wrote $n = \operatorname{ord}(g)\,m$, so $g^n = (g^{\operatorname{ord}(g)})^m = 1^m = 1$. That is the whole argument.

Your second-half setup is also right: suppose $d+1$ distinct elements $g_1, \dots, g_{d+1}$ of $K$ all satisfy $g_i^d = 1$. Now stop thinking about groups. Each $g_i$ is a root of one particular polynomial in $K[x]$. Name it, and the root bound below ends the argument in one line.

**Problem 11(a), second half.** Let $K$ be a field and $d \geq 1$. Show that at most $d$ elements $g \in K$ satisfy $g^d = 1$.

What it uses:

- $K[x]$: polynomials with coefficients in $K$.
- A root of $f \in K[x]$ in $K$: an element $a \in K$ with $f(a) = 0$.
- Root bound: a nonzero polynomial of degree $d$ over a field $K$ has at most $d$ distinct roots in $K$.
- Your setup: $g_1, \dots, g_{d+1} \in K$, distinct, with $g_i^d = 1$ for every $i$.

Show that at most $d$ elements $g \in K$ satisfy $g^d = 1$: say which polynomial the $g_i$ are roots of, why it is nonzero of degree $d$, and where the contradiction lands.
