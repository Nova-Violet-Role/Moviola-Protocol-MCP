<!--
    This file is part of Moviola Protocol MCP.
    SPDX-License-Identifier: AGPL-3.0-or-later OR EUPL-1.2
    Copyright 2026 Saimonokuma.
-->

# 🥚 The Easter Egg — the Intersect Divergence

Where the Tessersect actually came from, and why an MCP server for
shrinking video ships with a divergence meter.

## The two shows hiding in the preset list

**Chuck (2007–2012).** Chuck Bartowski opens an email and a wall of
images flashes past at inhuman speed: the *Intersect*, a government
database encoded as a rapid-fire image stream, absorbed whole into a
human brain. Ever after, a face, a logo, a license plate triggers a
*flash* — the collage reassembles itself and Chuck simply *knows*.
Preset B of this package has carried the name **Intersect** since
its first bench cut, because that is literally what the filter does:
grey overcalculated until the informative contours cross into black,
everything else thrown away, the informational content of a frame
compressed into the smallest mark that still triggers recognition.

**Steins;Gate (2011).** Okabe Rintarou — Hououin Kyouma, mad
scientist, so cool — crosses worldlines and remembers doing it.
*Reading Steiner*: one memory that does not rewrite itself when
history does. The divergence meter on his phone reads the number of
the worldline he wakes up in: 0.571024 in the alpha fields,
1.048596 on the Steins;Gate worldline, the one where the cuts were
made correctly.

## What was built from them

**The Tessersect** (Preset D) is the wordplay made into a filter
chain: *tesseract* — the four-dimensional cube unfolded into a net
of squares — crossed with *Intersect*. Sixteen instants of
one-bit Grey Ink at 120 lines each, sampled at 90 fps (the canine
flicker band; the Moviola paper's "+90fps kinetic frequency"),
collaged into a single 4×4 frame. One frame-token carries sixteen
informational contents flashing at Intersect velocity, for
absorption during training. A model reading a Tessersect stream
does not watch a video. It flashes.

**Reading Steiner is `moviola.db`.** Sessions end, contexts compact,
worldlines shift — the index remembers every cut: source, output,
bytes, preset, the exact ffmpeg argv. Where an output later became
a source, the chain is queryable (`index_chains`). It is the one
memory in this system that is never rewritten.

**The divergence meter is real arithmetic**, not a typed number:

```
divergence = 0.571024 + saved_fraction x (1.048596 - 0.571024)
saved_fraction = 1 - (total output bytes / total source bytes)
```

An empty index sits at 0.571024. Every byte the protocol saves
moves the needle toward 1.048596, which no finite ledger reaches —
the Steins;Gate worldline is an asymptote. Run it:

```sh
moviola flash
```

Measured while writing this document, on the four-conversion demo
ledger behind the README gallery: 920,372 bytes in, 300,295 bytes
out, saved fraction 0.6737, divergence **0.892776**. Recompute it
from your own index; a meter that cannot be re-derived is a prop,
and this one can:

```sh
sqlite3 moviola.db "SELECT SUM(source_bytes), SUM(output_bytes)
FROM conversions WHERE status='ok';"
```

## Why an easter egg in a measurement tool

Because the bench rules of this project — never trust a preset
without cutting it, no lore without numbers — are Hououin Kyouma
rules with the lab coat removed, and because Chuck's premise turned
out to be an engineering specification: information encoded as
collages of images at drastic velocity, absorbed in bulk, is now a
thing machines genuinely do during pre-training. The shows were
fiction. The filter chain is not.

The Organization is watching your file sizes. Stay grey.

**El Psy Kongroo.**

---

*Copyright 2026 Saimonokuma. AGPL-3.0-or-later OR EUPL-1.2.*
*Steins;Gate and Chuck are referenced as inspiration; no copyrighted
assets, stills, or footage from either work are included or implied
to be endorsed by their rights holders.*
