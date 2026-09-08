<!-- chapter: Ch 03 — Rings -->
# HANDOFF

**Ch 03, Rings (Garling) — homework.** Assigned: **3.1, 3.2, 3.3, 3.8, 3.10,
3.11, 3.12, 3.14, 3.15, 3.17, 3.25, 3.26.** Sheet:
`handwritten/20260902-exercise-list.png`.

**Tooling.** `scripts/build.sh` fails silently on the Mac — use `board hw
build`. File pages to `chapters/ch03-rings/handwritten/`.

**Read the PNG.** Cards **0081, 0082, 0083** are dead weight in the transcript:
a session that could not open images asked the student three times to transcribe
their own handwriting, and they re-sent the same page three times. The contract
forbids this. The pages open fine with an ordinary image read; `board eyes
<path>` is the fallback. Never ask this student to type mathematics — the board
is in math mode and has no text box.

## Where it got to

**3.1, 3.10** complete and transcribed. **3.8** all but the infinite case.
**3.11** all but one clause. **3.2, 3.3** skipped 2026-09-02 ("I have lost
patience") — still owed, come back unremarked.

## Right — do not re-teach

deg(fg) = deg f + deg g over a domain, via aₙbₘ ≠ 0, proved unaided. Units of
R[x] = units of R, as constants. Units of ℤ₄[x]: constant term a unit, other
coefficients zero divisors; 2x+3 found unaided. b + (a) = 0 ⟺ a | b. Both the
forward direction of 3.11 and the divisibility half of its converse. **(2) in
ℚ is all of ℚ.** **1/4 as an element of (2) in ℚ but not (2) in ℤ** — answered
correctly this session, card 0080. **a a unit ⟹ (a) = R**, witness x = ra⁻¹,
with the ∃ stated properly — card 0086.

They did *not* write the second half of 0080 — which fact about 2 put 1/4
there. Card 0084 supplies it (1/4 = 2·⅛, and ⅛ exists because 2 is invertible)
and asks the same thing at full generality instead of re-asking the instance.

## How 3.11 and 3.12 went — oldest first

*3.11 and 3.12(a), (b) are all finished and transcribed. This section is the
record of how, kept for the misunderstandings in it. The live item is under
**Next** at the bottom.*

Card 0084 asked: a a unit in R ⟹ (a) = R. Their attempt got the first line
right — a⁻¹ ∈ R so e = aa⁻¹ ∈ (a) — then closed with "es = s ∈ R, so (a) = R",
which lands in the wrong set and uses nothing they had just proved. Card
0085 located that line and asked them to end it in (a) instead. They edited
"s ∈ R" to "s ∈ (a)" and changed nothing else — the conclusion asserted, not
earned. Root cause: they had written "by the definition of (a), ∀r ∈ R",
reading membership in (a) as a ∀ over r rather than an ∃, which is why the r
was never picked up and used. Card 0086 named that quantifier error and asked
only for the witness. **They then proved it: r ∈ (a) iff ∃x with xa = r, take
x = ra⁻¹.** Quantifier and witness both correct, unaided.
`handwritten/20260907-3.11-attempt10-unit-ideal-is-R-correct.png`.

**3.11 is finished and transcribed**, both directions, and the document
compiles (3 pages, 0 warnings). Card 0087 re-posed the last clause; they took
the contrapositive unaided and got R/(a) = R/R = {R}, then ended "which cannot
be an integral domain" with no reason — card 0088 asked which of the two
requirements fails, and rev 2 supplied e = 0. Correct.

One thing still owed on 3.11 and never asked: the closing line of the
divisibility contrapositive, "contrary to assumption, so a is prime". The
solution region stops at "not an integral domain". Recorded in a comment there.

Card 0089 closed 3.11 and posed **3.12** in full (R = ℤ + i√5ℤ; units are ±1;
φ(m+i√5n) = m²+5n²; 2 ± i√5 irreducible; 2 + i√5 not prime, so R is not a UFD),
then asked one mechanical rung. They got it all: αβ = 7 + i√5, φ = 6, 9, 54 —
and wrote φ(αβ) = φ(α)φ(β) unprompted, which is the point of the rung.
`handwritten/20260907-3.12-attempt1-phi-instance-correct.png`.

Card 0090 asked them to prove φ(αβ) = φ(α)φ(β) for arbitrary α, β. They took
the direct-expansion route, dropped the n's out of the cross terms — writing
i√5(m₁ + m₂) where it is i√5(m₁n₂ + m₂n₁) — and then wrote on the page: "This
is algebra hell. Assuming this is right so far, let's skip this algebra given I
know what must be proven."

**Skip granted, and the lemma is now mine, not theirs.** Card 0091 says where
the cross terms went, gives the closed identity, and shows the conjugate route
(φ(α) = αᾱ, conjugation multiplicative, three lines, no expansion) that they
declined on card 0090. φ multiplicative is available to them from here.
`handwritten/20260907-3.12-attempt2-phi-multiplicative-skipped.png`.

When 3.12(a) is written up, the write-up must say the multiplicativity lemma
was supplied rather than proved by them.

Card 0091 posed **3.12(a)** in full. They came back typed, no page: "Clearly
they are units. Each their own inverse. But how to prove nothing else has an
inverse?" A real question — the ±1 half is right, and what they cannot see is
how to close off an infinite ring.

Card 0092 answered it — you never check the other elements, you push αβ = 1
through φ and land in ℕ — and asked them to apply φ and name the set. They came
back with almost the whole of (a): αβ = 1, φ(αβ) = φ(1) = 1,
φ(α)φ(β) = 1, **φ: R → ℕ written unprompted**, φ(β) = φ(α), and the closing
"this forces m = ±1, n = 0".

One line was false and sat directly under the ℕ line: φ(α) ∈ {−1, 1}. Card 0093
put the two contradictory lines side by side; rev 4 replaced it with
φ(α) = 1 and nothing else changed. **3.12(a) is done and transcribed**;
document compiles, 3 pages, 0 warnings.
`handwritten/20260907-3.12a-attempt4-units-correct.png`.

Card 0094 posed **3.12(b)** in full with no ladder. They stalled, and the stall
is informative: they **put φ down** and went to coordinates — β = a + i√5b,
γ = c + i√5d, expanded correctly this time, and matched to the system
ac − 5bd = 2, ad + bc = 1. Then two pencilled questions: "will this system lead
to a contradiction?" and "Am I right so far?"

Card **0095** answers both. No, it cannot: a=1, b=0, c=2, d=1 solves it, being
1·(2 + i√5). **The misunderstanding is what irreducible means** — they were
hunting for "no factorization exists" rather than "every factorization contains
a unit". Also flagged: their added assumption a,b,c,d ≠ 0 is not available
(β = 3 has b = 0 and is not a unit).
`handwritten/20260907-3.12b-attempt5-coordinates-question.png`.

The card then laddered, since they stalled: compute φ(2 + i√5) and list every
way it factors as a product of two elements of ℕ.

**They did not need the ladder — they went straight to the whole of (b)** on
2026-09-08 and got almost all of it unaided: not units, suppose α = βγ with
neither a unit, φ(α) = 9, φ(βγ) = φ(β)φ(γ) = 9, splittings 3·3 and 1·9, then
"could m² + 5n² = 3? **NO**", then φ = 1 only if m = ±1, n = 0. That is the
proof. `handwritten/20260908-3.12b-attempt6-phi-argument-unfinished.png`.

Two faults, both after the proof was already finished:

- **They stopped one sentence short.** β = ±1 was never named a unit and never
  set against the supposition. Same pattern as cards 0085–0086 and 0088: they
  reach the last line and do not draw the conclusion from it.
- They then added a box for the φ(β) = 9 branch and got it wrong —
  "only if m = ±2, n = ±1", missing m = ±3, n = 0. That branch is the φ = 1
  branch with the letters swapped and needs no case work at all. (For the
  record: ±3 cannot divide 2 + i√5 anyway, so nothing downstream is poisoned.)

Card 0096 said the proof ends at the φ = 1 line, flagged the false list as both
wrong and unnecessary, and asked for the two closing lines only. **Rev 7 deleted
the box and wrote the close** — "So φ(β) = 1 or φ(γ) = 1, which means β or γ is
a unit" — in five minutes, unaided. **3.12(b) is done and transcribed**;
document compiles, 4 pages, 0 warnings.
`handwritten/20260908-3.12b-attempt7-irreducible-correct.png`.

Their page named both 2 ± i√5 and worked only 2 + i√5. The remark that the
other needs no separate argument (φ of it is 9 as well) is **mine**, card 0097,
and is recorded as supplied in the .tex comment.

## How 3.12(c) went

**3.12(c)** — posed cold, in full, on card 0097 with its definition list,
including the named result that irreducibles are prime in a UFD. The ask is
only the first half: show 2 + i√5 is not prime. The UFD deduction is deliberately
held back, because they answer the first half of a two-part ask and drop the
second.

The route: 9 = 3·3 = (2 + i√5)(2 − i√5), so 2 + i√5 divides 9 = 3·3 but divides
neither factor — 3/(2 + i√5) = (2 − i√5)/3 ∉ R. Card 0097 points them at the
number 9 and its factorization list, nothing more.

**Rev 8 (2026-09-08, card 0098).** They unpacked *not prime* correctly and
twice, the second time in full logical form: ∃c₁ with αc₁ = βγ, but no c₂ with
αc₂ = β or αc₂ = γ. Unprompted, and it is the hard half of these. Nothing on
the page is false. Then they pushed φ through it — φ(α)φ(c) = φ(β)φ(γ), so
9φ(c) = φ(β)φ(γ) — and wrote "But I'm stuck now...".

**The break is that they are solving for β and γ instead of choosing them.**
*Not prime* is an existence claim; they wrote the ∃ themselves and did not
notice it was theirs to satisfy. Their equation has three unknowns nobody has
chosen, so there is nothing in it to solve. This is the same reflex as rev 5 on
(b) — hunting a contradiction in a system of unknowns rather than producing or
constraining concrete objects. **Third appearance now; it is this student's
signature failure mode, not a one-off.** Name the existence/universal
distinction when it recurs.
`handwritten/20260908-3.12c-attempt8-definition-unpacked-stuck.png`.

Card 0098 named that, and laddered with one mechanical rung: compute
(2 + i√5)(2 − i√5). **They answered "It's 9" in three minutes, typed, no page.**
Correct.

Card 0099 read that back as α·(2 − i√5) = 9, so α | 9, pointed at their own
earlier 9 = 3·3, and asked the crux: **does 2 + i√5 divide 3?** Yes/no with a
reason. β = γ = 3 is left visible rather than announced.

Two routes to α ∤ 3, grade either:
- direct — 3/(2 + i√5) = (2 − i√5)/3, whose coordinates are not integers;
- via φ — 3 = αc gives 9 = 9φ(c), so φ(c) = 1, so c = ±1 by (a), so
  3 = ±(2 + i√5), false.

**Rev 9 (2026-09-08, card 0100) is the whole of the first half of (c), in the
right shape, with one false line.** They picked βγ = 9 with β = γ = 3, showed
α | 9 from (2 + i√5)(2 − i√5) = 9, ruled out α | 3 via φ, concluded not prime.
The φ chain is correct to φ(c₂) = 1. Then:

> φ(c₂) = 1 requires c₂ = ±1 **or c₂ = ±i√5**

φ(i√5) = 5, so the second candidate is false — and it directly contradicts
their own part (a), which forces m = ±1, n = 0. They then checked the spurious
candidate and correctly found (2 + i√5)(±i√5) ≠ 3, so the **conclusion is not
in danger**; the repair is one deletion.
`handwritten/20260908-3.12c-attempt9-not-prime-phi-list-wrong.png`.

**This is the third time they have mis-enumerated solutions of m² + 5n² = k**
— rev 3 in (a) wrote φ(α) ∈ {−1, 1} under its own φ : R → ℕ, rev 6 in (b) gave
the φ = 9 list as only m = ±2, n = ±1. The proof architecture is consistently
sound; the small integer enumeration underneath it is consistently sloppy.
Check every such list against m² + 5n² by hand before accepting it.

Card 0100 put their line beside their own (a) and asked one thing: compute
φ(i√5). **Rev 10 deleted the candidate, kept c₂ = ±1, and diagnosed the slip
itself in the margin — "I forgot n² is multiplied by 5 in φ".** Four minutes.
`handwritten/20260908-3.12c-attempt10-not-prime-correct.png`.

**The first half of (c) — 2 + i√5 is not prime — is done and transcribed.**
Document compiles, 4 pages, 0 warnings. The witness β = γ = 3 is theirs;
nothing in (c) was supplied.

**Rev 11 gave the deduction in three lines and it is correct:** irreducible by
(b), not prime, so R is not a UFD. **3.12 is complete and fully transcribed**;
document compiles, 4 pages, 0 warnings.
`handwritten/20260908-3.12c-attempt11-ufd-deduction-correct.png`.

They wrote the appeal to the named result as a bare "So". The .tex writes the
clause out and records that the result was supplied on card 0101, not proved by
them.

## How the irreducible/prime gloss got closed

**Worth keeping, because it was conceptual rather than a write-up gap.** Rev 11
glossed the conclusion as "an element in R could have multiple different
**prime** factorizations". False: factorization into primes is essentially
unique in any integral domain. What fails in R is uniqueness of factorization
into **irreducibles**. The gloss collapses exactly the distinction (b) and (c)
spent the hour separating, so it is worth closing rather than letting stand.

Card 0102 located it and asked one thing: **is 3 prime in R?** They answered in
two minutes and correctly: 3 | 9 = (2 + i√5)(2 − i√5) but 3 divides neither
factor. `handwritten/20260908-3.12c-attempt12-three-not-prime-correct.png`.
Card 0103 closed the loop — both sides of 9 = 3·3 = (2 + i√5)(2 − i√5) are
factorizations into irreducibles, neither into primes. **The gloss is settled
and 3.12 is closed.** It is deliberately absent from the solution region, being
a gloss rather than a proof step.

## How 3.3 went

**3.3, posed in full on card 0104.** *Show that an integral domain with a
finite number of elements is always a field.* Statement transcribed into
the .tex (it was a `\todo`). Posed cold
with its definition list, cancellation named as available, and the ask narrowed
to: fix a non-zero a and produce b with ab = e.

**Rev 1 came back in under two minutes with a different and equally good
skeleton**, attributed on the page to Dr. Cox-Steib: finiteness forces the
powers x, x², x³, … to repeat, so ∃n with xⁿ = x, so xⁿ⁻¹ = e, so xⁿ⁻² is the
inverse of x. That is the standard proof and the architecture is right.
`handwritten/20260908-3.3-attempt1-powers-repeat-nonzero-missing.png`.

**What is wrong: the word *non-zero* is absent from the entire page**, and the
last line therefore claims *all* elements have an inverse, which is false — 0
never does. The omission is load-bearing rather than cosmetic: the step
xⁿ = x ⟹ xⁿ⁻¹ = e is cancellation, it needs x ≠ 0, and nothing on the page
justifies it.

Card 0105 located that line and asked one thing: **run the argument with x = 0
and name the first line that says something false.** Expect them to land on
xⁿ⁻¹ = e giving 0 = e. That is the non-example that forces the hypothesis into
the proof.

**Rev 2 fixed both, in three minutes**, and did not answer the x = 0 question —
it went straight to the repair, which is the point. They wrote (x ≠ 0) on the
repetition line, changed the conclusion to *all nonzero elements*, and circled
xⁿ⁻¹ = e with an expansion beneath it: xⁿ = x ⟺ xⁿ⁻¹x = x ⟺ xⁿ⁻¹ = e
⟺ xⁿ⁻²x = e. `handwritten/20260908-3.3-attempt2-nonzero-added.png`.

**Still unearned, and now raised (card 0106): the word "meaning" in line two.**
"The powers repeat" gives xⁱ = xʲ for some i < j. It does not give xⁿ = x —
getting back to exponent 1 is itself a cancellation, and the line uses the
domain property without saying so. The non-example on the card is ℤ₄ with
x = 2: powers 2, 0, 0, 0, … repeat, yet no n ≥ 2 has 2ⁿ = 2. ℤ₄ is finite with
e ≠ 0 and is not a domain, which is exactly what their line leans on. They know
ℤ₄ from 3.10.

**Rev 3 (card 0107) answered with the reason rather than the form**, and the
reason is right: *an integral domain has no zero divisors, so xⁿ ≠ 0 for every
n, so the powers live among the nonzero elements, of which there are finitely
many.* That is the real content of the repetition step and they supplied it
unaided. `handwritten/20260908-3.3-attempt3-nonzero-powers-justified.png`.

**One gap left, and it is the same cancellation in two places.** They closed the
margin with "and loop back to x", which is still asserted: repetition in a
finite set gives xⁱ = xʲ at two exponents, and nothing says either is 1. The
same unnamed cancellation sits inside their circled expansion,
xⁿ⁻¹x = x ⟹ xⁿ⁻¹ = e.

Card 0107 asked for the concrete instance x³ = x⁷. **Rev 4 ignored the instance
and did it at general exponents, correctly and unaided:** xᵏ = xˡ with ℓ > k,
rewrite as xᵏx^(ℓ−k) = xᵏ, cancel xᵏ, so x^(ℓ−k) = e, so x·x^(ℓ−k) = x and the
sequence loops back to x. That also closed the loose end I never raised, since
ℓ > k forces n = ℓ−k+1 ≥ 2.
`handwritten/20260908-3.3-attempt4-cancellation-correct.png`.

**3.3 is done and transcribed.** Document compiles, 4 pages, 0 warnings.

One transcription note worth knowing about this board: **rev 4 replaced the ink
rather than adding to it**, so the finished proof lives across two pages — the
main argument and its margin in rev 3, the repeat lemma in rev 4. The .tex
assembles them in argument order and says so. Check for this whenever a page
suddenly gets shorter.

## Next — 3.14, in progress

**3.14, posed in full on card 0108.** *A proper ideal I is prime if ab ∈ I
implies a ∈ I or b ∈ I; show a non-zero c ∈ R is prime iff (c) is a prime
ideal.* Statement now transcribed into the .tex. Posed cold, with the two
hinges listed as things they already own from 3.11: a ∈ (c) ⟺ c | a, and
(c) = R ⟺ c is a unit. The second is what matches "not a unit" on the left to
"proper" on the right, and it is the half most likely to be dropped.

**It was dropped, exactly as predicted. Rev 5 (2026-09-08 11:24, card 0109)
has both divisibility halves right and unaided, and no mention of a unit
anywhere on the page.**

What they wrote, and it is all correct: forward, ab ∈ (c) gives cr = ab, so
c | ab, so c | a or c | b, WLOG c | a, so ∃r₁ with r₁c = a, so a ∈ (c).
Reverse, the same argument run backwards — a | bc gives bc ∈ (a), so b ∈ (a) or
c ∈ (a), so a | b. Nothing on the page is false.
`handwritten/20260908-3.14-attempt5-both-directions-proper-missing.png`.

Two things about that page:

- **They relabelled the element as `a` in the reverse direction**, with b and c
  as the two factors. Harmless permutation of letters, flagged in one clause and
  not pursued; it must be renamed back to c in the transcription.
- **"Prime ideal" is two words and they proved one.** Neither direction touches
  properness: forward never shows (c) ≠ R, and the reverse never gets from
  "(c) proper" to "c is not a unit". Both are one line off the 3.11 hinge
  (c) = R ⟺ c a unit.

Card 0109 named that and asked **only the forward line** — assume c prime, so
not a unit, show (c) ≠ R. The mirror line for the converse was deliberately
held back, because they answer the first half of a two-part ask and drop the
second.

**Rev 6 (2026-09-08 11:33, card 0110) supplied it in nine minutes and it is
correct:** "Note c is prime, and hence not a unit. So (c) ≠ R, and is therefore
a proper ideal." Off the 3.11 hinge, unaided. **The forward direction of 3.14 is
finished.**
`handwritten/20260908-3.14-attempt6-forward-proper-correct.png`.

**Rev 6 wrote over the reverse direction — it exists only on rev 5.** Same
replace-the-ink behaviour as rev 4 of 3.3. Card 0110 told them not to rewrite it
and quoted it back with the letters normalised to c, so they can see it is held.

Card 0110 asked the last line owed: assume (c) is a prime ideal, so (c) ≠ R,
show c is not a unit.

**Rev 7 (2026-09-08 11:36, card 0111) has the chain right and the conclusion
about the wrong object.** They wrote: "(c) is a prime ideal by assumption, so
it's a proper ideal of R, meaning **(c) can't be a unit**." The subject of the
last clause is the ideal, not the element — and an ideal is a set, so "is a
unit" is not a question about it at all. The clause is empty rather than false,
and 3.14 needs a statement about c.
`handwritten/20260908-3.14-attempt7-not-a-unit-wrong-object.png`.

**This is the same failure as card 0085, where the last line landed in R instead
of in (a): they reach the final clause and attach it to the nearest object
rather than the one the theorem is about.** Fourth appearance of the
stop-one-clause-short family. Card 0111 put c and (c) side by side in a table —
element versus set, "is a unit" versus "= R" — pointed at the 3.11 biconditional
read right to left, said everything before the clause stands, and asked only for
the clause rewritten about c with the hinge named.

When that lands, **3.14 is complete** — assemble it from three pieces into the
empty region (`board hw` shows 03.14 EMPTY): the forward direction and its
properness line from rev 6, the reverse direction from rev 5 with a → c, and the
not-a-unit line from rev 7 once repaired.

The route card 0104 expected instead — x ↦ ax injective by cancellation, hence
surjective by finiteness, so e is in the image — is not the one they took. Do
not push them onto it; theirs works.

## 3.2 — skipped 2026-09-08 10:30, second time

**Skip means *not now*, and this is a homework sheet, so it is still owed.** Do
not press and do not remark on it; come back once the rest of the sheet is done.
Card 0103 posed it in full (R an integral domain with field of fractions F;
show the field of fractions of R[x₁,…,xₙ] is naturally F(x₁,…,xₙ)) with its
definition list and the option to take n = 1 first. They skipped within ninety
seconds of it landing.

That is now two skips on 3.2 — 2026-09-02 with "I have lost patience", and this
one. It is the only problem on the sheet they have refused twice, and the empty
solution region is what remembers it.

**They were most of the way through it on 2026-09-02.** What they had then, from
cards 0020–0031:
elements of F are classes of pairs, not pairs; the miniature instance p = x + 2,
q = 2x; that the move is to find a *different representative* rather than to
form ab⁻¹; d = b₁b₂ for two denominators, and that it never needs cancellation.
Where they stopped: card 0031 explained what "dα ∈ R[x]" is actually asking and
they never answered it. **That is the rung to return to if they stall** —
clearing denominators for an arbitrary α ∈ F[x].

## The rest of the sheet

`board hw` order, **6 of 12 written up**: 3.2, 3.14, 3.15, 3.17, 3.25,
3.26 still to write up. 3.14's statement is transcribed and its region is
empty, pending the one line card 0109 asked for.

- **3.15, 3.17, 3.25, 3.26** — statements not yet transcribed (`\todo`
  placeholders in the .tex). The statements are in
  `reading/ch03.txt`, under the section-end **Exercises** headings — grep the
  number. `handwritten/20260902-exercise-list.png` is only the list of assigned
  numbers, not the statements; it also carries their own annotations, "worth
  trouble" under 3.12 and a circle round 3.3.
- **3.2** — still owed, skipped twice. Come back to it unremarked.
- **3.8** — the infinite-K monomorphism half is still open (skipped 2026-09-06).
- **3.11** — one closing line never asked: the divisibility contrapositive ends
  at "not an integral domain" and never says "contrary to assumption, so a is
  prime". Noted in a comment in the solution region.

Their rev-8 line "'part of β' and 'part of γ' can't form α because α is
irreducible" is true and does no work in (c). Flagged as such rather than
pursued.

**New this session:** the ladder was unnecessary. When they stall and then get a
concrete handle (φ, here), they can run the whole argument. Do not assume a
stall means the next question must be smaller — it may mean the wrong tool was
in their hand.

Garling (p. 362) defines prime only for **non-zero** a, and 3.11 needs that:
R/(0) ≅ R is a domain while 0 is not prime.

## This student

Concrete lands; general lands only off **two instances that disagree** — one is
never enough, and they will promote a single instance to a theorem (ℤ's ±1
became "the only units in any R[x]"). The ℚ/ℤ pair for (2) is the current
instance of that pattern and it worked.

They answer the first half of a two-part ask and drop the second. Ask one thing.

**They prove the substantive clause of a definition and drop its side
conditions.** Three instances now: *non-zero* absent from all of 3.3, *not a
unit* and *proper* absent from all of 3.14, and the repeated failure to name the
last line a contradiction. When a definition is a conjunction, expect only the
interesting conjunct and ask for the other one by name.

They revise one page in place and often **fix the wrong end** — say which end.

**They will skip pure algebra grind, in writing, mid-page, and they are right
to.** Grant it and take the computation over. But check what they asked you to
assume before you assume it — on 2026-09-07 the skip came attached to a false
line, and letting it stand would have poisoned all of 3.12.

Pencilled questions get answered first, in their own card; their questions beat
their attempts. **"I'm stuck" is unreliable when a page comes with it** — read
the working. With no page it is real, and on 2026-09-07 it was followed twenty
minutes later by the correct answer with no further prompting. Their
handwritten | and ∤ are near-identical: check against the argument, not the ink.
Their set notation runs loose ("q ∈ ℚ ∉ ℤ") — read the intent, do not spend a
turn on it.
