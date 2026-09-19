#!/usr/bin/env python3
"""A project's drawer: what comes next, and what it can be shown.

Galois Theory is painless for one reason that has nothing to do with mathematics:
`chapters.tsv` exists, so the drawer lists eleven chapters and a tap opens one.
A project had nothing, and the drawer said so -- "sittings here are made as you
go" -- which reads as helpful and means *you decide, at a keyboard, every time*.
Reported in those terms: "I don't wanna have to type this shit."

But a working project does write down what it is doing next. It is not called a
syllabus and it is not kept in the repository, and those were the only two
reasons nothing read it. What is guarded here is that reading it stays
discovery rather than configuration, that a path out of a README can never
reach outside the repository, and that a document somebody else wrote is never
offered as though it were one of this project's own.

The tree here is a MONOREPO, because that is what there is now: a family
directory, a workspace inside it, and a README in one workspace pointing across
the tree at a plan in another. That pointer used to reach a SIBLING directory
and now reaches two levels away, which is the one thing about path resolution
the move actually changed -- and the bound is still a bound, which is the
other half and the half worth a test.
"""

import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tutorboard.course import plan, reading      # noqa: E402
from tutorboard import atlas, fenced, machines, sense   # noqa: E402

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


def pdf(path, pages=1):
    """Something big enough to be taken for a document, without a LaTeX run."""
    write(path, "%PDF-1.4\n" + ("%% filler line to clear the size floor\n" * 900))


TODO = """PSYCH-ASR — REMAINING WORK

NOTE TO FUTURE EDITORS: this file tracks what is LEFT to do.

>>> NEXT ACTION (start here in a fresh session) <<<
  STEP 1. THE TYPIST BAKE-OFF — VARY THE ASR MODEL. (Added 2026-09-09.)
    Grade each candidate's words against the corrected reference.
  STEP 2. THE STOPWATCH — AND THE REFERENCE RTTM IT UNBLOCKS. (Added 2026-09-09.)
    Re-align the corrected words to the waveform. Highest value on the list.
    2a. Written long on purpose. A drawer shows two hundred and forty
        characters of a step, and everything a person needs in order to choose
        how to work on this one is written after them, which is the whole
        reason the sheet cannot be asking its question about the blurb.
    2b. THE LAST LINE IS THE POINT, and nothing above it says so.
  STEP 3. THE GRID, WHICH IS A CUBE. (Added 2026-09-09.)
    4 x 2 x 5 = 40 cells, from 13 jobs.

ORIENTATION
  Standing context, not a task. Preserve on every edit.
"""

# A plan that writes both forms, which is what a real one does. `TRD-EHR_TODO.txt`
# opens with five `STEP`s about the manuscript and then keeps thirteen unchecked
# checklist items, and the whole second half of it reached the board nowhere.
BOTH = """TRD-EHR — REMAINING WORK

WHAT WE DO NEXT — READ THIS FIRST, ANSWER FROM IT

  STEP 1. INTEGRATE HIS SECTIONS. Take the rewritten Methods first.
  STEP 4. THE CLARITY PASS — ONE SECTION AT A TIME.
    Out of order on purpose: the plan's numbers are the plan's.

THE FALSIFICATION HALF

- [ ] 5-FOLD CV OVER THE WHOLE PIPELINE. Added 2026-08-28. NOT BUILT.
    The body of an item is read the same way a step's is.
- [x] REFIT INSIDE THE BOOTSTRAP. DONE 2026-08-27. Finished, so not a task.
- [ ] FALSIFICATION BATTERY (all four). The last one.
"""

# --- the sandbox: one repository, three workspaces in two families -----------
# The arrangement these repositories actually use, and the one nothing could
# read: the code is in one workspace and the plan for it is in another, across
# the tree rather than beside it.
home = tempfile.mkdtemp(prefix="tutor-plan-home-")
real_home = os.environ.get("HOME")
real_courses = os.environ.get("TUTORBOARD_COURSES")
proj = os.path.join(home, "research", "PSYCH-ASR")
hub = os.path.join(home, "research", "Research-Journey")
book = os.path.join(home, "courses", "Galois-Theory")
try:
    write(os.path.join(home, "atlas.json"), json.dumps({"families": [
        {"id": "courses", "name": "Courses"},
        {"id": "research", "name": "Research"},
    ]}))
    write(os.path.join(hub, "planning", "PSYCH-ASR_TODO.txt"), TODO)
    pdf(os.path.join(hub, "psych-asr-feasibility", "stage1_pipeline_walkthrough.pdf"))
    pdf(os.path.join(hub, "psych-asr-feasibility", "stage2_reference_walkthrough.pdf"))
    # Somebody else's paper, cited by path in the same README.
    pdf(os.path.join(hub, "paper2-counterfactual", "references",
                     "11_VanderWeeleDing2017_Evalue.pdf"))
    # And a file outside the home entirely, which nothing may reach.
    outside = tempfile.mkdtemp(prefix="tutor-plan-outside-")
    write(os.path.join(outside, "SECRET_TODO.md"), "- [ ] should never be read\n")

    write(os.path.join(proj, "tutorboard.json"), json.dumps({"name": "PSYCH-ASR"}))
    write(os.path.join(proj, "README.md"), """# PSYCH-ASR

This project's live task list is `~/research/Research-Journey/planning/PSYCH-ASR_TODO.txt`.

A conceptual walkthrough of Stage 1 lives at
`~/research/Research-Journey/psych-asr-feasibility/stage1_pipeline_walkthrough.pdf`.
Everything after that deck has its own: `stage2_reference_walkthrough.pdf`, in
the same directory, is the sequel.

The E-value is discussed in
`~/research/Research-Journey/paper2-counterfactual/references/11_VanderWeeleDing2017_Evalue.pdf`.

Do not read %s.
""" % os.path.join(outside, "SECRET_TODO.md"))

    # `~` is written in these READMEs and has to mean this test's home, not the
    # person running it.
    os.environ["HOME"] = home
    # The repository root, for the same reason `HOME` is set: the bound a path
    # out of a README is checked against is the REPOSITORY now, and the test
    # must not be checked against the one this machine really has.
    os.environ["TUTORBOARD_COURSES"] = home
    atlas.forget()
    plan._cache.clear()
    reading._cache.clear()

    # --- where the plan is ---------------------------------------------------
    check("a plan in a hub beside the repository is found from the README",
          plan.where(proj) == "~/research/Research-Journey/planning/PSYCH-ASR_TODO.txt")

    steps = plan.steps(proj)
    check("and its steps are read, in the plan's own order",
          [x["num"] for x in steps] == ["1", "2", "3"])
    check("a step is named by its own first clause, not by its first paragraph",
          steps[0]["title"] == "THE TYPIST BAKE-OFF — VARY THE ASR MODEL")
    check("and the date stamp a human reader wants is not in the title",
          "Added" not in steps[0]["label"])
    check("the label is what a drawer shows and a sitting is filed under",
          steps[2]["label"] == "3. THE GRID, WHICH IS A CUBE")
    # The block that says to start there is honoured; the standing-context
    # section after the steps is not a step.
    check("standing context is not offered as a thing to do",
          not [x for x in steps if "ORIENTATION" in x["label"]])

    # --- a path out of a file is not a path anything will follow -------------
    check("a plan outside the repository is refused, however plainly it is named",
          plan._resolve(proj, os.path.join(outside, "SECRET_TODO.md")) is None)
    check("and so is one reached by climbing out of the tree",
          plan._resolve(proj, "../../../../etc/passwd") is None)
    # The bound WIDENED to the repository when eleven of them became one, and
    # this is what that buys: a README in one workspace naming a plan in
    # another, spelled the way somebody writes it in a file that lives two
    # levels down.
    check("but a plan in another workspace, named relatively, is reached",
          plan._resolve(proj, "../../research/Research-Journey/planning/PSYCH-ASR_TODO.txt")
          == os.path.realpath(os.path.join(hub, "planning", "PSYCH-ASR_TODO.txt")))

    # --- a README names its dependencies' plans too, and a hub owns none -----
    # PSYCH-ASR points at LOCAL-LLM_TODO.txt because it runs on that
    # infrastructure. Taking every plan a README names would put somebody else's
    # next steps under "What's next"; taking the first would have given the hub
    # one project's plan as though it were the whole of what it is doing.
    write(os.path.join(hub, "planning", "LOCAL-LLM_TODO.txt"),
          "STEP 1. WEB ACCESS FOR THE CODING AGENT.\n  Not this project's step.\n")
    write(os.path.join(proj, "README.md"), open(os.path.join(proj, "README.md")).read()
          + "\nIt depends on `~/research/Research-Journey/planning/LOCAL-LLM_TODO.txt`.\n")
    plan._cache.clear()
    check("a plan named after this repository is its own, and the rest are mentions",
          plan.paths(proj) == [os.path.join(hub, "planning", "PSYCH-ASR_TODO.txt")])
    check("so a dependency's steps never appear under what this project does next",
          not [x for x in plan.steps(proj) if "WEB ACCESS" in x["label"]])

    write(os.path.join(hub, "tutorboard.json"), json.dumps({"name": "Research Journey"}))
    write(os.path.join(hub, "README.md"), """# Research Journey

A multi-project narrative hub. The live task lists are
`planning/PSYCH-ASR_TODO.txt` and `planning/LOCAL-LLM_TODO.txt`.
""")
    plan._cache.clear()
    hub_steps = plan.steps(hub)
    check("a hub that owns no plan of its own offers every one it holds",
          len(plan.paths(hub)) == 2)
    check("and says which project each step belongs to",
          [x for x in hub_steps if x["label"].startswith("PSYCH-ASR · ")]
          and [x for x in hub_steps if x["label"].startswith("LOCAL-LLM · ")])
    check("while a project with one plan is not made to say its own name",
          not [x for x in plan.steps(proj) if " · " in x["label"]])
    plan._cache.clear()

    # --- EVERY FORM THE PLAN WROTE, IN THE PLAN'S OWN ORDER -----------------
    #
    # `_collect` was called once per kind and broke at the first kind that
    # matched anything, so a plan opening with `STEP` entries was those entries
    # and nothing else. Half of TRD-EHR -- the falsification battery, the 5-fold
    # CV, the entire counterfactual half -- was invisible on the board, and so
    # was any checklist item added to it afterwards.
    write(os.path.join(hub, "planning", "TRD-EHR_TODO.txt"), BOTH)
    write(os.path.join(proj, "tutorboard.json"),
          json.dumps({"name": "TRD-EHR",
                      "plan": "~/research/Research-Journey/planning/TRD-EHR_TODO.txt"}))
    plan._cache.clear()
    both = plan.steps(proj)
    check("a plan's numbered steps and its checklist items are all read",
          [x["title"] for x in both] == [
              "INTEGRATE HIS SECTIONS",
              "THE CLARITY PASS — ONE SECTION AT A TIME",
              "5-FOLD CV OVER THE WHOLE PIPELINE",
              "FALSIFICATION BATTERY (all four)"])
    check("a finished item is not offered as a thing to do",
          not [x for x in both if "REFIT INSIDE THE BOOTSTRAP" in x["title"]])
    # THE NUMBERING RULE. A `STEP` keeps the number the plan gave it, because a
    # person reading the file and a person reading the drawer have to be talking
    # about the same step -- so step 4 is 4 even though it is the second entry.
    # An item has no number of its own and takes its place in the merged
    # sequence, which is what stops the first item being a second 1 on a picture
    # that already has one.
    check("a numbered step keeps the plan's number, wherever it falls",
          [x["num"] for x in both[:2]] == ["1", "4"])
    check("and an item numbers on from the steps rather than restarting at 1",
          [x["num"] for x in both[2:]] == ["3", "4"])
    check("no two steps answer to one label, because a label is the lookup key",
          len(set(x["label"] for x in both)) == len(both))
    # The stop line is the next entry of ANY kind. A step whose summary ran on
    # over the items after it was matched against every module they mention,
    # and its chip landed on boxes it says nothing about.
    check("an item's body is read the same way a step's is",
          "read the same way a step's is" in both[2]["summary"])
    check("the item before a finished one stops there too, and does not "
          "swallow it", "DONE 2026-08-27" not in both[2]["summary"])
    write(os.path.join(proj, "tutorboard.json"), json.dumps({"name": "PSYCH-ASR"}))
    os.remove(os.path.join(hub, "planning", "TRD-EHR_TODO.txt"))
    plan._cache.clear()

    # --- a repository that declares one outright ----------------------------
    write(os.path.join(proj, "MY_PLAN.md"),
          "## First thing\nDo it.\n\n## Second thing\nThen this.\n")
    write(os.path.join(proj, "tutorboard.json"),
          json.dumps({"name": "PSYCH-ASR", "plan": "MY_PLAN.md"}))
    plan._cache.clear()
    check("a repository that declares a plan is believed over its own README",
          plan.where(proj) == "MY_PLAN.md")
    check("and a plan written as headings is read as steps",
          [x["title"] for x in plan.steps(proj)] == ["First thing", "Second thing"])
    write(os.path.join(proj, "tutorboard.json"), json.dumps({"name": "PSYCH-ASR"}))
    os.remove(os.path.join(proj, "MY_PLAN.md"))
    plan._cache.clear()

    # --- a course that follows a book has a syllabus instead ----------------
    write(os.path.join(book, "chapters.tsv"), "01\t1\t9\tch01-a\tGroups\n")
    write(os.path.join(book, "README.md"), "# Galois Theory\n\nA course.\n")
    check("a book course has no plan, and that is an answer rather than a gap",
          plan.path(book) is None and plan.status(book, {}) is None)

    # --- the documents ------------------------------------------------------
    docs = reading.documents(proj)
    ids = [d["id"] for d in docs]
    check("a deck the README names by path is offered",
          "stage1-pipeline-walkthrough" in ids)
    # "in the same directory" is how a README names the second one, and it is
    # the sentence that made the more useful of the two unreachable.
    check("and so is the one it names by filename alone, beside the first",
          "stage2-reference-walkthrough" in ids)
    # A README cites the papers it is built on. They are not this project's
    # documents and offering them buries the two that are.
    check("somebody else's paper in a reference library is not offered",
          not [i for i in ids if "vanderweele" in i.lower()])
    check("a document is named the way its author says it out loud",
          docs[0]["name"] == "stage1 pipeline walkthrough")

    # An id from a request is checked by lookup, never by construction.
    target, name = reading.find(proj, "stage2-reference-walkthrough")
    check("an id resolves to the file it names", target and os.path.isfile(target))
    check("and one this course does not offer resolves to nothing",
          reading.find(proj, "../../../etc/passwd") == (None, None)
          and reading.find(proj, "not-a-document") == (None, None))

    # --- THE FENCE, WHICH IS NOT A DEPTH AND NOT A SIZE FLOOR ---------------
    #
    # `research/PSYCH-ASR/phi/` is session content: the recordings, the turn
    # tables, the joined transcripts. `manuscript.py` refused that directory by
    # name and this module did not, so `phi/stage1/Audio Transcription.pdf` was
    # offered in the drawer under the id `audio-transcription`, `paper.pages_of`
    # rendered it to PNGs, and `sense.reading_sense` wrote its address into a
    # tutor's prompt beside an instruction to open and read a page before showing
    # one. One rule, two lists, one of them wrong. `tutorboard/fenced.py` is the
    # one list now.
    #
    # Fat enough to clear the size floor and shallow enough to be walked to, so
    # that what refuses it is the refusal rather than either bound.
    fence = os.path.join(proj, "phi", "stage1")
    pdf(os.path.join(fence, "Audio Transcription.pdf"))
    write(os.path.join(proj, "README.md"), """# PSYCH-ASR

This project's live task list is `~/research/Research-Journey/planning/PSYCH-ASR_TODO.txt`.
A walkthrough is at `~/research/Research-Journey/psych-asr-feasibility/stage1_pipeline_walkthrough.pdf`,
and `stage2_reference_walkthrough.pdf` is in the same directory.

The session content is under `phi/stage1/Audio Transcription.pdf`.
""")
    reading._cache.clear()
    fenced_ids = [d["id"] for d in reading.documents(proj)]
    check("a document inside the fenced directory is offered nowhere, however "
          "plainly the README names it",
          "audio-transcription" not in fenced_ids)
    check("and the two decks that are this project's own are still offered",
          "stage1-pipeline-walkthrough" in fenced_ids
          and "stage2-reference-walkthrough" in fenced_ids)
    check("an id naming it resolves to nothing, so nothing renders it",
          reading.find(proj, "audio-transcription") == (None, None))
    check("and the walk does not reach it either",
          not [p for p in reading._in_repo(proj) if "Audio Transcription" in p])
    check("nor does the README-pointer path, which is the one the directory "
          "test alone would have walked past",
          not [p for p in reading._pointed_at(proj)
               if "Audio Transcription" in p])
    check("the refusal is by directory name at any depth",
          reading._fenced(os.path.join("a", "b", "c", "phi", "x.pdf"))
          and not reading._fenced(os.path.join(
              "docs", "stage2_reference_walkthrough.pdf")))
    fenced_line = sense.reading_sense(type("R", (), {"root": proj})())
    check("and a tutor is never told the address of a page of it",
          "audio-transcription" not in fenced_line
          and "stage2-reference-walkthrough" in fenced_line)

    # --- AND THE SAME QUESTION ASKED OF THE WHOLE WORKSPACE -----------------
    #
    # Every check above is the fence refusing a PATH that was about to be handed
    # to something. None of them answers the question a person asks before any
    # of it: *does this box hold content only one assistant may read?* Nothing
    # did, so the `who:` row offered a hosted model here exactly as it does in a
    # course, and the only thing between that tap and a hosted model reaching
    # for session content was a hook the person cannot see.
    #
    # ONE LEVEL DEEP, because this labels a workspace on a chooser rather than
    # guarding a file about to be opened. The names themselves, not a flag: a
    # row saying `phi/` names something a person can go and look at.
    fenced.forget()
    check("a workspace holding a fenced directory says so, by name",
          fenced.holds(proj) == ("phi",))
    check("and one that holds none says nothing, which is every other workspace",
          fenced.holds(book) == ())
    os.makedirs(os.path.join(book, "test_data"), exist_ok=True)
    write(os.path.join(book, "docs", "stage2_reference_walkthrough.pdf"), "x")
    fenced.forget()
    check("a directory whose name merely CONTAINS one is not a fence, and "
          "neither is a file named after one",
          fenced.holds(book) == ())
    os.makedirs(os.path.join(book, "chapters", "data"), exist_ok=True)
    fenced.forget()
    check("nor is one two levels down, which is a vendored dependency's "
          "working directory rather than this workspace's fence",
          fenced.holds(book) == ())
    shutil.rmtree(os.path.join(book, "chapters", "data"))
    shutil.rmtree(os.path.join(book, "test_data"))
    shutil.rmtree(os.path.join(book, "docs"))

    # And it reaches the board attached to the workspace it is about, which is
    # what lets a dispatcher say it about a box nobody is looking at.
    fenced.forget()
    listed = {w["repo"]: w.get("fenced")
              for w in machines.workspaces(type("R", (), {"root": book})())}
    check("every workspace the board lists carries its own answer",
          listed.get("PSYCH-ASR") == ["phi"]
          and listed.get("Research-Journey") == [])

    shutil.rmtree(os.path.join(proj, "phi"))
    fenced.forget()
    reading._cache.clear()

    # --- what the tutor is told ---------------------------------------------
    write(os.path.join(proj, "README.md"), """# PSYCH-ASR

This project's live task list is `~/research/Research-Journey/planning/PSYCH-ASR_TODO.txt`.
A walkthrough is at `~/research/Research-Journey/psych-asr-feasibility/stage1_pipeline_walkthrough.pdf`,
and `stage2_reference_walkthrough.pdf` is in the same directory.
""")
    plan._cache.clear()
    reading._cache.clear()

    line = sense.where_sense(None, proj)
    check("a project's tutor is told where the plan is, by name",
          "~/research/Research-Journey/planning/PSYCH-ASR_TODO.txt" in line)
    # The round trips this removes: a 1,500-line README, a pointer out of it,
    # and a 1,300-line task list, paid for on every cold turn.
    check("and handed the steps rather than sent to find them",
          "THE TYPIST BAKE-OFF" in line and "THE GRID" in line)
    check("and told the plan outranks anything it would have chosen",
          "OUTRANKS ANYTHING YOU WOULD HAVE CHOSEN" in line)
    check("and told to open the step this sitting is labelled with",
          "the step this sitting is labelled with" in line)
    check("a project with no plan is still told to read what the README points at",
          "follow what it points at" in sense.where_sense(None, book))

    class FakeRepo(object):
        root = proj
    line = sense.reading_sense(FakeRepo())
    check("and told which documents it can put on a card",
          "stage2-reference-walkthrough" in line and "stage1-pipeline-walkthrough" in line)
    check("and exactly how to put a page of one there",
          "/doc/" in line and "24.png" in line)
    # A slide is an object to work on. A tutor that pastes one instead of asking
    # a question has written the word dump this whole arrangement replaces.
    check("and that a slide never replaces the question",
          "not an explanation that replaces the exercise" in line)
    check("a course with no documents is told nothing about slides",
          sense.reading_sense(type("R", (), {"root": book})()) == "")
finally:
    if real_home is not None:
        os.environ["HOME"] = real_home
    if real_courses is None:
        os.environ.pop("TUTORBOARD_COURSES", None)
    else:
        os.environ["TUTORBOARD_COURSES"] = real_courses
    atlas.forget()
    shutil.rmtree(home, ignore_errors=True)
    shutil.rmtree(outside, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a project has a syllabus after all, and the board can show it")
