# Galois Theory

## Where things are

- The book is A Course in Galois Theory; chapters.tsv lists its chapters. Each is chapters/chNN-slug/ with notes/, homework/ and handwritten/; reading/ (the excerpt) and textbook/ stay out of git.
- latex/coursemacros.sty is the shared preamble.
- Worksheets live in homework/<sheet>/ with the typeset .tex and handwritten/ beside it.
- Write-ups live in the actual homework document: a chapter's homework/ set or a worksheet under homework/. Bind the sitting with `board writeup use <set>` before the first add. A docs/<session>/writeup.tex is never the destination.

## Now

Session 20261103-163801 works Part I of the owner's uploaded sheet `GaloisTheoryAtWork.pdf`: Problems 20, 21, 22.

The write-up lives in `chapters/ch07-splitting-fields/homework/ch07-homework.tex`, bound to ch07. Problems 20(a)-(e) are written up and the Problem 21 statement sits under an empty region; the PDF rebuilt clean at 2026-11-12 10:57. `board writeup status` reports 8 of 9, next 21.

20(e) closed on t0010-r17: take φ the inclusion F→K, write K=F(α) with minimal polynomial m, set f=m; part (d) gives |Emb_φ(K,K)|=[K:F], part (c) turns that into |Gal(K/F)|=[K:F]. The page's opening line supplies the missing distinctness reason — |Emb| counts the roots of φ(m), so it reaches deg m exactly when there are deg m distinct roots — which is what separability gives. The (d) region still carries the owner's original line and is left as typed.

Now: 21(a), just posed. Rung asked: fix j∈S and take a solution y supported inside S; why must y−(y_j/x_j)x be zero? The move: it is a solution supported in S and zero at j, so if nonzero its support is a proper subset of S, against minimality; hence zero and y=(y_j/x_j)x.

Next: 21(b) Dedekind's lemma, then 21(c). Then 22. Parts II-IV wait; the ch07 sheet (Problems 13-19) stays closed.

Steering: t0006 demanded the surjectivity candidate outright, so give definitions outright and never ask them to name a map. Their 2026-11-07 turn demands every write-up go in the actual homework document as we go, never a `docs/` write-up; card 0024 records it. The 2026-11-12 turn says "type up ... and let's move on": do not re-litigate the distinctness line; it is flagged once and left. Mode stays teach.

## Open decisions

The board's own fallback still makes `docs/<session>/writeup.tex` for an unbound sitting, so bind each sitting to its homework set before the first add. A board-code change to make the fallback create or prefer a homework set waits for a worktree and a pause in the sitting.

## Done recently

- 20(e) closed on t0010-r17 and written up under label 20: φ the inclusion F→K, K=F(α) with minimal polynomial m, f=m, part (d) gives |Emb_φ(K,K)|=[K:F], part (c) identifies it with Gal(K/F). The same page's opening line names the distinctness reason. Problem 21 posed under an empty region.
- 20(d) typed into label 20 on 2026-11-12 from t0010-r16 (filed `handwritten/ch07-20.png`): the induction, base case, reduction to |Emb_φ(F(α),L)|=[F(α):F], and the fibre sum. The distinctness line is kept as written; separability is the missing reason.
- 20(c) closed on t0010-r11 and written up under label 20: φ the inclusion F→K, Emb_φ(K,K)=Gal(K/F), part (b)'s bound gives |Gal(K/F)|≤[K:F].
- 19(d) closed and written up under label 19: √3=ζ₁₂⁻¹+ζ₁₂, i.e. x¹¹+x at ζ₁₂, matching 2cos(π/6). Filed `handwritten/ch07-19.png`.
- 19(c), 19(b), 18(c) and 17(a) closed and written up under labels 19, 19, 18 and 17: the √m product, the ζ₈ targets, the double sum with l=km, and the D₄ presentation.
- The automorphisms and splitting-fields worksheet (7-12), and the solutions moved from the retired project's writeup.tex (13(d), 14(a)-(c), 15(b)-(d), 16(a)-(c)), are in ch07-homework.tex.
