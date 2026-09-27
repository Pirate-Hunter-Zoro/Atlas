---
kind: question
title: records-61c-pay-for-line-two
---
Correct. $\operatorname{Var}(N) = \sum_{i=1}^{n} \left(\frac{1}{i} - \frac{1}{i^2}\right) = \sum_{i=1}^{n} \frac{i-1}{i^2}$, and every line of the arithmetic is right. $\mathbb{E}[I_i^2] = 1/i$ because squaring a $0/1$ variable changes nothing. Subtracting $(1/i)^2$ gives the term. That is 61(c), and I have transcribed it into the write-up.

One step in it is not paid for yet, and it is the one you objected to an hour ago.

Line 2 is $\operatorname{Var}\left(\sum_i I_i\right) = \sum_i \operatorname{Var}(I_i)$. That move is not linearity. Variance does not pass through a sum for free -- in general $\operatorname{Var}(X+Y) = \operatorname{Var}(X) + \operatorname{Var}(Y) + 2\operatorname{Cov}(X,Y)$, and the move you made is only valid when those covariances vanish. You wrote "they're not independent" and then used independence. One of those has to go.

So settle it by counting, for $n=3$.

Everything this uses:

- $X_1, \ldots, X_n$: independent, identically distributed, continuous -- so ties have probability $0$ and all $n!$ rank-orderings are equally likely.
- A record occurs at time $i$ when $X_i > \max(X_1, \ldots, X_{i-1})$.
- $I_i$: equals $1$ if a record occurs at time $i$, else $0$.
- $I_2 = 1$ exactly when $X_2 > X_1$.
- $I_3 = 1$ exactly when $X_3$ is the largest of the three.
- $X$ and $Y$ are independent when $P\{X=a,\, Y=b\} = P\{X=a\}P\{Y=b\}$ for every $a,b$.
- The six orderings, written as the ranks of $(X_1, X_2, X_3)$ with $3$ meaning largest, each of probability $1/6$:
$$(1,2,3),\quad (1,3,2),\quad (2,1,3),\quad (2,3,1),\quad (3,1,2),\quad (3,2,1).$$

Mark $I_2$ and $I_3$ against each of those six rows, then give me three numbers: $P\{I_2=1\}$, $P\{I_3=1\}$, and $P\{I_2=1,\, I_3=1\}$.
