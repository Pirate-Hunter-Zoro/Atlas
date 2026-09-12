---
kind: correct
title: Correct. The product half is done — now the epimorphism.
---

That is right. The line that carried it is the third one: from
$\sum_m \bigl(\sum_{i+j=m} a_i b_j\bigr) k^m$ back out to
$\bigl(\sum_i a_i k^i\bigr)\bigl(\sum_j b_j k^j\bigr)$ — the same collecting by
total degree you did with $x$, read backwards, with $k$ in its place. Both
halves of the homomorphism clause are now settled, and I am typing it up.

**Next piece of 3.8, in the book's words:**

> Show that if $K$ is finite then $\Phi$ is an *epimorphism*.

Not yet — one thing first.

- *$K^K$:* every mapping from $K$ to $K$, with the operations of 3.1.
- *Epimorphism:* a ring homomorphism that is onto. So: every $h \in K^K$ is
  $\Phi(f)$ for some $f \in K[x]$.

---

**Your move.** Take $K = \Fq{2} = \{0, 1\}$. Let $h \in \Fq{2}^{\Fq{2}}$ be the
mapping
$$h(0) = 1, \qquad h(1) = 0.$$

Write down a polynomial $f \in \Fq{2}[x]$ with $\Phi(f) = h$ — that is, one with
$\bigl(\Phi(f)\bigr)(0) = 1$ and $\bigl(\Phi(f)\bigr)(1) = 0$. Show both
evaluations.

Remember $1 + 1 = 0$ in $\Fq{2}$.
