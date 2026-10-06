---
kind: lesson
title: check 12c-order-n
---
**Your automorphism page is right, and it is now a clean proof: homomorphism, Fermat fixes $\mathbb{F}_p$, injective, finite so surjective.** No question on the page, so straight on.

One word to add when it goes in the write-up: $(a-b)^p = 0 \Rightarrow a = b$ holds because a field has no zero divisors. I will put that clause in when I transcribe 12(c).

The order is the only piece left. Once it is agreed, all of 12(c) goes into the write-up together.

**Problem 12(c), last piece.** Let $p$ be prime, $q = p^n$, and $E$ a splitting field of $x^q - x$ over $\mathbb{F}_p$. Show that the Frobenius map $\varphi(a) = a^p$ has order exactly $n$.

What it uses:

- $\varphi^m$ means $\varphi$ applied $m$ times, so $\varphi^m(a) = a^{p^m}$.
- Order of $\varphi$: the least $m \geq 1$ with $\varphi^m(a) = a$ for every $a \in E$.
- 12(b): $|E| = q = p^n$, and every $a \in E$ satisfies $a^q = a$.
- Root bound (11(a)): a nonzero polynomial of degree $d$ over a field has at most $d$ roots in it.

Two halves. First, $\varphi^n$ is the identity. Second, for $1 \leq m < n$, $\varphi^m$ is not the identity. For the second, suppose $\varphi^m$ were the identity. Then every element of $E$ is a root of one particular polynomial. Count its roots against its degree.

**Show that $\varphi^n(a) = a$ for every $a \in E$, and that for each $1 \leq m < n$ some $a \in E$ has $\varphi^m(a) \neq a$.**
