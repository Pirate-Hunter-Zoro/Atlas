---
kind: question
title: records-61d-tail-collapses
---
Your question first, because it is the right one: yes, $P\{N=i\}$ is hard, and the fix is to never compute it. Your formula is true --- $\mathbb{E}[N] = \sum_{i \ge 2} i \cdot P\{N=i\}$ holds. But $\{N=i\}$ demands no record at times $2, \ldots, i-1$ *and* a record at time $i$, and that "and" is exactly the thing you say you cannot guarantee. You are right that you cannot, cheaply.

The tail form has no "and" in it. $\{N > n\}$ says only: no record at any of times $2, \ldots, n$. Nothing is required to happen. And a block of $n-1$ "no record" statements collapses into one sentence about a single maximum --- if no $X_k$ with $k \le n$ ever beat everything before it, then nothing ever overtook $X_1$.

That is the whole problem, so here it is again in full.

**Let $N = \min\{n : n > 1 \text{ and a record occurs at time } n\}$ --- the first time after time $1$ that a record occurs. Show that $\mathbb{E}[N] = \infty$.**

Everything this uses:

- $X_1, X_2, \ldots$: independent, identically distributed, continuous, so ties have probability $0$ and all $n!$ orderings of the first $n$ are equally likely.
- A record occurs at time $n$ when $X_n > \max(X_1, \ldots, X_{n-1})$.
- Time $1$ is a record by convention, which is why $N$ starts looking at time $2$.
- Tail formula, for $N$ taking values in $\{1, 2, 3, \ldots\}$: $\mathbb{E}[N] = \sum_{n=0}^{\infty} P\{N > n\}$.
- $\{N > n\}$: no record occurred at any of the times $2, 3, \ldots, n$.
- Harmonic series: $\sum_{n \ge 1} 1/n = \infty$.

One thing, for general $n \ge 2$ and not for $n = 3$. The event $\{N > n\}$ says the largest of $X_1, \ldots, X_n$ sits in one particular position. Which position, and therefore what is $P\{N > n\}$?
