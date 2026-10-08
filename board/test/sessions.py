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
