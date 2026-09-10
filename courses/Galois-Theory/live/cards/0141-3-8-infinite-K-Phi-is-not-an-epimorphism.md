---
kind: note
title: Skipped, so the monomorphism half stands. The other half of 3.8 is a construction.
---

Taken as known: if $f \in K[x]$ vanishes at every point of an infinite $K$, then
$f$ is the zero polynomial — a nonzero $f$ would have a degree $n$ and at most
$n$ roots, and no list of $n$ elements exhausts an infinite $K$. So
$\ker \Phi = \{0\}$ and $\Phi$ is a monomorphism. One half left.

---

## Exercise 3.8, the last quarter

Let $K$ be a field. For $f = a_{0} + a_{1}x + \cdots + a_{n}x^{n} \in K[x]$
and $k \in K$, define

$$(\Phi(f))(k) = a_{0} + a_{1}k + \cdots + a_{n}k^{n},$$

so that $\Phi : K[x] \to K^{K}$. You have already shown that $\Phi$ is a ring
homomorphism, that **when $K$ is finite** it is an epimorphism but not a
monomorphism, and now that **when $K$ is infinite** it is a monomorphism.

**Remaining: show that when $K$ is infinite, $\Phi$ is not an epimorphism.**

### Everything the statement uses

- $K[x]$: polynomials in $x$ with coefficients in the field $K$. Two polynomials are equal iff every coefficient agrees. Every element of $K[x]$ has only **finitely many** nonzero coefficients.
- $K^{K}$: the ring of **all** functions from $K$ to $K$, added and multiplied pointwise. No continuity, no formula, no rule — any assignment of an output in $K$ to each input in $K$ is an element of $K^{K}$.
- $\Phi(f)$: the function $K \to K$ that $f$ computes — "evaluate $f$ at the input".
- *Epimorphism:* a surjective homomorphism — every function $K \to K$ whatsoever equals $\Phi(f)$ for some polynomial $f$. To deny it you need **one** function that no polynomial computes.
- *Zero polynomial:* every coefficient is $0$. *Zero function:* value $0$ at every point of $K$. Different objects, different rings.
- *Root:* $k \in K$ with $f(k) = 0$.
- *Degree:* $\deg f = n$ when $a_{n} \neq 0$ is the top nonzero coefficient. The zero polynomial has no degree here; every other polynomial has one, and it is a finite number.
- **Your 3.15** (cards 0116–0119): if $K$ is a field and $f \in K[x]$ is nonzero with $\deg f = n$, then $f$ has **at most $n$ roots in $K$**.
- $K$ *infinite:* $K$ has infinitely many elements — so no finite list of elements of $K$ exhausts it, and removing one element still leaves infinitely many.

---

**Your move.** The monomorphism half was a claim about every polynomial at once.
This half is the opposite shape: you get to choose the witness.

**Let $K$ be infinite. Produce a single function $g : K \to K$ and prove that
$g \neq \Phi(f)$ for every $f \in K[x]$. Conclude that $\Phi$ is not an
epimorphism.**

Your root bound says a nonzero polynomial cannot vanish too often. So build a
$g$ that vanishes far too often — and is still not the zero function.
