"""Bothost compatibility entrypoint.

Production start is defined in Dockerfile CMD (supervisord all-in-one).
This file exists so Bothost language detection succeeds on deploy.
"""

from __future__ import annotations

if __name__ == "__main__":
    import os
    import subprocess
    import sys

    entrypoint = os.environ.get("BOTHOST_ENTRYPOINT", "/usr/local/bin/entrypoint.sh")
    if os.path.isfile(entrypoint):
        os.execv(entrypoint, [entrypoint])
    print("Entrypoint not found; expected custom Dockerfile CMD.", file=sys.stderr)
    sys.exit(1)
