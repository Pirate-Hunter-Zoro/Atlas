---
kind: lesson
title: new-sheet-four-problems-now-square-gamma
---
That sheet came through readable and I have read both pages: six problems, titled
"Field Extensions and the Ring $F[x]$". 4.2 stays skipped. We work this instead.

Four of the six, in this order, and why:

- **Problem 6** first. Its field is $\mathbb{Q}(\sqrt{2},\sqrt{3})$ — the exact object you
  just walked away from in 4.2, but with numbers in place of a general bound.
- **Problem 3** next. Its part (b) *is* exercise 4.6, which you already proved, so only
  (a) and (c) are live.
- **Problem 1**, then **Problem 5**. Problems 2 and 4 last.

**Problem 6. A concrete quartic.** Let $K = \mathbb{Q}(\sqrt{2},\sqrt{3})$ and
$\gamma = \sqrt{2}+\sqrt{3}$.

(a) Show that $[K:\mathbb{Q}] = 4$.

(b) Show that $K = \mathbb{Q}(\gamma)$, and compute $m_{\gamma,\mathbb{Q}}$.

(c) Find three proper intermediate fields.

What you need:

- $[K:\mathbb{Q}]$ — the dimension of $K$ as a vector space over $\mathbb{Q}$.
- $\mathbb{Q}(\gamma)$ — the smallest subfield of $K$ containing $\mathbb{Q}$ and $\gamma$.
- $m_{\gamma,\mathbb{Q}}$ — the **monic** polynomial with rational coefficients, of least
  degree, having $\gamma$ as a root.
- **intermediate field** — a subfield of $K$ containing $\mathbb{Q}$.
- **proper**, here — neither $\mathbb{Q}$ itself nor all of $K$.
- **Tower law** — $[K:\mathbb{Q}] = [K:M]\,[M:\mathbb{Q}]$ for $\mathbb{Q} \subseteq M \subseteq K$.
- **spanning bound** — if $m$ elements span a vector space, its dimension is at most $m$.

**Your move.** One line of arithmetic, nothing more. Square $\gamma$, and write the answer as
a rational combination of $1$, $\sqrt{2}$, $\sqrt{3}$ and $\sqrt{6}$. Tell me which of those
four actually show up.
