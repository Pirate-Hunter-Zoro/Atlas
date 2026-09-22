---
kind: lesson
title: independence-lands-1a-closed-now-1b
---
**Independence lands, and 1(a) is closed.** $\deg h = \deg g + \deg f \ge n$
against $\deg h \le n-1$ is the collision, and it is exactly right. So yes ---
the question you asked yourself halfway down the page, "but are they linearly
independent?", you then answered.

One line needs a word. You wrote "by assumption $h \neq 0_{F[x]}$", but the
assumption you had stated was $\overline{h} = \overline{0}$, which says nothing
about $h$ itself. What you were using is the contradiction hypothesis, and it
has to be declared before it is leaned on: suppose some $c_i \neq 0$, hence
$h \neq 0$. The write-up now opens the independence half that way, and writes
the zero polynomial as $0$ in $F[x]$, since the field in this problem is $F$.

Problem 1(b): $F$ a field, $f \in F[x]$ non-constant of degree $n$,
$A = F[x]/(f)$. Show that if $A$ is an integral domain, then $A$ is a field.

What this uses:

- integral domain --- a commutative ring with $1 \neq 0$ and no zero divisors, so $\overline{u}\,\overline{v} = \overline{0}$ forces $\overline{u} = \overline{0}$ or $\overline{v} = \overline{0}$.
- field --- every non-zero element has a multiplicative inverse.
- $A = F[x]/(f)$ --- classes $\overline{g} = g + (f)$, equal exactly when the difference lies in $(f)$.
- $\dim_F A = n$ --- 1(a), just closed; $A$ is a finite-dimensional vector space over $F$.
- multiplication by $\overline{g}$ --- the map $T \colon A \to A$ sending $\overline{u}$ to $\overline{g}\,\overline{u}$; it is $F$-linear, the same map as in exercise 4.3.
- rank--nullity --- an $F$-linear map from a finite-dimensional space to itself is injective exactly when it is surjective.

Fix a non-zero $\overline{g} \in A$ and let $T$ be multiplication by
$\overline{g}$.

**One line: why is $T$ injective? Name the hypothesis that gives it. Stop there
--- do not produce the inverse yet.**
