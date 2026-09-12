---
kind: wrong
title: Both divisibility halves are right. Neither direction ever mentions a unit.
---

The divisibility content is correct in both directions and nothing on the page
is false.

Forward: $ab \in (c)$ gives $cr = ab$, so $c \mid ab$, so $c \mid a$ or
$c \mid b$, so $a \in (c)$. Right. Reverse: $bc \in (a)$ forces $b \in (a)$ or
$c \in (a)$, hence $a \mid b$. Right — you relabelled the element as $a$ there,
which is harmless, but rename it back to $c$ when you write it out.

**The break is that "prime ideal" is two words and you have only proved one of
them.**

$$\text{prime ideal} \;=\; \text{proper} \;+\; (ab \in I \Rightarrow a \in I \text{ or } b \in I)$$

Your forward direction ends at the second word. It never says $(c) \neq R$. And
the definition of a prime *element* also has a clause you never used: $c$ is
non-zero **and not a unit**. Those two are the same fact seen from either side,
and it is the hinge listed on the last card:

- *$(c) = R \iff c$ is a unit* — you proved both directions of this in 3.11.

So each direction owes one extra line, and they are mirror images. Take the
forward one only.

---

**Your move.** Assume $c$ is prime, so $c$ is non-zero and not a unit. Show that
$(c)$ is proper, i.e. $(c) \neq R$.

One line, and the hinge above is the whole of it — do not reprove it.
