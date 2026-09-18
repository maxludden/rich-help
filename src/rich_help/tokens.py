"""Token-level highlighting.

Builds Rich `Text` with explicit spans. Never markup: `[OPTIONS]` is valid
Rich markup and would silently vanish if it were parsed as such.
"""

from __future__ import annotations

import re

from rich.text import Text

TOKEN_RE = re.compile(
    r"""
      (?P<url>https?://[^\s,)\]'"]+)
    | (?P<default>\((?:default|defaults to)[^)]{0,60}\)|\[default:[^\]]{0,60}\])
    | (?P<env>\$\{?[A-Z_][A-Z0-9_]*\}?)
    | (?P<literal>`[^`\n]{1,60}`|'[^'\n]{1,40}'|"[^"\n]{1,40}")
    | (?P<longflag>--(?:\[[a-zA-Z0-9-]{1,12}\])?[a-zA-Z0-9][a-zA-Z0-9-]*)
    | (?P<shortflag>(?<![\w-])-[a-zA-Z0-9?@#](?![\w-]))
    | (?P<placeholder><[^<>\n]{1,40}>)
    | (?P<metavar>(?<![\w-])[A-Z][A-Z0-9_]{1,}(?![\w-]))
    | (?P<punct>[\[\]{}|])
    """,
    re.VERBOSE,
)

# Metavars and bracket punctuation are meaningful in a synopsis or an option
# spec, but in prose they fire on ordinary acronyms ("HTTP POST") and are noise.
DESC_SKIP = {"metavar", "punct"}


def styled(s: str, theme: dict[str, str], *, spec: bool) -> Text:
    """Build a Rich Text with explicit spans — never markup."""
    t = Text(s, style="" if spec else theme.get("desc", ""))
    for m in TOKEN_RE.finditer(s):
        kind = m.lastgroup
        if kind is None or (not spec and kind in DESC_SKIP):
            continue
        style = theme.get(kind, "")
        if style:
            t.stylize(style, m.start(), m.end())
    return t
