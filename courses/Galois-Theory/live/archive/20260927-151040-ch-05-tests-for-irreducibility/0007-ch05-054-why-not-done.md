---
kind: question
title: ch05-054-why-not-done
---
Your proof is one line short, and your own answer just showed which line. Line 3 of your proof says $a, b_0, b_1 \in K[x]$. The problem only gave you $a, b \in K(y)[x]$, and those can have $y$ in a denominator, like $\tfrac{1}{y}x$ did.

Your rescaling was right. With $c = y$ you got $x$ and $x + 1$, and both are in $\mathbb{Q}[x][y]$. Neither is a unit of $\mathbb{Q}(y)[x]$, because both have degree $1$ in $x$. That last fact is what the proof needs: rescaling moved the factors into polynomials without touching their degree in $x$.

This always works, and the result that says so is Gauss's lemma, used with $R = K[y]$. Once you cite it, line 3 is earned and the rest of your proof runs unchanged. That is the whole gap.

Everything it uses:

- $K(y)$ — rational functions in $y$ over $K$: ratios $p/q$ with $p, q \in K[y]$, $q \neq 0$.
- $K(y)[x]$ — polynomials in $x$ with coefficients in $K(y)$.
- $K[x][y]$ — polynomials in $x$ and $y$ with coefficients in $K$, no denominators; the same ring as $K[y][x]$.
- unit of $K(y)[x]$ — a nonzero element of $K(y)$, that is, degree $0$ in $x$.
- Gauss's lemma, over $R = K[y]$ — $K[y]$ is a unique factorisation domain with fraction field $K(y)$. If $h \in K[y][x]$ and $h = ab$ with $a, b \in K(y)[x]$, there is a nonzero $c \in K(y)$ with $ca$ and $c^{-1}b$ both in $K[y][x]$.
- degree in $x$ — multiplying by a nonzero $c \in K(y)$ does not change it.

So: suppose $f - yg = ab$ with $a, b \in K(y)[x]$ and $a$ not a unit. Use Gauss's lemma to replace $a, b$ by factors in $K[x][y]$, and say in one line why the new $a$ is still not a unit of $K(y)[x]$.
