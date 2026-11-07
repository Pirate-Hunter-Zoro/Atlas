# Galois Theory

## Where things are

- The book is A Course in Galois Theory; chapters.tsv lists its chapters. Each is chapters/chNN-slug/ with notes/, homework/ and handwritten/; reading/ (the excerpt) and textbook/ stay out of git.
- latex/coursemacros.sty is the shared preamble.
- Worksheets live in homework/<sheet>/ with the typeset .tex and handwritten/ beside it.
- Write-ups live in the actual homework document: a chapter's homework/ set or a worksheet under homework/. Bind the sitting with `board writeup use <set>` before the first add. A docs/<session>/writeup.tex is never the destination.

## Now

Session 20261103-163801, a lecture with no chapter label, works Part I of the owner's uploaded sheet `GaloisTheoryAtWork.pdf`: Problems 20, 21, 22, proving the fundamental theorem from scratch.

The write-up lives in the actual homework document, `chapters/ch07-splitting-fields/homework/ch07-homework.tex`, under Problem 20. This turn bound the sitting to ch07, moved Problem 20 and their part-(a) argument out of `docs/writeup-20261103-163801/writeup.tex`, filed their page as `handwritten/ch07-20.png`, removed the `docs/` file, and rebuilt the PDF clean. Card 0024 reports it and re-poses 20(b).

20(a) is closed. Their page proved the inequality half and the equality clause: since $\gamma$ is a bijection, $|\operatorname{Emb}_\phi(F(\alpha),L)|=|R|$ always, so equality holds exactly when $|R|=\deg m$, i.e. $\phi(m)$ has $\deg m$ distinct roots in $L$. The SOLUTION 20 region holds the full argument.

Card 0024 poses 20(b): $|\operatorname{Emb}_\phi(K,L)|\le[K:F]$ by induction on $[K:F]$, and asks them to state the induction hypothesis so it applies over $F(\alpha)$ after choosing $\alpha\in K\setminus F$. The obstacle is that the hypothesis must cover an arbitrary base field; do not hand them the restriction-map argument until they show that.

After 20(b): 20(c), 20(d), 20(e); then 21, 22. Parts II-IV wait; the ch07 sheet (Problems 13-19) stays closed.

Steering: t0006 demanded the surjectivity candidate outright, so give definitions outright and do not ask them to name the map. Their latest turn demands every write-up go in the actual homework document as we go, never a `docs/` write-up; card 0024 records it. Mode stays teach.

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
