---
kind: note
title: Stuck is fine. Here is what "$d\alpha \in R[x]$" is actually asking.
---

I think the trouble is the *target*, not the algebra. Inside $F$, "this element is in $R$" cannot mean literal containment — elements of $F$ are classes of pairs. It means: **the class equals $r/1$ for some $r \in R$.** That is the shape you are trying to reach, and once you know it the work is one cross-multiplication.

Two rules, both already yours:

- Multiplication in $F$: $\dfrac{p}{q}\cdot\dfrac{p'}{q'} = \dfrac{pp'}{qq'}$, and $d \in R$ sits in $F$ as $d/1$.
- Equality in $F$: $\dfrac{p}{q} = \dfrac{p'}{q'}$ exactly when $pq' = p'q$.

Concretely first, in $R = \mathbb{Z}$. Say the coefficient is $2/3$ and the only other denominator is $5$, so $d = 15$. Then

$$\frac{15}{1}\cdot\frac{2}{3} = \frac{30}{3} = \frac{10}{1},$$

and that last equality is not cancellation — it is $30 \cdot 1 = 3 \cdot 10$. The integer produced is $10 = 5 \cdot 2$: the *other* denominator times the numerator.

Now the same thing with letters. Fix one non-zero coefficient $a/b$ of $\alpha$. Since $d$ is the product of **all** the denominators, $b$ is one of its factors: write $d = bc$, where $c \in R$ is the product of the rest. Then

$$\frac{d}{1}\cdot\frac{a}{b} = \frac{bca}{b}.$$

**Your move.** Name the element $r \in R$ for which $\dfrac{bca}{b} = \dfrac{r}{1}$, and check that equality by writing out the cross-multiplication the definition demands.

That single line, said for an arbitrary coefficient, is the whole of $d\alpha \in R[x]$ — and $d\beta$ goes the same way, since $d$ was built from $\beta$'s denominators too.
