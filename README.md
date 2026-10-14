<!--
    This file is part of Moviola Protocol MCP.
    SPDX-License-Identifier: AGPL-3.0-or-later OR EUPL-1.2
    Copyright 2026 Saimonokuma.
-->

<div align="center">

# ⚜️ Moviola Protocol MCP

**Grey is the ink. Motion is the message. Every cut is on the record.**

*An MCP server and CLI that convert any video or image format through the grey
presets of the 1940s telecinema cutting room — NTSC-J seated black, one-bit
Grey Ink, and a 90 fps collage that flashes sixteen instants per frame*

[![Ko-fi](https://img.shields.io/badge/Support-Ko--fi-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/saimonokuma)
[![Nova-Violet Role](https://img.shields.io/badge/Nova--Violet-Role-9b59b6?style=for-the-badge)](https://github.com/Nova-Violet-Role)
[![License](https://img.shields.io/badge/License-AGPL--3.0_OR_EUPL--1.2-764ba2?style=for-the-badge)](LICENSE)

[![MCP stdio](https://img.shields.io/badge/MCP-stdio%20%C2%B7%209%20tools-2C3E50?style=flat-square)](#-mcp-tools--every-tool-every-argument)
[![UVX](https://img.shields.io/badge/UVX-wheel%20verified%20clean--room-27ae60?style=flat-square)](#-install)
[![Tests](https://img.shields.io/badge/tests-21%20passing-27ae60?style=flat-square)](#-verify-it-yourself)
[![ffmpeg trio](https://img.shields.io/badge/ffmpeg-ffprobe%20%C2%B7%20ffplay-374151?style=flat-square)](#requirements)
[![REUSE](https://img.shields.io/badge/REUSE-compliant-blue?style=flat-square)](https://reuse.software/)

</div>

---

## 👋 Welcome

**You are welcome here, whatever you came for.** If you want an MCP tool that
turns a two-hour recording into something an AI model can actually ingest,
[start with Install](#-install) — one `uvx` line, no checkout. If you train
models and you are counting bytes per frame across a billion-image corpus,
[start with the training section](#-for-training-enthusiasts): the arithmetic
is printed, including where our own early claims were wrong. And if you came
to check whether the numbers on this page are real, [start with
Verify](#-verify-it-yourself) and try to falsify one — that is not tolerated
here, it is the *point*. There is an issue form for exactly that.

New here? The fastest path is to let your agent do it:

```sh
uvx --from https://github.com/Nova-Violet-Role/Moviola-Protocol-MCP/releases/download/v0.2.0/moviola_protocol_mcp-0.2.0-py3-none-any.whl moviola doctor
```

Exit 0 and a JSON block naming your `ffmpeg`, `ffprobe` and `ffplay` means
you are done installing. Everything after that is conversion.

---

## 📜 About

**The Moviola Protocol is a rendering discipline, measured at the bench.**
Conventional video spends its bytes on 24-bit colour at frame rates chosen
for human persistence of vision. A model does not need either. What it needs
is *structure*: borders, subtitles, contours, text, the shape of change. The
protocol keeps exactly that and executes the rest:

```
source -> fps -> NTSC-J range seat -> 8-bit grey -> edge relief
       -> [overcalc -> 1-bit threshold] -> [4x4 collage] -> 2-pass palette -> output
```

* **Silent by construction.** GIF carries no audio; neither does anything
  else we emit (`-an` everywhere). The audio is not compressed — it is executed.
* **Black is seated first.** `scale=in_range=limited:out_range=full` (the
  NTSC-J seat) puts true black at 0 before a single colour is counted, so an
  8-colour palette is a floor, not a hope.
* **Dither is off, always.** Dither is noise wearing a costume; it
  multiplies frame differences and the byte count with them.
* **No lore without numbers.** Every dial in this README was cut and read
  from the mux report on real files. A null result killed its dial the same
  day (the event-gate that died that way is documented in
  [the Tessersect section](#-canine-logic--the-tessersect)).
* **The chronist speaks below.** Every conversion is written to
  `moviola.db` with its full argv before the tool returns, so the dimension
  change between any two files intertwined by the protocol can be evaluated
  at any time, by anyone, with `sqlite3`.

That is the artifact. It converts, it is measured, and the numbers on this
page each have an exit code behind them.

---

## 🎞️ The presets — thirty seconds each, on camera

One source, four renderings. The source is a 29.6 s, 1100×640, 10 fps screen
recording (230,093 B mp4). Every GIF below is the direct output of the
printed command — re-run one and compare bytes; a demo that does not
reproduce is a failed demo.

| Preset | The 30 seconds | Bytes | Dims · fps · frames |
|:--|:--|--:|:--|
| **A · Standard Moviola** | ![Standard Moviola: 8-bit grey, 8 colours](https://raw.githubusercontent.com/Nova-Violet-Role/Moviola-Protocol-MCP/main/docs/presets/doctor-standard.gif) | 189,882 | 1100×640 · 10 · 296 |
| **B · Moviola Intersect** | ![Intersect: 1-bit Grey Ink](https://raw.githubusercontent.com/Nova-Violet-Role/Moviola-Protocol-MCP/main/docs/presets/doctor-intersect.gif) | 29,968 | 1100×640 · 10 · 296 |
| **C · Intersect Torch** | ![Torch: 1-bit, 5 fps, 360p](https://raw.githubusercontent.com/Nova-Violet-Role/Moviola-Protocol-MCP/main/docs/presets/doctor-torch.gif) | 14,920 | 618×360 · 5 · 148 |
| **D · Canine Tessersect** | ![Canine Tessersect: 16 instants per collage frame](https://raw.githubusercontent.com/Nova-Violet-Role/Moviola-Protocol-MCP/main/docs/presets/doctor-canine.gif) | 65,525 | 824×480 · 5.88 · 167 collages |

```sh
moviola convert doctor.mp4 doctor-standard.gif  --preset standard
moviola convert doctor.mp4 doctor-intersect.gif --preset intersect
moviola convert doctor.mp4 doctor-torch.gif     --preset torch
moviola convert doctor.mp4 doctor-canine.gif    --preset canine
```

### Every characteristic, side by side

| Characteristic | A · Standard | B · Intersect | C · Torch | D · Canine Tessersect | Passthrough |
|:--|:--|:--|:--|:--|:--|
| Sampling | 10 fps (10–15) | 10 fps | 5 fps | 90 fps | source rate |
| Range seat | NTSC-J `limited→full` | NTSC-J | NTSC-J | NTSC-J | — |
| Grey stage | `format=gray` (8-bit) | grey + overcalc | grey + overcalc | grey + overcalc | — |
| Border stage | `greyedge` relief | `greyedge` | `greyedge` | `greyedge` | — |
| Bit depth out | 3 bits/pixel palette (8 colours) | **1 bit** (2 levels) | **1 bit** | **1 bit** per cell | source |
| Measured levels | 7–8 greys | {0, 192} grey ink on black | {0, ~192} | {0, ~192} per cell | — |
| Resize | none | none | 360p (480p choosable, never upscales) | 120p **cells**, 4×4 collage | none |
| Information per output frame | 1 instant | 1 instant | 1 instant | **16 instants** | 1 instant |
| Doctor clip bytes | 189,882 | 29,968 | 14,920 | 65,525 | container-dependent |
| Doctor byte rate | 6,415 B/s | 1,012 B/s | 504 B/s | 2,213 B/s (35 instants/s carried) | — |
| Bench tape bytes † | 154,362 | 49,159 | 32,653 | — | — |
| Built for | evidence GIFs, docs, chat | subtitles, borders, contours, 3D edges | pre-training slideshows, documentaries | training absorption, Intersect-style flash corpora | plain format change, gif→mp4 for models |

† Bench tape: 706×264, 5 s, 569,469 B HEVC mp4 — the `MOVIOLA-PROTOCOL.md`
reference-ladder tape. Standard reproduces its published 166 KB canonical
floor within generation loss (their source was the `.tape` render; ours is
one transcode further away).

### The exact filter chains

Nothing here is a secret sauce; `moviola presets` prints these verbatim.

```
A  fps=10,scale=in_range=limited:out_range=full,format=gray,greyedge
   + palettegen=max_colors=8 / paletteuse=dither=none            (GIF)

B  fps=10,scale=...:..,format=gray,greyedge,format=gray,
   curves=all='0/0 0.30/0.02 0.5/0.5 0.70/0.98 1/1',
   lut=y='if(gt(val,128),255,0)',format=gray
   + palettegen=max_colors=2:reserve_transparent=0              (GIF)

C  B with fps=5 and scale=-2:'min(360,ih)'   (480 choosable; never upscales)

D  fps=90,scale=-2:'min(120,ih)':..,format=gray,greyedge,format=gray,
   curves=all='...',lut=y='...',format=gray,tile=4x4
   + palettegen=max_colors=2:reserve_transparent=0              (GIF)
```

The **overcalc** curve is the heart of B, C and D: luma is stretched hard
around mid-grey *before* the 1-bit threshold, so a faint subtitle edge or a
hairline contour — the pixels a flat threshold would discard — crosses into
black. Grey is overcalculated precisely so that black lands where the
information is.

---

## 📐 The numbers, honestly

This project began with a claim: a 1 h 50 m video under 5 MB with Preset A,
under 3 MB with Preset B. **On animated screen content, measured rates say
otherwise**, and the correction is printed here rather than quietly edited:

| Preset | Measured rate (doctor clip) | 1 h 50 m at that rate | Verdict on the early claim |
|:--|--:|--:|:--|
| A · Standard | 6,415 B/s | ≈ 42 MB | ❌ not at 1100×640 animated content |
| B · Intersect | 1,012 B/s | ≈ 6.7 MB | ❌ close, not under 3 MB |
| C · Torch 360p | 504 B/s | ≈ 3.3 MB | ≈ the B claim, one preset down |
| D · Tessersect | 2,213 B/s carrying 35 instants/s | ≈ 14.6 MB | density, not minimal bytes |

Where the claims *do* hold: **near-static content** — slides, lectures,
terminal recordings, talking heads. A static Torch frame measured **~100 B**
(14,920 B over 148 frames, most of them changed; unchanged runs compress far
harder). Content that changes every frame at 1100×640 is the worst case this
protocol will ever meet, and it is the case we chose to publish. Your index
will tell you your own rates within one conversion; believe those.

> ⚖️ **Method** — *Reality is the judge.* Every number above is meant to be
> re-run by you. If one of them is wrong on your machine, telling us is the
> most welcome contribution we accept, and there is an issue form for it.

---

## 🚀 Install

### Requirements

| Need | Why | How we find it |
|:--|:--|:--|
| **uv** | runs the wheel with `uvx`, no venv to manage | your package manager |
| **ffmpeg + ffprobe** | every conversion and probe (`ffplay` reported, not required) | `MOVIOLA_FFMPEG_DIR` → `FFMPEG_PATH` → `C:\Hybrid\64bit` → `PATH` |
| Python ≥ 3.10 | only if you install the library yourself; `uvx` brings its own | — |

The `C:\Hybrid\64bit` probe is this project's house install (ffmpeg
N-123549, a full GPL build with `greyedge`, `morpho`, `palettegen` — all
verified present). Any full ffmpeg build on `PATH` works identically;
`moviola doctor` prints the searched locations and the winner, so a wrong
binary is a visible fact, not a mystery.

### Three ways in

```sh
# 1. From the GitHub release wheel (today's verified path)
uvx --from https://github.com/Nova-Violet-Role/Moviola-Protocol-MCP/releases/download/v0.2.0/moviola_protocol_mcp-0.2.0-py3-none-any.whl moviola-protocol-mcp

# 2. Straight from the repository
uvx --from git+https://github.com/Nova-Violet-Role/Moviola-Protocol-MCP moviola-protocol-mcp

# 3. From PyPI — the name `moviola-protocol-mcp` is reserved-free and the
#    metadata is ready; the first upload waits on a project token.
uvx moviola-protocol-mcp        # after the PyPI upload lands
```

For development: `git clone`, then `uv sync`, `uv run pytest` (21 tests),
`uv run moviola doctor`.

---

## 🕹️ MCP tools — every tool, every argument

Transport: **stdio**. Architecture: traditional flat tools — nine fixed
operations, each with a declared JSON schema, no discovery layer to drift.
Register it anywhere MCP speaks:

```json
{
  "mcpServers": {
    "moviola": {
      "command": "uvx",
      "args": ["moviola-protocol-mcp"],
      "env": { "MOVIOLA_FFMPEG_DIR": "C:\\Hybrid\\64bit", "MOVIOLA_DB": "D:\\media\\moviola.db" }
    }
  }
}
```

### `convert_media`

Any video/image → the format named by the output extension. The preset
shapes the pixels; the extension chooses the container.

| Argument | Type | Default | Meaning |
|:--|:--|:--|:--|
| `source` | string | — | input path (any ffmpeg-readable format) |
| `output` | string | — | output path; extension picks gif/mp4/webm/webp/png/jpg/… |
| `preset` | string | `"standard"` | `standard`·`intersect`·`torch`·`canine`·`passthrough` (aliases `a`–`d`, `tessersect`) |
| `fps` | int\|null | preset's | sampling rate (Standard accepts 10–15; Tessersect cell velocity) |
| `height` | int\|null | preset's | Torch 360/480; Tessersect cell height (120); never upscales |
| `crf` | int | 23 | x264 quality for mp4-family outputs (plugin parity) |
| `db_path` | string\|null | `./moviola.db` | index location (`MOVIOLA_DB` if set) |
| `ffmpeg_dir` | string\|null | auto | directory holding the trio |
| `timeout_seconds` | int | 7200 | hard ceiling; expiry is a named error, recorded in the index |

Returns: `{id, source, source_bytes, output, output_bytes, preset, fps,
height, ratio, bytes_saved, db_path, ffmpeg, command}` — the exact argv is
in the result *and* in the index row. Reverse direction included:
`gif → mp4` with `preset="passthrough"` reproduces the OpenCode plugin
transcode (libx264, crf 23, yuv420p, faststart, silent), plus an
even-dimension pad the plugin lacks — visible only on odd-sized inputs,
where the plugin version fails and this one does not.

### `slideshow_from_images`

Ordered PNG/JPG set → one gif/mp4/webp slideshow.

| Argument | Type | Default | Meaning |
|:--|:--|:--|:--|
| `images` | list[string] | — | image paths, in presentation order |
| `output` | string | — | output path |
| `preset` | string | `"torch"` | as above; with `canine`, each image is **one collage cell** |
| `seconds_per_image` | float | 1.0 | hold per image (Torch pre-training form: 0.2 ⇒ 5 img/s) |
| `fps`, `height`, `db_path`, `ffmpeg_dir`, `timeout_seconds` | — | — | as in `convert_media` |

Returns the conversion result plus `{images, seconds_per_image}` (the
effective cell duration under Tessersect, `1/(fps or 90)`).

### `probe_media`

`{path, ffmpeg_dir?}` → `{path, bytes, format, width, height, fps,
duration, codec, frames}` from ffprobe. Missing ffprobe degrades to
size-only facts, named as such — silence is never dressed as health.

### `list_presets`

No arguments → the five presets with summaries, defaults and the exact
filter-chain strings, straight from the code that runs them.

### `doctor`

`{ffmpeg_dir?}` → `{ffmpeg, ffprobe, ffplay, searched, ffmpeg_version}`.
First thing to run on a new machine; first thing to paste into a bug report.

### `index_history` · `index_stats` · `index_chains`

Read the ledger. `index_history {limit=50, preset?, db_path?}` newest
first, sizes included. `index_stats {db_path?}` per-preset conversions,
bytes in/out, mean ratio. `index_chains {db_path?}` the intertwined files:
every conversion whose source was itself an earlier output, parent and
child side by side — the dimension-change audit trail this project exists
to keep.

### `install_opencode_plugin`

`{target_dir?, plugin_format="mjs", include_read_tool=true, force=false}` →
copies the bundled gif-as-mp4 plugin (and, unless declined, the portable
read tool) into an OpenCode config directory. See
[The OpenCode plugin](#-the-opencode-plugin--gif-in-mp4-out).

---

## 💻 CLI — the same core, no server

```sh
moviola convert lecture.mp4 lecture.gif --preset standard --fps 12
moviola convert lecture.mp4 lecture-torch.gif --preset torch --height 480
moviola convert lecture.mp4 lecture-tessersect.gif --preset canine
moviola convert frames.gif frames.mp4 --preset passthrough
moviola convert still.png still-grey.jpg --preset intersect
moviola slideshow slide*.png deck-torch.gif --preset torch --seconds 0.2
moviola slideshow slide*.png deck-tessersect.gif --preset canine
moviola probe lecture.mp4
moviola presets
moviola doctor
moviola history --preset canine --limit 10
moviola stats
moviola chains
moviola install-plugin --target ~/.config/opencode
moviola flash
```

Every verb accepts `--db PATH` and `--ffmpeg-dir PATH`, prints JSON, and
exits nonzero with the failure named on stderr. Well — every verb but one.
`moviola flash` prints something else. See [the Easter Egg](#-the-easter-egg--the-intersect-divergence).

---

## 🗄️ The index — `moviola.db`, always seeable

One SQLite file, default `./moviola.db` in the working directory
(`MOVIOLA_DB` overrides). One row per conversion, success or failure,
written before the tool returns:

| Column group | Columns |
|:--|:--|
| When | `id`, `created_at` (UTC ISO-8601) |
| Source | `source_path`, `source_bytes`, `source_format`, `source_width`, `source_height`, `source_fps`, `source_duration` |
| Output | `output_path`, `output_bytes`, `output_format`, `output_width`, `output_height`, `output_fps` |
| The cut | `preset`, `height`, `ratio`, `bytes_saved`, `ffmpeg_path`, `command` (full argv, JSON) |
| The verdict | `status` (`ok`/`error`), `error` |

Query it with anything:

```sh
sqlite3 moviola.db "SELECT preset, COUNT(*), SUM(source_bytes), SUM(output_bytes)
FROM conversions WHERE status='ok' GROUP BY preset;"
```

Files **intertwined** by the protocol — a Torch GIF fed back in to become
an mp4, a Standard GIF re-cut under Tessersect — are joinable in one
query, and `index_chains` is exactly that join. Dimension change across a
whole lineage stops being folklore and becomes a `SELECT`.

---

## 🐕 Canine Logic & the Tessersect

The Moviola papers in this repository describe a *"Canine-Logic"* sensor:
1-bit sparse matrices, delta-motion only, kinetic frequency above 90 fps —
the Dynamic Vision Sensor (DVS) reading of how a dog actually sees:
dichromatic, rod-dominated, acuity-poor, *motion-rich*, with a flicker
fusion threshold near 70–90 Hz where a human's saturates around 60. A dog
watching your 24 fps video sees a slideshow. A dog watching the world
sees the deltas.

**Preset D, the Canine Logic Moviola Tessersect** is that description as
an ffmpeg chain, built for machines rather than retinas:

1. **Sample at 90 fps** — the top of the canine flicker band, the paper's
   +90fps kinetic frequency, and (not coincidentally) Intersect velocity.
2. **Cut every instant to a 120-line 1-bit Grey-Ink cell** — NTSC-J seat,
   greyedge relief, overcalc curve, hard threshold. Two levels survive:
   black, and the grey ink at ~192 that carries every border, subtitle and
   contour.
3. **Collage sixteen consecutive cells into one 4×4 tesseract net**,
   oldest top-left → newest bottom-right. One output frame = sixteen
   informational contents, the way Chuck's Intersect encodes a database
   as a flashing wall of images for instant absorption. (The name is the
   wordplay owned outright: **Tessersect** = tesseract × Intersect.)

What this buys a training pipeline: a vision model that ingests frames as
tokens absorbs **16 instants per frame** at 824×480 for a 1100×640 source —
temporal density a frame-sampler would need sixteen separate ingestions
to match, at 65,525 B for 29.6 s of animated content. And two honest
limits, measured while building it:

* **Cells hold state on slow sources.** `fps=90` over a 10 fps source
  repeats each instant ~9 times across cells — the 1-bit sensor watching
  a slower world, exactly as the paper's DVS holds state between events.
  Feed it a true 90+ fps capture and every cell is a distinct instant.
* **An event gate was tried and killed.** Dropping near-duplicate cells
  with `mpdecimate` collapsed the doctor clip to a single collage frame:
  at 120 lines, small-but-dense text changes fall under its changed-block
  fraction. Tessersect therefore keeps every sampled instant. A dial
  that erases the information it was built to carry does not ship.

For **slideshows**, images *are* the cells: sixteen slides per collage
frame, cell duration `1/90 s` at flash velocity — a thousand-slide corpus
deck becomes 63 collage frames.

---

## 🎓 For training enthusiasts

This MCP is built as much for dataset builders as for developers. Three
recipes, with the arithmetic printed:

**Documentary → laptop-scale corpus.** `convert_media` with `torch`
(default 360p, 5 fps, 1-bit). At the doctor clip's worst-case 504 B/s, a
1 h 50 m source is ~3.3 MB; lecture-style content with static frames
measures ~100 B/frame, i.e. ~1.8 MB per hour at 5 fps. Subtitles survive:
that is what the overcalc curve is *for*.

**Billion-image pre-training, honestly.** At a measured ~100 B per static
Torch frame, 10⁹ frames ≈ 100 GB as monolithic GIF streams — and GIF is
the honest ceiling: shard by source (one file per lecture/deck), never one
file per corpus. With **Tessersect**, the same billion instants pack 16
per frame: ~6.25×10⁷ collage frames. At the doctor clip's 392 B per
collage (65,525 B / 167), that is ~24 GB carrying a billion instants —
for animated content. Static informational slides (code, text, diagrams)
measure far below both anchors. Run one conversion, read your own
`bytes_saved`, multiply. The index is your dataset card's evidence table.

**Slideshow decks as flash corpora.** `slideshow_from_images` with
`canine` turns an ordered folder of PNG/JPG (screenshots, code pages,
document scans) into Tessersect flash frames at 90 cells/s ingestion
velocity. Pair with `index_stats` to report exactly what the corpus cost.

---

## 🔌 The OpenCode plugin — GIF in, MP4 out

Models that refuse `image/gif` still refuse your evidence. The Nova Violet
OpenCode build solved this in-source: the read tool attaches a GIF as
`video/gif`, and the session relabels it `video/mp4` on the wire (servers
validate the mime allowlist but sniff content, so *the label routes while
the bytes rule*). This wheel ships that adapter for **stock** OpenCode:

| File (in the wheel) | Form | Installs to |
|:--|:--|:--|
| `plugin_data/moviola-gif-as-mp4.mjs` | ECMAScript, no build step, local models welcome | `<config>/plugins/` |
| `plugin_data/moviola-gif-as-mp4.ts` | TypeScript source, same logic | `<config>/plugins/` |
| `plugin_data/read.ts` | the portable read tool (attaches GIF as video) | `<config>/tools/read.ts` |
| `plugin_data/install.mjs` + `package.json` | npm installer (`moviola-install-plugin` bin) | `npx` after npm publish |

```sh
moviola install-plugin                      # ~/.config/opencode, .mjs form
moviola install-plugin --target .opencode --format ts
node install.mjs ~/.config/opencode         # or straight from an unpacked wheel
```

A different existing `tools/read.ts` is **never** overwritten without
`--force` — the skip is named in the result. Opt out at runtime with
`OPENCODE_GIF_AS_VIDEO=0`, the same switch as the in-source build. One
deliberate widening versus the source: the plugin relabels `image/gif`
too, because stock OpenCode produces it; the rename lives only on the
wire copy, your stored sessions keep their true mime.

---

## 🥚 The Easter Egg — the Intersect Divergence

Where the Tessersect actually came from: an email full of flashing images
that puts a database in a man's head, a mad scientist (so cool) whose
memory survives the rewriting of history, a divergence meter reading
0.571024 in one worldline and 1.048596 in the one where the cuts were
made correctly — the whole tale, and what was engineered from it, lives
in [docs/easter-egg.md](docs/easter-egg.md).

The short version is a verb:

```sh
$ moviola flash
INTERSECT FLASH - I know Moviola.
...
Divergence meter: 0.892776
Reading Steiner: 4 conversions remembered in .../moviola.db - the index
does not forget a cut when the worldline changes.
The Organization is watching your file sizes. Stay grey.
El Psy Kongroo.
```

That 0.892776 is not set dressing. It is
`0.571024 + saved_fraction × (1.048596 − 0.571024)` computed live from the
demo ledger behind the gallery above (920,372 B in, 300,295 B out).
Yours will differ. It is supposed to.

---

## 🎓 Verify it yourself

```sh
git clone https://github.com/Nova-Violet-Role/Moviola-Protocol-MCP.git
cd Moviola-Protocol-MCP
uv sync
uv run pytest            # 21 tests: acceptance, presets, index, behaviours,
                         # a real MCP stdio session, the easter egg
uv run moviola doctor    # trio + version, exit 0
uv run moviola convert <any-clip> out.gif --preset canine
sqlite3 moviola.db "SELECT preset, source_bytes, output_bytes FROM conversions;"
```

The acceptance test was written first and watched fail
(`ModuleNotFoundError`, for the right reason) before a line of the package
existed. The wheel you install was verified by *listing its contents* —
which caught, and killed, a first build that contained nothing but
metadata — and by running it clean-room from a bare temp directory
against the reference clip. An instrument that has never failed on
purpose is an untested instrument; every instrument here has been
failed on purpose.

---

## 🤝 Contributing

| Area | How you can help |
|:--|:--|
| 🎯 **Falsify a claim** | Prove one of our documented numbers wrong on your content. Credited in the changelog. |
| 🎞️ **Presets** | Cut a new dial on real footage and bring the mux report — numbers first, names after. |
| 🖥️ **Platforms** | Run `doctor` + the suite where ffmpeg lives somewhere else, and tell us what diverged. |
| 🌍 **Docs** | Say which sentence you had to read twice. That is a defect in the sentence. |
| 💡 **Ideas** | Tell us what a *measured* media tool should refuse to claim. |

## 🏛️ Where this sits in the organisation

**Nova-Violet Role** is a non-profit working where cognitive science, law
and software meet — frameworks for approaching complex problems from more
than one angle at a time. Moviola Protocol MCP is its *sensory* arm: the
same discipline the organisation applies to reasoning (declare the shape,
measure reality against it, keep the ledger) applied to pixels. The
papers in this repository (`MOVIOLA-PROTOCOL.md` is the bench truth;
`Moviola_Protocol.md` is the vision it answers to) are the two ends of
that argument, and the code is where they agree to be bound by exit codes.

## ☕ Supporting a non-profit

[Ko-fi](https://ko-fi.com/saimonokuma) buys time, never priority. The
roadmap is set by falsified claims and measured benches, in the open.

---

## 📄 Licence

Copyright 2026 **Saimonokuma**.

`SPDX-License-Identifier: AGPL-3.0-or-later OR EUPL-1.2`

Licensed under the GNU Affero General Public License v3.0 or later, or,
at your choice, the European Union Public Licence v1.2. These are
**copyleft** licences, chosen deliberately over permissive ones: what is
shared here cannot be enclosed later, by anyone, including us. If this
project ever goes quiet, the code, the measurements and the history
remain yours to carry forward.

Steins;Gate and Chuck are referenced in `docs/easter-egg.md` as
inspiration only; no assets from either work are included.

---

<div align="center">

### ⚜️ Moviola Protocol MCP

*Cut in grey. Measured in bytes. Remembered in the index.*

[![Support Our Journey](https://img.shields.io/badge/🔗_Support_Our_Journey-Ko--fi-FF5E5B?style=for-the-badge)](https://ko-fi.com/saimonokuma)

[Issues](https://github.com/Nova-Violet-Role/Moviola-Protocol-MCP/issues) · [Releases](https://github.com/Nova-Violet-Role/Moviola-Protocol-MCP/releases) · [Licence](LICENSE) · [Easter Egg](docs/easter-egg.md)

© 2026 Nova-Violet Role · Non-Profit Organization

All frameworks open-source under copyleft licences — AGPL-3.0-or-later OR EUPL-1.2

*Created with ❤️ for the advancement of human understanding*

</div>

---

<details>
<summary><b>Topics</b></summary>

`#MCP` `#ModelContextProtocol` `#MCPServer` `#FFmpeg` `#VideoConversion` `#GIF`
`#Greyscale` `#OneBit` `#MachineVision` `#PreTraining` `#DatasetTools` `#UVX`
`#Python` `#OpenCode` `#OpenCodePlugin` `#SQLite` `#MediaIndex` `#CanineLogic`
`#Tessersect` `#Neuromorphic` `#DVS` `#Agpl` `#Eupl` `#Copyleft` `#Spdx`
`#OpenSource` `#NonProfit` `#AiTooling` `#DeveloperTools` `#Falsifiable`

</details>
