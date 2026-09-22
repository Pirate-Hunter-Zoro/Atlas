---
kind: lesson
title: k-equals-q-gamma-lands-now-name-the-degree
---
**All of it is right, and the last paragraph is the part that matters.** You did not
just show the two radicals are in $\mathbb{Q}(\gamma)$ --- you said why that finishes
the equality. $\mathbb{Q}(\gamma)$ is the smallest field containing $\gamma$, and $K$
contains $\gamma$, so $\mathbb{Q}(\gamma) \subseteq K$. $K$ is the smallest field
containing $\sqrt{2}$ and $\sqrt{3}$, and $\mathbb{Q}(\gamma)$ contains both, so
$K \subseteq \mathbb{Q}(\gamma)$. Two inclusions, equality. That is the whole argument
and you wrote both halves of it.

Half of 6(b) is closed. The minimal polynomial is the other half, and you already have
every piece of it on paper.

**Problem 6(b).** Let $K = \mathbb{Q}(\sqrt{2},\sqrt{3})$ and $\gamma = \sqrt{2}+\sqrt{3}$.
Show that $K = \mathbb{Q}(\gamma)$, and compute $m_{\gamma,\mathbb{Q}}$.

What this uses:

- $m_{\gamma,\mathbb{Q}}$ --- the monic polynomial with rational coefficients of *least* degree having $\gamma$ as a root.
- $\deg m_{\gamma,\mathbb{Q}} = [\mathbb{Q}(\gamma):\mathbb{Q}]$ --- the degree of the minimal polynomial is the degree of the extension it generates.
- $[\mathbb{Q}(\gamma):\mathbb{Q}]$ --- the dimension of $\mathbb{Q}(\gamma)$ as a vector space over $\mathbb{Q}$.
- $[K:\mathbb{Q}] = 4$ --- your 6(a), by the tower law.
- $K = \mathbb{Q}(\gamma)$ --- this page, just now.
- $\gamma^4 - 10\gamma^2 + 1 = 0$ --- your r43, squaring twice.
- Monic of degree $d$ killing $\gamma$ is not enough to be minimal on its own; a lower-degree one could still exist.

**Your move.** Say what $[\mathbb{Q}(\gamma):\mathbb{Q}]$ is and how you know, then say
what that makes $\deg m_{\gamma,\mathbb{Q}}$, and then say which polynomial
$m_{\gamma,\mathbb{Q}}$ therefore is and why nothing smaller can beat it.
