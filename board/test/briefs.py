#!/usr/bin/env python3
"""The meeting deck: one engine (`briefs.py`), one artifact in projects/Meetings.

  * ONE CLASSIFIER. A subject's own work is listed with its whole message; a
    save, and another subject's work that swept this subject's TUTOR.md, are
    not.
  * THE WINDOW SNAPS TO A MIDNIGHT. A commit five minutes before a naive
    seven-day cliff is inside "the last week".
  * THE INPUTS: commits, the TUTOR.md diff, the sessions that ended. A subject
    with no TUTOR.md history still briefs.
  * THE DECK IS AN ARTIFACT. `POST /meeting` writes doc.json and the brief in
    projects/Meetings/docs/meeting/ and asks a `[writeup]` turn in a session
    bound to Meetings. Asking again replaces it -- one doc.json, one
    meeting.tex -- and clears its ink.
  * ONE LANDING JUDGE, `artifacts.status`: being written, ready, did not land.
    A number no source gives is listed; a tailnet address refuses the deck.
  * THE BRIEF, THE FIGURES AND THE PDF ARE IGNORED by the root rules, and no
    `*.out` is tracked.
  * A DECK WITH A BRIEF IS REVISED AGAINST IT, and `board deckfig` copies a
    figure only from a subject the brief names.
"""

import http.client
import json
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
BOARD = os.path.join(ROOT, "bin", "board")
sys.path.insert(0, ROOT)

tmp = os.path.realpath(tempfile.mkdtemp(prefix="tutor-briefs-"))
base = os.path.join(tmp, "Atlas")
os.environ["BOARD_STATE_DIR"] = os.path.join(tmp, ".state")
os.environ["TUTORBOARD_TRASH"] = os.path.join(tmp, ".trash")
os.environ["XDG_CONFIG_HOME"] = os.path.join(tmp, ".config")
os.environ["TUTORBOARD_COURSES"] = base
os.environ["TUTORBOARD_PAGES"] = os.path.join(tmp, ".pages")

from tutorboard import artifacts, briefs, gitops, sense, sessions, writeups  # noqa: E402
from tutorboard.course import library                                        # noqa: E402
from tutorboard.lesson import notes as lesson_notes                          # noqa: E402
from tutorboard.runner import service as runner_service                    # noqa: E402
from tutorboard.server import app, handler, registry, spawn                  # noqa: E402
from tutorboard.server.routes import library as library_route                # noqa: E402
from tutorboard.server.routes import writing as writing_route                # noqa: E402

fails = []


def check(name, cond, said=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (" -- %s" % (said,) if said else ""))


def write(path, text, mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if isinstance(text, bytes) else "w") as fh:
        fh.write(text)
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def png(path, mtime, w=64, h=48):
    """A real PNG, noisy enough to clear the results walk's size floor."""
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))
    rnd = random.Random(path)
    raw = b"".join(b"\x00" + bytes(rnd.randrange(256) for _ in range(w * 3))
                   for _ in range(h))
    write(path, b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2,
                                                                  0, 0, 0))
          + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""), mtime)


def git(*args, when=None, cwd=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    if when is not None:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = "%d +0000" % int(when)
    return subprocess.run(["git"] + list(args), cwd=cwd or base, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=True).stdout.decode()


def commit(message, when):
    git("add", "-A")
    git("commit", "-q", "--no-verify", "-m", message, when=when)


NOW = time.time()
DAY = 86400
CLIFF = NOW - 7 * DAY
TRD = os.path.join(base, "projects", "TRD")
PSY = os.path.join(base, "projects", "PSY")
PW = os.path.join(base, "projects", "PW")
PROB = os.path.join(base, "courses", "Prob")
MEET = os.path.join(base, "projects", "Meetings")
DECK = os.path.join(MEET, "docs", "meeting")

handler.PING_SECONDS = 0.5
runner_service.wake = lambda repo: False

try:
    # ---- the fixture: an Atlas with five subjects and a fortnight of work --
    for root, name, phi in ((TRD, "TRD-EHR", False), (PSY, "PSYCH-ASR", True),
                            (PW, "Paper-Writer", False), (PROB, "Probability", False),
                            (MEET, "Meetings", True)):
        write(os.path.join(root, "tutorboard.json"), json.dumps({"name": name, "phi": phi}))
    write(os.path.join(base, ".gitignore"), "/sessions/\n**/.ink/\n*.pdf\n_brief.*\n"
          "figures/\n_provenance.json\n")
    write(os.path.join(TRD, "TUTOR.md"), "# TRD\n\n## Now\n\n- WEIGHT THE NEIGHBOURS\n")
    write(os.path.join(PSY, "README.md"), "psy\n")
    write(os.path.join(PROB, "notes.md"), "n\n")
    write(os.path.join(PW, "draft.md"), "d\n")
    git("init", "-q", "-b", "main")
    commit("everything, to start from", NOW - 30 * DAY)
    # In time order: `git log --since` stops at the first commit older than it.
    write(os.path.join(PSY, "src", "old.py"), "x\n")
    commit("projects/PSY: something long ago", NOW - 20 * DAY)
    write(os.path.join(PSY, "src", "asr.py"), "x\n")
    commit("projects/PSY: the reference transcript is built", CLIFF - 300)

    write(os.path.join(TRD, "src", "knn.py"), "k = 50\n")
    write(os.path.join(TRD, "TUTOR.md"), "# TRD\n\n## Now\n\n- WEIGHT THE NEIGHBOURS\n"
          "- the gap is neighbourhood size TUTOR-DIFF-MARKER\n")
    commit("projects/TRD: the KNN gap is neighbourhood size\n\nBODY-ONE-MARKER: "
           "AUC 0.602 at k = 50 against 0.594.", NOW - 3 * DAY)
    write(os.path.join(PROB, "notes.md"), "n2\n")
    write(os.path.join(TRD, "TUTOR.md"), open(os.path.join(TRD, "TUTOR.md")).read()
          + "- swept by a save\n")
    commit("courses/Prob: %s" % gitops.SAVE, NOW - 2 * DAY)
    write(os.path.join(PW, "draft.md"), "d2\n")
    write(os.path.join(TRD, "TUTOR.md"), open(os.path.join(TRD, "TUTOR.md")).read()
          + "- swept by another project\n")
    commit("projects/PW: wrote the methods section", NOW - DAY)
    os.makedirs(os.path.join(PSY, "phi"), exist_ok=True)
    png(os.path.join(TRD, "figures", "k_sweep.png"), NOW - 2 * DAY)
    png(os.path.join(TRD, "figures", "old_roc.png"), NOW - 25 * DAY)

    # An ended session on Prob, inside the period.
    rec = sessions.new("Conditional probability", base=base, now=NOW - 2 * DAY)
    sdir = sessions.path(rec["id"], base)
    sessions.repo(rec["id"], base).set_state(subject="courses/Prob")
    write(os.path.join(sdir, "cards", "0001-lesson.md"), "---\nkind: lesson\n---\nA card.\n")
    sessions.end(rec["id"], base=base, now=NOW - 2 * DAY + 3600)

    # ---- one classifier ------------------------------------------------------
    ids = {"projects/TRD", "projects/PW", "courses/Prob"}
    check("a save is a save, under any prefix",
          briefs.is_save("courses/Prob: " + gitops.SAVE, ids)
          and briefs.is_save("stopping point.") and not briefs.is_save("projects/TRD: knn", ids))
    c = {"subject": "projects/PW: methods", "files": ["projects/PW/a", "projects/TRD/TUTOR.md"]}
    check("another subject's work is `other` to this one",
          briefs.classify(c, "projects/TRD", ids) == "other")
    c = {"subject": "tidy", "files": ["projects/PW/a", "projects/TRD/TUTOR.md"]}
    check("and so is unprefixed work elsewhere that swept only TUTOR.md here",
          briefs.classify(c, "projects/TRD", ids) == "other")
    c = {"subject": "projects/TRD: k", "files": ["projects/TRD/src/knn.py"]}
    check("a subject's own commit is `work`", briefs.classify(c, "projects/TRD", ids) == "work")
    found = subprocess.run(["git", "grep", "-n", gitops.SAVE, "--", "board/tutorboard"],
                           cwd=REPO, stdout=subprocess.PIPE,
                           universal_newlines=True).stdout.splitlines()
    check("the save message is defined once in board/tutorboard", len(found) == 1, found)

    # ---- the window, the gather ------------------------------------------------
    since, said = briefs.resolve_since("7d", base)
    check("the window snaps to a midnight", since == briefs.snap(CLIFF) and said == "the last week")
    check("a span that is not one is refused", briefs.resolve_since("nope", base)[0] is None)
    check("`last` with no deck yet is refused", briefs.resolve_since("last", base)[0] is None)
    blocks, every, why = briefs.blocks_for(base, None, since)
    by = dict((b["id"], b) for b in blocks)
    check("Meetings is never a subject of its own deck",
          "projects/Meetings" not in [s["id"] for s in every])
    t = by.get("projects/TRD") or {}
    check("a subject's own commits, with their whole messages",
          [c["subject"] for c in t.get("commits", [])]
          == ["projects/TRD: the KNN gap is neighbourhood size"]
          and "BODY-ONE-MARKER" in t["commits"][0]["body"])
    check("its TUTOR.md diff over the period is carried",
          "TUTOR-DIFF-MARKER" in t.get("story", ""))
    check("the commit five minutes before the cliff is in the week",
          [c["subject"] for c in (by.get("projects/PSY") or {}).get("commits", [])]
          == ["projects/PSY: the reference transcript is built"])
    p = by.get("courses/Prob") or {}
    check("the sessions that ended in the period are an input",
          [s["title"] for s in p.get("sessions", [])] == ["Conditional probability"]
          and p["sessions"][0]["cards"] == 1)
    check("and a save is not a commit of its subject", p.get("commits") == [])
    psy, _, _ = briefs.blocks_for(base, ["projects/PSY"], since)
    dry = briefs.write_brief(base, DECK, psy, since, human=said, dry=True)
    check("A BRIEF WITH NO TUTOR.md HISTORY BUILDS",
          psy and psy[0]["story"] == "" and "reference transcript" in dry["markdown"]
          and not os.path.exists(DECK))
    dry = briefs.write_brief(base, DECK, blocks, since, human=said, dry=True)
    md = dry["markdown"]
    check("the brief says who it is for and carries the bodies",
          "MENTORS" in md and "BODY-ONE-MARKER" in md and "Conditional probability" in md)
    check("and says which subject holds a fence, without naming anything under it",
          "projects/PSY holds `phi/`" in md and "phi/session" not in md)

    # ---- a period spanning the memory migration (T30b, T30c) ---------------
    # Before it, a subject's continuity was HANDOFF.md and threads.json; the
    # migration wrote TUTOR.md and RULES.md in one commit and deleted the old
    # files in another. A gather across both still reports the subject's work.
    mig_base = os.path.join(tmp, "Migrated")
    MIG = os.path.join(mig_base, "projects", "Mig")
    write(os.path.join(MIG, "tutorboard.json"), json.dumps({"name": "Mig", "phi": False}))
    write(os.path.join(MIG, "HANDOFF.md"), "the sweep is half run\n")
    write(os.path.join(MIG, "threads.json"), json.dumps({"threads": []}))
    write(os.path.join(mig_base, "board", "x.py"), "x\n")
    write(os.path.join(mig_base, ".gitignore"), "/sessions/\n")
    git("init", "-q", "-b", "main", cwd=mig_base)

    def mig_commit(message, when):
        git("add", "-A", cwd=mig_base)
        git("commit", "-q", "--no-verify", "-m", message, when=when, cwd=mig_base)
    mig_commit("projects/Mig: the sweep runs", NOW - 20 * DAY)
    write(os.path.join(MIG, "TUTOR.md"), "# Mig\n\n## Now\n\n- [ ] MIGRATED-SWEEP finish\n")
    write(os.path.join(MIG, "RULES.md"), "# Rules\n\n- one\n")
    write(os.path.join(mig_base, "board", "scripts", "m.py"), "m\n")
    mig_commit("subjects: contracts become RULES.md and TUTOR.md (T30b)", NOW - 3 * DAY)
    os.remove(os.path.join(MIG, "HANDOFF.md"))
    os.remove(os.path.join(MIG, "threads.json"))
    write(os.path.join(mig_base, "board", "x.py"), "y\n")
    mig_commit("board: the old planning layer goes (T30c)", NOW - 2 * DAY)
    write(os.path.join(MIG, "src", "sweep.py"), "k = 1\n")
    mig_commit("Mig: the sweep finishes", NOW - DAY)
    mblocks, _, _ = briefs.blocks_for(mig_base, None, since)
    m = mblocks[0] if mblocks else {}
    check("A GATHER SPANNING THE MIGRATION REPORTS PROGRESS: its TUTOR.md is new "
          "in the period, and the slug-prefixed commit after it is the subject's",
          m.get("id") == "projects/Mig" and "MIGRATED-SWEEP" in m.get("story", "")
          and "Mig: the sweep finishes" in [c["subject"] for c in m.get("commits", [])],
          m)
    check("a slug prefix names its subject as the id prefix does",
          briefs.owner_of("TRD: k", ids) == "projects/TRD"
          and briefs.owner_of("projects/TRD: k", ids) == "projects/TRD"
          and briefs.classify({"subject": "PW: methods",
                               "files": ["projects/TRD/src/x.py"]},
                              "projects/TRD", ids) == "other")

    # ---- the server ------------------------------------------------------------
    httpd = app.make_server(base, 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def ask(method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=60)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        conn.request(method, path, body=data,
                     headers={"Content-Type": "application/json"} if data else {})
        r = conn.getresponse()
        out = r.status, r.read()
        conn.close()
        try:
            return out[0], json.loads(out[1].decode("utf-8"))
        except ValueError:
            return out[0], {}

    def inbox(sid):
        try:
            with open(os.path.join(sessions.path(sid, base), "inbox", "messages.jsonl"),
                      encoding="utf-8") as fh:
                return [json.loads(l) for l in fh if l.strip()]
        except OSError:
            return []

    def read_all(sid):
        """The turn took its ask, and nothing works there now."""
        where = sessions.path(sid, base)
        lines = inbox(sid)
        with open(os.path.join(where, "inbox", "messages.jsonl"), "w", encoding="utf-8") as fh:
            for m in lines:
                m["read"] = True
                fh.write(json.dumps(m) + "\n")

    def deck_rec():
        """The deck's record, as the front door watches it: the Meetings
        library's payload, `meeting`."""
        library.forget()
        return ask("GET", "/library.json?subject=projects/Meetings")[1].get("meeting") or {}

    def files(name):
        return [os.path.join(h, n) for h, _, ns in os.walk(MEET) for n in ns if n == name]

    status, body = ask("POST", "/meeting", {"since": "nope"})
    check("a period that is not one is refused", status == 400 and "nope" in body.get("detail", ""))
    status, body = ask("POST", "/meeting", {"since": "7d", "items": ["projects/Nope"]})
    check("so is a subject that is not one", status == 400)
    status, body = ask("POST", "/meeting", {"since": "7d",
                                             "items": ["projects/TRD", "courses/Prob"]})
    sid = body.get("session") or ""
    held = sessions.get(sid, base) or {}
    check("the deck is asked for in a session bound to projects/Meetings",
          status == 200 and body.get("state") == "being written"
          and held.get("subject") == "projects/Meetings", body)
    doc = artifacts.read(DECK) or {}
    check("the deck is the artifact docs/meeting, listing that session",
          doc.get("source") == "meeting.tex" and doc.get("sessions") == [sid]
          and doc.get("title", "").startswith(briefs.TITLE))
    line = [m["text"] for m in inbox(sid) if m.get("signal") == "writeup"]
    check("a [writeup] turn is asked over the brief, naming the file",
          line and line[0].startswith("[writeup]") and "docs/meeting/_brief.md" in line[0]
          and "projects/Meetings/docs/meeting/meeting.tex" in line[0]
          and "meetingws" not in line[0])
    check("the brief and the period's figure are beside it; the old figure is only "
          "catalogued",
          os.path.isfile(os.path.join(DECK, "_brief.md"))
          and any("k_sweep" in f or "k-sweep" in f
                  for f in (briefs.read_brief(DECK) or {}).get("figures", []))
          and not any("old" in f for f in (briefs.read_brief(DECK) or {}).get("figures", [])))
    w = writeups.read(sessions.repo(sid, base), body.get("id"))
    check("the writeup record is judged by the artifact", (w or {}).get("dir") == "docs/meeting")
    got = deck_rec()
    check("it is being written while the ask is unread, said on the Meetings library",
          got.get("state") == "being written" and not got.get("ready"), got)
    status, got = ask("GET", "/library/view/meeting?subject=projects/Meetings")
    check("and the reader draws nothing yet", not got.get("ok"), got)
    check("`last` measures from the deck asked for", briefs.resolve_since("last", base)[0])

    # ---- the writer writes and builds it ----------------------------------------
    fig = (briefs.read_brief(DECK) or {}).get("figures", [""])[0]

    def frame(title, body):
        return "\\begin{frame}{%s}\n%s\n\\end{frame}" % (title, body)

    def deck_tex(*frames):
        return ("\\documentclass[aspectratio=169]{beamer}\n\\usepackage{hyperref}\n"
                "\\begin{document}\n%s\n\\end{document}\n" % "\n".join(frames))

    def built(tex):
        time.sleep(1.1)
        write(os.path.join(DECK, "meeting.tex"), tex)
        write(os.path.join(DECK, "meeting.pdf"), b"%PDF-1.4\n%%EOF\n")

    built(deck_tex(frame("Findings", "AUC 0.602 against 0.594.\\par"
                         "\\includegraphics[width=0.5\\linewidth]{%s}" % fig),
                   frame("Two arms", "The weighted arm reaches 0.713 in a subgroup.")))
    read_all(sid)
    got = deck_rec()
    check("once built and the turn is over, it is ready", got.get("state") == "ready"
          and got.get("ready"), got)
    check("and what no source gives rides on it, for the reader to list",
          "0.713" in [n["value"] for n in got.get("check", {}).get("numbers", [])], got)
    status, lib = ask("GET", "/library.json?subject=projects/Meetings")
    row = [d for d in lib.get("documents", []) if d.get("meeting")]
    check("the deck's row in the Meetings library carries it, with which deck it is",
          len(row) == 1 and row[0]["id"] == "meeting"
          and row[0]["meeting"]["deck"] == briefs.deck_id(base), row)
    status, lib = ask("GET", "/library.json?subject=projects/TRD")
    check("and no other subject's library does", "meeting" not in lib
          and not [d for d in lib.get("documents", []) if "meeting" in d])
    prov = briefs.provenance(base)
    nums = [n["value"] for n in prov.get("numbers", [])]
    check("a number no source gives is listed beside the deck, with its slide",
          "0.713" in nums and any(n["frame"] == 2 for n in prov["numbers"]))
    check("and the ones the sources give are not", "0.602" not in nums and "0.594" not in nums)
    check("a figure the board copied is not flagged", prov.get("figures") == [])
    check("the writeup record says done", writeups.state(sessions.repo(sid, base), body.get("id")) == "done")
    docs = [d for d in library.documents(MEET) if d.get("artifact") == "docs/meeting"]
    check("the deck is a document in the Meetings library", len(docs) == 1)

    # ---- the ignore rules, in this repository ------------------------------------
    rel = "projects/Meetings/docs/meeting/"
    ignored = [n for n in ("_brief.md", "_brief.json", "figures/x.png", "meeting.pdf",
                           "_provenance.json", "meeting.out")
               if subprocess.run(["git", "check-ignore", "-q", rel + n], cwd=REPO).returncode == 0]
    check("the deck's brief, figures, PDF and sidecar are ignored by root rules",
          len(ignored) == 6, ignored)
    check("and its source and doc.json are not",
          subprocess.run(["git", "check-ignore", "-q", rel + "meeting.tex"], cwd=REPO).returncode
          and subprocess.run(["git", "check-ignore", "-q", rel + "doc.json"], cwd=REPO).returncode)
    out = subprocess.run(["git", "ls-files", "*.out"], cwd=REPO, stdout=subprocess.PIPE,
                         universal_newlines=True).stdout
    check("no *.out is tracked", out.strip() == "", out)
    meet = json.load(open(os.path.join(REPO, "projects", "Meetings", "tutorboard.json")))
    check("projects/Meetings is tracked, and holds patient data",
          meet == {"name": "Meetings", "phi": True}
          and os.path.isfile(os.path.join(REPO, "projects", "Meetings", "TUTOR.md")))

    # ---- a deck with a brief is revised against it ---------------------------------
    status, said_ = ask("POST", "/library/feedback?subject=projects/Meetings",
                        {"document": "meeting", "text": "Add the ROC curve."})
    last = inbox(sid)[-1]["text"] if inbox(sid) else ""
    check("feedback on the deck is a revision in the Meetings session, pointing at the "
          "brief and board deckfig",
          status == 200 and last.startswith("[revise]") and "docs/meeting/_brief.md" in last
          and "ADDED is the feedback" in last and "board deckfig docs/meeting" in last, last)
    check("the brief sentence is only there when it is asked for",
          sense.revise_sense("a.pdf", "f.md") ==
          sense.REVISE_SENSE % ("a.pdf", "f.md") + sense.MEASURE_SENSE + sense.RULE_SENSE)

    # Ink on a deck with a brief: a round that came back wipes what it delivered.
    meet_repo = registry.sessionless(MEET, base)

    def ink(key):
        write(writing_route.ann_path(meet_repo, key),
              json.dumps({"card": key, "sent": False,
                          "strokes": [{"p": [[0.1, 0.1], [0.2, 0.2]]}]}))
        write(writing_route.ann_path(meet_repo, key, ".png"), b"\x89PNG\r\n\x1a\n")

    ink("doc/meeting/p1")
    ink("doc/meeting/p2")
    library.forget()
    first = library.write_note(meet_repo, "meeting", "")
    check("the first round carries both marked slides", first.get("ok") and first.get("marks") == 2,
          first)
    with open(first["path"], "a", encoding="utf-8") as fh:
        fh.write("\n## What was changed\n\nThe ROC curve is on slide 2.\n")
    ink("doc/meeting/p2")
    library.forget()
    st = [d for d in library.status(meet_repo)["documents"] if d["id"] == "meeting"]
    check("the library's payload says one slide is waiting",
          st and st[0]["marks"]["pages"] == 1 and st[0]["marks"]["waiting"] == 1, st)
    view = library.ink(meet_repo, library.find(MEET, "meeting"))
    check("once the round lands, only ink drawn since is on the deck",
          list(view) == ["doc/meeting/p2"], list(view))

    # ---- board deckfig --------------------------------------------------------
    env = dict(os.environ, TUTORBOARD_SESSION=sessions.path(sid, base))

    def deckfig(*args):
        p = subprocess.run([sys.executable, BOARD, "deckfig"] + list(args), cwd=base,
                           env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, timeout=120)
        return p.returncode, p.stdout.strip(), p.stderr.strip()

    code, out, err = deckfig("docs/meeting", "projects/TRD", "old roc")
    check("board deckfig copies a catalogued figure by a word of its name",
          code == 0 and out.startswith("figures/projects-trd--")
          and os.path.isfile(os.path.join(DECK, out)), (out, err))
    code, _, err = deckfig("docs/meeting", "projects/PW", "draft")
    check("and refuses a subject the deck was not made from", code == 1 and "made from" in err, err)
    code, _, err = deckfig("docs", "projects/TRD", "old roc")
    check("and a directory with no brief", code == 1 and "_brief.json" in err, err)

    # ---- asking again replaces it and clears its ink ---------------------------
    write(os.path.join(base, ".ink", writing_route.ann_file("doc/meeting/p1") + ".json"),
          json.dumps({"card": "doc/meeting/p1", "strokes": [{"p": [[0, 0]]}]}))
    status, body2 = ask("POST", "/meeting", {"since": "7d", "items": ["projects/TRD"]})
    check("asking again goes to the same Meetings session",
          status == 200 and body2.get("session") == sid, body2)
    check("ASKING TWICE LEAVES ONE doc.json, and the old deck is gone until the "
          "writer writes the new one",
          files("doc.json") == [os.path.join(DECK, "doc.json")] and files("meeting.tex") == []
          and not os.path.exists(os.path.join(MEET, "docs", "meeting-2")))
    check("and its ink is cleared, the deck page's and the library's",
          not artifacts.ink_files(os.path.join(MEET, ".ink"), ["meeting"])
          and not artifacts.ink_files(os.path.join(base, ".ink"), ["meeting"]))
    built(deck_tex(frame("Findings", "\\href{http://compute-node.tail0c6c62.ts.net:8937}"
                         "{The findings}")))
    check("and ONE meeting.tex once it is written", len(files("meeting.tex")) == 1)
    read_all(sid)
    got = deck_rec()
    check("a link to the tailnet under other words refuses the deck",
          got.get("state") == "did not land" and "ts.net" in got.get("why", ""), got)

    # ---- a turn that ended with nothing -----------------------------------------
    ask("POST", "/meeting", {"since": "7d", "items": ["projects/TRD"]})
    read_all(sid)
    quiet, artifacts.QUIET = artifacts.QUIET, 0
    try:
        got = deck_rec()
    finally:
        artifacts.QUIET = quiet
    check("a turn that ended without a deck did not land, and says so",
          got.get("state") == "did not land" and "without writing" in got.get("why", ""), got)

    # ---- the command line ------------------------------------------------------
    p = subprocess.run([sys.executable, BOARD, "meeting", "--since", "7d", "--subject",
                        "projects/TRD", "--print"], cwd=base, env=dict(os.environ),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, timeout=120)
    check("`board meeting --print` prints the brief", p.returncode == 0
          and "BODY-ONE-MARKER" in p.stdout, p.stderr)
    httpd.shutdown()
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("one engine briefs the period, and the deck is one artifact in "
      "projects/Meetings, replaced each time")
