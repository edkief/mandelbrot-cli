"""Animated zoom: render a sequence of frames and stitch into a GIF / MP4."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Union

import numpy as np
from PIL import Image

from .core import compute_mandelbrot, get_palette, to_rgb


PathLike = Union[str, Path]


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _log_lerp(start: float, end: float, t: float) -> float:
    """Linearly interpolate in log-space (geometric progression)."""
    if start <= 0 or end <= 0:
        # Fallback to plain linear interp for non-positive values
        return start + (end - start) * t
    log_s = np.log(start)
    log_e = np.log(end)
    return float(np.exp(log_s + (log_e - log_s) * t))


def animate(
    out_path: PathLike,
    cx: float,
    cy: float,
    zoom_start: float,
    zoom_end: float,
    frames: int,
    fps: float,
    width: int,
    height: int,
    max_iter: int,
    palette: str = "magma",
) -> Path:
    """Render an animated zoom GIF/MP4.

    The zoom level for frame ``i`` (in ``[0, frames - 1]``) is
    ``zoom_start * (zoom_end / zoom_start) ** (i / (frames - 1))`` —
    log-linear interpolation so the perceived speed is constant.
    """
    if frames < 2:
        raise ValueError(f"frames must be >= 2, got {frames}")
    if fps <= 0:
        raise ValueError(f"fps must be > 0, got {fps}")

    pal_arr = get_palette(palette)
    pil_frames: list[Image.Image] = []
    progress_every = max(1, frames // 10)

    for i in range(frames):
        t = i / (frames - 1)
        z = _log_lerp(zoom_start, zoom_end, t)
        # Ramp up iteration depth as we zoom in
        iters = max_iter + i * 25
        escape = compute_mandelbrot(cx, cy, width, height, z, iters)
        rgb = to_rgb(escape, pal_arr, iters)
        pil_frames.append(Image.fromarray(rgb, mode="RGB"))
        if (i + 1) % progress_every == 0 or i == frames - 1:
            print(f"  frame {i + 1}/{frames}  zoom={z:.3e}", file=__import__("sys").stderr)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = int(round(1000.0 / fps))

    suffix = out.suffix.lower()

    if suffix in (".mp4", ".webm"):
        if _has_ffmpeg():
            _encode_ffmpeg(pil_frames, out, fps)
        else:
            print(
                f"  note: {suffix} requested but ffmpeg is not installed; "
                "writing animated GIF instead.",
                file=__import__("sys").stderr,
            )
            out = out.with_suffix(".gif")
            _encode_gif(pil_frames, out, duration_ms)
        return out

    if suffix != ".gif":
        # Unknown extension — default to .gif next to the requested path.
        print(
            f"  note: unknown extension {suffix!r}; defaulting to .gif.",
            file=__import__("sys").stderr,
        )
        out = out.with_suffix(".gif")

    _encode_gif(pil_frames, out, duration_ms)
    return out


def _encode_gif(
    pil_frames: list[Image.Image], out: Path, duration_ms: int
) -> None:
    """Encode a list of RGB frames as a GIF.

    Note: we intentionally do *not* pass ``optimize=True`` or
    ``disposal=2`` — Pillow's multi-frame GIF writer drops frames when
    those flags are set (https://github.com/python-pillow/Pillow/issues/4594).
    A per-frame adaptive palette keeps file size reasonable without
    losing frames.
    """
    paletted = [
        img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
        for img in pil_frames
    ]
    paletted[0].save(
        out,
        format="GIF",
        save_all=True,
        append_images=paletted[1:],
        duration=duration_ms,
        loop=0,
    )


def _encode_ffmpeg(
    pil_frames: list[Image.Image], out: Path, fps: float
) -> None:
    """Pipe frames into ffmpeg and encode an MP4/WebM."""
    codec_args = {
        ".mp4": ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast"],
        ".webm": ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30"],
    }
    suffix = out.suffix.lower()
    args = ["ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{pil_frames[0].width}x{pil_frames[0].height}",
            "-pix_fmt", "rgb24", "-r", str(fps), "-i", "pipe:0"]
    args += codec_args.get(suffix, codec_args[".mp4"])
    args += ["-an", str(out)]

    proc = subprocess.run(
        args,
        input=b"".join(_frame_to_bytes(f) for f in pil_frames),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (rc={proc.returncode}): "
            + proc.stderr.decode("utf-8", errors="ignore")[-1000:]
        )


def _frame_to_bytes(img: Image.Image) -> bytes:
    """Return raw RGB bytes for an RGB PIL image."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    return np.asarray(img, dtype=np.uint8).tobytes()