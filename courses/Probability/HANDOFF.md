# Handoff

**Last session:** 2026-08-26 evening, a homework sitting on **hw01**
(`homework/hw01/hw01.tex`), Ross ch.1 — axioms of probability. Ended mid-problem,
with a question posed and unanswered.

## The assignment

`homework/hw01/assignment/Prob.Homework1.2026.pdf`, due 2 September 2026:

1. **Problem 1** (instructor's own): prove P(E∪F) = P(E) + P(F) − P(EF) from the axioms.
2. **Ross ch.1 #8** — Bonferroni, P(EF) ≥ P(E) + P(F) − 1.
3. **Ross ch.1 #10** — Boole's inequality.
4. **Ross ch.1 #12** — E before F in a repeated experiment, P(E)/[P(E)+P(F)].
5. **Ross ch.1 #39** — three stores, a woman resigns, Bayes.
6. **Ross ch.1 #41** — rats, black dominant, Bayes with five offspring.

Practice only, explicitly not handed in: ch.1 #4, 5, 6, 7, 17.

All six statements are transcribed into `homework/hw01/hw01.tex` with empty marked
solution regions; it compiles clean (1 page, 0 warnings). **Every solution region is
still empty** — nothing has been agreed correct yet. Those edits are uncommitted in
the working tree.

## Where the student got to

Only **Problem 1**, and it is roughly two-thirds done.

### What they got right — do not teach it again

On the slate (`live/answers/t0001-r2.png`) they drew a labelled Venn diagram and wrote

  P(E∪F) = P((E∩Fᶜ) ∪ (F∩Eᶜ) ∪ (E∩F)) = P(E∩Fᶜ) + P(F∩Eᶜ) + P(E∩F)

annotated "(mutually exclusive)". **They found the disjoint-split manoeuvre unaided**,
and chose the three-piece carve rather than the two-piece one. They understand that
axiom 3 is the only rule that turns a union into a sum and that it needs disjointness.
That idea is theirs now; reuse it freely in #8 and #10 without re-teaching it.

### What is still owed, and what the misunderstanding is

Two things, both named in card 0003:

1. *(minor)* "(mutually exclusive)" is a label, not an argument. They owe one line of
   English per pair. They habitually justify structure by labelling a region rather
   than by saying why — and that sentence is the graded step.
2. *(the real gap)* Their right-hand side is in the wrong currency. P(E) and P(F)
   appear nowhere in it — they have written the probabilities of two slivers of E but
   never of E itself — so no rearrangement of those three terms can reach the target.
   The fix is the manoeuvre they already own, applied to a *smaller* set: split E on
   its own into EF ∪ EFᶜ, get P(EFᶜ) = P(E) − P(EF), same for F, substitute.

They did not get this wrong so much as not see that the same tool applies twice, at
two different scales. Card 0003 asked for the E line in symbols; ten minutes passed
with nothing written, so card 0004 re-taught it concretely — a fair die with
E = {1,2,3,4}, F = {3,4,5,6}, so 4/6 = 2/6 + 2/6 is visibly axiom 3 on a two-piece
carve — and pointed at their own drawing, where the circle E is already cut into the
lens EF and the crescent EFᶜ. **That question is still open and unanswered.**

## The single next thing to teach

Read whatever revision of t0001 arrives and check for exactly one line:
P(E) = P(EF) + P(EFᶜ), rearranged to P(EFᶜ) = P(E) − P(EF). That is the next thing
because everything else in Problem 1 is already on their page, and because it is the
step they have now stalled on twice — nothing after it will land until it does.

If it lands, do not drip-feed further: ask for the F line and the substitution
together, since they have the manoeuvre and splitting it would read as stalling. If it
does not land, go smaller than the die — two named outcomes, not six.

When Problem 1 is agreed, typeset it into the SOLUTION 1 region **in their three-piece
form, not a tidier two-piece one**, file their ink beside it, and build. Then #8:
Bonferroni is Problem 1 rearranged plus P(E∪F) ≤ 1, so it should be quick.

## About this student

- **They work in a diagram first**, then write algebra beside it. The picture is where
  the reasoning actually lives — open the PNG and read the drawing, not just the lines.
- **They ask instead of guessing.** They wrote "Am I on the right track?" in a bubble on
  the slate. Answer the marked question first, in its own card, before assessing the
  working around it.
- **A stall arrives as a resend, not as silence.** When they do not know what to write,
  what comes back is the previous page again. Read that as *the last step did not land*
  and re-teach it from a new angle; do not repeat the same card louder.
- **They send photographs of the iPad screen instead of using Send on the writing
  panel.** Twice (20:06 and 20:23), the second time after being corrected explicitly.
  Assume it recurs. When an upload lands in `live/inbox/uploads/`, compare it against the
  latest `live/answers/t*.png` before treating it as new work — both times it was the
  board itself photographed, with no new ink. Say so in two lines and spend the rest of
  the card teaching; do not burn a turn on the scolding.
