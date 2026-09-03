---
kind: note
title: The reduction is right. You are stuck because you are still building $h$.
---

Two things on the page are correct and settled.

$0_{K^{K}} = M - M = \Phi(f) - \Phi(g) = \Phi(g-f)$, so $h = g-f \in \Ker\Phi$.
That is the reduction, and it is done.

And your reason the finite trick dies is right: $\prod_{k \in K}\delta_{k}$ over
an infinite $K$ would be a product of infinitely many factors, which is not a
polynomial at all. Correct, and worth having said.

**Now the reason you are stuck.** You are still hunting for a formula for $h$ —
some expression, built out of $\delta$'s or anything else, that you can look at
and see is zero. There is no such formula to find, and looking for one is what
is costing you the exercise.

$h$ is not something you construct here. It is something you *rule out*. You
know exactly one thing about it — $h(k) = 0$ for every single $k \in K$ — and
the question is not "what does such an $h$ look like" but "how much room is
there for a non-zero one to exist at all". So: stop writing $h$ down, and start
counting.

You used the degree fact in one direction on the last card: given the roots, the
degree has to be at least this big. The other direction is what you have not
touched.

---

**Your move.** Work in $\mathbb{Q}[x]$, and forget $\Phi$ entirely for a
moment. I claim there is a non-zero polynomial of degree $3$ having all four of
$0, 1, 2, 3$ as roots. Either write one down, or say what stops you.
