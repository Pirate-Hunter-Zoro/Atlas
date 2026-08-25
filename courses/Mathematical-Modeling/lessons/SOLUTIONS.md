# Lesson exercises — worked solutions

Every lesson notebook that carries an exercise set now has a worked solution notebook at

```
lessons/lesson-NN/work/Adv Lesson NN Exercises.nb
```

Sixteen notebooks, covering Lessons 01 through 16. Each one is a Wolfram `Notebook[]`
expression: Title, Section headings numbered to match Dr. Doty's exercise numbers, Input cells
holding the answers as typeset box structures, and Text cells holding the written explanations
the exercises ask for. Output cells are deliberately absent — the exercises are submitted with
outputs cleared, and these open ready to evaluate.

## Coverage

| Lesson | Topic | Exercises | Status |
|---|---|---|---|
| 00 | Mathematica interface | none | nothing to do — the notebook has no exercise section |
| 01 | Interface, assignment, functions | 10 | done |
| 02 | Exact and approximate arithmetic | 8 | done |
| 03 | Solve, Plot, D, Integrate, Simplify | 8 | done |
| 04 | Graphics | 16 | done |
| 05 | Lists | 25 | done |
| 06 | Replacement rules and evaluation | 11 | done |
| 07 | Internal form, Boolean tests, attributes | 9 | done |
| 08 | Pattern matching, conditional definitions | 12 | done |
| 09 | Defaults, definition order, tags, attributes | 7 | done |
| 10 | Modules, recursion, procedural programming | 10 | done |
| 11 | Patterns in arguments and rules | 18 | done |
| 12 | Pure functions | 6 | done |
| 13 | Trace and held evaluation | 3 | done |
| 14 | Dynamic interaction, files, strings | 4 | done |
| 15 | Contexts | 6 | done |
| 16 | Packages | 4 | done |
| 17 | Dynamic interaction | none | nothing to do — the notebook has no exercise section |

Lesson 11's original numbering has two exercises numbered 14. The solution notebook keeps the
professor's numbers and continues 15, 16, 17, 18 from the second one, so the last section is
numbered 18 where the source notebook stops at 17.

## Typeset input cells

The Input cells hold real box structures, not linear ASCII. `x^2` is a
superscript, `1/13` is a built fraction, `Sqrt[2]` is a radical sign, and the
palette operator forms the exercises keep asking for are the actual cell
content: `D[f[x], x]` is stored and displayed as the subscripted partial-
derivative operator, `Integrate[f[x], x]` as the integral sign with its
differential, definite integrals with limits on the sign, and `Sum` as a sigma
with its index underneath and limit above. Pi, E and I are the typeset
constants. These are the same box structures the Basic Math Input palette
produces, so the cells look typed rather than transcribed - and they evaluate,
because the boxes *are* the input.

464 of the 525 input cells are typeset. The remaining 61 are deliberate:

- **53 are `?` and `??` information queries.** `?f` is front-end shorthand and
  has to stay exactly that. Converting it would turn it into
  `Information["f", LongForm -> False]`, which is not what the exercise asks
  you to type. There is nothing to typeset in it anyway.
- **8 are the `Manipulate` cells** (Lesson 4 Exercises 14-15, Lesson 14
  Exercises 1-2). `MakeBoxes` renders a `Manipulate` into a live widget rather
  than into input syntax, and a pre-rendered widget is the wrong content for
  an input cell. They stay as ordinary text, which is what you would type.

## Verification

Three separate proofs, all machine-checked, none of them "it looked right":

1. **Every typeset statement is proved equivalent to its source.** The boxes
   are parsed back and must yield the identical held expression, up to a
   normalisation that folds only what the evaluator folds unconditionally
   (`Times`/`Plus` re-association and negative numeric literals). Anything
   that could not be proved was left as literal text rather than converted -
   which is how the `Manipulate` cells ended up as text.
2. **Every cell is proved as a whole**, not just statement by statement, so
   the assembled cell means what the original sequence of statements meant.
3. **Serialisation is verified.** Each finished `.nb` is read back off disk and
   required to be the exact expression that was written.

On top of that, every input cell of the finished notebooks was evaluated
straight from its boxes under Wolfram Engine 15.0.0. All 525 parse; none
fails. The only messages produced anywhere are the four the exercises
deliberately provoke and then ask you to explain:

- Lesson 6, Exercises 1 and 2: `Integrate::ilim`, from destroying the
  integration variable.
- Lesson 7, Exercise 7: `Integrate::ilim`, from `Plot` re-evaluating a held
  integral at every sample point.
- Lesson 9, Exercise 4: `SetDelayed::write`, from trying to add a downvalue to
  `Integrate`.
- Lesson 11, Exercise 7: `Thread::tdlen`, from multiplying a two-element list
  by an empty one.

Three defects were found and fixed by these checks rather than by reading:

- `MakeBoxes` silently absorbs display wrappers - `FullForm`, `TreeForm`,
  `MatrixForm`, `TableForm`, `ColumnForm`, `Style` - rendering what they mean
  instead of representing the call, so the wrapper vanishes from the boxes.
  Those are converted by a separate path that protects the wrapper first.
- `MakeBoxes` sometimes returns a rendered *result* (an `InterpretationBox`
  around a laid-out grid). Such boxes pass a naive round-trip check, because
  the interpretation carries the right expression, but they are wrong for an
  input cell and they do not survive serialisation intact. They are rejected.
- A line break is **not** a statement separator to the box parser - it is
  implicit multiplication, so two definitions on consecutive lines would parse
  as their product. Statements are therefore separated by explicit semicolons.
  Every statement affected was a definition returning `Null`, so nothing that
  displays was changed.

**Not verified from here:** this node has no Mathematica front end, only the
kernel. The notebooks are proved to parse, evaluate and serialise correctly,
but nobody has *looked* at one rendered. Open one before printing sixteen.

## Submission

Output cells are absent by design - the exercises are to be submitted with
outputs cleared. Your name and the course are in the Title cell; there is no
quiz section to fill in.

## Places where the exercise's premise no longer holds

Version 15 does not behave the way the notebooks (written against version 6) assume. Four
divergences are flagged inside the solutions where they arise:

1. **Lesson 7, Exercise 7.** `Attributes[Plot]` no longer lists `HoldAll` — it returns
   `{Protected, ReadProtected}`. Plot still holds its first argument and still localises the
   plot variable, so the observed behaviour the exercise describes is intact, but the documented
   attribute that used to explain it is gone. The solution demonstrates the holding directly
   instead, via the repeated `Integrate::ilim` messages.

2. **Lesson 9, Exercise 2.** The exercise invites you to conclude that interchanging two
   definitions changes the result. It does not. Mathematica sorts a `PatternTest` pattern ahead
   of a bare `Blank`, so the catch-all is demoted to last wherever it is typed, and both versions
   produce the same table. Exercise 3 is the case where order genuinely does decide the answer,
   because there all three tests have the same shape and Mathematica cannot rank them.

3. **Lesson 11, Exercise 16.** The exercise expects `(1/2 + y)^3` to be missed by the rule
   `(x_)^3 -> x^333`. It is not missed in this version — the full form is
   `Power[Plus[Rational[1, 2], y], 3]`, with a literal 3 in the exponent, so it matches.

4. **Lesson 13, Exercise 1.** `Trace` output is far shorter than the exercise's framing suggests,
   because `D` and `Integrate` do their work inside built-in code that `Trace` does not open up.
   What the traces actually show is the canonical reordering of `Plus` arguments and then the
   answer in one step.

Two further traps are recorded that are not version-specific, and that the exercises' own
phrasing walks into:

- **Lesson 11, Exercise 7.** `f[{1, 2}]` does fail, but the pattern match succeeds — the failure
  is in listable multiplication of a two-element list by an empty one.
- **Lesson 15, Exercise 4.** Wrapping the assignment in `Begin`/`End` does *not* create a symbol
  in the new context, because `Global`newSymbol` already exists and is found on the context path
  first. The naive version is shown failing before it is repaired, since that failure is exactly
  what Exercise 6 asks you to explain.

## One deliberate substitution

Lesson 4 Exercise 8 generates random data. `SeedRandom` was added ahead of it so that the data,
the least-squares fit in Exercise 9, and the pictures in Exercises 10 and 11 all refer to the
same twenty points on every re-run. Delete that one line to restore the exercise as written.
