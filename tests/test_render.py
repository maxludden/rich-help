"""Rendering: preservation guarantees, themes, and markup safety."""

from __future__ import annotations

import pytest

from rich_help import THEMES, decode_overstrike, format_help

from .conftest import SAMPLES


class TestSynopsisPreservation:
    """A synopsis carries meaning in its alignment -- `ssh`'s continuation
    lines are aligned under the command name -- so it is reproduced exactly
    rather than reflowed."""

    def test_ssh_synopsis_is_byte_identical(self) -> None:
        raw = (SAMPLES / "ssh.txt").read_text()
        expected = "\n".join(raw.splitlines()[1:])  # minus the getopt complaint
        assert format_help(raw, color=False).rstrip("\n") == expected.rstrip("\n")

    @pytest.mark.parametrize("width", [40, 80, 200])
    def test_synopsis_ignores_width(self, width: int) -> None:
        raw = (SAMPLES / "ssh.txt").read_text()
        assert format_help(raw, width=width, color=False) == format_help(
            raw, width=80, color=False
        )


class TestMarkupSafety:
    """`[OPTIONS]` is valid Rich markup. If the console parsed markup it would
    silently vanish, so the renderer builds Text with explicit spans only."""

    @pytest.mark.parametrize(
        "token",
        ["[OPTIONS]", "[-46AaCfGgKk]", "[<pathspec>...]", "[--[no-]status]", "{a,b}"],
    )
    def test_bracket_syntax_survives(self, token: str) -> None:
        out = format_help(f"usage: tool {token}\n", color=False)
        assert token in out


class TestReflow:
    def test_rejoins_text_wrapped_at_someone_elses_width(self) -> None:
        raw = (
            "Commands:\n"
            "  check                       Verify installed packages have compatible\n"
            "dependencies.\n"
        )
        out = format_help(raw, width=100, color=False)
        assert "Verify installed packages have compatible dependencies." in out

    def test_no_reflow_leaves_the_break_alone(self) -> None:
        raw = "Options:\n  -x   alpha beta\n       gamma delta\n"
        out = format_help(raw, width=100, color=False, reflow=False)
        assert "alpha beta gamma delta" not in out

    def test_narrow_width_falls_back_to_hanging_layout(self) -> None:
        raw = "Commands:\n  reallylongcommandname   Does a thing with a long description\n"
        out = format_help(raw, width=40, color=False)
        assert all(len(line) <= 40 for line in out.splitlines())


class TestThemes:
    @pytest.mark.parametrize("theme", sorted(THEMES))
    def test_every_theme_emits_styling(self, theme: str) -> None:
        out = format_help("Options:\n  -v, --verbose  Say more\n", theme=theme)
        assert "\x1b" in out

    @pytest.mark.parametrize("theme", sorted(THEMES))
    def test_every_theme_defines_the_same_keys(self, theme: str) -> None:
        assert set(THEMES[theme]) == set(THEMES["dark"])

    def test_color_off_emits_none(self) -> None:
        out = format_help("Options:\n  -v, --verbose  Say more\n", color=False)
        assert "\x1b" not in out


class TestManPages:
    def test_overstrike_becomes_real_styling(self) -> None:
        bold = "".join(f"{c}\b{c}" for c in "NAME")
        out = format_help(f"{bold}\n       tool - does things\n")
        assert "\x1b[1m" in out or "\x1b[1;" in out
        assert "NAME" in out

    def test_man_layout_is_preserved(self) -> None:
        """Man mode preserves columns by design, so every line must come back
        exactly -- same content, same order, same indentation -- with only the
        overstrike decoded away. Comparing counts would let a page whose lines
        were reordered slip through."""
        raw = (SAMPLES / "git-commit-man.txt").read_text()
        expected = [decode_overstrike(ln)[0].rstrip() for ln in raw.splitlines()]
        while expected and not expected[0].strip():
            expected.pop(0)
        while expected and not expected[-1].strip():
            expected.pop()

        got = [ln.rstrip() for ln in format_help(raw, color=False).splitlines()]
        assert got == expected


class TestEdgeCases:
    @pytest.mark.parametrize("raw", ["", "\n", "   \n\n  \n"])
    def test_empty_input_does_not_crash(self, raw: str) -> None:
        assert format_help(raw, color=False).strip() == ""

    def test_single_word(self) -> None:
        assert "hello" in format_help("hello\n", color=False)

    @pytest.mark.parametrize("width", [1, 5, 12, 20])
    def test_absurd_widths_do_not_crash(self, width: int) -> None:
        raw = "Options:\n  -v, --verbose   Say considerably more than usual\n"
        assert format_help(raw, width=width, color=False).strip()
