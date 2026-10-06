---
kind: lesson
title: check 11b-at-most-phi
---
Your start counts the wrong set, so it stalls. Supposing $\varphi(d)+1$ elements with $g^d = 1$ cannot contradict 11(a). The root bound allows up to $d$ such elements, and $d \geq \varphi(d)$. The bound has to come from structure: every element of order $d$ lives inside one cyclic group.

The recipe for the first half. Fix $d \mid n$ and split into two cases.

- No element of $G$ has order $d$. Then the count is $0 \leq \varphi(d)$. Done.
- Some $h \in G$ has order $d$. Its powers $1, h, \dots, h^{d-1}$ are $d$ distinct solutions of $x^d = 1$ in $K$. By 11(a) there are at most $d$ solutions, so these are all of them.

The missing step is yours: in the second case, show that every $g \in G$ of order $d$ is a power of $h$. Then the last fact in the list below finishes the count.

**Problem 11(b), first half.** Let $K$ be a field and $G \subseteq K^\times$ a finite subgroup of order $n$. Fix $d \mid n$, and suppose $h \in G$ has order $d$.

What it uses:

- $K^\times$: the nonzero elements of $K$ under multiplication.
- $\operatorname{ord}(g)$: the least $k \geq 1$ with $g^k = 1$.
- $\langle h \rangle = \{1, h, \dots, h^{d-1}\}$: the powers of $h$; these are $d$ distinct elements when $\operatorname{ord}(h) = d$.
- Euler's function $\varphi(d)$: the number of $k \in \{1, \dots, d\}$ with $\gcd(k, d) = 1$.
- In a cyclic group $\langle h \rangle$ of order $d$, $h^k$ has order $d$ exactly when $\gcd(k, d) = 1$. So it holds exactly $\varphi(d)$ elements of order $d$.
- 11(a): at most $d$ elements $x \in K$ satisfy $x^d = 1$.

Show that every $g \in G$ with $\operatorname{ord}(g) = d$ lies in $\langle h \rangle$, and conclude that $G$ has at most $\varphi(d)$ elements of order $d$.
