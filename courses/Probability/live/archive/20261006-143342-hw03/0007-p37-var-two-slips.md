---
kind: lesson
title: p37-var-two-slips
---
**Part (a) is correct: $E[X] = 3$.** Part (b) has the right method and two slips, so $12.24$ is not the variance.

**Slip one: the last step never happened.** Your first line says $\mathrm{Var}(X) = E[X^2] - (E[X])^2$. The sum you then computed is $E[X^2]$ alone. The $-(E[X])^2 = -9$ from your own first line is missing from the boxed answer.

**Slip two: two means changed on the way down.** Your top-left list says $\lambda_A = 2.6$ and $\lambda_C = 3.4$. The bottom lines use $2.4$ and $3.6$ instead. Your $12.24$ is exactly what those wrong values give.

Everything else stands: conditioning on the typist, and $E[X^2 \mid T=t] = \lambda_t + \lambda_t^2$ from the Poisson variance.

**Problem 37.** A manuscript goes to typist $A$, $B$ or $C$, each equally likely. The number of errors $X$ is Poisson with mean $2.6$ if $A$ types it, $3$ if $B$ does, and $3.4$ if $C$ does.
(a) Find $E[X]$. Done: $3$.
(b) Find $\mathrm{Var}(X)$.

- $T$ = the typist who does the work, with $P(T=A)=P(T=B)=P(T=C)=\tfrac13$.
- $\lambda_A = 2.6$, $\lambda_B = 3$, $\lambda_C = 3.4$.
- Poisson($\lambda$): mean $\lambda$, variance $\lambda$, so $E[X^2 \mid T=t] = \lambda_t + \lambda_t^2$.
- $\mathrm{Var}(Y) = E[Y^2] - (E[Y])^2$ for any random variable $Y$.
- Conditioning on $T$: $E[g(X)] = \sum_t E[g(X)\mid T=t]\,P(T=t)$.

Redo the bottom of part (b) with $2.6$ and $3.4$, then subtract $(E[X])^2$.

What is $\mathrm{Var}(X)$?
