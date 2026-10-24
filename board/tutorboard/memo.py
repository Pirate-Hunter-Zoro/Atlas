"""A subject's two memory files: the owner's RULES.md and the tutor's TUTOR.md.

RULES.md is the owner's. The tutor reads it and never writes it, and the brief
reads it at HEAD, so an uncommitted edit cannot steer a turn; the brief flags
one instead. The pre-commit hook refuses a turn's commit that touches it.

TUTOR.md is the tutor's: four sections (`subjects.TUTOR_SECTIONS`), at most
`WORDS` words in all, written only through `write` (`board memo <section>`).
The cap refuses rather than trims, because the brief carries the whole file on
every turn and a trimmed tail loses what comes next.

Stdlib only; no walrus, no `match`.
"""

import os
import re
import subprocess

from . import subjects


RULES = "RULES.md"
TUTOR = "TUTOR.md"
SECTIONS = subjects.TUTOR_SECTIONS
# The whole of TUTOR.md, headings included.
WORDS = 800

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


class Refused(ValueError):
    """A memo that cannot be written as asked; the message says why."""


def word_count(text):
    return len(re.findall(r"\S+", text or ""))


def section_name(said):
    """The canonical section `said` names, case and spacing aside, or None."""
    want = " ".join(str(said or "").split()).lower()
    for name in SECTIONS:
        if name.lower() == want:
            return name
    return None


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def _skeleton(root):
    from .course import config                               # local: light here
    try:
        name = config.read_config(root).get("name")
    except Exception:                                        # noqa: BLE001
        name = None
    return subjects._tutor_md(str(name) if name else os.path.basename(root))


def _strip_heading(body, name):
    """The body without a leading `## <name>` line the writer repeated."""
    lines = body.strip("\n").splitlines()
    if lines:
        m = _HEADING.match(lines[0])
        if m and section_name(m.group(2)) == name:
            lines = lines[1:]
    return "\n".join(lines).strip("\n")


def replace_section(text, name, body, append=False):
    """`text` with the `## <name>` section's body replaced by `body` (or
    `body` added to its end), the section added at the end where it is missing.
    The section runs to the next heading of level 2 or shallower."""
    lines = (text or "").splitlines()
    start = None
    for i, line in enumerate(lines):
        m = _HEADING.match(line)
        if m and len(m.group(1)) == 2 and section_name(m.group(2)) == name:
            start = i
            break
    body = body.strip("\n")
    if start is None:
        head = "\n".join(lines).rstrip("\n")
        block = "## %s\n\n%s" % (name, body) if body else "## %s" % name
        return (head + "\n\n" if head else "") + block + "\n"
    end = len(lines)
    for j in range(start + 1, len(lines)):
        m = _HEADING.match(lines[j])
        if m and len(m.group(1)) <= 2:
            end = j
            break
    old = "\n".join(lines[start + 1:end]).strip("\n")
    if append and old:
        body = old + ("\n" + body if body else "")
    middle = [""] + body.splitlines() + [""] if body else [""]
    out = lines[:start + 1] + middle + lines[end:]
    return "\n".join(out).rstrip("\n") + "\n"


def write(root, section, body, append=False, words=WORDS):
    """Write one section of `root`'s TUTOR.md. Returns (path, count).

    Refused (`Refused`, nothing written): a section that is not one of the
    four, and a resulting file over `words` words. Only ever TUTOR.md; a
    missing one starts as the four-section skeleton.
    """
    name = section_name(section)
    if not name:
        raise Refused("%r is not a TUTOR.md section; the sections are: %s"
                      % (section, ", ".join('"%s"' % s for s in SECTIONS)))
    path = os.path.join(root, TUTOR)
    text = _read(path)
    if text is None:
        text = _skeleton(root)
    new = replace_section(text, name, _strip_heading(body or "", name),
                          append=append)
    n = word_count(new)
    if n > words:
        raise Refused("TUTOR.md would be %d words, and the cap is %d. Nothing "
                      "was written. Cut this section or another one (`board "
                      "memo <section>` replaces a section whole)." % (n, words))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(new)
    os.replace(tmp, path)
    return path, n


def open_tasks(root):
    """The text of every open `- [ ]` line in TUTOR.md, in file order."""
    out = []
    for line in tutor(root).splitlines():
        m = re.match(r"^\s*[-*]\s+\[ \]\s+(.*\S)\s*$", line)
        if m:
            out.append(m.group(1))
    return out


def tutor(root):
    """TUTOR.md's text, stripped, or ""."""
    return (_read(os.path.join(root, TUTOR)) or "").strip()


def _git(root, argv):
    try:
        p = subprocess.run(["git"] + argv, cwd=root, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace")


def rules(root):
    """(text, drift): RULES.md as committed at HEAD, and how the working tree
    differs from it -- None when it does not, else "edited", "uncommitted" (no
    HEAD copy) or "deleted". ("", None) where there is no RULES.md at all."""
    head = _git(root, ["show", "HEAD:./" + RULES])
    work = _read(os.path.join(root, RULES))
    if head is None and work is None:
        return "", None
    if head is None:
        return "", "uncommitted"
    if work is None:
        return head.strip(), "deleted"
    if work.strip() != head.strip():
        return head.strip(), "edited"
    return head.strip(), None
