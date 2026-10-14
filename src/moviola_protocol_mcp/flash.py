# SPDX-License-Identifier: AGPL-3.0-or-later OR EUPL-1.2
# Copyright 2026 Saimonokuma.
"""The Easter Egg: an Intersect flash and a divergence meter.

Chuck's Intersect flashes a wall of images and the knowledge is
simply there. The Tessersect is that wall, built for machines.
Steins;Gate's divergence meter reads which worldline you are on;
here the number is derived from the index, never typed:

    divergence = 0.571024 + saved_fraction * (1.048596 - 0.571024)

0.571024 is where an empty index sits (nothing saved yet);
1.048596 - the Steins;Gate worldline - is the asymptote a perfect
ledger approaches as saved_fraction tends to 1. Reading Steiner
is what moviola.db does: it remembers every cut across sessions,
conversions and worldlines, when everything else has forgotten.

Full reading: docs/easter-egg.md. El Psy Kongroo.
"""

from __future__ import annotations

from .index_db import index_stats
from .presets import list_presets

ALPHA_DIVERGENCE = 0.571024
STEINS_GATE_DIVERGENCE = 1.048596


def divergence(db_path: str | None = None) -> float:
    """Compute the worldline divergence from the index's saved bytes."""
    stats = index_stats(db_path=db_path)
    bytes_in = sum(row["bytes_in"] or 0 for row in stats["by_preset"])
    bytes_out = sum(row["bytes_out"] or 0 for row in stats["by_preset"])
    if not bytes_in:
        return ALPHA_DIVERGENCE
    saved_fraction = min(1.0, max(0.0, 1.0 - bytes_out / bytes_in))
    span = STEINS_GATE_DIVERGENCE - ALPHA_DIVERGENCE
    return ALPHA_DIVERGENCE + saved_fraction * span


def flash_report(db_path: str | None = None) -> str:
    """Print-ready Intersect flash: every preset, then the meter."""
    stats = index_stats(db_path=db_path)
    lines = [
        "INTERSECT FLASH - I know Moviola.",
        "",
    ]
    for preset in list_presets():
        lines.append(f"* {preset['title']}")
        lines.append(f"  {preset['summary']}")
    lines += [
        "",
        f"Divergence meter: {divergence(db_path):.6f}",
        f"Reading Steiner: {stats['total_rows']} conversions remembered "
        f"in {stats['db_path']} - the index does not forget a cut "
        "when the worldline changes.",
    ]
    if stats["total_rows"] == 0:
        lines.append(
            "No flashes recorded in this worldline yet - convert "
            "something and the meter will move."
        )
    lines += [
        "",
        "The Organization is watching your file sizes. Stay grey.",
        "El Psy Kongroo.",
    ]
    return "\n".join(lines)
