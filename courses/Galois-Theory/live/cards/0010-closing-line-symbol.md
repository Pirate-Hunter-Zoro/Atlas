---
kind: wrong
title: The last line says the opposite of what you proved
---

The hard half landed. *"$x \in H$ since $H, gH$ partition $G$"* is the step the whole
exercise was waiting for — that is where $[G:H] = 2$ finally does some work, and you named
the right fact without being told which one it was.

Now read your own sentence back:

> So since $x \in gH$ due to the contradiction, $x \in H$ since $H, gH$ partition $G$.

**One character is doing the wrong job.** You reached the contradiction by *supposing*
$x \in gH$; a contradiction discharges the supposition, so what you are left holding is the
opposite of what you wrote down. As it stands the sentence asserts $x \in gH$ and then
concludes $x \in H$ on the grounds that the two sets are **disjoint** — which is precisely
what a partition forbids. Fix the symbol; the sentence around it is already right.

And then finish it. What you have, for the $h$ you fixed on line two, is

$$x = g \circ h \circ g^{-1} \in H.$$

That is *one element*. The exercise asks about $gHg^{-1}$, which is a *set*. Look back at
how you introduced $h$ and ask what was arbitrary about it — then say what that buys you for
the whole set.

---

**Your move.** Rewrite the closing sentence with the right symbol and add the one line that
carries $x \in H$ up to $gHg^{-1}$. Strike the *"If $gHg^{-1} = H$, we're done"* line while
you are in there. That is the finished proof, and I write it into the chapter file the turn
it arrives.
