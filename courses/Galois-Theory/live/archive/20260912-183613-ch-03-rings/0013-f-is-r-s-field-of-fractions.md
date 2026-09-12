---
kind: note
title: Yes. $F$ is not some other field — it is built out of $R$.
---

Direct answer to the bubble: **yes**, and it is the tightest relation available.

The hypothesis of 3.2 says it outright: *$R$ is an integral domain, with field of fractions $F$.* $F$ is not a field handed to you alongside $R$. It is manufactured from $R$ and nothing else:

$$F = \{\, a/b \;:\; a,b \in R,\; b \neq 0_R \,\}, \qquad a/b = c/d \iff ad = bc.$$

Every symbol on the right-hand side of that is an element of $R$.

And $R$ sits *inside* $F$: the map $a \mapsto a/1_R$ is an injective ring homomorphism, so $F$ contains a faithful copy of $R$. That is the whole content of "relate".

Your example is right for exactly this reason: $\mathbb{Q}$ *is* the field of fractions of $\mathbb{Z}$. Had you written $R = \mathbb{Z}$, $F = \mathbb{R}$, the hypothesis would simply be false — $\mathbb{R}$ is a field containing $\mathbb{Z}$, but it is not $\mathbb{Z}$'s field of fractions. Containing $R$ is not enough; $F$ has to be *generated* by quotients of elements of $R$.

Why this is the hinge of 3.2 and not a side remark: both objects in the statement are towers built on the same ground floor. On the left, the field of fractions of $R[x_1,\ldots,x_n]$. On the right, $F(x_1,\ldots,x_n)$ — which is the field of fractions of $F[x_1,\ldots,x_n]$, and $F$ itself came from $R$. One ring at the bottom of both. That shared bottom is what makes an identification *natural* rather than a coincidence.

**Your move.** Take $R = \mathbb{Z}$, $F = \mathbb{Q}$, with the embedding $a \mapsto a/1_R$. Write down which element of $\mathbb{Q}$ the integer $3$ is sent to, and then name one element of $\mathbb{Q}$ that is **not** in the image of that map.
