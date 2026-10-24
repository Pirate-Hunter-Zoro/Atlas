"""Paragraph shape — a claim, its support, and its consequence.

A paragraph in a paper does one job: it makes a single claim, supports it, and says
what follows. A reader who has read only the first and last sentence of every
paragraph should come away with the argument. That is not a style preference, it is
how a paper gets read: a reviewer under time pressure reads openers, and an author who
buried the claim in sentence four has written a paper nobody read.

**What this gate can and cannot do.** It cannot tell whether a topic sentence is
*good*. It can catch every structural way a paragraph fails to have one, and that
turns out to be most of the failures:

  * **It opens on a citation.** "Smith et al. found that..." begins with somebody
    else's authority instead of this paper's claim.
  * **It opens on a number or a statistic.** "Of the 42,579 patients, 3,105..." is a
    result looking for the sentence that should have introduced it.
  * **It opens on a connective.** "However," "Furthermore," "In addition," — a
    paragraph that opens on a hinge is a continuation of the one before it, and the
    two should be one paragraph or two claims.
  * **It opens on a subordinate clause.** "Because the cohort was retrospective,
    ..." delays the claim past the comma. The claim goes first.
  * **It is one sentence long.** A single sentence cannot be a claim plus anything. It
    is usually a fact that escaped from the paragraph above it, which is exactly how
    one appears after a compression pass.

    The floor is two and not three, and the difference was settled by reading rather
    than by reasoning. Three refused eight paragraphs in a real manuscript and was
    wrong about seven: an attrition statement with nothing more to say, a lead-in
    before a run of bolded subsections, a claim and the consequence it licenses, and
    the compact findings a Conclusions section is made of. Whether two sentences are
    enough is a question about the section, and the OUTLINE answers it by naming a
    topic sentence for every planned paragraph.
  * **It runs past nine sentences, or past a hundred and twenty words.** Either one
    is two claims, and the reader is being asked to work out where one ended. The two
    catch different failures and neither subsumes the other: nine short sentences is
    two claims as surely as five long ones, and a 155-word block of five is what a
    paragraph that grew by accretion looks like.
  * **It ends on a citation or a bare number.** The last sentence should say what the
    paragraph means, not cite one more source.
  * **It ends on a signpost.** "The full encoding rules are described in Supplement
    M5 and two example narratives are reproduced in Supplement S5" tells the reader
    where to go instead of what the paragraph established. A cross-reference is
    support, exactly as a citation is, and it belongs under the claim rather than in
    the position the claim should hold.

**The share, not the count.** A section fails when too *many* of its paragraphs break
shape, not when one does. A one-sentence paragraph is right at the end of a
Discussion; a bulleted list is a paragraph to the parser and has no topic sentence by
design. Gating on any single defect would produce a gate that fires on every section
and is therefore ignored.

**And the share needs a denominator.** Under `PARAGRAPH_DEFECT_MIN_PARAGRAPHS` the
ratio is arithmetic rather than measurement — "1 of 1 paragraphs are mis-shaped
(100%)" on a twenty-word back-matter section is a blocking finding about nothing. The
defects are still reported; the section-level verdict is withheld.

**Two things this gate checks that are not paragraph shape**, and both are about
POSITION rather than about the paragraph they sit in, which is why they are section
reasons and not defects diluted in the share:

  * **A section may not open on a roadmap.** A first paragraph whose subject is the
    document rather than its content — "the results are reported in the order of the
    two objectives", "this section describes..." — spends the first thing a reader
    reads on what the table of contents already told them. It is one paragraph of
    twenty-four in the section where it was found, invisible under any share ceiling,
    and the first thing on the page.
  * **A Results paragraph's opening sentence carries its figure.** When the claim IS
    a number, the claim and the number belong in the same sentence. This one advises
    rather than blocks: a short report whose findings are qualitative is legitimate
    and scores badly here.

Pure arithmetic and pattern matching. No model.
"""

import re
from dataclasses import dataclass, field

from .. import config
from . import numbers, prose

# A citation marker in any of the three styles a manuscript here uses: a numbered
# marker, an author-year parenthetical, or a pandoc-style @key.
_CITATION_OPENERS = (
    re.compile(r"^\s*\[\s*\d"),                          # [1], [12,14]
    re.compile(r"^\s*\(\s*[A-Z][A-Za-z'’-]+[,\s]"),      # (Smith, 2024)
    re.compile(r"^\s*@[A-Za-z]"),                        # @smith2024
    re.compile(r"^\s*[A-Z][A-Za-z'’-]+\s+(?:et\s+al\.?|and\s+[A-Z][A-Za-z'’-]+)"
               r"\s+(?:\(\d{4}\)|\[\d)"),                # Smith et al. (2024)
)

_NUMBER_OPENER = re.compile(r"^\s*[\(\[]?[-+]?\d")

# A pointer to somewhere else in the document. Same family as a citation: it is where
# the support lives, not what the paragraph means.
_CROSSREF_RE = re.compile(
    r"(?<![A-Za-z])(?:supplement(?:ary)?(?:\s+(?:material|table|figure|file))?|"
    r"appendix|table|figure|fig\.?|section|panel|supplementary)\s*"
    r"(?:[SMEA]?\d+|[SMEA]\d*)\b", re.IGNORECASE)

# The frames that make a pointer the whole sentence rather than a note attached to a
# claim. "Discrimination was flat across encoders, as shown in Figure 3" ends on its
# finding and merely says where to look, so every frame here is rejected when "as"
# precedes it — that one word is the difference between a signpost and an attachment.
_SIGNPOST_RE = re.compile(
    r"(?<![A-Za-z])(?:see|are\s+(?:described|reported|given|reproduced|listed|shown|"
    r"provided|summarised|summarized|detailed|presented|tabulated|found|set\s+out)|"
    r"is\s+(?:described|reported|given|reproduced|listed|shown|provided|summarised|"
    r"summarized|detailed|presented|tabulated|found|set\s+out)|"
    r"(?:full\s+)?details\s+(?:are|is|appear)|refer\s+to)\s+", re.IGNORECASE)

_AS_ATTACHED_RE = re.compile(r"(?<![A-Za-z])as\s+$", re.IGNORECASE)


def _ends_on_signpost(sentence):
    """Whether the last sentence points somewhere instead of concluding.

    Requires both halves: a cross-reference AND a frame that makes the pointer the
    sentence's own business. A trailing "(Table 2)" on a sentence that states a result
    is not this defect, and neither is "as shown in Figure 3"."""
    if not _CROSSREF_RE.search(sentence):
        return False
    for match in _SIGNPOST_RE.finditer(sentence):
        if _AS_ATTACHED_RE.search(sentence[:match.start()]):
            continue
        if _CROSSREF_RE.search(sentence[match.end():]):
            return True
    # "The field-level crosswalk, row by row, is Supplement S10." No signpost verb at
    # all: the cross-reference is the predicate.
    return bool(re.search(r"(?<![A-Za-z])(?:is|are|was|were)\s+(?:in\s+)?"
                          r"(?:supplement|appendix|table|figure|section)\b",
                          sentence, re.IGNORECASE))

# Connectives that make a sentence a hinge rather than a claim.
_CONNECTIVES = (
    "however", "furthermore", "moreover", "in addition", "additionally",
    "nevertheless", "nonetheless", "therefore", "thus", "hence", "consequently",
    "on the other hand", "by contrast", "in contrast", "similarly", "likewise",
    "that said", "meanwhile", "also", "second", "third", "finally", "lastly",
    "next", "then",
)

# Openers that delay the claim past a comma.
_SUBORDINATORS = (
    "because", "although", "though", "while", "whereas", "since", "given that",
    "if", "unless", "when", "after", "before", "as ", "in order to", "to assess",
    "to evaluate", "to determine", "having",
)


def _starts_with(sentence, phrases):
    low = sentence.lower().lstrip("\"'“‘([ ")
    for phrase in phrases:
        if low.startswith(phrase):
            # A whole word, not a prefix: "thus" matches, "thusly" does not, and
            # "as " already carries its own boundary.
            rest = low[len(phrase):]
            if not rest or not rest[0].isalpha():
                return phrase
    return ""


def _opens_on_citation(sentence):
    return any(pattern.match(sentence) for pattern in _CITATION_OPENERS)


def _delays_the_claim(sentence):
    """Whether the sentence buries its claim behind a subordinate clause.

    Only counts when the clause actually runs long enough to be in the way. "If so,
    the estimate is biased" puts the claim three words in and is fine."""
    phrase = _starts_with(sentence, _SUBORDINATORS)
    if not phrase:
        return ""
    head, _, tail = sentence.partition(",")
    if not tail.strip():
        return ""                       # no comma: it is one clause, not two
    return phrase if len(head.split()) >= 6 else ""


# The one defect kind that is reported and never counted toward the section's share.
LONG_IN_WORDS = "too long (words)"


@dataclass
class ParagraphDefect:
    index: int                # 1-based position in the section
    kind: str                 # what is wrong
    detail: str               # one sentence a person can act on
    anchor: str               # the exact sentence to repair, or "" when it is shape


@dataclass
class ParagraphReport:
    total: int
    checked: int              # paragraphs the shape rules applied to
    defects: list = field(default_factory=list)
    share: float = 0.0
    passed: bool = True
    reasons: list = field(default_factory=list)
    advisories: list = field(default_factory=list)   # reported, never blocking
    results_topic_share: float = None                # None when not measured

    def brief(self):
        return (f"{self.total} paragraphs, {len(self.defects)} shape defect(s) "
                f"across {self.checked} checked ({self.share:.0%})")


# A figure or table caption, or a panel label. Written `***Table S3.** ...*` or
# `**(A) Nearest retrieval**`, both of which the parser sees as a paragraph.
#
# The third form carries no emphasis at all: `Table 1. Cohort characteristics.` is
# what `pandoc -f docx` writes, because Word holds the caption's styling outside the
# text. Requiring emphasis missed every caption in a returned manuscript and measured
# seven of them as one-sentence paragraphs. The label, its number and the stop that
# follows are what make it a caption; the punctuation after the number is what keeps
# the pattern off "Table 2 gives every selected characteristic", which is prose.
_CAPTION_RE = re.compile(r"^\s*(?:\*{2,3}\s*(?:Table|Figure|Fig\.?|Panel)\b"
                         r"|\*\*\([A-Za-z0-9]+\)"
                         r"|(?:Table|Figure|Fig\.|Panel)\s*S?\d+\s*[.:])",
                         re.IGNORECASE)


def _is_caption(paragraph):
    """Whether a block is a caption or a panel label rather than a paragraph.

    A caption describes a figure. It has no topic sentence and no concluding sentence
    by design, and it is routinely one or two sentences long. Judging it against
    paragraph shape produces a defect on every figure in a supplement, which is how a
    gate stops being read. Its SENTENCES are still measured — a caption a reader
    cannot parse is a real defect — only its shape is exempt."""
    return bool(_CAPTION_RE.match(paragraph))


# A block that is nothing but an emphasized label, and a thematic break. Neither is a
# paragraph.
#
# "**TRD-positive example.**" above a fenced narrative and "**(A) Nearest retrieval**"
# above a figure are labels: they name what follows, they have no claim and no support,
# and they are one "sentence" long by construction. A `---` rule is not even text. The
# paragraph parser sees all three as blocks, so a supplement section reproducing two
# example narratives reported three too-short paragraphs out of six and failed at 50%,
# on two labels and a horizontal rule.
#
# The label rule is deliberately narrow: the WHOLE block has to be emphasis, so
# "**Strata.** Six sociodemographic families and two clinical ones." is still a
# paragraph and still checked. A run-in heading with prose after it is prose.
_LABEL_ONLY_RE = re.compile(r"^\s*(?:\*{1,3}|_{1,3})[^*_]{1,120}(?:\*{1,3}|_{1,3})"
                            r"\s*$")
_THEMATIC_BREAK_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")


def _is_label(paragraph):
    """Whether a block is a standalone label or a horizontal rule rather than prose."""
    return bool(_THEMATIC_BREAK_RE.match(paragraph)
                or _LABEL_ONLY_RE.match(paragraph))


def _introduces_a_list(paragraph):
    """Whether a block is a stem introducing a list rather than a paragraph.

    A block ending in a colon is, by definition, pointing at what comes next. Its
    support is the list beneath it, so judging it as a paragraph with no support is
    both wrong and actively harmful: the writer's repair for a long sentence is to
    break it into a stem and a list, and this rule is what stops the gate from calling
    that repair a defect."""
    return paragraph.rstrip().endswith(":")


# A first paragraph whose subject is the document rather than its content.
#
# Two families, and they are matched differently because they fail differently.
#
# The first names the document's own organization, and it is a defect wherever in the
# opening paragraph it appears: "the results are reported in the order of the two
# objectives", "the remainder of this section". The reader has the headings.
#
# The second is a self-reference verb, and it is only a defect at the START of the
# first sentence and only outside the sections whose job is to say what the paper
# does. "Here we report" as the close of an Introduction is the standard purpose
# statement of a scientific paper, not a roadmap, and refusing it would be the gate
# fighting the one place the construction belongs.
_ROADMAP_ORG_RE = re.compile(
    r"(?:are|is)\s+(?:reported|presented|organi[sz]ed|described|given|set\s+out)"
    r"\s+in\s+the\s+order"
    r"|is\s+organi[sz]ed\s+as\s+follows"
    r"|in\s+what\s+follows"
    r"|the\s+(?:remainder|rest)\s+of\s+(?:this|the)\s+"
    r"(?:section|paper|manuscript|supplement|appendix)"
    r"|comes?\s+first,\s+then"
    r"|the\s+following\s+(?:section|subsection|paragraph)s?\b",
    re.IGNORECASE)

_ROADMAP_SELF_RE = re.compile(
    r"^\s*(?:This\s+(?:section|subsection|supplement|appendix)\s+"
    r"(?:describes|reports|presents|summari[sz]es|covers|details|provides|"
    r"contains|documents|lists)"
    r"|Here\s+we\s+(?:describe|report|present|summari[sz]e|list|document))",
    re.IGNORECASE)

# Where a purpose statement is the section's job rather than a roadmap.
_PURPOSE_SECTIONS = ("abstract", "introduction", "background")


def _opens_on_a_roadmap(paragraph, section_name=""):
    """The roadmap phrase a section's first paragraph opens on, or "".

    Only the first paragraph of a section is asked. A sentence in the middle of a
    Methods section saying where the fuller specification lives is a signpost, which
    is a different rule and a milder one."""
    match = _ROADMAP_ORG_RE.search(paragraph)
    if match:
        return " ".join(match.group(0).split())
    if prose.section_matches(section_name, _PURPOSE_SECTIONS):
        return ""
    sents = prose.sentences(paragraph)
    match = _ROADMAP_SELF_RE.match(sents[0]) if sents else None
    return " ".join(match.group(0).split()) if match else ""


# The manuscript's Results section, by its own heading. A supplement section that
# happens to be called "Results" is not it, which is why the caller says which
# document this is.
_RESULTS_HEADINGS = ("results", "findings")


def _results_topic_share(blocks, body):
    """(share, checked, openers-without-a-figure) for a Results section, or None.

    None when the section is too short to measure or is not reporting figures at all.
    A Results section that names its predictors rather than measuring them reports in
    words and is correct; the density guard is what keeps the rule off it."""
    firsts = []
    for _, paragraph in blocks:
        sents = prose.sentences(paragraph)
        if sents:
            firsts.append(sents[0])
    if len(firsts) < config.RESULTS_TOPIC_MIN_PARAGRAPHS:
        return None
    stripped = prose.strip_structure(body)
    words = prose.word_count(stripped)
    if not words:
        return None
    density = 100.0 * len(numbers.extract(stripped)) / words
    if density < config.RESULTS_TOPIC_DENSITY_MIN:
        return None
    bare = [s for s in firsts if not numbers.extract(s)]
    return (len(firsts) - len(bare)) / len(firsts), len(firsts), bare


def _check_one(index, paragraph, signposts_count=True):
    """Every shape defect in one paragraph.

    `signposts_count` is False in a methods section, where a closing cross-reference
    is the paragraph's conclusion — see `config.SIGNPOST_EXEMPT_SECTIONS`."""
    out = []
    sents = prose.sentences(paragraph)
    if not sents:
        return out

    first, last = sents[0], sents[-1]

    if len(sents) < config.PARAGRAPH_MIN_SENTENCES:
        out.append(ParagraphDefect(
            index, "too short",
            f"paragraph {index} is {len(sents)} sentence(s). A paragraph is a claim, "
            f"its support, and what follows from it, which takes at least "
            f"{config.PARAGRAPH_MIN_SENTENCES}. Either fold it into the paragraph it "
            f"belongs to or give the claim its support.",
            first))
    elif len(sents) > config.PARAGRAPH_MAX_SENTENCES:
        out.append(ParagraphDefect(
            index, "too long",
            f"paragraph {index} runs {len(sents)} sentences against a ceiling of "
            f"{config.PARAGRAPH_MAX_SENTENCES}. It is carrying two claims. Find where "
            f"the second one starts and break there.",
            first))
    elif prose.word_count(paragraph) > config.PARAGRAPH_MAX_WORDS:
        out.append(ParagraphDefect(
            index, LONG_IN_WORDS,
            f"paragraph {index} runs {prose.word_count(paragraph)} words against a "
            f"ceiling of {config.PARAGRAPH_MAX_WORDS}. Its sentence count is inside "
            f"the band, so this is a paragraph that grew rather than one that welded: "
            f"find the second claim and break there.",
            first))

    if _opens_on_citation(first):
        out.append(ParagraphDefect(
            index, "no topic sentence",
            f"paragraph {index} opens on a citation. Open on this paper's claim and "
            f"cite the support underneath it.",
            first))
    elif _NUMBER_OPENER.match(first):
        out.append(ParagraphDefect(
            index, "no topic sentence",
            f"paragraph {index} opens on a number. A statistic is support, not a "
            f"claim. Say what it shows, then give it.",
            first))
    elif (phrase := _starts_with(first, _CONNECTIVES)):
        out.append(ParagraphDefect(
            index, "hinge opener",
            f"paragraph {index} opens on \"{phrase}\", which makes it a continuation "
            f"of the paragraph before it. Either merge the two or open on the claim "
            f"this paragraph is making.",
            first))
    elif (phrase := _delays_the_claim(first)):
        out.append(ParagraphDefect(
            index, "buried claim",
            f"paragraph {index} opens \"{phrase}...\" and does not reach its claim "
            f"until after the comma. Put the claim first and the condition second.",
            first))

    if len(sents) >= config.PARAGRAPH_MIN_SENTENCES:
        if _opens_on_citation(last):
            out.append(ParagraphDefect(
                index, "no concluding sentence",
                f"paragraph {index} ends on a citation. The last sentence should say "
                f"what the paragraph means for this paper.",
                last))
        elif _NUMBER_OPENER.match(last) and len(last.split()) < 12:
            out.append(ParagraphDefect(
                index, "no concluding sentence",
                f"paragraph {index} ends on a bare number. Close on what it means.",
                last))
        elif signposts_count and _ends_on_signpost(last):
            out.append(ParagraphDefect(
                index, "no concluding sentence",
                f"paragraph {index} ends on a pointer to somewhere else in the "
                f"document. A cross-reference is support, like a citation. Close on "
                f"what this paragraph established and put the pointer under it.",
                last))
    return out


def check(text, section_name="", manuscript=True):
    """Gate a section's paragraph shape. Returns a ParagraphReport.

    `section_name` exempts the sections where the rules do not apply: an abstract is
    one structured block, a declarations section is a list, and references are not
    prose at all. It also turns OFF the closing-signpost rule in a methods section,
    where a pointer at the fuller specification is what the paragraph concludes on
    rather than a substitute for its conclusion.

    `manuscript` says whether this section belongs to the manuscript rather than to a
    supplement, a checklist or a cover letter. Only the Results topic-sentence rule
    reads it, and only because a supplement section called "Results" is not the
    manuscript's Results: measured across a published supplement, half its sections
    open without a number and are right to."""
    if prose.section_matches(section_name, config.PARAGRAPH_EXEMPT_SECTIONS):
        return ParagraphReport(total=0, checked=0, passed=True)

    name = (section_name or "").strip().lower()
    signposts_count = not any(tag in name
                              for tag in config.SIGNPOST_EXEMPT_SECTIONS)

    blocks = prose.paragraphs(text)
    checkable = [(i + 1, p) for i, p in enumerate(blocks)
                 if not prose.is_list_item(p) and not _introduces_a_list(p)
                 and not _is_caption(p) and not _is_label(p)]

    defects = []
    for index, paragraph in checkable:
        defects.extend(_check_one(index, paragraph, signposts_count))

    checked = len(checkable)
    # One paragraph can carry two defects; the share is of paragraphs, not of defects,
    # because that is the question — how much of this section is mis-shaped.
    #
    # EXCEPT THE WORD CEILING, which is reported and does not count. It is a length
    # rule wearing a shape rule's clothes, and unlike every other defect here it did
    # not survive a negative control: Komorowski's published Nature Medicine methods
    # supplement runs 10% of its paragraphs past 120 words with a maximum of 204, which
    # would consume two-thirds of the share allowance before a single real shape defect
    # was counted. See the note above SENTENCE_MID_WORDS in config.py.
    bad = len({d.index for d in defects if d.kind != LONG_IN_WORDS})
    share = 0.0 if not checked else bad / checked

    reasons, advisories = [], []
    if (checked >= config.PARAGRAPH_DEFECT_MIN_PARAGRAPHS
            and share > config.PARAGRAPH_DEFECT_SHARE_MAX):
        kinds = sorted({d.kind for d in defects})
        reasons.append(
            f"{bad} of {checked} paragraphs are mis-shaped ({share:.0%}); the ceiling "
            f"is {config.PARAGRAPH_DEFECT_SHARE_MAX:.0%}. What is wrong: "
            f"{', '.join(kinds)}.")

    if checkable:
        phrase = _opens_on_a_roadmap(checkable[0][1], section_name)
        if phrase:
            reasons.append(
                f"the section opens on a roadmap: \"{phrase}\". The heading has "
                f"already said what the section is about, so the first thing a reader "
                f"reads is the table of contents a second time. Open on the first "
                f"thing this section has to report.")

    topic_share = None
    if manuscript and prose.section_matches(section_name, _RESULTS_HEADINGS):
        measured = _results_topic_share(checkable, text)
        if measured is not None:
            topic_share, n_first, bare = measured
            if topic_share < config.RESULTS_TOPIC_FIGURE_SHARE_MIN:
                advisories.append(
                    f"{topic_share:.0%} of this section's paragraphs open on a "
                    f"sentence carrying a reported figure, against a floor of "
                    f"{config.RESULTS_TOPIC_FIGURE_SHARE_MIN:.0%} over {n_first} "
                    f"paragraphs. When the claim IS a number, the claim and the "
                    f"number go in the same sentence; a bare claim followed by its "
                    f"figure is two sentences doing one sentence's work. The first "
                    f"is \"{bare[0][:70]}...\"")

    return ParagraphReport(total=len(blocks), checked=checked, defects=defects,
                           share=round(share, 4), passed=not reasons, reasons=reasons,
                           advisories=advisories,
                           results_topic_share=(None if topic_share is None
                                                else round(topic_share, 4)))
