---
kind: lesson
title: check 8a-which-composite
---
The chain is the right idea, but $f = g\circ h$ is in the wrong order, and "clearly" is covering the three things 8(a) asks you to show.

No question on the page, so straight to the one gap: which way the maps go. ($F/(p)$ I am reading as $F[x]/(p)$.)

Here are $g$ and $h$ made explicit. The first isomorphism theorem applied to $\mathrm{ev}_\alpha$ gives $\phi_\alpha: F[x]/(p)\to F(\alpha)$, $f+(p)\mapsto f(\alpha)$. It points **away** from the quotient, so the arrow you need out of $F(\alpha)$ is its inverse:

- $g = \phi_\alpha^{-1}: F(\alpha)\to F[x]/(p)$, so $g(\alpha) = x+(p)$.
- $h = \phi_\beta: F[x]/(p)\to F(\beta)$, $f+(p)\mapsto f(\beta)$, so $h(x+(p)) = \beta$.

Your move, one small thing: of $g\circ h$ and $h\circ g$, which one is even defined as a map $F(\alpha)\to F(\beta)$? Take that one and push $\alpha$ through it, one arrow at a time, to find where $\alpha$ lands.
