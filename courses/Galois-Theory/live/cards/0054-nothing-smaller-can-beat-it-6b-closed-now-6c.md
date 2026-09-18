---
kind: lesson
title: nothing-smaller-can-beat-it-6b-closed-now-6c
---
**Right, and 6(b) is closed.** $[\mathbb{Q}(\gamma):\mathbb{Q}] = 4$ because
$\mathbb{Q}(\gamma)$ *is* $K$, so $\deg m_{\gamma,\mathbb{Q}} = 4$, so your quartic
$x^4 - 10x^2 + 1$ --- monic, rational, degree $4$, kills $\gamma$ --- has no room
to be beaten. Your last line is the reason: nothing of lower degree can have
$\gamma$ as a root, because $4$ is the least degree there is. Both halves of 6(b)
are now in the write-up and it builds.

That leaves 6(c), and you already own the two facts it needs.

**Problem 6(c).** Let $K = \mathbb{Q}(\sqrt{2},\sqrt{3})$. Find three proper
intermediate fields.

What this uses:

- *Intermediate field* --- a field $F$ with $\mathbb{Q} \subseteq F \subseteq K$.
- *Proper* --- $F \neq \mathbb{Q}$ and $F \neq K$. Both ends are excluded.
- $[K:\mathbb{Q}] = 4$ --- your 6(a).
- Tower law --- $[K:\mathbb{Q}] = [K:F]\,[F:\mathbb{Q}]$ for any intermediate $F$, so $[F:\mathbb{Q}]$ divides $4$.
- $\mathbb{Q}(\alpha)$ --- the smallest field containing $\mathbb{Q}$ and $\alpha$; it sits inside $K$ whenever $\alpha \in K$.
- $\gamma^2 = 5 + 2\sqrt{6}$ --- your r42, from 6(a).
- $\sqrt{2}, \sqrt{3} \in K$ by definition of $K$.

**Your move.** Name three elements of $K$, each irrational, no two of them
generating the same field, and say which field each one generates. Three fields,
strictly between $\mathbb{Q}$ and $K$.
