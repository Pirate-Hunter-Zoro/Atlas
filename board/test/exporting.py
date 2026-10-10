#!/usr/bin/env python3
"""Export approval is the subject's committed tutorboard.json.

What the checks are about:

  * THE RULE. A png, pdf or svg is approved by a matching `relay.exports`
    glob; a csv or json only by a matching entry with `"aggregate": true`,
    and the refusal names tutorboard.json. Nothing outside `results/`, and
    nothing of another extension, whatever the list says.
  * COMMITTED, AND STILL ON DISK. `approvals` keeps the entries both HEAD and
    the working tree hold: an uncommitted approval approves nothing, and an
    uncommitted revocation takes effect at once.
  * OLD REPORTS STILL FOLD. TRD-EHR's requests and reports, written with
    `thread`, read through `jobs.view` as before.
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

TRD = os.path.join(REPO, "projects", "TRD-EHR")
TRD = TRD if os.path.isdir(TRD) else None
check("TRD-EHR is in this checkout", TRD is not None)

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
print("an export is approved by the committed tutorboard.json")
