---
kind: correct
title: Right convention — corrected, see card 0018
---
> **Corrected.** The tracking below is right; two of the labels written from it were not. $1\to3,\ 3\to1,\ 2\to2$ is $(1\,3)$, not $(1\,3\,2)$. Card 0018 has the repair.

Convention: right factor acts first. Tracking $1$: $(1\,3\,2)$ sends $1\to 3$, then $(1\,2)$ sends $3\to 3$, so the product sends $1\to 3$. Tracking $3$: $(1\,3\,2)$ sends $3\to 2$, then $(1\,2)$ sends $2\to 1$, so $3\to 1$. Tracking $2$: $(1\,3\,2)$ sends $2\to 1$, then $(1\,2)$ sends $1\to 2$, so $2\to 2$. The cycle is $(1\,3)$ — the convention and the tracking are yours and both are right.

The conjugation check: $(1\,3\,2)(1\,2)(1\,2\,3) = (1\,3)$, a transposition, not an element of order 3.

So far you have $g=(1\,2\,3)$ of order 3 and $h=(1\,2)$ being conjugated by it. The next line on your page should be the orbit of $h=(1\,2)$ under repeated conjugation by $g$ — the three conjugates $h,\ ghg^{-1},\ g^2hg^{-2}$ — and then the subgroup of $\Symn{3}$ they generate. We will write that as $\langle\,h,\ g\,\rangle$ and read it off from the orbits on $\{1,2,3\}$.

**Your move:** compute $g^2 h g^{-2}$ on the page (same convention, same tracking), write the three conjugates side by side, and tell me which subgroup of $\Symn{3}$ they generate.
