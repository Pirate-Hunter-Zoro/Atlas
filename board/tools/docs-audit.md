# The documents are audited against the code they describe

A document that lies costs more than one that is missing, because a missing one
sends somebody to the code. Nothing else in this tree asks whether a sentence
about the code is still TRUE: `test/tracked.py` audits what git carries and
`test/teaching.py` audits where a rule is written down. Neither reads a claim
and then goes and checks it.

**This is a job specification, not a program.** It names no assistant and no
orchestration API, because the thing worth keeping is the decomposition and the
discipline, not one vendor's spelling of `spawn`. Any assistant that can run
several readers and collect structured results can execute it; one reader doing
the surfaces in sequence gets the same answer and takes longer.

## Why it is many readers and not one

The checkable surface is about eight thousand lines of core documentation plus
twenty-three workspace files, and the work is not reading them. It is reading
each claim and then opening the code it names. That is one context per surface,
and the surfaces do not need to talk to each other.

## The five surfaces

| Surface | Read | Check against |
| --- | --- | --- |
| `board-readme` | `board/README.md` | `board/` — `bin/board`, `bin/tutor`, `tutorboard/**`, `web/**`, `scripts/**`, `test/**` |
| `handoff-settled` | `HANDOFF.md`, the *Settled* section and *Before anything* | `board/` |
| `libr` | `projects/libr-local-llm/*.md` | that project's `bin/*`, sbatch scripts and python |
| `workspaces` | `{README,AI_INSTRUCTIONS,DIRECTION}.md` under `courses/Galois-Theory`, `courses/Probability`, `research/PSYCH-ASR`, `research/TRD-EHR` | `board/`, each workspace's own tree, and its `.gitignore` |
| `paper-writer` | `projects/Paper-Writer/*.md` | that project's package and its 517 tests |

`board/README.md` is long. Sample it by prioritising sentences that name a
function, module, command, flag, path or env var — those are the checkable
ones.

## What counts as a finding

**A falsehood of fact, and nothing else.** A claim is a finding when a reader
who believed it would do the wrong thing:

- a named function, flag, file, command, env var or path that does not exist or
  does not behave as described;
- a *nothing does X yet* / *still to be decided* / *not built* statement about
  something that has since been built;
- a number contradicted by a number elsewhere in the tree.

**Not findings:** prose style, tone, length, missing documentation, wording you
would have chosen differently, anything suspected without reading the code, or
a future plan honestly labelled as a plan. An empty result is a correct result.

Every finding carries the document path and line, the claim quoted, what the
code actually does, and the `path:line` that proves it.

## Every finding is then attacked

A model asked to find stale documentation will find stale documentation, and
most of what comes back untreated is wording. So each candidate goes to a
second reader whose **only** job is to show the document was right all along,
and which is told to default to *the document is fine* when uncertain. What
survives that is a fact.

Report the count of what did not survive, and the count of anything dropped for
a cap. A filter nobody can see is a filter nobody trusts.

## Two standing constraints

**The readers do not edit.** These documents are in the owner's voice, and
several agents rewriting prose in parallel produce several registers and a
merge conflict. The fleet returns facts; one turn applies them afterwards, in
one register. This is a decision, not timidity.

**`courses/Galois-Theory` may have a live session in it.** Read-only there,
always.

## Known drifts, named on purpose

Naming a drift already half-corrected is not cheating. It is the difference
between finding the tail of one and rediscovering its head.

- The board used to be a separate clone at `~/Tutor-Board`; it is `board/` in
  this repository now. Any document still pointing at the old path is wrong, as
  is any that describes its workspace as its own git remote.
- Whatever each workspace document says about what git tracks must match the
  real `.gitignore` and `git ls-files`. **Atlas is public**, so this is the one
  class of error here with a consequence outside the tree.
