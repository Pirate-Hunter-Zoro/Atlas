"""Synthetic relay history. No real project, data, or historical job is read."""
import json
import os


def write_history(root):
    def put(rel, body):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
    put("tutorboard.json", json.dumps({"name": "Relay Lab", "phi": False,
        "check": "python3 -m unittest"}))
    put("slurm_jobs/sweep.sbatch", "#!/bin/bash\n#RELAY-VAR SIZE [0-9]+\ntrue\n")
    put("slurm_jobs/diagnose.sbatch", "#!/bin/bash\n#RELAY-DIAGNOSTIC\n"
        "#RELAY-VAR LOOK [A-Z_]+/[a-z_]+\ntrue\n")
    for ident, state, job in (("fixture-failed", "failed", "7001"),
                              ("fixture-done", "completed", "7002")):
        request = {"id": ident, "kind": "recipe", "thread": "legacy-sweep",
                   "recipe": "slurm_jobs/sweep.sbatch", "env": {"SIZE": "8"},
                   "produces": ["results/sweep"], "export": [], "filed": 1.0}
        report = {"id": ident, "kind": "recipe", "thread": "legacy-sweep",
                  "jobid": job, "state": state, "exit": "1:0" if state == "failed" else "0:0",
                  "produced": ["results/sweep"], "missing": [], "exported": [],
                  "relay": [], "submitted": 2.0, "updated": 3.0}
        put("relay/requests/" + ident + ".json", json.dumps(request))
        put("relay/reports/" + ident + ".json", json.dumps(report))
