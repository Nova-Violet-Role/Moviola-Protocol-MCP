# SPDX-License-Identifier: AGPL-3.0-or-later OR EUPL-1.2
# Copyright 2026 Saimonokuma.
"""TorchPy bridge: Moviola media as PyTorch training instances.

Ladder-compatible by construction: frames can be extracted at any
scaling-ladder stage, chosen in lines (the p metric) or in DPI at a
named reference width, from any filetype ffmpeg decodes - video,
GIF, WebP, still images - including every output of the five
renderings recorded in moviola.db. A Canine Tessersect collage can
be kept as one 16-instant instance or unpacked into its 16 cells.

No numpy, no Pillow: ffmpeg decodes to raw 8-bit grey bytes and
torch reads them with frombuffer. torch itself is an optional
extra (`pip install moviola-protocol-mcp[torch]`); every function
except the Dataset works without it, so demonstrations and exports
run anywhere.
"""

from __future__ import annotations

import io
import json
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .convert import height_for_dpi
from .ffmpeg_tools import ConversionError, locate_trio, probe_media, run_ffmpeg
from .index_db import list_conversions

LADDER_STAGES = (1080, 720, 480, 350, 240, 120)

MEDIA_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".avi",
    ".m4v",
    ".mpg",
    ".mpeg",
    ".ts",
    ".flv",
    ".wmv",
    ".gif",
    ".webp",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tif",
    ".tiff",
    ".avif",
}

try:  # torch is an optional extra; the bridge must import without it.
    import torch
    from torch.utils.data import Dataset as _TorchDataset
except Exception:  # pragma: no cover - exercised when torch absent
    torch = None  # type: ignore[assignment]
    _TorchDataset = object  # type: ignore[assignment,misc]


@dataclass(frozen=True)
class GrayFrames:
    """All grey frames of one file: row-major bytes, frame after frame."""

    data: bytes
    frames: int
    width: int
    height: int

    def frame(self, index: int) -> bytes:
        size = self.width * self.height
        start = index * size
        return self.data[start : start + size]


def _even(value: float) -> int:
    rounded = int(value + 0.5)
    return max(2, rounded + (rounded % 2))


def _target_dims(
    facts: dict,
    height: int | None,
    dpi: float | None,
    reference_width_inches: float,
) -> tuple[int, int]:
    src_w, src_h = facts.get("width"), facts.get("height")
    if not src_w or not src_h:
        raise ConversionError("cannot extract frames: ffprobe reported no dimensions")
    if dpi is not None and height is not None:
        raise ConversionError("dpi and height are two names for one choice; pass one")
    if dpi is not None:
        height = height_for_dpi(dpi, reference_width_inches, src_w, src_h)
    if height is None:
        return int(src_w), int(src_h)
    out_h = min(int(height), int(src_h))
    out_w = _even(src_w * out_h / src_h)
    return out_w, out_h


def extract_gray_frames(
    path: str,
    height: int | None = None,
    dpi: float | None = None,
    reference_width_inches: float = 10.0,
    ffmpeg_dir: str | None = None,
    timeout_seconds: int = 7200,
) -> GrayFrames:
    """Decode every frame of a media file to 8-bit grey bytes.

    Works for any filetype ffmpeg decodes (video, GIF, WebP, still
    images). height selects a ladder stage in lines; dpi selects it
    in pixels-per-inch at the reference width. Never upscales.
    """
    trio = locate_trio(ffmpeg_dir)
    if trio.ffmpeg is None:
        raise ConversionError("ffmpeg not found; see doctor for searched paths")
    facts = probe_media(path, trio.ffprobe)
    out_w, out_h = _target_dims(facts, height, dpi, reference_width_inches)
    # fps_mode passthrough: one output frame per stored frame, always.
    # The default vsync resamples fractional GIF rates (100/17) and
    # silently duplicates instances into a dataset - measured 334
    # extractions from a 167-frame collage before this line existed.
    args = [str(trio.ffmpeg), "-v", "error", "-i", path]
    if (out_w, out_h) != (facts.get("width"), facts.get("height")):
        args += ["-vf", f"scale={out_w}:{out_h}"]
    args += ["-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    try:
        run = subprocess.run(
            args,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as err:
        raise ConversionError(
            f"ffmpeg exceeded the {timeout_seconds}s ceiling during extraction"
        ) from err
    if run.returncode != 0:
        tail = "\n".join(
            (run.stderr or b"").decode("utf-8", "replace").splitlines()[-6:]
        )
        raise ConversionError(
            f"ffmpeg exited {run.returncode} extracting {path}:\n{tail}"
        )
    frame_size = out_w * out_h
    count = len(run.stdout) // frame_size if frame_size else 0
    return GrayFrames(
        data=run.stdout[: count * frame_size],
        frames=count,
        width=out_w,
        height=out_h,
    )


def unpack_collage(frame: bytes, width: int, height: int, grid: int = 4) -> list[bytes]:
    """Split one Tessersect collage frame into its cells, in time order.

    Cells read row-major, oldest top-left to newest bottom-right -
    the order tile=4x4 laid them down.
    """
    if width % grid or height % grid:
        raise ConversionError(
            f"collage {width}x{height} is not divisible into a {grid}x{grid} net"
        )
    cell_w, cell_h = width // grid, height // grid
    cells: list[bytes] = []
    for cell_row in range(grid):
        for cell_col in range(grid):
            cell = bytearray()
            for y in range(cell_h):
                start = (cell_row * cell_h + y) * width + cell_col * cell_w
                cell += frame[start : start + cell_w]
            cells.append(bytes(cell))
    return cells


def collect_media_files(root: str) -> list[str]:
    """Every training-usable media file under a directory, sorted."""
    base = Path(root)
    return [
        str(path)
        for path in sorted(base.rglob("*"))
        if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS
    ]


def sources_from_index(
    db_path: str | None = None,
    preset: str | None = None,
    limit: int = 100000,
) -> list[str]:
    """Dataset sources from the index, oldest first, per rendering.

    preset filters to one of the five renderings (standard,
    intersect, torch, canine, passthrough); None takes all of them.
    """
    rows = list_conversions(db_path=db_path, limit=limit, preset=preset)
    ok = [row["output_path"] for row in rows if row.get("status") == "ok"]
    return list(reversed(ok))


def _resolve_sources(sources: "str | list[str]") -> list[str]:
    if isinstance(sources, str):
        path = Path(sources)
        if path.is_dir():
            return collect_media_files(sources)
        return [sources]
    resolved: list[str] = []
    for item in sources:
        resolved.extend(_resolve_sources(item))
    return resolved


class MoviolaFrameDataset(_TorchDataset):
    """A torch Dataset of Moviola grey frames, ladder-stage aware.

    Each item is a float32 tensor [1, H, W] in 0..1. Choose the
    stage in lines (height or ladder_stage, one of LADDER_STAGES)
    or in DPI at a reference width. With unpack_collage=True a
    Tessersect collage frame yields its 16 cells as 16 instances.
    Frames are extracted once per file and cached in memory, which
    suits demonstration and fine-tuning scale; for streaming-scale
    corpora, export shards with export_webdataset instead.
    """

    def __init__(
        self,
        sources: "str | list[str]",
        height: int | None = None,
        dpi: float | None = None,
        reference_width_inches: float = 10.0,
        ladder_stage: int | None = None,
        unpack_collage: bool = False,
        ffmpeg_dir: str | None = None,
    ) -> None:
        if torch is None:
            raise RuntimeError(
                "torch is not installed; install the training extra: "
                "pip install 'moviola-protocol-mcp[torch]' - frames remain "
                "available torch-free via extract_gray_frames"
            )
        if ladder_stage is not None:
            if ladder_stage not in LADDER_STAGES:
                raise ConversionError(
                    f"ladder_stage must be one of {LADDER_STAGES}, got {ladder_stage}"
                )
            if height is not None or dpi is not None:
                raise ConversionError("ladder_stage already names the height")
            height = ladder_stage
        self.height = height
        self.dpi = dpi
        self.reference_width_inches = reference_width_inches
        self.unpack_collage = unpack_collage
        self._cache: dict[str, GrayFrames] = {}
        self._entries: list[tuple[str, int, int | None]] = []
        for source in _resolve_sources(sources):
            frames = self._frames_for(source, ffmpeg_dir)
            for frame_index in range(frames.frames):
                if unpack_collage:
                    for cell_index in range(16):
                        self._entries.append((source, frame_index, cell_index))
                else:
                    self._entries.append((source, frame_index, None))

    @classmethod
    def from_index(
        cls,
        db_path: str | None = None,
        preset: str | None = None,
        **kwargs,
    ) -> "MoviolaFrameDataset":
        """Build a dataset from moviola.db, optionally per rendering."""
        return cls(sources_from_index(db_path=db_path, preset=preset), **kwargs)

    def _frames_for(self, source: str, ffmpeg_dir: str | None = None) -> GrayFrames:
        if source not in self._cache:
            self._cache[source] = extract_gray_frames(
                source,
                height=self.height,
                dpi=self.dpi,
                reference_width_inches=self.reference_width_inches,
                ffmpeg_dir=ffmpeg_dir,
            )
        return self._cache[source]

    def __len__(self) -> int:
        return len(self._entries)

    def __getitem__(self, index: int):
        source, frame_index, cell_index = self._entries[index]
        frames = self._frames_for(source)
        raw = frames.frame(frame_index)
        width, height = frames.width, frames.height
        if cell_index is not None:
            raw = unpack_collage(raw, width, height)[cell_index]
            width //= 4
            height //= 4
        tensor = torch.frombuffer(bytearray(raw), dtype=torch.uint8)
        return tensor.reshape(1, height, width).float() / 255.0


def export_image_folder(
    sources: "str | list[str]",
    out_dir: str,
    image_format: str = "png",
    height: int | None = None,
    dpi: float | None = None,
    reference_width_inches: float = 10.0,
    ffmpeg_dir: str | None = None,
    timeout_seconds: int = 7200,
) -> dict:
    """Export every frame as an image file, ImageFolder-ready.

    Layout: <out_dir>/<source-stem>/<stem>-NNNNNN.<fmt> - one class
    directory per source, which torchvision's ImageFolder reads
    directly. Format conversion covers png, jpg, bmp, webp, tiff.
    """
    if image_format not in {"png", "jpg", "jpeg", "bmp", "webp", "tiff"}:
        raise ConversionError(f"unsupported image format for export: {image_format}")
    trio = locate_trio(ffmpeg_dir)
    if trio.ffmpeg is None:
        raise ConversionError("ffmpeg not found; see doctor for searched paths")
    out_root = Path(out_dir)
    written = 0
    for source in _resolve_sources(sources):
        facts = probe_media(source, trio.ffprobe)
        out_w, out_h = _target_dims(facts, height, dpi, reference_width_inches)
        stem = Path(source).stem
        class_dir = out_root / stem
        class_dir.mkdir(parents=True, exist_ok=True)
        before = len(list(class_dir.glob(f"*.{image_format}")))
        args = [str(trio.ffmpeg), "-y", "-v", "error", "-i", source]
        if (out_w, out_h) != (facts.get("width"), facts.get("height")):
            args += ["-vf", f"scale={out_w}:{out_h}"]
        args += ["-fps_mode", "passthrough"]
        if image_format in {"jpg", "jpeg"}:
            args += ["-q:v", "3"]
        args.append(str(class_dir / f"{stem}-%06d.{image_format}"))
        run_ffmpeg(args, timeout_seconds=timeout_seconds)
        written += len(list(class_dir.glob(f"*.{image_format}"))) - before
    return {"written": written, "out_dir": str(out_root), "format": image_format}


def export_webdataset(
    sources: "str | list[str]",
    tar_path: str,
    height: int | None = None,
    dpi: float | None = None,
    reference_width_inches: float = 10.0,
    ffmpeg_dir: str | None = None,
    timeout_seconds: int = 7200,
) -> dict:
    """Export a WebDataset tar shard: NNNNNNNNN.png + .json per frame.

    Each .json names the source file, frame index, dimensions and
    the stage the frame was cut at - the shard stays falsifiable
    against the index it came from.
    """
    files = _resolve_sources(sources)
    samples = 0
    with tarfile.open(tar_path, "w") as tar:
        with tempfile.TemporaryDirectory(prefix="moviola-wds-") as tmp:
            for source in files:
                exported = export_image_folder(
                    [source],
                    tmp,
                    image_format="png",
                    height=height,
                    dpi=dpi,
                    reference_width_inches=reference_width_inches,
                    ffmpeg_dir=ffmpeg_dir,
                    timeout_seconds=timeout_seconds,
                )
                stem = Path(source).stem
                pngs = sorted((Path(tmp) / stem).glob("*.png"))
                facts = probe_media(source, locate_trio(ffmpeg_dir).ffprobe)
                for frame_index, png in enumerate(pngs):
                    key = f"{samples:09d}"
                    tar.add(png, arcname=f"{key}.png")
                    meta = json.dumps(
                        {
                            "source": source,
                            "frame": frame_index,
                            "source_width": facts.get("width"),
                            "source_height": facts.get("height"),
                            "height": height,
                            "dpi": dpi,
                            "reference_width_inches": reference_width_inches,
                        }
                    ).encode("utf-8")
                    info = tarfile.TarInfo(f"{key}.json")
                    info.size = len(meta)
                    tar.addfile(info, io.BytesIO(meta))
                    samples += 1
                _ = exported
    return {
        "samples": samples,
        "tar_path": tar_path,
        "bytes": Path(tar_path).stat().st_size,
    }
