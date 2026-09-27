<!-- chapter: Ch 05 — Tests for irreducibility -->
Scope: Garling 05.4, 05.6, 05.7, 05.8, 05.10 in chapters/ch05-tests-for-irreducibility/homework/ch05-homework.tex. Chapter 6 is skipped; the worksheet they uploaded on 2026-09-22 replaces it.

Where they got to:
- Chapter 5 homework is complete, five of five: transcribed in their words, handwriting filed, build clean. Do not reopen any of it.
- 05.10 closed this session. Quintic: degree 10 over Q forces the top step over Q(i) to be 5. Quartic: total degree 4 would put i in Q(beta), which lies in R.

What they got wrong:
- 05.8: they asserted Q(2^(1/n)) is inside A without saying why 2^(1/n) is real and algebraic. Their professor accepted it, and so does the file.
- 05.10 quartic: they took beta as any root of x^4 - 4x + 2, then used "beta is real". Two of its roots are complex. They assumed an argument about one root works for every root. The file now picks a real root, from g(0) = 2 and g(1) = -1. One root suffices, since its minimal polynomial over Q(i) divides g and has degree 4.

What they got right, do not re-teach:
- Eisenstein, reading coefficients mod p, zero coefficients included.
- Gauss's lemma, and degree splitting in K[x][y].
- The tower law, both towers, and the divide-and-bound squeeze on degrees.
- A degree-1 step means the fields are equal.

Next: open the worksheet that replaces chapter 6. Read its exercises, pick three to five, and say which and why in the first card. Then pose the first one with one small check. The direction is theirs and settled.

How they work:
- They answer by rewriting the whole proof. Read the full page.
- They pick "a root" and later use a property only some roots have. Check which root is meant.
- When their professor accepted an argument, write it up and move on.
- They skip sanity checks once a proof is done. Let them.
- They swap letters (g vs h). Check every symbol before transcribing.
- Old answer PNGs are pruned. Recover them with git show <commit>^:courses/Galois-Theory/live/answers/tNNNN-rN.png.
