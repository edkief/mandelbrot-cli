"""Static PNG rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np
from PIL import Image

from .core import compute_mandelbrot, get_palette, to_rgb


PathLike = Union[str, Path]


def render_png(
    out_path: PathLike,
    cx: float,
    cy: float,
    zoom: float,
    width: int,
    height: int,
    max_iter: int,
    palette: str = "magma",
) -> Path:
    """Render a static Mandelbrot PNG to ``out_path``. Returns the path."""
    escape = compute_mandelbrot(cx, cy, width, height, zoom, max_iter)
    rgb = to_rgb(escape, get_palette(palette), max_iter)
    img = Image.fromarray(rgb, mode="RGB")
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, format="PNG", optimize=True)
    return out