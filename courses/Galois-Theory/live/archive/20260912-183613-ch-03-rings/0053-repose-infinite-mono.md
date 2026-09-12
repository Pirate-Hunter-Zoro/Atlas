---
kind: correct
title: Degree 5, $\prod_{k=0}^{4}(x-k)$. Correct — now the exercise.
---

Correct. Five roots cost you degree five, and there was no way to pay less. That
is the whole tool the infinite case needs.

---

**Problem 3.8**, the last clause:

> Suppose that $K$ is a field. If $f = a_{0} + a_{1}x + \cdots + a_{n}x^{n} \in
> K[x]$ and $k \in K$, let $(\Phi(f))(k) = a_{0} + a_{1}k + \cdots + a_{n}k^{n}$.
> Show that $\Phi$ is a ring homomorphism from $K[x]$ to $K^{K}$. Show that if
> $K$ is finite then $\Phi$ is an epimorphism, but not a monomorphism.
> **What happens if $K$ is infinite?**

Definitions and results the statement uses:

- $K^{K}$: all mappings from $K$ to $K$, added and multiplied pointwise; its
  zero is the mapping sending every $k \in K$ to $0$.
- $\Phi \colon K[x] \to K^{K}$ sends $f$ to the mapping $k \mapsto f(k)$, and is
  a ring homomorphism — you proved both halves of that already.
- *Monomorphism:* an injective ring homomorphism.
- $\Ker\Phi = \{h \in K[x] : h(k) = 0 \text{ for every } k \in K\}$.
- A ring homomorphism is injective exactly when $\Ker\Phi = \{0\}$.
- A root of $h$ is a $k \in K$ with $h(k) = 0$; a non-zero $h \in K[x]$ of
  degree $n$ has at most $n$ roots in $K$.
- The zero polynomial is the one with every coefficient $0$.

---

**Your move.** $K$ is an infinite field. Decide whether $\Phi$ is a
monomorphism, and prove the answer you give. This is card 0052's reduction —
one polynomial $h = f - g$ in $\Ker\Phi$ — meeting the degree count you just
did. Only this half; the epimorphism question comes after.
