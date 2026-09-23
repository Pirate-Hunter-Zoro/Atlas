---
kind: question
title: records-61b-indicators
---
Right --- skip the induction, and do not write it up. Your counting line *is* the whole proof of (a): $n!$ equally likely orderings, $(n-1)!$ of them with $X_n$ in the last place, ratio $1/n$. Nothing is left for an inductive step to do, and there is no base case to check.

Two bookkeeping corrections. Ordered smallest to largest, the maximum sits **last**, so it is $(n-1)!$ orderings with $X_n$ last; you wrote "first". And the "Suppose ... Then $P\{X_{n+1} > \max(X_1,\ldots,X_n)\}$" frame has to go, because the ratio written under it counts $n$ variables, not $n+1$ --- it is the statement itself, not a step toward it. hw02.tex now carries (a) as the counting argument alone, with the by-parts $n=2$ page filed beside it as a check rather than as a base case.

**Problem 61(b), in full.** Let $X_1, X_2, \ldots$ be independent and identically distributed continuous random variables. A *record* occurs at time $n$ if $X_n > \max(X_1, \ldots, X_{n-1})$. Show that
$$\mathbb{E}[\text{number of records by time } n] = \sum_{i=1}^{n} \frac{1}{i}.$$
The text's hint: represent the number of records as a sum of indicator variables.

Everything this uses:

- Record at time $i$: the event $X_i > \max(X_1, \ldots, X_{i-1})$. Time $1$ counts, vacuously.
- Part (a), now proved: $P\{\text{record at time } i\} = 1/i$.
- Indicator variable: a random variable equal to $1$ when a given event happens and $0$ when it does not.
- Expectation of an indicator: $\mathbb{E}[I] = 1 \cdot P(\text{event}) + 0 \cdot P(\text{not}) = P(\text{event})$.
- Linearity of expectation: $\mathbb{E}\left[\sum_i Y_i\right] = \sum_i \mathbb{E}[Y_i]$, for any random variables, independent or not.

One thing only, not the whole of (b): write the number of records by time $n$ as a sum of indicator variables --- say what each indicator indicates and what its index runs over --- and give the expectation of a single one of them.
