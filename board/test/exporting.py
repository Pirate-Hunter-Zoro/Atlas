#!/usr/bin/env python3
"""Export approval is the subject's committed tutorboard.json, and TRD-EHR's
thread marks moved there without approving one path more or less.

What the checks are about:

  * THE RULE. A png, pdf or svg is approved by a matching `relay.exports`
    glob; a csv or json only by a matching entry with `"aggregate": true`,
    and the refusal names tutorboard.json. Nothing outside `results/`, and
    nothing of another extension, whatever the list says.
  * COMMITTED, AND STILL ON DISK. `approvals` keeps the entries both HEAD and
    the working tree hold: an uncommitted approval approves nothing, and an
    uncommitted revocation takes effect at once.
  * THE MIGRATION IS EXACT. Over every path the old marks, the tracked
    `exports/` and every request and report name, the new list approves
    exactly what the thread file did. The committed tutorboard.json is what
    `scripts/migrate-exports.py` writes.
  * OLD REPORTS STILL FOLD. TRD-EHR's requests and reports, written with
    `thread`, read through `jobs.view` as before.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
from tutorboard import exports, jobs                                   # noqa: E402

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


def git(cwd, *args):
    p = subprocess.run(["git"] + list(args), cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL, check=False)
    return p.stdout.decode("utf-8", "replace")


spec = importlib.util.spec_from_file_location(
    "migrate_exports", os.path.join(ROOT, "scripts", "migrate-exports.py"))
migrate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migrate)

# --- the rule -------------------------------------------------------------------
ALLOWED = [{"glob": "results/figs/*.png"}, {"glob": "results/rows.csv"},
           {"glob": "results/agg/*", "aggregate": True}]
check("a png matching a glob exports",
      exports.approved(ALLOWED, "results/figs/roc.png") == (True, ""))
check("and `*` crosses directories, as fnmatch does",
      exports.approved(ALLOWED, "results/figs/a/b.png")[0])
ok, why = exports.approved(ALLOWED, "results/rows.csv")
check("a csv without `aggregate` is refused, with a reason naming "
      "tutorboard.json", not ok and "tutorboard.json" in why
      and "aggregate" in why)
check("a csv or json whose entry says aggregate exports",
      exports.approved(ALLOWED, "results/agg/summary.csv")[0]
      and exports.approved(ALLOWED, "results/agg/summary.json")[0])
ok, why = exports.approved(ALLOWED, "results/other.png")
check("a path no glob matches is refused, naming tutorboard.json",
      not ok and "tutorboard.json" in why)
check("outside results/, or of another extension, nothing approves it",
      not exports.approved([{"glob": "results/*"}], "scripts/a.png")[0]
      and not exports.approved([{"glob": "results/*", "aggregate": True}],
                               "results/model.joblib")[0]
      and not exports.approved([{"glob": "results/*"}], "results/../a.png")[0])
got, problems = exports.entries([
    {"glob": "results/a.png"}, {"glob": "scripts/*.png"},
    {"glob": "results/b.csv", "aggregate": "yes"}, "results/c.png",
    {"glob": "results/d.png", "path": "x"}, {"glob": "results/a.png"}])
check("entries: a good one kept once; outside results/, a non-boolean "
      "aggregate, a bare string and an unknown key each named",
      got == [{"glob": "results/a.png"}] and len(problems) == 4)

# --- approvals: committed, and still on disk ---------------------------------------
box = tempfile.mkdtemp(prefix="tutor-exporting-")
try:
    subj = os.path.join(box, "projects", "S")
    git(box, "init", "-q", "-b", "main")
    git(box, "config", "user.email", "t@example.com")
    git(box, "config", "user.name", "t")
    cfg = os.path.join(subj, "tutorboard.json")
    write(cfg, json.dumps({"name": "S", "relay": {"exports": [
        {"glob": "results/a.png"}, {"glob": "results/b.png"}]}}))
    check("an uncommitted tutorboard.json approves nothing",
          exports.approvals(subj) == [])
    git(box, "add", "-A")
    git(box, "commit", "-q", "-m", "S")
    check("committed, it approves its entries",
          exports.approvals(subj) == [{"glob": "results/a.png"},
                                      {"glob": "results/b.png"}])
    write(cfg, json.dumps({"name": "S", "relay": {"exports": [
        {"glob": "results/a.png"}, {"glob": "results/*.png"}]}}))
    check("an entry removed on disk is revoked at once; one added on disk "
          "waits for its commit", exports.approvals(subj)
          == [{"glob": "results/a.png"}])
finally:
    shutil.rmtree(box, ignore_errors=True)

# --- the migration: TRD-EHR ----------------------------------------------------------
TRD = next((os.path.join(REPO, p, "TRD-EHR") for p in ("projects", "research")
            if os.path.isdir(os.path.join(REPO, p, "TRD-EHR"))), None)
check("TRD-EHR is in this checkout", TRD is not None)
# The thread file as it stood when the marks moved, so the proof outlives it.
PINNED = "d3284678"
try:
    with open(os.path.join(TRD, "threads.json"), encoding="utf-8") as fh:
        old_doc = json.load(fh)
except OSError:
    old_doc = json.loads(git(REPO, "show",
                             "%s:research/TRD-EHR/threads.json" % PINNED))
with open(os.path.join(TRD, "tutorboard.json"), encoding="utf-8") as fh:
    new_list, problems = exports.entries(
        ((json.load(fh).get("relay") or {}).get("exports")))
marks = migrate.old_marks(old_doc)
check("TRD-EHR's tutorboard.json relay.exports is valid, and is exactly what "
      "migrate-exports.py writes", problems == [] and new_list
      and new_list == migrate.entries_for(marks))

# Every path anything names: the threads' marks, answered or not, the tracked
# exports/, and every results/ path in a request or a report.
universe = set()
for t in old_doc.get("threads") or []:
    for e in t.get("exports") or []:
        p = exports.rel(e.get("path") if isinstance(e, dict) else e)
        if p:
            universe.add(p)
rel_trd = os.path.relpath(TRD, REPO)
tracked_exports = [p[len(rel_trd) + 1 + len("exports/"):] for p in git(
    REPO, "ls-files", "--", rel_trd + "/exports").splitlines()]
universe.update(tracked_exports)
named = set()


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            for s in strings(v):
                yield s
    elif isinstance(value, list):
        for v in value:
            for s in strings(v):
                yield s


for sub in ("relay/reports", "relay/requests"):
    for rel in git(REPO, "ls-files", "--", "%s/%s" % (rel_trd, sub)).split():
        with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
            for s in strings(json.load(fh)):
                for word in s.split():
                    word = word.strip(",;:()'\"")
                    if word.startswith("results/"):
                        named.add(exports.rel(word))
named.discard(None)
universe.update(named)
check("the universe holds the marks, %d tracked exports and %d paths the "
      "reports and requests name" % (len(tracked_exports), len(named)),
      set(marks) <= universe and len(tracked_exports) > 0 and len(named) > 0)
differ = sorted(p for p in universe
                if migrate.old_approves(old_doc, p)
                != exports.approved(new_list, p)[0])
check("over all %d of them, the new list approves exactly what the old "
      "marks did" % len(universe), differ == [])
check("every old exportable path is approved by the new list, and the new "
      "list approves nothing the marks did not",
      set(p for p in universe if exports.approved(new_list, p)[0])
      == set(marks))
widened = sorted(p for p in set(tracked_exports) | named
                 if exports.approved(new_list, p)[0]
                 and not migrate.old_approves(old_doc, p))
check("no tracked file under exports/ or relay/reports/ names a path the new "
      "list approves that the old marks did not", widened == [])
check("the one path listed but never marked aggregate stays refused",
      not exports.approved(
          new_list, "results/cross_embedder_retrieval/"
                    "cross_embedder_retrieval.csv")[0])
check("a glob character in a marked path is escaped: it matches only itself",
      migrate.entries_for(["results/a[1]*.png"])
      == [{"glob": "results/a[[]1][*].png"}]
      and exports.approved(migrate.entries_for(["results/a[1]*.png"]),
                           "results/a[1]*.png")[0]
      and not exports.approved(migrate.entries_for(["results/a[1]*.png"]),
                               "results/a1x.png")[0])

# --- old reports still fold ------------------------------------------------------------
copy = tempfile.mkdtemp(prefix="tutor-trd-fold-")
try:
    shutil.copytree(os.path.join(TRD, "relay", "requests"),
                    os.path.join(copy, "relay", "requests"))
    shutil.copytree(os.path.join(TRD, "relay", "reports"),
                    os.path.join(copy, "relay", "reports"))
    reqs = jobs.requests(copy)
    view = jobs.view(copy)
    relayed = [r for r in view.values() if r.get("request")]
    reps = jobs.reports(copy)
    check("every TRD-EHR request folds into jobs.view, once each",
          len(relayed) == len(reqs) > 0)
    check("each with its report's state, its old thread kept for the "
          "lines that name it",
          all(r["state"] != exports.REQUESTED for r in relayed
              if r["request"] in reps)
          and all(jobs.title_of(r) == (r.get("thread") or r["request"])
                  for r in relayed))
    one = view.get("relay:2026-10-02-knn-across-embedders-neighbor-count-sweep")
    check("2110916 reads FAILED, its Slurm id and thread intact",
          one and one["state"] == "FAILED" and one["slurm"] == "2110916"
          and one["thread"] == "knn-across-embedders")
finally:
    shutil.rmtree(copy, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("an export is approved by the committed tutorboard.json, exactly as "
      "TRD-EHR's thread marks approved it")
