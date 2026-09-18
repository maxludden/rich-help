"""Rendering: blocks and man pages to a Rich console."""

from __future__ import annotations

import io
import textwrap

from rich.console import Console
from rich.text import Text

from .normalize import NLine, normalize
from .parse import ALLCAPS_RE, Block, Para, paragraphs, parse
from .theme import THEMES
from .tokens import styled


def wrap(text: str, width: int) -> list[str]:
    if width < 12:
        return [text]
    return textwrap.wrap(
        text,
        width=width,
        break_long_words=False,
        break_on_hyphens=False,  # never split `--dry-run`
    ) or [""]


class Renderer:
    def __init__(self, console: Console, theme: dict[str, str], width: int, reflow: bool):
        self.c = console
        self.t = theme
        self.w = width
        self.reflow = reflow

    def emit(self, blocks: list[Block]) -> None:
        prev_blank = True
        for b in blocks:
            if b.kind == "blank":
                if not prev_blank:
                    self.c.print()
                    prev_blank = True
                continue
            getattr(self, f"_{b.kind}")(b)
            prev_blank = False

    def _header(self, b: Block) -> None:
        text = b.lines[0].text.strip()
        self.c.print(Text(text, style=self.t.get("heading", "")))

    def _synopsis(self, b: Block) -> None:
        for ln in b.lines:
            self.c.print(styled(ln.text, self.t, spec=True))

    def _prose(self, b: Block) -> None:
        paras = paragraphs(b.lines, self.reflow)
        base = min((ln.indent for ln in b.lines if not ln.blank), default=0)
        pad = " " * base
        for p in paras:
            if p.verbatim:
                self.c.print(Text(pad + p.text, style=self.t.get("literal", "")))
                continue
            for row in wrap(p.text, self.w - base):
                self.c.print(styled(pad + row, self.t, spec=False))

    def _deflist(self, b: Block) -> None:
        indent = min(b.term_indent, 4) or 2
        longest = max(len(e.term) for e in b.entries)
        desc_col = indent + longest + 2

        # Fall back to hanging layout when the term column would squeeze
        # descriptions into a sliver, or when the source was already hanging.
        use_inline = b.inline and desc_col <= max(28, self.w // 2) and self.w - desc_col >= 28
        hang_col = indent + 4

        for e in b.entries:
            paras = paragraphs(e.desc, self.reflow)
            term = Text(" " * indent) + styled(e.term, self.t, spec=True)

            if use_inline:
                rows = self._para_rows(paras, self.w - desc_col)
                if not rows:
                    self.c.print(term)
                    continue
                first, *rest = rows
                head = term.copy()
                head.append(" " * (desc_col - indent - len(e.term)))
                head.append_text(first)
                self.c.print(head)
                for r in rest:
                    if not r.plain:
                        self.c.print()
                        continue
                    line = Text(" " * desc_col)
                    line.append_text(r)
                    self.c.print(line)
            else:
                self.c.print(term)
                for r in self._para_rows(paras, self.w - hang_col):
                    if not r.plain:
                        self.c.print()
                        continue
                    line = Text(" " * hang_col)
                    line.append_text(r)
                    self.c.print(line)

    def _para_rows(self, paras: list[Para], width: int) -> list[Text]:
        rows: list[Text] = []
        for p in paras:
            if p.break_before:
                rows.append(Text(""))
            if p.verbatim:
                rows.append(Text(p.text, style=self.t.get("literal", "")))
                continue
            for row in wrap(p.text, width):
                rows.append(styled(row, self.t, spec=False))
        return rows


def render_man(lines: list[NLine], console: Console, theme: dict[str, str]) -> None:
    """Man pages are already well laid out; preserve columns, add color.

    The overstrike spans decoded from nroff are authoritative, so they take
    priority and our token highlighting layers underneath them.
    """
    for ln in lines:
        if not ln.text.strip():
            console.print()
            continue
        if ALLCAPS_RE.match(ln.text) and ln.indent == 0:
            console.print(Text(ln.text, style=theme.get("heading", "")))
            continue
        t = styled(ln.text, theme, spec=True)
        # Overstrike carries structure only. Applying a themed *color* here
        # would override the token hues underneath (a bolded `--interactive`
        # would stop looking like a flag), so layer weight, not color.
        for start, end in ln.under:
            t.stylize("italic", start, end)
        for start, end in ln.bold:
            t.stylize("bold", start, end)
        console.print(t)


def render_to(
    console: Console,
    raw: str,
    *,
    theme: dict[str, str],
    width: int,
    reflow: bool = True,
) -> None:
    """Render help text to an existing console.

    The single dispatch point between the two document types, shared by the
    CLI and the library API so they can never drift apart.
    """
    lines, is_man = normalize(raw)
    if is_man:
        render_man(lines, console, theme)
    else:
        Renderer(console, theme, width, reflow).emit(parse(lines))


def format_help(
    raw: str,
    *,
    theme: str = "dark",
    width: int = 100,
    reflow: bool = True,
    color: bool = True,
) -> str:
    """Format help text and return it as a string.

    The library entry point, and what the tests drive so they exercise the
    real render path in-process rather than shelling out to a script.
    """
    buf = io.StringIO()
    console = Console(
        file=buf,
        markup=False,
        highlight=False,
        soft_wrap=True,
        force_terminal=color or None,
        no_color=not color,
        color_system="truecolor" if color else None,
        width=width,
    )
    render_to(
        console,
        raw,
        theme=THEMES[theme] if color else {},
        width=width,
        reflow=reflow,
    )
    return buf.getvalue()
