"""A revision: the document that was delivered comes back, and only what is wrong
with it changes.

A job carrying a `## Revision` section names a document this harness already wrote
and a file holding what somebody said is wrong with it. Everything the ordinary
pipeline does before drafting — gathering the evidence, fixing the grounding,
planning the papers, mapping the argument, outlining the sections — is machinery for
deciding **what the paper is**. A revision has already answered that, on disk, in
prose somebody has read. Running it again does not confirm the answer; it produces a
second one, and the second one is a different paper.

So a revision takes the short path, and this module is the whole of it:

    IMPORT   the delivered Markdown is split on its own headings into the same
             `sections/sNN.md` files the drafting stage would have produced, and an
             outline is DERIVED from what is there rather than proposed by a model
    BRIEF    the feedback becomes the first thing the editor reads, on every section
    SWEEP    `engine.revising` runs, which is the anchored-edit loop — so the text
             outside what the feedback names is not passed through a model at all
    BUILD    assembly, the final sweep, conversion and delivery, unchanged

**Nothing here calls a model.** The import is a parse and the brief is a quotation,
which is what makes the whole path testable with a string and a temp directory.

**Why the outline is derived and not gated.** `gates/structure.py` asks whether a
proposed plan is a well-formed manuscript: contiguous numbering, IMRaD order, budgets
inside the venue's limit, a topic sentence for every planned paragraph. Every one of
those questions is about a document that does not exist yet. Asked of one that does,
a failure has no repair that is not a rewrite — and a rewrite is the one operation a
correction must never become.
"""

import re
from pathlib import Path

from .. import config, jobspec, paths
from ..gates import prose
from ..infra import storage

# What can be revised. A delivered manuscript is Markdown and the built formats are
# derived from it, so Markdown is the source and the only thing worth editing: a
# revision applied to a `.docx` would be discarded by the next build.
REVISABLE = (".md", ".markdown")

# The heading level `building.assemble` writes, which is what a delivered manuscript
# is made of. `##` is the fallback for a document written by hand.
_H1 = re.compile(r"^#[ \t]+(.+?)\s*$", re.M)
_H2 = re.compile(r"^##[ \t]+(.+?)\s*$", re.M)

_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
_YAML_TITLE = re.compile(r"^title:\s*\"?(.+?)\"?\s*$", re.M)
_YAML_AUTHOR = re.compile(r"^\s*-\s*\"?(.+?)\"?\s*$", re.M)


def wanted(prompt_text):
    """Whether this job is a revision at all. One question, asked in three places."""
    return bool(jobspec.revision(prompt_text or ""))


# ---------------------------------------------------------------------------
# finding the document
# ---------------------------------------------------------------------------
def _candidates(spec):
    """Every place the named document could be, nearest the job's own word first.

    The job names a path relative to the workspace that asked, because that is the
    only form the board can write down that stays true when the repository is cloned
    somewhere else. `workspace` is the root it is relative to, and the rest are
    fallbacks for a job written by hand: an absolute path, and the analysis trees
    this harness was pointed at, whose parents are the workspace.
    """
    named = Path(spec["document"]).expanduser()
    out = []
    if spec.get("workspace"):
        out.append(Path(spec["workspace"]).expanduser() / named)
    out.append(named)
    for source in config.SOURCE_DIRS:
        here = Path(source).expanduser()
        for _ in range(3):
            out.append(here / named)
            here = here.parent
    out.append(config.OUT_DIR / named)
    return out


def locate(spec):
    """Where the named document actually is. Raises RuntimeError if it is nowhere.

    A revision whose document cannot be found must not proceed: the alternative is
    writing a fresh paper under the heading of a correction, which is the one outcome
    the `## Revision` section exists to prevent."""
    tried = []
    for candidate in _candidates(spec):
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in tried:
            continue
        tried.append(resolved)
        if resolved.is_file():
            if resolved.suffix.lower() not in REVISABLE:
                raise RuntimeError(
                    f"revision: {spec['document']} is a {resolved.suffix} file. Only "
                    f"the Markdown source can be revised — every other format is "
                    f"built from it, so an edit applied anywhere else is discarded by "
                    f"the next build. Name the .md.")
            return resolved
    shown = "; ".join(str(p) for p in tried[:6])
    raise RuntimeError(
        f"revision: the job names {spec['document']!r} and no such file exists. "
        f"Looked in: {shown}. Name the workspace root in the job's Revision section "
        f"(`workspace: /path/to/workspace`) or give an absolute path.")


def feedback_text(spec, limit=8000):
    """What was said about the document, as it was written, or "".

    Quoted rather than summarised. It is somebody's own account of what is wrong, and
    a paraphrase of it is this harness deciding what the complaint was. Missing is not
    fatal: the board writes the same words into the job's free-prose section, so the
    editor still sees them."""
    if not spec.get("feedback"):
        return ""
    for candidate in _candidates(dict(spec, document=spec["feedback"])):
        try:
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8",
                                           errors="replace")[:limit].strip()
        except OSError:
            continue
    return ""


# ---------------------------------------------------------------------------
# taking it apart
# ---------------------------------------------------------------------------
def front_matter(text):
    """The YAML block a delivered manuscript opens on, as `(title, [authors])`."""
    found = _FRONT_MATTER.match(text or "")
    if not found:
        return "", []
    block = found.group(1)
    title = _YAML_TITLE.search(block)
    authors = []
    if re.search(r"^author:\s*$", block, re.M):
        tail = block.split("author:", 1)[1]
        authors = [a.strip() for a in _YAML_AUTHOR.findall(tail) if a.strip()]
    return (title.group(1).strip() if title else ""), authors


def split_document(text):
    """`[(heading, body), ...]` — the document as the sections it is made of.

    Raises RuntimeError rather than losing anything. Two ways that could happen and
    both are refused: a document with no headings at all is not a manuscript this
    harness assembled, and prose sitting above the first heading has nowhere to go in
    a section list and would vanish on reassembly."""
    body = text or ""
    found = _FRONT_MATTER.match(body)
    if found:
        body = body[found.end():]

    pattern = _H1 if _H1.search(body) else _H2
    marks = list(pattern.finditer(body))
    if not marks:
        raise RuntimeError(
            "revision: the document has no headings, so it cannot be split into the "
            "sections the editor works on. A manuscript this harness delivered opens "
            "every section with a `# ` heading.")
    lead = body[:marks[0].start()].strip()
    if lead:
        raise RuntimeError(
            f"revision: {len(lead.split())} word(s) sit above the document's first "
            f"heading, and a section list has nowhere to keep them — reassembling "
            f"would silently drop them. Move that prose under a heading, or into the "
            f"front matter, and re-drop the job.")

    out = []
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        out.append((mark.group(1).strip(), body[mark.end():end].strip()))
    return out


# ---------------------------------------------------------------------------
# what the pipeline reads afterwards
# ---------------------------------------------------------------------------
def plan(project_rec):
    """Write the one-paper plan a revision needs, and return it. No model call.

    The plan exists for two readers and neither of them is a planner: `building`
    takes the title and the authors off it for the front matter, and `_report_length`
    takes the word limit. Everything a real plan carries — the points, the claims,
    the ladder — belongs to the document already, which is the whole reason this path
    exists."""
    spec = jobspec.revision(project_rec["prompt_text"])
    source = locate(spec)
    text = source.read_text(encoding="utf-8", errors="replace")
    title, authors = front_matter(text)
    title = title or jobspec.title(project_rec["prompt_text"]) or source.stem

    document = {
        "title": title,
        "revision": {"document": str(source), "named": spec["document"],
                     "feedback": spec.get("feedback", "")},
        "papers": [{"number": 1, "title": title,
                    "venue": jobspec.venue(project_rec["prompt_text"]),
                    "word_limit": jobspec.word_limit(project_rec["prompt_text"]),
                    "one_line": f"A revision of {spec['document']}."}],
        "points": [], "claims": [], "references": {},
    }
    if authors:
        document["authors"] = authors
    storage.save_json(document, paths.plan_path(project_rec["project_id"]))
    return document


def import_document(project_rec, paper_num, log_fn=None):
    """The delivered document, as the section files and the outline. Returns the
    outline.

    This is the step that replaces arguing, outlining and drafting, and it replaces
    them with a parse: every section of the outline it writes is a section the
    document already has, at the length it already is."""
    pid = project_rec["project_id"]
    spec = jobspec.revision(project_rec["prompt_text"])
    source = locate(spec)
    parts = split_document(source.read_text(encoding="utf-8", errors="replace"))

    sections = []
    for number, (heading, body) in enumerate(parts, start=1):
        words = prose.word_count(prose.strip_structure(body))
        storage.atomic_write_text(body + "\n",
                                  paths.section_path(pid, paper_num, number))
        sections.append({
            "number": number, "heading": heading, "words": words,
            # THE BUDGET IS WHAT THE SECTION ALREADY IS, and `delivered` is what tells
            # the length gate to drop its absolute floor. A delivered section of forty
            # words is a data-availability statement, and a gate that tells the editor
            # to grow it to a hundred and fifty is asking for invented content.
            "delivered": True,
            "claims": [], "evidence": [], "paragraphs": [],
            "exit_state": f"the reader has read {heading} as it was delivered",
        })
    outline = {"sections": sections, "revision": True}
    storage.save_json(outline, paths.outline_path(pid, paper_num))
    if log_fn:
        total = sum(s["words"] for s in sections)
        log_fn(f"paper {paper_num}: revising {source.name} — {len(sections)} "
               f"section(s), {total:,} words, nothing re-planned")
    return outline


# ---------------------------------------------------------------------------
# what the editor is told
# ---------------------------------------------------------------------------
def brief(project_rec, limit=8000):
    """The feedback, as the block that leads every editorial pass of this revision.

    It leads the brief rather than trailing it because an editor with a turn budget
    reads the top most carefully, and on a revision the person's own complaint
    outranks every gate: the gates are about whether the prose is well made, and this
    is about whether it says the right thing.
    """
    spec = jobspec.revision(project_rec.get("prompt_text", ""))
    if not spec:
        return ""
    said = feedback_text(spec, limit=limit)
    lines = [
        "", "=" * 70,
        "THIS IS A REVISION — WHAT THE AUTHOR SAYS IS WRONG WITH THIS DOCUMENT",
        "=" * 70,
        f"The document is `{spec['document']}`. It exists, it has been read, and it "
        f"is not a draft. Its structure, its terminology and its claims stand except "
        f"where the feedback below says otherwise.",
        "",
    ]
    if said:
        lines += [said, ""]
    else:
        lines += ["The feedback file could not be read from here. What was said is "
                  "quoted in the job prompt instead; work from that and invent "
                  "nothing.", ""]
    lines += [
        "Two rules for this pass, and they are the reason this path exists:",
        "",
        "  - Raise an issue where the feedback names one, and repair it with an "
        "anchored edit like any other. If nothing in THIS section is what the "
        "feedback is about, say so by returning no issues for it rather than finding "
        "something to change.",
        "  - Do not improve prose the feedback did not mention. A correction that "
        "rewrites the paragraph next to it is how a revision turns into a different "
        "paper, and everything you do not name is bit-identical afterwards by "
        "construction.",
        "",
    ]
    return "\n".join(lines)
