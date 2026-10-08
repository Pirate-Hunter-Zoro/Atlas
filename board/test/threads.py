#!/usr/bin/env python3
"""A project's spine is deliverables and threads, and a thread's status is derived.

What the checks are about:

  * THE FILE IS REFUSED WHOLE. A thread file with any problem is not written,
    and every problem comes back at once.
  * STATUS IS A FACT, NOT A FIELD. done, running, written, result, open -- the
    first true row wins, and only `closed` is typed.
  * GIT CAN SEE IT. `threads.json` sits at the workspace root because a
    workspace that ignores `live/` wholesale could never track it inside there,
    and `board thread` refuses aloud where a rule hides it.
  * THE WRITTEN MAPS ARE MIGRATED. PSYCH-ASR's and libr-local-llm's boxes are
    threads now, and their `live/map.json` is gone.
  * ONE PLAN, NOT TWO. A thread file's open tasks are the plan's steps.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
from tutorboard.course import map as mapping, plan, reading, threads  # noqa: E402

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


def run(cwd, args, stdin=""):
    p = subprocess.run([sys.executable, BOARD] + list(args), cwd=cwd,
                       input=stdin.encode("utf-8"), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=120)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def fresh():
    threads._cache.clear()
    mapping._cache.clear()
    plan._cache.clear()


def git(cwd, *args):
    subprocess.run(["git"] + list(args), cwd=cwd, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, check=False)


GOOD = {
    "version": 1,
    "deliverables": [{"id": "paper1", "title": "Paper 1",
                      "doc": "paper/manuscript.md"}],
    "threads": [
        {"id": "knn", "deliverable": "paper1", "title": "Weighted neighbours",
         "question": "Does weighting beat cosine?",
         "files": ["scripts/knn.py"],
         "outputs": ["results/knn.csv"],
         "writes": [{"file": "paper/manuscript.md",
                     "anchor": "## Nearest-neighbour retrieval"}],
         "tasks": [{"text": "Draw the figure", "done": False},
                   {"text": "Run the sweep", "done": True}],
         "decisions": [{"q": "How to count dimensions", "rule": None}],
         "blockedBy": [], "closed": False},
        {"id": "tripod", "deliverable": "paper1", "title": "TRIPOD checklist",
         "blockedBy": ["knn"]},
    ],
}

home = tempfile.mkdtemp(prefix="tutor-threads-")
try:
    # --- validation: refused whole, every problem at once -------------------
    clean, problems = threads.validate(GOOD)
    check("a good thread file validates", clean is not None and not problems)
    check("a decision with no rule is open, and a missing field takes its default",
          clean["threads"][0]["decisions"][0]["rule"] is None
          and clean["threads"][1]["tasks"] == []
          and clean["threads"][1]["closed"] is False)
    for bad, why in (
            (dict(GOOD, version=2), "a version this reader does not know"),
            (dict(GOOD, deliverables=[]), "no deliverable at all"),
            (dict(GOOD, threads=[{"id": "Not An Id", "deliverable": "paper1",
                                  "title": "x"}]), "an id that is not an id"),
            (dict(GOOD, threads=[{"id": "a", "deliverable": "ghost",
                                  "title": "x"}]),
             "a thread on a deliverable the file does not declare"),
            (dict(GOOD, threads=[{"id": "a", "deliverable": "paper1",
                                  "title": "x",
                                  "files": ["../../etc/passwd"]}]),
             "a path that climbs out of the workspace"),
            (dict(GOOD, threads=[{"id": "a", "deliverable": "paper1",
                                  "title": "x", "blockedBy": ["ghost"]}]),
             "a blockedBy naming a thread the file does not declare"),
            (dict(GOOD, threads=[{"id": "a", "deliverable": "paper1",
                                  "title": "x", "doc": "docs/a.pdf"}]),
             "a doc written as a path"),
            (dict(GOOD, threads=[{"id": "a", "deliverable": "paper1",
                                  "title": "x",
                                  "writes": [{"file": "m.md"}]}]),
             "a write-up with no anchor"),
            (dict(GOOD, threads=[{"id": "a", "deliverable": "paper1",
                                  "title": "x",
                                  "tasks": [{"text": "t", "done": "yes"}]}]),
             "a task whose done is not a boolean")):
        clean, problems = threads.validate(bad)
        check("refused: " + why, clean is None and len(problems) >= 1)
    clean, problems = threads.validate(
        {"version": 9, "deliverables": [{"id": "Bad"}], "threads": "no"})
    check("and every problem comes back at once",
          clean is None and len(problems) >= 3)

    # --- status: the first true row wins ------------------------------------
    t = threads.validate(GOOD)[0]["threads"][0]
    out, doc = "results/knn.csv", "paper/manuscript.md"
    anchored = {doc: "# Paper\n\n## Nearest-neighbour retrieval\n\nText."}
    job = {"thread": "knn", "jobid": "42", "cmd": "sbatch x", "produces": [out],
           "submitted": 0}

    def st(**kw):
        base = dict(present=set(), texts={}, dirty=[], jobs=[])
        base.update(kw)
        return threads.stage(t, **base)

    check("open: nothing it produces exists yet", st()["status"] == "open")
    check("result: every output exists",
          st(present={out})["status"] == "result")
    check("written: every output exists and every anchor is found",
          st(present={out}, texts=anchored)["status"] == "written")
    check("an output that exists with its anchor missing is a result, not written",
          st(present={out}, texts={doc: "# Paper"})["status"] == "result")
    check("running: a registered job is pending or running, whatever exists",
          st(present={out}, texts=anchored, jobs=[job])["status"] == "running")
    check("a job sacct called finished is not running",
          st(present={out}, jobs=[job, {"jobid": "42", "state": "COMPLETED"}])
          ["status"] == "result")
    check("a failed job is finished too",
          st(jobs=[job, {"jobid": "42", "state": "FAILED"}])["status"] == "open")
    check("another thread's job is not this one's",
          st(jobs=[dict(job, thread="tripod")])["status"] == "open")
    check("done: the owner closed it, and that beats a running job",
          threads.stage(dict(t, closed=True), set(), {}, [], [job])["status"]
          == "done")
    check("an open decision is a flag beside the status",
          st()["decisions"] == 1 and st()["tasks"] == 1)
    check("unsaved: git shows a change under one of the thread's paths",
          st(dirty=["scripts/knn.py"])["unsaved"] is True
          and st(dirty=["paper/manuscript.md"])["unsaved"] is True
          and st(dirty=["scripts/other.py"])["unsaved"] is False)
    bare = threads.validate(GOOD)[0]["threads"][1]
    check("a thread with no outputs and no write-up is open, not vacuously done",
          threads.stage(bare, set(), {}, [], [])["status"] == "open")

    # --- the same facts, read off a real workspace --------------------------
    repo = os.path.join(home, "repo")
    ws = os.path.join(repo, "research", "Paper")
    os.makedirs(ws)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@example.org")
    git(repo, "config", "user.name", "t")
    write(os.path.join(ws, "AI_INSTRUCTIONS.md"), "# rules\n")
    # The shape PSYCH-ASR and libr-local-llm have: `live/` ignored, and every
    # JSON file ignored with the thread file let back in.
    write(os.path.join(ws, ".gitignore"), "live/\nresults/\n*.json\n!threads.json\n")
    write(os.path.join(ws, "scripts", "knn.py"), "x = 1\n")
    write(os.path.join(ws, "paper", "manuscript.md"), "# Paper\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "seed")

    code, said = run(ws, ["thread"], json.dumps(GOOD))
    check("`board thread < file` writes it", code == 0
          and os.path.isfile(threads.path(ws)))
    check("and git can see it in a workspace that ignores live/ wholesale",
          subprocess.run(["git", "check-ignore", "-q", "threads.json"],
                         cwd=ws).returncode == 1)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "threads")

    fresh()
    check("a clean workspace with nothing produced is open and saved",
          threads.stages(ws)["knn"] == {"status": "open", "unsaved": False,
                                        "decisions": 1, "tasks": 1})
    write(os.path.join(ws, "results", "knn.csv"), "a,b\n")
    fresh()
    check("an output on disk, even an ignored one, makes it a result",
          threads.stages(ws)["knn"]["status"] == "result")
    write(os.path.join(ws, "paper", "manuscript.md"),
          "# Paper\n\n## Nearest-neighbour retrieval\n")
    fresh()
    s = threads.stages(ws)["knn"]
    check("the anchor written makes it written, and the edit makes it unsaved",
          s["status"] == "written" and s["unsaved"] is True)
    write(os.path.join(ws, "live", "jobs.jsonl"), json.dumps(job) + "\n")
    fresh()
    check("a job in the registry makes it running",
          threads.stages(ws)["knn"]["status"] == "running")
    with open(os.path.join(ws, "live", "jobs.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"jobid": "42", "state": "COMPLETED"}) + "\n")
    fresh()
    check("and the line that says it finished takes it back",
          threads.stages(ws)["knn"]["status"] == "written")

    # --- the command: every edit goes through validation --------------------
    code, said = run(ws, ["thread", "task", "knn", "Report the scatter"])
    clean = threads.read(ws)[0]
    check("`task` adds an open task",
          code == 0 and threads.thread(clean, "knn")["tasks"][-1]
          == {"text": "Report the scatter", "done": False})
    code, said = run(ws, ["thread", "done", "knn", "1"])
    check("`done` ticks a task by its number",
          code == 0 and threads.thread(threads.read(ws)[0], "knn")["tasks"][0]["done"])
    code, said = run(ws, ["thread", "done", "knn", "Report the scatter"])
    check("and by its text",
          code == 0 and threads.thread(threads.read(ws)[0], "knn")["tasks"][2]["done"])
    code, said = run(ws, ["thread", "decide", "knn", "1",
                          "Fewest dimensions holding 90% of the mass"])
    check("`decide` writes a decision's rule",
          code == 0 and threads.thread(threads.read(ws)[0], "knn")["decisions"][0]
          ["rule"] == "Fewest dimensions holding 90% of the mass")
    code, said = run(ws, ["thread", "decide", "knn", "Which venue"])
    check("and a new question with no rule is an open decision",
          code == 0 and threads.thread(threads.read(ws)[0], "knn")["decisions"][1]
          == {"q": "Which venue", "rule": None})
    write(os.path.join(ws, "live", "state.json"), json.dumps({"thread": "tripod"}))
    code, said = run(ws, ["thread", "close"])
    check("`close` with no thread named closes the sitting's thread",
          code == 0 and threads.thread(threads.read(ws)[0], "tripod")["closed"])
    code, said = run(ws, ["thread", "reopen", "tripod"])
    check("and `reopen` undoes it",
          code == 0 and not threads.thread(threads.read(ws)[0], "tripod")["closed"])
    code, said = run(ws, ["thread", "add"], json.dumps(
        {"id": "cover", "deliverable": "paper1", "title": "Cover letter"}))
    check("`add` adds a thread", code == 0
          and threads.thread(threads.read(ws)[0], "cover"))
    # --- a commit's thread prefix names a real thread ----------------------
    spine = threads.read(ws)[0]
    check("a push naming a real thread passes, workspace id or not",
          threads.commit_prefix(spine, "knn: draw the figure") == ("knn", None)
          and threads.commit_prefix(spine, "research/Paper: knn: x",
                                    "research/Paper") == ("knn", None))
    check("and one with no prefix is a save with no thread named",
          threads.commit_prefix(spine, "lesson complete") == ("", None))
    tid, wrong = threads.commit_prefix(spine, "kNN: draw it")
    check("a prefix that is no thread is refused, naming the real ones",
          tid == "" and wrong and "kNN" in wrong and "knn" in wrong
          and "cover" in wrong)
    check("and with no thread file there is nothing to check against",
          threads.commit_prefix(None, "anything: x") == ("", None))
    heads = subprocess.run(["git", "rev-list", "--all", "--count"], cwd=repo,
                           stdout=subprocess.PIPE).stdout
    code, said = run(ws, ["push", "knnn: typo in the thread"])
    check("`board push` refuses that subject and commits nothing",
          code == 1 and "`knnn` is not a thread" in said
          and subprocess.run(["git", "rev-list", "--all", "--count"], cwd=repo,
                             stdout=subprocess.PIPE).stdout == heads)

    before = open(threads.path(ws), encoding="utf-8").read()
    code, said = run(ws, ["thread", "add"], json.dumps(
        {"id": "late", "deliverable": "ghost", "files": ["../x.py"]}))
    check("a refused edit says every problem and writes nothing",
          code == 1 and said.count("\n  ") >= 2
          and open(threads.path(ws), encoding="utf-8").read() == before)
    code, said = run(ws, ["thread", "done", "knn", "no such task"])
    check("a task that is not there is refused, with the list",
          code == 1 and "Draw the figure" in said)
    code, said = run(ws, ["thread", "--show", "knn"])
    check("`--show <thread>` prints the thread and its derived stage",
          code == 0 and '"stage"' in said and '"status"' in said)

    os.remove(os.path.join(ws, "scripts", "knn.py"))
    fresh()
    code, said = run(ws, ["thread", "--check"])
    check("`--check` says aloud a file the tree no longer has",
          code == 0 and "scripts/knn.py" in said)
    fresh()
    resolved = threads.resolve(ws, threads.read(ws)[0])
    check("and the read drops it, leaving the thread in place",
          threads.thread({"threads": resolved}, "knn")["files"] == [])

    code, said = run(ws, ["thread", "task", "knn", "One more"])
    check("an edit to a tracked thread file lands", code == 0)

    # --- which documents a thread file claims -------------------------------
    docs = os.path.join(home, "docs")
    for rel in ("paper/manuscript.md", "paper/manuscript.pdf",
                "paper/parts/manuscript/01-intro.pdf",
                "homework/sweep/sweep.pdf", "paper/review/round.pdf",
                "stray/orphan.pdf"):
        write(os.path.join(docs, rel), "%PDF-1.4\n" + "%" * reading.MIN_BYTES)
    claimed = {"version": 1,
               "deliverables": [{"id": "p", "title": "P",
                                 "doc": "paper/manuscript.md"}],
               "threads": [{"id": "a", "deliverable": "p", "title": "A",
                            "files": ["homework/sweep"],
                            "writes": [{"file": "paper/review/round.md",
                                        "anchor": "# Round"}]}]}
    write(threads.path(docs), json.dumps(claimed))
    write(os.path.join(docs, "paper", "review", "round.md"), "# Round\n")
    reading._cache.clear()
    said = "\n".join(threads.check(docs))
    check("the claim fixture offers five documents",
          len(reading.documents(docs)) == 5)
    check("a deliverable's source claims the document built from it",
          "paper/manuscript.pdf" not in said)
    check("and a piece under parts/ belongs wherever its whole does",
          "01-intro" not in said)
    check("a directory in `files` claims the documents under it",
          "sweep.pdf" not in said)
    check("a write-up file claims its built document",
          "round.pdf" not in said)
    check("and a document nothing claims is still said aloud",
          "stray/orphan.pdf" in said)

    # A RULE THAT HIDES THE FILE is refused with the edit that fixes it.
    hidden = os.path.join(repo, "projects", "Hidden")
    write(os.path.join(hidden, "AI_INSTRUCTIONS.md"), "# rules\n")
    write(os.path.join(hidden, ".gitignore"), "live/\n*.json\n")
    code, said = run(hidden, ["thread"], json.dumps(GOOD))
    check("a thread file git cannot see is refused aloud, naming the fix",
          code == 1 and "!threads.json" in said)

    # --- one plan: the thread file's open tasks are the steps ---------------
    write(os.path.join(ws, "TODO.md"), "# plan\n\n- [ ] the old plan's step\n")
    fresh()
    steps = plan.steps(ws)
    check("a thread file with open tasks is the plan, alone",
          steps and all(s.get("thread") for s in steps)
          and not any("old plan" in s["label"] for s in steps)
          and plan.paths(ws) == [threads.path(ws)])
    fresh()
    m = mapping.status(ws)
    on = dict((n["id"], n) for n in m["nodes"])
    check("a thread's own open task lands on its own box, and a ticked one does not",
          [s["label"] for s in on["knn"]["steps"]] == ["One more"])

    no_open = json.loads(json.dumps(GOOD))
    for t in no_open["threads"]:
        t["tasks"] = [dict(x, done=True) for x in t.get("tasks", [])]
    run(ws, ["thread"], json.dumps(no_open))
    fresh()
    check("a thread file with no open task is still the plan, and the old TODO "
          "is not", plan.paths(ws) == [threads.path(ws)] and plan.steps(ws) == [])
    run(ws, ["thread"], json.dumps(GOOD))

    write(os.path.join(ws, "scripts", "knn.py"), "x = 1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "everything")
    fresh()
    saved = threads.stages(ws)["knn"]["unsaved"]
    os.remove(os.path.join(ws, "scripts", "knn.py"))
    fresh()
    check("deleting a thread's tracked file makes it unsaved",
          saved is False and threads.stages(ws)["knn"]["unsaved"] is True)
    fresh()

    # --- the three workspaces carry drafted thread files ---------------------
    psych = os.path.join(REPO, "research", "PSYCH-ASR")
    llm = os.path.join(REPO, "projects", "libr-local-llm")
    trd = os.path.join(REPO, "research", "TRD-EHR")
    for where, dels, ids in (
            (trd, ["paper1", "paper2"],
             ["knn-across-embedders", "reviewer-findings", "consistency-pass"]),
            (psych, ["stage1"],
             ["transcription", "word-alignment", "diarization", "speaker-join",
              "reference-transcript", "arm-measurement", "grid-sweep",
              "arm-selection", "recording-review"]),
            (llm, ["local-inference", "colibri-deck"],
             ["phi-path", "libr-hardware", "phi-deck"])):
        name = os.path.basename(where)
        fresh()
        clean, problems = threads.read(where)
        check("%s's thread file is valid" % name, clean and not problems)
        got = [t["id"] for t in (clean or {}).get("threads", [])]
        check("and it carries its deliverables and threads",
              clean and [d["id"] for d in clean["deliverables"]] == dels
              and all(i in got for i in ids))
        check("and `--check` finds nothing it claims that the tree does not",
              threads.check(where) == [])
        check("and its live/map.json is gone",
              not os.path.exists(os.path.join(where, "live", "map.json")))
        check("and git can see its thread file",
              subprocess.run(["git", "check-ignore", "-q", "threads.json"],
                             cwd=where).returncode == 1)
    clean = threads.read(trd)[0]
    knn = threads.thread(clean, "knn-across-embedders")
    check("the KNN thread's dimension count is decided",
          [d["rule"] for d in knn["decisions"]
           if d["q"] == "How to count dimensions an L2 fit uses"][0])
    check("and every Paper 1 thread has an open task, so the board's next means something",
          all(any(not x["done"] for x in t["tasks"])
              for t in clean["threads"] if t["deliverable"] == "paper1"))
    check("TRD-EHR's TODO file is folded into its threads and gone",
          not os.path.exists(os.path.join(trd, "planning", "TRD-EHR_TODO.txt")))
    check("a recording-review thread's one task is the owner's own listening",
          [x["text"] for x in threads.thread(threads.read(psych)[0],
                                              "recording-review")["tasks"]]
          and "listen" in threads.thread(threads.read(psych)[0],
                                         "recording-review")["tasks"][0]["text"])
    check("the deck waits on the two learn threads",
          threads.thread(threads.read(llm)[0], "phi-deck")["blockedBy"]
          == ["phi-path", "libr-hardware"])
    check("a box's directory folds into its files",
          "slurm_jobs/p0" in threads.thread(threads.read(llm)[0], "p0")["files"])
    check("and nothing is closed by the draft",
          not any(t["closed"] for w in (trd, psych, llm)
                  for t in threads.read(w)[0]["threads"]))

finally:
    shutil.rmtree(home, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a project's spine is its deliverables and threads, and their status is a fact")
