---
kind: lesson
title: the-quartic-is-right-monic-of-degree-4-is-not-yet-minimal
---
**Your quartic is right.** $(\gamma^2-5)^2 = 24$ expands to
$\gamma^4 - 10\gamma^2 + 25 = 24$, so $\gamma^4 - 10\gamma^2 + 1 = 0$. Degree $4$,
monic, rational coefficients. Every line of that arithmetic is correct.

**The bracket at the bottom is the leap.** You wrote "degree 4, monic, so this is
the minimal polynomial". Monic and degree $4$ is not what makes a polynomial
minimal --- *least* degree is. Nothing on the page yet stops $x^4 - 10x^2 + 1$
from factoring in $\mathbb{Q}[x]$ with a quadratic factor that also kills
$\gamma$. What rules that out is the degree of the extension: if
$[\mathbb{Q}(\gamma):\mathbb{Q}] = 4$ then no polynomial of degree $1, 2$ or $3$
can kill $\gamma$, and yours wins by being monic of exactly that degree.

So the two halves of this problem are one half. Show $K = \mathbb{Q}(\gamma)$ and
the degree is $4$ by 6(a), and the minimal polynomial falls out.

**Problem 6(b).** Let $K = \mathbb{Q}(\sqrt{2},\sqrt{3})$ and
$\gamma = \sqrt{2}+\sqrt{3}$. Show that $K = \mathbb{Q}(\gamma)$, and compute
$m_{\gamma,\mathbb{Q}}$.

What this uses:

- $\mathbb{Q}(\gamma)$ --- the smallest subfield of $\mathbb{C}$ containing $\mathbb{Q}$ and $\gamma$; being a field, it is closed under multiplication, addition and division by anything non-zero in it.
- $m_{\gamma,\mathbb{Q}}$ --- the monic rational polynomial of *least* degree with $\gamma$ as a root.
- $\deg m_{\gamma,\mathbb{Q}} = [\mathbb{Q}(\gamma):\mathbb{Q}]$.
- $[K:\mathbb{Q}] = 4$ --- what you proved in 6(a).
- $\mathbb{Q}(\gamma) \subseteq K$ --- immediate, since $\gamma \in K$; the work is the other inclusion.
- $\gamma^4 - 10\gamma^2 + 1 = 0$ --- this page.

**Your move, one multiplication.** Work out
$(\sqrt{2}+\sqrt{3})(\sqrt{3}-\sqrt{2})$. Then tell me whether
$\sqrt{3}-\sqrt{2}$ lies in $\mathbb{Q}(\gamma)$, and why.
