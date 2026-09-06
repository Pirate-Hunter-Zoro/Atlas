---
kind: question
title: 3.8, infinite $K$ — the monomorphism half, in full
---

**3.8 (Garling).** Suppose that $K$ is a field. If $f = a_{0} + a_{1}x + \cdots
+ a_{n}x^{n} \in K[x]$ and $k \in K$, let
$$(\Phi(f))(k) = a_{0} + a_{1}k + \cdots + a_{n}k^{n}.$$
Show that $\Phi$ is a ring homomorphism from $K[x]$ to $K^{K}$. Show that if $K$
is finite then $\Phi$ is an epimorphism, but not a monomorphism. **What happens
if $K$ is infinite?**

Everything before the last sentence is done. Of that last sentence, the piece
now owed is one claim:

> $K$ infinite $\Longrightarrow$ $\Phi$ is a monomorphism.

**Your move.** Prove it. This is the reduction you already made — $\ker\Phi = 0$
is what injectivity comes down to — met with the degree ceiling you established
with $x(x-1)(x-2)(x-3)$.

---

What the statement uses, one line each:

- $K^{K}$: all functions $K \to K$, added and multiplied pointwise (3.1).
- $K[x]$: finite sums $\sum_{i} a_{i}x^{i}$; each element has finitely many
  non-zero coefficients.
- $\deg h$: the largest $i$ with $a_{i} \neq 0$. Defined for every $h \neq 0$.
- *Monomorphism:* injective homomorphism.
- $\ker\Phi = \{h \in K[x] : \Phi(h) = 0\}$, the zero of $K^{K}$ being the
  function sending every $k \in K$ to $0$.
- For a homomorphism, injective $\iff$ $\ker\Phi = \{0\}$.
- *Root:* $k \in K$ with $(\Phi(h))(k) = 0$.
- A non-zero $h \in K[x]$ has at most $\deg h$ roots in $K$.

Start from: let $h \in \ker\Phi$ and suppose $h \neq 0$. Then count.
