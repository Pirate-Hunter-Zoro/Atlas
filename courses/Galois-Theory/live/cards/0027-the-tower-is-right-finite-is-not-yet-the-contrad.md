---
kind: lesson
title: the-tower-is-right-finite-is-not-yet-the-contradiction
---
Both finiteness reasons are right, and so is the product. $[K(\alpha):K]$ is
finite because $\alpha$ has a minimal polynomial over $K$. $[K(\alpha,\gamma):
K(\alpha)]$ is finite because $\alpha = f(\gamma)/g(\gamma)$ makes
$f(x) - \alpha g(x)$ a non-zero polynomial over $K(\alpha)$ with $\gamma$ as a
root. The tower law multiplies the two, so $[K(\alpha,\gamma):K]$ is finite.
None of that needs changing.

You stopped one sentence short. A finite degree is not by itself absurd, so
"is finite" is not yet the contradiction. One more move turns that finite
number into a claim about $\gamma$ itself, and that claim is what collides with
the case you are standing in.

Small wording fix: algebraic **over** $K(\alpha)$, not **in** it. "In" is
membership in a field; "over" names the field the coefficients are drawn from.

**Exercise 4.10.** Suppose $K(\alpha, \beta) : K$ is an extension, that
$\alpha$ is algebraic over $K$ but not in $K$, and that $\beta$ is
transcendental over $K$. Show that $K(\alpha, \beta) : K$ is not simple.

Where you are: you assumed some $\gamma$ with $K(\gamma) = K(\alpha, \beta)$,
and split on $\gamma$. The algebraic case is closed. This is the
transcendental case, so $\gamma$ is transcendental over $K$.

What it uses:

- Simple extension — $M : K$ is simple if $M = K(\gamma)$ for a single
  $\gamma \in M$.
- $[M:L]$ — the dimension of $M$ as a vector space over $L$; finite means a
  finite basis.
- Transcendental over $K$ — not a root of any non-zero polynomial in $K[x]$.
- Algebraic over $L$ — a root of some non-zero polynomial in $L[x]$.
- Degree of an algebraic element — if $\delta$ is algebraic over $L$ with
  minimal polynomial of degree $n$, then $[L(\delta):L] = n$.
- Tower law — for $L \subseteq M \subseteq N$, $[N:L] = [N:M]\,[M:L]$.
- Finite implies algebraic — if $[M:L]$ is finite, every element of $M$ is
  algebraic over $L$. The powers $1, \delta, \delta^2, \dots$ cannot all be
  linearly independent over $L$, so some linear combination of finitely many
  of them vanishes, and that combination is a non-zero polynomial with
  $\delta$ as a root.

**Your move.** You have $[K(\alpha,\gamma):K]$ finite, and $\gamma$ lies in
$K(\alpha,\gamma)$. Say what that forces about $\gamma$ over $K$, and name the
assumption it contradicts.
