#!/usr/bin/env python3
"""Learn, coach and build, in every workspace, on a thread or not.

  * EVERY SITTING CARRIES ITS KIND. `board open`, `board aim`, the board's
    `/session` and `/aim` write `kind` whether or not the sitting is on a
    thread, and a course's chapter flow is unchanged: still a lecture, still
    labelled with its chapter.
  * THE TURN IS TOLD WHICH KIND, off a thread too: the brief's sitting line,
    and the coach line in the waking words, in words that fit a solver or a
    proof as well as an estimator.
  * A HOLD STANDING IN THE WORKSPACE IS ON THE BRIEF, whatever the sitting.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tutorboard import atlas, brief, sense                             # noqa: E402
from tutorboard.course import config                                   # noqa: E402
from tutorboard.course import repo as course_repo                      # noqa: E402
from tutorboard.server.routes import lesson                            # noqa: E402

BOARD = os.path.join(ROOT, "bin", "board")
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


fake = tempfile.mkdtemp(prefix="everykind-")
saved = os.environ.get("TUTORBOARD_COURSES")
try:
    course = os.path.join(fake, "courses", "Course")
    write(os.path.join(course, "tutorboard.json"), json.dumps({"name": "Course"}))
    write(os.path.join(course, "chapters.tsv"), "01\t1\t9\tgroups\tGroups\n"
                                                "02\t10\t19\trings\tRings\n")
    write(os.path.join(course, "chapters", "ch01-groups", "notes.tex"), "x\n")
    algo = os.path.join(fake, "practice", "Algo")
    write(os.path.join(algo, "tutorboard.json"), json.dumps({"name": "Algo"}))
    write(os.path.join(algo, "leetcode", "coinchange", "coinchange.go"),
          "package coinchange\n")
    research = os.path.join(fake, "research", "Proj")
    write(os.path.join(research, "tutorboard.json"), json.dumps({"name": "Proj"}))
    env = dict(os.environ, TUTORBOARD_COURSES=fake, TUTOR_SLURM="0",
               TUTOR_NO_SPAWN="1")
    os.environ["TUTORBOARD_COURSES"] = fake
    atlas.forget()

    def board(where, *args):
        p = subprocess.run([sys.executable, BOARD] + list(args), cwd=where,
                           env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=120)
        return p.returncode, p.stdout.decode("utf-8", "replace")

    def state(where):
        with open(os.path.join(where, "live", "state.json"), encoding="utf-8") as fh:
            return json.load(fh)

    # --- a course's chapter, every kind ---------------------------------------
    code, out = board(course, "open", "Course", "Ch 01 — Groups")
    st = state(course)
    check("a course's chapter opens as it always has: a lecture, labelled",
          code == 0 and st.get("session") == "lecture"
          and st.get("chapter") == "Ch 01 — Groups")
    check("and carries its kind, read off the family's style", st.get("kind") == "learn")
    for kind, aim in (("coach", "coach"), ("build", "build"), ("learn", "teach")):
        code, out = board(course, "open", "Course", "Ch 01 — Groups", "--kind", kind)
        st = state(course)
        check("a chapter sitting may be %s" % kind,
              code == 0 and st.get("kind") == kind and st.get("aim") == aim
              and st.get("session") == "lecture"
              and st.get("chapter") == "Ch 01 — Groups")

    # --- a practice workspace with no thread file -----------------------------
    for kind in config.KINDS:
        code, out = board(algo, "open", "Algo", "coin change", "--kind", kind)
        check("a practice sitting with no thread file may be %s" % kind,
              code == 0 and state(algo).get("kind") == kind
              and not state(algo).get("thread"))
    code, out = board(algo, "aim", "coach")
    check("`board aim` keeps the kind in step on a sitting with no thread",
          code == 0 and state(algo).get("kind") == "coach"
          and state(algo).get("aim") == "coach")
    code, out = board(research, "open", "Proj", "a sitting", "--kind", "build")
    check("and so may a research sitting", code == 0
          and state(research).get("kind") == "build")

    # --- the board's own routes -----------------------------------------------
    st = {"session": "lecture", "chapter": "Ch 02 — Rings"}
    lesson._mark(st, None, None, None, course, None)
    check("a sitting the board opens with no aim still carries its kind",
          st.get("kind") == "learn")
    st = {"session": "lecture"}
    lesson._mark(st, None, None, None, algo, "coach")
    check("and one opened as coach is coach, with the aim beside it",
          st.get("kind") == "coach" and st.get("aim") == "coach")

    # --- what the turn is told ----------------------------------------------------
    repo = course_repo.Repo(algo)
    st = repo.state()
    st.update({"kind": "coach", "aim": "coach"})
    with open(repo.state_path, "w", encoding="utf-8") as fh:
        json.dump(st, fh)
    said = brief.sitting_sense(repo, repo.state())
    check("the brief says what kind a sitting off any thread is",
          "a COACH sitting" in said and "the solver" in said)
    check("in words that fit a solver or a proof, not only statistics",
          "statistical" not in config.KIND_SENSE["coach"]
          and "the proof" in config.KIND_SENSE["coach"])
    check("and the waking line says which half is whose",
          config.KIND_SENSE["coach"] in sense.aim_sense({"aim": "coach"}))
    write(os.path.join(algo, "relay", "holds", "coinchange.json"), json.dumps({
        "id": "coinchange", "label": "coin change",
        "files": ["leetcode/coinchange"], "check": None, "held": 0}))
    said = brief.sitting_sense(repo, repo.state())
    check("a hold standing in the workspace is on the brief, files named",
          "HELD AT THE CLUSTER: coin change (`coinchange`)" in said
          and "leetcode/coinchange" in said)
    whole = brief.briefing(repo, sense)
    check("and the whole briefing carries it", "a COACH sitting" in whole
          and "HELD AT THE CLUSTER" in whole)
finally:
    if saved is None:
        os.environ.pop("TUTORBOARD_COURSES", None)
    else:
        os.environ["TUTORBOARD_COURSES"] = saved
    atlas.forget()
    shutil.rmtree(fake, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("every workspace offers learn, coach and build, and the turn is told which")
