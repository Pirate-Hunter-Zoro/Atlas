---
kind: note
title: You are not looking for $ab^{-1}$. You are looking for a different representative.
---

You wrote: *all I know is that $b^{-1}$ exists but $ab^{-1}$ need not be in $\mathbb{Z}[x]$.* That is true, and it is also not what is being asked — which is exactly why you are stuck.

$ab^{-1}$ is not the target. An element of $\mathbb{Q}(x)$ **is** the class $a/b$, and the class does not change when you multiply both entries by the same non-zero $d$: the pairs $(a,b)$ and $(da, db)$ are related, since $a \cdot db = b \cdot da$. So $a/b = (da)/(db)$, same element, different representative.

That is precisely what you did last card. You did not invert $x$. You replaced the pair $(\tfrac12 x + 1,\; x)$ with the pair $(x+2,\; 2x)$ — same class, and both entries now in $\mathbb{Z}[x]$.

So $d$ has no obligation to simplify anything. Its one job: make $da$ and $db$ **both** land in $\mathbb{Z}[x]$.

Before the general $a$ and $b$, one concrete pair.

**Your move.** Take

$$a = \tfrac{1}{2}x^{2} + \tfrac{2}{3}x, \qquad b = \tfrac{5}{6}x + 3 .$$

Name the single integer $d$ for which $da$ and $db$ have *all* their coefficients in $\mathbb{Z}$, and write out $da$ and $db$.
