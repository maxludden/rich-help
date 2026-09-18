"""Command-line entry point."""

from __future__ import annotations

import argparse
import os
import sys

from rich.console import Console

from .acquire import acquire
from .render import render_to
from .theme import THEMES


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="rich-help",
        description="Format and colorize command help pages.",
        epilog=(
            "examples:\n  rich-help curl\n  rich-help git commit\n  mytool --help | rich-help\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("command", nargs="*", help="command (and subcommand) to get help for")
    ap.add_argument("--theme", choices=sorted(THEMES), default="dark")
    ap.add_argument("--width", type=int, default=0, help="output width (default: terminal)")
    ap.add_argument(
        "--no-reflow", action="store_true", help="keep the original line breaks in descriptions"
    )
    ap.add_argument("--force-color", action="store_true", help="colorize even when piped")
    ap.add_argument("--plain", action="store_true", help="no color at all")
    ap.add_argument("--pager", action="store_true", help="page the output")
    args = ap.parse_args()

    if args.command:
        raw, found = acquire(args.command)
        if not found:
            hint = raw.strip().splitlines()[0] if raw.strip() else "no help output"
            print(f"helpfmt: no help found for `{' '.join(args.command)}`: {hint}", file=sys.stderr)
            return 1
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()
    else:
        ap.print_help()
        return 2

    if not raw.strip():
        print("helpfmt: no help text found", file=sys.stderr)
        return 1

    no_color = args.plain or (os.environ.get("NO_COLOR") and not args.force_color)
    console = Console(
        markup=False,  # `[OPTIONS]` must not be parsed as markup
        highlight=False,  # Rich's own auto-highlighter would fight ours
        soft_wrap=True,  # our own wrapper owns line breaks; Rich must not crop
        force_terminal=True if args.force_color else None,
        color_system="truecolor" if args.force_color else "auto",
        no_color=bool(no_color),
        width=args.width or None,
    )
    theme = {} if no_color else THEMES[args.theme]
    width = args.width or min(console.width, 100)

    def emit() -> None:
        render_to(console, raw, theme=theme, width=width, reflow=not args.no_reflow)

    if args.pager and sys.stdout.isatty():
        os.environ.setdefault("LESS", "-R")
        with console.pager(styles=True):
            emit()
    else:
        emit()
    return 0


def entrypoint() -> int:
    """Console-script wrapper.

    `BrokenPipeError` is the normal way a run ends when the caller pipes into
    `head`; exiting through `os._exit` skips interpreter shutdown, which would
    otherwise try to flush the already-closed stdout and print a warning.
    """
    try:
        return main()
    except BrokenPipeError:
        os._exit(0)
    except KeyboardInterrupt:
        return 130
