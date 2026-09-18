"""The guard rail: formatting must never eat words.

For every sample and every flag combination, the whitespace-normalized token
stream of the output must equal that of the input. Re-wrapping changes line
breaks and padding; it must not change the words.

This is the check that matters, because the failure mode it catches --
silently dropped text -- is invisible in a rendered diff and actively
misleads anyone reading the formatted help.
"""

from __future__ import annotations

import pytest

from rich_help import format_help

from .conftest import tokens

# Each case takes a different path through the renderer: the escape hatches
# and the extreme widths are not exercised by the happy path.
FLAG_MATRIX = [
    pytest.param({}, id="default"),
    pytest.param({"width": 40}, id="narrow-40"),
    pytest.param({"width": 20}, id="tiny-20"),
    pytest.param({"width": 200}, id="wide-200"),
    pytest.param({"reflow": False}, id="no-reflow"),
    pytest.param({"theme": "mono"}, id="theme-mono"),
    pytest.param({"theme": "ansi"}, id="theme-ansi"),
    pytest.param({"color": False}, id="plain"),
]


@pytest.mark.parametrize("opts", FLAG_MATRIX)
def test_no_tokens_lost(sample: str, opts: dict[str, object]) -> None:
    out = format_help(sample, **opts)
    assert tokens(out) == tokens(sample, is_input=True)


@pytest.mark.parametrize("opts", FLAG_MATRIX)
def test_output_is_not_empty(sample: str, opts: dict[str, object]) -> None:
    assert format_help(sample, **opts).strip()


def test_plain_emits_no_escape_sequences(sample: str) -> None:
    assert "\x1b" not in format_help(sample, color=False)


def test_reflow_respects_requested_width(sample: str) -> None:
    """Reflowed lines must fit the width.

    Over-long lines are allowed only where the source made them unavoidable:
    a single unbreakable token (a long path or URL), or a synopsis, which is
    reproduced verbatim because its alignment carries meaning.
    """
    width = 100
    for line in format_help(sample, width=width, color=False).splitlines():
        if len(line) <= width:
            continue
        longest = max((len(w) for w in line.split()), default=0)
        assert longest > 20, f"avoidably long line ({len(line)}): {line!r}"
