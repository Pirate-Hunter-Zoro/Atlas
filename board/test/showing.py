#!/usr/bin/env python3
"""A figure the pipeline made, on the glass -- and nothing else out of the tree.

    `results/counterfactual_pipeline/<contrast>/propensity_by_arm.png` exists
    and cannot be put on the board. `reading.py` offers PDFs only and refuses
    `results` by name; nothing serves an image out of a workspace. The only
    route a figure had to a lesson was somebody copying it into
    `live/inbox/uploads/` -- a second copy of a file the next job overwrites.

Opening a route into a workspace's own directories is the largest of these
changes and the one with the most ways to go wrong, so this suite is about what
must NOT happen rather than about the figure arriving.

Four things, and each of them is a way the feature turns into a defect:

  * A PATH FROM A BROWSER NEVER REACHES A FILESYSTEM. What arrives is an id,
    compared against the ids of the figures discovery actually found. Same rule
    as `reading.find` and `walk.resolve`, and the same reason: the alternative
    is a query parameter carrying a repo-relative path, which is a traversal
    waiting to be written.

  * THE FENCE HOLDS HERE TOO. `research/PSYCH-ASR/phi/` is session content, and
    a route that serves images out of a workspace is the second place that has
    to be refused by name. `tutorboard/fenced.py` is the one list.

  * IT IS BOUNDED. TRD-EHR's results tree holds 676 PNGs. A drawer is not a file
    manager and a payload polled four times a second is not a directory walk.

  * AND IT IS NOT CACHED. A figure is rebuilt at the same name by the next job,
    so a cached one is last week's result wearing this week's label -- which is
    the one failure a figure on a board must not have, because it is being
    looked at in order to decide something.
"""

import json
import os
import re
import shutil
import socket
import struct
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zlib
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard import fenced, sense                              # noqa: E402
from tutorboard.course import results, repo as course_repo        # noqa: E402
from tutorboard.server.handler import Handler                     # noqa: E402
from tutorboard.server.hub import Hub                             # noqa: E402
from tutorboard.server.tikz import TikzWorker                     # noqa: E402

fails = []


def check(label, cond):
    print(("ok   " if cond else "FAIL ") + label)
    if not cond:
        fails.append(label)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def get(port, path):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path))
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def png_bytes(width=64, height=64):
    """A real PNG, big enough to clear the size floor.

    Written out here rather than drawn: this suite is about the route and the
    refusals, and needing matplotlib to test them would mean they never run.
    Noise rather than a flat colour, because a flat one compresses to a couple
    of hundred bytes and the size floor would refuse it -- which would be the
    suite testing its own fixture.
    """
    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload
                + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF))
    head = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + os.urandom(width * 3) for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head)
            + chunk(b"IDAT", zlib.compress(raw, 1)) + chunk(b"IEND", b""))


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


BIG = png_bytes()


# ---------------------------------------------------------------------------
# a workspace shaped like the one this is for
# ---------------------------------------------------------------------------
TMP = tempfile.mkdtemp(prefix="showing-")
WS = os.path.join(TMP, "TRD-EHR")
os.makedirs(WS)
with open(os.path.join(WS, "tutorboard.json"), "w", encoding="utf-8") as fh:
    json.dump({"name": "TRD-EHR"}, fh)

# The figure this change exists for, written once per contrast under the SAME
# filename -- which is the reason an id cannot come from a basename.
for contrast in ("bupropion_vs_ssri", "bupropion_vs_snri", "snri_vs_ssri"):
    write(os.path.join(WS, "results", "counterfactual_pipeline", contrast,
                       "propensity_by_arm.png"), BIG)
write(os.path.join(WS, "figures", "roc_curve.png"), BIG)
write(os.path.join(WS, "tables", "table_one.png"), BIG)

# And everything that must not be offered.
write(os.path.join(WS, "results", "phi", "turn_table.png"), BIG)
write(os.path.join(WS, "results", "cohort", "raw", "waveform.png"), BIG)
write(os.path.join(WS, "notebooks", "scratch.png"), BIG)          # not a result dir
write(os.path.join(WS, "results", "spacer.png"), b"\x89PNG\r\n\x1a\ntiny")
write(os.path.join(WS, "results", "summary.csv"), b"a,b\n1,2\n")
write(os.path.join(WS, "results", "deep", "a", "b", "c", "buried.png"), BIG)

repo = course_repo.Repo(WS)
with open(repo.state_path, "w", encoding="utf-8") as fh:
    json.dump({"course": "TRD-EHR"}, fh)

results._cache.clear()
found = results.figures(WS)
ids = [f["id"] for f in found]
rels = [f["rel"] for f in found]


# ---------------------------------------------------------------------------
# 1. what is offered, and what is not
# ---------------------------------------------------------------------------
print("\n-- an allowlist of trees, and a fence behind it --")

check("the figure this exists for is offered",
      [r for r in rels if r.endswith("counterfactual_pipeline/"
                                     "bupropion_vs_ssri/propensity_by_arm.png")])
check("and so is one in each of the other result directories",
      "figures/roc_curve.png" in rels and "tables/table_one.png" in rels)
check("a picture outside the result directories is not a result",
      not [r for r in rels if "notebooks" in r])

check("A FENCED DIRECTORY IS REFUSED INSIDE AN ALLOWED TREE",
      not [r for r in rels if "/phi/" in r])
check("and at any depth under one, not only at the top",
      not [r for r in rels if "/raw/" in r])
check("which is the same list the manuscript factory refuses",
      fenced.refused("results/phi/turn_table.png")
      and fenced.refused("results/cohort/raw/waveform.png")
      and not fenced.refused("results/counterfactual_pipeline/x.png"))

check("a file too small to be a plot is not offered",
      not [r for r in rels if "spacer" in r])
check("and neither is something that is not a picture at all",
      not [r for r in rels if r.endswith(".csv")])
check("a figure buried deeper than a result is not offered",
      not [r for r in rels if "buried" in r])


# ---------------------------------------------------------------------------
# 2. the id: unique, and the same one tomorrow
# ---------------------------------------------------------------------------
print("\n-- an id is what a card keeps, so it is stable and it is unique --")

three = [f for f in found if f["rel"].endswith("propensity_by_arm.png")]
check("three figures written under one filename get three ids",
      len(three) == 3 and len(set(f["id"] for f in three)) == 3)
check("and each says which one it is, because the drawer shows three rows",
      sorted(f["where"] for f in three) == [
          "counterfactual_pipeline/bupropion_vs_snri",
          "counterfactual_pipeline/bupropion_vs_ssri",
          "counterfactual_pipeline/snri_vs_ssri"])
check("an id is a function of the path and nothing else, so a card written "
      "today still resolves next month",
      results.ident("results/a/b.png") == results.ident("results/a/b.png")
      and results.ident("results/a/b.png") != results.ident("results/c/b.png"))
check("and a path too long to fit in one is still uniquely named",
      len(results.ident("results/" + "x" * 300 + "/plot.png")) <= results.MAX_ID
      and results.ident("results/" + "x" * 300 + "/plot.png")
      != results.ident("results/" + "y" * 300 + "/plot.png"))
check("every id is one the route will accept",
      all(re.match(r"^[a-z0-9-]{1,%d}$" % results.MAX_ID, i) for i in ids))


# ---------------------------------------------------------------------------
# 3. bounded, in both directions
# ---------------------------------------------------------------------------
print("\n-- bounded, because a results tree has hundreds in it --")

for i in range(60):
    write(os.path.join(WS, "results", "many", "plot_%02d.png" % i), png_bytes())
results._cache.clear()
lots = results.figures(WS)
check("a drawer is offered %d figures and no more" % results.MAX_FIGURES,
      len(lots) == results.MAX_FIGURES)
check("newest first, because the one being asked about is the one that changed",
      all(lots[i]["at"] >= lots[i + 1]["at"] for i in range(len(lots) - 1)))
check("so what the cap drops is the oldest, not an arbitrary two dozen",
      not [f for f in lots if f["rel"].endswith("table_one.png")])
# Taken away again, so the sections below are about a workspace with figures in
# it rather than about the flood.
shutil.rmtree(os.path.join(WS, "results", "many"))
results._cache.clear()

started = time.time()
results._cache.clear()
results.figures(WS)
first = time.time() - started
started = time.time()
results.figures(WS)
check("and the answer is remembered rather than re-walked on every payload",
      time.time() - started < max(first, 0.001))
check("for the same window as every other discovery on this board",
      results.CACHE_SECONDS == 30)


# ---------------------------------------------------------------------------
# 4. a real board, and a name from a browser
# ---------------------------------------------------------------------------
print("\n-- the client names an id; it never names a path --")

worker = TikzWorker(repo)
hub = Hub(repo, worker)
hub.payload = json.dumps({})
PORT = free_port()
httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
httpd.daemon_threads = True
httpd.repo = repo
httpd.hub = hub
threading.Thread(target=httpd.serve_forever, daemon=True).start()

real = [f for f in results.figures(WS)
        if f["rel"].endswith("bupropion_vs_ssri/propensity_by_arm.png")]
check("the figure this change exists for has an id to ask for", bool(real))
if real:
    status, heads, body = get(PORT, "/result/" + real[0]["id"])
    check("an id the workspace offers is served, as a picture",
          status == 200 and body.startswith(b"\x89PNG")
          and heads.get("Content-Type") == "image/png")
    check("and not with a cache header, because the next job overwrites it",
          "max-age" not in (heads.get("Cache-Control") or ""))

for evil in ("/result/../../../../etc/passwd",
             "/result/..%2f..%2fetc%2fpasswd",
             "/result/results/summary.csv",
             "/result/" + "a" * 200,
             "/result/PROPENSITY_BY_ARM",
             "/result/propensity_by_arm.png",
             "/result/",
             "/result/nothing-by-that-name"):
    status, _h, _b = get(PORT, evil)
    check("refused: %s" % evil, status == 404)

# A figure that IS on disk, inside a fenced directory, asked for by the id it
# would have had. The refusal is the fence and not the lookup failing by luck.
status, _h, _b = get(PORT, "/result/" + results.ident("results/phi/turn_table.png"))
check("and an id naming a figure inside the fence is refused too", status == 404)


# ---------------------------------------------------------------------------
# 5. the payload, the briefing, and the cache rule
# ---------------------------------------------------------------------------
print("\n-- what the board is told, and what the tutor is told --")

built = hub.build()
check("the board's payload carries the figures", bool(built.get("results"))
      and len(built["results"]["figures"]) == len(results.figures(WS)))
check("each with a name, a place and a date the drawer can show",
      all(f.get("name") and f.get("iso") is not None
          for f in built["results"]["figures"]))
check("and never with the path, because the board addresses one by id",
      all("rel" not in f for f in built["results"]["figures"]))

line = sense.results_sense(repo)
check("a tutor is told the figures exist and how to put one in a card",
      "/result/" in line and real and real[0]["id"] in line)
check("and told a figure is something to ask about rather than an explanation",
      "under it" in line.lower())
check("and never handed the address of one inside the fence",
      results.ident("results/phi/turn_table.png") not in line)

empty = os.path.join(TMP, "Galois-Theory")
os.makedirs(os.path.join(empty, "chapters"))
check("a workspace with no results sends nothing rather than an empty group",
      results.status(type("R", (), {"root": empty})()) is None
      and sense.results_sense(type("R", (), {"root": empty})()) == "")

sw = open(os.path.join(ROOT, "web", "sw.js"), encoding="utf-8").read()
live = re.search(r"var LIVE = /(.+)/;", sw)
check("the service worker sends the figure route to the network, always",
      bool(live) and re.match(live.group(1), "/result/anything"))
check("which is the rule it already has for a document rebuilt at one name",
      bool(live) and re.match(live.group(1), "/download/homework"))
check("and the shell version was bumped, or the app serves its cached copy",
      'VERSION = "board-shell-v' in sw)


# ---------------------------------------------------------------------------
# 6. BROWSING THEM -- the other half, and the one somebody asked for
# ---------------------------------------------------------------------------
# The drawer above puts ONE figure in a card. The ask was the other question:
#
#     "I want to be able to see the figures and results from this task --
#     there's no easy way for me to browse through results and figures in this
#     interface."
#
# A mission's card had just ended by naming what it wrote -- a figure and four
# tables, under a directory -- and the only way to look at any of it was a
# terminal. So the library page grew a second list, and this is what it must
# and must not do. Same walk, same allowlist, same fence, same ids: what is new
# is the tables, the grouping, and reading a table back for a page that cannot
# open a file.
print("\n-- everything this workspace produced, browsable, and still fenced --")


def text(path, said):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(said)


# The mission's own shape: a figure and four tables in one directory, written
# after everything else in the tree.
SWEEP = os.path.join(WS, "results", "neighbor_count_sweep")
write(os.path.join(SWEEP, "neighbor_count_sweep.png"), BIG)
text(os.path.join(SWEEP, "sweep_curve.csv"),
     "alpha,n_neighbors,roc_auc\n"
     + "".join("1.0,%d,0.%03d\n" % (k, k) for k in range(1, 501)))
text(os.path.join(SWEEP, "sweep_intervals.csv"), "k,lo,hi\n40,0.61,0.66\n")
text(os.path.join(SWEEP, "sweep_summary.json"),
     '{"n_anchors": 8516, "best_k": 40}')
text(os.path.join(SWEEP, "what_it_found.md"), "# what the sweep found\n\nk=40.\n")
# And a table inside the fence, which must be as refused as the picture was.
text(os.path.join(WS, "results", "phi", "turn_table.csv"), "patient,turn\n1,hi\n")

results.forget()
made = results.browse(repo)
rows = [r for g in made["groups"] for r in g["figures"] + g["tables"]]
wheres = [g["where"] for g in made["groups"]]
sweep = [g for g in made["groups"] if g["where"] == "neighbor_count_sweep"]

# ---- found by walking, and declared nowhere ----
check("a directory nobody registered is on the list because it is on disk",
      bool(sweep))
check("and there is no list anywhere in the workspace naming it -- the only "
      "file that could have declared it does not",
      "neighbor_count_sweep" not in open(
          os.path.join(WS, "tutorboard.json"), encoding="utf-8").read())
check("the figure the card names is in it, under the filename the card used",
      bool(sweep) and "neighbor_count_sweep.png" in
      [f["file"] for f in sweep[0]["figures"]])
check("and so are its four tables, which are a separate list from the figures",
      bool(sweep) and sorted(t["file"] for t in sweep[0]["tables"]) == [
          "sweep_curve.csv", "sweep_intervals.csv", "sweep_summary.json",
          "what_it_found.md"])
check("the directory that changed last is the first group, because that is "
      "the result somebody has come to look at",
      wheres and wheres[0] == "neighbor_count_sweep")
check("and a row never carries the path, because the board addresses one by id",
      rows and all("rel" not in r for r in rows))
check("a table says what it is on disk rather than what anybody assumed",
      sorted(set(t["format"] for g in made["groups"] for t in g["tables"]))
      == ["csv", "json", "md"])

# ---- THE FENCE, BY NAME, ON BOTH KINDS ----
check("A FENCED DIRECTORY IS IN NO GROUP ON THE BROWSE LIST",
      not [w for w in wheres if "phi" in w.split("/")])
check("and neither its picture nor its table is a row anywhere on it",
      not [r for r in rows if r["file"] in ("turn_table.png",
                                            "turn_table.csv")])
check("the fenced table cannot be read back by the id it would have had",
      results.table(WS, results.ident("results/phi/turn_table.csv"))
      .get("ok") is not True)
check("nor by the route, which answers 404 rather than an empty table",
      get(PORT, "/library/table/"
          + results.ident("results/phi/turn_table.csv"))[0] == 404)
check("and the refusal is the one list, matched on the NAME at any depth",
      fenced.refused("results/phi/turn_table.csv")
      and "phi" in fenced.NEVER)

# ---- a picture, over the route the drawer already uses ----
shot = sweep[0]["figures"][0] if sweep and sweep[0]["figures"] else {}
status, heads, body = get(PORT, "/result/" + (shot.get("id") or "x"))
check("tapping the figure on the browse list serves the picture",
      status == 200 and body.startswith(b"\x89PNG")
      and heads.get("Content-Type") == "image/png")

# A FIGURE PAST THE DRAWER'S TWO DOZEN IS STILL ON THE PAGE, so the route has
# to resolve it. `MAX_FIGURES` is a cap on what a CARD is offered; a page that
# lists four hundred and 404s three hundred and seventy-six of them is worse
# than one that lists none.
for i in range(results.MAX_IN_GROUP + 10):
    write(os.path.join(WS, "results", "lots", "plot_%02d.png" % i), png_bytes())
results.forget()
flood = results.browse(repo)
drawer = set(f["id"] for f in results.figures(WS))
listed = [r for g in flood["groups"] for r in g["figures"]]
past = [f for f in listed if f["id"] not in drawer]
check("the browse list is not capped at the drawer's two dozen",
      len(listed) > results.MAX_FIGURES and bool(past))
check("and a figure past that cap is served rather than 404ed",
      get(PORT, "/result/" + past[0]["id"])[0] == 200)
check("a group still says how many rows it is not showing, because a silent "
      "cap reads as *this is all there is*",
      any(g["more"] for g in flood["groups"] if g["where"] == "lots"))
shutil.rmtree(os.path.join(WS, "results", "lots"))
results.forget()

# ---- a table, read back rather than downloaded ----
by_file = {}
for g in results.browse(repo)["groups"]:
    for t in g["tables"]:
        by_file[t["file"]] = t
check("every table written into the sweep directory is addressable",
      set(by_file) >= {"sweep_curve.csv", "sweep_summary.json",
                       "what_it_found.md"})
# A missing one is a FAILED check above and an unreadable id below, rather than
# a traceback: a suite that dies at the first hole stops saying what else broke.
by_file.setdefault("sweep_curve.csv", {"id": "-"})
by_file.setdefault("sweep_summary.json", {"id": "-"})
by_file.setdefault("what_it_found.md", {"id": "-"})

def read_back(which):
    """One table over the route, as the page would get it."""
    status, _h, body = get(PORT, "/library/table/" + by_file[which]["id"])
    try:
        return status, json.loads(body.decode("utf-8"))
    except ValueError:
        return status, {}


status, sheet = read_back("sweep_curve.csv")
check("a CSV comes back as columns and rows rather than as a download",
      status == 200 and sheet.get("shape") == "rows"
      and sheet.get("columns") == ["alpha", "n_neighbors", "roc_auc"])
check("bounded, and it says how much of the file it is showing",
      len(sheet.get("rows") or []) == results.MAX_ROWS
      and sheet.get("more") == 500 - results.MAX_ROWS)
check("a JSON one comes back as text, because it is not rows",
      read_back("sweep_summary.json")[1].get("shape") == "text")
check("and it is the numbers that are in the file",
      "8516" in (read_back("sweep_summary.json")[1].get("text") or ""))
check("a markdown one comes back as what it says",
      "what the sweep found" in
      (read_back("what_it_found.md")[1].get("text") or ""))

check("a figure id is not a table, and the table route says so",
      get(PORT, "/library/table/" + shot["id"])[0] == 404)
check("and a table id is not a figure, so the picture route refuses it too",
      get(PORT, "/result/" + by_file["sweep_curve.csv"]["id"])[0] == 404)
for evil in ("/library/table/../../../../etc/passwd",
             "/library/table/..%2f..%2fetc%2fpasswd",
             "/library/table/results/summary.csv",
             "/library/table/",
             "/library/table/nothing-by-that-name"):
    check("refused: %s" % evil, get(PORT, evil)[0] == 404)

# ---- the whole payload, over the route the page fetches ----
status, _h, body = get(PORT, "/library/results.json")
try:
    page = json.loads(body.decode("utf-8"))
except ValueError:
    page = {}
check("the library page's own fetch answers with the groups",
      status == 200 and page.get("ok") is True and bool(page.get("groups")))
check("and says which directories it looked in, so *nothing here* is checkable",
      sorted(page.get("looked") or []) == ["figures", "results", "tables"])

# ---- AND AN EMPTY ONE EXPLAINS ITSELF ----
check("a workspace with no results says why rather than drawing an empty box",
      results.browse(type("R", (), {"root": empty})()).get("why", "")
      .startswith("This workspace has no results directory"))
check("and names where a job would have to write for one to appear",
      "results/" in results.browse(type("R", (), {"root": empty})())["why"])

# A workspace whose output is session content -- PSYCH-ASR's own shape, a
# top-level `phi/` and no results directory. The empty page must NAME the fence
# rather than reading as a workspace that has never run anything.
sealed = os.path.join(TMP, "PSYCH-ASR")
write(os.path.join(sealed, "phi", "stage1", "turn_table.png"), BIG)
text(os.path.join(sealed, "phi", "stage1", "turns.csv"), "patient,turn\n1,hi\n")
fenced.forget()
results.forget()
shut = results.browse(type("R", (), {"root": sealed})())
check("a workspace that holds a fence has it NAMED on the page, so an empty "
      "list cannot pass for a workspace with nothing in it",
      not shut["groups"] and shut["fenced"] == ["phi"]
      and "`phi/`" in shut["why"])
check("and nothing inside it is listed, whichever kind of file it is",
      not [r for g in shut["groups"] for r in g["figures"] + g["tables"]]
      and not results.index(sealed))
check("nor readable by the id it would have had, either kind",
      results.find(sealed, results.ident("phi/stage1/turn_table.png"))[0] is None
      and results.table(sealed, results.ident("phi/stage1/turns.csv"))
      .get("ok") is not True)

check("the service worker sends the table route to the network too, because a "
      "job rewrites a result under the name it already had",
      bool(live) and re.match(live.group(1), "/library/table/anything")
      and re.match(live.group(1), "/library/results.json"))

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a figure goes on the glass, every result is browsable, and the tree "
      "stays where it is")
