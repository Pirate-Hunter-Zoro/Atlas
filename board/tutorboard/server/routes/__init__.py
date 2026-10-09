"""The board's routes, one module per family of paths.

Each module here answers for one family and says whether it took the request.
`NOT_MINE` is that answer, and it is a sentinel rather than `False` because a
route that handled a request returns whatever `send_json` returned, which is
`None` -- and `None` cannot mean both "handled" and "not mine".
"""

NOT_MINE = object()
