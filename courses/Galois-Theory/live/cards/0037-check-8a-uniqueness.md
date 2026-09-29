---
kind: lesson
title: check 8a-uniqueness
---
$f=h^{-1}\circ g$ is right, with your arrows: $g: F(\alpha)\to F[x]/(p)$ and $h: F(\beta)\to F[x]/(p)$, both pointing into the quotient. Card 0036 read $g,h$ the other way round, out of the quotient; your diagram does not, so existence stands.

Your "clearly" is the two pushes: $\alpha \mapsto x+(p) \mapsto \beta$, and $c \mapsto c+(p) \mapsto c$ for $c\in F$. That is all it hides. What is left is "unique".

8(a): let $p\in F[x]$ be irreducible with roots $\alpha,\beta$. Show there is a unique isomorphism $\sigma: F(\alpha)\to F(\beta)$ that fixes $F$ and sends $\alpha$ to $\beta$.

- $g: F(\alpha)\to F[x]/(p)$, $f(\alpha)\mapsto f+(p)$; $h: F(\beta)\to F[x]/(p)$ likewise. Both from the first isomorphism theorem.
- Existence: $\sigma = h^{-1}\circ g$.
- "Fixes $F$": $\sigma(c)=c$ for every $c\in F$.
- From 7(b): every element of $F(\alpha)$ is $f(\alpha)$ for some $f\in F[x]$.

Your move: suppose $\tau: F(\alpha)\to F(\beta)$ also fixes $F$ and sends $\alpha$ to $\beta$. Show $\tau=\sigma$.
