---
kind: correct
title: $b \neq 1$ is right. Now say the same thing one level up.
---

Correct. In lowest terms an element of $\mathbb{Q}$ is an integer exactly when its denominator is $1$, so the classes nothing maps to are exactly those with $\gcd(a,b)=1$ and $b \neq 1$. The step that carried it was keeping $\gcd(a,b)=1$: it pins a single representative, and only then does a condition on $b$ mean anything.

So $\mathbb{Z} \hookrightarrow \mathbb{Q}$ is injective and **not** surjective, and the things it misses are the whole point of $\mathbb{Q}$.

Now look at your arrow, which has not changed in eight revisions:

$$\phi : R[x_1,\ldots,x_n] \longrightarrow F(x_1,\ldots,x_n).$$

That is the same shape of map as $\mathbb{Z} \to \mathbb{Q}$, one level up — and you already settled, earlier, that $x_1$ has no inverse in $\mathbb{Z}[x_1,x_2]$ while $1/x_1$ sits in $\mathbb{Q}(x_1,x_2)$. So $\phi$ misses things, exactly as $\mathbb{Z} \to \mathbb{Q}$ does.

**3.2, in full:** *Suppose that $R$ is an integral domain, with field of fractions $F$. Show that the field of fractions of $R[x_1,\ldots,x_n]$ can be identified naturally with $F(x_1,\ldots,x_n)$.*

- *Field of fractions of $D$:* the classes $a/b$, $a,b \in D$, $b \neq 0_D$, with $a/b = c/d \iff ad = bc$.
- *$F(x_1,\ldots,x_n)$:* by definition the field of fractions of $F[x_1,\ldots,x_n]$.
- *Identified:* an isomorphism of rings, not merely an injection.

**Your move.** Write the corrected arrow: what does the domain of $\phi$ have to be?
