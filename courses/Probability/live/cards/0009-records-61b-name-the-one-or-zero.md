---
kind: question
title: records-61b-name-the-one-or-zero
---
Line 3 is the answer, and you wrote it. You put $1$ and $0$ on the page: $\frac{1}{i}\cdot 1 + \frac{i-1}{i}\cdot 0$. That is a value of $1$ when time $i$ is a record and $0$ when it is not, averaged against its two probabilities. You just averaged one line too early, and the thing being averaged never got a name.

Once it is averaged it is a constant, so the outer $\mathbb{E}$ on lines 2 through 4 is still wrapped around a number, and line 1 still has $\mathbb{E}[\cdot]$ inside the sum.

Take the same outcome: $n = 3$, with $X_1 = 0.4$, $X_2 = 0.9$, $X_3 = 0.7$. Records at times $1$ and $2$, not at time $3$, so $N = 2$.

Call the $1$-or-$0$ thing from your line 3 $I_i$. Do not average it. Write down its three values on this one outcome:

$$I_1 = \;?\qquad I_2 = \;?\qquad I_3 = \;?$$

and then their sum.

Everything this uses:

- Record at time $i$: the event $X_i > \max(X_1,\ldots,X_{i-1})$. Time $1$ is a record, vacuously.
- $N$: the number of records by time $n$. Random -- it changes with the outcome.
- $I_i$: the $1$-or-$0$ quantity in your line 3, read on a single outcome rather than averaged.
- Part (a), proved: $P\{\text{record at time } i\} = 1/i$.
- Linearity of expectation: $\mathbb{E}[\sum_i Y_i] = \sum_i \mathbb{E}[Y_i]$, for any random variables $Y_i$.
- Problem 61(b) asks: find the expected number of records by time $n$.
- $X_1,\ldots,X_n$ are i.i.d. and continuous, so ties have probability $0$.

So: for $X_1 = 0.4$, $X_2 = 0.9$, $X_3 = 0.7$, give me $I_1$, $I_2$, $I_3$ and $I_1 + I_2 + I_3$.
