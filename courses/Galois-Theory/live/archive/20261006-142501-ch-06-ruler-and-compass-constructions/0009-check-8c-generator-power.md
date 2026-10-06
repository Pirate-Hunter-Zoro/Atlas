---
kind: lesson
title: check 8c-generator-power
---
The root half is right, with one correction. The reason $\zeta_p^{\,k} \neq 1$ is $k < p$, not $k > 0$: at $k = p$ you get $\zeta_p^{\,p} = 1$. So $(\zeta_p^{\,k})^p = (\zeta_p^{\,p})^k = 1$, and since $\zeta_p^{\,k} \neq 1$ it is a root of the factor $\Phi_p$, not of $x - 1$.

The field half describes the elements of $\mathbb{Q}(\zeta_p^{\,k})$ but does not say which field it is. The point is that it equals $\mathbb{Q}(\zeta_p)$. One inclusion is free: $\zeta_p^{\,k}$ is already in $\mathbb{Q}(\zeta_p)$. The other needs $\zeta_p$ to be a polynomial in $\zeta_p^{\,k}$ — in fact a single power of it.

Try it on the smallest case first. Take $p = 5$ and $k = 2$.

What you need:
- $\zeta_5 = e^{2\pi i/5}$, so $\zeta_5^{\,5} = 1$ and exponents of $\zeta_5$ only matter mod $5$.
- $\mathbb{Q}(\beta)$ is the smallest field containing $\mathbb{Q}$ and $\beta$; it contains every power of $\beta$.

With $p = 5$, $k = 2$: find $m$ with $(\zeta_5^{\,2})^m = \zeta_5$. What condition on $m$, stated mod $5$, did you use?
