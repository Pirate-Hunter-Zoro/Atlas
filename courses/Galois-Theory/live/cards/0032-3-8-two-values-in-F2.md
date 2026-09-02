---
kind: question
title: 3.8. First, two values in $\mathbb{F}_2$.
---

Next on the sheet is **3.8**, in the book's words:

> Suppose that $K$ is a field. If $f = a_0 + a_1x + \cdots + a_nx^n \in K[x]$ and $k \in K$, let $(\Phi(f))(k) = a_0 + a_1k + \cdots + a_nk^n$. Show that $\Phi$ is a ring homomorphism from $K[x]$ to $K^K$. Show that if $K$ is finite then $\Phi$ is an epimorphism, but not a monomorphism. What happens if $K$ is infinite?

You are not answering that yet.

What the statement uses:

- $K^K$: the set of **all** functions from $K$ to $K$, made a ring by working pointwise — $(g+h)(k) = g(k)+h(k)$ and $(gh)(k) = g(k)h(k)$, with zero the constant function $0$ and identity the constant function $1$.
- $\Phi(f)$ is therefore not a number: it is the *function* sending each $k \in K$ to $f$ evaluated at $k$.
- *Epimorphism:* a surjective homomorphism. *Monomorphism:* an injective one.
- $\mathbb{F}_2 = \{0, 1\}$, the field with two elements, where $1 + 1 = 0$.

**Your move.** Take $K = \mathbb{F}_2$ and $f = x^2 + x \in \mathbb{F}_2[x]$. Write down the function $\Phi(f)$ by giving both of its values: $(\Phi(f))(0)$ and $(\Phi(f))(1)$.
