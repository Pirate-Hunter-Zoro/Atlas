---
kind: question
title: ch05-057-read-the-coefficients
---
Your 05.6 proof is correct and complete, and it is now typeset in the chapter write-up, `ch05-homework.tex`. The $3 + 6x$ check is skipped; your proof already covers it.

Two slips on your page, both fixed in the file:
- The WLOG line (without loss of generality) now reads $\deg h = \deg f$. With $g = c$ constant, it is $h$ that carries the degree.
- You wrote "$h = \deg m$". The file says $m = \deg h$, matching your $k = \deg g$.

Next is 05.7, Eisenstein's criterion applied straight.

**Problem 05.7.** Show that if $p$ is a prime number then $x^n - p$ is irreducible in $\mathbb{Q}[x]$.

One small thing first. Take $p = 5$ and $n = 3$, so the polynomial is
$$x^3 - 5 = f_0 + f_1 x + f_2 x^2 + f_3 x^3.$$

Everything this uses:
- $f_0, \ldots, f_n$ — the coefficients, $f_i$ multiplying $x^i$. A missing power has coefficient $0$.
- $p \mid a$ — $p$ divides $a$, meaning $a = pb$ for some integer $b$. Every prime divides $0$.
- Eisenstein's criterion — if $f \in \mathbb{Z}[x]$, $p$ divides every coefficient except the leading one $f_n$, $p \nmid f_n$, and $p^2 \nmid f_0$, then $f$ is irreducible in $\mathbb{Q}[x]$.
- irreducible — not a unit, and in every factorisation into two factors one of them is a unit.

Write down $f_0, f_1, f_2, f_3$ for $x^3 - 5$. For each one, say whether $5$ divides it, and whether $25$ divides $f_0$.
