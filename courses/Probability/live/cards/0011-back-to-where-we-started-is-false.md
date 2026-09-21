---
kind: question
title: back-to-where-we-started-is-false
---
$E[X \mid \text{next misses}] \neq E[X]$. That one substitution is what collapsed your equation, and your algebra was honest about it.

$X$ counts trials from the very first one. When the trial after the run reaches $n$ misses, the $N_n + 1$ trials already performed do not get handed back. You are not at trial $0$. Those trials are on the clock forever, so the miss branch has to carry them.

It is also false about the *state*. The trial that missed showed something, so it is itself a run of $1$. You are not starting from nothing either.

The hit branch has the smaller version of the same defect: you wrote $\frac{m^n-1}{m-1} = E[N_n]$, but the hit itself took a trial, so that branch is $E[N_n] + 1$.

**Exercise (Homework 3, Problem 22).**
Independent trials, each equally likely to have any of $m$ possible outcomes, are performed until the same outcome occurs $k$ consecutive times. If $N$ is the number of trials, show that
$$
E[N] = \frac{m^{k}-1}{m-1}.
$$

*Definitions / symbols used*
- Each trial takes one of $m$ values, each with probability $1/m$, independent of every other trial.
- The **run** at trial $n$: the number of trials ending at $n$ that all show the same outcome.
- $N_j$ = the first trial at which the run reaches $j$. So $N_1 = 1$ and $N = N_k$.
- **Law of total expectation**: $E[X] = \sum_i E[X \mid A_i] P(A_i)$ over events $A_i$ partitioning the space.
- The partition: at trial $N_n + 1$, either it matches (probability $\frac{1}{m}$) or it misses (probability $\frac{m-1}{m}$).

**The one thing.** Fair coin, so $m = 2$, and $k = 2$ — two heads or two tails in a row. The formula says $E[N] = \frac{2^2-1}{2-1} = 3$, and that number is not in dispute.

Toss $1$ happens; the run is $1$. Now condition on toss $2$.

Give me the two numbers $E[N \mid \text{toss 2 matches}]$ and $E[N \mid \text{toss 2 misses}]$. Each is a plain integer. Your check is that they must average to $3$, because each branch has probability $\frac{1}{2}$.
