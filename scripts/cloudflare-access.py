#!/usr/bin/python3
"""Refresh a Cloudflare Access header in git, from local config.

A subject may carry `.atlas/cloudflare-access.json`:

    {"app": "https://git.example.org", "subject": "projects/Example"}

`app` is the Access-protected host. `subject`, optional, is the directory the
header is for; with it, nothing runs while that directory is absent. The
git key is `http.<app>/.extraHeader` unless the file names one.

The header holds a short-lived application token. This first asks cloudflared
for the app's token, which it exchanges from the stored organization token, so
the header stays fresh while that session lives. When it cannot, and the
subject names an `email`, this runs cloudflare-email-login.py, which reads the
one-time PIN from that mailbox and signs in with no browser. A subject without
an `email` gets a notification instead.

    cloudflare-access.py [--config PATH]... [--say]

With no `--config`, every subject's `.atlas/cloudflare-access.json` is read.
`--say` prints one line per app; without it the run is silent, which is what
the LaunchAgent wants. The token is never printed or logged.

Stdlib only, 3.7-clean: setup-mac runs it under /usr/bin/python3.
"""

import base64
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

sys.dont_write_bytecode = True

HOME = os.path.expanduser("~")
ATLAS = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
STATE_DIR = os.environ.get("BOARD_STATE_DIR") or os.path.join(
    HOME, ".local", "state", "tutor-board")
STATE = os.path.join(STATE_DIR, "cloudflare-access.json")
SETUP_DIR = os.path.join(
    os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local", "state"),
    "atlas-setup")
LOG = os.path.join(SETUP_DIR, "cloudflare-access.log")
LOG_MAX = 2000000
PREFIX = "Cf-Access-Jwt-Assertion: "
RENEW_SECONDS = 3600
TOKEN_TIMEOUT = 60
NOTIFY_EVERY = 6 * 3600
EMAIL_LOGIN = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "cloudflare-email-login.py")
EMAIL_RETRY = 1800
EMAIL_BACKOFF = 6 * 3600


def now():
    return time.time()


def stamp(when=None):
    return datetime.fromtimestamp(when or now()).replace(
        microsecond=0).isoformat()


def log(line):
    try:
        os.makedirs(SETUP_DIR, exist_ok=True)
        if os.path.getsize(LOG) > LOG_MAX:
            os.replace(LOG, LOG + ".old")
    except OSError:
        pass
    try:
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("%s %s\n" % (stamp(), line))
    except OSError:
        pass


def read_state():
    try:
        with open(STATE, "r", encoding="utf-8") as fh:
            said = json.load(fh)
        if isinstance(said, dict) and isinstance(said.get("apps"), dict):
            return said
    except (OSError, ValueError):
        pass
    return {"apps": {}}


def write_state(said):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp = STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(said, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, STATE)
    except OSError as exc:
        log("could not write %s: %s" % (STATE, exc))


def notify(title, message):
    """A desktop notification, once the failure has lasted a while."""
    script = ('display notification "%s" with title "%s"'
              % (message.replace("\\", "\\\\").replace('"', '\\"'),
                 title.replace("\\", "\\\\").replace('"', '\\"')))
    try:
        subprocess.run(["osascript", "-e", script], timeout=15,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        pass


def git(*args):
    try:
        p = subprocess.run(["git"] + list(args), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True,
                           timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, "", str(exc)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def exp_of(token):
    """The token's `exp`, or None. Never raises."""
    try:
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)
        said = json.loads(base64.urlsafe_b64decode(part.encode("ascii")))
        return int(said.get("exp")) if said.get("exp") else None
    except (IndexError, ValueError, TypeError):
        return None


def configs(extra):
    if extra:
        return [os.path.abspath(os.path.expanduser(p)) for p in extra]
    out = []
    for base in ("courses", "projects"):
        out += sorted(glob.glob(os.path.join(
            ATLAS, base, "*", ".atlas", "cloudflare-access.json")))
    return out


def say(said, show):
    if show:
        print(said)


def refresh(path, show=False):
    """`(ok, said)` for one config file."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, ValueError) as exc:
        line = "%s: cannot read: %s" % (path, exc)
        log(line)
        say(line, show)
        return False, line
    if not isinstance(cfg, dict):
        line = "%s: not a JSON object" % path
        log(line)
        say(line, show)
        return False, line
    app = str(cfg.get("app") or "").strip().rstrip("/")
    if not app.startswith("https://"):
        line = "%s: `app` must be an https URL" % path
        log(line)
        say(line, show)
        return False, line
    subject = str(cfg.get("subject") or "").strip()
    if subject:
        where = os.path.join(ATLAS, subject)
        if not os.path.isdir(os.path.join(where, ".git")):
            line = "%s: %s is not cloned here; nothing to refresh" % (
                app, subject)
            log(line)
            say(line, show)
            return True, line
    key = str(cfg.get("git_key") or "http.%s/.extraHeader" % app)
    prefix = str(cfg.get("header") or PREFIX)
    renew = int(cfg.get("renew_minutes") or 60) * 60
    token_bin = shutil.which("cloudflared", path=os.environ.get(
        "PATH", "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"))
    if not token_bin:
        line = ("%s: cloudflared is not installed; run `brew install "
                "cloudflared`" % app)
        return fail(app, line, show)
    code, header, _ = git("config", "--global", "--get", key)
    current = header[len(prefix):] if code == 0 and header.startswith(prefix) \
        else ""
    current_exp = exp_of(current) if current else None
    if current_exp and current_exp - now() > renew:
        left = (current_exp - now()) / 3600.0
        line = "%s: fresh, %.1f h left" % (app, left)
        log(line)
        say(line, show)
        remember(app, True, current_exp, line)
        return True, line
    try:
        p = subprocess.run([token_bin, "access", "token", "--app=" + app],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, timeout=TOKEN_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        return fail(app, "%s: cloudflared did not answer (%s)" % (app, exc),
                    show)
    token = (p.stdout or "").strip()
    new_exp = exp_of(token) if p.returncode == 0 else None
    if p.returncode != 0 or not token or not new_exp or new_exp <= now():
        if email_login(path, app, key, prefix, show):
            code, header, _ = git("config", "--global", "--get", key)
            token = header[len(prefix):] if code == 0 and \
                header.startswith(prefix) else ""
            new_exp = exp_of(token) if token else None
            line = "%s: refreshed by email PIN, expires %s" % (
                app, stamp(new_exp))
            log(line)
            say(line, show)
            remember(app, True, new_exp, line)
            return True, line
        detail = (p.stderr or "").strip().splitlines()
        return fail(app, "%s: the Cloudflare session needs a login and the "
                    "email PIN bot could not take over: run "
                    "`cloudflared access login %s` in Terminal"
                    % (app, app) + (" (%s)" % detail[-1] if detail else ""),
                    show)
    if token == current and current_exp == new_exp:
        line = ("%s: app token still valid, %.0f min left; it refreshes "
                "after expiry" % (app, (new_exp - now()) / 60.0))
        log(line)
        say(line, show)
        remember(app, True, new_exp, line)
        return True, line
    code, _out, err = git("config", "--global", "--replace-all", key,
                          prefix + token)
    if code != 0:
        return fail(app, "%s: could not write the git header: %s" % (app, err),
                    show)
    line = "%s: refreshed, expires %s" % (app, stamp(new_exp))
    log(line)
    say(line, show)
    remember(app, True, new_exp, line)
    return True, line


def fail(app, line, show):
    log(line)
    say(line, show)
    said = read_state()
    old = (said.get("apps") or {}).get(app) or {}
    remember(app, False, None, line)
    when = old.get("notified_at") or 0
    if not old.get("ok", True) and now() - when < NOTIFY_EVERY:
        return False, line
    notify("Atlas: %s" % app, line)
    said = read_state()
    entry = said.setdefault("apps", {}).setdefault(app, {})
    entry["notified_at"] = now()
    write_state(said)
    return False, line


def remember(app, ok, exp, detail):
    said = read_state()
    entry = said.setdefault("apps", {}).setdefault(app, {})
    entry.update({"at": now(), "at_iso": stamp(), "ok": ok, "detail": detail})
    if exp:
        entry["exp"] = exp
        entry["exp_iso"] = stamp(exp)
    write_state(said)


def email_login(path, app, key, prefix, show):
    """Run the subject's email-PIN login. True when the header ends up fresh.

    Only a subject whose config names an `email` opts in. A cooldown keeps a
    broken mailbox from mailing a PIN on every run; three failures back off to
    the six-hour notification interval.
    """
    if not os.path.isfile(EMAIL_LOGIN):
        return False
    try:
        with open(path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, ValueError):
        return False
    if not isinstance(cfg, dict) or not cfg.get("email"):
        return False
    said = read_state()
    entry = said.setdefault("apps", {}).setdefault(app, {})
    last = entry.get("email_at") or 0
    streak = int(entry.get("email_fails") or 0)
    wait = EMAIL_RETRY if streak < 3 else EMAIL_BACKOFF
    if now() - last < wait:
        return False
    entry["email_at"] = now()
    write_state(said)
    p = None
    try:
        p = subprocess.run(
            [sys.executable, EMAIL_LOGIN, "--config", path, "--say"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as exc:
        log("%s: email login did not run (%s)" % (app, exc))
    if p is not None:
        for line in ((p.stdout or "") + (p.stderr or "")).splitlines():
            if line.strip():
                log("email: " + line.strip())
    code, header, _ = git("config", "--global", "--get", key)
    token = header[len(prefix):] if code == 0 and header.startswith(prefix) \
        else ""
    new_exp = exp_of(token) if token else None
    said = read_state()
    entry = said.setdefault("apps", {}).setdefault(app, {})
    if p is not None and p.returncode == 0 and new_exp and new_exp > now():
        entry["email_fails"] = 0
        write_state(said)
        return True
    entry["email_fails"] = streak + 1
    write_state(said)
    return False


def main(argv):
    show = "--say" in argv
    extra = []
    rest = [a for a in argv if a != "--say"]
    i = 0
    while i < len(rest):
        if rest[i] == "--config" and i + 1 < len(rest):
            extra.append(rest[i + 1])
            i += 2
            continue
        if rest[i] in ("-h", "--help"):
            print(__doc__.strip())
            return 0
        print("unknown option: %s" % rest[i], file=sys.stderr)
        return 2
    found = configs(extra)
    if not found:
        return 0
    bad = 0
    for path in found:
        ok, _line = refresh(path, show)
        if not ok:
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
