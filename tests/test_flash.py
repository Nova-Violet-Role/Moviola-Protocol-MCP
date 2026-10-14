"""The easter egg: an Intersect flash, and a divergence meter that is computed."""

from __future__ import annotations

from pathlib import Path

import pytest

from moviola_protocol_mcp.index_db import record_conversion


def _seed(db: str, source_bytes: int, output_bytes: int) -> None:
    record_conversion(
        db,
        {
            "created_at": "2026-10-14T00:00:00+00:00",
            "source_path": "worldline.mp4",
            "source_bytes": source_bytes,
            "output_path": "worldline.gif",
            "output_bytes": output_bytes,
            "preset": "canine",
            "ratio": output_bytes / source_bytes,
            "bytes_saved": source_bytes - output_bytes,
            "status": "ok",
        },
    )


def test_the_flash_reports_a_divergence_derived_from_the_index(tmp_path: Path) -> None:
    from moviola_protocol_mcp.flash import divergence, flash_report

    empty_db = str(tmp_path / "empty.db")
    assert divergence(empty_db) == pytest.approx(0.571024)

    db = str(tmp_path / "moviola.db")
    _seed(db, 1_000_000, 100_000)  # 90% saved: most of the way to Steins;Gate
    value = divergence(db)
    assert 0.571024 < value < 1.048596

    report = flash_report(db)
    assert "INTERSECT FLASH" in report
    assert "El Psy Kongroo" in report
    assert "Reading Steiner" in report
    assert "Tessersect" in report
