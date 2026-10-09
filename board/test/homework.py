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
\newenvironment{problem}[1]{\par\noindent\textbf{Problem #1.}\ }{\par}
\newcommand{\todo}[1]{\textbf{[TODO: #1]}}
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

    code, out = run(prob, "hw", "use", "hw04")
    check("`board hw use` binds the sitting to a set", code == 0 and "hw04" in out)
    with open(os.path.join(prob, "live", "state.json"), encoding="utf-8") as fh:
        state = json.load(fh)
    check("and records which one", state.get("hw") == "homework/hw04/hw04.tex")

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

    # --- the book's chapters, read off the chapter directories ---------------
    check("a course's chapters come off its chapter directories",
          [(c["num"], c["title"]) for c in homework.chapters(gal)]
          == [("7", "splitting fields")]
          and homework.chapter_label(homework.opening(gal))
          == "Ch 7 — splitting fields"
          and homework.chapter_dir(gal, "Ch 7 — splitting fields")
          == "chapters/ch07-splitting-fields"
          and homework.chapters(prob) == [])
    code, out = run(gal, "hw", "new", "ch07")
    with open(os.path.join(gal, "live", "state.json"), encoding="utf-8") as fh:
        pinned = json.load(fh).get("hw")
    check("`board writeup new chNN` writes into that chapter's set",
          code == 0 and pinned
          == "chapters/ch07-splitting-fields/homework/ch07-homework.tex"
          and not os.path.isdir(os.path.join(gal, "docs")))
    code, out = run(gal, "brief")
    check("and the brief lists the book's chapters",
          code == 0 and "book: 1 chapter -- 7 splitting fields" in out)
    code, out = run(prob, "brief")
    check("a subject with no chapters has no book line", "\nbook: " not in out)

    # ---- a write-up for something that has none -----------------------------
    #
    # Every session produces a compiled document, and most workspaces are not
    # courses: there is no chapter to bind and no sheet to bind to. The session's
    # own write-up is an artifact at docs/<slug>/writeup.tex, from the one
    # template, found by the session's pin and never listed as a set.
    bare = os.path.join(tmp, "bare")
    write(os.path.join(bare, "tutorboard.json"), '{"name": "B", "mode": "math"}')
    check("a workspace can start with no sets at all", homework.sets(bare) == [])

    made, new = homework.start(bare, {}, title="Notes on Yoneda")
    check("one can be started by title", new and made["name"] == "notes-on-yoneda")
    check("as the session's own artifact under docs/",
          made["rel"] == os.path.join("docs", "notes-on-yoneda", "writeup.tex")
          and os.path.isfile(os.path.join(bare, "docs", "notes-on-yoneda", "doc.json")))
    check("which is no problem set", homework.sets(bare) == [])
    check("and is found by its pin",
          (homework.bound(bare, {"hw": made["rel"]}) or {}).get("name")
          == "notes-on-yoneda"
          and (homework.status(bare, {"hw": made["rel"]}) or {}).get("total") == 0)

    body = open(made["tex"], encoding="utf-8").read()
    check("it carries a title somebody chose", "\\title{Notes on Yoneda}" in body)
    check("and stands alone where there is no coursemacros.sty, using them where "
          "there is", "newenvironment{problem}" in body
          and "IfFileExists{coursemacros.sty}{\\usepackage{coursemacros}}" in body)

    again, new2 = homework.start(bare, {"hw": made["rel"]})
    check("starting it again is the same write-up, untouched",
          not new2 and again["tex"] == made["tex"]
          and open(made["tex"], encoding="utf-8").read() == body)

    said, why = homework.add(made["tex"], "1", "Show it.", "It is shown.")
    said2, _ = homework.add(made["tex"], "2", "", "And this.")
    st = homework.status(bare, {"hw": made["rel"]})
    check("added answers are problems in the order they were agreed",
          said["region"] == "added" and said2["statement"] == "placeholder"
          and [p["label"] for p in st["problems"]] == ["1", "2"]
          and st["written"] == 2 and st["stated"] == 1)

    code, out = run(bare, "writeup", "new", "Second", "Topic")
    check("the command line starts one too",
          code == 0 and "docs/second-topic/writeup.tex" in out)
    with open(os.path.join(bare, "live", "state.json"), encoding="utf-8") as fh:
        check("and pins the sitting to it",
              json.load(fh).get("hw", "").endswith("second-topic/writeup.tex"))

    # ---- the brief carries the debt, in a LECTURE, with nothing pinned -------
    #
    # A chapter's exercises get worked in sittings opened as lectures, and the
    # write-up is owed there exactly as it is in a homework sitting. The brief
    # used to print a homework line only when `state["hw"]` was set, which only
    # `board hw use` and a homework sitting write. So a lecture opened as "Ch 4" was
    # never once told that a file existed and was empty; an evening of agreed
    # mathematics stayed in the cards, and what compiled was the scaffold.
    #
    # The counts are the point, not the name. "homework set: ch07" is a fact
    # about configuration and reads as already handled. "0 of 3 written up" is
    # a debt.
    write(os.path.join(gal, "live", "state.json"), json.dumps(
        {"course": "G", "chapter": "Ch 07 — splitting fields",
         "session": "lecture"}))
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

    # Real LaTeX, through `board build`: the set compiles as it stands. A
    # machine with no TeX skips the checks that need a PDF.
    HAVE_TEX = tex.have_tex()

    # A real throwaway repository with NO origin: `gitops.save` commits and
    # says so, which is every part of a push this suite is about and none of
    # the network.
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
          code == 0 and "compiling" in out
          and (os.path.exists(pdf) or not HAVE_TEX))
    check("and says which set it built", "hw05" in out)
    check("and then actually commits", "committed" in out)

    # ONE PATH TO A COMMIT: `board push` and the save button both go through
    # `gitops.save`, so the terminal's door cannot drift from the iPad's.
    src = open(os.path.join(ROOT, "bin", "board"), encoding="utf-8").read()
    push_body = src[src.index("def cmd_push("):src.index("def cmd_slate(")]
    check("bin/board commits through gitops.save and runs no script of its own",
          "gitops.save(top, specs, message)" in push_body
          and "save-and-push.sh" not in push_body)

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
    stamp = os.path.getmtime(pdf) if HAVE_TEX else 0
    code, out = run(prob, "push", "again")
    check("a push with the PDF already current does not rebuild",
          not HAVE_TEX or (code == 0 and "compiling" not in out
                           and os.path.getmtime(pdf) == stamp))

    # Write to the source, and it is out of date again.
    with open(tex_path, "a", encoding="utf-8") as fh:
        fh.write("\n%% one more agreed exercise\n")
    os.utime(tex_path, (stamp + 10, stamp + 10))
    code, out = run(prob, "push", "and another")
    check("touching the write-up makes the next push rebuild it",
          code == 0 and "compiling" in out)

    # A LaTeX error must not eat the source. The `.tex` is the record.
    with open(tex_path, "r", encoding="utf-8") as fh:
        good = fh.read()
    with open(tex_path, "w", encoding="utf-8") as fh:
        fh.write(good.replace("\\end{document}",
                              "\\undefinedmacrohere\n\\end{document}"))
    code, out = run(prob, "push", "with a broken write-up")
    check("a build that fails still pushes the source, which is the record",
          code == 0 and "committed" in out)
    check("and says so loudly rather than shipping a stale PDF in silence",
          "BUILD FAILED" in out)

    # ---- the compiler has to be findable, wherever it is installed --------
    #
    # `board hw build` goes through `board build`, which finds TeX wherever
    # this machine installed it and puts the board's macros on TEXINPUTS. A
    # board started by a login agent has a PATH of /usr/bin:/bin.
    from tutorboard import build
    env = build.tex_env_for(tex_path)
    check("the build runs with TeX on its PATH",
          all(d in env["PATH"].split(os.pathsep) for d in tex.tex_bin_dirs()))
    check("and with the board's own macros where LaTeX will look for them",
          os.path.join(ROOT, "tex") in env["TEXINPUTS"].split(os.pathsep))

    # "FAILED" on its own is what sends somebody to a laptop to discover that
    # nothing was wrong with their mathematics. The board has to carry the
    # reason: the LaTeX error, or that this machine has no LaTeX.
    code, out = run(prob, "hw", "build")
    check("a build that fails is given a reason",
          code != 0 and ("Undefined control sequence" in out
                         or (not HAVE_TEX and "No LaTeX" in out)))
    rec = json.load(open(os.path.join(prob, "live", "hw.json"), encoding="utf-8"))
    check("and the reason is recorded for the board to show",
          rec["ok"] is False and len(rec["detail"].strip()) > 40)

    with open(tex_path, "w", encoding="utf-8") as fh:
        fh.write(good)
    code, out = run(prob, "hw", "build")
    check("and once it is fixed, hw build compiles it beside the source",
          not HAVE_TEX or (code == 0 and os.path.exists(pdf)
                           and not os.path.exists(os.path.splitext(tex_path)[0] + ".aux")))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("%d FAILURES" % len(fails) if fails else "the board knows which problem set this is")
sys.exit(1 if fails else 0)
