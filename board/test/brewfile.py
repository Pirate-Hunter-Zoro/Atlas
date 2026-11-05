#!/usr/bin/env python3
"""What model text can put in a Brewfile, Brewfile.all and a mise.toml.

    python3 test/brewfile.py

brew bundle runs Brewfile.all as Ruby on every clone, and mise runs a
mise.toml's [hooks] and [env]. Fixture Atlases in a temp dir; nothing is
installed. Each rule is tested both ways.

  - NAMES: a brew or cask name matches toolplan.NAME; `owner/repo/x` and a
    tap only from Brewfile.taps.
  - WHY: --why is one comment line with no quote or backslash.
  - THE UNION: only bare `tap "x"`, `brew "x"`, `cask "x"` lines reach
    Brewfile.all, rebuilt from the name; every other line is refused and
    reported (stderr, tools.json refused_brew). A subject directory whose name
    holds a line break cannot break the header comment.
  - THE PROBE: a name or --why that once made a working `system(...)` line is
    refused, and Brewfile.all passes `ruby -c`, holds only bare lines, and
    runs nothing when Ruby loads it.
  - MISE: backend keys (`npm:`, `pipx:`, `cargo:`) are quoted; a version that
    is not plain, an unknown backend, and a mise.toml with [hooks], [env],
    [tasks], a top-level key or a postinstall option are refused, however the
    TOML spells it (dotted key, multi-line value, a tool named `tools`).
  - TEMPLATES: mise renders every string as tera, so a value with a brace,
    %, #, $, a paren or a quote is refused, in mise.toml and .tool-versions.
  - THE CHAIN: every config mise reads in the target and above it up to the
    Atlas root (.mise.toml, mise.local.toml, .tool-versions,
    .config/mise/conf.d/...) passes the same check, under any name macOS
    folds to one of them (MISE.LOCAL.TOML, a long s for the s); a linked
    directory mise would follow is refused; and the set matches what
    `mise config ls` lists. `mise_env` keeps mise to that chain: no config
    above the root, MISE_YES=0, no file-name override. Checked against the
    real mise, offline, in a HOME of its own.
  - OPTIONS: no name of any kind starts with `-`, so none reads as an
    option on brew's or mise's command line; a dash inside one is fine.
  - `toolplan mise-chain <dir>` says why a chain is refused and exits 3, and
    is silent with 0 on a clean one: setup.sh's gate. `toolplan mise-run`
    runs its argv there under `mise_env`, and nothing on a refused chain.
  - A Brewfile that is not UTF-8 is reported whole, not dropped silently.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
sys.path.insert(0, BOARD)

work = os.path.realpath(tempfile.mkdtemp(prefix="brewfile-"))
os.environ["BOARD_STATE_DIR"] = os.path.join(work, "state")
os.environ["XDG_STATE_HOME"] = os.path.join(work, "xdg")
for k in ("TUTORBOARD_COURSES", "TUTORBOARD_SESSION", "TUTORBOARD_TURN"):
    os.environ.pop(k, None)

from tutorboard import toolplan                              # noqa: E402

fails = []
LINE = re.compile(r'^(tap|brew|cask) "[a-z0-9][a-z0-9+._@/-]*"$')


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)[:2000]) if detail else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def read(path):
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            return fh.read()
    except OSError:
        return ""


def fresh(name, brewfile=None):
    base = os.path.join(work, name)
    os.makedirs(base)
    if brewfile is not None:
        write(os.path.join(base, "Brewfile"), brewfile)
    return base


def only_bare(text):
    """Every line a `#` header comment or a bare tap, brew or cask line."""
    lines = text.split("\n")
    return text.endswith("\n") and all(
        LINE.match(l) or (l.startswith("# ") and i < 2) or (l == "" and i == len(lines) - 1)
        for i, l in enumerate(lines))


RUBY = shutil.which("ruby")


def ruby_ok(path):
    """(ruby -c passed, loading it with stub brew/cask/tap ran no code)."""
    if not RUBY:
        return None, None
    p = subprocess.run([RUBY, "-c", path], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    return p.returncode == 0 and "Syntax OK" in p.stdout, p.stdout


try:
    # =======================================================================
    # names
    # =======================================================================
    taps = set(["acme/tools"])
    for name in ("jq", "whisper.cpp", "python@3.12", "font-dejavu", "c++filt", "a_b",
                 "acme/tools/widget-cli"):
        check("name accepted: %s" % name, toolplan.name_problem("brew", name, taps) == "")
    for name in ('jq"; system("x"); "', "Jq", "-jq", ".jq", "", "jq x", "jq\n",
                 "jq#{x}", "jq\\", "other/tap/x", "acme/tools", "a/b/c/d", "../x",
                 "acme/tools/Widget"):
        check("name refused: %r" % name, toolplan.name_problem("brew", name, taps) != "")
    check("a tap in Brewfile.taps is accepted",
          toolplan.name_problem("tap", "acme/tools", taps) == "")
    check("a tap not in Brewfile.taps is refused, and a malformed one",
          "not in Brewfile.taps" in toolplan.name_problem("tap", "evil/tap", taps)
          and toolplan.name_problem("tap", 'acme/tools", "https://x', taps) != "")
    allow = fresh("allow")
    write(os.path.join(allow, "Brewfile.taps"),
          "# taps the owner allows\nacme/tools   # widgets\nNot/Valid\nx/y/z\n\n")
    check("allowed_taps reads owner/repo lines, skipping comments and bad lines",
          toolplan.allowed_taps(allow) == set(["acme/tools"]),
          toolplan.allowed_taps(allow))
    check("no Brewfile.taps allows no tap", toolplan.allowed_taps(fresh("notaps")) == set())

    # =======================================================================
    # declare: names and --why
    # =======================================================================
    d = fresh("declare", "# head\nbrew \"uv\"\n")
    before = read(os.path.join(d, "Brewfile"))
    got = toolplan.declare(d, "brew", 'jq"; system("touch x"); brew "y')
    check("declare refuses an injected brew name and writes nothing",
          not got["changed"] and "lower-case" in got["note"]
          and read(os.path.join(d, "Brewfile")) == before, got)
    got = toolplan.declare(d, "cask", "evil/tap/thing")
    check("declare refuses a tapped cask whose tap is not allowed",
          not got["changed"] and "not in Brewfile.taps" in got["note"], got)
    write(os.path.join(d, "Brewfile.taps"), "acme/tools\n")
    got = toolplan.declare(d, "brew", "acme/tools/widget-cli")
    check("declare accepts a tapped name once its tap is allowed",
          got["changed"] and got["entry"] == 'brew "acme/tools/widget-cli"', got)
    got = toolplan.declare(d, "brew", "jq",
                           why='json\nsystem("touch x") # "quoted" \\ back\r\n  tail')
    text = read(os.path.join(d, "Brewfile"))
    check("--why becomes one comment line: no line break, quote or backslash",
          got["changed"]
          and got["entry"] == 'brew "jq"  # json system(touch x) # quoted back tail'
          and text.endswith(got["entry"] + "\n") and text.count("\n") == 4
          and got["why"] == "json system(touch x) # quoted back tail", (got, text))
    check("clean_why keeps a plain reason as it is and caps the length",
          toolplan.clean_why("json on the command line") == "json on the command line"
          and len(toolplan.clean_why("x" * 500)) == toolplan.WHY_MAX
          and toolplan.clean_why(None) == "" and toolplan.clean_why("\n\t") == "")

    # =======================================================================
    # the union
    # =======================================================================
    u = fresh("union", '# root\nbrew "uv"   # the tool\ntap "acme/tools"\n'
                       'brew "acme/tools/widget-cli"\ncask "font-x"\n\n')
    write(os.path.join(u, "Brewfile.taps"), "acme/tools\n")
    sub = os.path.join(u, "courses", "C")
    write(os.path.join(sub, "tutorboard.json"), json.dumps({"check": "true"}))
    write(os.path.join(sub, "Brewfile"),
          'brew "go"\n'
          'brew "jq"; system("touch PWNED"); brew "x"\n'
          'system("touch PWNED")\n'
          'brew "ok", args: ["HEAD"]\n'
          'brew "a#{system(\'x\')}"\n'
          'tap "evil/tap"\n'
          'brew "evil/tap/x"\n'
          'mas "Xcode", id: 497799835\n'
          '`touch PWNED`\n'
          '=begin\n'
          '# a "comment" with system("x")\n')
    got, labels, refused = toolplan.checked(u)
    check("checked keeps each bare line whose name passes, rebuilt, taps first",
          got == ['tap "acme/tools"', 'brew "acme/tools/widget-cli"', 'brew "go"',
                  'brew "uv"', 'cask "font-x"']
          and labels == ["Brewfile", "courses/C/Brewfile"], (got, labels))
    lines = [r[1] for r in refused]
    check("and refuses every other line, naming its file, comments and blanks aside",
          lines == ['brew "jq"; system("touch PWNED"); brew "x"',
                    'system("touch PWNED")', 'brew "ok", args: ["HEAD"]',
                    'brew "a#{system(\'x\')}"', 'tap "evil/tap"', 'brew "evil/tap/x"',
                    'mas "Xcode", id: 497799835', '`touch PWNED`', '=begin']
          and all(r[0] == "courses/C/Brewfile" and r[2] for r in refused), refused)
    latin = fresh("latin", 'brew "uv"\n')
    write(os.path.join(latin, "courses", "L", "tutorboard.json"),
          json.dumps({"check": "true"}))
    with open(os.path.join(latin, "courses", "L", "Brewfile"), "wb") as fh:
        fh.write(b'brew "go"\nsystem("touch \xff")\n')
    got, _labels, refused = toolplan.checked(latin)
    check("a Brewfile that is not UTF-8 is reported whole and none of it is kept",
          got == ['brew "uv"'] and refused == [
              ("courses/L/Brewfile", toolplan.WHOLE_FILE, "not UTF-8, so none of it is read")],
          (got, refused))
    toolplan.write_union(latin, os.path.join(work, "latin-out", "Brewfile.all"))
    check("and tools.json refused_brew names it",
          [r["file"] for r in toolplan.read().get("refused_brew", [])]
          == ["courses/L/Brewfile"], toolplan.read().get("refused_brew"))
    clean = fresh("clean", 'brew "uv"\n# a comment\n\ncask "font-x"  # a face\n')
    check("a Brewfile of bare lines, comments and blanks refuses nothing",
          toolplan.checked(clean)[2] == []
          and toolplan.union(clean)[0] == ['brew "uv"', 'cask "font-x"'])
    text = toolplan.union_text(u)
    check("union_text holds no refused line, only the header and bare lines",
          only_bare(text) and "system" not in text and "PWNED" not in text
          and "evil" not in text and "=begin" not in text, text)
    dest = os.path.join(work, "out", "Brewfile.all")
    changed, path = toolplan.write_union(u, dest)
    doc = toolplan.read()
    check("write_union writes it and keeps the refused lines in tools.json",
          changed and read(dest) == text
          and [r["line"] for r in doc.get("refused_brew", [])] == lines
          and all(r["file"] == "courses/C/Brewfile" for r in doc["refused_brew"]),
          doc.get("refused_brew"))
    write(os.path.join(sub, "Brewfile"), 'brew "go"\n')
    toolplan.write_union(u, dest)
    check("and drops refused_brew once no line is refused",
          "refused_brew" not in toolplan.read(), toolplan.read())
    write(os.path.join(sub, "Brewfile"), 'brew "go"\nsystem("touch PWNED")\n')
    env = dict(os.environ, PYTHONPATH=BOARD)
    p = subprocess.run([sys.executable, "-m", "tutorboard.toolplan", "union", "--atlas", u],
                       env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True)
    check("`toolplan union` prints the union and each refused line to stderr",
          p.returncode == 0 and p.stdout == toolplan.union_text(u)
          and "refused courses/C/Brewfile: 'system(\"touch PWNED\")'" in p.stderr,
          (p.stdout, p.stderr))
    p = subprocess.run([sys.executable, "-m", "tutorboard.toolplan", "union", "--write",
                        "--atlas", u], env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True)
    check("`toolplan union --write` counts the refused lines on stdout",
          p.returncode == 0 and "1 line(s) refused, see tools.json refused_brew" in p.stdout,
          (p.stdout, p.stderr))
    p = subprocess.run([sys.executable, "-m", "tutorboard.toolplan", "union", "--write",
                        "--atlas", clean], env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True)
    check("and says nothing of refusals when there are none",
          p.returncode == 0 and "refused" not in p.stdout and p.stderr == "",
          (p.stdout, p.stderr))

    # A subject whose directory name carries a line break and Ruby.
    odd = fresh("odd", 'brew "uv"\n')
    weird = os.path.join(odd, "courses", 'X\nsystem("touch PWNED")\n#')
    write(os.path.join(weird, "tutorboard.json"), json.dumps({"check": "true"}))
    write(os.path.join(weird, "Brewfile"), 'brew "go"\n')
    text = toolplan.union_text(odd)
    check("a subject name with a line break stays inside the header comment",
          only_bare(text) and text.count("\n") == 4 and 'brew "go"' in text, text)

    # =======================================================================
    # the probe: the old working system(...) line
    # =======================================================================
    probe = fresh("probe", 'brew "uv"\n')
    mark = os.path.join(work, "PWNED")
    a = toolplan.declare(probe, "brew", 'jq"; system("touch %s"); brew "x' % mark)
    b = toolplan.declare(probe, "brew", "bat", why='json\nsystem("touch %s")' % mark)
    c = toolplan.declare(probe, "cask", 'x"\nsystem("touch %s")\n#' % mark)
    m = toolplan.declare(probe, "mise", 'node"=1\n[hooks]\nenter = "touch %s' % mark)
    v = toolplan.declare(probe, "mise", "node", version='22"\n[hooks]\nenter = "touch x')
    check("the probe's injected names and version are refused",
          not a["changed"] and not c["changed"] and not m["changed"]
          and not v["changed"], (a, c, m, v))
    check("and its injected --why lands as one comment line",
          b["changed"] and "\n" not in b["entry"] and '"' not in b["why"], b)
    # A hand-edited Brewfile carries the old payload too.
    write(os.path.join(probe, "courses", "C", "tutorboard.json"),
          json.dumps({"check": "true"}))
    write(os.path.join(probe, "courses", "C", "Brewfile"),
          'brew "jq"; system("touch %s"); brew "x"\nsystem("touch %s")\n' % (mark, mark))
    dest = os.path.join(work, "probe-out", "Brewfile.all")
    toolplan.write_union(probe, dest)
    text = read(dest)
    check("the probe's Brewfile.all holds only the header and bare lines",
          only_bare(text) and text.endswith('brew "bat"\nbrew "uv"\n')
          and "system" not in text, text)
    if RUBY:
        ok, said = ruby_ok(dest)
        check("the probe's Brewfile.all passes ruby -c", ok, said)
        subprocess.run([RUBY, "-e", "def brew(*a);end;def cask(*a);end;def tap(*a);end;"
                        "load ARGV[0]", dest], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
        check("and Ruby loading it runs no system()", not os.path.exists(mark))
    else:
        check("ruby is on the PATH, for ruby -c", False, "no ruby; the probe was not run")

    # =======================================================================
    # mise
    # =======================================================================
    mi = fresh("mise")
    got = toolplan.declare(mi, "mise", "npm:prettier", why="formatting")
    got2 = toolplan.declare(mi, "mise", "pipx:black", version="24.1.0")
    got3 = toolplan.declare(mi, "mise", "cargo:ripgrep")
    got4 = toolplan.declare(mi, "mise", "npm:@scope/pkg", version="1.2.3")
    got5 = toolplan.declare(mi, "mise", "python", version="3.12")
    text = read(os.path.join(mi, "mise.toml"))
    check("a backend key is quoted, a bare key is not",
          all(g["changed"] for g in (got, got2, got3, got4, got5))
          and '"npm:prettier" = "latest"  # formatting\n' in text
          and '"pipx:black" = "24.1.0"\n' in text and '"cargo:ripgrep" = "latest"\n' in text
          and '"npm:@scope/pkg" = "1.2.3"\n' in text and 'python = "3.12"\n' in text, text)
    check("and pinned_in reads the quoted keys back",
          toolplan.pinned_in(mi) == ["cargo:ripgrep", "npm:@scope/pkg", "npm:prettier",
                                     "pipx:black", "python"], toolplan.pinned_in(mi))
    got = toolplan.declare(mi, "mise", "npm:prettier", version="3.3.0")
    text = read(os.path.join(mi, "mise.toml"))
    check("a second pin of a quoted key replaces it",
          got["changed"] and text.count("npm:prettier") == 1
          and '"npm:prettier" = "3.3.0"' in text, text)
    for name, why in (("asdf:evil/plugin", "not one of"),
                      ("vfox:x", "not one of"),
                      ('npm:x" = "1"\n[hooks]', "a mise tool"),
                      ("npm:", "a mise tool"),
                      ("node=1", "a mise tool"),
                      ("tools.node", "a mise tool")):
        got = toolplan.declare(mi, "mise", name)
        check("mise name refused: %r" % name, not got["changed"] and why in got["note"], got)
    for name in ("-y", "--yes", "-C", "--force", "-", "npm:-x", "npm:--yes",
                 "pipx:-e", "-npm:x"):
        got = toolplan.declare(mi, "mise", name)
        check("option-shaped mise name refused: %r" % name,
              not got["changed"] and toolplan.mise_name_problem(name) != "", got)
    for name in ("y-1", "a_b", "9lives", "npm:@scope/x-y", "npm:a-b"):
        check("a mise name with a dash or underscore inside is accepted: %s" % name,
              toolplan.mise_name_problem(name) == "")
    for kind in ("brew", "cask"):
        for name in ("-y", "--force", "--HEAD", "-"):
            check("option-shaped %s name refused: %r" % (kind, name),
                  toolplan.name_problem(kind, name, {"acme/tools"}) != "")
    check("an option-shaped tap half is refused",
          toolplan.name_problem("tap", "-x/tools", {"-x/tools"}) != ""
          and toolplan.name_problem("brew", "acme/-x/y", {"acme/-x"}) != "")
    check("a .tool-versions tool shaped like an option is refused",
          toolplan.tool_versions_problem("-y 1\n") != ""
          and toolplan.tool_versions_problem("y-1 1\n") == "")
    for toml in ('[tools]\n"-y" = "1"\n', '[tools."--yes"]\nversion = "1"\n'):
        check("a mise.toml pinning an option-shaped tool is refused: %r" % toml,
              "edit it by hand" in toolplan.mise_text_problem(toml)[0])
    check("a TOML key that needs no quotes keeps none, a backend key is quoted",
          toolplan.mise_key("y-1") == "y-1" and toolplan.mise_key("npm:x") == '"npm:x"')
    for version in ('22"', "22\n[hooks]", "path:/tmp/x", "../x", "1 2", "\\"):
        got = toolplan.declare(mi, "mise", "node", version=version)
        check("mise version refused: %r" % version,
              not got["changed"] and "a mise version" in got["note"], got)
    for version in ("22", "3.12.1", "latest", "lts", "ref:main", "prefix:1.2"):
        got = toolplan.declare(mi, "mise", "node", version=version)
        check("mise version accepted: %s" % version,
              got["changed"] or "already pinned" in got["note"], got)
    before = read(os.path.join(mi, "mise.toml"))
    check("only the [tools] table was written",
          [l for l in before.splitlines() if l.startswith("[")] == ["[tools]"], before)

    for label, toml in (
            ("[hooks]", '[tools]\nnode = "22"\n\n[hooks]\nenter = "touch x"\n'),
            ("[env]", '[env]\nPATH = "x"\n[tools]\nnode = "22"\n'),
            ("[tasks]", '[tools]\n[tasks.x]\nrun = "x"\n'),
            ("[settings]", '[settings]\nexperimental = true\n'),
            ("a top-level key", 'env_file = ".env"\n[tools]\n'),
            ("an inline postinstall",
             '[tools]\nnode = { version = "22", postinstall = "touch x" }\n'),
            ("a subtable postinstall",
             '[tools.node]\nversion = "22"\npostinstall = "touch x"\n'),
            ("a nested tool table", '[tools.node.env]\nX = "1"\n'),
            ("a dotted postinstall",
             '[tools]\nnode.version = "22"\nnode.postinstall = "touch PWNED"\n'),
            ("a quoted dotted postinstall", '[tools]\n"node".postinstall = "touch x"\n'),
            ("a spaced dotted postinstall", '[tools]\nnode . postinstall = "touch x"\n'),
            ("a backend dotted postinstall", '[tools]\n"npm:x".postinstall = "touch x"\n'),
            ("a postinstall in a multi-line array",
             '[tools]\nnode = [\n  { postinstall = "touch x", version = "22" },\n]\n'),
            ("a postinstall on an inline table's second line",
             '[tools]\nnode = { version = "22",\n  postinstall = "touch x" }\n'),
            ("a dotted install_env in a subtable",
             '[tools.node]\nversion = "22"\ninstall_env.X = "1"\n'),
            ("an inline install_env",
             '[tools]\nnode = { version = "22", install_env = { X = "1" } }\n'),
            ("a tool named tools", '[tools.tools]\npostinstall = "touch x"\n'),
            ("an array of tables", '[[tools.node]]\nversion = "22"\n'),
            ("a multi-line string", '[tools]\nnode = """\n22"""\n'),
            ("a tool defined twice", '[tools]\nnode = "20"\n[tools.node]\nversion = "22"\n'),
            ("an asdf plugin", '[tools]\n"asdf:evil/x" = "1"\n'),
            ("a quoted top-level table", '["hooks"]\nenter = "touch x"\n'),
            ("a quoted option key", '[tools.node]\n"postinstall" = "touch x"\n'),
            ("text TOML will not parse", '[tools]\nnode = { version = "22" os = "macos" }\n')):
        hm = fresh("mise-" + re.sub(r"\W", "", label))
        write(os.path.join(hm, "mise.toml"), toml)
        got = toolplan.declare(hm, "mise", "python", version="3.12")
        check("declare refuses a mise.toml with %s and leaves it" % label,
              not got["changed"] and "edit it by hand" in got["note"]
              and read(os.path.join(hm, "mise.toml")) == toml, got)
    for label, toml in (
            ("min_version and comments", 'min_version = "2024.1"\n# x\n[tools]\nnode = "22"\n'),
            ("a [tools.node] subtable", '[tools]\n[tools.node]\nversion = "20"\n'),
            ("an inline version table", '[tools]\nnode = { version = "22" }\n'),
            ("a string value naming env", '[tools]\n"npm:env" = "1"\n'),
            ("an array of versions", '[tools]\nnode = ["20", "22"]\n'),
            ("an inline table with os", '[tools]\nnode = { version = "22", os = ["macos"] }\n'),
            ("a subtable with os", '[tools.node]\nversion = "22"\nos = ["macos", "linux"]\n'),
            ("spaced headers and literal strings", "[ tools ]\n'npm:prettier' = '3'\n")):
        hm = fresh("mise-ok-" + re.sub(r"\W", "", label))
        write(os.path.join(hm, "mise.toml"), toml)
        got = toolplan.declare(hm, "mise", "python", version="3.12")
        check("declare writes a mise.toml with %s" % label,
              got["changed"] and 'python = "3.12"' in read(os.path.join(hm, "mise.toml")),
              got)

    # mise renders every string as a tera template, so a value with a brace
    # (or %, #, $, a paren, a quote) is refused wherever it sits.
    tera = "{{ exec(command='touch PWNED') }}"
    for label, toml in (
            ("a tool's version", '[tools]\nnode = "%s"\n' % tera),
            ("a literal-string version", "[tools]\nnode = '{{ exec(command=\"x\") }}'\n"),
            ("an inline version", '[tools]\nnode = { version = "%s" }\n' % tera),
            ("an array of versions", '[tools]\nnode = ["22", "%s"]\n' % tera),
            ("an os entry", '[tools]\nnode = { version = "22", os = ["%s"] }\n' % tera),
            ("a subtable version", '[tools.node]\nversion = "%s"\n' % tera),
            ("min_version", 'min_version = "%s"\n[tools]\n' % tera),
            ("a {%% block %%}", '[tools]\nnode = "{%% if true %%}22{%% endif %%}"\n'),
            ("an env reference", '[tools]\nnode = "$NODE"\n')):
        problem = toolplan.mise_text_problem(toml)[0]
        check("mise_text_problem refuses a tera template in %s" % label,
              "edit it by hand" in problem, (toml, problem))
    for value in ("22", "latest", "lts", "3.12.1", "ref:v1.2", "prefix:3", "sub-1:lts",
                  "1.2.3-rc.1+b", "2024.1", "nightly"):
        toml = '[tools]\nnode = "%s"\n[tools.go]\nversion = "%s"\n' % (value, value)
        problem, pins = toolplan.mise_text_problem(toml)
        check("mise_text_problem passes plain version %s" % value,
              problem == "" and pins == {"node": value, "go": value}, (problem, pins))

    # The tomllib check only runs where tomllib is (3.11+); the line grammar
    # refuses every case above without it.
    try:
        import tomllib                                       # noqa: F401
        have_toml = True
    except ImportError:
        have_toml = False
    if have_toml:
        check("tomllib is here, so TOML that will not parse is refused by it too", True)
    else:
        print("note python %s has no tomllib; the line grammar alone was tested"
              % sys.version.split()[0])

    # A pin declare would write must still parse and pin the name.
    dot = fresh("mise-dotted-version")
    write(os.path.join(dot, "mise.toml"), '[tools]\nnode.version = "22"\n')
    got = toolplan.declare(dot, "mise", "node", version="20")
    check("declare refuses a dotted node.version rather than writing node twice",
          not got["changed"] and "edit it by hand" in got["note"]
          and read(os.path.join(dot, "mise.toml")) == '[tools]\nnode.version = "22"\n', got)
    check("mise_text_problem refuses the text that write would have made",
          toolplan.mise_text_problem('[tools]\nnode.version = "22"\nnode = "20"\n')[0] != "")
    problem, pins = toolplan.mise_text_problem(
        '# x\n[tools]\nnode = "22"  # why\n"npm:x" = { version = "1" }\n[tools.go]\nversion = "1.22"\n')
    check("mise_text_problem reads each tool's pin from a plain file",
          problem == "" and pins == {"node": "22", "npm:x": "1", "go": "1.22"}, (problem, pins))

    # =======================================================================
    # the chain: every config mise reads where it runs
    # =======================================================================
    ch = fresh("chain")
    write(os.path.join(ch, "mise.toml"), '[tools]\nnode = "22"\n')
    sub = os.path.join(ch, "courses", "C")
    outside_dir = fresh("outside-env")
    write(os.path.join(sub, "tutorboard.json"), json.dumps({"check": "true"}))
    write(os.path.join(sub, "mise.toml"), '[tools]\ngo = "1.22"\n')
    check("a clean chain has no problem, root and subject",
          toolplan.mise_chain_problem(sub, ch) == ""
          and toolplan.mise_chain_problem(ch, ch) == "")
    got = toolplan.declare(ch, "mise", "python", version="3.12", subject="C")
    check("declare writes a subject's mise.toml when the chain is clean",
          got["changed"] and 'python = "3.12"' in read(os.path.join(sub, "mise.toml")), got)
    hooks = '[hooks]\npreinstall = "touch PWNED"\n'
    for rel in (".mise.toml", "mise.local.toml", ".mise.local.toml", "mise.dev.toml",
                "mise/config.toml", ".mise/config.toml", ".config/mise.toml",
                ".config/mise/config.toml", ".config/mise/conf.d/x.toml"):
        for where, label in ((sub, "the subject"), (os.path.join(ch, "courses"), "a parent"),
                             (ch, "the root")):
            bad = os.path.join(where, rel)
            write(bad, hooks)
            before = read(os.path.join(sub, "mise.toml"))
            got = toolplan.declare(ch, "mise", "ruby", version="3.3", subject="C")
            check("declare refuses when %s has %s with [hooks], naming it" % (label, rel),
                  not got["changed"] and os.path.relpath(bad, ch) in got["note"]
                  and "edit it by hand" in got["note"]
                  and read(os.path.join(sub, "mise.toml")) == before, got)
            check("  and mise_configs lists it, so the kick trusts nothing unchecked",
                  bad in toolplan.mise_configs(sub, ch))
            os.remove(bad)
    # .tool-versions: mise renders it as a template without asking for trust.
    for where, label in ((sub, "the subject"), (ch, "the root")):
        tv = os.path.join(where, ".tool-versions")
        write(tv, "node {{ exec(command='touch PWNED') }}\n")
        got = toolplan.declare(ch, "mise", "ruby", version="3.3", subject="C")
        check("declare refuses when %s has a .tool-versions template, naming it" % label,
              not got["changed"] and os.path.relpath(tv, ch) in got["note"]
              and "edit it by hand" in got["note"], got)
        check("  and mise_configs lists .tool-versions", tv in toolplan.mise_configs(sub, ch))
        os.remove(tv)
    for text in ("node {{ exec(command='x') }}\n", "node\n", "node 22 $(touch x)\n",
                 "asdf:evil/x 1\n", "node 22 'x'\n"):
        check("tool_versions_problem refuses %r" % text,
              toolplan.tool_versions_problem(text) != "")
    # mise renders all of a .tool-versions, comments too.
    for text in ("node 22 # {{ exec(command='x') }}\n", "# {% if true %}x{% endif %}\n",
                 "# {# c #}\n", "node 22 # 100%\n", "node path:./bin\n",
                 "node 22 path:/tmp/x\n"):
        check("tool_versions_problem refuses a comment template or a path: %r" % text,
              "edit it by hand" in toolplan.tool_versions_problem(text))
    tv_ok = "# pins\nnode 22.1.0 20  # two\n\npython 3.12\nnpm:prettier latest\n"
    check("tool_versions_problem passes plain tools, versions and plain comments",
          toolplan.tool_versions_problem(tv_ok) == "")
    for text in ('[tools]\nnode = "22"  # {{ exec(command="x") }}\n',
                 '# {% if true %}\n[tools]\n', '# {# c #}\n[tools]\n',
                 '[tools]\nnode = "path:./bin"\n', '[tools]\nnode = ["22", "path:/x"]\n',
                 "[tools]\nnode = { version = 'path:/x' }\n",
                 '[tools.node]\nversion = "path:/x"\n'):
        check("mise_text_problem refuses a comment template or a path: pin %r" % text,
              "edit it by hand" in toolplan.mise_text_problem(text)[0])
    check("mise_text_problem passes a plain comment and an inline table",
          toolplan.mise_text_problem(
              '# 100 percent { plain\n[tools]\nnode = { version = "22" }  # why\n')[0] == "")
    # A miserc can send mise to files the chain never names: refused, even empty.
    for rel in (".miserc.toml", "miserc.toml", ".miserc.local.toml", "miserc.local.toml",
                ".config/miserc.toml", ".config/miserc.local.toml", "mise/miserc.toml"):
        for where, label in ((sub, "the subject"), (os.path.join(ch, "courses"), "a parent"),
                             (ch, "the root")):
            rc = os.path.join(where, rel)
            write(rc, "")
            problem = toolplan.mise_chain_problem(sub, ch)
            check("mise_chain_problem refuses an empty %s in %s, naming it" % (rel, label),
                  os.path.relpath(rc, ch) in problem and "edit it by hand" in problem, problem)
            check("  and mise_configs lists it", rc in toolplan.mise_configs(sub, ch))
            os.remove(rc)
    check("the chain passes once the miserc is gone", toolplan.mise_chain_problem(sub, ch) == "")
    write(os.path.join(sub, ".tool-versions"), tv_ok)
    check("a plain .tool-versions passes the chain", toolplan.mise_chain_problem(sub, ch) == "")
    os.remove(os.path.join(sub, ".tool-versions"))
    # macOS opens mise.local.toml under any name that folds to it: another
    # case, or a long s (U+017F) for the s.
    tpl = "[tools]\nnode = \"{{ exec(command='touch PWNED') }}\"\n"
    for rel, text in (("MISE.LOCAL.TOML", tpl), ("Mise.Local.toml", tpl),
                      ("miſe.local.toml", tpl), (".MISE.TOML", tpl),
                      (".TOOL-VERSIONS", "node {{ exec(command='touch PWNED') }}\n"),
                      (".tool-verſions", "node {{ exec(command='touch PWNED') }}\n"),
                      (".MISERC.toml", ""), ("MISE/conf.d/x.TOML", tpl),
                      (".Config/MISE/config.toml", tpl)):
        bad = os.path.join(sub, rel)
        write(bad, text)
        problem = toolplan.mise_chain_problem(sub, ch)
        check("mise_chain_problem refuses %r, naming it" % rel,
              "edit it by hand" in problem and toolplan._fold(problem).startswith(
                  toolplan._fold(os.path.join("courses", "C", rel))), problem)
        check("  and mise_configs lists it",
              toolplan._fold(bad) in [toolplan._fold(p) for p in toolplan.mise_configs(sub, ch)])
        top = os.path.join(sub, rel.split("/")[0])
        shutil.rmtree(top) if "/" in rel else os.remove(bad)
    for rel, text in (("MISE.LOCAL.TOML", '[tools]\nruby = "3.2"\n'),
                      (".TOOL-VERSIONS", "node 22\n"), (".tool-verſions", "node 22\n")):
        good = os.path.join(sub, rel)
        write(good, text)
        check("a plain %r passes the chain, read as the file it folds to" % rel,
              toolplan.mise_chain_problem(sub, ch) == ""
              and good in toolplan.mise_configs(sub, ch), toolplan.mise_chain_problem(sub, ch))
        os.remove(good)
    check("a name that folds to no mise file is not one",
          [toolplan._fold(n) for n in ("mıse.toml", "mi‍se.toml", "MISE.toml.bak")]
          == ["mıse.toml", "mi‍se.toml", "mise.toml.bak"])
    # mise follows a linked directory to files the chain never walks.
    hidden = os.path.join(sub, "hidden")
    write(os.path.join(hidden, "x.toml"), tpl)
    for rel in (".config/mise/conf.d", ".config/mise", "mise", ".mise", ".config",
                "mise/conf.d", ".mise/conf.d"):
        link = os.path.join(sub, rel)
        os.makedirs(os.path.dirname(link), exist_ok=True)
        os.symlink(os.path.relpath(hidden, os.path.dirname(link)), link)
        problem = toolplan.mise_chain_problem(sub, ch)
        check("mise_chain_problem refuses a linked %s, naming it" % rel,
              problem.startswith(os.path.join("courses", "C", rel) + " is a linked directory"),
              problem)
        check("  and mise_configs lists the link", link in toolplan.mise_configs(sub, ch))
        os.remove(link)
        for top in (".config", "mise", ".mise"):
            shutil.rmtree(os.path.join(sub, top), ignore_errors=True)
    write(os.path.join(sub, ".config", "mise", "conf.d", "x.toml"), '[tools]\nruby = "3.2"\n')
    check("a real conf.d of plain [tools] passes the chain",
          toolplan.mise_chain_problem(sub, ch) == "")
    shutil.rmtree(os.path.join(sub, ".config"))
    shutil.rmtree(hidden)
    check("the chain is clean again", toolplan.mise_chain_problem(sub, ch) == "")

    # `toolplan mise-chain`, setup.sh's gate.
    def chain_cli(target):
        p = subprocess.run([sys.executable, "-B", "-m", "tutorboard.toolplan", "mise-chain",
                            target, "--atlas", ch], cwd=BOARD, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True, timeout=60,
                           env=dict(os.environ, TUTORBOARD_COURSES=ch))
        return p.returncode, p.stdout, p.stderr
    got = (chain_cli(sub), chain_cli(ch))
    check("`toolplan mise-chain` is silent with exit 0 on a clean chain, subject and root",
          got == ((0, "", ""), (0, "", "")), got)
    for bad, rel in ((os.path.join(sub, "mise.local.toml"), "courses/C/mise.local.toml"),
                     (os.path.join(ch, "mise.toml"), "mise.toml")):
        saved = read(bad)
        write(bad, '[tools]\nnode = "22"\n' + hooks)
        code, out, err = chain_cli(sub)
        check("`toolplan mise-chain` names a refused %s and exits 3" % rel,
              code == 3 and out.startswith(rel + " has a [hooks] table")
              and "edit it by hand" in out and out.count("\n") == 1,
              (code, out, err))
        if saved:
            write(bad, saved)
        else:
            os.remove(bad)
    check("and is clean again once the [hooks] are gone", chain_cli(sub)[0] == 0)
    for rel, text in ((".tool-versions", "node 22  # {{ exec(command='touch x') }}\n"),
                      (".miserc.toml", 'override_config_filenames = ["evil.toml"]\n')):
        bad = os.path.join(sub, rel)
        write(bad, text)
        code, out, err = chain_cli(sub)
        check("`toolplan mise-chain` refuses %s and exits 3" % rel,
              code == 3 and out.startswith(os.path.join("courses", "C", rel)), (code, out, err))
        os.remove(bad)
    check("and is clean again once they are gone", chain_cli(sub)[0] == 0)

    # `toolplan mise-run`, setup.sh's only way to run mise.
    said = os.path.join(work, "mise-run.said")

    def run_cli(target):
        if os.path.exists(said):
            os.remove(said)
        p = subprocess.run([sys.executable, "-B", "-m", "tutorboard.toolplan", "--atlas", ch,
                            "mise-run", target, "--", "/bin/sh", "-c",
                            'printf "%s|%s|%s|%s|%s" "$PWD" "$MISE_YES" '
                            '"$MISE_TRUSTED_CONFIG_PATHS" "$MISE_CEILING_PATHS" "$*" >"$0"',
                            said, "--atlas", "x"], cwd=BOARD, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True, timeout=60,
                           env=dict(os.environ, TUTORBOARD_COURSES=ch, MISE_YES="1",
                                    MISE_TRUSTED_CONFIG_PATHS="/"))
        return p.returncode, p.stdout, read(said)
    got = run_cli(sub)
    check("`toolplan mise-run` runs its argv in the directory under mise_env, the "
          "arguments after -- its own",
          got == (0, "", "%s|0|%s|%s|--atlas x" % (
              os.path.realpath(sub), os.pathsep.join(toolplan.mise_configs(sub, ch)),
              os.path.dirname(ch))), got)
    write(os.path.join(sub, ".mise.toml"), '[tools]\nnode = "22"\n' + hooks)
    got = run_cli(sub)
    check("and runs nothing on a refused chain: exit 3 and the reason",
          got[0] == 3 and got[1].startswith(os.path.join("courses", "C", ".mise.toml"))
          and got[2] == "", got)
    os.remove(os.path.join(sub, ".mise.toml"))

    menv = toolplan.mise_env(sub, ch, {"MISE_YES": "1", "PATH": "/bin",
                                       "MISE_DEFAULT_CONFIG_FILENAME": "x.toml",
                                       "MISE_DEFAULT_TOOL_VERSIONS_FILENAME": "x",
                                       "MISE_OVERRIDE_CONFIG_FILENAMES": "x.toml",
                                       "MISE_OVERRIDE_TOOL_VERSIONS_FILENAMES": "x",
                                       "MISE_TRUSTED_CONFIG_PATHS": "/"})
    check("mise_env says no to every prompt, stops above the root, trusts the chain only "
          "and drops every file-name override",
          menv == {"PATH": "/bin", "MISE_YES": "0", "MISE_CEILING_PATHS": os.path.dirname(ch),
                   "MISE_TRUSTED_CONFIG_PATHS": os.pathsep.join(toolplan.mise_configs(sub, ch))},
          menv)
    check("mise_env stops above the target itself when it is outside the root",
          toolplan.mise_env(outside_dir, ch, {})["MISE_CEILING_PATHS"]
          == os.path.dirname(outside_dir))

    write(os.path.join(sub, "mise.local.toml"), '[tools]\nruby = "3.2"\n')
    check("a sibling config of plain [tools] passes the chain",
          toolplan.mise_chain_problem(sub, ch) == "")
    os.remove(os.path.join(sub, "mise.local.toml"))
    outside = fresh("outside")
    write(os.path.join(outside, "mise.toml"), '[tools]\nnode = "22"\n')
    check("a target outside the Atlas root reads only its own configs",
          toolplan.mise_configs(outside, ch) == [os.path.join(outside, "mise.toml")])
    write(os.path.join(sub, "mise.toml.bak"), hooks)
    write(os.path.join(sub, "notes.toml"), hooks)
    check("a file mise does not read is not part of the chain",
          toolplan.mise_chain_problem(sub, ch) == ""
          and toolplan.mise_configs(sub, ch) == [os.path.join(sub, "mise.toml"),
                                                 os.path.join(ch, "mise.toml")],
          toolplan.mise_configs(sub, ch))

    # mise_configs must cover every file mise itself loads.
    MISE = shutil.which("mise")
    if MISE:
        ls = fresh("mise-ls")
        deep = os.path.join(ls, "a", "b")
        names = ("mise.toml", ".mise.toml", "mise.local.toml", ".mise.local.toml",
                 "mise.dev.toml", ".mise.dev.toml", "mise.dev.local.toml",
                 "mise/config.toml", "mise/config.local.toml", "mise/conf.d/c.toml",
                 ".mise/config.toml", ".mise/conf.d/a.toml",
                 ".config/mise.toml", ".config/mise.local.toml",
                 ".config/mise/config.toml", ".config/mise/mise.toml",
                 ".config/mise/config.local.toml", ".config/mise/conf.d/b.toml",
                 ".tool-versions")
        for rel in names:
            write(os.path.join(deep, rel),
                  "node 22\n" if rel == ".tool-versions" else "[tools]\n")
        write(os.path.join(ls, "a", "mise.toml"), "[tools]\n")
        menv = dict(os.environ, MISE_ENV="dev", MISE_TRUSTED_CONFIG_PATHS=ls)
        p = subprocess.run([MISE, "config", "ls", "--json"], cwd=deep, env=menv,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True)
        try:
            listed = set(os.path.realpath(c["path"]) for c in json.loads(p.stdout)
                         if os.path.realpath(c["path"]).startswith(ls + os.sep))
        except (ValueError, KeyError, TypeError):
            listed = None
        mine = set(toolplan.mise_configs(deep, ls))
        check("every config `mise config ls` reads is in mise_configs",
              listed and listed <= mine, (sorted(listed or []), sorted(mine), p.stderr))
    else:
        check("mise is on the PATH, for the config ls cross-check", False, "no mise")

    # The real mise, offline, in a HOME of its own whose config says yes to
    # every prompt. A config above the Atlas root renders an exec template.
    if MISE:
        up = fresh("mise-up")
        mroot = os.path.join(up, "atlas")
        msub = os.path.join(mroot, "courses", "C")
        homes = fresh("mise-homes")
        pwn_up = os.path.join(homes, "PWNED_UP")
        write(os.path.join(up, "mise.toml"),
              "[env]\nX = \"{{ exec(command='touch %s') }}\"\n" % pwn_up)
        write(os.path.join(mroot, "mise.toml"), '[tools]\nnode = "22"\n')
        write(os.path.join(msub, "mise.toml"), "[tools]\n")

        def mise_run(argv, env, state):
            mhome = os.path.join(homes, "home-" + state)
            write(os.path.join(mhome, ".config", "mise", "config.toml"),
                  "[settings]\nyes = true\n")
            env = dict(env, HOME=mhome, XDG_CONFIG_HOME=os.path.join(mhome, ".config"),
                       XDG_DATA_HOME=os.path.join(mhome, "data"),
                       XDG_STATE_HOME=os.path.join(mhome, "state"),
                       XDG_CACHE_HOME=os.path.join(mhome, "cache"), MISE_OFFLINE="1")
            for k in ("MISE_DATA_DIR", "MISE_STATE_DIR", "MISE_CACHE_DIR", "MISE_CONFIG_DIR",
                      "MISE_GLOBAL_CONFIG_FILE", "MISE_ENV"):
                env.pop(k, None)
            p = subprocess.run([MISE] + argv, cwd=msub, env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               universal_newlines=True, timeout=120)
            trusted = os.path.join(mhome, "state", "mise", "trusted-configs")
            # Each mark is a link to the directory whose config mise trusted.
            marks = sorted(os.listdir(trusted)) if os.path.isdir(trusted) else []
            return p, [os.path.realpath(os.path.join(trusted, m)) for m in marks]

        old = dict(os.environ, MISE_YES="1", MISE_TRUSTED_CONFIG_PATHS=os.pathsep.join(
            toolplan.mise_configs(msub, mroot)))
        p, trusted = mise_run(["install", "--locked", "node"], old, "old")
        check("the probe is live: with MISE_YES=1 mise trusts the config above the root "
              "and runs its template", os.path.exists(pwn_up)
              and up in trusted, (p.stdout[-800:], trusted))
        if os.path.exists(pwn_up):
            os.remove(pwn_up)
        env = toolplan.mise_env(msub, mroot, dict(os.environ, MISE_YES="1"))
        p, trusted = mise_run(["install", "--locked", "node"], env, "new")
        check("under mise_env mise never reads the config above the root, runs nothing "
              "and never marks it trusted", not os.path.exists(pwn_up)
              and up not in trusted, (p.stdout[-800:], trusted))
        p, _t = mise_run(["config", "ls", "--json"], env, "ls")
        try:
            seen = set(os.path.realpath(c["path"]) for c in json.loads(p.stdout)
                       if os.path.realpath(c["path"]).startswith(up + os.sep))
        except (ValueError, KeyError, TypeError):
            seen = None
        check("and still reads the checked chain, root and subject, and nothing else",
              p.returncode == 0 and seen == {os.path.join(mroot, "mise.toml"),
                                             os.path.join(msub, "mise.toml")},
              (p.stdout[-800:], seen))

        # A [tools] template and a .tool-versions template run under mise
        # itself, so the content check is what stops them.
        pwn = os.path.join(homes, "PWNED_T")
        for rel, text in (("mise.toml",
                           "[tools]\nnode = \"{{ exec(command='touch %s') }}\"\n" % pwn),
                          (".tool-versions", "node {{ exec(command='touch %s') }}\n" % pwn)):
            bad = os.path.join(msub, rel)
            before = read(bad)
            write(bad, text)
            p, _t = mise_run(["install", "--locked", "node"], toolplan.mise_env(msub, mroot),
                             "tpl-" + rel)
            check("the probe is live: mise runs a %s template under mise_env" % rel,
                  os.path.exists(pwn), p.stdout[-800:])
            if os.path.exists(pwn):
                os.remove(pwn)
            problem = toolplan.mise_chain_problem(msub, mroot)
            check("  so mise_chain_problem refuses it, naming %s" % rel,
                  os.path.join("courses", "C", rel) in problem, problem)
            if before:
                write(bad, before)
            else:
                os.remove(bad)
        # A template in a .tool-versions comment, and a .miserc.toml that
        # points mise at an [env] template in a file the chain never names.
        evil = os.path.join(msub, "evil.toml")
        for rel, text, extra in (
                (".tool-versions", "node 22  # {{ exec(command='touch %s') }}\n" % pwn, None),
                (".miserc.toml", 'override_config_filenames = ["evil.toml"]\n',
                 "[env]\nX = \"{{ exec(command='touch %s') }}\"\n" % pwn)):
            bad = os.path.join(msub, rel)
            write(bad, text)
            if extra:
                write(evil, extra)
            p, _t = mise_run(["install", "--locked", "node"], toolplan.mise_env(msub, mroot),
                             "rc-" + rel)
            check("the probe is live: mise runs the template behind %s under mise_env" % rel,
                  os.path.exists(pwn), p.stdout[-800:])
            if os.path.exists(pwn):
                os.remove(pwn)
            problem = toolplan.mise_chain_problem(msub, mroot)
            check("  so mise_chain_problem refuses it, naming %s" % rel,
                  os.path.join("courses", "C", rel) in problem, problem)
            os.remove(bad)
            if extra:
                os.remove(evil)
        check("the chain passes again once the templates are gone",
              toolplan.mise_chain_problem(msub, mroot) == "")
        # On a file system that folds names, mise opens mise.local.toml as
        # any name that folds to it; and it follows a linked conf.d.
        folds = os.path.exists(os.path.join(msub, "MISE.TOML"))
        hid = os.path.join(msub, "hidden")
        write(os.path.join(hid, "x.toml"),
              "[tools]\nnode = \"{{ exec(command='touch %s') }}\"\n" % pwn)
        cases = [(".config/mise/conf.d", None)]
        if folds:
            cases += [(rel, "[tools]\nnode = \"{{ exec(command='touch %s') }}\"\n" % pwn)
                      for rel in ("MISE.LOCAL.TOML", "miſe.local.toml")]
            cases += [(".TOOL-VERSIONS", "node {{ exec(command='touch %s') }}\n" % pwn)]
        for rel, text in cases:
            bad = os.path.join(msub, rel)
            if text is None:
                os.makedirs(os.path.dirname(bad), exist_ok=True)
                os.symlink(os.path.relpath(hid, os.path.dirname(bad)), bad)
            else:
                write(bad, text)
            p, _t = mise_run(["install", "--locked", "node"], toolplan.mise_env(msub, mroot),
                             "fold-%d" % cases.index((rel, text)))
            check("the probe is live: mise runs the template in %r under mise_env" % rel,
                  os.path.exists(pwn), p.stdout[-800:])
            if os.path.exists(pwn):
                os.remove(pwn)
            problem = toolplan.mise_chain_problem(msub, mroot)
            check("  so mise_chain_problem refuses it, naming %r" % rel,
                  problem.startswith(os.path.join("courses", "C", rel)), problem)
            os.remove(bad)
        shutil.rmtree(os.path.join(msub, ".config"))
        shutil.rmtree(hid)
        check("folding: this file system folds names, so the case probes ran", folds)
        check("the chain passes again once they are gone",
              toolplan.mise_chain_problem(msub, mroot) == "")
finally:
    shutil.rmtree(work, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "no model text reaches Ruby or a mise table but [tools]")
sys.exit(1 if fails else 0)
