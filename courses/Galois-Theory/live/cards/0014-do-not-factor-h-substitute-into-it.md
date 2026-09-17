---
kind: lesson
title: do-not-factor-h-substitute-into-it
---
Line three is false as written. You have $h(x) = (x - \gamma^2)\ell(x)$, then
you replace $x - \gamma^2$ by $(x-\gamma)(x+\gamma)$. But
$(x-\gamma)(x+\gamma) = x^2 - \gamma^2$, which is a different polynomial from
$x - \gamma^2$.

The deeper trouble is where $\ell$ lives. The factor theorem applied to $h$ at
the root $\gamma^2$ gives $\ell$ with coefficients in $K(\gamma^2)$, not in
$K$. A factorisation whose coefficients already involve $\gamma^2$ cannot show
that $\gamma$ is algebraic *over $K$*. That needs one non-zero polynomial whose
coefficients lie in $K$ alone, with $\gamma$ as a root.

So do not factor $h$. Substitute into it.

**The warm-up again.** Let $\gamma$ be transcendental over $K$. Show that
$\gamma^2$ is transcendental over $K$. By contradiction: suppose some non-zero
$h \in K[x]$ has $h(\gamma^2) = 0$.

**Your move.** From that $h$, write down a single polynomial $q \in K[x]$,
obtained by substituting something for $x$ in $h$, such that $q(\gamma) = 0$.
Then say two things: what the coefficients of $q$ are in terms of the
coefficients of $h$, and why $q$ is not the zero polynomial. One line each.

This is the one fact the transcendental branch of 4.10 needs, so it is worth
getting cleanly.

What it uses:

- $K[x]$ — polynomials in $x$ with coefficients in $K$.
- Algebraic over $K$ — a root of some non-zero polynomial in $K[x]$.
- Transcendental over $K$ — not algebraic over $K$.
- The zero polynomial — every coefficient is $0$. A non-zero polynomial has at least one non-zero coefficient.
- $K(\gamma^2)$ — the smallest subfield containing $K$ and $\gamma^2$.
- Factor theorem — if $c$ is a root of $h$ then $h(x) = (x-c)\ell(x)$, with $\ell$ over whatever field contains $K$ and $c$.
- **Exercise 4.10**, where this is going — $K(\alpha,\beta):K$ an extension, $\alpha$ algebraic over $K$ but not in $K$, $\beta$ transcendental over $K$; show $K(\alpha,\beta):K$ is not simple.
