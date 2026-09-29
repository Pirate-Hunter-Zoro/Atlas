---
kind: lesson
title: check 8a-push-alpha-and-c
---
Inverting one arrow is right, but $g\circ h^{-1}$ inverts the wrong one: it runs $F(\beta)\to F(\alpha)$ and sends $\beta$ to $\alpha$.

Push $\beta$ through it with $g=\phi_\alpha$, $h=\phi_\beta$ (both point out of the quotient): $h^{-1}(\beta)=x+(p)$, then $g(x+(p))=\alpha$. So your map is $\sigma^{-1}$, not $\sigma$. The one you want is $\sigma = h\circ g^{-1}$. No question on the page, so that is the only correction.

8(a): let $p\in F[x]$ be irreducible with roots $\alpha,\beta$. Show there is a unique isomorphism $\sigma: F(\alpha)\to F(\beta)$ that fixes $F$ and sends $\alpha$ to $\beta$.

- $\mathrm{ev}_\alpha: F[x]\to F(\alpha)$, $f\mapsto f(\alpha)$; surjective, kernel $(p)$.
- $\phi_\alpha: F[x]/(p)\to F(\alpha)$, $f+(p)\mapsto f(\alpha)$: the isomorphism the first isomorphism theorem gives. Same for $\phi_\beta$.
- $g=\phi_\alpha$, $h=\phi_\beta$, $\sigma=h\circ g^{-1}$.
- "Fixes $F$": $\sigma(c)=c$ for every constant $c\in F$.

Your move, one small thing: push $\alpha$, and then a constant $c\in F$, through $\sigma = h\circ g^{-1}$ one arrow at a time. Where does each land?
