# mandelbrot-cli

A small, dependency-light CLI for drawing the Mandelbrot set in three flavours:

| Mode        | What it does                                                          |
| ----------- | --------------------------------------------------------------------- |
| `render`    | Renders a single static PNG.                                           |
| `view`      | Interactive, keyboard-driven viewer in your terminal (ANSI half-block).|
| `animate`   | Renders a log-zoom animation as an animated GIF (or MP4 if ffmpeg).    |

The math kernel is fully vectorised with NumPy (no Python per-pixel loops) and the inner iteration is masked so escaped pixels are skipped on subsequent steps.

## Install

```bash
pip install -r requirements.txt
```

For MP4 output from `animate` you also need [`ffmpeg`](https://ffmpeg.org/) on `PATH`. Without it, `animate` falls back to GIF.

## Quick start

```bash
# Static PNG: classic view of the whole set
python -m mandelbrot render \
    --cx -0.5 --cy 0 --zoom 1.5 --iters 1000 \
    --width 1200 --height 800 --palette magma \
    --out examples/mandelbrot.png

# Interactive terminal viewer
python -m mandelbrot view

# Animated zoom into the seahorse valley
python -m mandelbrot animate \
    --cx -0.74364 --cy 0.13182 \
    --zoom-start 0.01 --zoom-end 1e-4 \
    --frames 60 --fps 15 --palette inferno \
    --out examples/seahorse_zoom.gif
```

Each subcommand has full `--help`.

## Subcommands

### `render`

```
python -m mandelbrot render [--cx -0.5] [--cy 0.0] [--zoom 1.5]
                            [--width 1200] [--height 800]
                            [--iters 1000] [--palette magma]
                            [--out mandelbrot.png]
```

`zoom` is the **half-width** of the viewport in fractal units; the vertical half-width is `zoom * (height / width)`.

### `view`

```
python -m mandelbrot view [--cx -0.5] [--cy 0.0] [--zoom 1.5]
                          [--iters 256] [--palette magma]
```

Key bindings (the viewer uses raw ANSI, no curses):

| Key             | Action                                  |
| --------------- | --------------------------------------- |
| Arrow keys      | Pan by 1/4 of the visible viewport      |
| `+` / `=`       | Zoom in (×2 detail)                     |
| `-` / `_`       | Zoom out (×2)                           |
| `i`             | Double iteration depth (slower, sharper)|
| `r`             | Reset to starting view                  |
| `h` / `?`       | Show help                               |
| `q` / `Esc`     | Quit                                    |

The viewer requires a TTY. Pixel rows are packed two-per-terminal-row using the Unicode upper-half-block (`▀`), so vertical resolution is effectively doubled.

### `animate`

```
python -m mandelbrot animate [--cx -0.74364] [--cy 0.13182]
                             [--zoom-start 0.01] [--zoom-end 1e-5]
                             [--frames 60] [--fps 15]
                             [--width 480] [--height 320]
                             [--iters 400] [--palette magma]
                             [--out zoom.gif]
```

Zoom is interpolated **log-linearly** so the perceived speed of approach stays constant as the camera dives in. Iteration depth is also ramped up per frame. The output suffix decides the container:

| `--out` suffix | Encoder                                |
| -------------- | -------------------------------------- |
| `.gif`         | Pillow, adaptive palette, no optimize  |
| `.mp4` / `.webm` | ffmpeg (libx264 / libvpx-vp9)         |
| anything else  | Falls back to `.gif`                   |

## Palettes

```
python -m mandelbrot --list-palettes
# Available palettes: magma, inferno, viridis, ocean, fire, grayscale
```

All palettes are 256-entry RGB tables built by linear interpolation between a handful of anchor colours, so you can tweak or add new ones in `mandelbrot/core.py` without touching the math.

## Project layout

```
mandelbrot/
  __init__.py
  __main__.py
  core.py         # numpy escape-time kernel + palettes
  render.py       # static PNG renderer
  interactive.py  # ANSI half-block terminal viewer
  animate.py      # log-zoom animation + GIF/MP4 encoder
  cli.py          # argparse entry point (subcommands: render, view, animate)
examples/
  mandelbrot.png        # sample static render
  seahorse_zoom.gif     # sample animation
requirements.txt
README.md
```

## Notes & limitations

- The escape-time kernel uses a smoothed iteration count (`n + 1 - log2(log2 |Z|)`) so boundary detail doesn't band.
- The interactive viewer relies on true colour ANSI (`\x1b[38;2;…m`); old terminals without 24-bit colour will fall back to default colours.
- `animate` writes frames fully in-memory. Very long animations (e.g. 500+ frames at 1080p) can use a lot of RAM.
- `animate` without ffmpeg always writes a GIF; GIF file size grows quickly with iteration depth, so prefer moderate `--iters` (≤ 1000) and modest frame counts.