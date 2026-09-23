---
kind: question
title: records-61c-variance-of-the-sum
---
---
kind: question
title: records-61c-variance-of-the-sum
---
That is 61(b), finished. Line 2 now puts $\mathbb{E}$ outside the sum, so line 3 is a real application of linearity instead of a move past a constant. Line 4 reads a $1$-or-$0$ quantity against its two probabilities, $\frac{1}{i}$ and $\frac{i-1}{i}$, and gives $\frac{1}{i}$. Line 5 is the harmonic sum.

One correction, already made in `homework/hw02/hw02.tex`. Your symbol $\text{record}_i$ names an *event*, a set of outcomes, and an event cannot sit inside $\mathbb{E}[\cdot]$ -- only a number can. The file now defines $I_i$ to be $1$ when a record occurs at time $i$ and $0$ when it does not, and runs your five lines with $I_i$ in that slot. Nothing else of yours was changed.

Now 61(c), which is the same decomposition again with a harder second step.

**Problem 61(c).** $X_1, X_2, \ldots$ are independent, identically distributed, continuous. A record occurs at time $n$ if $X_n > \max(X_1,\ldots,X_{n-1})$. Let $N$ be the number of records by time $n$. Show that
$$\operatorname{Var}(N) = \sum_{i=1}^{n} \frac{i-1}{i^{2}}.$$

Everything this uses:

- $I_i$: equals $1$ if a record occurs at time $i$, else $0$. So $N = \sum_{i=1}^n I_i$.
- $P\{\text{record at time } i\} = 1/i$, proved in part (a).
- $\mathbb{E}[I_i] = 1/i$, proved in part (b).
- Variance: $\operatorname{Var}(Y) = \mathbb{E}[Y^2] - (\mathbb{E}[Y])^2$.
- Variance of a sum of *independent* random variables is the sum of their variances. The $I_i$ here are independent; take that as given for now.
- $I_i$ takes only the values $0$ and $1$.

Before the sum, one term. Fix a single $i$.

What is $\mathbb{E}[I_i^{2}]$, and hence what is $\operatorname{Var}(I_i)$?
