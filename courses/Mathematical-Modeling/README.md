# Advanced Mathematical Modeling — coursework

MATH 7013/5013 (Dr. Dale Doty). Two tracks running in parallel:

- **Lessons 00–17** — Mathematica programming: lists, functional style, recursion, pattern
  matching, arbitrary precision, graphics, efficiency, dynamics, presentations.
- **Section notebooks** — the "New Sect X.Y" series, grouped by Dr. Doty's chapter numbering.

**There is a textbook, and it is now in `textbook/`.** The syllabus assigns Beltrami,
*Mathematics for Dynamic Modeling* (Academic Press, 1987; the syllabus cites ISBN
9780120855667, a later printing of the same book). An earlier version of this README claimed no
textbook existed. That was wrong, and the syllabus was sitting in `syllabus/` saying otherwise
the whole time.

It governs the **chapters** track only. Dr. Doty's "New Sect X.Y" notebooks follow Beltrami's
chapter and section numbering, so the book is the reference the notebooks were written against.
The **lessons** track is Mathematica programming and owes the book nothing.

In practice the notebooks are still the material — everything submitted comes out of them. The
book is there for when a notebook assumes a derivation it does not show.

> **AI assistants: read [`AI_INSTRUCTIONS.md`](./AI_INSTRUCTIONS.md) in full before doing
> anything.** It is the operating contract for this repository and it is model-agnostic —
> Claude, Codex, DeepSeek/open-code, Cursor, a local model, all the same. Nothing auto-loads it,
> so read it the moment you are pointed at this README.
>
> Mathematica code counts as code. In normal mode you describe what to evaluate in English and
> name the built-in functions; the user types every line of it.

## Layout

```
units.tsv           unit table — lessons and chapters. Single source of truth.
syllabus/           the course syllabus
textbook/           Beltrami, Mathematics for Dynamic Modeling — the assigned text
course-materials/   inbox for new instructor notebooks; scaffold.sh files them
latex/
  coursemacros.sty  shared preamble, dynamical-systems macros
  templates/        notes and homework templates
scripts/
  scaffold.sh       create unit folders, file notebooks, generate .tex
  exercises.sh      print a lesson's exercise notebook for submission
  nb2pdf.wls          ... through Wolfram, when the Engine is activated
  nb2tex.py           ... through LaTeX, when it is not
  build.sh          compile one .tex
lessons/lesson-NN/
  material/         "Adv Lesson NN.nb" as distributed
  work/             your own notebooks
  notes/            lesson-NN-notes.tex
  handwritten/      iPad exports
  build/
chapters/chNN-slug/
  material/         "New Sect X.Y" notebooks as distributed
  notes/            chNN-notes.tex
  homework/         chNN-homework.tex — the exercise notebook, typeset
  handwritten/      iPad exports
  build/
```

New notebooks from the professor go into `course-materials/`; the next `make scaffold` files
them into the right unit.

## Where the titles come from

Chapter and lesson titles in `units.tsv` are read off the section headings inside the notebooks.
Lessons are titled by number: their notebooks carry no title cell, and inventing one would be
worse than a number.

Those chapter titles are Dr. Doty's, not Beltrami's, and they are **not** the same strings. Now
that the book is here, both are known and they can be compared. Unresolved on purpose: renaming
the `units.tsv` titles to Beltrami's would leave the already-generated `.tex` files carrying the
old ones, and `scaffold.sh` never overwrites an existing `.tex`. Changing them is a decision, not
a cleanup.

| repo | `units.tsv` title | Beltrami chapter | notebooks present |
|---|---|---|---|
| `ch01` | Simple dynamic models | 1. Simple Dynamic Models | 1.1, 1.2, 1.3, 1.4 Exercises |
| `ch02` | Ordinary differential equations | 2. Stable and Unstable Motion, I | 2.1, 2.2, 2.3, 2.4 Exercises |
| `ch03` | Stability and linearization | 3. Stable and Unstable Motion, II | 3.1–3.2, 3.3, 3.4, 3.5 Derive, 3.5 Exercises |
| — | — | 4. Growth and Decay | none |
| `ch05` | Flux and conservation models | 5. Motion in Time and Space | 5.1, 5.2, 5.3, 5.4 (×2), 5.6, 5.8 Exercises |
| `ch06` | Limit cycles and parameters | 6. Cycles and Bifurcation | 6.1, 6.3, 6.5 Exercises |
| `ch07` | Gradient systems | 7. Bifurcation and Catastrophe | 7.1, 7.2, 7.5 Exercises |
| `ch08` | Chaos and attractors | 8. Chaos | 8.1 |
| — | — | 9. There Is a Better Way | none |

Chapters 4 and 9 have no notebooks and therefore no folders.

Section numbering lines up with Beltrami exactly in chapters 5, 6 and 7 — including the exercise
notebook landing on Beltrami's own exercise-section number (5.8, 6.5, 7.5). It does not line up
in chapters 1, 2 and 3, where the exercise notebook sits one number below Beltrami's exercise
section, and chapter 3 has a 3.4 and a 3.5 that Beltrami's chapter 3 does not have. Recorded, not
explained.

## The rhythm

1. Work the lesson or section notebook. The assistant teaches one concept at a time and will
   not hand you Mathematica code in normal mode.
2. Do the exercises — by hand on the iPad into `handwritten/`, in Mathematica into `work/`.
3. The assistant reviews both and reports what it finds.
4. The assistant writes the `.tex` and transcribes your solutions into it.
5. The assistant compiles and reports.

You do not type up mathematics. That is clerical work and it belongs to the assistant.

## Transcription, not authorship

The assistant typesets **your** mathematics. It does not write its own and put your name on it.
Everything in a solution region comes off a page you uploaded, in your order, in your notation,
including your mistakes — errors get reported to you in conversation, never silently repaired in
the document. Illegible handwriting gets a question, never a plausible guess.

Presentation is the assistant's call: line breaks, alignment, which environment, delimiter
sizing, how a hand-drawn diagram becomes tikz. Content is yours.

If you have not uploaded work for a problem, its region stays empty and marked pending. No
upload, no mathematics. To have the assistant actually solve something, ask for that explicitly
— it will say so in its response and in the region's marker, so the document never blurs whose
work is whose.

## Solution markers

```
% ===== SOLUTION 3 — transcribed from handwritten/ch03-homework.pdf p.2 =====
% ===== END SOLUTION 3 =====
```

The provenance stamp names the page a region came from, so re-transcribing is repeatable and it
stays obvious which upload each answer is set from.

## Build

Handled by the assistant. Entry points: `make scaffold`, `make lesson N=07`,
`make exercises N=01`, `make notes CH=03`, `make homework CH=03`, `make all`, `make clean`,
`make list`.

### Printing a notebook for submission

```
make exercises N=01      one lesson
make exercises-all       every lesson that has an exercise notebook
```

The submission format for this course is a printed notebook with **the output cleared**, not a
`.nb` file. `scripts/exercises.sh` produces one, by whichever of two routes the machine can
actually manage:

| | `scripts/nb2pdf.wls` | `scripts/nb2tex.py` |
|---|---|---|
| Needs | an **activated** Wolfram Engine | nothing but `pdflatex` |
| Produces | a real Mathematica printout — the notebook's own styles, `1/13` drawn as a built-up fraction | a LaTeX document with the same content, 2-D forms written linearly (`D[f[x], x]`, `Integrate[f[x], x]`) |
| When | the normal case | a machine where the Engine has not been activated yet |

Wolfram is tried first and LaTeX is the fallback, decided by whether the run **succeeds** rather
than by asking about the licence — asking costs a kernel start, which is most of the total time.
Every notebook goes to one `wolframscript` invocation for the same reason: the kernel takes the
better part of a minute to start, so sixteen separate runs cost sixteen startups and one costs
one.

Both routes drop output cells, always. The exercise notebooks currently hold none, so today that
changes nothing — but the moment one is evaluated it would, and a submission that quietly starts
carrying output is the failure worth preventing in advance.

Neither route writes mathematics. Input cells are transcribed and never authored; every
character came out of the `.nb`.

## Tooling — what we used and how we got it

Everything below was installed **without root**, into the home directory, on the Laureate
compute node `compute301` (RHEL 9, x86-64, glibc 2.34, 96 cores, 1 TB RAM).

### Mathematica 15.0.1 desktop — tried, abandoned, removed

Downloaded from the TU site-license entitlement at `account.wolfram.com`. The download link is
session-gated: the `account.wolfram.com/dl/...` URL redirects to a sign-in page, so the working
approach was to start the download in a browser, cancel it, and copy the real
`files.wolframcdn.com` URL (with its signature token) out of the browser's download list. That
URL fetches fine from the node.

The installer is a makeself archive that accepts a target directory and an executables
directory, so it installs under `$HOME` with no root at all. That part worked: 8.9 GB installed,
kernel started, reported its MathID.

**Activation is what killed it.** The kernel's automatic Web Activation silently falls through to
the manual prompt, and self-service manual activation in the Wolfram account portal returns
"We are unable to generate a password with the information provided." Both point at the same
cause: TU's site license does not permit end-user self-activation — the password has to come
from a site administrator (Chuck Mason, Jonathan Oxton, or Dale Doty, who is also the
instructor). See `WOLFRAM-LICENSE.md` for keys, MathID, and the drafted request.

Worth recording because it was diagnosed wrong once: this is **not** a network problem. An
earlier guess blamed a blocked `activate.wolfram.com`, but that hostname does not exist anywhere
— public DNS returns NXDOMAIN. Every real Wolfram host resolves and answers from this node.

The install and its 2.5 GB installer were deleted afterwards, reclaiming 11.4 GB.

### On the Mac

`brew install --cask wolfram-engine` — the same 15.0.0, no extraction games, no root argument to
have. Two things then differ from the node and both are recorded in `WOLFRAM-LICENSE.md`: the
cask links the *Player's* `wolframscript`, which cannot find the Engine's kernel until
`wolframscript -configure WOLFRAMSCRIPT_KERNELPATH=...` is run once; and the Engine still has to
be **activated on this machine**, interactively, in a real terminal. That activation has not
happened yet. LaTeX is MacTeX at `/Library/TeX/texbin`; `latexmk` is absent, and `build.sh`
already falls back to a plain `pdflatex` loop when it is, so nothing needed changing.

### Wolfram Engine 15.0.0 — what we actually use, and it works

Free, and **activated**. Verified on this node: `2+2` returns 4, `$LicenseType` reports
`Professional`, `$Version` is 15.0.0 for Linux x86-64, and `Export` of a `Plot` produces a valid
PNG. Graphics render, which is the part that matters for the section notebooks.

Obtained the same way as Mathematica — sign in at `wolfram.com/engine`, start the Linux
download, cancel it, copy the real CDN URL out of the browser's download list. 2.15 GB.

**The installer refuses to run without root**, unlike Mathematica's. The root requirement is
only for system-wide desktop and MIME integration, useless on a headless node. The payload is
three `.tar.xz` archives (`Core`, `FunctionInformation`, `Paclets`) inside a makeself wrapper,
so it was extracted with makeself's `--target` option and the archives untarred directly into
`~/WolframEngine/15.0` — exactly what the installer does with them. 7.2 GB installed.

**Activation used a personal Wolfram ID, deliberately.** The free Engine entitlement has nothing
to do with TU's site licence; it attaches to whichever Wolfram ID claims it. Binding it to a
university address that dies at graduation would be self-defeating, so it was claimed on a
personal Gmail account through `wolfram.com/engine/free-license` in a private browser window —
private specifically so it would not silently attach to the signed-in school ID.

Activation itself is interactive: run `wolframscript` and it prompts for the Wolfram ID and
password, once. It must be run from a **real terminal**; Claude Code's `!` bash mode does not
provide an interactive TTY, so both prompts receive empty input and it fails instantly with
"Incorrect username or password", which looks like a credential error and is not one.

The licence record it writes is `~/.WolframEngine/Licensing/mathpass`. **That file contains a
password — it is not reproduced here and should not be committed anywhere.** One field in it
reads `20261003`, which has the shape of an expiry date of 3 October 2026. Wolfram's FAQ says
the authentication does not expire; that field suggests otherwise. Unresolved — if the Engine
stops working around then, this is the first thing to check.

### What ended up on PATH

`~/bin` is already on the PATH and now holds symlinks to the Engine binaries:

| link | target |
|---|---|
| `wolframscript` | `WolframEngine/15.0/SystemFiles/Kernel/Binaries/Linux-x86-64/wolframscript` |
| `WolframKernel`, `wolfram`, `math`, `WolframPlayer` | `WolframEngine/15.0/Executables/…` |

`wolframscript` is worth noting: it is **not** in `Executables/` where the other binaries live,
it is buried under `SystemFiles/Kernel/Binaries/Linux-x86-64/`. Nothing puts it on the PATH for
you when the installer has not been run as root.

`WolframPlayer` shipping inside the Engine bundle was unexpected — it means a genuine Wolfram
front end may be available, with working `Manipulate` sliders for Dr. Doty's lessons, without a
separate Player download. It is a GUI application, so it needs X11 forwarding to be usable from
a headless node. Untested so far.

### Jupyter as the front end

Wolfram Engine is a kernel with no notebook interface. `WolframLanguageForJupyter` — Wolfram's
own Jupyter kernel — supplies one.

What you get: cell output, typeset results, and inline graphics (`Plot`, `ContourPlot`,
`StreamPlot`, `Graphics3D` all render as images). What you do not get: `Manipulate`, `Animate`
and `Dynamic` are not interactive outside Wolfram's own front end — a `Manipulate` renders as a
static snapshot and 3D plots cannot be rotated.

### Alternatives considered

| Option | Verdict |
|---|---|
| Mathematica Online | Entitled through the site license, 55,000 cloud credits, no activation, full interactivity, saves real `.nb` files. Rejected only because the free local stack was preferred — still the best fallback. |
| Wolfram Player | Free, no activation, runs Dr. Doty's lesson notebooks *with* working `Manipulate` sliders, but cannot evaluate anything you type. Useful alongside Jupyter for reading the lessons. |
| Wolfram Engine + Jupyter | Chosen. Free, local, evaluates and plots. |
| Engine + Player combined | Impossible. Player's front end refuses to evaluate by design and cannot be pointed at another kernel; Engine has no front end. Two halves that do not mate. |

Submission format made this workable: printed notebooks with output cleared, not `.nb` files.
The only cost is cosmetic — a printed Jupyter notebook does not look like a Mathematica notebook.

### LaTeX

TinyTeX, already present at `~/.TinyTeX`. Missing packages were added with `tlmgr`
(`fancyhdr`, `mathtools`, `stmaryrd`, `tikz-cd`; `tlmgr` itself needed a self-update first).

`latexmk` is broken on this node — the system perl has no `Time::HiRes` — so `scripts/build.sh`
detects that and falls back to running `pdflatex` twice, three times when the log asks for it.

## The live board

Lessons are not read in the terminal. The assistant runs `board start` from this repository and
tells you which address to open. This machine gets a `127.0.0.1` one; the iPad, which is not on
the institute network, reaches the same board over **Tailscale**. All of them show the same page
at the same time.

On the iPad, open it once in Safari and use Share → **Add to Home Screen**. After that it is an
app with its own icon, no browser chrome, and a long-press shortcut straight to the slate.

Everything the assistant teaches appears there as typeset mathematics the moment it is written:
real LaTeX, real subgroup lattices and commutative diagrams, no refresh and no compile step. You
answer in the terminal, in the box at the bottom of the board, or by hand: the ✎ button opens a
slate you write on with the Apple Pencil. Tap send and the assistant opens the page and reads
your handwriting — no exporting, no airdropping, no retyping a proof you already wrote. Turn on
*live* and it sees each page as you pause. Photos and PDFs dropped anywhere on the board work
too.

With the board on the iPad and the slate for your working, a whole session can happen without
touching the keyboard.

You never run a board command. The tool is `~/Tutor-Board`; its README explains the rest.

## Git

The remote is `origin`, at
[Pirate-Hunter-Zoro/Mathematical-Modeling](https://github.com/Pirate-Hunter-Zoro/Mathematical-Modeling),
tracked by `main`. Nothing is committed or pushed automatically.

**The repository is private, and what is tracked depends on it staying that way.** The
instructor's notebooks and the syllabus are tracked only for that reason. If it is ever made
public, ignore them *first* — and purge them from history rather than merely deleting them, since
a file stays reachable in past commits until it is actually removed.

**The textbook scan is tracked**, and that decision has since been taken deliberately rather
than left in the third state this section used to warn about. It is safe only while this
repository stays private: the Beltrami scan is a copyrighted 1987 Academic Press book, and a
public repo carrying it is a takedown waiting to happen. It is also in the history now, so
making the repo public means purging it, not deleting it.

The board's `live/` directory is the other thing worth knowing about. It is no longer a blanket
ignore: the lesson transcript — `live/cards/`, `live/turns.jsonl`, `live/state.json`,
`live/slate/`, `live/answers/`, `live/archive/`, `live/inbox/`, `live/text/` — is tracked, so a
session started on one machine is the same session when the other picks it up. Only the
per-machine runtime stays ignored (`.board.json`, `agent.json`, `board.log`, the figure cache and
exports). This matches Probability and Galois-Theory exactly.
