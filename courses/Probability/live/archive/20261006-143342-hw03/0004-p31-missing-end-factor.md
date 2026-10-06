---
kind: lesson
title: p31-missing-end-factor
---
Both of your structures are right, and both probabilities are missing the same factor: the element that *ends* the run.

A first run of $0$s has length exactly $i$ only if elements $1$ to $i$ are $0$ **and element $i+1$ is a $1$**. Your $(1-p)^i$ says only the first part. It counts sequences whose run is length $i$ *or longer*.

The quick way to see it is broken: take $p = 1/3$. Your formula gives
$$P(1) = \tfrac{2}{3} + \tfrac{1}{3} = 1,$$
so every longer length would have to have probability $0$. But $P(2) = \tfrac{4}{9} + \tfrac{1}{9} > 0$. Your probabilities add to more than $1$.

Your second-run line has the same hole. The first-run factor ($p$ or $1-p$) and the $i-1$ further elements are there. The element that closes the second run is not.

Your reading that the second run's symbol is forced opposite to the first is correct. Keep it.

**Problem 31.** Each element in a sequence of binary data is $1$ with probability $p$ or $0$ with probability $1-p$, independently. A *run* is a maximal stretch of consecutive equal values. In $1,1,0,1,1,1,0$ the runs have lengths $2$, $1$, $3$.
(a) Find the expected length of the first run.
(b) Find the expected length of the second run.

- $L_1$, $L_2$ = the lengths of the first and second runs.
- A run of length exactly $i$ needs $i$ equal elements and then one element of the other value.
- Elements are independent, so the probability of a pattern is the product of its elements' probabilities.

Put the closing element into both formulas: what are $P(L_1 = i)$ and $P(L_2 = i)$?
