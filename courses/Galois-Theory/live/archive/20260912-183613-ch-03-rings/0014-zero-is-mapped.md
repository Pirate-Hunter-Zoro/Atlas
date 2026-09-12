---
kind: wrong
title: $3 \mapsto 3/1$ is right. "$0$ is not mapped" is false.
---

The equivalence relation line is correct as written, and $3 \mapsto 3/1$ is correct.

The last line is where it breaks. **$0_R$ is mapped.** The embedding $a \mapsto a/1_R$ is defined for *every* $a \in R$ with no exception, so $0 \mapsto 0/1_R$, and $0/1_R$ is $0_F$. Nothing in $R$ is left out — that is what makes it a ring homomorphism at all: it has to send $0_R$ to $0_F$ and $1_R$ to $1_F$.

Where $0_R$ is genuinely forbidden is the **denominator**, and that is a different slot in the same expression. Which is the flat correction on the line above it: you wrote

$$F = \{\, r_1/r_2 \;:\; r_1, r_2 \in R \,\}$$

and it needs $r_2 \neq 0_R$. Numerators range over all of $R$, including $0_R$; denominators over $R \setminus \{0_R\}$. You already had that condition written correctly on the right-hand side of the diagram for $b$.

So the question is still open, and it is asking for something else. The image of $\mathbb{Z} \to \mathbb{Q}$ is the set of all fractions of the form $a/1$ — a faithful copy of $\mathbb{Z}$ sitting inside $\mathbb{Q}$. Every integer is in there. But $\mathbb{Q}$ is *strictly bigger* than that copy, and the elements it has left over are the entire reason $F$ is worth constructing.

**Your move.** Name one element of $\mathbb{Q}$ that is **not** equal to $a/1$ for any integer $a$ — and say in one line why no integer maps to it.
