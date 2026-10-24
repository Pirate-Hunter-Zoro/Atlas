#!/usr/bin/env python3
"""Subjects: every directory under courses/ or projects/, with no registry.

A fixture tree, never the real one: `all`, `find` (a qualified id under a
merged-away parent finds nothing), `kind_of`, `identify`, `roots`, `root`,
`read_config` and lookups by slug (a project by its bare name). atlas.py is
gone. On the real tree, a subject holding a toolchain marker (mise.toml,
Cargo.toml, pubspec.yaml, build.zig.zon, at its root or one directory down;
pyproject.toml, lean-toolchain or go.mod at its root) names its check, and
keeps the marker's lockfile beside it; build.zig.zon is its own lockfile, and
a pyproject.toml has a uv.lock.
"""

import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.pop("TUTORBOARD_COURSES", None)

from tutorboard import subjects  # noqa: E402
from tutorboard.course import config                         # noqa: E402

fails = []


def check(name, ok):
    print("%s %s" % ("ok  " if ok else "FAIL", name))
    if not ok:
        fails.append(name)


def mk(base, rel, cfg=None):
    where = os.path.join(base, rel)
    os.makedirs(where, exist_ok=True)
    if cfg is not None:
        with open(os.path.join(where, "tutorboard.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(cfg, fh)
    return where


# --- root -------------------------------------------------------------------
check("root() is the parent of board/",
      subjects.root() == os.path.dirname(os.path.realpath(ROOT)))
check("there is no atlas.json, and the subjects' parents come from code",
      not os.path.exists(os.path.join(subjects.root(), "atlas.json"))
      and [d for d, _ in subjects.DIRS] == ["courses", "projects"])
check("and atlas.py is gone",
      not os.path.exists(os.path.join(ROOT, "tutorboard", "atlas.py")))

tmp = os.path.realpath(tempfile.mkdtemp(prefix="subjects-"))
try:
    topo = mk(tmp, "courses/Topology", {"name": "Algebraic Topology"})
    mk(tmp, "courses/.trash")
    psych = mk(tmp, "projects/PSYCH-ASR", {"name": "PSYCH-ASR", "phi": True})
    mk(tmp, "projects/X")
    mk(tmp, "projects/libr-local-llm", {"name": "libr-local-llm"})
    mk(tmp, "projects/Paper-Writer", {"name": "Paper-Writer"})
    mk(tmp, "projects/Arena-Lab")
    # Residue left at the legacy parents on a machine that has not moved it.
    mk(tmp, "research/Leftover", {"name": "Leftover"})
    mk(tmp, "practice/Stale")
    mk(tmp, "vendor/colibri")
    with open(os.path.join(tmp, "projects", "notes.txt"), "w") as fh:
        fh.write("not a subject\n")

    os.environ["TUTORBOARD_COURSES"] = tmp
    check("TUTORBOARD_COURSES overrides root()", subjects.root() == tmp)

    # --- all ----------------------------------------------------------------
    got = subjects.all()
    ids = [s["id"] for s in got]
    check("all() lists every non-dot directory under the subject parents",
          ids == ["courses/Topology", "projects/Arena-Lab",
                  "projects/PSYCH-ASR", "projects/Paper-Writer", "projects/X",
                  "projects/libr-local-llm"])
    check("research/ and practice/ hold no subject: they merged into projects/",
          not any(i.startswith(("research/", "practice/")) for i in ids)
          and subjects.kind_of(os.path.join(tmp, "research", "Leftover")) == "")
    check("an empty projects/X is a subject, with no marker", "projects/X" in ids)
    check("each record is {id, kind, slug, name, root}",
          all(sorted(s) == ["id", "kind", "name", "root", "slug"] for s in got))
    kinds = dict((s["id"], s["kind"]) for s in got)
    check("courses/ holds courses; projects/ projects",
          kinds["courses/Topology"] == "course"
          and kinds["projects/X"] == "project"
          and kinds["projects/PSYCH-ASR"] == "project"
          and kinds["projects/Arena-Lab"] == "project")
    names = dict((s["id"], s["name"]) for s in got)
    check("name comes from tutorboard.json, else the slug",
          names["courses/Topology"] == "Algebraic Topology"
          and names["projects/Arena-Lab"] == "Arena Lab")
    check("vendor/ and dot directories are not subjects",
          not any("colibri" in i or ".trash" in i for i in ids))

    # --- the catch-all ------------------------------------------------------
    check("with no courses/Random, scratch() is None", subjects.scratch() is None)
    mk(tmp, "courses/Random", {"name": "Random lessons", "phi": False})
    check("scratch() names courses/Random once it exists",
          subjects.SCRATCH == "courses/Random" and subjects.scratch() == "courses/Random"
          and subjects.find(subjects.scratch())["name"] == "Random lessons")
    shutil.rmtree(os.path.join(tmp, "courses", "Random"))

    # --- find ---------------------------------------------------------------
    check("find by qualified id", subjects.find("courses/Topology")["root"] == topo)
    check("find by slug", subjects.find("Topology")["id"] == "courses/Topology")
    check("find by root", subjects.find(topo)["id"] == "courses/Topology")
    check("a miss is None", subjects.find("Nowhere") is None
          and subjects.find("") is None)
    check("a path is never built from the ident",
          subjects.find("courses/../projects/X") is None)
    check("kind_of a subject and a path inside one",
          subjects.kind_of(topo) == "course"
          and subjects.kind_of(os.path.join(psych, "src", "a.py")) == "project")
    check("kind_of a non-subject path is empty",
          subjects.kind_of(os.path.join(tmp, "vendor", "colibri")) == ""
          and subjects.kind_of(os.path.join(tmp, "courses")) == ""
          and subjects.kind_of("/") == "")

    # No fallback: an id under a merged-away parent is not a subject's id.
    check("find('research/PSYCH-ASR') returns nothing, though PSYCH-ASR exists",
          subjects.find("research/PSYCH-ASR") is None
          and subjects.find("practice/Arena-Lab") is None
          and subjects.find("PSYCH-ASR")["id"] == "projects/PSYCH-ASR")
    check("and residue under such a parent is never a subject",
          subjects.find("research/Leftover") is None
          and subjects.find("Leftover") is None)
    check("nor is a stray path ending in a subject's name",
          subjects.find(os.path.join(tmp, "elsewhere", "PSYCH-ASR")) is None
          and subjects.find("vendor/PSYCH-ASR") is None)

    # --- identify and roots ------------------------------------------------
    check("roots lists every subject's directory in walk order",
          subjects.roots() == [s["root"] for s in subjects.all()])
    check("identify reads the parent directory",
          subjects.identify(topo) == "courses/Topology"
          and subjects.identify(os.path.join(tmp, "vendor", "colibri")) == "colibri")
    check("identify still names a subject that is gone",
          subjects.identify(os.path.join(tmp, "courses", "Gone")) == "courses/Gone")

    # --- lookups by slug ----------------------------------------------------
    check("a project resolves by its bare slug",
          (subjects.find("Paper-Writer") or {}).get("root")
          == os.path.join(tmp, "projects", "Paper-Writer"))

    # --- read_config --------------------------------------------------------
    one = mk(tmp, "projects/Conf", {
        "name": "Conf", "phi": False, "check": "make test",
        "stance": "do", "aim": "build",
        "subtitle": "x", "mode": "code"})
    cfg = config.read_config(one)
    check("read_config returns name, phi and check",
          cfg["name"] == "Conf" and cfg["phi"] is False
          and cfg["check"] == {"all": ["bash", "-c", "make test"],
                               "line": "make test"}
          and "relay" not in cfg)
    check("and ignores stance, aim, subtitle and mode",
          not any(k in cfg for k in ("stance", "aim", "subtitle", "mode",
                                     "said_stance")))
    bare = config.read_config(mk(tmp, "projects/Bare-One"))
    check("absent phi is None, name from the directory",
          bare["phi"] is None
          and bare["name"] == "Bare One" and bare["check"] is None)
    check("phi stays literal: a string is not an answer",
          config.read_config(mk(tmp, "projects/Str", {"phi": "false"}))["phi"]
          is None)

    # --- create -------------------------------------------------------------
    import subprocess
    gen = os.path.join(tmp, "gen")
    os.makedirs(gen)
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    env.pop("TUTORBOARD_TURN", None)

    def git(*args):
        return subprocess.run(["git"] + list(args), cwd=gen, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True)
    git("init", "-q")
    git("commit", "-q", "--allow-empty", "-m", "fixture")
    mk(gen, "projects/Old")
    os.environ.update({k: env[k] for k in env if k.startswith("GIT_")})
    check("slugify keeps case and makes one dash of every other run",
          subjects.slugify("Algebraic  Topology: I") == "Algebraic-Topology-I"
          and subjects.slugify("../x") == "x")

    def refused(ident, phi=None):
        try:
            subjects.create(ident, phi=phi, base=gen)
        except subjects.Refused as exc:
            return str(exc)
        return ""
    for bad in ("../x", "/abs", "research/x", "practice/x", "courses/a/b",
                "courses/..", "courses/", "~/x", "courses/!!!", "projects/Old"):
        check("create refuses %r" % bad, bool(refused(bad, phi=False)))
    check("a project with no phi answer is refused, asking it",
          "patient data" in refused("projects/P"))
    check("a course is never phi true", bool(refused("courses/C", phi=True)))
    check("and none of the refusals made a directory or a commit",
          sorted(os.listdir(gen)) == [".git", "projects"]
          and git("rev-list", "--count", "HEAD").stdout.strip() == "1")
    rec, ok, said = subjects.create("courses/Point Set Topology", base=gen)
    check("create makes the slug's directory and returns its record",
          ok and rec["id"] == "courses/Point-Set-Topology"
          and rec["name"] == "Point Set Topology" and rec["kind"] == "course")
    check("in one commit", git("rev-list", "--count", "HEAD").stdout.strip() == "2"
          and git("status", "--porcelain").stdout == "")
    check("and the new subject is listed",
          "courses/Point-Set-Topology" in [s["id"] for s in subjects.all(gen)])
    rec, ok, said = subjects.create("projects/Clinic", phi=True, base=gen)
    ign = open(os.path.join(gen, "projects", "Clinic", ".gitignore")).read()
    check("a patient-data project carries the PHI ignore stanza",
          ok and ign.split() == ["/phi/", "/results/", ".env"]
          and git("check-ignore", "-q", "projects/Clinic/phi/x").returncode == 0)
    rec, ok, said = subjects.create("projects/Open", phi=False, base=gen)
    check("a project with phi false has no stanza and says false",
          ok and not os.path.exists(os.path.join(gen, "projects", "Open", ".gitignore"))
          and config.read_config(rec["root"])["phi"] is False)
    check("a slug is one subject, whatever its case or parent",
          bool(refused("courses/open", phi=False)))
finally:
    os.environ.pop("TUTORBOARD_COURSES", None)
    shutil.rmtree(tmp, ignore_errors=True)

# --- the real tree ------------------------------------------------------------
real = subjects.root()
listed = set()
for parent, _kind in subjects.DIRS:
    try:
        for n in os.listdir(os.path.join(real, parent)):
            if not n.startswith(".") and os.path.isdir(os.path.join(real, parent, n)):
                listed.add("%s/%s" % (parent, n))
    except OSError:
        pass
check("on this tree, all() is exactly the directories under the subject parents",
      set(s["id"] for s in subjects.all()) == listed)

# The catch-all is a course on this tree, named for what it is, and its name
# does not collide with the board's uploads drawer (Scratch). A tree with no
# subjects at all (test/independence.py) has no catch-all to check.
if listed:
    _scratch = subjects.find(subjects.SCRATCH)
    check("this tree's catch-all is courses/Random, \"Random lessons\", a course with "
          "phi false",
          subjects.scratch() == subjects.SCRATCH and _scratch
          and _scratch["name"] == "Random lessons" and _scratch["kind"] == "course"
          and subjects.phi(_scratch["root"]) is False)
check("and its name is not Scratch",
      subjects.SCRATCH.split("/")[1].lower() != "scratch")

# --- markers: a pinned toolchain has its lockfile and its check ---------------
from tutorboard import toolplan                               # noqa: E402
box = os.path.realpath(tempfile.mkdtemp(prefix="markers-"))
try:
    mk(box, "projects/R/app")
    for rel in ("projects/R/mise.toml", "projects/R/app/Cargo.toml",
                "projects/R/target/Cargo.toml", "projects/R/.hidden/Cargo.toml",
                "projects/R/node_modules/x/Cargo.toml", "projects/R/a/b/Cargo.toml",
                "projects/R/ui/pubspec.yaml", "projects/R/build/pubspec.yaml",
                "projects/R/warden/build.zig.zon", "projects/R/zig-out/build.zig.zon",
                "projects/R/zig-pkg/build.zig.zon", "projects/R/.zig-cache/build.zig.zon"):
        os.makedirs(os.path.dirname(os.path.join(box, rel)), exist_ok=True)
        open(os.path.join(box, rel), "w").close()
    found = toolplan.markers(os.path.join(box, "projects", "R"))
    got = [(m, os.path.relpath(d, box)) for m, _l, d in found]
    check("markers count at the root and one directory down, never in target/, "
          "build/, node_modules/, zig-out/, zig-pkg/ or a dot directory",
          got == [("mise.toml", "projects/R"), ("Cargo.toml", "projects/R/app"),
                  ("pubspec.yaml", "projects/R/ui"), ("build.zig.zon", "projects/R/warden")])
    check("warden/build.zig.zon is a marker and its own lockfile, so the rule that "
          "a lockfile sits beside it holds",
          [(m, l) for m, l, d in found if m == "build.zig.zon"]
          == [("build.zig.zon", "build.zig.zon")])
finally:
    shutil.rmtree(box, ignore_errors=True)
# The root-only markers: a pyproject.toml, a lean-toolchain or a go.mod.
ROOT_MARKERS = ("pyproject.toml", "lean-toolchain", "go.mod")
for subject in subjects.all():
    found = toolplan.markers(subject["root"])
    at_root = [m for m in ROOT_MARKERS
               if os.path.isfile(os.path.join(subject["root"], m))]
    if "pyproject.toml" in at_root:
        check("%s: its pyproject.toml has a uv.lock beside it" % subject["id"],
              os.path.isfile(os.path.join(subject["root"], "uv.lock")))
    if not found and not at_root:
        continue
    try:
        with open(os.path.join(subject["root"], "tutorboard.json"), encoding="utf-8") as fh:
            named = json.load(fh).get("check")
    except (OSError, ValueError):
        named = None
    check("%s: it holds %s, and its tutorboard.json names its check"
          % (subject["id"], (found[0][0] if found else at_root[0])), bool(named))
    for marker, lock, where in found:
        check("%s: %s has %s beside it" % (
            subject["id"], os.path.relpath(os.path.join(where, marker), subject["root"]),
            lock), os.path.isfile(os.path.join(where, lock)))

print()
print("%d FAILURES" % len(fails) if fails
      else "a subject is a directory under courses/ or projects/, and nothing registers one")
sys.exit(1 if fails else 0)
