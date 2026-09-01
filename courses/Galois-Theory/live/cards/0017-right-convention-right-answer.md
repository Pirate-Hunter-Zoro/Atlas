---
kind: correct
title: Right convention, right answer
---
Convention: right factor acts first. Tracking $1$: $(1\,3\,2)$ sends $1\to 3$, then $(1\,2)$ sends $3\to 3$, so the product sends $1\to 3$. Tracking $3$: $(1\,3\,2)$ sends $3\to 2$, then $(1\,2)$ sends $2\to 1$, so $3\to 1$. Tracking $2$: $(1\,3\,2)$ sends $2\to 1$, then $(1\,2)$ sends $1\to 2$, so $2\to 2$. The cycle is $(1\,3\,2)$, exactly what you wrote.

The conjugation check now closes: $\sigma h \sigma^{-1} = (1\,3\,2)(1\,2)(1\,2\,3) = (1\,3\,2)$. That is the element of order 3 you were promised.

So far you have $g=(1\,2\,3)$ of order 3, and $\sigma=(1\,3\,2)$ acting on it by conjugation. The next line on your page should be the orbit of $h=(1\,2)$ under repeated conjugation by $g$ — the three conjugates $h,\ ghg^{-1},\ g^2hg^{-2}$ — and then the subgroup of $\Symn{3}$ they generate. We will write that as $\langle\,h,\ g\,\rangle$ and read it off from the orbits on $\{1,2,3\}$.

**Your move:** compute $g^2 h g^{-2}$ on the page (same convention, same tracking), write the three conjugates side by side, and tell me which subgroup of $\Symn{3}$ they generate.
