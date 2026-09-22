---
kind: lesson
---
Five problems, and **5.7** goes first because Eisenstein's criterion applies to it straight off the page. Then 5.6, which is the same criterion with the coefficients read backwards; then 5.8, which needs 5.7 already in hand; then 5.10; then 5.4 last, which is the hardest. The plan file now says exactly that, and the Chapter 4 worksheet order it used to hold is gone. The write-up file `ch05-homework.tex` now carries all five statements with empty solution regions, and it compiles clean.

**Exercise 5.7.** Show that if $p$ is a prime number then $x^n - p$ is irreducible in $\mathbb{Q}[x]$.

What that leans on:

- *Irreducible in $R[x]$*: $f$ is not a unit, and $f = gh$ in $R[x]$ forces $g$ or $h$ to be a unit.
- *Prime in $R$*: $p$ is nonzero, is not a unit, and $p \mid ab$ implies $p \mid a$ or $p \mid b$.
- *Relatively prime coefficients*: no prime of $R$ divides every one of $f_0, \ldots, f_n$.
- *Eisenstein's criterion* (Theorem 5.2): for $f = f_0 + f_1x + \cdots + f_nx^n$ over an integral domain $R$ with $f_0, \ldots, f_n$ relatively prime, if a prime $p$ of $R$ divides $f_i$ for $0 \le i < n$, does not divide $f_n$, and $p^2$ does not divide $f_0$, then $f$ is irreducible in $R[x]$.
- *Gauss' lemma*: a polynomial of $\mathbb{Z}[x]$ with relatively prime coefficients is irreducible in $\mathbb{Z}[x]$ exactly when it is irreducible in $\mathbb{Q}[x]$.

One thing before you prove it. Here are three polynomials in $\mathbb{Z}[x]$:
$$x^3 - 3, \qquad 2x^3 + 3x + 3, \qquad x^3 + 3x^2 + 9x + 9.$$
Eisenstein's criterion at the prime $p = 3$ applies to two of these and fails for the third. Which one does it fail for, and which of the criterion's conditions is the one that breaks?
