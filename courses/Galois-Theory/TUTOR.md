# Galois Theory

## Where things are

- The book is A Course in Galois Theory; chapters.tsv lists its chapters. Each is chapters/chNN-slug/ with notes/, homework/ and handwritten/; reading/ (the excerpt) and textbook/ stay out of git.
- latex/coursemacros.sty is the shared preamble.
- Worksheets live in homework/<sheet>/ with the typeset .tex and handwritten/ beside it.

## Now

Chapter 7 worksheet, problems 13-19, in session 20261009-193922. `chapters/ch07-splitting-fields/homework/ch07-homework.tex` holds 13(a)(b)(d), 14(a)-(d), 15(b)-(d), 16(a)-(d) and now 17(a). The PDF rebuilt clean at 17:49 and the board reads 5 of 7.

Problem 17(a) is closed. t0232 finished it: at $i$, $b\equiv b'\pmod 2$; at $\alpha$, $a\equiv a'\pmod 4$; so the eight $\sigma^{a}\tau^{b}$ are distinct, and with $[E:\QQ]=8$ they are all of $\operatorname{Gal}(E/\QQ)\cong D_{4}$. Written up under label 17; the page is `handwritten/ch07-17.png` (t0232).

Card 0133 poses 17(b) in full and asks the first move: $H=\langle\sigma\rangle$, which field $\sigma$ fixes and why $E^{H}$ has degree $2$ over $\QQ$. Then $\langle\sigma^{2},\tau\rangle$ with $\QQ(\sqrt2)$ and $\langle\sigma^{2},\sigma\tau\rangle$ with $\QQ(\sqrt{-2})$. After 17(b): 17(c) (five order-$2$ subgroups, hint is a fixed-field plus degree check), 17(d) (lattice of ten, which are Galois, reconcile with 16), then 18 and 19.

Still open:

- 13(c): the $p=13$ subgroup list. Write it up from the $p=7$ work on the early pages (cards 0011-0026); never re-pose $p=13$.
- 15(a): complex conjugation restricted to $K$. Set aside for 14, never answered; 15(b)-(d) are written up without it.
- 17(c), 17(d), 18, 19: not started.

Standing directions: no small cases, examples or subgroup lists once they are working a proof ("Focus on the proof", t0191); "move on" means move on, and a dropped problem stays dropped until they reopen it; never write the proof for them (t0192). A request to read files, transcribe or compile is done, not taught (t0219). A definition they ask for is stated in full first (t0229 asked for $D_4$). A computation they ask for is given exactly in the card, with no next step attached.

## Open decisions

## Done recently

- 17(a) closed and written up as label 17: existence of $\sigma$ via Corollary 2 of Theorem 7.5 over $\QQ(i)$, $|\sigma|=4$ from $\sigma^{2}(\alpha)=-\alpha$, $|\tau|=2$, $\tau\sigma\tau^{-1}=\sigma^{-1}$ checked at $i$ and $i\alpha$, the eight $\sigma^{a}\tau^{b}$ distinct by the $i$ and $\alpha$ evaluations, hence $\operatorname{Gal}(E/\QQ)\cong D_{4}$. PDF clean, `handwritten/ch07-17.png` is t0232.
- The automorphisms and splitting-fields worksheet, problems 7-12: Aut(ℚ(ζₙ)/ℚ) inside (ℤ/nℤ)ˣ, Φₚ irreducible, the whole machine on x⁴+1, the splitting field of x³−2, and the finite-field pair.
- The solutions stranded in a retired project's `writeup.tex` were moved into `ch07-homework.tex`: 13(d), 14(a)-(c), 15(b)-(d), 16(a)-(c).
- The $p=13$, $d=2$ worked case of 13(d), carried from that project's writeup.tex into ch07-homework.tex, with the nine 13(d) pages as `handwritten/ch07-13d*.png`.
- 16(d) closed on the owner's $i=i\alpha\cdot\alpha^{-1}$ line from t0225.
