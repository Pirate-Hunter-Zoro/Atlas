---
kind: note
title: Mostly. But you are not allowed to write $\phi^{-1}$ yet.
---

You asked, so here is the audit.

**Right.** $R$ an integral domain — fixed. $F$ as you describe it. $d$ = the product of the denominators of the non-zero coefficients of $\alpha$ and $\beta$: right, and it is the only $d$ you need. $d\alpha, d\beta \in R[x]$: true — though that is the claim I asked you to check by cross-multiplication last card, and you have asserted it instead.

**Not right.** $\phi^{-1}$ presumes $\phi$ is a bijection, and that is what you are trying to prove. You do not have an inverse. You have a **candidate preimage**, and surjectivity is exactly this: given $\alpha/\beta$, *exhibit* an element of $\operatorname{Frac}(R[x])$, then *check* that $\phi$ sends it to $\alpha/\beta$. Nothing more, and nothing you can skip.

So the line is not $\phi^{-1}(\alpha/\beta) = d\alpha/d\beta$. It is: set $\gamma = d\alpha/d\beta$, an element of $\operatorname{Frac}(R[x])$ — and then the check. (It is an element only if $d\beta \neq 0$; that clause belongs in your proof, with its reason.)

The check is the part you have not written at all, and it is one line.

**Your move.** With $\gamma = d\alpha/d\beta \in \operatorname{Frac}(R[x])$, verify that $\phi(\gamma) = \alpha/\beta$ in $F(x)$.

- $\phi$ sends the class of the pair $(p, q)$ over $R[x]$ to the class of the same pair over $F[x]$.
- Two classes are equal in $F(x)$ exactly when the cross-products agree: $p/q = p'/q'$ iff $pq' = p'q$.
