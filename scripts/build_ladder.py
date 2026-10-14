# SPDX-License-Identifier: AGPL-3.0-or-later OR EUPL-1.2
# Copyright 2026 Saimonokuma.
"""Build the three scaling-ladder GIFs and print the measured tables.

Variants (one stepping ladder GIF each):
  V1 DPI-metric  preset standard, stage chosen by --dpi logic at a
                 10-inch reference width, segments labeled in DPI
  V2 p-resolution preset intersect, stages labeled in p
  V3 Torch        preset torch, stages labeled in p with byte rates

Stages: Original(1080) 720 480 350 240 120 lines. The source is a
generated true-1080p text/code-rich clip (training-style content),
so every stage is a real downscale. Per-stage byte numbers come
from direct convert_media cuts recorded in the work index; the
labels and the common-canvas assembly are a presentation-only
second pass and are never quoted as measurements.

Run:  uv run python scripts/build_ladder.py
Out:  docs/ladder/ladder-{dpi,p,torch}.gif + JSON tables on stdout
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from moviola_protocol_mcp.convert import convert_media
from moviola_protocol_mcp.ffmpeg_tools import locate_trio, probe_media, run_ffmpeg

STAGES = [1080, 720, 480, 350, 240, 120]
REFERENCE_WIDTH_INCHES = 10.0
SEGMENT_SECONDS = 2.0
SEGMENT_START = 4.0
CANVAS_W, CANVAS_H, LABEL_H = 854, 480, 44


def dpi_for_stage(height: int, src_w: int, src_h: int) -> float:
    """DPI at the reference width whose derived height is this stage."""
    width_px = height * src_w / src_h
    return width_px / REFERENCE_WIDTH_INCHES


def make_source(ffmpeg: Path, dest: Path) -> None:
    lines = [
        "def tessersect(cells):  # 16 instants, one flash",
        "    return [grey_ink(c) for c in cells]",
        "class MoviolaFrameDataset(Dataset):",
        "    def __getitem__(self, i):  # [1,H,W] float",
        "        return self.frames[i] / 255.0",
        "DIVERGENCE = 0.571024 + saved * 0.477572",
        "for epoch in range(90):  # canine flicker band",
        "    batch = loader.next()  # 24.6 B per instant",
    ]
    filters = []
    for i, line in enumerate(lines):
        text = line.replace(":", "\\:").replace("'", "")
        filters.append(
            f"drawtext=text='{text}':fontsize=40:fontcolor=white:x=70:y={110 + i * 95}"
        )
    filters.append(
        "drawtext=text='MOVIOLA SCALING LADDER 1080p SOURCE':fontsize=54:"
        "fontcolor=white:x=70:y=30"
    )
    filters.append("drawbox=x='mod(t*240,1760)':y=940:w=120:h=90:color=white:t=fill")
    filters.append(
        "drawtext=text='t=%{pts\\:hms}':fontsize=40:fontcolor=white:x=1500:y=30"
    )
    run_ffmpeg(
        [
            str(ffmpeg),
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x14141f:s=1920x1080:r=30:d=12",
            "-vf",
            ",".join(filters),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "16",
            str(dest),
        ],
        timeout_seconds=600,
    )


def make_segment(ffmpeg: Path, stage_gif: Path, label: str, dest: Path) -> None:
    """Presentation pass: window, neighbor-scale to canvas, label bar."""
    text = label.replace(":", "\\:").replace("'", "")
    vf = (
        f"fps=10,scale={CANVAS_W}:-2:flags=neighbor,"
        f"pad={CANVAS_W}:{CANVAS_H + LABEL_H}:(ow-iw)/2:0:black,"
        f"drawtext=text='{text}':fontsize=26:fontcolor=white:"
        f"x=(w-text_w)/2:y={CANVAS_H + 10},"
        "split[a][b];[a]palettegen=max_colors=16[p];[b][p]paletteuse=dither=none"
    )
    run_ffmpeg(
        [
            str(ffmpeg),
            "-y",
            "-v",
            "error",
            "-ss",
            str(SEGMENT_START),
            "-t",
            str(SEGMENT_SECONDS),
            "-i",
            str(stage_gif),
            "-filter_complex",
            f"[0:v]{vf}",
            "-loop",
            "0",
            "-an",
            str(dest),
        ],
        timeout_seconds=600,
    )


def concat_segments(ffmpeg: Path, segments: list[Path], dest: Path, work: Path) -> None:
    listing = work / "concat.txt"
    listing.write_text(
        "".join(f"file '{s}'\n" for s in segments), encoding="utf-8", newline="\n"
    )
    run_ffmpeg(
        [
            str(ffmpeg),
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-filter_complex",
            "[0:v]split[a][b];[a]palettegen=max_colors=16[p];"
            "[b][p]paletteuse=dither=none",
            "-loop",
            "0",
            "-an",
            str(dest),
        ],
        timeout_seconds=600,
    )


def main() -> int:
    trio = locate_trio()
    if trio.ffmpeg is None:
        print("ffmpeg not found", file=sys.stderr)
        return 1
    repo = Path(__file__).resolve().parents[1]
    out_dir = repo / "docs" / "ladder"
    out_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="moviola-ladder-"))
    db = str(work / "ladder.db")

    source = work / "source-1080p.mp4"
    print(f"generating source -> {source}", file=sys.stderr)
    make_source(trio.ffmpeg, source)
    facts = probe_media(str(source), trio.ffprobe)
    duration = float(facts["duration"] or 12.0)
    src_w, src_h = int(facts["width"]), int(facts["height"])
    print(
        f"source: {source.stat().st_size} B, {src_w}x{src_h}, {duration}s",
        file=sys.stderr,
    )

    variants = [
        ("dpi", "standard"),
        ("p", "intersect"),
        ("torch", "torch"),
    ]
    report: dict = {"source": facts, "variants": {}}
    for variant, preset in variants:
        rows = []
        segments: list[Path] = []
        for stage in STAGES:
            dpi = dpi_for_stage(stage, src_w, src_h)
            stage_gif = work / f"{variant}-{stage}.gif"
            kwargs: dict = {}
            if variant == "dpi":
                kwargs = {
                    "dpi": dpi,
                    "reference_width_inches": REFERENCE_WIDTH_INCHES,
                }
            else:
                kwargs = {"height": stage}
            result = convert_media(
                str(source),
                str(stage_gif),
                preset=preset,
                db_path=db,
                **kwargs,
            )
            rate = result["output_bytes"] / duration
            stage_facts = probe_media(str(stage_gif), trio.ffprobe)
            row = {
                "stage_height": stage,
                "dpi_at_10in": round(dpi, 1),
                "output_width": stage_facts["width"],
                "output_height": stage_facts["height"],
                "output_bytes": result["output_bytes"],
                "bytes_per_second": round(rate),
                "mb_per_1h50m": round(rate * 6600 / 1_000_000, 2),
            }
            rows.append(row)
            if variant == "dpi":
                label = (
                    f"{dpi:.0f} DPI at 10in  {stage_facts['width']}x"
                    f"{stage_facts['height']}  {round(rate)} B/s"
                )
            elif variant == "torch":
                label = f"TORCH {stage}p  {round(rate)} B/s"
            else:
                label = (
                    f"{stage}p  {stage_facts['width']}x{stage_facts['height']}"
                    f"  {round(rate)} B/s"
                )
            segment = work / f"seg-{variant}-{stage}.gif"
            make_segment(trio.ffmpeg, stage_gif, label, segment)
            segments.append(segment)
            print(f"{variant} {stage}p: {row}", file=sys.stderr)
        ladder_gif = out_dir / f"ladder-{variant}.gif"
        concat_segments(trio.ffmpeg, segments, ladder_gif, work)
        report["variants"][variant] = {
            "preset": preset,
            "ladder_gif": str(ladder_gif),
            "ladder_bytes": ladder_gif.stat().st_size,
            "stages": rows,
        }
        print(
            f"ladder {variant}: {ladder_gif} {ladder_gif.stat().st_size} B",
            file=sys.stderr,
        )

    report["work_dir"] = str(work)
    report["db"] = db
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
