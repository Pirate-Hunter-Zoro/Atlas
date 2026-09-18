"""The meeting deck: what landed, what it means, what is next, what is blocked.

    "have functionality to produce 'meeting notes' for me with in-built links
     that will take me to those results/code/sections of my board writing to
     explain those notes."

    "I want a presentation like the ones made for PSYCH-ASR created and
     rendered for me... We're also not gonna save every presentation pertaining
     to meeting notes -- this is a one-off communication tool. BUT what we will
     do is save each most recent one."

A BEAMER FRAME PER WORKSPACE, at `meetings/meeting.pdf`, and there is exactly
one of it: making a new one REPLACES the one before. `meetings/` is tracked, so
nothing accumulates in the tree and `git log` holds every deck there has ever
been -- which is recoverable, and a delete is not.

ONE FRAME IS EXACTLY ONE PAGE, and that is load-bearing rather than
typographic. The page a mark is on is how that mark finds its workspace --
`page_map` below, and `proposals.py` on the other end of it -- so a frame that
quietly spilled onto a second page would route somebody's mentor's suggestion
into the wrong project.

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
A slide you are going to stand behind in front of your mentors is the last place
for a sentence nobody wrote, and a model asked to write the deck would buy
polish at the price of the one property that makes it usable without checking.
If a frame reads badly, the fix is `frames` below.

Two rules about what comes out, and they are the ones from the handoff:

  SHORT. A frame nobody can read across a room is not a frame.
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

# Where the deck goes. At the REPOSITORY root, not in a workspace: a document
# about five workspaces filed under one of them is misfiled, and it is also
# what keeps the deck out of every workspace's own library.
OUT_DIR = "meetings"

# How many commits the PROSE form lists before it counts them instead --
# `render`, which is what `board notes --print` gives and what the deck is
# built alongside. A summary is not a changelog; past this, what matters is
# that there were forty of them. The frames have their own, smaller, numbers.
MAX_LISTED = 6

# How many next-steps and blocked boxes are worth saying out loud.
MAX_NEXT = 3
MAX_BLOCKED = 4

# A commit subject longer than this is a paragraph somebody put on one line.
SUBJECT = 100

# ---------------------------------------------------------------------------
# THE DECK: ONE OF THEM, AT A FIXED PATH
# ---------------------------------------------------------------------------
# Asked for in these words: *"we're also not gonna save every presentation
# pertaining to meeting notes -- this is a one-off communication tool. BUT what
# we will do is save each most recent one... if I elect to make a new one, then
# that new one REPLACES the old one."*
#
# So there is no `-v1, -v2, -v3` here and no date in the name: one stem, written
# over. `meetings/` is TRACKED rather than ignored, which is what makes that
# safe -- nothing accumulates in the tree, and `git log` still holds every deck
# there has ever been. That is the cheap version of "we are not going to save
# every presentation", and it is recoverable, which a delete is not.
STEM = "meeting"

# What was on each frame, beside the frames. The reader needs to know WHICH
# WORKSPACE a page is about, because a mark on a page is direction input for
# that workspace and for no other -- and the routing is in the geometry rather
# than in anything a person types.
RECORD = STEM + ".json"

# What a mark on a slide of it is keyed under. The same grammar every marked
# page in this system uses -- `doc/<ident>/p<n>`, `writing.ANN_DOC` -- so the
# pen, the store and the picture of the page are the ones that already exist.
# It is a constant rather than derived from the filename because there is
# exactly one deck: a second ident would be a second document.
ANN_IDENT = STEM

# HOW MUCH GOES ON ONE FRAME, and these are smaller than the note's numbers on
# purpose. A slide is read across a room in the thirty seconds somebody spends
# looking at it before you start talking; the note is read sitting down. Six
# commits is a readable paragraph and an unreadable slide.
DECK_COMMITS = 4
DECK_CLOSED = 3
DECK_MEANING = 3
DECK_BLOCKED = 2

# And a subject is clipped shorter for a frame than for a page, for the same
# reason. Beamer's column is about 80 characters wide at this size.
DECK_SUBJECT = 78

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
            return None, ("there is no earlier deck to measure from. Give a "
                          "date or a span for the first one.")
        return when, "the last deck"

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
    """When the deck was last written, or 0."""
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
        # WHAT THEY CALL IT. The qualified id is the address and is the last
        # resort here: `research/PSYCH-ASR` is a path, and a frame title in
        # front of mentors wants the name of the project.
        "name": ws.get("course") or ws.get("repo") or ws.get("dir") or ws["id"],
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


# ---------------------------------------------------------------------------
# the deck
# ---------------------------------------------------------------------------
# A PRESENTATION, NOT A DOCUMENT, and the difference is the frame. A note is
# read sitting down and its unit is the paragraph; this is stood in front of
# mentors and its unit is a slide, which is a hard limit on how much may be on
# it. `render` above is the same blocks as prose and is what `--print` gives.
#
# ASSEMBLED, NOT GENERATED, and that is the decision in this whole item. A model
# asked to write the deck would produce better sentences, and the price is the
# one property that makes it usable without checking: every line here is a
# commit subject somebody wrote, a plan step they typed, or a box they named.
# A slide you are going to stand behind in front of your mentors is the last
# place in this repository for a sentence nobody wrote. If the deck reads badly
# the fix is this function, not a turn.
#
# ONE FRAME PER WORKSPACE AND EXACTLY ONE PAGE PER FRAME. `shrink` is what
# guarantees the second half: it scales a frame that would overflow instead of
# letting beamer spill it onto a page nobody planned. That matters far beyond
# typography -- the page a mark is on is how the mark finds its workspace, and a
# frame that quietly became two pages would route somebody's mentor's suggestion
# into the wrong project.
def frames(blocks, human, base_url, whole):
    """The deck's body, as LaTeX. One title frame, then one frame per block."""
    out = []
    moved = sum(len(b["commits"]) for b in blocks)
    subtitle = ("%s across %s, since %s."
                % (_plural(moved, "commit"), _plural(len(blocks), "workspace"),
                   human)) if blocks else ("Nothing landed in %s." % human)

    out.append("\\begin{frame}[plain]")
    out.append("  \\titlepage")
    out.append("  \\begin{center}\\small %s\\end{center}"
               % document.inline_tex(subtitle))
    out.append("\\end{frame}")
    out.append("")

    if not blocks:
        # ONE FRAME SAYING SO, rather than a deck of empty headings. Standing in
        # front of a slide that says nothing happened is a shorter meeting than
        # standing in front of eleven that each say it separately.
        out.append("\\begin{frame}{Nothing to report}")
        out.append("  %s" % document.inline_tex(
            "%d workspace%s were looked at and none of them moved in %s."
            % (whole, "" if whole == 1 else "s", human)))
        out.append("\\end{frame}")
        out.append("")
        return "\n".join(out) + "\n"

    def link(text, addr):
        """A real link, or the address as text. NEVER SOMETHING THAT LOOKS LIKE
        A LINK AND IS NOT -- `render` states the rule and this obeys the same
        one, because a deck is opened on a laptop in the meeting as often as it
        is projected."""
        if not addr or not base_url:
            return text
        return "[%s](%s%s)" % (text, base_url, addr)

    for b in blocks:
        out.append("\\begin{frame}[shrink=25]{%s}{%s}"
                   % (document.inline_tex(link(b["name"], b["link"])),
                      document.inline_tex(_subtitle_of(b, human))))
        out.append("  \\begin{itemize}\\small")

        for c in b["commits"][:DECK_COMMITS]:
            out.append("    \\item %s \\textcolor{gray}{\\tiny(%s)}"
                       % (document.inline_tex(_clip(c["subject"], DECK_SUBJECT)),
                          document.inline_tex(_when(c["at"]))))
        if len(b["commits"]) > DECK_COMMITS:
            out.append("    \\item \\textcolor{gray}{\\ldots and %d more.}"
                       % (len(b["commits"]) - DECK_COMMITS))

        for t in b["closed"][:DECK_CLOSED]:
            out.append("    \\item \\textbf{Closed.} %s"
                       % document.inline_tex(_clip(t, DECK_SUBJECT)))

        # WHAT IT MEANS, in their own names for their own work. This is the
        # section the written map exists for and the one a mentor can act on:
        # "psych\_asr/asr/align.py changed" is a fact about a filename.
        for n in b["meaning"][:DECK_MEANING]:
            said = (" --- " + _clip(n["does"], DECK_SUBJECT)) if n["does"] else ""
            out.append("    \\item \\textbf{%s}%s"
                       % (document.inline_tex(link(n["name"], n["link"])),
                          document.inline_tex(said)))

        if b["next"]:
            out.append("    \\item \\textbf{Next.} %s"
                       % document.inline_tex(
                           _clip(b["next"][0].rstrip("."), DECK_SUBJECT) + "."))

        for n in b["blocked"][:DECK_BLOCKED]:
            out.append("    \\item \\textbf{Blocked.} %s waits on %s."
                       % (document.inline_tex(link(n["name"], n["link"])),
                          document.inline_tex(" and ".join(n["on"]))))

        out.append("  \\end{itemize}")
        out.append("\\end{frame}")
        out.append("")

    return "\n".join(out) + "\n"


def _subtitle_of(b, human):
    """The one line under a frame's title: how much moved, and since when."""
    bits = []
    if b["commits"]:
        bits.append(_plural(len(b["commits"]), "commit"))
    if b["files"]:
        bits.append(_plural(b["files"], "file") + " touched")
    if b["closed"]:
        bits.append(_plural(len(b["closed"]), "step") + " closed")
    return ", ".join(bits) + (" since %s" % human if bits else human)


def page_map(blocks):
    """`{page: workspace id}` -- which frame is about which workspace.

    THE ROUTING IS IN THE GEOMETRY. A mark on a slide is direction input for the
    workspace that slide is about, and this is the only thing that knows which
    that is. Page 1 is the title and belongs to nobody, which is why it is not
    in here rather than being mapped to the first workspace.
    """
    return dict((str(i + 2), b["id"]) for i, b in enumerate(blocks))


def deck(base):
    """The one deck, as it stands, or None if none has been made.

    `pages` is what `page_map` wrote at build time, `since` is what it was made
    for, and `at` is when. Read off disk rather than recomputed: the deck on the
    glass is the one that was built, and rebuilding the map from a fresh `gather`
    would describe a deck that is not there.
    """
    out_dir = os.path.join(base, OUT_DIR)
    try:
        with open(os.path.join(out_dir, RECORD), "r", encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(rec, dict):
        return None
    rec["pdf"] = os.path.join(out_dir, STEM + ".pdf")
    rec["tex"] = os.path.join(out_dir, STEM + ".tex")
    rec["has_pdf"] = os.path.isfile(rec["pdf"])
    return rec


def ink_keys(repo):
    """Every annotation key on this deck that has strokes under it.

    The store is the board's own -- one record per key under `live/annotations`
    -- and the keys are `doc/meeting/p<n>`, so the pen, the picture and the
    coordinates are all the ones that already exist.
    """
    from .lesson import notes as lesson_notes          # local: avoids a cycle
    from .server.routes import writing                 # local: avoids a cycle

    out = {}
    for key, strokes in lesson_notes.load_notes(repo).items():
        found = writing.ann_doc_page(key)
        if found and strokes and found[0] == ANN_IDENT:
            out[key] = strokes
    return out


def clear_ink(repo):
    """Throw away every mark on the deck. Returns how many keys went.

    THE ONE DOCUMENT IN THIS SYSTEM WHERE OLD MARKS HAVE NO MEANING AT ALL. Ink
    on a paper is a complaint about that paper and survives a revision of it;
    ink on a slide is a direction somebody suggested in a meeting, and the
    moment it was sent it was consumed into that direction. The deck is
    overwritten at a fixed path with different pages on it, so a mark left on
    page 4 would reappear over next week's page 4, over a different workspace,
    as a suggestion nobody made.
    """
    from .server.routes import writing                 # local: avoids a cycle

    gone = 0
    for key in ink_keys(repo):
        stem = os.path.join(repo.notes, writing.ann_file(key))
        for ext in (".json", ".png"):
            try:
                os.remove(stem + ext)
            except OSError:
                continue
            if ext == ".json":
                gone += 1
    return gone


def build(base, since_ts, human, want=None, make_pdf=True, here=None,
          repo=None, write=True):
    """Gather, assemble, typeset, track. One deck, at one path, overwritten.

    `want` is which workspaces to look at -- their `id` or their bare directory
    -- and nothing else is looked at when it is given. Without it, every
    workspace in the repository is gathered and the ones that did not move are
    left out, which is what the front door does when nobody ticks anything.

    `repo` is the board that is serving, and the only thing it is for is the
    ink: the marks on the deck live in that board's annotation store, and a new
    deck at the same path with different pages on it must not inherit them.

    `write=False` ASSEMBLES AND TOUCHES NOTHING, which is what `--print` wants.
    There is one deck at one path now, so a run that wrote the source without
    building the PDF would leave a `.tex` and a `.pdf` beside each other that
    are not the same deck -- and would throw away the marks on the one that is
    still on the glass, for a command that was only asked to show its text.
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

    base_url = board_url(base, here)
    body = render(blocks, human, base_url, len(every))
    title = "Where the work is"

    if not write:
        return {"ok": True, "name": STEM,
                "workspaces": [b["id"] for b in blocks],
                "names": dict((b["id"], b["name"]) for b in blocks),
                "pages": page_map(blocks), "since": human, "at": time.time(),
                "markdown": body, "tex": "", "pdf": None, "detail": "",
                "wrote": False}

    out_dir = os.path.join(base, OUT_DIR)
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as exc:
        return {"ok": False, "detail": "could not make %s: %s" % (out_dir, exc)}

    tex_path = os.path.join(out_dir, STEM + ".tex")
    pdf_path = os.path.join(out_dir, STEM + ".pdf")
    # THE OLD PDF GOES BEFORE THE NEW SOURCE LANDS. One deck at one path means
    # a compile that fails would otherwise leave LAST week's rendering beside
    # THIS week's page map -- and the page map is how a mark finds its
    # workspace, so the reader would hand somebody a slide about one project
    # and route their marks on it to another.
    try:
        os.remove(pdf_path)
    except OSError:
        pass
    with open(tex_path, "w", encoding="utf-8") as fh:
        fh.write(document.BEAMER_HEAD % {
            "title": document.inline_tex(title),
            "author": document.inline_tex(_author(base)),
            "date": time.strftime("%d %B %Y"),
        })
        fh.write(frames(blocks, human, base_url, len(every)))
        fh.write("\n\\end{document}\n")

    pages = page_map(blocks)
    rec = {"ok": True, "name": STEM,
           "workspaces": [b["id"] for b in blocks],
           "names": dict((b["id"], b["name"]) for b in blocks),
           "pages": pages,
           "since": human, "at": time.time(),
           "markdown": body,
           "tex": os.path.relpath(tex_path, base), "pdf": None, "detail": ""}

    # THE OLD MARKS GO BEFORE THE NEW DECK IS ANNOUNCED, not after. They are
    # cleared even when LaTeX then refuses the deck: the .tex on disk is already
    # the new one, so the pages the old ink was drawn on are gone either way.
    if repo is not None:
        rec["cleared"] = clear_ink(repo)
    # AND THE PICTURES OF THOSE MARKS, which sit beside the deck rather than in
    # the board that served it. Local import: `proposals` is what reads this
    # deck's marks, so it imports this module.
    from . import proposals                          # local: avoids a cycle
    rec["pictures"] = proposals.forget_pictures(base)

    if make_pdf:
        ok, res = document.compile_pdf(base, tex_path)
        if ok:
            rec["pdf"] = os.path.relpath(res, base)
        else:
            rec["ok"] = False
            rec["detail"] = res

    # THE PAGE MAP IS WRITTEN WHATEVER LaTeX SAID, because the .tex is the deck
    # and the record describes it. It is written LAST so that a reader that
    # finds a record finds a deck beside it.
    try:
        with open(os.path.join(out_dir, RECORD), "w", encoding="utf-8") as fh:
            json.dump({"name": STEM, "workspaces": rec["workspaces"],
                       "names": rec["names"], "pages": pages,
                       "since": human, "at": rec["at"],
                       "built": bool(rec["pdf"])}, fh)
    except OSError as exc:
        rec["ok"] = False
        rec["detail"] = (rec["detail"] + " ") if rec["detail"] else ""
        rec["detail"] += "the page map could not be written: %s" % exc

    rec["tracked"] = document.track(
        base, [tex_path, pdf_path, os.path.join(out_dir, RECORD)])
    return rec


def _author(base):
    name = _git(base, ["config", "user.name"]).strip()
    return name or "the board"
