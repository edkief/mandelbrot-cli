"""Interactive terminal viewer: arrow keys pan, +/- zoom, q quits.

Uses raw ANSI escape codes (no curses) so it works in any TTY. Each
terminal row packs two pixel rows using the Unicode upper-half-block
character (``\u2580``): the foreground colour is the top pixel, the
background colour is the bottom pixel. That doubles the effective
vertical resolution.
"""

from __future__ import annotations

import os
import select
import shutil
import sys
import termios
import tty
from typing import Optional

import numpy as np

from .core import compute_mandelbrot, get_palette, to_rgb


# ---------------------------------------------------------------------------
# Terminal helpers
# ---------------------------------------------------------------------------


def _term_size() -> tuple[int, int]:
    """Return (cols, rows) of the controlling terminal."""
    try:
        cols, rows = shutil.get_terminal_size()
    except (OSError, ValueError):
        cols, rows = 80, 24
    return cols, rows


# Keys we recognise (escape-sequence based)
_SPECIAL_KEYS = {
    "\x1b[A": "up",
    "\x1b[B": "down",
    "\x1b[C": "right",
    "\x1b[D": "left",
    "\x1b[5~": "page_up",
    "\x1b[6~": "page_down",
}


def _read_key(timeout: float = 0.5) -> Optional[str]:
    """Read a single key from stdin in raw mode. Returns None on timeout.

    Recognised keys: ``up``, ``down``, ``left``, ``right``, ``+``, ``-``,
    ``=``, ``q``, ``r`` (reset), ``i`` (more iterations), ``h`` (help).
    """
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        # Block for up to ``timeout`` seconds
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if not rlist:
            return None
        ch = os.read(fd, 1).decode("utf-8", errors="ignore")
        if ch == "\x1b":
            # Possibly an escape sequence; peek for more bytes (short window)
            rlist2, _, _ = select.select([sys.stdin], [], [], 0.05)
            if rlist2:
                ch += os.read(fd, 2).decode("utf-8", errors="ignore")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

    if ch in _SPECIAL_KEYS:
        return _SPECIAL_KEYS[ch]
    if ch in ("\x1b",):
        return "esc"
    if ch in ("q", "Q", "\x03"):  # q or Ctrl-C
        return "quit"
    if ch in ("+", "="):
        return "zoom_in"
    if ch in ("-", "_"):
        return "zoom_out"
    if ch in ("r", "R"):
        return "reset"
    if ch in ("i", "I"):
        return "more_iter"
    if ch in ("h", "H", "?"):
        return "help"
    return ch


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


_ANSI_RESET = "\x1b[0m"
_ANSI_HIDE_CURSOR = "\x1b[?25l"
_ANSI_SHOW_CURSOR = "\x1b[?25h"
_ANSI_ALT_ON = "\x1b[?1049h"
_ANSI_ALT_OFF = "\x1b[?1049l"
_ANSI_CLEAR = "\x1b[2J\x1b[H"


def _render_halfblock(rgb: np.ndarray) -> str:
    """Encode an ``(H, W, 3)`` RGB image as ANSI half-block rows.

    Each terminal row carries two pixel rows. Returns a single string
    ready to be written to stdout (terminated with a final reset + newline).
    """
    h, w = rgb.shape[:2]
    # Need an even height for clean pairing
    if h % 2 == 1:
        rgb = np.concatenate([rgb, rgb[-1:]], axis=0)
        h += 1
    out: list[str] = []
    for r in range(0, h, 2):
        upper = rgb[r]
        lower = rgb[r + 1]
        for c in range(w):
            r1, g1, b1 = int(upper[c, 0]), int(upper[c, 1]), int(upper[c, 2])
            r2, g2, b2 = int(lower[c, 0]), int(lower[c, 1]), int(lower[c, 2])
            out.append(
                f"\x1b[38;2;{r1};{g1};{b1}m\x1b[48;2;{r2};{g2};{b2}m\u2580"
            )
        out.append(_ANSI_RESET + "\n")
    return "".join(out)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def view(
    cx: float = -0.5,
    cy: float = 0.0,
    zoom: float = 1.5,
    max_iter: int = 256,
    palette: str = "magma",
) -> None:
    """Run the interactive viewer. Blocks until the user quits."""
    if not sys.stdin.isatty():
        print(
            "error: interactive mode needs a TTY. Use 'render' or 'animate' instead.",
            file=sys.stderr,
        )
        sys.exit(2)

    pal_arr = get_palette(palette)
    cx0, cy0, zoom0 = cx, cy, zoom

    sys.stdout.write(_ANSI_ALT_ON + _ANSI_HIDE_CURSOR + _ANSI_CLEAR)
    sys.stdout.flush()
    try:
        while True:
            cols, rows = _term_size()
            # Leave one row at the bottom for the status line
            pixel_w = max(20, cols)
            pixel_h = max(20, (rows - 1) * 2)  # 2x via half-block
            aspect = pixel_h / pixel_w
            # Adjust zoom so the viewport's horizontal half-width is `zoom`
            # (vertical half-width = zoom * aspect)
            escape = compute_mandelbrot(cx, cy, pixel_w, pixel_h, zoom, max_iter)
            rgb = to_rgb(escape, pal_arr, max_iter)
            frame = _render_halfblock(rgb)
            status = (
                f" cx={cx:+.6f} cy={cy:+.6f} zoom={zoom:.3e}  "
                f"iters={max_iter}  palette={palette}   "
                f"[arrows pan | +/- zoom | r reset | i more iters | h help | q quit]"
            )
            # Move cursor home, write frame, write status, clear rest
            out = "\x1b[H" + frame + "\x1b[" + str(rows) + ";1H" + status + "\x1b[K"
            sys.stdout.write(out)
            sys.stdout.flush()

            key = _read_key(timeout=2.0)
            if key is None:
                continue
            if key in ("quit", "esc"):
                break
            if key in ("up", "down", "left", "right"):
                # Pan by 1/4 of the visible viewport width
                step = zoom * 0.25
                if key == "up":
                    cy -= step * aspect
                elif key == "down":
                    cy += step * aspect
                elif key == "left":
                    cx -= step
                elif key == "right":
                    cx += step
            elif key == "zoom_in":
                zoom *= 0.5
            elif key == "zoom_out":
                zoom *= 2.0
            elif key == "reset":
                cx, cy, zoom = cx0, cy0, zoom0
                max_iter = 256
            elif key == "more_iter":
                max_iter = min(max_iter * 2, 8192)
            elif key == "help":
                sys.stdout.write("\x1b[H" + _help_text())
                sys.stdout.flush()
                _read_key(timeout=5.0)
    finally:
        sys.stdout.write(_ANSI_ALT_OFF + _ANSI_SHOW_CURSOR + "\n")
        sys.stdout.flush()


def _help_text() -> str:
    return (
        "\n  Mandelbrot CLI — interactive viewer\n"
        "  ----------------------------------\n"
        "  Arrow keys      pan\n"
        "  + / =           zoom in (2x detail)\n"
        "  - / _           zoom out\n"
        "  i               double iteration depth (slower, more detail)\n"
        "  r               reset view\n"
        "  h / ?           this help\n"
        "  q / Esc         quit\n\n"
        "  press any key to return...\n"
    )