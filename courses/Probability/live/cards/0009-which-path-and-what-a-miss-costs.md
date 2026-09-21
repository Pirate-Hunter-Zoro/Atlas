---
kind: question
title: which-path-and-what-a-miss-costs
---
The right column. Your induction on $k$ is the standard proof of this, and the base case is already right: $k=1$ gives $\frac{m-1}{m-1}=1$, and one trial does produce a run of $1$.

The left column is not garbage; it is a harder problem than the one you were set. Getting $P(N=j)$ exactly means counting the length-$(j-k-1)$ prefixes that contain no run of $k$ anywhere, and that count has no closed form. It satisfies a recursion of its own, which you would have to solve before you could do the sum. Your $1-\left(m^{k}\cdot(j-k-1-k)\right)$ stands in for it and is not a probability: it goes negative as $j$ grows. Drop that column.

What your inductive step is missing is one conditioning step, and there is exactly one thing in it that is easy to get wrong.

**Exercise (Homework 3, Problem 22).**
Independent trials, each equally likely to have any of $m$ possible outcomes, are performed until the same outcome occurs $k$ consecutive times. If $N$ is the number of trials, show that
$$
E[N] = \frac{m^{k}-1}{m-1}.
$$

*Definitions / symbols used*
- Each trial takes one of $m$ values, each with probability $1/m$, independent of every other trial.
- The **run** at trial $n$ is the number of trials ending at $n$ that all show the same outcome.
- $N_j$ = the first trial at which the run reaches $j$. So $N_1=1$ and $N=N_k$.
- **Law of total expectation**: $E[X]=\sum_i E[X\mid A_i]P(A_i)$ for events $A_i$ that partition the space.

**The one thing.** The run has just reached $n$, at trial $N_n$. One more trial is made and it does **not** match — probability $\frac{m-1}{m}$. Counting from that trial onward, how many further trials do you still expect to need before the run reaches $n+1$? Pick one and say why it is that one and not the others:

(a) $E[N_{n+1}]$
(b) $E[N_{n+1}]-1$
(c) $E[N_{n+1}]+1$
