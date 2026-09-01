---
kind: correct
title: None in either — so that was the wrong test
---
Right, and exactly right. Write the two subgroups out and there is nowhere for a transposition to hide:

$$V_4 = \{e,\ (12)(34),\ (13)(24),\ (14)(23)\}$$
$$\gen{(1234)} = \{e,\ (1234),\ (13)(24),\ (1432)\}$$

Three double transpositions in one; two $4$-cycles and one double transposition in the other. Not a single $(ab)$ anywhere.

So the question I asked on card 0035 — *which one contains no 2-cycles* — does not separate them, because neither does. You had already written "also no 2-cycles" against $V_4$ in your own margin before I asked. Scratch that question.

The test that *does* separate them is the one you named yourself: **conjugation preserves cycle type**. So a normal subgroup cannot hold some elements of a given cycle type and not the others — conjugating would walk you straight out of it.

That kills $\gen{(1234)}$. It holds the $4$-cycles $(1234)$ and $(1432)$, and $S_4$ has six $4$-cycles in all, so some conjugate of $(1234)$ lands outside it. Not normal.

$V_4$ goes the other way, and you can see it from the list above: the only cycle type in it is $2{+}2$, and $(12)(34), (13)(24), (14)(23)$ are *all* the $2{+}2$ elements of $S_4$. Nothing to walk out to. Normal.

That closes 1.7. The live question is on card 0040.
