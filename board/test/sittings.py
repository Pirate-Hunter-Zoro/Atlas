#!/usr/bin/env python3
"""Slides from sittings: which sittings, what they did, the deck, and its ink.

    "I just want to be able to select from tutoring sessions what we've done
     over all sessions and get to pick a list of the things I want to include
     in the presentation. I leave it up to the AI tutor to actually decide what
     slides are dedicated to which things accomplished, but various figures,
     etc. that are relevant should be accessible to the tutor as well as it
     makes the slides. I want to be able to mark up on the slide... and get it
     re-rendered. I don't want to be limited to one slide per project."

What this guards, in the order a tap meets it:

  * THE LISTING IS EVERY SITTING, and none of the noise. A shell -- a sitting
    filed before anything happened in it -- is hidden; one with no state.json,
    or an empty one, is listed rather than tripping anything; and consecutive
    sittings on one chapter are one row, with the window of both.
  * WHAT A SITTING DID is its commits inside the window, minus the saves; the
    bullets of the handoff THAT sitting wrote, found in git where it is not on
    disk any more; and "everything this sitting covered".
  * AN ID, NEVER A PATH. A pick is matched against the listing, and `../` is a
    miss rather than a directory.
  * THE FENCE. Nothing under `phi/` or `data/` is snapshotted, catalogued or
    named in the brief, and every path the brief names passes `fenced.refused`.
  * THE DISPATCH is `/writeup`'s own: a refused start writes nothing, and an
    allowed one leaves a `[writeup]` line pointing at the brief, in the
    workspace holding most of what was ticked.
  * THE FENCE HOSTS. A deck touching a fenced workspace is written inside it.
  * AND THE INK IS A REVISION THAT KNOWS ITS BRIEF, sends only marks no earlier
    round delivered unless that round did not come back, marks ink delivered
    only once the revision was asked, and can pull one more figure -- from a
    workspace the deck is about -- with `board deckfig`.
"""

import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


fake = tempfile.mkdtemp(prefix="tutor-sittings-")
os.environ["TUTORBOARD_COURSES"] = fake

from tutorboard import atlas, fenced, sense, sittings, writeups   # noqa: E402
from tutorboard.course import library, results                    # noqa: E402
from tutorboard.course import repo as course_repo                 # noqa: E402
from tutorboard.lesson import notes as lesson_notes               # noqa: E402
from tutorboard.server import handler, hub, spawn, tikz           # noqa: E402
from tutorboard.server.routes import writing as writing_route     # noqa: E402

atlas.forget()

with open(os.path.join(fake, "atlas.json"), "w", encoding="utf-8") as fh:
    json.dump({"families": [{"id": "courses", "name": "Courses"},
                            {"id": "research", "name": "Research"}]}, fh)


def write(path, text, mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if isinstance(text, bytes) else "w"
    with open(path, mode) as fh:
        fh.write(text)
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def png(path, mtime, w=640, h=480):
    """A PNG big enough for `results` to call a figure, with a real IHDR."""
    import struct
    head = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" \
        + struct.pack(">II", w, h) + b"\x08\x02\x00\x00\x00"
    write(path, head + b"\x00" * 1400, mtime)


DAY = 86400
T0 = time.time() - 12 * DAY
T0 = T0 - (T0 % DAY) + 12 * 3600        # a round hour, far enough back


def at(day, hour, minute=0):
    return T0 + day * DAY + hour * 3600 + minute * 60


def stamp(t):
    return time.strftime("%Y%m%d-%H%M%S", time.localtime(t))


def opened(t):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(t))


def filed(root, t, label, state=None, cards=0, turns=0, bodies=None,
          card_at=None):
    folder = os.path.join(root, "live", "archive", "%s-%s" % (stamp(t), label))
    os.makedirs(folder, exist_ok=True)
    if state is not None:
        write(os.path.join(folder, "state.json"), json.dumps(state))
    for n in range(cards):
        body = (bodies or {}).get(n, "A card about %s." % label)
        write(os.path.join(folder, "%04d-lesson.md" % (n + 1)),
              "---\nkind: lesson\n---\n%s\n" % body, card_at)
    if turns:
        write(os.path.join(folder, "turns.jsonl"),
              "".join('{"id": "t%04d", "t": 1}\n' % i for i in range(turns)))
    return os.path.basename(folder)


def workspace(family, name):
    where = os.path.join(fake, family, name)
    os.makedirs(os.path.join(where, "live"), exist_ok=True)
    write(os.path.join(where, "tutorboard.json"), json.dumps({"name": name}))
    return where


fields = workspace("courses", "Fields")
proj = workspace("research", "Proj")

# ---- Fields: a shell, two unlabelled sittings, two on one chapter, one open --
shell = filed(fields, at(1, 10), "shell", {"chapter": "Ch 01"}, cards=0, turns=1)
nostate = filed(fields, at(2, 10), "nostate", None, cards=1, card_at=at(2, 9))
empty = filed(fields, at(3, 10), "emptystate", {}, cards=1, card_at=at(3, 9))
rings_a = filed(fields, at(4, 12), "ch-02-rings",
                {"chapter": "Ch 02 — Rings", "opened": opened(at(4, 10))},
                cards=2, turns=2)
rings_b = filed(fields, at(5, 12), "ch-02-rings",
                {"chapter": "Ch 02 — Rings", "opened": opened(at(5, 10))},
                cards=1, turns=1)
write(os.path.join(fields, "live", "state.json"),
      json.dumps({"course": "Fields", "chapter": "Ch 03 — Fields",
                  "opened": opened(at(6, 10))}))
write(os.path.join(fields, "live", "cards", "0001-lesson.md"),
      "---\nkind: lesson\n---\nSplitting fields.\n")
write(os.path.join(fields, "HANDOFF.md"),
      "<!-- chapter: Ch 03 — Fields -->\n## Where this got to\n\n"
      "- Splitting fields are unique up to isomorphism, shown by induction\n")
write(os.path.join(fields, "live", "handoffs", "ch-02-rings.md"),
      "<!-- chapter: Ch 02 — Rings -->\n## Where this got to\n\n"
      "- The parked bullet: every maximal ideal is prime\n")

# ---- Proj: three sittings, the first and last on one chapter ---------------
p1 = filed(proj, at(4, 18), "knn",
           {"chapter": "knn", "opened": opened(at(4, 16))}, cards=2, turns=2)
p2 = filed(proj, at(6, 18), "sweep",
           {"chapter": "sweep", "opened": opened(at(6, 16))}, cards=1, turns=1)
p3 = filed(proj, at(8, 18), "knn",
           {"chapter": "knn", "opened": opened(at(8, 16))}, cards=1, turns=1)

# The figures. Only `results/` is walked, and `phi/` and `data/` never are.
roc = "results/figs/roc.png"
png(os.path.join(proj, roc), at(4, 17), 1800, 1200)
png(os.path.join(proj, "results/figs/embedded.png"), at(1, 1))
png(os.path.join(proj, "results/figs/named.png"), at(1, 2))
png(os.path.join(proj, "results/figs/old.png"), at(1, 3))
png(os.path.join(proj, "results/data/leak3.png"), at(4, 17))
png(os.path.join(proj, "phi/leak.png"), at(4, 17))
png(os.path.join(proj, "data/leak2.png"), at(4, 17))
for n in range(28):
    png(os.path.join(proj, "results/many/fig%02d.png" % n), at(4, 16, n))
results.forget()
embedded_id = results.ident("results/figs/embedded.png")
roc_id = results.ident(roc)
with open(os.path.join(proj, "live", "archive", p1, "0002-lesson.md"), "w",
          encoding="utf-8") as fh:
    fh.write("---\nkind: lesson\n---\nThe overlap.\n\n![it](/result/%s)\n"
             % embedded_id)

# ---- the history, with dates -------------------------------------------------
def git(*args, when=None):
    env = dict(os.environ)
    if when is not None:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = "%d +0000" % int(when)
    env.setdefault("GIT_AUTHOR_NAME", "t")
    env.setdefault("GIT_AUTHOR_EMAIL", "t@t")
    env.setdefault("GIT_COMMITTER_NAME", "t")
    env.setdefault("GIT_COMMITTER_EMAIL", "t@t")
    return subprocess.run(["git"] + list(args), cwd=fake, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=True).stdout.decode()


def commit(path, text, subject, when, body=""):
    write(os.path.join(fake, path), text)
    git("add", path)
    git("commit", "-q", "-m", subject + ("\n\n" + body if body else ""), when=when)


git("init", "-q")
git("config", "user.name", "t")
git("config", "user.email", "t@t")
commit("atlas.json", open(os.path.join(fake, "atlas.json")).read(), "the atlas",
       at(0, 1))
commit("courses/Fields/notes.md", "out\n", "Out of window work", at(3, 11))
commit("courses/Fields/notes.md", "lattice\n",
       "Rings: the ideal lattice is drawn", at(4, 11),
       body="The lattice of ideals of Z/12 is drawn, with every inclusion.")
commit("courses/Fields/notes.md", "save\n", "courses/Fields: lesson complete",
       at(4, 11, 30))
commit("courses/Fields/notes.md", "tx\n", "lesson transcript", at(4, 11, 40))
# A WORKSPACE'S PREFIX ON REAL WORK. Only what follows the prefix says whether
# it is a save, and this is the homework.
commit("courses/Fields/notes.md", "hw\n",
       "courses/Fields: homework 3 through problem 31", at(4, 11, 45))
commit("courses/Fields/notes.md", "other\n", "research/Proj: stopping point",
       at(4, 11, 50))
commit("research/Proj/TODO.md",
       "# Plan\n\nSTEP 1. Weight the metric by importance. (Added 2026-09-01.)\n"
       "STEP 2. Sweep the neighbour count. (Added 2026-09-01.)\n"
       "STEP 3. Write the supplement table\n\n"
       "- [ ] Draw the forest plot\n- [ ] Bootstrap the intervals\n",
       "plan", at(4, 15))
commit("research/Proj/code.py", "w = 1\n", "Weight the metric by importance",
       at(4, 17), body="AUC moves from 0.594 to 0.625.")
# Inside p1's window: STEP 1 is done and deleted, the forest plot is ticked,
# STEP 2 is only re-dated and STEP 3 only renumbered. Two finished, not four.
commit("research/Proj/TODO.md",
       "# Plan\n\nSTEP 1. Sweep the neighbour count. (Added 2026-09-05.)\n"
       "STEP 2. Write the supplement table\n\n"
       "- [x] Draw the forest plot\n- [ ] Bootstrap the intervals\n",
       "plan moved on", at(4, 17, 50))
commit("research/Proj/HANDOFF.md",
       "<!-- chapter: knn -->\n## Where this got to\n\n- The knn bullet from "
       "the first sitting, which mentions named.png\n", "handoff", at(4, 17, 20))
commit("research/Proj/HANDOFF.md",
       "<!-- chapter: sweep -->\n## Where this got to\n\n- A sweep bullet that "
       "belongs to another chapter\n", "handoff again", at(4, 17, 40))
write(os.path.join(proj, "HANDOFF.md"),
      "<!-- chapter: knn -->\n## Where this got to\n\nThe third sitting's own "
      "paragraph, from the live file.\n\nHOW THEY WORK. They answer by "
      "rewriting the object, not in prose.\n\n## How this student works\n\n"
      "Answer the questions on their page before any exercise.\n\n"
      "## Teach next\n\nGrade the BH answer, then sharpen it.\n\n"
      "## Open question\n\nWhether the sweep needs a second seed.\n")
sittings.forget()

base = fake

# ---------------------------------------------------------------------------
# the listing
# ---------------------------------------------------------------------------
got = sittings.listing(base)
rows = got["sittings"]
ids = [r["id"] for r in rows]
by = dict((r["id"], r) for r in rows)
check("the listing answers, and says where the sheet folds",
      got["ok"] is True and got["fold"] == sittings.MOST_ROWS)
check("a shell -- no cards, one turn -- is not offered",
      not [i for i in ids if shell in i])
check("a sitting with no state.json is listed, under its folder's label",
      "courses/Fields@" + nostate in ids
      and "nostate" in by["courses/Fields@" + nostate]["label"])
check("and so is one whose state is {}",
      "courses/Fields@" + empty in ids)
merged = "courses/Fields@" + rings_a
check("two consecutive sittings on one chapter are ONE row, named by the first",
      merged in ids and "courses/Fields@" + rings_b not in ids)
check("which says it is two, and carries both sittings' cards",
      "2 sittings" in by[merged]["label"] and by[merged]["cards"] == 3)
check("the open sitting is its own row and says it is open",
      "courses/Fields@live" in ids
      and "open now" in by["courses/Fields@live"]["label"])
check("a chapter left and come back to is two rows, not one",
      "research/Proj@" + p1 in ids and "research/Proj@" + p3 in ids)
check("newest first within a workspace",
      ids.index("research/Proj@" + p3) < ids.index("research/Proj@" + p1))
check("the row counts commits in its window, not the saves -- and a "
      "workspace-prefixed commit that is real work is not a save",
      by[merged]["commits"] == 2)
check("and a workspace holding a fence says so on its rows",
      by["research/Proj@" + p1]["fenced"] == ["data", "phi"])
real_fold = sittings.MOST_ROWS
sittings.MOST_ROWS = 1
folded = sittings.listing(base)
oldest = [r["id"] for r in folded["sittings"] if r["ws"] == "courses/Fields"][-1]
check("EVERY SITTING IS SENT, however many a workspace has: the fold is the "
      "sheet's, and an old one past it can still be picked",
      [r["id"] for r in folded["sittings"]] == ids and folded["fold"] == 1
      and [g["sitting"] for g in sittings.items(base, [oldest])["groups"]]
      == [oldest])
sittings.MOST_ROWS = real_fold
check("nothing on a row is a path",
      not any("/" in str(v) and os.sep + "live" in str(v)
              for r in rows for v in r.values()))

# NO TWO ROWS SHARE A MOMENT. `opened` is to the minute and a filing to the
# second, so a sitting opened the minute the last was filed would start before
# that one ended. A separate atlas, so the rows above are not disturbed.
base2 = tempfile.mkdtemp(prefix="tutor-sittings-adj-")
with open(os.path.join(base2, "atlas.json"), "w", encoding="utf-8") as fh:
    json.dump({"families": [{"id": "courses", "name": "Courses"}]}, fh)
adj = os.path.join(base2, "courses", "Adj")
write(os.path.join(adj, "tutorboard.json"), json.dumps({"name": "Adj"}))
filed(adj, at(2, 10) + 30, "first", {"chapter": "A", "opened": opened(at(2, 9))},
      cards=1, turns=2)
filed(adj, at(3, 10), "second", {"chapter": "B", "opened": opened(at(2, 10))},
      cards=1, turns=2)
atlas.forget()
adj_rows = [r for _, _, rs in sittings._rows(base2)[0] for r in rs]
atlas.forget()
check("a sitting opened the minute the last was filed starts where that one "
      "ended, not a few seconds before",
      len(adj_rows) == 2 and adj_rows[0]["start"] == adj_rows[1]["end"]
      == at(2, 10) + 30)

# ---------------------------------------------------------------------------
# what they did
# ---------------------------------------------------------------------------
everything = sittings.items(base, ids)
groups = dict((g["sitting"], g) for g in everything["groups"])
texts = [i["text"] for g in everything["groups"] for i in g["items"]]
kinds = lambda sid: [i["kind"] for i in groups[sid]["items"]]   # noqa: E731
check("a real commit inside the window is an item",
      "Rings: the ideal lattice is drawn" in
      [i["text"] for i in groups[merged]["items"]])
check("the saves are not: `lesson complete` under a workspace's own prefix, "
      "`lesson transcript`, and `stopping point` under another's",
      not [t for t in texts if "lesson complete" in t or t == "lesson transcript"
           or "stopping point" in t])
check("while a commit under a workspace's prefix that says what was done is "
      "an item",
      "courses/Fields: homework 3 through problem 31"
      in [i["text"] for i in groups[merged]["items"]])
check("a save-like word after a prefix is still read as the rest of the "
      "subject, not the prefix",
      sittings.noise("courses/Fields: lesson complete", {"courses/Fields"})
      and not sittings.noise("courses/Fields: 4.11 typeset, and the pages "
                             "behind it filed", {"courses/Fields"}))
check("and a commit outside every window is nobody's",
      "Out of window work" not in texts)
check("every sitting can be taken whole, because a course's commits say nothing",
      all(g["items"][-1]["kind"] == "whole" for g in everything["groups"]))
check("which says how many cards it is",
      groups[merged]["items"][-1]["text"]
      == "Everything this sitting covered (3 cards)")
p1_text = [i["text"] for i in groups["research/Proj@" + p1]["items"]]
check("an older sitting's handoff is the revision committed in its window",
      any("knn bullet from the first sitting" in t for t in p1_text))
check("and only one stamped with its own chapter",
      not any("sweep bullet" in t for t in p1_text))
p1_steps = [i["text"] for i in groups["research/Proj@" + p1]["items"]
            if i["kind"] == "step"]
check("a plan step is finished only when it is gone at the window's end: the "
      "deleted one and the ticked one",
      sorted(p1_steps) == ["Draw the forest plot", "Weight the metric by importance"])
check("not one that was only re-dated or renumbered",
      not [t for t in p1_steps if "Sweep" in t or "supplement" in t])
p3_text = [i["text"] for i in groups["research/Proj@" + p3]["items"]]
check("a handoff's notes about the student and the next move are not offered "
      "as things done",
      not [t for t in p3_text if "HOW THEY WORK" in t or "questions on their page"
           in t or "Grade the BH" in t or "second seed" in t])
check("the newest sitting on a chapter reads the live file",
      any("third sitting's own paragraph" in i["text"]
          for i in groups["research/Proj@" + p3]["items"]))
check("or the parked one, where another chapter is open now",
      any("parked bullet" in i["text"] for i in groups[merged]["items"]))
check("and the open sitting reads the live handoff stamped with its chapter",
      any("unique up to isomorphism" in i["text"]
          for i in groups["courses/Fields@live"]["items"]))
check("an item says where it came from",
      [i["detail"] for i in groups[merged]["items"] if i["kind"] == "handoff"]
      == ["Where this got to"])
check("items carry nothing but their id, sitting, kind, text and detail",
      all(sorted(i) == sorted(sittings.PUBLIC)
          for g in everything["groups"] for i in g["items"]))
again = sittings.items(base, ids)
check("and the same picks give the same ids, so a tick survives the round trip",
      [i["id"] for g in again["groups"] for i in g["items"]]
      == [i["id"] for g in everything["groups"] for i in g["items"]])

# ---------------------------------------------------------------------------
# an id, never a path
# ---------------------------------------------------------------------------
hostile = ["../../etc@passwd", "courses/Fields@../../x", "nope@live",
           "courses/Fields@live/../..", "", None, 7]
check("a pick that is not a row is dropped, whatever it looks like",
      sittings.items(base, hostile)["groups"] == [])
check("and one that is, among them, is still honoured",
      [g["sitting"] for g in
       sittings.items(base, hostile + [merged])["groups"]] == [merged])
gathered, _ = sittings.gather(base, [merged])
check("an item id that is not one of them ticks nothing",
      sittings.ticked(gathered, ["../x", "0123456789", "zz"]) == [])

# ---------------------------------------------------------------------------
# the host, the brief, the figures and the fence
# ---------------------------------------------------------------------------
proj_groups, _ = sittings.gather(base, ["research/Proj@" + p1, merged])
want = [i["id"] for g in proj_groups for i in g["items"]]
picked = sittings.ticked(proj_groups, want)
check("the host is the workspace holding the most ticked items",
      sittings.host_for(picked) == "research/Proj")
tie = sittings.ticked(proj_groups, [proj_groups[1]["items"][0]["id"],
                                    proj_groups[0]["items"][0]["id"]])
check("and a tie goes to the one listed first",
      sittings.host_for(tie) == "research/Proj")
# A FENCED WORKSPACE HOSTS ANY DECK THAT TOUCHES IT, however little of it was
# ticked: the .tex is tracked, and the push's PHI scan reads only what is under
# a fenced root.
lean = sittings.ticked(proj_groups, [proj_groups[0]["items"][0]["id"]]
                       + [i["id"] for i in proj_groups[1]["items"]])
check("a deck ticking one thing from a fenced workspace and many from an open "
      "one is written in the fenced one",
      len(lean[1]["items"]) > len(lean[0]["items"])
      and lean[1]["ws"] == "courses/Fields"
      and sittings.host_for(lean) == "research/Proj"
      and sittings.mixed_fences(lean) == "")
two = [{"ws": "research/A", "row": {"fenced": ["phi"]}, "items": [1]},
       {"ws": "research/B", "row": {"fenced": ["data"]}, "items": [1, 2]}]
check("and ticks from two fenced workspaces are refused, in a sentence",
      "research/A and research/B" in sittings.mixed_fences(two))
open_only = [{"ws": "courses/X", "row": {"fenced": []}, "items": [1]},
             {"ws": "courses/Y", "row": {"fenced": []}, "items": [1, 2]}]
check("with no fence in play, the most ticked items still decide",
      sittings.host_for(open_only) == "courses/Y"
      and sittings.mixed_fences(open_only) == "")

# HALF-OPEN WINDOWS: a commit on the line between two sittings is the later
# one's, and the open sitting still owns a commit made this second.
a_row = {"start": 100, "end": 200, "live": False}
b_row = {"start": 200, "end": 300, "live": False}
on_line = [{"at": 200, "subject": "on the line"}]
check("a commit at the boundary is offered by one sitting, the later",
      sittings._in(on_line, a_row, set()) == []
      and len(sittings._in(on_line, b_row, set())) == 1
      and len(sittings._in([{"at": 300, "subject": "now"}],
                           dict(b_row, live=True), set())) == 1)

slug = sittings.deck_slug(proj)
check("the deck is named for the minute it was asked",
      re.match(r"^deck-\d{6}-\d{4}$", slug) is not None)
rec = sittings.write_brief(base, proj, slug, picked, wid="t0042",
                           host="research/Proj")
deck = os.path.join(proj, "writeups", slug)
brief = open(os.path.join(deck, sittings.BRIEF_MD), encoding="utf-8").read()
snaps = sorted(os.listdir(os.path.join(deck, "figures")))
check("a minute already taken gets -2",
      sittings.deck_slug(proj) == slug + "-2")
check("the brief lists what was ticked, with its source",
      "Weight the metric by importance" in brief
      and "AUC moves from 0.594 to 0.625." in brief)
check("and where to read more, by absolute path",
      os.path.join(proj, "live", "archive", p1) in brief)
check("it says which workspaces hold a fence, and to stay out",
      "research/Proj holds `phi/`: never open anything under it." in brief)
check("at most %d figures are copied, and the brief says how many were left out"
      % sittings.MOST_FIGURES,
      len(snaps) == sittings.MOST_FIGURES
      and re.search(r"\b\d+ more figures? belonged to these sittings", brief))
check("a figure written inside the window is copied, named for its workspace",
      "research-proj--%s.png" % roc_id in snaps)
check("so is one embedded in the sitting's cards, whenever it was written",
      "research-proj--%s.png" % embedded_id in snaps)
check("and one a ticked item names", any("named" in n for n in snaps))
check("the brief gives a figure's size, read off the PNG itself",
      "1800 x 1200" in brief)
check("one nobody claimed is only in the catalog",
      not any("-old-" in n for n in snaps)
      and results.ident("results/figs/old.png") in brief)
check("the brief says which workspaces the deck was made from",
      sorted(rec["workspaces"]) == ["courses/Fields", "research/Proj"])
check("with the command that fetches it",
      "board deckfig writeups/%s <workspace> <result id>" % slug in brief)
check("NOTHING UNDER phi/ OR data/ IS COPIED, CATALOGUED OR NAMED",
      not re.search(r"leak", brief) and not any("leak" in n for n in snaps))
paths_named = re.findall(r"`(/[^`]+)`", brief)
check("every path the brief names passes the fence",
      paths_named and all(not fenced.refused(os.path.relpath(p, base))
                          for p in paths_named))
ignore = open(os.path.join(deck, ".gitignore"), encoding="utf-8").read()
check("the deck's .gitignore keeps figures, the PDF and the brief out of a "
      "public repository", all(x in ignore.splitlines()
                               for x in ("figures/", "*.pdf", "_brief.*")))
check("the brief tells the tutor it plans the slides, one page per frame",
      "YOU PLAN THEM" in brief and "ONE PAGE PER FRAME" in brief
      and "aspectratio=169" in brief)
check("and _brief.json is what the server reads back",
      rec["slug"] == slug and rec["wid"] == "t0042"
      and json.load(open(os.path.join(deck, sittings.BRIEF_JSON)))["host"]
      == "research/Proj")
mention = [dict(g) for g in picked]
mention[0] = dict(mention[0], items=mention[0]["items"] + [
    {"id": "f" * 10, "kind": "handoff", "text": "the old curve, again"}])
_, _, cat, _ = sittings.figures_for(mention)
check("the catalog puts a figure the ticked items mention first, however old",
      cat and cat[0]["rec"]["file"] == "old.png"
      and cat[0]["rec"]["at"] < max(c["rec"]["at"] for c in cat))
library.forget()
check("the library does not offer the brief as a document",
      not [d for d in library.documents(proj) if d["stem"].startswith("_brief")])

# ---------------------------------------------------------------------------
# board deckfig
# ---------------------------------------------------------------------------
BOARD = os.path.join(ROOT, "bin", "board")


def deckfig(*args):
    p = subprocess.run([sys.executable, BOARD, "deckfig"] + list(args),
                       cwd=proj, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       env=dict(os.environ))
    return p.returncode, p.stdout.decode().strip(), p.stderr.decode().strip()


old_id = results.ident("results/figs/old.png")
code, out, _ = deckfig("writeups/" + slug, "research/Proj", old_id)
check("board deckfig copies a catalogued figure and prints the path to use",
      code == 0 and out == "figures/research-proj--%s.png" % old_id
      and os.path.isfile(os.path.join(deck, out)))
code, _, err = deckfig("writeups/" + slug, "research/Proj", "no-such-figure")
check("and refuses an id that workspace does not offer, in a sentence",
      code == 1 and "offers no figure" in err)
os.makedirs(os.path.join(proj, "writeups", "plain"), exist_ok=True)
code, _, err = deckfig("writeups/plain", "research/Proj", old_id)
check("and a folder that is not a deck made from sittings",
      code == 1 and "_brief.json" in err)
code, _, err = deckfig("live", "research/Proj", old_id)
check("and a folder outside writeups/",
      code == 1 and "writeups/" in err)
code, _, err = deckfig("writeups/" + slug, "research/Nowhere", old_id)
check("and a workspace this repository has not got",
      code == 1 and "not a workspace" in err)
os.remove(os.path.join(deck, out))
code, out2, _ = deckfig("writeups/" + slug, "research/Proj", "old")
check("a word from a file's name finds a figure the catalog did not list",
      code == 0 and out2 == "figures/research-proj--%s.png" % old_id)
code, _, err = deckfig("writeups/" + slug, "research/Proj", "fig")
check("and a word that matches several lists their ids instead of guessing",
      code == 1 and "matches" in err and err.count("fig") >= 3)
fonly_groups, _ = sittings.gather(base, [merged])
sittings.write_brief(base, proj, "deck-fonly", fonly_groups, wid="t0043")
code, _, err = deckfig("writeups/deck-fonly", "research/Proj", old_id)
check("and a workspace the deck was not made from is refused, even one with "
      "the figure", code == 1 and "made from courses/Fields" in err
      and not os.path.exists(os.path.join(proj, "writeups", "deck-fonly",
                                          "figures")))
shutil_rm_ = __import__("shutil").rmtree
shutil_rm_(os.path.join(proj, "writeups", "deck-fonly"))

# ---------------------------------------------------------------------------
# the routes, over real HTTP, with the board serving Fields
# ---------------------------------------------------------------------------
repo = course_repo.Repo(fields)
woken = []
spawn.wake_tutor = lambda r: woken.append(r) or True
worker = tikz.TikzWorker(repo)
worker.start()
board = hub.Hub(repo, worker)
board.payload = json.dumps(board.build())
sock = socket.socket()
sock.bind(("127.0.0.1", 0))
port = sock.getsockname()[1]
sock.close()
httpd = ThreadingHTTPServer(("127.0.0.1", port), handler.Handler)
httpd.daemon_threads = True
httpd.repo = repo
httpd.hub = board
threading.Thread(target=httpd.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:%d" % port


def post(path, body):
    req = urllib.request.Request(BASE + path, method="POST",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def tree(root):
    out = []
    for here, dirs, files in os.walk(root):
        out += [os.path.relpath(os.path.join(here, f), root) for f in files]
    return sorted(out)


status, body = post("/sittings", {})
check("POST /sittings is the listing",
      status == 200 and [r["id"] for r in body["sittings"]] == ids)
status, body = post("/sittings/items", {"picks": [merged, "../x"]})
check("POST /sittings/items answers for the picks that are rows",
      status == 200 and [g["sitting"] for g in body["groups"]] == [merged])
status, body = post("/sittings/deck", {"picks": [merged], "items": []})
check("a deck of nothing is refused by name",
      status == 400 and body.get("error") == "tick at least one thing")

# A START REFUSED OVER THERE WRITES NOTHING ANYWHERE.
real_cli = spawn.tutor_cli
spawn.tutor_cli = lambda args, timeout=30: (1, "claude is already on a mission "
                                                "in Proj")
shutil_rm = __import__("shutil").rmtree
shutil_rm(os.path.join(proj, "writeups"))
before = tree(os.path.join(proj, "live"))
status, body = post("/sittings/deck", {"picks": ["research/Proj@" + p1, merged],
                                       "items": want})
check("a refused start answers 409 with the words it came in",
      status == 409 and "already on a mission in Proj" in (body.get("error") or ""))
check("and nothing was written: no writeups/, no new live/ files",
      not os.path.exists(os.path.join(proj, "writeups"))
      and tree(os.path.join(proj, "live")) == before)

ran = []
spawn.tutor_cli = lambda args, timeout=30: (ran.append(list(args)) or
                                            (0, "claude starting in Proj"))
status, body = post("/sittings/deck", {"picks": ["research/Proj@" + p1, merged],
                                       "items": want})
spawn.tutor_cli = real_cli
check("an allowed one is asked for in the workspace holding the most of it",
      status == 200 and body.get("host") == "research/Proj"
      and ran and ran[-1] == ["agent", "start", "Proj", "--respawn"])
slug2 = body.get("slug") or ""
over = course_repo.Repo(proj)
with open(over.messages_path, encoding="utf-8") as fh:
    lines = [json.loads(l) for l in fh if l.strip()]
check("the host's inbox opens with a [writeup] line naming the brief",
      lines and lines[0]["text"].startswith("[writeup] ")
      and "writeups/%s/_brief.md" % slug2 in lines[0]["text"]
      and lines[0].get("signal") == "writeup")
check("which names the file the front door finds it by, exactly",
      "writeups/%s/%s.tex" % (slug2, slug2) in lines[0]["text"])
check("and a record says it is being written",
      os.path.isfile(os.path.join(proj, "live", "writeups",
                                  "%s.json" % body.get("id"))))
check("the brief is there before the turn is, carrying the ask's id",
      json.load(open(os.path.join(proj, "writeups", slug2,
                                  sittings.BRIEF_JSON)))["wid"] == body.get("id"))
check("the reply says where, in a sentence the sheet paints",
      "The tutor is writing it in Proj" in (body.get("detail") or ""))

# ---------------------------------------------------------------------------
# where the deck got to
# ---------------------------------------------------------------------------
writeups.forget()
check("the record reads as being written", writeups.state(proj, body["id"])
      == "writing")
status, got = post("/sittings/decks", {})
mine = [d for d in got.get("decks") or [] if d["slug"] == slug2]
check("the new deck is listed as being written",
      mine and mine[0]["state"] == "being written" and mine[0]["doc"] == "")
# The turn writes the .tex first and builds second -- and the writeup record
# freezes `done` on the first document to change, which is the .tex.
write(os.path.join(proj, "writeups", slug2, slug2 + ".tex"),
      "\\documentclass{beamer}\\title{What knn bought}\\begin{document}"
      "\\end{document}\n")
library.forget()
writeups.forget()
status, got = post("/sittings/decks", {})
mine = [d for d in got.get("decks") or [] if d["slug"] == slug2]
check("a .tex with no PDF yet is still being written, whatever the record froze",
      mine and mine[0]["state"] == "being written")


def quiet(folder, ago):
    for here, _, files in os.walk(folder):
        for n in files:
            os.utime(os.path.join(here, n), (time.time() - ago, time.time() - ago))


deckdir2 = os.path.join(proj, "writeups", slug2)
quiet(deckdir2, sittings.QUIET + 60)
status, got = post("/sittings/decks", {})
mine = [d for d in got.get("decks") or [] if d["slug"] == slug2]
check("a quiet deck whose ask is still unread in the inbox is still being "
      "written: the turn is queued, not over",
      mine and mine[0]["state"] == "being written")
# The daemon takes the ask -- `board inbox` marks it read -- and the turn ends.
with open(over.messages_path, encoding="utf-8") as fh:
    taken = [json.loads(l) for l in fh if l.strip()]
for m in taken:
    m["read"] = True
with open(over.messages_path, "w", encoding="utf-8") as fh:
    fh.write("".join(json.dumps(m) + "\n" for m in taken))
agent_path = os.path.join(proj, "live", "agent.json")
from tutorboard import machine                                   # noqa: E402
write(agent_path, json.dumps({"state": "working", "pid": os.getpid(),
                              "host": machine.node_name(), "agent": "claude",
                              "last_seen": time.time(),
                              "turn_signal": "writeup"}))
status, got = post("/sittings/decks", {})
mine = [d for d in got.get("decks") or [] if d["slug"] == slug2]
check("while a turn is working there, it is still being written",
      mine and mine[0]["state"] == "being written")
write(agent_path, json.dumps({"state": "listening", "pid": os.getpid(),
                              "host": machine.node_name(), "agent": "claude",
                              "last_seen": time.time()}))
status, got = post("/sittings/decks", {})
mine = [d for d in got.get("decks") or [] if d["slug"] == slug2]
check("once the turn is over and the deck has sat quiet, a .tex with no PDF "
      "did not land -- long before the two-hour ceiling",
      mine and mine[0]["state"] == "did not land")
check("and it says the deck was written but did not build",
      mine and "written but did not build" in mine[0]["why"])
os.utime(os.path.join(deckdir2, slug2 + ".tex"), None)
status, got = post("/sittings/decks", {})
mine = [d for d in got.get("decks") or [] if d["slug"] == slug2]
check("a deck whose source moved a moment ago is still being written",
      mine and mine[0]["state"] == "being written")
os.remove(agent_path)
write(os.path.join(proj, "writeups", slug2, slug2 + ".pdf"),
      b"%PDF-1.4\n" + b"%" * 40000 + b"\n%%EOF\n")
status, got = post("/sittings/decks", {})
mine = [d for d in got.get("decks") or [] if d["slug"] == slug2]
found = [d for d in library.documents(proj)
         if d["dir"] == "writeups/" + slug2 and d["stem"] == slug2]
check("its PDF makes it ready, with the library's own id for it",
      mine and mine[0]["state"] == "ready" and found
      and mine[0]["doc"] == found[0]["id"])
check("titled from the source the turn wrote",
      mine and mine[0]["title"] == "What knn bought")
stale = sittings.write_brief(base, proj, "deck-000101-0000", picked, wid="t9999")
path = os.path.join(proj, "writeups", "deck-000101-0000", sittings.BRIEF_JSON)
stale["at"] = time.time() - writeups.CEILING - 60
json.dump(stale, open(path, "w"))
status, got = post("/sittings/decks", {})
dead = [d for d in got.get("decks") or [] if d["slug"] == "deck-000101-0000"]
check("past the ceiling with no PDF it did not land",
      dead and dead[0]["state"] == "did not land")
check("and with no source either, it says the tutor never wrote it",
      dead and "without writing the deck" in dead[0]["why"])

# ---------------------------------------------------------------------------
# a deck hosted where the board is, and its ink
# ---------------------------------------------------------------------------
fields_groups, _ = sittings.gather(base, [merged])
fwant = [i["id"] for i in fields_groups[0]["items"]]
woken[:] = []
status, body = post("/sittings/deck", {"picks": [merged], "items": fwant})
check("a deck whose host is the board's own workspace wakes its tutor instead",
      status == 200 and body.get("host") == "courses/Fields" and woken)
fslug = body["slug"]
write(os.path.join(fields, "writeups", fslug, fslug + ".tex"),
      "\\documentclass{beamer}\\title{Rings}\\begin{document}\\end{document}\n")
write(os.path.join(fields, "writeups", fslug, fslug + ".pdf"),
      b"%PDF-1.4\n" + b"%" * 40000 + b"\n%%EOF\n")
write(os.path.join(fields, "writeups", "other", "other.tex"),
      "\\documentclass{article}\\title{Other}\\begin{document}\\end{document}\n")
library.forget()
fdoc = [d for d in library.documents(fields) if d["stem"] == fslug][0]
odoc = [d for d in library.documents(fields) if d["stem"] == "other"][0]
status, said = post("/library/feedback", {"document": fdoc["id"],
                                          "text": "Add the lattice figure."})
with open(repo.messages_path, encoding="utf-8") as fh:
    last = [json.loads(l) for l in fh if l.strip()][-1]["text"]
check("feedback on the deck is an ordinary library revision",
      status == 200 and last.startswith("[revise]"))
check("and its line points at the brief, says an addition is the feedback, "
      "and names board deckfig",
      "writeups/%s/_brief.md" % fslug in last and "ADDED is the feedback" in last
      and "board deckfig writeups/%s" % fslug in last)
status, said = post("/library/feedback", {"document": odoc["id"],
                                          "text": "Tighten it."})
with open(repo.messages_path, encoding="utf-8") as fh:
    last = [json.loads(l) for l in fh if l.strip()][-1]["text"]
check("while a document with no brief beside it gets the line it always did",
      "COMPOSED FROM SITTINGS" not in last and "_brief.md" not in last)
check("the brief sentence is only there when it is asked for",
      sense.revise_sense("a.pdf", "f.md") ==
      sense.REVISE_SENSE % ("a.pdf", "f.md") + sense.MEASURE_SENSE
      + sense.RULE_SENSE
      and "_brief.md" in sense.rework_sense("a.pdf", "f.md", "x" * 30,
                                            brief="writeups/d/_brief.md"))


def ink(key, sent=False):
    stem = writing_route.ann_file(key)
    write(os.path.join(repo.notes, stem + ".json"),
          json.dumps({"card": key, "sent": sent,
                      "strokes": [{"p": [[0.1, 0.1], [0.2, 0.2]]}]}))
    write(os.path.join(repo.notes, stem + ".png"), b"\x89PNG\r\n\x1a\n")


ink("doc/%s/p2" % fdoc["id"])
ink("doc/%s/p3" % fdoc["id"])
library.forget()
first = library.write_note(repo, fdoc["id"], "")
check("the first round carries both marked slides",
      first.get("ok") and first.get("marks") == 2)
check("and records them as delivered",
      all(lesson_notes.load_notes_sent(repo).get("doc/%s/p%d" % (fdoc["id"], n))
          for n in (2, 3)))
# THE ROUND CAME BACK: the revision writes `## What was changed` under the note.
with open(first["path"], "a", encoding="utf-8") as fh:
    fh.write("\n## What was changed\n\nThe lattice figure is on slide 3.\n")
ink("doc/%s/p3" % fdoc["id"])            # slide 3 drawn on again
library.forget()
st = [d for d in library.status(repo)["documents"] if d["id"] == fdoc["id"]][0]
check("once the round lands, the slide whose ink it delivered is wiped, "
      "and the slide drawn on since is all that is on the deck",
      st["marks"]["pages"] == 1 and st["marks"]["waiting"] == 1)
p2 = os.path.join(repo.notes, writing_route.ann_file("doc/%s/p2" % fdoc["id"]))
p3 = os.path.join(repo.notes, writing_route.ann_file("doc/%s/p3" % fdoc["id"]))
check("its record and its picture are gone from the drawer",
      not os.path.exists(p2 + ".json") and not os.path.exists(p2 + ".png"))
check("while ink drawn after the round is kept for the next one",
      os.path.exists(p3 + ".json"))
view = library.ink(repo, fdoc)
check("and the reader is handed only the ink that is left",
      list(view) == ["doc/%s/p3" % fdoc["id"]])
second = library.write_note(repo, fdoc["id"], "")
text = open(second["path"], encoding="utf-8").read()
check("a second round leaves out a slide whose ink already went, and carries "
      "the one drawn on since",
      second.get("ok") and second.get("marks") == 1
      and "page 3" in text and "page 2" not in text)

# THE SECOND ROUND DID NOT COME BACK -- no `What was changed`, no PDF rebuilt
# after it. A retry is a tap: every mark goes again, and an empty note is not
# refused while ink is on the slides.
os.utime(os.path.join(fields, "writeups", fslug, fslug + ".pdf"),
         (time.time() - 3600, time.time() - 3600))
library.forget()
st = [d for d in library.status(repo)["documents"] if d["id"] == fdoc["id"]][0]
check("after a round that did not land, its ink is kept and waiting again",
      st["marks"]["waiting"] == 1 and os.path.exists(p3 + ".json"))
third = library.write_note(repo, fdoc["id"], "")
check("and the retry carries all of it rather than being refused",
      third.get("ok") and third.get("marks") == 1)
check("a PDF rebuilt after the note counts as the round coming back",
      (os.utime(os.path.join(fields, "writeups", fslug, fslug + ".pdf"), None)
       or True) and library.last_round_landed(fields, fdoc))

# THE INK IS DELIVERED WHEN THE REVISION IS ASKED, not when the note is written.
from tutorboard.server.routes import library as library_route   # noqa: E402
real_revise = library_route._revise
library_route._revise = lambda *a, **k: {"revise": "board", "asked": False,
                                         "detail": "nothing could be asked"}
ink("doc/%s/p4" % fdoc["id"])
library.forget()
status, said = post("/library/feedback", {"document": fdoc["id"], "text": ""})
library_route._revise = real_revise
check("a note whose revision could not be asked leaves its ink undelivered",
      status == 200 and said.get("asked") is False
      and not lesson_notes.load_notes_sent(repo).get("doc/%s/p4" % fdoc["id"])
      and "keys" not in said)
status, said = post("/library/feedback", {"document": fdoc["id"], "text": ""})
check("while one that was asked records it as delivered",
      status == 200 and said.get("asked") is True
      and lesson_notes.load_notes_sent(repo).get("doc/%s/p4" % fdoc["id"]))

# A DOCUMENT NOT MADE FROM SITTINGS keeps the library's old rule: all its ink,
# every round.
ink("doc/%s/p1" % odoc["id"])
library.forget()
library.write_note(repo, odoc["id"], "")
again = library.write_note(repo, odoc["id"], "")
check("a document with no brief beside it sends its ink every round, as before",
      again.get("ok") and again.get("marks") == 1)

# AFTER THE MEETING: THE INK IS A DIRECTION. `/library/direction` writes one
# proposal turn in this workspace and never a revision.
library.forget()
with open(repo.messages_path, encoding="utf-8") as fh:
    before = sum(1 for l in fh if l.strip())
status, said = post("/library/direction", {"document": fdoc["id"], "text": ""})
check("with nothing marked and nothing said, a direction is refused",
      status == 400 and not said.get("ok"))
ink("doc/%s/p9" % fdoc["id"])
library.forget()
status, said = post("/library/direction",
                    {"document": fdoc["id"],
                     "text": "Dr. Paulus's idea, not confirmed yet."})
with open(repo.messages_path, encoding="utf-8") as fh:
    lines = [json.loads(l) for l in fh if l.strip()]
last = lines[-1]["text"]
check("marks sent as a direction wake ONE proposal turn",
      status == 200 and said.get("ok") and len(lines) == before + 1
      and last.startswith("[direction] ") and not last.startswith("[revise]"))
check("which is told it proposes and does not apply, names the page, and "
      "carries their words",
      "YOU ARE PROPOSING, NOT APPLYING" in last and "page 9" in last
      and "not confirmed yet" in last and "Do not revise the document" in last)
check("with a picture of the marks copied under live/, beside nothing tracked",
      said.get("images") and said["images"][0].startswith("live/directions/")
      and os.path.isfile(os.path.join(repo.root, said["images"][0])))
check("and the ink is recorded as delivered, so a later fix does not carry it",
      lesson_notes.load_notes_sent(repo).get("doc/%s/p9" % fdoc["id"]))

# A RE-SAVE THAT ONLY ATTACHES A PICTURE keeps ink delivered; a changed page
# does not.
p9 = "doc/%s/p9" % fdoc["id"]
same = json.load(open(os.path.join(repo.notes, writing_route.ann_file(p9) + ".json")))
post("/annotate/save", {"card": p9, "strokes": same["strokes"], "send": False,
                        "png": ""})
check("re-saving the same strokes leaves them delivered",
      lesson_notes.load_notes_sent(repo).get(p9))
post("/annotate/save", {"card": p9, "strokes": same["strokes"] + same["strokes"],
                        "send": False, "png": ""})
check("while drawing on the page again puts it back in the next round",
      not lesson_notes.load_notes_sent(repo).get(p9))

httpd.shutdown()
print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a deck from any sittings, planned by the tutor, corrected with ink")
