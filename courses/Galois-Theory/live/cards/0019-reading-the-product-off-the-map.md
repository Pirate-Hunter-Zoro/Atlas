---
kind: note
title: Read the product off the map, never off the factors
---
Fair question. Here is the whole thing, one point at a time, right factor first:

| $x$ | $(1\,3\,2)$ sends it to | then $(1\,2)$ sends it to | net |
|---|---|---|---|
| $1$ | $3$ | $3$ | $1 \mapsto 3$ |
| $2$ | $1$ | $2$ | $2 \mapsto 2$ |
| $3$ | $2$ | $1$ | $3 \mapsto 1$ |

The product is the map in the last column: it swaps $1$ and $3$ and fixes $2$. A map that swaps two things and fixes the third is $(1\,3)$. Nothing else it could be.

The part that "makes no sense" is, I think, the expectation that a $2$-cycle times a $3$-cycle should come out looking like the factors. There is no such rule. The factors are not letters being concatenated — they are two functions, and they share the symbols $1$ and $2$, so they interfere. The only way to name the composite is to compute where each point goes and then read the cycle off *that*.

You already have a free check on this one. A $3$-cycle on $\{1,2,3\}$ moves all three points — it fixes nothing. The composite above fixes $2$. So it could not have been a $3$-cycle whatever the arithmetic said, and that is the flag your margin was reaching for.

**Your move:** same table, three rows, for $(1\,2)(1\,2\,3)$. Right factor first, track $1$, $2$, $3$, then read the cycle off the last column.
