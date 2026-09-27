<!-- chapter: Ch 05 — Tests for irreducibility -->
Scope: Garling 05.4, 05.6, 05.7, 05.8, 05.10, stated in chapters/ch05-tests-for-irreducibility/homework/ch05-homework.tex. After ch05, the worksheet they uploaded replaces chapter 6.

Where they got to:
- 05.4, 05.6, 05.7, 05.8 are transcribed in their words, their handwriting is filed, and the build is clean (2 pages). Do not reopen any of them.
- 05.10 (x^5 - 4x + 2 and x^4 - 4x + 2 irreducible over Q(i)) is posed and not answered. The open check: for a root α of the quintic, why must 2 and 5 divide [Q(i,α):Q], and why is it at most 10?

What they got wrong:
- 05.8: they asserted Q(2^(1/n)) ⊂ A without saying why 2^(1/n) is real and algebraic, or that "smallest field" is what puts it inside A. Their professor accepted it as written, and so does the file. Know the habit; do not reopen it.

What they got right, do not re-teach:
- Eisenstein, and reading coefficients mod p, zero coefficients included.
- Gauss's lemma lands a factorisation in K[x][y]. Degrees in y then split 0 + 1.
- The tower law gives [A:Q] ≥ n for every n.

Next: finish 05.10. The quintic comes from degree divisibility: [Q(i,α):Q] = 10, so the degree over Q(i) is 5. The quartic needs one more idea. Take a real root (f(0) = 2 and f(1) = -1), so i ∉ Q(α), which gives degree 8 over Q and 4 over Q(i). Teach that last idea as its own step. After 05.10 is written up, move to the uploaded worksheet.

How they work:
- They answer by rewriting the whole proof, not the micro-question. Read the full page.
- When they say their professor accepted an argument and tell you to write it up, do it and move on.
- They skip sanity checks once a proof is done. Let them.
- Letters get swapped (g vs h). Check every symbol before transcribing.
- Old answer PNGs are pruned from the working tree. Recover them with git show <commit>^:courses/Galois-Theory/live/answers/tNNNN-rN.png.
