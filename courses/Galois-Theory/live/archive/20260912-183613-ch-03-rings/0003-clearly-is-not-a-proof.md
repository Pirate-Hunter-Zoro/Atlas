---
kind: wrong
title: The pair is right. "Clearly" is not a proof.
---

Settled, and I will not ask for it again:

- The zero of $R^S$ is the constant function $s \mapsto 0_R$ and the identity is $s \mapsto 1_R$. Both correct.
- The pair in the lower block is exactly the right pair: $f$ equal to $1_R$ at $s_1$ and $0_R$ elsewhere, $g$ equal to $1_R$ at $s_2$ and $0_R$ elsewhere, with $s_1 \neq s_2$. Their product is the zero function, and for the right reason — at every $s$, at least one of the two factors is $0_R$.

**The break is the third line of the upper block.** *"Clearly by the specified function properties we have all ring properties"* is the thing 3.1 asks you to show, restated as though it had been shown. It names no axiom, and it never uses the one fact the whole problem turns on: both operations are defined **pointwise**, so an identity in $R^S$ is the corresponding identity in $R$, evaluated at each $s$ separately.

**Two smaller things in the lower block.** What you exhibited is called a **zero divisor** — a non-zero element whose product with another non-zero element is $0$. "Non-zero divisor" is the opposite property. And nothing there says *why* $f$ and $g$ are non-zero; that is one line, and it needs an axiom of $R$.

**Your move.** One axiom, written out in full, to fix the shape. Let $f, g, h \in R^S$ and prove left distributivity:
$$f(g+h) = fg + fh.$$
Two elements of $R^S$ are equal iff they agree at every $s \in S$. So fix an arbitrary $s \in S$, evaluate each side at $s$ using only the two defining formulas, and name the property of $R$ that closes the gap between them.

Four or five lines. This one axiom, not all of them.
