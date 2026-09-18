"""Support `python -m rich_help`."""

from __future__ import annotations

import sys

from .cli import entrypoint

if __name__ == "__main__":
    sys.exit(entrypoint())
