#!/usr/bin/env python3
"""import_live: each workspace's live/ becomes one open session.

    python3 test/import_live.py

A fixture workspace holding one of every live/ entry is imported into a temp
Atlas, then reversed; nothing here touches a real live/ or the real sessions/.

  * --dry-run changes nothing and prints a plan.
  * session.json: title, mode from the stance, writeup from `hw`, seen,
    opened; bound to the post-merge subject.
  * Every entry lands where HANDOFF T14's table says: cards (old links
    rewritten), a "Carried over" note card from NEXT.md and handoffs/, the
    inbox with its read marks, uploads, card ink in the session and document
    ink in `<subject>/.ink/`, marked/ into materials/, job state into
    `<subject>/relay/state/`, agent.json idle with `owed` kept, archive/ left,
    the rest under imported/. `next_turn_id` continues.
  * `board writeup status` in an imported course session resolves its set.
  * A live/ with no cards, turns or messages makes no session.
  * --reverse restores every byte, the subject's registry included.
  * Where ~/Archive/atlas-migration/2026-10-07/live-dirs.tgz exists, the same
    on copies of Galois-Theory, Probability and TRD-EHR extracted from it.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_DIR = os.path.dirname(HERE)
BOARD = os.path.join(BOARD_DIR, "bin", "board")
SCRIPT = os.path.join(BOARD_DIR, "scripts", "import-live.py")
TGZ = os.path.expanduser("~/Archive/atlas-migration/2026-10-07/live-dirs.tgz")
sys.path.insert(0, BOARD_DIR)

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if isinstance(text, bytes) else "w") as fh:
        fh.write(text)


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def snapshot(root):
    """{relpath: digest} for files, {relpath/: ""} for directories."""
    out = {}
    for here, dirs, files in os.walk(root):
        for d in dirs:
            out[os.path.relpath(os.path.join(here, d), root) + "/"] = ""
        for f in files:
            p = os.path.join(here, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root)] = hashlib.sha1(fh.read()).hexdigest()
    return out


def lines(path):
    try:
        return [json.loads(x) for x in read(path).splitlines() if x.strip()]
    except OSError:
        return []


def unread(path):
    return sum(1 for r in lines(path) if not r.get("read"))


def cards(d):
    from tutorboard.sessions import CARD_NAME
    try:
        return sorted(n for n in os.listdir(d) if CARD_NAME.match(n))
    except OSError:
        return []


def run(*argv, **env):
    e = dict(os.environ)
    e.update(env)
    return subprocess.run([sys.executable] + list(argv), stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True,
                          env=e)


tmp = os.path.realpath(tempfile.mkdtemp(prefix="tutor-import-live-"))
os.environ["TUTORBOARD_COURSES"] = os.path.join(tmp, "atlas")
os.environ["TUTORBOARD_TRASH"] = os.path.join(tmp, "trash")
os.environ.pop("TUTORBOARD_SESSION", None)

from tutorboard import sessions                                     # noqa: E402
from tutorboard.course import repo as course_repo                   # noqa: E402
from tutorboard.lesson import turns                                 # noqa: E402

atlas = os.path.join(tmp, "atlas")
ws = os.path.join(atlas, "research", "Demo")
live = os.path.join(ws, "live")
home = os.path.join(atlas, "projects", "Demo")

# --- the fixture: one of every live/ entry --------------------------------------
write(os.path.join(ws, "tutorboard.json"), json.dumps({"name": "Demo Project"}))
write(os.path.join(ws, "homework", "hw01", "hw01.tex"), "\\section*{1}\n")
write(os.path.join(live, "state.json"), json.dumps({
    "course": "Demo", "chapter": "ch02", "hw": "homework/hw01/hw01.tex",
    "stance": "do", "opened": "2026-10-01 09:30"}))
write(os.path.join(live, ".seen.json"), json.dumps({"at": 123.5}))
write(os.path.join(live, "cards", "0001-first.md"),
      "---\nkind: lesson\ntitle: first\n---\nSee [this](#/w/Research/Demo/card/0002)"
      " and [that](#/w/Courses/Other/card/0002).\n")
write(os.path.join(live, "cards", "0002-second.md"),
      "---\nkind: question\n---\nWhat is 2 + 2?\n")
write(os.path.join(live, "slate", "page-01.json"), "{}")
write(os.path.join(live, "answers", "t0001-r1.png"), b"\x89PNG")
os.makedirs(os.path.join(live, "text"))
write(os.path.join(live, "turns.jsonl"),
      '{"id": "t0001", "rev": 1, "t": 100.0}\n{"id": "t0002", "rev": 1, "t": 200.0}\n')
write(os.path.join(live, ".turnseq"), "7\n")
write(os.path.join(live, "inbox", "messages.jsonl"),
      '{"id": "t0001", "read": true, "text": "a"}\n'
      '{"id": "t0002", "read": false, "text": "b"}\n')
write(os.path.join(live, "inbox", "uploads", "notes.pdf"), b"%PDF-1.4")
write(os.path.join(live, "inbox", "stray.txt"), "stray")
write(os.path.join(live, "annotations", "0001.json"), '{"card": "0001"}')
write(os.path.join(live, "annotations", "0001.png"), b"png")
write(os.path.join(live, "annotations", "0001.dir.png"), b"dir")
write(os.path.join(live, "annotations", "doc-paper-p1-0a1b2c3d.json"),
      '{"card": "doc/paper/p1"}')
write(os.path.join(live, "annotations", "odd.json"), "{}")
write(os.path.join(live, "directions", "p1.png"), b"dir")
write(os.path.join(live, "NEXT.md"), "Next: finish problem 3.\n")
write(os.path.join(live, "handoffs", "hw01.md"), "hw01 is done; see [card](#/w/research/Demo/card/0001).\n")
for name in ("hw.json", "push.json", ".board.json", "board.log", "BRIEF.md",
             "TEACHING.md"):
    write(os.path.join(live, name), name)
os.makedirs(os.path.join(live, "tikzcache"))
write(os.path.join(live, "paper", "x-1.png"), b"page")
write(os.path.join(live, "marked", "notes-marked.pdf"), b"%PDF-1.4 marked")
write(os.path.join(live, "export.json"), '{"pages": 2}')
write(os.path.join(live, "jobs.jsonl"), '{"id": "job-new", "state": "RUNNING"}\n')
write(os.path.join(live, "jobs.reported", "relay.heard"), "1")
write(os.path.join(live, "missions", "task-1.json"), json.dumps({"kind": "task"}))
write(os.path.join(live, "missions", "task-1.task.claimed"), "")
write(os.path.join(live, "missions", "m1.json"), json.dumps({"kind": "mission"}))
write(os.path.join(live, "agent.json"), json.dumps({
    "agent": "claude", "state": "listening", "pid": 99999, "owed": "[say] hello",
    "turns": 4}))
write(os.path.join(live, "cost.jsonl"), '{"usd": 0.1}\n')
write(os.path.join(live, "agent.log"), "log\n")
write(os.path.join(live, "archive", "20260901-lesson", "cards", "0001-x.md"), "old")
write(os.path.join(live, "mystery.bin"), b"\x00")
# The subject already holds a registry: the import appends, the reverse restores.
write(os.path.join(home, "relay", "state", "jobs.jsonl"),
      '{"id": "job-old", "state": "COMPLETED"}\n')
# An empty live/ elsewhere, and a course whose `hw` is a set's name.
for d in ("cards", "slate", "inbox/uploads", "archive"):
    os.makedirs(os.path.join(atlas, "research", "Empty", "live", d))
course = os.path.join(atlas, "courses", "Calc")
write(os.path.join(course, "tutorboard.json"), json.dumps({"name": "Calculus"}))
write(os.path.join(course, "chapters", "ch01-limits", "homework", "ch01-homework.tex"),
      "\\begin{problem}[1]\n\\end{problem}\n")
write(os.path.join(course, "live", "state.json"), json.dumps({"hw": "ch01"}))
write(os.path.join(course, "live", "cards", "0001-a.md"), "---\nkind: lesson\n---\nHi.\n")

before = snapshot(atlas)
manifest = os.path.join(tmp, "import.jsonl")

# --- dry run ----------------------------------------------------------------------
p = run(SCRIPT, "--atlas", atlas, "--workspace", ws, "--subject", "projects/Demo",
        "--manifest", manifest, "--dry-run")
check("--dry-run exits 0 and prints a plan",
      p.returncode == 0 and "dry run: research/Demo -> session" in p.stdout
      and "move " in p.stdout, p.stdout[-2000:])
check("--dry-run changes nothing", snapshot(atlas) == before
      and not os.path.exists(manifest))

# --- refusals ---------------------------------------------------------------------
for bad in ("research/Demo", "../x", "/abs", "projects/../x", "projects"):
    p = run(SCRIPT, "--atlas", atlas, "--workspace", ws, "--subject", bad,
            "--manifest", manifest)
    check("a subject id %r is refused" % bad, p.returncode == 1
          and snapshot(atlas) == before, p.stdout)

# --- import -----------------------------------------------------------------------
p = run(SCRIPT, "--atlas", atlas, "--workspace", ws, "--subject", "projects/Demo",
        "--manifest", manifest)
check("import exits 0", p.returncode == 0, p.stdout)
mapping = course_repo._read_json(os.path.join(atlas, "sessions", ".imported.json"))
sid = mapping.get("research/Demo")
check("sessions/.imported.json maps the old workspace id to the session",
      sid and sessions.path(sid, atlas), mapping)
where = sessions.path(sid, atlas) or os.path.join(tmp, "missing")
rec = sessions.get(sid, atlas) or {}
check("session.json: title from the subject's name and the chapter",
      rec.get("title") == "Demo Project: ch02", rec)
check("session.json: bound to the post-merge subject, open, mode from the stance",
      rec.get("subject") == "projects/Demo" and rec.get("ended") is None
      and rec.get("mode") == "do", rec)
check("session.json: writeup is the homework source under the subject",
      rec.get("writeup") == "projects/Demo/homework/hw01/hw01.tex", rec)
check("session.json: seen from .seen.json, opened from state.json",
      rec.get("seen") == 123.5 and rec.get("opened") == "2026-10-01 09:30:00", rec)
check("session.json carries every key", set(course_repo.SESSION_KEYS) <= set(rec), rec)

names = cards(os.path.join(where, "cards"))
check("every card comes over, and one 'Carried over' card is appended",
      names == ["0001-first.md", "0002-second.md", "0003-carried-over.md"], names)
first = read(os.path.join(where, "cards", "0001-first.md"))
check("this workspace's old card link is rewritten to the session",
      "(#/s/%s/card/0002)" % sid in first and "#/w/Research/Demo" not in first, first)
check("another workspace's link is left alone",
      "(#/w/Courses/Other/card/0002)" in first, first)
carried = read(os.path.join(where, "cards", "0003-carried-over.md"))
check("the carried-over card is a note holding NEXT.md and each handoff",
      carried.startswith("---\nkind: note\ntitle: Carried over\n---\n")
      and "finish problem 3" in carried and "hw01 is done" in carried
      and "#/s/%s/card/0001" % sid in carried, carried)
check("slate, answers, text, turns and .turnseq keep their names",
      os.path.isfile(os.path.join(where, "slate", "page-01.json"))
      and os.path.isfile(os.path.join(where, "answers", "t0001-r1.png"))
      and os.path.isdir(os.path.join(where, "text"))
      and len(lines(os.path.join(where, "turns.jsonl"))) == 2)
repo = sessions.repo(sid, atlas)
check("next_turn_id continues from the workspace's high-water mark",
      turns.next_turn_id(repo) == "t0008", turns.next_turn_id(repo))
check("the inbox keeps its read marks: one unread before, one after",
      unread(os.path.join(where, "inbox", "messages.jsonl")) == 1)
check("inbox uploads land in uploads/",
      os.path.isfile(os.path.join(where, "uploads", "notes.pdf")))
check("card ink stays in the session; direction ink does not come over",
      os.path.isfile(os.path.join(where, "annotations", "0001.json"))
      and os.path.isfile(os.path.join(where, "annotations", "0001.png"))
      and not os.path.exists(os.path.join(where, "annotations", "0001.dir.png")))
check("document ink goes to <subject>/.ink/",
      os.path.isfile(os.path.join(home, ".ink", "doc-paper-p1-0a1b2c3d.json")))
check("marked/ goes to <subject>/materials/marked/",
      os.path.isfile(os.path.join(home, "materials", "marked", "notes-marked.pdf")))
check("export.json, cost.jsonl and agent.log keep their names",
      all(os.path.isfile(os.path.join(where, n))
          for n in ("export.json", "cost.jsonl", "agent.log")))
agent = course_repo._read_json(os.path.join(where, "agent.json"))
check("agent.json is idle, holds no pid, and keeps owed",
      agent.get("state") == "idle" and agent.get("pid") is None
      and agent.get("owed") == "[say] hello" and agent.get("turns") == 4, agent)
state = os.path.join(home, "relay", "state")
check("the registry joins the subject's, by jobs.migrate_state",
      [r.get("id") for r in lines(os.path.join(state, "jobs.jsonl"))]
      == ["job-old", "job-new"])
check("claims and Colibri tasks land in relay/state/",
      os.path.isfile(os.path.join(state, "reported", "relay.heard"))
      and os.path.isfile(os.path.join(state, "colibri", "task-1.json"))
      and os.path.isfile(os.path.join(state, "colibri", "task-1.task.claimed")))
imported = sorted(os.path.relpath(os.path.join(h, f), os.path.join(where, "imported"))
                  for h, _, fs in os.walk(os.path.join(where, "imported")) for f in fs)
check("anything else is under imported/, and the output names it",
      imported == ["annotations/odd.json", "inbox/stray.txt", "missions/m1.json",
                   "mystery.bin"]
      and "mystery.bin" in p.stdout and "inbox/stray.txt" in p.stdout,
      (imported, p.stdout))
dropped = ("hw.json", "tikzcache", "paper", "push.json", ".board.json", "board.log",
           "BRIEF.md", "TEACHING.md", "directions", "NEXT.md", "handoffs",
           "state.json", ".seen.json")
check("dropped entries are not in the session",
      not any(os.path.exists(os.path.join(where, n)) for n in dropped))
check("live/ keeps only archive/, for the caller",
      sorted(os.listdir(live)) == ["archive"], os.listdir(live))
p2 = run(SCRIPT, "--atlas", atlas, "--workspace", ws, "--subject", "projects/Demo",
         "--manifest", manifest)
check("a second import of the same workspace is refused",
      p2.returncode == 1 and "already imported" in p2.stdout, p2.stdout)

# --- a course: board writeup status resolves the set ----------------------------------
p = run(SCRIPT, "--atlas", atlas, "--workspace", course, "--subject",
        "courses/Calc", "--manifest", manifest)
calc = course_repo._read_json(os.path.join(atlas, "sessions", ".imported.json")).get(
    "courses/Calc")
crec = sessions.get(calc, atlas) or {}
check("a set named by `hw` becomes writeup",
      crec.get("writeup") == "courses/Calc/chapters/ch01-limits/homework/ch01-homework.tex"
      and crec.get("title") == "Calculus: ch01", crec)
p = run(BOARD, "writeup", "status", TUTORBOARD_SESSION=sessions.path(calc, atlas) or "")
check("`board writeup status` in the imported session resolves ch01",
      p.returncode == 0 and p.stdout.startswith("ch01 "), p.stdout)

# --- an empty live/ ---------------------------------------------------------------
p = run(SCRIPT, "--atlas", atlas, "--workspace", os.path.join(atlas, "research", "Empty"),
        "--subject", "projects/Empty", "--manifest", manifest)
check("a live/ with no cards, turns or messages makes no session",
      p.returncode == 0 and "no session" in p.stdout
      and "research/Empty" not in course_repo._read_json(
          os.path.join(atlas, "sessions", ".imported.json"))
      and len(sessions.all(atlas)) == 2, p.stdout)
check("and its emptied directories go, archive/ left",
      os.listdir(os.path.join(atlas, "research", "Empty", "live")) == ["archive"])

# --- reverse ----------------------------------------------------------------------
p = run(SCRIPT, "--reverse", manifest)
check("--reverse exits 0", p.returncode == 0, p.stdout)
after = snapshot(atlas)
check("--reverse restores every byte and directory, the subject's registry included",
      after == before,
      sorted(set(after.items()) ^ set(before.items()))[:12])
shutil.rmtree(tmp, ignore_errors=True)


# --- the real live/ dirs, copied out of the T00 tarball ----------------------------
REAL = (("courses/Galois-Theory", "courses/Galois-Theory"),
        ("courses/Probability", "courses/Probability"),
        ("research/TRD-EHR", "projects/TRD-EHR"))
if not os.path.isfile(TGZ):
    print("SKIPPED the rehearsal on live-dirs.tgz: %s is not here" % TGZ)
else:
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="tutor-import-real-"))
    atlas = os.path.join(tmp, "atlas")
    want = tuple(old + "/live/" for old, _ in REAL)
    with tarfile.open(TGZ, "r:gz") as tf:
        members = [m for m in tf.getmembers()
                   if m.name.startswith(want) and "/live/archive/" not in m.name
                   and (m.isfile() or m.isdir())]
        if hasattr(tarfile, "data_filter"):
            tf.extractall(atlas, members, filter="data")
        else:
            tf.extractall(atlas, members)
    src = os.path.join(os.path.dirname(BOARD_DIR), "courses", "Galois-Theory")
    for rel in ("tutorboard.json", os.path.join("chapters", "ch07-splitting-fields",
                                                "homework")):
        a, b = os.path.join(src, rel), os.path.join(atlas, "courses", "Galois-Theory", rel)
        if os.path.isdir(a):
            shutil.copytree(a, b)
        elif os.path.isfile(a):
            shutil.copy2(a, b)
    before = snapshot(atlas)
    manifest = os.path.join(tmp, "import.jsonl")
    counts = {}
    for old, new_id in REAL:
        lv = os.path.join(atlas, old, "live")
        counts[old] = (len(cards(os.path.join(lv, "cards"))),
                       len(lines(os.path.join(lv, "turns.jsonl"))),
                       unread(os.path.join(lv, "inbox", "messages.jsonl")),
                       course_repo._read_json(os.path.join(lv, "agent.json")).get("owed"),
                       os.path.isfile(os.path.join(lv, "NEXT.md"))
                       or os.path.isdir(os.path.join(lv, "handoffs")))
        p = run(SCRIPT, "--atlas", atlas, "--workspace", os.path.join(atlas, old),
                "--subject", new_id, "--manifest", manifest)
        check("live-dirs.tgz %s imports" % old, p.returncode == 0, p.stdout[-1500:])
    mapping = course_repo._read_json(os.path.join(atlas, "sessions", ".imported.json"))
    check("one open session each", len(mapping) == 3 and all(
        (sessions.get(s, atlas) or {}).get("ended", 1) is None
        for s in mapping.values()), mapping)
    for old, new_id in REAL:
        where = sessions.path(mapping.get(old), atlas) or os.path.join(tmp, "x")
        n, t, u, owed, carry = counts[old]
        names = cards(os.path.join(where, "cards"))
        check("%s: every card, plus 'Carried over' (%d + %d)" % (old, n, int(carry)),
              len(names) == n + int(carry) and (not carry or names[-1].endswith(
                  "-carried-over.md")), names[-3:])
        check("%s: equal turns (%d), unread messages (%d) and owed (%r)"
              % (old, t, u, owed),
              len(lines(os.path.join(where, "turns.jsonl"))) == t
              and unread(os.path.join(where, "inbox", "messages.jsonl")) == u
              and course_repo._read_json(os.path.join(where, "agent.json")).get(
                  "owed") == owed)
    trd = sessions.get(mapping.get("research/TRD-EHR"), atlas) or {}
    check("TRD-EHR's missing state.json imports: '<name>: imported', bound to "
          "projects/TRD-EHR", trd.get("title", "").endswith(": imported")
          and trd.get("subject") == "projects/TRD-EHR", trd)
    prob = os.path.join(sessions.path(mapping.get("courses/Probability"), atlas)
                        or tmp, "cards")
    last = cards(prob)[-1:] or [""]
    check("Probability's handoffs/ lands in the 'Carried over' card",
          last[0].endswith("-carried-over.md")
          and "From handoffs/hw03.md" in read(os.path.join(prob, last[0])))
    p = run(BOARD, "writeup", "status", TUTORBOARD_SESSION=sessions.path(
        mapping.get("courses/Galois-Theory"), atlas) or "")
    check("`board writeup status` in the Galois session resolves ch07",
          p.returncode == 0 and p.stdout.startswith("ch07 "), p.stdout[:300])
    p = run(SCRIPT, "--reverse", manifest)
    check("--reverse restores the copy exactly", p.returncode == 0
          and snapshot(atlas) == before, p.stdout[-1500:])
    shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("every live/ entry has a destination, and the import reverses exactly")
