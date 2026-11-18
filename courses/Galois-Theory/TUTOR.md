# Galois Theory

## Where things are

- The book is A Course in Galois Theory; chapters.tsv lists its chapters. Each is chapters/chNN-slug/ with notes/, homework/ and handwritten/; reading/ (the excerpt) and textbook/ stay out of git.
- latex/coursemacros.sty is the shared preamble.
- Worksheets live in homework/<sheet>/ with the typeset .tex and handwritten/ beside it.
- Write-ups live in the actual homework document: a chapter's homework/ set or a worksheet under homework/. Bind the sitting with `board writeup use <set>` before the first add. A docs/<session>/writeup.tex is never the destination.

## Now

Session 20261103-163801 works Part I of the uploaded sheet `GaloisTheoryAtWork.pdf`: Problems 20, 21, 22. The write-up is `chapters/ch07-splitting-fields/homework/ch07-homework.tex`, bound to ch07; 20, 21 and 22(a), (b), (c) are typed into label 22. Problem 22 is pinned; it is the seven-step proof of the fundamental theorem.

22(c) closed on t0019-r13: roots of $M=\prod_i m_{\nu_i}$ all lie in $K$, and $K=F(\nu_1,\dots,\nu_n)$ is the smallest field holding $F$ and them, so $K$ is the splitting field. Written up under label 22; page filed `handwritten/ch07-22.png`. Card 0071 posed 22(d).

Open rung: $f$ has coefficients in $F$, so in $L$; show $K$ is the splitting field of $f$ over $L$ (roots in $K$; roots plus $L$ generate $K$). The route after that: $K/L$ Galois gives $|\operatorname{Gal}(K/L)|=[K:L]$ by 20(e), and (c) with base $L$ gives $K^{\operatorname{Gal}(K/L)}=L$.

## Open decisions

The board's own fallback still makes `docs/<session>/writeup.tex` for an unbound sitting, so bind each sitting to its homework set before the first add. A board-code change to make the fallback create or prefer a homework set waits for a worktree and a pause in the sitting.

## Done recently

- 22(c) closed on t0019-r13 and written up under label 22: $K^G=F$ by the tower law, the orbit product in $F[x]$ from the $\sigma G=G$ reordering, that product the minimal polynomial $m_\alpha$, then $f=\prod_i m_{\nu_i}\in F[x]$ with all roots in $K$, and $K=F(\nu_1,\dots,\nu_n)$ the smallest field holding them, so $f$'s splitting field is $K$. Card 0071 posed 22(d).
- 21(c) closed on t0010-r29 and written up under label 21 at the owner's direction (card 0057): the correspondence $T\mapsto(T(e_1),\dots,T(e_d))$, additivity and F-scaling, the K-vector-space identification $F^{d^2}\cong K^d\cong\operatorname{Hom}_F(K,K)$ as their diagram states it, restriction to $K^\times$, Dedekind (b), and $|\operatorname{Gal}(K/F)|\le d$. The K-linearity check for $c\in K$ was not written; the owner called it trivial and moved on. Problem 22 posed and pinned.
- 21(b) Dedekind's lemma closed on t0010-r24 and written up under label 21: the owner chose $g$ with $\chi_1(g)\neq\chi_n(g)$, evaluated at $gx$, subtracted $\chi_1(g)$ times the relation at $x$, and boxed $c_n(\chi_n(g)-\chi_1(g))\neq0$; the survivor is a nontrivial relation among $\chi_2,\dots,\chi_n$ with fewer terms than the minimal one, a contradiction. Page filed `handwritten/ch07-21.png`. Card 0050 posed 21(c).
- 21(a) closed on t0010 and written up under label 21: the minimal-support argument from t0010-r20 (subtracting the multiple of $x$ strictly shrinks the support) and the rank-nullity existence clause.
- 20(e) closed on t0010-r17 and written up under label 20: $\phi$ the inclusion $F\to K$, $K=F(\alpha)$ with minimal polynomial $m$, $f=m$, part (d) gives $|\operatorname{Emb}_\phi(K,K)|=[K:F]$, part (c) identifies it with $\operatorname{Gal}(K/F)$.
- 20(d) typed into label 20 from t0010-r16 (filed `handwritten/ch07-20.png`): the induction, base case, reduction to $|\operatorname{Emb}_\phi(F(\alpha),L)|=[F(\alpha):F]$, and the fibre sum. The distinctness line is kept as written; separability is the missing reason.
- 20(c) closed on t0010-r11 and written up under label 20: $\phi$ the inclusion $F\to K$, part (b)'s bound gives $|\operatorname{Gal}(K/F)|\le[K:F]$.
- 19(d) closed and written up under label 19: $\sqrt3=\zeta_{12}^{-1}+\zeta_{12}$, matching $2\cos(\pi/6)$. Filed `handwritten/ch07-19.png`.
- 19(b), 19(c), 18(c) and 17(a) closed and written up under labels 19, 19, 18 and 17: the $\sqrt m$ product, the $\zeta_8$ targets, the double sum with $l=km$, and the $D_4$ presentation.
- 22(a) closed on t0019-r8 and written up under label 22 from t0019-r7 plus their $\sigma(a)$ reason; page filed `handwritten/ch07-22.png`. Card 0066 posed 22(b).
- 22(b) closed on t0019-r9 and written up under label 22 after (a): the chain $|H|\le|\operatorname{Gal}(K/K^H)|\le[K:K^H]\le|H|$ from the definition, 20(c) and (a), so all equal and $\operatorname{Gal}(K/K^H)=H$, $[K:K^H]=|H|$. Card 0067 posed 22(c).
