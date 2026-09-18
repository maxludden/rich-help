"""Shared fixtures and helpers.

Samples live in `tests/samples/` and are located relative to this file, so
pytest behaves the same whether it is run from the repo root or from `tests/`.
"""

from __future__ import annotations

import pathlib
import re

import pytest

SAMPLES = pathlib.Path(__file__).parent / "samples"

ANSI = re.compile(
    r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]"
)
# nroff overstrike: the last glyph of each pair wins, exactly as `col -b` does.
OVERSTRIKE = re.compile(r".\x08")
NOISE = re.compile(
    r"^\s*\S*\s*(illegal|unknown|invalid|unrecognized)\s+(option|argument)\b", re.I
)


def sample_paths() -> list[pathlib.Path]:
    return sorted(SAMPLES.glob("*.txt"))


def sample_ids() -> list[str]:
    return [p.stem for p in sample_paths()]


@pytest.fixture(params=sample_paths(), ids=sample_ids())
def sample(request: pytest.FixtureRequest) -> str:
    """Each help-page sample, one test per file."""
    return request.param.read_text()


def tokens(text: str, *, is_input: bool = False) -> list[str]:
    """Whitespace-normalized token stream, ignoring color and line breaks.

    Reflow deliberately changes line breaks and padding, so comparing lines
    would fail on correct output. Tokens are what must survive.
    """
    text = OVERSTRIKE.sub("", ANSI.sub("", text))
    lines = text.splitlines()
    if is_input:
        # `normalize()` drops getopt complaints, but only from the leading
        # edge. Mirror that exactly: the same words mid-page are real help
        # text, and excusing them here would blind the check to real loss.
        while lines and NOISE.match(lines[0]):
            lines.pop(0)
    return "\n".join(lines).split()
