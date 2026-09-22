<!-- chapter: New direction — For chapter 5, we are going to do problems 5.4, 5.6, 5.7,… -->
Nothing was taught. The whole session was one turn: the student changed direction, and that turn re-planned the workspace around it. They have answered nothing yet, so there is no misunderstanding to record and nothing that must not be re-taught.

The direction, in their words: Chapter 5, exercises 5.4, 5.6, 5.7, 5.8, 5.10. Nothing else in the chapter. 5.1, 5.2, 5.3, 5.5, 5.9, 5.11 and 5.12 are out of scope — do not teach or transcribe them.

What is on disk now:

- `PLAN.md` is rewritten around those five, in teaching order 5.7, 5.6, 5.8, 5.10, 5.4. The order is deliberate: 5.7 is Eisenstein applied straight; 5.6 is Eisenstein with the coefficients reversed; 5.8 needs 5.7 to supply an element of degree $n$ for every $n$; 5.4 is last because it goes through $K[y][x]$ and Gauss' lemma over an integral domain.
- `chapters/ch05-tests-for-irreducibility/homework/ch05-homework.tex` holds all five statements, transcribed from the reading, each with an empty marked solution region. `board hw build` said OK, 1 page, 0 warnings. The old placeholder labelled `05.1` is gone.
- The map is still underived. It was never drawn, so the change did not make it stale. Draw it only if they ask.
- The README opening is still accurate and was not touched.

The single next thing: card 0001 is live and unanswered. It states 5.7 in full and asks one pre-step — of $x^3-3$, $2x^3+3x+3$ and $x^3+3x^2+9x+9$, which one Eisenstein at $p=3$ fails for. The answer is the third, because $p^2=9$ divides the constant term $9$. Watch for them picking the right polynomial but naming the wrong condition; that is the confusion this question exists to catch. Pick up there rather than re-posing it.

Note on the student: they redirect the work by fiat, mid-chapter, without explanation. Take it and rewrite the files; do not ask why.
