---
kind: lesson
title: not-for-every-i-for-one-i-and-that-is-the-whole-fix
---
Your contradiction is right and the quantifier on it is wrong. You wrote "prove
$f_i - \alpha g_i \ne 0$ for all $i$", and that is false. Where $g_i = 0$ the
coefficient is just $f_i$, and $f_i$ is very often $0$ too — any $i$ above the
degree of both $f$ and $g$ makes both vanish.

You do not need all $i$. A polynomial is non-zero as soon as ONE coefficient is
non-zero. So choose an $i$ with $g_i \ne 0$, which exists because $g$ is not the
zero polynomial, and run your two lines at that $i$ only: if $f_i - \alpha g_i = 0$
then $\alpha = f_i g_i^{-1}$, and that inverse exists precisely because you chose
$g_i \ne 0$. That is the line you were asked to name. So $p(x) = f(x) - \alpha g(x)$
is a non-zero element of $K(\alpha)[x]$ with $p(\gamma) = 0$, and $\gamma$ is
algebraic over $K(\alpha)$. Everything down to your last line is now closed.

**4.10, in full.** $\alpha$ is algebraic over $K$ and $\alpha \notin K$;
$\beta$ is transcendental over $K$. Show that $K(\alpha, \beta) : K$ is not simple.

What it uses:

- Simple extension — $L : K$ with $L = K(\gamma)$ for a single $\gamma \in L$.
- Algebraic over $L$ — some non-zero polynomial in $L[x]$ has it as a root.
- Transcendental over $L$ — no such polynomial.
- $[M : L]$ — the dimension of $M$ as a vector space over $L$.
- $\alpha$ algebraic over $K$ gives $[K(\alpha) : K]$ finite.
- Tower law — for $K \subseteq L \subseteq M$, $[M : K] = [M : L][L : K]$.
- Finite degree over $K$ makes every element algebraic over $K$.
- Established: $\gamma$ transcendental, $K(\gamma) = K(\alpha, \beta)$,
  and $\gamma$ algebraic over $K(\alpha)$.

**Your move.** You have $\gamma$ algebraic over $K(\alpha)$, and you want $\gamma$
algebraic over $K$ — which contradicts the transcendental case you are in. Get
there with the tower law, using $K \subseteq K(\alpha) \subseteq K(\alpha)(\gamma)$.
Two degrees are finite; say which, and why each one is.
