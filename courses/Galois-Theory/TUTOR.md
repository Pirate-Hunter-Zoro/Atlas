# Galois Theory

## Where things are

- The book is A Course in Galois Theory; chapters.tsv lists its chapters. Each is chapters/chNN-slug/ with notes/, homework/ and handwritten/; reading/ (the excerpt) and textbook/ stay out of git.
- latex/coursemacros.sty is the shared preamble.
- Worksheets live in homework/<sheet>/ with the typeset .tex and handwritten/ beside it.
- Write-ups live in the actual homework document: a chapter's homework/ set or a worksheet under homework/. Bind the sitting with `board writeup use <set>` before the first add. A docs/<session>/writeup.tex is never the destination.

## Now

Session 20261103-163801 works Part I of the uploaded sheet `GaloisTheoryAtWork.pdf`: Problems 20, 21, 22. Write-up lives in `chapters/ch07-splitting-fields/homework/ch07-homework.tex`, bound to ch07; 20(a)-(e), 21(a) and 21(b) are written up, and 21(c)'s F-linearity rung is done. On t0010-r28 the owner proved the map built from a tuple is $F$-linear ($T(a+b)=T(a)+T(b)$, $T(ca)=c\,T(a)$), the rung card 0054 asked. Card 0055 credits it and asks one question: show the correspondence $T\mapsto(T(e_1),\dots,T(e_d))$ is $K$-linear -- that $c\cdot T$ is again $F$-linear with tuple $c\,(T(e_1),\dots,T(e_d))$, and likewise for sums -- so $\operatorname{Hom}_F(K,K)$ is a $K$-vector space of dimension $d$. After that: apply (b) to the restrictions of $\operatorname{Gal}(K/F)$ to $K^\times$ for $|\operatorname{Gal}(K/F)|\le d$; then write up 21(c) and pose and do 22.

STRONG STEERING: one question per card, hold it (set on t0010-r26). Define a term before using it; the owner objects to vague wording (t0010-r27 "What rule?").

## Open decisions

The board's own fallback still makes `docs/<session>/writeup.tex` for an unbound sitting, so bind each sitting to its homework set before the first add. A board-code change to make the fallback create or prefer a homework set waits for a worktree and a pause in the sitting.

## Done recently

- 21(b) Dedekind's lemma closed on t0010-r24 and written up under label 21: the owner chose $g$ with $\chi_1(g)\neq\chi_n(g)$, evaluated at $gx$, subtracted $\chi_1(g)$ times the relation at $x$, and boxed $c_n(\chi_n(g)-\chi_1(g))\neq0$; the survivor is a nontrivial relation among $\chi_2,\dots,\chi_n$ with fewer terms than the minimal one, a contradiction. Page filed `handwritten/ch07-21.png`. Card 0050 posed 21(c).
- 21(a) closed on t0010 and written up under label 21: the minimal-support argument from t0010-r20 (subtracting the multiple of $x$ strictly shrinks the support) and the rank-nullity existence clause.
- 20(e) closed on t0010-r17 and written up under label 20: $\phi$ the inclusion $F\to K$, $K=F(\alpha)$ with minimal polynomial $m$, $f=m$, part (d) gives $|\operatorname{Emb}_\phi(K,K)|=[K:F]$, part (c) identifies it with $\operatorname{Gal}(K/F)$.
- 20(d) typed into label 20 from t0010-r16 (filed `handwritten/ch07-20.png`): the induction, base case, reduction to $|\operatorname{Emb}_\phi(F(\alpha),L)|=[F(\alpha):F]$, and the fibre sum. The distinctness line is kept as written; separability is the missing reason.
- 20(c) closed on t0010-r11 and written up under label 20: $\phi$ the inclusion $F\to K$, part (b)'s bound gives $|\operatorname{Gal}(K/F)|\le[K:F]$.
- 19(d) closed and written up under label 19: $\sqrt3=\zeta_{12}^{-1}+\zeta_{12}$, matching $2\cos(\pi/6)$. Filed `handwritten/ch07-19.png`.
- 19(b), 19(c), 18(c) and 17(a) closed and written up under labels 19, 19, 18 and 17: the $\sqrt m$ product, the $\zeta_8$ targets, the double sum with $l=km$, and the $D_4$ presentation.
