---
kind: wrong
title: Right track. Now your right-hand side is in the wrong currency.
---

Yes. The split is the correct one and the diagram shows you know why it works: you carved $E\cup F$ into

$$E\cup F = (EF^c)\ \cup\ (FE^c)\ \cup\ (EF)$$

three pieces that overlap nowhere, and let axiom 3 turn the union into a sum. That is the whole manoeuvre, and you found it without being shown it. Keep those lines.

Two things left, and only one of them is real work.

**The small one.** You wrote *(mutually exclusive)* in brackets. That is the step being graded, and a bracket is not an argument. An outcome in $EF^c$ is in $E$ and not in $F$; an outcome in $EF$ is in $F$. So nothing can be in both — and the same kind of one-line reason for the other two pairs. Say it in words on the page.

**The real one.** Look at where you are against where you are going:

| you have | you need |
|---|---|
| $P(EF^c) + P(FE^c) + P(EF)$ | $P(E) + P(F) - P(EF)$ |

$P(EF)$ is already sitting there in both. But $P(E)$ and $P(F)$ appear nowhere on your side — you have never written down the probability of $E$ itself, only of two slivers of it. No amount of rearranging those three terms will produce a $P(E)$, because the symbol is not in the room.

So you have to put it there, and the only tool that does that is the manoeuvre you have just used, applied to a smaller set.

> **Your move.** Forget $F\cup E$ for a moment. Take the set $E$ on its own and split *it* into two disjoint pieces, one of which is $EF^c$. Write down what axiom 3 gives you, then solve that line for $P(EF^c)$.

One line, on the same page, under what you already have. Do $F$ the same way once you have it, and the substitution finishes the proof.
