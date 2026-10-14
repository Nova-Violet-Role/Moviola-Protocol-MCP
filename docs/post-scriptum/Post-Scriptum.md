<!--
    This file is part of Moviola Protocol MCP.
    SPDX-License-Identifier: AGPL-3.0-or-later OR EUPL-1.2
    Copyright 2026 Saimonokuma.
-->

<div align="center">

# 📜 Post-Scriptum — for Lecturers

**What was released, what it will do to training, and how to teach with it**

*Written after the release of Moviola Protocol MCP, the eye of Symbiose-OS,
by the partner who built it beside its Creator — for the teachers who will
put it in front of students.*

[![Nova-Violet Role](https://img.shields.io/badge/Nova--Violet-Role-9b59b6?style=for-the-badge)](https://github.com/Nova-Violet-Role)
[![License](https://img.shields.io/badge/License-AGPL--3.0_OR_EUPL--1.2-764ba2?style=for-the-badge)](../../LICENSE)

</div>

---

## We did it — and what "it" is

A piece of **Symbiose-OS** is public. Not the whole system — by its
Creator's judgment the whole remains too agnostic for humanity in 2026,
indifferent to any single doctrine, vendor or model family in a decade
that wants its intelligence product-shaped. What shipped instead is one
organ, complete and measured: **the eye**. Moviola Protocol MCP converts
any video or image into grey, one-bit, contour-first form at byte costs
two to four orders of magnitude under conventional corpora, indexes every
cut in a permanent ledger, and hands the result to training stacks —
PyTorch, JAX, MaxText, TorchTitan, Megatron-LM, AMD Primus, Unsloth — in
their native layouts.

Was it too much for 2026? The release itself is the answer: a whole
agnostic operating system would have been received as a manifesto. A
single organ that arrives with 41 tests, five verification gates, a
witness bench and its own falsification forms is received as an
instrument. That is the release doctrine of Symbiose — parts, proven in
the open, until assembly is a formality. Perhaps in forty years the
whole reads as obvious. The eye reads as obvious *now*, because anyone
can run it this afternoon and check every number on this page.

## What we measured (teach these as facts)

| Anchor | Measured value | Instrument |
|:--|--:|:--|
| Torch frame, animated screen content | ~101 B/frame | indexed cut, ffprobe frames |
| Tessersect instant (16 per collage) | 24.6 B/instant | 65,525 B ÷ 2,672 instants |
| Dense A4 tome page, Canine deck | 331 B/page | slideshow cut, 6-page bench |
| Dense A4 tome page, Torch deck | 1,690 B/page | slideshow cut |
| 1 h 50 m film, Torch @270p | ≈ 2.64 MB | rate × 6,600 s (labeled extrapolation) |
| Format reduction vs starved H.264 | 7.7× (Intersect) · 15.4× (Torch) | before/after bytes in `moviola.db` |
| Dataset integrity | extracted frames == probed frames, 57/57 rows | witness bench, fps-passthrough decode |

## What follows by reasoning (teach these as arguments)

**Token economics will move first.** Multimodal training is throttled by
visual tokens per context window. A Tessersect collage carries sixteen
ordered instants in one ingested frame — temporal density a frame
sampler needs sixteen ingestions to match. If models learn to read
collages natively, video understanding gains an order of magnitude of
*time per token*, and every curriculum built on frame budgets is
repriced.

**The long tail becomes trainable.** Wildlife archives, lecture
libraries, medical atlases, a century of documentary film: corpora that
exist but were never economical to feed. At hundreds of bytes per page
and single-digit megabytes per film, "train on the whole archive"
stops being a grant proposal and becomes a homework assignment.

**Edge and sovereign training get the largest relative gain.** A
school, a clinic, a field station with one workstation can fine-tune
on its own thousand hours without a datacenter or anyone's cloud.
Democratisation effects of that kind routinely outweigh benchmark
deltas in historical importance.

**The MMPROJ question sharpens.** The papers in `sources/` argue the
multimodal projector exists to *translate* dense RGB into a language
model's latent grammar, at enormous token cost. If the world arrives
already encoded as logic — contours, deltas, one-bit events — there
is progressively less to translate. Moviola does not prove the
projector obsolete; it makes the experiment — *how much projector
does a contour-native stream still need?* — cheap enough for a
seminar to run. That is how components die in science: not by
editorial, by invoice.

## What nobody knows yet (teach these as open problems)

- **Downstream accuracy per task.** We proved the format preserves
  human-legible structure. Model accuracy trained on 1-bit collages
  versus RGB frames — per task, per scale — is unmeasured everywhere,
  including here. It is now an affordable experiment; it is not a
  concluded one.
- **Colour-critical domains will resist.** Plumage, some dermatology,
  mineral colour: where hue *is* the signal, grey is a hypothesis
  that will fail, and students should be made to find that boundary
  themselves.
- **DVS transfer.** Event-camera research shows delta streams train
  reactive systems well. Whether *recorded* corpora cut into delta
  form transfer the same way is the robotics question of the decade,
  now with a public format to ask it in.

## Teaching with it — a four-session module

**Session 1 — The price of a frame.** Students convert one clip through
all five renderings, read `moviola.db`, and compute B/frame by hand
from ffprobe facts. Objective: a byte is a pedagogical unit.

**Session 2 — Resolution is a choice.** The scaling ladder in both
metrics: reproduce one stage table with `--height`, then the same
stage with `--dpi`, and explain why both numbers are honest and
neither is complete without its reference. Find the 720p anomaly;
explain it or refute our mechanism.

**Session 3 — Datasets with lineage.** Build a TorchPy dataset from
the index (`MoviolaFrameDataset.from_index`), export WebDataset and
Unsloth layouts, and write the dataset card *from the ledger* —
every claim on the card must cite a query.

**Session 4 — Falsify us.** Each student picks one number in the
README or the witness bench and tries to break it on their own
content. Successful falsifications are the highest grade this module
awards; the project credits them in its changelog regardless of the
grade.

### Lab exercises (expected outputs are measured anchors)

```sh
# Lab 1: your first cut and its ledger row
moviola convert any.mp4 out.gif --preset intersect
sqlite3 moviola.db "SELECT preset, source_bytes, output_bytes, ratio FROM conversions;"
# Lab 2: the ladder, both metrics
moviola convert any.mp4 a.gif --preset standard --height 240
moviola convert any.mp4 b.gif --preset standard --dpi 43
moviola probe a.gif; moviola probe b.gif        # same stage, two names
# Lab 3: sixteen instants, one token
moviola convert any.mp4 strips.gif --preset canine
uv run python scripts/demo_torch_dataset.py moviola.db
# Lab 4: verify us
uv run python scripts/verify_all.py             # five gates, all must pass
# Lab 5: diverge
moviola flash                                    # your worldline, computed
```

### Discussion questions

1. When does discarding colour *improve* a dataset, and when is it
   vandalism? Answer with one domain each way and a measurement plan.
2. Is a collage of 16 instants one training example or sixteen?
   What does your answer do to dataset-size reporting?
3. The index remembers every cut forever. When is dataset lineage a
   scientific duty, and when does it become surveillance of the
   dataset builders?
4. Symbiose-OS is withheld as "too agnostic" for 2026. Is releasing
   proven organs one at a time a responsible path to a system its
   own creator judges premature — or does it merely distribute the
   risk? Defend either position against the release history in this
   repository.

## Closing

This will change training — not by replacing RGB corpora, but by
changing their physics: time becomes cheap to feed, archives become
affordable to learn from whole, and a dataset can finally be priced
in bytes per instant of information with the receipts attached.
The first group that trains natively on Tessersect strips and
publishes the accuracy-per-byte curve will either validate the
thesis of the papers in `sources/` or show the field exactly where
the contour stops being enough. Both outcomes are progress. Both
are now within a student's reach.

That is what a released organ is for. The rest of Symbiose-OS will
arrive the same way this did: piece by piece, measured, in the
open — until one day the assembly is the only step left, and by
then there will be nothing in it the world has not already checked.

Burn the redundancy. Keep the contour. Log the ash.

**El Psy Kongroo.**

*— written in the cutting room, after the burn, with the ledger open.*

---

<div align="center">

*Post-Scriptum to Moviola Protocol MCP · For lecturers, students, and falsifiers*

© 2026 Nova-Violet Role · Non-Profit Organization · Copyright 2026 Saimonokuma

AGPL-3.0-or-later OR EUPL-1.2

</div>
