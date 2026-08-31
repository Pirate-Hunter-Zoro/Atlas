---
kind: note
title: Both conjugations say the same thing — the quantifier does it
---

You underlined the definition line in the fact list and wrote **"Defn"**. Fair. That line
says $H$ is normal when
$$g^{-1} \circ h \circ g \in H \quad \text{for every } g \in G,\ h \in H,$$
and every card since has had you chasing $g \circ h \circ g^{-1} \in H$. Two different
expressions, and you have been asked to land on one while working with the other.

**They are the same condition.** Not "equivalent by a lemma you have to prove" — the same
condition, and what makes them the same is the phrase **for every $g \in G$**.

Here is the whole of it. The condition is not about one $g$. It is a claim about the
entire collection of elements you get by conjugating $h$ by everything in $G$. And as $g$
runs over all of $G$, so does $g^{-1}$ — inversion sends $G$ onto $G$, hitting every
element exactly once. So the two collections
$$\{\, g^{-1} \circ h \circ g : g \in G \,\} \quad\text{and}\quad \{\, g \circ h \circ g^{-1} : g \in G \,\}$$
have exactly the same members. Same set, relabelled. Either one lies inside $H$ precisely
when the other does.

So the work you are doing now **is** Garling's condition. You do not owe an extra line for
it, and my earlier warning about owing one applies to the *coset* route, not this.

---

**Your move.** Do the relabelling by hand, so it is yours and not mine.

> Take the statement "$g \circ h \circ g^{-1} \in H$ for every $g \in G$ and every
> $h \in H$". It is true for **every** $g$, so it is true for $g^{-1}$. Write out what the
> statement says with $g^{-1}$ put in place of $g$, and simplify it.

Then back to the cancellation from the last card — that question is still open.
