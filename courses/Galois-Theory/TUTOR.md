# Galois Theory

## Where things are

- The book is A Course in Galois Theory; chapters.tsv lists its chapters. Each is chapters/chNN-slug/ with notes/, homework/ and handwritten/; reading/ (the excerpt) and textbook/ stay out of git.
- latex/coursemacros.sty is the shared preamble.
- Worksheets live in homework/<sheet>/ with the typeset .tex and handwritten/ beside it.

## Now

Chapter 7 worksheet, problems 13-19, in session 20261009-193922. `chapters/ch07-splitting-fields/homework/ch07-homework.tex` holds 13(a)(b)(d), 14(a)-(d), 15(b)-(d), 16(a)-(d), 17(a)(b)(d), 18(a)-(d), 19(a); the PDF rebuilt clean. `handwritten/ch07-19.png` is t0257.

19(a) closed on t0257 and is written up under label 19. Their chain: order of $\zeta_b^c$ is $a$ (t0255), so it is a primitive $a$-th root and $\QQ(\zeta_a)=\QQ(\zeta_b^c)$; $\zeta_b^c$ is $c$ copies of $\zeta_b$, so the containment. Card 0159 (on the board now) poses 19(b) and points at $\zeta_8+\zeta_8^{-1}$ via the hint in (d).

Next after (b): (c) $N=4|m|$, then (d) $m=3$ with $\sqrt3=2\cos(\pi/6)=\zeta_{12}+\zeta_{12}^{-1}$. Write each up with `board writeup add 19`, including everything agreed so far.

## Open decisions

## Done recently

- 18(c) closed on t0248 and written up under label 18: the double sum with $l=km$, multiplicativity of the symbol collapsing $(k/p)^2$ to $1$, and the inner sum $p-1$ at $m=p-1$ against $-1$ elsewhere. The final arithmetic, $g^2=(-1/p)p$, was card 0149's. PDF clean, `handwritten/ch07-18.png` is t0248.
- 17(a) closed and written up as label 17: existence of $\sigma$ via Corollary 2 of Theorem 7.5 over $\QQ(i)$, $|\sigma|=4$ from $\sigma^{2}(\alpha)=-\alpha$, $|\tau|=2$, $\tau\sigma\tau^{-1}=\sigma^{-1}$ checked at $i$ and $i\alpha$, the eight $\sigma^{a}\tau^{b}$ distinct by the $i$ and $\alpha$ evaluations, hence $\operatorname{Gal}(E/\QQ)\cong D_{4}$.
- The automorphisms and splitting-fields worksheet, problems 7-12: Aut(ℚ(ζₙ)/ℚ) inside (ℤ/nℤ)ˣ, Φₚ irreducible, the whole machine on x⁴+1, the splitting field of x³−2, and the finite-field pair.
- The solutions stranded in a retired project's `writeup.tex` were moved into `ch07-homework.tex`: 13(d), 14(a)-(c), 15(b)-(d), 16(a)-(c).
- The $p=13$, $d=2$ worked case of 13(d), carried from that project's writeup.tex into ch07-homework.tex, with the nine 13(d) pages as `handwritten/ch07-13d*.png`.
- 16(d) closed on the owner's $i=i\alpha\cdot\alpha^{-1}$ line from t0225.
