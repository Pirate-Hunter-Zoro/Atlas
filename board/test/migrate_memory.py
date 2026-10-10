#!/usr/bin/env python3
"""board/scripts/migrate-memory.py, and PSYCH-ASR's fence in the brief.

  * --draft turns a contract and threads.json into RULES.md and TUTOR.md:
    each open task a `- [ ]` line, each open decision a bullet, no done task.
  * The check passes a good pair and names what fails: a lost open task, a
    lost open decision, TUTOR.md over its cap or missing a section, RULES.md
    over its cap, a fenced contract whose RULES.md lacks phi/, and a retired
    command named in either file.
  * PSYCH-ASR's committed RULES.md reaches a bound session's brief with its
    data-fence rule.

Stdlib only.
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
SCRIPT = os.path.join(ROOT, "scripts", "migrate-memory.py")
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


def run(*args):
    p = subprocess.run([sys.executable, SCRIPT] + list(args),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=60)
    return p.returncode, p.stdout


base = os.path.realpath(tempfile.mkdtemp(prefix="tutor-migmem-"))
os.environ["TUTORBOARD_COURSES"] = base
os.environ["TUTORBOARD_TRASH"] = os.path.realpath(
    tempfile.mkdtemp(prefix="tutor-migmem-trash-"))
os.environ.pop("TUTORBOARD_SESSION", None)
os.environ.pop("TUTORBOARD_TURN", None)

from tutorboard import brief, sense, sessions                        # noqa: E402

CONTRACT = """# AI_INSTRUCTIONS.md

## The data fence -- before anything else

Concretely, refuse to open any of these:

- anything under `phi/`, the whole directory
- `.wav` recordings

### What is left open

## 11. The live board

### The rules that do not bend

- **You never make the user transcribe what they already wrote.** Open it.
- **Code is checked before it is pushed.** Always.

---

## 12. Sentences
"""

THREADS = {"threads": [
    {"id": "a", "tasks": [{"text": "Build the reference RTTM", "done": False},
                          {"text": "A finished thing", "done": True}],
     "decisions": [{"q": "Which arm", "rule": None},
                   {"q": "Which format", "rule": "RTTM"}]},
    {"id": "b", "tasks": [{"text": "Listen to the recording", "done": False}]},
]}

try:
    subj = "projects/Probe"
    proj = os.path.join(base, subj)
    write(os.path.join(proj, "AI_INSTRUCTIONS.md"), CONTRACT)
    write(os.path.join(proj, "threads.json"), json.dumps(THREADS))
    write(os.path.join(proj, "DIRECTION.md"),
          "<!-- set: 2026-09-21 -->\nRun the grid, do not judge it.\n")

    code, out = run("--atlas", base, "--all", "--draft")
    tutor = read(os.path.join(proj, "TUTOR.md"))
    rules = read(os.path.join(proj, "RULES.md"))
    check("--all --draft writes both files", code == 0 and "TUTOR.md" in out
          and "RULES.md" in out, out)
    check("each open task is a `- [ ]` line and no done task is",
          "- [ ] Build the reference RTTM" in tutor
          and "- [ ] Listen to the recording" in tutor
          and "A finished thing" not in tutor, tutor)
    check("the open decision is a bullet; a settled one is not",
          "- Which arm" in tutor and "Which format" not in tutor, tutor)
    check("the owner's direction lands under Now",
          "Run the grid, do not judge it." in tutor, tutor)
    check("RULES.md carries the rule leads and the fence's list",
          "You never make the user transcribe" in rules and "phi/" in rules,
          rules)

    code, out = run("--atlas", base, subj)
    check("the draft passes the check", code == 0 and " ok " in out, out)

    write(os.path.join(proj, "TUTOR.md"),
          tutor.replace("- [ ] Listen to the recording\n", ""))
    code, out = run("--atlas", base, subj)
    check("a lost open task fails, named",
          code == 1 and "Listen to the recording" in out, out)

    write(os.path.join(proj, "TUTOR.md"), tutor.replace("- Which arm\n", ""))
    code, out = run("--atlas", base, subj)
    check("a lost open decision fails, named",
          code == 1 and "open decision missing" in out and "Which arm" in out,
          out)

    write(os.path.join(proj, "TUTOR.md"), tutor + ("word " * 800))
    code, out = run("--atlas", base, subj)
    check("TUTOR.md over 800 words fails", code == 1 and "over 800" in out, out)

    write(os.path.join(proj, "TUTOR.md"),
          tutor.replace("## Done recently", "## Later"))
    code, out = run("--atlas", base, subj)
    check("a missing section fails", code == 1 and "sections are" in out, out)
    write(os.path.join(proj, "TUTOR.md"), tutor)

    write(os.path.join(proj, "RULES.md"), "# Rules\n\n" + ("word " * 301))
    code, out = run("--atlas", base, subj)
    check("RULES.md over 300 words fails, and so does a fence it lost",
          code == 1 and "over 300" in out and "data fence" in out, out)

    write(os.path.join(proj, "RULES.md"),
          rules + "- Keep it true with `board thread done`.\n")
    code, out = run("--atlas", base, subj)
    check("a retired command fails", code == 1 and "board thread" in out, out)
    write(os.path.join(proj, "RULES.md"), rules)

    # ---- PSYCH-ASR's fence reaches the brief ------------------------------
    real = os.path.join(ATLAS, "projects", "PSYCH-ASR", "RULES.md")
    psych = os.path.join(base, "projects", "PSYCH-ASR")
    write(os.path.join(psych, "tutorboard.json"),
          json.dumps({"name": "PSYCH-ASR", "phi": True}))
    shutil.copy(real, os.path.join(psych, "RULES.md"))
    write(os.path.join(base, ".gitignore"), "/sessions/\n")
    for argv in (["init", "-q"], ["add", "-A"],
                 ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
                  "-m", "fixture"]):
        subprocess.run(["git", "-C", base] + argv, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    sid = sessions.new(base=base)["id"]
    sessions.bind(sid, "projects/PSYCH-ASR", base=base)
    said = brief.briefing(sessions.repo(sid, base, create=True), sense)
    check("PSYCH-ASR's brief carries its data-fence rule from HEAD",
          "Never read anything under phi/" in said
          and "LOCAL-MODELS.md" in said, said[-1500:])
finally:
    shutil.rmtree(base, ignore_errors=True)

print("\n%d failure(s)" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
