"""The venue gate — the journal's own rules, checked before anybody submits.

Every other gate here asks whether the manuscript is good. This one asks whether the
journal will accept the file at all, which is a different question and is answered by
an editorial assistant in about ninety seconds.

**The failure it was written from.** A manuscript went through two full redrafts, every
gate in this project passing on both, carrying an abstract of 810 words against a
venue ceiling of 450. It had been over the ceiling before either redraft and got 41%
worse during them, because nothing was counting. It also carried four URLs in its body
against a checklist that says all URLs are cited as references, and it was missing a
mandatory Abbreviations section outright. None of those is a hard problem to fix. All
of them are desk rejections or fee letters, and all of them were invisible to a
pipeline whose only notion of a venue was one integer called `word_limit`.

**What this gate does not do.** It does not judge. Nothing here is a matter of taste
or of quality; every check is "the venue said a number and the manuscript is on the
wrong side of it". That is what makes the gate cheap to trust and cheap to update: when
a journal changes a rule, one number moves in `venues.py` and the reasoning is a URL.

**Advisory limits are reported, not enforced.** A venue that *recommends* 10,000 words
and charges a fee above it has not set a ceiling, and a gate that blocked there would
refuse legitimate manuscripts. It warns, and it says what the consequence is, because
"you will be invoiced" is the information the author actually needs.

**An unknown venue fails.** Not silently, and not with a pass. Writing to a journal
nobody has profiled is ordinary; doing it while being told the manuscript is compliant
is how the 810-word abstract survived.

**Why the abstract's SHAPE is checked here and nowhere else.** Every prose gate in
this project exempts the abstract, for good reasons that all concern its form: it is
one structured block, its labels are the venue's, and its keyword line is
semicolon-separated by convention. The consequence was that nothing measured the one
section a reader meets detached from the paper. This gate already parses the abstract
and splits it on the venue's own labels, so the two measurements that survive
contact with a real published abstract live here: a hard per-sentence ceiling, and
the balance between the Methods label and the Results label. See
`config.ABSTRACT_SENTENCE_MAX_WORDS` for what was tried and refused.
"""

import re
from dataclasses import dataclass, field

from .. import config, venues
from . import prose


@dataclass
class VenueReport:
    venue: str
    passed: bool
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)


# A manuscript's own top-level headings, so the gate can find its abstract and its
# body without being handed them separately. `prose.strip_structure` is not used here:
# this gate wants the structure.
_HEADING = re.compile(r"^(#{1,2})\s+(.+?)\s*$", re.M)

# Sections that are not body prose for the purpose of a word count. The venue counts
# what a reader reads, and a reference list is not that.
_NOT_BODY = ("title page", "references", "abbreviations")

# A `#` run that is not at the start of its line. Markdown makes a heading only out of
# the ones that are; the rest print verbatim. The preceding character must be
# non-space, which is what separates a swallowed heading from an indented one.
_INLINE_HEADING = re.compile(r"\S[ \t]+#{1,6}[ \t]+\S[^\n]{0,60}")


def sections(text):
    """The manuscript as {heading: body}, in order, comments and code fences gone."""
    text = re.sub(r"<!--.*?-->", "", text or "", flags=re.S)
    text = re.sub(r"^```.*?^```\s*$", "", text, flags=re.S | re.M)
    out, last, start = {}, None, 0
    for m in _HEADING.finditer(text):
        if last is not None:
            out[last] = text[start:m.start()]
        last, start = m.group(2).strip(), m.end()
    if last is not None:
        out[last] = text[start:]
    return out


def abstract_of(parts):
    for heading, body in parts.items():
        if heading.strip().lower() == "abstract":
            return body
    return ""


def body_of(parts):
    """Everything a reader reads, which is not the same as everything in the file."""
    keep = []
    for heading, body in parts.items():
        low = heading.strip().lower()
        if any(low.startswith(x) for x in _NOT_BODY):
            continue
        if low.startswith("multimedia appendix"):
            continue
        keep.append(body)
    return "\n".join(keep)


def abstract_labels(abstract, headings):
    """The abstract as {label: text}, split on the venue's own structural headings.

    Both punctuations, because a venue's template uses one and a builder the other:
    `**Methods.**` and `**Methods:**` are the same label."""
    out, order = {}, list(headings or ())
    if not order:
        return out
    pattern = "|".join(re.escape(h) for h in order)
    marks = list(re.finditer(rf"\*\*({pattern})\s*[.:]?\*\*[.:]?", abstract or "",
                             re.IGNORECASE))
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(abstract)
        out[mark.group(1)] = abstract[mark.end():end]
    return out


def _abstract_words(abstract, headings):
    """The abstract's own words, with the venue's structural labels removed.

    The labels are the venue's, not the author's, so counting them against the
    author's allowance is charging them for the form."""
    stripped = abstract
    for h in headings or ():
        stripped = stripped.replace(f"**{h}.**", "").replace(f"**{h}:**", "")
    stripped = re.sub(r"^\*\*Keywords\.\*\*.*", "", stripped, flags=re.S | re.M)
    return len(stripped.split())


def check(text, venue, profile=None, today=None):
    """Check a manuscript against its venue's stated requirements.

    `text` is the assembled manuscript. `venue` is what the plan says the venue is.
    `profile` overrides the lookup, for a venue the library does not hold."""
    profile = profile or venues.profile_for(venue)
    errors, warnings, stats = [], [], {}

    if profile is None:
        return VenueReport(
            venue=str(venue or "(none stated)"), passed=False,
            errors=[f"no venue profile for {venue!r}. The journal's own limits are "
                    f"therefore unchecked, and an abstract over its ceiling is a desk "
                    f"rejection no other gate here can see. Add a profile to "
                    f"`paperwriter/venues.py` with the URL you read it from and the "
                    f"date, or pass one explicitly."])

    defects = venues.profile_defects(profile)
    if defects:
        return VenueReport(venue=profile.get("name", str(venue)), passed=False,
                           errors=[f"the venue profile is unusable: {d}"
                                   for d in defects])

    age = venues.staleness_days(profile, today=today)
    if age is not None and age > venues.PROFILE_STALE_DAYS:
        warnings.append(
            f"the profile for {profile['name']} was read {age} days ago from "
            f"{profile['source'].split(',')[0]}. Journals revise their instructions on "
            f"no schedule; re-read it before submitting.")

    parts = sections(text)
    abstract = abstract_of(parts)
    body = body_of(parts)

    # 1. The abstract: length, then structure.
    if profile["abstract_max_words"] is not None:
        n = _abstract_words(abstract, profile["abstract_headings"])
        stats["abstract_words"] = n
        limit = profile["abstract_max_words"]
        if not abstract.strip():
            errors.append("the manuscript has no Abstract section.")
        elif n > limit:
            errors.append(
                f"the abstract runs {n:,} words against this venue's ceiling of "
                f"{limit:,}. This is checked by an editorial assistant before a "
                f"reviewer sees the paper.")

    for heading in profile["abstract_headings"] or ():
        if f"**{heading}.**" not in abstract and f"**{heading}:**" not in abstract:
            errors.append(
                f"the abstract has no `{heading}` heading. This venue requires a "
                f"structured abstract with "
                f"{', '.join(profile['abstract_headings'])}, in that order.")

    # 1b. The abstract's shape. No other gate reads it; see the module docstring.
    labelled = abstract_labels(abstract, profile["abstract_headings"])
    prose_only = "\n\n".join(labelled.values()) if labelled else abstract
    prose_only = re.sub(r"(?:\*\*Keywords\.?\*\*|(?<![A-Za-z])Keywords\s*[:.]).*",
                        "", prose_only, flags=re.S | re.IGNORECASE)
    over = [s for s in prose.sentences(prose_only)
            if len(s.split()) > config.ABSTRACT_SENTENCE_MAX_WORDS]
    if over:
        stats["abstract_longest_sentence"] = max(len(s.split()) for s in over)
        # A warning rather than an error: calibrated on two abstracts of one paper,
        # and Chekroud 2016 in Lancet Psychiatry opens its Methods label with 51
        # words. See the note above ABSTRACT_SENTENCE_MAX_WORDS in config.py.
        warnings.append(
            f"{len(over)} abstract sentence(s) run past "
            f"{config.ABSTRACT_SENTENCE_MAX_WORDS} words, the longest at "
            f"{stats['abstract_longest_sentence']}. An abstract is read detached from "
            f"the paper by somebody deciding whether to read further, and it has no "
            f"room for the one long sentence a 5,000-word section can absorb. The "
            f"first is \"{over[0][:80]}...\"")

    methods = labelled.get("Methods", "")
    results = labelled.get("Results", "")
    if methods.strip() and results.strip():
        m_words, r_words = len(methods.split()), len(results.split())
        ratio = m_words / max(r_words, 1)
        stats["abstract_methods_results_ratio"] = round(ratio, 2)
        if ratio > config.ABSTRACT_METHODS_RESULTS_RATIO_MAX:
            warnings.append(
                f"the abstract spends {m_words} words on Methods against {r_words} on "
                f"Results, a ratio of {ratio:.2f} against a soft ceiling of "
                f"{config.ABSTRACT_METHODS_RESULTS_RATIO_MAX}. A structured abstract "
                f"exists so a detached reader gets the FINDING; procedure has a whole "
                f"Methods section and a supplement behind it, and a finding has a "
                f"hundred words. Move the procedural detail down and give the space "
                f"to the result.")

    # 2. Keywords. The bold run-in is this project's builder's markup, not the
    #    venue's, so a plain `Keywords:` line counts too — matching on the markup
    #    turned seven present keywords into zero on a manuscript written in Word.
    #    Separated by semicolons or by commas, because journals ask for both.
    kw = re.search(r"(?:\*\*Keywords\.?\*\*|(?<![A-Za-z])Keywords\s*[:.])"
                   r"(.*?)(?:\n\n|\Z)", text, re.S | re.IGNORECASE)
    raw = kw.group(1) if kw else ""
    terms = raw.split(";") if ";" in raw else raw.split(",")
    count = len([k for k in terms if k.strip()]) if kw else 0
    stats["keywords"] = count
    lo, hi = profile["keywords_min"], profile["keywords_max"]
    if lo is not None and count < lo:
        errors.append(f"{count} keyword(s); this venue asks for {lo} to {hi}.")
    elif hi is not None and count > hi:
        errors.append(f"{count} keywords; this venue allows at most {hi}.")

    # 3. The body. Hard limits block; advisory ones warn and say what they cost.
    if profile["body_max_words"] is not None:
        n = prose.word_count(prose.strip_structure(body))
        stats["body_words"] = n
        limit = profile["body_max_words"]
        if n > limit:
            note = (f"the body runs {n:,} words against this venue's "
                    f"{limit:,}. {profile['body_limit_consequence']}")
            (errors if profile["body_limit_is_hard"] else warnings).append(note)

    # 4. Everything the venue counts, when it states a count at all.
    for key, label, pattern in (
            ("references_max", "references", r"^\d+\.\s+\S"),
            ("figures_max", "figures", r"\*\*\*Figure \d+\.\*\*"),
            ("tables_max", "tables", r"\*\*\*Table \d+\.\*\*")):
        found = len(re.findall(pattern, text, re.M))
        stats[label] = found
        cap = profile[key]
        if cap is not None and found > cap:
            errors.append(f"{found} {label} against this venue's limit of {cap}.")

    # 5. Required sections, where the venue requires them.
    #
    #    Matched against the manuscript's own HEADINGS, without case, and not against
    #    the file. A phrase anywhere in the text used to satisfy this, so a bold
    #    run-in lead-in inside one free-form Declarations block counted as a section
    #    — and a bold run-in is not a section a copyeditor, a submission portal, or a
    #    reader scanning for the data-availability statement can find. Every one of
    #    those patterns had been written to the shape of one manuscript's own
    #    Declarations block rather than to the venue's requirement, which is the
    #    failure this gate exists to prevent, living inside the gate.
    headings = [h.strip() for h in parts]
    for label, pattern, where in profile["required_sections"] or ():
        pool = headings
        if where == venues.IN_METHODS:
            pool = [h for h in headings if h.lower().startswith("method")]
        elif where == venues.IN_DECLARATIONS:
            pool = [h for h in headings if h.lower().startswith("declaration")]
        if not any(re.search(pattern, h, re.IGNORECASE) for h in pool):
            errors.append(
                f"no `{label}` heading" + ("" if where == venues.ANYWHERE
                                           else f" in the {where}")
                + f". This venue lists it as mandatory, and a bold lead-in inside "
                  f"another section is not a section anybody can find. Give it its "
                  f"own heading, in the venue's own wording.")

    for label, pattern in profile.get("recommended_sections") or ():
        if not any(re.search(pattern, h, re.IGNORECASE) for h in headings):
            warnings.append(
                f"no `{label}` heading. This venue's instructions list it, and this "
                f"profile could not verify that it is mandatory for an original "
                f"paper that is not a trial. Add it or re-read the instructions "
                f"page before submitting.")

    # 6. URLs in the body. The commonest way to break this is a Methods section that
    #    names its own code repository, which reads as good practice and is not what
    #    the venue asked for.
    if not profile["urls_in_body_allowed"]:
        found = re.findall(r"https?://[^\s)\]>]+", body)
        stats["body_urls"] = len(found)
        if found:
            shown = ", ".join(sorted(set(found))[:4])
            errors.append(
                f"{len(found)} URL(s) in the body: {shown}. This venue requires every "
                f"URL to be cited as a reference instead.")

    # 7. Title length. A venue that states a character limit wins; when none does, a
    #    word ceiling still applies, because most venues state nothing and a title
    #    nobody can read is a paper nobody opens. One manuscript reached 34 words and
    #    258 characters with every word of it accurate.
    m = re.search(r"\*\*Title\.?\*\*\s*(.+?)(?:\n\n|\Z)", text, re.S)
    if m:
        title = " ".join(m.group(1).split())
        stats["title_chars"] = len(title)
        stats["title_words"] = len(title.split())
        if profile["title_max_chars"] is not None:
            if len(title) > profile["title_max_chars"]:
                errors.append(
                    f"the title is {len(title)} characters against this venue's "
                    f"{profile['title_max_chars']}.")
        elif stats["title_words"] > config.TITLE_MAX_WORDS:
            errors.append(
                f"the title runs {stats['title_words']} words against a ceiling of "
                f"{config.TITLE_MAX_WORDS}. A title names the finding and the design. "
                f"Everything past that is the abstract's job.")

    # 8. The short title is a running head. It sits in the margin of every page, so the
    #    constraint is the margin rather than a matter of taste.
    m = re.search(r"\*\*Short[ -]title\.?\*\*\s*(.+?)(?:\n\n|\Z)", text,
                  re.S | re.IGNORECASE)
    if m:
        short = " ".join(m.group(1).split())
        stats["short_title_chars"] = len(short)
        if len(short) > config.SHORT_TITLE_MAX_CHARS:
            errors.append(
                f"the short title is {len(short)} characters against a ceiling of "
                f"{config.SHORT_TITLE_MAX_CHARS}. It is a running head, and the limit "
                f"is what fits in a page margin.")

    # 9. A heading marker that is not at the start of a line.
    #
    #    Markdown only makes a heading out of `#` when it opens the line. Anywhere else
    #    it is four literal characters, and pandoc prints them. The whole failure is
    #    one absent newline: an edit left "...is documented in Supplement S8. # Methods"
    #    at the end of an Introduction paragraph, so the built .docx carried "# Methods"
    #    as body text and had no Methods heading at all. The outline had one. Every
    #    per-section gate passed, because the section boundary the gates are handed had
    #    simply stopped existing.
    #
    #    A `#` inside a code span or a fenced block is content and is left alone, which
    #    is why this reads the stripped body.
    stripped = prose.strip_structure(re.sub(r"<!--.*?-->", "", text or "", flags=re.S))
    swallowed = [" ".join(m.group(0).split())
                 for m in _INLINE_HEADING.finditer(stripped)]
    stats["swallowed_headings"] = len(swallowed)
    if swallowed:
        errors.append(
            f"{len(swallowed)} heading marker(s) sit inside a line instead of opening "
            f"one: {'; '.join(swallowed[:3])}. Markdown renders those as literal "
            f"characters of body text and the section they were meant to start does "
            f"not exist in the built document. Put a blank line in front of each.")

    # 10. The headings a manuscript is not a manuscript without.
    #
    #     The venue's own `required_sections` covers what THIS journal demands. This
    #     covers IMRaD, which every journal demands and none bothers to state, and it
    #     is checked here because this is the gate that reads the assembled file.
    present = [h.strip().lower() for h in parts]
    for openings in config.MANUSCRIPT_REQUIRED_HEADINGS:
        if any(h.startswith(o) for h in present for o in openings):
            continue
        errors.append(
            f"the assembled manuscript has no `{openings[0].title()}` heading. A "
            f"section with no heading is a section a reader and a copyeditor both "
            f"lose, whatever the outline says is there.")

    return VenueReport(venue=profile["name"], passed=not errors, errors=errors,
                       warnings=warnings, stats=stats)
