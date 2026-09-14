---
kind: correct
title: $f = \prod_{k \in K}\delta_{k}$. Correct — the finite case of 3.8 is done.
---

Correct. Take any $c \in K$. The factor $\delta_{c}$ contributes $1$, but $K$ has
at least two elements, so some $k \neq c$ is in the product and $\delta_{k}(c) =
0$ — the whole product dies at $c$. Every $c$, so $\Phi(f) = 0$.

One line your page leaves implicit and I will not write for you: *why $f$ is
non-zero as a polynomial.* It is a product of non-zero polynomials, and that
only forces a non-zero product because $K[x]$ has no zero divisors. Say it.

Cheaper witness, for later: $\prod_{c \in K}(x - c)$ has degree $|K|$ and does
the same job; yours has degree $|K|\bigl(|K|-1\bigr)$. Both are correct answers.

---

**Problem 3.8**, the last clause:

> Suppose that $K$ is a field. If $f = a_{0} + a_{1}x + \cdots + a_{n}x^{n} \in
> K[x]$ and $k \in K$, let $(\Phi(f))(k) = a_{0} + a_{1}k + \cdots + a_{n}k^{n}$.
> Show that $\Phi$ is a ring homomorphism from $K[x]$ to $K^{K}$. Show that if
> $K$ is finite then $\Phi$ is an epimorphism, but not a monomorphism.
> **What happens if $K$ is infinite?**

Definitions the statement uses:

- $K^{K}$: all mappings from $K$ to $K$, added and multiplied pointwise.
- $\Phi \colon K[x] \to K^{K}$ sends $f$ to the mapping $k \mapsto f(k)$.
- *Monomorphism:* an injective ring homomorphism; *epimorphism:* a surjective one.
- $\ker\Phi = \{f \in K[x] : f(k) = 0 \text{ for every } k \in K\}$, and a
  homomorphism is injective exactly when $\ker\Phi = \{0\}$.
- A non-zero $f \in K[x]$ of degree $n$ has at most $n$ roots in $K$.

---

**Your move.** $K$ is now an infinite field — take $K = \mathbb{Q}$ if you want
something to hold. Decide whether $\Phi$ is a monomorphism, and prove the
answer you give. Just that half; the epimorphism half comes after.
