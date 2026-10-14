"""DPI as a resolution metric: pixels per inch at a stated reference size."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from moviola_protocol_mcp.convert import convert_media, height_for_dpi
from moviola_protocol_mcp.ffmpeg_tools import locate_trio, probe_media


def test_height_for_dpi_derives_the_pixel_grid_from_inches() -> None:
    # 32 dpi across a 10-inch reference width = 320 px wide;
    # a 640x360 source keeps aspect, so 180 lines.
    assert height_for_dpi(32, 10.0, 640, 360) == 180
    # 192 dpi across 10 inches = 1920 px wide = 1080 lines at 16:9.
    assert height_for_dpi(192, 10.0, 1920, 1080) == 1080


def test_converting_by_dpi_lands_on_the_derived_height(tmp_path: Path) -> None:
    trio = locate_trio()
    if trio.ffmpeg is None:
        pytest.skip("ffmpeg not found")
    clip = tmp_path / "clip.mp4"
    run = subprocess.run(
        [
            str(trio.ffmpeg),
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=duration=2:size=640x360:rate=10",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(clip),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 0, run.stderr

    out = tmp_path / "by-dpi.gif"
    result = convert_media(
        str(clip),
        str(out),
        preset="intersect",
        dpi=32,
        db_path=str(tmp_path / "moviola.db"),
    )
    facts = probe_media(str(out), trio.ffprobe)
    assert facts["width"] == 320
    assert facts["height"] == 180
    assert result["height"] == 180


def test_dpi_and_explicit_height_together_are_refused(tmp_path: Path) -> None:
    with pytest.raises(Exception, match="dpi and height"):
        convert_media(
            str(tmp_path / "x.mp4"),
            str(tmp_path / "y.gif"),
            dpi=72,
            height=240,
            db_path=str(tmp_path / "moviola.db"),
        )
