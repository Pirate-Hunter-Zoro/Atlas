---
kind: lesson
title: g-bar-equals-r-bar-lands-now-spell-r-out
---
**That is exactly right.** Barring $g = qf + r$ gives
$\overline{g} = \overline{q}\,\overline{f} + \overline{r}$, and $\overline{f} = \overline{0}$
kills the first term, so $\overline{g} = \overline{r}$. You also carried the $r = 0$
clause into the statement this time. Spanning is now one line from done.

Spend the degree bound. You know $r = 0$ or $\deg r < n$, so $r$ is a polynomial in
$x$ with at most $n$ coefficients. Write those coefficients as
$c_0, c_1, \dots, c_{n-1} \in F$, bar the whole thing, and say what
$\overline{g}$ is a combination of.

Problem 1(a): $F$ a field, $f \in F[x]$ non-constant of degree $n$, $A = F[x]/(f)$;
show $\overline{1}, \overline{x}, \dots, \overline{x^{n-1}}$ is a basis of $A$ over
$F$, so $\dim_F A = n$.

What this uses:

- $F[x]$ --- polynomials in $x$ with coefficients in $F$; $x$ is an indeterminate, never an element of $F$.
- $(f)$ --- all multiples $qf$ with $q \in F[x]$.
- $A = F[x]/(f)$ --- classes $\overline{g} = g + (f)$, equal exactly when the difference is a multiple of $f$.
- $\overline{f} = \overline{0}$ --- the one relation in $A$.
- Arithmetic on representatives: $\overline{g} + \overline{h} = \overline{g+h}$, $\overline{g}\,\overline{h} = \overline{gh}$, and $c\cdot\overline{g} = \overline{cg}$ for $c \in F$.
- Division with remainder --- there are $q, r \in F[x]$ with $g = qf + r$ and $r = 0$ or $\deg r < n$.
- Spanning --- every element of $A$ is an $F$-combination of $\overline{1}, \dots, \overline{x^{n-1}}$.
- Independence --- the only $F$-combination of those classes equal to $\overline{0}$ is the one with every coefficient $0$. Still to come.

**So: write $r$ out in coefficients $c_0, \dots, c_{n-1}$, bar it, and tell me the
$F$-combination that $\overline{g}$ equals.**
