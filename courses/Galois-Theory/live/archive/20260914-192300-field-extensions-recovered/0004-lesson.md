---
kind: lesson
---
Both rows are right, and so is the conclusion you drew from them.

[L:k] = 7 and 7 is prime, so [L:M][M:k] = 7 has only the two factorisations you wrote: 7 and 1, or 1 and 7. No other pair of positive whole numbers multiplies to 7.

One word in passing: k and L are fields here, not rings. Your reading of them — big one the vectors, small one the scalars — is exactly right.

Now the step that turns those two rows into "there is no intermediate field", and it is the only thing I want from you this time.

Row one says [M:k] = 1. Why does that force M = k?

Start from M as a vector space over k of dimension 1. Say what a basis of it looks like, then say which elements of L that basis can reach.

what the question uses:
- k ⊆ M ⊆ L: M is an intermediate field — a subfield of L that contains k.
- [L:k]: the dimension of L as a vector space over k.
- tower law: [L:k] = [L:M][M:k], for any intermediate M.
- dimension 1: a basis with exactly one element in it.
- basis: a spanning set with no redundancy.
- spans: every element can be written as basis vectors, each multiplied by one coefficient from k, added up.
- M is a field, so 1 ∈ M, and 1 ∈ k too.
