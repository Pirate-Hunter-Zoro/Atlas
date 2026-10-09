#!/usr/bin/env python3
"""Existing documents become artifacts, and their ink follows them.

    migrate-artifacts.py --plan        [--atlas ROOT]
    migrate-artifacts.py --apply-tree  [--atlas ROOT] [--map PATH]
    migrate-artifacts.py --apply-ink   ROOT [--map PATH]
    migrate-artifacts.py --rebuild     ROOT [--map PATH]

--plan        Print every tree move, every doc.json written, every file
              untracked and every ink key renamed (old library id to new).
              Changes nothing.
--apply-tree  `git mv` each MOVES directory to `docs/<slug>/` with a doc.json,
              write doc.json in place for each PLACES tree and every course
              homework set, untrack LaTeX scratch and built PDFs in moved
              directories, and write the key map. Stages; the caller commits.
--apply-ink   Rename the `.ink/` files (`.json`, `.png`, `.dir.png`, `.gone`)
              of every subject by the map's `ink` list, and rewrite the key
              each record carries. Ink is ignored, so it is run where the ink
              is: the cutover runs it in the main checkout after import.
--rebuild     `board build` every course document with a `.tex` source, and
              every source the map lists, and assert a PDF beside each.

ROOT defaults to the checkout this script sits in. The map defaults to
`board/scripts/artifact-moves.json` beside this script.

New ids are computed, never guessed: the library's own listing is run on a
skeleton of each subject (symlinks to every document file), once as it is and
once with the moves applied, and documents are paired by their source path.
"""

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

BOARD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BOARD)

from tutorboard import artifacts, build, fenced, sessions   # noqa: E402
from tutorboard.course import homework, library    # noqa: E402
from tutorboard.server.routes import writing                # noqa: E402

ATLAS = os.path.dirname(BOARD)
MAP = os.path.join(BOARD, "scripts", "artifact-moves.json")

# Directories that move to `docs/<slug>/`, by subject and glob.
MOVES = [
    ("projects/TRD-EHR", "homework/*"),
    ("projects/TRD-EHR", "writeups/deck-*"),
]

# Hand-made trees that get a doc.json in place: subject, directory, source,
# and a title where the source's own first heading is not one. One doc.json
# per directory, so the principal document is named; the others in the tree
# stay legacy documents with their ids.
PLACES = [
    ("projects/PSYCH-ASR", "docs", "stage1_pipeline_walkthrough.tex", None),
    ("projects/libr-local-llm", "docs", "fleet_walkthrough.tex", None),
    ("projects/TRD-EHR", "paper1-trd-prediction", "manuscript.md",
     "Feature Vectors and Narrative Embeddings for Predicting a Treatment "
     "Switching Proxy for Treatment Resistant Depression"),
    ("projects/TRD-EHR", "paper2-counterfactual", "PAPER2_OUTLINE.md",
     "Paper 2 outline: counterfactual antidepressant selection from EHR"),
]

COURSES = "courses"

# What a build leaves that is not a document: untracked in a moved directory.
SCRATCH = tuple(build.SCRATCH)

# What the skeleton mirrors: the files the library and artifacts read.
MIRRORED = ("doc.json", "_brief.json", "_brief.md")


def say(*a):
    print(*a)
    sys.stdout.flush()


def git(root, *args):
    p = subprocess.run(["git"] + list(args), cwd=root, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    return p.returncode, p.stdout.strip()


def tracked(root, rel):
    code, out = git(root, "ls-files", "--", rel)
    return [l for l in out.splitlines() if l.strip()] if code == 0 else []


# ---------------------------------------------------------------------------
# the plan
# ---------------------------------------------------------------------------
def _sources(d):
    return sorted(n for n in os.listdir(d)
                  if os.path.splitext(n)[1].lower() in artifacts.EXTS
                  and os.path.isfile(os.path.join(d, n)))


def _main_source(d):
    """The source named after its directory, else the only one, else ""."""
    found = _sources(d)
    base = os.path.basename(d.rstrip("/"))
    named = [n for n in found if os.path.splitext(n)[0] == base]
    if named:
        return named[0]
    return found[0] if len(found) == 1 else ""


def _title(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    return library._from_source(path, stem)[0]


def plan(atlas):
    """Everything --apply-tree would do, as data. Reads only."""
    out = {"moves": [], "placed": [], "untracked": [], "problems": []}
    import glob
    for subject, pattern in MOVES:
        root = os.path.join(atlas, subject)
        if not os.path.isdir(root):
            continue
        for d in sorted(glob.glob(os.path.join(root, pattern))):
            if not os.path.isdir(d) or fenced.refused(d):
                continue
            rel = os.path.relpath(d, root).replace(os.sep, "/")
            src = _main_source(d)
            if not src:
                out["problems"].append("%s/%s: no one source to name" % (subject, rel))
                continue
            slug = artifacts.slugify(os.path.basename(d))
            dest = "%s/%s" % (artifacts.DOCS, slug)
            if os.path.exists(os.path.join(root, dest)):
                out["problems"].append("%s/%s: %s is taken" % (subject, rel, dest))
                continue
            stems = set(os.path.splitext(n)[0] for n in _sources(d))
            gone = []
            for t in tracked(root, rel):
                name = os.path.basename(t)
                stem, ext = os.path.splitext(name)
                if name.endswith(SCRATCH) or (ext.lower() == ".pdf" and stem in stems):
                    gone.append(t)
            out["moves"].append({"subject": subject, "from": rel, "to": dest,
                                 "source": src,
                                 "title": _title(os.path.join(d, src))})
            out["untracked"] += [{"subject": subject, "path": t} for t in gone]
    for subject, rel, src, title in PLACES:
        d = os.path.join(atlas, subject, rel)
        if not os.path.isfile(os.path.join(d, src)):
            continue
        out["placed"].append({"subject": subject, "dir": rel, "source": src,
                              "title": title or _title(os.path.join(d, src))})
    top = os.path.join(atlas, COURSES)
    for name in sorted(os.listdir(top)) if os.path.isdir(top) else []:
        root = os.path.join(top, name)
        if not os.path.isdir(root) or name.startswith("."):
            continue
        seen = {}
        for s in homework.sets(root):
            rel = os.path.relpath(s["dir"], root).replace(os.sep, "/")
            src = os.path.basename(s["tex"])
            best = seen.get(rel)
            # One doc.json per directory: the set named after it wins.
            if best and os.path.splitext(best["source"])[0] == os.path.basename(rel):
                continue
            seen[rel] = {"subject": "%s/%s" % (COURSES, name), "dir": rel,
                         "source": src, "title": s["title"]}
        out["placed"] += [seen[k] for k in sorted(seen)]
    return out


# ---------------------------------------------------------------------------
# ids, from the library's own listing on a skeleton
# ---------------------------------------------------------------------------
def _skeleton(root, dest):
    """Mirror the document files of `root` into `dest` as symlinks, pruned the
    way the library and the artifact walk prune. Fenced names are never entered."""
    for here, dirs, files in os.walk(root):
        rel = os.path.relpath(here, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        dirs[:] = [x for x in dirs if not x.startswith(".")
                   and x not in library.IGNORE and not fenced.refused(x)]
        if depth > library.MAX_DEPTH:
            dirs[:] = []
            continue
        for n in files:
            ext = os.path.splitext(n)[1].lower()
            if ext not in library.FORMATS and n not in MIRRORED:
                continue
            src = os.path.join(here, n)
            if fenced.refused(src):
                continue
            to = os.path.join(dest, rel, n) if rel != "." else os.path.join(dest, n)
            os.makedirs(os.path.dirname(to), exist_ok=True)
            os.symlink(src, to)


def _listing(root):
    """`{path: id}`, path being the source (or the PDF) relative to `root`."""
    out = {}
    for group, ident, rel, stem, formats, art in library._listing(root):
        if art:
            path = art["path"]
        else:
            src, pdf = library._offered(formats, group == "material")
            path = src or pdf
        out[os.path.relpath(path, root).replace(os.sep, "/")] = ident
    return out


def _doc_json(d, source, title):
    with open(os.path.join(d, artifacts.DOC_JSON), "w", encoding="utf-8") as fh:
        json.dump({"title": title, "source": source, "sessions": [],
                   "asked_at": None}, fh, indent=2)
        fh.write("\n")


def ink_map(atlas, p):
    """`[{subject, from, to}]` for every document whose library id changes,
    and the documents the after-listing lost (`problems`)."""
    subjects = sorted(set([m["subject"] for m in p["moves"]]
                          + [x["subject"] for x in p["placed"]]))
    renames, lost = [], []
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="migrate-artifacts-"))
    try:
        for subject in subjects:
            real = os.path.join(atlas, subject)
            before = os.path.join(tmp, "before", subject)
            after = os.path.join(tmp, "after", subject)
            _skeleton(real, before)
            _skeleton(real, after)
            moves = [m for m in p["moves"] if m["subject"] == subject]
            for m in moves:
                to = os.path.join(after, m["to"])
                os.makedirs(os.path.dirname(to), exist_ok=True)
                os.rename(os.path.join(after, m["from"]), to)
                _doc_json(to, m["source"], m["title"])
            gone = [u["path"] for u in p["untracked"] if u["subject"] == subject]
            for rel in gone:
                for m in moves:
                    if rel == m["from"] or rel.startswith(m["from"] + "/"):
                        rel = m["to"] + rel[len(m["from"]):]
                try:
                    os.remove(os.path.join(after, rel))
                except OSError:
                    pass
            for x in p["placed"]:
                if x["subject"] == subject:
                    d = os.path.join(after, x["dir"])
                    if os.path.isdir(d):
                        _doc_json(d, x["source"], x["title"])
            old, new = _listing(before), _listing(after)
            for path, ident in sorted(old.items()):
                moved = path
                for m in moves:
                    if path.startswith(m["from"] + "/"):
                        moved = m["to"] + path[len(m["from"]):]
                if moved not in new and moved.endswith(".pdf"):
                    # A built PDF that was untracked: the source is the document.
                    stem = moved[:-4]
                    moved = next((stem + e for e in library.SOURCE
                                  if stem + e in new), moved)
                if moved not in new:
                    lost.append("%s: %s (%s) is no document after the move"
                                % (subject, path, ident))
                elif new[moved] != ident:
                    renames.append({"subject": subject, "from": ident,
                                    "to": new[moved], "path": moved})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return renames, lost


def full_plan(atlas):
    p = plan(atlas)
    renames, lost = ink_map(atlas, p)
    p["ink"] = renames
    p["problems"] += lost
    p["rebuild"] = sorted(
        "%s/%s/%s" % (m["subject"], m["to"], m["source"]) for m in p["moves"]
        if m["source"].endswith(".tex") and any(
            u["subject"] == m["subject"] and u["path"].lower().endswith(".pdf")
            and u["path"].startswith(m["from"] + "/") for u in p["untracked"]))
    return p


def show(p):
    for m in p["moves"]:
        say("move    %s/%s -> %s  (source %s)" % (m["subject"], m["from"], m["to"],
                                                 m["source"]))
    for u in p["untracked"]:
        say("untrack %s/%s" % (u["subject"], u["path"]))
    for x in p["placed"]:
        say("place   %s/%s/doc.json  (source %s)" % (x["subject"], x["dir"],
                                                    x["source"]))
    for r in p["ink"]:
        say("ink     %s: doc/%s/p* -> doc/%s/p*" % (r["subject"], r["from"], r["to"]))
    for r in p["rebuild"]:
        say("rebuild %s" % r)
    for x in p["problems"]:
        say("PROBLEM %s" % x)
    say("%d moves, %d untracked, %d doc.json, %d ink keys, %d problems"
        % (len(p["moves"]), len(p["untracked"]), len(p["placed"]), len(p["ink"]),
           len(p["problems"])))


# ---------------------------------------------------------------------------
# --apply-tree
# ---------------------------------------------------------------------------
KEY_REF = '"doc/%s/p'


def apply_tree(atlas, map_path):
    p = full_plan(atlas)
    show(p)
    if p["problems"]:
        say("refused: the plan has problems; nothing was changed")
        return 1
    for m in p["moves"]:
        root = os.path.join(atlas, m["subject"])
        code, out = git(root, "status", "--porcelain", "--", m["from"])
        if out:
            say("refused: %s/%s has uncommitted changes:\n%s"
                % (m["subject"], m["from"], out))
            return 1
    staged = []
    for m in p["moves"]:
        root = os.path.join(atlas, m["subject"])
        for u in p["untracked"]:
            if u["subject"] == m["subject"] and u["path"].startswith(m["from"] + "/"):
                code, out = git(root, "rm", "-q", "--cached", "--", u["path"])
                if code:
                    say("git rm --cached %s failed: %s" % (u["path"], out))
                    return 1
        os.makedirs(os.path.join(root, artifacts.DOCS), exist_ok=True)
        code, out = git(root, "mv", "--", m["from"], m["to"])
        if code:
            say("git mv %s %s failed: %s" % (m["from"], m["to"], out))
            return 1
        # What git did not carry (ignored or untracked) follows its document.
        left = os.path.join(root, m["from"])
        if os.path.isdir(left):
            for here, dirs, files in os.walk(left, topdown=False):
                for n in files:
                    src = os.path.join(here, n)
                    dst = os.path.join(root, m["to"], os.path.relpath(src, left))
                    if not os.path.exists(dst):
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.move(src, dst)
                try:
                    os.rmdir(here)
                except OSError:
                    pass
        parent = os.path.dirname(left)
        try:
            os.rmdir(parent)
        except OSError:
            pass
        d = os.path.join(root, m["to"])
        artifacts.place(d, m["source"], m["title"])
        staged.append(os.path.join(m["subject"], m["to"], artifacts.DOC_JSON))
    for x in p["placed"]:
        d = os.path.join(atlas, x["subject"], x["dir"])
        artifacts.place(d, x["source"], x["title"])
        staged.append(os.path.join(x["subject"], x["dir"], artifacts.DOC_JSON))
    # A tracked record naming a renamed key names the new one.
    for r in p["ink"]:
        root = os.path.join(atlas, r["subject"])
        code, out = git(root, "grep", "-l", "-F", KEY_REF % r["from"])
        for rel in out.splitlines() if code == 0 else []:
            path = os.path.join(root, rel)
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            fixed = re.sub(r'"doc/%s/p(\d+)"' % re.escape(r["from"]),
                           lambda mm: '"doc/%s/p%s"' % (r["to"], mm.group(1)), text)
            if fixed != text:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(fixed)
                staged.append(os.path.join(r["subject"], rel))
    rec = {"about": "Written by migrate-artifacts.py --apply-tree. `ink` maps "
                    "each document's old library id to its new one, per subject; "
                    "--apply-ink renames <subject>/.ink/ by it.",
           "moves": [{k: m[k] for k in ("subject", "from", "to", "source")}
                     for m in p["moves"]],
           "placed": [{k: x[k] for k in ("subject", "dir", "source")}
                      for x in p["placed"]],
           "untracked": ["%s/%s" % (u["subject"], u["path"]) for u in p["untracked"]],
           "ink": [{k: r[k] for k in ("subject", "from", "to")} for r in p["ink"]],
           "rebuild": p["rebuild"]}
    # A run with nothing left to move keeps the map the moving run wrote.
    if p["moves"] or not os.path.isfile(map_path):
        os.makedirs(os.path.dirname(os.path.abspath(map_path)), exist_ok=True)
        with open(map_path, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=2)
            fh.write("\n")
    # `-f`: a subject that ignores `*.json` (PSYCH-ASR, libr-local-llm) still
    # tracks the doc.json written here; it holds a title and a file name.
    code, out = git(atlas, "add", "-f", "--", *sorted(set(staged)))
    if code:
        say("git add failed: %s" % out)
        return 1
    rel_map = os.path.relpath(os.path.abspath(map_path), atlas)
    if not rel_map.startswith(".."):
        git(atlas, "add", "--", rel_map)
    # The library's own check: every document it listed before is listed after
    # under the id the map says.
    library.forget()
    for r in p["ink"]:
        root = os.path.join(atlas, r["subject"])
        if not library.find(root, r["to"]):
            say("after the move the library has no %s in %s" % (r["to"], r["subject"]))
            return 1
    say("staged; commit it")
    return 0


# ---------------------------------------------------------------------------
# --apply-ink
# ---------------------------------------------------------------------------
def _read_map(map_path):
    with open(map_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _strokes(folder):
    n = 0
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(folder, name), "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict):
            n += len(rec.get("strokes") or [])
    return n


def apply_ink(atlas, map_path):
    rec = _read_map(map_path)
    renames = rec.get("ink") or []
    status = 0
    for subject in sorted(set(r["subject"] for r in renames)):
        folder = os.path.join(atlas, subject, sessions.INK)
        if not os.path.isdir(folder):
            say("%s: no %s/, nothing to rename" % (subject, sessions.INK))
            continue
        before = _strokes(folder)
        pairs = []
        for r in renames:
            if r["subject"] != subject:
                continue
            for name, key, ext in sessions._ink_of(folder, r["from"]):
                page = writing.ann_doc_page(key)[1]
                new_key = "doc/%s/p%d" % (r["to"], page)
                pairs.append((name, writing.ann_file(new_key) + ext, new_key))
        sources = set(n for n, _, _ in pairs)
        clash = [d for _, d, _ in pairs
                 if os.path.exists(os.path.join(folder, d)) and d not in sources]
        if clash:
            say("%s: refused, these already exist: %s" % (subject, ", ".join(clash)))
            status = 1
            continue
        # Two steps, so a rename chain (a -> b while b -> c) never overwrites.
        stamp = ".migrating-%d-" % os.getpid()
        for name, _, _ in pairs:
            os.rename(os.path.join(folder, name), os.path.join(folder, stamp + name))
        for name, dest, key in pairs:
            src = os.path.join(folder, stamp + name)
            if dest.endswith((".json", ".gone")):
                with open(src, "r", encoding="utf-8") as fh:
                    try:
                        body = json.load(fh)
                    except ValueError:
                        body = None
                if isinstance(body, dict):
                    body["card"] = key
                    with open(src, "w", encoding="utf-8") as fh:
                        json.dump(body, fh)
            os.rename(src, os.path.join(folder, dest))
            say("%s: %s -> %s" % (subject, name, dest))
        after = _strokes(folder)
        say("%s: %d file(s) renamed; %d stroke(s) before, %d after"
            % (subject, len(pairs), before, after))
        if before != after:
            status = 1
    return status


# ---------------------------------------------------------------------------
# --rebuild
# ---------------------------------------------------------------------------
def rebuild_targets(atlas, map_path):
    out = []
    top = os.path.join(atlas, COURSES)
    for name in sorted(os.listdir(top)) if os.path.isdir(top) else []:
        root = os.path.join(top, name)
        if not os.path.isdir(root) or name.startswith("."):
            continue
        for group, ident, rel, stem, formats, art in library._listing(root):
            src = art["path"] if art else formats.get(".tex", "")
            if group != "material" and src.endswith(".tex") \
                    and build.document_class(src):
                out.append(os.path.abspath(src))
    if map_path and os.path.isfile(map_path):
        for rel in _read_map(map_path).get("rebuild") or []:
            path = os.path.join(atlas, rel)
            if os.path.isfile(path):
                out.append(os.path.abspath(path))
    return sorted(set(out))


def _one(src):
    started = time.time()
    got = build.build(src)
    pdf = os.path.splitext(src)[0] + ".pdf"
    ok = got["ok"] and os.path.isfile(pdf) and os.path.getmtime(pdf) >= started - 1
    return src, ok, got.get("detail") or ""


def rebuild(atlas, map_path, jobs=4):
    targets = rebuild_targets(atlas, map_path)
    bad = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        for src, ok, detail in pool.map(_one, targets):
            rel = os.path.relpath(src, atlas)
            if ok:
                say("built   %s" % rel)
            else:
                bad.append(rel)
                say("FAILED  %s\n%s" % (rel, detail[-800:]))
    say("%d built, %d failed" % (len(targets) - len(bad), len(bad)))
    return 1 if bad or not targets else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="migrate-artifacts.py",
                                 description=__doc__.split("\n\n")[0])
    how = ap.add_mutually_exclusive_group(required=True)
    how.add_argument("--plan", action="store_true")
    how.add_argument("--apply-tree", action="store_true")
    how.add_argument("--apply-ink", metavar="ROOT")
    how.add_argument("--rebuild", metavar="ROOT")
    ap.add_argument("--atlas", default=ATLAS, help="the Atlas root (default: this checkout)")
    ap.add_argument("--map", default=MAP, help="the key map (default: %(default)s)")
    args = ap.parse_args(argv)
    if args.plan:
        p = full_plan(os.path.realpath(args.atlas))
        show(p)
        return 1 if p["problems"] else 0
    if args.apply_tree:
        return apply_tree(os.path.realpath(args.atlas), args.map)
    if args.apply_ink:
        return apply_ink(os.path.realpath(args.apply_ink), args.map)
    return rebuild(os.path.realpath(args.rebuild), args.map)


if __name__ == "__main__":
    sys.exit(main())
