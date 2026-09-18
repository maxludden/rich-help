"""CLI behaviour: argument handling, exit codes, and acquisition."""

from __future__ import annotations

import io
import sys

import pytest

from rich_help.acquire import acquire, run
from rich_help.cli import main


def invoke(argv: list[str], stdin: str | None = None) -> tuple[int, str]:
    """Run main() in-process with argv and stdin patched."""
    old_argv, old_stdin, old_stdout = sys.argv, sys.stdin, sys.stdout
    sys.argv = ["rich-help", *argv]
    sys.stdin = io.StringIO(stdin) if stdin is not None else old_stdin
    sys.stdout = io.StringIO()
    try:
        code = main()
        return code, sys.stdout.getvalue()
    finally:
        sys.argv, sys.stdin, sys.stdout = old_argv, old_stdin, old_stdout


class TestFilterMode:
    def test_reads_stdin(self) -> None:
        code, out = invoke(["--plain"], stdin="usage: tool [OPTIONS]\n")
        assert code == 0
        assert "usage: tool [OPTIONS]" in out

    def test_empty_stdin_exits_non_zero(self) -> None:
        code, _ = invoke(["--plain"], stdin="")
        assert code == 1

    def test_plain_suppresses_color(self) -> None:
        _, out = invoke(["--plain"], stdin="Options:\n  -v  verbose\n")
        assert "\x1b" not in out


class TestWrapperMode:
    def test_unknown_command_exits_non_zero(self) -> None:
        code, _ = invoke(["definitely-not-a-real-command-xyz"])
        assert code == 1

    def test_a_real_command_succeeds(self) -> None:
        code, out = invoke(["--plain", sys.executable])
        assert code == 0
        assert out.strip()


class TestAcquire:
    def test_missing_executable_is_reported_not_rendered(self) -> None:
        _, found = acquire(["definitely-not-a-real-command-xyz"])
        assert found is False

    def test_a_single_argv_entry_holding_a_command_line_is_split(self) -> None:
        """`rich-help "git commit"` -- no executable name contains a space,
        so splitting beats a confusing "No such file or directory"."""
        _, found = acquire([f"{sys.executable} --help"])
        assert found is True

    def test_man_failure_is_not_mistaken_for_help(self) -> None:
        """Regression: `man` answers "No manual entry for <name>" and quotes
        the name back. When the name contains "command", the keyword probe
        matched it and an error message was rendered as documentation."""
        from rich_help.acquire import looks_like_help

        assert not looks_like_help("No manual entry for some-fake-command-xyz\n")

    def test_exit_code_is_ignored(self) -> None:
        """Plenty of tools print help to stderr and exit non-zero."""
        out, _ = run([sys.executable, "-c", "import sys; sys.stderr.write('usage: x\\n'); sys.exit(2)"])
        assert "usage: x" in out


class TestArgumentValidation:
    def test_rejects_an_unknown_theme(self) -> None:
        with pytest.raises(SystemExit):
            invoke(["--theme", "nope"], stdin="usage: x\n")

    @pytest.mark.parametrize("theme", ["dark", "ansi", "mono"])
    def test_accepts_every_theme(self, theme: str) -> None:
        code, _ = invoke(["--theme", theme, "--force-color"], stdin="Options:\n  -v  verbose\n")
        assert code == 0
