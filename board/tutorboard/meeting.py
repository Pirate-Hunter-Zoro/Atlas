"""Meeting notes: what landed, what it means, what is next, what is blocked.

    "have functionality to produce 'meeting notes' for me with in-built links
     that will take me to those results/code/sections of my board writing to
     explain those notes."

This is the first thing in the system that SPENDS what the last two pieces of
work built, and it does not work without either of them.

  * §2.1 gave every place an address, so a claim in a note can point at the
    thing it is a claim about. A note that says "the grid is blocked" and cannot
    show you the grid is a note you have to go and verify.
  * §2.2 let a workspace be drawn by hand, so a commit touching
    `psych_asr/asr/align.py` can be reported as *the stopwatch* -- which is what
    the person calls it. That is the entire reason the written map is worth
    having, and this is where it gets spent.

**Nothing here is generated prose.** Every sentence is assembled from something
already written down by a person: a commit subject they wrote, a plan step they
typed, a box they named. This module summarises and links; it does not describe.
A meeting note whose sentences were invented is a meeting note that has to be
checked before it can be used, which is worse than no note.

Two rules about what comes out, and they are the ones from the handoff:

  SHORT. A meeting note nobody can read in a lift is not a meeting note.
  ONE-READ. One idea per sentence, the conclusion first, names and numbers
  rather than adjectives.

Standard library only, like everything else.
"""

import json
import os
import re
import subprocess
import time

from . import atlas, paths
from .course import document, plan
from .course import map as course_map

# Where the notes go. At the REPOSITORY root, not in a workspace: a note about
# five workspaces filed under one of them is misfiled, and the person looking
# for "the notes from the meeting on the 14th" is not looking inside a course.
OUT_DIR = "meetings"

# How many commits are LISTED before they are counted instead. A meeting note is
# not a changelog; past this, what matters is that there were forty of them.
MAX_LISTED = 6

# How many next-steps and blocked boxes are worth saying out loud.
MAX_NEXT = 3
MAX_BLOCKED = 4

# A commit subject longer than this is a paragraph somebody put on one line.
SUBJECT = 100

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday",
            "saturday", "sunday")


# ---------------------------------------------------------------------------
# when
# ---------------------------------------------------------------------------
def resolve_since(spec, root=None):
    """`(epoch, what to call it)` -- or `(None, why not)`.

    Four shapes, because the question is asked four ways by the same person in
    the same week: a date, a span, a weekday, and "since the last lot".
    """
    spec = str(spec or "").strip().lower()
    if not spec:
        return None, "say a date (2026-09-01), a span (7d, 2w), a weekday, or `last`"

    if spec == "last":
        when = _last_notes(root)
        if not when:
            return None, ("there are no earlier notes to measure from. Give a "
                          "date or a span for the first set.")
        return when, "the last set of notes"

    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", spec)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # CHECKED BEFORE `mktime`, WHICH NORMALISES RATHER THAN REFUSING:
        # month 13 quietly becomes January of the next year and day 40 rolls
        # into the month after. A typo in a date would then be a different date
        # that works, and the note would be about the wrong fortnight with
        # nothing anywhere saying so.
        if not (1 <= mo <= 12 and 1 <= d <= 31 and 1970 <= y <= 2200):
            return None, "%s is not a date" % spec
        try:
            t = time.mktime((y, mo, d, 0, 0, 0, 0, 0, -1))
        except (OverflowError, ValueError):
            return None, "%s is not a date this machine can represent" % spec
        return t, spec

    m = re.match(r"^(\d+)\s*([dwm])$", spec)
    if m:
        n = int(m.group(1))
        days = {"d": 1, "w": 7, "m": 30}[m.group(2)] * n
        if not 1 <= days <= 3650:
            return None, "%s is not a period anybody holds a meeting about" % spec
        said = ("yesterday" if days == 1
                else "last week" if days == 7
                else "the last %d days" % days)
        return time.time() - days * 86400, said

    if spec.startswith("last-"):
        spec = spec[5:]
    if spec in WEEKDAYS:
        # The most recent one, and today does not count: "since Monday" said on
        # a Monday means a week of work, not none of it.
        want = WEEKDAYS.index(spec)
        now = time.localtime()
        back = (now.tm_wday - want) % 7 or 7
        midnight = time.mktime((now.tm_year, now.tm_mon, now.tm_mday,
                                0, 0, 0, 0, 0, -1))
        return midnight - back * 86400, "last " + spec

    return None, ("%r is not a date (2026-09-01), a span (7d, 2w), a weekday, "
                  "or `last`" % spec)


def _last_notes(root):
    """When the newest set of notes was written, or 0."""
    base = root or atlas.root()
    if not base:
        return 0
    out_dir = os.path.join(base, OUT_DIR)
    newest = 0
    try:
        names = os.listdir(out_dir)
    except OSError:
        return 0
    for n in names:
        if not n.endswith(".tex"):
            continue
        try:
            newest = max(newest, os.path.getmtime(os.path.join(out_dir, n)))
        except OSError:
            continue
    return newest


# ---------------------------------------------------------------------------
# what landed
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


def _clip(text, limit):
    """Cut at a word, and say that it was cut. A subject sheared mid-word reads
    as a subject somebody mistyped."""
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return (cut or text[:limit]).rstrip(" ,;:-—") + "…"


def landed(base, rel, since_ts):
    """Commits in the period that touched this workspace, newest first.

    Scoped by PATHSPEC rather than filtered afterwards, because there is one
    repository now and every workspace's history runs through the same log. A
    note about Galois Theory that lists PSYCH-ASR's afternoon is a note nobody
    can trust about either.
    """
    raw = _git(base, ["log", "--since=@%d" % int(since_ts),
                      "--no-merges", "--pretty=%H%x00%at%x00%s",
                      "--", rel])
    out = []
    for line in raw.splitlines():
        bits = line.split("\0")
        if len(bits) != 3:
            continue
        out.append({"sha": bits[0][:8], "at": int(bits[1] or 0),
                    "subject": _clip(bits[2].strip(), SUBJECT)})
    return out


def touched(base, rel, since_ts):
    """Every file in this workspace a commit in the period changed."""
    raw = _git(base, ["log", "--since=@%d" % int(since_ts), "--no-merges",
                      "--name-only", "--pretty=format:", "--", rel])
    seen, out = set(), []
    prefix = rel.rstrip("/") + "/"
    for line in raw.splitlines():
        line = line.strip()
        if not line or line in seen:
            continue
        seen.add(line)
        if line.startswith(prefix):
            out.append(line[len(prefix):])
    return out


# ---------------------------------------------------------------------------
# what closed
# ---------------------------------------------------------------------------
def closed(base, rel, root, since_ts):
    """Plan steps that went away in the period.

    A plan here lists what is LEFT -- the convention these projects are written
    to is "DELETE, don't annotate", so a finished step is a deleted line and
    nothing anywhere records that it was finished. That deletion is the record,
    and this is the one place that reads it.
    """
    try:
        targets = plan.paths(root)
    except Exception:                                        # noqa: BLE001
        targets = []
    if not targets:
        return []
    rels = []
    for t in targets:
        if paths.within(t, base):
            rels.append(os.path.relpath(t, base))
    if not rels:
        return []

    raw = _git(base, ["log", "--since=@%d" % int(since_ts), "--no-merges",
                      "-U0", "--pretty=format:", "--"] + rels)
    out, seen = [], set()
    for line in raw.splitlines():
        if not line.startswith("-") or line.startswith("---"):
            continue
        text = line[1:]
        m = plan.STEP.match(text)
        title = ""
        if m:
            title = m.group(2)
        else:
            m2 = plan.TODO_ITEM.match(text)
            if m2 and m2.group(1) == " ":
                title = m2.group(2)
        title = re.sub(r"\s+", " ", title).strip(" .-—").strip()
        if not title or len(title) < 6 or title in seen:
            continue
        seen.add(title)
        out.append(_clip(title, SUBJECT))
    return out


# ---------------------------------------------------------------------------
# what it means, and where to look
# ---------------------------------------------------------------------------
def _address(ws_id, surface=None, **rest):
    """One address, in the §2.1 grammar, spelled the way `address.js` spells it.

    THERE IS ONE GRAMMAR AND THIS OBEYS IT. A second speller is a second set of
    links that resolve slightly differently, and the whole point of the grammar
    is that a note written in March opens in September or says plainly that it
    cannot.
    """
    fam, _, name = ws_id.partition("/")
    if not fam or not name:
        return ""
    bits = ["#/w/" + _enc(fam) + "/" + _enc(name)]
    if surface == "node":
        bits.append("/node/" + rest["node"])
    elif surface == "code":
        segs = [_enc(s) for s in str(rest["path"]).split("/")]
        tail = "/".join(segs)
        if rest.get("symbol"):
            tail += "::" + rest["symbol"]
        bits.append("/code/" + tail)
    return "".join(bits)


_SAFE = re.compile(r"^[A-Za-z0-9._~-]$")


def _enc(s):
    """Percent-encoding, the same subset `encodeURIComponent` leaves alone."""
    out = []
    for ch in str(s):
        if _SAFE.match(ch):
            out.append(ch)
        else:
            for b in ch.encode("utf-8"):
                out.append("%%%02X" % b)
    return "".join(out)


def meaning(root, ws_id, changed):
    """The written map's own words for the parts that changed.

    THIS IS WHY THE WRITTEN MAP IS WORTH HAVING. Without it the best a note can
    say is that `psych_asr/asr/align.py` changed, which is a fact about a
    filename. With it the note says *the stopwatch* moved, and that is a
    sentence somebody can take into a meeting.

    Silent when there is no written map. A derived box is a directory, and
    reporting "the psych_asr/asr directory changed" as though it meant something
    is the padding this whole module exists not to produce.
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

    changed = set(changed)
    out = []
    for node in built["nodes"]:
        owned = set(node.get("files") or [])
        d = (node.get("dir") or "").rstrip("/")
        hit = owned & changed
        if not hit and d:
            hit = set(f for f in changed if f.startswith(d + "/"))
        if not hit:
            continue
        out.append({
            "id": node["id"], "name": node["name"],
            "does": node.get("does") or "",
            "files": sorted(hit)[:3],
            "link": _address(ws_id, "node", node=node["id"]),
        })
    return out


def blocked(root, ws_id):
    """Every box that says it is waiting, and what on. `blockedBy`, spent."""
    try:
        built = course_map.status(root)
    except Exception:                                        # noqa: BLE001
        return []
    if not built or not built.get("written"):
        return []
    names = dict((n["id"], n["name"]) for n in built["nodes"])
    out = []
    for node in built["nodes"]:
        on = [names.get(b, b) for b in (node.get("blockedBy") or [])]
        if not on:
            continue
        out.append({"id": node["id"], "name": node["name"], "on": on,
                    "link": _address(ws_id, "node", node=node["id"])})
    return out[:MAX_BLOCKED]


def nextup(root):
    """The next open steps, in the plan's own order, never re-ordered."""
    try:
        return [s.get("title") or s.get("label") or ""
                for s in plan.steps(root)][:MAX_NEXT]
    except Exception:                                        # noqa: BLE001
        return []


# ---------------------------------------------------------------------------
# one workspace's block
# ---------------------------------------------------------------------------
def gather(base, ws, since_ts):
    """Everything worth saying about one workspace, or None if nothing is."""
    root = ws["root"]
    rel = os.path.relpath(root, base)
    commits = landed(base, rel, since_ts)
    files = touched(base, rel, since_ts)
    block = {
        "id": ws["id"],
        "name": ws.get("course") or ws.get("repo") or ws["id"],
        "link": _address(ws["id"]),
        "commits": commits,
        "closed": closed(base, rel, root, since_ts),
        "meaning": meaning(root, ws["id"], files),
        "next": nextup(root),
        "blocked": blocked(root, ws["id"]),
        "files": len(files),
    }
    # A WORKSPACE THAT DID NOT MOVE IS LEFT OUT, not written up as "no
    # activity". Eleven headings with nothing under ten of them is the shape of
    # a report nobody reads, and it buries the one that moved.
    #
    # MOVED means commits or a closed plan step -- something that happened in
    # the period. Being blocked is a standing fact rather than news: a note for
    # a quiet fortnight that lists every blocked box in the repository is long,
    # and length is the one thing a meeting note cannot afford. A blockage on a
    # workspace that IS moving is reported, which is when somebody can act on it.
    if not commits and not block["closed"]:
        return None
    return block


# ---------------------------------------------------------------------------
# the document
# ---------------------------------------------------------------------------
def _url_of(root):
    """The reachable URL one board wrote down for itself, or "" ."""
    try:
        with open(os.path.join(root, "live", ".board.json"),
                  "r", encoding="utf-8") as fh:
            info = json.load(fh) or {}
    except (OSError, ValueError):
        return ""
    for u in info.get("urls") or []:
        if "127.0.0.1" not in u and "localhost" not in u:
            return u.rstrip("/")
    return ""


def board_url(base, here=None):
    """A URL a link in this document can actually be opened from.

    A LINK IN A PDF HAS TO BE ABSOLUTE. A bare `#/w/…` fragment is right on the
    board's own pages and inert in a document somebody opens on a laptop --
    pdflatex writes no `/URI` for it at all, so it is not a link, it just looks
    like one. That is the failure this whole grammar exists to avoid, one layer
    out: a claim that cannot be checked, wearing the clothes of one that can.

    ANY running board will do as the entry point, which is why this falls back
    through every workspace rather than insisting on one. Each board serves the
    same front door, and the front door routes an address for another workspace
    by switching to it (§2.1). So the first reachable board is a door to all of
    them.
    """
    if here:
        found = _url_of(here)
        if found:
            return found
    for ws in atlas.workspaces(base):
        found = _url_of(ws["root"])
        if found:
            return found
    return ""


def _plural(n, one, many=None):
    return "%d %s" % (n, one if n == 1 else (many or one + "s"))


def _when(t):
    try:
        return time.strftime("%d %b", time.localtime(t))
    except (OSError, ValueError):
        return ""


def render(blocks, human, base_url, whole):
    """The note, as markdown. Short, and every claim carrying its address.

    `document.md_to_tex` turns `[text](url)` into `\href`, so the links survive
    into the PDF and are live in it.
    """
    out = []
    if not blocks:
        out.append("Nothing landed in %s." % human)
        out.append("")
        out.append("That is the note. %d workspace%s were looked at."
                   % (whole, "" if whole == 1 else "s"))
        return "\n".join(out)

    moved = sum(len(b["commits"]) for b in blocks)
    out.append("%s across %s, since %s."
               % (_plural(moved, "commit"),
                  _plural(len(blocks), "workspace"), human))
    if not base_url:
        out.append("")
        out.append("*No board is running for this machine to link through, so "
                   "the addresses below are written out rather than linked. "
                   "Open one on the board and they resolve.*")
    out.append("")

    def link(text, addr):
        """A real link, or the address written out as text. NEVER SOMETHING
        THAT LOOKS LIKE A LINK AND IS NOT -- that is the same failure the
        grammar exists to prevent, one layer out."""
        if not addr:
            return text
        if not base_url:
            return "%s (`%s`)" % (text, addr)
        return "[%s](%s%s)" % (text, base_url, addr)

    for b in blocks:
        out.append("## " + b["name"])
        out.append("")

        # WHAT LANDED. Summarised rather than listed: the subjects are the
        # person's own sentences, and past a handful what matters is the count.
        if b["commits"]:
            head = "**Landed.** " + _plural(len(b["commits"]), "commit")
            if b["files"]:
                head += ", %s touched" % _plural(b["files"], "file")
            out.append(head + ".")
            out.append("")
            for c in b["commits"][:MAX_LISTED]:
                out.append("- %s *(%s)*" % (c["subject"], _when(c["at"])))
            if len(b["commits"]) > MAX_LISTED:
                out.append("- …and %d more."
                           % (len(b["commits"]) - MAX_LISTED))
            out.append("")

        if b["closed"]:
            out.append("**Closed.** " + _plural(len(b["closed"]), "plan step")
                       + " came off the plan.")
            out.append("")
            for t in b["closed"][:MAX_LISTED]:
                out.append("- " + t)
            out.append("")

        # WHAT IT MEANS, in the person's own names for their own work. This is
        # the section the written map exists for.
        if b["meaning"]:
            out.append("**What moved.**")
            out.append("")
            for n in b["meaning"]:
                said = (" — " + n["does"]) if n["does"] else ""
                out.append("- %s%s" % (link(n["name"], n["link"]), said))
            out.append("")

        # THE CONCLUSION FIRST, which for this section is the one step that is
        # actually next. The rest are after it and are a list, because they are
        # a list; the first one is a sentence because it is the answer.
        if b["next"]:
            out.append("**Next.** " + b["next"][0].rstrip(".") + ".")
            if len(b["next"]) > 1:
                out.append("")
                out.append("Then: " + "; ".join(
                    t.rstrip(".") for t in b["next"][1:]) + ".")
            out.append("")

        if b["blocked"]:
            out.append("**Blocked.**")
            out.append("")
            for n in b["blocked"]:
                out.append("- %s waits on %s."
                           % (link(n["name"], n["link"]),
                              " and ".join(n["on"])))
            out.append("")

        out.append("%s" % link("Open " + b["name"], b["link"]))
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def build(base, since_ts, human, want=None, make_pdf=True, here=None):
    """Gather, render, typeset, track. The record the board paints.

    Same pipeline as every other document in this system: markdown into
    `document.md_to_tex`, a numbered `-vN` rather than a timestamp, and staged
    rather than committed, because a commit is a decision a person makes.
    """
    every = atlas.workspaces(base)
    if want:
        want = set(want)
        every = [w for w in every
                 if w["id"] in want or w["dir"] in want]
        if not every:
            return {"ok": False,
                    "detail": "none of those are workspaces in this repository"}

    blocks = []
    for ws in every:
        try:
            one = gather(base, ws, since_ts)
        except Exception:                                    # noqa: BLE001
            one = None
        if one:
            blocks.append(one)

    body = render(blocks, human, board_url(base, here), len(every))
    title = "Meeting notes — " + time.strftime("%d %B %Y")

    out_dir = os.path.join(base, OUT_DIR)
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as exc:
        return {"ok": False, "detail": "could not make %s: %s" % (out_dir, exc)}

    stem = "meeting-" + time.strftime("%Y-%m-%d")
    version = document.next_version(out_dir, stem)
    name = "%s-v%d" % (stem, version)
    tex_path = os.path.join(out_dir, name + ".tex")

    with open(tex_path, "w", encoding="utf-8") as fh:
        fh.write(document.TEX_HEAD % {
            "title": document.inline_tex(title),
            "author": document.inline_tex(_author(base)),
            "date": time.strftime("%B %d, %Y"),
            "macros": "",
        })
        # `md_to_tex` hands back one string, not a list of lines. Joining a
        # string joins its CHARACTERS, which produced a 40-page document one
        # letter per line and compiled perfectly well.
        fh.write(document.md_to_tex(body))
        fh.write("\n\\end{document}\n")

    rec = {"ok": True, "name": name, "version": version,
           "workspaces": [b["id"] for b in blocks],
           "markdown": body,
           "tex": os.path.relpath(tex_path, base), "pdf": None, "detail": ""}
    if make_pdf:
        ok, res = document.compile_pdf(base, tex_path)
        if ok:
            rec["pdf"] = os.path.relpath(res, base)
        else:
            rec["ok"] = False
            rec["detail"] = res
    rec["tracked"] = document.track(
        base, [tex_path, os.path.join(out_dir, name + ".pdf")])
    return rec


def _author(base):
    name = _git(base, ["config", "user.name"]).strip()
    return name or "the board"
