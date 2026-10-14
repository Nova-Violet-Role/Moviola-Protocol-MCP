"""Verbose debuggability: every conversion can narrate itself, indefinitely."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from moviola_protocol_mcp.cli import main as cli_main
from moviola_protocol_mcp.convert import convert_media
from moviola_protocol_mcp.ffmpeg_tools import locate_trio


@pytest.fixture(scope="module")
def clip(tmp_path_factory: pytest.TempPathFactory) -> Path:
    trio = locate_trio()
    if trio.ffmpeg is None:
        pytest.skip("ffmpeg not found")
    dest = tmp_path_factory.mktemp("vfx") / "clip.mp4"
    run = subprocess.run(
        [
            str(trio.ffmpeg),
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=duration=1:size=320x240:rate=10",
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


def test_verbose_conversion_traces_chain_argv_and_index_row(
    clip: Path, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    out = tmp_path / "v.gif"
    quiet = convert_media(
        str(clip), str(out), preset="intersect", db_path=str(tmp_path / "m.db")
    )
    assert "debug" not in quiet

    loud = convert_media(
        str(clip),
        str(tmp_path / "v2.gif"),
        preset="intersect",
        dpi=43,
        db_path=str(tmp_path / "m.db"),
        verbose=True,
    )
    assert "debug" in loud
    joined = "\n".join(loud["debug"])
    assert "filter_chain=" in joined
    assert "argv=" in joined
    assert "dpi=43" in joined
    assert "index_row id=" in joined
    assert "[moviola]" in capsys.readouterr().err


def test_verbose_env_and_cli_flag_both_speak(
    clip: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    monkeypatch.setenv("MOVIOLA_VERBOSE", "1")
    result = convert_media(
        str(clip),
        str(tmp_path / "env.gif"),
        preset="torch",
        db_path=str(tmp_path / "m.db"),
    )
    assert "debug" in result
    monkeypatch.delenv("MOVIOLA_VERBOSE")

    rc = cli_main(
        [
            "--verbose",
            "convert",
            str(clip),
            str(tmp_path / "cli.gif"),
            "--preset",
            "torch",
            "--db",
            str(tmp_path / "m.db"),
        ]
    )
    assert rc == 0
    assert "[moviola]" in capsys.readouterr().err
