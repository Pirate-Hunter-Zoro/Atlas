---
kind: lesson
title: That was a photograph of the board. Here is the same step, with numbers.
---

What arrived was a picture of the board itself, with your 08:14 ink sitting inside it — which I already have. No new line came with it. The writing panel below still has that page loaded under your pen; add the next line to it and tap **Send**.

Now the step again, from a different direction. I said it in symbols last time and it did not take, so take a die instead.

Roll one fair die. Let $E=\{1,2,3,4\}$ and $F=\{3,4,5,6\}$.

| set | outcomes | probability |
|---|---|---|
| $E$ | $1,2,3,4$ | $4/6$ |
| $EF$ | $3,4$ | $2/6$ |
| $EF^c$ | $1,2$ | $2/6$ |

Look only at the $E$ row. Every outcome of $E$ falls into exactly one of two camps: the ones that are also in $F$, and the ones that are not. Nothing sits in both camps, and nothing in $E$ escapes both. So the four outcomes of $E$ split cleanly into two and two, and the probabilities add:

$$\tfrac{4}{6} \;=\; \tfrac{2}{6} + \tfrac{2}{6}.$$

That addition is not an arithmetic coincidence. It is axiom 3 — the same rule you already used on the three pieces of $E\cup F$ — applied to a set carved into two pieces instead of three.

And it is already drawn on your page. The circle $E$ is cut by the boundary of $F$ into exactly two regions: the lens $EF$ and the crescent $EF^c$. You labelled both of them. What you have never written down is what their two probabilities add up to.

> **Your move.** One line, for general $E$ and $F$, not for the die. Write what axiom 3 gives you for $P(E)$ when $E$ is split that way, then rearrange that line to get $P(EF^c)$ on its own.

Once you have it, the identical line for $F$ and the substitution into the three-term sum you already wrote is the whole rest of the proof.
