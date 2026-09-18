"""Getting help text out of a program that may not want to give it up."""

from __future__ import annotations

import os
import re
import subprocess

from .normalize import strip_ansi

# Things a shell or `man` says when there is no help to be had. These can
# otherwise slip through the probe below, because the failing command's own
# name is quoted back and may itself contain a word like "command".
NO_HELP_RE = re.compile(
    r"^\s*(no manual entry|no such file|command not found"
    r"|is not recognized|permission denied)",
    re.IGNORECASE,
)


def run(argv: list[str]) -> tuple[str, bool]:
    """Run a command, merging stderr. Many tools print help to stderr and
    exit non-zero, so the exit code is deliberately ignored."""
    try:
        p = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=20,
            env={**os.environ, "NO_COLOR": "1", "TERM": "dumb"},
        )
    except (FileNotFoundError, PermissionError) as exc:
        return f"{exc}", False
    except subprocess.TimeoutExpired:
        return f"`{' '.join(argv)}` timed out", False
    out = (p.stdout or "") + (p.stderr or "")
    return out, looks_like_help(out)


def looks_like_help(text: str) -> bool:
    """Does this output read like help, rather than like a failure?"""
    # Probe cleaned text: in a man page `SYNOPSIS` arrives as overstrike
    # (`S\bSY\bYN\bN...`), so none of these keywords match the raw bytes and
    # a perfectly good man page gets rejected as "not help".
    probe = re.sub(r".\x08", "", strip_ansi(text))
    body = [ln for ln in probe.splitlines() if ln.strip()]
    if not body or len("\n".join(body)) < 20:
        return False
    if NO_HELP_RE.match(body[0]):
        return False

    head = "\n".join(body[:40])
    if re.match(r"\s*(usage|synopsis)\b", head, re.IGNORECASE):
        return True
    # Otherwise insist on more than one line. A single line mentioning
    # "command" or "option" is far more likely to be an error message --
    # `man` answering "No manual entry for <name>" quotes the name back,
    # and the name itself can contain the very words we look for.
    return len(body) > 1 and bool(
        re.search(r"usage|synopsis|options?\b|commands?\b|--\w", head, re.IGNORECASE)
    )


def acquire(cmd: list[str]) -> tuple[str, bool]:
    """Try the usual ways a program is willing to describe itself.

    Returns (text, found). `found` is False when nothing we ran produced
    something that reads like help, so the caller can exit non-zero instead
    of pretty-printing an error message as if it were documentation.
    """
    # `helpfmt "git commit"` — a single argv entry holding a whole command
    # line. No real executable name contains a space, so splitting is safe
    # and saves a confusing "No such file or directory: 'git commit'".
    if len(cmd) == 1 and " " in cmd[0].strip():
        cmd = cmd[0].split()

    attempts = [cmd + ["--help"], cmd + ["-h"]]
    if len(cmd) >= 2:
        attempts.append([cmd[0], "help"] + cmd[1:])
    else:
        attempts.append(cmd + ["help"])
    attempts.append(["man", cmd[-1] if len(cmd) == 1 else "-".join(cmd)])

    best = ""
    for argv in attempts:
        out, ok = run(argv)
        if ok:
            return out, True
        if len(out) > len(best):
            best = out
    return best, False
