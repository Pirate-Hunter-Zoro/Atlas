---
kind: lesson
title: check 11b-cyclic
---
11(a) is right, both halves. The $g_i$ are $d+1$ roots in $K$ of $x^d - 1$, and that breaks the root bound. Your page leaves out two words the argument leans on. The $g_i$ must be distinct, and $x^d - 1$ must be nonzero of degree $d$ (its leading coefficient is $1$). The write-up now states both, and 11(a) is typeset beside your handwriting.

**Problem 11(b).** Let $K$ be a field and $G \subseteq K^\times$ a finite subgroup of order $n$. Show that $G$ is cyclic.

The route: for each divisor $d$ of $n$, count the elements of $G$ of order exactly $d$. Show there are at most $\varphi(d)$ of them. Then the divisor sum below forces an element of order $n$.

What it uses:

- $K^\times$: the nonzero elements of $K$ under multiplication.
- $\operatorname{ord}(g)$: the least $k \geq 1$ with $g^k = 1$.
- Cyclic: some $g \in G$ has $G = \{1, g, \dots, g^{n-1}\}$; equivalently, some $g \in G$ has order $n$.
- Euler's function $\varphi(d)$: the number of $k \in \{1, \dots, d\}$ with $\gcd(k, d) = 1$.
- In a cyclic group $\langle h \rangle$ of order $d$, $h^k$ has order $d$ exactly when $\gcd(k, d) = 1$. So it holds exactly $\varphi(d)$ elements of order $d$.
- Divisor sum: $\sum_{d \mid n} \varphi(d) = n$.
- 11(a): every $g \in G$ has $\operatorname{ord}(g) \mid n$, and at most $d$ elements $g \in K$ satisfy $g^d = 1$.

Show that $G$ is cyclic: prove that for each $d \mid n$, $G$ has at most $\varphi(d)$ elements of order $d$, and then that $G$ has an element of order $n$.
