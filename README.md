# helpfmt

Format and colorize command help pages.

```bash
./helpfmt.py curl              # wrapper: runs `curl --help`
./helpfmt.py git commit        # runs `git commit --help`
mytool --help | ./helpfmt.py   # filter mode
```

Requires [`uv`](https://docs.astral.sh/uv/). The script declares its own
dependency on `rich` in a PEP 723 header, so there is nothing to install —
the shebang (`#!/usr/bin/env -S uv run --script`) handles it.

## What it actually does

Colorizing is the easy half. The useful half is **repairing layout**: most
tools hard-wrap their help at whatever width the author had, so on a wide
terminal you read an 80-column column, and on a narrow one you get output
like this (real `pip --help`):

```shell
  check    Verify installed packages have compatible dependencies.
```

`helpfmt` rejoins those wrapped continuations into paragraphs and re-wraps
them to *your* width.

## Design: two tiers

1. Classify each **block** — synopsis, section header, definition list,
   prose, indented example. Only blocks classified with confidence get
   re-laid-out.
2. Anything unclassified is emitted **verbatim** with token-level recolor.

Worst case is therefore "plain help with some color", never lost text.

Blocks deliberately left alone:

- **Synopsis** (`usage: ssh [-46Aa...]`) — the continuation alignment is
  meaningful, so it is reproduced byte-identically.
- **Indented examples** inside descriptions.
- **Man pages.** `git commit --help` renders through `man`, which marks bold
  as `X\bX` and italic as `_\bX` overstrike. That is an authoritative style
  signal, so man-style input takes a separate path: columns preserved,
  overstrike decoded to real bold/italic, color layered underneath.

## Options

| flag | effect |
| :--- | :--- |
| `--theme dark\|ansi\|mono` | `dark` = truecolor<br>`ansi` = named colors, inherits your terminal palette (works on light backgrounds)<br>`mono` = bold/dim only |
| `--width N` | output width (default: terminal, capped at 100) |
| `--no-reflow` | keep the original line breaks |
| `--plain` / `NO_COLOR=1` | no color |
| `--force-color` | colorize even when piped |
| `--pager` | page the output |

## Verifying changes

`verify_helpfmt.py` is the guard rail that matters. For every sample it
strips ANSI from the output and compares the whitespace-normalized **token
stream** against the input — they must be identical modulo re-wrapping.

```bash
python3 verify_helpfmt.py samples
```

It runs the whole corpus across a flag matrix (widths 100/40/20,
`--no-reflow`, all three themes, `--plain`), because the escape hatches and
extreme widths take different code paths than the happy path.

This catches the one failure mode that really hurts: silently eaten text.
It found several genuine bugs, including Rich cropping at the console width
despite `crop=False` (only `soft_wrap=True` disables that), and description
continuations being mistaken for indented examples and overflowing.

Add samples freely — any `samples/*.txt` is picked up. Collect one with:

```bash
sometool --help > samples/sometool.txt 2>&1
```

## Known limits

- A line containing **both** tabs and overstrike drops its overstrike spans
  (expanding tabs would invalidate the offsets). These do not co-occur in
  practice; token highlighting still applies.
- Definition lists are detected by consistent term indentation. Help text
  that indents inconsistently falls back to verbatim prose.
- `--theme dark` assumes a dark background; use `--theme ansi` otherwise.
- Wrapper mode runs the real executable, so **shell aliases and functions are
  not visible to it**. If `grep` is aliased to `ugrep` in your shell,
  `helpfmt grep` documents `/usr/bin/grep`. Pipe instead when that matters:
  `grep --help 2>&1 | helpfmt`.
