#!/usr/bin/env python3
"""RULES.md and TUTOR.md in the brief, and `board memo`.

  * The brief carries the bound subject's RULES.md as committed at HEAD, and a
    flag line when the working tree differs; an uncommitted edit's text never
    reaches it.
  * The brief carries TUTOR.md, and points at board/TEACHING.md. It never
    carries the subject's README.md, NEXT.md, HANDOFF.md, DIRECTION.md or
    threads.json.
  * `board memo <section>` replaces one section of TUTOR.md from stdin, or adds
    to it with --append. A result over 800 words is refused, naming the count,
    and nothing is written. It never writes RULES.md.
  * An unbound session has no TUTOR.md, and `board memo` says to bind first.
  * No `NEXT.md` or `board note` is left in board/, except import_live's
    "Carried over" mapping.

Everything runs in a temp Atlas (`TUTORBOARD_COURSES`).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ATLAS = os.path.dirname(ROOT)
BOARD = os.path.join(ROOT, "bin", "board")
sys.path.insert(0, ROOT)

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n     " + str(detail)[:600]) if detail else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


base = os.path.realpath(tempfile.mkdtemp(prefix="tutor-memo-"))
trash = os.path.realpath(tempfile.mkdtemp(prefix="tutor-memo-trash-"))
os.environ["TUTORBOARD_COURSES"] = base
os.environ["TUTORBOARD_TRASH"] = trash
os.environ.pop("TUTORBOARD_SESSION", None)
os.environ.pop("TUTORBOARD_TURN", None)

from tutorboard import brief, memo, sense, sessions                   # noqa: E402


def git(*args):
    return subprocess.run(["git", "-C", base] + list(args),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True, timeout=60)


def board(args, session, stdin=""):
    env = dict(os.environ, TUTORBOARD_SESSION=session)
    p = subprocess.run([sys.executable, BOARD] + list(args), cwd=base, env=env,
                       input=stdin, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True,
                       timeout=120)
    return p.returncode, p.stdout


try:
    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    write(os.path.join(base, ".gitignore"), "/sessions/\n")
    proj = os.path.join(base, "projects", "Probe")
    write(os.path.join(proj, "tutorboard.json"),
          json.dumps({"name": "Probe", "phi": False}))
    write(os.path.join(proj, "RULES.md"),
          "# Rules\n\n- Never read the held-out split before the analysis is frozen.\n")
    write(os.path.join(proj, "README.md"), "# Probe\n\nREADME-SENTINEL text.\n")
    write(os.path.join(proj, "NEXT.md"), "NEXT-SENTINEL\n")
    write(os.path.join(proj, "HANDOFF.md"), "HANDOFF-SENTINEL\n")
    write(os.path.join(proj, "DIRECTION.md"), "DIRECTION-SENTINEL\n")
    write(os.path.join(proj, "threads.json"), json.dumps({"threads": [
        {"id": "t", "title": "THREAD-SENTINEL"}]}))
    write(os.path.join(proj, "TUTOR.md"),
          "# Probe\n\n## Where things are\n\nsrc/ holds the loader.\n\n"
          "## Now\n\nWire the loader to the split.\n\n## Open decisions\n\n"
          "- which split seed\n\n## Done recently\n\n- the loader\n")
    git("add", "-A")
    git("commit", "-q", "-m", "fixture")

    rec = sessions.new(base=base)
    sid = rec["id"]
    sess = sessions.path(sid, base)

    # ---- unbound ---------------------------------------------------------
    said = brief.briefing(sessions.repo(sid, base, create=True), sense)
    check("an unbound session's brief says there is no TUTOR.md yet, and how "
          "to bind", "bound to no subject" in said and "board bind" in said, said)
    code, out = board(["memo", "Now"], sess, "anything")
    check("and `board memo` refuses, saying to bind first",
          code != 0 and "board bind" in out, out)

    sessions.bind(sid, "projects/Probe", base=base)
    repo = sessions.repo(sid, base, create=True)

    # ---- the brief -------------------------------------------------------
    said = brief.briefing(repo, sense)
    check("a bound brief carries RULES.md's text from HEAD",
          "Never read the held-out split" in said, said)
    check("with no drift flag when the working tree matches",
          "differs from HEAD" not in said)
    check("it carries TUTOR.md", "Wire the loader to the split." in said
          and "which split seed" in said)
    check("and points at board/TEACHING.md", "board/TEACHING.md" in said)
    check("no README, NEXT.md, HANDOFF.md, DIRECTION.md or threads.json enters it",
          not any(s in said for s in ("README-SENTINEL", "NEXT-SENTINEL",
                                      "HANDOFF-SENTINEL", "DIRECTION-SENTINEL",
                                      "THREAD-SENTINEL")), said)
    check("nor any `board note` or NEXT.md instruction",
          "board note" not in said and "NEXT.md" not in said)
    check("`where_sense` never says to read the README first",
          "README.md at the root first" not in sense.where_sense(None, proj)
          and "TUTOR.md" in sense.where_sense(None, proj))

    write(os.path.join(proj, "RULES.md"),
          "# Rules\n\n- An uncommitted EDIT-SENTINEL rule.\n")
    said = brief.briefing(repo, sense)
    check("an uncommitted RULES.md edit is flagged",
          "differs from HEAD" in said, said)
    check("and the brief still carries HEAD's text, not the edit",
          "Never read the held-out split" in said and "EDIT-SENTINEL" not in said)
    git("checkout", "--", "projects/Probe/RULES.md")

    os.remove(os.path.join(proj, "RULES.md"))
    said = brief.briefing(repo, sense)
    check("a RULES.md deleted in the working tree still binds from HEAD, flagged",
          "Never read the held-out split" in said and "deleted in the working tree"
          in said, said)
    git("checkout", "--", "projects/Probe/RULES.md")

    # ---- board memo ------------------------------------------------------
    rules_before = read(os.path.join(proj, "RULES.md"))
    tutor_before = read(os.path.join(proj, "TUTOR.md"))
    code, out = board(["memo", "Now"], sess, " ".join(["word"] * 900))
    check("`board memo Now` with 900 words is refused",
          code != 0 and "words" in out, out)
    check("naming the count", any(str(n) in out for n in range(900, 960)), out)
    check("and nothing is written",
          read(os.path.join(proj, "TUTOR.md")) == tutor_before)

    hundred = " ".join("w%d" % i for i in range(100))
    code, out = board(["memo", "Now"], sess, hundred + "\n")
    after = read(os.path.join(proj, "TUTOR.md"))
    check("`board memo Now` with 100 words lands", code == 0, out)
    now = after.split("## Now", 1)[1].split("\n## ", 1)[0]
    check("in the Now section", hundred in now and "Wire the loader" not in now,
          after)
    rest = after.replace(now, "")
    check("and only there: every other section is as it was",
          hundred not in rest
          and "src/ holds the loader." in after and "which split seed" in after
          and "- the loader" in after
          and [l for l in after.splitlines() if l.startswith("## ")]
          == ["## " + s for s in memo.SECTIONS], after)
    check("RULES.md is untouched", read(os.path.join(proj, "RULES.md")) == rules_before)

    code, out = board(["memo", "open decisions", "--append"], sess,
                      "- which embedder\n")
    after = read(os.path.join(proj, "TUTOR.md"))
    dec = after.split("## Open decisions", 1)[1].split("\n## ", 1)[0]
    check("--append adds to a section, and a section name ignores case",
          code == 0 and "which split seed" in dec and "which embedder" in dec, after)

    code, out = board(["memo", "Rules"], sess, "anything")
    check("a name that is not one of the four sections is refused, naming them",
          code != 0 and "Where things are" in out and "Done recently" in out, out)
    check("and RULES.md is never written",
          read(os.path.join(proj, "RULES.md")) == rules_before)

    code, out = board(["memo", "--show"], sess)
    check("`board memo --show` prints TUTOR.md", code == 0 and "which embedder" in out)

    # A missing TUTOR.md starts as the skeleton.
    os.remove(os.path.join(proj, "TUTOR.md"))
    code, out = board(["memo", "Done recently"], sess, "## Done recently\n\n- one\n")
    made = read(os.path.join(proj, "TUTOR.md"))
    check("a missing TUTOR.md starts as the four-section skeleton, and a repeated "
          "heading is not doubled",
          code == 0 and [l for l in made.splitlines() if l.startswith("## ")]
          == ["## " + s for s in memo.SECTIONS] and made.count("Done recently") == 1
          and "- one" in made, made)

    # ---- the pure section writer -----------------------------------------
    text = "# T\n\n## Now\n\nold\n\n### a sub-heading\n\nstill now\n\n## Done recently\n\nx\n"
    got = memo.replace_section(text, "Now", "new")
    check("a section runs to the next heading of its level, sub-headings included",
          "old" not in got and "still now" not in got and "new" in got
          and "## Done recently\n\nx" in got, got)
    got = memo.replace_section("# T\n", "Open decisions", "- a")
    check("a missing section is added at the end",
          got.endswith("## Open decisions\n\n- a\n"), got)

    # ---- no note is left -------------------------------------------------
    # Whole words (-w).
    p = subprocess.run(["git", "grep", "-n", "-w", "-e", "NEXT\\.md", "-e",
                        "board note", "--", "board"], cwd=ATLAS,
                       stdout=subprocess.PIPE, universal_newlines=True)
    left = [l for l in p.stdout.splitlines()
            if not l.startswith(("board/tutorboard/sessions.py:",
                                 "board/test/import_live.py:",
                                 "board/test/memo.py:"))]
    check("no NEXT.md or `board note` is left in board/, except import_live's "
          "\"Carried over\" mapping", left == [], "\n".join(left))
    check("and carry.py is gone",
          not os.path.exists(os.path.join(ROOT, "tutorboard", "carry.py")))
finally:
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(trash, ignore_errors=True)

print()
print("%d FAILURES" % len(fails) if fails
      else "the brief reads the owner's rules at HEAD and the tutor's notes, and "
           "the tutor writes only its own")
sys.exit(1 if fails else 0)
