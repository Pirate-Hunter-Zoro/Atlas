# Probability — coursework

Reading, notes, and assigned homework for a graduate probability course following
Sheldon M. Ross, *Introduction to Probability Models* (10th edition), plus the professor's
lecture modules.

> **AI assistants: read [`AI_INSTRUCTIONS.md`](./AI_INSTRUCTIONS.md) in full before doing
> anything.** It is the operating contract for this repository and it is model-agnostic —
> Claude, Codex, DeepSeek/open-code, Cursor, a local model, all the same. Nothing auto-loads it,
> so read it the moment you are pointed at this README. Then read
> [`HANDOFF.md`](./HANDOFF.md) — where the last session got to, what went wrong in it, and what
> comes next. It is the only continuity between sessions, and it is rewritten before each one
> ends.

## Layout

```
textbook/           the full text (tracked — private repo)
chapters.tsv        chapter table — numbers, titles, page ranges. Single source of truth.
latex/
  coursemacros.sty  shared preamble, probability macros
  templates/        notes and homework templates
scripts/
  split-textbook.sh cut the full text into per-chapter excerpts
  scaffold.sh       create chapter / homework folders and .tex files
  build.sh          compile one .tex
chapters/chNN-slug/
  reading/chNN.pdf  this chapter's excerpt, cut by `make split` (tracked)
  lectures/         the professor's module slides for this chapter
  notes/            chNN-notes.tex
  handwritten/      iPad exports — the work as originally written
  build/            compiler output
homework/hwNN/
  assignment/       the assignment sheet as distributed
  hwNN.tex          the typeset solutions
  handwritten/      iPad exports
  build/
```

Homework is numbered by assignment, not by chapter, because the assignments cut across
chapters.

## The rhythm

1. Read the chapter and watch the modules. The assistant teaches one concept at a time, with
   one question per response, and will not dump a summary on you.
2. Work the problems by hand on the board's slate and tap send. No exporting, no airdropping —
   the assistant opens the page you just wrote. Pages worth keeping get copied into the relevant
   `handwritten/`.
3. The assistant reviews the handwritten work and locates the break. A wrong step goes back to
   you unrepaired; nothing is typeset until you both agree it is right.
4. The assistant generates the `.tex` scaffold: every statement transcribed, every solution
   region empty and marked.
5. Once a solution is agreed correct, the assistant transcribes *your* argument into the marked
   region — same steps, same order. You do not retype a proof you already wrote by hand.
6. The assistant compiles and reports. You never run the build yourself.

## Solution markers

Every place your work belongs is fenced like this. It stays empty until you have done the
mathematics by hand and it has been agreed correct; only then does the assistant typeset your
argument into it. No assistant ever invents a solution you have not produced:

```
% ===== SOLUTION 3 =====
% TODO(mferguson): your work goes here.
% ===== END SOLUTION 3 =====
```

## Build

Handled by the assistant. Entry points: `make split`, `make scaffold`, `make scaffold-hw HW=04`,
`make notes CH=03`, `make homework HW=02`, `make all`, `make clean`, `make list`.

## Chapters

| # | Title | PDF pages |
|---|---|---|
| 1 | Introduction to Probability Theory | 19–38 |
| 2 | Random Variables | 39–114 |
| 3 | Conditional Probability and Conditional Expectation | 115–208 |
| 4 | Markov Chains | 209–308 |
| 5 | The Exponential Distribution and the Poisson Process | 309–388 |
| 6 | Continuous-Time Markov Chains | 389–438 |
| 7 | Renewal Theory and Its Applications | 439–514 |
| 8 | Queueing Theory | 515–596 |
| 9 | Reliability Theory | 597–648 |
| 10 | Brownian Motion and Stationary Processes | 649–684 |
| 11 | Simulation | 685–752 |

Lecture modules exist so far for chapters 1–4; homework sets 1–3 are in `homework/`.

## The live board

Lessons are not read in the terminal. The assistant runs `board start` from this repository and
tells you which address to open. This machine gets a `127.0.0.1` one; the iPad, which is not on
the institute network, reaches the same board over **Tailscale**. All of them show the same page
at the same time.

On the iPad, open it once in Safari and use Share → **Add to Home Screen**. After that it is an
app with its own icon, no browser chrome, and a long-press shortcut straight to the slate.

Everything the assistant teaches appears there as typeset mathematics the moment it is written:
real LaTeX, real diagrams, no refresh and no compile step. This course runs the board in **math
mode**, so you answer by hand rather than by typing: the ✎ button opens a slate you write on with
the Apple Pencil, and every question card carries an answer block with a **skip this one** button
that means *move on*. Tap send and the assistant opens the page and reads your handwriting — no
exporting, no airdropping, no retyping a proof you already wrote. You can also write directly on
a card the assistant wrote and send those marks as a question about that line. Turn on *live* and
it sees each page as you pause. Photos and PDFs dropped anywhere on the board work too.

With the board on the iPad and the slate for your working, a whole session can happen without
touching the keyboard.

You never run a board command. The tool is `~/Tutor-Board`; its README explains the rest.

## Git

The remote is `origin`, at
[Pirate-Hunter-Zoro/Probability](https://github.com/Pirate-Hunter-Zoro/Probability), tracked by
`main`. Nothing is committed or pushed automatically.

**The repository is private, and what is tracked depends on it staying that way.** Instructor
material — textbook, excerpts, lecture slides, assignment sheets — is tracked only for that
reason. If it is ever made public, ignore all of it *first* — and purge it from history rather
than merely deleting it, since a file stays reachable in past commits until it is actually
removed.
