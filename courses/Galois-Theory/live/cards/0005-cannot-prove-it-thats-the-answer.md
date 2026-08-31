---
kind: note
title: You cannot prove it, and that is the answer
---

**You asked how to prove $g H g^{-1}$ is a coset of $H$. Straight answer: you cannot,
and you should stop trying.** Not for want of a trick — there is no trick.

Suppose you had it. $g H g^{-1}$ is a subgroup, so it contains $e$. The cosets of $H$
partition $G$ and $e \in H$, so **the only coset containing $e$ is $H$ itself**. Then
"$g H g^{-1}$ is a coset" hands you $g H g^{-1} = H$ on the spot — which is the whole
exercise. Any proof of your lemma is already a proof of 1.3.

That is why three attempts have died at the same line. Your algebra was never the
problem. You have been trying to prove 1.3 as a step towards proving 1.3.

(The sentence itself you have now fixed: "if $g H g^{-1}$ is a coset **and** a group,
it must be $H$" is the correct form of that inference. That part is settled.)

**Now the thing worth taking away.**

"$G = H \cup g^{*}H$, disjoint" is a statement about **elements**: every element of $G$
lies in exactly one of the two pieces. It is not a statement about **sets**. An
arbitrary subset of $G$ is under no obligation to sit inside one piece — it may have
some members in $H$ and some in $g^{*}H$. So "which piece is $g H g^{-1}$?" is a
question with no answer available, and that is the wall you keep walking into.

One element at a time, though, the dichotomy is free. $g h g^{-1}$ is a single element
of $G$, so it is in one piece or the other, and there is nothing to prove.

---

**Your move.** Drop the set.

> Take $g \notin H$ and one $h \in H$, and put $x = g \circ h \circ g^{-1}$. Since
> $g \notin H$, the second coset is $gH$ itself. So $x \in H$ or $x \in gH$. Suppose
> $x \in gH$ — what does that force about $g$?
