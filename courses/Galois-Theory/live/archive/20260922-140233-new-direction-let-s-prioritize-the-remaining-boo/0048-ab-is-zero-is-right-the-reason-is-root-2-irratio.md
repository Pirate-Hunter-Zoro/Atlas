---
kind: lesson
title: ab-is-zero-is-right-the-reason-is-root-2-irrational
---
**$ab = 0$ is right, and your squaring is right.** From $\sqrt{3} = a + b\sqrt{2}$
you get $3 = a^2 + 2b^2 + 2ab\sqrt{2}$, and that equation does force the product
$ab$ to vanish.

One tightening on the reason. "$a, b \in \mathbb{Q}$" is not by itself what kills
it --- what kills it is that $\sqrt{2}$ is irrational. Rearrange to
$2ab\sqrt{2} = 3 - a^2 - 2b^2$. The right-hand side is rational. If $ab \neq 0$
you may divide by $2ab$ and get $\sqrt{2} = (3 - a^2 - 2b^2)/(2ab)$, which says
$\sqrt{2}$ is rational. It is not. So $ab = 0$.

Now $ab = 0$ means $a = 0$ or $b = 0$, and each of those two cases has to be
killed on its own. Killing both is the whole of what is left in 6(a).

**Problem 6(a), restated.** $K = \mathbb{Q}(\sqrt{2},\sqrt{3})$. Show
$[K:\mathbb{Q}] = 4$.

What this uses:

- $[K:\mathbb{Q}]$ --- the dimension of $K$ as a vector space over $\mathbb{Q}$.
- tower law --- $[K:\mathbb{Q}] = [K:M][M:\mathbb{Q}]$ for $\mathbb{Q} \subseteq M \subseteq K$, here with $M = \mathbb{Q}(\sqrt{2})$.
- $[\mathbb{Q}(\sqrt{2}):\mathbb{Q}] = 2$ --- already settled, from $x^2 - 2$.
- $\mathbb{Q}(\sqrt{2})$ --- every element is $a + b\sqrt{2}$ with $a, b$ rational, and nothing else is.
- $[K:\mathbb{Q}(\sqrt{2})]$ is $2$ or $1$ --- and it is $1$ only if $\sqrt{3} \in \mathbb{Q}(\sqrt{2})$, which is the assumption you are killing.
- $\sqrt{2}$, $\sqrt{3}$ and $\sqrt{6}$ are all irrational --- take all three as given.

**Your move.** Take the two cases separately. With $b = 0$, what does
$\sqrt{3} = a + b\sqrt{2}$ collapse to, and which of the three given
irrationalities does it contradict? With $a = 0$, it collapses to
$\sqrt{3} = b\sqrt{2}$ --- multiply both sides by $\sqrt{2}$ and say what you are
left with, and which irrationality that one contradicts.
