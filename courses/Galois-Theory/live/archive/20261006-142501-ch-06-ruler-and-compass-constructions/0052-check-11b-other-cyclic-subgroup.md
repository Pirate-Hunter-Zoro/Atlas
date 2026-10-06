---
kind: lesson
title: check 11b-other-cyclic-subgroup
---
No: any $h'$ of order $d$ is already a power of $h$, so $\langle h' \rangle = \langle h \rangle$. A second element of order $d$ can exist, but it never builds a second cyclic group of order $d$. Showing that is exactly the step left, and 11(a) is the tool.

The idea. $h'$ and every power of $h$ are roots of the same polynomial, $x^d - 1$. The powers of $h$ already supply $d$ distinct roots. 11(a) caps that polynomial at $d$ roots in $K$. So nothing outside $\langle h \rangle$ is left over for $h'$ to be.

Your case analysis and your count of $\varphi(d)$ inside $\langle h \rangle$ are right. One slip: the list is $1, h, \dots, h^{d-1}$, which is $d$ elements. $h^d = 1$ is the first entry again. That count of exactly $d$ is what the argument leans on.

**Problem 11(b), first half.** Let $K$ be a field and $G \subseteq K^\times$ a finite subgroup of order $n$. Fix $d \mid n$, and suppose $h \in G$ has order $d$.

What it uses:

- $K^\times$: the nonzero elements of $K$ under multiplication.
- $\operatorname{ord}(g)$: the least $k \geq 1$ with $g^k = 1$.
- $\langle h \rangle = \{1, h, \dots, h^{d-1}\}$: the powers of $h$; these are $d$ distinct elements when $\operatorname{ord}(h) = d$.
- Euler's function $\varphi(d)$: the number of $k \in \{1, \dots, d\}$ with $\gcd(k, d) = 1$.
- In a cyclic group $\langle h \rangle$ of order $d$, $h^k$ has order $d$ exactly when $\gcd(k, d) = 1$. So it holds exactly $\varphi(d)$ elements of order $d$.
- 11(a): at most $d$ elements $x \in K$ satisfy $x^d = 1$.

Show that every $g \in G$ with $\operatorname{ord}(g) = d$ lies in $\langle h \rangle$, and conclude that $G$ has at most $\varphi(d)$ elements of order $d$.
