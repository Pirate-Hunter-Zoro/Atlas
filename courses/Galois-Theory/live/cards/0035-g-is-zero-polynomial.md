---
kind: correct
title: Correct — and your $g$ is the zero polynomial
---

Correct. $\Phi(g) = \Phi(f)$ as elements of $K^K$ (both send $0 \mapsto 0$ and
$1 \mapsto 0$), and $g \neq f$ in $\mathbb{F}_2[x]$. That is a non-zero kernel,
so **$\Phi$ is not a monomorphism** — you have just answered that clause of 3.8
for $K = \mathbb{F}_2$.

One thing to notice about what you picked: $x + x = (1+1)x = 0 \cdot x = 0$ in
$\mathbb{F}_2[x]$, so your $g$ *is* the zero polynomial. It still does the job —
$0 \neq x^2 + x$, and $\Phi(0)$ is the zero function — but say it as $g = 0$ and
the point is sharper: $x^2 + x$ lies in $\ker \Phi$.

Now the first clause of the problem, which is the one everything else rests on.

**3.8.** Suppose that $K$ is a field. If $f = a_0 + a_1x + \cdots + a_nx^n \in
K[x]$ and $k \in K$, let $(\Phi(f))(k) = a_0 + a_1k + \cdots + a_nk^n$. Show
that $\Phi$ is a ring homomorphism from $K[x]$ to $K^K$.

What that leans on:

- *$K^K$:* all mappings $K \to K$, with $(u+v)(k) = u(k)+v(k)$ and
  $(uv)(k) = u(k)v(k)$ — the ring you built in 3.1.
- *Sum in $K[x]$:* coefficientwise, $(f+g)$ has $i$-th coefficient $a_i + b_i$.
- *Ring homomorphism:* $\Phi(f+g) = \Phi(f) + \Phi(g)$ and
  $\Phi(fg) = \Phi(f)\Phi(g)$.
- *Two functions are equal* when they agree at every point of $K$.

**Your move.** The additive half only: let $f = \sum a_ix^i$ and
$g = \sum b_ix^i$ in $K[x]$, and prove $\Phi(f+g) = \Phi(f) + \Phi(g)$. Fix an
arbitrary $k \in K$ and compute both sides at $k$. The product half is the next
turn.
