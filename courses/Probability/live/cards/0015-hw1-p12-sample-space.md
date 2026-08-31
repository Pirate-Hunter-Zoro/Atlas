---
kind: wrong
title: The set you wrote has no constraint in it
---

Two things. The second is the one that matters.

**The word.** *Sample* space, not event space. The sample space is the set of outcomes; the events are subsets of it. Ross is asking for the first.

**The set.** Write out what your condition actually rules out:

$$E \cup F \cup (E \cup F)^{c} = S,$$

the whole original sample space — every outcome of the original experiment lies in it, by the definition of a complement. So "each $o_i \in E \cup F \cup (E\cup F)^c$" is a condition satisfied by *every* infinite sequence of outcomes there is. It excludes nothing.

What you have described, then, is the sample space of **repeat the experiment forever**. Nothing in it knows the experiment ever stops, and stopping is the entire content of the word *until* in the problem.

Your own first line already knows better. You wrote

$$P(\text{$E$ before $F$ on trial } n) = P(E^cF^c)^{\,n-1}P(E),$$

and that is only a product of $n-1$ copies of one thing and one copy of another because you are demanding something specific of trials $1,\dots,n-1$ and something *different* of trial $n$. Those two demands are what your set is missing.

---

**Describe it again.** A single typical element, written out: say how long the sequence is, what is required of every trial before the last, and what is required of the last one.
