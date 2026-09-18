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

And then it became a DECK, which adds four rules of its own:

  * ONE DECK, AT ONE PATH. Making a new one REPLACES the one before it. The
    history is `git log`'s, which cannot go stale and costs the tree nothing.
  * ONE FRAME PER WORKSPACE AND ONE PAGE PER FRAME. The page a mark is on is
    how the mark finds its workspace, so a frame that quietly became two pages
    would route somebody's mentor's suggestion into the wrong project.
  * A MARK ON A SLIDE IS DIRECTION, NOT FEEDBACK. It must not write a feedback
    file, must not archive anything, and must not replace any assistant --
    every one of those is what `/library/feedback` does, and it is the obvious
    wrong next line of code.
  * AND OLD INK GOES WITH THE OLD DECK. This is the one document in the system
    where a mark has no meaning once it is sent: it was consumed into a
    direction, and next week page 4 is a different project.
"""

import json
import os
import shutil
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
from tutorboard import atlas, direction, meeting, proposals           # noqa: E402
from tutorboard.course import document, plan                          # noqa: E402
from tutorboard.course import map as course_map                       # noqa: E402
from tutorboard.course import repo as course_repo                     # noqa: E402
from tutorboard import tex as board_tex                               # noqa: E402
from tutorboard.server import handler, hub, spawn, tikz               # noqa: E402
from tutorboard.server.routes import writing as writing_route         # noqa: E402

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

    # --- one deck, at one path ---------------------------------------------
    # NOT `-v1, -v2, -v3`, which is what every other document here is numbered
    # with. Asked for outright: *"we're also not gonna save every presentation
    # ... if I elect to make a new one, then that new one REPLACES the old
    # one."* The history is `git log`'s, which cannot go stale.
    check("the deck has one name, not a version",
          rec["name"] == rec2["name"] == meeting.STEM)

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


    # -----------------------------------------------------------------------
    # THE DECK
    # -----------------------------------------------------------------------
    # A second workspace moves, so there are two frames and a mark can be shown
    # to reach the right one rather than the only one.
    write(os.path.join(quiet, "notes.tex"), "x" + PAD)
    git(base, "add", "-A")
    git(base, "commit", "-q", "-m",
        "Galois: 4.11 typeset, and the pages behind it filed")

    # LaTeX is not on every machine, and a suite that needs it to run at all
    # is a suite that gets skipped whole. The assembly is checked either way;
    # only the compile and the page count are held back.
    HAVE_TEX = board_tex.have_tex()
    deck = meeting.build(base, since, "the test", make_pdf=HAVE_TEX)
    check("the deck is written", deck.get("name") == meeting.STEM)
    tex = open(os.path.join(base, deck["tex"]), encoding="utf-8").read()
    check("it is a PRESENTATION and not an article",
          "{beamer}" in tex and "{article}" not in tex)
    check("one title frame, then one frame per workspace that moved",
          tex.count("\\begin{frame}") == 1 + len(deck["workspaces"])
          and len(deck["workspaces"]) == 2)

    # EVERY LINE ON A FRAME TRACES TO SOMETHING SOMEBODY WROTE. This is the
    # property the whole module exists for, and the one a model writing the
    # deck would cost. The labels -- Closed, Next, Blocked -- are this file's
    # own furniture; everything else on a bullet has to be a commit subject, a
    # plan step, or a box somebody named.
    SOURCES = ["the seam is cut", "Galois: 4.11 typeset",
               "CUT THE SEAM", "RUN THE GRID",
               "the stopwatch", "the grid",
               "Puts a start and an end on every word"]
    invented = []
    for line in tex.splitlines():
        line = line.strip()
        if not line.startswith("\\item"):
            continue
        if "and 0 more" in line or "\\ldots and" in line:
            continue
        if not any(src in line for src in SOURCES):
            invented.append(line)
    check("nothing on a frame was invented: every bullet is somebody's own "
          "sentence", not invented)
    check("and a claim on a frame carries the address of the thing it is about",
          "/w/research/PSYCH-ASR/node/stopwatch" in tex)

    check("and the page map says which frame is whose",
          deck["pages"] == {"2": "research/PSYCH-ASR",
                            "3": "courses/Galois-Theory"})

    pages = 0
    if HAVE_TEX and shutil.which("pdfinfo"):
        check("the deck typesets", deck.get("ok") and deck.get("pdf"))
        got = subprocess.run(["pdfinfo", os.path.join(base, deck["pdf"] or "")],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, timeout=20)
        for ln in got.stdout.decode("utf-8", "replace").splitlines():
            if ln.startswith("Pages:"):
                pages = int(ln.split()[1])
        # ONE PAGE PER FRAME, and this is not a typographic nicety. The page a
        # mark is on is how the mark finds its workspace; a frame that spilled
        # onto a second page would route a mentor's suggestion into the wrong
        # project.
        check("every frame is exactly one page",
              pages == 1 + len(deck["workspaces"]))
    else:
        print("skip  no LaTeX or no pdfinfo here, so the compile and the page "
              "count are not checked")

    want_files = ["meeting.json", "meeting.tex"]
    if deck.get("pdf"):
        want_files = ["meeting.json", "meeting.pdf", "meeting.tex"]
    left = sorted(n for n in os.listdir(os.path.join(base, meeting.OUT_DIR))
                  if os.path.isfile(os.path.join(base, meeting.OUT_DIR, n)))
    check("making a new one leaves exactly one deck on disk",
          left == want_files)
    check("and the deck can be read back off disk with its page map",
          (meeting.deck(base) or {}).get("pages") == deck["pages"])
    # ONE PATH MEANS THE RENDERING AND THE PAGE MAP MUST NOT DISAGREE. A build
    # that produces no PDF leaves none behind: last week's rendering beside
    # this week's page map is a slide about one project whose marks route to
    # another.
    meeting.build(base, since, "the test", make_pdf=False)
    check("a build with no PDF leaves no stale one beside the new source",
          not os.path.isfile(os.path.join(base, meeting.OUT_DIR,
                                          meeting.STEM + ".pdf"))
          and not (meeting.deck(base) or {}).get("has_pdf"))
    deck = meeting.build(base, since, "the test", make_pdf=HAVE_TEX)

    # `--print` ASSEMBLES AND TOUCHES NOTHING. There is one deck at one path,
    # so a run that wrote the source without building the PDF would leave a
    # `.tex` and a `.pdf` beside each other that are not the same deck -- and
    # would throw away the marks on the one still on the glass, for a command
    # that was asked only to show its text.
    was = sorted(os.listdir(os.path.join(base, meeting.OUT_DIR)))
    text = meeting.build(base, since, "the test", make_pdf=False, write=False)
    check("asking only for the text of it writes nothing at all",
          text.get("markdown")
          and sorted(os.listdir(os.path.join(base, meeting.OUT_DIR))) == was)

    # -----------------------------------------------------------------------
    # THE ROUTES, over real HTTP
    # -----------------------------------------------------------------------
    # The board serving is the QUIET one, and the marked slide is the other
    # workspace's. That is the real case: the front door is served by whichever
    # board is answering, and a proposal has to land in the project the slide
    # is about rather than in the one that happened to serve the page.
    woken = []
    spawn.wake_tutor = lambda r: woken.append(r.root) or True
    spawn.fresh_tutor = lambda root, course: fails.append(
        "an assistant was replaced by a mark on a slide")

    serving = course_repo.Repo(quiet)
    worker = tikz.TikzWorker(serving)
    worker.start()
    board = hub.Hub(serving, worker)
    board.payload = json.dumps(board.build())

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler.Handler)
    httpd.daemon_threads = True
    httpd.repo = serving
    httpd.hub = board
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    BASE = "http://127.0.0.1:%d" % port

    def post(path, body):
        req = urllib.request.Request(
            BASE + path, method="POST",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def get(path):
        try:
            with urllib.request.urlopen(BASE + path, timeout=60) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    try:
        # --- WHICH PROJECTS, with what each one has to report ---------------
        status, body = post("/notes/what", {"since": "30d"})
        check("the sheet can ask what each workspace has to report",
              status == 200 and body.get("ok"))
        by_id = dict((w["id"], w) for w in body.get("workspaces") or [])
        check("every workspace is offered, whether or not it moved",
              set(by_id) == {"research/PSYCH-ASR", "courses/Galois-Theory"})
        check("and each one says what it has, not just its name",
              by_id["research/PSYCH-ASR"]["commits"] >= 1
              and by_id["research/PSYCH-ASR"]["closed"] == 1
              and by_id["research/PSYCH-ASR"]["files"] >= 1
              and by_id["research/PSYCH-ASR"]["moved"] is True)
        status, body = post("/notes/what", {"since": "not-a-period"})
        check("a period nobody can read is refused by the sheet",
              status == 400 and not body.get("ok"))

        # --- `want` REACHES `build` FROM THE ROUTE --------------------------
        # It always could; nothing ever passed it, so the capability was
        # written, reachable from a terminal and invisible from the glass.
        status, body = post("/notes", {"since": "30d",
                                       "want": ["courses/Galois-Theory"]})
        check("asking for one project from the route gets that one only",
              status == 200 and body.get("workspaces") == ["courses/Galois-Theory"])
        status, body = post("/notes", {"since": "30d", "want": ["nope/nothing"]})
        check("and a name that is not a workspace is refused BY NAME",
              "workspaces in this repository" in (body.get("detail") or ""))

        # Back to a deck with both frames on it, which is what the marks need.
        status, body = post("/notes", {"since": "30d"})
        check("a deck built from the route covers both",
              status == 200 and len(body.get("workspaces") or []) == 2)
        status, body = get("/meeting/deck.json")
        check("the reader is told which slide is about which project",
              body.get("ok") and body.get("pages", {}).get("2")
              == "research/PSYCH-ASR")

        # --- READING IT, THROUGH THE LIBRARY'S OWN MACHINERY ---------------
        status, body = get("/meeting/view")
        if body.get("ok"):
            check("the reader gets a page per frame, and the marks with them",
                  len(body.get("pages") or []) == (pages or len(body["pages"]))
                  and "ink" in body and body.get("pages_of", {}).get("2"))
        else:
            print("skip  %s" % (body.get("detail") or "the pages could not be "
                                                      "drawn here"))

        # --- A MARK ON A SLIDE IS DIRECTION --------------------------------
        def ink(page, strokes=3, png=True):
            """Marks on one slide, exactly as `/annotate/save` stores them."""
            key = "doc/%s/p%d" % (meeting.ANN_IDENT, page)
            stem = writing_route.ann_file(key)
            with open(os.path.join(serving.notes, stem + ".json"), "w",
                      encoding="utf-8") as fh:
                json.dump({"card": key, "sent": False,
                           "strokes": [{"p": [[0.1, 0.1], [0.2, 0.3]]}] * strokes},
                          fh)
            if png:
                with open(os.path.join(serving.notes, stem + ".png"), "wb") as fh:
                    fh.write(b"\x89PNG\r\n\x1a\n")
            return key

        target = course_repo.Repo(proj)
        before = os.path.getmtime(target.state_path) \
            if os.path.exists(target.state_path) else 0
        archived_before = len(os.listdir(target.archive))

        key = ink(2)
        status, body = post("/meeting/direction", {})
        check("marks on a slide are accepted as direction",
              status == 200 and body.get("ok"))
        check("and they go to the workspace THAT SLIDE IS ABOUT, not to the "
              "board that served it",
              [s["workspace"] for s in body.get("sent") or []]
              == ["research/PSYCH-ASR"])

        said = ""
        with open(target.messages_path, encoding="utf-8") as fh:
            said = fh.read()
        check("a turn lands in that workspace, as the student's own",
              '"from": "student"' in said and "[direction]" in said)
        check("it is told to PROPOSE and not to apply",
              "YOU ARE PROPOSING, NOT APPLYING" in said
              and "board write" in said)
        check("and it is handed the picture of what they drew",
              "meetings/marks/p2.png" in said)
        check("the picture is beside the deck, where the turn can open it",
              os.path.isfile(os.path.join(base, "meetings", "marks", "p2.png")))

        # THE TRAP, AND IT IS THE WHOLE POINT OF THE ROUTE. Everything about
        # the reader makes `/library/feedback` the obvious next line of code,
        # and it writes a feedback file and wakes a turn to FIX THE SLIDES.
        feedback = []
        for here, dirs, names in os.walk(base):
            if os.path.basename(here) == "feedback":
                feedback += [os.path.join(here, n) for n in names]
        check("no feedback file is written anywhere: the marks are not about "
              "the deck", not feedback)
        check("no direction is applied", not os.path.isfile(direction.path(proj)))
        check("nothing is archived", len(os.listdir(target.archive))
              == archived_before)
        check("the sitting on that board is left alone",
              (os.path.getmtime(target.state_path)
               if os.path.exists(target.state_path) else 0) == before)
        check("and the workspace that was marked is the one woken",
              proj in woken)

        # The marks are recorded as delivered, so yesterday's ink does not
        # demand a decision every time anything is sent.
        rec_path = os.path.join(serving.notes,
                                writing_route.ann_file(key) + ".json")
        check("the marks are recorded as having gone somewhere",
              json.load(open(rec_path, encoding="utf-8")).get("sent") is True)

        # --- A MARK ON THE TITLE SLIDE BELONGS TO NOBODY --------------------
        meeting.clear_ink(serving)
        ink(1)
        status, body = post("/meeting/direction", {})
        check("a mark on the title slide is refused, by name, rather than "
              "guessed at", status == 400 and not body.get("ok")
              and "nowhere to go" in (body.get("detail") or ""))

        # --- THE INK GOES WITH THE DECK IT WAS DRAWN ON ---------------------
        # The one document here where an old mark has no meaning at all: it was
        # consumed into a direction the moment it was sent, and the new deck has
        # a different project on page 4.
        meeting.clear_ink(serving)
        ink(2)
        check("there is ink on the deck", len(meeting.ink_keys(serving)) == 1)
        status, body = post("/notes", {"since": "30d"})
        check("replacing the deck clears every mark on it",
              status == 200 and not meeting.ink_keys(serving))
        check("and the pictures of those marks go with them",
              not os.path.isdir(os.path.join(base, "meetings", "marks"))
              or not os.listdir(os.path.join(base, "meetings", "marks")))
        check("sending marks nobody made says so rather than waking anything",
              post("/meeting/direction", {})[1].get("ok") is False)
    finally:
        httpd.shutdown()

finally:
    os.environ.pop("TUTORBOARD_COURSES", None)
    atlas.forget()
    shutil.rmtree(base, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a meeting deck is assembled from what somebody wrote, and a mark on a "
      "slide is direction for that project")
