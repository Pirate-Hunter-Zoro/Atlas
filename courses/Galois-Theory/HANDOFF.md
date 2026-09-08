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

## Next

**Finish 3.11's last clause: R/(a) a domain ⟹ a is not a unit.** Everything
else in the problem is transcribed; this one line closes it.

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

The card then ladders, since they stalled: compute φ(2 + i√5) and list every
way it factors as a product of two elements of ℕ. Expect 9, and 1·9, 3·3, 9·1.
Next rung after that: φ never takes the value 3, so {3,3} is out and one factor
has φ = 1, hence is a unit. Then re-pose (b) in full.

Watch for the coordinates reflex returning in (c).

3.12's statement is transcribed into the .tex; its solution region is empty.

Then the rest of the chain: (a) = R means the quotient has one class, so
1 = 0 there, and a domain forbids 1 = 0. Then transcribe 3.11 in full and move
to 3.12.

Garling (p. 362) defines prime only for **non-zero** a, and 3.11 needs that:
R/(0) ≅ R is a domain while 0 is not prime.

## This student

Concrete lands; general lands only off **two instances that disagree** — one is
never enough, and they will promote a single instance to a theorem (ℤ's ±1
became "the only units in any R[x]"). The ℚ/ℤ pair for (2) is the current
instance of that pattern and it worked.

They answer the first half of a two-part ask and drop the second. Ask one thing.

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
