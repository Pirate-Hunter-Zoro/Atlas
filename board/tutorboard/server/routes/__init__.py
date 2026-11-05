"""The board's routes, one module per family of paths.

Each module says whether it took the request. `NOT_MINE` is a sentinel, not
`False`, because a handled request returns `send_json`'s `None`.
"""

NOT_MINE = object()


def asked_subject(h):
    """The `?subject=` of this request, or None when it names none."""
    import urllib.parse
    query = urllib.parse.parse_qs(urllib.parse.urlparse(h.path or "").query)
    said = (query.get("subject") or [""])[0]
    return said or None


def doc_repo(h, repo, ident):
    """The Repo a session reads document `ident` through: the session's, or
    the subject the board names (`?subject=`) or its stored `doc` names
    (`sessions.reading`). None when that subject is none or lacks `ident`."""
    from ... import sessions                             # local: light
    try:
        return sessions.reading(repo, ident, asked_subject(h))
    except sessions.NotReadable:
        return None
