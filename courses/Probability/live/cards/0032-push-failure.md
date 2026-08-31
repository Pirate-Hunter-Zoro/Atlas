---
kind: note
title: Two machines compiled the same file. Neither will yield
---

**The error is a rejected non-fast-forward.** This clone is 5 commits ahead of
`origin/main` and 1 behind it. Git refuses a push that would drop that one.

The commit you are behind is `32302b7`, *"Homework 1 compiled: all six problems
typeset"* — the compute node's build. It touches three files and only three:
`hw01.aux`, `hw01.log`, `hw01.pdf`.

`hw01.tex` is **byte-identical on both sides.** No mathematics is in conflict.
Two machines compiled the same source and committed two different PDFs of it,
and a PDF embeds a timestamp, so they differ even when the document does not.

**Why it will not clear on its own:** `scripts/save-and-push.sh` — the thing
behind the Push button — commits, then pushes, and never fetches. It has no step
that integrates the other side. So once any other machine pushes, every push
from here is rejected, permanently, and re-tapping cannot help. That is the bug,
and it is in the script rather than in your repository.

I am fixing the script: fetch, merge the remote in before pushing, and where the
only conflicts are generated build files, keep this clone's freshly built copy —
the one I verified at 4 pages and zero warnings. Anything conflicting outside a
`build/` directory stops and reports instead. A script must never silently pick
a winner between two versions of your work.

No rebase, no force, nothing rewritten.

**Done — it pushed.** The merge hit exactly the two conflicts predicted,
`hw01.log` and `hw01.pdf`, resolved both to this machine's build, and went up
clean. `main` and `origin/main` are level. The PDF is still 4 pages and the log
has no conflict markers in it. The compute node's commit is in the history, not
discarded.

---

**Your move.** Those artifacts are tracked, which is *why* two machines fight
over them. I can stop tracking `homework/*/build/` — the conflict stops
recurring, and the PDF stops appearing on GitHub, so you would rebuild rather
than download it.

Keep the PDF in the repository, or stop tracking it?
