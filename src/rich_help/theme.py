"""Color themes.

Each theme maps a token kind to a Rich style string. `dark` is truecolor;
`ansi` uses named colors so it inherits the terminal palette (and therefore
works on light backgrounds); `mono` is weight and slant only.
"""

from __future__ import annotations

THEMES: dict[str, dict[str, str]] = {
    # Truecolor, tuned for dark terminals.
    "dark": {
        "heading": "bold #7aa2f7",
        "term": "bold #7dcfff",
        "longflag": "bold #9ece6a",
        "shortflag": "bold #b4f9f8",
        "placeholder": "italic #e0af68",
        "metavar": "italic #e0af68",
        "literal": "#bb9af7",
        "punct": "#565f89",
        "desc": "#c0caf5",
        "default": "italic #737aa2",
        "env": "#f7768e",
        "url": "underline #7dcfff",
        "prose": "#a9b1d6",
    },
    # Named ANSI colors — inherits whatever palette the terminal is set to,
    # so it works on light backgrounds too.
    "ansi": {
        "heading": "bold blue",
        "term": "bold cyan",
        "longflag": "bold green",
        "shortflag": "bold cyan",
        "placeholder": "italic yellow",
        "metavar": "italic yellow",
        "literal": "magenta",
        "punct": "dim",
        "desc": "",
        "default": "dim italic",
        "env": "red",
        "url": "underline cyan",
        "prose": "",
    },
    # Structure only: bold/dim/italic, no hue. Good for `| less` and logs.
    "mono": {
        "heading": "bold underline",
        "term": "bold",
        "longflag": "bold",
        "shortflag": "bold",
        "placeholder": "italic",
        "metavar": "italic",
        "literal": "",
        "punct": "dim",
        "desc": "",
        "default": "dim italic",
        "env": "",
        "url": "underline",
        "prose": "",
    },
}
