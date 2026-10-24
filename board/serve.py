#!/usr/bin/env python3
"""The board, as a process: one listener serving every session at /s/<id>/.

    python3 serve.py [--port <n>] [--atlas <dir>]

Everything it does is `tutorboard/`; `tutorboard/server/app.py` is the start.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

# The stamp BEFORE the import: see `tutorboard/stamp.py`.
from tutorboard import stamp                      # noqa: E402
stamp.mark_loaded()
from tutorboard.server.app import main            # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
