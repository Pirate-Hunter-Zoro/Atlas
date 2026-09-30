---
kind: lesson
title: check 8a-uniqueness-again
---
Problem 8(b) is agreed. The label is fixed, you checked all three Eisenstein conditions at $p$, and you shifted back from $\Phi_p(x+1)$ to $\Phi_p(x)$. The line $p \mid \binom{p}{k}$ for $2 \le k \le p-1$ stands as a stated fact, which is how the sheet uses it. It is now typeset in the worksheet beside your handwriting.

One problem is still open: uniqueness in 8(a), from the start of the sitting.

**Problem 8(a).** Let $p \in F[x]$ be irreducible, with roots $\alpha$ and $\beta$ in (possibly different) extensions of $F$. Show there is a unique isomorphism $F(\alpha) \to F(\beta)$ fixing $F$ and sending $\alpha \mapsto \beta$.

What you need:
- $\sigma = h^{-1}\circ g : F(\alpha) \to F(\beta)$ is your isomorphism. It fixes $F$ and sends $\alpha \mapsto \beta$.
- $\tau : F(\alpha) \to F(\beta)$ is any isomorphism that fixes $F$ and sends $\alpha \mapsto \beta$.
- Every element of $F(\alpha)$ is $f(\alpha)$ for some $f \in F[x]$, because the evaluation map is surjective.
- A map that adds, multiplies and fixes $F$ commutes with evaluating a polynomial with coefficients in $F$. That is the step inside your 7(b).

Existence is done. Take any $\tau : F(\alpha) \to F(\beta)$ that fixes $F$ and sends $\alpha \mapsto \beta$, and show that $\tau = \sigma$.
