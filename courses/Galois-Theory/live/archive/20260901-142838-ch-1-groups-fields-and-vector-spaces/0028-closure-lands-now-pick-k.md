---
kind: correct
title: Closure lands — now choose K
---
$(1\,4)(3\,2)$ is right, and it is the same element as $(1\,4)(2\,3)$ — disjoint cycles commute, and a transposition reads the same both ways. So the product of two of them landed on the third, which is the closure you needed.

Notice what else that computation bought you. The same pattern holds for any two distinct non-identity elements of $H$: their product is the third one, and that description does not care which order you multiply in. So **$H$ is abelian.**

$$H = \{\, e,\ (1\,2)(3\,4),\ (1\,3)(2\,4),\ (1\,4)(2\,3) \,\}, \qquad H \triangleleft S_4 .$$

You now have $G = S_4$ and $H$. Two things are left, and they are the whole of Exercise 1.5:

- a subgroup $K \leq H$ with $K \triangleleft H$ — and $H$ being abelian is the tool for that half;
- a specific $g \in S_4$ and a specific $k \in K$ with $gkg^{-1} \notin K$.

For the second one, remember what conjugation does in $S_n$: conjugating by $\sigma$ just relabels the points, sending the cycle $(a\,b)(c\,d)$ to $(\sigma a\,\sigma b)(\sigma c\,\sigma d)$. That is the machine you want to point at $K$. $K$ has to be small enough that the relabelling can throw an element out of it — which tells you how big to make $K$.

**Your move:** name $K$, say in one line why $K \triangleleft H$, and give the pair $(g, k)$ together with the computed $gkg^{-1}$.
