# Galois Theory — coursework

Reading, notes, and assigned homework for a graduate course in Galois theory, following
D. J. H. Garling, *A Course in Galois Theory* (Cambridge University Press).

> **AI assistants: read [`AI_INSTRUCTIONS.md`](./AI_INSTRUCTIONS.md) in full before doing
> anything.** It is the operating contract for this repository and it is model-agnostic —
> Claude, Codex, DeepSeek/open-code, Cursor, a local model, all the same. Nothing auto-loads it,
> so read it the moment you are pointed at this README.

## Layout

```
HANDOFF.md          what the last session left for the next one — read first
PLAN.md             the order of work: which exercises are open, and in which order
DIRECTION.md        what this workspace is for, in the student's own words. Outranks the plan
textbook/           the set text, read from disk and never tracked — see Git below
chapters.tsv        chapter table — numbers, titles, page ranges. Single source of truth.
latex/
  coursemacros.sty  shared preamble and Garling-flavoured macros
  templates/        notes and homework templates
scripts/
  split-textbook.sh cut the full text into per-chapter excerpts
  scaffold.sh       create a chapter's folders and .tex files from the templates
chapters/chNN-slug/
  reading/chNN.pdf  this chapter's excerpt, cut by `make split` — derived, not tracked
  notes/            chNN-notes.tex
  homework/         chNN-homework.tex, and handwritten/ beside it — the ink for each
                    answer, filed under the .tex it belongs to
  build/            compiler output
homework/slug/      a write-up belonging to no chapter — the worksheet — laid out the
                    same way: slug.tex, handwritten/, build/
```

## The rhythm

1. Read the chapter. The assistant teaches it one concept at a time, with one question per
   response, and will not dump a summary on you.
2. Work the problem by hand on the board's slate and tap **send**. Nothing to export, nothing to
   airdrop — your ink lands in the lesson under the question it answers.
3. The assistant opens the page, reads it, and locates the break rather than repairing it. Your
   working comes back under your pen and the same block updates in place.
4. The assistant generates the `.tex` scaffold: every statement transcribed, every solution
   region empty and marked.
5. Once an answer is agreed correct, the assistant typesets *your* argument into its region —
   same steps, same order — and files the handwriting beside it in that chapter's `handwritten/`.
6. The assistant compiles and reports. You never run the build yourself.

Sessions end without warning, so the assistant leaves `HANDOFF.md` at the root: where you got to,
what is owed, and what comes next. It is read at the start of the next session, and it is the only
continuity there is.

## Solution markers

Every place your work belongs is fenced like this, and no assistant writes inside it:

```
% ===== SOLUTION 4.7 =====
% TODO(mferguson): your work goes here.
% ===== END SOLUTION 4.7 =====
```

**One `problem` environment per lettered part, and every opener matched by a closer with the
same label.** `board hw status` pairs the markers to say what is written up and what is next, so
a part folded into its parent's statement is invisible to it and an unmatched opener swallows
every region below it.

## Build

Handled by the assistant. `make split`, `make scaffold`, `make chapter CH=07`, `make all` and
`make clean` cover the chapters. A worksheet is not a chapter and `make` does not reach it:
`board hw list` names every set, `board hw use <name>` pins the sitting to one, and
`board hw build` compiles it.

## Chapters

| # | Title | PDF pages |
|---|---|---|
| 1 | Groups, fields and vector spaces | 12–22 |
| 2 | The axiom of choice, and Zorn's lemma | 23–26 |
| 3 | Rings | 27–45 |
| 4 | Field extensions | 48–57 |
| 5 | Tests for irreducibility | 58–62 |
| 6 | Ruler-and-compass constructions | 63–67 |
| 7 | Splitting fields | 68–79 |
| 8 | The algebraic closure of a field | 80–86 |
| 9 | Normal extensions | 87–90 |
| 10 | Separability | 91–99 |
| 11 | Automorphisms and fixed fields | 100–109 |
| 12 | Finite fields | 110–115 |
| 13 | The theorem of the primitive element | 116–118 |
| 14 | Cubics and quartics | 119–126 |
| 15 | Roots of unity | 127–131 |
| 16 | Cyclic extensions | 132–139 |
| 17 | Solution by radicals | 140–147 |
| 18 | Transcendental elements and algebraic independence | 148–155 |
| 19 | Some further topics | 156–163 |
| 20 | The calculation of Galois groups | 164–171 |

Chapters 1–3 are Part 1, the algebraic preliminaries. Chapters 4–20 are Part 2, the theory
proper.

## The live board

Lessons are not read in the terminal. The assistant runs `board start` from this repository and
tells you which address to open. This machine gets a `127.0.0.1` one; the iPad, which is not on
the institute network, reaches the same board over **Tailscale**. All of them show the same page
at the same time.

On the iPad, open it once in Safari and use Share → **Add to Home Screen**. After that it is an
app with its own icon, no browser chrome, and a long-press shortcut straight to the slate.

Everything the assistant teaches appears there as typeset mathematics the moment it is written:
real LaTeX, real subgroup lattices and commutative diagrams, no refresh and no compile step. You
answer by hand — this course is in **math mode**, so there is no text box and never will be. The ✎
button opens a slate you write on with the Apple Pencil, and it opens itself whenever a question is
owed. Tap send and the assistant opens the page and reads
your handwriting — no exporting, no airdropping, no retyping a proof you already wrote. Turn on
*live* and it sees each page as you pause. Photos and PDFs dropped anywhere on the board work
too.

With the board on the iPad and the slate for your working, a whole session can happen without
touching the keyboard.

You never run a board command. The tool is `board/` at the root of Atlas, on the path as
`board`; `board/README.md` explains the rest.

## Git

This course is a directory in [Pirate-Hunter-Zoro/Atlas](https://github.com/Pirate-Hunter-Zoro/Atlas),
tracked by `main`, and it is not its own clone. Nothing here is committed or pushed
automatically; `scripts/save-and-push.sh` is what the board's save button runs.

**That repository is PUBLIC.** Garling's text and the excerpts cut from it are somebody else's
copyright, so they live on disk and out of git: the root `.gitignore` refuses `**/textbook/*.pdf`
and `**/chapters/*/reading/ch*.pdf`, and `board/test/tracked.py` fails the suite if one is ever
added anyway. What is tracked is everything written *about* the reading — the notes, the
homework, the typeset answers, `chapters.tsv`. `make split` regenerates the excerpts from the
book in one command, so nothing is lost by their absence.
