---
kind: note
title: The letter P never appears on your line 1
---

Fair enough — that was too vague. Here is the concrete version.

Look at your page. Line 1 is a statement about **sets**:

$$E = EF \cup EF^{c}.$$

Nowhere on your page does a $P$ ever get put in front of it. That is the entire missing move: **take $P$ of both sides.** Then the disjointness you annotated is what lets axiom 3 split the right-hand side.

Watch it happen with actual numbers. One fair die, $E=\{1,2,3,4\}$, $F=\{3,4,5\}$:

| set | outcomes | probability |
|---|---|---|
| $E$ | $\{1,2,3,4\}$ | $4/6$ |
| $EF$ | $\{3,4\}$ | $2/6$ |
| $EF^{c}$ | $\{1,2\}$ | $2/6$ |

The set identity says $\{1,2,3,4\} = \{3,4\}\cup\{1,2\}$. Put $P$ on it and the two disjoint pieces add:

$$\tfrac{4}{6} = \tfrac{2}{6} + \tfrac{2}{6}.$$

Now read that as an equation to be **rearranged**, not just verified. If I want the middle term $P(EF^{c})=2/6$ on its own, I subtract: $2/6 = 4/6 - 2/6$, that is, $P(EF^{c}) = P(E) - P(EF)$.

That is ordinary algebra on an equation with three quantities in it. Nothing probabilistic happens after axiom 3 fires.

---

**Your move.** Take $P$ of both sides of your own line 1, in general — no die, just $E$ and $F$ — and write the equation axiom 3 gives you. Then rearrange it so that $P(EF^{c})$ sits alone on the left.

One line, then one more. Do not touch line 2 yet.
