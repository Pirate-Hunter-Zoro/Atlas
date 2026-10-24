"""The board's routes, one module per family of paths.

Each module says whether it took the request. `NOT_MINE` is a sentinel, not
`False`, because a handled request returns `send_json`'s `None`.
"""

NOT_MINE = object()
