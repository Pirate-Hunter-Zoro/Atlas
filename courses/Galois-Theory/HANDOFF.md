<!-- chapter: Ch 05 — Tests for irreducibility -->
Scope: Garling 05.4, 05.6, 05.7, 05.8, 05.10, stated in chapters/ch05-tests-for-irreducibility/homework/ch05-homework.tex. After ch05, the worksheet they uploaded replaces chapter 6.

Where they got to:
- 05.4, 05.6, 05.7, 05.8 are transcribed in their words, their handwriting is filed, and the build is clean. Do not reopen any of them.
- 05.10 (x^5 - 4x + 2 and x^4 - 4x + 2 irreducible over Q(i)) is open. They set up the quintic: [Q(α):Q] = 5 by Eisenstein at 2, and both towers, so 10 divides [Q(i,α):Q].
- The last session re-posed the open check (why is [Q(i,α):Q(i)] ≤ 5?). They left before answering.

What they got wrong:
- 05.8: they asserted Q(2^(1/n)) ⊂ A without saying why 2^(1/n) is real and algebraic. Their professor accepted it, and so does the file.
- 05.10: they had the divisibility but could not find the upper bound.

What they got right, do not re-teach:
- Eisenstein, and reading coefficients mod p, zero coefficients included.
- Gauss's lemma, and degree splitting in K[x][y].
- The tower law, and both towers for the quintic.

Next: re-pose the top-step bound, restated in full. The answer is that the minimal polynomial of α over Q(i) divides x^5 - 4x + 2, which lies in Q(i)[x]. So the total degree is 10, the degree over Q(i) is 5, and the quintic is irreducible. Then the quartic, with its extra idea as its own step. Take a real root (f(0) = 2, f(1) = -1), so i ∉ Q(α). That gives degree 8 over Q and 4 over Q(i). Write up 05.10 (board hw use ch05) once both halves are agreed, then move to the worksheet.

How they work:
- They answer by rewriting the whole proof. Read the full page.
- When they say their professor accepted an argument, write it up and move on.
- They skip sanity checks once a proof is done. Let them.
- They swap letters (g vs h). Check every symbol before transcribing.
- Old answer PNGs are pruned. Recover them with git show <commit>^:courses/Galois-Theory/live/answers/tNNNN-rN.png.
