# SPDX-License-Identifier: AGPL-3.0-or-later OR EUPL-1.2
# Copyright 2026 Saimonokuma.
"""Quintuple check: five independent gates, everything re-proved.

Gate 1  test suite            uv run pytest, exit read directly
Gate 2  encoding              every repo text file UTF-8 / LF / clean
Gate 3  instruments + alarms  trio and filters present; deliberate
                              failures refuse by name and are indexed
Gate 4  clean-room wheel      fresh build, uvx from the wheel file,
                              doctor + a real canine conversion
Gate 5  statement audit       README byte claims vs files on disk,
                              witness integrity flags, sources layout

Exit 0 only when all five gates pass. Each gate prints its own
evidence; nothing is taken from a previous run. Run any time:

    uv run python scripts/verify_all.py [--skip-gate4]
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

FAILURES: list[str] = []


def gate(number: int, name: str, ok: bool, detail: str) -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[gate {number}] {mark} {name} - {detail}")
    if not ok:
        FAILURES.append(f"gate {number} {name}: {detail}")


def run(args: list[str], cwd: Path, timeout: int = 1200) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def gate1_suite() -> None:
    result = run([sys.executable, "-m", "pytest", "-q"], REPO)
    last = (result.stdout.strip().splitlines() or [""])[-1]
    gate(1, "test suite", result.returncode == 0, f"exit {result.returncode}: {last}")


def gate2_encoding() -> None:
    bad: list[str] = []
    checked = 0
    roots = ["src", "tests", "scripts", "docs", "sources"]
    files: list[Path] = []
    for root in roots:
        files.extend(
            p
            for p in (REPO / root).rglob("*")
            if p.is_file()
            and p.suffix.lower()
            in {".py", ".md", ".toml", ".yml", ".json", ".ts", ".mjs", ".svg"}
        )
    files += [REPO / "README.md", REPO / "pyproject.toml", REPO / "LICENSE"]
    for path in files:
        data = path.read_bytes()
        checked += 1
        problems = []
        if b"\r" in data:
            problems.append("CR")
        if data.startswith(b"\xef\xbb\xbf"):
            problems.append("BOM")
        if any(b < 9 or (10 < b < 32 and b != 13) for b in data):
            problems.append("CTL")
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            problems.append("UTF8")
        if problems:
            bad.append(f"{path.relative_to(REPO)}:{','.join(problems)}")
    gate(
        2,
        "encoding",
        not bad,
        f"{checked} files clean" if not bad else "; ".join(bad[:5]),
    )


def gate3_instruments_and_alarms() -> None:
    from moviola_protocol_mcp.convert import convert_media
    from moviola_protocol_mcp.ffmpeg_tools import ConversionError, locate_trio
    from moviola_protocol_mcp.index_db import list_conversions
    from moviola_protocol_mcp.presets import get_preset

    trio = locate_trio()
    details: list[str] = []
    ok = trio.ffmpeg is not None and trio.ffprobe is not None
    details.append(f"trio={'found' if ok else 'MISSING'} at {trio.ffmpeg}")
    if trio.ffmpeg:
        filters = run([str(trio.ffmpeg), "-v", "error", "-filters"], REPO, 120)
        wanted = [
            "greyedge",
            "morpho",
            "palettegen",
            "paletteuse",
            "tile",
            "curves",
            " lut ",
        ]
        missing = [w.strip() for w in wanted if w not in filters.stdout]
        ok = ok and not missing
        details.append(f"filters missing={missing or 'none'}")
    # Alarm trips: each refusal must fire by name.
    try:
        get_preset("banana")
        ok = False
        details.append("unknown preset NOT refused")
    except ValueError:
        details.append("unknown preset refused")
    with tempfile.TemporaryDirectory(prefix="moviola-verify-") as tmp:
        db = str(Path(tmp) / "alarms.db")
        corrupt = Path(tmp) / "corrupt.mp4"
        corrupt.write_bytes(b"this is not media at all" * 10)
        try:
            convert_media(str(corrupt), str(Path(tmp) / "x.gif"), db_path=db)
            ok = False
            details.append("corrupt source NOT refused")
        except ConversionError:
            rows = list_conversions(db)
            recorded = bool(rows) and rows[0]["status"] == "error"
            ok = ok and recorded
            details.append(f"corrupt refused and indexed={recorded}")
        try:
            convert_media(
                str(corrupt), str(Path(tmp) / "y.gif"), dpi=72, height=240, db_path=db
            )
            ok = False
            details.append("dpi+height NOT refused")
        except ConversionError:
            details.append("dpi+height refused")
    gate(3, "instruments + alarms", ok, "; ".join(details))


def gate4_cleanroom_wheel() -> None:
    uv = shutil.which("uv")
    if not uv:
        gate(4, "clean-room wheel", False, "uv not on PATH")
        return
    with tempfile.TemporaryDirectory(prefix="moviola-cleanroom-") as tmp:
        work = Path(tmp)
        build = run([uv, "build", "--out-dir", str(work / "dist")], REPO, 900)
        wheels = sorted((work / "dist").glob("*.whl")) if build.returncode == 0 else []
        if not wheels:
            gate(4, "clean-room wheel", False, f"build exit {build.returncode}")
            return
        wheel = str(wheels[0])
        doctor = run(
            [uv, "tool", "run", "--from", wheel, "moviola", "doctor"], work, 900
        )
        ok = doctor.returncode == 0
        detail = f"doctor exit {doctor.returncode}"
        if ok:
            trio_ffmpeg = None
            from moviola_protocol_mcp.ffmpeg_tools import locate_trio

            trio_ffmpeg = locate_trio().ffmpeg
            clip = work / "clip.mp4"
            gen = run(
                [
                    str(trio_ffmpeg),
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
                work,
                300,
            )
            conv = run(
                [
                    uv,
                    "tool",
                    "run",
                    "--from",
                    wheel,
                    "moviola",
                    "convert",
                    str(clip),
                    str(work / "out.gif"),
                    "--preset",
                    "canine",
                ],
                work,
                900,
            )
            out_ok = (work / "out.gif").exists() and (
                work / "out.gif"
            ).stat().st_size > 0
            db_ok = (work / "moviola.db").exists()
            ok = gen.returncode == 0 and conv.returncode == 0 and out_ok and db_ok
            detail += (
                f"; canine convert exit {conv.returncode}, gif={out_ok}, db={db_ok}"
            )
        gate(4, "clean-room wheel", ok, detail)


def gate5_statement_audit() -> None:
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    details: list[str] = []
    ok = True
    for gif in sorted((REPO / "docs" / "presets").glob("*.gif")):
        size_text = f"{gif.stat().st_size:,}"
        present = size_text in readme
        ok = ok and present
        details.append(f"{gif.name} {size_text}B in README={present}")
    witness_json = REPO / "docs" / "witnesses" / "ladder-witnesses.json"
    if witness_json.exists():
        report = json.loads(witness_json.read_text(encoding="utf-8"))
        rows = [r for s in report["sources"] for r in s["rows"]]
        integrity = all(r["integrity_frames_equal"] for r in rows)
        repro = (report.get("reproducibility") or {}).get("byte_identical")
        ok = ok and integrity and repro is True
        details.append(f"witness rows={len(rows)} integrity={integrity} repro={repro}")
    else:
        ok = False
        details.append("witness json missing")
    papers = sorted(p.name for p in (REPO / "sources").glob("*.md"))
    sources_ok = len(papers) == 7 and (REPO / "sources" / "README.md").exists()
    ok = ok and sources_ok
    details.append(f"sources papers={len(papers)}")
    funding_ok = (REPO / ".github" / "FUNDING.yml").exists()
    ok = ok and funding_ok
    details.append(f"FUNDING.yml={funding_ok}")
    gate(5, "statement audit", ok, "; ".join(details))


def main() -> int:
    skip4 = "--skip-gate4" in sys.argv
    print("MOVIOLA QUINTUPLE CHECK - every statement re-proved")
    gate1_suite()
    gate2_encoding()
    gate3_instruments_and_alarms()
    if skip4:
        print("[gate 4] SKIP clean-room wheel (--skip-gate4)")
    else:
        gate4_cleanroom_wheel()
    gate5_statement_audit()
    if FAILURES:
        print("\nFAILURES:")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1
    print("\nALL GATES PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
