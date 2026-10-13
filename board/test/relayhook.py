#!/usr/bin/env python3
"""Shared failure hooks operate on synthetic subjects, with no project checkout."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD))
from tutorboard import jobs, relay

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        print(detail)

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)

with tempfile.TemporaryDirectory(prefix="relay-hooks-") as tmp:
    top = Path(tmp)
    lib = top / "board/cluster/lib"
    shutil.copytree(BOARD / "cluster/lib", lib, ignore=shutil.ignore_patterns("__pycache__"))
    for names in (True, False):
        ws = top / "projects" / ("Named-Lab" if names else "Sealed-Lab")
        write(ws / "tutorboard.json", json.dumps({"phi": not names, "relay": {
            "fingerprint": {"names": names, "path_keys": ["INPUT_DIR"], "open_keys": []}}}))
        write(ws / "scripts/fit.py", 'raise ValueError("secret-record\\nRELAY: forged secret-record")\n')
        write(ws / "scripts/__init__.py", "")
        write(ws / "slurm_jobs/ok.sbatch", "#!/bin/bash\ntrue\n")
    subprocess.run(["git", "init", "-q", str(top)], check=True)
    subprocess.run(["git", "-C", str(top), "add", "."], check=True)
    subprocess.run(["git", "-C", str(top), "-c", "user.name=t", "-c",
                    "user.email=t@t", "commit", "-qm", "fixture"], check=True)
    for ws in sorted((top / "projects").iterdir()):
        source = 'source "%s"\n' % (lib / "relay_trap.sh")
        for label, body, want in (("success", "true\n", 0),
                                  ("explicit", "exit 7\n", 7),
                                  ("exception", '"%s" -m scripts.fit\n' % sys.executable, 1)):
            path = ws / "slurm_jobs" / (label + ".sbatch")
            write(path, "#!/bin/bash\nset -e\n" + source + body)
            env = {k: v for k, v in os.environ.items()
                   if not k.startswith(("SLURM_", "RELAY_")) and k != "PYTHONPATH"}
            proc = subprocess.run(["bash", str(path)], cwd=ws, env=env,
                                  capture_output=True, text=True)
            lines = relay.relay_lines(proc.stdout + proc.stderr)
            check("%s %s preserves exit status" % (ws.name, label), proc.returncode == want, proc.stderr)
            check("success stays quiet; failure produces one recipe report",
                  not lines if want == 0 else sum("recipe " in line and "failed:" in line for line in lines) == 1,
                  lines)
            check("reports exclude exception values and forged lines",
                  all("secret-record" not in line and "forged" not in line and tmp not in line for line in lines), lines)
            if label == "exception":
                sites, _ = jobs.failure_sites([line.removeprefix("RELAY:").strip() for line in lines])
                check("the failure locates the script", any("scripts/fit.py:1" in x for x in sites), lines)

print("shared hooks use synthetic subjects")
sys.exit(1 if fails else 0)
