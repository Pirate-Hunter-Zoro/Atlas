---
kind: lesson
title: ch05-057-middle-coefficients
---
Three of the four Eisenstein conditions are right, but the proof skips the middle coefficients $a_1, \dots, a_{n-1}$. Eisenstein needs $p$ to divide every one of them, and your page never says so.

One small slip: $a_0 = -p$, not $p$. It does no harm, because $p \mid -p$ and $p^2 \nmid -p$ just as before.

**The exercise (05.7).** Show that if $p$ is a prime number then $x^n - p$ is irreducible in $\mathbb{Q}[x]$.

What you need:
- $a_0, a_1, \dots, a_n$: the coefficients of $x^n - p = a_0 + a_1 x + \dots + a_n x^n$, with $a_i$ the coefficient of $x^i$.
- Eisenstein's criterion: let $f \in \mathbb{Z}[x]$ and $p$ prime. If $p \mid a_i$ for $0 \le i \le n-1$, $p \nmid a_n$, and $p^2 \nmid a_0$, then $f$ is irreducible in $\mathbb{Q}[x]$.
- $a \mid b$: $b = ac$ for some integer $c$.

**The check.** What is $a_i$ for $1 \le i \le n-1$? Using the definition of $a \mid b$ above, show that $p$ divides it.
