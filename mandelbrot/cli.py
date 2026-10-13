"""Command-line entry point for the Mandelbrot CLI.

Subcommands
-----------
render    Static PNG render to a file.
view      Interactive terminal viewer (TTY only).
animate   Render a log-zoom animation as a GIF.
"""

from __future__ import annotations

import argparse
import sys

from . import core
from . import render as render_mod
from . import interactive as interactive_mod
from . import animate as animate_mod


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mandelbrot",
        description="CLI Mandelbrot fractal drawer: render, view, animate.",
    )
    p.add_argument(
        "--list-palettes",
        action="store_true",
        help="print available palettes and exit.",
    )
    sub = p.add_subparsers(dest="cmd")

    # -- render --
    pr = sub.add_parser("render", help="render a static PNG file.")
    pr.add_argument("--cx", type=float, default=-0.5, help="center X in fractal units.")
    pr.add_argument("--cy", type=float, default=0.0, help="center Y in fractal units.")
    pr.add_argument(
        "--zoom",
        type=float,
        default=1.5,
        help="half-width of the viewport in fractal units (default: 1.5).",
    )
    pr.add_argument("--width", type=int, default=1200, help="image width in pixels.")
    pr.add_argument("--height", type=int, default=800, help="image height in pixels.")
    pr.add_argument("--iters", type=int, default=1000, help="max iterations.")
    pr.add_argument(
        "--palette",
        default="magma",
        choices=core.list_palettes(),
        help="colour palette (default: magma).",
    )
    pr.add_argument(
        "--out", type=str, default="mandelbrot.png", help="output PNG path."
    )

    # -- view --
    pv = sub.add_parser("view", help="interactive terminal viewer (requires TTY).")
    pv.add_argument("--cx", type=float, default=-0.5)
    pv.add_argument("--cy", type=float, default=0.0)
    pv.add_argument("--zoom", type=float, default=1.5)
    pv.add_argument("--iters", type=int, default=256, help="starting max iterations.")
    pv.add_argument(
        "--palette",
        default="magma",
        choices=core.list_palettes(),
        help="colour palette (default: magma).",
    )

    # -- animate --
    pa = sub.add_parser("animate", help="render a log-zoom animation to a GIF.")
    pa.add_argument("--cx", type=float, default=-0.74364, help="zoom target X.")
    pa.add_argument("--cy", type=float, default=0.13182, help="zoom target Y.")
    pa.add_argument("--zoom-start", type=float, default=1.0, help="starting half-width.")
    pa.add_argument("--zoom-end", type=float, default=1e-5, help="ending half-width.")
    pa.add_argument("--frames", type=int, default=60)
    pa.add_argument("--fps", type=float, default=15.0)
    pa.add_argument("--width", type=int, default=480)
    pa.add_argument("--height", type=int, default=320)
    pa.add_argument("--iters", type=int, default=400, help="base max iterations.")
    pa.add_argument(
        "--palette",
        default="magma",
        choices=core.list_palettes(),
        help="colour palette (default: magma).",
    )
    pa.add_argument("--out", type=str, default="zoom.gif", help="output path.")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_palettes:
        print("Available palettes: " + ", ".join(core.list_palettes()))
        return 0

    if not args.cmd:
        parser.print_help()
        return 1

    if args.cmd == "render":
        out = render_mod.render_png(
            out_path=args.out,
            cx=args.cx,
            cy=args.cy,
            zoom=args.zoom,
            width=args.width,
            height=args.height,
            max_iter=args.iters,
            palette=args.palette,
        )
        print(f"wrote {out}")
        return 0

    if args.cmd == "view":
        interactive_mod.view(
            cx=args.cx,
            cy=args.cy,
            zoom=args.zoom,
            max_iter=args.iters,
            palette=args.palette,
        )
        return 0

    if args.cmd == "animate":
        out = animate_mod.animate(
            out_path=args.out,
            cx=args.cx,
            cy=args.cy,
            zoom_start=args.zoom_start,
            zoom_end=args.zoom_end,
            frames=args.frames,
            fps=args.fps,
            width=args.width,
            height=args.height,
            max_iter=args.iters,
            palette=args.palette,
        )
        print(f"wrote {out}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())