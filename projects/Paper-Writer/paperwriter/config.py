"""Every tunable in the harness, in one module. No logic, no I/O.

The design is documented in full in README.md; this file is the knob panel, so
the stages stay declarative and a behaviour change is a one-line edit here (or an
environment variable, so a service file can override it without touching code).

Every runtime path is rooted at STATE_DIR, and STATE_DIR is env-overridable:
pointing PAPER_STATE_DIR at a temp tree relocates the journal, the evidence, the
ledgers, staging, and the logs in one move. That is what makes the deterministic
half testable anywhere.

Every environment variable is prefixed `PAPER_`.
"""

import os
import shutil
from pathlib import Path

# --- Roots -------------------------------------------------------------------

# The repo. `paperwriter/config.py` -> repo root is two levels up.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env_path(var, default):
    """A path tunable overridable from the environment."""
    val = os.environ.get(var)
    return Path(val).expanduser() if val else default


def _env_flag(var, default=True):
    """A boolean tunable. Anything in the falsey set turns it off."""
    raw = os.environ.get(var)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


# --- The drop folder ---------------------------------------------------------

# Where finished manuscripts are delivered, and where the drop folder lives beneath
# it. Default to a directory in the repo's parent so a clone works with no setup;
# point PAPER_OUT_DIR at a synced folder to drive the whole thing from a phone.
OUT_DIR = _env_path("PAPER_OUT_DIR", PROJECT_ROOT.parent / "Manuscripts")

# One filled prompt-template markdown file here is one job. Finished and failed
# prompts move into subfolders that are NOT re-scanned — file it away, never delete.
#
# `_inbox` cannot collide with a delivered project folder: delivery names those with
# `paths.slug`, which maps every non-alphanumeric run to a hyphen and strips leading
# ones, so a slug can never begin with an underscore.
INBOX_DIR = _env_path("PAPER_INBOX_DIR", OUT_DIR / "_inbox")
INBOX_FINISHED_DIR = INBOX_DIR / "finished"
INBOX_FAILED_DIR = INBOX_DIR / "failed"

# A short human-readable status document written beside the jobs, so progress is
# legible without a terminal. Set to "" to turn it off.
STATUS_FILENAME = os.environ.get("PAPER_STATUS_FILE", "_STATUS.md")

# How long a dropped file must stop changing before it is admitted. A file being
# written or synced into place is not a job yet.
INBOX_SETTLE_SEC = int(os.environ.get("PAPER_INBOX_SETTLE_SEC", "10"))

# The committed base prompts. Load-bearing non-code artifacts; they live at the repo
# root so they are easy to find and hand-edit.
PROMPTS_DIR = PROJECT_ROOT / "prompts"

# The runtime state tree. Everything the harness writes lives under here.
STATE_DIR = _env_path("PAPER_STATE_DIR", PROJECT_ROOT / "state")

# Artifacts are written into a hidden sibling directory and then atomically renamed,
# so no stage ever observes a half-written section.
STAGING_DIRNAME = ".staging"

# --- Where the evidence comes from -------------------------------------------
#
# A paper is written against results that already exist. SOURCE_DIRS are read-only
# trees the evidence stage may mine: an analysis repository's `results/`, a
# `references/` folder of PDFs, a reporting checklist. Colon-separated.
#
# Nothing here is ever written to. The harness reads numbers and citations out of
# these trees and freezes them into `state/evidence/`, and from that point on the
# frozen copy is ground truth — so a rerun of the analysis mid-draft cannot silently
# change what the manuscript claims.
_SOURCES_RAW = os.environ.get("PAPER_SOURCE_DIRS", "").strip()
SOURCE_DIRS = tuple(Path(p).expanduser() for p in _SOURCES_RAW.split(":") if p.strip())

# --- Prose and judgment: Claude, and only Claude -----------------------------
#
# Every text call in this harness goes to the same model. Evidence gathering,
# planning, outlining, drafting, editing, ledger merges — one model, one prompt
# style, one set of habits to write against.
#
# This used to be a five-provider registry with a two-tier model split (a cheap model
# wrote, an expensive one judged) and a per-role routing table. All of it is gone, and
# the argument is in `paperwriter/providers/__init__.py`. The short version: the split
# gave every quality problem two suspects, and the roles routed to the cheap tier kept
# having to be routed back after one of them cost a run.
#
# Prose quality is the entire product. There is no volume argument that beats it.

# Which binary drives Claude. Headless, on a logged-in session — the harness holds no
# API key and never has.
CLI_BIN = os.environ.get("PAPER_CLI_BIN", "claude")

# The model. One line, and it is the most consequential line in this file.
MODEL = os.environ.get("PAPER_MODEL", "claude-opus-5")

# --- What that consumes ------------------------------------------------------
#
# $ per MILLION tokens, as (input, output). Consumed only by `paperwriter/cost.py`,
# which projects what a paper costs; nothing at runtime reads it.
#
# These are LIST PRICES, and on a seat you are not charged them (see
# `infra/budget.record_usage`) — so read them as a measure of allowance consumed,
# not as a bill.
#
# Re-check before trusting a total; published rates move.
PRICES = {
    "claude-opus-5":      (5.00, 25.00),    # what this harness runs
    "claude-fable-5":    (10.00, 50.00),
    "claude-opus-4-8":    (5.00, 25.00),
    "claude-sonnet-5":    (2.00, 10.00),
    "claude-haiku-4-5":   (1.00,  5.00),
}

# --- The role table: what each kind of work is allowed to spend ---------------
#
# One table instead of eight stages each hand-tuning `max_turns` and `timeout` at
# its own call site. That scatter is not hypothetical harm: drafting sat at the
# smallest budget in the pipeline against the largest artifact in it for as long as
# the numbers were not written down next to each other.
#
#   max_turns agent turns
#   timeout   seconds for one call
#   tools     tool grant, smallest that does the job — this runs unattended with
#             permissions skipped, so a narrow grant is a narrow blast radius
#   oneshot   the role's whole input is INLINED in the prompt, so the model reads
#             nothing and writes the artifact in one call. This is the single largest
#             lever in the project — bigger than any model choice. An agentic CLI
#             re-sends the whole conversation, including every tool result, on every
#             turn, so a writer that opens the previous draft and lays a section down
#             in eight appends pays for that transcript eight times. Inlined and
#             written once, the same work at the same model is two or three turns. A
#             one-shot role gets a Write-only tool grant, because granting Read to a
#             model told not to read is an invitation.
TEXT_ROLES = {
    # Mines the results trees, the reference PDFs, and the reporting checklist. The
    # only role that genuinely needs to go and find its own input, and therefore the
    # only one that cannot be one-shot.
    "evidence":     {"max_turns": 80, "timeout": 2400,
                     "tools": ("Read", "Write", "Grep", "Glob", "WebSearch",
                               "WebFetch")},
    # Fixing the terminology, the estimand, and the reader the paper is written for,
    # once, before a word is drafted. The failure it prevents is a wrong choice
    # repeated on every page — a representation called three different things in one
    # manuscript, which reads to a reviewer as three different methods.
    "grounding":    {"max_turns": 24, "timeout": 2400,
                     "oneshot": True, "tools": ("Write",)},
    # The project plan: which papers, which venues, which claims belong to which.
    "planning":     {"max_turns": 40, "timeout": 3600,
                     "oneshot": True, "tools": ("Write",)},
    # The argument map: every claim the paper makes, the evidence each rests on, and
    # the section it lands in. The largest structured artifact in the pipeline.
    "argument":     {"max_turns": 40, "timeout": 3600,
                     "oneshot": True, "tools": ("Write",)},
    # Paragraph-level outlines for every section: one entry per paragraph, carrying
    # its topic sentence and the evidence ids it uses.
    "outlining":    {"max_turns": 30, "timeout": 3000,
                     "oneshot": True, "tools": ("Write",)},
    # Writes one section. The turn budget is not a length allowance — one Write
    # carries the whole section — it is headroom for thinking before that write.
    "drafting":     {"max_turns": 10, "timeout": 2400,
                     "oneshot": True, "tools": ("Write",)},
    # Finishing a section that stopped short. Its own role rather than a second use
    # of `drafting`, because it is a different job with a different input, and
    # because it should be separately visible in the cost breakdown.
    "continuation": {"max_turns": 10, "timeout": 2400,
                     "oneshot": True, "tools": ("Write",)},
    # The editorial pass: reads a whole section against the whole ledger and writes
    # back every defect WITH its exact repair. The most leveraged call in the
    # pipeline, because it is not only deciding what is wrong, it is writing the
    # correction that gets applied verbatim.
    "review":       {"max_turns": 10, "timeout": 1800,
                     "oneshot": True, "tools": ("Write",)},
    # Schema extraction from prose that is already in the prompt. Mechanical, and
    # structurally validated afterwards by `memory.ledger.merge_ledger_update`, so a
    # bad proposal here costs a revision at worst, never a corrupt ledger.
    "ledger_merge": {"max_turns": 6, "timeout": 900,
                     "oneshot": True, "tools": ("Write",)},
}

# Extra PATH entries prepended for subprocess model calls.
EXTRA_PATH = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]

# How long to wait out a model-side allowance ceiling before trying again.
MODEL_QUOTA_BACKOFF_SEC = int(os.environ.get("PAPER_MODEL_QUOTA_BACKOFF_SEC", "300"))

# --- Length ------------------------------------------------------------------
#
# Academic length is a CEILING, and that is the one place this project's targets
# invert from the novel harness it grew out of. A journal that says 4,000 words means
# it, and a manuscript over the limit is desk-rejected before a reviewer reads a
# sentence. So sections carry a budget from the outline and the gate enforces both
# ends of it: too short means a claim was asserted rather than supported, too long
# means the section is padded and will be cut by someone who is not the author.
#
# The floor is deliberately loose and the ceiling deliberately tight.
#
# **The floor is 50 and it used to be 150, which is the number that matters here,
# because the floor does not merely report a short section — `stages.drafting`
# re-prompts the model for continuation prose until the draft clears it.** A wrong
# floor is therefore an instruction to pad, and 150 was wrong about eight sections of
# a published manuscript: a 55-word Conclusions, a 67-word Ethical Considerations, a
# 113-word Implications and Next Steps. Every one of them is the right length for what
# it has to say. 50 refuses a heading with a stub under it and nothing else, which is
# the only case the absolute floor can judge without a plan to judge it against.
#
# The real floor is the outline's, at `SECTION_UNDER_BUDGET_RATIO` of the budget, and
# it still applies wherever a section was planned. A section nobody planned has no
# claim count to be short of.
#
# The floor also does not apply to a section that DECLARES rather than argues. A
# two-word conflicts statement and a thirty-one-word data-availability statement are
# both the right length whatever the plan says, so `gates/length.py` drops the floor
# to zero for a back-matter section, keyed on the section's phase.
SECTION_MIN_WORDS = int(os.environ.get("PAPER_SECTION_MIN_WORDS", "50"))

# The absolute ceiling on one top-level section, independent of any outline budget.
#
# Nothing in this project held one. A venue's body limit is a whole-manuscript number
# and advisory at that; `length.check`'s ceiling is 1.15x whatever the PLANNER wrote,
# so a plan that budgets 2,700 words for Results passes at 2,767. The result is a
# Results section three times the length of the Discussion it feeds, which no gate
# could see.
#
# A section is the unit a reader holds before the next heading resets it. Past about
# 1,800 words it is two sections, or one section plus a supplement entry — and the
# repair is the second of those, which is why the gate's reason says to relocate the
# quantitative half rather than to compress sentences.
#
# The number is set at the granularity the machinery uses. `stages.sweep.sections`
# splits on H1, and an outline section IS an H1, so this is a whole Methods or a
# whole Results — not a subsection. A published manuscript's Methods at this scope
# runs 1,133 words, so the ceiling leaves roughly 60% of headroom over the longest
# section of a real, accepted paper while refusing three of five sections of the
# draft that paper replaced (Results 2,767, Discussion 2,496, Methods 2,047). A
# tighter cap measured at H2 rejects the accepted paper outright at the scope the
# sweep actually applies it.
SECTION_MAX_WORDS = int(os.environ.get("PAPER_SECTION_MAX_WORDS", "1800"))

# --- Titles -------------------------------------------------------------------
#
# A venue that states a character limit wins, and most do not state one — which meant
# nothing checked a title at all. One manuscript carried a 34-word, 258-character title
# reading "Typed Feature Vectors, Generalized Pretrained Transformer Embeddings of
# Deterministic Patient Narratives, and Nearest-Neighbor Retrieval for Predicting a
# Treatment-Switch-Defined Electronic Health Record Proxy for Treatment-Resistant
# Depression: Retrospective Cohort Study". Every word in it is accurate. Nobody can
# read it, and a title nobody reads is a paper nobody opens.
#
# A title names the finding and the design. Twenty words is generous for both.
TITLE_MAX_WORDS = int(os.environ.get("PAPER_TITLE_MAX_WORDS", "20"))

# The short title is a RUNNING HEAD. It sits in the margin of every page, and the
# constraint is the margin rather than a matter of taste: journals converge on about
# fifty characters because that is what fits. The same manuscript's short title ran to
# 137.
SHORT_TITLE_MAX_CHARS = int(os.environ.get("PAPER_SHORT_TITLE_MAX_CHARS", "60"))

# --- Reporting density, for Results-phase sections only -----------------------
#
# A Results section's job is to report numbers. How many words it spends per number is
# therefore a measure of how much of it is reporting and how much is talking about the
# reporting. Pointed at a real manuscript before and after a compression pass, this
# tracked every edit: 8.9 to 6.8 in the discrimination section, 12.9 to 10.9 in
# calibration, 15.8 to 14.9 in the validity checks.
#
# It WARNS and does not block, and the exception is the reason why. A section that
# names its predictors — suicidality, insomnia, obsessive-compulsive disorder — is
# reporting in words rather than in figures, scores 20 on this measure, and is correct.
# Blocking would tell that section to invent numbers.
RESULTS_WORDS_PER_NUMBER_WARN = float(
    os.environ.get("PAPER_RESULTS_WORDS_PER_NUMBER_WARN", "20.0"))

# Below this many words a ratio is noise rather than a measurement.
RESULTS_DENSITY_MIN_WORDS = int(
    os.environ.get("PAPER_RESULTS_DENSITY_MIN_WORDS", "80"))

# How far over its outline budget a section may run before the gate blocks. 1.15 is
# one long paragraph of slack on a 1,000-word section.
SECTION_OVER_BUDGET_RATIO = float(
    os.environ.get("PAPER_SECTION_OVER_BUDGET_RATIO", "1.15"))

# And how far under, for the same reason in the other direction. A section at 55% of
# its planned length is not concise, it is missing a claim.
SECTION_UNDER_BUDGET_RATIO = float(
    os.environ.get("PAPER_SECTION_UNDER_BUDGET_RATIO", "0.6"))

# --- Readability -------------------------------------------------------------
#
# Not the children's-book band this code was born with. Academic prose in a clinical
# or methodological journal sits around FK grade 11-15: above that the reviewer is
# re-reading sentences.
#
# **The floor is deliberately generous, and it is the one threshold here that must
# never be tightened.** This whole harness exists to produce prose a reader
# understands on one pass, and short sentences made of plain words are how that is
# achieved — so a gate that penalises a well-written section for scoring 9.9 is a gate
# arguing against the project's entire purpose. It is here only to catch a section
# that has dropped the precision its claims need, which is a real failure and a rare
# one, and its own message says as much.
#
# **Reading ease is measured and reported and never enforced. There is no floor and
# there must not be one.** The band was defended on the ground that it was wrong about
# Methods and right about Introduction, Results and Discussion. A published version of
# one of this project's own manuscripts — rewritten by its senior author, shorter and
# tighter than what the harness produced — scores 6.4, 16.4 and 3.2 in those three
# sections against the floor of 20 that used to stand here, and the harness's own
# longer, worse draft cleared it in all three. A gate that refuses the better paper
# and passes the worse one is measuring the wrong thing: reading ease is dominated by
# syllables per word, syllables per word in a clinical paper is subject matter, and
# `gates/sentences.py` measures the half that is a choice.
#
# A floor of zero would not have said this. Reading ease goes negative on real
# clinical prose, so zero enforces nothing while leaving a live reason string for the
# next maintainer to re-tighten. The number is computed and carried in the report, so
# the record still shows what a section scored.
#
# The FK ceiling survives, because it catches something the sentence gate does not:
# long words in long sentences at once. It sits at 18 rather than 16 because the same
# reference manuscript peaks at 17.2 in its Discussion.
READABILITY_FK_GRADE_MIN = float(os.environ.get("PAPER_FK_GRADE_MIN", "8.0"))
READABILITY_FK_GRADE_MAX = float(os.environ.get("PAPER_FK_GRADE_MAX", "18.0"))

# --- The one-read rule, measured ---------------------------------------------
#
# "The reader must understand every sentence the first time" is a slogan until it is
# counted. These are the counts, and every one of them was calibrated against a real
# manuscript whose reviewers complained about density: body text at a mean of 26.2
# words per sentence, 23% of sentences past 35 words, 74 semicolons and 34 em-dashes
# in 15,000 words. Nearly every one of those marks welded a second claim into a
# sentence that already carried one.
#
# The targets below are what that manuscript should have been.

# Mean words per sentence, across a section. The band, not a point: prose that is
# uniformly short is its own failure and reads like a machine wrote it.
SENTENCE_MEAN_WORDS_MAX = float(os.environ.get("PAPER_SENTENCE_MEAN_MAX", "22.0"))
SENTENCE_MEAN_WORDS_MIN = float(os.environ.get("PAPER_SENTENCE_MEAN_MIN", "12.0"))

# A sentence past this is doing two jobs. Some are legitimate; a section where many
# are is not.
SENTENCE_LONG_WORDS = int(os.environ.get("PAPER_SENTENCE_LONG_WORDS", "35"))
SENTENCE_LONG_SHARE_MAX = float(os.environ.get("PAPER_SENTENCE_LONG_SHARE_MAX", "0.08"))

# The MIDDLE of the length distribution, which is where a heavy text and a readable
# one actually separate, and which nothing here measured.
#
# Above 35 words two manuscripts of the same paper — the harness's draft and the
# published rewrite of it — are indistinguishable: 1.2% against 0.9%, both far under
# the 8% ceiling above, and neither carries a sentence past 45. The whole difference
# sits between 25 and 35 words, and the draft runs 18.9% of its sentences there
# against the rewrite's 5.6%. The tail rule cannot see it because there is no tail.
#
# 25 is not read off either text. It is the ceiling plain-language and medical-writing
# guidance converge on, and this is the 35-word rule one band down.
#
# **It is enforced at DOCUMENT scope, and that is measured rather than preferred.**
# The published supplement's own section M3 runs 23% of its thirteen sentences past 25
# words, so any per-section ceiling tight enough to catch the draft refuses the
# published text. Across a whole document the two separate cleanly: 18.9% and 17.4%
# for the draft's manuscript and supplement, 5.6% and 6.6% for the rewrite's. The
# ceiling clears the rewrite by a factor of two and a half and refuses both of the
# draft's documents.
# WHY THESE FOUR ARE ADVISORY AND NOT BLOCKING.
#
# They were calibrated on one comparison -- our draft against the senior author's
# rewrite of it -- with no negative control, and a later pass supplied one. Measured
# through this project's own splitter, the share of sentences past 25 words is:
#
#   the rewrite                    4.8%      Sentence-BERT, EMNLP      15.7%
#   our draft                     13.1%      BGE, arXiv                16.4%
#                                            XGBoost, KDD              19.9%
#                                            TRIPOD+AI, BMJ            25.5%
#                                            scikit-learn, JMLR        27.3%
#                                            Qwen3-Embedding, arXiv    41.5%
#
# The rewrite is a three-to-five-times outlier against published prose, and our draft
# already sits at the tight end of normal. A ceiling set to match the rewrite refuses
# TRIPOD+AI -- the reporting guideline this packet is written to follow -- and the
# same held for the section, paragraph and abstract ceilings: all four fired on every
# external paper tested, at two to three times their threshold.
#
# So the numbers stay and the block goes. Terseness of that order is a quality of one
# author's rewrite, not a property of publishable prose, and a gate cannot tell the
# difference. What a gate CAN say is "this section is long, here is the number" and
# leave the judgement where it belongs. Raise any of these to blocking only against a
# corpus of papers nobody here wrote.
SENTENCE_MID_WORDS = int(os.environ.get("PAPER_SENTENCE_MID_WORDS", "25"))
SENTENCE_MID_SHARE_MAX = float(os.environ.get("PAPER_SENTENCE_MID_SHARE_MAX", "0.15"))

# The hard ceiling. One sentence of 60 words is a defect wherever it appears.
SENTENCE_HARD_MAX_WORDS = int(os.environ.get("PAPER_SENTENCE_HARD_MAX", "55"))

# Sentence length must VARY. Standard deviation below this floor means every sentence
# is the same length, which is the loudest tell that a machine wrote the paragraph.
SENTENCE_STDEV_MIN = float(os.environ.get("PAPER_SENTENCE_STDEV_MIN", "4.0"))

# Welds, per 1,000 words. A semicolon or an em-dash is almost always two sentences
# pretending to be one. Not banned — occasionally one is exactly right — but rationed.
SEMICOLONS_PER_KWORD_MAX = float(os.environ.get("PAPER_SEMICOLON_RATE_MAX", "2.0"))
EMDASHES_PER_KWORD_MAX = float(os.environ.get("PAPER_EMDASH_RATE_MAX", "2.0"))

# The local density ceiling: mean words per sentence within ONE paragraph.
#
# Every measurement above is a section average, and an average hides the paragraph
# that earns it. A real manuscript from this harness passed its Methods section at a
# mean of 20.8 while carrying a four-sentence paragraph at 27.2 — the section's other
# nineteen sentences paid for it. Six such paragraphs sat in sections that passed. The
# reader does not read the average; they read the paragraph, and they read it twice.
#
# The ceiling is looser than the section ceiling on purpose. One paragraph is allowed
# to be the heavy one — a definition, a set of exclusions, a passage that genuinely
# carries more clauses than its neighbours. What is not allowed is a paragraph nobody
# can read hiding behind twenty sentences that carry it.
PARAGRAPH_MEAN_WORDS_MAX = float(os.environ.get("PAPER_PARAGRAPH_MEAN_MAX", "26.0"))

# Below this many sentences a paragraph mean is not a measurement. Two sentences, one
# of them a legitimate 40-word list of covariates, average 26 and mean nothing.
PARAGRAPH_DENSITY_MIN_SENTENCES = int(
    os.environ.get("PAPER_PARAGRAPH_DENSITY_MIN_SENTENCES", "3"))

# How many of the worst-offending sentences the editor is shown verbatim when the
# section fails a sentence gate. Readability is a whole-text statistic and cannot be
# anchored to a span; the longest sentences can be, which turns an un-anchorable gate
# into a list of ordinary anchored edits.
EDIT_LONG_SENTENCES = int(os.environ.get("PAPER_EDIT_LONG_SENTENCES", "15"))

# --- Paragraph shape ---------------------------------------------------------
#
# A paragraph is a claim, its support, and its consequence. The gate cannot judge
# whether a topic sentence is good, but it can catch every structural way a paragraph
# fails to have one: a paragraph that opens on a citation, opens on a number, opens
# with a connective, or is one sentence long and therefore has no structure at all.
# The floor is TWO, and it was three until a real manuscript was read against it.
#
# Three is the right shape for a paragraph that argues: a claim, its support, and what
# follows. It is the wrong floor for the paragraphs a paper is also made of. Of eight
# paragraphs the floor of three refused in one manuscript, seven were correct at two
# sentences: an attrition statement with nothing more to say, a two-sentence lead-in
# before a run of bolded subsections, a claim and the consequence it licenses, and the
# compact findings a Conclusions section is made of.
#
# Exactly one was a real defect, and it was ONE sentence — a fact left floating between
# two paragraphs after a compression pass. That is the line. A single sentence cannot
# be a claim plus anything. Two can be a claim and what follows from it, and whether
# that is enough is a question about the section, which the OUTLINE answers by naming a
# topic sentence for every planned paragraph. Counting sentences was standing in for
# that judgement and getting it wrong seven times in eight.
PARAGRAPH_MIN_SENTENCES = int(os.environ.get("PAPER_PARAGRAPH_MIN_SENTENCES", "2"))
PARAGRAPH_MAX_SENTENCES = int(os.environ.get("PAPER_PARAGRAPH_MAX_SENTENCES", "9"))

# And a ceiling on the paragraph's WORDS, which is a different failure from its
# sentence count and is caught by nothing else. Nine short sentences is two claims;
# so is one 155-word block of five long ones, and the sentence ceiling has never fired
# on either manuscript this project has measured (maxima 8 and 7).
#
# 120 is the lowest cap in a 100/110/120/130/150 sweep that the published rewrite
# clears completely, in the manuscript and in the supplement both: its longest
# paragraphs are 113 and 111 words. The draft it replaced runs 15 of 87 manuscript
# paragraphs over it, topping out at 155. At the register's own ~19 words per
# sentence, 120 words is six sentences, which is the same claim the sentence ceiling
# makes and the same one the two-sentence floor makes from below.
PARAGRAPH_MAX_WORDS = int(os.environ.get("PAPER_PARAGRAPH_MAX_WORDS", "120"))

# What share of a section's paragraphs may break the shape rules before it blocks.
# Not zero: a one-sentence paragraph is right at the end of a Discussion, and a table
# caption is a paragraph to the parser.
PARAGRAPH_DEFECT_SHARE_MAX = float(
    os.environ.get("PAPER_PARAGRAPH_DEFECT_SHARE_MAX", "0.15"))

# Below this many checkable paragraphs a share is not a measurement. "1 of 1
# paragraphs are mis-shaped (100%)" is what a twenty-word Corresponding Author section
# reports, and "1 of 3 (33%)" is what a short subsection reports on one defect that
# would be invisible inside its parent. Neither is a finding, both block, and every
# defect kind added to this gate makes the arithmetic worse. The individual defects
# are still reported; only the section-level share is withheld.
PARAGRAPH_DEFECT_MIN_PARAGRAPHS = int(
    os.environ.get("PAPER_PARAGRAPH_DEFECT_MIN_PARAGRAPHS", "5"))

# --- The Results topic sentence ----------------------------------------------
#
# A Results paragraph whose claim IS a number states the claim and the number in the
# same sentence. Spending a bare claim sentence first and giving the figure in the
# next one is two sentences doing one sentence's work, and it is most of what makes a
# long Results section long.
#
# Measured on the manuscript's Results section: the harness's draft puts a reported
# figure in 2 of 24 opening sentences (8%), the published rewrite in 8 of 9 (89%).
# The floor is 50% and not 80% because 80% is demonstrably unsafe one document over —
# the published supplement's own S-sections run 0 to 50% on the same measure, which is
# why the check is scoped to the manuscript's Results heading and nowhere else.
#
# It ADVISES. A Results section whose findings are qualitative is a legitimate short
# report and scores badly here; the density guard skips most of those and the
# advisory severity covers the rest.
RESULTS_TOPIC_FIGURE_SHARE_MIN = float(
    os.environ.get("PAPER_RESULTS_TOPIC_FIGURE_SHARE_MIN", "0.50"))

# Below this many checkable paragraphs the share is noise, and below this many
# reported figures per 100 words the section is not reporting figures at all.
RESULTS_TOPIC_MIN_PARAGRAPHS = int(
    os.environ.get("PAPER_RESULTS_TOPIC_MIN_PARAGRAPHS", "3"))
RESULTS_TOPIC_DENSITY_MIN = float(
    os.environ.get("PAPER_RESULTS_TOPIC_DENSITY_MIN", "4.0"))

# --- The abstract ------------------------------------------------------------
#
# Every prose gate exempts the abstract, for good reasons that all concern its shape:
# it is one structured block, its labels are the venue's, and a keyword line is
# semicolon-separated by convention. The consequence is that nothing measured the one
# section a reader meets detached from the paper.
#
# Two things are worth measuring there and the rest is not. A hard per-sentence
# ceiling, because an abstract has no room for the one legitimate long sentence a
# 5,000-word section can absorb: the published rewrite's longest abstract sentence is
# 32 words and the draft's is 38, with three more between 34 and 37. And the balance
# between the Methods label and the Results label, because a structured abstract
# exists so that a detached reader gets the FINDING — procedure has a whole Methods
# section and a supplement behind it, and a finding has a hundred words. The draft
# spends 137 words on Methods against 76 on Results, a ratio of 1.80; the rewrite
# spends 93 against 110, a ratio of 0.85.
#
# What is deliberately NOT measured there, because each one refuses the published
# abstract: the semicolon ration (two semicolons in 311 words scores 6.4 per thousand),
# the mean sentence length (real published abstracts run 21 and 24 words against the
# rewrite's 15.9, so the whole catch would live in a band of one text), and any
# per-label share ceiling (the rewrite's Results label is 35% of its abstract).
ABSTRACT_SENTENCE_MAX_WORDS = int(
    os.environ.get("PAPER_ABSTRACT_SENTENCE_MAX_WORDS", "35"))
ABSTRACT_METHODS_RESULTS_RATIO_MAX = float(
    os.environ.get("PAPER_ABSTRACT_METHODS_RESULTS_RATIO_MAX", "1.2"))

# --- The point made over and over ---------------------------------------------
#
# Three sections each spending a paragraph on the same background fact. Every
# instance true, well written and relevant; end to end it reads as a paper that does
# not trust its reader. Two is normal — a Discussion picks up what the Results said —
# so the floor is three.
ECHO_MIN_SECTIONS = int(os.environ.get("PAPER_ECHO_MIN_SECTIONS", "3"))

# Jaccard overlap of content words. A writer restating a point never uses the same
# words twice, so this is deliberately loose; it was set by pointing the check at a
# real manuscript and walking it up until the table captions stopped matching.
ECHO_SIMILARITY = float(os.environ.get("PAPER_ECHO_SIMILARITY", "0.45"))

# Below this many content words, heavy overlap does not mean two sentences say the
# same thing.
ECHO_MIN_CONTENT_WORDS = int(os.environ.get("PAPER_ECHO_MIN_CONTENT_WORDS", "8"))

# Sections whose paragraph-shape and sentence rules are relaxed entirely. An abstract
# is one structured block, a declarations section is a list, and references are not
# prose. An abbreviations list is a definition list, and a venue that requires one
# produced a 92-word "sentence" made of fourteen glossary entries.
#
# **Back matter is here as nine separate named sections, not as one `Declarations`
# block, because that is how a journal wants it written.** `gates/venue.py` requires
# each mandatory section to exist as its own heading; a manuscript that complies then
# carries nine short headings, and without this list every one of them draws findings
# from gates that have no business reading them — a sentence-mean floor on a two-word
# conflicts statement, a 100% mis-shaped-paragraph share on a one-line data
# availability statement, a reading-ease band on an author-contributions list. Nine
# blocking findings, on the part of the manuscript that is correct.
#
# **Matched as a heading PREFIX, not for equality.** "Multimedia Appendix 1" is what
# the venue calls the section and it never equals the tag.
PARAGRAPH_EXEMPT_SECTIONS = (
    "abstract", "title page", "declarations", "references", "keywords",
    "abbreviations", "contents",
    "acknowledgement", "acknowledgment", "funding", "conflicts of interest",
    "conflict of interest", "competing interests", "data availability",
    "data sharing", "author contributions", "authors contributions",
    "authors' contributions", "protocol and registration", "multimedia appendix",
    "corresponding author", "author orcids",
)

# --- The final sweep ---------------------------------------------------------
#
# How many blocking findings the sweep writes to the log. The full list always reaches
# `report.md` and the journal; this is only the console, where a hundred lines scrolling
# past is the same as none. Ten is what fits on a screen beside the build output.
SWEEP_LOG_FINDINGS = int(os.environ.get("PAPER_SWEEP_LOG_FINDINGS", "10"))

# Sections where READABILITY is not measured, because both its numbers are
# dominated by syllables per word and a methods section's syllable count is its
# subject matter.
#
# Flesch reading ease and Flesch-Kincaid grade are driven by two things: sentence
# length, which `gates.sentences` already measures directly and far more precisely,
# and word length, which is the part this gate exists for. In a Methods section the
# word length is not a choice. "Psychiatric and substance-use comorbidity, medical
# comorbidity, prior antidepressant exposure and medication burden, health-care
# utilization, and sociodemographic characteristics" is a list of the domains the
# study used, every word of it required, and nothing a writer does to that sentence
# improves it.
#
# Measured on a real manuscript the gate refused nine sections — the main Methods and
# eight of thirteen Supplementary Methods, at reading ease 5 to 19 against a floor of
# 20 — and all nine were correct. The lowest was a predictor-selection section at
# -1.0, which is a list of clinical domains and cannot be raised without renaming the
# analysis. That is the third time this project has met the same failure: a measure
# right about prose in general is wrong about prose whose subject IS the thing being
# measured. Nominalization density and caption restatement both died on it.
#
# What is left is the sections where the vocabulary is a choice — Introduction,
# Results, Discussion, Conclusions — and there the gate stays live and passes at
# reading ease 30 to 38. The rule itself stays in `prompts/draft.md`, where a writer
# reads it, and out of the gate, where it would only teach a writer to rename the
# analysis.
# Matched as a heading PREFIX, so "supplement m" covers a Supplementary Methods
# section — M1 through M13 are methods and score the same way the main Methods does.
READABILITY_EXEMPT_SECTIONS = tuple(sorted(
    {"methods", "materials and methods", "material and methods",
     "supplementary methods", "supplement m"}
    | set(PARAGRAPH_EXEMPT_SECTIONS)))

# Sections whose numbers are BIBLIOGRAPHIC rather than findings, so the number gate
# does not scan them.
#
# This is deliberately NOT PARAGRAPH_EXEMPT_SECTIONS, and the difference is the
# abstract. An abstract is exempt from paragraph shape because it is one structured
# block, and it is the LAST place a number should go unchecked: rounding 0.712 to 0.71
# in the abstract while the results say 0.712 is the defect the number gate exists for.
# So the abstract stays under the gate, and so does a declarations section.
#
# What comes out is the front and back matter that carries citations and labels. A
# Vancouver reference is a dense block of numbers and not one of them is a result — a
# volume, an issue, a page range, a DOI prefix, an arXiv id — and no evidence ledger
# will ever contain doi:10.1145/3626772.3657878. On an assembled 30-reference
# manuscript the gate returned 58 unsupported numbers, all 58 bibliographic, against
# 257 real figures every one of which traced.
NUMBER_EXEMPT_SECTIONS = ("references", "title page", "abbreviations", "keywords",
                          "acknowledgements")

# The top-level headings a manuscript is not a manuscript without.
#
# IMRaD, and it is checked against the ASSEMBLED document rather than the outline,
# because the outline had all five and the file did not. A newline went missing in
# front of "# Methods" during an edit, so the marker ended up inside the last sentence
# of the Introduction — "...is documented in Supplement S8. # Methods" — and pandoc
# rendered it as four literal characters of body text. The built .docx had no Methods
# heading anywhere and every gate in this project passed, because a gate handed one
# section at a time cannot notice that a section boundary stopped existing.
#
# Matched on a lowercased heading that STARTS WITH one of these, so "Materials and
# methods" is not matched by "methods" but "Methods and analysis" is. Each entry is a
# tuple of acceptable openings for the same section.
MANUSCRIPT_REQUIRED_HEADINGS = (
    ("abstract",),
    ("introduction", "background"),
    ("methods", "materials and methods", "material and methods"),
    ("results", "findings"),
    ("discussion",),
)

# Sections whose words are SOMEBODY ELSE'S, so a locked term does not govern them.
#
# Exactly one, and the narrowness is the point. A reference list is other people's
# titles: a lock forbidding "resistant depression" in favour of "TRD" flagged two
# entries whose published titles are "Treatment resistant depression in electronic
# health records: definitions matter" and "Treatment resistant depression:
# socio-demographic characteristics...". You cannot rename somebody else's paper, and
# the only repair the gate offered was to misquote a citation.
#
# The ABSTRACT is not on this list and must not be. It is the author's own prose and
# the part of the paper most people read, so a forbidden synonym there is a defect in
# the worst possible place. Nor is the abbreviation table, which is the paper's own
# vocabulary written out, or the keyword line, which the author chose.
TERM_BORROWED_SECTIONS = ("references",)

# Sections where a CLOSING CROSS-REFERENCE is the paragraph's conclusion rather than a
# substitute for one, so the signpost rule does not run.
#
# A methods paragraph's job is to specify a procedure. When the fuller specification
# lives in a supplement — which is the whole design of a condensed Methods with a
# thirteen-section Supplementary Methods behind it — the pointer IS the rest of that
# paragraph's content, not a dodge in place of its meaning. "Full index-selection rules
# are given in Supplement M2" is where the paragraph goes, and there is nothing else
# for it to close on.
#
# This was measured rather than assumed. Pointed at a real Methods section the rule
# refused eight of twenty-one paragraphs, and all eight were correct as written: the
# data-version paragraph, the eligibility cascade, the index-selection rules, the
# inferential boundary, the predictor rationale, the missingness frequencies, the
# leakage safeguards, the retrieval equations. A gate that fires on eight correct
# paragraphs in one section is a gate somebody switches off, which is the same
# calculation that narrowed the dash ration and the nominalization count.
#
# Everything else about a methods paragraph is still checked, including the OPENER.
# Matching is on a lowercased section name containing one of these, so "Methods",
# "Materials and methods" and "Supplement M4. Predictor selection" all qualify — a
# supplementary methods section is a methods section.
SIGNPOST_EXEMPT_SECTIONS = ("methods", "supplement m", "supplementary method",
                            "appendix")

# Sections a paper is SUPPOSED to restate itself in. The paragraph-shape rules still
# apply to a conclusions section — it is prose and it has topic sentences — so this is
# its own list rather than a reuse of PARAGRAPH_EXEMPT_SECTIONS. A conclusions that
# introduced new material would be the defect; one that repeats the Discussion is the
# section working, and counting it makes the normal arc of a paper look like a fault.
ECHO_EXEMPT_SECTIONS = tuple(sorted(set(PARAGRAPH_EXEMPT_SECTIONS) |
                                    {"conclusions", "conclusion", "summary"}))

# --- Terminology drift -------------------------------------------------------
#
# The terminology gate can only forbid the synonyms somebody thought to list. The
# manuscript that gate was written from went on to carry four names for one arm —
# "typed feature representation", "feature representation", "feature matrix" and
# "feature-vector" — because only "rule-based approach" had been banned. Nothing
# fired, because nothing was looking for a name the lock had never heard of.
#
# So the gate also looks for drift: a phrase sharing a locked term's modifier but
# ending in a different role noun. "Feature matrix" against a locked "feature
# representation" is a candidate second name; "feature selection" is not, because
# selection is not a thing the paper is naming.
TERM_ROLE_NOUNS = ("representation", "approach", "model", "matrix", "vector",
                   "method", "arm", "pipeline", "encoding", "framework", "scheme",
                   "predictor", "classifier", "embedding", "baseline", "variant")

# A one-off near-variant is usually ordinary English. A phrase used this many times is
# a name, whether or not anybody declared it one.
TERM_DRIFT_MIN_USES = int(os.environ.get("PAPER_TERM_DRIFT_MIN_USES", "2"))

# --- Gate thresholds ---------------------------------------------------------

# What fraction of the claims the paper plans to make must be backed by at least one
# frozen evidence item before drafting may start. Below this, the project parks and
# gathers more rather than drafting a paper on evidence it never assembled.
EVIDENCE_COVERAGE_MIN = float(os.environ.get("PAPER_EVIDENCE_COVERAGE_MIN", "0.85"))

# Numbers in prose are checked against the evidence ledger. A number that is not
# there is a blocking defect — this is the academic analogue of a canon breach, and
# it is the single most valuable gate in the project.
#
# Tolerance for a rounded restatement: 0.712 written as 0.71 is the same number.
# Expressed as a relative difference.
NUMBER_MATCH_TOLERANCE = float(os.environ.get("PAPER_NUMBER_TOLERANCE", "0.005"))

# Small integers, years, and section/figure/table numbers are not findings. Checking
# them produces noise and nothing else.
NUMBER_CHECK_MIN = float(os.environ.get("PAPER_NUMBER_CHECK_MIN", "0"))

# --- The editorial loop ------------------------------------------------------
#
# A section gets this many passes before the loop starts asking whether it is still
# improving. Three, because on measured trajectories the fourth pass rarely beat the
# third and the tenth was routinely worse than the fifth.
EDIT_MAX_PASSES = int(os.environ.get("PAPER_EDIT_MAX_PASSES", "3"))

# The absolute ceiling, however well it is converging.
EDIT_HARD_MAX_PASSES = int(os.environ.get("PAPER_EDIT_HARD_MAX_PASSES", "6"))

# How many recent passes have to beat the best count before them for the loop to
# count as still improving.
EDIT_STALL_PASSES = int(os.environ.get("PAPER_EDIT_STALL_PASSES", "2"))

# Structural repairs — a passage replaced wholesale rather than find/replaced — per
# pass. Capped because each one is new prose that nothing has read yet.
SURGERY_MAX_PER_PASS = int(os.environ.get("PAPER_SURGERY_MAX_PER_PASS", "2"))

# A replacement passage shorter than this fraction of what it replaced is a deletion
# wearing a rewrite's clothes. Refused.
SURGERY_MIN_RATIO = float(os.environ.get("PAPER_SURGERY_MIN_RATIO", "0.6"))

# How many whole-paper sweeps run after every section exists.
REVISION_SWEEPS = int(os.environ.get("PAPER_REVISION_SWEEPS", "2"))

# A draft on disk with at least this many words is resumed rather than re-rolled.
DRAFT_RESUME_MIN_WORDS = int(os.environ.get("PAPER_DRAFT_RESUME_MIN_WORDS", "120"))

# Continuation passes allowed on a section that came in under its floor.
DRAFT_MAX_CONTINUATIONS = int(os.environ.get("PAPER_DRAFT_MAX_CONTINUATIONS", "2"))

# --- The argument map --------------------------------------------------------

# Every claim must be placed in exactly one section, and every section must carry at
# least this many. A section with one claim is a paragraph.
SECTION_MIN_CLAIMS = int(os.environ.get("PAPER_SECTION_MIN_CLAIMS", "2"))

# --- The support ladder ------------------------------------------------------
#
# points -> claims -> evidence. `gates/ladder.py` checks the top join: that
# everything in the paper serves what the paper is for. These five numbers decide
# what "serves" is allowed to mean, so changing one changes what this harness will
# publish.

# How many points a paper may be about. One is the ordinary case and the degenerate
# case at once — the `headline` boolean this replaced was this gate with the count
# fixed at one. Two is common: a comparison, plus what the comparison rules out.
# Three is the most a reader carries out of the room. Four is the count at which the
# author has stopped choosing, and the manuscript that produced this gate had three
# stated objectives of which two were support for the first.
POINTS_MIN = int(os.environ.get("PAPER_POINTS_MIN", "1"))
POINTS_MAX = int(os.environ.get("PAPER_POINTS_MAX", "3"))

# A point stated in fewer words than this is a topic. "Representation comparison" is
# six characters short of being a heading; "the embedding does not outperform the
# feature vector" is a point. Six is the floor at which a sentence with a subject and
# a verb becomes possible.
POINT_MIN_WORDS = int(os.environ.get("PAPER_POINT_MIN_WORDS", "6"))

# Claims required to carry a point. A point served by one claim IS that claim, and
# promoting it promises the reader more than the paper delivers.
POINT_MIN_CLAIMS = int(os.environ.get("PAPER_POINT_MIN_CLAIMS", "2"))

# What share of claims may declare a `setup` or `reporting` role instead of serving a
# point. A paper cannot be all argument — the cohort has to be described before
# anything is claimed about it — but an unbounded exemption turns the ladder into
# decoration, and "setup" is the easiest label in the world to reach for. A third is
# generous for a clinical paper with a long Methods.
ROLE_CLAIM_SHARE_MAX = float(os.environ.get("PAPER_ROLE_CLAIM_SHARE_MAX", "0.34"))

# What share of the planned WORDS may sit in sections that serve no point. This is the
# check that catches the real failure, because a graph check only asks whether every
# claim has a parent and a determined writer satisfies that by attaching claims
# loosely. Length cannot be argued with. The warn threshold exists because this share
# grows quietly, one complete and irrelevant section at a time.
UNLADDERED_WORDS_WARN = float(os.environ.get("PAPER_UNLADDERED_WORDS_WARN", "0.15"))
UNLADDERED_WORDS_MAX = float(os.environ.get("PAPER_UNLADDERED_WORDS_MAX", "0.30"))

# The other half of the budget: how much of the paper ONE claim may consume.
#
# The unladdered budget above catches material attached to nothing. It does not catch
# material attached to something and then elaborated out of all proportion — a whole
# supplement section, with a rubric, two verbatim prompts, four worked examples and a
# re-judging experiment, in service of a single null result about a weighting scheme
# layered on a predictor the paper had already reported as not competitive. Every one
# of those words laddered. The section served a point. It was still four times the
# length its claim could carry.
#
# So a claim also has a ceiling. It WARNS rather than blocks, and the reason is worth
# stating: word share is a proxy for proportion, and a proxy that stalls a run is a
# proxy somebody raises until it stops firing. A headline claim legitimately owns a
# large share of a short paper. What the warning is for is the strand nobody decided
# to stop writing, surfaced where an author can look at it.
CLAIM_WORDS_WARN = float(os.environ.get("PAPER_CLAIM_WORDS_WARN", "0.25"))

# One case does block, because it is not a proxy for anything. A LIMITATION written at
# the length of a finding reads as a finding — the caveat stops qualifying the result
# and starts competing with it. A caveat is a paragraph. If it needs a section, it is
# not a caveat, and the honest repair is to promote it to a claim that serves a point
# or to cut it.
CLAIM_WORDS_MAX_MINOR = float(os.environ.get("PAPER_CLAIM_WORDS_MAX_MINOR", "0.12"))
CLAIM_MINOR_KINDS = ("limitation",)

# Paragraphs in a section that may advance no claim, as a share. A transition and a
# closing line are legitimate; a section of them is a section with no argument in it.
PARAGRAPH_ROLE_SHARE_MAX = float(
    os.environ.get("PAPER_PARAGRAPH_ROLE_SHARE_MAX", "0.34"))

# How many sections the argument stage plans per model call. A paper is small enough
# that this is usually the whole thing in one call; the chunking exists so a
# multi-paper project cannot produce an artifact too large to write in one turn.
ARGUMENT_CHUNK_SECTIONS = int(os.environ.get("PAPER_ARGUMENT_CHUNK_SECTIONS", "12"))

# --- Shipping ----------------------------------------------------------------
#
# Delivery puts the documents on disk. If that disk is a git working tree, the work is
# not anywhere until somebody commits it, and that is the step that gets forgotten for
# a week while the author believes the paper is filed. So the pipeline can finish the
# job — but pushing to a remote is the only outward-facing thing this harness does, so
# both halves are opt-in and the machinery is deliberately narrow. See
# `infra/shipping.py` for what it refuses and why.

# The git working tree to commit delivered papers into. Empty means never commit.
# Only files delivery actually wrote are staged, by path; there is no `git add -A`
# anywhere, because a daemon that swept the tree would eventually commit half of an
# unrelated edit under a message about a manuscript.
SHIP_REPO = _env_path("PAPER_SHIP_REPO", None) if os.environ.get("PAPER_SHIP_REPO") \
    else None

# Whether to push after committing. A separate switch from SHIP_REPO because a local
# commit is reversible by one command and a push is not.
SHIP_PUSH = _env_flag("PAPER_SHIP_PUSH", False)

# --- Building ----------------------------------------------------------------
#
# The manuscript is authored in Markdown and built to the format a journal actually
# accepts. Pandoc does the conversion; a reference .docx supplies the styles.
#
# **Why this is a search and not a string.** Pandoc is very often installed somewhere
# that is not on PATH — inside a conda distribution, inside an RStudio Server tree,
# inside a Quarto bundle. On the machine this harness was written on it lives in an
# Anaconda `bin/` whose `condabin/` is on PATH and whose `bin/` is not. Defaulting to
# the bare name "pandoc" then means conversion silently does not happen, the run
# reports success because the Markdown IS the deliverable, and the .docx beside it
# quietly goes stale. That is the worst of the three outcomes: not a failure, not a
# conversion, just an old file that still looks like an artifact.
#
# So the default resolves: PATH first, then the usual places, and only then the bare
# name, which at least produces a clear error. An explicit PAPER_PANDOC_BIN always
# wins and is never second-guessed.
_PANDOC_CANDIDATES = (
    "/opt/apps/easybuild/software/Anaconda3/2025.06-0/bin/pandoc",
    "/usr/lib/rstudio-server/bin/pandoc/pandoc",
    "/usr/lib/rstudio/bin/pandoc/pandoc",
    "/opt/quarto/bin/tools/pandoc",
    "/usr/local/bin/pandoc",
)


def _find_pandoc():
    explicit = os.environ.get("PAPER_PANDOC_BIN", "").strip()
    if explicit:
        return explicit
    found = shutil.which("pandoc")
    if found:
        return found
    for candidate in _PANDOC_CANDIDATES:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    for root in (os.environ.get("CONDA_PREFIX"), os.environ.get("CONDA_EXE")):
        if not root:
            continue
        base = Path(root)
        base = base.parent.parent if base.is_file() else base
        candidate = base / "bin" / "pandoc"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return "pandoc"


PANDOC_BIN = _find_pandoc()

# The output formats built for every finished paper, in order. Markdown is always
# kept — it is the source — so this is what is built FROM it.
BUILD_FORMATS = tuple(f.strip() for f in
                      os.environ.get("PAPER_BUILD_FORMATS", "docx").split(",")
                      if f.strip())

# --- PDF, which is a different machine from .docx ----------------------------
#
# A .docx is a zip pandoc writes itself. A PDF goes through a TeX engine, and two
# of the defaults are wrong for a manuscript full of statistics.
#
# pdflatex REFUSES a Unicode minus. `difference +0.008 (−0.001 to 0.017)` stops the
# run with "Unicode character − (U+2212) not set up for use with LaTeX", and a paper
# that reports differences has hundreds of them. xelatex reads UTF-8, so it is the
# default here rather than pandoc's.
#
# And xelatex's own default face is Latin Modern, which has no ₀₈₉, no ρ and no ≈.
# Pandoc reports each one as "Missing character" on stderr and exits 0, so the symbol
# is simply not on the page — a ρ dropped out of "ρ = 0.41" is a silent change to what
# the paper says, in the direction nobody checks. So the face is named, and it is one
# with the coverage: DejaVu Sans is installed on every machine this runs on.
#
# Both are overridable because a journal that wants a serif is a real request and this
# is not the place to argue with it — but then the glyph coverage is the setter's
# problem, and a run that starts reporting missing characters is why.
PDF_ENGINE = os.environ.get("PAPER_PDF_ENGINE", "xelatex").strip() or "xelatex"
PDF_MAINFONT = os.environ.get("PAPER_PDF_MAINFONT", "DejaVu Sans").strip()
PDF_MONOFONT = os.environ.get("PAPER_PDF_MONOFONT", "DejaVu Sans Mono").strip()

# A reference document supplying the journal's styles, if the project has one. The
# job prompt may name one per paper; this is the fallback.
_REFDOC_RAW = os.environ.get("PAPER_REFERENCE_DOCX", "").strip()
REFERENCE_DOCX = Path(_REFDOC_RAW).expanduser() if _REFDOC_RAW else None

# Whether a build failure blocks delivery. It does not: the Markdown IS the
# manuscript, and a missing pandoc must never be why a finished paper is not
# delivered.
BUILD_REQUIRED = _env_flag("PAPER_BUILD_REQUIRED", False)

# Extra directories on pandoc's resource path, for every conversion. Colon-separated.
#
# **What this is for, and why it is not PAPER_SOURCE_DIRS.** A manuscript refers to its
# figures the way the FINISHED paper will: `![](../results/roc.png)`, relative to the
# folder the document will live in. The harness converts in the state tree, where that
# path resolves to nothing, so pandoc drops the figure — and a dropped figure is a
# warning on stderr and a zero exit status, which is to say silence.
#
# The fix cannot be "add the analysis tree", because the `..` is doing the work: what
# pandoc needs is a directory whose SIBLING is the results folder, not the results
# folder itself. Only the author knows which directory that is, so this is a knob and
# not a search. Set it to the folder the delivered paper will sit in:
#
#   PAPER_BUILD_RESOURCE_DIRS=$HOME/Research-Journey/paper1-trd-prediction
#
# Leaving it empty is correct for a paper with no figures, which is every paper this
# harness writes on its own — it has no way to emit an image reference, and "figure" in
# every one of its prompts means a number. This exists for the manuscript a person has
# since put figures into, which is every manuscript, eventually.
_BUILD_RESOURCE_RAW = os.environ.get("PAPER_BUILD_RESOURCE_DIRS", "")
BUILD_RESOURCE_DIRS = tuple(
    Path(d).expanduser() for d in _BUILD_RESOURCE_RAW.split(os.pathsep) if d.strip())

# --- Stalling: what happens instead of failing -------------------------------
#
# Nothing in this harness has a terminal failure state. A unit that cannot advance
# stalls, and a stalled unit is retried on an escalating backoff, forever — because
# an API outage, an allowance ceiling, and a full disk all resolve on their own or
# when a person acts, and none of them is a reason to abandon a manuscript.
STALL_BACKOFF_BASE_SEC = int(os.environ.get("PAPER_STALL_BACKOFF_BASE_SEC", "300"))
STALL_BACKOFF_MAX_SEC = int(os.environ.get("PAPER_STALL_BACKOFF_MAX_SEC", "3600"))

# --- Retry caps --------------------------------------------------------------

# How many words of the previous section's closing prose the writer is shown, so the
# join between two sections reads as one document.
DIGEST_PREV_TAIL_WORDS = int(os.environ.get("PAPER_DIGEST_PREV_TAIL_WORDS", "300"))

# Infrastructure failures inside one section stage before the paper stalls.
SECTION_STAGE_ERROR_RETRIES = 3

# How many times a stage may re-propose after a GATE rejection. Distinct from the
# transient cap below: this counts a model that produced a real artifact the gates
# refused, which is judgement, not infrastructure.
GATE_MAX_ATTEMPTS = int(os.environ.get("PAPER_GATE_MAX_ATTEMPTS", "3"))

# Transient subprocess failures: a killed process, a dropped connection.
TRANSIENT_MAX_ATTEMPTS = 4
TRANSIENT_RETRY_BACKOFF_SEC = 20

# Substrings that identify a failure as transient rather than terminal.
TRANSIENT_SIGNATURES = (
    "connection reset", "connection refused", "connection aborted",
    "timed out", "timeout", "temporarily unavailable", "service unavailable",
    "bad gateway", "gateway timeout", "internal server error",
    "502", "503", "504", "econnreset", "etimedout", "socket hang up",
    "overloaded", "please try again", "stream closed", "broken pipe",
)

# Substrings that identify an allowance ceiling. Never a failure: the engine defers.
QUOTA_SIGNATURES = (
    "usage limit", "rate limit", "rate_limit", "quota", "429",
    "too many requests", "insufficient credit", "out of credit",
    "resource exhausted", "resource_exhausted",
)

# --- Budget gating -----------------------------------------------------------

# A JSON file the operator can edit to pause the harness or cap what it spends.
BUDGET_FILE = _env_path("PAPER_BUDGET_FILE", STATE_DIR / "budget.json")

# --- Loop cadence ------------------------------------------------------------

POLL_INTERVAL_SEC = 5      # brisk poll while any unit is active
IDLE_INTERVAL_SEC = 30     # slow poll when the inbox and journal are quiet

# --- Quiet hours: when the harness must not compete with its owner ------------
#
# Off by default here, unlike the novel factory this grew out of: a paper is a few
# hours of work rather than an overnight run, and an author waiting on a Methods
# section does not want it deferred until five o'clock.
QUIET_HOURS_ENABLED = _env_flag("PAPER_QUIET_HOURS", False)
QUIET_START_HOUR = int(os.environ.get("PAPER_QUIET_START_HOUR", "9"))
QUIET_END_HOUR = int(os.environ.get("PAPER_QUIET_END_HOUR", "17"))

QUIET_DAYS = tuple(
    int(d) for d in os.environ.get("PAPER_QUIET_DAYS", "0,1,2,3,4").split(",")
    if d.strip().isdigit())

QUIET_RECHECK_SEC = int(os.environ.get("PAPER_QUIET_RECHECK_SEC", "600"))
