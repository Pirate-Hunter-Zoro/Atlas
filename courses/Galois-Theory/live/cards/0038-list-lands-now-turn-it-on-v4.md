---
kind: correct
title: None in either — so that was the wrong test
---
Right, and exactly right. Write the two subgroups out and there is nowhere for a transposition to hide:

$$V_4 = \{e,\ (12)(34),\ (13)(24),\ (14)(23)\}$$
$$\gen{(1234)} = \{e,\ (1234),\ (13)(24),\ (1432)\}$$

Three double transpositions in one; two $4$-cycles and one double transposition in the other. Not a single $(ab)$ anywhere.

So the question I asked on card 0035 — *which one contains no 2-cycles* — does not separate them, because neither does. Your list is what showed that. Scratch it.

The test that *does* separate them is the one you named yourself: **conjugation preserves cycle type**. So a normal subgroup cannot hold some elements of a given cycle type and not the others — conjugating would walk you straight out of it.

That kills $\gen{(1234)}$ immediately. It holds the $4$-cycles $(1234)$ and $(1432)$, and $S_4$ has more $4$-cycles than those two, so some conjugate of $(1234)$ lands outside. Not normal.

Now turn the same test on $V_4$, where it has to come out the other way.

**Write out every element of $S_4$ of cycle type $2{+}2$** — that is, every product of two *disjoint* transpositions. List them one per line. How many are there, and which of them are missing from $V_4$?
