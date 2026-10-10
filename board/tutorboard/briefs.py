"""The meeting deck: a brief of a period, and the artifact a turn writes over it.

    resolve_since(spec)              a period, snapped to a local midnight
    classify(commit, rel, ids)       work | save | other, for one subject
    blocks_for(base, want, since)    what each subject did in the period
    write_brief(base, deck, blocks)  _brief.md, _brief.json and the figures
    replace(base, blocks, ...)       the deck asked for again: the old one to the
                                     trash with its ink, a fresh doc.json, a brief
    judge(base)                      being written | ready | did not land, from
                                     `artifacts.status`
    check_sources, internal_names    what on a built deck no source supports

One deck, the artifact `projects/Meetings/docs/meeting/` with source
`meeting.tex`, replaced on each ask (git keeps every version). A brief holds,
per subject: the period's commits that are its own work, how its TUTOR.md
changed, the sessions that ended, and the period's figures plus a catalog.

The constraint: Meetings is `"phi": true`, so the pre-commit audit reads the
source before it can leave; brief, figures, PDF and sidecar are ignored.
"""

import json
import os
import re
import shutil
import struct
import subprocess
import time

from . import artifacts, fenced, gitops, paths, sessions, subjects
from .course import library

# The deck: one artifact, in one subject, replaced each time.
MEETINGS = "projects/Meetings"
SLUG = "meeting"
STEM = "meeting"
TITLE = "Meeting deck"

# What sits beside the deck. `_` keeps the brief out of the library's walk.
BRIEF_MD = library.DECK_BRIEF
BRIEF_JSON = "_brief.json"
PROVENANCE = "_provenance.json"
FIGURES = "figures"

# How much of each source the brief carries.
BODY_CHARS = 6000
DIFF_CHARS = 14000
MOST_COMMITS = 40
MOST_SESSIONS = 30
MOST_TABLES = 40
MOST_CATALOG = 300
MOST_FIGURES = 24
PER_SUBJECT_FIGURES = 12
SUBJECT_CHARS = 100

# What the sources are read to, at most, when the numbers are checked.
SOURCE_BYTES = 400000
CORPUS_BYTES = 8000000

# The tutor's file, whose diff over the period is the subject's story.
STORY = "TUTOR.md"

# A save, not a piece of work: what follows a subject's prefix decides.
SAVES = (gitops.SAVE, "lesson transcript", "stopping point")
SAVE_RE = re.compile(r"^(?:[\w.+-]+\s+)?hand-?off\b")

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday",
            "saturday", "sunday")
SESSION_WHEN = "%Y-%m-%d %H:%M:%S"

# An address a mentor cannot open, or a hostname nobody outside may see.
INTERNAL_URL = re.compile(
    r"(?:[a-z0-9-]+\.)+ts\.net|\b(?:localhost|127\.0\.0\.1)\b|#/w/", re.I)

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


# ---------------------------------------------------------------------------
# where
# ---------------------------------------------------------------------------
def meetings_root(base=None):
    """The Meetings subject's directory, or "" where this tree has none."""
    found = subjects.find(MEETINGS, base)
    return found["root"] if found and found["id"] == MEETINGS else ""


def deck_dir(base=None):
    """`<Meetings>/docs/meeting`, or "" without Meetings."""
    root = meetings_root(base)
    return os.path.join(root, artifacts.DOCS, SLUG) if root else ""


def deck_rel():
    """The deck's directory relative to the Meetings subject."""
    return "%s/%s" % (artifacts.DOCS, SLUG)


# ---------------------------------------------------------------------------
# when
# ---------------------------------------------------------------------------
def snap(t):
    """Local midnight at or before `t`: a week asked for at 20:18 keeps the
    commit made at 20:13 seven days earlier."""
    lt = time.localtime(t)
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))


def asked_at(base=None):
    """When the deck was last asked for, as epoch seconds, or 0."""
    d = deck_dir(base)
    rec = artifacts.read(d) if d else None
    return artifacts._when((rec or {}).get("asked_at")) if rec else 0


def resolve_since(spec, base=None, now=None):
    """`(epoch, what to call it)` -- or `(None, why not)`. Always a midnight."""
    now = time.time() if now is None else now
    spec = str(spec or "").strip().lower()
    if not spec:
        return None, "say a date (2026-09-01), a span (7d, 2w), a weekday, or `last`"
    if spec == "last":
        when = asked_at(base)
        if not when:
            return None, ("there is no earlier deck to measure from. Give a date "
                          "or a span for the first one.")
        return snap(when), "the last deck"
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", spec)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # Checked before `mktime`, which normalises rather than refusing.
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
        days = {"d": 1, "w": 7, "m": 30}[m.group(2)] * int(m.group(1))
        if not 1 <= days <= 3650:
            return None, "%s is not a period anybody holds a meeting about" % spec
        said = ("yesterday" if days == 1 else "the last week" if days == 7
                else "the last %d days" % days)
        return snap(now - days * 86400), said
    if spec.startswith("last-"):
        spec = spec[5:]
    if spec in WEEKDAYS:
        # The most recent one; today does not count.
        back = (time.localtime(now).tm_wday - WEEKDAYS.index(spec)) % 7 or 7
        return snap(now) - back * 86400, "since " + spec.capitalize()
    return None, ("%r is not a date (2026-09-01), a span (7d, 2w), a weekday, "
                  "or `last`" % spec)


def _day(t):
    lt = time.localtime(t)
    return "%s %d %s %d" % (time.strftime("%A", lt), lt.tm_mday,
                            time.strftime("%B", lt), lt.tm_year)


def period_text(since_ts, until_ts=None):
    """The exact period, as the title slide says it."""
    return "%s to %s" % (_day(since_ts), _day(time.time() if until_ts is None
                                               else until_ts))


def _stamp(t):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(t))


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------
def _git(top, args, timeout=60):
    try:
        p = subprocess.run(["git"] + args, cwd=top, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return p.stdout.decode("utf-8", "replace") if p.returncode == 0 else ""


def _clip(text, limit):
    """Cut at a word, and say that it was cut."""
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return (cut or text[:limit]).rstrip(" ,;:-") + "..."


def _until(until_ts):
    return [] if until_ts is None else ["--until=@%d" % int(until_ts)]


def _log(top, rel, since_ts, until_ts=None):
    """Every commit in the period that touched `rel`, newest first, with every
    file it changed: whether its work is here depends on what else it touched."""
    raw = _git(top, ["log", "--since=@%d" % int(since_ts)] + _until(until_ts)
               + ["--no-merges", "--full-diff", "--name-only",
                  "--pretty=format:%x01%H%x00%at%x00%s", "--", rel])
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


# ---------------------------------------------------------------------------
# the classifier
# ---------------------------------------------------------------------------
def owner_of(subject, ids):
    """The subject id a commit subject's prefix names, or "": the slug
    (`TRD-EHR: `) or the full id (`projects/TRD-EHR: `)."""
    said = str(subject or "")
    if ":" not in said:
        return ""
    head = said.split(":", 1)[0].strip()
    if head in ids:
        return head
    named = [i for i in ids if i.split("/")[-1] == head]
    return named[0] if len(named) == 1 else ""


def is_save(subject, ids=()):
    """A save rather than a piece of work, whoever's prefix is on it."""
    said = str(subject or "").strip()
    if owner_of(said, ids):
        said = said.split(":", 1)[1].strip()
    said = said.lower().rstrip(".")
    return said in SAVES or bool(SAVE_RE.match(said))


def classify(commit, rel, ids):
    """`work`, `save` or `other`: what `commit` is to the subject at `rel`.
    Another subject's prefix, or a TUTOR.md-only touch alongside work
    elsewhere, is `other`."""
    owner = owner_of(commit["subject"], ids)
    if owner and owner != rel:
        return "other"
    if is_save(commit["subject"], ids):
        return "save"
    prefix = rel.strip("/") + "/"
    inside = [f for f in commit["files"] if f.startswith(prefix)]
    outside = [f for f in commit["files"] if not f.startswith(prefix)]
    if inside and outside and all(f == prefix + STORY for f in inside):
        return "other"
    return "work"


# ---------------------------------------------------------------------------
# one subject
# ---------------------------------------------------------------------------
def tutor_diff(top, rel, since_ts, until_ts=None):
    """How the subject's TUTOR.md changed over the period, or "". Against the
    working tree while the period is open; an untracked one newer than the
    period's start is carried whole."""
    one = "%s/%s" % (rel, STORY)
    start = _git(top, ["rev-list", "-1", "--before=@%d" % int(since_ts),
                       "HEAD"]).strip() or EMPTY_TREE
    end = []
    if until_ts is not None:
        stop = _git(top, ["rev-list", "-1", "--before=@%d" % int(until_ts),
                          "HEAD"]).strip()
        end = [stop] if stop else []
    diff = _git(top, ["diff", "--no-color", start] + end + ["--", one])
    if not diff.strip() and not end:
        path = os.path.join(top, one)
        if os.path.isfile(path) and not _git(top, ["ls-files", "--", one]).strip():
            try:
                if os.path.getmtime(path) >= since_ts:
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        diff = "(new, not yet committed)\n" + fh.read()
            except OSError:
                diff = ""
    return _clip(diff, DIFF_CHARS) if diff.strip() else ""


def _session_at(said):
    try:
        return time.mktime(time.strptime(str(said or "")[:19], SESSION_WHEN))
    except (ValueError, OverflowError):
        return 0


def _count_cards(folder):
    from .lesson import cards                          # local: a heavy import
    try:
        return len([n for n in os.listdir(folder) if cards.CARD_RE.match(n)])
    except OSError:
        return 0


def ended_sessions(base, subject_id, since_ts, until_ts=None):
    """The sessions bound to `subject_id` that ended in the period, oldest
    first: `{id, title, opened, ended, cards, cards_dir, turns}`."""
    stop = time.time() if until_ts is None else until_ts
    out = []
    for rec in sessions.all(base):
        if rec.get("subject") != subject_id or not rec.get("ended"):
            continue
        end = _session_at(rec["ended"])
        if not end or not since_ts <= end <= stop + 1:
            continue
        where = sessions.path(rec.get("id"), base)
        if not where:
            continue
        cards = os.path.join(where, "cards")
        out.append({"id": rec["id"], "title": str(rec.get("title") or "").strip(),
                    "opened": rec.get("opened") or "", "ended": rec["ended"],
                    "end": end, "cards": _count_cards(cards), "cards_dir": cards,
                    "turns": os.path.join(where, "turns.jsonl")})
    out.sort(key=lambda s: s["end"])
    return out[-MOST_SESSIONS:]


def _body(top, sha):
    return _clip(_git(top, ["show", "-s", "--format=%B", sha]), BODY_CHARS)


def _memo_lines(root):
    """TUTOR.md's bullet lines: the tutor's own headings, which a slide must
    not copy as typed (`internal_names`)."""
    try:
        with open(os.path.join(root, STORY), "r", encoding="utf-8",
                  errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    out = []
    for line in text.splitlines():
        m = re.match(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$", line)
        if m and len(m.group(1).strip()) >= 8:
            out.append(m.group(1).strip())
    return out


def gather(base, subject, since_ts, until_ts=None, ids=None):
    """What the period holds for one subject record (`subjects.all`), or None
    where nothing moved."""
    top = os.path.realpath(base)
    rel = os.path.relpath(os.path.realpath(subject["root"]), top).replace(os.sep, "/")
    if ids is None:
        ids = set(s["id"] for s in subjects.all(base))
    work = []
    for c in _log(top, rel, since_ts, until_ts):
        if classify(c, rel, ids) != "work" or len(work) >= MOST_COMMITS:
            continue
        c["body"] = _body(top, c["full"])
        work.append(c)
    story = tutor_diff(top, rel, since_ts, until_ts)
    held = ended_sessions(base, subject["id"], since_ts, until_ts)
    if not (work or story or held):
        return None
    return {"id": subject["id"], "name": subject["name"], "root": subject["root"],
            "rel": rel, "commits": work, "story": story, "sessions": held,
            "steps": _memo_lines(subject["root"]),
            "fenced": list(fenced.holds(subject["root"]))}


def blocks_for(base, want, since_ts, until_ts=None):
    """`(blocks, every, refusal)`. `want` is subject ids or slugs, matched
    against `subjects.all`; empty is every subject. Meetings is never one."""
    every = [s for s in subjects.all(base) if s["id"] != MEETINGS]
    ids = set(s["id"] for s in every)
    if want:
        want = set(str(w).strip().strip("/") for w in want)
        every = [s for s in every if s["id"] in want or s["slug"] in want]
        if not every:
            return [], [], "none of those are subjects in this repository"
    blocks = []
    for s in every:
        try:
            one = gather(base, s, since_ts, until_ts, ids=ids)
        except Exception:                                    # noqa: BLE001
            one = None
        if one:
            blocks.append(one)
    return blocks, every, ""


# ---------------------------------------------------------------------------
# figures: the snapshot, and finding one by a word
# ---------------------------------------------------------------------------
def ws_slug(subject_id):
    """A subject id as the front of a filename: result ids are unique per
    subject only."""
    return re.sub(r"[^a-z0-9]+", "-", str(subject_id or "").lower()).strip("-") or "ws"


def png_size(path):
    """`(width, height)` off a PNG's IHDR, or None."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(24)
    except OSError:
        return None
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def snapshot(root_from, rid, subject_id, deck):
    """Copy one figure beside a deck, through `library.find_result`. Its path relative
    to the deck, or "" where `root_from` offers no such id."""
    target, _ = library.find_result(root_from, rid)
    if not target:
        return ""
    ext = os.path.splitext(target)[1].lower() or ".png"
    name = "%s--%s%s" % (ws_slug(subject_id), rid, ext)
    dest = os.path.join(deck, FIGURES, name)
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(target, dest)
    except OSError:
        return ""
    return FIGURES + "/" + name


def figure_named(root, wanted):
    """The id of the one figure `wanted` names in the subject at `root`, or a
    list of the ids it could mean (empty where it names none). An exact id
    first; otherwise every word of `wanted` must begin a word of the figure's
    file name, pretty name or folder."""
    want = str(wanted or "").strip().lower()
    try:
        idx = library.result_index(root)
    except Exception:                                        # noqa: BLE001
        return []
    figs = dict((k, v) for k, v in idx.items() if v.get("kind") == "figure")
    if want in figs:
        return want
    words = [w for w in re.split(r"[^a-z0-9]+", want) if w]
    if not words:
        return []
    hits = []
    for rid, rec in figs.items():
        hay = " ".join(str(rec.get(k) or "") for k in ("file", "name", "where"))
        have = [t for t in re.split(r"[^a-z0-9]+", hay.lower()) if t]
        if all(any(t.startswith(w) for t in have) for w in words):
            hits.append((-(rec.get("at") or 0), rid))
    hits.sort()
    if len(hits) == 1:
        return hits[0][1]
    return [rid for _, rid in hits[:8]]


def read_brief(deck):
    """`_brief.json` beside a deck, or None."""
    try:
        with open(os.path.join(deck, BRIEF_JSON), "r", encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return None
    return got if isinstance(got, dict) else None


def drawn_from(deck):
    """The subjects a deck's brief was made from, which `board deckfig` may
    copy from (older briefs: `workspaces`, or sitting prefixes)."""
    rec = read_brief(deck) or {}
    out = []
    for w in (rec.get("subjects") or []) + (rec.get("workspaces") or []):
        if isinstance(w, str) and w not in out:
            out.append(w)
    for i in rec.get("items") or []:
        ws = str((i or {}).get("sitting") or "").split("@", 1)[0]
        if ws and ws not in out:
            out.append(ws)
    return out


def _stems(text):
    return set(w[:6] for w in re.findall(r"[a-z][a-z0-9]+", str(text).lower())
               if len(w) >= 3)


def _figures(blocks, since_ts, until_ts):
    """`(chosen, catalog, catalog_left)`: the period's figures, newest first and
    at most `PER_SUBJECT_FIGURES` a subject; every other figure of those
    subjects in the catalog, the ones the commits mention first."""
    stop = time.time() if until_ts is None else until_ts
    chosen, rest = [], []
    for b in blocks:
        try:
            idx = library.result_index(b["root"])
        except Exception:                                    # noqa: BLE001
            continue
        figs = sorted((r for r in idx.values() if r.get("kind") == "figure"),
                      key=lambda r: -(r.get("at") or 0))
        n = 0
        for r in figs:
            one = {"ws": b["id"], "root": b["root"], "rec": r}
            if since_ts <= (r.get("at") or 0) <= stop + 1 and n < PER_SUBJECT_FIGURES:
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
        return len(said & _stems(" ".join(str(f["rec"].get(k) or "")
                                          for k in ("file", "name", "where"))))

    rest.sort(key=lambda f: (-overlap(f), -(f["rec"].get("at") or 0)))
    return chosen, rest[:MOST_CATALOG], max(0, len(rest) - MOST_CATALOG)


def _tables(blocks, since_ts, until_ts):
    stop = time.time() if until_ts is None else until_ts
    out = []
    for b in blocks:
        try:
            idx = library.result_index(b["root"])
        except Exception:                                    # noqa: BLE001
            continue
        for r in sorted(idx.values(), key=lambda r: -(r.get("at") or 0)):
            if r.get("kind") != "table" or fenced.refused(r.get("rel") or ""):
                continue
            if since_ts <= (r.get("at") or 0) <= stop + 1:
                out.append({"ws": b["id"], "path": os.path.join(b["root"], r["rel"]),
                            "iso": r.get("iso") or ""})
    return out[:MOST_TABLES]


def _allowed(base, path):
    rel = os.path.relpath(path, base)
    return "" if fenced.refused(rel) or fenced.refused(path) else path


def _cell(text):
    return str(text or "").replace("|", "/").replace("\n", " ")


def _quote(text):
    return "  > " + str(text).replace("\n", "\n  > ")


def _fence_block(text):
    return ["```diff", str(text).rstrip("\n").replace("```", "'''"), "```"]


# ---------------------------------------------------------------------------
# the brief
# ---------------------------------------------------------------------------
def write_brief(base, deck, blocks, since_ts, until_ts=None, human="", dry=False):
    """Write `_brief.md`, `_brief.json` and the figures into `deck`, and return
    the record. `dry` writes nothing and returns the text in `markdown`."""
    period = period_text(since_ts, until_ts)
    names = dict((b["id"], b["name"]) for b in blocks)
    here = os.path.relpath(deck, base).replace(os.sep, "/")
    if not dry:
        os.makedirs(deck, exist_ok=True)
    chosen, catalog, catalog_left = _figures(blocks, since_ts, until_ts)
    made = []
    for f in chosen:
        rid = f["rec"]["id"]
        if dry:
            ext = os.path.splitext(f["rec"].get("rel") or "")[1].lower() or ".png"
            rel = "%s/%s--%s%s" % (FIGURES, ws_slug(f["ws"]), rid, ext)
        else:
            rel = snapshot(f["root"], rid, f["ws"], deck)
        if not rel:
            continue
        size = None if dry else png_size(os.path.join(deck, rel))
        made.append({"file": rel, "ws": f["ws"], "id": rid,
                     "where": f["rec"].get("where") or "",
                     "name": f["rec"].get("name") or "",
                     "date": f["rec"].get("iso") or "",
                     "size": ("%d x %d" % size) if size else ""})
    tables = _tables(blocks, since_ts, until_ts)

    sources, steps, fences = [], [], []
    out = ["# The brief for the meeting deck `%s/%s.tex`" % (here, STEM), "",
           "Written by the board on %s. You write `%s.tex` beside this file and "
           "build it; nothing else here is yours to edit." % (_stamp(time.time()),
                                                              STEM), "",
           "## Who it is for", "",
           "The MENTORS who supervise these projects, at their next meeting. They "
           "know the field. They saw none of the work, the sessions or the board, "
           "and none of its private names mean anything to them.", "",
           "## The period", "",
           "%s (%s). The title slide says exactly this."
           % (period, human or "the period asked for"), "",
           "## The subjects", ""]
    out += ["- **%s** (`%s`)" % (b["name"], b["id"]) for b in blocks] + [""]

    for b in blocks:
        out += ["## %s (`%s`)" % (b["name"], b["id"]), ""]
        memo = os.path.join(b["root"], STORY)
        if os.path.isfile(memo) and _allowed(base, memo):
            out += ["To read more: `%s`." % os.path.relpath(memo, base), ""]
            sources.append(memo)
        out += ["### What landed: %d commit%s of its own work"
                % (len(b["commits"]), "" if len(b["commits"]) == 1 else "s"), ""]
        if not b["commits"]:
            out += ["None in the period.", ""]
        for c in b["commits"]:
            head = _clip(c["subject"], 160)
            out.append("- `%s` (%s) **%s**" % (c["sha"], _stamp(c["at"]), head))
            body = (c.get("body") or "").strip()
            if body and body != head.strip():
                out.append(_quote(body))
        out.append("")
        if b["story"]:
            out += ["### How %s changed over the period" % STORY, ""]
            out += _fence_block(b["story"]) + [""]
        if b["sessions"]:
            out += ["### Sessions that ended in the period", ""]
            for s in b["sessions"]:
                where = []
                for what, p in (("cards", s["cards_dir"]), ("transcript", s["turns"])):
                    if os.path.exists(p) and _allowed(base, p):
                        where.append("%s `%s`" % (what, p))
                        if what == "cards":
                            sources.append(p)
                out.append("- %s, %s to %s: %d card%s%s" % (
                    s["title"] or "untitled", s["opened"][:16], s["ended"][:16],
                    s["cards"], "" if s["cards"] == 1 else "s",
                    (". " + "; ".join(where)) if where else ""))
            out.append("")
        steps += b.get("steps") or []
        for name in b["fenced"]:
            line = "- %s holds `%s/`: never open anything under it." % (b["id"], name)
            if line not in fences:
                fences.append(line)

    if tables:
        out += ["## Tables written in the period", "",
                "Open one for a number the commits do not give.", ""]
        for t in tables:
            out.append("- %s: `%s` (%s)" % (t["ws"], os.path.relpath(t["path"], base),
                                            t["iso"]))
            sources.append(t["path"])
        out.append("")
    if fences:
        out += ["## Fences", ""] + fences + [""]

    out += ["## Figures already copied beside the deck", ""]
    if made:
        out += ["| file | subject | where | name | date | pixels |",
                "|---|---|---|---|---|---|"]
        out += ["| `%s` | %s | %s | %s | %s | %s |"
                % (f["file"], f["ws"], _cell(f["where"]), _cell(f["name"]),
                   f["date"], f["size"]) for f in made]
    else:
        out.append("None: nothing in the period wrote a figure this board can show.")
    out += ["", "OPEN A FIGURE BEFORE YOU USE IT, and say on the slide what it "
            "shows.", "", "## Other figures you may pull", "",
            "`board deckfig %s <subject> <result id>` copies one into `figures/` "
            "and prints the path to put in `\\includegraphics`." % here, ""]
    if catalog:
        out += ["| subject | result id | where | name | date |", "|---|---|---|---|---|"]
        out += ["| %s | `%s` | %s | %s | %s |"
                % (f["ws"], f["rec"]["id"], _cell(f["rec"].get("where")),
                   _cell(f["rec"].get("name")), f["rec"].get("iso") or "")
                for f in catalog]
    else:
        out.append("There are none.")
    if catalog_left:
        out += ["", "%d more exist and are not listed; give `board deckfig` a word "
                "from a file name instead of an id." % catalog_left]
    out += ["", "## How to write it", "",
            "- `\\documentclass[aspectratio=169]{beamer}`.",
            "- A title slide with the period above; one summary slide, each "
            "subject in one line with its headline number; per subject as many "
            "slides as it needs; one closing slide of asks for the mentors.",
            "- ONE PAGE PER FRAME: no `allowframebreaks`, no `\\pause`, no overlays.",
            "- No internal names on a slide: no commit hashes, no lines copied "
            "from TUTOR.md as typed, no links to the board.",
            "- Every number on a slide comes from this brief or a file it names. "
            "After the build the board checks each one and lists any it cannot "
            "find beside the deck.",
            "- A figure is `\\includegraphics[width=\\linewidth,height=0.72"
            "\\textheight,keepaspectratio]{figures/<file>}`.",
            "- Build it with `board build %s/%s.tex`. A LaTeX error is yours to "
            "fix before the turn ends." % (here, STEM), ""]
    markdown = "\n".join(out)

    rec = {"kind": "meeting", "at": time.time(), "since": since_ts,
           "until": until_ts, "period": period, "human": human,
           "subjects": [b["id"] for b in blocks], "names": names,
           "figures": [f["file"] for f in made],
           "sources": sorted(set(s for s in sources if _allowed(base, s))),
           "steps": sorted(set(steps))}
    if dry:
        rec["markdown"] = markdown
        return rec
    with open(os.path.join(deck, BRIEF_MD), "w", encoding="utf-8") as fh:
        fh.write(markdown)
    with open(os.path.join(deck, BRIEF_JSON), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2)
    return rec


# ---------------------------------------------------------------------------
# asking: the deck replaced
# ---------------------------------------------------------------------------
def ink_dirs(base, repo=None):
    """Where ink on the deck can be: Meetings' `.ink/` (the library's), the
    Atlas root's (ink a sessionless save made without `?subject=`), and
    `repo`'s own annotations."""
    out = []
    root = meetings_root(base)
    if root:
        out.append(os.path.join(root, sessions.INK))
    out.append(os.path.join(base, sessions.INK))
    if repo is not None and getattr(repo, "notes", None):
        out.append(repo.notes)
    seen = []
    for d in out:
        if os.path.realpath(d) not in [os.path.realpath(x) for x in seen]:
            seen.append(d)
    return seen


def replace(base, blocks, since_ts, human="", session=None, until_ts=None,
            ink=None, now=None):
    """The deck asked for again: the old directory and its ink go to the trash,
    a fresh doc.json is written listing `session`, and the brief beside it.
    Returns `{doc_dir, brief, record}`; `doc_dir` is relative to Meetings.
    ValueError without Meetings."""
    root = meetings_root(base)
    if not root:
        raise ValueError("%s is missing; `board bind %s --create --phi yes` makes it"
                         % (MEETINGS, MEETINGS))
    now = time.time() if now is None else now
    d = os.path.join(root, artifacts.DOCS, SLUG)
    trash = ""
    if os.path.lexists(d):
        trash = artifacts._trash(now, "%s-%s" % (ws_slug(MEETINGS), SLUG))
        shutil.move(d, os.path.join(trash, SLUG))
    for ink_dir in (ink if ink is not None else ink_dirs(base)):
        for p in artifacts.ink_files(ink_dir, [SLUG]):
            if not trash:
                trash = artifacts._trash(now, "%s-%s" % (ws_slug(MEETINGS), SLUG))
            keep = os.path.join(trash, ".ink")
            os.makedirs(keep, exist_ok=True)
            shutil.move(p, os.path.join(keep, os.path.basename(p)))
    art = artifacts.create(root, SLUG, session=session, source=STEM + ".tex",
                           now=now)
    if art["id"] != SLUG:
        raise ValueError("%s/%s could not be claimed" % (artifacts.DOCS, SLUG))
    doc = artifacts.read(art["dir"])
    doc["title"] = "%s, %s" % (TITLE, period_text(since_ts, until_ts))
    artifacts._write_json(os.path.join(art["dir"], artifacts.DOC_JSON), doc)
    brief = write_brief(base, art["dir"], blocks, since_ts, until_ts, human)
    return {"doc_dir": art["rel"], "brief": brief, "record": doc, "trash": trash}


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
        p = subprocess.run(["pdftotext", "-layout", pdf, "-"], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return p.stdout.decode("utf-8", "replace") if p.returncode == 0 else ""


# NUMBERS. A decimal, a grouped integer (`42{,}579`, `42,579`), or a plain one.
NUMBER_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
                       r"(?![\w])")
UNIT_RE = re.compile(r"\d*\.?\d+(?:pt|em|ex|cm|mm|in|bp|sp|px)\b"
                     r"|\d*\.?\d+\s*\\(?:linewidth|textwidth|textheight|paperwidth"
                     r"|paperheight|columnwidth|baselineskip)")
# Commands whose every argument is layout or an address, never a claim.
DROP_ALL = re.compile(
    r"\\(?:includegraphics|label|ref|eqref|cite\w*|url|"
    r"vspace\*?|hspace\*?|setlength|addtolength|definecolor|usetheme|"
    r"usecolortheme|usefonttheme|setbeamer\w+|rule|resizebox|"
    r"begin\{column\}|column)\s*(?:\[[^\]]*\]\s*)*(?:\{[^{}]*\}\s*)*")
# And the ones whose FIRST argument is: a colour, a scale, a link's target.
DROP_FIRST = re.compile(
    r"\\(?:color|textcolor|colorbox|scalebox|href)\s*(?:\[[^\]]*\]\s*)*\{[^{}]*\}")


def _numbers_of(text):
    return [m.replace(",", "") for m in NUMBER_RE.findall(text)]


def _clean_tex(tex):
    """The deck's body with what is not a claim taken out: the preamble,
    comments, layout arguments, dimensions and colour mixes."""
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
    """Every rounding of every number in the sources, so a slide's `60.2 %` is
    found for a source's `0.602`."""
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


def _corpus(base, brief, deck):
    """The brief and every source it names, read to a limit."""
    parts = []
    try:
        with open(os.path.join(deck, BRIEF_MD), "r", encoding="utf-8",
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
    total = 0
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


def _figures_used(deck, tex):
    """The image files the build read, relative to the deck: the `.fls` where
    there is one, else the log, else the `\\includegraphics` in the source."""
    found = []
    exts = (".png", ".jpg", ".jpeg", ".pdf", ".eps", ".svg")
    try:
        with open(os.path.join(deck, STEM + ".fls"), "r", encoding="utf-8",
                  errors="replace") as fh:
            for ln in fh:
                if ln.startswith("INPUT "):
                    p = ln[6:].strip()
                    if p.lower().endswith(exts) and not p.endswith(STEM + ".pdf"):
                        found.append(p)
    except OSError:
        pass
    if not found:
        try:
            with open(os.path.join(deck, STEM + ".log"), "r", encoding="utf-8",
                      errors="replace") as fh:
                found = re.findall(r"<([^<>\s,]+\.(?:png|jpe?g|pdf|eps))", fh.read(),
                                   re.I)
        except OSError:
            pass
    if not found:
        found = re.findall(r"\\includegraphics\s*(?:\[[^\]]*\])?\{([^{}]+)\}", tex)
    out = []
    for p in found:
        full = os.path.normpath(p if os.path.isabs(p) else os.path.join(deck, p))
        rel = os.path.relpath(full, deck).replace(os.sep, "/")
        if rel not in out:
            out.append(rel)
    return out


def check_sources(base, deck, brief):
    """`{numbers, figures}` -- everything on the deck no source supports. A
    number counts when some number in a source rounds to it (directly, or as a
    percentage); a figure when the board copied it from a subject the deck is
    about."""
    try:
        with open(os.path.join(deck, STEM + ".tex"), "r", encoding="utf-8",
                  errors="replace") as fh:
            tex = fh.read()
    except OSError:
        tex = ""
    body = _clean_tex(tex)
    frames = _frame_titles(body)
    have = _supported_values(_corpus(base, brief, deck))
    numbers, seen = [], set()
    for m in NUMBER_RE.finditer(body):
        raw = m.group(1).replace(",", "")
        if "." not in raw and raw.isdigit() and int(raw) <= 10:
            continue                          # a count or a label, not a claim
        d = len(raw.split(".", 1)[1]) if "." in raw else 0
        if ("%." + str(d) + "f") % float(raw) in have or raw in have:
            continue
        n, title = _where(frames, m.start())
        if (raw, n) in seen:
            continue
        seen.add((raw, n))
        ctx = re.sub(r"\\[a-zA-Z]+\*?|[{}$\\]", " ",
                     body[max(0, m.start() - 60):m.end() + 40])
        numbers.append({"value": m.group(1), "frame": n, "title": title,
                        "context": _clip(re.sub(r"\s+", " ", ctx), 140)})
    copied = set(brief.get("figures") or [])
    offered = {}
    for w in drawn_from_record(brief):
        found = subjects.find(w, base)
        try:
            offered[ws_slug(w)] = set(library.result_index(found["root"])) if found else set()
        except Exception:                                    # noqa: BLE001
            offered[ws_slug(w)] = set()
    figures = []
    for rel in _figures_used(deck, tex):
        if rel in copied:
            continue
        m = re.match(r"^%s/([a-z0-9-]+)--([A-Za-z0-9_-]+)\.[A-Za-z]+$" % FIGURES, rel)
        if m and m.group(2).lower() in offered.get(m.group(1), set()) \
                and os.path.isfile(os.path.join(deck, rel)):
            continue
        figures.append({"file": rel})
    return {"numbers": numbers, "figures": figures}


def drawn_from_record(brief):
    return [w for w in (brief.get("subjects") or brief.get("workspaces") or [])
            if isinstance(w, str)]


def internal_names(text, brief):
    """`(leaks, headings)` in the deck's text: addresses nobody outside can
    open, and the tutor's own lines copied as typed in capitals."""
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


def finalize(base, deck):
    """Read a built deck back: what no source supports, and any address on
    it nobody outside can open. Writes `_provenance.json` and returns it."""
    brief = read_brief(deck) or {}
    pdf = os.path.join(deck, STEM + ".pdf")
    leaks, heads = internal_names(pdf_text(pdf), brief)
    # AND THE SOURCE, because a link's target is not text: `\href{<tailnet>}
    # {Open}` prints "Open" and puts the address where any click finds it.
    try:
        with open(os.path.join(deck, STEM + ".tex"), "r", encoding="utf-8",
                  errors="replace") as fh:
            src = re.sub(r"(?<!\\)%.*", "", fh.read())
    except OSError:
        src = ""
    leaks = sorted(set(leaks) | set(internal_names(src, {})[0]))
    found = check_sources(base, deck, brief)
    found["internal"] = [{"heading": h} for h in heads]
    found["problems"] = ["the deck prints %s, an address nobody at the meeting "
                         "can open" % u for u in leaks]
    found["pages"] = pdf_pages(pdf)
    found["pdf_at"] = artifacts._mtime(pdf)
    found["checked_at"] = time.time()
    try:
        with open(os.path.join(deck, PROVENANCE), "w", encoding="utf-8") as fh:
            json.dump(found, fh, indent=2)
    except OSError:
        pass
    return found


def provenance(base=None, deck=None):
    """`_provenance.json` beside the deck, or {}."""
    deck = deck or deck_dir(base)
    try:
        with open(os.path.join(deck, PROVENANCE), "r", encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return {}
    return got if isinstance(got, dict) else {}


def _checked(base, deck):
    """The sidecar for the PDF on disk now, read back once per build."""
    prov = provenance(deck=deck)
    if prov and prov.get("pdf_at") == artifacts._mtime(os.path.join(deck, STEM + ".pdf")):
        return prov
    return finalize(base, deck)


def judge(base=None, now=None):
    """`(state, why)`: `being written`, `ready` or `did not land` -- or
    `("", "")` with no deck. Landing is `artifacts.status`'s; a built deck
    that prints an address nobody outside can open does not land."""
    d = deck_dir(base)
    rec = artifacts.read(d) if d else None
    if not rec:
        return "", ""
    got = artifacts.status(d, now=now, base=base)
    if got == "writing":
        return "being written", ""
    if got == "failed":
        asked = artifacts._when(rec.get("asked_at"))
        tex = os.path.join(d, str(rec.get("source") or STEM + ".tex"))
        if artifacts._mtime(tex) > asked:
            return "did not land", ("The deck was written but did not build. Ask "
                                    "for it again.")
        return "did not land", ("The assistant ended without writing the deck. "
                                "Ask for it again.")
    problems = _checked(base, d).get("problems") or []
    if problems:
        return "did not land", ("It was built but cannot be offered: %s. Ask for "
                                "it again." % "; ".join(problems[:4]))
    return "ready", ""


def deck(base=None, now=None):
    """The deck as the front door and the Meetings library read it, or None.
    `state` is `judge`'s; `pages` and `check` are filled only when ready with
    its PDF; `deck` is `deck_id`."""
    d = deck_dir(base)
    rec = artifacts.read(d) if d else None
    if not rec:
        return None
    state, why = judge(base, now=now)
    brief = read_brief(d) or {}
    ready = state == "ready" and os.path.isfile(os.path.join(d, STEM + ".pdf"))
    prov = provenance(deck=d) if ready else {}
    names = brief.get("names") or {}
    return {"state": state, "why": why, "ready": ready,
            "deck": str(rec.get("asked_at") or ""),
            "since": brief.get("human") or "", "period": brief.get("period") or "",
            "subjects": [names.get(s) or s for s in brief.get("subjects") or []],
            "pages": int(prov.get("pages") or 0),
            "check": dict((k, prov.get(k) or [])
                          for k in ("numbers", "figures", "internal"))}


def deck_id(base=None):
    """Which deck this is, as a string, or "": its `asked_at`. A save of deck
    ink names the deck it was drawn on, and a save naming another is refused."""
    d = deck_dir(base)
    rec = artifacts.read(d) if d else None
    return str((rec or {}).get("asked_at") or "")
