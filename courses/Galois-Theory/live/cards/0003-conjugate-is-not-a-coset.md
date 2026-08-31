---
kind: wrong
title: 1.3 — "another coset of H" is the thing you have to prove
---

**Settled, and it is exactly what was missing before.** You have now used index 2
properly: for $g \notin H$ the two cosets are $H$ and $gH$, they are disjoint, and
together they exhaust $G$. That partition is right, and rev 1 never had it.

**The break is the four words "another coset of $H$".**

Nothing on the page entitles you to them. $g H g^{-1}$ is a *conjugate* of $H$; a
conjugate is not a coset. In $\Sigma_3$ with $H = \{e,(12)\}$ and $g = (13)$ you get
$g H g^{-1} = \{e,(23)\}$, and that is not a coset of $H$ — not a left one, not a right
one.

And in the index-2 case that phrase is not a small gap, it is the entire exercise. The
only coset that contains $e$ is $H$ itself, so the instant you are allowed to call
$g H g^{-1}$ a coset, your next two lines finish the proof automatically. All of the
content is hiding inside that one unproven word. It is the same assumption as rev 1 —
you have given it a name rather than a justification.

One smaller thing, because it will wreck the next step if it survives: you pick
$g \neq e$ and conclude $gH \neq H$. That does not follow. $gH = H$ precisely when
$g \in H$, so the hypothesis you want throughout is $g \notin H$.

The closure computation at the bottom is left over from rev 1 and now does nothing.

---

**Your move.** Stop arguing about the *set* $g H g^{-1}$ and argue about one *element*
of it.

> Fix $g \notin H$ and $h \in H$, and put $x = g \circ h \circ g^{-1}$. Your partition
> says $x \in H$ or $x \in gH$, with no third option. Suppose $x \in gH$. What does
> that force about $g$?
