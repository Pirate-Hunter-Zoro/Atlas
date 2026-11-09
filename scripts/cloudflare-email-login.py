#!/usr/bin/python3
"""Log in to a Cloudflare Access app by reading its one-time PIN from email.

A subject's `.atlas/cloudflare-access.json` opts in by naming the mailbox:

    {"app": "https://git.example.org", "subject": "projects/Example",
     "email": "you@example.com", "imap_host": "imap.mail.me.com"}

This runs the same login a browser does, without the browser: it asks
Cloudflare to email a one-time PIN, waits for that mail over IMAP, submits the
code, and writes the resulting application token into the git header. The
password for IMAP is read from the login keychain, never from this file, and
the PIN, the token and the password are never printed or logged.

    cloudflare-email-login.py [--config PATH]... [--say] [--dry-run]
                              [--keep-email] [--timeout SECONDS]

With no `--config`, every subject's `.atlas/cloudflare-access.json` that names
an `email` is read. `--dry-run` discovers the login endpoint and stops before
any mail is sent. The header key and prefix match cloudflare-access.py.

Config keys beyond `app` and `subject`:

    email                 the mailbox Cloudflare sends the PIN to; required
    imap_host             default from the address's domain
    imap_port             default 993
    imap_folders          default ["INBOX", "Junk", "Junk Email"]
    imap_keychain_service default "atlas-cloudflare-imap"
    imap_keychain_account default the email address
    from_match            sender filter, default "cloudflare"
    delete_email          delete the PIN mail after use, default true
    git_key               default http.<app>/.extraHeader
    header                default "Cf-Access-Jwt-Assertion: "
    timeout               seconds to wait for the mail, default 180

Stdlib only, 3.7-clean: setup-mac runs it under /usr/bin/python3.
"""

import base64
import email
import email.header
import email.utils
import glob
import imaplib
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

sys.dont_write_bytecode = True

HOME = os.path.expanduser("~")
ATLAS = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SETUP_DIR = os.path.join(
    os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local", "state"),
    "atlas-setup")
LOG = os.path.join(SETUP_DIR, "cloudflare-email-login.log")
LOG_MAX = 2000000
PREFIX = "Cf-Access-Jwt-Assertion: "
DEFAULT_FOLDERS = ["INBOX", "Junk", "Junk Email"]
CODE_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")
CODE_FALLBACK_RE = re.compile(r"(?<!\d)(\d{4,8})(?!\d)")
TAG_RE = re.compile(r"<[^>]+>")
UA = "atlas-cloudflare-email-login/1"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
IMAP_HOSTS = {
    "icloud.com": "imap.mail.me.com",
    "me.com": "imap.mail.me.com",
    "mac.com": "imap.mail.me.com",
    "gmail.com": "imap.gmail.com",
    "googlemail.com": "imap.gmail.com",
    "outlook.com": "outlook.office365.com",
    "hotmail.com": "outlook.office365.com",
    "live.com": "outlook.office365.com",
    "yahoo.com": "imap.mail.yahoo.com",
}


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


def say(line, show=True):
    if show:
        print(line)


def b64url_json(part):
    """The JSON object inside one base64url segment, or {}."""
    try:
        part = part.replace("-", "+").replace("_", "/")
        part += "=" * (-len(part) % 4)
        said = json.loads(base64.b64decode(part.encode("ascii")))
        return said if isinstance(said, dict) else {}
    except (ValueError, TypeError):
        return {}


def exp_of(token):
    try:
        return int(b64url_json(token.split(".")[1]).get("exp"))
    except (IndexError, ValueError, TypeError):
        return None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def http(url, fields=None, timeout=30):
    """`(status, headers, body)` with redirects left alone. Never raises on 3xx."""
    headers = {"User-Agent": UA, "Accept": "text/html,*/*"}
    body = None
    if fields is not None:
        body = urllib.parse.urlencode(fields).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers,
                                 method="POST" if body is not None else "GET")
    try:
        res = _OPENER.open(req, timeout=timeout)
        return res.status, _headers(res.headers), res.read()
    except urllib.error.HTTPError as exc:
        return exc.code, _headers(exc.headers), exc.read()
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError("%s: %s" % (url, exc))


def _headers(raw):
    out = {}
    try:
        items = raw.items()
    except AttributeError:
        items = []
    for key, value in items:
        out[key.lower()] = value
    return out


def location(headers):
    return (headers.get("location") or "").strip()


def keychain(service, account):
    p = subprocess.run(
        ["/usr/bin/security", "find-generic-password",
         "-s", service, "-a", account, "-w"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, timeout=20)
    if p.returncode != 0 or not p.stdout.strip():
        raise RuntimeError(
            "no password for service %r account %r in the login keychain; "
            "store one with `security add-generic-password -U -a %r -s %r -w`"
            % (service, account, account, service))
    return p.stdout.rstrip("\n")


def imap_date(when):
    """An IMAP SEARCH date, in English, whatever the machine's locale."""
    t = time.gmtime(when)
    return "%02d-%s-%04d" % (t.tm_mday, MONTHS[t.tm_mon - 1], t.tm_year)


def imap_host_for(address, explicit):
    if explicit:
        return str(explicit)
    domain = address.rsplit("@", 1)[-1].lower()
    if domain in IMAP_HOSTS:
        return IMAP_HOSTS[domain]
    raise RuntimeError("no IMAP host known for %s; set imap_host in the "
                       "subject's cloudflare-access.json" % domain)


def _decode_part(part):
    payload = part.get_payload(decode=True) or b""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, "replace")
    except LookupError:
        return payload.decode("utf-8", "replace")


def message_text(msg):
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.get_content_type() == "text/plain":
            return _decode_part(part)
    for part in parts:
        if part.get_content_type() == "text/html":
            return TAG_RE.sub(" ", _decode_part(part))
    return ""


def message_subject(msg):
    try:
        return str(email.header.make_header(
            email.header.decode_header(msg.get("Subject") or "")))
    except (ValueError, TypeError):
        return str(msg.get("Subject") or "")


def message_time(msg):
    try:
        return email.utils.parsedate_to_datetime(msg.get("Date")).timestamp()
    except (TypeError, ValueError, IndexError):
        return None


def mailbox_password(cfg):
    """The IMAP app password, read before any mail is asked for."""
    address = cfg["email"]
    service = cfg.get("imap_keychain_service") or "atlas-cloudflare-imap"
    account = cfg.get("imap_keychain_account") or address
    return keychain(service, account)


def find_pin(cfg, since, show, password):
    """Wait for the PIN mail and return its code. Deletes it unless kept."""
    address = cfg["email"]
    host = imap_host_for(address, cfg.get("imap_host"))
    port = int(cfg.get("imap_port") or 993)
    folders = cfg.get("imap_folders") or DEFAULT_FOLDERS
    match = str(cfg.get("from_match") or "cloudflare").lower()
    delete = cfg.get("delete_email", True) is not False
    deadline = now() + int(cfg.get("timeout") or 180)
    ctx = ssl.create_default_context()
    searched = imap_date(since - 120)
    tried = set()
    conn = None
    try:
        while now() < deadline:
            if conn is None:
                conn = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
                conn.login(address, password)
            for folder in folders:
                typ, _ = conn.select(folder, readonly=not delete)
                if typ != "OK":
                    continue
                typ, data = conn.search(None, "SINCE %s" % searched)
                if typ != "OK" or not data or not data[0]:
                    continue
                for mid in reversed(data[0].split()):
                    key = (folder, mid)
                    if key in tried:
                        continue
                    tried.add(key)
                    typ, raw = conn.fetch(mid, "(RFC822)")
                    if typ != "OK" or not raw or not raw[0]:
                        continue
                    msg = email.message_from_bytes(raw[0][1])
                    when = message_time(msg)
                    if when is not None and when < since - 120:
                        continue
                    sender = str(msg.get("From") or "").lower()
                    if match and match not in sender:
                        continue
                    text = message_text(msg)
                    found = CODE_RE.search(text) or CODE_FALLBACK_RE.search(text)
                    if not found:
                        continue
                    code = found.group(1)
                    if delete:
                        conn.store(mid, "+FLAGS", "\\Deleted")
                        try:
                            conn.expunge()
                        except imaplib.IMAP4.error:
                            pass
                    return code
            time.sleep(5)
    except imaplib.IMAP4.error as exc:
        raise RuntimeError("IMAP login or search failed for %s: %s"
                           % (address, exc))
    except (ssl.SSLError, OSError) as exc:
        raise RuntimeError("cannot reach IMAP %s for %s: %s"
                           % (host, address, exc))
    finally:
        if conn is not None:
            try:
                conn.logout()
            except imaplib.IMAP4.error:
                pass
    raise RuntimeError("no Cloudflare PIN mail arrived within %d s; check "
                       "that %s is allowed on the Access app and that IMAP is "
                       "enabled" % (int(cfg.get("timeout") or 180), address))


def discover(app, timeout):
    """`(team, kid, hostname)` for the app's Cloudflare Access login."""
    status, headers, _body = http(app, timeout=timeout)
    loc = location(headers)
    if status not in (301, 302, 303, 307, 308) or "cloudflareaccess.com" not in loc:
        raise RuntimeError("%s did not redirect to Cloudflare Access (HTTP %s)"
                           % (app, status))
    url = urllib.parse.urlparse(loc)
    query = urllib.parse.parse_qs(url.query)
    meta_token = (query.get("meta") or [""])[0]
    segments = meta_token.split(".")
    meta = b64url_json(segments[1]) if len(segments) > 1 else {}
    kid = (query.get("kid") or [meta.get("aud") or ""])[0]
    host = meta.get("hostname") or url.path.rsplit("/", 1)[-1]
    if not kid or not host:
        raise RuntimeError("%s: could not read the Access login parameters" % app)
    return url.netloc, kid, host


def login(cfg, app, show, dry_run=False):
    """Do the whole PIN login and return the token."""
    team, kid, host = discover(app, 30)
    if dry_run:
        say("%s: login at %s for %s (kid %d chars)"
            % (app, team, host, len(kid)), show)
        return None
    password = mailbox_password(cfg)
    before = now()
    verify = "https://%s/cdn-cgi/access/verify-code/%s?%s" % (
        team, host, urllib.parse.urlencode({"kid": kid, "redirect_url": "/"}))
    status, headers, _body = http(verify, {
        "email": cfg["email"],
        "client_id": "",
        "connector_id": "",
        "connector_type": "",
        "redirect_url": "",
    })
    loc = location(headers)
    nonce = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query).get("nonce", [""])[0]
    if status not in (301, 302, 303, 307, 308) or not nonce:
        raise RuntimeError("%s: Cloudflare did not send a PIN (HTTP %s); check "
                           "that email is allowed on the Access app"
                           % (app, status))
    code = find_pin(cfg, before, show, password)
    status, headers, _body = http("https://%s/cdn-cgi/access/callback" % team,
                                  {"code": code, "nonce": nonce})
    loc = location(headers)
    parsed = urllib.parse.urlparse(loc)
    if status not in (301, 302, 303, 307, 308) or not loc:
        raise RuntimeError("%s: Cloudflare refused the PIN (HTTP %s)"
                           % (app, status))
    if parsed.path.startswith("/cdn-cgi/access/login/"):
        raise RuntimeError("%s: Cloudflare rejected the PIN; it may have "
                           "expired before it was read" % app)
    token = urllib.parse.parse_qs(parsed.query).get("token", [""])[0]
    if not token:
        token = authorization_cookie(headers)
    if not token or exp_of(token) is None:
        raise RuntimeError("%s: Cloudflare accepted the PIN but returned no "
                           "token" % app)
    return token


def authorization_cookie(headers):
    """The token from a Set-Cookie: CF_Authorization=... header, or ""."""
    found = re.search(r"CF_Authorization=([^;\s]+)", headers.get("set-cookie") or "")
    return found.group(1) if found else ""


def write_header(key, prefix, token):
    p = subprocess.run(["git", "config", "--global", "--replace-all",
                        key, prefix + token],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, timeout=30)
    if p.returncode != 0:
        raise RuntimeError("could not write the git header: %s"
                           % (p.stderr or "").strip())


def config_paths(extra):
    if extra:
        return [os.path.abspath(os.path.expanduser(p)) for p in extra]
    out = []
    for base in ("courses", "projects"):
        out += sorted(glob.glob(os.path.join(
            ATLAS, base, "*", ".atlas", "cloudflare-access.json")))
    return out


def refresh(path, show, dry_run, keep_email, timeout=None):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, ValueError) as exc:
        raise RuntimeError("%s: cannot read: %s" % (path, exc))
    if not isinstance(cfg, dict):
        raise RuntimeError("%s: not a JSON object" % path)
    if not cfg.get("email"):
        return None
    if timeout:
        cfg["timeout"] = timeout
    app = str(cfg.get("app") or "").strip().rstrip("/")
    if not app.startswith("https://"):
        raise RuntimeError("%s: `app` must be an https URL" % path)
    if keep_email:
        cfg["delete_email"] = False
    key = str(cfg.get("git_key") or "http.%s/.extraHeader" % app)
    prefix = str(cfg.get("header") or PREFIX)
    token = login(cfg, app, show, dry_run)
    if dry_run:
        return None
    write_header(key, prefix, token)
    say("%s: signed in by email PIN, expires %s"
        % (app, stamp(exp_of(token))), show)
    return token


def main(argv):
    show = "--say" in argv
    dry_run = "--dry-run" in argv
    keep_email = "--keep-email" in argv
    extra = []
    timeout = None
    skip = False
    for i, arg in enumerate(argv):
        if skip:
            skip = False
            continue
        if arg == "--config" and i + 1 < len(argv):
            extra.append(argv[i + 1])
            skip = True
            continue
        if arg == "--timeout" and i + 1 < len(argv):
            try:
                timeout = int(argv[i + 1])
            except ValueError:
                print("--timeout needs a number of seconds", file=sys.stderr)
                return 2
            skip = True
            continue
        if arg in ("--say", "--dry-run", "--keep-email"):
            continue
        if arg in ("-h", "--help"):
            print(__doc__.strip())
            return 0
        print("unknown option: %s" % arg, file=sys.stderr)
        return 2
    bad = 0
    for path in config_paths(extra):
        try:
            refresh(path, show, dry_run, keep_email, timeout)
        except RuntimeError as exc:
            log(str(exc))
            say(str(exc), show or dry_run)
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
