"""Locate the ffmpeg/ffprobe/ffplay trio, probe media, run ffmpeg.

Resolution order, first hit wins:
1. explicit directory argument
2. MOVIOLA_FFMPEG_DIR, then FFMPEG_PATH (file or directory)
3. C:\\Hybrid\\64bit, then C:\\Hybrid\\32bit (the house install)
4. PATH

ffmpeg is always run as an argument list. No shell ever sees these paths.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

HYBRID_DIRS = [Path(r"C:\Hybrid\64bit"), Path(r"C:\Hybrid\32bit")]
EXE_SUFFIX = ".exe" if os.name == "nt" else ""


class ConversionError(RuntimeError):
    """ffmpeg ran and said no, or could not be found at all."""


@dataclass
class Trio:
    ffmpeg: Path | None
    ffprobe: Path | None
    ffplay: Path | None
    searched: list[str] = field(default_factory=list)

    def describe(self) -> dict:
        return {
            "ffmpeg": str(self.ffmpeg) if self.ffmpeg else None,
            "ffprobe": str(self.ffprobe) if self.ffprobe else None,
            "ffplay": str(self.ffplay) if self.ffplay else None,
            "searched": self.searched,
        }


def _trio_in(directory: Path) -> Trio | None:
    ffmpeg = directory / f"ffmpeg{EXE_SUFFIX}"
    if not ffmpeg.exists():
        return None
    ffprobe = directory / f"ffprobe{EXE_SUFFIX}"
    ffplay = directory / f"ffplay{EXE_SUFFIX}"
    return Trio(
        ffmpeg=ffmpeg,
        ffprobe=ffprobe if ffprobe.exists() else None,
        ffplay=ffplay if ffplay.exists() else None,
    )


def locate_trio(explicit_dir: str | None = None) -> Trio:
    """Find the trio. The returned Trio names every place searched."""
    searched: list[str] = []
    candidates: list[Path] = []
    if explicit_dir:
        candidates.append(Path(explicit_dir))
    env_dir = os.environ.get("MOVIOLA_FFMPEG_DIR")
    if env_dir:
        candidates.append(Path(env_dir))
    env_ffmpeg = os.environ.get("FFMPEG_PATH")
    if env_ffmpeg:
        env_path = Path(env_ffmpeg)
        candidates.append(env_path if env_path.is_dir() else env_path.parent)
    candidates.extend(HYBRID_DIRS)

    for directory in candidates:
        searched.append(str(directory))
        trio = _trio_in(directory)
        if trio:
            trio.searched = searched
            if trio.ffprobe is None:
                which_probe = shutil.which("ffprobe")
                trio.ffprobe = Path(which_probe) if which_probe else None
            return trio

    searched.append("PATH")
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        which_probe = shutil.which("ffprobe")
        which_play = shutil.which("ffplay")
        return Trio(
            ffmpeg=Path(which_ffmpeg),
            ffprobe=Path(which_probe) if which_probe else None,
            ffplay=Path(which_play) if which_play else None,
            searched=searched,
        )
    return Trio(ffmpeg=None, ffprobe=None, ffplay=None, searched=searched)


def require_ffmpeg(trio: Trio) -> Path:
    if trio.ffmpeg is None:
        places = ", ".join(trio.searched)
        raise ConversionError(
            f"ffmpeg not found; searched: {places}. "
            "Set MOVIOLA_FFMPEG_DIR or FFMPEG_PATH."
        )
    return trio.ffmpeg


def _parse_frame_rate(raw: str | None) -> float | None:
    if not raw or raw == "0/0":
        return None
    if "/" in raw:
        num, _, den = raw.partition("/")
        try:
            return float(num) / float(den) if float(den) else None
        except ValueError:
            return None
    try:
        return float(raw)
    except ValueError:
        return None


def probe_media(path: str, ffprobe: Path | None) -> dict:
    """Probe one file with ffprobe. Missing ffprobe yields size only."""
    target = Path(path)
    facts: dict = {
        "path": str(target),
        "bytes": target.stat().st_size if target.exists() else None,
        "format": target.suffix.lstrip(".").lower() or None,
        "width": None,
        "height": None,
        "fps": None,
        "duration": None,
        "codec": None,
        "frames": None,
    }
    if ffprobe is None or not target.exists():
        return facts
    run = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(target),
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if run.returncode != 0:
        return facts
    try:
        report = json.loads(run.stdout)
    except json.JSONDecodeError:
        return facts
    fmt = report.get("format") or {}
    if fmt.get("duration"):
        facts["duration"] = float(fmt["duration"])
    if fmt.get("format_name"):
        facts["format"] = fmt["format_name"]
    for stream in report.get("streams") or []:
        if stream.get("codec_type") == "video":
            facts["width"] = stream.get("width")
            facts["height"] = stream.get("height")
            facts["codec"] = stream.get("codec_name")
            facts["fps"] = _parse_frame_rate(stream.get("avg_frame_rate"))
            if stream.get("nb_frames"):
                try:
                    facts["frames"] = int(stream["nb_frames"])
                except ValueError:
                    pass
            break
    return facts


def run_ffmpeg(args: list[str], timeout_seconds: int = 7200) -> None:
    """Run ffmpeg in the foreground; a nonzero exit raises with its tail.

    stdin is always DEVNULL: inside an MCP stdio server, inherited
    stdin is the JSON-RPC pipe, and ffmpeg must never read or wait
    on the transport that carries the tool call itself.
    """
    try:
        run = subprocess.run(
            args,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as err:
        raise ConversionError(
            f"ffmpeg exceeded the {timeout_seconds}s ceiling and was stopped"
        ) from err
    if run.returncode != 0:
        tail = "\n".join((run.stderr or "").splitlines()[-8:])
        raise ConversionError(f"ffmpeg exited {run.returncode}:\n{tail}")


def ffmpeg_version(ffmpeg: Path) -> str | None:
    run = subprocess.run(
        [str(ffmpeg), "-version"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if run.returncode != 0:
        return None
    lines = (run.stdout or "").splitlines()
    return lines[0] if lines else None
