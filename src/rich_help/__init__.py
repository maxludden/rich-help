"""rich-help — format and colorize command help pages.

    rich-help curl                 # wrapper mode: runs `curl --help`
    rich-help git commit           # runs `git commit --help`
    somecmd --help | rich-help     # filter mode

Two-tier design: blocks classified with confidence are re-laid-out (rejoined,
re-wrapped, aligned); everything else is emitted verbatim with token-level
recolor. The worst case is "plain help with some color", never lost text.
"""

from __future__ import annotations

from .acquire import acquire, looks_like_help
from .cli import entrypoint, main
from .normalize import NLine, decode_overstrike, normalize, strip_ansi
from .parse import Block, Entry, Para, paragraphs, parse
from .render import Renderer, format_help, render_man, render_to
from .theme import THEMES
from .tokens import styled

__version__ = "0.1.0"

__all__ = [
    "Block",
    "Entry",
    "NLine",
    "Para",
    "Renderer",
    "THEMES",
    "__version__",
    "acquire",
    "format_help",
    "decode_overstrike",
    "entrypoint",
    "looks_like_help",
    "main",
    "normalize",
    "paragraphs",
    "parse",
    "render_man",
    "render_to",
    "strip_ansi",
    "styled",
]
