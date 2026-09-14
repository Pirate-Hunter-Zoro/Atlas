#!/usr/bin/env python3
"""Meeting notes: assembled from what a person wrote, never invented.

    "have functionality to produce 'meeting notes' for me with in-built links
     that will take me to those results/code/sections of my board writing to
     explain those notes."

This is the first thing that SPENDS the address grammar and the written map, and
the checks are about the ways that spending can quietly go wrong.

  * NOTHING IN A NOTE IS GENERATED PROSE. Every sentence comes out of a commit
    subject somebody wrote, a plan step they typed, or a box they named. A note
    whose sentences were invented has to be verified before it can be used,
    which is worse than having no note at all.
  * A CLAIM CARRIES THE ADDRESS OF THE THING IT IS ABOUT, in the §2.1 grammar
    and spelled the way `address.js` spells it. Two spellers is two sets of
    links that resolve slightly differently.
  * A LINK IS REAL OR IT IS NOT A LINK. With no board to link through, the
    address is written out as text rather than wrapped in something that looks
    clickable and is inert -- which is the same failure the grammar exists to
    prevent, one layer out.
  * A WORKSPACE WITH NOTHING TO SAY IS LEFT OUT. Eleven headings with nothing
    under ten of them is the shape of a report nobody reads, and it buries the
    one that moved.
  * THE SCOPE IS THE WORKSPACE. There is one repository now and every
    workspace's history runs through the same log; a note about Galois Theory
    that lists PSYCH-ASR's afternoon is a note nobody can trust about either.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tutorboard import atlas, meeting                                 # noqa: E402
from tutorboard.course import document, plan                          # noqa: E402
from tutorboard.course import map as course_map                       # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def git(base, *args):
    return subprocess.run(["git"] + list(args), cwd=base,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          timeout=30).stdout.decode("utf-8", "replace")


PAD = "\n" + ("# padding, to clear the size floor on a walkable file\n" * 12)

TODO = """PROJECT — REMAINING WORK

>>> NEXT ACTION <<<
  STEP 1. CUT THE SEAM THE TYPIST NEEDS. (Added 2026-09-09.)
    It lives in psych_asr/asr/align.py and nothing else can start until it does.
  STEP 2. RUN THE GRID.
    Forty cells, thirteen jobs.
"""

TODO_AFTER = """PROJECT — REMAINING WORK

>>> NEXT ACTION <<<
  STEP 2. RUN THE GRID.
    Forty cells, thirteen jobs.
"""

base = tempfile.mkdtemp(prefix="tutor-meeting-")
try:
    # A repository shaped like Atlas: families, and workspaces under them.
    write(os.path.join(base, "atlas.json"), json.dumps(
        {"families": [{"id": "research", "name": "Research"},
                      {"id": "courses", "name": "Courses"}]}))
    proj = os.path.join(base, "research", "PSYCH-ASR")
    quiet = os.path.join(base, "courses", "Galois-Theory")
    for r in (proj, quiet):
        write(os.path.join(r, "tutorboard.json"), "{}\n")
        os.makedirs(os.path.join(r, "live"), exist_ok=True)
    write(os.path.join(proj, "psych_asr", "asr", "align.py"),
          "def align():\n    return 1" + PAD)
    write(os.path.join(proj, "planning", "TODO.txt"), TODO)
    write(os.path.join(proj, "README.md"), "# P\n\nThe plan is planning/TODO.txt\n")
    write(os.path.join(quiet, "README.md"), "# G\n")

    git(base, "init", "-q", "-b", "main")
    git(base, "config", "user.email", "t@example.com")
    git(base, "config", "user.name", "Tester")
    git(base, "add", "-A")
    git(base, "commit", "-q", "-m", "everything, to start from")

    # AFTER the first commit, not five seconds before it. git compares whole
    # seconds, so the sleeps are what make "since" mean anything at all here.
    time.sleep(1.1)
    since = time.time()
    time.sleep(1.1)

    # Work lands in ONE workspace, and the plan loses a step.
    write(os.path.join(proj, "psych_asr", "asr", "align.py"),
          "def align():\n    return 2" + PAD)
    write(os.path.join(proj, "planning", "TODO.txt"), TODO_AFTER)
    git(base, "add", "-A")
    git(base, "commit", "-q", "-m", "the seam is cut, and the stopwatch is its own pass")

    atlas.forget()
    os.environ["TUTORBOARD_COURSES"] = base

    # --- when ------------------------------------------------------------
    check("a date is a date", meeting.resolve_since("2026-09-01")[0] is not None)
    check("a span is a span", meeting.resolve_since("2w")[0] is not None)
    check("a weekday is the most recent one, and today does not count",
          meeting.resolve_since("monday")[0] < time.time())
    check("`last` with no earlier notes says so rather than guessing",
          meeting.resolve_since("last", base)[0] is None)
    for bad in ("", "wat", "0d", "9999d", "2026-13-40"):
        check("refused: %r" % bad, meeting.resolve_since(bad, base)[0] is None)

    # --- the scope is the workspace ---------------------------------------
    got = meeting.landed(base, "research/PSYCH-ASR", since)
    check("a commit that touched this workspace is in its block",
          len(got) == 1 and "the seam is cut" in got[0]["subject"])
    check("and the same commit is NOT in a workspace it did not touch",
          meeting.landed(base, "courses/Galois-Theory", since) == [])

    files = meeting.touched(base, "research/PSYCH-ASR", since)
    check("the files it changed are named relative to the workspace",
          "psych_asr/asr/align.py" in files)

    # --- what closed, read out of the deletion ----------------------------
    gone = meeting.closed(base, "research/PSYCH-ASR", proj, since)
    check("a plan step that was DELETED is reported as closed",
          any("SEAM" in t.upper() for t in gone))
    check("and a step still in the plan is not",
          not any("GRID" in t.upper() for t in gone))

    # --- what it means: the written map, spent ----------------------------
    drawn = {"version": 1, "title": "Stage 1",
             "nodes": [{"id": "stopwatch", "name": "the stopwatch",
                        "does": "Puts a start and an end on every word.",
                        "files": ["psych_asr/asr/align.py"]},
                       {"id": "grid", "name": "the grid",
                        "files": ["psych_asr/asr/align.py"],
                        "blockedBy": ["stopwatch"]}]}
    problems, _ = course_map.write_written(proj, drawn)
    check("the worked example's map is valid", not problems)
    course_map._cache.clear()
    plan._cache.clear()

    means = meeting.meaning(proj, "research/PSYCH-ASR", files)
    check("a changed file is reported by the NAME THE PERSON GAVE IT",
          any(n["name"] == "the stopwatch" for n in means))
    check("and the box carries its own address",
          all(n["link"].startswith("#/w/research/PSYCH-ASR/node/")
              for n in means))

    stuck = meeting.blocked(proj, "research/PSYCH-ASR")
    check("what is blocked is named, and what it waits on is named too",
          any(n["name"] == "the grid" and n["on"] == ["the stopwatch"]
              for n in stuck))

    # --- the grammar, once ------------------------------------------------
    check("an address is spelled the way the grammar spells it",
          meeting._address("research/PSYCH-ASR", "node", node="typist")
          == "#/w/research/PSYCH-ASR/node/typist")
    check("and a workspace with a space in its name is encoded, never split",
          meeting._address("courses/To Turn In") == "#/w/courses/To%20Turn%20In")
    check("a workspace outside every family cannot be addressed at all",
          meeting._address("loose") == "")

    # --- the note -----------------------------------------------------------
    rec = meeting.build(base, since, "the test", make_pdf=False)
    check("a note is written", rec.get("ok"))
    body = rec["markdown"]
    check("only the workspace that moved is in it",
          "PSYCH-ASR" in body and "Galois-Theory" not in body)
    check("the person's own commit subject is the sentence",
          "the seam is cut" in body)
    check("the closed step is reported as closed",
          "Closed" in body and "SEAM" in body.upper())
    check("what moved is said in the map's words",
          "the stopwatch" in body)
    check("what is blocked says what it waits on",
          "the grid" in body and "waits on the stopwatch" in body)
    check("what is next is the plan's own next step, not a re-ordering",
          "RUN THE GRID" in body.upper())

    # NO BOARD IS RUNNING in this fixture, so there is nothing to link through.
    check("with no board to link through, an address is TEXT, not a dead link",
          "](" not in body and "#/w/research/PSYCH-ASR/node/" in body)
    check("and the note says why, once",
          "written out rather than linked" in body)

    # With a board, the links are real and absolute.
    write(os.path.join(proj, "live", ".board.json"), json.dumps(
        {"urls": ["http://127.0.0.1:9171/", "http://box.example:9171/"]}))
    rec2 = meeting.build(base, since, "the test", make_pdf=False)
    check("with a board, every link is absolute",
          "](http://box.example:9171#/w/research/PSYCH-ASR" in rec2["markdown"])
    check("and the loopback URL is never the one offered",
          "127.0.0.1" not in rec2["markdown"])

    # --- a period in which nothing happened ---------------------------------
    rec3 = meeting.build(base, time.time() + 60, "the future", make_pdf=False)
    check("a period with nothing in it says so in one line, not in eleven "
          "empty headings",
          "Nothing landed" in rec3["markdown"] and "##" not in rec3["markdown"])
    check("and a standing blockage is not news in a period nothing happened in",
          "the grid" not in rec3["markdown"])

    # --- numbered, never stamped -------------------------------------------
    check("notes are numbered v1, v2, v3",
          rec["name"].endswith("-v1") and rec2["name"].endswith("-v2"))

    # --- a URL survives being typeset --------------------------------------
    # `#` IS A MACRO PARAMETER CHARACTER. A link left in place through the
    # escape pass came out as `\href{\#/w/...}`, which is not a mangled link --
    # it is a fatal LaTeX error and NO PDF AT ALL. Every address is a fragment,
    # so every one of them hit this.
    tex = document.md_to_tex("see [the box](http://x.example:9/#/w/a/b_c) now")
    check("a fragment in a link survives the TeX escape pass",
          "\\href{http://x.example:9/\\#/w/a/b_c}" in tex)
    check("and the link TEXT is still escaped normally",
          document.md_to_tex("[a_b](http://x/#q)").count("\\_") == 1)

    # --- one workspace only -------------------------------------------------
    one = meeting.build(base, since, "the test",
                        want=["courses/Galois-Theory"], make_pdf=False)
    check("asking for one workspace gets that one and no other",
          "PSYCH-ASR" not in one["markdown"])
    none = meeting.build(base, since, "the test", want=["nope/nothing"],
                         make_pdf=False)
    check("asking for a workspace that is not here says so",
          not none.get("ok") and "workspaces in this repository" in none["detail"])

finally:
    os.environ.pop("TUTORBOARD_COURSES", None)
    atlas.forget()
    shutil.rmtree(base, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a meeting note is assembled from what somebody wrote, and every claim "
      "carries its address")
