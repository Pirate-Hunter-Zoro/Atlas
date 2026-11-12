# Galois Theory

## Where things are

- The book is A Course in Galois Theory; chapters.tsv lists its chapters. Each is chapters/chNN-slug/ with notes/, homework/ and handwritten/; reading/ (the excerpt) and textbook/ stay out of git.
- latex/coursemacros.sty is the shared preamble.
- Worksheets live in homework/<sheet>/ with the typeset .tex and handwritten/ beside it.
- Write-ups live in the actual homework document: a chapter's homework/ set or a worksheet under homework/. Bind the sitting with `board writeup use <set>` before the first add. A docs/<session>/writeup.tex is never the destination.

## Now

Session 20261103-163801 works Part I of the uploaded sheet `GaloisTheoryAtWork.pdf`: Problems 20, 21, 22. The write-up is `chapters/ch07-splitting-fields/homework/ch07-homework.tex`, bound to ch07; 20(a)-(e) and 21(a)-(c) are written up. Problem 22 is posed and pinned, its solution region empty; it is the seven-step proof of the fundamental theorem.

21(c) closed on t0010-r29 at the owner's direction. They wrote the full route and, on being told the one missing step (the K-linearity of $T\mapsto(T(e_1),\dots,T(e_d))$, i.e. that $(c\cdot T)$ is F-linear with tuple $c\,(T(e_i))$ for $c\in K$), said it was trivial and to write up what we have and move on. Card 0057 wrote it up faithfully to the page: the identification $F^{d^2}\cong K^d\cong\operatorname{Hom}_F(K,K)$ is recorded exactly as their diagram states it, not proved. The K-linearity proof is dropped; do not reopen it.

Next: teach Problem 22. Step (a) (Artin's lemma) is posed; its first rung asks them to count the n-equation system in n+1 unknowns and see from 21(a) that it has a nonzero solution. Close (a) before (b). One question per card; define a term before using it.

## Open decisions

The board's own fallback still makes `docs/<session>/writeup.tex` for an unbound sitting, so bind each sitting to its homework set before the first add. A board-code change to make the fallback create or prefer a homework set waits for a worktree and a pause in the sitting.

## Done recently

- 21(c) closed on t0010-r29 and written up under label 21 at the owner's direction (card 0057): the correspondence $T\mapsto(T(e_1),\dots,T(e_d))$, additivity and F-scaling, the K-vector-space identification $F^{d^2}\cong K^d\cong\operatorname{Hom}_F(K,K)$ as their diagram states it, restriction to $K^\times$, Dedekind (b), and $|\operatorname{Gal}(K/F)|\le d$. The K-linearity check for $c\in K$ was not written; the owner called it trivial and moved on. Problem 22 posed and pinned.
- 21(b) Dedekind's lemma closed on t0010-r24 and written up under label 21: the owner chose $g$ with $\chi_1(g)\neq\chi_n(g)$, evaluated at $gx$, subtracted $\chi_1(g)$ times the relation at $x$, and boxed $c_n(\chi_n(g)-\chi_1(g))\neq0$; the survivor is a nontrivial relation among $\chi_2,\dots,\chi_n$ with fewer terms than the minimal one, a contradiction. Page filed `handwritten/ch07-21.png`. Card 0050 posed 21(c).
- 21(a) closed on t0010 and written up under label 21: the minimal-support argument from t0010-r20 (subtracting the multiple of $x$ strictly shrinks the support) and the rank-nullity existence clause.
- 20(e) closed on t0010-r17 and written up under label 20: $\phi$ the inclusion $F\to K$, $K=F(\alpha)$ with minimal polynomial $m$, $f=m$, part (d) gives $|\operatorname{Emb}_\phi(K,K)|=[K:F]$, part (c) identifies it with $\operatorname{Gal}(K/F)$.
- 20(d) typed into label 20 from t0010-r16 (filed `handwritten/ch07-20.png`): the induction, base case, reduction to $|\operatorname{Emb}_\phi(F(\alpha),L)|=[F(\alpha):F]$, and the fibre sum. The distinctness line is kept as written; separability is the missing reason.
- 20(c) closed on t0010-r11 and written up under label 20: $\phi$ the inclusion $F\to K$, part (b)'s bound gives $|\operatorname{Gal}(K/F)|\le[K:F]$.
- 19(d) closed and written up under label 19: $\sqrt3=\zeta_{12}^{-1}+\zeta_{12}$, matching $2\cos(\pi/6)$. Filed `handwritten/ch07-19.png`.
- 19(b), 19(c), 18(c) and 17(a) closed and written up under labels 19, 19, 18 and 17: the $\sqrt m$ product, the $\zeta_8$ targets, the double sum with $l=km$, and the $D_4$ presentation.
