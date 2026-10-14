"""The index: every conversion seeable, intertwined files chainable."""

from __future__ import annotations

from pathlib import Path

from moviola_protocol_mcp.index_db import (
    conversion_chains,
    index_stats,
    list_conversions,
    record_conversion,
)


def _row(source: str, output: str, preset: str, source_bytes: int, output_bytes: int):
    return {
        "created_at": "2026-10-14T00:00:00+00:00",
        "source_path": source,
        "source_bytes": source_bytes,
        "output_path": output,
        "output_bytes": output_bytes,
        "preset": preset,
        "ratio": output_bytes / source_bytes,
        "bytes_saved": source_bytes - output_bytes,
        "status": "ok",
    }


def test_recorded_conversions_are_listed_newest_first_with_sizes(
    tmp_path: Path,
) -> None:
    db = str(tmp_path / "moviola.db")
    record_conversion(db, _row("a.mp4", "a.gif", "standard", 1000, 800))
    record_conversion(db, _row("b.mp4", "b.gif", "torch", 2000, 100))

    rows = list_conversions(db, limit=10)
    assert [row["output_path"] for row in rows] == ["b.gif", "a.gif"]
    assert rows[0]["preset"] == "torch"
    assert rows[0]["bytes_saved"] == 1900
    assert list_conversions(db, preset="standard")[0]["output_path"] == "a.gif"


def test_files_intertwined_by_the_protocol_form_a_chain(tmp_path: Path) -> None:
    db = str(tmp_path / "moviola.db")
    record_conversion(db, _row("lecture.mp4", "lecture.gif", "standard", 9000, 3000))
    record_conversion(db, _row("lecture.gif", "lecture-small.gif", "torch", 3000, 400))

    chains = conversion_chains(db)
    assert len(chains) == 1
    assert chains[0]["shared_path"] == "lecture.gif"
    assert chains[0]["child_preset"] == "torch"
    assert chains[0]["child_output_bytes"] == 400


def test_index_stats_total_bytes_per_preset(tmp_path: Path) -> None:
    db = str(tmp_path / "moviola.db")
    record_conversion(db, _row("a.mp4", "a.gif", "standard", 1000, 800))
    record_conversion(db, _row("b.mp4", "b.gif", "standard", 3000, 1200))

    stats = index_stats(db)
    assert stats["total_rows"] == 2
    assert stats["by_preset"][0]["preset"] == "standard"
    assert stats["by_preset"][0]["bytes_in"] == 4000
    assert stats["by_preset"][0]["bytes_out"] == 2000
