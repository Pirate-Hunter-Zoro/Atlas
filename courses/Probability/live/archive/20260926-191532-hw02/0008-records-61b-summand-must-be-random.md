---
kind: question
title: records-61b-summand-must-be-random
---
No, and the reason has moved down a line. The number is right, and lines 2 through 5 are now doing real work: you did pull $\mathbb{E}$ through the sum, which is the step that was missing. But look at what you are summing. You wrote the count as $\sum_{i=1}^{n} \mathbb{E}[\text{record}_i]$, and $\mathbb{E}[\text{record}_i]$ is a *number* -- it is $1/i$, a constant. So your first line says $\mathbb{E}[N] = \mathbb{E}[\text{a constant}]$, and the linearity step underneath it has nothing left to do.

The thing inside the sum has to be random. It has to depend on which outcome happened.

**The tiny thing.** Take $n = 3$ and this one outcome: $X_1 = 0.4$, $X_2 = 0.9$, $X_3 = 0.7$. Records at times $1$ and $2$; not at time $3$, since $0.7 < 0.9$. So $N = 2$ for this outcome.

Your summand gives $1, \tfrac{1}{2}, \tfrac{1}{3}$ here, totalling $\tfrac{11}{6}$. Not $2$. It cannot be, because those three numbers are the same whatever the $X$'s do.

Write the three numbers that *must* sit in the sum for this outcome so that it totals $2$. Then one line: what rule turns an outcome into those three numbers?

Everything this uses:

- Record at time $i$: the event $X_i > \max(X_1,\ldots,X_{i-1})$. Time $1$ is a record, vacuously.
- $N$: the number of records by time $n$. A random variable -- it changes with the outcome.
- Part (a), proved: $P\{\text{record at time } i\} = 1/i$.
- Indicator variable: a random variable equal to $1$ on outcomes where a stated event happens, $0$ on the rest.
- Linearity of expectation: $\mathbb{E}[\sum_i Y_i] = \sum_i \mathbb{E}[Y_i]$, for any random variables $Y_i$, independent or not.
- Problem 61(b) asks: find the expected number of records by time $n$.
- $X_1,\ldots,X_n$ are i.i.d. and continuous, so ties have probability $0$.

So: for $X_1 = 0.4$, $X_2 = 0.9$, $X_3 = 0.7$, the three numbers the sum needs -- and the rule that produced them.
