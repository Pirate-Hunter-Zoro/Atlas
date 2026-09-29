#!/usr/bin/env python3
"""The meeting deck: a presentation to the mentors, written over a brief.

    "I'm looking at the meeting deck right now. It's absolute dog shit."

The deck is the deck from sittings with a preset, so what is checked here is
what a meeting has that a deck from sittings has not -- on a fixture shaped like
the week that deck was made from:

  * THE BRIEF CARRIES THE WORK, WHOLE. A project's own commits come with their
    full messages. A `courses/X: lesson complete` save that swept the project's
    HANDOFF.md contributes that diff and is NOT listed as the project's commit,
    and neither is another project's work that swept it.
  * THE WINDOW SNAPS TO A MIDNIGHT. A commit five minutes before a naive
    seven-day cliff is inside "the last week".
  * A STALE PLAN STEP IS FLAGGED when a landed commit looks to have done it.
  * THE FENCE HOSTS, AND TWO FENCES ARE REFUSED -- `sittings.host_for`'s own
    answer, not a second one.
  * THE PAGE MAP IS READ OFF THE BUILD. A project with two frames routes ink on
    both of its pages to it; a frame with no `\\meetingws` refuses the deck.
  * NOTHING INTERNAL AND NOTHING UNSUPPORTED IS SILENT. No tailnet URL and no
    plan heading in capitals in the PDF's text; a URL there refuses the deck,
    and a number no source gives is in the sidecar.
  * AND A MARK ON A SLIDE IS STILL DIRECTION, NOT FEEDBACK, and old ink goes
    with the old deck.
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

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


base = tempfile.mkdtemp(prefix="tutor-meeting-")
os.environ["TUTORBOARD_COURSES"] = base

from tutorboard import (atlas, direction, fenced, meeting, proposals,  # noqa: E402
                        sense, sittings, writeups)
from tutorboard.course import library, results                        # noqa: E402
from tutorboard.course import repo as course_repo                     # noqa: E402
from tutorboard.server import handler, hub, spawn, tikz               # noqa: E402
from tutorboard.server.routes import writing as writing_route         # noqa: E402


def write(path, text, mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if isinstance(text, bytes) else "w"
    with open(path, mode) as fh:
        fh.write(text)
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def png(path, mtime, w=64, h=48):
    """A real PNG -- pdflatex refuses a fake one -- noisy enough to clear the
    results walk's size floor."""
    import random
    import struct
    import zlib

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))

    rnd = random.Random(path)
    raw = b"".join(b"\x00" + bytes(rnd.randrange(256) for _ in range(w * 3))
                   for _ in range(h))
    data = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    write(path, data, mtime)


def git(*args, when=None):
    env = dict(os.environ)
    if when is not None:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = "%d +0000" % int(when)
    for k, v in (("GIT_AUTHOR_NAME", "t"), ("GIT_AUTHOR_EMAIL", "t@t"),
                 ("GIT_COMMITTER_NAME", "t"), ("GIT_COMMITTER_EMAIL", "t@t")):
        env.setdefault(k, v)
    return subprocess.run(["git"] + list(args), cwd=base, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=True).stdout.decode()


def commit(message, when):
    git("add", "-A")
    git("commit", "-q", "-m", message, when=when)


NOW = time.time()
CLIFF = NOW - 7 * 86400
START = meeting.snap(CLIFF)
DAY = 86400

TODO = """TRD -- REMAINING WORK

  STEP 1. INTEGRATE HIS SECTIONS. Take his text essentially as written and
    confine departures to cross-references.
  STEP 2. RUN THE FALSIFICATION BATTERY.
    Twelve contrasts, one job each.
"""

try:
    write(os.path.join(base, "atlas.json"), json.dumps(
        {"families": [{"id": "research", "name": "Research"},
                      {"id": "courses", "name": "Courses"}]}))
    trd = os.path.join(base, "research", "TRD")
    psy = os.path.join(base, "research", "PSY")
    psy2 = os.path.join(base, "research", "PSY2")
    prob = os.path.join(base, "courses", "Prob")
    for r, name in ((trd, "TRD-EHR"), (psy, "PSYCH-ASR"), (psy2, "OTHER-ASR"),
                    (prob, "Probability")):
        write(os.path.join(r, "tutorboard.json"), json.dumps({"name": name}))
        os.makedirs(os.path.join(r, "live"), exist_ok=True)
    write(os.path.join(base, ".gitignore"), "live/\n*/*/live/\n")
    write(os.path.join(trd, "planning", "TODO.txt"), TODO)
    write(os.path.join(trd, "README.md"), "# TRD\n\nThe plan is planning/TODO.txt\n")
    write(os.path.join(trd, "HANDOFF.md"), "The KNN gap is open.\n")
    write(os.path.join(psy, "DIRECTION.md"), "<!-- set: old -->\nRepair the transcript.\n")
    write(os.path.join(psy, "README.md"), "# PSY\n")
    write(os.path.join(psy2, "README.md"), "# PSY2\n")
    write(os.path.join(prob, "notes.md"), "lesson one\n")
    git("init", "-q", "-b", "main")
    commit("everything, to start from", NOW - 20 * DAY)

    # THE FENCES. Untracked, like the real ones.
    os.makedirs(os.path.join(psy, "phi"), exist_ok=True)
    write(os.path.join(psy, "phi", "session.txt"), "never read")
    os.makedirs(os.path.join(psy2, "data"), exist_ok=True)
    fenced.forget()

    # FIVE MINUTES BEFORE THE NAIVE CLIFF, and after the midnight it snaps to.
    edge = CLIFF - 300 if CLIFF - 300 > START + 1 else (START + CLIFF) / 2.0
    write(os.path.join(psy, "DIRECTION.md"),
          "<!-- set: new -->\nThe master reference transcript is built and "
          "awaits approval. The grid is next.\n")
    commit("psy direction change", edge)

    # THE WEEK'S FINDINGS, each a paragraph of a message.
    write(os.path.join(trd, "scripts", "knn.py"), "K = 50\n")
    commit("the KNN gap is neighbourhood size, not the metric\n\n"
           "At k = 50 plain cosine reaches 0.594 (0.578-0.610); the metric "
           "change alone moves nothing. BODY-ONE-MARKER.", NOW - 6 * DAY)
    write(os.path.join(trd, "scripts", "arms.py"), "ARMS = 2\n")
    commit("the retrieval slate is two arms\n\n"
           "Plain cosine is the baseline and the importance-weighted metric the "
           "second arm. BODY-TWO-MARKER.", NOW - 5 * DAY)
    write(os.path.join(trd, "results", "tables", "sweep.csv"),
          "k,auc,lo,hi\n50,0.602,0.587,0.619\n", NOW - 4 * DAY)
    png(os.path.join(trd, "results", "figs", "k_sweep.png"), NOW - 4 * DAY)
    png(os.path.join(trd, "results", "figs", "old_roc.png"), NOW - 15 * DAY)
    commit("Table S7's importance-weighted row at k = 50 carries its interval, "
           "0.602 (0.587-0.619): the sweep adds bootstrap intervals at chosen k "
           "BODY-THREE-MARKER", NOW - 4 * DAY)
    write(os.path.join(trd, "paper", "manuscript.tex"), "his sections\n")
    commit("the manuscript is the senior author's revision: his sections are "
           "integrated as written", NOW - 3 * DAY)

    # A SAVE FROM ANOTHER WORKSPACE that swept TRD's handoff with it.
    write(os.path.join(prob, "notes.md"), "lesson two\n")
    write(os.path.join(trd, "HANDOFF.md"),
          "The KNN gap is neighbourhood size. SAVE-DIFF-MARKER.\n")
    commit("courses/Prob: lesson complete", NOW - 2 * DAY)
    # AND ANOTHER PROJECT'S WORK that swept it again.
    write(os.path.join(prob, "tool.py"), "x = 1\n")
    write(os.path.join(trd, "HANDOFF.md"),
          "The KNN gap is neighbourhood size. OTHER-DIFF-MARKER.\n")
    commit("Paper-Writer holds prose to what publishable prose does",
           NOW - 2 * DAY + 60)
    # AND THE SECOND FENCED PROJECT MOVES TOO.
    write(os.path.join(psy2, "README.md"), "# PSY2\n\nmoved\n")
    commit("psy2 moved", NOW - DAY)
    results.forget()
    atlas.forget()
    sittings.forget()

    ids = set(w["id"] for w in atlas.workspaces(base))
    check("the fixture has four workspaces",
          ids == {"research/TRD", "research/PSY", "research/PSY2", "courses/Prob"})

    # --- when --------------------------------------------------------------
    since, said = meeting.resolve_since("7d", base)
    lt = time.localtime(since)
    check("the last week starts at a local midnight",
          (lt.tm_hour, lt.tm_min, lt.tm_sec) == (0, 0, 0) and said == "the last week")
    check("a commit five minutes before the naive cliff is before the cliff",
          edge < CLIFF)
    check("and inside the snapped window", since <= edge)
    check("the period is said exactly, for the title slide",
          meeting.period_text(since, NOW).endswith(str(time.localtime(NOW).tm_year))
          and " to " in meeting.period_text(since, NOW))
    for bad in ("", "wat", "0d", "9999d", "2026-13-40", "2026-02-31"):
        check("refused: %r" % bad, meeting.resolve_since(bad, base)[0] is None)
    check("`last` with no earlier deck says so rather than guessing",
          meeting.resolve_since("last", base)[0] is None)

    # --- whose a commit is --------------------------------------------------
    blocks, every, why = meeting.blocks_for(
        base, ["research/TRD", "research/PSY"], since)
    by = dict((b["id"], b) for b in blocks)
    check("both projects moved", set(by) == {"research/TRD", "research/PSY"})
    t = by["research/TRD"]
    subjects = [c["subject"] for c in t["commits"]]
    check("TRD's own four commits are its commits",
          len(t["commits"]) == 4
          and any("neighbourhood size" in s for s in subjects))
    check("and each carries its whole message",
          any("BODY-ONE-MARKER" in c["body"] for c in t["commits"])
          and any("BODY-TWO-MARKER" in c["body"] for c in t["commits"])
          and any("BODY-THREE-MARKER" in c["body"] for c in t["commits"]))
    check("a `courses/X: lesson complete` save is NOT a TRD commit",
          not any("lesson complete" in s for s in subjects))
    check("nor is another project's work that swept TRD's handoff",
          not any("Paper-Writer" in s for s in subjects))
    save = [s for s in t["saves"] if "lesson complete" in s["subject"]]
    check("the save contributes the HANDOFF.md diff it carried",
          save and "SAVE-DIFF-MARKER" in save[0]["diff"]
          and save[0]["owner"] == "courses/Prob")
    check("and the other project's work contributes its diff too",
          any("OTHER-DIFF-MARKER" in s["diff"] for s in t["saves"]))
    check("the handoff's diff over the whole period is carried",
          "OTHER-DIFF-MARKER" in t["story"].get("HANDOFF.md", ""))
    p = by["research/PSY"]
    check("the direction change five minutes before the cliff is in the week",
          [c["subject"] for c in p["commits"]] == ["psy direction change"]
          and "master reference transcript" in p["story"].get("DIRECTION.md", ""))

    stale = [s for s in t["open"] if s["title"].upper().startswith("INTEGRATE")]
    check("a stale plan step a landed commit satisfies is flagged",
          stale and stale[0]["maybe"])
    fresh = [s for s in t["open"] if "FALSIFICATION" in s["title"].upper()]
    check("and a step nothing did is not", fresh and not fresh[0]["maybe"])

    host, clash = meeting.host_for(blocks)
    check("the fenced project hosts the deck", host == "research/PSY" and not clash)
    two, _, _ = meeting.blocks_for(base, ["research/PSY", "research/PSY2"], since)
    check("two fenced projects in one deck are refused, by name",
          "research/PSY" in (meeting.host_for(two)[1] or "")
          and "research/PSY2" in meeting.host_for(two)[1])

    # --- the brief, dry -----------------------------------------------------
    dry = meeting.write_brief(base, os.path.join(psy, "writeups", "meeting"),
                              blocks, since, human=said, host=host, dry=True)
    md = dry["markdown"]
    check("the dry brief writes nothing",
          not os.path.exists(os.path.join(psy, "writeups", "meeting")))
    check("the brief says who the audience is", "MENTORS" in md)
    check("the brief carries the bodies", "BODY-ONE-MARKER" in md
          and "BODY-TWO-MARKER" in md and "BODY-THREE-MARKER" in md)
    check("and hands the writer plan headings in words, not capitals",
          "Integrate his sections" in md and "INTEGRATE HIS SECTIONS" not in md)
    check("and says the stale step may already be done",
          "MAY ALREADY BE DONE" in md)
    check("and never names anything under the fence", "phi/session" not in md)

    # -----------------------------------------------------------------------
    # THE ROUTES, over real HTTP. The board serving is the course; the deck is
    # written in the fenced project.
    # -----------------------------------------------------------------------
    woken, started = [], []
    spawn.wake_tutor = lambda r: woken.append(r.root) or True
    spawn.tutor_cli = lambda args, timeout=60: (started.append(args) or (0, ""))
    spawn.fresh_tutor = lambda root, course: fails.append(
        "an assistant was replaced by a mark on a slide")
    meeting.SETTLE = 0
    # WHETHER THE HOST'S TURN IS OVER, which the test decides: a deck is read
    # back once, when its writer is done with it.
    turn = {"over": False}
    sittings._turn_over = lambda root, wid: turn["over"]

    serving = course_repo.Repo(prob)
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
            BASE + path, method="POST", data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def get(path):
        try:
            with urllib.request.urlopen(BASE + path, timeout=120) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    deck_dir = os.path.join(psy, "writeups", "meeting")
    HAVE_TEX = bool(shutil.which("pdflatex")) and bool(shutil.which("pdfinfo"))

    def build(tex):
        """Play the writer: the `.tex`, built the way the turn is told to --
        pdflatex twice, in the deck's own directory."""
        write(os.path.join(deck_dir, "meeting.tex"), tex)
        for ext in (".pdf", ".aux"):
            try:
                os.remove(os.path.join(deck_dir, "meeting" + ext))
            except OSError:
                pass
        for _ in range(2):
            subprocess.run(["pdflatex", "-interaction=nonstopmode",
                            "meeting.tex"], cwd=deck_dir,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=300)
        return os.path.isfile(os.path.join(deck_dir, "meeting.pdf"))

    def deck_tex(frames, preamble=""):
        return ("\\documentclass[aspectratio=169]{beamer}\n"
                "\\usepackage{meetingws}\n" + preamble +
                "\\title{Progress}\\date{%s}\n\\begin{document}\n%s\n"
                "\\end{document}\n" % (meeting.period_text(since, NOW),
                                       "\n".join(frames)))

    def frame(title, ws, body):
        mark = "\\meetingshared" if ws == "*" else "\\meetingws{%s}" % ws if ws else ""
        return "\\begin{frame}{%s}%s\n%s\n\\end{frame}" % (title, mark, body)

    try:
        # --- which projects ---------------------------------------------
        status, body = post("/notes/what", {"since": "7d"})
        rows = dict((w["id"], w) for w in body.get("workspaces") or [])
        check("the sheet is told what each project has",
              status == 200 and rows["research/TRD"]["commits"] == 4
              and rows["research/TRD"]["moved"] and rows["research/PSY"]["fenced"])

        status, body = post("/notes", {"since": "7d",
                                       "want": ["research/PSY", "research/PSY2"]})
        check("two fenced projects are refused by the route, and nothing is "
              "written", status == 400 and "PSY2" in (body.get("detail") or "")
              and not os.path.exists(deck_dir))

        # --- asked for --------------------------------------------------
        status, body = post("/notes", {"since": "7d",
                                       "want": ["research/TRD", "research/PSY"]})
        check("the deck is asked for, and is being written",
              status == 200 and body.get("ok") and body.get("state") == "being written")
        check("in the fenced project, whose assistant may read it",
              body.get("host") == "research/PSY"
              and started and started[-1][:3] == ["agent", "start", "PSY"])
        wid = body.get("id")
        brief = open(os.path.join(deck_dir, "_brief.md"), encoding="utf-8").read()
        check("the brief is beside where the deck goes, with TRD's bodies",
              "BODY-ONE-MARKER" in brief and "BODY-THREE-MARKER" in brief)
        check("the save's diff is in it, and the save is not a TRD commit",
              "SAVE-DIFF-MARKER" in brief
              and "**courses/Prob: lesson complete**" not in brief)
        check("the package every frame names its project with is beside it",
              os.path.isfile(os.path.join(deck_dir, "meetingws.sty")))
        ign = open(os.path.join(deck_dir, ".gitignore"), encoding="utf-8").read()
        check("the figures, the PDF, the brief and the sidecar are untracked",
              all(x in ign for x in ("figures/", "*.pdf", "_brief.*",
                                     "_provenance.*")))
        figs = json.load(open(os.path.join(deck_dir, "_brief.json")))["figures"]
        check("the period's figure is copied beside the deck, and the old one "
              "is only catalogued",
              any("k-sweep" in f or "k_sweep" in f for f in figs)
              and not any("old" in f for f in figs))
        inbox = open(course_repo.Repo(psy).messages_path, encoding="utf-8").read()
        check("a [writeup] turn is asked for in the host, over the brief",
              "[writeup]" in inbox and "writeups/meeting/_brief.md" in inbox
              and "meetingws" in inbox and "MENTORS" in inbox)
        check("the meeting prompt lives beside the deck from sittings' one",
              "writeups/meeting/meeting.tex" in sense.meeting_about(
                  "writeups/meeting", "x"))
        status, body = get("/meeting/deck.json")
        check("the sheet is told it is being written",
              body.get("state") == "being written" and not body.get("built"))
        status, body = get("/meeting/view")
        check("and the reader draws nothing yet, saying why",
              not body.get("ok") and body.get("why") == "being written")

        fig = figs[0] if figs else ""
        good = deck_tex([
            frame("", "*", "\\titlepage"),
            frame("Summary", "*", "TRD-EHR: retrieval reaches 0.602 at k = 50."),
            frame("The gap is neighbourhood size", "research/TRD",
                  "AUC 0.602 (0.587--0.619) against 0.594.\\par"
                  "\\includegraphics[width=0.5\\linewidth]{%s}" % fig),
            frame("Two arms", "research/TRD",
                  "The weighted arm reaches 0.713 in a subgroup."),
            frame("A new direction", "research/PSY",
                  "The reference transcript is built and awaits approval."),
            frame("Asks", "*", "Approve the reference."),
        ])
        if HAVE_TEX and build(deck_tex([frame("", "", "\\titlepage")])):
            # A FIRST BUILD MID-TURN IS NOT THE DECK. The writer is still at it.
            status, body = get("/meeting/deck.json")
            check("a build while the turn is still working is not read back",
                  body.get("state") == "being written")
            ok_built = build(good)
            turn["over"] = True
        else:
            ok_built = False
        if HAVE_TEX and ok_built:
            status, body = get("/meeting/deck.json")
            check("a built deck is read back and is ready",
                  body.get("state") == "ready" and body.get("built"))
            check("the page map comes off the compiled PDF: a two-frame project "
                  "has both of its pages",
                  body.get("pages") == {"3": "research/TRD", "4": "research/TRD",
                                        "5": "research/PSY"})
            check("the title, summary and closing pages belong to nobody",
                  not any(k in body["pages"] for k in ("1", "2", "6")))
            check("and the host's writeup record says it landed",
                  writeups.state(psy, wid) == "done")
            docs = library.documents(psy)
            check("the meeting deck is not a library document: its ink is "
                  "direction", not any("meeting" in (d.get("dir") or "")
                                       for d in docs))

            prov = json.load(open(os.path.join(deck_dir, "_provenance.json")))
            said_nums = [n["value"] for n in prov["numbers"]]
            check("a number not in any source is in the sidecar", "0.713" in said_nums)
            check("and the ones the sources give are not",
                  "0.602" not in said_nums and "0.594" not in said_nums
                  and "0.587" not in said_nums and "50" not in said_nums)
            check("and it says which slide", any(n["frame"] == 4 and
                                                 n["value"] == "0.713"
                                                 for n in prov["numbers"]))
            check("a figure the board copied is not flagged", not prov["figures"])
            text = meeting.pdf_text(os.path.join(deck_dir, "meeting.pdf"))
            check("no tailnet URL in the PDF's text",
                  "ts.net" not in text and "#/w/" not in text)
            check("and no plan heading in capitals", "INTEGRATE HIS" not in text)

            status, body = get("/meeting/view")
            if body.get("ok"):
                check("the reader draws every page, with whose each is",
                      len(body.get("pages") or []) == 6
                      and body.get("pages_of", {}).get("4") == "research/TRD")
                check("and is handed the sidecar to show",
                      any(n["value"] == "0.713"
                          for n in body["unsupported"]["numbers"]))
            else:
                print("skip  %s" % (body.get("detail") or "no pages drawn here"))

            # --- ink on BOTH of a project's pages goes to it ---------------
            def ink(page):
                key = "doc/%s/p%d" % (meeting.ANN_IDENT, page)
                stem = writing_route.ann_file(key)
                with open(os.path.join(serving.notes, stem + ".json"), "w",
                          encoding="utf-8") as fh:
                    json.dump({"card": key, "sent": False,
                               "strokes": [{"p": [[0.1, 0.1], [0.2, 0.3]]}]}, fh)
                with open(os.path.join(serving.notes, stem + ".png"), "wb") as fh:
                    fh.write(b"\x89PNG\r\n\x1a\n")
                return key

            ink(3)
            ink(4)
            status, body = post("/meeting/direction", {})
            sent = body.get("sent") or []
            check("ink on both of a project's pages is routed to that project",
                  status == 200 and [s["workspace"] for s in sent]
                  == ["research/TRD"] and sent[0]["pages"] == [3, 4])
            said = open(course_repo.Repo(trd).messages_path, encoding="utf-8").read()
            check("as a proposal, pointing at the deck where it is",
                  "[direction]" in said and "YOU ARE PROPOSING" in said
                  and "research/PSY/writeups/meeting/meeting.pdf" in said)
            feedback = [n for h, _, ns in os.walk(base)
                        if os.path.basename(h) == "feedback" for n in ns]
            check("no feedback file is written anywhere", not feedback)
            check("no direction is applied", not os.path.isfile(direction.path(trd)))
            meeting.clear_ink(serving)
            ink(1)
            status, body = post("/meeting/direction", {})
            check("a mark on a shared page is refused rather than guessed at",
                  status == 400 and "nowhere to go" in (body.get("detail") or ""))

            # --- a frame with no \meetingws refuses the deck ----------------
            ink(4)
            status, body = post("/notes", {"since": "7d",
                                           "want": ["research/TRD", "research/PSY"]})
            check("asking again replaces the deck and clears its ink",
                  status == 200 and not meeting.ink_keys(serving)
                  and not os.path.isfile(os.path.join(deck_dir, "meeting.pdf")))
            bad = deck_tex([
                frame("", "*", "\\titlepage"),
                frame("Findings", "research/TRD", "0.602"),
                frame("Unmarked", "", "0.602"),
                frame("Asks", "*", "Approve."),
            ])
            build(bad)
            status, body = get("/meeting/deck.json")
            check("a frame with no \\meetingws refuses the deck, by page",
                  body.get("state") == "did not land"
                  and "page 3" in (body.get("why") or "") and not body.get("built"))
            status, body = get("/meeting/view")
            check("and it is not offered to the reader", not body.get("ok"))

            # --- a tailnet URL refuses it; a copied heading is listed --------
            post("/notes", {"since": "7d", "want": ["research/TRD", "research/PSY"]})
            leak = deck_tex([
                frame("", "*", "\\titlepage"),
                frame("Findings", "research/TRD",
                      "INTEGRATE HIS SECTIONS\\par "
                      "\\url{http://compute-node.tail0c6c62.ts.net:8937}"),
            ], preamble="\\usepackage{url}\n")
            build(leak)
            status, body = get("/meeting/deck.json")
            check("a tailnet URL in the PDF refuses the deck",
                  body.get("state") == "did not land"
                  and "ts.net" in (body.get("why") or ""))
            prov = json.load(open(os.path.join(deck_dir, "_provenance.json")))
            check("and a plan heading copied in capitals is in the sidecar",
                  any("INTEGRATE HIS SECTIONS" in x["heading"]
                      for x in prov["internal"]))

            # --- a link whose TARGET is the tailnet, under innocent words ----
            post("/notes", {"since": "7d", "want": ["research/TRD", "research/PSY"]})
            link = deck_tex([
                frame("", "*", "\\titlepage"),
                frame("Findings", "research/TRD",
                      "\\href{http://compute-node.tail0c6c62.ts.net:8937/"
                      "\\#/w/research/TRD}{The findings}"),
            ], preamble="\\usepackage{hyperref}\n")
            build(link)
            text = meeting.pdf_text(os.path.join(deck_dir, "meeting.pdf"))
            status, body = get("/meeting/deck.json")
            check("a link to the tailnet under other words refuses the deck",
                  "ts.net" not in text and body.get("state") == "did not land"
                  and "ts.net" in (body.get("why") or ""))
        else:
            print("skip  no LaTeX here, so the build, the page map and the "
                  "provenance are not checked")

        # --- a turn that ended with nothing ---------------------------------
        post("/notes", {"since": "7d", "want": ["research/TRD", "research/PSY"]})
        turn["over"] = True
        was_quiet = meeting.QUIET
        meeting.QUIET = 0
        try:
            status, body = get("/meeting/deck.json")
        finally:
            meeting.QUIET = was_quiet
        check("a turn that ended without a deck did not land, and says so",
              body.get("state") == "did not land"
              and "without writing" in (body.get("why") or ""))
        check("since the last deck is measurable once one was asked for",
              meeting.resolve_since("last", base)[0] is not None)

        # --- somebody's own writeups/meeting/ is not taken away -------------
        shutil.rmtree(deck_dir)
        write(os.path.join(deck_dir, "meeting.tex"), "MINE\n")
        status, body = post("/notes", {"since": "7d",
                                       "want": ["research/TRD", "research/PSY"]})
        check("a writeups/meeting/ the board did not write refuses the ask, and "
              "is left as it was",
              status == 409 and "not a meeting deck" in (body.get("detail") or "")
              and open(os.path.join(deck_dir, "meeting.tex")).read() == "MINE\n"
              and sorted(os.listdir(deck_dir)) == ["meeting.tex"])
        shutil.rmtree(deck_dir)
    finally:
        httpd.shutdown()

    # --- the command line, which is the second entry point ------------------
    got = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "board"),
                          "notes", "--meeting", "--since", "7d", "--workspace",
                          "research/TRD", "--print"], cwd=trd,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env=dict(os.environ), timeout=120)
    out = got.stdout.decode("utf-8", "replace")
    check("`board notes --meeting --print` prints the brief and writes nothing",
          got.returncode == 0 and "BODY-ONE-MARKER" in out
          and not os.path.isdir(os.path.join(trd, "writeups", "meeting")))
    outside = tempfile.mkdtemp(prefix="tutor-meeting-out-")
    try:
        got = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "board"),
                              "notes", "--meeting", "--since", "7d",
                              "--workspace", "research/PSY", "--brief-to",
                              os.path.join(outside, "b")], cwd=trd,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             env=dict(os.environ), timeout=120)
        check("a fenced project's brief is not written outside it",
              got.returncode != 0 and not os.listdir(outside))
        got = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "board"),
                              "notes", "--meeting", "--since", "7d",
                              "--workspace", "research/TRD", "--brief-to",
                              os.path.join(outside, "b")], cwd=trd,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             env=dict(os.environ), timeout=120)
        check("and an unfenced one's is",
              got.returncode == 0
              and os.path.isfile(os.path.join(outside, "b", "_brief.md")))
    finally:
        shutil.rmtree(outside, ignore_errors=True)

finally:
    os.environ.pop("TUTORBOARD_COURSES", None)
    atlas.forget()
    shutil.rmtree(base, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("the meeting deck is written over a brief of the period, routed page by "
      "page off its own build, and nothing unsupported on it is silent")
