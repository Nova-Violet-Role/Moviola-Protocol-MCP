"""The always-seeable index: one SQLite row per conversion.

Default location is ./moviola.db in the working directory, overridable
with the MOVIOLA_DB environment variable or an explicit argument. The
chronist speaks below: every cut is logged with its full parameters,
so the dimension change between files intertwined by the protocol
(a source that was itself an earlier output) is always queryable.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL,
    source_path   TEXT NOT NULL,
    source_bytes  INTEGER,
    source_format TEXT,
    source_width  INTEGER,
    source_height INTEGER,
    source_fps    REAL,
    source_duration REAL,
    output_path   TEXT NOT NULL,
    output_bytes  INTEGER,
    output_format TEXT,
    output_width  INTEGER,
    output_height INTEGER,
    output_fps    REAL,
    preset        TEXT NOT NULL,
    height        INTEGER,
    ratio         REAL,
    bytes_saved   INTEGER,
    ffmpeg_path   TEXT,
    command       TEXT,
    status        TEXT NOT NULL DEFAULT 'ok',
    error         TEXT
);
"""

COLUMNS = [
    "created_at",
    "source_path",
    "source_bytes",
    "source_format",
    "source_width",
    "source_height",
    "source_fps",
    "source_duration",
    "output_path",
    "output_bytes",
    "output_format",
    "output_width",
    "output_height",
    "output_fps",
    "preset",
    "height",
    "ratio",
    "bytes_saved",
    "ffmpeg_path",
    "command",
    "status",
    "error",
]


def resolve_db_path(db_path: str | None = None) -> Path:
    if db_path:
        return Path(db_path)
    env = os.environ.get("MOVIOLA_DB")
    if env:
        return Path(env)
    return Path.cwd() / "moviola.db"


def connect(db_path: str | None = None) -> sqlite3.Connection:
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def record_conversion(db_path: str | None, row: dict) -> int:
    """Append one conversion row and return its id."""
    with connect(db_path) as conn:
        placeholders = ", ".join("?" for _ in COLUMNS)
        names = ", ".join(COLUMNS)
        cursor = conn.execute(
            f"INSERT INTO conversions ({names}) VALUES ({placeholders})",
            [row.get(column) for column in COLUMNS],
        )
        conn.commit()
        return int(cursor.lastrowid or 0)


def list_conversions(
    db_path: str | None = None,
    limit: int = 50,
    preset: str | None = None,
) -> list[dict]:
    with connect(db_path) as conn:
        if preset:
            rows = conn.execute(
                "SELECT * FROM conversions WHERE preset = ? ORDER BY id DESC LIMIT ?",
                (preset, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM conversions ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(row) for row in rows]


def conversion_chains(db_path: str | None = None) -> list[dict]:
    """Intertwined files: conversions whose source was an earlier output."""
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT parent.id AS parent_id, parent.preset AS parent_preset,
                   parent.output_path AS shared_path,
                   parent.output_bytes AS parent_output_bytes,
                   child.id AS child_id, child.preset AS child_preset,
                   child.output_path AS child_output_path,
                   child.output_bytes AS child_output_bytes
            FROM conversions AS parent
            JOIN conversions AS child
              ON child.source_path = parent.output_path
            WHERE parent.status = 'ok' AND child.status = 'ok'
            ORDER BY parent.id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def index_stats(db_path: str | None = None) -> dict:
    """Per-preset totals: counts, bytes in, bytes out, mean ratio."""
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT preset, COUNT(*) AS conversions,
                   SUM(source_bytes) AS bytes_in,
                   SUM(output_bytes) AS bytes_out,
                   AVG(ratio) AS mean_ratio
            FROM conversions
            WHERE status = 'ok'
            GROUP BY preset
            ORDER BY preset
            """
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM conversions").fetchone()[0]
    return {
        "db_path": str(resolve_db_path(db_path)),
        "total_rows": int(total),
        "by_preset": [dict(row) for row in rows],
    }
