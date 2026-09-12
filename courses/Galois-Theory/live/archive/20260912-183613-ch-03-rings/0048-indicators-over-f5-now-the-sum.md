---
kind: correct
title: $\delta_{0}$ over $\Fq{5}$ is right, inverse and all. Now the sum.
---

Correct, and you jumped a field to do it. $p(0) = (-1)(-2)(-3)(-4) = 4\cdot 3
\cdot 2 \cdot 1 = 4$ in $\Fq{5}$, and $4^{-1} = 4$ because $16 \equiv 1$, so
$$\delta_{0}(x) = 4(x-1)(x-2)(x-3)(x-4)$$
takes the value $1$ at $0$ and $0$ at $1,2,3,4$. That is the recipe in general:
kill the other points with the factors, then scale by the inverse of what
survives.

So for each $c \in \Fq{5}$ write $\delta_{c}$ for the polynomial built that same
way at $c$ — value $1$ at $c$, value $0$ at the other four points.

Definitions the question uses, so nothing has to be hunted for:

- $\Fq{5}^{\Fq{5}}$: all mappings from $\Fq{5}$ to $\Fq{5}$, added and
  multiplied pointwise.
- $\Phi \colon \Fq{5}[x] \to \Fq{5}^{\Fq{5}}$: sends a polynomial $f$ to the
  mapping $k \mapsto f(k)$.
- $\delta_{c}(c) = 1$, and $\delta_{c}(a) = 0$ for every $a \neq c$.

---

**Your move.** Let $h \in \Fq{5}^{\Fq{5}}$ be
$$h(0) = 3, \quad h(1) = 0, \quad h(2) = 0, \quad h(3) = 1, \quad h(4) = 0.$$

Write down an $f \in \Fq{5}[x]$ with $\Phi(f) = h$, using only the $\delta_{c}$
and elements of $\Fq{5}$ — then show $f(3) = 1$ by saying what each term of your
$f$ contributes at $x = 3$.
