"""mandelbrot-cli: a small CLI Mandelbrot fractal drawer.

Public submodules
=============
core         -- numpy escape-time kernel and palette table.
render       -- static PNG renderer.
interactive  -- ANSI half-block terminal viewer.
animate      -- zoom-animation GIF encoder.
cli          -- argparse entry point (``python -m mandelbrot``).
"""

from .core import compute_mandelbrot, get_palette, list_palettes, to_rgb

__all__ = [
    "compute_mandelbrot",
    "get_palette",
    "list_palettes",
    "to_rgb",
]

__version__ = "0.1.0"