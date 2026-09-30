---
kind: lesson
title: check 8a-uniqueness
---
We pick up at uniqueness in Problem 8(a) of the automorphisms worksheet, not Chapter 6. You skipped Chapter 6 for this sheet; Problems 7 to 10 are the plan, and 7(a) to 7(c) are already typeset.

Your existence argument for 8(a) is agreed. You built $\sigma = h^{-1}\circ g$, where $g : F(\alpha) \to F[x]/(p)$ and $h : F(\beta) \to F[x]/(p)$ come from the evaluation maps. One half is left.

**Problem 8(a).** Let $p \in F[x]$ be irreducible, with roots $\alpha$ and $\beta$ in (possibly different) extensions of $F$. Show there is a unique isomorphism $F(\alpha) \to F(\beta)$ fixing $F$ and sending $\alpha \mapsto \beta$.

What you need:
- $\sigma : F(\alpha) \to F(\beta)$ is your isomorphism: it fixes $F$ and sends $\alpha \mapsto \beta$.
- $\tau : F(\alpha) \to F(\beta)$ is any other isomorphism that fixes $F$ and sends $\alpha \mapsto \beta$.
- Every element of $F(\alpha)$ is $f(\alpha)$ for some $f \in F[x]$ (the evaluation map is surjective).
- A map that adds, multiplies and fixes $F$ commutes with evaluating a polynomial with coefficients in $F$ (the step inside your 7(b)).

Let $\tau : F(\alpha) \to F(\beta)$ fix $F$ and send $\alpha \mapsto \beta$. Show that $\tau = \sigma$.
