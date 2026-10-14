"""Core conversion: any video/image to any video/image, Moviola-rendered.

Silent by construction: GIF carries no audio and every other output
drops it too (-an), matching the bench doctrine. Every conversion,
successful or not, is written to the index before returning.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .ffmpeg_tools import (
    ConversionError,
    Trio,
    locate_trio,
    probe_media,
    require_ffmpeg,
    run_ffmpeg,
)
from .index_db import record_conversion, resolve_db_path
from .presets import Preset, get_preset

IMAGE_OUTPUTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}
ANIMATED_WEBP_VIDEO_INPUTS = {".gif", ".mp4", ".mov", ".mkv", ".webm", ".avi"}
EVEN_PAD = "pad=ceil(iw/2)*2:ceil(ih/2)*2"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _gif_args(preset: Preset, chain: str) -> list[str]:
    colors = preset.palette_colors or 256
    reserve = ":reserve_transparent=0" if colors <= 2 else ""
    graph = (
        f"[0:v]{chain},split[a][b];"
        f"[a]palettegen=max_colors={colors}{reserve}[p];"
        f"[b][p]paletteuse=dither=none"
    )
    if preset.name == "passthrough" or not chain:
        graph = (
            f"[0:v]split[a][b];"
            f"[a]palettegen=max_colors={colors}[p];"
            f"[b][p]paletteuse=dither=none"
        )
    return ["-filter_complex", graph, "-loop", "0", "-an"]


def _video_args(preset: Preset, chain: str, suffix: str, crf: int) -> list[str]:
    args: list[str] = []
    if chain:
        args += ["-vf", f"{chain},{EVEN_PAD},format=yuv420p"]
    else:
        args += ["-vf", f"{EVEN_PAD}", "-pix_fmt", "yuv420p"]
    if suffix in {".mp4", ".mov", ".m4v", ".mkv"}:
        args += [
            "-c:v",
            "libx264",
            "-crf",
            str(crf),
            "-preset",
            "veryfast",
        ]
        if suffix in {".mp4", ".mov", ".m4v"}:
            args += ["-movflags", "+faststart"]
    elif suffix == ".webm":
        args += ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", str(crf + 7)]
    args.append("-an")
    return args


def _output_args(
    preset: Preset,
    chain: str,
    suffix: str,
    source_suffix: str,
    crf: int,
) -> list[str]:
    if suffix == ".gif":
        return _gif_args(preset, chain)
    if suffix == ".webp" and source_suffix in ANIMATED_WEBP_VIDEO_INPUTS:
        args = ["-vf", chain] if chain else []
        return args + ["-c:v", "libwebp", "-loop", "0", "-an"]
    if suffix in IMAGE_OUTPUTS:
        args = ["-vf", chain] if chain else []
        args += ["-frames:v", "1"]
        if suffix in {".jpg", ".jpeg"}:
            args += ["-q:v", "3"]
        return args
    return _video_args(preset, chain, suffix, crf)


def _run_conversion(
    input_args: list[str],
    source_label: str,
    source_bytes: int | None,
    source_facts: dict,
    output: Path,
    preset: Preset,
    fps: int | None,
    height: int | None,
    crf: int,
    db_path: str | None,
    trio: Trio,
    timeout_seconds: int,
) -> dict:
    ffmpeg = require_ffmpeg(trio)
    output.parent.mkdir(parents=True, exist_ok=True)
    suffix = output.suffix.lower()
    still = suffix in IMAGE_OUTPUTS and suffix != ".webp"
    chain = preset.filter_chain(fps=fps, height=height, include_fps=not still)
    source_suffix = Path(source_label.split(" (+")[0]).suffix.lower()
    args = [str(ffmpeg), "-y", "-v", "error", *input_args]
    args += _output_args(preset, chain, suffix, source_suffix, crf)
    args.append(str(output))

    row: dict = {
        "created_at": _now(),
        "source_path": source_label,
        "source_bytes": source_bytes,
        "source_format": source_facts.get("format"),
        "source_width": source_facts.get("width"),
        "source_height": source_facts.get("height"),
        "source_fps": source_facts.get("fps"),
        "source_duration": source_facts.get("duration"),
        "output_path": str(output),
        "output_format": suffix.lstrip("."),
        "preset": preset.name,
        "height": height or preset.default_height,
        "ffmpeg_path": str(ffmpeg),
        "command": json.dumps(args),
        "status": "ok",
    }
    try:
        run_ffmpeg(args, timeout_seconds=timeout_seconds)
        if not output.exists() or output.stat().st_size == 0:
            raise ConversionError(f"ffmpeg produced no output at {output}")
    except ConversionError as err:
        row["status"] = "error"
        row["error"] = str(err)
        record_conversion(db_path, row)
        raise

    output_facts = probe_media(str(output), trio.ffprobe)
    row["output_bytes"] = output.stat().st_size
    row["output_width"] = output_facts.get("width")
    row["output_height"] = output_facts.get("height")
    row["output_fps"] = output_facts.get("fps")
    if source_bytes:
        row["ratio"] = row["output_bytes"] / source_bytes
        row["bytes_saved"] = source_bytes - row["output_bytes"]
    row_id = record_conversion(db_path, row)

    return {
        "id": row_id,
        "source": source_label,
        "source_bytes": source_bytes,
        "output": str(output),
        "output_bytes": row["output_bytes"],
        "preset": preset.name,
        "fps": fps or preset.default_fps,
        "height": row["height"],
        "ratio": row.get("ratio"),
        "bytes_saved": row.get("bytes_saved"),
        "db_path": str(resolve_db_path(db_path)),
        "ffmpeg": str(ffmpeg),
        "command": args,
    }


def convert_media(
    source: str,
    output: str,
    preset: str = "standard",
    fps: int | None = None,
    height: int | None = None,
    crf: int = 23,
    db_path: str | None = None,
    ffmpeg_dir: str | None = None,
    timeout_seconds: int = 7200,
) -> dict:
    """Convert one file (video or image) to the output path's format.

    The Moviola preset shapes the pixels; the output extension chooses
    the container. gif to mp4 with preset passthrough reproduces the
    OpenCode plugin transcode exactly (plus an even-dimension pad the
    plugin lacks, which only changes odd-sized inputs).
    """
    source_path = Path(source)
    if not source_path.exists():
        raise ConversionError(f"source not found: {source}")
    chosen = get_preset(preset)
    trio = locate_trio(ffmpeg_dir)
    facts = probe_media(source, trio.ffprobe)
    return _run_conversion(
        input_args=["-i", str(source_path)],
        source_label=str(source_path),
        source_bytes=source_path.stat().st_size,
        source_facts=facts,
        output=Path(output),
        preset=chosen,
        fps=fps,
        height=height,
        crf=crf,
        db_path=db_path,
        trio=trio,
        timeout_seconds=timeout_seconds,
    )


def slideshow_from_images(
    images: list[str],
    output: str,
    preset: str = "torch",
    seconds_per_image: float = 1.0,
    fps: int | None = None,
    height: int | None = None,
    crf: int = 23,
    db_path: str | None = None,
    ffmpeg_dir: str | None = None,
    timeout_seconds: int = 7200,
) -> dict:
    """Build a slideshow (gif/mp4/webp) from PNG/JPG images in order.

    With the Torch preset at 5 fps and seconds_per_image=0.2 this is
    the pre-training form: five text/code-rich frames per second in
    one small file. With the Canine Tessersect each image is one
    cell of the 4x4 collage, paced at the 90 fps flash velocity
    (seconds_per_image is then the cell duration only through fps:
    cell duration = 1/(fps or 90)).
    """
    if not images:
        raise ConversionError("slideshow needs at least one image")
    paths = [Path(image) for image in images]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise ConversionError(f"images not found: {', '.join(missing)}")
    if seconds_per_image <= 0:
        raise ConversionError("seconds_per_image must be positive")

    chosen = get_preset(preset)
    trio = locate_trio(ffmpeg_dir)
    if chosen.collage:
        # One image per Tessersect cell, at the flash velocity.
        seconds_per_image = 1.0 / (fps or chosen.default_fps)
    total_bytes = sum(path.stat().st_size for path in paths)
    label = str(paths[0]) + (f" (+{len(paths) - 1} images)" if len(paths) > 1 else "")

    with tempfile.TemporaryDirectory(prefix="moviola-slides-") as tmp:
        listing = Path(tmp) / "slides.txt"
        lines: list[str] = []
        for path in paths:
            escaped = str(path).replace("'", "'\\''")
            lines.append(f"file '{escaped}'")
            lines.append(f"duration {seconds_per_image}")
        escaped_last = str(paths[-1]).replace("'", "'\\''")
        lines.append(f"file '{escaped_last}'")
        listing.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        result = _run_conversion(
            input_args=["-f", "concat", "-safe", "0", "-i", str(listing)],
            source_label=label,
            source_bytes=total_bytes,
            source_facts={"format": paths[0].suffix.lstrip(".").lower()},
            output=Path(output),
            preset=chosen,
            fps=fps,
            height=height,
            crf=crf,
            db_path=db_path,
            trio=trio,
            timeout_seconds=timeout_seconds,
        )
    result["images"] = len(paths)
    result["seconds_per_image"] = seconds_per_image
    return result
