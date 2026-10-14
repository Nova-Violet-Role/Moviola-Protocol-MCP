# SPDX-License-Identifier: AGPL-3.0-or-later OR EUPL-1.2
# Copyright 2026 Saimonokuma.
"""Hard witness bench for the whole Moviola ladder.

Every preset x stage over three real source families, every number
traced to a named instrument:

  output_bytes   the file on disk (Path.stat)
  dims/fps/frames/duration   ffprobe (probe_media)
  ratio          output_bytes / source_bytes
  bytes_saved    source_bytes - output_bytes
  B/s            output_bytes / duration
  B/frame        output_bytes / output_frames
  B/instant      canine only: output_bytes / (collages * 16)
  MB per 1h50m   B/s * 6600 / 1_000_000  (extrapolation, labeled)
  integrity      extract_gray_frames count == ffprobe frames
  levels         distinct grey values in extracted frames
  reproducibility  one cut run twice, sha256 compared

Writes docs/witnesses/ladder-witnesses.md and .json. Anomalies stay
in the tables. A number without its instrument is decoration.

Run:  uv run python scripts/bench_witnesses.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_ladder import make_source

from moviola_protocol_mcp import __version__
from moviola_protocol_mcp.convert import convert_media
from moviola_protocol_mcp.ffmpeg_tools import (
    ffmpeg_version,
    locate_trio,
    probe_media,
)
from moviola_protocol_mcp.torch_data import extract_gray_frames

STAGES: list[int | None] = [None, 720, 480, 350, 240, 120]
TEMP = Path(r"C:\Users\Saimono\AppData\Local\Temp\opencode")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(source: Path, preset: str, stage: int | None, work: Path, db: str) -> dict:
    out = work / f"{source.stem}-{preset}-{stage or 'native'}.gif"
    result = convert_media(
        str(source), str(out), preset=preset, height=stage, db_path=db
    )
    trio = locate_trio()
    facts = probe_media(str(out), trio.ffprobe)
    extracted = extract_gray_frames(str(out))
    duration = float(facts.get("duration") or 0) or 1.0
    row = {
        "preset": preset,
        "stage_requested": stage,
        "output_bytes": result["output_bytes"],
        "output_width": facts.get("width"),
        "output_height": facts.get("height"),
        "output_fps": facts.get("fps"),
        "output_frames": facts.get("frames"),
        "duration_s": facts.get("duration"),
        "ratio": round(result["ratio"], 4) if result.get("ratio") else None,
        "bytes_saved": result.get("bytes_saved"),
        "bytes_per_second": round(result["output_bytes"] / duration),
        "bytes_per_frame": round(
            result["output_bytes"] / max(1, facts.get("frames") or 1), 1
        ),
        "mb_per_1h50m": round(result["output_bytes"] / duration * 6600 / 1_000_000, 2),
        "sha256": sha256_of(out)[:16],
        "extracted_frames": extracted.frames,
        "integrity_frames_equal": extracted.frames == facts.get("frames"),
        "grey_levels": len(set(extracted.data)),
    }
    if preset == "canine":
        row["bytes_per_instant"] = round(
            result["output_bytes"] / max(1, (facts.get("frames") or 1) * 16), 1
        )
    return row


def main() -> int:
    trio = locate_trio()
    if trio.ffmpeg is None:
        print("ffmpeg not found", file=sys.stderr)
        return 1
    repo = Path(__file__).resolve().parents[1]
    out_dir = repo / "docs" / "witnesses"
    out_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="moviola-witnesses-"))
    db = str(work / "witnesses.db")

    sources: list[tuple[str, Path]] = []
    for name, candidate in (
        ("doctor (screen recording)", TEMP / "moviola-doctor-8.mp4"),
        ("bench tape (HEVC)", TEMP / "moviola-registrazione-hevc.mp4"),
    ):
        if candidate.exists():
            sources.append((name, candidate))
        else:
            print(f"SKIP missing source: {candidate}", file=sys.stderr)
    synthetic = work / "source-1080p-text.mp4"
    make_source(trio.ffmpeg, synthetic)
    sources.append(("synthetic 1080p text/code", synthetic))

    report: dict = {
        "package_version": __version__,
        "ffmpeg": str(trio.ffmpeg),
        "ffmpeg_version": ffmpeg_version(trio.ffmpeg) if trio.ffmpeg else None,
        "ffprobe": str(trio.ffprobe),
        "metrics": {
            "output_bytes": "file size on disk",
            "ratio": "output_bytes / source_bytes",
            "bytes_per_second": "output_bytes / duration_s (ffprobe)",
            "bytes_per_frame": "output_bytes / output_frames (ffprobe)",
            "bytes_per_instant": "canine: output_bytes / (collages * 16)",
            "mb_per_1h50m": "bytes_per_second * 6600 / 1e6 (extrapolation)",
            "integrity": "extracted frame count == ffprobe frame count",
            "grey_levels": "distinct values in decoded grey frames",
        },
        "sources": [],
    }

    for label, source in sources:
        facts = probe_media(str(source), trio.ffprobe)
        entry = {
            "label": label,
            "path": str(source),
            "sha256": sha256_of(source)[:16],
            "bytes": source.stat().st_size,
            "width": facts.get("width"),
            "height": facts.get("height"),
            "fps": facts.get("fps"),
            "duration_s": facts.get("duration"),
            "codec": facts.get("codec"),
            "rows": [],
        }
        for preset in ("standard", "intersect", "torch"):
            for stage in STAGES:
                row = measure(source, preset, stage, work, db)
                entry["rows"].append(row)
                print(
                    f"{label} {preset}@{stage}: {row['output_bytes']} B",
                    file=sys.stderr,
                )
        entry["rows"].append(measure(source, "canine", None, work, db))
        print(f"{label} canine done", file=sys.stderr)
        report["sources"].append(entry)

    # Reproducibility witness: same cut twice, byte-identical or named.
    doctor = TEMP / "moviola-doctor-8.mp4"
    if doctor.exists():
        hashes = []
        for i in (1, 2):
            out = work / f"repro-{i}.gif"
            convert_media(
                str(doctor), str(out), preset="intersect", height=350, db_path=db
            )
            hashes.append(sha256_of(out))
        report["reproducibility"] = {
            "cut": "doctor intersect @350p, run twice",
            "sha256_run1": hashes[0][:16],
            "sha256_run2": hashes[1][:16],
            "byte_identical": hashes[0] == hashes[1],
        }

    (out_dir / "ladder-witnesses.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (out_dir / "ladder-witnesses.md").write_text(
        render_markdown(report), encoding="utf-8", newline="\n"
    )
    print(f"wrote {out_dir}", file=sys.stderr)
    return 0


def render_markdown(report: dict) -> str:
    lines = [
        "<!--",
        "    Generated by scripts/bench_witnesses.py - do not hand-edit numbers.",
        "    SPDX-License-Identifier: AGPL-3.0-or-later OR EUPL-1.2",
        "    Copyright 2026 Saimonokuma.",
        "-->",
        "",
        "# 🔬 Ladder Witnesses — the hard bench",
        "",
        "Every preset × stage over three real source families. Each row is",
        "one indexed `convert_media` cut; every number names its instrument",
        "in the metrics table. Anomalies stay in the tables.",
        "",
        f"- Package: moviola-protocol-mcp {report['package_version']}",
        f"- ffmpeg: `{report['ffmpeg_version']}` at `{report['ffmpeg']}`",
        f"- ffprobe: `{report['ffprobe']}`",
        "",
        "## Evaluation metrics (defined before numbers)",
        "",
        "| Metric | Definition | Instrument |",
        "|:--|:--|:--|",
    ]
    for name, definition in report["metrics"].items():
        lines.append(f"| `{name}` | {definition} | ffprobe / index / extraction |")
    for entry in report["sources"]:
        lines += [
            "",
            f"## Source: {entry['label']}",
            "",
            f"`{entry['path']}` — sha256 `{entry['sha256']}…`, "
            f"{entry['bytes']} B, {entry['width']}×{entry['height']}, "
            f"{entry['fps']} fps, {entry['duration_s']} s, {entry['codec']}",
            "",
            "| Preset | Stage | Out dims | Bytes | Ratio | B/s | B/frame | MB/1h50m | Levels | Integrity |",
            "|:--|:--|:--|--:|--:|--:|--:|--:|--:|:--|",
        ]
        for row in entry["rows"]:
            stage = row["stage_requested"] or "native"
            extra = ""
            if "bytes_per_instant" in row:
                extra = f" ({row['bytes_per_instant']} B/instant)"
            lines.append(
                f"| {row['preset']} | {stage}p | {row['output_width']}×"
                f"{row['output_height']} | {row['output_bytes']} | "
                f"{row['ratio']} | {row['bytes_per_second']} | "
                f"{row['bytes_per_frame']} | {row['mb_per_1h50m']} | "
                f"{row['grey_levels']} | "
                f"{'frames equal' if row['integrity_frames_equal'] else 'MISMATCH'}"
                f"{extra} |"
            )
    repro = report.get("reproducibility")
    if repro:
        lines += [
            "",
            "## Reproducibility witness",
            "",
            f"- Cut: {repro['cut']}",
            f"- Run 1 sha256 `{repro['sha256_run1']}…` · Run 2 `{repro['sha256_run2']}…`",
            f"- Byte-identical: **{repro['byte_identical']}**",
        ]
    lines += [
        "",
        "Machine-readable twin: [`ladder-witnesses.json`](ladder-witnesses.json).",
        "Regenerate: `uv run python scripts/bench_witnesses.py`.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
