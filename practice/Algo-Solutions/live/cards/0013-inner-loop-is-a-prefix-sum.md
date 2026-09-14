---
kind: correct
title: The inner sum is a prefix sum, and that is the whole improvement
---

> *($O(n^2)$, unsure how to improve...)*

Taking the aside first, since it is the real question on the page.

Look at what your inner loop actually asks at index $i$: *over everything to my left, total the $I$'s of the entries whose value is smaller than mine.* Two constraints, and they are not the same kind of thing. **Position** is already free — you sweep left to right, so everything you have recorded is to the left by construction. **Value** is a range: every value strictly below $\texttt{nums}[i]$.

So strip position out and the inner loop is: keep a running total over a *range of values*, and after each entry change exactly one value's contribution. Range-sum with point-update is a solved problem, not a cleverness problem — a Fenwick tree answers each query in $O(\log n)$, which makes the whole count $O(n \log n)$.

And your four numbers are right. $I = 1, 1, 3, 2$, so $A(2) = 7$ — and the arrows you drew *are* the recurrence, stated without being asked for it: $I(i) = 1 + \sum I(j)$ over $j < i$ with $\texttt{nums}[j] < \texttt{nums}[i]$.

## Your move

Same list, position order kept:

$$\texttt{nums} = [\,6,\;2,\;8,\;4\,].$$

Take a table $S$ **indexed by value**, positions $1$ through $8$, every entry $0$ to start. Sweep the list left to right, and at an entry of value $v$:

1. $I = 1 + (S[1] + S[2] + \cdots + S[v-1])$ — the prefix of $S$ strictly below $v$.
2. Then set $S[v] \leftarrow I$.

**Write $S$ after each of the four entries — four tables of eight numbers — and the $I$ you got at each step.**

- $I(i)$: number of strictly increasing subsequences ending at index $i$; a single entry counts as one.
- $A(g)$: number of strictly increasing subsequences of `nums` with every element divisible by $g$.
- $E(m)$: those whose GCD is exactly $m$; $A(g) = \sum_{g \mid m} E(m)$.
- *prefix of $S$ below $v$*: the sum of $S[1..v-1]$, nothing above.
- *point update*: one cell of $S$ changes, the rest stand.
- $8$ is only the table size because $\max(\texttt{nums}) = 8$ here.

Your four $I$'s must come out $1, 1, 3, 2$ again. If they do not, the table is being read or written at the wrong index, and I want to see which step disagrees.
