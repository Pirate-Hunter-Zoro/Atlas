---
kind: lesson
title: open ch05-057-read-the-coefficients
---
We start with Garling 05.7, a direct use of Eisenstein's criterion. Your first job is one small check on $x^3 - 5$.

The plan for this sitting is four problems from the Chapter 5 homework sheet. 05.6 is already done and typeset.
- 05.7: $x^n - p$ is irreducible. It is Eisenstein with one trap, so it goes first.
- 05.4: $f - yg$ is irreducible in $K(y)[x]$. You worked it last time, but no full argument is on file yet.
- 05.8: the real algebraic numbers have infinite degree over $\mathbb{Q}$. It uses 05.7.
- 05.10: two polynomials irreducible over $\mathbb{Q}(i)$. Eisenstein again, in a new ring.

**The exercise (05.7).** Show that if $p$ is a prime number then $x^n - p$ is irreducible in $\mathbb{Q}[x]$.

**The check.** Take $p = 5$ and $n = 3$, so the polynomial is $x^3 - 5 = f_0 + f_1 x + f_2 x^2 + f_3 x^3$.

What you need:
- $f_0, f_1, \dots, f_n$: the coefficients, with $f_i$ the coefficient of $x^i$.
- Eisenstein's criterion: let $f \in \mathbb{Z}[x]$ and $p$ prime. If $p \mid f_i$ for $0 \le i \le n-1$, $p \nmid f_n$, and $p^2 \nmid f_0$, then $f$ is irreducible in $\mathbb{Q}[x]$.
- $a \mid b$: $b = ac$ for some integer $c$.

For $x^3 - 5$, write down $f_0, f_1, f_2, f_3$. Then say which of them 5 divides, and whether 25 divides $f_0$.
