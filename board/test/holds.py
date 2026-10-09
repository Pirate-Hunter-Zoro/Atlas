#!/usr/bin/env python3
"""A sitting held at the cluster: the owner writes there, the coach answers here.

What the checks are about:

  * A HOLD IS CHECKED WHOLE. Refused on something already held, one with no
    files, a closed workspace's hold with no check, an untracked check, and a
    file another hold has -- every problem at once.
  * A HOLD NEEDS NO THREAD. Paths named, or the sitting's own homework file,
    chapter or thread, in any workspace.
  * WHILE IT LASTS, THE MAC DOES NOT WRITE THE FILES. `board push` refuses a
    commit touching one, and says which.
  * THE CLUSTER'S PULL LEAVES THE OWNER'S EDITS ALONE. Rebase with autostash
    under uncommitted edits to a held file while the Mac pushes elsewhere; and
    nothing moves at all when the Mac has touched that file.
  * WHAT A REPORT CARRIES FAILS CLOSED. Output is open only where
    tutorboard.json says `"phi": false` on disk and at HEAD, with no fence and
    the policy loaded. A closed workspace's report carries only `RELAY:` lines.
    An open one's carries the check's output, paths made relative, cut to fit,
    a flagged line withheld.
  * ONE ROUND TRIP. `board send` on the cluster, a `[coach]` wake on the Mac,
    `board coach` back, and `board send` prints the reply.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
from tutorboard import atlas, fenced, holds, jobs                      # noqa: E402
from tutorboard.course import config, threads                          # noqa: E402

BOARD = os.path.join(ROOT, "bin", "board")
GO = "/usr/local/go/bin/go"
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


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def git(cwd, *args):
    p = subprocess.run(["git"] + list(args), cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL, check=False)
    return p.stdout.decode("utf-8", "replace")


SPINE = {
    "version": 1,
    "deliverables": [{"id": "paper2", "title": "Paper 2", "doc": ""}],
    "threads": [
        {"id": "aipw", "deliverable": "paper2", "title": "The AIPW rung",
         "files": ["src/aipw"], "check": "checks/aipw.sh"},
        {"id": "other", "deliverable": "paper2", "title": "Other",
         "files": ["src/aipw/shared.py", "src/other.py"]},
        {"id": "bare", "deliverable": "paper2", "title": "Bare"},
    ],
}

# --- the thread's check, and the validator ----------------------------------
clean, problems = threads.validate(SPINE)
check("a thread names its check, and one that names none has \"\"",
      not problems and threads.thread(clean, "aipw")["check"] == "checks/aipw.sh"
      and threads.thread(clean, "bare")["check"] == "")
bad = json.loads(json.dumps(SPINE))
bad["threads"][0]["check"] = "../outside.sh"
check("a check outside the workspace is refused",
      any("check" in p for p in threads.validate(bad)[1]))

tracked = {"checks/aipw.sh", "src/aipw/est.py"}
rec, problems = holds.validate_hold(clean, "aipw", {}, tracked)
check("a thread with files and a tracked check may be held",
      not problems and rec["id"] == "aipw" and rec["thread"] == "aipw"
      and rec["files"] == ["src/aipw"]
      and rec["check"] == {"script": "checks/aipw.sh"}
      and rec["label"] == "The AIPW rung")
_, problems = holds.validate_hold(clean, "aipw", {"aipw": {"held": 0}}, set())
check("held already AND an untracked check: both said at once",
      len(problems) == 2 and "already held" in problems[0]
      and "not tracked" in problems[1])
_, problems = holds.validate_hold(clean, "bare", {}, tracked)
check("no files and no check: both said",
      len(problems) == 2 and "no files" in problems[0] and "no check" in problems[1])
_, problems = holds.validate_hold(
    clean, "other", {"aipw": {"thread": "aipw", "files": ["src/aipw"]}}, tracked)
check("a file another hold covers is refused, by name",
      any("src/aipw/shared.py is already held, by thread aipw" in p
          for p in problems))
check("an unknown thread is refused",
      holds.validate_hold(clean, "nope", {}, tracked)[0] is None)

req = {"id": "check-aipw-1", "kind": "colibri", "thread": "aipw", "brief": "x"}
_, problems = jobs.validate(req, clean, tracked, {}, (), True)
check("a request is refused an id a step's check report would share",
      any("check-" in p for p in problems) and holds.is_check(req["id"]))

standing = {"aipw": {"thread": "aipw", "files": ["src/aipw"], "held": 0}}
said = holds.refused_writes(["src/aipw/est.py", "notes.md", "src/aipwx.py"],
                            clean, standing)
check("a write under a held directory is refused, and only that one",
      len(said) == 1 and said[0].startswith("src/aipw/est.py belongs to "
                                            "thread aipw"))
grown = json.loads(json.dumps(SPINE))
grown["threads"][0]["files"].append("src/new.py")
check("a file added to the thread mid-hold is held too",
      holds.refused_writes(["src/new.py"], threads.validate(grown)[0], standing))
check("a hold written before ids existed still reads by its thread",
      holds.check_of({"thread": "aipw", "check": "checks/aipw.sh"})
      == {"script": "checks/aipw.sh"}
      and holds.hold_id({"thread": "aipw"}) == "aipw")

# --- a hold with no thread ------------------------------------------------------
GO_CHECK, cp = config.clean_check({"all": ["go", "test", "./..."],
                                   "one": ["go", "test", "./{dir}/..."],
                                   "path": ["/usr/local/go/bin"]})
check("a workspace's check is read whole", not cp and GO_CHECK["path"]
      == ["/usr/local/go/bin"])
check("a check that runs something not named is refused",
      config.clean_check({"all": ["rm", "-rf", "."]})[0] is None
      and "neither" in config.clean_check({"all": ["/bin/rm"]})[1][0])
check("and so is a placeholder in `all`, which has no held path to fill it",
      config.clean_check({"all": ["go", "test", "./{dir}"]})[0] is None)
check("a check may be one shell command, which the brief prints as written",
      config.clean_check("uv run --extra test python -m pytest tests -q")[0]
      == {"all": ["bash", "-c", "uv run --extra test python -m pytest tests -q"],
          "line": "uv run --extra test python -m pytest tests -q"}
      and config.check_line(GO_CHECK) == "go test ./...")
check("a check reaching outside the workspace is refused, in either form",
      all(config.clean_check(c)[0] is None for c in (
          "cd ../TRD-EHR && pytest", "cat $HOME/x",
          {"all": ["go", "test", "../../projects/x/..."]},
          {"all": ["uv", "run", "--directory=../x", "pytest"]},
          {"all": ["bash", "-c", "cd ../x && make"]},
          {"all": ["make", "-C", "/elsewhere"]})))

target = {"id": "coinchange", "files": ["leetcode/coinchange"],
          "dirs": ["leetcode/coinchange"]}
rec, problems = holds.validate_hold(None, target, {}, set(), spec=GO_CHECK)
check("a directory is held with no thread file, its check the workspace's",
      not problems and rec["id"] == "coinchange" and "thread" not in rec
      and rec["check"] == {"spec": "one",
                           "argv": ["go", "test", "./leetcode/coinchange/..."]})
LEAN = {"all": ["bash", "scripts/build.sh"],
        "one": ["bash", "scripts/build.sh", "{module}"]}
rec, _ = holds.validate_hold(None, {"id": "e01", "files": [
    "Exercises/Sets/E01.lean"]}, {}, set(), spec=LEAN)
check("a Lean file's check builds its module",
      rec["check"]["argv"] == ["bash", "scripts/build.sh", "Exercises.Sets.E01"])
check("a placeholder is never filled with an option or a way out",
      holds.check_spec({"one": ["go", "vet", "{file}"]}, [("-x", False)])[0]
      is None
      and holds.check_spec({"one": GO_CHECK["one"]}, [("-x", True)])[0] is None
      and holds.check_spec({"one": GO_CHECK["one"]}, [("../up", True)])[0] is None)
check("`{file}` asked of a directory falls back to `all`",
      holds.check_spec({"one": ["go", "vet", "{file}"], "all": ["go", "vet"]},
                       [("leetcode", True)])[0]["spec"] == "all")
check("two held paths are checked by `all`",
      holds.check_spec(GO_CHECK, [("a", True), ("b", True)])[0]["spec"] == "all")
_, problems = holds.validate_hold(None, {"id": "x", "files": ["a.go"]}, {}, set())
check("a closed workspace refuses a hold with no check",
      any("no check" in p and "closed" in p for p in problems))
rec, problems = holds.validate_hold(None, {"id": "x", "files": ["a.go"]}, {},
                                    set(), open_=True)
check("an open one allows it, unchecked", not problems and rec["check"] is None)
_, problems = holds.validate_hold(None, {"id": "check-x", "files": ["a"]}, {},
                                  set(), open_=True)
check("a hold's id may not be a check report's", any("check-" in p for p in problems))
_, problems = holds.validate_hold(clean, {"id": "aipw", "files": ["a"]}, {},
                                  set(), open_=True)
check("nor another thread's", any("id of a thread" in p for p in problems))
mine = {"coinchange": {"id": "coinchange", "files": ["leetcode/coinchange"],
                       "held": 0}}
_, problems = holds.validate_hold(None, {"id": "other", "files": [
    "leetcode/coinchange/coinchange.go"]}, mine, set(), open_=True)
check("a file another hold owns is refused, naming the hold",
      any("is already held, by the hold coinchange" in p for p in problems))
_, problems = holds.validate_hold(None, {"id": "all", "files": ["leetcode"]},
                                  mine, set(), open_=True)
check("and so is a directory that would swallow one",
      any("leetcode holds leetcode/coinchange" in p for p in problems))
check("an id is a slug of the path's name",
      holds.slug("Coin_Change") == "coin-change" and holds.slug("check-me")
      == "h-check-me")

# --- the bounded output -----------------------------------------------------------
base = "/srv/x/projects/Algo"
text = ("\x1b[31m--- FAIL: TestCoinChange\x1b[0m\n"
        "    coinchange_test.go:9: ran in %s/leetcode/coinchange\n"
        "    coinchange_test.go:10: PATIENT-0042\n"
        "    and /home/someone/secret.csv\n"
        "FAIL\talgo/leetcode/coinchange\t0.002s\n" % base)
got = holds.check_output(text, base, lambda s: "PATIENT-" in s)
check("ANSI goes, the workspace's path goes relative, indentation stays",
      got["output"][0] == "--- FAIL: TestCoinChange"
      and got["output"][1] == "    coinchange_test.go:9: ran in leetcode/coinchange")
check("a line the PHI policy flags is withheld and counted",
      got["withheld"] == 1 and not any("PATIENT" in x for x in got["output"]))
check("any other absolute or home path becomes <path>",
      "    and <path>" in got["output"])
long = "\n".join("line %d" % i for i in range(1000))
got = holds.check_output(long, base, lambda s: False)
check("at most the first 40 and last 120 lines, the cut marked",
      got["output_total"] == 1000 and got["output_cut"] == 840
      and got["output"][0] == "line 0" and got["output"][40] == "… 840 lines cut …"
      and got["output"][-1] == "line 999" and len(got["output"]) == 161)
got = holds.check_output("\n".join("x" * 400 for _ in range(150)), base,
                         lambda s: False)
check("each line cut to 300 characters, and 16 KB in all",
      all(len(x) <= holds.MAX_LINE for x in got["output"])
      and sum(len(x) + 1 for x in got["output"]) <= holds.OUT_BYTES + 40
      and got["output_cut"] > 0)

# --- RELAY: lines --------------------------------------------------------------
lines, withheld = holds.relay_lines(
    "loading\nRELAY: n=120 mean=0.42\nrow 17: 0.9\nRELAY:ate=0.03\n"
    "RELAY: phi/session_01\n", names_phi=lambda s: "phi/" in s)
check("only RELAY: lines are kept, prefix dropped, a flagged one withheld",
      lines == ["n=120 mean=0.42", "ate=0.03"] and withheld == 1)
check("an absolute or home path in a RELAY: line becomes <path>",
      holds.relay_lines("RELAY: read 412 rows from /mnt/lab/storage/x.csv\n"
                        "RELAY: and ~/scratch/y\n")[0]
      == ["read 412 rows from <path>", "and <path>"])
check("at most MAX_LINES of them",
      len(holds.relay_lines("RELAY: x\n" * 100)[0]) == holds.MAX_LINES)
check("a crash is its exception type, never its message",
      holds.crash_type("Traceback...\n  File x\nValueError: row 17 was 0.9\n")
      == "ValueError" and holds.crash_type("all fine\n") == "")
check("a check report is told apart from a request's",
      holds.is_check("check-aipw-3") and not holds.is_check("2026-10-03-x"))
check("the coach file's header round-trips",
      holds.parse_coach(holds.coach_text("aipw", 3, "Next: the outcome model."))
      == ("aipw", 3, "Next: the outcome model."))

# --- one repository, three workspaces, two machines and one origin ----------------
PHI_POLICY = ("def names_phi(text):\n"
              "    t = str(text)\n"
              "    return 'phi/' in t or 'PATIENT-' in t\n")
COIN = ("package coinchange\n\n"
        "// CoinChange is the fewest coins making amount, or -1.\n"
        "func CoinChange(coins []int, amount int) int {\n\treturn -1\n}\n")
COIN_TEST = (
    "package coinchange\n\nimport (\n\t\"os\"\n\t\"testing\"\n)\n\n"
    "func TestCoinChange(t *testing.T) {\n"
    "\twd, _ := os.Getwd()\n"
    "\tt.Log(\"ran in\", wd)\n"
    "\tt.Log(\"PATIENT-0042 must never leave\")\n"
    "\tcases := []struct {\n\t\tcoins        []int\n\t\tamount, want int\n\t}{\n"
    "\t\t{[]int{1, 2, 5}, 11, 3},\n\t\t{[]int{2}, 3, -1},\n\t}\n"
    "\tfor _, c := range cases {\n"
    "\t\tif got := CoinChange(c.coins, c.amount); got != c.want {\n"
    "\t\t\tt.Errorf(\"coins %v amount %d: got %d, want %d\", c.coins, "
    "c.amount, got, c.want)\n\t\t}\n\t}\n}\n")

tmp = tempfile.mkdtemp(prefix="holds-")
saved_courses = os.environ.get("TUTORBOARD_COURSES")
try:
    origin = os.path.join(tmp, "origin.git")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin],
                   check=True)
    seed = os.path.join(tmp, "seed")
    os.makedirs(seed)
    git(seed, "init", "-q", "-b", "main")
    git(seed, "config", "user.email", "owner@example.com")
    git(seed, "config", "user.name", "Owner")
    write(os.path.join(seed, ".gitignore"), "ai-config/\n")
    # A research workspace with NO fence directory, closed by `"phi": true`
    # -- TRD-EHR's shape.
    ws = os.path.join(seed, "projects", "Proj")
    write(os.path.join(ws, "AI_INSTRUCTIONS.md"), "# contract\n")
    write(os.path.join(ws, "tutorboard.json"),
          json.dumps({"name": "Proj", "phi": True}))
    write(os.path.join(ws, ".gitignore"), "live/\nresults/\n")
    write(os.path.join(ws, "src", "aipw", "est.py"), "def est():\n    pass\n")
    write(os.path.join(ws, "notes.md"), "draft\n")
    write(os.path.join(ws, "checks", "aipw.sh"),
          "#!/bin/bash\necho 'RELAY: n=120 ate=0.031'\necho 'row 17 is 0.9'\n"
          "echo 'to stderr' >&2\nexit 0\n")
    write(threads.path(ws), json.dumps(SPINE))
    # A practice workspace with no thread file: LeetCode in Go.
    algo = os.path.join(seed, "projects", "Algo")
    write(os.path.join(algo, "AI_INSTRUCTIONS.md"), "# contract\n")
    write(os.path.join(algo, ".gitignore"), "live/\n")
    write(os.path.join(algo, "go.mod"), "module algo\n\ngo 1.24\n")
    write(os.path.join(algo, "tutorboard.json"), json.dumps({
        "name": "Algo", "phi": False, "check": {"all": ["go", "test", "./..."],
                                  "one": ["go", "test", "./{dir}/..."],
                                  "path": [os.path.dirname(GO)]}}))
    write(os.path.join(algo, "leetcode", "coinchange", "coinchange.go"), COIN)
    write(os.path.join(algo, "leetcode", "coinchange", "coinchange_test.go"),
          COIN_TEST)
    # A course, with a chapter and a homework file.
    course = os.path.join(seed, "courses", "Course")
    write(os.path.join(course, "AI_INSTRUCTIONS.md"), "# contract\n")
    write(os.path.join(course, ".gitignore"), "live/\n")
    write(os.path.join(course, "tutorboard.json"),
          json.dumps({"name": "Course", "phi": False}))
    write(os.path.join(course, "chapters.tsv"), "01\t1\t9\tgroups\tGroups\n")
    write(os.path.join(course, "chapters", "ch01-groups", "notes.tex"), "x\n")
    write(os.path.join(course, "homework", "hw01", "hw01.tex"),
          "\\begin{problem}\n\\end{problem}\n")
    # Two projects that do not say `"phi": false` where it counts: X has no
    # `phi` key at all; Y says false on disk, but HEAD has no key.
    for name in ("X", "Y"):
        write(os.path.join(seed, "projects", name, "tutorboard.json"),
              json.dumps({"name": name}))
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "start")
    git(seed, "remote", "add", "origin", origin)
    git(seed, "push", "-q", "-u", "origin", "main")

    def clone(name):
        top = os.path.join(tmp, name)
        subprocess.run(["git", "clone", "-q", origin, top], check=True)
        git(top, "config", "user.email", "owner@example.com")
        git(top, "config", "user.name", "Owner")
        # The lab's policy, private and never committed, on both machines.
        write(os.path.join(top, "ai-config", "policy", "phi.py"), PHI_POLICY)
        return top

    cl_top, mac_top = clone("cluster"), clone("mac")
    cl, mac = (os.path.join(t, "projects", "Proj") for t in (cl_top, mac_top))
    on_cluster = dict(os.environ, TUTOR_SLURM="1", TUTORBOARD_COURSES=cl_top,
                      GOFLAGS="-count=1", GOTOOLCHAIN="local", GOPROXY="off")
    on_mac = dict(os.environ, TUTOR_SLURM="0", TUTORBOARD_COURSES=mac_top)

    def board(where, env, *args, stdin=None):
        p = subprocess.run([sys.executable, BOARD] + list(args), cwd=where,
                           env=env, input=(stdin or "").encode(),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=240)
        return p.returncode, p.stdout.decode("utf-8", "replace")

    def inbox(where):
        # No session filed a held step, so each [coach] line is a home
        # notice (D16), oldest first here.
        from tutorboard import cluster
        top = cluster.atlas_of(where)
        rel = os.path.relpath(where, top)
        return [n for n in reversed(cluster.notices(top, limit=0))
                if n.get("subject") == rel]

    # --- which workspaces are open ---------------------------------------------
    os.environ["TUTORBOARD_COURSES"] = cl_top
    atlas.forget()
    fenced.forget()
    cl_algo = os.path.join(cl_top, "projects", "Algo")
    cl_course = os.path.join(cl_top, "courses", "Course")
    cl_x = os.path.join(cl_top, "projects", "X")
    cl_y = os.path.join(cl_top, "projects", "Y")
    write(os.path.join(cl_y, "tutorboard.json"),
          json.dumps({"name": "Y", "phi": False}))
    check("a workspace saying \"phi\": false, on disk and at HEAD, with the "
          "policy loaded is open", holds.output_open(cl_algo)
          and holds.output_open(cl_course))
    check("a workspace saying \"phi\": true is closed, with no fence on disk",
          not holds.output_open(cl, names_phi=lambda s: False,
                                cfg={"phi": True})
          and not holds.output_open(cl, names_phi=lambda s: False))
    check("a workspace whose config has no phi is closed",
          not holds.output_open(cl_algo, names_phi=lambda s: False, cfg={}))
    check("a project with no phi key is closed, whatever its family",
          not holds.output_open(cl_x)
          and not holds.output_open(cl_x, names_phi=lambda s: False)
          and config.read_config(cl_x)["phi"] is None)
    check("false on disk but not at HEAD is closed",
          config.read_config(cl_y)["phi"] is False
          and holds._head_phi(cl_y) is None
          and not holds.output_open(cl_y, names_phi=lambda s: False))
    write(os.path.join(cl_algo, "tutorboard.json"), json.dumps({"phi": "false"}))
    check("a phi that is not literally false is closed: a string is not false",
          not holds.output_open(cl_algo, names_phi=lambda s: False)
          and config.read_config(cl_algo)["phi"] is None)
    git(cl_top, "checkout", "--", "projects/Algo/tutorboard.json")
    check("a checkout without the lab's policy is closed",
          not holds.output_open(cl_algo, names_phi=False))
    os.makedirs(os.path.join(cl_algo, "phi"))
    fenced.forget()
    check("and so is one holding a fence directory",
          not holds.output_open(cl_algo))
    os.rmdir(os.path.join(cl_algo, "phi"))
    fenced.forget()
    check("the repository's top, a family's directory and a directory inside "
          "a workspace are closed: none says \"phi\": false of its own",
          not holds.output_open(cl_top) and not holds.output_open(
              os.path.join(cl_top, "projects"))
          and not holds.output_open(os.path.join(cl_algo, "leetcode")))
    write(os.path.join(cl_algo, "tutorboard.json"), json.dumps({"phi": True}))
    write(os.path.join(cl, "tutorboard.json"),
          json.dumps({"name": "Proj", "phi": False}))
    check("on-disk phi closes, and an edit to false does not open what "
          "HEAD closes", not holds.output_open(cl_algo)
          and not holds.output_open(cl, names_phi=lambda s: False)
          and holds._head_phi(cl) is True and holds._head_phi(cl_algo) is False)
    git(cl_top, "checkout", "--", "projects/Algo/tutorboard.json",
        "projects/Proj/tutorboard.json")
    shutil.rmtree(cl_y)
    git(cl_top, "checkout", "--", "projects/Y")
    os.symlink("../../projects/Proj/checks/aipw.sh",
               os.path.join(cl_algo, "leak.sh"))
    git(cl_top, "add", "projects/Algo/leak.sh")
    git(cl_top, "commit", "-q", "-m", "a symlink")
    check("a tracked symlink out of the workspace is not a script it may run",
          "leak.sh" not in holds._tracked(cl_algo)
          and "go.mod" in holds._tracked(cl_algo))
    git(cl_top, "reset", "-q", "--hard", "HEAD~1")
    code, out = board(cl_top, on_cluster, "hold", "--check",
                      "projects/Proj/checks/aipw.sh", "--", "projects/Proj/src")
    check("a hold from the repository's top, over another workspace, is "
          "refused", code == 1 and "not a workspace" in out)

    # --- what a bare `board hold` holds -------------------------------------------
    t, said, p = holds.resolve_target(cl_course, [], {
        "session": "homework", "chapter": "hw01",
        "hw": "homework/hw01/hw01.tex"})
    check("a homework sitting holds its homework file",
          not p and t["files"] == ["homework/hw01/hw01.tex"] and t["id"] == "hw01"
          and "homework file" in said)
    t, said, p = holds.resolve_target(cl_course, [], {"chapter": "Ch 01 — Groups"})
    check("a chapter sitting holds the chapter's directory, found on disk",
          not p and t["files"] == ["chapters/ch01-groups"]
          and t["dirs"] == ["chapters/ch01-groups"] and "chapter" in said)
    t, said, p = holds.resolve_target(cl, [], {"thread": "aipw"})
    check("a thread's sitting holds its thread", t == {
        "thread": "aipw", "check": "", "source": "the sitting's thread"})
    check("a sitting with nothing to hold asks for the files",
          holds.resolve_target(cl_algo, [], {"session": "lecture"})[2]
          and "name the files" in holds.resolve_target(cl_algo, [], {})[2][0])
    check("a path that is not there is refused",
          holds.resolve_target(cl_algo, ["--", "leetcode/nope"], {})[2])
    check("and so is one outside the workspace",
          holds.resolve_target(cl_algo, ["--", "../Course"], {})[2])

    # --- the fenced round trip: projects/Proj, a thread, RELAY: only --------------
    code, out = board(mac, on_mac, "hold", "aipw")
    check("a hold is refused on the Mac", code == 1 and "no Slurm" in out)
    code, out = board(cl, on_cluster, "hold", "aipw")
    check("`board hold` on the cluster holds and pushes",
          code == 0 and "held at the cluster" in out
          and "RELAY: lines only" in out
          and git(origin, "show", "main:projects/Proj/relay/holds/aipw.json"))
    files = git(cl_top, "show", "--name-only", "--format=", "HEAD").split()
    check("in one commit carrying the hold and nothing else",
          files == ["projects/Proj/relay/holds/aipw.json"])
    code, out = board(cl, on_cluster, "hold", "aipw")
    check("a second hold on the same thread is refused",
          code == 1 and "already held" in out)

    git(mac_top, "pull", "-q", "--ff-only")
    write(os.path.join(mac, "src", "aipw", "est.py"), "def est():\n    return 1\n")
    code, out = board(mac, on_mac, "push", "a turn's edit")
    check("on the Mac, `board push` refuses a commit touching a held file",
          code == 1 and "src/aipw/est.py belongs to thread aipw" in out)
    check("and nothing was committed",
          "est.py" in git(mac_top, "status", "--porcelain"))
    os.environ["TUTOR_SLURM"] = "0"
    check("a push narrowed to a path no hold covers passes the check",
          holds.refusal(mac, [os.path.join(mac, "notes.md")]) == ""
          and holds.refusal(mac).startswith("nothing was committed"))
    os.environ.pop("TUTOR_SLURM", None)
    git(mac_top, "checkout", "--", "projects/Proj/src/aipw/est.py")

    write(os.path.join(cl, "src", "aipw", "est.py"),
          "def est(y, a, x):\n    # the owner, mid-step\n    pass\n")
    write(os.path.join(cl, "src", "aipw", "fresh.py"), "x = 1\n")
    write(os.path.join(mac, "notes.md"), "draft, from the Mac\n")
    git(mac_top, "commit", "-q", "-am", "notes")
    git(mac_top, "push", "-q")
    ok, said = holds.sync(cl_top)
    check("the cluster pulls while the owner has uncommitted held edits",
          ok and read(os.path.join(cl, "notes.md")) == "draft, from the Mac\n")
    check("and the edits are exactly where they were, untracked file too",
          "the owner, mid-step" in read(os.path.join(cl, "src", "aipw", "est.py"))
          and os.path.exists(os.path.join(cl, "src", "aipw", "fresh.py"))
          and git(cl_top, "stash", "list").strip() == "")
    head = git(cl_top, "rev-parse", "HEAD")
    write(os.path.join(mac, "src", "aipw", "est.py"), "def est():\n    return 2\n")
    git(mac_top, "commit", "-q", "-am", "a Mac turn that broke the rule")
    git(mac_top, "push", "-q")
    ok, said = holds.sync(cl_top)
    check("origin touching an edited held file stops the pull, naming it",
          not ok and "projects/Proj/src/aipw/est.py" in said)
    check("with nothing moved and the owner's edit intact",
          git(cl_top, "rev-parse", "HEAD") == head
          and "the owner, mid-step" in read(os.path.join(cl, "src", "aipw",
                                                          "est.py")))
    git(mac_top, "revert", "--no-edit", "HEAD")
    git(mac_top, "push", "-q")
    ok, _ = holds.sync(cl_top)
    check("once origin leaves the file alone again, the pull goes through",
          ok and "the owner, mid-step" in read(os.path.join(cl, "src", "aipw",
                                                             "est.py")))

    code, out = board(cl, on_cluster, "release", "aipw")
    check("`board release` refuses while a held file has uncommitted edits",
          code == 1 and "board send" in out)

    sender = subprocess.Popen(
        [sys.executable, BOARD, "send", "aipw", "--wait", "90"], cwd=cl,
        env=on_cluster, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    rel = "projects/Proj/relay/reports/check-aipw-1.json"
    deadline = time.time() + 60
    while time.time() < deadline and not git(origin, "show", "main:" + rel):
        time.sleep(0.5)
    rep = json.loads(git(origin, "show", "main:" + rel) or "{}")
    check("`board send` pushes the check's report",
          rep.get("kind") == "check" and rep.get("step") == 1
          and rep.get("exit") == 0 and rep.get("state") == "completed"
          and rep.get("hold") == "aipw" and rep.get("thread") == "aipw")
    check("which carries the RELAY: line and nothing else the check printed",
          rep.get("relay") == ["n=120 ate=0.031"] and rep.get("open") is False
          and "output" not in rep
          and "row 17" not in json.dumps(rep) and "stderr" not in json.dumps(rep))
    check("and names the files the step changed",
          rep.get("files") == ["src/aipw/est.py", "src/aipw/fresh.py"])
    log = git(origin, "log", "-2", "--format=%an|%s", "main").splitlines()
    check("the step is its own commit, `aipw: step`, authored by the owner",
          log == ["Owner|aipw: check 1", "Owner|aipw: step"])

    git(mac_top, "pull", "-q", "--ff-only")
    woke = holds.wake(mac)
    said = inbox(mac)[-1]
    step_sha = git(origin, "rev-parse", "main~1").strip()[:12]
    check("the pull carrying the report wakes one [coach] turn",
          len(woke) == 1 and said["signal"] == "coach"
          and said["text"].startswith("[coach] Step 1 of thread aipw"))
    check("naming the step's commit, the check's exit and its RELAY: lines",
          "git show %s" % step_sha in said["text"]
          and "exit 0" in said["text"]
          and "RELAY: n=120 ate=0.031" in said["text"]
          and "board coach aipw --step 1" in said["text"])
    check("and, fenced, it keeps the turn to aggregates",
          "never about rows" in said["text"] and "output" not in said["text"])
    check("and a second wake on the same report drops nothing",
          holds.wake(mac) == [])

    code, out = board(mac, on_mac, "coach", "aipw", "--step", "1",
                      stdin="The estimate is in. Next: the outcome model.\n")
    check("`board coach` on the Mac commits the reply alone and pushes it",
          code == 0 and git(origin, "show", "--name-only", "--format=",
                            "main").split()
          == ["projects/Proj/relay/coach/aipw.md"])
    try:
        out = sender.communicate(timeout=120)[0].decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        sender.kill()
        out = ""
    check("and `board send` prints it in the cluster terminal",
          sender.returncode == 0 and "Next: the outcome model." in out
          and "RELAY: n=120 ate=0.031" in out)
    git(mac_top, "pull", "-q", "--ff-only")
    check("a step already answered wakes nothing", holds.wake(mac) == [])
    code, out = board(cl, on_cluster, "release", "aipw")
    check("with the step sent, `board release` ends the hold and pushes it",
          code == 0 and not git(origin, "show",
                                "main:projects/Proj/relay/holds/aipw.json"))

    # --- the open round trip: LeetCode in Go, no thread file -----------------------
    mac_algo = os.path.join(mac_top, "projects", "Algo")
    if not os.access(GO, os.X_OK):
        print("skip the Go round trip: no %s on this machine" % GO)
    else:
        code, out = board(cl_algo, on_cluster, "hold", "--", "leetcode/coinchange")
        hrel = "projects/Algo/relay/holds/coinchange.json"
        held = json.loads(git(origin, "show", "main:" + hrel) or "{}")
        check("a directory is held in a workspace with no thread file",
              code == 0 and held.get("id") == "coinchange"
              and held.get("files") == ["leetcode/coinchange"]
              and "thread" not in held)
        check("its check is the workspace's, made concrete for the package",
              held.get("check") == {"spec": "one", "argv": [
                  "go", "test", "./leetcode/coinchange/..."]}
              and "the check's own, cut to fit" in out)
        code, out = board(cl_algo, on_cluster, "hold", "--as", "other", "--",
                          "leetcode/coinchange/coinchange.go")
        check("a hold on a file another hold owns is refused, naming it",
              code == 1 and "already held, by the hold coinchange" in out)

        git(mac_top, "pull", "-q", "--ff-only")
        write(os.path.join(mac_algo, "leetcode", "coinchange", "coinchange.go"),
              COIN.replace("return -1", "return 0"))
        code, out = board(mac_algo, on_mac, "push", "a turn's edit")
        check("the Mac refuses to write the held package",
              code == 1 and "leetcode/coinchange/coinchange.go belongs to the "
              "hold coinchange" in out)
        git(mac_top, "checkout", "--",
            "projects/Algo/leetcode/coinchange/coinchange.go")

        # The owner's step: wrong, so the test fails and says how.
        write(os.path.join(cl_algo, "leetcode", "coinchange", "coinchange.go"),
              COIN.replace("return -1", "return amount"))
        code, out = board(cl_algo, on_cluster, "send", "--no-wait")
        rel = "projects/Algo/relay/reports/check-coinchange-1.json"
        rep = json.loads(git(origin, "show", "main:" + rel) or "{}")
        body = "\n".join(rep.get("output") or [])
        check("`board send` runs `go test` on the package and reports it failed",
              code == 0 and rep.get("state") == "failed" and rep.get("exit") == 1
              and rep.get("open") is True and rep.get("hold") == "coinchange")
        check("its full output reaches the report: which case, and why",
              "--- FAIL: TestCoinChange" in body
              and "coins [1 2 5] amount 11: got 11, want 3" in body
              and "coinchange_test.go:" in body)
        check("with the workspace's paths relative and nothing absolute",
              "ran in leetcode/coinchange" in body and tmp not in json.dumps(rep)
              and os.path.realpath(tmp) not in json.dumps(rep))
        check("and the line the PHI policy flags withheld",
              "PATIENT" not in json.dumps(rep) and rep.get("withheld") == 1)
        log = git(origin, "log", "-2", "--format=%s", "main").splitlines()
        check("the step is `coinchange: step`", log == [
            "coinchange: check 1", "coinchange: step"])

        git(mac_top, "pull", "-q", "--ff-only")
        woke = holds.wake(mac_algo)
        said = inbox(mac_algo)[-1]["text"]
        step_sha = git(origin, "rev-parse", "main~1").strip()[:12]
        check("the Mac wakes a [coach] turn on the hold",
              len(woke) == 1 and said.startswith("[coach] Step 1 of coinchange")
              and "git show %s" % step_sha in said)
        check("carrying the output, and saying to read it rather than rerun it",
              "| --- FAIL: TestCoinChange" in said
              and "got 11, want 3" in said and "its output is above" in said
              and "board coach coinchange --step 1" in said)
        code, out = board(mac_algo, on_mac, "coach", "--step", "1", stdin=(
            "Returning amount uses only ones. Next: a table of the fewest "
            "coins for every value up to amount.\n"))
        check("`board coach` with one hold standing needs no id", code == 0)
        code, out = board(cl_algo, on_cluster, "send", "--reply")
        check("and `board send --reply` prints it on the cluster",
              code == 0 and "a table of the fewest coins" in out)
        code, out = board(cl_algo, on_cluster, "release")
        check("`board release` with one hold standing ends it",
              code == 0 and not git(origin, "show", "main:" + hrel))

    # --- a course sitting holding its homework file -------------------------------
    git(cl_top, "pull", "-q", "--ff-only")
    write(os.path.join(cl_course, "live", "state.json"), json.dumps({
        "session": "homework", "chapter": "hw01",
        "hw": "homework/hw01/hw01.tex"}))
    code, out = board(cl_course, on_cluster, "hold")
    check("a bare `board hold` in a course holds the sitting's homework file",
          code == 0 and "homework file: homework/hw01/hw01.tex" in out
          and git(origin, "show", "main:courses/Course/relay/holds/hw01.json"))
    write(os.path.join(cl_course, "homework", "hw01", "hw01.tex"),
          "\\begin{problem}\nLet $G$ be a group.\n\\end{problem}\n")
    code, out = board(cl_course, on_cluster, "send", "--no-wait")
    rep = json.loads(git(origin, "show", "main:courses/Course/relay/reports/"
                                         "check-hw01-1.json") or "{}")
    check("with no check, the step goes as the diff alone",
          code == 0 and rep.get("state") == "unchecked"
          and rep.get("files") == ["homework/hw01/hw01.tex"])
    mac_course = os.path.join(mac_top, "courses", "Course")
    git(mac_top, "pull", "-q", "--ff-only")
    holds.wake(mac_course)
    said = inbox(mac_course)[-1]["text"]
    check("and the coach is told so", "this hold has no check" in said)
    code, out = board(cl_course, on_cluster, "hold", "--", "chapters/ch01-groups")
    check("a second hold stands beside it", code == 0)
    code, out = board(cl_course, on_cluster, "release", "hw01")
    check("and one is released by its id while the other stands",
          code == 0 and not git(origin, "show",
                                "main:courses/Course/relay/holds/hw01.json")
          and git(origin, "show",
                  "main:courses/Course/relay/holds/ch01-groups.json"))
    code, out = board(cl_course, on_cluster, "release", "ch01-groups")
    check("and then the other", code == 0)
finally:
    if saved_courses is None:
        os.environ.pop("TUTORBOARD_COURSES", None)
    else:
        os.environ["TUTORBOARD_COURSES"] = saved_courses
    atlas.forget()
    shutil.rmtree(tmp, ignore_errors=True)

# --- the real repository ------------------------------------------------------------
for ws in ("projects/TRD-EHR", "projects/PSYCH-ASR", "projects/libr-local-llm",
           "projects/Algo-Solutions", "projects/Lean-Theorem-Proving",
           "courses/Galois-Theory", "courses/Probability", "projects/Paper-Writer"):
    root = os.path.join(REPO, ws)
    if os.path.isdir(root):
        check("%s: git would see a hold" % ws, holds.visible(root) == "")
for ws in ("projects/TRD-EHR", "projects/PSYCH-ASR", "projects/libr-local-llm"):
    root = os.path.join(REPO, ws)
    if os.path.isdir(root):
        check("%s is closed: RELAY: lines only" % ws,
              not holds.output_open(root, names_phi=lambda s: False))
        check("%s says so in a tracked tutorboard.json" % ws,
              config.read_config(root)["phi"] is True
              and not jobs.ignored(root, "tutorboard.json"))
# Fail closed: exactly the subjects that say `"phi": false` at HEAD are open,
# and only with the lab's policy loaded. Without ai-config, none is.
OPEN = {"projects/Paper-Writer", "projects/Algo-Solutions",
        "projects/Lean-Theorem-Proving", "courses/Galois-Theory",
        "courses/Probability"}
atlas.forget()
policy = callable(holds._policy(REPO))
found = {w["id"]: holds.output_open(w["root"])
         for w in atlas.workspaces(REPO)}
check("the open subjects are exactly %s%s" % (
          ", ".join(sorted(OPEN)), "" if policy else " (none: no policy here)"),
      {w for w, o in found.items() if o} == (
          {w for w in OPEN if w in found} if policy else set()))
for ws in sorted(OPEN):
    root = os.path.join(REPO, ws)
    if os.path.isdir(root):
        check("%s says \"phi\": false in a tracked tutorboard.json" % ws,
              config.read_config(root)["phi"] is False
              and holds._head_phi(root) is False
              and not jobs.ignored(root, "tutorboard.json"))
for ws in ("projects/Algo-Solutions", "projects/Lean-Theorem-Proving"):
    root = os.path.join(REPO, ws)
    if os.path.isdir(root):
        cfg = config.read_config(root)
        check("%s declares a check that reads clean" % ws,
              cfg["check"] and not cfg["check_problems"])

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a sitting in any workspace is written at the cluster and coached from "
      "the Mac, and only an open workspace's output leaves it whole")
