---
kind: lesson
title: p40a-done-p40b-paths
---
**Done for (a): $\mathrm{Var}(X) = 113.75$, and your write-up now says so.** Your setup was right. One symbol was not: $(2+X)^2 = 4 + 4X + X^2$, not $4 + 2X + X^2$. The cross term is $2 \cdot 2 \cdot X$. Same for door 2: $(3+X)^2 = 9 + 6X + X^2$.

$$S = 0.5(4 + 4\mu + S) + 0.3(9 + 6\mu + S) \;\Rightarrow\; 0.2S = 4.7 + 3.8\mu = 40.8 \;\Rightarrow\; S = 204$$

$$\mathrm{Var}(X) = 204 - 9.5^2 = 113.75$$

I checked it a second way, as a random number of trips each lasting 2 or 3 days. It agrees.

**I can't plug numbers into (b), because the setup is wrong, not the algebra.** In (b) he remembers. He never takes a door twice. So "given door 1, $X$ looks like $2 + X$" is false. After door 1 he chooses only between doors 2 and 3. Your $\mu = 5$ comes from a prisoner who forgets.

**Problem 40(b).** Same cell and doors. Each time, he picks uniformly among the doors he has not yet used. Find $E[X]$, and then $\mathrm{Var}(X)$ for part (c).

- $X$ = days until freedom.
- Door 1: back in 2 days. Door 2: back in 3 days. Door 3: free at once.
- "Not yet used": first pick is from 3 doors, the second from 2, the third is forced.

He can only escape by one of five door orders:

| order | $X$ |
|---|---|
| 3 | 0 |
| 1, 3 | 2 |
| 2, 3 | 3 |
| 1, 2, 3 | 5 |
| 2, 1, 3 | 5 |

Give the probability of each of the five orders.
