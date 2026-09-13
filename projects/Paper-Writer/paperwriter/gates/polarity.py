"""One thing asserted and then denied — sameness, in both directions, about the same
noun.

Every gate here measures a sentence, a paragraph, or a count. None of them reads two
sentences and notices that the paper has contradicted itself, and `repetition` is the
near miss: it finds a point made three times and forgives a point made twice, which is
exactly the count a contradiction has.

**The failure this was written from.** A Methods section said, in bold, that *both
representations were built from the same curated field inventory*. Twenty-five lines
later the same section said that *FEATURE and EMBEDDED do not receive an identical
field inventory*. Both sentences were true, because the first was about which fields
predictor selection chose and the second was about how some of those fields were then
encoded. Nothing in either sentence said so. A reader hit the second one, went back to
the first, and stopped trusting the paragraph — which is the one-read rule failing at a
distance no per-sentence check can see.

Every gate in this project passed it. The sentences were short, the paragraphs had
topic sentences, the vocabulary was locked, the numbers were in the ledger, and the two
claims were a page apart in the same section.

**What it measures.** Sentences asserting that two things are *the same* or *identical*
in some respect, keyed on the head noun of that respect. When one document asserts
sameness on a noun and also denies it on the same noun, both sentences are reported as
a pair. The polarity is read from the clause the marker sits in, not the sentence, so
"built from the same inventory, and neither was built from a raw record" is one
assertion rather than an assertion and a denial.

**Why it is advisory.** The gate cannot see subjects. A paper may legitimately say that
A and B share a cohort while C and D do not, and that is a pair here. So this reports a
pair to be read rather than a defect to be fixed, and the fix, when there is one, is
usually a word: the two sentences are about different senses of one noun and neither
one names its sense.

Set overlap and a negator list. No model, no I/O.
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field

from .. import config
from . import prose

# The assertion of sameness. `identical` alone, because "an identical field inventory"
# carries no "the same".
_MARKER_RE = re.compile(r"\b(?:same|identical)\b", re.IGNORECASE)

# What turns the clause into a denial. `rather than` is here because "estimates the
# pipelines rather than the same effect" denies the sameness it names, and `without`
# for the same reason.
_NEGATORS = (
    "not", "n't", "never", "no", "none", "neither", "nor", "without", "cannot",
    "rather than", "fails to", "fail to", "failed to", "ceases to",
)

# What makes the sameness claim conditional rather than asserted. "only a comparison
# of encodings to the extent that both carry the same information" does not say they
# do; it says what follows if they do, and the table underneath is the paper checking
# it. A conditional is neither side of a contradiction, so it is dropped rather than
# bucketed — the first version of this gate counted them as assertions and reported a
# supplement section as contradicting the sentence that introduced it.
_CONDITIONALS = (
    "to the extent that", "insofar as", "in so far as", "if", "unless", "whether",
    "assuming", "provided that", "only where", "only when", "would", "were they to",
)

# Clause boundaries, for reading polarity at the clause rather than the sentence. A
# negator on the far side of one of these governs a different claim.
_CLAUSE_RE = re.compile(
    r",|;|:|\(|\)|\band\b|\bbut\b|\bso\b|\byet\b|\bor\b|\bwhile\b|\bwhereas\b"
    r"|\bbecause\b|\balthough\b|\bthough\b|\bwhich\b|\bwhereby\b", re.IGNORECASE)

# The words that end a noun phrase. Everything between the marker and one of these is
# the respect in which two things are, or are not, the same.
_PHRASE_END = frozenset("""
of to in on for with by from as at is are was were be been being and or but not nor so
that this these those it its their they them we our us he she which who whose than
then there here into over under about above each both all any some more most other
such only own very can will just do does did if when while because across between
""".split())

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z-]*")

# Nouns too general to key on. "the same thing", "the same way", "the same time" name
# no respect at all, and keying on them collides every sentence in the paper.
_EMPTY_HEADS = frozenset("""
thing things way ways time times sense senses respect respects direction directions
place places point points kind kinds order reason reasons manner extent
""".split())

_CAPTION_RE = re.compile(r"\*{2,3}\s*(?:Table|Figure|Fig\.?|Panel)\b"
                         r"|\*\*\([A-Za-z0-9]+\)", re.IGNORECASE)

_SECTION_RE = re.compile(r"^(#{1,2})\s+(.+?)\s*$", re.MULTILINE)


@dataclass
class Clash:
    """One noun asserted same and denied same, with a sentence for each side."""
    noun: str
    asserted: list = field(default_factory=list)     # (section, sentence)
    denied: list = field(default_factory=list)       # (section, sentence)

    def reason(self):
        here = self.asserted[0]
        there = self.denied[0]
        return (f'"{self.noun}" is called the same in {here[0] or "the document"} and '
                f'not the same in {there[0] or "the document"}. Both may be true of '
                f'different senses of "{self.noun}", and a reader who hits the second '
                f"sentence goes back to the first. Name the sense in each, or drop "
                f"one.")


@dataclass
class PolarityReport:
    clashes: list = field(default_factory=list)
    checked: int = 0              # sameness assertions found
    passed: bool = True
    reasons: list = field(default_factory=list)

    def brief(self):
        return (f"{self.checked} sameness claim(s), {len(self.clashes)} asserted and "
                f"denied on one noun")


def _singular(word):
    """Crude enough. "inventories" and "inventory" have to key together, and nothing
    downstream depends on the result being a real lemma."""
    low = word.lower()
    if low.endswith("ies") and len(low) > 4:
        return low[:-3] + "y"
    if low.endswith("sses") or low.endswith("ches") or low.endswith("shes"):
        return low[:-2]
    if low.endswith("s") and not low.endswith("ss") and len(low) > 3:
        return low[:-1]
    return low


def _respect(sentence, at):
    """The head noun of the phrase the sameness marker modifies, or "".

    Walks forward from the marker over the noun phrase and returns its last token. The
    modifiers are deliberately discarded: "the same curated field inventory" and "an
    identical field inventory" are one claim about one noun, and keying on the full
    phrase is how the pair that motivated this module escapes.

    `of` is walked through once rather than treated as the end of the phrase, because
    "the same set of values" is a claim about values and "an identical set of rendered
    fields" is a claim about fields. Keying both on "set" made them a pair, and they
    are two unrelated sentences in two unrelated sections."""
    tail = sentence[at:]
    head = ""
    hopped = False
    for match in _TOKEN_RE.finditer(tail):
        token = match.group(0).lower()
        if token in _PHRASE_END:
            if token == "of" and head and not hopped:
                hopped, head = True, ""
                continue
            break
        head = match.group(0)
        if match.end() > 80:
            break
    return _singular(head) if head else ""


def _clause(sentence, at):
    """The clause the marker at `at` sits in, lowercased."""
    start = 0
    for boundary in _CLAUSE_RE.finditer(sentence[:at]):
        start = boundary.end()
    return sentence[start:at].lower()


def _holds(phrases, clause):
    return any(re.search(r"\b" + re.escape(p) + r"\b", clause) for p in phrases)


def _body_sentences(text):
    """Every body-prose sentence with the section it sits in. Front matter, back matter
    and captions are dropped, on the same list `repetition` uses: an abstract restates
    the paper, and its sameness claims are the manuscript's own, counted twice."""
    exempt = {s.lower() for s in config.ECHO_EXEMPT_SECTIONS}
    parts = _SECTION_RE.split(text or "")
    out = []
    for i in range(1, len(parts), 3):
        name = parts[i + 1].strip()
        body = parts[i + 2] if i + 2 < len(parts) else ""
        if name.lower() in exempt:
            continue
        for sentence in prose.sentences(prose.strip_structure(body)):
            if _CAPTION_RE.search(sentence):
                continue
            out.append((name, sentence))
    return out


def check(text):
    """Find nouns this document calls the same in one place and not the same in
    another."""
    asserted = defaultdict(list)
    denied = defaultdict(list)
    checked = 0

    for name, sentence in _body_sentences(text):
        flat = " ".join(sentence.split())
        for marker in _MARKER_RE.finditer(flat):
            noun = _respect(flat, marker.end())
            if not noun or noun in _EMPTY_HEADS:
                continue
            clause = _clause(flat, marker.start())
            if _holds(_CONDITIONALS, clause):
                continue
            checked += 1
            bucket = denied if _holds(_NEGATORS, clause) else asserted
            if (name, flat) not in bucket[noun]:
                bucket[noun].append((name, flat))

    clashes = []
    for noun in sorted(set(asserted) & set(denied)):
        clashes.append(Clash(noun=noun, asserted=asserted[noun], denied=denied[noun]))

    return PolarityReport(
        clashes=clashes, checked=checked, passed=not clashes,
        reasons=[c.reason() for c in clashes])
