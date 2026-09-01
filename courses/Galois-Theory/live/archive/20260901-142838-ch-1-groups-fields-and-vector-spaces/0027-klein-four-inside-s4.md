---
kind: lesson
title: Then forget those names — you already own the pieces
---
Fair. Card 0026 named two things you have not met, which was my error, not a gap in you. Ignore $A_4$ and $V_4$ entirely. Everything the counterexample needs is something you were fluent in an hour ago: **cycle notation, and the fact that conjugation preserves cycle type.**

Work inside $G = S_4$, the permutations of $\{1,2,3,4\}$.

Look at the elements of $S_4$ whose cycle type is *two disjoint transpositions*. There are exactly three of them:

$$(1\,2)(3\,4), \qquad (1\,3)(2\,4), \qquad (1\,4)(2\,3).$$

Every pair $\{a,b\}$ splits the four points once, and picking $\{1,2\}$, $\{1,3\}$ or $\{1,4\}$ as the part containing $1$ exhausts the possibilities. Now throw in the identity and call the whole four-element set

$$H = \{\, e,\ (1\,2)(3\,4),\ (1\,3)(2\,4),\ (1\,4)(2\,3) \,\}.$$

Two facts about $H$, and you already have the argument for the second one:

- $H$ is a **subgroup**: each of those elements is its own inverse, and the product of any two of them is the third. That is the check below.
- $H \triangleleft S_4$: conjugating by any $g \in S_4$ sends an element of cycle type $2+2$ to an element of cycle type $2+2$, and $H$ contains *all* of those, plus $e$. So $gHg^{-1} \subseteq H$ for every $g$ — nothing can escape a set that is closed under cycle type.

That is your $H$. The $K$ inside it, and the witness, are still yours to find.

**Your move — one product, before we go on.** With the right factor acting first, compute

$$(1\,2)(3\,4) \cdot (1\,3)(2\,4)$$

and say which element of $H$ it is.
