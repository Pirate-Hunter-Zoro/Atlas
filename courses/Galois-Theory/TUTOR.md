# Galois Theory

## Where things are

- The book is A Course in Galois Theory; chapters.tsv lists its chapters. Each is chapters/chNN-slug/ with notes/, homework/ and handwritten/; reading/ (the excerpt) and textbook/ stay out of git.
- latex/coursemacros.sty is the shared preamble.
- Worksheets live in homework/<sheet>/ with the typeset .tex and handwritten/ beside it.

## Now

Chapter 7 worksheet, problems 13-19, in session 20261009-193922. `chapters/ch07-splitting-fields/homework/ch07-homework.tex` holds 13(a)(b)(d), 14(a)-(d), 15(b)-(d), 16(a)-(d), 17(a)(b)(d), and 18(a); the PDF rebuilt clean. `handwritten/ch07-18.png` is t0243.

17 closed on t0241: the lattice with the six Galois fields circled, and the note that $\QQ(\alpha)$ is not Galois over $\QQ$ though $E$ is Galois over $\QQ$ and over $\QQ(\alpha)$. Label 17 was rewritten with (a), (b) and (d), the lattice as a TikZ picture; (c) stays out per the t0235 direction, never re-pose it.

On Problem 18 (Gauss sums), 18(a) closed on t0243 (cyclic Galois group of order $p-1$, unique index-$2$ subgroup, correspondence) and is written up. Card 0144 asks the 18(b) rung: apply $\sigma_a$ to $g$, substitute $l=ak$, name the coefficient of $\zeta^{l}$. Next: 18(b) closes once they see the coefficient is $(a/p)(l/p)$; 18(c) is the double sum with $l=km$; 18(d) names $\QQ(\sqrt{p^*})$ and needs $p=7$ against 14, then $p=5$ and $p=13$. Then 19.

Still open: 13(c) (the $p=13$ subgroup list) and 15(a) (conjugation on $K$, set aside).

## Open decisions

## Done recently

- 17(a) closed and written up as label 17: existence of $\sigma$ via Corollary 2 of Theorem 7.5 over $\QQ(i)$, $|\sigma|=4$ from $\sigma^{2}(\alpha)=-\alpha$, $|\tau|=2$, $\tau\sigma\tau^{-1}=\sigma^{-1}$ checked at $i$ and $i\alpha$, the eight $\sigma^{a}\tau^{b}$ distinct by the $i$ and $\alpha$ evaluations, hence $\operatorname{Gal}(E/\QQ)\cong D_{4}$. PDF clean, `handwritten/ch07-17.png` is t0232.
- The automorphisms and splitting-fields worksheet, problems 7-12: Aut(ℚ(ζₙ)/ℚ) inside (ℤ/nℤ)ˣ, Φₚ irreducible, the whole machine on x⁴+1, the splitting field of x³−2, and the finite-field pair.
- The solutions stranded in a retired project's `writeup.tex` were moved into `ch07-homework.tex`: 13(d), 14(a)-(c), 15(b)-(d), 16(a)-(c).
- The $p=13$, $d=2$ worked case of 13(d), carried from that project's writeup.tex into ch07-homework.tex, with the nine 13(d) pages as `handwritten/ch07-13d*.png`.
- 16(d) closed on the owner's $i=i\alpha\cdot\alpha^{-1}$ line from t0225.
- 18(a) closed on t0243 and written up as label 18: cyclic Galois group of order $p-1$, the unique index-$2$ subgroup, $[G:H]=[K:\QQ]$. PDF clean, `handwritten/ch07-18.png` is t0243.
