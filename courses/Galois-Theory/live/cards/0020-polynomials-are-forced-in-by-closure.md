---
kind: lesson
title: polynomials-are-forced-in-by-closure
---
Polynomials in $\gamma$ are not something we add. The field axioms force them
in. Your definition is exactly the right place to start: $K(\gamma)$ is the
smallest field containing $K$ and $\gamma$. Now follow what "field" makes you
keep.

It contains $\gamma$. A field is closed under multiplication, so it also
contains $\gamma^2$, $\gamma^3$, every power. It contains each $c \in K$, so it
contains $c\gamma^n$. It is closed under addition, so it contains any finite sum
of those, for instance $c_3\gamma^3 + c_1\gamma + c_0$. A finite sum of that
shape *is* what "a polynomial in $\gamma$" means: it is $f(\gamma)$ for some
$f \in K[x]$.

Then division. A field is closed under dividing by anything non-zero, so it
contains $f(\gamma)/g(\gamma)$ for every $f,g \in K[x]$ with $g(\gamma) \ne 0$.
Nothing was chosen at any step; each one was forced. And the set of all those
quotients is itself a field, so the smallest field cannot be smaller than it.
That is why $K(\gamma)$ *equals* that set.

$K(\alpha,\beta)$ is the same story with two letters instead of one.

What it uses:

- $K(\gamma)$ — the smallest subfield containing $K$ and $\gamma$.
- Field — closed under $+$, $-$, $\times$, and division by non-zero elements.
- $K[x]$ — polynomials with coefficients in $K$.
- $f(\gamma)$ — the element you get by putting $\gamma$ in for $x$ in $f$.
- Transcendental over $K$ — no non-zero polynomial in $K[x]$ has it as a root.

Where this goes: in 4.10 we had $\alpha \in K(\gamma)$, and this fact is the
only reason some $f$ and $g$ with $\alpha = f(\gamma)/g(\gamma)$ exist.

**Your move.** Let $K = \mathbb{Q}$ and let $\gamma$ be transcendental over
$\mathbb{Q}$. Here are four expressions: $\gamma^5$; $7\gamma^3 - 2\gamma + 4$;
$1/(\gamma^2+1)$; $\sqrt{\gamma}$. Three of them are forced into
$\mathbb{Q}(\gamma)$ — say which three, and which closure rule forces each one
in. For the remaining one, say why no closure rule puts it there.
