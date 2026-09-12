---
kind: correct
title: $f = 3\delta_{0} + \delta_{3}$. Correct — that is the epimorphism.
---

Right, and the evaluation is the whole reason it works: at $x = 3$ the first
term contributes $3\delta_{0}(3) = 3\cdot 0 = 0$ and the second contributes
$\delta_{3}(3) = 1$, so only the term built at $3$ survives. Every other point
is killed by its own $\delta$.

That surviving-term argument is the epimorphism. Now write it for an arbitrary
$h$.

---

**Problem 3.8**, the part you are now answering:

> Suppose that $K$ is a field. If $f = a_{0} + a_{1}x + \cdots + a_{n}x^{n} \in
> K[x]$ and $k \in K$, let $(\Phi(f))(k) = a_{0} + a_{1}k + \cdots + a_{n}k^{n}$.
> Show that if $K$ is **finite** then $\Phi$ is an **epimorphism**.

Definitions the statement uses:

- $K^{K}$: all mappings from $K$ to $K$, added and multiplied pointwise.
- $\Phi \colon K[x] \to K^{K}$ sends $f$ to the mapping $k \mapsto f(k)$.
- *Epimorphism:* a surjective ring homomorphism — for every $h \in K^{K}$ there
  is some $f \in K[x]$ with $\Phi(f) = h$.
- $\delta_{c} \in K[x]$, for $c \in K$: $\delta_{c}(c) = 1$ and
  $\delta_{c}(a) = 0$ for every other $a \in K$. You built these by hand over
  $\Fq{3}$ and $\Fq{5}$; $K$ finite is what lets you form the product over all
  the other points.

---

**Your move.** Let $K$ be a finite field and let $h \in K^{K}$ be arbitrary.
Write down an $f \in K[x]$ built from the $\delta_{c}$, and then take an
arbitrary $k \in K$ and show $(\Phi(f))(k) = h(k)$ — saying which term of the
sum survives at $k$ and why the rest vanish.
