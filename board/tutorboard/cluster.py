"""cluster.py -- the names `sync.py` holds, re-exported until the LIBR exit
deletes this file. `Ear` is `sync.Sync`. Nothing new imports from here.
"""

from .sync import (CODE_PREFIX, EVERY, LS_TIMEOUT, NOTICES,  # noqa: F401
                   NOTICES_SERVED, PULL_STATE, PULL_TIMEOUT, STORE, Sync,
                   atlas_of, notices, notices_path, wake)

Ear = Sync
