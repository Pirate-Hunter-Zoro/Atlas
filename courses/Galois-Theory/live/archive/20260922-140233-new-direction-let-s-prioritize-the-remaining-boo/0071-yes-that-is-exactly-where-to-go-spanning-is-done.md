---
kind: lesson
title: yes-that-is-exactly-where-to-go-spanning-is-done
---
**Yes --- that is exactly where you should be going, and you have just finished
spanning.** Nothing is missing from that line. You wrote
$r = \sum_{i=0}^{n-1} c_i x^i$ and barred it to
$\overline{r} = \sum_{i=0}^{n-1} c_i \overline{x}^{\,i}$, and since
$\overline{g} = \overline{r}$, every element of $A$ is an $F$-combination of
$\overline{1}, \overline{x}, \dots, \overline{x^{n-1}}$. That is half the basis
claim, closed.

One note on your parentheses: $\deg g = m$ is not given and you do not need it.
$g$ is arbitrary, and the bound that does the work is on $r$, not on $g$.

Now independence, the other half. Suppose some $F$-combination of those classes
is $\overline{0}$: take $c_0, \dots, c_{n-1} \in F$ with
$c_0\overline{1} + c_1\overline{x} + \dots + c_{n-1}\overline{x^{n-1}} = \overline{0}$.
Collect them into one polynomial $h = \sum_{i=0}^{n-1} c_i x^i$ in $F[x]$, so the
assumption reads $\overline{h} = \overline{0}$.

Problem 1(a): $F$ a field, $f \in F[x]$ non-constant of degree $n$, $A = F[x]/(f)$;
show $\overline{1}, \overline{x}, \dots, \overline{x^{n-1}}$ is a basis of $A$ over
$F$, so $\dim_F A = n$.

What this uses:

- $F[x]$ --- polynomials in $x$ with coefficients in $F$; $x$ is an indeterminate, never an element of $F$.
- $(f)$ --- all multiples $qf$ with $q \in F[x]$.
- $A = F[x]/(f)$ --- classes $\overline{g} = g + (f)$, equal exactly when the difference is a multiple of $f$.
- $\overline{h} = \overline{0}$ --- means $h - 0 = h$ lies in $(f)$.
- Arithmetic on representatives: $\overline{g} + \overline{h} = \overline{g+h}$ and $c\cdot\overline{g} = \overline{cg}$ for $c \in F$.
- Degrees --- $\deg h \le n-1 < n = \deg f$, or $h = 0$.
- Spanning --- done, above.
- Independence --- the only such $c_0, \dots, c_{n-1}$ are all $0$.

**So: with $h = \sum_{i=0}^{n-1} c_i x^i$ and $\overline{h} = \overline{0}$, tell me
what that says about $h$ and $f$ --- one sentence, no conclusion yet.**
