---
kind: correct
title: You were not stuck. "How can we not have at least degree 4?" — you can't, and that is the answer.
---

Read your own last line back. *How can we not have at least degree 4?* You
can't. There is no non-zero cubic with those four roots, my claim was false, and
you are the one who refuted it — degrees add in $\mathbb{Q}[x]$, so
$x(x-1)(x-2)(x-3)$ cannot be shaved down to degree $3$. (The no-zero-divisors
fact you reached for is about $\mathbb{Q}[x]$, and it holds because $\mathbb{Q}$
is a field. Same fact you still owe me for $f \neq 0$ in the finite case.)

So you now hold the ceiling, not just the floor: four roots force degree at
least four, and turned around, **a non-zero polynomial of degree $n$ cannot have
more than $n$ roots.** That is the direction you had never used.

---

**Problem 3.8**, the last clause:

> Suppose that $K$ is a field. If $f = a_{0} + a_{1}x + \cdots + a_{n}x^{n} \in
> K[x]$ and $k \in K$, let $(\Phi(f))(k) = a_{0} + a_{1}k + \cdots + a_{n}k^{n}$.
> Show that $\Phi$ is a ring homomorphism from $K[x]$ to $K^{K}$. Show that if
> $K$ is finite then $\Phi$ is an epimorphism, but not a monomorphism.
> **What happens if $K$ is infinite?**

Definitions and results the statement uses:

- $\Phi \colon K[x] \to K^{K}$ sends $f$ to $k \mapsto f(k)$, and is a ring
  homomorphism — proved.
- *Monomorphism:* an injective ring homomorphism.
- $\Ker\Phi = \{h \in K[x] : h(k) = 0 \text{ for every } k \in K\}$, and a ring
  homomorphism is injective exactly when $\Ker\Phi = \{0\}$.
- Every non-zero $h \in K[x]$ has a degree, and it is a **finite** number $n$.
- A non-zero $h$ of degree $n$ has at most $n$ roots in $K$.

---

**Your move.** $K$ is an infinite field. Decide whether $\Phi$ is a
monomorphism, and prove it. You have $h = g - f \in \Ker\Phi$ from your own
page, and now the ceiling. Only this half.
