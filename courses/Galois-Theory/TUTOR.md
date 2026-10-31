# Galois Theory

## Where things are

- The book is A Course in Galois Theory; chapters.tsv lists its chapters. Each is chapters/chNN-slug/ with notes/, homework/ and handwritten/; reading/ (the excerpt) and textbook/ stay out of git.
- latex/coursemacros.sty is the shared preamble.
- Worksheets live in homework/<sheet>/ with the typeset .tex and handwritten/ beside it.

## Now

Chapter 7 homework, problems 13-19, session 20261009-193922. All seven problems are closed and written up in `chapters/ch07-splitting-fields/homework/ch07-homework.tex`; the PDF is clean. 19(a)-(d) sit under label 19, with `handwritten/ch07-19.png` filed from t0270 (19(d)). Nothing outstanding on this sheet.

## Open decisions

## Done recently

- 19(d) closed on t0270 and written up under label 19: the division $\sqrt3=\zeta_{12}^2/\zeta_{12}^3+\zeta_{12}^4/\zeta_{12}^3=\zeta_{12}^{-1}+\zeta_{12}=\zeta_{12}^{11}+\zeta_{12}$, i.e. $x^{11}+x$ at $x=\zeta_{12}$, matching $2\cos(\pi/6)=\sqrt3$. Filed t0270 as `handwritten/ch07-19.png`; PDF clean.
- 19(c) closed on t0267 and written up under label 19: the product $\sqrt m=i^{k}\prod_{p\mid m}\sqrt p$, the gcd/order argument $\QQ(\zeta_n)=\QQ(\zeta_N^{N/n})\subseteq\QQ(\zeta_N)$, the modulus $N=4|m|$ placing $i$, every odd $\sqrt p$ (split by $p\pmod4$ via 18(d)) and $\sqrt2$, then field closure. PDF clean.
- 19(b) closed on t0259 and written up under label 19: $\zeta_8^2=i$, $\zeta_8+\zeta_8^{-1}=\sqrt2$, $\zeta_8+\zeta_8^{3}=i\sqrt2=\sqrt{-2}$, one element of $\QQ(\zeta_8)$ per target.
- 18(c) closed on t0248 and written up under label 18: the double sum with $l=km$, multiplicativity of the symbol collapsing $(k/p)^2$ to $1$, and the inner sum $p-1$ at $m=p-1$ against $-1$ elsewhere. The final arithmetic, $g^2=(-1/p)p$, was card 0149's.
- 17(a) closed and written up as label 17: existence of $\sigma$ via Corollary 2 of Theorem 7.5 over $\QQ(i)$, $|\sigma|=4$ from $\sigma^{2}(\alpha)=-\alpha$, $|\tau|=2$, $\tau\sigma\tau^{-1}=\sigma^{-1}$ checked at $i$ and $i\alpha$, the eight $\sigma^{a}\tau^{b}$ distinct, hence $\operatorname{Gal}(E/\QQ)\cong D_{4}$.
- The automorphisms and splitting-fields worksheet, problems 7-12: Aut(ℚ(ζₙ)/ℚ) inside (ℤ/nℤ)ˣ, Φₚ irreducible, the machine on x⁴+1, the splitting field of x³−2, and the finite-field pair.
- The solutions stranded in a retired project's `writeup.tex` were moved into `ch07-homework.tex`: 13(d), 14(a)-(c), 15(b)-(d), 16(a)-(c).
- The $p=13$, $d=2$ worked case of 13(d), carried from that project's writeup.tex into ch07-homework.tex, with the nine 13(d) pages as `handwritten/ch07-13d*.png`.
