---
kind: correct
title: $f = \sum_{k} h(k)\delta_{k}$. Correct — the epimorphism is done.
---

Correct. The step that carried it is the third line: $\Phi$ is a homomorphism,
so it goes inside the sum, and then $\sum_{k} h(k)\delta_{k}(k_{1})$ collapses
to the single term at $k = k_{1}$ because every other $\delta_{k}$ kills
$k_{1}$. $k_{1}$ was arbitrary, so $\Phi(f) = h$ in $K^{K}$.

I am typesetting it as you wrote it. Two things your page leaves implicit and I
will not add for you: that the sum is *finite* only because $K$ is, and that the
discarded terms are $h(k)\cdot 0$.

---

**Problem 3.8**, the next clause:

> Suppose that $K$ is a field. If $f = a_{0} + a_{1}x + \cdots + a_{n}x^{n} \in
> K[x]$ and $k \in K$, let $(\Phi(f))(k) = a_{0} + a_{1}k + \cdots + a_{n}k^{n}$.
> Show that if $K$ is finite then $\Phi$ is an epimorphism, **but not a
> monomorphism.**

Definitions the statement uses:

- $K^{K}$: all mappings from $K$ to $K$, added and multiplied pointwise.
- $\Phi \colon K[x] \to K^{K}$ sends $f$ to the mapping $k \mapsto f(k)$.
- *Monomorphism:* an injective ring homomorphism.
- $\ker \Phi = \{ f \in K[x] : \Phi(f) = 0 \}$, the zero of $K^{K}$ being the
  mapping sending every $k$ to $0$.
- A homomorphism is injective exactly when $\ker\Phi = \{0\}$ — so one non-zero
  polynomial in the kernel finishes it.
- The zero polynomial is the one with every coefficient $0$; $x^{2}+x$ is not
  the zero polynomial, whatever it does to $\Fq{2}$.

---

**Your move.** $K$ is an arbitrary finite field. Write down one non-zero
$f \in K[x]$ with $\Phi(f) = 0$, and say why $f(k) = 0$ for every $k \in K$.
You have the $\Fq{2}$ case already — $x^{2}+x$ — so this is that, one level up,
and the $\delta_{c}$ you have been building are made of the same ingredient.
