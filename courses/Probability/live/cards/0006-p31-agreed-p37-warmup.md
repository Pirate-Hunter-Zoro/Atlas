---
kind: lesson
title: p31-agreed-p37-warmup
---
**Your question first.** The identity $\sum_{i\ge1} i\,q^{i-1}(1-q) = \frac{1}{1-q}$ is the mean of a geometric random variable, from Ross section 4.8.1. You do not have to prove it. Cite it as "the mean of a geometric with success probability $1-q$ is $\frac{1}{1-q}$."

Why it is that: $q^{i-1}(1-q)$ is the chance the first success comes on trial $i$ when each trial succeeds with probability $1-q$. So the sum is $\sum i\,P(N=i) = E[N]$, and a geometric's mean is one over its success probability.

**Problem 31 is correct and finished.** Both halves check out:

$$E[L_1] = \frac{1-p}{p} + \frac{p}{1-p}, \qquad E[L_2] = 1 + 1 = 2.$$

Your factoring was clean both times: one factor pulled out, and what was left was exactly the geometric sum. Your boxed first-run sum now carries the closing factor too. That is six of eight. I am typesetting it into hw03.tex now.

**Problem 37.** A manuscript goes to typist $A$, $B$ or $C$, each equally likely. The number of errors $X$ is Poisson with mean $2.6$ if $A$ types it, $3$ if $B$ does, and $3.4$ if $C$ does.
(a) Find $E[X]$.
(b) Find $\mathrm{Var}(X)$.

- $T$ = the typist who does the work, with $P(T=A)=P(T=B)=P(T=C)=\tfrac13$.
- Poisson($\lambda$): mean $\lambda$, variance $\lambda$.
- $\mathrm{Var}(Y) = E[Y^2] - (E[Y])^2$ for any random variable $Y$.
- Conditioning on $T$: $E[g(X)] = \sum_t E[g(X)\mid T=t]\,P(T=t)$.

One small thing before the full problem. Typist $A$ typed it, so $X$ is Poisson with mean $2.6$.

What is $E[X^2 \mid T = A]$?
