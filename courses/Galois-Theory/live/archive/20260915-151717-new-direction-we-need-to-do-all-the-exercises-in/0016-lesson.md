---
kind: lesson
title: not-monic-and-that-breaks-4-5-as-printed
---
Right polynomial, wrong normalisation: yours is not monic. $2^{1/3}x^2 - 2^{2/3}$
does have $\alpha = 2^{1/6}$ as a root, it is degree $2$, and its coefficients do
sit in $L = \mathbb{Q}(2^{1/3})$. Divide the whole thing through by $2^{1/3}$ and
you have the minimal polynomial itself, $m_L = x^2 - 2^{1/3}$. Monic is part of
the definition, so the minimal polynomial is that one and not a scalar multiple
of it.

Now read its constant term. $-2^{1/3}$ is not rational. So you have built a tower
where $[L(\alpha):L] = 2$ and $[L:K] = 3$ are coprime and $m_L$ does **not** have
its coefficients in $K$. Exercise 4.5 as printed is false, and that is the
counterexample.

The hypothesis is the thing that is wrong. It should compare $[K(\alpha):K]$ with
$[L:K]$, not $[L(\alpha):L]$ with $[L:K]$. In your tower $[K(\alpha):K] = 6$ and
$[L:K] = 3$ share a factor of $3$, so the repaired statement is never asked about
this example.

**Exercise 4.5, repaired.** Let $L(\alpha) : L : K$ be a tower of fields with
$\alpha$ algebraic over $K$. Suppose $[K(\alpha):K]$ and $[L:K]$ are coprime.
Show that the minimal polynomial of $\alpha$ over $L$ has all its coefficients in
$K$ — in fact that it is equal to the minimal polynomial of $\alpha$ over $K$.

What you need:

- $m_K$ — the monic polynomial of least degree with coefficients in $K$ and $\alpha$ as a root. Call its degree $n$.
- $m_L$ — the same thing with coefficients in $L$. Call its degree $d$.
- **Theorem 4.4** — $[K(\alpha):K] = n$ and $[L(\alpha):L] = d$.
- **Tower law** — $[L(\alpha):K] = [L(\alpha):L]\,[L:K]$, and the same degree also equals $[L(\alpha):K(\alpha)]\,[K(\alpha):K]$.
- **Coprime** — greatest common divisor $1$; and if $a$ divides $bc$ with $\gcd(a,b) = 1$ then $a$ divides $c$.

**Your move.** One step only. Every coefficient of $m_K$ lies in $K$, and
$K \subseteq L$, so $m_K$ is also a polynomial over $L$ with $\alpha$ as a root.
Say why that forces $m_L$ to divide $m_K$, and write down the inequality between
$d$ and $n$ it gives you.
