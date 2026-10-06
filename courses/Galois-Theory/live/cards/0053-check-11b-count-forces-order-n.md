---
kind: lesson
title: check 11b-count-forces-order-n
---
Right: the first half of 11(b) is done. At most $\varphi(d)$ elements of $G$ have order $d$.

One line to add in the write-up. "This group forms all roots of $x^d - 1$" is 11(a) at work: $\langle h \rangle$ gives $d$ distinct roots, and 11(a) allows no more. Then any $g$ of order $d$ has $g^d = 1$, so it is one of those roots, so $g \in \langle h \rangle$. Your list still ends at $h^d$; it stops at $h^{d-1}$.

Now the second half, which is where the identity at the top of your page earns its place.

**Problem 11(b).** Let $K$ be a field and $G \subseteq K^\times$ a finite subgroup of order $n$. Show that $G$ is cyclic.

What it uses:

- $K^\times$: the nonzero elements of $K$ under multiplication.
- $\operatorname{ord}(g)$: the least $k \geq 1$ with $g^k = 1$. By Lagrange's theorem, $\operatorname{ord}(g) \mid n$.
- $N(d)$: the number of elements of $G$ of order exactly $d$.
- First half (yours): $N(d) \leq \varphi(d)$ for every $d \mid n$.
- Euler's function $\varphi(d)$: the number of $k \in \{1, \dots, d\}$ with $\gcd(k, d) = 1$. Note $\varphi(n) \geq 1$.
- The identity you wrote: $\sum_{d \mid n} \varphi(d) = n$.
- Cyclic: $G = \langle g \rangle$ for some $g$, which for $|G| = n$ means some $g$ has order $n$.

Every element of $G$ has exactly one order, and that order divides $n$. Use this to compute $\sum_{d \mid n} N(d)$, compare it with $\sum_{d \mid n} \varphi(d)$, and conclude that $G$ has an element of order $n$, so $G$ is cyclic.
