"""Handing a manuscript job to Paper-Writer, and showing what comes back.

    "a `make` sitting in workspace W assembles a job -- the plan, the written
     map, the figures and tables it names, the manuscript sections that already
     exist -- drops it in Paper-Writer's inbox, and the delivered manuscript
     lands in W under a tracked path. Then it is a document like any other."

**THE BOARD DOES NOT RUN PAPER-WRITER.** That is the whole design and it is worth
being blunt about, because the tempting thing is to import it.

`projects/Paper-Writer` is a working manuscript factory with its own daemon, its
own state directory, its own three-layer memory and its own ledgers. It admits a
job by finding a filled-in `PROMPT_TEMPLATE.md` in a drop folder once the file
has stopped changing. That is a contract made of a directory and a file format,
which is the loosest coupling two programs can have -- and it is the reason this
module is 300 lines rather than a second copy of somebody else's engine.

So the board's whole business here is three things:

    ASSEMBLE   turn what the board already knows about workspace W into the
               sections that template asks for
    DROP       write it into the inbox, once, and say where it went
    SHOW       read the status file back, and find what was delivered

Nothing in here imports `paperwriter`. Nothing in here starts a process. If the
daemon is not running, a job sits in the inbox until it is -- which is exactly
what should happen, and is said out loud rather than discovered later.

Standard library only, like everything else.
"""

import os
import re
import time

from . import atlas, fenced
from .course import config, plan
from .course import map as course_map

# The workspace that holds the factory. FOUND, NOT CONFIGURED -- it is a
# workspace like any other and `atlas.find` is how this system locates one. A
# repository without it simply cannot make papers, and says so.
WRITER = "projects/Paper-Writer"

# Where the factory keeps its drop folder, relative to its own root, when
# nothing says otherwise. `paperwriter/config.py` defaults `PAPER_OUT_DIR` to
# `<project>/../Manuscripts` and the inbox to `_inbox` under it; both are
# overridable, and `service/paperwriter.env` is where this machine records what
# it actually runs with. Read rather than assumed: a hard-coded path here is a
# job dropped where nothing is looking.
OUT_FALLBACK = os.path.join("..", "Manuscripts")
INBOX_NAME = "_inbox"
STATUS_NAME = "_STATUS.md"

# What a job is called on disk. Dated and versioned rather than stamped with the
# time, the same rule every other document in this system follows.
JOB_RE = re.compile(r"^(?P<stem>.+)-v(?P<n>\d+)\.md$")


def writer_root(base=None):
    """Paper-Writer's own directory, or "" if this repository has no factory."""
    found = atlas.find(WRITER, base)
    return found["root"] if found else ""


def _env_file(root):
    """`PAPER_*` settings this machine actually runs with.

    `service/paperwriter.env` is shell, sourced with `set -a`, and deliberately
    "plain KEY=value with no logic -- a config file that can branch is a
    program". So it can be read as key/value without running it, which is the
    only reason this is safe to do at all.
    """
    out = {}
    path = os.path.join(root, "service", "paperwriter.env")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                if key.startswith("PAPER_"):
                    out[key] = value.strip().strip('"').strip("'")
    except OSError:
        return {}
    return out


def _expand(root, value):
    value = os.path.expanduser(os.path.expandvars(value))
    if not os.path.isabs(value):
        value = os.path.join(root, value)
    return os.path.realpath(value)


def out_dir(base=None):
    """Where finished papers land and the drop folder lives."""
    root = writer_root(base)
    if not root:
        return ""
    # The environment this process is in wins, then the deployed file, then the
    # documented default -- which is the order `paperwriter/config.py` itself
    # resolves them in.
    said = os.environ.get("PAPER_OUT_DIR") or _env_file(root).get("PAPER_OUT_DIR", "")
    return _expand(root, said or OUT_FALLBACK)


def inbox(base=None):
    """The drop folder. A job written here is admitted on the next cycle."""
    where = out_dir(base)
    if not where:
        return ""
    said = (os.environ.get("PAPER_INBOX_DIR")
            or _env_file(writer_root(base)).get("PAPER_INBOX_DIR", ""))
    if said:
        return _expand(writer_root(base), said)
    return os.path.join(where, INBOX_NAME)


# ---------------------------------------------------------------------------
# assembling the job
# ---------------------------------------------------------------------------
# WHAT THE BOARD ALREADY KNOWS, in the shapes that template asks for. Nothing
# here is invented: the claims come from the plan the person maintains, the
# evidence directories from what is actually on disk, the terminology from the
# written map's own names. Where the board does not know something it says so in
# the job rather than guessing, because a guessed venue plans the manuscript to
# the wrong length and a guessed checklist places the wrong obligations.

# WHAT MAY BE MINED, AND WHAT MAY NEVER BE. Both come from `fenced.py`, and the
# only reason they are named again here is that a caller reads better for it.
#
# They used to be declared in this file, and `course/reading.py` had its own
# opinion about the same tree and a different answer: the manuscript factory
# could not be pointed at `phi/` while the document drawer offered a transcript
# out of it to a tutor. Two lists about one rule, and one of them wrong.
#
# The allowlist is what the gathering stage is permitted to mine -- the board
# choosing `PAPER_SOURCE_DIRS` on somebody's behalf. The refusal is checked
# again on top of it, which is belt and braces on purpose: it is what makes
# adding a name to the allowlist safe without re-deriving which workspaces hold
# what. `test/writing_up.py` fails the suite if either stops holding.
RESULT_DIRS = fenced.RESULT_DIRS
NEVER = fenced.NEVER
refused = fenced.refused

# Where a delivered manuscript lands inside the workspace that asked for it.
# TRACKED, which is the point: "the delivered manuscript lands in W under a
# tracked path. Then it is a document like any other."
LANDING = "manuscripts"

MAX_CLAIMS = 12


def _evidence(root):
    """The read-only trees the gathering stage may mine, for this workspace.

    Allowlisted, then checked again against `NEVER`. The second pass is not
    redundant: it is what makes adding a name to `RESULT_DIRS` safe to do
    without re-deriving which workspaces hold what.
    """
    out = []
    for name in RESULT_DIRS:
        if refused(name):
            continue
        where = os.path.join(root, name)
        if os.path.isdir(where) and not refused(where):
            out.append(where)
    return out


def _sections(root):
    """Manuscript prose that already exists here, so a job does not re-write it."""
    out = []
    where = os.path.join(root, LANDING)
    for base, dirs, files in os.walk(where):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for n in sorted(files):
            if n.lower().endswith((".md", ".tex")) and not n.startswith("_"):
                out.append(os.path.relpath(os.path.join(base, n), root))
        if len(out) >= 40:
            break
    return out


def _claims(root):
    """The plan's open steps, as the starting point for what a paper argues.

    NOT AS CLAIMS. A step is a thing to do and a claim is a thing to argue, and
    the template is explicit that "Model comparison" is a heading rather than a
    claim. So these go into the job as what they are -- the work this paper is
    about -- and the person writing the job turns them into claims. Offering
    them already phrased as claims would be the board inventing an argument.
    """
    try:
        return [s.get("title") or s.get("label") or ""
                for s in plan.steps(root)][:MAX_CLAIMS]
    except Exception:                                        # noqa: BLE001
        return []


def _vocabulary(root):
    """The written map's own names for the parts of this work.

    The template's most load-bearing free-prose field is the terminology lock --
    "one name per thing", and the aliases that must never appear. A workspace
    somebody has drawn has already answered half of that: *the typist*, *the
    stopwatch*, *the name-tagger* are the names in use, and `also` carries the
    real identifier each one stands for. Handing both over is the difference
    between a lock somebody has to write from scratch and one they correct.
    """
    try:
        info = course_map.written_status(root)
        if not info["has"] or info["problems"]:
            return []
        built = course_map.status(root)
    except Exception:                                        # noqa: BLE001
        return []
    if not built or not built.get("written"):
        return []
    out = []
    for n in built["nodes"]:
        out.append({"name": n["name"], "also": n.get("also") or "",
                    "does": n.get("does") or ""})
    return out


def job(root, title="", venue="", checklist="", notes=""):
    """The filled-in template, as text. Nothing is written to disk here.

    Kept separate from `submit` so that `board make --paper --dry-run` can print
    exactly what would be dropped. A job is a document somebody is going to be
    held to; being able to read it before it is admitted is worth one function.
    """
    ws = atlas.identify(root)
    cfg = config.read_config(root) or {}
    name = cfg.get("name") or os.path.basename(root)
    title = title or ("A paper from " + name)

    out = ["# %s" % title, ""]
    out.append("<!-- Assembled by `board make --paper` from %s on %s. Everything"
               " below came off disk in that workspace; nothing in it was"
               " invented. Edit it before the harness admits it -- it is"
               " admitted once the file stops changing. -->"
               % (ws, time.strftime("%Y-%m-%d %H:%M")))
    out += ["", "---", "", "## Evidence", ""]
    out.append(name)
    out += ["", "<!-- PAPER_SOURCE_DIRS for this job, which are the directories"
            " this workspace actually keeps results in: -->", ""]
    found = _evidence(root)
    if found:
        out.append("    PAPER_SOURCE_DIRS=" + ":".join(found))
    else:
        out.append("    (this workspace has no results/, figures/ or tables/"
                   " directory yet -- name the tree to mine before submitting)")

    out += ["", "---", "", "## Claims", ""]
    out.append("<!-- THESE ARE NOT CLAIMS YET. They are what this workspace's"
               " own plan says is being worked on, in its order, and a step is a"
               " thing to do rather than a thing to argue. Turn each one you"
               " want into a claim, delete the rest, and add the limitation a"
               " reviewer will raise. -->")
    out.append("")
    steps = _claims(root)
    if steps:
        for s in steps:
            out.append("- %s" % s)
    else:
        out.append("- (this workspace has no plan the board could read; write"
                   " the claims by hand)")

    out += ["", "---", "", "## Venue", ""]
    out.append(venue or "<!-- NOT KNOWN TO THE BOARD. Name the journal and its"
                        " word limit; the first number followed by \"word\""
                        " becomes a hard ceiling. A wrong number plans the"
                        " manuscript to the wrong length. -->")

    out += ["", "---", "", "## Reporting checklist", ""]
    out.append(checklist or "<!-- NAMED, NEVER INFERRED -- the template is"
                            " explicit about this. `none` is a valid answer if"
                            " you say why. -->")

    out += ["", "---", "", "## Scope", "", "1 paper."]

    out += ["", "---", "", "## Anything the harness cannot work out", ""]
    if notes:
        out += [notes, ""]

    vocab = _vocabulary(root)
    if vocab:
        out.append("The names this work is done under, from its own map. One"
                   " name per thing, and these are the names:")
        out.append("")
        for v in vocab:
            line = "- **%s**" % v["name"]
            if v["also"]:
                line += " — %s" % v["also"]
            if v["does"]:
                line += ". %s" % v["does"]
            out.append(line)
        out.append("")
        out.append("<!-- Add the ALIASES: the words a fluent writer would reach"
                   " for when the locked term feels repetitive, which must never"
                   " appear. That is the half that does the work. -->")
        out.append("")

    have = _sections(root)
    if have:
        out.append("Manuscript prose that already exists in this workspace, and"
                   " is not to be written again:")
        out.append("")
        for rel in have:
            out.append("- `%s`" % rel)
        out.append("")

    out.append("The finished paper is to be delivered into `%s/%s/`."
               % (ws, LANDING))
    return "\n".join(out).rstrip() + "\n"


# ---------------------------------------------------------------------------
# dropping it, and reading what comes back
# ---------------------------------------------------------------------------
def _slug(text):
    out = re.sub(r"[^A-Za-z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return (out or "paper")[:48]


def _next_version(where, stem):
    """v1, v2, v3, never a timestamp -- `document.next_version`'s rule, here.

    Not imported from there: that one counts `.pdf` and `.tex` pairs in an
    export directory, and this counts jobs in somebody else's inbox. Same rule,
    different question, and welding them together would tie the board's export
    numbering to a directory the board does not own.
    """
    high = 0
    try:
        names = os.listdir(where)
    except OSError:
        return 1
    for n in names:
        m = JOB_RE.match(n)
        if m and m.group("stem") == stem:
            high = max(high, int(m.group("n")))
    return high + 1


def submit(root, title="", venue="", checklist="", notes="", base=None,
           dry_run=False):
    """Assemble a job and drop it in the inbox. The one function of the seam.

    Returns a record the board can paint. It never starts anything: if the
    daemon is not running the job sits there until it is, which is the correct
    behaviour and is said out loud in `detail` rather than found out later.
    """
    writer = writer_root(base)
    if not writer:
        return {"ok": False,
                "detail": "this repository has no %s workspace, so there is "
                          "nothing to hand a manuscript job to" % WRITER}

    where = inbox(base)
    body = job(root, title=title, venue=venue, checklist=checklist, notes=notes)
    stem = _slug(title or config.read_config(root).get("name")
                 or os.path.basename(root))

    if dry_run:
        return {"ok": True, "dry_run": True, "inbox": where,
                "markdown": body, "name": stem}

    try:
        os.makedirs(where, exist_ok=True)
    except OSError as exc:
        return {"ok": False,
                "detail": "could not make the drop folder %s: %s" % (where, exc)}

    name = "%s-v%d.md" % (stem, _next_version(where, stem))
    path = os.path.join(where, name)
    try:
        # WRITTEN WHOLE, THEN MOVED. The harness admits a job "once the file has
        # stopped changing", so a file that appears empty and grows is a file it
        # may look at halfway through. A rename inside one directory is atomic.
        tmp = path + ".part"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(body)
        os.replace(tmp, path)
    except OSError as exc:
        return {"ok": False, "detail": "could not write %s: %s" % (path, exc)}

    rec = {"ok": True, "name": name, "path": path, "inbox": where,
           "workspace": atlas.identify(root),
           "landing": os.path.join(root, LANDING),
           "markdown": body}
    rec["detail"] = ("Dropped. Paper-Writer admits it on its next cycle, once "
                     "the file has stopped changing. Nothing here starts it: if "
                     "the daemon is not running the job waits, which is what "
                     "should happen.")
    return rec


def status(base=None):
    """What the factory says it is doing, as it says it.

    `_STATUS.md` is Paper-Writer's own phone-readable summary and it is the
    right thing to show: it is written by the thing doing the work, and a board
    that re-derived progress from the state directory would be a second opinion
    about somebody else's job.
    """
    where = out_dir(base)
    if not where:
        return {"ok": False, "detail": "no %s workspace in this repository"
                                       % WRITER}
    path = os.path.join(where, STATUS_NAME)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            said = fh.read()
    except OSError:
        return {"ok": True, "out": where, "said": "",
                "detail": "nothing has been submitted yet, or the harness has "
                          "not run a cycle since it was"}
    try:
        when = os.path.getmtime(path)
    except OSError:
        when = 0
    return {"ok": True, "out": where, "said": said[:8000], "at": when}


def waiting(base=None):
    """Jobs sitting in the inbox that nothing has taken yet."""
    where = inbox(base)
    out = []
    try:
        names = sorted(os.listdir(where))
    except OSError:
        return out
    for n in names:
        if not n.endswith(".md"):
            continue
        p = os.path.join(where, n)
        try:
            out.append({"name": n, "at": os.path.getmtime(p),
                        "size": os.path.getsize(p)})
        except OSError:
            continue
    return out


def delivered(root):
    """Manuscripts that have landed in this workspace, newest first.

    Looked for where the job SAID they would land, which is a tracked path in
    the workspace that asked. A paper somewhere else is a paper nobody can find
    from the board, and that is the whole reason the landing is named in the job
    rather than left to the factory's own out-directory.
    """
    where = os.path.join(root, LANDING)
    out = []
    for base_dir, dirs, files in os.walk(where):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for n in sorted(files):
            if not n.lower().endswith((".md", ".docx", ".pdf")):
                continue
            p = os.path.join(base_dir, n)
            try:
                out.append({"rel": os.path.relpath(p, root),
                            "at": os.path.getmtime(p),
                            "size": os.path.getsize(p)})
            except OSError:
                continue
    out.sort(key=lambda x: -x["at"])
    return out[:40]
