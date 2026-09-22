---
kind: lesson
title: the-basis-of-k-is-the-wrong-basis
---
---
kind: lesson
title: the-basis-of-k-is-the-wrong-basis
---
**You unpacked the wrong $n$.** $\{k_1,\dots,k_n\}$ is a basis for $K$ over $F$
and your independence line is correct, but $\alpha$ never appears in it. A
basis of the *big* field cannot tell you anything about one element's minimal
polynomial. The $n$ you need to break apart is the one in the tower law, and a
tower needs a field in the middle.

So: find the middle field first, on a case small enough to see.

Take $K = \mathbb{Q}(\sqrt[4]{2})$, so $F = \mathbb{Q}$ and $n = [K:F] = 4$.
Take $\alpha = \sqrt{2}$, which does live in $K$, since $\sqrt2 =
(\sqrt[4]{2})^2$.

What this uses:

- $\mathbb{Q}(\sqrt[4]{2})$ --- the smallest subfield of $\mathbb{R}$ containing $\mathbb{Q}$ and $\sqrt[4]{2}$; it has degree $4$ over $\mathbb{Q}$.
- $F(\alpha)$ --- the smallest subfield of $K$ containing $F$ and $\alpha$.
- $m_{\alpha,F}$ --- the monic polynomial over $F$ of least degree with $\alpha$ as a root.
- $\deg m_{\alpha,F} = [F(\alpha):F]$.
- Tower law --- $[K:F] = [K:M]\,[M:F]$ whenever $F \subseteq M \subseteq K$ are fields.

**Your move.** Name a field $M$ with $\mathbb{Q} \subseteq M \subseteq
\mathbb{Q}(\sqrt[4]{2})$ that contains $\alpha = \sqrt2$, and give $[M:\mathbb{Q}]$.
