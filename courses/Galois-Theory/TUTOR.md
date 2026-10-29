# Galois Theory

## Where things are

- The book is A Course in Galois Theory; chapters.tsv lists its chapters. Each is chapters/chNN-slug/ with notes/, homework/ and handwritten/; reading/ (the excerpt) and textbook/ stay out of git.
- latex/coursemacros.sty is the shared preamble.
- Worksheets live in homework/<sheet>/ with the typeset .tex and handwritten/ beside it.

## Now

Chapter 7 worksheet, problems 13-19, in session 20261009-193922. `chapters/ch07-splitting-fields/homework/ch07-homework.tex` holds 13(a)(b)(d), 14(a)-(d), 15(b)-(d), 16(a)-(d), 17(a)(b)(d), 18(a)-(d); the PDF rebuilt clean. Problem 19 is on their screen: `board writeup pose 19` pinned it, statement kept, region still their TODO.

18 closed on t0250: $g^2=p^*$, $\sigma_a(g)=(a/p)g$, and $g\in\QQ$ would force $(a/p)=1$ for every $a$, which fails because exactly half the residues are squares; so $g\notin\QQ$, $[\QQ(g):\QQ]=2$, and 18(a)'s one quadratic subfield inside $\QQ(\zeta_p)$ is $\QQ(g)=\QQ(\sqrt{p^*})$. Their page wrote "so $g\in\QQ$" and card 0151 says plainly it must be $\notin$. Label 18 carries (a)-(d); the $p=5,7,13$ arithmetic was cards 0149-0150 and stays out of the tex. `handwritten/ch07-18.png` is t0250.

Next: 19(a), the rung asks which power of $\zeta_b$ is a primitive $a$-th root. Then (b) inside $\zeta_8$, (c) $N=4|m|$, (d) $m=3$ with $\sqrt3=2\cos(\pi/6)=\zeta_{12}+\zeta_{12}^{-1}$.

17 closed on t0241 (lattice, Galois fields circled); (c) stays out per t0235, never re-pose it. 16(d) closed on t0225.

Still open: 13(c) (the $p=13$ subgroup list) and 15(a) (conjugation on $K$, set aside).

## Open decisions

## Done recently

- 18(c) closed on t0248 and written up under label 18: the double sum with $l=km$, multiplicativity of the symbol collapsing $(k/p)^2$ to $1$, and the inner sum $p-1$ at $m=p-1$ against $-1$ elsewhere. The final arithmetic, $g^2=(-1/p)p$, was card 0149's. PDF clean, `handwritten/ch07-18.png` is t0248.
- 17(a) closed and written up as label 17: existence of $\sigma$ via Corollary 2 of Theorem 7.5 over $\QQ(i)$, $|\sigma|=4$ from $\sigma^{2}(\alpha)=-\alpha$, $|\tau|=2$, $\tau\sigma\tau^{-1}=\sigma^{-1}$ checked at $i$ and $i\alpha$, the eight $\sigma^{a}\tau^{b}$ distinct by the $i$ and $\alpha$ evaluations, hence $\operatorname{Gal}(E/\QQ)\cong D_{4}$.
- The automorphisms and splitting-fields worksheet, problems 7-12: Aut(ℚ(ζₙ)/ℚ) inside (ℤ/nℤ)ˣ, Φₚ irreducible, the whole machine on x⁴+1, the splitting field of x³−2, and the finite-field pair.
- The solutions stranded in a retired project's `writeup.tex` were moved into `ch07-homework.tex`: 13(d), 14(a)-(c), 15(b)-(d), 16(a)-(c).
- The $p=13$, $d=2$ worked case of 13(d), carried from that project's writeup.tex into ch07-homework.tex, with the nine 13(d) pages as `handwritten/ch07-13d*.png`.
- 16(d) closed on the owner's $i=i\alpha\cdot\alpha^{-1}$ line from t0225.
