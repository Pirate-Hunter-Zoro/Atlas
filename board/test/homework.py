#!/usr/bin/env python3
"""A homework sitting is producing a document, and the board has to know which one.

Two shapes of problem set exist in the courses this drives, and neither is more
correct than the other:

    homework/hw04/hw04.tex                        numbered by assignment
    chapters/ch07-*/homework/ch07-homework.tex     numbered by chapter

So the set is discovered, not assumed, and the problem labels are opaque strings
because one course numbers problems 1, 2, 3 and the other numbers them 7.1, 7.2.

What is guarded here is the reading, not the writing: the assistant edits the
.tex with its own tools, and this only has to report which problems are still
empty and never point a compile or a page of handwriting at the wrong set.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard import tex
from tutorboard.course import homework  # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


SET = r"""\documentclass[11pt]{article}
\begin{document}
\begin{problem}{%(a)s}
  A statement that has been transcribed.
\end{problem}
%% ===== SOLUTION %(a)s =====
Let $D$ be finite. The map is injective, hence onto.
%% ===== END SOLUTION %(a)s =====

\begin{problem}{%(b)s}
  A statement transcribed, but not yet worked.
\end{problem}
%% ===== SOLUTION %(b)s =====
%% TODO(mferguson): your work goes here.
%% ===== END SOLUTION %(b)s =====

\begin{problem}{%(c)s}
  \todo{statement not yet transcribed}
\end{problem}
%% ===== SOLUTION %(c)s =====
%% TODO(mferguson): your work goes here.
%% ===== END SOLUTION %(c)s =====
\end{document}
"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


tmp = tempfile.mkdtemp(prefix="tutor-hw-")
try:
    # --- the assignment-numbered shape ---------------------------------------
    prob = os.path.join(tmp, "byset")
    write(os.path.join(prob, "tutorboard.json"), '{"name": "P", "mode": "math"}')
    write(os.path.join(prob, "homework", "hw04", "hw04.tex"), SET % {"a": "1", "b": "2", "c": "3"})
    write(os.path.join(prob, "homework", "hw05", "hw05.tex"), SET % {"a": "1", "b": "2", "c": "3"})
    # A build directory is output, not a problem set.
    write(os.path.join(prob, "homework", "hw04", "build", "hw04.tex"), "junk")

    names = [s["name"] for s in homework.sets(prob)]
    check("assignment-numbered sets are found", names == ["hw04", "hw05"])
    check("a build directory is not mistaken for a set",
          all("build" not in s["rel"] for s in homework.sets(prob)))

    # --- the chapter-numbered shape ------------------------------------------
    gal = os.path.join(tmp, "bychapter")
    write(os.path.join(gal, "tutorboard.json"), '{"name": "G", "mode": "math"}')
    write(os.path.join(gal, "chapters", "ch07-splitting-fields", "homework",
                       "ch07-homework.tex"), SET % {"a": "7.1", "b": "7.2", "c": "7.3"})
    write(os.path.join(gal, "chapters", "ch07-splitting-fields", "notes",
                       "ch07-notes.tex"), "notes are not homework")

    names = [s["name"] for s in homework.sets(gal)]
    check("chapter-numbered sets are found", names == ["ch07"])
    check("a chapter's notes file is not its homework",
          all("notes" not in s["rel"] for s in homework.sets(gal)))

    # --- which set is this sitting -------------------------------------------
    check("the session label picks the set out",
          (homework.find(prob, {"chapter": "Homework 5"}) or {}).get("name") == "hw05")
    check("and does so for a chapter-numbered course",
          (homework.find(gal, {"chapter": "Ch 7 — splitting fields"}) or {}).get("name")
          == "ch07")
    check("a pinned set beats the label",
          (homework.find(prob, {"chapter": "Homework 5",
                                "hw": "homework/hw04/hw04.tex"}) or {}).get("name") == "hw04")
    check("a sole set needs no label at all",
          (homework.find(gal, {}) or {}).get("name") == "ch07")
    # Guessing wrong here compiles the wrong document or files handwriting into
    # someone else's problem, so an unresolvable guess is no answer.
    check("an ambiguous sitting resolves to nothing rather than to a guess",
          homework.find(prob, {}) is None)
    check("and says what there was to choose from",
          homework.status(prob, {})["ambiguous"] == ["hw04", "hw05"])

    # --- which set is being WRITTEN INTO, which is a narrower question --------
    #
    # `find` answers "compile what?" and falls back to the lone set in a course.
    # `bound` answers "is this sitting owing a write-up?", and that one may not
    # guess: a line put in front of the assistant every turn has to be about the
    # file the sitting is actually filling, or it becomes noise and stops being
    # read. A chapter named in the session label is a binding; nothing is not.
    check("a named chapter binds the sitting without anybody running `hw use`",
          (homework.bound(gal, {"session": "lecture",
                                "chapter": "Ch 7 — splitting fields"}) or {}).get("name")
          == "ch07")
    check("a pin binds it too",
          (homework.bound(prob, {"hw": "homework/hw04/hw04.tex"}) or {}).get("name")
          == "hw04")
    check("a sole set is NOT a binding, though it is a findable set",
          homework.bound(gal, {"session": "lecture", "chapter": "loose ends"}) is None
          and (homework.find(gal, {}) or {}).get("name") == "ch07")

    # --- how much of it is done ----------------------------------------------
    st = homework.status(prob, {"chapter": "Homework 4"})
    check("every problem is counted", st["total"] == 3)
    check("a filled region counts as written up", st["written"] == 1)
    check("a region holding only the placeholder comment does not",
          st["problems"][1]["written"] is False)
    check("a transcribed statement with an empty region is the to-do state",
          st["problems"][1]["stated"] is True and st["problems"][1]["written"] is False)
    check("an untranscribed statement is visible as such",
          st["problems"][0]["stated"] is True and st["problems"][2]["stated"] is False)
    check("problems keep the order they appear in",
          [p["label"] for p in st["problems"]] == ["1", "2", "3"])

    # --- what is still owed, which is what a skip leaves behind ---------------
    #
    # A student may work an assigned sheet in any order they like: skipping is
    # theirs, and it means "not now" rather than "never". The assistant then has
    # to come back, and "come back" has to survive two hours, a restart and a
    # different tutor -- so it is read off the DOCUMENT, where an unanswered
    # problem is an empty region sitting in the sheet's own order, and not off
    # anybody's memory of the conversation.
    check("what is still to write up is named, in the sheet's order",
          st["outstanding"] == ["2", "3"])
    check("and the next agreed answer has a region waiting for it",
          st["next"] == "2")
    check("a written-up problem is not outstanding",
          "1" not in st["outstanding"])

    # Answered out of order: problem 3 done while 2 is still empty. The document
    # is written in the sheet's order regardless, so 2 is still the next one --
    # its region sits above 3's and stays empty until it is filled.
    jumbled = os.path.join(tmp, "jumbled")
    write(os.path.join(jumbled, "tutorboard.json"), '{"name": "J", "mode": "math"}')
    body = SET % {"a": "1", "b": "2", "c": "3"}
    body = body.replace(
        "% TODO(mferguson): your work goes here.\n% ===== END SOLUTION 3 =====",
        "By Boole's inequality the union is at most the sum.\n% ===== END SOLUTION 3 =====")
    write(os.path.join(jumbled, "homework", "hw06", "hw06.tex"), body)
    stj = homework.status(jumbled, {"chapter": "Homework 6"})
    check("a problem answered out of turn is written up where the sheet puts it",
          [p["label"] for p in stj["problems"]] == ["1", "2", "3"]
          and stj["problems"][2]["written"] is True)
    check("and the one skipped over is still the next one owed",
          stj["outstanding"] == ["2"] and stj["next"] == "2")

    # The degenerate case the person asked about: skip the only one left and it
    # comes straight back, because there is nothing else to carry on with.
    last = homework.outstanding([{"label": "9", "written": False}])
    check("skipping the last problem leaves exactly one thing owed: that problem",
          last == ["9"])
    check("and a finished sheet owes nothing",
          homework.outstanding([{"label": "9", "written": True}]) == [])

    # The real templates use one comment marker; a doubled one is an ordinary
    # thing for a person to write and opens no less real a region.
    dbl = os.path.join(tmp, "doubled")
    write(os.path.join(dbl, "tutorboard.json"), '{"name": "D", "mode": "math"}')
    write(os.path.join(dbl, "homework", "hw01", "hw01.tex"),
          SET.replace("%%", "%%%%") % {"a": "1", "b": "2", "c": "3"})
    dst = homework.status(dbl, {})
    check("a doubled comment marker still opens a solution region",
          dst["total"] == 3 and dst["written"] == 1)

    gst = homework.status(gal, {})
    check("dotted problem labels survive",
          [p["label"] for p in gst["problems"]] == ["7.1", "7.2", "7.3"])

    # --- the command line ----------------------------------------------------
    board = os.path.join(ROOT, "bin", "board")

    def run(cwd, *args):
        p = subprocess.run([sys.executable, board] + list(args), cwd=cwd,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        return p.returncode, p.stdout.decode("utf-8", "replace")

    code, out = run(prob, "open", "P", "Homework 4", "--homework")
    check("opening a homework sitting binds it to a set", code == 0 and "hw04" in out)
    with open(os.path.join(prob, "live", "state.json"), encoding="utf-8") as fh:
        state = json.load(fh)
    check("and records which one", state.get("hw") == "homework/hw04/hw04.tex")
    check("and that it is homework", state.get("session") == "homework")

    code, out = run(prob, "hw")
    check("status reports the set and what is empty",
          code == 0 and "hw04" in out and "EMPTY" in out and "1 of 3" in out)

    code, out = run(prob, "hw", "use", "hw05")
    check("a set can be pinned by name", code == 0)
    code, out = run(prob, "hw")
    check("and the pin takes effect", "hw05" in out)

    code, out = run(prob, "hw", "use", "hw99")
    check("pinning a set that does not exist fails loudly", code != 0)

    # Filing handwriting: the frozen answer, never the live slate page.
    os.makedirs(os.path.join(prob, "live", "answers"), exist_ok=True)
    with open(os.path.join(prob, "live", "answers", "t0001-r1.png"), "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")
    with open(os.path.join(prob, "live", "turns.jsonl"), "w", encoding="utf-8") as fh:
        json.dump({"id": "t0001", "rev": 1, "kind": "ink", "answers": "0001",
                   "t": 1.0, "png": "/answers/t0001-r1.png"}, fh)
    code, out = run(prob, "hw", "file", "2")
    filed = os.path.join(prob, "homework", "hw05", "handwritten", "hw05-2.png")
    check("a sent page files into the set it belongs to",
          code == 0 and os.path.isfile(filed))

    code, out = run(prob, "hw", "file", "../../etc/passwd")
    check("a label cannot escape the handwritten directory",
          not os.path.exists(os.path.join(tmp, "passwd")))

    code, out = run(gal, "hw", "list")
    check("list works without a session being open", code == 0 and "ch07" in out)

    # ---- a write-up for something that has none -----------------------------
    #
    # Every sitting produces a compiled document, and most workspaces are not
    # courses: there is no chapter to bind and no sheet to bind to, so the rule
    # had no file to be obeyed with and the evening stayed in the cards. The
    # portable layout is the answer, because `sets()` already looks for it.
    bare = os.path.join(tmp, "bare")
    write(os.path.join(bare, "tutorboard.json"), '{"name": "B", "mode": "math"}')
    check("a workspace can start with no sets at all", homework.sets(bare) == [])

    made, why = homework.scaffold(bare, "Yoneda Lemma", title="Notes on Yoneda")
    check("one can be started by name", made and why is None)
    check("in the layout every workspace can hold",
          made and made["rel"] == os.path.join("homework", "yoneda-lemma",
                                               "yoneda-lemma.tex"))
    check("and it is found the moment it exists",
          [s["name"] for s in homework.sets(bare)] == ["yoneda-lemma"])
    check("and binds the sitting without a pin",
          (homework.bound(bare, {"chapter": "Yoneda Lemma"}) or {}) .get("name")
          == "yoneda-lemma" or
          (homework.find(bare, {}) or {}).get("name") == "yoneda-lemma")

    body = open(made["tex"], encoding="utf-8").read()
    check("it carries a title somebody chose", "Notes on Yoneda" in body)
    check("and stands alone where there is no coursemacros.sty",
          "newenvironment{problem}" in body and "usepackage{coursemacros}" not in body)

    # A write-up already started is somebody's evening, and a second `new` on the
    # same name must not be the thing that ends it.
    again, why2 = homework.scaffold(bare, "yoneda-lemma")
    check("starting the same one twice refuses rather than overwrites",
          again is None and "already exists" in (why2 or ""))
    check("and the first one is untouched",
          open(made["tex"], encoding="utf-8").read() == body)

    check("a name that flattens to nothing is refused",
          homework.scaffold(bare, "///")[0] is None)

    # Where the workspace HAS the shared preamble, the document uses it, so a
    # write-up started this way reads like every other one in that course.
    withmac = os.path.join(tmp, "withmac")
    write(os.path.join(withmac, "tutorboard.json"), '{"name": "W", "mode": "math"}')
    write(os.path.join(withmac, "latex", "coursemacros.sty"), "% macros")
    m2, _ = homework.scaffold(withmac, "reading-group")
    check("a course's own macros are used when the course has them",
          "usepackage{coursemacros}" in open(m2["tex"], encoding="utf-8").read())

    code, out = run(bare, "hw", "new", "second-topic", "A", "Second", "Topic")
    check("the command line starts one too", code == 0 and "second-topic" in out)
    with open(os.path.join(bare, "live", "state.json"), encoding="utf-8") as fh:
        check("and pins the sitting to it",
              json.load(fh).get("hw", "").endswith("second-topic.tex"))

    # ---- the brief carries the debt, in a LECTURE, with nothing pinned -------
    #
    # A chapter's exercises get worked in sittings opened as lectures, and the
    # write-up is owed there exactly as it is in a homework sitting. The brief
    # used to print a homework line only when `state["hw"]` was set, which only
    # `board hw use` and `--homework` write. So a lecture opened as "Ch 4" was
    # never once told that a file existed and was empty; an evening of agreed
    # mathematics stayed in the cards, and what compiled was the scaffold.
    #
    # The counts are the point, not the name. "homework set: ch07" is a fact
    # about configuration and reads as already handled. "0 of 3 written up" is
    # a debt.
    code, out = run(gal, "open", "G", "Ch 07 — splitting fields")
    with open(os.path.join(gal, "live", "state.json"), encoding="utf-8") as fh:
        lecture = json.load(fh)
    check("a lecture pins nothing, which is what made this invisible",
          lecture.get("session") != "homework" and not lecture.get("hw"))
    code, out = run(gal, "brief")
    check("the brief tells a lecture that a chapter's write-up is owed",
          code == 0 and "ch07" in out)
    check("and says how much of it, not merely which file",
          code == 0 and "1 of 3 written up" in out)
    check("and names the region the next agreed answer goes in",
          code == 0 and "next 7.2" in out)

    # ---- the write-up is part of the commit ------------------------------
    #
    # An exercise is finished when it is typeset, not when it is agreed: the point
    # of the hour is the piece of mathematics. Compiling it was a step the tutor
    # had to remember at the end of a turn that had already delivered its card,
    # and a session ends by being abandoned far more often than it ends tidily.
    # What got pushed was then a `.tex` carrying tonight's proof beside a `.pdf`
    # from last week that does not -- which is worse than no PDF at all, because
    # it looks finished and is silently missing the exercise.
    tex_path = os.path.join(prob, "homework", "hw05", "hw05.tex")
    pdf = os.path.splitext(tex_path)[0] + ".pdf"

    # Stand in for LaTeX: a build script is honoured before the built-in path,
    # and this test is about WHEN a build happens, not about compiling TeX.
    scripts = os.path.join(prob, "scripts")
    os.makedirs(scripts, exist_ok=True)
    with open(os.path.join(scripts, "build.sh"), "w", encoding="utf-8") as fh:
        fh.write('#!/usr/bin/env bash\necho "pretending to compile $1"\n'
                 'printf %%s "%%PDF-1.4" > "${1%%.tex}.pdf"\n')

    # A real throwaway repository with NO origin, because there is one
    # save-and-push.sh and it is the tool's: a workspace has no copy of its own
    # for a test to stub out. With no `origin` the script commits and says so,
    # which is every part of a push this suite is about and none of the network.
    def sh(*args):
        subprocess.run(list(args), cwd=prob, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True)

    sh("git", "init", "-q", "-b", "main", ".")
    sh("git", "config", "user.email", "t@t")
    sh("git", "config", "user.name", "t")
    sh("git", "add", "-A")
    sh("git", "commit", "-qm", "the course as it stands")

    check("a set with no PDF at all is out of date", not os.path.exists(pdf))
    code, out = run(prob, "push", "an agreed exercise")
    check("pushing compiles the write-up first",
          code == 0 and "compiling" in out and os.path.exists(pdf))
    check("and says which set it built", "hw05" in out)
    check("and then actually commits", "committed" in out)

    # THE SCRIPT IS THE TOOL'S, and this is the assertion that says so. `board
    # push` reaching for a `scripts/save-and-push.sh` beside the sitting is two
    # doors onto two different files, and the terminal's was the older one.
    # Asserted on the path the code resolves rather than on any sentence about
    # it: the repository holds exactly one copy and it is under the tool.
    src = open(os.path.join(ROOT, "bin", "board"), encoding="utf-8").read()
    push_body = src[src.index("def cmd_push("):src.index("def cmd_slate(")]
    resolved = [ln for ln in push_body.splitlines()
                if "save-and-push.sh" in ln and "os.path.join" in ln]
    check("bin/board resolves save-and-push.sh under the tool and nowhere else",
          len(resolved) == 1 and "TOOL" in resolved[0]
          and "live.root" not in resolved[0])
    check("and the tool's copy is the one that is actually there",
          os.path.isfile(os.path.join(ROOT, "scripts", "save-and-push.sh"))
          and not os.path.exists(os.path.join(prob, "scripts", "save-and-push.sh")))

    # AND THE SUBJECT LEADS WITH THE WORKSPACE, which is the other half of one
    # door. The commit carries the whole repository, so a history of subjects
    # reading "lesson complete" says nothing about which afternoon each one was.
    # `test/beside.py` holds the same assertion for the save button.
    subject = subprocess.run(["git", "log", "-1", "--format=%s"], cwd=prob,
                             stdout=subprocess.PIPE).stdout.decode().strip()
    check("and the commit subject leads with the workspace, the same as the "
          "save button's",
          subject == "byset: an agreed exercise")

    # AND `push.json` IS THE SAME RECORD EITHER DOOR WROTE. The board draws the
    # last outcome off this file and cannot tell which door made the commit, so
    # a field the save button writes and the terminal does not is a board that
    # says less about a terminal push than about a tap.
    rec = json.load(open(os.path.join(prob, "live", "push.json"), encoding="utf-8"))
    check("and push.json names the workspace, the same field the save button "
          "writes", rec.get("workspace") == "byset")

    # A second push with nothing changed must not rebuild: an ordinary save in
    # the middle of a lesson should cost nothing.
    stamp = os.path.getmtime(pdf)
    code, out = run(prob, "push", "again")
    check("a push with the PDF already current does not rebuild",
          code == 0 and "compiling" not in out and os.path.getmtime(pdf) == stamp)

    # Write to the source, and it is out of date again.
    with open(tex_path, "a", encoding="utf-8") as fh:
        fh.write("\n%% one more agreed exercise\n")
    os.utime(tex_path, (stamp + 10, stamp + 10))
    code, out = run(prob, "push", "and another")
    check("touching the write-up makes the next push rebuild it",
          code == 0 and "compiling" in out)

    # A LaTeX error must not eat the source. The `.tex` is the record.
    with open(os.path.join(scripts, "build.sh"), "w", encoding="utf-8") as fh:
        fh.write('#!/usr/bin/env bash\necho "! Undefined control sequence."\nexit 1\n')
    with open(tex_path, "a", encoding="utf-8") as fh:
        fh.write("\n%% broken\n")
    code, out = run(prob, "push", "with a broken write-up")
    check("a build that fails still pushes the source, which is the record",
          code == 0 and "committed" in out)
    check("and says so loudly rather than shipping a stale PDF in silence",
          "BUILD FAILED" in out)

    # ---- the compiler has to be findable, wherever it is installed --------
    #
    # A course's build.sh knows where TeX lives on the machine it was written on
    # and nowhere else -- Probability's prepends TinyTeX's Linux directory,
    # which on the Mac does not exist. So a board started by a login agent, with
    # a PATH of /usr/bin:/bin and nothing more, ran that script, could not find
    # pdflatex, and reported the failure as the document's. An evening's
    # homework was written up and could not be typeset, and the source was
    # fine the whole time.
    with open(os.path.join(scripts, "build.sh"), "w", encoding="utf-8") as fh:
        fh.write('#!/usr/bin/env bash\n'
                 'printf %s "$PATH" > "$(dirname "$0")/../seen-path"\n'
                 'printf %s "${TEXINPUTS:-}" > "$(dirname "$0")/../seen-inputs"\n'
                 'printf %%s "%%PDF-1.4" > "${1%%.tex}.pdf"\n')
    code, out = run(prob, "hw", "build")
    seen_path = open(os.path.join(prob, "seen-path"), encoding="utf-8").read()
    seen_inputs = open(os.path.join(prob, "seen-inputs"), encoding="utf-8").read()
    check("the course's build script runs with TeX on its PATH",
          all(d in seen_path.split(os.pathsep) for d in tex.tex_bin_dirs()))
    check("and with the board's own macros where LaTeX will look for them",
          os.path.join(ROOT, "tex") in seen_inputs.split(os.pathsep))

    # "FAILED" on its own is what sends somebody to a laptop to discover that
    # nothing was wrong with their mathematics. Whatever the reason -- no
    # compiler on this machine, or a script that discards its own output -- the
    # board has to carry one.
    with open(os.path.join(scripts, "build.sh"), "w", encoding="utf-8") as fh:
        fh.write('#!/usr/bin/env bash\nexit 1\n')
    code, out = run(prob, "hw", "build")
    check("a build that fails silently is still given a reason",
          code != 0 and len(out.strip()) > 40)
    rec = json.load(open(os.path.join(prob, "live", "hw.json"), encoding="utf-8"))
    check("and the reason is recorded for the board to show",
          rec["ok"] is False and len(rec["detail"].strip()) > 40)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("%d FAILURES" % len(fails) if fails else "the board knows which problem set this is")
sys.exit(1 if fails else 0)
