"""Acceptance test: the walking skeleton of the Moviola Protocol MCP.

Converting a real clip with the Standard Moviola preset must produce a
smaller GIF and exactly one row in the always-seeable index database.
"""

from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path

import pytest

REFERENCE_MP4 = Path(
    r"C:\Users\Saimono\AppData\Local\Temp\opencode\moviola-doctor-8.mp4"
)


def _make_clip(ffmpeg: str, dest: Path) -> Path:
    """Generate a 2 second test clip when the reference clip is absent."""
    run = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=duration=2:size=320x240:rate=10",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(dest),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 0, run.stderr
    return dest


def test_converting_a_clip_with_standard_moviola_produces_a_smaller_gif_and_one_index_row(
    tmp_path: Path,
) -> None:
    from moviola_protocol_mcp.convert import convert_media
    from moviola_protocol_mcp.ffmpeg_tools import locate_trio

    trio = locate_trio()
    if trio.ffmpeg is None:
        pytest.skip("ffmpeg not found (looked in C:\\Hybrid\\64bit and PATH)")

    source = (
        REFERENCE_MP4
        if REFERENCE_MP4.exists()
        else _make_clip(str(trio.ffmpeg), tmp_path / "clip.mp4")
    )
    output = tmp_path / "clip-standard.gif"
    db_path = tmp_path / "moviola.db"

    result = convert_media(
        source=str(source),
        output=str(output),
        preset="standard",
        db_path=str(db_path),
    )

    assert output.exists(), result
    assert 0 < output.stat().st_size < source.stat().st_size
    assert result["preset"] == "standard"
    assert result["output_bytes"] == output.stat().st_size
    assert db_path.exists()

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT preset, source_bytes, output_bytes FROM conversions"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "standard"
    assert rows[0][1] == source.stat().st_size
    assert rows[0][2] == output.stat().st_size
