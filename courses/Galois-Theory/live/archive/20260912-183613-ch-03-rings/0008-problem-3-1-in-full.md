---
kind: question
title: Problem 3.1, in full
---

Headings fixed. The distributivity line is complete and correct, and that was the whole point of asking for one axiom: each axiom of $R^S$ is its counterpart in $R$, evaluated at a fixed arbitrary $s$. The rest go the same way, so 3.1 goes back to you whole.

**Problem 3.1.** *Suppose that $S$ is a set and $R$ is a ring. Let $R^S$ denote the set of all mappings from $S$ to $R$. Show that $R^S$ is a ring, under the operations defined by*

$$(f+g)(s) = f(s) + g(s), \qquad (fg)(s) = f(s)g(s).$$

*Show that if $S$ has more than one element then there exist non-zero elements $f$ and $g$ in $R^S$ for which $fg = 0$.*

Everything the statement leans on:

- *Ring:* abelian group under $+$; multiplication associative and commutative with an identity $1 \neq 0$; multiplication distributes over $+$.
- *$R^S$:* its elements are **functions** $S \to R$. Two are equal iff they agree at every $s \in S$.
- *Zero and identity of $R^S$:* the constant functions $s \mapsto 0_R$ and $s \mapsto 1_R$. You have both.
- *Non-zero in $R^S$:* **not equal to the zero element of $R^S$** — so it takes a non-zero value at *some* $s$, not at every $s$.
- *$fg = 0$ in $R^S$:* the function $fg$ *is* the zero function, i.e. $(fg)(s) = 0_R$ for **every** $s \in S$.

**Your move.** Write 3.1 out as a finished answer. Keep what you have — the distributive axiom and the pair $f, g$ — and do not redo them.

Three things are not on your page yet: the remaining ring axioms, by the same pointwise argument; the reason each of $f$ and $g$ is non-zero; and the check that $(fg)(s) = 0_R$ at *every* $s$, not only at $s_1$ and $s_2$.
