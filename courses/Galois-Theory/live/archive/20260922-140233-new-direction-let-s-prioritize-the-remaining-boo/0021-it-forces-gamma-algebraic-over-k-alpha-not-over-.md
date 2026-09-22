---
kind: lesson
title: it-forces-gamma-algebraic-over-k-alpha-not-over-k
---
It does not force $\gamma$ algebraic over $K$. It forces $\gamma$ algebraic over
$K(\alpha)$, and the step from there down to $K$ is the tower law, one line later.
Your line $f(\gamma) - \alpha g(\gamma) = 0$ is exactly right and is the whole
engine of the problem.

Look at what polynomial that is a root of. Set $p(x) = f(x) - \alpha g(x)$. Its
coefficients are $f_i - \alpha g_i$. Those are not in $K$, because $\alpha$ is not.
They are in $K(\alpha)$. So $p \in K(\alpha)[x]$ and $p(\gamma) = 0$: that is the
definition of $\gamma$ being algebraic over $K(\alpha)$.

And $\alpha \notin K$ is not spent on the base field. It is spent on something you
have not checked yet: that $p$ is not the *zero* polynomial. A root of the zero
polynomial proves nothing, since every element is one.

What it uses:

- $\alpha \notin K$, $\alpha$ algebraic over $K$, $\beta$ transcendental over $K$.
- $K(\gamma)$ — all quotients $f(\gamma)/g(\gamma)$ with $f, g \in K[x]$ and $g(\gamma) \ne 0$.
- Algebraic over $L$ — some non-zero polynomial in $L[x]$ has it as a root.
- $K(\alpha)[x]$ — polynomials whose coefficients lie in $K(\alpha)$.
- Zero polynomial — every coefficient is $0$. Not a witness for algebraic.
- Tower law — $[M:K] = [M:L][L:K]$ for $K \subseteq L \subseteq M$.

**Your move.** Suppose, for contradiction, that $p(x) = f(x) - \alpha g(x)$ *is*
the zero polynomial, so $f_i - \alpha g_i = 0$ for every $i$. Recall $g$ is not the
zero polynomial, so some $g_i \ne 0$. Derive a contradiction with $\alpha \notin K$
from that — two lines, and say which line needs $g_i \ne 0$.
