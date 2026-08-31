# Handoff — 31 August 2026

Read this before the first card of the next session. The contract says so, and this file is the
only continuity there is.

## What this session was

Not a lesson. No board, no cards, no teaching. It was a repair sitting on the sixteen lesson
exercise notebooks, start to finish, and it is finished and pushed (`3890a83`).

## Where the work stands

**Lessons 00–17 — done.** All sixteen exercise notebooks are complete and printed:

- Built from Dr. Doty's own question cells, copied out of `material/` unchanged — his Exercises
  header, his name/class block, his preamble cells, every numbered question in his order and his
  numbering, Lesson 11's two exercises numbered 14 included.
- 538 input cells, all 525 of the originals unchanged.
- 56 written explanations, one per exercise that asks for one, short, at the end of that exercise.
- Zero output cells. That is the submission format and it is not negotiable — see below.
- PDFs in `lessons/lesson-NN/build/`. The owner downloaded copies from the repo root and deleted
  them; do not leave build artefacts at the root.

**Chapters (Beltrami) — not started, and that is fine.** All seven `chNN-homework.tex` files are
still the 37-line scaffold with a `PENDING` marker, and every `handwritten/` is empty. Nothing has
been assigned into them; the syllabus promises a schedule it does not contain. The owner said on
31 August 2026: *"don't worry about the textbook — honestly we probably don't even need it."*
Treat that track as dormant unless he reopens it. If he does, it needs one of two things from him
and neither is yours to invent: which Beltrami problems are assigned, or handwritten pages to
transcribe.

## The one fact that will trip you up

**Submissions are code only, no output cells.** Dr. Doty said so in class; the owner confirmed it
directly. The notebooks read the other way — Lesson 1 Exercise 2 says "Cut and Paste the two
Input-Output cell pairs into this notebook", Exercise 3 wants an explanation "below your
Input-Output cells" — and the syllabus is silent. Do not re-derive this from the notebook text and
reach the opposite answer, and do not offer to evaluate the notebooks to "fix" the missing output.
The README records this with its provenance.

## What he got right, and what he corrected me on

- He caught that the printed PDFs had no question text on them at all. He was right, and it had
  been true for sixteen notebooks and two commits.
- He knew the no-output rule cold when I flagged the apparent contradiction. Believe him on course
  logistics; the repo is the thing that is out of date, not him.
- He asked for the prose answers explicitly, which is the exception `AI_INSTRUCTIONS.md` provides
  for, and then told me **not** to mark inside the homework that they were assistant-written. That
  record lives in `lessons/ASSISTANT-NOTES.md` and nowhere else. Honour both halves of that.

## How he works

- Short, direct instructions. He will say "do it" and mean the whole thing — finish and report,
  do not hand back a step and wait.
- He asks a yes/no question when he wants a yes/no answer. "Is lesson 1 done?" wanted "no, and
  here is what is missing", not a survey.
- He will tell you when he has handled something himself (he deleted the root PDFs rather than
  asking me to). Do not re-do it; check first.
- He tracks whether a claim was verified. Verify against a live kernel before asserting behaviour,
  and say plainly when you did not.

## The single next thing

Nothing is pending. The next session starts whatever he opens — most likely a lesson or section
notebook to actually *learn*, since every exercise set is now submitted work rather than something
to be taught. If he opens a chapter, ask which Beltrami problems are assigned before writing a
line of the `.tex`.

## Traps in the tooling, learned the hard way

- `scripts/rebuild-exercises.wls` refuses to run on an already-rebuilt notebook (its Section count
  no longer matches the question count). That guard is deliberate. If you need to re-run it, restore
  the notebooks from git first.
- Do not audit a notebook from a linearised dump. `ToString[..., InputForm]` renders `ColumnForm`
  cells as their formatted column, which made two correct Lesson 5 answers look empty. Cross-check
  against the raw cell text before calling anything missing.
- `make exercises-all` is one kernel start for all sixteen. Never loop it per lesson.
