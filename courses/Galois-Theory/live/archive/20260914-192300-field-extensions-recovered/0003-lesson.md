---
kind: lesson
---
Yes — that is exactly what [L:k] counts, with one word added: the SMALLEST number of vectors in L you need to span L using coefficients from k. Your ℂ over ℝ example is the right one and 2 is the right number. Every complex number is a·1 + b·i with a and b real, so {1, i} spans ℂ, and no single element of ℂ spans it over ℝ.

That word "smallest" is doing real work, and it is the one thing I want you to say why about.

Take L = ℂ, k = ℝ, and the set {1, i, 1+i}. It has three elements and it does span ℂ over ℝ. So why is [ℂ:ℝ] still 2 rather than 3?

what the question uses:
- k ⊆ L: k is a subfield of L — same addition and multiplication, k is just the smaller one.
- L as a vector space over k: add inside L, scale by elements of k.
- spans: every element of L can be written as a sum of those vectors, each multiplied by one coefficient from k.
- basis: a spanning set with no redundancy in it.
- [L:k]: the dimension of L as a vector space over k — the size of a basis.

I have not touched your tower rows yet. That is the next card.
