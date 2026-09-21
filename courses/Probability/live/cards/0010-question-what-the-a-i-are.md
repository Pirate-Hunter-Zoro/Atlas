---
kind: lesson
title: question what-the-A-i-are
---
The $A_i$ are not the first trial. They are the two things that can happen on the **one trial after the run reaches $n$**, and there are exactly two of them.

Conditioning on the first trial's value gets you nothing here. All $m$ outcomes are symmetric, so $E[N \mid \text{first trial is } 1]$ equals $E[N \mid \text{first trial is } 2]$ equals every other one. The sum $\sum_i E[N\mid A_i]P(A_i)$ collapses straight back to $E[N]$ and you have learned nothing.

The partition that does work is at trial $N_n + 1$, the trial immediately after the run first reaches length $n$:

- $A_1$: that trial **matches** the run. Probability $\frac{1}{m}$. The run is now $n+1$, so $N_{n+1} = N_n + 1$.
- $A_2$: that trial **misses**. Probability $\frac{m-1}{m}$. The run collapses.

Your base case and your induction statement are both right as written. This is the only missing piece.

**Exercise (Homework 3, Problem 22).**
Independent trials, each equally likely to have any of $m$ possible outcomes, are performed until the same outcome occurs $k$ consecutive times. If $N$ is the number of trials, show that
$$
E[N] = \frac{m^{k}-1}{m-1}.
$$

*Definitions / symbols used*
- Each trial takes one of $m$ values, each with probability $1/m$, independent of every other trial.
- The **run** at trial $n$ is the number of trials ending at $n$ that all show the same outcome.
- $N_j$ = the first trial at which the run reaches $j$. So $N_1 = 1$ and $N = N_k$.
- **Law of total expectation**: $E[X] = \sum_i E[X\mid A_i]P(A_i)$ over events $A_i$ that partition the space.

**The one thing.** Take case $A_2$: the run had reached $n$, the next trial missed. Counting from that missing trial onward, how many further trials do you expect to need before the run reaches $n+1$? Pick one and say why it is that one and not the other two:

(a) $E[N_{n+1}]$
(b) $E[N_{n+1}] - 1$
(c) $E[N_{n+1}] + 1$
