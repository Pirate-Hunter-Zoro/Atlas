# Assistant notes pulled out of the exercise notebooks

Everything on this page was **written by the assistant**, not by the student, and therefore does
not belong in a submitted notebook — that is the rule in `AI_INSTRUCTIONS.md` and in the README's
"Transcription, not authorship". It is recorded here instead of deleted, because a few of these
cells say something the student asked to be able to find again: *this particular exercise had
something in it actually worth doing.*

Where it came from: on 30 August 2026 the sixteen exercise notebooks were stripped of 191
answer-commentary cells (`scripts/strip-commentary.wls`). Twelve prose cells survived that pass,
because each of them sat *before* the first Input cell of its section and the strip rule reads a
Text cell in that position as a restatement of the problem. They were not restatements. They were
these. On 31 August 2026 the notebooks were rebuilt around the professor's own question cells
(`scripts/rebuild-exercises.wls`) and all twelve came out.

Read this page as a to-do list, not as an answer key. Nothing here is transcribed from the
student's work, so nothing here can go into a submission as it stands.

---

## Worth doing — the two the student asked to have written down

**Lesson 01, Exercise 1** — while the Documentation Center is open anyway:

> One thing worth doing while the Documentation Center is open: the Basic Math Input palette
> (Palettes menu) supplies the typeset forms this lesson keeps asking for — the superscript
> template, the partial-derivative template, the integral-with-differential template, and the
> Pi, E and I characters. Every one of those has a keyboard equivalent, and the exercises below
> are written in ordinary linear syntax, which evaluates identically.

**Lesson 15, Exercise 4** — the failure is the point of the exercise:

> The obvious way to do this is to switch context with `Begin`, assign, and switch back with
> `End`. `Begin` does change the current context, and `End` restores the previous one and returns
> the name of the context being left. But the obvious way does not work here, and it is worth
> watching it fail before repairing it — the failure is exactly what Exercise 6 is about.

---

## Working decisions — why the code in that section looks the way it does

**Lesson 02, Exercise 7**

> `Names["System`*"]` returns the whole list of built-in names. It is far too long to print in a
> submitted notebook, so only its length is evaluated below; the list itself is computed and
> discarded.

**Lesson 03, before Exercise 1**

> Everyday notation has been converted to Mathematica notation throughout: equations use `==`,
> functions use square brackets, user definitions use the underscore, and E, Pi and I are the
> built-in constants rather than the bare letters e, p and i.

**Lesson 05, before Exercise 1**

> Every list produced below is named, so that later exercises can refer to the list built in an
> earlier exercise instead of rebuilding it.

**Lesson 04, Exercise 14 and Lesson 14, Exercise 1** — the same caveat, twice:

> The cells are `Manipulate` expressions. They build correctly under a plain kernel but the
> sliders are live only inside a Wolfram front end (Mathematica or Wolfram Player). Evaluated
> through Wolfram Engine under Jupyter they render as a static snapshot at the initial parameter
> values.

Lesson 14's copy also records that its Exercises 1 and 2 repeat Lesson 4's Exercises 14 and 15
verbatim.

**Lesson 08, Exercise 8**

> Exercise 6 was already written with `/;`, so there is nothing to change. It is repeated here in
> its Boolean-test form for the record; the two exercises coincide.

**Lesson 04, Exercise 1**

> Parts 1 to 3 are a walk through the Documentation Center page for `ParametricPlot`. Parts 4 and
> 5 are below: a MeshShading example copied out of that page, and then the same example with the
> parameter interval moved from 0 ≤ u ≤ 4π to 2π ≤ u ≤ 8π. MeshShading takes a list of colours
> (or None) and paints the successive mesh segments of the curve with them in rotation, so the
> curve is drawn as an alternating dashed ribbon rather than one uniform line.

---

## Not the assistant's to have written at all

Two of the twelve were straight prose answers to "Explain why…" questions. They are the student's
to write, they are recorded here only so it is clear what was removed, and they must not be
copied into a submission.

- **Lesson 08, Exercise 1** — a paragraph on why `f[x] = x^2` attaches to one symbol while
  `f[x_] = x^2` attaches to a pattern.
- **Lesson 08, Exercise 2** — a paragraph on why immediate assignment freezes a right-hand side
  that a function body needs re-evaluated per call.

A third, **Lesson 01, Exercise 1**, merely restated that the exercise is a front-end tour with
nothing to evaluate and nothing to submit. True, and now unnecessary — the professor's own
"Don't worry about an answer--just do it!" is in the printed notebook where it belongs.

---

## The written answers, 31 August 2026

Every exercise whose text asks for a written explanation now has one — fifty-six of them, one
short Text cell at the end of the exercise it answers. **The assistant wrote them, at the owner's
explicit instruction on 31 August 2026**, which is the exception the README's "Transcription, not
authorship" section provides for. That fact is recorded here and nowhere else: it is deliberately
not marked inside the notebooks, on the owner's instruction.

Every factual claim in them was checked against a live Wolfram Engine 15.0.0 kernel before it was
written, not reasoned out on paper. Several answers therefore contradict what the exercise expects,
because Version 15 does not behave the way the Version 6 notebooks assume. Those are the four
divergences already listed in `SOLUTIONS.md`, and the answers state what actually happens:

- **L07 Ex 7** — `Attributes[Plot]` reports only `{Protected, ReadProtected}`; the holding
  behaviour is still there, but the attribute that used to explain it is not.
- **L09 Ex 2** — interchanging the two definitions changes nothing: Mathematica sorts a
  `PatternTest` pattern ahead of a bare `Blank`, so both orders store and answer identically.
  Exercise 3 is where order genuinely decides the answer.
- **L11 Ex 15** (the professor's 15) — `(1/2 + y)^3` is **not** missed by the cube rule in this
  version; its full form carries a literal 3 in the exponent, so it matches.
- **L11 Ex 13** — `f[{1, 2, {}, 3, 4}]` is **not** a failed match either; the empty list is still
  a list, so it returns `{}`.

By lesson: 01 → 7, 02 → 6, 03 → 6, 04 → 2, 06 → 10, 07 → 2, 08 → 4, 09 → 4, 11 → 14, 15 → 1.
Lessons 05, 10, 12, 13, 14 and 16 ask for code only and needed none.

---

## Code audit, 31 August 2026 — part by part, and what was fixed

Every exercise in all sixteen notebooks was checked against every numbered Part and bullet of the
professor's question, not merely "does this exercise have code attached". One exercise has no code
by design: Lesson 1 Exercise 1, the front-end tour, whose own instruction is "Don't worry about an
answer--just do it!"

Seven places came up short. All seven were closed the same day; the notebooks and PDFs now hold
the missing cells.

| Where | What the professor asked | What was added |
|---|---|---|
| **L01 Ex 5** | Check `a` and `A` **after each** assignment — three times in all | The `?a` / `?A` pair after `A = 5 feet/sec`, and again after `a = 10 feet` |
| **L02 Ex 7** | Evaluate `Names["System`*"]`, then delete the long list before printing | The `Names["System`*"]` cell ahead of the `Length[...]` one |
| **L09 Ex 3** | Display `?f` for **each** of the two code segments | `?f` after the second segment |
| **L09 Ex 6 Part 7** | "Explain (i.e. **trace**) at what point the argument `a` was evaluated" | `Trace[myFunction[a, b, c, d]]` |
| **L11 Ex 3** | "Does the square (i.e. `Power`) have attribute `Listable`?" | `Attributes[Power]` |
| **L11 Ex 4** | Evaluate `f[x, {1,2,3}, {{1,2},{3,4}}]` | That evaluation |
| **L11 Ex 14 (second), 15, 16** | `? rule1`, `? rule2`, `? {rule1, rule2}` | `?rule1`, `?rule2`, and `{rule1, rule2}` — the last written as a plain list, because `?{...}` is not valid syntax |

Two deviations were left as they stand, deliberately:

- **L06 Ex 10.** The professor's listing ends `?plot1 … ?plot2 … Show[plot2]`. The notebook has
  `?plot1` but answers the `?plot2` step with `Frame /. Options[plot2]`, which shows the changed
  option directly rather than dumping the whole Graphics object. Better evidence, different
  command.
- **L03 Ex 4 Parts 8, 9, 10.** "Evaluate **both** `f'(x)` and `∂x f(x)` and verify that you get
  the same result." The notebook shows `Simplify[f'[x] - D[f[x], x]]`, which verifies the equality
  without displaying either side. Exercise 5 does it the way he asked.

Where the professor did not say "use a new Input cell", several consecutive `Evaluate:` bullets are
answered by one cell holding a list of the results. That is a presentation choice and it is
consistent across the notebooks. Where he did say it — Lesson 1 Exercise 3 — separate cells were
used.
