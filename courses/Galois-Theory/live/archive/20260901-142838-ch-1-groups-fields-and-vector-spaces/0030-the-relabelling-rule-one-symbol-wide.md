---
kind: wrong
title: The relabelling rule — one symbol wide
---
Stop multiplying. Conjugation is a relabelling, and here is the rule, written as a single equality:

$$g\,(a\ b)(c\ d)\,g^{-1} \;=\; (g(a)\ g(b))(g(c)\ g(d)).$$

The right side is read off from $g$, never computed. Each point on the left is sent by $g$ to the point on the right; that is the whole definition.

Now apply it with $g = (2\ 3)$. Send each number through $g$:

- $1 \mapsto 1$ (fixed by $g$)
- $2 \mapsto 3$
- $3 \mapsto 2$
- $4 \mapsto 4$ (fixed by $g$)

So $(1\ 2)(3\ 4)$ relabels to $(g(1)\ g(2))(g(3)\ g(4)) = (1\ 3)(2\ 4)$.

That is the answer — one line, no products, no $g^{-1}$ in sight.

**What you missed on card 0025.** Your write-up of Exercise 1.5 *was* correct, and I closed it as such (card 0029). The shortcut in this card is a speed note for the rest of the course, not a correction. Tell me, in one line: with $g = (2\ 3)$, what is $g(4)$?
