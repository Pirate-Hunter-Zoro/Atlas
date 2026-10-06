---
kind: lesson
title: check 12c-where-things-live
---
**Yes: $\mathbb{F}_p$ is the integers mod $p$, the set $\{0, 1, \dots, p-1\}$ with arithmetic mod $p$.** There is no bigger universe around both. $E$ is the universe.

- $\mathbb{F}_p$ is the field we start from.
- $E$ is built on top of it: $\mathbb{F}_p$ with every root of $x^q - x$ adjoined. So $\mathbb{F}_p \subseteq E$.
- Inside $E$, the copy of $\mathbb{F}_p$ is $0, 1, 1+1, 1+1+1, \dots$, the sums of $1$ you used in 12(b).
- Every element in 12(c) lives in $E$: $a$, $a^p$, $\varphi(a)$, all of them.

Your line $(a^p)^q = (a^q)^p = a^p$ is correct. It shows $a^p$ is again a root. You need less than that: $E$ is a field, so $a^p = a \cdot a \cdots a$ is in $E$ for free. Either way, all it gives is that $\varphi$ is a map $E \to E$. None of the four pieces is done yet.

**Problem 12(c).** Let $p$ be prime, $q = p^n$, and let $E$ be a splitting field of $x^q - x$ over $\mathbb{F}_p$. Show that the Frobenius map $\varphi(a) = a^p$ is an automorphism of $E$ fixing $\mathbb{F}_p$, and that it has order exactly $n$.

What it uses:

- $E$: by 12(b), $|E| = q$ and every $a \in E$ satisfies $a^q = a$.
- Automorphism of $E$ fixing $\mathbb{F}_p$: a bijection $\sigma: E \to E$ with $\sigma(a+b) = \sigma(a) + \sigma(b)$, $\sigma(ab) = \sigma(a)\sigma(b)$, and $\sigma(c) = c$ for every $c \in \mathbb{F}_p$.
- Your 12(b) fact: $(a+b)^p = a^p + b^p$ in $E$.
- Fermat's little theorem: $c^p = c$ for every $c \in \mathbb{F}_p$.
- A homomorphism of fields is injective: its kernel is an ideal, and a field has no ideals but $0$ and itself.
- An injective map from a finite set to itself is a bijection.
- $\varphi^m$ means $\varphi$ applied $m$ times, so $\varphi^m(a) = a^{p^m}$.
- Order of $\varphi$: the least $m \geq 1$ with $\varphi^m(a) = a$ for every $a \in E$.
- Root bound (11(a)): a nonzero polynomial of degree $d$ over a field has at most $d$ roots in it.

Four pieces: $\varphi$ is a homomorphism, $\varphi$ is a bijection, $\varphi$ fixes $\mathbb{F}_p$, and $\varphi$ has order exactly $n$. The last has two halves: $\varphi^n$ is the identity, and $\varphi^m$ is not the identity for $1 \leq m < n$.

**Show that $\varphi(a) = a^p$ is an automorphism of $E$ fixing $\mathbb{F}_p$, and that $\varphi^n$ is the identity while $\varphi^m$ is not for any $1 \leq m < n$.**
