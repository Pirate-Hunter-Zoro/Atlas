#!/usr/bin/env python3
"""The session store: new, end, reopen, delete, and a Repo serving a session.

    python3 test/sessions.py

Everything runs in a temp Atlas (`TUTORBOARD_COURSES`) with its own git
repository and a temp trash. Nothing here touches the real `sessions/`.

  * `new` makes `sessions/<stamp>/` with session.json as specified and the
    layout of section 2; a second `new` in the same second takes `-2`, and
    neither touches the other.
  * A card, a slate page and a turn in one session survive a second `new`,
    and `next_turn_id` continues in the first. Only `end` sets `ended`.
  * A Repo serves a session: the Atlas root while unbound, the subject's root
    when bound; `hw` appears when `writeup` is a homework set, so `board hw`
    works on it.
  * `end` commits the subject's TUTOR.md and the artifacts listing the session,
    and nothing else; `delete` moves the directory to the trash.
  * `/sessions/` is ignored, and the pre-commit hook refuses
    `git add -f sessions/x/cards/0001.md`.
  * The meeting gather reads an ended session from the store.
  * `bind` sets `subject` with a non-waking `[bind]` line and files nothing;
    `bind --create` makes a subject in one commit, with the PHI ignore stanza
    for a patient-data project, and refuses `../x`, `/abs` and `research/x`.
  * `file` moves an upload into the bound subject and its ink to
    `<subject>/.ink/`, re-keyed: the old keys are gone and the new ones load.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_DIR = os.path.dirname(HERE)
ATLAS = os.path.dirname(BOARD_DIR)
BOARD = os.path.join(BOARD_DIR, "bin", "board")
sys.path.insert(0, BOARD_DIR)

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


def write(path, text, mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if isinstance(text, bytes) else "w") as fh:
        fh.write(text)
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def tree(root):
    out = {}
    for here, _, files in os.walk(root):
        for f in files:
            p = os.path.join(here, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root)] = fh.read()
    return out


base = os.path.realpath(tempfile.mkdtemp(prefix="tutor-sessions-"))
trash = os.path.realpath(tempfile.mkdtemp(prefix="tutor-sessions-trash-"))
scratch = os.path.realpath(tempfile.mkdtemp(prefix="tutor-sessions-hook-"))
os.environ["TUTORBOARD_COURSES"] = base
os.environ["TUTORBOARD_TRASH"] = trash
os.environ.pop("TUTORBOARD_SESSION", None)

from tutorboard import gitops, meeting, paths, sessions, sittings   # noqa: E402
from tutorboard.course import homework                              # noqa: E402
from tutorboard.course import repo as course_repo                   # noqa: E402
from tutorboard.lesson import state as lesson_state                 # noqa: E402
from tutorboard.lesson import turns as lesson_turns                 # noqa: E402

check("TUTORBOARD_TRASH moves the trash, so no delete here reaches the real one",
      paths.TRASH == trash)


def git(*args, **kw):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    env.pop("TUTORBOARD_TURN", None)
    return subprocess.run(["git"] + list(args), cwd=kw.get("cwd", base), env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)


def board(args, session=None, cwd=None, stdin=""):
    env = dict(os.environ)
    env.pop("TUTORBOARD_SESSION", None)
    if session:
        env["TUTORBOARD_SESSION"] = session
    p = subprocess.run([sys.executable, BOARD] + list(args), cwd=cwd or base,
                       env=env, input=stdin, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True,
                       timeout=120)
    return p.returncode, p.stdout


try:
    # ---- a fixture Atlas: one course with a homework set, one project ------
    galois = os.path.join(base, "courses", "Galois")
    hw_rel = "chapters/ch07-splitting/homework/ch07-homework.tex"
    write(os.path.join(galois, "tutorboard.json"), json.dumps({"name": "Galois"}))
    write(os.path.join(galois, hw_rel),
          "\\begin{problem}{7.1}\nShow it.\n\\end{problem}\n"
          "% ===== SOLUTION 7.1 =====\n% ===== END SOLUTION 7.1 =====\n")
    write(os.path.join(galois, "chapters/ch07-splitting/notes.tex"), "notes\n")
    write(os.path.join(galois, "TUTOR.md"), "# Where things are\n")
    proj = os.path.join(base, "projects", "Proj")
    write(os.path.join(proj, "tutorboard.json"),
          json.dumps({"name": "Proj", "phi": False}))
    write(os.path.join(base, ".gitignore"), "/sessions/\n")
    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "fixture")

    # ---- new ---------------------------------------------------------------
    now = time.time()
    a = sessions.new(base=base, now=now)
    a_dir = sessions.path(a["id"], base)
    check("new makes sessions/<YYYYMMDD-HHMMSS>/ under the Atlas root",
          a_dir == os.path.join(base, "sessions",
                                time.strftime("%Y%m%d-%H%M%S", time.localtime(now))))
    want = {"id": a["id"], "title": None, "subject": None, "mode": "teach",
            "opened": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
            "ended": None, "writeup": None, "seen": 0, "code": None,
            "view": "board"}
    on_disk = json.load(open(os.path.join(a_dir, "session.json")))
    check("session.json is exactly the specified record, unbound, in teach",
          on_disk == want, on_disk)
    check("with the layout of section 2",
          all(os.path.isdir(os.path.join(a_dir, d)) for d in
              ("cards", "slate", "answers", "inbox", "uploads", "text",
               "annotations"))
          and not os.path.exists(os.path.join(a_dir, "archive")))

    # ---- a card, a slate page, a turn; then a second new -------------------
    code, out = board(["write", "lesson", "Opening"], session=a_dir,
                      stdin="The first card.\n")
    cards = sorted(os.listdir(os.path.join(a_dir, "cards")))
    check("board write, run in the session, writes its card there",
          code == 0 and len(cards) == 1 and cards[0].startswith("0001-"), out)
    check("and leaves the Atlas root without a live/",
          not os.path.exists(os.path.join(base, "live")))
    ra = sessions.repo(a["id"], base)
    check("a Repo of an unbound session works at the Atlas root",
          ra.root == base and ra.session == a_dir and ra.stored)
    check("and its uploads sit at the session's top",
          ra.uploads == os.path.join(a_dir, "uploads"))
    write(os.path.join(ra.slate, "page-01.json"),
          json.dumps({"page": 1, "w": 10, "h": 10, "strokes": [[1, 2]]}))
    write(os.path.join(ra.slate, "page-01.png"), b"\x89PNG fake")
    tid = lesson_turns.next_turn_id(ra)
    write(os.path.join(ra.answers, "%s-r1.png" % tid), b"\x89PNG fake")
    with open(ra.turns_path, "a") as fh:
        fh.write(json.dumps({"id": tid, "rev": 1, "kind": "ink"}) + "\n")
    lesson_turns.bump_turn_hwm(ra, tid)
    before = tree(a_dir)

    b = sessions.new(base=base, now=now)
    b_dir = sessions.path(b["id"], base)
    check("a second new in the same second takes -2",
          b["id"] == a["id"] + "-2" and b_dir and b_dir != a_dir)
    check("and the first session keeps every file, byte for byte",
          tree(a_dir) == before)
    check("next_turn_id continues in the first session",
          tid == "t0001" and lesson_turns.next_turn_id(
              sessions.repo(a["id"], base)) == "t0002")
    check("while the second starts its own",
          lesson_turns.next_turn_id(sessions.repo(b["id"], base)) == "t0001"
          and os.listdir(os.path.join(b_dir, "cards")) == [])
    code, out = board(["archive"], session=a_dir)
    check("board archive in a session refuses and moves nothing",
          code == 1 and tree(a_dir) == before, out)
    check("neither is ended: only end sets ended",
          sessions.get(a["id"], base)["ended"] is None
          and sessions.get(b["id"], base)["ended"] is None)
    check("all lists both, newest first",
          [s["id"] for s in sessions.all(base)] == [b["id"], a["id"]])
    check("an id is matched, never joined: ../ and junk are no session",
          sessions.path("../" + a["id"], base) is None
          and sessions.path("20261008-120000/../x", base) is None
          and sessions.get("nope", base) is None)

    # ---- a bound session, its writeup and `board hw` ------------------------
    c = sessions.new("Ch 7", base=base, now=now + 5)
    c_dir = sessions.path(c["id"], base)
    rc = sessions.repo(c["id"], base)
    rc.set_state(subject="courses/Galois")
    rc = sessions.repo(c["id"], base)
    check("bound, a session's Repo works in the subject's root",
          rc.root == galois and rc.session == c_dir)
    st = rc.state()
    check("with no writeup, there is no hw", "hw" not in st and st["writeup"] is None)
    code, out = board(["hw", "use", "ch07"], session=c_dir)
    rec = json.load(open(os.path.join(c_dir, "session.json")))
    check("board hw use writes the set as the session's writeup",
          code == 0 and rec["writeup"] == "courses/Galois/" + hw_rel
          and "hw" not in rec, (code, out, rec))
    check("and state() exposes it as the legacy hw key",
          sessions.repo(c["id"], base).state().get("hw") == hw_rel)
    code, out = board(["hw", "status"], session=c_dir)
    check("board hw status in the session resolves ch07",
          code == 0 and out.startswith("ch07") and "7.1" in out, out)
    load = lesson_state.load_hw(sessions.repo(c["id"], base))
    check("and the board's payload finds the same set",
          load and load.get("name") == "ch07")
    rc.set_state(writeup="courses/Galois/chapters/ch07-splitting/notes.tex")
    check("a writeup that is not a homework set gives no hw",
          "hw" not in sessions.repo(c["id"], base).state())
    rc.set_state(hw=None)
    rec = json.load(open(os.path.join(c_dir, "session.json")))
    check("clearing hw leaves writeup null, not missing",
          "writeup" in rec and rec["writeup"] is None)
    check("homework.find answers on a session state with no chapter",
          homework.find(galois, sessions.repo(c["id"], base).state()) is not None)
    code, out = board(["hw", "status"], session=b_dir)
    check("board hw in an unbound session says to bind first",
          code == 1 and "bind" in out, out)

    # ---- end, reopen ---------------------------------------------------------
    write(os.path.join(galois, "TUTOR.md"), "# Where things are\n\nch07 now.\n")
    doc = os.path.join(galois, "docs", "ch7-notes")
    write(os.path.join(doc, "doc.json"),
          json.dumps({"title": "Ch 7", "source": "ch7.tex",
                      "sessions": [c["id"]], "asked_at": now}))
    write(os.path.join(doc, "ch7.tex"), "\\documentclass{article}\n")
    other = os.path.join(galois, "docs", "elsewhere")
    write(os.path.join(other, "doc.json"),
          json.dumps({"title": "x", "source": "x.tex", "sessions": ["other"],
                      "asked_at": now}))
    write(os.path.join(galois, "stray.md"), "not the session's\n")
    head = git("rev-parse", "HEAD").stdout.strip()
    rec, ok, said = sessions.end(c["id"], base=base, now=now + 60)
    files = git("show", "--name-only", "--pretty=format:", "HEAD").stdout.split()
    check("end sets ended", ok and rec["ended"] ==
          time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now + 60))
          and sessions.get(c["id"], base)["ended"] == rec["ended"], said)
    check("and makes one commit: the subject's TUTOR.md and the artifact "
          "listing this session",
          git("rev-list", "--count", "%s..HEAD" % head).stdout.strip() == "1"
          and sorted(files) == [
              "courses/Galois/TUTOR.md", "courses/Galois/docs/ch7-notes/ch7.tex",
              "courses/Galois/docs/ch7-notes/doc.json"], files)
    check("and nothing else: another artifact and a stray file stay out",
          "?? courses/Galois/docs/elsewhere/" in git("status", "--porcelain").stdout
          and "?? courses/Galois/stray.md" in git("status", "--porcelain").stdout)
    check("no session file is ever committed",
          "sessions" not in git("ls-files").stdout)
    sessions.reopen(c["id"], base)
    check("reopen clears ended", sessions.get(c["id"], base)["ended"] is None)
    head = git("rev-parse", "HEAD").stdout.strip()
    rec, ok, said = sessions.end(b["id"], base=base)
    check("ending an unbound session commits nothing",
          ok and rec["ended"] and git("rev-parse", "HEAD").stdout.strip() == head)

    # ---- the CLI ------------------------------------------------------------
    code, out = board(["session", "new", "From", "the", "CLI"], cwd=ATLAS)
    new_id = out.split()[0] if out.split() else ""
    check("board session new prints the id, in the store TUTORBOARD_COURSES "
          "names", code == 0 and sessions.get(new_id, base)
          and sessions.get(new_id, base)["title"] == "From the CLI", out)
    code, out = board(["session", "show"], session=sessions.path(new_id, base))
    check("board session show, in the session, prints its session.json",
          code == 0 and json.loads(out)["id"] == new_id, out)
    code, out = board(["session", "end", new_id])
    check("board session end ends it",
          code == 0 and sessions.get(new_id, base)["ended"], out)
    code, out = board(["session", "end"])
    check("and end without an id is refused", code == 2)
    code, out = board(["session", "delete", new_id])
    moved = [h for h, _, fs in os.walk(trash)
             if os.path.basename(h) == new_id and "session.json" in fs]
    check("board session delete moves the directory to the trash",
          code == 0 and sessions.get(new_id, base) is None and moved
          and os.path.isfile(os.path.join(moved[0], "session.json")), out)
    code, out = board(["session", "show", "nope"])
    check("an unknown id is a sentence and exit 1", code == 1 and "nope" in out)
    gone = sessions.delete(b["id"], base=base)
    check("delete is a move: the session is whole in the trash",
          os.path.isfile(os.path.join(gone, "session.json"))
          and not os.path.exists(b_dir) and os.path.isdir(a_dir))

    # ---- the meeting gather reads an ended session ----------------------------
    d = sessions.new("Splitting fields", base=base, now=now - 3 * 3600)
    d_dir = sessions.path(d["id"], base)
    sessions.repo(d["id"], base).set_state(subject="courses/Galois")
    write(os.path.join(d_dir, "cards", "0001-lesson.md"),
          "---\nkind: lesson\n---\nA card.\n")
    write(os.path.join(d_dir, "cards", "0002-lesson.md"),
          "---\nkind: lesson\n---\nAnother.\n")
    sessions.end(d["id"], base=base, now=now - 3600)
    sittings.forget()
    blocks, _, why = meeting.blocks_for(base, ["courses/Galois"], now - 6 * 3600)
    held = [r["id"] for blk in blocks for r in blk["sittings"]]
    check("the meeting gather's session walk reads a fixture ended session",
          not why and "courses/Galois@" + d["id"] in held, (why, held))
    row = [r for blk in blocks for r in blk["sittings"]
           if r["id"] == "courses/Galois@" + d["id"]]
    check("as a filed row of its two cards, titled by the session",
          row and row[0]["live"] is False and row[0]["cards"] == 2
          and "Splitting fields" in row[0]["label"])

    # ---- bind, and bind --create ----------------------------------------------
    from tutorboard.lesson import notes as lesson_notes             # noqa: E402
    from tutorboard.server.routes import writing                    # noqa: E402
    e = sessions.new("Generic", base=base, now=now + 100)
    e_dir = sessions.path(e["id"], base)
    write(os.path.join(e_dir, "uploads", "slides.pdf"), b"%PDF-1.4 fake\n")
    up_before = sorted(os.listdir(os.path.join(e_dir, "uploads")))

    def inbox(where):
        try:
            with open(os.path.join(where, "inbox", "messages.jsonl")) as fh:
                return [json.loads(l) for l in fh if l.strip()]
        except OSError:
            return []

    code, out = board(["bind", "courses/Nowhere"], session=e_dir)
    check("bind to a subject that is not there is refused, naming --create",
          code == 1 and "--create" in out
          and sessions.get(e["id"], base)["subject"] is None, out)
    code, out = board(["bind", "courses/Galois"], session=e_dir)
    lines = inbox(e_dir)
    check("bind sets subject, validated against subjects.all()",
          code == 0 and sessions.get(e["id"], base)["subject"] == "courses/Galois",
          out)
    check("and appends one [bind] line that wakes nothing (written read)",
          len(lines) == 1 and lines[0]["text"] == "[bind] courses/Galois"
          and lines[0]["read"] is True and lines[0]["signal"] == "bind", lines)
    code, out = board(["inbox"], session=e_dir)
    check("so board inbox, what a turn waits on, has nothing new",
          code == 0 and "inbox empty" in out, out)
    check("and bind files nothing: the upload stays in uploads/",
          sorted(os.listdir(os.path.join(e_dir, "uploads"))) == up_before)
    check("a bound session's Repo works in the subject",
          sessions.repo(e["id"], base).root == galois)
    code, out = board(["bind", "Galois"], session=e_dir)
    check("binding again to the same subject writes no second line",
          code == 0 and len(inbox(e_dir)) == 1, out)

    head = git("rev-parse", "HEAD").stdout.strip()
    f = sessions.new("Fresh", base=base, now=now + 110)
    f_dir = sessions.path(f["id"], base)
    code, out = board(["bind", "courses/Test", "--create"], session=f_dir)
    files = git("show", "--name-only", "--pretty=format:", "HEAD").stdout.split()
    check("bind courses/Test --create makes one commit",
          code == 0 and git("rev-list", "--count", "%s..HEAD" % head)
          .stdout.strip() == "1", out)
    check("holding the directory's tutorboard.json and TUTOR.md, nothing else",
          sorted(files) == ["courses/Test/TUTOR.md",
                            "courses/Test/tutorboard.json"], files)
    cfg = json.load(open(os.path.join(base, "courses", "Test", "tutorboard.json")))
    check("a course is phi false", cfg == {"name": "Test", "phi": False}, cfg)
    tutor = open(os.path.join(base, "courses", "Test", "TUTOR.md")).read()
    check("TUTOR.md is the skeleton of the four sections, in order",
          [l[3:] for l in tutor.splitlines() if l.startswith("## ")]
          == ["Where things are", "Now", "Open decisions", "Done recently"], tutor)
    check("and the session is bound to the new course",
          sessions.get(f["id"], base)["subject"] == "courses/Test")

    g = sessions.new("Patients", base=base, now=now + 120)
    g_dir = sessions.path(g["id"], base)
    code, out = board(["bind", "projects/New", "--create"], session=g_dir)
    check("a project without --phi is refused, asking about patient data",
          code == 1 and "--phi" in out
          and not os.path.exists(os.path.join(base, "projects", "New")), out)
    head = git("rev-parse", "HEAD").stdout.strip()
    code, out = board(["bind", "projects/New", "--create", "--phi", "yes"],
                      session=g_dir)
    check("git check-ignore -q projects/New/phi/x succeeds right after "
          "bind projects/New --create --phi yes",
          code == 0 and git("check-ignore", "-q", "projects/New/phi/x")
          .returncode == 0, out)
    check("and so do results/ and .env",
          git("check-ignore", "-q", "projects/New/results/r.csv").returncode == 0
          and git("check-ignore", "-q", "projects/New/.env").returncode == 0)
    files = git("show", "--name-only", "--pretty=format:", "HEAD").stdout.split()
    check("in one commit with the .gitignore, tutorboard.json and TUTOR.md",
          git("rev-list", "--count", "%s..HEAD" % head).stdout.strip() == "1"
          and sorted(files) == ["projects/New/.gitignore", "projects/New/TUTOR.md",
                                "projects/New/tutorboard.json"], files)
    check("tutorboard.json says phi true",
          json.load(open(os.path.join(base, "projects", "New", "tutorboard.json")))
          ["phi"] is True)
    head = git("rev-parse", "HEAD").stdout.strip()
    for bad in ("../x", "/abs", "research/x", "courses/Test", "courses/a/b"):
        code, out = board(["bind", bad, "--create", "--phi", "no"], session=g_dir)
        check("--create refuses %s" % bad,
              code == 1 and out.startswith("board bind: ")
              and "Traceback" not in out, out)
    check("and none of them committed or made anything",
          git("rev-parse", "HEAD").stdout.strip() == head
          and not os.path.exists(os.path.join(base, "research"))
          and not os.path.exists(os.path.join(os.path.dirname(base), "x"))
          and not os.path.exists("/abs"))
    code, out = board(["bind", "projects/Plain Data", "--create", "--phi", "no"])
    check("with no session, --create only makes the subject, slugified",
          code == 0 and os.path.isfile(os.path.join(
              base, "projects", "Plain-Data", "tutorboard.json"))
          and not os.path.exists(os.path.join(
              base, "projects", "Plain-Data", ".gitignore")), out)

    # ---- file, and the ink that follows ---------------------------------------
    code, out = board(["file", "slides.pdf"],
                      session=sessions.path(sessions.new(base=base)["id"], base))
    check("file in an unbound session is refused",
          code == 1 and "bind it first" in out, out)
    old_id = sessions.ink_ident("uploads/slides.pdf")
    keys = ["doc/%s/p%d" % (old_id, n) for n in (1, 2)]
    notes_dir = os.path.join(e_dir, "annotations")
    stroke = {"pts": [[1, 2], [3, 4]], "w": 2}
    for k in keys:
        stem = writing.ann_file(k)
        write(os.path.join(notes_dir, stem + ".json"),
              json.dumps({"card": k, "strokes": [stroke], "sent": False}))
        write(os.path.join(notes_dir, stem + ".png"), b"\x89PNG ink")
    write(os.path.join(notes_dir, writing.ann_file(keys[0]) + ".gone"),
          json.dumps({"card": keys[0], "at": 1, "strokes": [stroke]}))
    write(os.path.join(notes_dir, "0001.json"),
          json.dumps({"card": "0001", "strokes": [stroke]}))
    other_key = "doc/%s/p1" % sessions.ink_ident("uploads/other.pdf")
    write(os.path.join(notes_dir, writing.ann_file(other_key) + ".json"),
          json.dumps({"card": other_key, "strokes": [stroke]}))
    for bad in ("../outside", "/tmp/x", ".ink/x.pdf", "phi/x.pdf",
                "results/x.pdf"):
        code, out = board(["file", "slides.pdf", bad], session=e_dir)
        check("file refuses %s" % bad,
              code == 1 and out.startswith("board file: ")
              and "Traceback" not in out, out)
    code, out = board(["file", "nope.pdf"], session=e_dir)
    check("file refuses a name that is not an upload", code == 1, out)
    check("and a refusal moves nothing",
          os.path.isfile(os.path.join(e_dir, "uploads", "slides.pdf"))
          and not os.path.exists(os.path.join(galois, "materials")))

    head = git("rev-parse", "HEAD").stdout.strip()
    code, out = board(["file", "slides.pdf"], session=e_dir)
    new_id = sessions.ink_ident("materials/slides.pdf")
    new_keys = ["doc/%s/p%d" % (new_id, n) for n in (1, 2)]
    check("file moves the upload into materials/ by default",
          code == 0 and os.path.isfile(os.path.join(galois, "materials", "slides.pdf"))
          and not os.path.exists(os.path.join(e_dir, "uploads", "slides.pdf")), out)
    left = os.listdir(notes_dir)
    check("the old ink keys are gone from the session",
          not any(writing.ann_file(k) in n for k in keys for n in left), left)
    check("while card ink and another upload's ink stay",
          "0001.json" in left
          and writing.ann_file(other_key) + ".json" in left, left)

    class InkDrawer(object):
        notes = os.path.join(galois, ".ink")
    loaded = lesson_notes.load_notes(InkDrawer)
    check("the new keys load from <subject>/.ink/",
          sorted(loaded) == new_keys and loaded[new_keys[0]] == [stroke], loaded)
    check("with their pictures and the buried strokes, re-keyed",
          all(os.path.isfile(writing.png_path(InkDrawer, k)) for k in new_keys)
          and writing.gone_of(InkDrawer, new_keys[0]) == [stroke])
    check("filing commits nothing",
          git("rev-parse", "HEAD").stdout.strip() == head)
    filed = [l for l in inbox(e_dir) if l.get("signal") == "filed"]
    check("and leaves a [filed] line that wakes nothing",
          len(filed) == 1 and filed[0]["read"] is True
          and "courses/Galois/materials/slides.pdf" in filed[0]["text"], filed)

    write(os.path.join(e_dir, "uploads", "scan.png"), b"\x89PNG scan")
    code, out = board(["file", "uploads/scan.png", "notes/ch7-scan.png",
                       "--session", e["id"]])
    check("file takes a relative path inside the subject and --session",
          code == 0 and os.path.isfile(os.path.join(galois, "notes", "ch7-scan.png")),
          out)
    write(os.path.join(e_dir, "uploads", "slides.pdf"), b"%PDF again\n")
    code, out = board(["file", "slides.pdf"], session=e_dir)
    check("and refuses a destination already taken",
          code == 1 and "exists" in out
          and os.path.isfile(os.path.join(e_dir, "uploads", "slides.pdf")), out)

    # ---- the ignore rule and the commit-time gate -----------------------------
    shutil.copytree(os.path.join(ATLAS, ".githooks"), os.path.join(scratch, ".githooks"))
    shutil.copyfile(os.path.join(ATLAS, ".gitignore"), os.path.join(scratch, ".gitignore"))
    shutil.copytree(os.path.join(BOARD_DIR, "tutorboard"),
                    os.path.join(scratch, "board", "tutorboard"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    write(os.path.join(scratch, "README.md"), "scratch\n")
    git("init", "-q", cwd=scratch)
    git("config", "core.hooksPath", os.path.join(scratch, ".githooks"), cwd=scratch)
    git("add", "-A", cwd=scratch)
    p = git("commit", "-q", "-m", "scratch", cwd=scratch)
    check("the scratch clone commits cleanly through the hook", p.returncode == 0,
          p.stderr)
    write(os.path.join(scratch, "sessions", "x", "cards", "0001.md"), "a card\n")
    check("/sessions/ is ignored",
          git("check-ignore", "-q", "sessions/x/cards/0001.md",
              cwd=scratch).returncode == 0)
    git("add", "-f", "sessions/x/cards/0001.md", cwd=scratch)
    p = git("commit", "-q", "-m", "a session", cwd=scratch)
    check("git add -f sessions/x/cards/0001.md is refused by the pre-commit hook",
          p.returncode != 0 and "sessions/x/cards/0001.md" in p.stderr, p.stderr)
    ok, said = gitops.commit(scratch, ["sessions/x/cards/0001.md"], "via gitops")
    check("and so is a gitops commit naming it", not ok, said)
finally:
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(trash, ignore_errors=True)
    shutil.rmtree(scratch, ignore_errors=True)

print()
if fails:
    print("%d failed" % len(fails))
    sys.exit(1)
print("all passed")
