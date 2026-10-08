#!/usr/bin/env python3
"""A walkthrough: a lesson about machinery that already exists.

Every other sitting on this board ends in the student producing something new.
In a working project most of what has to be understood was written months ago,
and a tutor with nowhere to put that does the only thing it can -- there is a
card in PSYCH-ASR that proves it, invented arithmetic on fictional numbers in a
repository whose owner wanted an algorithm on disk explained to him.

So: the scope is a file in this repository, checked before it reaches
anything. What is guarded here is that nothing invented reaches the filesystem
or the prompt, and that who writes the code is the session's mode alone.
"""

import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tutorboard.course import walk            # noqa: E402
from tutorboard.course import config          # noqa: E402
from tutorboard import brief, sense           # noqa: E402
from tutorboard.course import repo as course_repo   # noqa: E402
from tutorboard.lesson import archive         # noqa: E402
from tutorboard.server import handler, hub, tikz    # noqa: E402
from http.server import ThreadingHTTPServer   # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# A file has to be big enough to be worth a sitting; `MIN_BYTES` is the floor and
# every fixture here clears it without anybody having to count characters.
BODY = "\n".join("    # a line of it that is long enough to be real" for _ in range(8))

# --- what a repository can be walked through ---------------------------------
# Discovered, never registered, exactly as chapters and problem sets are.
proj = tempfile.mkdtemp(prefix="tutor-walk-proj-")
prose = tempfile.mkdtemp(prefix="tutor-walk-prose-")
try:
    write(proj, "psych_asr/__init__.py", "from . import evaluate\n" + BODY)
    write(proj, "psych_asr/config.py", "SETTING = 1\n" + BODY)
    write(proj, "psych_asr/evaluate/__init__.py", "\n" + BODY)
    write(proj, "psych_asr/evaluate/grade.py",
          "import re\n\n\ndef grade(reference, candidate):\n" + BODY + "\n\n\nclass Finding:\n    pass\n")
    write(proj, "psych_asr/transcript/corrections.py",
          "def apply_corrections(turns, log):\n" + BODY + "\n")
    write(proj, "scripts/run.sh", "#!/usr/bin/env bash\nset -eu\n" + BODY + "\n")
    write(proj, "README.md", "# a project\n" + BODY)
    write(proj, "notes.txt", "not machinery\n" + BODY)
    write(proj, "psych_asr/tiny.py", "x = 1\n")
    # A SHEBANG IS AS GOOD A DECLARATION AS A SUFFIX, and `SOURCE` keyed on the
    # suffix alone -- so the entire surface of colibrì, which is `bin/coli`,
    # `bin/coli-up`, `bin/coli-ask` and `bin/coli-code`, was invisible. A
    # walkthrough of that workspace offered six files and not one of them was
    # the one anybody would ask for.
    write(proj, "bin/coli-up",
          "#!/usr/bin/env bash\nset -eu\nwarm() {\n" + BODY + "\n}\n")
    write(proj, "bin/coli-ask", "#!/bin/bash\n" + BODY + "\n")
    write(proj, "bin/tally", "#!/usr/bin/env python3\ndef tally(rows):\n" + BODY + "\n")
    # And a file that declared nothing at all is not machinery. A licence, a
    # lock file and a data dump all have no suffix either.
    write(proj, "LICENSE", "All rights reserved.\n" + BODY)
    write(proj, "README", "# prose with no suffix\n" + BODY)
    for d in ("live", "node_modules", "__pycache__", "results", "data", ".git"):
        os.makedirs(os.path.join(proj, d), exist_ok=True)
        write(proj, os.path.join(d, "buried.py"), "def buried():\n" + BODY + "\n")

    names = [u["name"] for u in walk.units(proj)]
    check("a project offers its own source files",
          "psych_asr/evaluate/grade.py" in names
          and "psych_asr/transcript/corrections.py" in names)
    check("and shell scripts, because a pipeline is taught by its job script too",
          "scripts/run.sh" in names)
    check("and a script with a #! line and no suffix at all, which is what a "
          "driver command is",
          "bin/coli-up" in names and "bin/coli-ask" in names
          and "bin/tally" in names)
    # A README is read by reading it. A walkthrough over one is a lecture with
    # extra steps, and offering it buries the files that do something.
    check("but never prose", not [n for n in names if n.endswith((".md", ".txt"))])
    check("and never a file that declared nothing -- no suffix and no shebang",
          "LICENSE" not in names and "README" not in names)
    # The symbol check has to know which language a shebang stands in for, or a
    # function named inside a suffixless script is a name it cannot verify --
    # and an unverifiable name is one `resolve` refuses to carry.
    chosen, _ = walk.resolve(proj, ["bin/coli-up::warm"])
    check("a function inside a #! bash script is found the way one in a .sh is",
          [u["name"] for u in chosen] == ["bin/coli-up::warm"])
    chosen, _ = walk.resolve(proj, ["bin/tally::tally"])
    check("and one inside a #! python script too",
          [u["name"] for u in chosen] == ["bin/tally::tally"])
    check("while a name such a script does not define is still refused",
          walk.resolve(proj, ["bin/coli-up::missing"])[1] == ["bin/coli-up::missing"])
    check("and never build output, dependencies, data or the board's own live/",
          not [n for n in names if n.split("/")[0]
               in ("live", "node_modules", "__pycache__", "results", "data", ".git")])
    check("an __init__.py is a namespace, not machinery, and is not offered",
          not [n for n in names if n.endswith("__init__.py")])
    check("and neither is a file with nothing in it",
          "psych_asr/tiny.py" not in names)
    check("each one says which directory it is in, so a list of a hundred can be read",
          all(u["dir"] for u in walk.units(proj))
          and {u["dir"] for u in walk.units(proj)}
          >= {"psych_asr", "psych_asr/evaluate", "scripts"})
    check("and they come back in the repository's own order, not the order os.walk found them",
          names == sorted(names, key=lambda n: (os.path.dirname(n), n)))

    write(prose, "README.md", "# all narrative, no machinery\n" + BODY)
    check("a repository with no source says so rather than inventing something",
          walk.units(prose) == [] and walk.status(prose, {}) is None
          and walk.kind(prose) == "")

    # --- a name from a request is checked, never trusted ----------------------
    # A person names machinery the way their language names it, and the last
    # component of a dotted name is as likely to be the function as the module.
    chosen, unknown = walk.resolve(proj, ["psych_asr/evaluate/grade.py"])
    check("a file can be named by its path",
          [u["name"] for u in chosen] == ["psych_asr/evaluate/grade.py"])
    chosen, _ = walk.resolve(proj, ["psych_asr.evaluate.grade"])
    check("or as a module, the way the language names it",
          [u["name"] for u in chosen] == ["psych_asr/evaluate/grade.py"])
    chosen, _ = walk.resolve(proj, ["psych_asr.evaluate.grade.grade"])
    check("or as a definition inside one, which is where a walkthrough starts",
          [u["name"] for u in chosen] == ["psych_asr/evaluate/grade.py::grade"]
          and chosen[0]["symbol"] == "grade")
    chosen, _ = walk.resolve(proj, ["psych_asr.evaluate.grade.Finding"])
    check("a class is a definition too", chosen and chosen[0]["symbol"] == "Finding")
    # The whole point of checking: a walkthrough announced over a function that
    # is not there sends the tutor looking, and it will find something else and
    # teach that instead.
    check("a name the file does not define is refused rather than carried",
          walk.resolve(proj, ["psych_asr.evaluate.grade.missing"])[1]
          == ["psych_asr.evaluate.grade.missing"])
    check("and so is a file this repository does not have",
          walk.resolve(proj, ["psych_asr/evaluate/nothing.py"])[1]
          == ["psych_asr/evaluate/nothing.py"])
    check("a bare filename works where the repository has only one of them",
          [u["name"] for u in walk.resolve(proj, ["corrections.py"])[0]]
          == ["psych_asr/transcript/corrections.py"])
    write(proj, "scripts/config.py", "OTHER = 2\n" + BODY)
    walk._cache.clear()
    check("and resolves to nothing where it would have to guess between two",
          walk.resolve(proj, ["config.py"])[1] == ["config.py"])
    check("naming the same file twice walks it once",
          len(walk.resolve(proj, ["psych_asr.evaluate.grade",
                                  "psych_asr/evaluate/grade.py"])[0]) == 1)
    check("a file and one definition inside it are two different scopes",
          len(walk.resolve(proj, ["psych_asr.evaluate.grade",
                                  "psych_asr.evaluate.grade.grade"])[0]) == 2)

    # --- the scope is re-resolved on the way out, never echoed back -----------
    state = {"walk": ["psych_asr/evaluate/grade.py::grade",
                      "psych_asr/gone.py"]}
    check("a scope naming something deleted since drops it",
          [u["name"] for u in walk.scope(proj, state)]
          == ["psych_asr/evaluate/grade.py::grade"])

    check("a short scope is named in the sitting label",
          walk.sitting_label(walk.resolve(proj, ["psych_asr.evaluate.grade.grade"])[0])
          == "Walkthrough — grade")
    check("and a long one is counted instead of listed",
          walk.sitting_label([{"short": "a"}] * 5) == "Walkthrough — 5 files")
finally:
    shutil.rmtree(prose, ignore_errors=True)

# --- what the tutor is actually told ------------------------------------------
# A walkthrough is a method the tutor picks in teach mode, not a sitting kind: a
# state still saying `session: walk` reads as a lecture.
try:
    json.dump({"name": "PSYCH-ASR"},
              open(os.path.join(proj, "tutorboard.json"), "w"))
    r = course_repo.Repo(proj)
    st = r.state()
    st.update({"session": "walk",
               "walk": ["psych_asr/evaluate/grade.py::grade"]})
    json.dump(st, open(r.state_path, "w"))
    line = sense.session_sense(r)
    check("a legacy walk sitting reads as a lecture in teach mode",
          "WALKTHROUGH SITTING" not in line and "IN TEACH MODE" in line
          and "a walkthrough of code that already exists" in line)
finally:
    pass

# --- the mode is the session's, and tutorboard.json says nothing about it ------
teach_repo = tempfile.mkdtemp(prefix="tutor-walk-teach-")
do_repo = tempfile.mkdtemp(prefix="tutor-walk-do-")
try:
    json.dump({"name": "PSYCH-ASR"},
              open(os.path.join(teach_repo, "tutorboard.json"), "w"))
    json.dump({"name": "TRD-EHR", "stance": "do"},
              open(os.path.join(do_repo, "tutorboard.json"), "w"))
    write(teach_repo, "psych_asr/grid.py", "def sweep():\n" + BODY + "\n")
    write(do_repo, "pipeline/confound.py", "def overlap():\n" + BODY + "\n")

    rd = course_repo.Repo(do_repo)
    st = rd.state()
    st.update({"session": "lecture", "chapter": "the propensity model"})
    json.dump(st, open(rd.state_path, "w"))
    line = sense.session_sense(rd)
    check("a tutorboard.json stance of do is ignored: the session teaches",
          "IN TEACH MODE" in line and "IN DO MODE" not in line)

    rt = course_repo.Repo(teach_repo)
    st = rt.state()
    st.update({"session": "lecture", "chapter": "the grid sweep", "mode": "do"})
    json.dump(st, open(rt.state_path, "w"))
    line = sense.session_sense(rt)
    check("a session in do mode is told to write the code",
          "IN DO MODE" in line and "you write the code yourself" in line)
    line = brief.briefing(rt, sense)
    check("the briefing names the mode", "mode: do" in line)
    st.pop("mode")
    json.dump(st, open(rt.state_path, "w"))
    line = brief.briefing(rt, sense)
    check("and teach when the session says nothing", "mode: teach" in line)
    check("a workspace that names no check gets no check line",
          "\ncheck: " not in line)
    json.dump({"name": "PSYCH-ASR", "check": "uv run --extra test python -m pytest tests -q"},
              open(os.path.join(teach_repo, "tutorboard.json"), "w"))
    line = brief.briefing(rt, sense)
    check("the briefing names the workspace's check, to run before a push",
          "check: uv run --extra test python -m pytest tests -q" in line
          and "before a push" in line)
finally:
    shutil.rmtree(teach_repo, ignore_errors=True)
    shutil.rmtree(do_repo, ignore_errors=True)

# --- the sitting itself, through the real handler -----------------------------
tmp = tempfile.mkdtemp(prefix="tutor-walk-")
try:
    json.dump({"name": "PSYCH-ASR"},
              open(os.path.join(tmp, "tutorboard.json"), "w"))
    write(tmp, "psych_asr/evaluate/grade.py",
          "def grade(reference, candidate):\n" + BODY + "\n")
    write(tmp, "psych_asr/transcript/corrections.py",
          "def apply_corrections(turns, log):\n" + BODY + "\n")
    walk._cache.clear()
    repo = course_repo.Repo(tmp)
    open(os.path.join(repo.cards, "0001-mid-lesson.md"), "w",
         encoding="utf-8").write("---\nkind: lesson\ntitle: A card\n---\n\nx\n")

    worker = tikz.TikzWorker(repo)
    worker.start()
    board = hub.Hub(repo, worker)
    board.payload = json.dumps(board.build())

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler.Handler)
    httpd.daemon_threads = True
    httpd.repo = repo
    httpd.hub = board
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    BASE = "http://127.0.0.1:%d" % port

    def post(path, body):
        req = urllib.request.Request(BASE + path, method="POST",
                                     data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    try:
        payload = board.build()
        check("the board is told what can be walked through before any walkthrough exists",
              payload.get("walk") and len(payload["walk"]["units"]) == 2)
        check("and that nothing is being walked through yet",
              payload["walk"]["scope"] == [])

        status, _ = post("/session", {
            "session": "walk", "over": ["psych_asr.evaluate.grade.grade"]})
        check("the board no longer opens a walkthrough sitting", status == 400)
        check("and the lesson it would have interrupted is untouched",
              not archive.list_archive(repo))
        status, _ = post("/session", {"session": "lecture", "stance": "do"})
        check("a stance sent with a sitting is ignored",
              status == 200 and not repo.state().get("stance")
              and "IN DO MODE" not in sense.session_sense(repo))
    finally:
        httpd.shutdown()
finally:
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(proj, ignore_errors=True)

# ---------------------------------------------------------------------------
# ANY PATH IN ATLAS, WITH board/ AND vendor/ READ-ONLY
# ---------------------------------------------------------------------------
# A name this subject does not have is looked for under the Atlas root. The
# subject's own source comes first, the bare-filename shortcut stays the
# subject's, and nothing private, hidden, ignored or fenced is reachable.
from tutorboard import atlas                                # noqa: E402

home = tempfile.mkdtemp(prefix="tutor-walk-atlas-")
outside = tempfile.mkdtemp(prefix="tutor-walk-outside-")
was = os.environ.get("TUTORBOARD_COURSES")
try:
    write(home, "courses/Topology/tutorboard.json", '{"name": "Topology"}')
    write(home, "courses/Topology/topo/space.py",
          "def open_sets(x):\n" + BODY + "\n")
    write(home, "projects/PSYCH-ASR/tutorboard.json", '{"name": "PSYCH-ASR"}')
    write(home, "projects/PSYCH-ASR/psych_asr/grade.py",
          "def grade(a, b):\n" + BODY + "\n")
    write(home, "projects/PSYCH-ASR/phi/a.py", "def a():\n" + BODY + "\n")
    write(home, "projects/PSYCH-ASR/results/r.py", "def r():\n" + BODY + "\n")
    write(home, "board/tutorboard/relay.py",
          "def run_once(base):\n" + BODY + "\n")
    write(home, "board/data/x.py", "def x():\n" + BODY + "\n")
    write(home, "board/node_modules/katex/index.js",
          "function render() {\n" + BODY + "\n}\n")
    write(home, "vendor/colibri/bin/coli-up",
          "#!/usr/bin/env bash\nwarm() {\n" + BODY + "\n}\n")
    write(home, "vendor/colibri/raw/x.py", "def x():\n" + BODY + "\n")
    write(home, "vendor/colibri/README.md", "# colibri\n" + BODY)
    write(home, "ai-config/policy/phi.py", "def fence():\n" + BODY + "\n")
    write(home, "sessions/20261008-000000/x.py", "def x():\n" + BODY + "\n")
    write(home, ".hidden/x.py", "def x():\n" + BODY + "\n")
    write(outside, "secret.py", "def secret():\n" + BODY + "\n")
    os.symlink(os.path.join(outside, "secret.py"),
               os.path.join(home, "projects", "PSYCH-ASR", "escape.py"))
    os.environ["TUTORBOARD_COURSES"] = home
    walk._cache.clear()
    ws = os.path.join(home, "courses", "Topology")

    check("a vendor tree is not a subject: the family is skipped",
          [w["id"] for w in atlas.workspaces()]
          == ["courses/Topology", "projects/PSYCH-ASR"])
    check("and the vendor-tree machinery is gone",
          not hasattr(atlas, "trees") and not hasattr(atlas, "find_tree")
          and not hasattr(walk, "resolve_any")
          and not hasattr(walk, "ELSEWHERE"))

    chosen, unknown = walk.resolve(ws, ["board/tutorboard/relay.py"])
    check("board/tutorboard/relay.py resolves from a course, read-only",
          not unknown and len(chosen) == 1
          and chosen[0]["path"] == "board/tutorboard/relay.py"
          and chosen[0]["readonly"] is True
          and os.path.realpath(chosen[0]["root"]) == os.path.realpath(home))
    chosen, unknown = walk.resolve(ws, ["vendor/colibri/bin/coli-up"])
    check("vendor/colibri/bin/coli-up resolves by its shebang, read-only",
          not unknown and [u["name"] for u in chosen]
          == ["vendor/colibri/bin/coli-up"] and chosen[0]["readonly"] is True)
    chosen, unknown = walk.resolve(ws, ["vendor/colibri/bin/coli-up::warm",
                                        "board.tutorboard.relay.run_once"])
    check("a symbol in Atlas is carried once the file really defines it",
          not unknown and sorted(u["name"] for u in chosen)
          == ["board/tutorboard/relay.py::run_once",
              "vendor/colibri/bin/coli-up::warm"])
    check("and one it does not define is unknown",
          walk.resolve(ws, ["board/tutorboard/relay.py::missing"])[1]
          == ["board/tutorboard/relay.py::missing"])

    chosen, unknown = walk.resolve(ws, ["topo/space.py", "board/tutorboard/relay.py"])
    check("the subject's own source comes first, and is not read-only",
          not unknown and [u["path"] for u in chosen]
          == ["topo/space.py", "board/tutorboard/relay.py"]
          and chosen[0]["readonly"] is False
          and os.path.realpath(chosen[0]["root"]) == os.path.realpath(ws))
    chosen, unknown = walk.resolve(
        ws, ["projects/PSYCH-ASR/psych_asr/grade.py::grade"])
    check("another project's source resolves, and is not read-only",
          not unknown and chosen[0]["readonly"] is False
          and chosen[0]["name"] == "projects/PSYCH-ASR/psych_asr/grade.py::grade")
    check("the bare-filename shortcut stays subject-local",
          walk.resolve(ws, ["relay.py", "coli-up", "grade.py"])[1]
          == ["relay.py", "coli-up", "grade.py"]
          and [u["path"] for u in walk.resolve(ws, ["space.py"])[0]]
          == ["topo/space.py"])

    fenced_names = ["projects/PSYCH-ASR/phi/a.py", "vendor/colibri/raw/x.py",
                    "board/data/x.py::x", "projects.PSYCH-ASR.phi.a"]
    chosen, unknown = walk.resolve(ws, fenced_names)
    check("a fenced name is refused anywhere in Atlas",
          chosen == [] and unknown == fenced_names)
    refused = ["ai-config/policy/phi.py", "sessions/20261008-000000/x.py",
               ".hidden/x.py", "projects/PSYCH-ASR/results/r.py",
               "board/node_modules/katex/index.js", "vendor/colibri/README.md",
               "projects/PSYCH-ASR/escape.py", "../" + os.path.basename(outside)
               + "/secret.py", os.path.join(outside, "secret.py"),
               "courses/Topology/../../etc/passwd", "board/tutorboard/nope.py"]
    for name in refused:
        check("refused: %s" % name, walk.resolve(ws, [name])[1] == [name])
    chosen, _ = walk.resolve(ws, ["Board/tutorboard/relay.py"])
    check("a differently-cased board/ path is still read-only",
          all(u["readonly"] for u in chosen))

    st = {"walk": ["vendor/colibri/bin/coli-up::warm"]}
    check("a scope in Atlas is re-resolved on the way out",
          [u["name"] for u in walk.scope(ws, st)]
          == ["vendor/colibri/bin/coli-up::warm"])

    line = sense.session_sense(course_repo.Repo(ws))
    check("the sense says any path in Atlas may be traced, board/ and vendor/ "
          "read-only",
          "TRACE ANY PATH IN ATLAS" in line
          and "board/ and vendor/ ARE READ-ONLY" in line)
finally:
    if was is None:
        os.environ.pop("TUTORBOARD_COURSES", None)
    else:
        os.environ["TUTORBOARD_COURSES"] = was
    walk._cache.clear()
    shutil.rmtree(home, ignore_errors=True)
    shutil.rmtree(outside, ignore_errors=True)

# The real Atlas root: the board's own relay module, from a temp subject.
atlas_root = os.path.dirname(ROOT)
somewhere = tempfile.mkdtemp(prefix="tutor-walk-real-")
try:
    chosen, unknown = walk.resolve(somewhere, ["board/tutorboard/relay.py"],
                                   base=atlas_root)
    check("the real board/tutorboard/relay.py resolves read-only",
          not unknown and chosen[0]["readonly"] is True)
finally:
    walk._cache.clear()
    shutil.rmtree(somewhere, ignore_errors=True)

# --- the fence: no code walker looks inside a directory in fenced.NEVER -------
from tutorboard import fenced                                # noqa: E402
from tutorboard.course import symbols                        # noqa: E402

fence = tempfile.mkdtemp(prefix="tutor-walk-fence-")
try:
    for rel in ("pkg/ok.py", "stage1/run.py", "raw/x.py", "phi/y.py",
                "PHI/z.py", "pkg/Audio/w.py"):
        write(fence, rel, "def f():\n" + BODY + "\n    return 1\n")
    walk._cache.clear()
    check("in_fence matches any lower-cased component, and nothing else",
          fenced.in_fence("a/Stage1/x.py") and fenced.in_fence("phi")
          and fenced.in_fence("a\\raw\\b.py")
          and not fenced.in_fence("pkg/ok.py") and not fenced.in_fence("raw.py")
          and not fenced.in_fence(""))
    check("walk.units lists only the file outside every fence",
          [u["path"] for u in walk.units(fence)] == ["pkg/ok.py"])
    typed = ["stage1/run.py::f", "stage1/run.py", "stage1.run.f", "phi/y.py",
             "raw/x.py::f", "PHI/z.py"]
    chosen, unknown = walk.resolve(fence, typed)
    check("walk.resolve refuses a typed path through the fence",
          chosen == [] and unknown == typed)
    chosen, unknown = walk.resolve(fence, ["pkg/ok.py::f"])
    check("and still resolves the path beside it",
          [u["name"] for u in chosen] == ["pkg/ok.py::f"] and unknown == [])
    check("symbols.of opens no fenced file, even when handed one",
          symbols.of(fence, "phi/y.py")["defines"] == []
          and symbols.of(fence, "stage1/run.py")["defines"] == []
          and symbols.of(fence, "pkg/ok.py")["defines"] != []
          and symbols.exact(fence, "raw/x.py") is False)
finally:
    walk._cache.clear()
    shutil.rmtree(fence, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a walkthrough is held over machinery that exists, and a stance is a sitting's")
