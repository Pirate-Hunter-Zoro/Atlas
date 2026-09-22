---
kind: lesson
title: five-plus-two-root-six-lands-now-root-3-is-not-in-q-root-2
---
**$5 + 2\sqrt{6}$ is right, and the two that appear are $1$ and $\sqrt{6}$.** The
cross term is $2\sqrt{2}\sqrt{3} = 2\sqrt{6}$, and $2 + 3 = 5$. So
$\gamma^2 = 5\cdot 1 + 2\cdot\sqrt{6}$, with no $\sqrt{2}$ and no $\sqrt{3}$
standing alone. That line is what part (b) will run on, so keep it.

**Problem 6(a).** Let $K = \mathbb{Q}(\sqrt{2},\sqrt{3})$. Show that
$[K:\mathbb{Q}] = 4$.

The route is the tower law with $M = \mathbb{Q}(\sqrt{2})$, giving
$[K:\mathbb{Q}] = [K:\mathbb{Q}(\sqrt{2})]\cdot[\mathbb{Q}(\sqrt{2}):\mathbb{Q}]$.
The right-hand factor is $2$, because $x^2 - 2$ is the minimal polynomial of
$\sqrt{2}$ over $\mathbb{Q}$. So the whole exercise is the left-hand factor, and
that factor is $2$ exactly when $\sqrt{3}$ is not already inside
$\mathbb{Q}(\sqrt{2})$.

What this uses:

- $K = \mathbb{Q}(\sqrt{2},\sqrt{3})$ --- the smallest subfield of $\mathbb{C}$ containing $\mathbb{Q}$, $\sqrt{2}$ and $\sqrt{3}$.
- $[K:\mathbb{Q}]$ --- the dimension of $K$ as a vector space over $\mathbb{Q}$.
- tower law --- $[K:\mathbb{Q}] = [K:M][M:\mathbb{Q}]$ whenever $\mathbb{Q} \subseteq M \subseteq K$.
- $\mathbb{Q}(\sqrt{2})$ --- every element of it is $a + b\sqrt{2}$ with $a$ and $b$ rational, and nothing else is.
- $m_{\alpha,F}$ --- the monic polynomial over $F$ of least degree with $\alpha$ as a root; its degree is $[F(\alpha):F]$.
- why the left factor is $2$ or $1$ --- $\sqrt{3}$ satisfies $x^2 - 3$ over $\mathbb{Q}(\sqrt{2})$, so its minimal polynomial there has degree $2$ or $1$, and it is $1$ only if $\sqrt{3}$ lies in $\mathbb{Q}(\sqrt{2})$.
- $\sqrt{2}$ is irrational --- take it as given.

**Your move.** Suppose $\sqrt{3} = a + b\sqrt{2}$ with $a$ and $b$ rational.
Square both sides. What you get forces one product of two things to be zero ---
say which product it is, and why it has to vanish.
