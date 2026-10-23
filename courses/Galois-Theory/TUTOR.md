# Galois Theory

## Where things are

- The book is A Course in Galois Theory; chapters.tsv lists its chapters. Each is chapters/chNN-slug/ with notes/, homework/ and handwritten/; reading/ (the excerpt) and textbook/ stay out of git.
- latex/coursemacros.sty is the shared preamble.
- Worksheets live in homework/<sheet>/ with the typeset .tex and handwritten/ beside it.

## Now

Chapter 7 worksheet, problems 13-19, in session 20261009-193922. `chapters/ch07-splitting-fields/homework/ch07-homework.tex` now holds 13(a), 13(b), 13(d), 14(a)-(c), 15(b)-(d) and 16(a)-(c). The board counts 4 of 7 written up and the PDF builds (`board writeup status`). Pages for 14, 15 and 16 are filed in `homework/handwritten/`.

The solutions had been written into `projects/libr-local-llm/docs/galois-theory-ch07/writeup.tex`; they are now in the course set, and that file is stale -- do not transcribe from it again. Its 13(d) ended with a stale "still owed" note; the version in the homework is closed by the owner's $K^G=\QQ$ step (t0200).

Still open:

- 13(c): the $p=13$ subgroup list. The owner chose to answer it with the $p=7$ case on their early pages (cards 0011-0026); write it up as 13(c) from those pages, never re-pose $p=13$.
- 15(a): complex conjugation restricted to $K$. Set aside for 14, never answered; 15(b)-(d) are written up without it.
- 14(d): posed at card 0120, unanswered. The lattice, four nodes each, edges labelled.
- 17, 18, 19: not started.

Standing directions: no small cases, examples or subgroup lists once they are working a proof ("Focus on the proof", t0191); "move on" means move on, and a dropped problem stays dropped until they reopen it; never write the proof for them (t0192). A request to read files, transcribe or compile is done, not taught (t0219).

## Open decisions

## Done recently

- The automorphisms and splitting-fields worksheet, problems 7-12: Aut(ℚ(ζₙ)/ℚ) inside (ℤ/nℤ)ˣ, Φₚ irreducible, the whole machine on x⁴+1, the splitting field of x³−2, and the finite-field pair.
- The solutions stranded in libr's `writeup.tex` were moved into `ch07-homework.tex`: 13(d), 14(a)-(c), 15(b)-(d), 16(a)-(c). The PDF rebuilds clean and the board reads 4 of 7.
- The $p=13$, $d=2$ worked case of 13(d), the 14(c) order-two note and two 14 clauses carried from libr's writeup.tex into ch07-homework.tex, with the nine 13(d) pages as `handwritten/ch07-13d*.png`. libr's copy is deleted.
