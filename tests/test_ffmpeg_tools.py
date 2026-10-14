"""Subprocess hygiene for the ffmpeg trio.

Inside an MCP stdio server, inherited stdin is the JSON-RPC pipe.
Every ffmpeg/ffprobe child must therefore get DEVNULL stdin, or it
can wait on (or consume) the transport carrying its own tool call.
Measured regression: an encode that takes 1.7 s from the CLI hung
past a 20 s MCP client ceiling before this invariant existed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from moviola_protocol_mcp import ffmpeg_tools


class _Completed:
    returncode = 0
    stdout = '{"streams": [], "format": {}}'
    stderr = ""


def _capture(monkeypatch) -> list[dict]:
    calls: list[dict] = []

    def fake_run(*args, **kwargs):
        calls.append(kwargs)
        return _Completed()

    monkeypatch.setattr(ffmpeg_tools.subprocess, "run", fake_run)
    return calls


def test_run_ffmpeg_closes_stdin(monkeypatch) -> None:
    calls = _capture(monkeypatch)
    ffmpeg_tools.run_ffmpeg(["ffmpeg", "-version"])
    assert calls[0]["stdin"] is subprocess.DEVNULL


def test_probe_media_closes_stdin(monkeypatch, tmp_path: Path) -> None:
    calls = _capture(monkeypatch)
    target = tmp_path / "clip.mp4"
    target.write_bytes(b"not really media")
    ffmpeg_tools.probe_media(str(target), Path("ffprobe"))
    assert calls[0]["stdin"] is subprocess.DEVNULL


def test_ffmpeg_version_closes_stdin(monkeypatch) -> None:
    calls = _capture(monkeypatch)
    ffmpeg_tools.ffmpeg_version(Path("ffmpeg"))
    assert calls[0]["stdin"] is subprocess.DEVNULL
