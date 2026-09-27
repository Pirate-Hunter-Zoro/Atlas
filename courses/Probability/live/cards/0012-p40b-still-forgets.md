---
kind: lesson
title: p40b-still-forgets
---
**(a) is finished and typeset. (b) is not fixed yet, so there is nothing to plug in.** Your (b) line, $\mu = \tfrac13(2+\mu) + \tfrac13(3+\mu)$, still says that after door 1 he is back where he started. He is not. He has used door 1 and will never take it again. So the $X$ after he returns is a different variable from the $X$ at the start. You cannot write $2 + \mu$ for it.

No recursion is needed. There are only five ways out, so $E[X]$ is a five-term sum. The arithmetic after that is mine.

**Problem 40(b).** Same cell and doors. Each time, he picks uniformly among the doors he has not yet used. Find $E[X]$, and then $\mathrm{Var}(X)$ for part (c).

- $X$ = days until freedom.
- Door 1: back in 2 days. Door 2: back in 3 days. Door 3: free at once.
- "Not yet used": first pick is uniform over 3 doors, the second over the 2 left, the third is forced.
- The probability of an order is the product of the probability of each pick in it.

| order | $X$ | probability |
|---|---|---|
| 3 | 0 | ? |
| 1, 3 | 2 | ? |
| 2, 3 | 3 | ? |
| 1, 2, 3 | 5 | ? |
| 2, 1, 3 | 5 | ? |

Fill in the five probabilities in the last column.
