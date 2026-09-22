---
kind: lesson
title: h-bar-equals-f-bar-is-true-and-empty
---
**$\overline{h} = \overline{f}$ is true, and that is the problem with it.**
$f$ is a multiple of itself, so $\overline{f} = \overline{0}$ always ---
for every $f$, in every quotient. Your line therefore says
$\overline{0} = \overline{0}$. It is correct and it carries no information
about $h$.

Everything above it is right. $\overline{g} = \overline{r}$, $r$ spelled out,
spanning closed, and independence set up with the correct hypothesis
$\overline{h} = \overline{0}$.

The statement you want lives in $F[x]$, not in $A$. Bars hide exactly the thing
independence needs: the degree of $h$. So unbar it. $\overline{h} = \overline{0}$
means $h - 0 \in (f)$, and $(f)$ has a definition you can write out with a
quantifier.

Problem 1(a): $F$ a field, $f \in F[x]$ non-constant of degree $n$,
$A = F[x]/(f)$; show $\overline{1}, \overline{x}, \dots, \overline{x^{n-1}}$
is a basis of $A$ over $F$, so $\dim_F A = n$.

What this uses:

- $F[x]$ --- polynomials in $x$ with coefficients in $F$; $x$ is an indeterminate.
- $(f)$ --- the set of all $qf$ with $q \in F[x]$; the multiples of $f$.
- $A = F[x]/(f)$ --- classes $\overline{g} = g + (f)$; $\overline{g} = \overline{h}$ exactly when $g - h \in (f)$.
- $\overline{0}$ --- the class of $0$, which is $(f)$ itself; so $\overline{h} = \overline{0}$ means $h \in (f)$.
- $h = \sum_{i=0}^{n-1} c_i x^i$ --- your polynomial, with $c_0, \dots, c_{n-1} \in F$.
- $\deg h \le n - 1 < n = \deg f$, unless $h = 0$.
- Spanning --- closed last turn.
- Independence --- still open: show those $c_i$ are all $0$.

**So: rewrite $\overline{h} = \overline{0}$ as a statement about $h$ and $f$
inside $F[x]$, with no bars in it. One sentence, and do not draw a conclusion
from it yet.**
