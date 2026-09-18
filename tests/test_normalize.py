"""Normalization: ANSI, nroff overstrike, tabs, and leading noise."""

from __future__ import annotations

import pytest

from rich_help import decode_overstrike, normalize, strip_ansi
from rich_help.acquire import looks_like_help


class TestDecodeOverstrike:
    """`man` marks bold as `X\\bX` and italic as `_\\bX` when not writing to a
    terminal. That is an authoritative style signal, so it is decoded rather
    than guessed at."""

    def test_plain_text_is_untouched(self) -> None:
        assert decode_overstrike("NAME") == ("NAME", [], [])

    def test_bold_becomes_a_span(self) -> None:
        text, bold, under = decode_overstrike("N\bNA\bAM\bME\bE")
        assert text == "NAME"
        assert bold == [(0, 4)]
        assert under == []

    def test_underline_becomes_a_span(self) -> None:
        text, bold, under = decode_overstrike("_\bx")
        assert (text, bold, under) == ("x", [], [(0, 1)])

    def test_nroff_bullet_keeps_the_target_glyph(self) -> None:
        """`+\\bo` is a composite bullet; like `col -b`, the last glyph wins."""
        text, _, _ = decode_overstrike("+\bo")
        assert text == "o"

    def test_adjacent_runs_do_not_merge_across_plain_text(self) -> None:
        text, bold, _ = decode_overstrike("a\ba b\bb")
        assert text == "a b"
        assert bold == [(0, 1), (2, 3)]


class TestStripAnsi:
    def test_removes_sgr(self) -> None:
        assert strip_ansi("\x1b[1;31mred\x1b[0m") == "red"

    def test_keeps_bracket_text(self) -> None:
        assert strip_ansi("[OPTIONS]") == "[OPTIONS]"


class TestNormalize:
    def test_detects_a_man_page(self) -> None:
        _, is_man = normalize("N\bNA\bAM\bME\bE\n       tool - does things\n")
        assert is_man is True

    def test_plain_help_is_not_a_man_page(self) -> None:
        _, is_man = normalize("usage: tool [OPTIONS]\n")
        assert is_man is False

    def test_drops_leading_getopt_complaint(self) -> None:
        lines, _ = normalize("ssh: illegal option -- -\nusage: ssh [-46]\n")
        assert lines[0].text.startswith("usage:")

    def test_keeps_those_words_mid_page(self) -> None:
        """Only the leading edge is noise. The same words in a description
        are real help text and must survive."""
        raw = "usage: tool\n\nOptions:\n  -x  Fail on unknown option errors.\n"
        lines, _ = normalize(raw)
        assert any("unknown option" in ln.text for ln in lines)

    def test_expands_tabs(self) -> None:
        lines, _ = normalize("usage: x\n\t-a\tdo a\n")
        assert "\t" not in lines[1].text


class TestLooksLikeHelp:
    def test_accepts_plain_usage(self) -> None:
        assert looks_like_help("usage: tool [OPTIONS]\n  -h  help\n")

    def test_accepts_an_overstruck_man_page(self) -> None:
        """Regression: the probe used to run on raw bytes, where `SYNOPSIS`
        arrives as `S\\bSY\\bYN\\bN...` and matches nothing -- so a perfectly
        good man page was rejected and `rich-help git commit` exited 1."""
        bold = "".join(f"{c}\b{c}" for c in "SYNOPSIS")
        page = f"GIT-COMMIT(1)\n\n{bold}\n       git commit [-a] [-m <msg>]\n"
        assert looks_like_help(page)

    @pytest.mark.parametrize("text", ["", "   ", "command not found"])
    def test_rejects_non_help(self, text: str) -> None:
        assert not looks_like_help(text)
