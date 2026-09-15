---
kind: lesson
---
Yes, and with one word added: the FEWEST.

[L:k] is the smallest number of vectors in L you need so that every element of L is a sum of those vectors, each multiplied by one coefficient from k. Your example is right on both counts. {1, i} reaches every a+bi with a and b real, and no single vector does, so [ℂ:ℝ] = 2.

"Fewest" is doing real work there. {1, i, 1+i} also spans ℂ, but three spanning vectors do not make the degree 3 — 1+i is already reachable from the other two, so that set is redundant and is not a basis. Every basis of the same space has the same size, and that common size is the degree.

Now the one step I want, and the sentence you just wrote is the tool for it.

Row one of your table says [M:k] = 1. Why does that force M = k?

Take M as a vector space over k of dimension 1. By your own rule, one vector spans it. Say which element of L that single basis vector can be taken to be, then say which elements of L it reaches once you multiply it by coefficients from k.

what the question uses:
- k ⊆ M ⊆ L: M is an intermediate field — a subfield of L that contains k.
- [L:k]: the dimension of L as a vector space over k, which is the size of a basis.
- tower law: [L:k] = [L:M][M:k], for any intermediate M.
- basis: a spanning set with nothing redundant in it.
- spans: every element is a sum of basis vectors, each times one coefficient from k.
- dimension 1: a basis with exactly one element.
- M is a field, so 1 ∈ M, and 1 ∈ k as well.
