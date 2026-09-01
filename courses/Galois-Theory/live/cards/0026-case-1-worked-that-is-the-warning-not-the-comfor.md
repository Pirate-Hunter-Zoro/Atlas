---
kind: wrong
title: Case 1 worked — that is the warning, not the comfort
---
You split into two cases. Case 1 closed cleanly: when $g \in H$, the hypothesis $K \triangl H$ is exactly what you need, so $gkg^{-1} \in K$.

Then you wrote Case 2 ($g \notin H$) and reached for a tool you do not have: you wanted to say "since $K \triangl H$", and apply it to $k$ with the conjugating element $gkg^{-1}$. But the hypothesis $K \triangl H$ only lets you conjugate $k$ by elements **of $H$**. And $gkg^{-1}$ is an element of $H$ (you proved that on the line above — good), **not** the element you started with $g$.

So the conjugating element is wrong. You would need to conjugate $k$ by something in $H$ that, after rearrangement, gives $gkg^{-1} \in K$. There is no such rearrangement available in general.

Read that again: a proof attempt that **fails to produce the needed element from the hypotheses** is not an incomplete proof waiting for one more line. It is a failed proof attempt. And the failure is not a typo — it is the answer telling you "no".

The statement of Exercise 1.5 is **false**. Normality does **not** pass through. Your job now is to build a counterexample: a named group $G$, a named subgroup $H \triangl G$, a named subgroup $K \triangl H$, and one specific $g \in G$, $k \in K$ with $gkg^{-1} \notin K$.

The smallest place this happens is a group of order 12. You know $A_4$ (order 12) and you know the Klein four-group $V_4 \subseteq A_4$. Both should be on your shelf from earlier exercises.

**Your move:** name $G$, $H$, $K$, and the witness pair $(g, k)$.
