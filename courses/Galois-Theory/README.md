# Galois Theory — coursework

Reading, notes, and assigned homework for a graduate course in Galois theory, following
D. J. H. Garling, *A Course in Galois Theory* (Cambridge University Press).

> **AI assistants: read [`AI_INSTRUCTIONS.md`](./AI_INSTRUCTIONS.md) in full before doing
> anything.** It is the operating contract for this repository and it is model-agnostic —
> Claude, Codex, DeepSeek/open-code, Cursor, a local model, all the same. Nothing auto-loads it,
> so read it the moment you are pointed at this README.

## Layout

```
textbook/           the full scanned text (tracked — private repo)
chapters.tsv        chapter table — numbers, titles, page ranges. Single source of truth.
latex/
  coursemacros.sty  shared preamble and Garling-flavoured macros
  templates/        notes and homework templates
scripts/
  split-textbook.sh cut the full text into per-chapter excerpts
  scaffold.sh       create a chapter's folders and .tex files from the templates
chapters/chNN-slug/
  reading/chNN.pdf  this chapter's excerpt, cut by `make split` (tracked)
  notes/            chNN-notes.tex
  homework/         chNN-homework.tex
  handwritten/      iPad exports — the work as originally written
  build/            compiler output
```

## The rhythm

1. Read the chapter. The assistant teaches it one concept at a time, with one question per
   response, and will not dump a summary on you.
2. Work the problems by hand on the iPad. Export the PDF into that chapter's `handwritten/`.
3. The assistant reviews the handwritten work and finds the breaks before anything is typeset.
4. The assistant generates the `.tex` scaffold: every statement transcribed, every solution
   region empty and marked.
5. You type the mathematics into the marked regions.
6. The assistant compiles and reports. You never run the build yourself.

## Solution markers

Every place your work belongs is fenced like this, and no assistant writes inside it:

```
% ===== SOLUTION 4.7 =====
% TODO(mferguson): your work goes here.
% ===== END SOLUTION 4.7 =====
```

## Build

Handled by the assistant. For reference, the entry points are `make split`, `make scaffold`,
`make chapter CH=07`, `make all`, and `make clean`.

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

## Git

The remote is `origin`, at
[Pirate-Hunter-Zoro/Galois-Theory](https://github.com/Pirate-Hunter-Zoro/Galois-Theory), tracked
by `main`. Nothing here is committed or pushed automatically.

**The repository is private, and what is tracked depends on it staying that way.** The textbook
and its excerpts are tracked only for that reason; if it is ever made public, ignore `textbook/`
and `chapters/*/reading/*.pdf` *first* — and purge them from history rather than merely deleting
them, since a file stays reachable in past commits until it is actually removed.
