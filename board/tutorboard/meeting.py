"""The meeting deck: a presentation to the mentors, written over a brief.

    "I just used the meeting notes functionality to try to review the most
     recent implementations we did in PSYCH-ASR and TRD-EHR. I'm looking at
     the meeting deck right now. It's absolute dog shit."

The test is whether it can *"actually generate a professional coherent
presentation on my most recent progress"* -- something put in front of mentors
without rewriting it.

ONE ENGINE, TWO ENTRY POINTS. A meeting deck is a deck from sittings with a
preset: every commit, handoff and direction change of a period, across the
chosen workspaces, and ink that means DIRECTION rather than revision. So it is
written the way `sittings.py` writes one -- this module writes a brief, the
`[writeup]` turn writes the deck over it through `routes/library.py`'s own
dispatch -- and what is left here is only what a meeting has that a deck from
sittings has not:

  * `gather` -- per workspace, what the period holds: the commits that are its
    own work, with their whole messages; the saves, which carry the HANDOFF.md
    and DIRECTION.md diff instead of a line of their own; those two files' diff
    over the whole period; the sittings held in it; the plan steps that closed,
    and the open ones a landed commit appears to have done already.
  * `write_brief` -- that, plus the figures of the period copied beside the
    deck and a catalog of the rest, into `_brief.md` and `_brief.json`.
  * `finalize` -- once the deck is built: the page map off the compiled PDF
    (every page carries one `\\meetingws`), the numbers and figures checked
    against the sources, and anything unsupported listed beside the deck.

WHERE IT LIVES. In one HOST workspace, at `writeups/meeting/`, one deck replaced
each time; `meetings/meeting.json` at the root points at it and holds the page
map. The host is `sittings.host_for`'s answer: a fenced workspace hosts any deck
that touches it, because the push's PHI scan reads only what sits under a fenced
root, and the assistant that writes it is whichever may read that workspace. Two
fenced workspaces in one deck are refused (`sittings.mixed_fences`).

THE PAGE A MARK IS ON IS STILL HOW IT FINDS ITS WORKSPACE (`proposals.py`), so a
content page with no workspace or with two refuses the deck by name before it is
offered. Title, summary and closing pages say `\\meetingshared` and belong to
nobody.

Standard library only, like everything else.
"""

import json
import math
import os
import re
import shutil
import subprocess
import threading
import time

from . import atlas, fenced, paths
from .course import plan

# The root directory holding the pointer to the deck and the pictures of its
# marks. Neither is tracked: the deck itself is under its host.
OUT_DIR = "meetings"

# One deck, one name, replaced each time.
STEM = "meeting"
RECORD = STEM + ".json"
ANN_IDENT = STEM

# Where the deck is, under its host workspace.
WRITEUPS = "writeups"
DECK_DIR = "meeting"

# What sits beside the deck. `_` keeps the brief and the sidecar out of the
# library's walk; the package is what gives a frame its workspace.
BRIEF_MD = "_brief.md"
BRIEF_JSON = "_brief.json"
PROVENANCE = "_provenance.json"
STY = "meetingws.sty"
FIGURES = "figures"

# UNTRACKED, BECAUSE THE REPOSITORY IS PUBLIC. The figures can be made from
# records and the brief quotes diffs and cards. The `.tex` and the package are
# tracked, and a fenced host's push scan reads them before they leave.
IGNORE = ("figures/", "*.pdf", "_brief.*", "_provenance.*", "*.aux", "*.log",
          "*.nav", "*.snm", "*.toc", "*.out", "*.vrb", "*.fls",
          "*.fdb_latexmk", "*.synctex.gz")

# The package every frame's workspace is written through. `\meetingpage` is
# read back off the `.aux`, one line per shipped page; `\thepage` is expanded
# at shipout, so it is the page the frame actually landed on.
STY_TEXT = r"""%% Written by the board. Every frame of the meeting deck says whose it is:
%% \meetingws{<workspace id>} on a project's frame, \meetingshared on the
%% title, summary and closing frames. A mark on a page is routed by it.
\NeedsTeXFormat{LaTeX2e}
\ProvidesPackage{meetingws}[2026/09/28 meeting deck page marks]
\newcommand{\meetingpage}[2]{}
\newcommand{\meetingws}[1]{\protected@write\@auxout{}{\string\meetingpage{\thepage}{#1}}}
\newcommand{\meetingshared}{\meetingws{*}}
\endinput
"""

# How much of each source the brief carries. Whole commit messages are the
# point; a limit is only there so one runaway paragraph cannot fill it.
BODY_CHARS = 6000
DIFF_CHARS = 8000
WINDOW_DIFF_CHARS = 14000
MOST_COMMITS = 40
MOST_SAVES = 20
MOST_TABLES = 40
MOST_CATALOG = 300
MOST_FIGURES = 24
PER_WORKSPACE_FIGURES = 12

# What the brief's sources are read to, at most, when the numbers are checked.
SOURCE_BYTES = 400000
CORPUS_BYTES = 8000000

# The files that tell a workspace's story.
STORY = ("HANDOFF.md", "DIRECTION.md")

# A save, not a piece of work: what follows a workspace's prefix decides.
SAVES = ("lesson complete", "lesson transcript", "stopping point")
SAVE_RE = re.compile(r"^(?:[\w.+-]+\s+)?hand-?off\b")

# How a deck being written is judged. `SETTLE` is how long the deck's directory
# has to sit still, once its turn is over, before it is read -- pdflatex writes
# the PDF more than once. `QUIET` and `CEILING` are the deck from sittings'
# own.
SETTLE = 15
QUIET = 120
CEILING = 2 * 3600

# A commit subject longer than this is a paragraph somebody put on one line.
SUBJECT = 100

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday",
            "saturday", "sunday")

# An address a mentor cannot open, or a hostname nobody outside may see.
INTERNAL_URL = re.compile(
    r"(?:[a-z0-9-]+\.)+ts\.net|\b(?:localhost|127\.0\.0\.1)\b|#/w/", re.I)


# ---------------------------------------------------------------------------
# when
# ---------------------------------------------------------------------------
def snap(t):
    """Local midnight at or before `t`. A window starts at a day boundary: a
    week asked for at 20:18 must not cut the direction change made at 20:13
    seven days earlier."""
    lt = time.localtime(t)
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))


def resolve_since(spec, root=None):
    """`(epoch, what to call it)` -- or `(None, why not)`. Always a midnight."""
    spec = str(spec or "").strip().lower()
    if not spec:
        return None, "say a date (2026-09-01), a span (7d, 2w), a weekday, or `last`"

    if spec == "last":
        when = _last_notes(root)
        if not when:
            return None, ("there is no earlier deck to measure from. Give a "
                          "date or a span for the first one.")
        return snap(when), "the last deck"

    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", spec)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # CHECKED BEFORE `mktime`, WHICH NORMALISES RATHER THAN REFUSING.
        if not (1 <= mo <= 12 and 1 <= d <= 31 and 1970 <= y <= 2200):
            return None, "%s is not a date" % spec
        try:
            t = time.mktime((y, mo, d, 0, 0, 0, 0, 0, -1))
        except (OverflowError, ValueError):
            return None, "%s is not a date this machine can represent" % spec
        if time.localtime(t).tm_mday != d:
            return None, "%s is not a date" % spec
        return t, spec

    m = re.match(r"^(\d+)\s*([dwm])$", spec)
    if m:
        n = int(m.group(1))
        days = {"d": 1, "w": 7, "m": 30}[m.group(2)] * n
        if not 1 <= days <= 3650:
            return None, "%s is not a period anybody holds a meeting about" % spec
        said = ("yesterday" if days == 1
                else "the last week" if days == 7
                else "the last %d days" % days)
        return snap(time.time() - days * 86400), said

    if spec.startswith("last-"):
        spec = spec[5:]
    if spec in WEEKDAYS:
        # The most recent one, and today does not count.
        want = WEEKDAYS.index(spec)
        now = time.localtime()
        back = (now.tm_wday - want) % 7 or 7
        return snap(time.time()) - back * 86400, "since " + spec.capitalize()

    return None, ("%r is not a date (2026-09-01), a span (7d, 2w), a weekday, "
                  "or `last`" % spec)


def _last_notes(root):
    """When the last deck was asked for, or 0."""
    base = root or atlas.root()
    if not base:
        return 0
    rec = _read_record(base)
    if rec and rec.get("asked_at"):
        return float(rec["asked_at"])
    newest = 0
    out_dir = os.path.join(base, OUT_DIR)
    try:
        names = os.listdir(out_dir)
    except OSError:
        return 0
    for n in names:
        if n.endswith(".tex"):
            try:
                newest = max(newest, os.path.getmtime(os.path.join(out_dir, n)))
            except OSError:
                continue
    return newest


def _day(t):
    """`Monday 21 September 2026`, with no leading zero on the day."""
    lt = time.localtime(t)
    return "%s %d %s %d" % (time.strftime("%A", lt), lt.tm_mday,
                            time.strftime("%B", lt), lt.tm_year)


def period_text(since_ts, until_ts=None):
    """The exact period, as the title slide says it."""
    until_ts = time.time() if until_ts is None else until_ts
    return "%s to %s" % (_day(since_ts), _day(until_ts))


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------
def _git(base, args, timeout=30):
    try:
        p = subprocess.run(["git"] + args, cwd=base, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if p.returncode != 0:
        return ""
    return p.stdout.decode("utf-8", "replace")


def repo_of(root, base):
    """`(top, rel)`: Atlas, which holds every workspace's history, and where
    the workspace sits inside it.

    Both ends by their real names: the board can be reached through a symlink,
    and git answers with the resolved path."""
    top = os.path.realpath(base)
    return top, os.path.relpath(os.path.realpath(root), top)


def prefix_of(rel):
    """What a repository path starts with when it is inside `rel`: `""` for a
    workspace that is the whole repository, else `rel/`."""
    rel = (rel or ".").strip("/")
    return "" if rel in ("", ".") else rel + "/"


def _clip(text, limit):
    """Cut at a word, and say that it was cut."""
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return (cut or text[:limit]).rstrip(" ,;:-—") + "…"


def _until(until_ts):
    return [] if until_ts is None else ["--until=@%d" % int(until_ts)]


def landed(base, rel, since_ts, until_ts=None):
    """Commits in the period that touched this path, newest first, subjects
    clipped. Scoped by pathspec; `sittings.py` reads a sitting's with it."""
    raw = _git(base, ["log", "--since=@%d" % int(since_ts)] + _until(until_ts)
               + ["--no-merges", "--pretty=%H%x00%at%x00%s", "--", rel])
    out = []
    for line in raw.splitlines():
        bits = line.split("\0")
        if len(bits) != 3:
            continue
        out.append({"sha": bits[0][:8], "at": int(bits[1] or 0),
                    "subject": _clip(bits[2].strip(), SUBJECT)})
    return out


def closed(base, rel, root, since_ts, until_ts=None):
    """Plan steps deleted in the period, read out of the plan's own diff.
    `base` is Atlas (`repo_of`)."""
    try:
        targets = plan.paths(root)
    except Exception:                                        # noqa: BLE001
        targets = []
    top = os.path.realpath(base)
    rels = [os.path.relpath(os.path.realpath(t), top) for t in targets
            if paths.within(os.path.realpath(t), top)]
    if not rels:
        return []
    raw = _git(base, ["log", "--since=@%d" % int(since_ts)] + _until(until_ts)
               + ["--no-merges", "-U0", "--pretty=format:", "--"] + rels)
    out, seen = [], set()
    for line in raw.splitlines():
        if not line.startswith("-") or line.startswith("---"):
            continue
        title = _step_title(line[1:])
        if not title or len(title) < 6 or title in seen:
            continue
        seen.add(title)
        out.append(_clip(title, SUBJECT))
    return out


def _step_title(line):
    """A plan line's step title, or ""."""
    m = plan.STEP.match(line)
    if m:
        title = m.group(2)
    else:
        m2 = plan.TODO_ITEM.match(line)
        title = m2.group(2) if m2 and m2.group(1) == " " else ""
    title = re.sub(r"\s+", " ", title).strip(" .-—").strip()
    return re.sub(r"(?:\s*\([^)]*\)[.]?)+$", "", title).strip(" .-—")


# ---------------------------------------------------------------------------
# whose a commit is
# ---------------------------------------------------------------------------
def _log(base, rel, since_ts, until_ts=None):
    """Every commit in the period that touched `rel`, newest first, with EVERY
    file it changed -- `--full-diff`, because whether a commit's own work is in
    this workspace depends on what else it touched."""
    raw = _git(base, ["log", "--since=@%d" % int(since_ts)] + _until(until_ts)
               + ["--no-merges", "--full-diff", "--name-only",
                  "--pretty=format:%x01%H%x00%at%x00%s", "--", rel], timeout=60)
    out = []
    for chunk in raw.split("\x01"):
        lines = chunk.strip("\n").splitlines()
        if not lines:
            continue
        bits = lines[0].split("\0")
        if len(bits) != 3:
            continue
        out.append({"sha": bits[0][:8], "full": bits[0], "at": int(bits[1] or 0),
                    "subject": bits[2].strip(),
                    "files": [f.strip() for f in lines[1:] if f.strip()]})
    return out


def owner_of(subject, ids):
    """The workspace a subject's `<id>: ` prefix names, or ""."""
    said = str(subject or "")
    if ":" not in said:
        return ""
    head = said.split(":", 1)[0].strip()
    return head if head in ids else ""


def is_save(subject, ids):
    """A save rather than a piece of work: `lesson complete`, `stopping point`,
    a handoff -- whoever's prefix is on it."""
    said = str(subject or "").strip()
    if owner_of(said, ids):
        said = said.split(":", 1)[1].strip()
    said = said.lower().rstrip(".")
    return said in SAVES or bool(SAVE_RE.match(said))


def classify(commit, ws_id, rel, ids):
    """`work`, `save` or `other` -- what this commit is to this workspace.

    A commit counts for a workspace only if its own work is there. Another
    workspace's save that swept this one's HANDOFF.md is `other`; a save of any
    workspace is `save`; and a commit whose only files here are HANDOFF.md or
    DIRECTION.md while it changed things elsewhere is another project's work
    with this handoff swept into it. The last two carry their diff instead.
    """
    owner = owner_of(commit["subject"], ids)
    if owner and owner != ws_id:
        return "other"
    if is_save(commit["subject"], ids):
        return "save"
    prefix = prefix_of(rel)
    inside = [f for f in commit["files"] if f.startswith(prefix)]
    outside = [f for f in commit["files"] if not f.startswith(prefix)]
    story = set(prefix + s for s in STORY)
    if inside and outside and all(f in story for f in inside):
        return "other"
    return "work"


def _body(base, sha):
    return _clip(_git(base, ["show", "-s", "--format=%B", sha]), BODY_CHARS)


def _story_rels(rel):
    return [prefix_of(rel) + s for s in STORY]


def _commit_story(base, sha, rel):
    """What one commit did to this workspace's HANDOFF.md and DIRECTION.md."""
    return _clip(_git(base, ["show", "--format=", "--no-color", sha, "--"]
                      + _story_rels(rel)), DIFF_CHARS)


EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def story_diff(base, rel, since_ts, until_ts=None):
    """`{name: diff}`: how HANDOFF.md and DIRECTION.md changed over the period.
    Against the working tree when the period is open, because the meeting is
    now; a file nothing tracks yet is carried whole. `base` is Atlas
    (`repo_of`)."""
    start = _git(base, ["rev-list", "-1", "--before=@%d" % int(since_ts),
                        "HEAD"]).strip() or EMPTY_TREE
    end = []
    if until_ts is not None:
        stop = _git(base, ["rev-list", "-1", "--before=@%d" % int(until_ts),
                           "HEAD"]).strip()
        end = [stop] if stop else []
    out = {}
    for name, one in zip(STORY, _story_rels(rel)):
        diff = _git(base, ["diff", "--no-color", start] + end + ["--", one])
        if not diff.strip() and not end:
            path = os.path.join(base, one)
            tracked = _git(base, ["ls-files", "--", one]).strip()
            if not tracked and os.path.isfile(path):
                try:
                    if os.path.getmtime(path) >= since_ts:
                        with open(path, "r", encoding="utf-8",
                                  errors="replace") as fh:
                            diff = "(new, not yet committed)\n" + fh.read()
                except OSError:
                    diff = ""
        if diff.strip():
            out[name] = _clip(diff, WINDOW_DIFF_CHARS)
    return out


# ---------------------------------------------------------------------------
# the plan
# ---------------------------------------------------------------------------
_STOP = frozenset((
    "the", "and", "for", "with", "its", "into", "from", "this", "that", "only",
    "any", "not", "are", "all", "was", "were", "has", "have", "but", "then",
    "than", "one", "each", "every", "what", "which", "when", "where", "who",
    "they", "them", "there", "their", "been", "being", "does", "done", "out",
    "off", "over", "under", "same", "also", "more", "most", "less", "via",
    "step", "added", "corrected", "next", "now", "new", "after", "before"))


def _stems(text):
    """Distinctive word stems -- the first six letters of every word of three
    or more that is not a common one. Crude on purpose: `integrate`,
    `integrated` and `integration` are one stem."""
    return set(w[:6] for w in re.findall(r"[a-z][a-z0-9]+", str(text).lower())
               if len(w) >= 3 and w not in _STOP)


def open_steps(text):
    """`[{title, detail}]`: every step a plan still lists, with the indented
    lines under it -- the words a mentor-facing sentence can be made from."""
    out, seen, cur, indent = [], set(), None, 0
    for line in (text or "").splitlines():
        title = _step_title(line)
        if title and len(title) >= 6:
            key = " ".join(sorted(_stems(title)))
            cur = None
            if key in seen:
                continue
            seen.add(key)
            # THE HEADING, AND THE REST AS DETAIL. `INTEGRATE HIS SECTIONS.
            # Same treatment as the 2026-09-02 round: ...` is a step called
            # three words, and the sentence after it describes it.
            head, rest = _head_of(title)
            cur = {"title": _clip(head, 200), "detail": [rest] if rest else []}
            indent = len(line) - len(line.lstrip())
            out.append(cur)
            continue
        if cur is None:
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if len(line) - len(line.lstrip()) <= indent or len(cur["detail"]) >= 6:
            cur = None
            continue
        cur["detail"].append(stripped)
    for s in out:
        s["detail"] = _clip(" ".join(s["detail"]), 500)
    return out


def _head_of(title):
    """`(heading, rest)`: a step's words up to its first full stop, colon or
    dash, where that comes early enough to be a heading."""
    m = re.match(r"^(.{6,90}?)(?:[.:]\s+|\s+[—-]{1,2}\s+)(\S.*)$", title)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return title, ""


def maybe_done(step, commits):
    """The commits that look as though they already did this open step.

    Most of the step title's stems in one commit's message -- at least two, and
    at least 60 % -- or a large share of its description's. A flag, not a
    verdict: the writer is told to check the commit before calling the step
    next, which is the whole cure for a stale plan."""
    title = _stems(step["title"])
    words = title | _stems(step.get("detail") or "")
    hits = []
    for c in commits:
        said = _stems(c["subject"] + " " + (c.get("body") or ""))
        t = len(title & said)
        b = len(words & said)
        if (len(title) >= 2 and t >= max(2, math.ceil(0.6 * len(title)))) \
                or (len(words) >= 8 and b >= max(8, math.ceil(0.5 * len(words)))):
            hits.append(c["sha"])
    return hits


def _sentence_case(title):
    """A plan heading typed in capitals, as a sentence. The brief hands the
    writer words, not a heading to copy onto a slide."""
    letters = [ch for ch in title if ch.isalpha()]
    if letters and sum(ch.isupper() for ch in letters) > 0.7 * len(letters):
        low = title.lower()
        return low[:1].upper() + low[1:]
    return title


# ---------------------------------------------------------------------------
# one workspace
# ---------------------------------------------------------------------------
def _name_of(ws):
    try:
        from .course import config
        return config.read_config(ws["root"])["name"] or ws["dir"]
    except Exception:                                        # noqa: BLE001
        return ws.get("dir") or ws["id"]


def gather(base, ws, since_ts, until_ts=None, ids=None, rows=None):
    """Everything the period holds for one workspace, or None where nothing
    moved. `rows` is `sittings._shown`'s, passed in so a deck of five
    workspaces walks the archives once.

    `base` is Atlas, which holds the history and is what the brief names paths
    against (`repo_of`)."""
    root = ws["root"]
    top, rel = repo_of(root, base)
    if ids is None:
        ids = set(w["id"] for w in atlas.workspaces(base))
    work, saves = [], []
    for c in _log(top, rel, since_ts, until_ts):
        kind = classify(c, ws["id"], rel, ids)
        if kind == "work":
            if len(work) < MOST_COMMITS:
                c["body"] = _body(top, c["full"])
                # A FINDING WRITTEN INTO THE HANDOFF. `the KNN gap is
                # neighbourhood size, not the metric` is a subject whose whole
                # argument is the HANDOFF.md diff it carries.
                story = set(_story_rels(rel))
                c["diff"] = (_commit_story(top, c["full"], rel)
                             if story & set(c["files"]) else "")
                work.append(c)
            continue
        if len(saves) >= MOST_SAVES:
            continue
        diff = _commit_story(top, c["full"], rel)
        prefix = prefix_of(rel)
        also = [f[len(prefix):] for f in c["files"] if f.startswith(prefix)
                and f[len(prefix):] not in STORY]
        if not diff.strip() and not (kind == "save" and also):
            continue
        saves.append({"sha": c["sha"], "at": c["at"], "subject": c["subject"],
                      "owner": owner_of(c["subject"], ids), "kind": kind,
                      "diff": diff, "also": also[:20] if kind == "save" else []})

    story = story_diff(top, rel, since_ts, until_ts)

    held = []
    if rows is not None:
        stop = time.time() if until_ts is None else until_ts
        for r in rows:
            if r["ws"] != ws["id"] or r["end"] < since_ts or r["start"] > stop:
                continue
            held.append(r)

    steps_now = []
    try:
        targets = plan.paths(root)
    except Exception:                                        # noqa: BLE001
        targets = []
    # Two names for each plan: against Atlas for the brief, which names files
    # the way the writer opens them, and against the top for git.
    plan_rels, plan_git = [], []
    for t in targets:
        try:
            with open(t, "r", encoding="utf-8", errors="replace") as fh:
                steps_now += open_steps(fh.read())
            plan_rels.append(os.path.relpath(t, base))
            plan_git.append(os.path.relpath(os.path.realpath(t), top))
        except OSError:
            continue
    left = [_stems(s["title"] + " " + s["detail"]) for s in steps_now]
    def still_open(t):
        head = _stems(_head_of(t)[0])
        return any(_same(_stems(t), k) or (head and head <= k) for k in left)

    gone = [t for t in closed(top, rel, root, since_ts, until_ts)
            if not still_open(t)]
    # A PLAN REWRITTEN IS NOT A PLAN DONE: most of it going at once is a change
    # of direction, and the brief says so rather than calling it finished.
    was = _steps_at(top, plan_git, since_ts)
    dropped = []
    if len(gone) > 2 and 2 * len(gone) > max(was, len(gone)):
        dropped, gone = gone, []
    for s in steps_now:
        s["maybe"] = maybe_done(s, work)

    block = {"id": ws["id"], "name": _name_of(ws), "root": root, "rel": rel,
             "commits": work, "saves": saves, "story": story, "sittings": held,
             "closed": gone, "dropped": dropped, "open": steps_now,
             "plans": plan_rels, "fenced": list(fenced.holds(root))}
    if not (work or saves or story or gone or dropped or held):
        return None
    return block


def _steps_at(base, plan_rels, when):
    """How many steps the plans listed at `when`, off the last commit before."""
    n = 0
    for r in plan_rels:
        sha = _git(base, ["rev-list", "-1", "--before=@%d" % int(when), "HEAD",
                          "--", r]).strip()
        if sha:
            n += len(open_steps(_git(base, ["show", "%s:%s" % (sha, r)])))
    return n


def _same(a, b):
    if not a or not b:
        return False
    return len(a & b) >= 0.6 * max(len(a), len(b))


def blocks_for(base, want, since_ts, until_ts=None):
    """`(blocks, every, refusal)` for the workspaces asked for. `want` is ids
    or bare directory names, matched against the walk; nothing else is read."""
    from . import sittings                              # local: a cycle
    every = atlas.workspaces(base)
    if want:
        want = set(want)
        every = [w for w in every if w["id"] in want or w["dir"] in want]
        if not every:
            return [], [], "none of those are workspaces in this repository"
    ids = set(w["id"] for w in atlas.workspaces(base))
    try:
        rows, _ = sittings._shown(base)
    except Exception:                                        # noqa: BLE001
        rows = []
    blocks = []
    for ws in every:
        try:
            one = gather(base, ws, since_ts, until_ts, ids=ids, rows=rows)
        except Exception:                                    # noqa: BLE001
            one = None
        if one:
            blocks.append(one)
    return blocks, every, ""


def _groups(blocks):
    """The blocks in the shape `sittings.host_for` reads, so the meeting deck
    takes the deck from sittings' answer rather than a second one."""
    return [{"ws": b["id"], "ws_name": b["name"],
             "row": {"fenced": b["fenced"], "root": b["root"]},
             "items": b["commits"] + b["saves"] + b["closed"] + b["sittings"]
             + b.get("dropped", [])
             + ([1] if b["story"] else [])}
            for b in blocks]


def host_for(blocks):
    """`(host id, refusal)`. A fenced workspace hosts; two cannot share."""
    from . import sittings                              # local: a cycle
    groups = _groups(blocks)
    clash = sittings.mixed_fences(groups)
    if clash:
        return "", clash
    return sittings.host_for(groups), ""


# ---------------------------------------------------------------------------
# the brief
# ---------------------------------------------------------------------------
def _figures(blocks, since_ts, until_ts):
    """`(chosen, catalog, catalog_left)`: the period's figures first, newest
    first and at most `PER_WORKSPACE_FIGURES` a workspace; every other figure
    of those workspaces in the catalog, the ones the brief's words mention
    first."""
    from .course import results
    stop = time.time() if until_ts is None else until_ts
    chosen, rest = [], []
    for b in blocks:
        try:
            idx = results.index(b["root"])
        except Exception:                                    # noqa: BLE001
            continue
        figs = sorted((r for r in idx.values() if r.get("kind") == "figure"),
                      key=lambda r: -(r.get("at") or 0))
        n = 0
        for r in figs:
            one = {"ws": b["id"], "root": b["root"], "rec": r}
            if since_ts <= (r.get("at") or 0) <= stop + 1 \
                    and n < PER_WORKSPACE_FIGURES:
                chosen.append(one)
                n += 1
            else:
                rest.append(one)
    chosen.sort(key=lambda f: -(f["rec"].get("at") or 0))
    rest += chosen[MOST_FIGURES:]
    chosen = chosen[:MOST_FIGURES]
    said = set()
    for b in blocks:
        for c in b["commits"]:
            said |= _stems(c["subject"] + " " + c.get("body", ""))

    def overlap(f):
        r = f["rec"]
        return len(said & _stems(" ".join(str(r.get(k) or "")
                                          for k in ("file", "name", "where"))))

    rest.sort(key=lambda f: (-overlap(f), -(f["rec"].get("at") or 0)))
    return chosen, rest[:MOST_CATALOG], max(0, len(rest) - MOST_CATALOG)


def _tables(blocks, since_ts, until_ts):
    from .course import results
    stop = time.time() if until_ts is None else until_ts
    out = []
    for b in blocks:
        try:
            idx = results.index(b["root"])
        except Exception:                                    # noqa: BLE001
            continue
        for r in sorted(idx.values(), key=lambda r: -(r.get("at") or 0)):
            if r.get("kind") != "table" or fenced.refused(r.get("rel") or ""):
                continue
            if since_ts <= (r.get("at") or 0) <= stop + 1:
                out.append({"ws": b["id"], "rel": r["rel"],
                            "path": os.path.join(b["root"], r["rel"]),
                            "name": r.get("name") or "", "iso": r.get("iso") or ""})
    return out[:MOST_TABLES]


def _allowed(base, path):
    rel = os.path.relpath(path, base)
    return "" if fenced.refused(rel) or fenced.refused(path) else path


def _when(t):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(t))


def _quote(text):
    return "  > " + str(text).replace("\n", "\n  > ")


def _fence_block(text):
    return ["```diff", str(text).rstrip("\n").replace("```", "'''"), "```"]


def deck_rel(host_root, base):
    """The deck's directory, relative to the repository."""
    return os.path.relpath(os.path.join(host_root, WRITEUPS, DECK_DIR), base)


def write_brief(base, deck, blocks, since_ts, until_ts=None, human="",
                wid="", host="", dry=False):
    """Write the deck's directory -- `.gitignore`, the page-mark package, the
    figures, `_brief.md`, `_brief.json` -- and return the record. `dry` writes
    nothing and returns the record with the brief's text in `markdown`."""
    from . import sittings                              # local: a cycle
    until_shown = time.time() if until_ts is None else until_ts
    period = period_text(since_ts, until_shown)
    names = dict((b["id"], b["name"]) for b in blocks)
    here = os.path.relpath(deck, base)
    if not dry:
        os.makedirs(deck, exist_ok=True)
        with open(os.path.join(deck, ".gitignore"), "w", encoding="utf-8") as fh:
            fh.write("# written by the board: figures can be made from records,"
                     " the brief\n# quotes diffs, and this repository is public."
                     " The .tex is tracked.\n" + "\n".join(IGNORE) + "\n")
        with open(os.path.join(deck, STY), "w", encoding="utf-8") as fh:
            fh.write(STY_TEXT)

    chosen, catalog, catalog_left = _figures(blocks, since_ts, until_ts)
    made = []
    for f in chosen:
        rid = f["rec"]["id"]
        if dry:
            ext = os.path.splitext(f["rec"].get("rel") or "")[1].lower() or ".png"
            rel = "%s/%s--%s%s" % (FIGURES, sittings.ws_slug(f["ws"]), rid, ext)
        else:
            rel = sittings.snapshot(f["root"], rid, f["ws"], deck)
        if not rel:
            continue
        size = None if dry else sittings.png_size(os.path.join(deck, rel))
        made.append({"file": rel, "ws": f["ws"], "id": rid,
                     "where": f["rec"].get("where") or "",
                     "name": f["rec"].get("name") or "",
                     "date": f["rec"].get("iso") or "",
                     "size": ("%d x %d" % size) if size else ""})
    tables = _tables(blocks, since_ts, until_ts)

    sources = []
    steps = []
    out = ["# The brief for the meeting deck `%s/%s.tex`" % (here, STEM), "",
           "Written by the board on %s. You write `%s/%s.tex` and build it; "
           "nothing else in this directory is yours to edit."
           % (_when(time.time()), WRITEUPS + "/" + DECK_DIR, STEM), "",
           "## Who it is for", "",
           "The MENTORS who supervise these projects, at their next meeting. "
           "They know the field. They did not see any of the work, the "
           "sittings, the plan files or the board, and none of its private "
           "names mean anything to them. They will mark up the slides with "
           "suggestions for what to do next.", "",
           "## The period", "",
           "%s (%s). The title slide says exactly this." % (period, human or
                                                             "the period asked for"),
           "",
           "## The projects", ""]
    for b in blocks:
        out.append("- **%s** -- workspace id `%s`, the argument its frames "
                   "give `\\meetingws`." % (b["name"], b["id"]))
    out.append("")

    fences = []
    for b in blocks:
        out += ["## %s (`%s`)" % (b["name"], b["id"]), ""]
        reads = []
        for name in STORY:
            p = os.path.join(b["root"], name)
            if os.path.isfile(p) and _allowed(base, p):
                reads.append("`%s`" % os.path.relpath(p, base))
                sources.append(p)
        for r in b["plans"]:
            p = os.path.join(base, r)
            if _allowed(base, p):
                reads.append("the plan `%s`" % r)
                sources.append(p)
        if reads:
            out += ["To read more: " + ", ".join(reads) + ".", ""]

        out += ["### What landed: %d commit%s of this project's own work"
                % (len(b["commits"]), "" if len(b["commits"]) == 1 else "s"),
                ""]
        if not b["commits"]:
            out += ["None in the period. The story is in the handoff and "
                    "direction below.", ""]
        for c in b["commits"]:
            head = _clip(c["subject"], 160)
            out.append("- `%s` (%s) **%s**" % (c["sha"], _when(c["at"]), head))
            # THE WHOLE MESSAGE, which here is often one 300-word subject line:
            # a clipped one is half a clause, and that was the old deck.
            body = (c.get("body") or "").strip()
            if body and body != head.strip():
                out.append(_quote(body))
            if (c.get("diff") or "").strip():
                out += ["", "  What it wrote into the handoff or direction:",
                        ""] + _fence_block(c["diff"]) + [""]
        out.append("")

        if b["saves"]:
            out += ["### Saves that carried this project's handoff or direction",
                    "",
                    "These are NOT this project's commits. A save of the board, "
                    "or another project's work, swept these files in; what they "
                    "changed is the record.", ""]
            for s in b["saves"]:
                who = ("a save from %s" % s["owner"] if s["kind"] == "other"
                       and s["owner"] else "another project's work"
                       if s["kind"] == "other" else "a save")
                out.append("- `%s` (%s), %s: %s" % (s["sha"], _when(s["at"]),
                                                   who, _clip(s["subject"], 120)))
                if s["also"]:
                    out.append("  It also changed, in this project: %s."
                               % ", ".join("`%s`" % f for f in s["also"]))
                if s["diff"].strip():
                    out += [""] + _fence_block(s["diff"]) + [""]
            out.append("")

        if b["story"]:
            out += ["### How HANDOFF.md and DIRECTION.md changed over the period",
                    ""]
            for name, diff in b["story"].items():
                out += ["%s:" % name, ""] + _fence_block(diff) + [""]

        if b["sittings"]:
            out += ["### Sittings held in the period", ""]
            for r in b["sittings"]:
                where = []
                for m in r["members"]:
                    for what, p in (("cards", m["cards_dir"]),
                                    ("transcript", m["turns"])):
                        if os.path.exists(p) and _allowed(base, p):
                            where.append("%s `%s`" % (what, p))
                            if what == "cards":
                                sources.append(p)
                out.append("- %s: %d card%s%s" % (
                    r["label"], r["cards"], "" if r["cards"] == 1 else "s",
                    (". " + "; ".join(where)) if where else ""))
            out.append("")

        if b["closed"]:
            out += ["### Plan steps that closed", ""]
            out += ["- %s" % _sentence_case(t) for t in b["closed"]] + [""]
            steps += b["closed"]
        if b.get("dropped"):
            out += ["### Plan steps dropped when the plan was rewritten", "",
                    "Most of the plan went at once, which is a change of "
                    "direction rather than work done. Say what was dropped and "
                    "why only where the direction diff above explains it.", ""]
            out += ["- %s" % _sentence_case(t) for t in b["dropped"]] + [""]
            steps += b["dropped"]
        if b["open"]:
            out += ["### Plan steps still open", "",
                    "In the plan's order. A step marked MAY ALREADY BE DONE has "
                    "a landed commit that looks as though it did it: read that "
                    "commit above before calling the step next.", ""]
            for s in b["open"]:
                line = "- %s" % _sentence_case(s["title"])
                if s["detail"]:
                    line += " -- %s" % s["detail"]
                if s["maybe"]:
                    line += " **MAY ALREADY BE DONE: %s.**" % ", ".join(
                        "`%s`" % sha for sha in s["maybe"])
                out.append(line)
                steps.append(s["title"])
            out.append("")

        for name in b["fenced"]:
            line = "- %s holds `%s/`: never open anything under it." % (b["id"], name)
            if line not in fences:
                fences.append(line)

    if tables:
        out += ["## Tables written in the period", "",
                "Open one for a number the commits do not give.", ""]
        for t in tables:
            out.append("- %s: `%s` (%s)" % (t["ws"], os.path.relpath(
                t["path"], base), t["iso"]))
            sources.append(t["path"])
        out.append("")
    if fences:
        out += ["## Fences", ""] + fences + [""]

    out += ["## Figures already copied beside the deck", ""]
    if made:
        out += ["| file | workspace | where | name | date | pixels |",
                "|---|---|---|---|---|---|"]
        out += ["| `%s` | %s | %s | %s | %s | %s |"
                % (f["file"], f["ws"], sittings._cell(f["where"]),
                   sittings._cell(f["name"]), f["date"], f["size"]) for f in made]
    else:
        out.append("None: nothing in the period wrote a figure this board can "
                   "show.")
    out += ["", "OPEN A FIGURE BEFORE YOU USE IT, and say on the slide what it "
            "shows.", "",
            "## Other figures you may pull", "",
            "`board deckfig %s/%s <workspace> <result id>` copies one into "
            "`figures/` and prints the path to put in `\\includegraphics`."
            % (WRITEUPS, DECK_DIR), ""]
    if catalog:
        out += ["| workspace | result id | where | name | date |",
                "|---|---|---|---|---|"]
        out += ["| %s | `%s` | %s | %s | %s |"
                % (f["ws"], f["rec"]["id"], sittings._cell(f["rec"].get("where")),
                   sittings._cell(f["rec"].get("name")), f["rec"].get("iso") or "")
                for f in catalog]
    else:
        out.append("There are none.")
    if catalog_left:
        out += ["", "%d more exist and are not listed; give `board deckfig` a "
                "word from a file name instead of an id." % catalog_left]

    out += ["", "## The shape of the deck", "",
            "1. A title slide: what the deck is, and the period exactly as "
            "given above. `\\meetingshared`.",
            "2. One summary slide: each project in one line, with its headline "
            "number. `\\meetingshared`.",
            "3. Per project, as many slides as it needs, each with "
            "`\\meetingws{<its workspace id>}`: what was found (the number and "
            "the figure), what changed in direction and why, and what is next "
            "in plain words.",
            "4. One closing slide: the decisions or asks for the mentors. "
            "`\\meetingshared`.", "",
            "## How to write it", "",
            "- `\\documentclass[aspectratio=169]{beamer}`, then "
            "`\\usepackage{meetingws}` -- the file is beside the deck.",
            "- EVERY FRAME calls exactly one of `\\meetingws{<workspace id>}` "
            "or `\\meetingshared`. A mentor's mark on a page is routed to the "
            "project its frame names; a frame with none, or two, refuses the "
            "deck.",
            "- ONE PAGE PER FRAME: no `allowframebreaks`, no `\\pause`, no "
            "overlays.",
            "- No internal names on a slide: no commit hashes, no map box "
            "names, no plan headings copied as written, no `his` or `her` "
            "without saying whose, no links to the board.",
            "- Every number on a slide comes from this brief or a file it "
            "names. After the build the board checks each one and lists any "
            "it cannot find beside the deck.",
            "- A figure is `\\includegraphics[width=\\linewidth,height=0.72"
            "\\textheight,keepaspectratio]{figures/<file>}`.",
            "- Build it IN ITS OWN DIRECTORY: `cd %s/%s && pdflatex "
            "-interaction=nonstopmode %s.tex`, twice. The `.aux` it leaves is "
            "where the page marks are read from, so leave it there. A LaTeX "
            "error is yours to fix before the turn ends."
            % (WRITEUPS, DECK_DIR, STEM), ""]
    markdown = "\n".join(out)

    rec = {"kind": "meeting", "slug": DECK_DIR, "wid": wid, "host": host,
           "at": time.time(), "since": since_ts, "until": until_ts,
           "period": period, "human": human,
           "workspaces": [b["id"] for b in blocks], "names": names,
           "figures": [f["file"] for f in made],
           "sources": sorted(set(s for s in sources if _allowed(base, s))),
           "steps": sorted(set(steps)), "items": []}
    if dry:
        rec["markdown"] = markdown
        return rec
    with open(os.path.join(deck, BRIEF_MD), "w", encoding="utf-8") as fh:
        fh.write(markdown)
    with open(os.path.join(deck, BRIEF_JSON), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2)
    return rec


def read_brief(deck):
    try:
        with open(os.path.join(deck, BRIEF_JSON), "r", encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return None
    return got if isinstance(got, dict) and got.get("kind") == "meeting" else None


def is_deck_dir(path):
    """Is this directory the meeting deck? The library leaves it out: its
    reader is `/meeting`, where ink is direction rather than revision."""
    return read_brief(path) is not None


# ---------------------------------------------------------------------------
# the record at the root
# ---------------------------------------------------------------------------
_LOCK = threading.Lock()


def _record_path(base):
    return os.path.join(base, OUT_DIR, RECORD)


def _read_record(base):
    try:
        with open(_record_path(base), "r", encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        return None
    return rec if isinstance(rec, dict) else None


def _write_record(base, rec):
    path = _record_path(base)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2)
    os.replace(tmp, path)


def _deck_of(base, rec):
    where = str((rec or {}).get("dir") or "")
    if not where or where.startswith("..") or os.path.isabs(where):
        return ""
    deck = os.path.realpath(os.path.join(base, where))
    if not paths.within(deck, base):
        return ""
    return deck


def deck(base):
    """The one deck, as the record describes it, or None if none was asked
    for. `has_pdf` is true only for a deck that is READY -- built, and its page
    map read back off the build."""
    rec = _read_record(base)
    if not rec:
        return None
    d = _deck_of(base, rec)
    rec["pdf"] = os.path.join(d, STEM + ".pdf") if d else ""
    rec["tex"] = os.path.join(d, STEM + ".tex") if d else ""
    rec["has_pdf"] = bool(d) and rec.get("state") == "ready" \
        and os.path.isfile(rec["pdf"])
    return rec


def provenance(base):
    """What the sidecar beside the deck lists, or {}."""
    rec = _read_record(base)
    d = _deck_of(base, rec) if rec else ""
    if not d:
        return {}
    try:
        with open(os.path.join(d, PROVENANCE), "r", encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return {}
    return got if isinstance(got, dict) else {}


# ---------------------------------------------------------------------------
# asking for one
# ---------------------------------------------------------------------------
def _clear_deck(d):
    """Take a deck's directory away. One deck, replaced each time: git holds
    every `.tex` there has been."""
    if d and os.path.isdir(d) and (is_deck_dir(d)
                                   or os.path.isfile(os.path.join(d, STY))):
        shutil.rmtree(d, ignore_errors=True)


def occupied(host_root):
    """Why the deck cannot be written in this host, or "". A `writeups/meeting/`
    the board did not write is somebody's document, and asking would take it
    away: `_clear_deck` leaves it, and the brief and the writer would write
    over it."""
    d = os.path.join(host_root, WRITEUPS, DECK_DIR)
    if os.path.lexists(d) and not (os.path.isdir(d) and (
            is_deck_dir(d) or os.path.isfile(os.path.join(d, STY)))):
        return ("%s/%s/ in %s is not a meeting deck the board wrote, and the "
                "deck would write over it. Move it, then ask again."
                % (WRITEUPS, DECK_DIR, os.path.basename(host_root.rstrip("/"))))
    return ""


def prepare(base, host_root, blocks, since_ts, human, wid, host, repo=None,
            until_ts=None):
    """Everything that happens once the ask is allowed and before the turn is
    asked: the old deck, its ink and its pictures go; the new brief is written;
    the record says it is being written. Returns the record."""
    from . import proposals                          # local: a cycle
    with _LOCK:
        old = _read_record(base)
        old_deck = _deck_of(base, old) if old else ""
        new_deck = os.path.join(host_root, WRITEUPS, DECK_DIR)
        _clear_deck(old_deck)
        _clear_deck(new_deck)
        # The assembled deck's leftovers at the root. The pointer replaces them.
        for n in (STEM + ".tex", STEM + ".pdf"):
            try:
                os.remove(os.path.join(base, OUT_DIR, n))
            except OSError:
                pass
        brief = write_brief(base, new_deck, blocks, since_ts, until_ts, human,
                            wid=wid, host=host)
        cleared = clear_ink(repo) if repo is not None else 0
        pictures = proposals.forget_pictures(base)
        rec = {"name": STEM, "state": "being written", "why": "", "wid": wid,
               "host": host, "dir": os.path.relpath(new_deck, base),
               "asked_at": time.time(), "since": human, "since_ts": since_ts,
               "period": brief["period"], "workspaces": brief["workspaces"],
               "names": brief["names"], "pages": {}, "problems": [],
               "unsupported": 0, "built": False, "at": time.time(),
               "cleared": cleared, "pictures": pictures}
        _write_record(base, rec)
    return rec


# ---------------------------------------------------------------------------
# once it is built
# ---------------------------------------------------------------------------
def pdf_pages(pdf):
    """How many pages, off `pdfinfo`, or 0."""
    try:
        p = subprocess.run(["pdfinfo", pdf], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return 0
    for ln in p.stdout.decode("utf-8", "replace").splitlines():
        if ln.startswith("Pages:"):
            try:
                return int(ln.split()[1])
            except (IndexError, ValueError):
                return 0
    return 0


def pdf_text(pdf):
    """The deck's text, or "" where `pdftotext` is not here."""
    try:
        p = subprocess.run(["pdftotext", "-layout", pdf, "-"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return p.stdout.decode("utf-8", "replace") if p.returncode == 0 else ""


MARK_RE = re.compile(r"\\meetingpage\{(\d+)\}\{([^{}]*)\}")


def page_map(deck_dir, workspaces, pages=None):
    """`(pages, problems)` off the compiled deck: `{page: workspace id}` for
    every project page, and one sentence per page that cannot be routed. A
    shared page belongs to nobody and is not in the map."""
    pdf = os.path.join(deck_dir, STEM + ".pdf")
    aux = os.path.join(deck_dir, STEM + ".aux")
    n = pdf_pages(pdf) if pages is None else pages
    if not n:
        return {}, ["the PDF has no pages this board can count"]
    try:
        with open(aux, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        stale = os.path.getmtime(aux) < os.path.getmtime(pdf) - 300
    except OSError:
        return {}, ["no page says whose it is: the build left no %s.aux, so "
                    "the deck was not built with \\usepackage{meetingws}" % STEM]
    if stale:
        return {}, ["%s.aux is older than the PDF, so its page marks describe "
                    "another build" % STEM]
    by = {}
    for p, w in MARK_RE.findall(text):
        by.setdefault(int(p), set()).add(w.strip())
    out, problems = {}, []
    known = set(workspaces)
    for p in range(1, n + 1):
        got = by.get(p) or set()
        if not got:
            problems.append("page %d says no workspace: its frame has no "
                            "\\meetingws (or \\meetingshared)" % p)
            continue
        if len(got) > 1:
            problems.append("page %d is marked with two: %s"
                            % (p, " and ".join(sorted(got))))
            continue
        w = got.pop()
        if w == "*":
            continue
        if w not in known:
            problems.append("page %d names %s, which this deck is not about"
                            % (p, w))
            continue
        out[str(p)] = w
    return out, problems


# NUMBERS. A decimal, a grouped integer (`42{,}579`, `42,579`), or a plain one.
NUMBER_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
                       r"(?![\w])")
UNIT_RE = re.compile(r"\d*\.?\d+(?:pt|em|ex|cm|mm|in|bp|sp|px)\b"
                     r"|\d*\.?\d+\s*\\(?:linewidth|textwidth|textheight|paperwidth"
                     r"|paperheight|columnwidth|baselineskip)")
# Commands whose every argument is layout or an address, never a claim.
DROP_ALL = re.compile(
    r"\\(?:meetingws|includegraphics|label|ref|eqref|cite\w*|url|"
    r"vspace\*?|hspace\*?|setlength|addtolength|definecolor|usetheme|"
    r"usecolortheme|usefonttheme|setbeamer\w+|rule|resizebox|"
    r"begin\{column\}|column)\s*(?:\[[^\]]*\]\s*)*(?:\{[^{}]*\}\s*)*")
# And the ones whose FIRST argument is: a colour, a scale, a link's target.
DROP_FIRST = re.compile(
    r"\\(?:color|textcolor|colorbox|scalebox|href)\s*(?:\[[^\]]*\]\s*)*\{[^{}]*\}")


def _numbers_of(text):
    """Every number in a text, as strings, thousands separators taken out."""
    return [m.replace(",", "") for m in NUMBER_RE.findall(text)]


def _clean_tex(tex):
    """The deck's body with everything that is not what a slide says taken
    out: the preamble, comments, commands' options and arguments that are
    layout, dimensions, and colour mixes."""
    body = tex.split("\\begin{document}", 1)[-1]
    body = re.sub(r"(?<!\\)%.*", "", body)
    body = body.replace("{,}", ",").replace("\\,", "").replace("~", " ")
    body = DROP_ALL.sub(" ", body)
    body = DROP_FIRST.sub(" ", body)
    body = UNIT_RE.sub(" ", body)
    body = re.sub(r"![0-9]+", " ", body)
    body = re.sub(r"\\\\\[[^\]]*\]", " ", body)
    return body


def _supported_values(corpus):
    """Every rounding of every number in the sources, so a slide's `60.2 %`
    is found for a source's `0.602` and its `0.60` for `0.602`."""
    have = set()
    for raw in set(_numbers_of(corpus)):
        try:
            v = float(raw)
        except ValueError:
            continue
        for x in (v, v * 100, v / 100):
            for d in range(0, 5):
                have.add(("%." + str(d) + "f") % round(x, d))
    return have


def _frame_titles(body):
    """`[(offset, title)]` of every frame, so a finding can say which slide."""
    out = []
    for m in re.finditer(r"\\begin\{frame\}(?:\[[^\]]*\])?(?:\{([^{}]*)\})?", body):
        title = m.group(1) or ""
        if not title:
            t = re.search(r"\\frametitle\{([^{}]*)\}", body[m.end():m.end() + 400])
            title = t.group(1) if t else ""
        out.append((m.start(), re.sub(r"\\[a-zA-Z]+|[{}$]", "", title).strip()))
    return out


def _where(frames, offset):
    n, title = 0, ""
    for i, (at, t) in enumerate(frames):
        if at <= offset:
            n, title = i + 1, t
    return n, title


def _corpus(base, brief, deck_dir):
    """The brief and every source it names, read to a limit."""
    parts = []
    total = 0
    try:
        with open(os.path.join(deck_dir, BRIEF_MD), "r", encoding="utf-8",
                  errors="replace") as fh:
            parts.append(fh.read())
    except OSError:
        pass
    files = []
    for s in brief.get("sources") or []:
        s = str(s)
        if not _allowed(base, s) or not paths.within(s, base):
            continue
        if os.path.isdir(s):
            try:
                files += [os.path.join(s, n) for n in sorted(os.listdir(s))
                          if n.endswith(".md")]
            except OSError:
                continue
        elif os.path.isfile(s):
            files.append(s)
    for f in files:
        if total >= CORPUS_BYTES:
            break
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                got = fh.read(SOURCE_BYTES)
        except OSError:
            continue
        total += len(got)
        parts.append(got)
    return "\n".join(parts)


def _figures_used(deck_dir, tex):
    """The image files the build read, relative to the deck: the recorder's
    `.fls` where there is one, else the log's `<file>` entries, else the
    `\\includegraphics` in the source."""
    found = []
    fls = os.path.join(deck_dir, STEM + ".fls")
    log = os.path.join(deck_dir, STEM + ".log")
    exts = (".png", ".jpg", ".jpeg", ".pdf", ".eps", ".svg")
    try:
        with open(fls, "r", encoding="utf-8", errors="replace") as fh:
            for ln in fh:
                if ln.startswith("INPUT "):
                    p = ln[6:].strip()
                    if p.lower().endswith(exts) and not p.endswith(STEM + ".pdf"):
                        found.append(p)
    except OSError:
        pass
    if not found:
        try:
            with open(log, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            found = re.findall(r"<([^<>\s,]+\.(?:png|jpe?g|pdf|eps))", text, re.I)
        except OSError:
            pass
    if not found:
        found = re.findall(r"\\includegraphics\s*(?:\[[^\]]*\])?\{([^{}]+)\}", tex)
    out = []
    for p in found:
        full = os.path.normpath(p if os.path.isabs(p) else os.path.join(deck_dir, p))
        rel = os.path.relpath(full, deck_dir).replace(os.sep, "/")
        if rel not in out:
            out.append(rel)
    return out


def check_sources(base, deck_dir, brief):
    """`{numbers, figures, internal}` -- everything on the deck no source
    supports. A number counts when some number in a source rounds to it
    (directly, or as a percentage); a figure when it was copied by the board
    or through `board deckfig` from a workspace the deck is about."""
    from . import sittings                              # local: a cycle
    from .course import results
    try:
        with open(os.path.join(deck_dir, STEM + ".tex"), "r", encoding="utf-8",
                  errors="replace") as fh:
            tex = fh.read()
    except OSError:
        tex = ""
    body = _clean_tex(tex)
    frames = _frame_titles(body)
    have = _supported_values(_corpus(base, brief, deck_dir))

    numbers, seen = [], set()
    for m in NUMBER_RE.finditer(body):
        raw = m.group(1).replace(",", "")
        if "." not in raw and len(raw) == 1:
            continue                          # a count or a label, not a claim
        if "." not in raw and raw.isdigit() and int(raw) <= 10:
            continue
        d = len(raw.split(".", 1)[1]) if "." in raw else 0
        key = ("%." + str(d) + "f") % float(raw)
        if key in have or raw in have:
            continue
        n, title = _where(frames, m.start())
        ctx = re.sub(r"\\[a-zA-Z]+\*?|[{}$\\]", " ", body[max(0, m.start() - 60):
                                                          m.end() + 40])
        ctx = re.sub(r"\s+", " ", ctx).strip()
        if (raw, n) in seen:
            continue
        seen.add((raw, n))
        numbers.append({"value": m.group(1), "frame": n, "title": title,
                        "context": _clip(ctx, 140)})

    copied = set(brief.get("figures") or [])
    offered = {}
    for w in brief.get("workspaces") or []:
        for ws in atlas.workspaces(base):
            if ws["id"] == w:
                try:
                    offered[sittings.ws_slug(w)] = set(results.index(ws["root"]))
                except Exception:                            # noqa: BLE001
                    offered[sittings.ws_slug(w)] = set()
    figures = []
    for rel in _figures_used(deck_dir, tex):
        if rel in copied:
            continue
        m = re.match(r"^%s/([a-z0-9-]+)--([A-Za-z0-9_-]+)\.[A-Za-z]+$" % FIGURES, rel)
        if m and m.group(2).lower() in offered.get(m.group(1), set()) \
                and os.path.isfile(os.path.join(deck_dir, rel)):
            continue
        figures.append({"file": rel})

    return {"numbers": numbers, "figures": figures}


def internal_names(text, brief):
    """`(leaks, headings)` in the deck's text: addresses nobody outside can
    open, and plan headings copied as the plan types them."""
    flat = re.sub(r"\s+", " ", text or "")
    leaks = sorted(set(m.group(0) for m in INTERNAL_URL.finditer(flat)))
    heads = []
    for t in brief.get("steps") or []:
        letters = [ch for ch in t if ch.isalpha()]
        if not letters or sum(ch.isupper() for ch in letters) < 0.7 * len(letters):
            continue
        key = re.sub(r"\s+", " ", t).strip(" .")
        if len(key) >= 8 and key in flat:
            heads.append(key)
    return leaks, heads


def finalize(base, rec):
    """Read a built deck back: its page map, and what no source supports.
    Returns the record, now `ready` or `did not land`, and writes the sidecar
    beside the deck."""
    d = _deck_of(base, rec)
    brief = read_brief(d) or {}
    pages, problems = page_map(d, rec.get("workspaces") or [])
    text = pdf_text(os.path.join(d, STEM + ".pdf"))
    leaks, heads = internal_names(text, brief)
    # AND THE SOURCE, because a link's target is not text: `\href{<tailnet>}
    # {Open}` prints "Open" and puts the address in the PDF where any click
    # finds it. Comments are not the deck.
    try:
        with open(os.path.join(d, STEM + ".tex"), "r", encoding="utf-8",
                  errors="replace") as fh:
            src = re.sub(r"(?<!\\)%.*", "", fh.read())
    except OSError:
        src = ""
    leaks = sorted(set(leaks) | set(internal_names(src, {})[0]))
    for u in leaks:
        problems.append("the deck prints %s, an address nobody at the meeting "
                        "can open" % u)
    found = check_sources(base, d, brief)
    found["internal"] = [{"heading": h} for h in heads]
    found["problems"] = problems
    found["pages"] = pages
    found["checked_at"] = time.time()
    try:
        with open(os.path.join(d, PROVENANCE), "w", encoding="utf-8") as fh:
            json.dump(found, fh, indent=2)
    except OSError:
        pass
    rec["pages"] = pages
    rec["problems"] = problems
    rec["unsupported"] = (len(found["numbers"]) + len(found["figures"])
                          + len(found["internal"]))
    rec["built"] = True
    rec["state"] = "did not land" if problems else "ready"
    rec["why"] = ("It was built but cannot be offered: %s. Ask for it again."
                  % "; ".join(problems[:4])) if problems else ""
    rec["at"] = time.time()
    _end_writeup(base, rec, "failed" if problems else "done")
    return rec


def _end_writeup(base, rec, how):
    """Freeze the host's writeup record: the meeting deck is not in the
    library, so the library's stamps would never say it landed."""
    from . import writeups
    host_root = _host_root(base, rec)
    wid = rec.get("wid") or ""
    if not host_root or not wid:
        return
    w = writeups.read(host_root, wid)
    if w and not w.get("ended"):
        w["ended"], w["ended_at"] = how, time.time()
        writeups.write(host_root, w)
        writeups.forget()


def _host_root(base, rec):
    for ws in atlas.workspaces(base):
        if ws["id"] == rec.get("host"):
            return ws["root"]
    return ""


def status(base):
    """The record, judged: `being written` until the deck is built and read
    back, then `ready` or `did not land`. Cheap while nothing has moved."""
    from . import sittings, writeups                    # local: a cycle
    with _LOCK:
        rec = _read_record(base)
        if not rec or rec.get("state") != "being written":
            return rec
        d = _deck_of(base, rec)
        pdf = os.path.join(d, STEM + ".pdf") if d else ""
        asked = float(rec.get("asked_at") or 0)
        now = time.time()
        host_root = _host_root(base, rec) or (os.path.dirname(os.path.dirname(d))
                                        if d else "")
        wid = rec.get("wid") or ""
        newest = sittings._newest_in(d) if d else 0
        try:
            built = bool(pdf) and os.path.getmtime(pdf) >= asked - 1
        except OSError:
            built = False
        over = sittings._turn_over(host_root, wid) if host_root and wid else False
        # READ BACK ONCE, WHEN THE TURN IS DONE WITH IT. A writer builds, looks,
        # fixes and builds again, and the judgement is frozen: a first build
        # read back mid-turn is a page map of a deck that no longer exists, or a
        # refusal of one the writer was about to fix. The ceiling is for a turn
        # whose end cannot be read.
        if built and ((over and now - newest >= SETTLE)
                      or now - asked >= CEILING):
            rec = finalize(base, rec)
            _write_record(base, rec)
            return rec
        gone = (writeups.state(host_root, wid) == "failed" if host_root and wid
                else False) or now - asked >= CEILING
        if not gone and over and now - newest >= QUIET:
            gone = True
        if gone and not built:
            tex = bool(d) and os.path.isfile(os.path.join(d, STEM + ".tex"))
            rec["state"] = "did not land"
            rec["why"] = ("The deck was written but did not build. Ask for it "
                          "again." if tex else
                          "The assistant ended without writing the deck. Ask "
                          "for it again.")
            rec["at"] = now
            _end_writeup(base, rec, "failed")
            _write_record(base, rec)
        return rec


# ---------------------------------------------------------------------------
# the ink
# ---------------------------------------------------------------------------
def ink_keys(repo):
    """Every annotation key on this deck that has strokes under it."""
    from .lesson import notes as lesson_notes          # local: avoids a cycle
    from .server.routes import writing                 # local: avoids a cycle

    out = {}
    for key, strokes in lesson_notes.load_notes(repo).items():
        found = writing.ann_doc_page(key)
        if found and strokes and found[0] == ANN_IDENT:
            out[key] = strokes
    return out


def drawn_on(repo, pdf, pages):
    """`(build, rebuilt)` for the deck on the glass, the library's way.

    `pages` is `paper.pages_of`'s answer with `ink` already in it. `build` is
    `{digest, at, pages}`, which `/meeting` hands back with every save so the
    record says what the marks were drawn on (`writing.clean_build`).
    `rebuilt` is `library.drawn_on`'s flag, or None. A new deck clears the old
    one's ink, so the flag only ever means a deck recompiled in place. No copy
    is offered off it: ink here is direction, not a document to keep.
    """
    from .course import library                        # local: avoids a cycle

    try:
        at = os.path.getmtime(pdf)
    except OSError:
        at = 0
    build = {"digest": pages.get("digest") or "", "at": at,
             "pages": pages.get("n") or 0}
    flag = library.drawn_on(repo, None, build["digest"],
                            pages.get("ink") or {})["rebuilt"]
    return build, flag


def deck_id(base):
    """Which deck this is, as a string, or "".

    `asked_at` is set once per `prepare` and kept through a recompile in place,
    so it names one deck across its builds. A save of deck ink names the deck
    it was drawn on, and a save naming another is refused
    (`/annotate/save`): a page left open over a new deck would otherwise write
    last meeting's rings onto this one's slides.
    """
    rec = _read_record(base) or {}
    at = rec.get("asked_at")
    return repr(float(at)) if isinstance(at, (int, float)) else ""


def clear_ink(repo):
    """Throw away every mark on the deck. Returns how many keys went.

    Ink on a slide is a direction somebody suggested in a meeting; it was
    consumed the moment it was sent, and the next deck has a different project
    on page 4.
    """
    from .server.routes import writing                 # local: avoids a cycle

    gone = 0
    for key in ink_keys(repo):
        for ext in (".json", ".png"):
            try:
                os.remove(writing.ann_path(repo, key, ext))
            except OSError:
                continue
            if ext == ".json":
                gone += 1
    return gone
