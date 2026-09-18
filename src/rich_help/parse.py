"""Block segmentation, classification, and reflow.

Tier 1 of the two-tier design: group lines into blocks and classify them.
Only blocks classified with confidence are re-laid-out downstream.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .normalize import NLine

USAGE_RE = re.compile(r"^(?P<ind>\s*)(?P<kw>usage|synopsis)\b\s*:?\s*(?P<rest>.*)$", re.I)
HEADER_RE = re.compile(r"^\s{0,4}[A-Za-z][A-Za-z0-9 /_'&-]{0,40}:\s*$")
ALLCAPS_RE = re.compile(r"^\s{0,4}[A-Z][A-Z0-9 _-]{2,40}\s*$")
FLAG_START_RE = re.compile(r"^\s*-{1,2}[A-Za-z0-9?@#]")
# `  install    Install packages.` / `  -d, --data <data>   HTTP POST data`
INLINE_TERM_RE = re.compile(r"^(?P<ind>\s*)(?P<term>\S.*?)(?:\s{2,})(?P<desc>\S.*)$")
BARE_TERM_RE = re.compile(r"^\s*[A-Za-z0-9][\w.-]*\s*$")


@dataclass
class Entry:
    term: str
    desc: list[NLine] = field(default_factory=list)
    desc_col: int = 0  # source column the description starts at


@dataclass
class Block:
    kind: str  # header | synopsis | deflist | prose | blank
    lines: list[NLine] = field(default_factory=list)
    entries: list[Entry] = field(default_factory=list)
    term_indent: int = 0
    inline: bool = True


def is_header(ln: NLine) -> bool:
    if ln.blank or FLAG_START_RE.match(ln.text):
        return False
    return bool(HEADER_RE.match(ln.text) or ALLCAPS_RE.match(ln.text))


def looks_like_term(ln: NLine, nxt: NLine | None, term_indent: int) -> bool:
    """Does this line start a definition-list entry?"""
    if ln.blank or ln.indent != term_indent:
        return False
    if FLAG_START_RE.match(ln.text):
        return True
    inline = INLINE_TERM_RE.match(ln.text)
    if inline:
        # First column must be short enough to read as a term, not a sentence.
        return len(inline.group("term")) <= 40
    # A bare word whose description hangs on the next, deeper line.
    if BARE_TERM_RE.match(ln.text) and nxt and not nxt.blank and nxt.indent > term_indent:
        return True
    return False


def parse(lines: list[NLine]) -> list[Block]:
    blocks: list[Block] = []
    i, n = 0, len(lines)

    while i < n:
        ln = lines[i]

        if ln.blank:
            blocks.append(Block("blank"))
            i += 1
            continue

        m = USAGE_RE.match(ln.text)
        if m and (m.group("rest") or i + 1 < n):
            i = _take_synopsis(lines, i, blocks, bool(m.group("rest").strip()))
            continue

        if is_header(ln):
            blocks.append(Block("header", [ln]))
            i += 1
            continue

        nxt = lines[i + 1] if i + 1 < n else None
        if ln.indent >= 1 and looks_like_term(ln, nxt, ln.indent):
            j = _take_deflist(lines, i, blocks)
            if j > i:
                i = j
                continue

        i = _take_prose(lines, i, blocks)

    return blocks


def _take_synopsis(lines: list[NLine], i: int, blocks: list[Block], has_rest: bool) -> int:
    """Gather a usage line plus its alignment-bearing continuations."""
    block = Block("synopsis", [lines[i]])
    i += 1
    # Continuations are deeply indented (ssh/git align under the command). When
    # the usage keyword stood alone (pip), any indented line continues it.
    min_cont = 4 if has_rest else 1
    while i < len(lines):
        ln = lines[i]
        if ln.blank or ln.indent < min_cont or FLAG_START_RE.match(ln.text):
            break
        block.lines.append(ln)
        i += 1
    blocks.append(block)
    return i


def _take_deflist(lines: list[NLine], i: int, blocks: list[Block]) -> int:
    term_indent = lines[i].indent
    block = Block("deflist", term_indent=term_indent)
    cur: Entry | None = None
    n = len(lines)
    inline_hits = total = 0
    last_len = 0

    while i < n:
        ln = lines[i]

        if ln.blank:
            j = i
            while j < n and lines[j].blank:
                j += 1
            if j >= n or lines[j].indent < term_indent or is_header(lines[j]):
                break
            if cur is not None:
                cur.desc.append(ln)
            i += 1
            continue

        nxt = lines[i + 1] if i + 1 < n else None

        starts_entry = ln.indent == term_indent and looks_like_term(ln, nxt, term_indent)
        if not starts_entry and cur is not None and cur.desc_col:
            # Some tools indent long-only options deeper than short+long ones
            # (uv: `-n, --no-cache` at column 2, `--cache-dir` at column 6).
            # Such a line is still a term, not a continuation -- real
            # continuations sit at the description column, which is further
            # right than any term in the block.
            starts_entry = (
                term_indent < ln.indent < cur.desc_col
                and FLAG_START_RE.match(ln.text) is not None
                and INLINE_TERM_RE.match(ln.text) is not None
            )

        if starts_entry:
            m = INLINE_TERM_RE.match(ln.text)
            total += 1
            if m:
                inline_hits += 1
                cur = Entry(m.group("term"))
                # Keep the source's real description column. Continuation lines
                # are aligned to it, and if we invented a different column they
                # would look deeper-indented and be mistaken for examples.
                cur.desc_col = m.start("desc")
                cur.desc.append(NLine(" " * cur.desc_col + m.group("desc")))
            else:
                cur = Entry(ln.text.strip())
            block.entries.append(cur)
            last_len = len(ln.text)
            i += 1
            continue

        if cur is not None and ln.indent > term_indent:
            cur.desc.append(ln)
            last_len = len(ln.text)
            i += 1
            continue

        # pip hard-wraps past the terminal width and spills to column 0.
        # Rescue that only when the previous line really looks truncated.
        if (
            cur is not None
            and ln.indent == 0
            and last_len >= 70
            and not is_header(ln)
            and not FLAG_START_RE.match(ln.text)
        ):
            cur.desc.append(NLine(" " * (cur.desc_col or term_indent + 4) + ln.text.strip()))
            last_len = len(ln.text)
            i += 1
            continue

        break

    if not block.entries:
        return i
    while block.entries and block.entries[-1].desc and block.entries[-1].desc[-1].blank:
        block.entries[-1].desc.pop()
    block.inline = total > 0 and inline_hits / total >= 0.6
    blocks.append(block)
    return i


def _take_prose(lines: list[NLine], i: int, blocks: list[Block]) -> int:
    block = Block("prose")
    n = len(lines)
    while i < n:
        ln = lines[i]
        if ln.blank or is_header(ln) or USAGE_RE.match(ln.text):
            break
        nxt = lines[i + 1] if i + 1 < n else None
        if block.lines and ln.indent >= 1 and looks_like_term(ln, nxt, ln.indent):
            break
        block.lines.append(ln)
        i += 1
    if not block.lines:  # never stall
        if i >= n:
            return i
        block.lines.append(lines[i])
        i += 1
    blocks.append(block)
    return i


# ------------------------------------------------------------- reflowing ---


@dataclass
class Para:
    text: str
    verbatim: bool = False
    break_before: bool = False  # the source had a blank line here


def paragraphs(desc: list[NLine], reflow: bool) -> list[Para]:
    """Rejoin hard-wrapped description lines into paragraphs.

    This is the pass that repairs help text wrapped at someone else's
    terminal width. Deeply-indented runs (examples) are kept verbatim.
    """
    body = [ln for ln in desc]
    while body and body[0].blank:
        body.pop(0)
    while body and body[-1].blank:
        body.pop()
    if not body:
        return []

    base = min(ln.indent for ln in body if not ln.blank)
    out: list[Para] = []
    buf: list[str] = []
    pending = False  # a blank line is waiting to be honoured

    def add(text: str, verbatim: bool = False) -> None:
        nonlocal pending
        out.append(Para(text, verbatim=verbatim, break_before=pending and bool(out)))
        pending = False

    def flush() -> None:
        if buf:
            add(" ".join(buf))
            buf.clear()

    for ln in body:
        if ln.blank:
            flush()
            pending = True
            continue
        if ln.indent > base + 3:  # example / nested list
            flush()
            add(ln.text[base:], verbatim=True)
            continue
        if not reflow:
            flush()
            add(ln.text.strip())
            continue
        stripped = ln.text.strip()
        # A bullet starts its own paragraph rather than gluing to the last.
        if buf and re.match(r"^([-*\u2022]\s|\(?\d+[.)]\s)", stripped):
            flush()
        buf.append(stripped)
    flush()
    return out
