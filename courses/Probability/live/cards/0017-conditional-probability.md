---
kind: lesson
title: Conditional probability — shrink the sample space, then renormalise
---

Rev 4 has it: a *sequence*, length $\ell$. Problem 4 is closed and transcribed.

---

Everything left on this sheet turns on one idea. You are told something has
happened, and you want the probability of something else *given* that.

Being told $B$ happened does two things. It throws away every outcome outside
$B$ — those are now impossible. And it leaves the surviving outcomes in the same
proportions to one another as before, because nothing you were told changed how
they compare. So the only part of $A$ that can still happen is $AB$, and its
probability is measured against $B$ rather than against $S$:

$$P(A \mid B) = \frac{P(AB)}{P(B)}, \qquad P(B) > 0.$$

The denominator is the renormalisation. Without it $P(\cdot \mid B)$ would not
sum to $1$ over the new, smaller space, and it would not be a probability at
all. Note also that $P(S \mid B) = P(B)/P(B) = 1$: conditioning on $B$ makes $B$
the whole world.

**One roll of a fair die.** Let $B = \{2,4,6\}$, the roll is even, and let
$A = \{4,5,6\}$, the roll exceeds $3$. Unconditionally $P(A) = 3/6 = 1/2$. Told
the roll is even, the world is $\{2,4,6\}$ and the part of $A$ still alive is
$AB = \{4,6\}$:

$$P(A \mid B) = \frac{2/6}{3/6} = \frac{2}{3}.$$

Two of the three surviving outcomes are in $A$ — which is what the formula was
built to say. Knowing the roll is even made "over $3$" more likely, from $1/2$
to $2/3$.
