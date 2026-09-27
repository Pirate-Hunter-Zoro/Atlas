---
kind: question
title: records-61d-probability-n-exceeds-3
---
Agreed, and your margin note is the reason line 2 is legal. The record indicators really are independent, so $\operatorname{Var}(\sum_i I_i) = \sum_i \operatorname{Var}(I_i)$, and 61(c) is finished.

Your objection an hour ago was the wrong instinct. The count you skipped settles it: across the six orderings, $I_2 = 1$ in three of them, $I_3 = 1$ in two, and both in exactly one. So $P\{I_2=1\} = 1/2$, $P\{I_3=1\} = 1/3$, and $P\{I_2=1,\, I_3=1\} = 1/6 = \tfrac{1}{2}\cdot\tfrac{1}{3}$.

What your margin note says in general: the ranking among $X_1, \ldots, X_{k-1}$ and the position of $X_k$ among all $k$ are separate parts of the ordering, and every ordering is equally likely, so knowing which records broke before time $k$ leaves $X_k$ equally likely to land in any of the $k$ slots. The write-up now carries that argument where it said "not yet justified".

So, 61(d), the last part.

**Let $N = \min\{n : n > 1 \text{ and a record occurs at time } n\}$ --- the first time after time $1$ that a record occurs. Show that $\mathbb{E}[N] = \infty$.**

Everything this uses:

- $X_1, X_2, \ldots$: independent, identically distributed, continuous, so ties have probability $0$ and all $n!$ orderings of the first $n$ are equally likely.
- A record occurs at time $n$ when $X_n > \max(X_1, \ldots, X_{n-1})$.
- Time $1$ is a record by convention, which is why $N$ starts looking at time $2$.
- For a random variable taking values in $\{1, 2, 3, \ldots\}$, $\mathbb{E}[N] = \sum_{n=0}^{\infty} P\{N > n\}$.
- The six orderings, ranks of $(X_1, X_2, X_3)$ with $3$ largest, each of probability $1/6$:
$$(1,2,3),\quad (1,3,2),\quad (2,1,3),\quad (2,3,1),\quad (3,1,2),\quad (3,2,1).$$

One thing before the whole proof. The event $\{N > 3\}$ says no record occurred at time $2$ and none at time $3$. Mark which of those six rows that is, and give me $P\{N > 3\}$.
