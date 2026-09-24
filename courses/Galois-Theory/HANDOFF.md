<!-- chapter: Ch 05 — Tests for irreducibility -->
Scope this sitting: Garling 05.4, 05.6, 05.7, 05.8, 05.10, stated in chapters/ch05-tests-for-irreducibility/homework/ch05-homework.tex.

Where they got to:
- 05.4 (f - yg irreducible in K(y)[x]): worked through step by step, ending on where Gauss's lemma lands the factorisation. The solution region is still EMPTY. It is unclear whether they ever gave one full argument. Check their answer PNGs for 05.4 in live/answers/ before re-teaching; transcribe it if a full argument exists, otherwise re-pose 05.4 in full.
- 05.6 (Eisenstein upside down, p | f_i for i >= 1, p not dividing f_0, p^2 not dividing f_n): agreed correct. Transcribed, handwriting filed, build clean.
- 05.7 (x^n - p irreducible over Q): just opened. The open question asks for the coefficients of x^3 - 5 and which ones 5 divides.
- 05.8 and 05.10: not started.

What they got wrong in 05.6:
- In the constant-factor case they had c | f_i for every i but did not see that this IS the definition of relatively prime coefficients. They asked why c must be a unit. Once told, they used it correctly.
- Bookkeeping slips: the WLOG line said deg g = deg f when g was the constant, and they wrote "h = deg m" for m = deg h. Both are fixed in the tex.

What they got right, do not re-teach:
- Reduce mod p. R/(p) is an integral domain, so degrees add.
- Positive-degree case: p | g_k and p | h_m, so p^2 | f_n, a contradiction.

Next: finish 05.7. It is a direct application of Eisenstein's criterion, and the only trap is seeing that the zero middle coefficients are divisible by p. Then settle 05.4, then 05.8.

How they work:
- They answer by rewriting the whole proof, not just the micro-question. Read the full page and assess the proof.
- They skip sanity checks once the proof is done. Let them.
- Their proofs are sound, but naming slips (g vs h, swapped letters) recur. Check every symbol.
