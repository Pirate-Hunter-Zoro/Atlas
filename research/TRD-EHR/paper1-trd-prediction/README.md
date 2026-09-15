# Paper 1 — TRD prediction

Everything for the TRD-prediction manuscript. The narrative of how the work got
here is §1 of the repository's [`README.md`](../README.md); this file says what
is in this folder, what is submitted, and how to rebuild it.

**The paper makes two points, and that is the rule that governs the folder.**
As of 2026-09-06 every section of the manuscript is placed under one of them, and
material that serves neither is held in `reserve/` rather than printed. The rule is
enforced rather than remembered: the point-and-claim map is gated by Paper-Writer's
`gates/ladder.py` before any prose moves.

1. A generalized pretrained transformer embedding of a patient narrative does not
   significantly outperform a typed feature vector built from the same record. Best
   against best, +0.008 ROC AUC (95% CI −0.003 to +0.019).
2. Nearest-neighbor retrieval over that embedding — the clinical digital-twin premise
   — captures real label-informative structure and still loses decisively to a trained
   model, on every encoder tested.

**And one emphasis that runs through both.** In both arms the patient data were
hand-picked: predictor selection ran once, before either representation existed, and
the narrative the encoder reads is a fixed template over that same selection. So
neither point is evidence about what a model would do with a raw record. This is a
scope condition on two answers, not a third answer, and it was briefly and wrongly
written up as a third point on 2026-09-06.

`review/two_points_rationale.md` is why, what came out, and what is waiting on the
senior author. Read it before proposing an addition to the main text.

## The packet

Four documents, each as Markdown source plus a built `.docx` and a built `.pdf`.
The Markdown is the source of truth; both built forms are artifacts and are
regenerated rather than edited.

The `.docx` is what the journal takes and what the senior author marks up. The
`.pdf` is the reading copy: the tutoring board renders PDFs and only PDFs, so it
is how the packet is read on the iPad beside a lesson rather than on a laptop
beside one.

| Document | What it is |
| --- | --- |
| `manuscript.md` | the manuscript |
| `supplement.md` | Supplementary Methods (M1–M13) and supplementary results (S1–S11) |
| `tripod_ai_checklist.md` | the TRIPOD+AI reporting checklist, item by item |
| `cover_letter.md` | the cover letter |

**The references were renumbered on 2026-09-07** and every reference number in
`review/` and `reserve/` predates that pass. The old-to-new map is in the comment
block directly above the reference list in `manuscript.md`; read it before chasing a
number quoted anywhere else in this folder. The list had never been in order of first
appearance, which is what Vancouver and JMIR both require, and the manuscript header
had claimed it was.

All four carry HTML comment blocks at the top and inside sections recording the
decisions that govern them — naming rules, what may not drift back, which
reviewer comment a passage answers. Those comments never reach either built form.
Read them before editing the prose around them.

## `parts/` — the packet, one file per section

Every section of the manuscript and of the supplement, as its own `.md` and `.docx`.
Ten parts and twenty-two, numbered in reading order and named after their headings.

**Derived, never edited.** Each part carries a header saying which document it came
from, which position it holds, and that an edit made there is lost the next rebuild.
The assembled documents at the top level are the source of truth and these are produced
from them by `paperwriter.stages.splitting`. A part that disagrees with its parent is a
bug in the splitter, not a second version of the paper.

**What it is for.** Sending the Methods to the coauthor who wrote the Methods. Diffing
one section across two drafts. Handing a statistician the Results without the other
eleven thousand words around it. Every one of those used to be a scroll-and-select.

Not submitted, and not a substitute for the four packet documents. Run `rebuild`
after re-splitting.

## `reserve/` — complete, and deliberately not submitted

Five analyses and passages that are finished, held in the folder, and produced
only if a reviewer asks, plus the two machine-readable files the packet was
gated against: the point-and-claim map and the terminology lock. Nothing here
is a draft, and nothing here was cut for being wrong. Each document carries a
header comment saying what its status is and why it is held back.

| Document | What it holds |
| --- | --- |
| `grounding.json` | the terminology lock, the estimand, the reader, and the reporting checklist. Updated 2026-09-07: "feature matrix" is now a banned alias, and the approved second names for each arm are declared in `also_called` rather than left for the drift check to guess at |
| `point_claim_map.json` | the point-and-claim map this packet was gated against: two points, twenty claims, every claim serving a point or declaring a role. Run it through `paperwriter.gates.ladder.check` to reproduce the verdict quoted in `review/two_points_rationale.md` |
| `llm_similarity_judge.md` | the LLM clinical-similarity judge, complete: the full four-by-four retrieval grid, the verbatim rubric and prompts, the worked examples, the sub-score audit, and the re-judging experiment. Held back because it changed nothing where retrieval works — 0.5939 under cosine weighting against 0.5947 under the judge — and helped only under the negative controls |
| `methods_reserve.md` | the eight passages the Methods condensation removed that survive nowhere in the packet, each verbatim with the reviewer question that would want it back. It also carries the rule that keeps Methods from re-inflating: **Methods does not grow** |
| `limitations_reserve.md` | **superseded.** The record of the 2026-09-03 removal of the Limitations section, which was reversed on 2026-09-06. Still the right place for the audit of where each limitation also lives outside the Discussion; its section 4 is the earlier text, not what is submitted |
| `matched_input_parity.md` | the matched-input representation-parity re-run: does the field mismatch between the two representations carry the published comparison? It does not |
| `religion_sensitivity.md` | religion retained against religion removed, in both representations: does the result lean on a field that is 29.4% unrecorded? It does not |

The two analysis reports have their numbers tracked beside them, in
`reserve/parity_results/` and `reserve/religion_results/`, because both
`results` trees are gitignored and a commit would otherwise carry the prose and
none of the numbers. Each of those folders has its own README saying what it
holds, what it deliberately does not, and how to refresh it.

## `review/` — what was asked, and what was done

Internal. Not submitted, and not written for the journal.

| Document | What it is |
| --- | --- |
| `two_points_rationale.md` | **start here for the current state.** Why the paper was refocused onto points on 2026-09-06, why the hand-picking emphasis is not a third point, what left the packet, what came back, what the support-ladder gate said, and the four things waiting on the senior author |
| `manuscript_header_through_2026-09-03.md` | the round-by-round decision record that used to sit in a comment block at the top of `manuscript.md`, preserved verbatim when that header was rewritten as a statement of the rules in force. Read it when the question is *why* a rule exists rather than *what* it is |
| `MP_review_latest.md` | the record of the most recent senior-author round: the email, the nine comments, the tracked changes — and beneath them the verbal follow-up of 2026-09-04, which is staged and not applied |
| `round_2026-09-02_brief.md` | that round in five minutes — what was asked, what was done, what is left. Start here |
| `round_2026-09-02.md` | the same round item by item, with the reasoning, the word counts, the verification tables, and the arguments that exist nowhere else |
| `feedback/` | the documents he supplied: the tracked-changes manuscript, his replacement Methods and Discussion, the covering email |

When the brief and the long account disagree, the long one is right.

## `references/` — the citation library

26 of the 31 cited papers, held as PDFs so a citation can be checked without a
search. The file-number prefixes are a library index and have never matched the
manuscript's reference numbers — `CITATION_MAP.md` is the authority on which is
which. `references/README.md` is the role-grouped manifest and records what is
still missing; `reprint_request_emails.md` holds drafted requests for the four
papers that are paywalled.

## Rebuilding

From anywhere in this repository:

```bash
rebuild                                  # every document whose Markdown you changed
rebuild --strict                         # and fail on a figure that will not fit
rebuild reserve/religion_sensitivity.md  # one document

bash ../scripts/rebuild-packet.sh        # the four packet documents, .docx AND .pdf
```

`rebuild` builds a `.docx`. The packet's four also carry a `.pdf`, and
`scripts/rebuild-packet.sh` is the one command that keeps both current — run it
after editing any of the four. It names those four rather than building a PDF of
everything: fifty-five PDFs would bury the packet in the board's document drawer,
which offers two dozen.

A document is addressed by its path, and its `.docx` is written beside its source,
so a document in `reserve/` or `review/` rebuilds the same way as one at the top
level. Only what changed is rebuilt: fifty-five documents take seven seconds, one
takes one.

The build resolves figure paths against the paper folder — which is what the `../results/`
in a section under `parts/` is written relative to — then opens each built `.docx` and
counts the images actually in it against the ones its Markdown asks for. A document that
came up short fails the run. Figure widths are checked too: a figure with no explicit
width is imported at full page width, and a row of panels wider than the printable
column is silently shrunk until the panels stop lining up with their labels. Those two
warn, and `--strict` makes them fail, which is the run to make before submitting.

`rebuild` is a shell function from the sibling Paper-Writer repository; see *Editing a
document and rebuilding it* in the top-level README.
