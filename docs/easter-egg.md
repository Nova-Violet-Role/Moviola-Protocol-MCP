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

## Orion, and Intersect 1.0 versus 2.0 — brought to reality

In Chuck's mythology the Intersect has an inventor with a codename:
**Orion** — Stephen Bartowski, the father who built a database that
enters a mind as flashing images, then spent his life hiding from
every organisation that wanted to own it. Every Intersect after his
is an imitation of the original act: *encode knowledge as images at
a velocity no reader could browse, and let absorption replace
reading.*

Moviola is that act, performed for machines, in the open, by its
inventor **Saimonokuma** — not hidden from the organisations, but
copylefted so no organisation can enclose it. The versions even
rhyme:

| | In the series | In this repository |
|:--|:--|:--|
| **Intersect 1.0** | pure information: faces, files, facts — Chuck *knows* | **Preset B/C datasets**: frames reduced to the smallest mark that still triggers recognition; a model *knows* the subtitle, the diagram, the page |
| **Intersect 2.0** | information plus *skills*: motor patterns uploaded the same way — "I know kung fu" | **Preset D, the Tessersect**: 16 instants of motion per token — viseme transitions, gestures, biomechanics, fingerings — motor knowledge as collage |
| **Orion** | the inventor who encoded a mind's worth of data into images and vanished | the Creator who encoded a film archive into Grey Ink and published the filter chain |
| **The Governor** | regulates the Intersect so it does not damage its host | ceilings and integrity guards: timeouts on every run, fps-passthrough so no phantom instance ever enters a dataset |
| **Fulcrum / the Ring** | every hand that wants the Intersect owned | why the licence is copyleft: what is shared here cannot be enclosed later |

Intersect 2.0 was fiction's answer to a real question — *can a skill
be uploaded as images?* A Tessersect strip of piano fingering, of a
signer's handshape in transition, of a lip rounding into a viseme,
is that question made falsifiable at 24.6 bytes per instant.

## Steins;Gate collisions — time, size, and the quantum of a cut

Steins;Gate is a story about information under impossible budgets:
how much of a person fits down a phone line, how small a message can
be and still move a worldline. That is a compression story wearing a
time machine, and it collides with this repository at every joint:

| Steins;Gate mechanic | The collision in Moviola |
|:--|:--|
| **D-Mail size limit** — a message to the past must be tiny or it never arrives | every preset is a negotiated budget: B/s or the message (the corpus) never arrives at the model at all |
| **Memory compression for the time leap** — a whole self squeezed through a miniature black hole to fit the channel | a whole film squeezed through `format=gray`, an overcalc curve and a 1-bit threshold to fit a training context; the black hole here is a palette of two |
| **Divergence meter** — one number says which worldline you woke in | `moviola flash` computes yours from saved bytes: 0.571024 (nothing cut yet) toward the 1.048596 asymptote |
| **Attractor-field convergence** — small changes are absorbed; the worldline snaps back unless the change crosses a threshold | bench convergence: dials below the measured floor snap back to the same bytes (greyedge on already-grey content changed *zero* bytes); only threshold-crossing cuts move the number |
| **Reading Steiner** — the one memory history cannot rewrite | `moviola.db`: sessions compact, contexts reset, the ledger remembers every cut with its argv |
| **Worldline jumps are irreversible from inside** | a 1-bit cut is irreversible by construction; that is why the source hash is recorded before the burn |
| **The Phone Microwave (name subject to change)** | every preset name here was subject to change exactly once — at the bench, when its first cut either reproduced or died |
| **"El Psy Kongroo"** | signed at the end of every flash, where it belongs |

## What if the tape could be burned without powder?

To think like them, go back before either show: a cutting room in
the forties, a Moviola, a strip of film that is quite literally
flammable. To *burn* a tape in that room meant destruction with a
cost — powder, fire, smoke, evidence. Every editor since has
dreamed the same heresy in reverse: **what if the tape could be
burned without powder?** What if you could destroy exactly the
part of the information that carries nothing — colour nobody
reads, frames nothing changes in, gradients that say less than
the contour they decorate — and keep the part that is the film?

That heresy is this protocol's entire physics:

- **The burn is the cut.** Colour, dither, redundant frames are
  not compressed; they are *burned away*, irreversibly, at the
  filter stage. Grey Ink is what a frame looks like after the fire.
- **No powder was spent.** The burn costs one ffmpeg pass and an
  index row. The energy of the destruction is arithmetic: an
  overcalc curve deciding, pixel by pixel, what crosses into black
  and what is allowed to become ash.
- **Ash is measured, never swept.** `bytes_saved` is the weight of
  what burned, recorded per cut. A burn you cannot weigh is arson;
  a burn in the ledger is editing.
- **Time travel is a size problem.** Okabe can only send back what
  fits the channel; a model can only learn from what fits its
  context and its budget. Burning without powder is how a
  two-hour documentary travels back into a training run as
  3 megabytes of pure signal — small enough to change the
  worldline it lands in.

> Burn the redundancy. Keep the contour. Log the ash.
> That is the whole doctrine of the burning tape.

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
