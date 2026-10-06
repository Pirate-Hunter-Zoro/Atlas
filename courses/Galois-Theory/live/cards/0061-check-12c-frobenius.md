---
kind: lesson
title: check 12c-frobenius
---
**12(b) is agreed.** "Includes $1$ and therefore all of $\mathbb{F}_p$" fills the gap. $1 \in R$, and your closure under $+$ gives every sum $1 + 1 + \dots + 1$, which is all of $\mathbb{F}_p$.

I am writing it up with one correction. Your last line says $a^{q-1} = a$; the write-up says $a^{q-1} = 1$ for $a \neq 0$.

**Problem 12(c).** Let $p$ be prime, $q = p^n$, and let $E$ be a splitting field of $x^q - x$ over $\mathbb{F}_p$. Show that the Frobenius map $\varphi(a) = a^p$ is an automorphism of $E$ fixing $\mathbb{F}_p$, and that it has order exactly $n$.

What it uses:

- $E$: by 12(b), $|E| = q$ and every $a \in E$ satisfies $a^q = a$.
- Automorphism of $E$ fixing $\mathbb{F}_p$: a bijection $E \to E$ with $\sigma(a+b) = \sigma(a) + \sigma(b)$, $\sigma(ab) = \sigma(a)\sigma(b)$, and $\sigma(c) = c$ for every $c \in \mathbb{F}_p$.
- Your 12(b) fact: $(a+b)^p = a^p + b^p$ in $E$.
- Fermat's little theorem: $c^p = c$ for every $c \in \mathbb{F}_p$.
- A homomorphism of fields sends $1 \mapsto 1$ and is injective: its kernel is an ideal, and a field has no ideals but $0$ and itself.
- An injective map from a finite set to itself is a bijection.
- $\varphi^m$ means $\varphi$ applied $m$ times, so $\varphi^m(a) = a^{p^m}$.
- Order of $\varphi$: the least $m \geq 1$ with $\varphi^m(a) = a$ for every $a \in E$.
- Root bound (11(a)): a nonzero polynomial of degree $d$ over a field has at most $d$ roots in it.

The recipe has four pieces: $\varphi$ is a homomorphism, $\varphi$ is a bijection, $\varphi$ fixes $\mathbb{F}_p$, and $\varphi$ has order exactly $n$. The last needs two halves: $\varphi^n$ is the identity, and $\varphi^m$ is not the identity for $1 \leq m < n$.

**Show that $\varphi(a) = a^p$ is an automorphism of $E$ fixing $\mathbb{F}_p$, and that $\varphi^n$ is the identity while $\varphi^m$ is not for any $1 \leq m < n$.**
