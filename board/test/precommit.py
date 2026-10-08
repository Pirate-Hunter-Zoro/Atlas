#!/usr/bin/env python3
"""The commit-time gate, `.githooks/pre-commit`, in a scratch repository.

    python3 test/precommit.py

A temporary repository carries this tree's `.githooks/`, `.gitignore` and
`board/tutorboard/`, with `core.hooksPath` at its own `.githooks` by absolute
path, exactly as bootstrap.sh sets it. Every commit below goes through the real
hook. Nothing here touches the real repository.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
ROOT = os.path.dirname(BOARD)
POLICY = os.path.join("ai-config", "policy", "phi.py")

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + detail) if detail else ""))


def put(rel, text, mode="w"):
    path = os.path.join(box, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode) as fh:
        fh.write(text)


def env(turn=False):
    e = dict(os.environ)
    e.pop("TUTORBOARD_TURN", None)
    if turn:
        e["TUTORBOARD_TURN"] = "1"
    return e


def git(*args, **kw):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t"]
                          + list(args), cwd=kw.get("cwd", box),
                          env=kw.get("env") or env(), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)


def commit(paths, msg="x", turn=False, force=False):
    """Stage `paths` and commit. `(committed, stderr)`; a refusal is unstaged."""
    git("add", *(["-f"] if force else []), "--", *paths)
    p = git("commit", "-q", "-m", msg, env=env(turn))
    if p.returncode != 0:
        git("reset", "-q")
    return p.returncode == 0, p.stderr


# Git runs a hook only if its index entry is executable, and core.fileMode
# false on a checkout means `chmod +x` alone never reaches the index.
_modes = subprocess.run(["git", "ls-files", "-s", "--", ".githooks"], cwd=ROOT,
                        stdout=subprocess.PIPE, universal_newlines=True).stdout
_hooks = [l.split()[0] + " " + l.split("\t")[-1] for l in _modes.splitlines()]
check("every tracked hook is executable in the index",
      _hooks and all(h.startswith("100755 ") for h in _hooks), ", ".join(_hooks))

box = tempfile.mkdtemp(prefix="tutor-precommit-")
other = tempfile.mkdtemp(prefix="tutor-precommit-other-")
try:
    shutil.copytree(os.path.join(ROOT, ".githooks"), os.path.join(box, ".githooks"))
    shutil.copyfile(os.path.join(ROOT, ".gitignore"), os.path.join(box, ".gitignore"))
    shutil.copytree(os.path.join(BOARD, "tutorboard"),
                    os.path.join(box, "board", "tutorboard"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    put("projects/S/tutorboard.json", json.dumps({"name": "S", "phi": True}))
    put("projects/O/tutorboard.json",
        json.dumps({"name": "O", "phi": False, "relay": {"exports": ["a"]}}))
    put("projects/O/RULES.md", "the owner's rules\n")
    git("init", "-q")
    git("config", "core.hooksPath", os.path.join(box, ".githooks"))
    done, err = commit(["."])
    check("a clean commit passes the gate", done, err)

    # ---- the audit ---------------------------------------------------------
    put("big.bin", "\0" * (30 * 1024 * 1024))
    done, err = commit(["big.bin"])
    check("a 30 MB file is refused", not done and "big.bin is 30 MB" in err, err)
    os.remove(os.path.join(box, "big.bin"))

    put("x_session1.wav", "")
    done, err = commit(["x_session1.wav"])
    check("x_session1.wav is refused", not done and "x_session1.wav" in err, err)
    os.remove(os.path.join(box, "x_session1.wav"))

    put("sessions/20261008-120000/session.json", "{}")
    done, err = commit(["sessions"], force=True)
    check("a path under sessions/ is refused, even forced past the ignore rule",
          not done and "sessions/20261008-120000/session.json" in err, err)
    shutil.rmtree(os.path.join(box, "sessions"))

    # ---- the participant-code scan ----------------------------------------
    code = "BL" + "123"
    put("projects/S/notes.md", "first\nmet %s today\n" % code)
    done, err = commit(["projects/S/notes.md"])
    check("BL and three digits in a \"phi\": true subject is refused, by file "
          "and line, without printing the code",
          not done and "projects/S/notes.md:2" in err and code not in err, err)
    put("projects/S/notes.md", "write it as BL###\n")
    done, err = commit(["projects/S/notes.md"])
    check("and BL### is how the rule is written about", done, err)
    put("projects/O/notes.md", "%s in a subject with no phi\n" % code)
    done, err = commit(["projects/O/notes.md"])
    check("a subject that is not \"phi\": true is not scanned", done, err)
    put("projects/S/%s_notes.md" % code, "x\n")
    done, err = commit(["projects/S"])
    check("a participant code in a filename is refused, masked",
          not done and "BL###_notes.md" in err and code not in err, err)
    os.remove(os.path.join(box, "projects/S/%s_notes.md" % code))

    # ---- what a tutor turn may not commit ---------------------------------
    put("projects/O/RULES.md", "the owner's rules, edited\n")
    done, err = commit(["projects/O/RULES.md"], turn=True)
    check("a turn's RULES.md change is refused", not done and "RULES.md" in err, err)
    put("projects/O/tutorboard.json",
        json.dumps({"name": "O", "phi": True, "relay": {"exports": ["a"]}}))
    done, err = commit(["projects/O/tutorboard.json"], turn=True)
    check("a turn's `phi` change is refused", not done and "`phi`" in err, err)
    put("projects/O/tutorboard.json",
        json.dumps({"name": "O", "phi": False, "relay": {"exports": ["b"]}}))
    done, err = commit(["projects/O/tutorboard.json"], turn=True)
    check("a turn's `relay.exports` change is refused",
          not done and "relay.exports" in err, err)
    put("projects/O/tutorboard.json",
        json.dumps({"name": "O renamed", "phi": False, "relay": {"exports": ["a"]}}))
    done, err = commit(["projects/O/tutorboard.json"], turn=True)
    check("a turn may change the rest of tutorboard.json", done, err)
    put("projects/N/tutorboard.json", json.dumps({"name": "N", "phi": False}))
    done, err = commit(["projects/N/tutorboard.json"], turn=True)
    check("and may create a new subject's", done, err)
    done, err = commit(["projects/O/RULES.md"])
    check("the owner, outside a turn, commits RULES.md", done, err)

    # ---- under a second for ten files -------------------------------------
    for i in range(10):
        put("projects/O/src/f%d.py" % i, "x = %d\n" % i)
    git("add", "projects/O/src")
    hook = os.path.join(box, ".githooks", "pre-commit")
    start = time.time()
    p = subprocess.run([hook], cwd=box, env=env(), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True)
    spent = time.time() - start
    check("a ten-file commit spends under 1 s in the hook (%.2f s)" % spent,
          p.returncode == 0 and spent < 1.0, p.stderr)
    git("commit", "-q", "--no-verify", "-m", "ten")

    # ---- commit-msg still strips attribution ------------------------------
    put("projects/O/a.md", "a\n")
    done, err = commit(["projects/O/a.md"],
                       msg="a change\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n")
    said = git("log", "-1", "--format=%B").stdout
    check("commit-msg still strips attribution",
          done and "a change" in said and "Co-Authored-By" not in said, said)

    # ---- a fence with no policy refuses everything ------------------------
    os.makedirs(os.path.join(box, "projects", "F", "phi"))
    put("projects/F/tutorboard.json", json.dumps({"name": "F", "phi": True}))
    done, err = commit(["projects/F/tutorboard.json"])
    check("a fence with no PHI policy refuses the commit, naming the policy",
          not done and POLICY in err, err)
    src = os.path.join(ROOT, POLICY)
    if os.path.isfile(src):
        os.makedirs(os.path.join(box, os.path.dirname(POLICY)))
        shutil.copyfile(src, os.path.join(box, POLICY))
        done, err = commit(["projects/F/tutorboard.json"])
        check("and with the policy in place the same commit passes", done, err)
    else:
        print("skip ai-config is not here; the policy-present case did not run")

    # ---- another repository pointed at this hook --------------------------
    git("init", "-q", cwd=other)
    git("config", "core.hooksPath", os.path.join(box, ".githooks"), cwd=other)
    with open(os.path.join(other, "x_session1.wav"), "w") as fh:
        fh.write("")
    with open(os.path.join(other, "RULES.md"), "w") as fh:
        fh.write("r\n")
    git("add", ".", cwd=other)
    p = git("commit", "-q", "-m", "x", cwd=other, env=env(True))
    check("another repository gets only the turn refusals: RULES.md in a turn",
          p.returncode != 0 and "RULES.md" in p.stderr
          and "x_session1.wav" not in p.stderr, p.stderr)
    p = git("commit", "-q", "-m", "x", cwd=other)
    check("and outside a turn it commits; the Atlas audit is not its rule",
          p.returncode == 0, p.stderr)
finally:
    shutil.rmtree(box, ignore_errors=True)
    shutil.rmtree(other, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("the commit-time gate refuses what a public repository may not carry")
