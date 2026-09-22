---
kind: lesson
title: gamma-inverse-lands-now-add-it-to-gamma
---
**Right, and the reason is the right one.** $(\sqrt{2}+\sqrt{3})(\sqrt{3}-\sqrt{2}) = 3 - 2 = 1$,
so $\sqrt{3}-\sqrt{2} = \gamma^{-1}$. A field is closed under division by anything
non-zero in it, and $\gamma \neq 0$, so $\gamma^{-1} \in \mathbb{Q}(\gamma)$.
That is the whole justification, and you gave it.

**Now you have two elements of $\mathbb{Q}(\gamma)$, not one.** Both $\gamma$ and
$\gamma^{-1}$ sit in it, and $\mathbb{Q}(\gamma)$ is closed under addition and
under multiplying by rationals. So anything you can build out of those two by
adding and scaling is also in there.

**Problem 6(b).** Let $K = \mathbb{Q}(\sqrt{2},\sqrt{3})$ and
$\gamma = \sqrt{2}+\sqrt{3}$. Show that $K = \mathbb{Q}(\gamma)$, and compute
$m_{\gamma,\mathbb{Q}}$.

What this uses:

- $\mathbb{Q}(\gamma)$ --- the smallest subfield of $\mathbb{C}$ containing $\mathbb{Q}$ and $\gamma$; closed under addition, multiplication, and division by its non-zero elements.
- $K = \mathbb{Q}(\sqrt{2},\sqrt{3})$ --- the smallest subfield containing $\mathbb{Q}$, $\sqrt{2}$ and $\sqrt{3}$; so $K \subseteq \mathbb{Q}(\gamma)$ holds as soon as both $\sqrt{2}$ and $\sqrt{3}$ are in $\mathbb{Q}(\gamma)$.
- $\mathbb{Q}(\gamma) \subseteq K$ --- already done, since $\gamma \in K$.
- $m_{\gamma,\mathbb{Q}}$ --- the monic rational polynomial of *least* degree killing $\gamma$.
- $\deg m_{\gamma,\mathbb{Q}} = [\mathbb{Q}(\gamma):\mathbb{Q}]$.
- $[K:\mathbb{Q}] = 4$ --- your 6(a).
- $\gamma^4 - 10\gamma^2 + 1 = 0$ --- your r43.
- $\gamma^{-1} = \sqrt{3}-\sqrt{2} \in \mathbb{Q}(\gamma)$ --- this page.

**Your move, one addition.** Compute $\gamma + \gamma^{-1}$, that is
$(\sqrt{2}+\sqrt{3}) + (\sqrt{3}-\sqrt{2})$. Then tell me which of $\sqrt{2}$ and
$\sqrt{3}$ that puts inside $\mathbb{Q}(\gamma)$, and how you get the other one.
