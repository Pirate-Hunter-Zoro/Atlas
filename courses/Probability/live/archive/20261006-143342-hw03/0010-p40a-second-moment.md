---
kind: lesson
title: p40a-second-moment
---
**Part (a)'s mean is right: $E[X] = 9.5$ days. Your variance for (a) is not.** The broken symbol is on the line $S = (2+\mu)^2(0.5) + \dots$. You wrote $E[X^2 \mid D=1] = (2+\mu)^2$. That squares the *mean* of $2+X$. You need the mean of the *square* of $2+X$, which is $E[(2+X)^2]$. Those differ by $\mathrm{Var}(X)$, the very thing you are solving for. So $S$ has to appear on both sides, just as $\mu$ did in the mean.

Part (b) has a separate problem. It comes next, once (a) is done.

**Problem 40(a), variance.** A prisoner's cell has three doors. Door 1 returns him to the cell after 2 days. Door 2 returns him after 3 days. Door 3 leads to freedom. He picks doors 1, 2, 3 with probabilities $0.5, 0.3, 0.2$ every time. Find $\mathrm{Var}(X)$.

- $X$ = days until freedom. $D$ = the first door he picks.
- $\mu = E[X] = 9.5$ (yours, agreed).
- $S = E[X^2]$, the unknown. $\mathrm{Var}(X) = S - \mu^2$.
- No memory: given $D=1$, $X$ has the same distribution as $2 + X$.
- Conditioning: $S = \sum_d E[X^2 \mid D=d]\,P(D=d)$.

Expand $E[X^2 \mid D=1] = E[(2+X)^2]$ in terms of $\mu$ and $S$.
