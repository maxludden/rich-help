"""Turn raw help output into clean, indexable lines.

Strips ANSI, decodes nroff overstrike into style spans, expands tabs, and
drops the getopt complaint some tools print ahead of their usage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

ANSI_RE = re.compile(
    r"\x1b\[[0-9;?]*[ -/]*[@-~]"  # CSI sequences
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC sequences
    r"|\x1b[@-Z\\-_]"  # two-char escapes
)

NOISE_RE = re.compile(
    r"^\s*\S*\s*(illegal|unknown|invalid|unrecognized)\s+(option|argument)\b",
    re.IGNORECASE,
)


def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)


def decode_overstrike(line: str) -> tuple[str, list[tuple[int, int]], list[tuple[int, int]]]:
    """Decode nroff overstrike into plain text plus bold/underline spans.

    `X\\bX` means bold X; `_\\bX` means underlined X. This is how `man` marks
    up text when it isn't writing to a terminal, so it is an authoritative
    style signal rather than a heuristic.
    """
    if "\x08" not in line:
        return line, [], []

    out: list[str] = []
    bold_ix: list[int] = []
    under_ix: list[int] = []
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if i + 2 < n and line[i + 1] == "\x08":
            target = line[i + 2]
            if ch == "_" and target != "_":
                under_ix.append(len(out))
            else:
                bold_ix.append(len(out))
            out.append(target)
            i += 3
            continue
        if ch == "\x08":
            if out:
                out.pop()
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out), _runs(bold_ix), _runs(under_ix)


def _runs(indices: list[int]) -> list[tuple[int, int]]:
    """Collapse sorted indices into contiguous (start, end) spans."""
    spans: list[tuple[int, int]] = []
    for ix in indices:
        if spans and spans[-1][1] == ix:
            spans[-1] = (spans[-1][0], ix + 1)
        else:
            spans.append((ix, ix + 1))
    return spans


@dataclass
class NLine:
    """One normalized source line."""

    text: str
    bold: list[tuple[int, int]] = field(default_factory=list)
    under: list[tuple[int, int]] = field(default_factory=list)

    @property
    def blank(self) -> bool:
        return not self.text.strip()

    @property
    def indent(self) -> int:
        return len(self.text) - len(self.text.lstrip())


def normalize(raw: str) -> tuple[list[NLine], bool]:
    """Clean input into NLines. Returns (lines, looks_like_a_man_page)."""
    lines: list[NLine] = []
    saw_overstrike = False

    for src in raw.splitlines():
        src = strip_ansi(src.rstrip("\r"))
        text, bold, under = decode_overstrike(src)
        if bold or under:
            saw_overstrike = True
        if "\t" in text:
            # expandtabs would invalidate the span offsets. Tabs and
            # overstrike never co-occur in practice (man output is already
            # space-padded), so drop spans rather than mis-align columns.
            text = text.expandtabs(8)
            bold, under = [], []
        lines.append(NLine(text.rstrip(), bold, under))

    # Drop leading getopt complaints, e.g. `ssh: illegal option -- -`.
    # Leading only: the same words appearing mid-page are real help text.
    while lines and NOISE_RE.match(lines[0].text):
        lines.pop(0)
    while lines and lines[0].blank:
        lines.pop(0)
    while lines and lines[-1].blank:
        lines.pop()
    return lines, saw_overstrike
