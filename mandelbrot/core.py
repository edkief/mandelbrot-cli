"""Core Mandelbrot math: vectorised escape-time kernel and palettes."""

from __future__ import annotations

from typing import Tuple

import numpy as np

# Type aliases
FloatArray = np.ndarray
RGBArray = np.ndarray  # shape (H, W, 3), dtype uint8


# ---------------------------------------------------------------------------
# Vectorised escape-time kernel
# ---------------------------------------------------------------------------


def compute_mandelbrot(
    cx: float,
    cy: float,
    width: int,
    height: int,
    zoom: float,
    max_iter: int,
) -> FloatArray:
    """Compute the Mandelbrot set over a rectangular viewport.

    The viewport spans ``[cx - zoom, cx + zoom]`` horizontally and a
    matching (aspect-corrected) range vertically. ``zoom`` is the
    half-width in fractal units.

    Returns a ``(height, width)`` ``float32`` array of *smoothed* escape
    counts. Pixels still in the set after ``max_iter`` iterations are
    assigned ``max_iter`` (a constant interior).
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"width/height must be positive, got {width}x{height}")
    if zoom <= 0:
        raise ValueError(f"zoom must be positive, got {zoom}")
    if max_iter < 1:
        raise ValueError(f"max_iter must be >= 1, got {max_iter}")

    aspect = height / width
    x = np.linspace(cx - zoom, cx + zoom, width, dtype=np.float64)
    y = np.linspace(cy - zoom * aspect, cy + zoom * aspect, height, dtype=np.float64)
    X, Y = np.meshgrid(x, y)
    C = (X + 1j * Y).astype(np.complex128)

    Z = np.zeros_like(C)
    # Default: still in the set after max_iter iterations
    M = np.full(C.shape, float(max_iter), dtype=np.float64)

    # Iteratively iterate. The mask ``still_in`` keeps us from re-updating
    # pixels that have already escaped — keeps the inner loop tight.
    still_in = np.ones(C.shape, dtype=bool)
    log_2 = np.log(2.0)

    for i in range(max_iter):
        # Update only pixels still iterating
        Z[still_in] = Z[still_in] * Z[still_in] + C[still_in]
        abs_z = np.abs(Z)
        escaped_now = still_in & (abs_z > 2.0)
        if not still_in.any():
            # Every pixel has escaped already; remaining interior pixels
            # (if any) are at M = max_iter by default.
            break
        if not escaped_now.any():
            # No new escapes this iteration but some pixels are still
            # iterating — keep going, they may escape later.
            continue
        # Smoothed iteration count: n + 1 - log2(log2(|Z|))
        log_zn = np.log(np.abs(Z[escaped_now]))
        # log_zn can be 0 if Z just touched zero — guard
        nu = np.log(np.maximum(log_zn, 1e-300)) / log_2
        M[escaped_now] = (i + 1) - nu
        still_in[escaped_now] = False

    return M.astype(np.float32)


# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------


def _gradient(stops: list[Tuple[float, Tuple[int, int, int]]]) -> np.ndarray:
    """Build a 256-entry palette by linear-interpolating between stops.

    ``stops`` is a list of ``(position in [0,1], (r, g, b))`` tuples,
    sorted by position. The palette is returned as ``(256, 3)`` uint8.
    """
    table = np.zeros((256, 3), dtype=np.uint8)
    positions = np.array([s[0] for s in stops], dtype=np.float64)
    colors = np.array([s[1] for s in stops], dtype=np.float64)
    # Sort just in case
    order = np.argsort(positions)
    positions = positions[order]
    colors = colors[order]
    xs = np.linspace(0.0, 1.0, 256)
    for c in range(3):
        table[:, c] = np.interp(xs, positions, colors[:, c])
    return table


def _magma() -> np.ndarray:
    return _gradient(
        [
            (0.0, (0, 0, 4)),
            (0.25, (70, 20, 90)),
            (0.5, (180, 50, 100)),
            (0.75, (250, 140, 70)),
            (1.0, (252, 250, 240)),
        ]
    )


def _inferno() -> np.ndarray:
    return _gradient(
        [
            (0.0, (0, 0, 4)),
            (0.25, (60, 15, 90)),
            (0.5, (170, 50, 100)),
            (0.75, (245, 130, 50)),
            (1.0, (252, 255, 164)),
        ]
    )


def _viridis() -> np.ndarray:
    return _gradient(
        [
            (0.0, (68, 1, 84)),
            (0.25, (59, 82, 139)),
            (0.5, (33, 144, 141)),
            (0.75, (94, 201, 98)),
            (1.0, (253, 231, 37)),
        ]
    )


def _ocean() -> np.ndarray:
    return _gradient(
        [
            (0.0, (5, 10, 40)),
            (0.4, (10, 80, 130)),
            (0.7, (60, 180, 200)),
            (1.0, (240, 250, 255)),
        ]
    )


def _fire() -> np.ndarray:
    return _gradient(
        [
            (0.0, (5, 0, 0)),
            (0.4, (180, 30, 0)),
            (0.7, (255, 140, 20)),
            (1.0, (255, 250, 200)),
        ]
    )


def _grayscale() -> np.ndarray:
    g = np.linspace(0, 255, 256).astype(np.uint8)
    return np.stack([g, g, g], axis=1)


_PALETTES = {
    "magma": _magma,
    "inferno": _inferno,
    "viridis": _viridis,
    "ocean": _ocean,
    "fire": _fire,
    "grayscale": _grayscale,
}


def list_palettes() -> list[str]:
    return list(_PALETTES.keys())


def get_palette(name: str) -> np.ndarray:
    """Return a ``(256, 3)`` uint8 palette. Unknown names raise ValueError."""
    key = name.lower()
    if key not in _PALETTES:
        raise ValueError(
            f"unknown palette {name!r}; available: {', '.join(_PALETTES)}"
        )
    return _PALETTES[key]()


def to_rgb(escape: FloatArray, palette: np.ndarray, max_iter: int) -> RGBArray:
    """Map smoothed escape counts to RGB using a 256-entry palette.

    Pixels with escape count == ``max_iter`` (inside the set) are coloured
    black. The remainder are mapped through the palette via a log-scaled
    index so the fine detail near the boundary isn't lost.
    """
    if palette.shape != (256, 3):
        raise ValueError(f"palette must be (256, 3), got {palette.shape}")

    # Mask: inside-set pixels
    inside = escape >= max_iter
    # Log-spaced indices so low escape counts still get distinct colours.
    safe = np.where(inside, 1.0, np.maximum(escape.astype(np.float64), 0.0))
    # Use a logarithm of safe (clamped at 1) to compress range
    t = np.log1p(np.maximum(safe - 1.0, 0.0)) / np.log1p(float(max_iter))
    idx = np.clip((t * 255.0).astype(np.int32), 0, 255)
    rgb = palette[idx].astype(np.uint8)
    rgb[inside] = np.array([0, 0, 0], dtype=np.uint8)
    return rgb