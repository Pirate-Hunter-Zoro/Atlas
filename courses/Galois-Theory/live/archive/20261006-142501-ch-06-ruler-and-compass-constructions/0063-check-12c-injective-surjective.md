---
kind: lesson
title: check 12c-injective-surjective
---
**Injective: $a^p = b^p$ gives $(a-b)^p = 0$, and a field has no zero divisors, so $a = b$.**

- $(a-b)^p = a^p + (-b)^p$, by your 12(b) fact $(x+y)^p = x^p + y^p$.
- $(-b)^p = -b^p$. For odd $p$ the sign comes straight through. For $p = 2$, $-1 = 1$ in $E$.
- So $(a-b)^p = a^p - b^p = 0$.
- In a field, $c^p = 0$ forces $c = 0$, because a product of nonzero elements is never zero.

**Surjective: you never have to solve $a^p = b$. $E$ is finite.** An injective map from a finite set to itself is a bijection. Here $q$ distinct inputs give $q$ distinct outputs, and $E$ has only $q$ elements, so every $b$ is hit.

If you want the $a$ anyway, it exists: $a = b^{p^{n-1}}$. Then $a^p = b^{p^n} = b^q = b$, by 12(b).

Your homomorphism lines are right, and so is the Fermat note. So $\varphi$ is an automorphism of $E$ fixing $\mathbb{F}_p$. Three of the four pieces are done. Only the order is left.

**Problem 12(c), last piece.** Let $p$ be prime, $q = p^n$, and $E$ a splitting field of $x^q - x$ over $\mathbb{F}_p$. Show that the Frobenius map $\varphi(a) = a^p$ has order exactly $n$.

What it uses:

- $\varphi^m$ means $\varphi$ applied $m$ times, so $\varphi^m(a) = a^{p^m}$.
- Order of $\varphi$: the least $m \geq 1$ with $\varphi^m(a) = a$ for every $a \in E$.
- 12(b): $|E| = q = p^n$, and every $a \in E$ satisfies $a^q = a$.
- Root bound (11(a)): a nonzero polynomial of degree $d$ over a field has at most $d$ roots in it.

Two halves. First, $\varphi^n$ is the identity. Second, for $1 \leq m < n$, $\varphi^m$ is not the identity. For the second, suppose it were, and ask which polynomial every element of $E$ would then be a root of.

**Show that $\varphi^n(a) = a$ for every $a \in E$, and that for each $1 \leq m < n$ some $a \in E$ has $\varphi^m(a) \neq a$.**
