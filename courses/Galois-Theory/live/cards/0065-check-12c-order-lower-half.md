---
kind: lesson
title: check 12c-order-lower-half
---
**Your first half is right: $\varphi^n(a) = a^{p^n} = a^q = a$, because every $a \in E$ is a root of $x^q - x$.** The "unsure" is the second half, so here is the recipe for it.

Suppose $1 \leq m < n$ and $\varphi^m(a) = a$ for every $a \in E$. Written out, that says $a^{p^m} = a$, so $a^{p^m} - a = 0$ for every $a \in E$. So every element of $E$ is a root of the single polynomial
$$g(x) = x^{p^m} - x \in \mathbb{F}_p[x].$$
Now compare two numbers: how many roots $g$ has in $E$, and how many roots the root bound allows it. One of them is $q$. The other is smaller. That is the contradiction.

**Problem 12(c), last piece.** Let $p$ be prime, $q = p^n$, and $E$ a splitting field of $x^q - x$ over $\mathbb{F}_p$. Show that for each $1 \leq m < n$, some $a \in E$ has $\varphi^m(a) \neq a$.

What it uses:

- $\varphi(a) = a^p$, the Frobenius map, so $\varphi^m(a) = a^{p^m}$.
- 12(b): $|E| = q = p^n$.
- Root bound (11(a)): a nonzero polynomial of degree $d$ over a field has at most $d$ roots in it.
- $g(x) = x^{p^m} - x$, the polynomial above.

Three things to write: the degree of $g$ and why $g$ is not the zero polynomial; how many roots $g$ would then have in $E$; and why that number is too big.

**Assuming $\varphi^m$ is the identity on $E$ for some $1 \leq m < n$, count the roots of $g(x) = x^{p^m} - x$ in $E$ against its degree, and conclude that $\varphi$ has order exactly $n$.**
