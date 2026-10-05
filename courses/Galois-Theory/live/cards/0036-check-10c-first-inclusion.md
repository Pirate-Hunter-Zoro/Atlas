---
kind: lesson
title: check 10c-first-inclusion
---
Yes, you are on the right track. Your plan is the two inclusions, and that is the whole proof.

The first half is exactly what you wrote. If every root $\beta$ of $x^n - a$ lies in $\mathbb{Q}(\alpha, \zeta_n)$, then the splitting field is inside $\mathbb{Q}(\alpha, \zeta_n)$.

"No smaller field does it" is true, but it is not something you can check directly. Make it concrete instead: show $\alpha$ and $\zeta_n$ both lie in the splitting field. Any field holding all the roots then holds $\mathbb{Q}(\alpha, \zeta_n)$. That is the reverse inclusion, and it is the same move you made in 10(a).

Your "let $\beta$ be a root" route is slightly different from card 0035's recipe, and it works. It saves listing the $n$ roots first.

So, the first half now. Take any $\beta$ with $\beta^n = a$. Look at $\beta / \alpha$.

What you need:
- $a \in \mathbb{Q}^{\times}$ means $a$ is a nonzero rational.
- $\alpha^n = a$, so $\alpha \ne 0$.
- $\zeta_n = e^{2\pi i/n}$. Its powers $1, \zeta_n, \dots, \zeta_n^{n-1}$ are $n$ distinct roots of $x^n - 1$.
- A nonzero polynomial of degree $n$ has at most $n$ roots in a field.
- The splitting field of $f$ over $\mathbb{Q}$ is the field generated over $\mathbb{Q}$ by all the complex roots of $f$.
- A field is closed under products and quotients by nonzero elements.

Let $\beta$ be any complex root of $x^n - a$. Show $\beta = \alpha \zeta_n^k$ for some $k$, and conclude $\beta \in \mathbb{Q}(\alpha, \zeta_n)$.
