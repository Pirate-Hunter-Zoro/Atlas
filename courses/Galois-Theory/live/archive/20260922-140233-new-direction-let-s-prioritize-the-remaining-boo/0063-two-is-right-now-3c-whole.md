---
kind: lesson
title: two-is-right-now-3c-whole
---
**Two is right, and $x^2-2$ is the right polynomial to point at.** The half you
left out is why nothing smaller works. Being monic with $\sqrt2$ as a root only
gives $\deg m_{\sqrt2,\mathbb{Q}} \le 2$; degree $1$ would mean $\sqrt2$ is a
root of $x - c$ with $c \in \mathbb{Q}$, i.e. $\sqrt2 \in \mathbb{Q}$. The
irrationality of $\sqrt2$ is what rules that out, and with it the degree is
exactly $2$. Everything you need is now on the table.

**Problem 3(c).** Show that $\sqrt2 \notin \mathbb{Q}(\sqrt[3]{2})$.

What this uses:

- $\mathbb{Q}(\sqrt[3]{2})$ --- the smallest subfield of $\mathbb{R}$ containing $\mathbb{Q}$ and the real cube root of $2$.
- $[K:F]$ --- the dimension of $K$ as a vector space over $F$.
- $m_{\alpha,F}$ --- the monic polynomial over $F$ of least degree with $\alpha$ as a root.
- $\deg m_{\alpha,F} = [F(\alpha):F]$.
- $x^3 - 2$ is irreducible over $\mathbb{Q}$, so $[\mathbb{Q}(\sqrt[3]{2}):\mathbb{Q}] = 3$.
- $\deg m_{\sqrt2,\mathbb{Q}} = 2$, just settled.
- 3(a), yours --- if $[K:F] = n$ then $\deg m_{\alpha,F}$ divides $n$ for every $\alpha \in K$.

**Your move.** Write the whole proof of 3(c), start to finish. Assume
$\sqrt2 \in \mathbb{Q}(\sqrt[3]{2})$, apply 3(a) to it, and say what goes wrong
with the two numbers above.
