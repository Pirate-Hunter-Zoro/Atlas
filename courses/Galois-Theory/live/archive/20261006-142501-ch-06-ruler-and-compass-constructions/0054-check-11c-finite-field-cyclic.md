---
kind: lesson
title: check 11c-finite-field-cyclic
---
Accepted: 11(b) is done, and $G$ is cyclic. One line was missing, and the write-up carries it.

"Each $N(d)$ corresponds with $\varphi(d)$" is the step that needs a reason. The reason is your first half. Subtract the two sums:
$$\sum_{d \mid n} \bigl(\varphi(d) - N(d)\bigr) = n - n = 0.$$
Every term is $\geq 0$, because $N(d) \leq \varphi(d)$. Nonnegative terms that sum to $0$ are all $0$. So $N(d) = \varphi(d)$ for every $d \mid n$, and in particular $N(n) = \varphi(n) \geq 1$. Your last line says $N(d) \geq 1$; it is $N(n)$ you need.

**Problem 11(c).** Deduce that $\mathbb{F}_q^\times$ is cyclic for every finite field $\mathbb{F}_q$.

What it uses:

- $\mathbb{F}_q$: a field with exactly $q$ elements.
- $\mathbb{F}_q^\times$: the nonzero elements of $\mathbb{F}_q$ under multiplication.
- 11(b), yours: if $K$ is a field and $G \subseteq K^\times$ is a finite subgroup, then $G$ is cyclic.
- Cyclic: $G = \langle g \rangle$ for some $g \in G$.

Choose $K$ and $G$ so that 11(b) applies, check each of its hypotheses, and conclude that $\mathbb{F}_q^\times$ is cyclic for every finite field $\mathbb{F}_q$.
