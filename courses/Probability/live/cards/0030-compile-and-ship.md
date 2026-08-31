---
kind: note
title: Shipped. Not compiled — and Tutor-Board is out of my reach, not broken
---

**Pushed.** This repository is committed and up to date — every solution, the
filed handwriting, the handoff. Nothing is at risk.

**Not compiled, and I want to be exact about why**, because "just compile it" is
the right instinct and it is not what is stopping me. LaTeX is fine:
`board doctor` finds `pdflatex` at `/Library/TeX/texbin/`, and the last real
LaTeX error in this document was zero. The refusal is one layer up — *this
session is not permitted to execute the binary*, and it is equally not permitted
to edit the file that would grant the permission. Both need a human to approve
once, and there is nobody attached to a headless run.

So it is one approval, not a fix. Open Claude Code in this repository
interactively and ask for the build; the prompt appears, you tap once, and it is
allowed from then on. Alternatively the project's local settings file under
`.claude` has a permissions allow list — `pdflatex` needs an entry beside the
`pdftotext` ones already in it.

**Tutor-Board I could not touch at all.** It lives outside this session's
working directory, so I cannot read a line of it, let alone change it or push
it. That needs a session opened with that directory in scope.

Worth saying anyway: no change to Tutor-Board could have fixed this. It cannot
hand a sandboxed process a permission the sandbox withheld — it already detects
the compiler correctly and correctly refuses to fake a PDF. What *is* worth
changing there is that `board hw build` printed the single word `FAILED` all
session while knowing more than that. I will make it say why, in a session that
can see the file.
