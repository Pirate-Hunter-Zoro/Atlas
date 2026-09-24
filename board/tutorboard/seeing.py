"""What is in this image, for an assistant that cannot see one.

`board see <path>` prints a description of a PNG, a JPEG or a page of a PDF.

WHY A BOARD SUBCOMMAND AND NOT A TOOL PROTOCOL. A subcommand is the one
interface every agent in the registry already has -- `board brief`, `board
recap`, `board write` -- so this needs no MCP, no adapter and no per-vendor
plumbing, and a new provider inherits it by existing. It is also the honest
fallback for the local model, which is the assistant that most needs it and the
one no hosted vision route may ever be handed a fenced file from.

WHERE THE IMAGE GOES IS A RECIPE FIELD, NOT A CONSTANT. A `vision` block on an
agent names either an endpoint, a model and a key, or a COMMAND to run on the
file -- a sighted assistant that is already installed needs no second provider
and no second key. The running agent's own recipe is asked first, and
`vision_agent` at the top of the config answers for the case where the agent
running the sitting has no eyes. Both come out of `tutor --agents --json`, which
is the registry, so there is no second table.

AND IT REFUSES A FENCED PATH BEFORE IT READS A BYTE. This sends a file to a
hosted provider, which is exactly what `ai-config/policy/phi.py` exists to stop
-- and a board subcommand does not go through any assistant's pre-tool hook. So
the check is here, first, by name, with the reason. Getting this wrong grows the
tool a documented route for sending session content to a third party.

Standard library only: `urllib.request`, a base64 data URL, no dependency.
"""

import base64
import json
import mimetypes
import os
import subprocess
import tempfile
import urllib.error
import urllib.request

from . import fenced, keys


# What the model is asked, when the caller asks nothing in particular. Written
# for the one thing this is for: a page of somebody's handwriting that a tutor
# has to read back and mark.
DEFAULT_ASK = (
    "Transcribe everything written or printed in this image, in reading order, "
    "and keep the layout of it -- line breaks, columns, what is crossed out. "
    "Mathematics as LaTeX. Then, in two or three sentences, say what the page "
    "IS: a worked solution, a problem sheet, a diagram, a photograph of a "
    "board. Do not solve anything and do not correct anything; report what is "
    "on the page."
)

# Poppler renders at this many pixels across. Wide enough that small handwriting
# survives, narrow enough that a base64 data URL of one page is not a megabyte
# of request body per page.
PAGE_WIDTH = 1600

TIMEOUT = 180

IMAGES = (".png", ".jpg", ".jpeg", ".webp", ".gif")


class Refused(Exception):
    """This path is not one this command may open, and the reason is the message."""


def registry():
    """`tutor --agents --json`, parsed, or {}. One subprocess, and it is fine.

    This is a command a person or an assistant runs occasionally, not a poll:
    `assistants.listing` caches it for the hub because the hub asks four times
    a second, and nothing here does.
    """
    from .server import spawn
    code, out = spawn.tutor_cli(["--agents", "--json"], timeout=30)
    if code != 0:
        return {}
    try:
        return json.loads(out.strip().splitlines()[-1]) or {}
    except (ValueError, IndexError):
        return {}


def route(agent=None, table=None):
    """Where an image goes, as `(settings, why-there-is-none)`.

    The running agent's own recipe first, then `vision_agent`. A recipe with
    eyes of its own is still asked FIRST rather than skipped: `board see` is
    also how a person checks the route, and answering from somebody else's
    recipe when this one names its own would be a lie about what happens.

    A ROUTE THROUGH A PROVIDER THAT IS STOOD DOWN IS NOT A ROUTE. The same
    hostname that drops a tutor's turns drops its vision request, and the
    stand-down a failed turn already wrote is the evidence -- so the next name
    on the list answers instead, and where none can, the refusal says which
    host went dark rather than sending a page at it to find out again.
    """
    from .net import egress
    table = registry() if table is None else table
    agents = {a.get("name"): a for a in (table.get("agents") or [])}
    tried, dark = [], []
    for name in (agent, table.get("vision_agent"), table.get("default")):
        if not name or name in tried:
            continue
        tried.append(name)
        got = (agents.get(name) or {}).get("vision")
        if not got or not (got.get("endpoint") or got.get("cmd")):
            continue
        stood = egress.stood_down(name)
        if stood:
            dark.append("'%s' is stood down (%s)"
                        % (name, stood["host"] and
                           "%s does not answer from this machine" % stood["host"]
                           or stood["why"]))
            continue
        return dict(got, agent=name), None
    if dark:
        return None, ("every vision route on this machine is stood down: %s. "
                      "A sighted assistant can open the file itself."
                      % "; ".join(dark))
    return None, ("no assistant on this machine names a vision route. Put a "
                  "`vision` block -- an endpoint or a command, and a model -- "
                  "on a recipe in the config, or name one in `vision_agent`.")


def _data_url(path):
    kind = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as fh:
        return "data:%s;base64,%s" % (
            kind, base64.b64encode(fh.read()).decode("ascii"))


def pages(path, page=None, width=PAGE_WIDTH):
    """The image files to send: the file itself, or a PDF's pages rendered.

    A temporary directory comes back with them and is the caller's to remove --
    returned rather than cleaned up here, because the files have to outlive this
    call by exactly as long as it takes to read them.
    """
    low = path.lower()
    if low.endswith(IMAGES):
        return [path], None
    if not low.endswith(".pdf"):
        raise Refused("%s is neither an image nor a PDF; `board see` reads "
                      "%s and .pdf" % (path, ", ".join(IMAGES)))
    from .course import paper
    env = paper.raster_env()
    tool = paper.renderer(env)
    if not tool:
        raise Refused("this machine has no page renderer -- pdftoppm, "
                      "pdftocairo or Ghostscript -- so a PDF cannot be turned "
                      "into something to look at. An image works.")
    box = tempfile.mkdtemp(prefix="board-see-")
    first = int(page or 1)
    name = tool[0]
    prefix = os.path.join(box, "page")
    if name in ("pdftoppm", "pdftocairo"):
        cmd = [name, "-png", "-scale-to-x", str(width), "-scale-to-y", "-1",
               "-f", str(first), "-l", str(first), path, prefix]
    else:
        cmd = ["gs", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
               "-sDEVICE=png16m", "-r%d" % max(72, int(width / 8.27)),
               "-dFirstPage=%d" % first, "-dLastPage=%d" % first,
               "-sOutputFile=%s-%%d.png" % prefix, path]
    subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=300)
    got = sorted(os.path.join(box, f) for f in os.listdir(box)
                 if f.lower().endswith(".png"))
    if not got:
        raise Refused("page %d of %s did not render; is the page there?"
                      % (first, path))
    return got, box


def ask(settings, images, prompt):
    """The answer, however this route is spelt. The text, or raises Refused.

    Two spellings, because a vision route is a recipe field and recipes are not
    all endpoints. `cmd` runs a sighted assistant that is already installed and
    hands it the file; `endpoint` is one HTTP request in the OpenAI
    chat-completions shape -- not an agent loop and not a conversation, which is
    why it is `/v1/chat/completions` rather than the Anthropic-format endpoint
    the same recipe drives a whole tutor through.
    """
    if settings.get("cmd"):
        return _ask_command(settings, images, prompt)
    need = settings.get("needs_key")
    key = keys.get(need) if need else None
    if need and not key:
        raise Refused("%s is not in %s, so there is nothing to authenticate "
                      "with. One `%s=...` line in that file is the whole of "
                      "the setup.%s"
                      % (need, keys.store(), need,
                         ("\n" + keys.why_not()) if keys.why_not() else ""))
    content = [{"type": "text", "text": prompt}]
    for img in images:
        content.append({"type": "image_url",
                        "image_url": {"url": _data_url(img)}})
    body = json.dumps({
        "model": settings.get("model"),
        "messages": [{"role": "user", "content": content}],
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        settings["endpoint"], data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer %s" % key} if key
        else {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            got = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise Refused("%s answered %s: %s" % (settings["endpoint"],
                                              exc.code, detail.strip()))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        # AND THE FINDING IS WRITTEN DOWN, so the next page is not sent at a
        # host that has just refused a connection. This is the same stand-down a
        # failed turn writes, on the same record and per agent, which is what
        # makes `route` able to pass over this recipe and answer from another.
        from .net import egress
        from urllib.parse import urlsplit
        host = urlsplit(settings["endpoint"]).hostname or ""
        if settings.get("agent") and egress.egress_ok():
            egress.mark_unreachable(settings["agent"], host)
        raise Refused("%s could not be reached: %s"
                      % (settings["endpoint"], exc))
    try:
        said = got["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise Refused("the answer had no text in it: %s"
                      % json.dumps(got)[:400])
    return (said or "").strip()


def _ask_command(settings, images, prompt):
    """A sighted assistant that is already installed, run once on these files.

    WHY A COMMAND IS A VISION ROUTE AT ALL. The models that teach here can see;
    what a hosted `/chat/completions` route buys is a SECOND provider, a second
    key and a model name that goes stale, for a job the binary on the path does
    already. So a recipe may name a command instead of an endpoint, and the
    fallback route on a machine is then whatever assistant it teaches with.

    RUN IN THE IMAGE'S OWN DIRECTORY, AND THE FILE ASKED FOR BY NAME. A headless
    turn has nobody to approve reading a path outside its working directory, and
    a refused read does not fail -- the model answers from the filename and
    sounds certain, which is the one outcome worse than an error. Every rendered
    page of a PDF lands in one temporary directory, so one directory always
    covers them.

    The answer is stdout. `{prompt}` in the command is the question with the
    filenames in it; nothing is put on the command line that is not already a
    path on this machine.
    """
    box = os.path.dirname(os.path.abspath(images[0])) or "."
    names = ", ".join(os.path.basename(p) for p in images)
    said = ("%s\n\nThe image is the file %s in this directory. Read it and "
            "answer about what is in it. Do not answer from the filename."
            % (prompt, names) if len(images) == 1 else
            "%s\n\nThe images are the files %s in this directory, in that "
            "order. Read them and answer about what is in them. Do not answer "
            "from the filenames." % (prompt, names))
    cmd = [a.replace("{prompt}", said) for a in settings["cmd"]]
    try:
        done = subprocess.run(cmd, cwd=box, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=TIMEOUT)
    except FileNotFoundError:
        raise Refused("`%s` is not on the path here, and it is the vision route "
                      "this machine names" % cmd[0])
    except subprocess.TimeoutExpired:
        raise Refused("`%s` did not answer within %d s" % (cmd[0], TIMEOUT))
    except OSError as exc:
        raise Refused("`%s` could not be run: %s" % (cmd[0], exc))
    out = (done.stdout or b"").decode("utf-8", "replace").strip()
    if done.returncode != 0 or not out:
        why = (done.stderr or b"").decode("utf-8", "replace").strip()[:400]
        raise Refused("`%s` exited %d and said nothing about the page%s"
                      % (cmd[0], done.returncode, (": " + why) if why else ""))
    return out


def describe(path, page=None, prompt=None, agent=None, table=None, root=None):
    """What is in this file, as text. Raises `Refused` with the reason.

    THE FENCE IS THE FIRST THING AND NOT THE SECOND. Nothing is opened, nothing
    is rendered and nothing leaves the machine for a path inside one -- see
    `fenced.refused_in`, which is the workspace-relative rule, and the note
    there for why it is that one rather than the any-depth `refused`: the slate
    pages this command exists to read live in the board's own `live/inbox/`.
    """
    path = os.path.abspath(os.path.expanduser(str(path or "")))
    hit = (fenced.refused_in(root, path) if root else fenced.refused(path))
    if hit:
        raise Refused(
            "%s is inside `%s/`, which is fenced -- and `board see` sends a "
            "file to a hosted provider. Nothing in there may leave this "
            "machine. The local model reads it where it sits; see the "
            "`private` recipe in `tutor --agents`." % (path, hit))
    if not os.path.isfile(path):
        raise Refused("there is no file at %s" % path)
    settings, why = route(agent, table)
    if not settings:
        raise Refused(why)
    images, box = pages(path, page)
    try:
        return ask(settings, images, prompt or DEFAULT_ASK), settings
    finally:
        if box:
            for f in os.listdir(box):
                try:
                    os.remove(os.path.join(box, f))
                except OSError:
                    pass
            try:
                os.rmdir(box)
            except OSError:
                pass
