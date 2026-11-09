# Galois Theory

## Where things are

- The book is A Course in Galois Theory; chapters.tsv lists its chapters. Each is chapters/chNN-slug/ with notes/, homework/ and handwritten/; reading/ (the excerpt) and textbook/ stay out of git.
- latex/coursemacros.sty is the shared preamble.
- Worksheets live in homework/<sheet>/ with the typeset .tex and handwritten/ beside it.
- Write-ups live in the actual homework document: a chapter's homework/ set or a worksheet under homework/. Bind the sitting with `board writeup use <set>` before the first add. A docs/<session>/writeup.tex is never the destination.

## Now

Session 20261103-163801 works Part I of the owner's uploaded sheet `GaloisTheoryAtWork.pdf`: Problems 20, 21, 22.

The write-up lives in `chapters/ch07-splitting-fields/homework/ch07-homework.tex`, bound to ch07. 20(a) and 20(b) are closed; `% ===== SOLUTION 20 =====` holds both arguments, and the PDF built clean at 2026-11-07 18:02. 20(b)'s page (t0010-r8) is filed as `handwritten/ch07-20.png`; card 0029 grades it and notes its one slip (the IH remark must bound `Emb_{phi*}(K,L)` for fixed `phi*`).

Now: 20(c), stated "Deduce that $|\operatorname{Gal}(K/F)|\le[K:F]$." Card 0031 corrected their `psi(k)=k` line (a map fixing F need not fix alpha) and their unnecessary `K=F(alpha)` step. Card 0032 answers their "I feel like I'm missing a theorem" turn: the missing fact is linear algebra, that an F-subspace of the finite-dimensional space K with dimension equal to [K:F] is all of K, so the injective psi is surjective. The open step: with phi the inclusion F->K, `Emb_phi(K,K)=Gal(K/F)`, and part (b) gives the inequality. When they land it, write up 20(c) under label 20; then 20(d), 20(e); then 21, 22. Parts II-IV wait; the ch07 sheet (Problems 13-19) stays closed.

Steering: t0006 demanded the surjectivity candidate outright, so give definitions outright and do not ask them to name the map. Their 2026-11-07 turn demands every write-up go in the actual homework document as we go, never a `docs/` write-up; card 0024 records it. Mode stays teach.

## Open decisions

The board's own fallback still makes `docs/<session>/writeup.tex` for an unbound sitting, so bind each sitting to its homework set before the first add. A board-code change to make the fallback create or prefer a homework set waits for a worktree and a pause in the sitting.

## Done recently

- 19(d) closed on t0270 and written up under label 19: the division $\sqrt3=\zeta_{12}^2/\zeta_{12}^3+\zeta_{12}^4/\zeta_{12}^3=\zeta_{12}^{-1}+\zeta_{12}=\zeta_{12}^{11}+\zeta_{12}$, i.e. $x^{11}+x$ at $x=\zeta_{12}$, matching $2\cos(\pi/6)=\sqrt3$. Filed t0270 as `handwritten/ch07-19.png`; PDF clean.
- 19(c) closed on t0267 and written up under label 19: the product $\sqrt m=i^{k}\prod_{p\mid m}\sqrt p$, the gcd/order argument $\QQ(\zeta_n)=\QQ(\zeta_N^{N/n})\subseteq\QQ(\zeta_N)$, the modulus $N=4|m|$ placing $i$, every odd $\sqrt p$ (split by $p\pmod4$ via 18(d)) and $\sqrt2$, then field closure. PDF clean.
- 19(b) closed on t0259 and written up under label 19: $\zeta_8^2=i$, $\zeta_8+\zeta_8^{-1}=\sqrt2$, $\zeta_8+\zeta_8^{3}=i\sqrt2=\sqrt{-2}$, one element of $\QQ(\zeta_8)$ per target.
- 18(c) closed on t0248 and written up under label 18: the double sum with $l=km$, multiplicativity of the symbol collapsing $(k/p)^2$ to $1$, and the inner sum $p-1$ at $m=p-1$ against $-1$ elsewhere. The final arithmetic, $g^2=(-1/p)p$, was card 0149's.
- 17(a) closed and written up as label 17: existence of $\sigma$ via Corollary 2 of Theorem 7.5 over $\QQ(i)$, $|\sigma|=4$ from $\sigma^{2}(\alpha)=-\alpha$, $|\tau|=2$, $\tau\sigma\tau^{-1}=\sigma^{-1}$ checked at $i$ and $i\alpha$, the eight $\sigma^{a}\tau^{b}$ distinct, hence $\operatorname{Gal}(E/\QQ)\cong D_{4}$.
- The automorphisms and splitting-fields worksheet, problems 7-12: Aut(ℚ(ζₙ)/ℚ) inside (ℤ/nℤ)ˣ, Φₚ irreducible, the machine on x⁴+1, the splitting field of x³−2, and the finite-field pair.
- The solutions stranded in a retired project's `writeup.tex` were moved into `ch07-homework.tex`: 13(d), 14(a)-(c), 15(b)-(d), 16(a)-(c).
- The $p=13$, $d=2$ worked case of 13(d), carried from that project's writeup.tex into ch07-homework.tex, with the nine 13(d) pages as `handwritten/ch07-13d*.png`.
