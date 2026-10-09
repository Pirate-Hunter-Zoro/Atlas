#!/usr/bin/env python3
"""The relay path parses, and runs, on the cluster's python3, which may be 3.7.

The relay path is board/bin/relay, board/bin/board (for its `code`
subcommand), the modules relay, jobs, colibri, exports, cluster, code, fenced,
leaving, paths, worktree, gitops and audit, and every tutorboard module they
import, followed to the end. A module named here that does not exist yet is
skipped.

Each file must parse with `ast.parse(src, feature_version=(3, 7))`, which
refuses the walrus, `match` and the newer grammar. Then the ast is searched
for what 3.7 parses but cannot run:

  * `.removeprefix` and `.removesuffix` (3.9);
  * `functools.cache` (3.9), by attribute or by `from functools import`;
  * `|` or `|=` with a dict literal on either side (3.9);
  * a builtin subscripted, `list[str]` and the like (3.9), unless the file
    has `from __future__ import annotations` and the subscript sits in an
    annotation.

Stdlib only.
"""

import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "tutorboard")

ENTRIES = [os.path.join(ROOT, "bin", "relay"), os.path.join(ROOT, "bin", "board")]
MODULES = ["relay", "jobs", "colibri", "exports", "cluster", "code", "fenced",
           "leaving", "paths", "worktree", "gitops", "audit"]
BUILTINS = ("list", "dict", "tuple", "set", "frozenset", "type")

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def module_file(dotted):
    """The file of `tutorboard.<dotted>`, or None."""
    base = os.path.join(PKG, *dotted.split("."))
    for cand in (base + ".py", os.path.join(base, "__init__.py")):
        if os.path.isfile(cand):
            return cand
    return None


def dotted_of(path):
    rel = os.path.relpath(path, PKG)[:-len(".py")].replace(os.sep, ".")
    return rel[:-len(".__init__")] if rel.endswith(".__init__") else rel


def imported(path, tree):
    """The tutorboard modules `tree` imports, as dotted names under it."""
    if path.startswith(PKG + os.sep):
        here = dotted_of(path).split(".")
        if not path.endswith("__init__.py"):
            here = here[:-1]
    else:
        here = None                      # an entry: only absolute imports count
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("tutorboard."):
                    out.add(a.name[len("tutorboard."):])
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                if here is None:
                    continue
                parent = here[:len(here) - (node.level - 1)] if node.level > 1 \
                    else list(here)
                stem = parent + (node.module.split(".") if node.module else [])
            elif node.module == "tutorboard":
                stem = []
            elif (node.module or "").startswith("tutorboard."):
                stem = node.module[len("tutorboard."):].split(".")
            else:
                continue
            if stem:
                out.add(".".join(stem))
            for a in node.names:
                out.add(".".join(stem + [a.name]))
    # Every package on the way down is imported too.
    for name in list(out):
        parts = name.split(".")
        for i in range(1, len(parts)):
            out.add(".".join(parts[:i]))
    return set(n for n in out if module_file(n))


def problems(path, src):
    """What in this file 3.7 cannot parse or run, as strings."""
    try:
        tree = ast.parse(src, filename=path, feature_version=(3, 7))
    except SyntaxError as exc:
        return ["line %s: %s" % (exc.lineno, exc.msg)], None
    future = any(isinstance(n, ast.ImportFrom) and n.module == "__future__"
                 and any(a.name == "annotations" for a in n.names)
                 for n in tree.body)
    annotations = set()
    if future:
        for node in ast.walk(tree):
            for ann in _annotations(node):
                annotations.update(id(n) for n in ast.walk(ann))
    out = []
    for node in ast.walk(tree):
        line = getattr(node, "lineno", "?")
        if isinstance(node, ast.Attribute):
            if node.attr in ("removeprefix", "removesuffix"):
                out.append("line %s: .%s is 3.9" % (line, node.attr))
            if (node.attr == "cache" and isinstance(node.value, ast.Name)
                    and node.value.id == "functools"):
                out.append("line %s: functools.cache is 3.9" % line)
        elif isinstance(node, ast.ImportFrom) and node.module == "functools":
            if any(a.name == "cache" for a in node.names):
                out.append("line %s: functools.cache is 3.9" % line)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            if isinstance(node.left, ast.Dict) or isinstance(node.right, ast.Dict):
                out.append("line %s: dict | dict is 3.9" % line)
        elif isinstance(node, ast.AugAssign) and isinstance(node.op, ast.BitOr):
            if isinstance(node.value, ast.Dict):
                out.append("line %s: dict |= dict is 3.9" % line)
        elif isinstance(node, ast.Subscript):
            if (isinstance(node.value, ast.Name) and node.value.id in BUILTINS
                    and id(node) not in annotations):
                out.append("line %s: %s[...] is 3.9" % (line, node.value.id))
    return out, tree


def _annotations(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.returns is not None:
            yield node.returns
        a = node.args
        for arg in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg]:
            if arg is not None and arg.annotation is not None:
                yield arg.annotation
    elif isinstance(node, ast.AnnAssign):
        yield node.annotation


def walk():
    """`{path: problems}` over the whole relay path."""
    todo = list(ENTRIES)
    for name in MODULES:
        found = module_file(name)
        if found:
            todo.append(found)
    seen, said = set(), {}
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        bad, tree = problems(path, src)
        said[path] = bad
        if tree is not None:
            todo.extend(module_file(n) for n in imported(path, tree))
    return said


# --- the check itself, on cases it must catch ---------------------------------
CASES = {
    "walrus": "if (n := 3):\n    pass\n",
    "match": "match x:\n    case 1:\n        pass\n",
    "removeprefix": "s = 'ab'.removeprefix('a')\n",
    "removesuffix": "s = name.removesuffix('.py')\n",
    "functools.cache": "import functools\n@functools.cache\ndef f():\n    pass\n",
    "from functools import cache": "from functools import cache\n",
    "dict | dict": "x = {'a': 1} | other\n",
    "dict |= dict": "x |= {'a': 1}\n",
    "list[str]": "def f(x: list[str]):\n    pass\n",
    "positional-only": "def f(a, /):\n    pass\n",
}
for name, src in sorted(CASES.items()):
    check("the check refuses %s" % name, problems("<case>", src)[0] != [])
check("and passes what 3.7 runs",
      problems("<case>", "import typing\nx = {**a, **b}\n"
               "def f(x: typing.List[str]) -> None:\n    return x\n")[0] == [])
check("a deferred annotation may name list[str]",
      problems("<case>", "from __future__ import annotations\n"
               "def f(x: list[str]) -> dict[str, int]:\n    pass\n")[0] == [])

# --- the relay path ------------------------------------------------------------
said = walk()
names = set(os.path.relpath(p, ROOT) for p in said)
check("the walk reaches the entries and the relay modules",
      {"bin/relay", "bin/board", "tutorboard/relay.py", "tutorboard/jobs.py",
       "tutorboard/colibri.py", "tutorboard/fenced.py", "tutorboard/leaving.py",
       "tutorboard/paths.py", "tutorboard/worktree.py",
       "tutorboard/code.py", "tutorboard/gitops.py", "tutorboard/audit.py"}
      <= names)
check("and follows their imports (relay imports atlas, which imports subjects)",
      {"tutorboard/atlas.py", "tutorboard/subjects.py"} <= names)
for path in sorted(said):
    rel = os.path.relpath(path, ROOT)
    check("%s runs on 3.7%s" % (rel, "" if not said[path] else
                                ": " + "; ".join(said[path][:5])),
          not said[path])

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("%d relay-path files parse and run on python 3.7" % len(said))
