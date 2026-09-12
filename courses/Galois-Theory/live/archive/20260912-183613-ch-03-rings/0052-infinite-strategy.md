---
kind: note
title: Right shape, wrong handle — subtract them instead of matching coefficients.
---

Taking your questions in order.

**"Is that the way to go here?"** The outer shape is right: assume $\Phi(f) =
\Phi(g)$ and force $f = g$, by contradiction if you like. The handle is wrong.
"Suppose one coefficient were mismatched" gives you nothing to contradict —
there is nothing absurd about two polynomials disagreeing in the $x^{3}$ slot,
and you have no way to reach from that one slot to anything false.

**Use that $\Phi$ is a homomorphism**, which you have already proved. Then
$$\Phi(f - g) = \Phi(f) - \Phi(g) = M - M = 0,$$
so $f - g \in \Ker\Phi$. And injectivity of a homomorphism *is* $\Ker\Phi =
\{0\}$ — the criterion you used in the finite case. So the two polynomials
collapse into one: you are no longer comparing $f$ against $g$, you are asking
what a single polynomial $h$ with $h(k) = 0$ for **every** $k \in K$ can be,
when $K$ is infinite. One object, one condition.

**"It wasn't in the finite case."** Correct, and hold onto it. In the finite
case you killed injectivity by exhibiting $\prod_{k \in K}\delta_{k}$ — a
non-zero polynomial vanishing on all of $K$. Whatever you do next has to be
something that argument cannot survive when $K$ is infinite.

**"I'm stuck."** Fine. One rung, then.

---

**Your move.** Work in $\mathbb{Q}[x]$. Write down the non-zero polynomial of
*smallest possible degree* that vanishes at all five of $0, 1, 2, 3, 4$, and say
what its degree is.
