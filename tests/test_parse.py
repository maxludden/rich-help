"""Block classification and reflow."""

from __future__ import annotations

from rich_help import normalize, paragraphs, parse
from rich_help.normalize import NLine


def blocks(raw: str) -> list:
    lines, _ = normalize(raw)
    return parse(lines)


def kinds(raw: str) -> list[str]:
    return [b.kind for b in blocks(raw) if b.kind != "blank"]


class TestClassification:
    def test_usage_becomes_a_synopsis(self) -> None:
        assert kinds("usage: tool [OPTIONS] <file>\n")[0] == "synopsis"

    def test_section_header_is_recognised(self) -> None:
        assert "header" in kinds("Options:\n  -v  verbose\n")

    def test_inline_options_form_a_deflist(self) -> None:
        b = [x for x in blocks("Options:\n  -v, --verbose   Say more\n") if x.kind == "deflist"]
        assert len(b) == 1
        assert b[0].inline is True
        assert b[0].entries[0].term == "-v, --verbose"

    def test_hanging_options_form_a_deflist(self) -> None:
        raw = "Options:\n    -A NUM, --after-context=NUM\n            Output NUM lines.\n"
        b = [x for x in blocks(raw) if x.kind == "deflist"]
        assert len(b) == 1
        assert b[0].inline is False

    def test_subcommands_form_a_deflist(self) -> None:
        raw = "Commands:\n  run      Run a command\n  init     Create a project\n"
        b = [x for x in blocks(raw) if x.kind == "deflist"]
        assert [e.term for e in b[0].entries] == ["run", "init"]

    def test_synopsis_does_not_swallow_the_option_list(self) -> None:
        """curl puts its options at indent 1, right under the usage line.
        They must not be read as usage continuations."""
        raw = "Usage: curl [options...] <url>\n -d, --data <data>  HTTP POST data\n"
        assert kinds(raw) == ["synopsis", "deflist"]


class TestMixedTermIndent:
    """uv indents long-only options deeper than short+long ones. Both are
    terms; a continuation would sit at the description column instead."""

    RAW = (
        "Cache options:\n"
        "  -n, --no-cache               Avoid reading from the cache, instead using a temp\n"
        "                               directory for the operation [env: UV_NO_CACHE=]\n"
        "      --cache-dir <CACHE_DIR>  Path to the cache directory\n"
    )

    def test_deeper_flag_starts_its_own_entry(self) -> None:
        b = [x for x in blocks(self.RAW) if x.kind == "deflist"][0]
        assert [e.term for e in b.entries] == ["-n, --no-cache", "--cache-dir <CACHE_DIR>"]

    def test_real_continuation_stays_with_its_entry(self) -> None:
        b = [x for x in blocks(self.RAW) if x.kind == "deflist"][0]
        assert len(b.entries[0].desc) == 2


class TestParagraphs:
    def test_hard_wrapped_lines_are_rejoined(self) -> None:
        desc = [NLine(" " * 8 + "Verify installed packages have"), NLine(" " * 8 + "compatible deps.")]
        out = paragraphs(desc, reflow=True)
        assert len(out) == 1
        assert out[0].text == "Verify installed packages have compatible deps."

    def test_blank_line_separates_paragraphs(self) -> None:
        desc = [NLine("    one"), NLine(""), NLine("    two")]
        out = paragraphs(desc, reflow=True)
        assert [p.text for p in out] == ["one", "two"]
        assert out[1].break_before is True

    def test_no_reflow_keeps_line_breaks_without_inventing_blanks(self) -> None:
        """Regression: every source line became its own paragraph, and the
        hanging layout then separated all of them with a blank line."""
        desc = [NLine("    one"), NLine("    two"), NLine("    three")]
        out = paragraphs(desc, reflow=False)
        assert [p.text for p in out] == ["one", "two", "three"]
        assert not any(p.break_before for p in out)

    def test_deeply_indented_run_is_kept_verbatim(self) -> None:
        desc = [NLine("    prose"), NLine("            $ example --command")]
        out = paragraphs(desc, reflow=True)
        assert out[-1].verbatim is True

    def test_continuation_at_the_description_column_is_not_verbatim(self) -> None:
        """Regression (pip): the first description line used to be synthesized
        at a made-up column, so real continuations looked deeper-indented,
        were treated as examples, and were emitted unwrapped."""
        raw = (
            "Commands:\n"
            "  check                       Verify installed packages have compatible\n"
            "                              dependencies.\n"
        )
        b = [x for x in blocks(raw) if x.kind == "deflist"][0]
        assert not any(p.verbatim for p in paragraphs(b.entries[0].desc, reflow=True))
