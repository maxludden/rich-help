"""Render sample help pages to SVG for docs and README.md.

    uv run scripts/generate_svgs.py                  # curated hero set, dark theme
    uv run scripts/generate_svgs.py --all             # every sample in tests/samples
    uv run scripts/generate_svgs.py pip tar --theme ansi mono
    uv run scripts/generate_svgs.py --out assets/svg --width 90

Samples are read from `tests/samples/*.txt` rather than shelling out to real
commands, so the images stay reproducible across machines and don't drift
with the installed version of `curl`/`git`/`pip`.
"""

from __future__ import annotations

import argparse
import io
import pathlib
import sys

from rich.console import Console
from rich.terminal_theme import TerminalTheme

from rich_help.render import render_to
from rich_help.theme import THEMES

REPO_ROOT = pathlib.Path(__file__).parent.parent
SAMPLES_DIR = REPO_ROOT / "tests" / "samples"

# A representative slice of the corpus: short synopsis-only, a medium
# definition list, and one with inline defaults/env vars. Kept small so the
# default run produces README-sized images rather than 600-line man pages.
HERO_SAMPLES = ["curl", "ssh", "tar", "pip"]

# Backdrop matched to the `dark` theme's palette (Tokyo Night) so the
# exported chrome doesn't clash with the syntax colors inside it.
TOKYO_NIGHT = TerminalTheme(
    (26, 27, 38),  # background
    (192, 202, 245),  # foreground
    [
        (21, 22, 30), (247, 118, 142), (158, 206, 106), (224, 175, 104),
        (122, 162, 247), (187, 154, 247), (125, 207, 255), (169, 177, 214),
    ],
    [
        (65, 72, 104), (247, 118, 142), (158, 206, 106), (224, 175, 104),
        (122, 162, 247), (187, 154, 247), (125, 207, 255), (192, 202, 245),
    ],
)


def render_svg(raw: str, *, theme_name: str, width: int, title: str) -> str:
    console = Console(
        file=io.StringIO(),
        record=True,
        markup=False,
        highlight=False,
        soft_wrap=True,
        force_terminal=True,
        color_system="truecolor",
        width=width,
    )
    render_to(console, raw, theme=THEMES[theme_name], width=width, reflow=True)
    return console.export_svg(title=title, theme=TOKYO_NIGHT)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "samples",
        nargs="*",
        help="sample names from tests/samples/ (default: curated hero set)",
    )
    ap.add_argument("--all", action="store_true", help="render every sample in tests/samples/")
    ap.add_argument(
        "--theme",
        nargs="+",
        choices=sorted(THEMES),
        default=["dark"],
        help="theme(s) to render (default: dark)",
    )
    ap.add_argument("--width", type=int, default=100, help="render width (default: 100)")
    ap.add_argument(
        "--out",
        type=pathlib.Path,
        default=REPO_ROOT / "assets" / "svg",
        help="output directory (default: assets/svg)",
    )
    args = ap.parse_args()

    if args.all:
        names = [p.stem for p in sorted(SAMPLES_DIR.glob("*.txt"))]
    elif args.samples:
        names = args.samples
    else:
        names = HERO_SAMPLES

    args.out.mkdir(parents=True, exist_ok=True)

    for name in names:
        path = SAMPLES_DIR / f"{name}.txt"
        if not path.is_file():
            print(f"skip {name}: no tests/samples/{name}.txt", file=sys.stderr)
            continue
        raw = path.read_text()
        for theme_name in args.theme:
            suffix = "" if args.theme == ["dark"] else f"-{theme_name}"
            out_path = args.out / f"{name}{suffix}.svg"
            svg = render_svg(
                raw,
                theme_name=theme_name,
                width=args.width,
                title=f"rich-help {name}",
            )
            out_path.write_text(svg)
            try:
                shown = out_path.relative_to(REPO_ROOT)
            except ValueError:
                shown = out_path
            print(f"wrote {shown}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
