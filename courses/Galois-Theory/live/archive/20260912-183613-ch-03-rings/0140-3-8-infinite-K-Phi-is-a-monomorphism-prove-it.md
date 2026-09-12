---
kind: note
title: Skipped, so the root count stands. Here is the infinite half of 3.8 in full.
---

Taken as known: over $\mathbb{Q}$ the polynomial $x^{3} - x$ has roots
$0, 1, -1$ and nothing else, so $\Phi(x^{3} - x)$ is **not** the zero function
of $\mathbb{Q}^{\mathbb{Q}}$. The trick that killed injectivity over
$\mathbb{Z}_{3}$ does not survive the move to an infinite field. Onward.

---

## Exercise 3.8, the last quarter

Let $K$ be a field. For $f = a_{0} + a_{1}x + \cdots + a_{n}x^{n} \in K[x]$
and $k \in K$, define

$$(\Phi(f))(k) = a_{0} + a_{1}k + \cdots + a_{n}k^{n},$$

so that $\Phi : K[x] \to K^{K}$. You have already shown that $\Phi$ is a ring
homomorphism, and that **when $K$ is finite** it is an epimorphism but not a
monomorphism.

**Show that when $K$ is infinite, $\Phi$ is a monomorphism but not an
epimorphism.**

### Everything the statement uses

- $K[x]$: polynomials in $x$ with coefficients in the field $K$. Two polynomials are equal iff every coefficient agrees.
- $K^{K}$: the ring of **all** functions from $K$ to $K$, added and multiplied pointwise. Its zero element is the function taking the value $0$ at every point of $K$.
- $\Phi(f)$: the function $K \to K$ that $f$ computes — "evaluate $f$ at the input".
- *Zero polynomial:* every coefficient is $0$. *Zero function:* value $0$ at every point. Different objects, different rings. This distinction is the whole exercise.
- *Monomorphism:* an injective homomorphism. For a ring homomorphism, equivalent to $\ker \Phi = \{0\}$ — only the zero polynomial maps to the zero function.
- *Epimorphism:* a surjective homomorphism — every function $K \to K$ whatsoever equals $\Phi(f)$ for some polynomial $f$.
- *Root:* $k \in K$ with $f(k) = 0$.
- *Degree:* $\deg f = n$ when $a_{n} \neq 0$ is the top nonzero coefficient. The zero polynomial has no degree here.
- **Your 3.15** (cards 0116–0119): if $K$ is a field and $f \in K[x]$ is nonzero with $\deg f = n$, then $f$ has **at most $n$ roots in $K$**.
- $K$ *infinite:* $K$ has infinitely many elements — so no finite list of elements of $K$ exhausts it.

---

**Your move — the monomorphism half only.** The failure over $\mathbb{Z}_{3}$
was a nonzero polynomial sitting in the kernel. Rule that out here.

**Let $K$ be infinite and let $f \in K[x]$ satisfy $\Phi(f) = 0$, the zero
function — that is, $f(k) = 0$ for every $k \in K$. Prove $f$ is the zero
polynomial.**

You already own the tool. Suppose $f$ were not the zero polynomial and count.

(The "not an epimorphism" half is a different kind of argument entirely. It gets
its own card once this one lands.)
