---
kind: question
title: one-toss-counted-twice
---
Yes — one simple mistake, and it is exactly one toss. Everything else on the page is right.

Your base case is right. Your partition is right. Your hit branch is now right: $\frac{m^n-1}{m-1}+1$, the trials to reach a run of $n$ plus the trial that finished it. And your algebra from the recursion down to the last line is clean — I followed it, and $\mu = \frac{m^{n+1}+m^2-2m}{m-1}$ is what your equation really says.

The miss branch is where the extra toss is. You wrote it as $\frac{m^n-1}{m-1}+1+\mu$. The $+1$ is the trial that missed. Then $\mu$ counts from toss $1$ — and *its* first toss is the one that establishes a run of $1$. The missing trial already did that. So you pay for it twice, and the branch should be

$$\frac{m^n-1}{m-1} + 1 + (\mu - 1).$$

Check the size of the damage: your answer exceeds the target by $\frac{m^2-2m+1}{m-1} = m-1$, which is exactly one extra toss charged at probability $\frac{m-1}{m}$, then scaled by $m$ when you solved. One toss.

**Exercise (Homework 3, Problem 22).**
Independent trials, each equally likely to have any of $m$ possible outcomes, are performed until the same outcome occurs $k$ consecutive times. If $N$ is the number of trials, show that
$$E[N] = \frac{m^{k}-1}{m-1}.$$

*Definitions / symbols used*
- Each trial takes one of $m$ values, each with probability $1/m$, independent of every other trial.
- The **run** at trial $n$: the number of trials ending at $n$ that all show the same outcome.
- $N_j$ = the first trial at which the run reaches $j$. So $N_1 = 1$ and $N = N_k$.
- $\mu = E[N_{n+1}]$, the quantity your induction step is solving for.
- **Law of total expectation**: $E[X] = \sum_i E[X \mid A_i]P(A_i)$ over events $A_i$ partitioning the space.
- Your partition: the trial after $N_n$ either matches (probability $\frac{1}{m}$) or misses (probability $\frac{m-1}{m}$).

**The one thing.** Fair coin, $m=2$, $k=2$, so $n=1$ and $\mu = 3$. Give me two integers: your miss branch $\frac{m^n-1}{m-1}+1+\mu$ evaluated here, and the true expected number of tosses given that toss $2$ misses. Then name which toss got charged twice.
