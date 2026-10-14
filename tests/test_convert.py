"""Conversion behaviours on generated fixtures (no machine-local files)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from moviola_protocol_mcp.convert import convert_media, slideshow_from_images
from moviola_protocol_mcp.ffmpeg_tools import locate_trio, probe_media


@pytest.fixture(scope="module")
def ffmpeg() -> str:
    trio = locate_trio()
    if trio.ffmpeg is None:
        pytest.skip("ffmpeg not found")
    return str(trio.ffmpeg)


@pytest.fixture(scope="module")
def clip(tmp_path_factory: pytest.TempPathFactory, ffmpeg: str) -> Path:
    dest = tmp_path_factory.mktemp("fx") / "clip.mp4"
    run = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=duration=3:size=640x360:rate=20",
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


def _png(ffmpeg: str, dest: Path, color: str, text: str) -> Path:
    run = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=640x360,drawtext=text='{text}':fontsize=48:fontcolor=white:x=40:y=140",
            "-frames:v",
            "1",
            str(dest),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 0, run.stderr
    return dest


def test_intersect_and_torch_shrink_below_standard(clip: Path, tmp_path: Path) -> None:
    db = str(tmp_path / "moviola.db")
    sizes = {}
    for preset in ("standard", "intersect", "torch"):
        out = tmp_path / f"{preset}.gif"
        result = convert_media(str(clip), str(out), preset=preset, db_path=db)
        sizes[preset] = result["output_bytes"]
        assert out.exists() and out.stat().st_size > 0
    assert sizes["intersect"] < sizes["standard"]
    assert sizes["torch"] < sizes["intersect"]


def test_gif_converts_back_to_mp4_with_the_plugin_settings(
    clip: Path, tmp_path: Path
) -> None:
    db = str(tmp_path / "moviola.db")
    gif = tmp_path / "once.gif"
    convert_media(str(clip), str(gif), preset="intersect", db_path=db)

    mp4 = tmp_path / "back.mp4"
    result = convert_media(str(gif), str(mp4), preset="passthrough", db_path=db)
    assert mp4.exists() and mp4.stat().st_size > 0
    facts = probe_media(str(mp4), locate_trio().ffprobe)
    assert facts["codec"] == "h264"
    assert result["preset"] == "passthrough"


def test_a_still_image_converts_to_a_grey_still_image(
    ffmpeg: str, tmp_path: Path
) -> None:
    db = str(tmp_path / "moviola.db")
    png = _png(ffmpeg, tmp_path / "slide.png", "navy", "MOVIOLA")
    jpg = tmp_path / "slide.jpg"
    convert_media(str(png), str(jpg), preset="standard", db_path=db)
    assert jpg.exists() and jpg.stat().st_size > 0

    one_bit = tmp_path / "slide-1bit.png"
    convert_media(str(png), str(one_bit), preset="torch", db_path=db)
    facts = probe_media(str(one_bit), locate_trio().ffprobe)
    assert facts["height"] == 360


def test_images_become_a_torch_slideshow_gif(ffmpeg: str, tmp_path: Path) -> None:
    db = str(tmp_path / "moviola.db")
    images = [
        str(_png(ffmpeg, tmp_path / "s1.png", "darkred", "ONE")),
        str(_png(ffmpeg, tmp_path / "s2.png", "darkgreen", "TWO")),
        str(_png(ffmpeg, tmp_path / "s3.png", "darkblue", "THREE")),
    ]
    out = tmp_path / "deck.gif"
    result = slideshow_from_images(
        images, str(out), preset="torch", seconds_per_image=0.2, db_path=db
    )
    assert out.exists() and out.stat().st_size > 0
    assert result["images"] == 3
    facts = probe_media(str(out), locate_trio().ffprobe)
    assert facts["height"] == 360
    assert facts["duration"] is not None and facts["duration"] >= 0.5


def test_missing_source_is_refused_by_name(tmp_path: Path) -> None:
    with pytest.raises(Exception, match="source not found"):
        convert_media(
            str(tmp_path / "nope.mp4"),
            str(tmp_path / "out.gif"),
            db_path=str(tmp_path / "moviola.db"),
        )
