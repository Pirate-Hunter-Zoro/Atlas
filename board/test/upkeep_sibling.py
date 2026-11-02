#!/usr/bin/env python3
"""upkeep/ is one system both repos carry: Media-Orchestrator's copy, when it is cloned
beside Atlas at ~/Developer/Media-Orchestrator, is Atlas's byte for byte, or carries a
lower VERSION (it has not pulled the newer copy yet, and upkeep runs the highest VERSION
it finds). Media-Orchestrator's suite checks the same from its side
(Torrent-Ingest/scripts/test_upkeep_sibling.py).

    python3 test/upkeep_sibling.py

Both ways, on fixture trees: identical trees, a lower sibling and no sibling pass; a byte,
an exec bit or an extra file under one VERSION fails, and so does a higher sibling;
caches (__pycache__, .pyc, .DS_Store) are not upkeep. UPKEEP_SIBLING names another
sibling checkout. Read-only. Stdlib only.
"""

import os
import shutil
import stat
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATLAS = os.path.dirname(os.path.dirname(HERE))
SIBLING_NAME = "Media-Orchestrator"
IGNORED = ("__pycache__", ".DS_Store")

fails = []


def check(name, cond, detail=""):
    if cond:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s%s" % (name, ("\n        " + detail) if detail else ""))
        fails.append(name)


def version_of(upkeep):
    try:
        with open(os.path.join(upkeep, "VERSION")) as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return 0


def tree(upkeep):
    """{relative path: (bytes, executable)} for every file but caches."""
    out = {}
    for root, dirs, files in os.walk(upkeep):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED)
        for name in files:
            if name in IGNORED or name.endswith(".pyc"):
                continue
            path = os.path.join(root, name)
            with open(path, "rb") as fh:
                body = fh.read()
            out[os.path.relpath(path, upkeep)] = (
                body, bool(os.stat(path).st_mode & stat.S_IXUSR))
    return out


def compare(mine, sibling):
    """(fine, why) for this repo's upkeep/ against a sibling checkout's."""
    if not os.path.isdir(sibling):
        return True, "no %s" % sibling
    name = os.path.basename(sibling.rstrip("/"))
    have = version_of(os.path.join(mine, "upkeep"))
    theirs = version_of(os.path.join(sibling, "upkeep"))
    if theirs < have:
        return True, "%s carries VERSION %d, this repo %d" % (name, theirs, have)
    if theirs > have:
        return False, ("%s carries upkeep VERSION %d, this repo %d: copy %s/upkeep/ over "
                       "this repo's upkeep/" % (name, theirs, have, sibling))
    a = tree(os.path.join(mine, "upkeep"))
    b = tree(os.path.join(sibling, "upkeep"))
    diff = sorted(p for p in set(a) | set(b) if a.get(p) != b.get(p))
    if diff:
        return False, ("VERSION %d in both, but these differ: %s; make the copies equal "
                       "and bump VERSION" % (have, ", ".join(diff[:10])))
    return True, "VERSION %d, byte for byte" % have


def fixture(root, version, files, exe=()):
    files = dict(files, VERSION=version)
    for rel, text in files.items():
        path = os.path.join(root, "upkeep", rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(text)
        if rel in exe:
            os.chmod(path, 0o755)
    return root


def main():
    print("fixture trees")
    tmp = tempfile.mkdtemp(prefix="upkeep-sibling-")
    try:
        files = {"upkeep.py": "print('one')\n", "opencode/install.py": "x = 1\n"}
        mine = fixture(os.path.join(tmp, "mine"), "3\n", files, exe=("upkeep.py",))
        cases = [
            ("an identical sibling passes", files, "3\n", ("upkeep.py",), True),
            ("a byte that differs under one VERSION fails",
             dict(files, **{"opencode/install.py": "x = 2\n"}), "3\n", ("upkeep.py",), False),
            ("an exec bit that differs under one VERSION fails", files, "3\n", (), False),
            ("an extra file under one VERSION fails", dict(files, extra="e\n"), "3\n",
             ("upkeep.py",), False),
            ("a lower sibling passes, however it differs", {"upkeep.py": "old\n"}, "2\n",
             (), True),
            ("a higher sibling fails", files, "4\n", ("upkeep.py",), False),
        ]
        for n, (label, fs, version, exe, want) in enumerate(cases):
            ok, why = compare(mine, fixture(os.path.join(tmp, "sib%d" % n), version, fs,
                                            exe=exe))
            check("%s (%s)" % (label, why), ok == want)
        cache = fixture(os.path.join(tmp, "cache"), "3\n", files, exe=("upkeep.py",))
        os.makedirs(os.path.join(cache, "upkeep", "__pycache__"))
        for rel in ("__pycache__/upkeep.cpython-39.pyc", ".DS_Store"):
            with open(os.path.join(cache, "upkeep", rel), "wb") as fh:
                fh.write(b"\0")
        check("caches are not upkeep", compare(mine, cache)[0])
        check("no sibling passes", compare(mine, os.path.join(tmp, "absent"))[0])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("this repo and its sibling")
    check("this repo carries upkeep/ with a VERSION",
          version_of(os.path.join(ATLAS, "upkeep")) > 0)
    sibling = os.environ.get("UPKEEP_SIBLING") or os.path.join(
        os.path.expanduser("~"), "Developer", SIBLING_NAME)
    ok, why = compare(ATLAS, sibling)
    check("%s: %s" % (sibling, why), ok)

    if fails:
        print("\n%d check(s) failed" % len(fails))
        return 1
    print("\nupkeep_sibling: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
