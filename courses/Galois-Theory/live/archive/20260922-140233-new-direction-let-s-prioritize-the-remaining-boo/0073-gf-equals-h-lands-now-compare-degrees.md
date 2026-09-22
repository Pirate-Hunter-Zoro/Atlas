---
kind: lesson
title: gf-equals-h-lands-now-compare-degrees
---
**$gf = h$ is exactly right, and it is the whole lever.** No bars, a quantifier,
a statement about two polynomials in $F[x]$. Everything above it stands too:
$\overline{g} = \overline{r}$, $r$ spelled out, spanning closed.

One thing to tidy in the line before it. You wrote $\overline{h} = \overline{f}$
before correcting to $h \in (f)$; only the second is worth anything, since
$\overline{f}$ is always $\overline{0}$.

Now degrees. You have $h = gf$ with $\deg f = n$, and you also know $h$ is a
combination of $\overline{1}, \dots, \overline{x^{n-1}}$, so $\deg h \le n-1$.
Those two facts are about to collide.

Problem 1(a): $F$ a field, $f \in F[x]$ non-constant of degree $n$,
$A = F[x]/(f)$; show $\overline{1}, \overline{x}, \dots, \overline{x^{n-1}}$
is a basis of $A$ over $F$, so $\dim_F A = n$.

What this uses:

- $F[x]$ --- polynomials in $x$ with coefficients in $F$; $x$ is an indeterminate.
- $(f)$ --- the multiples of $f$, that is all $qf$ with $q \in F[x]$.
- $A = F[x]/(f)$ --- classes $\overline{g} = g + (f)$; equal exactly when the difference lies in $(f)$.
- $h = \sum_{i=0}^{n-1} c_i x^i$ --- your polynomial, $c_0, \dots, c_{n-1} \in F$, so $\deg h \le n-1$ unless $h = 0$.
- $g \in F[x]$ --- the witness you just produced, with $gf = h$.
- $\deg$ --- degree of a non-zero polynomial; the zero polynomial has no degree.
- Degrees add: for non-zero $p, q$ in $F[x]$ over a field, $\deg(pq) = \deg p + \deg q$.
- Spanning --- closed.
- Independence --- open: show every $c_i$ is $0$.

**So: suppose $g \neq 0$ and write down $\deg(gf)$ in terms of $\deg g$ and $n$.
One line. Do not conclude anything yet --- just the degree.**
