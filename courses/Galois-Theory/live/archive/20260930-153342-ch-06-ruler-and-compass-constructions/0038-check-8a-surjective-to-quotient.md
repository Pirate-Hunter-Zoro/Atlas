---
kind: lesson
title: check 8a-surjective-to-quotient
---
The step from "surjective" to $F(\alpha)\cong F[x]/\ker H$ is the first isomorphism theorem itself. For any ring homomorphism $\varphi: R\to S$,
$$R/\ker\varphi \;\cong\; \operatorname{im}\varphi, \qquad r+\ker\varphi \mapsto \varphi(r).$$
Surjective means $\operatorname{im}H = F(\alpha)$, so the right-hand side is all of $F(\alpha)$. Without surjectivity you would only get $F[x]/\ker H$ isomorphic to the subring $F[\alpha]$.

Surjectivity of $H$ is the 7(b) fact: every element of $F(\alpha)$ is $f(\alpha)$ for some $f\in F[x]$.

Your side note is right: $\ker H=\ker G=(p)$. Both kernels contain $p$, both are proper, and $(p)$ is maximal because $p$ is irreducible. So your $g$ and $h$ are exactly these two induced isomorphisms, and existence stands.

Still open, from card 0037:
- $\sigma = h^{-1}\circ g: F(\alpha)\to F(\beta)$, fixes $F$, sends $\alpha\mapsto\beta$.
- "Fixes $F$": $\tau(c)=c$ for every $c\in F$.
- From 7(b): every element of $F(\alpha)$ is $f(\alpha)$ for some $f\in F[x]$.

Your move: suppose $\tau: F(\alpha)\to F(\beta)$ is an isomorphism that fixes $F$ and sends $\alpha$ to $\beta$. Show $\tau=\sigma$.
