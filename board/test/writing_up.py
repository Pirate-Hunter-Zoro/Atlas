#!/usr/bin/env python3
"""Handing a manuscript job to Paper-Writer -- and not becoming it.

    "keep the seam to one function: a `make` sitting in workspace W assembles a
     job ... drops it in Paper-Writer's inbox, and the delivered manuscript
     lands in W under a tracked path. ... Do not fold Paper-Writer's engine into
     the board."

The checks are about the ways a seam like this stops being a seam.

  * THE BOARD DOES NOT RUN THE FACTORY. It writes one file into a directory and
    reads a status file back. No import, no process, no second opinion about
    somebody else's job. The moment this module knows how a manuscript is
    written there are two engines and one of them is behind.
  * A JOB IS NEVER POINTED AT SESSION CONTENT. `PAPER_SOURCE_DIRS` is what the
    gathering stage may mine, and one workspace in this repository holds
    identifiable therapy audio and its transcripts. The list is an ALLOWLIST and
    there is a second refusal by directory name behind it, because the failure is
    silent and one-way: a job naming that tree would be admitted, gathered, and
    every number in the ledger would come from patient data in a manuscript
    nobody would think to check.
  * NOTHING IN A JOB IS INVENTED. The claims are the plan's own steps, offered as
    WORK rather than as claims, because a step is a thing to do and a claim is a
    thing to argue. The venue and the checklist are left blank on purpose -- the
    template says a wrong venue plans to the wrong length and an inferred
    checklist places the wrong obligations.
  * A JOB APPEARS WHOLE. The harness admits a file once it has stopped changing,
    so a file that appears empty and grows is one it may read halfway through.
"""

import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tutorboard import atlas, manuscript                              # noqa: E402
from tutorboard.course import map as course_map, plan                 # noqa: E402

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


PAD = "\n" + ("# padding, to clear the size floor on a walkable file\n" * 12)
PHI = "p" + "hi"

TODO = """PROJECT — REMAINING WORK

>>> NEXT ACTION <<<
  STEP 1. GRADE THE ARMS AGAINST THE CORRECTED REFERENCE.
    It lives in psych_asr/evaluate/grade.py.
  STEP 2. RUN THE GRID.
"""

base = tempfile.mkdtemp(prefix="tutor-ms-")
try:
    import json
    write(os.path.join(base, "atlas.json"), json.dumps(
        {"families": [{"id": "research", "name": "Research"},
                      {"id": "projects", "name": "Projects"}]}))
    proj = os.path.join(base, "research", "PSYCH-ASR")
    writer = os.path.join(base, "projects", "Paper-Writer")
    for r in (proj, writer):
        write(os.path.join(r, "tutorboard.json"), "{}\n")
        os.makedirs(os.path.join(r, "live"), exist_ok=True)

    write(os.path.join(proj, "psych_asr", "evaluate", "grade.py"),
          "def grade():\n    return 1" + PAD)
    write(os.path.join(proj, "planning", "TODO.txt"), TODO)
    write(os.path.join(proj, "README.md"), "# P\n\nThe plan is planning/TODO.txt\n")
    # What a job may be pointed at, and what it must never be.
    os.makedirs(os.path.join(proj, "results"), exist_ok=True)
    os.makedirs(os.path.join(proj, "figures"), exist_ok=True)
    os.makedirs(os.path.join(proj, PHI, "stage1"), exist_ok=True)
    os.makedirs(os.path.join(proj, "data", "raw"), exist_ok=True)
    write(os.path.join(proj, "manuscripts", "01-methods.md"), "# Methods\n")

    atlas.forget()
    os.environ["TUTORBOARD_COURSES"] = base
    os.environ.pop("PAPER_OUT_DIR", None)
    os.environ.pop("PAPER_INBOX_DIR", None)

    # --- the factory is FOUND, not configured -------------------------------
    check("Paper-Writer is found the way every workspace is found",
          manuscript.writer_root(base) == writer)
    check("and the drop folder is resolved from its own configuration",
          manuscript.inbox(base).endswith(os.path.join("Manuscripts", "_inbox")))

    # `service/paperwriter.env` is deliberately "plain KEY=value with no logic",
    # which is the only reason it is safe to read rather than run.
    write(os.path.join(writer, "service", "paperwriter.env"),
          "# a comment\nPAPER_OUT_DIR=../Delivered\nPAPER_MODEL=claude-opus-5\n")
    check("what this machine actually runs with outranks the documented default",
          manuscript.out_dir(base).endswith("Delivered"))
    os.remove(os.path.join(writer, "service", "paperwriter.env"))

    # --- a job is never pointed at session content --------------------------
    found = manuscript._evidence(proj)
    check("a job is pointed at the results and the figures",
          any(f.endswith("results") for f in found)
          and any(f.endswith("figures") for f in found))
    check("and NEVER at the session content, whatever else is in the workspace",
          not any(PHI in f for f in found))
    check("nor at a data tree, which is where all of it used to live",
          not any("/data" in f for f in found))
    for bad in (PHI, "data", "inbox", "stage1", "stage2", "raw", "audio",
                "/a/b/%s/stage1" % PHI, "x/data/raw"):
        check("refused as a tree to mine: %r" % bad, manuscript.refused(bad))
    for good in ("results", "figures", "tables", "results/roc"):
        check("allowed as a tree to mine: %r" % good,
              not manuscript.refused(good))

    # --- nothing in a job is invented ---------------------------------------
    body = manuscript.job(proj, title="The bake-off")
    check("the job is the template's own shape", all(
        h in body for h in ("## Evidence", "## Claims", "## Venue",
                            "## Reporting checklist", "## Scope")))
    check("the plan's own steps are in it",
          "GRADE THE ARMS" in body and "RUN THE GRID" in body)
    check("and they are offered as WORK, not as claims",
          "NOT CLAIMS YET" in body)
    check("the venue is left blank on purpose",
          "NOT KNOWN TO THE BOARD" in body)
    check("and so is the checklist, which the template says is never inferred",
          "NEVER INFERRED" in body)
    check("prose that already exists here is named, so it is not written twice",
          "manuscripts/01-methods.md" in body)
    check("and the job says where the finished paper is to land",
          "research/PSYCH-ASR/manuscripts" in body)

    # The written map, spent again: a terminology lock half-written.
    course_map.write_written(proj, {
        "version": 1,
        "nodes": [{"id": "grader", "name": "the grader",
                   "also": "psych_asr.evaluate.grade",
                   "does": "Reproduces the annotator's own error labels.",
                   "files": ["psych_asr/evaluate/grade.py"]}]})
    course_map._cache.clear()
    plan._cache.clear()
    body = manuscript.job(proj, title="The bake-off")
    check("a drawn workspace hands over its own names for its own parts",
          "the grader" in body and "psych_asr.evaluate.grade" in body)
    check("and is told to add the aliases, which is the half that does the work",
          "ALIASES" in body)

    # --- dropping it --------------------------------------------------------
    dry = manuscript.submit(proj, title="The bake-off", base=base, dry_run=True)
    check("a dry run prints the job and drops nothing",
          dry["ok"] and not os.path.isdir(manuscript.inbox(base)))

    rec = manuscript.submit(proj, title="The bake-off", base=base)
    check("a job is dropped in the inbox", rec["ok"]
          and os.path.isfile(rec["path"]))
    check("named v1, not stamped with the time", rec["name"].endswith("-v1.md"))
    again = manuscript.submit(proj, title="The bake-off", base=base)
    check("and a second job counts up rather than overwriting the first",
          again["name"].endswith("-v2.md") and os.path.isfile(rec["path"]))
    check("nothing half-written is left behind for the harness to admit",
          not any(n.endswith(".part")
                  for n in os.listdir(manuscript.inbox(base))))
    check("the board says the job WAITS rather than pretending to start it",
          "waits" in rec["detail"] or "waiting" in rec["detail"])

    queued = manuscript.waiting(base)
    check("and both jobs are reported as waiting", len(queued) == 2)

    # --- reading what comes back --------------------------------------------
    said = manuscript.status(base)
    check("with no status file, the board says so rather than inventing progress",
          said["ok"] and not said["said"])
    write(os.path.join(manuscript.out_dir(base), "_STATUS.md"),
          "# Status\n\nThe bake-off: DRAFTING, section 3 of 7.\n")
    said = manuscript.status(base)
    check("and when there is one, it shows what the FACTORY says, verbatim",
          "DRAFTING, section 3 of 7" in said["said"])

    # WHAT IS IN `manuscripts/` IS THE MANUSCRIPT, however it got there. The
    # board does not distinguish a paper the factory delivered from prose
    # somebody wrote by hand, and should not: "the delivered manuscript lands in
    # W under a tracked path. Then it is a document like any other." A record of
    # which half came from where would be a second ledger about somebody else's
    # job, and it would be wrong the first time anybody edited a delivered file.
    check("a workspace with nothing but its own prose has that, and no error",
          [d["rel"] for d in manuscript.delivered(proj)]
          == [os.path.join("manuscripts", "01-methods.md")])
    write(os.path.join(proj, "manuscripts", "bake-off.md"), "# The bake-off\n")
    got = manuscript.delivered(proj)
    check("and a manuscript that lands beside it is found too",
          any(d["rel"].endswith("bake-off.md") for d in got) and len(got) == 2)
    check("newest first, because that is the one somebody just asked for",
          got[0]["at"] >= got[1]["at"])

    # --- the seam is a seam --------------------------------------------------
    src = open(os.path.join(ROOT, "tutorboard", "manuscript.py"),
               encoding="utf-8").read()
    check("the board never imports the factory",
          "import paperwriter" not in src and "from paperwriter" not in src)
    check("and never starts a process",
          "subprocess" not in src and "os.system" not in src
          and "popen" not in src.lower())

    # --- a repository with no factory ---------------------------------------
    shutil.rmtree(writer)
    atlas.forget()
    none = manuscript.submit(proj, title="x", base=base)
    check("a repository with no factory says so instead of failing oddly",
          not none["ok"] and "Paper-Writer" in none["detail"])

finally:
    os.environ.pop("TUTORBOARD_COURSES", None)
    atlas.forget()
    shutil.rmtree(base, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a job is handed over, and the board does not become the thing it hands to")
