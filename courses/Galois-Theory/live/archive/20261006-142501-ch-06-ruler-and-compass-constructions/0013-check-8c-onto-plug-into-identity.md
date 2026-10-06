---
kind: lesson
title: check 8c-onto-plug-into-identity
---
Do not expand the sum. Plug $\zeta_p^k$ into the product identity instead: it has $\Phi_p$ as a factor, so it hands you $\Phi_p(\zeta_p^k)$ times something.

Your setup is right: $\zeta_p^k = e^{2\pi i k/p}$ with $0 < k < p$. Summing $p$ powers of it directly is the hard road. The identity $(x-1)\,\Phi_p(x) = x^p - 1$ is the easy one.

Put $x = \zeta_p^k$ into it. Two things to settle:
- What is $(\zeta_p^k)^p$? So what is the right-hand side?
- Is $\zeta_p^k - 1$ zero or not, given $0 < k < p$?

Then a product of two complex numbers is $0$ with one factor nonzero. That finishes it.

What you need:
- $\zeta_p = e^{2\pi i/p}$, $p$ prime, $1 \le k \le p-1$.
- $\Phi_p(x) = x^{p-1} + \dots + x + 1$.
- $(x-1)\,\Phi_p(x) = x^p - 1$, true for every complex $x$.
- $e^{2\pi i t} = 1$ exactly when $t$ is an integer.

Show: $\Phi_p(\zeta_p^k) = 0$ for each $k$ with $1 \le k \le p-1$, by evaluating $(x-1)\,\Phi_p(x) = x^p - 1$ at $x = \zeta_p^k$.
