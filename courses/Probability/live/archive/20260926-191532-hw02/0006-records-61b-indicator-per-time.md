---
kind: question
title: records-61b-indicator-per-time
---
Right track in the sense that your formula is true, and the wrong road in the sense that it is the expensive one. Let $N$ be the number of records by time $n$. Then $\mathbb{E}[N] = \sum_i i \cdot P\{N = i\}$ is just the definition of expectation for a count, so nothing there is wrong. Your own instinct is also right: $P\{N=i\}$ is genuinely hard. The probability of exactly $i$ records in $n$ trials is a Stirling-number count, and you would be computing the entire distribution of $N$ to extract one number from it.

One small fix inside your line: the sum starts at $i=1$, not $i=0$. Time $1$ is always a record, so $N \geq 1$ always and $P\{N=0\} = 0$.

The hint points somewhere else. Instead of breaking the *expectation* into the values $N$ can take, break the *random variable* $N$ itself into one piece per time step. Each piece is $0$ or $1$.

**The tiny thing, on actual numbers.** Suppose the first five values come out
$$X_1 = 3,\quad X_2 = 7,\quad X_3 = 2,\quad X_4 = 9,\quad X_5 = 5.$$
Write down five numbers, one for each time $i = 1,\ldots,5$, each of them $1$ if a record occurred at time $i$ and $0$ if not. Then add the five numbers up, and say what the total is and what it counts.

Everything this uses:

- Record at time $i$: the event $X_i > \max(X_1,\ldots,X_{i-1})$. Time $1$ counts, vacuously.
- $N$: the number of records by time $n$.
- Part (a), proved: $P\{\text{record at time } i\} = 1/i$.

For those five values: give the five $0$/$1$ numbers, their sum, and what the sum counts.
