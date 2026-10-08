#!/usr/bin/env python3
"""Subjects: every directory under courses/ or projects/, with no registry.

A fixture tree, never the real one: `all`, `find` (with the fallback from a
moved qualified id to its slug), `kind_of`, `root`, `read_config`, the
`atlas` shims and the two lookups by slug (`colibri.WORKSPACE`,
`manuscript.WRITER`).
"""

import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.pop("TUTORBOARD_COURSES", None)

from tutorboard import atlas, colibri, manuscript, subjects  # noqa: E402
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

tmp = os.path.realpath(tempfile.mkdtemp(prefix="subjects-"))
try:
    with open(os.path.join(tmp, "atlas.json"), "w", encoding="utf-8") as fh:
        json.dump({"families": [
            {"id": "courses", "name": "Courses"},
            {"id": "research", "name": "Research"},
            {"id": "projects", "name": "Projects"},
            {"id": "practice", "name": "Practice"},
            {"id": "vendor", "name": "Vendor", "vendor": True},
        ]}, fh)
    topo = mk(tmp, "courses/Topology", {"name": "Algebraic Topology"})
    mk(tmp, "courses/.trash")
    psych = mk(tmp, "research/PSYCH-ASR", {"name": "PSYCH-ASR", "phi": True})
    mk(tmp, "projects/X")
    mk(tmp, "projects/libr-local-llm", {"name": "libr-local-llm"})
    mk(tmp, "projects/Paper-Writer", {"name": "Paper-Writer"})
    mk(tmp, "practice/Algo-Solutions")
    mk(tmp, "vendor/colibri")
    with open(os.path.join(tmp, "projects", "notes.txt"), "w") as fh:
        fh.write("not a subject\n")

    os.environ["TUTORBOARD_COURSES"] = tmp
    atlas.forget()
    check("TUTORBOARD_COURSES overrides root()", subjects.root() == tmp)

    # --- all ----------------------------------------------------------------
    got = subjects.all()
    ids = [s["id"] for s in got]
    check("all() lists every non-dot directory under the subject parents",
          ids == ["courses/Topology", "research/PSYCH-ASR",
                  "projects/Paper-Writer", "projects/X",
                  "projects/libr-local-llm", "practice/Algo-Solutions"])
    check("an empty projects/X is a subject, with no marker", "projects/X" in ids)
    check("each record is {id, kind, slug, name, root}",
          all(sorted(s) == ["id", "kind", "name", "root", "slug"] for s in got))
    kinds = dict((s["id"], s["kind"]) for s in got)
    check("courses/ holds courses; projects/, research/ and practice/ projects",
          kinds["courses/Topology"] == "course"
          and kinds["projects/X"] == "project"
          and kinds["research/PSYCH-ASR"] == "project"
          and kinds["practice/Algo-Solutions"] == "project")
    names = dict((s["id"], s["name"]) for s in got)
    check("name comes from tutorboard.json, else the slug",
          names["courses/Topology"] == "Algebraic Topology"
          and names["practice/Algo-Solutions"] == "Algo Solutions")
    check("vendor/ and dot directories are not subjects",
          not any("colibri" in i or ".trash" in i for i in ids))

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

    # The fallback: research/PSYCH-ASR moves to projects/PSYCH-ASR.
    moved = os.path.join(tmp, "projects", "PSYCH-ASR")
    shutil.move(psych, moved)
    hit = subjects.find("research/PSYCH-ASR")
    check("a moved qualified id resolves the new subject by its slug",
          hit is not None and hit["id"] == "projects/PSYCH-ASR"
          and hit["root"] == moved)
    check("and through the atlas shim too",
          (atlas.find("research/PSYCH-ASR") or {}).get("id") == "projects/PSYCH-ASR")
    check("the fallback is only for a qualified id, not a stray path",
          subjects.find(os.path.join(tmp, "elsewhere", "PSYCH-ASR")) is None
          and subjects.find("vendor/PSYCH-ASR") is None)

    # --- the atlas shims ----------------------------------------------------
    ws = atlas.workspaces()
    check("atlas.workspaces keeps its record shape",
          all(sorted(w) == ["dir", "family", "family_name", "id", "root"]
              for w in ws))
    check("and lists the same subjects in atlas.json family order",
          [w["id"] for w in ws] == [s["id"] for s in subjects.all()])
    check("family and family_name come from the parent and atlas.json",
          ws[0]["family"] == "courses" and ws[0]["family_name"] == "Courses"
          and ws[0]["dir"] == "Topology")
    check("atlas.find by bare directory name",
          atlas.find("libr-local-llm")["id"] == "projects/libr-local-llm")
    check("atlas.family_of and identify read the parent directory",
          atlas.family_of(topo) == "courses"
          and atlas.identify(topo) == "courses/Topology"
          and atlas.identify(os.path.join(tmp, "vendor", "colibri")) == "colibri")
    check("identify still names a subject that is gone",
          atlas.identify(os.path.join(tmp, "courses", "Gone")) == "courses/Gone")

    # A flat tree (no atlas.json) still reads as bin/tutor's courses_dir did.
    flat = os.path.realpath(tempfile.mkdtemp(prefix="subjects-flat-"))
    try:
        mk(flat, "Galois-Theory", {"name": "Galois Theory"})
        mk(flat, "scratch")
        check("a flat tree lists its marked directories by bare name",
              [w["id"] for w in atlas.workspaces(flat)] == ["Galois-Theory"]
              and atlas.find("Galois-Theory", flat)["dir"] == "Galois-Theory")
    finally:
        shutil.rmtree(flat, ignore_errors=True)

    # --- lookups by slug ----------------------------------------------------
    for key in ("COLI_QUEUE_ROOT", "LLM_REPO", "COLI_LOG_DIR"):
        os.environ.pop(key, None)
    llm = os.path.join(tmp, "projects", "libr-local-llm")
    check("colibri.WORKSPACE resolves by slug",
          colibri.queue_root() == llm
          and colibri.log_dir() == os.path.join(llm, "slurm_jobs", "logs"))
    check("manuscript.WRITER resolves by slug",
          manuscript.writer_root() == os.path.join(tmp, "projects", "Paper-Writer"))

    # --- read_config --------------------------------------------------------
    one = mk(tmp, "projects/Conf", {
        "name": "Conf", "phi": False, "check": "make test",
        "relay": {"colibri": True}, "stance": "do", "aim": "build",
        "subtitle": "x", "mode": "code"})
    cfg = config.read_config(one)
    check("read_config returns name, phi, check and relay",
          cfg["name"] == "Conf" and cfg["phi"] is False
          and cfg["check"] == {"all": ["bash", "-c", "make test"],
                               "line": "make test"}
          and cfg["relay"] == {"colibri": True})
    check("and ignores stance, aim, subtitle and mode",
          not any(k in cfg for k in ("stance", "aim", "subtitle", "mode",
                                     "said_stance")))
    bare = config.read_config(mk(tmp, "projects/Bare-One"))
    check("absent phi is None, absent relay is {}, name from the directory",
          bare["phi"] is None and bare["relay"] == {}
          and bare["name"] == "Bare One" and bare["check"] is None)
    check("phi stays literal: a string is not an answer",
          config.read_config(mk(tmp, "projects/Str", {"phi": "false"}))["phi"]
          is None)
finally:
    os.environ.pop("TUTORBOARD_COURSES", None)
    atlas.forget()
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
check("and atlas.workspaces() names the same subjects",
      [w["id"] for w in atlas.workspaces()] == [s["id"] for s in subjects.all()])

print()
print("%d FAILURES" % len(fails) if fails
      else "a subject is a directory under courses/ or projects/, and nothing registers one")
sys.exit(1 if fails else 0)
